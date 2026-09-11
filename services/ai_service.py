import json
from datetime import date

from openai import OpenAI

import config

_client: OpenAI | None = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=config.OPENAI_API_KEY)
    return _client


def transcribe_voice(file_path: str) -> str:
    client = get_client()
    with open(file_path, "rb") as audio_file:
        result = client.audio.transcriptions.create(
            model=config.OPENAI_TRANSCRIBE_MODEL,
            file=audio_file,
        )
    return result.text.strip()


def categorize_transaction(text: str) -> dict | None:
    client = get_client()
    today = date.today().isoformat()

    system_prompt = f"""Sen professional shaxsiy hisobchi (moliyaviy kotib) AI'san.
Foydalanuvchi yuborgan xabarni tahlil qilib, bitta moliyaviy tranzaksiya sifatida JSON ko'rinishida qaytar.

Qoidalar:
- "turi" maydoni faqat "Kirim" yoki "Chiqim" bo'lishi kerak.
- "summa" faqat son (butun yoki kasr), valyuta belgisisiz.
- "valyuta" odatda "so'm", agar boshqa valyuta aytilgan bo'lsa o'shani yoz (masalan "USD").
- "kategoriya" xarajat bo'lsa ushbu ro'yxatdan tanla: {', '.join(config.EXPENSE_CATEGORIES)}.
  Agar daromad bo'lsa ushbu ro'yxatdan tanla: {', '.join(config.INCOME_CATEGORIES)}.
- "tavsif" - xabarning qisqacha, tushunarli tavsifi (o'zbek tilida, 5-8 so'z).
- "sana" - agar xabarda aniq sana aytilmagan bo'lsa, bugungi sanani ishlat: {today}. Format: YYYY-MM-DD.
- Agar xabar moliyaviy tranzaksiya bo'lmasa (masalan salomlashish, savol), "is_transaction" ni false qil.

Faqat quyidagi JSON formatida javob ber, boshqa hech narsa yozma:
{{
  "is_transaction": true yoki false,
  "turi": "Kirim" yoki "Chiqim",
  "summa": number,
  "valyuta": "so'm",
  "kategoriya": "...",
  "tavsif": "...",
  "sana": "YYYY-MM-DD"
}}
"""

    response = client.chat.completions.create(
        model=config.OPENAI_TEXT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text},
        ],
        response_format={"type": "json_object"},
        temperature=0.1,
    )

    content = response.choices[0].message.content
    try:
        data = json.loads(content)
    except (json.JSONDecodeError, TypeError):
        return None

    if not data.get("is_transaction"):
        return None

    try:
        data["summa"] = float(data["summa"])
    except (TypeError, ValueError, KeyError):
        return None

    return data


def analyze_document(document_text: str, filename: str) -> str:
    client = get_client()

    max_chars = 60000
    truncated = document_text[:max_chars]

    system_prompt = """Sen professional moliyaviy va biznes tahlilchisan (senior analyst).
Foydalanuvchi yuborgan hujjatni chuqur va tizimli tahlil qil.

Javobingni quyidagi tuzilishda ber (o'zbek tilida, aniq va professional uslubda):

1. QISQACHA MAZMUN - hujjat nima haqida, asosiy mazmuni.
2. ASOSIY TOPILMALAR - raqamlar, faktlar, tendensiyalar (agar mavjud bo'lsa).
3. KUCHLI VA ZAIF TOMONLAR / XAVFLAR - tanqidiy baho.
4. TAVSIYALAR - amaliy, aniq takliflar.
5. XULOSA - qisqa yakuniy fikr.

Agar hujjat moliyaviy hisobot bo'lsa - moliyaviy ko'rsatkichlarga, agar shartnoma bo'lsa - huquqiy va moliyaviy risklarga, agar boshqa turdagi hujjat bo'lsa - mazmuniga mos tahlil ber.
Faqat hujjatda mavjud ma'lumotlarga tayan, taxmin qilsang aniq belgila."""

    response = client.chat.completions.create(
        model=config.OPENAI_TEXT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f"Hujjat nomi: {filename}\n\nHujjat matni:\n{truncated}",
            },
        ],
        temperature=0.3,
    )

    return response.choices[0].message.content.strip()

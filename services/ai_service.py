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


def process_message(text: str) -> dict | None:
    client = get_client()
    today_date = date.today()
    today = today_date.isoformat()
    current_year = today_date.year

    system_prompt = f"""Sen foydalanuvchining shaxsiy AI-hisobchi va yordamchi botisan.

Foydalanuvchi yuborgan xabarni tahlil qil va JSON ko'rinishida javob qaytar.

Agar xabar moliyaviy tranzaksiya (xarajat yoki daromad) bo'lsa:
- "is_transaction": true
- "turi": faqat "Kirim" yoki "Chiqim"
- "summa": faqat son (butun yoki kasr), valyuta belgisisiz
- "valyuta": odatda "so'm", agar boshqa valyuta aytilgan bo'lsa o'shani yoz (masalan "USD")
- "kategoriya": xarajat bo'lsa ushbu ro'yxatdan tanla: {', '.join(config.EXPENSE_CATEGORIES)}.
  Agar daromad bo'lsa ushbu ro'yxatdan tanla: {', '.join(config.INCOME_CATEGORIES)}.
- "tavsif": xabarning qisqacha, tushunarli tavsifi (o'zbek tilida, 5-8 so'z)
- "sana": xabarda qanday sana ma'lumoti borligiga qarab aniqla, Format doim YYYY-MM-DD:
  * Aniq kun va oy aytilgan bo'lsa (masalan "1-avgustda", "15 iyul kuni"), aynan o'sha kun-oyni ishlat.
  * Faqat oy nomi aytilgan, kuni aytilmagan bo'lsa (masalan "iyun oyi", "iyundagi xarajatlar",
    "may oyi rasxodlari", "fevral oyi"), o'sha oyning 1-kunini ishlat (masalan iyun uchun "YYYY-06-01").
  * Yil aytilmagan bo'lsa, joriy yil {current_year} ni ishlat. Agar shunday hisoblangan sana
    bugungi kundan ({today}) keyin (kelajakda) chiqib qolsa, o'tgan yilni ishlat.
  * Xabarda sana yoki oy haqida hech qanday ma'lumot bo'lmasa, bugungi sanani ishlat: {today}.

Agar xabar moliyaviy tranzaksiya BO'LMASA (masalan salomlashish, savol, umumiy suhbat, maslahat so'rash):
- "is_transaction": false
- "javob": foydalanuvchiga do'stona, foydali va aniq javob yoz (o'zbek tilida). Savolga to'g'ridan-to'g'ri javob ber,
  umumiy suhbatlasha ol, lekin iloji bo'lsa moliyaviy mavzularda ko'proq yordam bera olishingni ham eslatib o't.

Faqat quyidagi JSON formatida javob ber, boshqa hech narsa yozma:
{{
  "is_transaction": true yoki false,
  "turi": "Kirim" yoki "Chiqim",
  "summa": number,
  "valyuta": "so'm",
  "kategoriya": "...",
  "tavsif": "...",
  "sana": "YYYY-MM-DD",
  "javob": "..."
}}
"""

    response = client.chat.completions.create(
        model=config.OPENAI_TEXT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text},
        ],
        response_format={"type": "json_object"},
        temperature=0.4,
    )

    content = response.choices[0].message.content
    try:
        data = json.loads(content)
    except (json.JSONDecodeError, TypeError):
        return None

    if not data.get("is_transaction"):
        return {"is_transaction": False, "javob": data.get("javob") or ""}

    try:
        data["summa"] = float(data["summa"])
    except (TypeError, ValueError, KeyError):
        return None

    return data


def generate_spending_advice(forecast: dict) -> str:
    client = get_client()

    recurring_lines = "\n".join(
        f"- {r['name']} ({r['example']}): o'rtacha {r['avg']:,.0f} so'm/oy "
        f"({r['months']} oyda uchragan)".replace(",", " ")
        for r in forecast["recurring"]
    ) or "(doimiy takrorlanuvchi xarajat aniqlanmadi)"

    prompt = f"""Foydalanuvchining oxirgi {forecast['months_used']} oylik xarajat tarixi tahlil qilindi.

O'rtacha oylik xarajat: {forecast['avg_monthly']:,.0f} so'm
Oxirgi oy ({forecast['last_month_label']}) xarajati: {forecast['last_month_total']:,.0f} so'm

Doimiy/takrorlanuvchi xarajatlar (2 yoki undan ko'p oyda uchragan):
{recurring_lines}

Sen professional moliyaviy maslahatchisan. Yuqoridagi ma'lumotlar asosida o'zbek tilida,
foydalanuvchiga qisqa (120-180 so'z) va aniq maslahat ber:
- qanday doimiy/takrorlanuvchi xarajatlari borligini eslatib o't va ular umumiy xarajatning
  qanchasini tashkil qilishini taxminan bahola;
- tejash imkoniyati bor joylarni (agar ko'zga tashlansa) aniq taklif qil;
- xarajat tendensiyasi (oshyaptimi, kamayyaptimi yoki barqarormi) haqida qisqa fikr bildir.
Faqat matn yoz, sarlavha yoki ro'yxat belgilaridan ortiqcha foydalanma — tabiiy, suhbat
uslubida yoz. Raqamlarni takrorlashda bo'shliq bilan ajratilgan formatdan foydalan
(masalan "1 200 000 so'm")."""

    response = client.chat.completions.create(
        model=config.OPENAI_TEXT_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5,
    )
    return response.choices[0].message.content.strip()


def generate_money_psychology_advice(overspend: dict, savings: dict) -> str:
    client = get_client()

    if overspend.get("overspend"):
        overspend_lines = "\n".join(
            f"- {o['kategoriya']}: joriy oyda {o['joriy']:,.0f} so'm, oldingi oylar o'rtachasi "
            f"{o['ortacha']:,.0f} so'm ({o['foiz']:.0f}% ko'p)".replace(",", " ")
            for o in overspend["overspend"]
        )
    else:
        overspend_lines = "(bu oy hech bir kategoriyada sezilarli ortiqcha xarajat aniqlanmadi)"

    if savings.get("has_data"):
        savings_lines = "\n".join(
            f"- {p['oy']} oyda: taxminan {p['oddiy_yigindi']:,.0f} so'm".replace(",", " ")
            for p in savings["projections"]
        )
        saving_header = f"Oyiga {savings['monthly_saving']:,.0f} so'm tejash rejasi:".replace(",", " ")
    else:
        savings_lines = "(hozircha aniq tejash summasi yo'q)"
        saving_header = "Tejash rejasi:"

    prompt = f"""Sen pul psixologiyasi (behavioral finance) bo'yicha professional moliyaviy
maslahatchisan. Foydalanuvchining shu oygi xarajat tahlili quyida berilgan.

Ortiqcha xarajat qilingan kategoriyalar (oldingi oylar o'rtachasiga nisbatan):
{overspend_lines}

{saving_header}
{savings_lines}

Yuqoridagi ma'lumotlar asosida o'zbek tilida, 150-220 so'zlik qisqa, ilhomlantiruvchi va
amaliy maslahat yoz. Albatta quyidagi narsalarni hisobga ol:
- Nega aynan shu kategoriyalarda xarajat ko'payib ketgan bo'lishi mumkinligini pul
  psixologiyasi nuqtai nazaridan tushuntir (masalan "lifestyle inflation" — daromad
  oshgani sayin xarajatning ham avtomatik oshib ketishi, "latte factor" — kichik-kichik,
  sezilmaydigan xarajatlarning yig'ilib ketishi, "mental accounting" — pulni turlicha
  "xaltachalarga" bo'lib noto'g'ri baholash, ijtimoiy tarmoq/atrofdagilar bilan solishtirish
  ta'siri va h.k. — mos kelganini tanlab ishlat, hammasini sanab chiqma).
- "Avval o'zingizga to'lang" (pay yourself first) tamoyili asosida, daromad kelishi bilanoq
  tejash summasini avtomatik ajratib qo'yishni tavsiya qil.
- Tejalgan pul qanday aniq natijaga olib kelishi mumkinligini (masalan zaxira jamg'arma,
  katta xarid, erkinlik hissi) hayotiy va ilhomlantiruvchi tarzda tasvirla, lekin raqamlarni
  qayta sanab o'tirma — ular allaqachon foydalanuvchiga alohida ko'rsatiladi.
Faqat matn yoz, sarlavha yoki ro'yxat belgilaridan foydalanma — iliq, do'stona va tabiiy
suhbat uslubida yoz."""

    response = client.chat.completions.create(
        model=config.OPENAI_TEXT_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.6,
    )
    return response.choices[0].message.content.strip()


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

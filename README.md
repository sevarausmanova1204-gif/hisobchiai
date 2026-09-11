# AI Hisobchi Telegram Bot

Ikkita asosiy funksiyaga ega Telegram bot:

1. **AI-hisobchi** — foydalanuvchi matn yoki ovozli xabar yuboradi ("Bozordan 50000 so'm oziq-ovqat oldim"), bot buni AI yordamida tahlil qilib (kirim/chiqim, summa, kategoriya, sana) Google Sheets jadvaliga yozadi. `/excel` buyrug'i orqali barcha yozuvlar Excel (.xlsx) fayl ko'rinishida, kategoriyalar bo'yicha xulosa varag'i bilan qaytariladi.
2. **AI-maslahatchi** — foydalanuvchi istalgan hujjat (PDF, DOCX, XLSX, TXT, CSV) yuborsa, bot professional tahlilchi sifatida hujjatni chuqur tahlil qilib, tuzilgan xulosa qaytaradi.

## Talab qilinadigan narsalar

- Python 3.10+
- Telegram bot tokeni ([@BotFather](https://t.me/BotFather) orqali)
- OpenAI API kaliti ([platform.openai.com](https://platform.openai.com/api-keys)) — matn tahlili, ovozni matnga o'girish va hujjat tahlili uchun
- Google Cloud xizmat hisobi (service account) — Google Sheets bilan ishlash uchun

## O'rnatish

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Sozlash

1. `.env.example` faylini `.env` nomiga nusxalang va qiymatlarni to'ldiring:

```bash
cp .env.example .env
```

2. **Telegram token**: `@BotFather` dan yangi bot yarating va tokenni `TELEGRAM_BOT_TOKEN` ga qo'ying.

3. **OpenAI kalit**: [platform.openai.com](https://platform.openai.com/api-keys) dan API key oling, `OPENAI_API_KEY` ga qo'ying. Bu matn tahlili, hujjat tahlili va ovozli xabarlarni matnga o'girish (Whisper) uchun ishlatiladi.

4. **Google Sheets**:
   - [Google Cloud Console](https://console.cloud.google.com/) da yangi loyiha yarating.
   - "Google Sheets API" va "Google Drive API" ni yoqing.
   - "Service Account" yarating, unga JSON kalit (credentials) yuklab oling va loyihaning ildiz papkasiga `credentials.json` nomi bilan saqlang (yoki `.env` dagi `GOOGLE_CREDENTIALS_FILE` ni mos yo'lga o'zgartiring).
   - Yangi Google Sheets jadval yarating, uni service account emailiga (masalan `xxx@xxx.iam.gserviceaccount.com`) **Editor** huquqi bilan ulashing (Share).
   - Jadval URL manzilidagi ID qismini (`https://docs.google.com/spreadsheets/d/<SPREADSHEET_ID>/edit`) `.env` dagi `SPREADSHEET_ID` ga qo'ying.

5. **Ruxsat berilgan foydalanuvchilar (ixtiyoriy)**: `.env` dagi `ALLOWED_USER_IDS` ga Telegram foydalanuvchi ID'laringizni vergul bilan ajratib yozing (masalan `@userinfo3bot` yordamida topish mumkin). Faqat shu ID'lar botdan foydalana oladi. Bo'sh qoldirilsa, bot hamma uchun ochiq bo'ladi.

## Ishga tushirish

```bash
python main.py
```

## 24/7 ishlashi uchun Railway'ga joylashtirish

Bot doimiy (kompyuter o'chirilgan yoki uxlab qolgan taqdirda ham) ishlashi uchun uni Railway kabi bulutli xizmatga joylashtirish mumkin:

1. [railway.app](https://railway.app/) da hisob oching (GitHub orqali kirish qulay) va kartangizni bog'lang (Railway pullik, lekin kichik botlar uchun oyiga bir necha dollar yetadi).
2. **New Project → Deploy from GitHub repo** ni tanlang va shu repozitoriyni (`hisobchiai`) tanlang.
3. Loyiha `Procfile` (`worker: python main.py`) orqali avtomatik "worker" (fon jarayoni) sifatida aniqlanadi — alohida sozlash shart emas.
4. **Variables** bo'limiga o'ting va quyidagi barcha o'zgaruvchilarni qo'shing (`.env` faylingizdagi qiymatlar bilan bir xil):
   - `TELEGRAM_BOT_TOKEN`
   - `OPENAI_API_KEY`
   - `SPREADSHEET_ID`
   - `WORKSHEET_NAME` (masalan `Tranzaksiyalar`)
   - `ALLOWED_USER_IDS`
   - `GOOGLE_CREDENTIALS_JSON` — bu yerga `credentials.json` faylining **butun matnini** joylang (Railway ko'p qatorli matnni qabul qiladi, formatlash shart emas). Bu bo'lsa, `GOOGLE_CREDENTIALS_FILE`ni qo'shish shart emas.
5. Saqlagach, Railway avtomatik deploy qiladi va bot fon jarayoni sifatida doimiy ishlay boshlaydi.
6. Keyingi safar kodni yangilab, GitHub'ga push qilsangiz, Railway avtomatik qayta deploy qiladi.

## Buyruqlar

- `/start` — botni boshlash, tanishtirish
- `/help` — yordam
- `/excel` — barcha moliyaviy yozuvlarni Excel fayl ko'rinishida yuklab olish

## Loyiha tuzilishi

```
excel bot/
├── main.py                  # Bot kirish nuqtasi
├── config.py                 # Sozlamalar (.env dan o'qiydi)
├── requirements.txt
├── Procfile                   # Railway/Heroku uchun worker jarayoni
├── runtime.txt                # Python versiyasi (bulut uchun)
├── .env.example
├── handlers/
│   ├── access.py               # ruxsat berilgan foydalanuvchilarni tekshirish
│   ├── keyboard.py             # asosiy tugmalar klaviaturasi
│   ├── common.py              # /start, /help
│   ├── accountant.py          # matn/ovozli xabar -> tranzaksiya
│   ├── balance.py              # /balans
│   ├── cancel.py                # yozuvni bekor qilish (undo)
│   ├── export.py               # /excel eksport
│   └── advisor.py              # hujjat tahlili
└── services/
    ├── ai_service.py            # OpenAI: kategoriyalash, transkripsiya, tahlil
    ├── sheets_service.py        # Google Sheets bilan ishlash
    ├── excel_service.py         # .xlsx fayl generatsiya qilish
    └── document_service.py      # PDF/DOCX/XLSX/TXT dan matn ajratib olish
```

## Eslatma

- Ovozli xabarlar OpenAI Whisper API orqali matnga o'giriladi, shuning uchun internet aloqasi va yetarli OpenAI balansi kerak.
- Skanerlangan (rasm ko'rinishidagi) PDF fayllardan matn avtomatik ajratib olinmaydi — OCR qo'shilmagan.
- `credentials.json` faylini hech qachon ochiq repozitoriyga yuklamang.

import os

from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

GOOGLE_CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID", "")
WORKSHEET_NAME = os.getenv("WORKSHEET_NAME", "Tranzaksiyalar")

OPENAI_TEXT_MODEL = os.getenv("OPENAI_TEXT_MODEL", "gpt-4o-mini")
OPENAI_TRANSCRIBE_MODEL = os.getenv("OPENAI_TRANSCRIBE_MODEL", "whisper-1")

_allowed_ids_raw = os.getenv("ALLOWED_USER_IDS", "")
ALLOWED_USER_IDS = {
    int(uid.strip()) for uid in _allowed_ids_raw.split(",") if uid.strip().isdigit()
}

EXPENSE_CATEGORIES = [
    "Oziq-ovqat",
    "Transport",
    "Kiyim-kechak",
    "Kommunal to'lovlar",
    "Sog'liqni saqlash",
    "Ta'lim",
    "Ko'ngilochar / dam olish",
    "Aloqa va internet",
    "Uy-joy",
    "Boshqa xarajatlar",
]

INCOME_CATEGORIES = [
    "Ish haqi",
    "Biznes daromadi",
    "Frilanс / qo'shimcha ish",
    "Sovg'a",
    "Boshqa daromad",
]

SHEET_HEADERS = [
    "Sana",
    "Turi",
    "Summa",
    "Valyuta",
    "Kategoriya",
    "Tavsif",
    "Foydalanuvchi",
]

REQUIRED_ENV_VARS = [
    "TELEGRAM_BOT_TOKEN",
    "OPENAI_API_KEY",
    "SPREADSHEET_ID",
]


def validate_config() -> list[str]:
    missing = [name for name in REQUIRED_ENV_VARS if not globals().get(name)]
    return missing

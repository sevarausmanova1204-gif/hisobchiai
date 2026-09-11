from telegram import Update
from telegram.ext import ContextTypes

from handlers.access import restricted
from handlers.keyboard import MAIN_KEYBOARD

WELCOME_TEXT = """Assalomu alaykum! Men sizning shaxsiy AI-hisobchi va tahlilchi botingizman.

📊 <b>Hisobchi funksiyasi</b>
Menga oddiy matn yoki ovozli xabar yuboring, masalan:
  • "Bozordan 50000 so'mlik oziq-ovqat oldim"
  • "Ish haqim 3 000 000 so'm tushdi"
Men uni avtomatik tahlil qilib, kerakli bo'limga ajratib Google Sheets jadvaliga saqlab qo'yaman.

📥 Barcha yozuvlaringizni Excel faylida olish uchun: /excel

📄 <b>AI-maslahatchi funksiyasi</b>
Har qanday hujjat (PDF, Word, Excel, TXT) yuboring — men uni professional tahlilchi sifatida chuqur tahlil qilib beraman.

Yordam uchun: /help"""

HELP_TEXT = """<b>Buyruqlar</b>
/start — botni ishga tushirish
/help — yordam
/excel — barcha moliyaviy yozuvlaringizni Excel fayl ko'rinishida yuklab olish
/balans — kirim, chiqim va joriy balansni ko'rish
/dashboard — moliyaviy holatingiz bo'yicha vizual dashboard (rasm)

<b>Qanday ishlatiladi</b>
1. Xarajat yoki daromadingizni matn yoki ovozli xabar orqali yozing — bot buni avtomatik kategoriyalab, Google Sheets-dagi Kirim yoki Chiqim varag'iga saqlaydi.
2. Istalgan hujjatni (PDF/DOCX/XLSX/TXT) yuboring — bot professional tahlilchi sifatida chuqur tahlil qilib javob beradi.
3. Pastdagi tugmalardan ham foydalanishingiz mumkin: 📊 Hisobot, 💼 Balans, 📈 Dashboard, 🧠 AI Maslahatchi, ℹ️ Yordam."""

ADVISOR_PROMPT_TEXT = """🧠 <b>AI Maslahatchi</b>

Tahlil qilinishi kerak bo'lgan hujjatni (PDF, DOCX, XLSX, TXT yoki CSV) shu chatga yuboring — men uni professional tahlilchi sifatida chuqur tahlil qilib, tuzilgan xulosa qaytaraman."""


@restricted
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_html(WELCOME_TEXT, reply_markup=MAIN_KEYBOARD)


@restricted
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_html(HELP_TEXT, reply_markup=MAIN_KEYBOARD)


@restricted
async def advisor_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_html(ADVISOR_PROMPT_TEXT)

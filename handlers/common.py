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

🔮 <b>Xarajat prognozi</b>
/prognoz — o'tgan oylardagi va doimiy takrorlanuvchi xarajatlaringizni o'rganib, maslahat beraman va kelasi 1/3/5/9/12 oy uchun taxminiy xarajatni hisoblab beraman.

💰 <b>Tejash rejasi</b>
/tejash — qaysi kategoriyada odatdagidan ko'p xarajat qilganingizni topib beraman, tejash maqsadi bo'yicha 3/6/12/24/36 oylik natija hisob-kitobini va pul psixologiyasi bo'yicha shaxsiy maslahat beraman. Har oyning 1-sanasida bu hisobotni o'zim ham avtomatik yuborib turaman.

Yordam uchun: /help"""

HELP_TEXT = """<b>Buyruqlar</b>
/start — botni ishga tushirish
/help — yordam
/excel — barcha moliyaviy yozuvlaringizni Excel fayl ko'rinishida yuklab olish
/balans — kirim, chiqim va joriy balansni ko'rish
/dashboard — moliyaviy holatingiz bo'yicha vizual dashboard (rasm), davr tanlab
/sheetsdashboard — Google Sheets ichida jadval va diagrammalardan iborat "Dashboard" varag'ini yaratadi/yangilaydi
/prognoz — o'tgan oylar va doimiy xarajatlaringiz asosida maslahat va 1/3/5/9/12 oylik xarajat prognozi
/tejash — ortiqcha xarajat qilingan kategoriyalar, tejash maqsadi bo'yicha hisob-kitob va pul psixologiyasi maslahati (masalan: /tejash 500000 — aniq summa bilan)
/tozalash — Google Sheets'dagi aynan bir xil takroriy yozuvlarni tozalaydi

<b>Qanday ishlatiladi</b>
1. Xarajat yoki daromadingizni matn yoki ovozli xabar orqali yozing — bot buni avtomatik kategoriyalab, Google Sheets-dagi Kirim yoki Chiqim varag'iga saqlaydi.
2. Istalgan hujjatni (PDF/DOCX/XLSX/TXT) yuboring — bot professional tahlilchi sifatida chuqur tahlil qilib javob beradi.
3. Pastdagi tugmalardan ham foydalanishingiz mumkin: 📊 Hisobot, 💼 Balans, 📈 Dashboard, 📄 Sheets Dashboard, 🧠 AI Maslahatchi, 🔮 Xarajat prognozi, 💰 Tejash rejasi, ℹ️ Yordam."""

ADVISOR_PROMPT_TEXT = """🧠 <b>AI Maslahatchi</b>

Tahlil qilinishi kerak bo'lgan hujjatni (PDF, DOCX, XLSX, TXT yoki CSV) shu chatga yuboring — men uni professional tahlilchi sifatida chuqur tahlil qilib, tuzilgan xulosa qaytaraman.

💡 Buning o'rniga o'tgan oylardagi xarajatlaringiz asosida maslahat va kelajak xarajat prognozini olmoqchi bo'lsangiz: /prognoz"""


@restricted
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_html(WELCOME_TEXT, reply_markup=MAIN_KEYBOARD)


@restricted
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_html(HELP_TEXT, reply_markup=MAIN_KEYBOARD)


@restricted
async def advisor_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_html(ADVISOR_PROMPT_TEXT)

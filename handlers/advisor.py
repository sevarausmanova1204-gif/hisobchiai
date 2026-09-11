import logging
import os
import tempfile

from telegram import Update
from telegram.ext import ContextTypes

from handlers.access import restricted
from services import ai_service, document_service, forecast_service, sheets_service

logger = logging.getLogger(__name__)

TELEGRAM_MAX_LEN = 4000


def _format_amount(amount: float) -> str:
    return f"{amount:,.0f}".replace(",", " ")


async def _send_long_message(update: Update, text: str) -> None:
    for i in range(0, len(text), TELEGRAM_MAX_LEN):
        await update.message.reply_text(text[i : i + TELEGRAM_MAX_LEN])


@restricted
async def spending_forecast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.chat.send_action("typing")

    try:
        transactions = sheets_service.get_all_transactions()
    except Exception:
        logger.exception("Google Sheets'dan ma'lumot olishda xato")
        await update.message.reply_text(
            "Google Sheets bilan bog'lanishda xatolik yuz berdi. Sozlamalarni tekshiring."
        )
        return

    forecast = forecast_service.compute_forecast(transactions)
    if not forecast["has_data"]:
        await update.message.reply_text(
            "Hozircha prognoz qilish uchun xarajat tarixi yetarli emas."
        )
        return

    try:
        advice = ai_service.generate_spending_advice(forecast)
    except Exception:
        logger.exception("Xarajat prognozi uchun maslahat yasashda xato")
        advice = None

    lines = ["📈 <b>Xarajat prognozi va maslahat</b>\n"]
    if advice:
        lines.append(advice + "\n")

    if forecast["recurring"]:
        lines.append("<b>Doimiy xarajatlaringiz</b>")
        for r in forecast["recurring"][:6]:
            example = f" ({r['example']})" if r["example"] and r["example"] != r["name"] else ""
            lines.append(f"  • {r['name']}{example}: {_format_amount(r['avg'])} so'm/oy")
        lines.append("")

    lines.append(
        f"<b>Taxminiy kelajak xarajatlari</b> "
        f"(oxirgi {forecast['months_used']} oylik o'rtacha — {_format_amount(forecast['avg_monthly'])} so'm/oy — asosida):"
    )
    for h in forecast_service.HORIZONS:
        lines.append(f"  • {h} oylik: {_format_amount(forecast['forecasts'][h])} so'm")

    await update.message.reply_html("\n".join(lines))


@restricted
async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    document = update.message.document
    if not document:
        return

    ext = os.path.splitext(document.file_name or "")[1].lower()
    if ext not in document_service.SUPPORTED_EXTENSIONS:
        await update.message.reply_text(
            "Bu fayl turini tahlil qila olmayman. Qo'llab-quvvatlanadigan formatlar: "
            "PDF, DOCX, XLSX, TXT, CSV."
        )
        return

    await update.message.reply_text("📄 Hujjat qabul qilindi, chuqur tahlil qilinmoqda...")
    await update.message.chat.send_action("typing")

    tg_file = await context.bot.get_file(document.file_id)

    with tempfile.TemporaryDirectory() as tmp_dir:
        local_path = os.path.join(tmp_dir, document.file_name)
        await tg_file.download_to_drive(local_path)

        try:
            text = document_service.extract_text(local_path)
        except Exception:
            logger.exception("Hujjatdan matn ajratib olishda xato")
            await update.message.reply_text(
                "Hujjatdan matnni o'qib bo'lmadi. Fayl buzilgan yoki himoyalangan bo'lishi mumkin."
            )
            return

    if not text or not text.strip():
        await update.message.reply_text(
            "Hujjatda tahlil qilinadigan matn topilmadi (skanerlangan rasm bo'lishi mumkin)."
        )
        return

    try:
        analysis = ai_service.analyze_document(text, document.file_name)
    except Exception:
        logger.exception("Hujjatni AI orqali tahlil qilishda xato")
        await update.message.reply_text(
            "Hujjatni tahlil qilishda xatolik yuz berdi. Birozdan so'ng qayta urinib ko'ring."
        )
        return

    await _send_long_message(update, f"🧠 Professional tahlil:\n\n{analysis}")

import logging
import os
import tempfile

from telegram import Update
from telegram.ext import ContextTypes

from handlers.access import restricted
from services import dashboard_service, sheets_service

logger = logging.getLogger(__name__)


@restricted
async def show_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.chat.send_action("upload_photo")

    try:
        transactions = sheets_service.get_all_transactions()
    except Exception:
        logger.exception("Google Sheets'dan ma'lumot olishda xato")
        await update.message.reply_text(
            "Google Sheets bilan bog'lanishda xatolik yuz berdi. Sozlamalarni tekshiring."
        )
        return

    if not transactions:
        await update.message.reply_text("Hozircha hech qanday yozuv mavjud emas.")
        return

    with tempfile.TemporaryDirectory() as tmp_dir:
        filepath = os.path.join(tmp_dir, "dashboard.png")
        try:
            dashboard_service.build_dashboard_image(transactions, filepath)
        except Exception:
            logger.exception("Dashboard rasmini yasashda xato")
            await update.message.reply_text(
                "Dashboard yasashda xatolik yuz berdi. Birozdan so'ng qayta urinib ko'ring."
            )
            return

        with open(filepath, "rb") as f:
            await update.message.reply_photo(
                photo=f,
                caption="📈 Moliyaviy dashboardingiz tayyor.",
            )

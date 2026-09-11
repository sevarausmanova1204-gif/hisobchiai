import logging
import os
import tempfile
from datetime import datetime

from telegram import Update
from telegram.ext import ContextTypes

from handlers.access import restricted
from services import excel_service, sheets_service

logger = logging.getLogger(__name__)


@restricted
async def export_excel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.chat.send_action("upload_document")

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

    text_report = excel_service.build_text_report(transactions)
    for i in range(0, len(text_report), 4000):
        await update.message.reply_html(text_report[i : i + 4000])

    filename = f"hisobot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

    with tempfile.TemporaryDirectory() as tmp_dir:
        filepath = os.path.join(tmp_dir, filename)
        excel_service.build_excel(transactions, filepath)

        with open(filepath, "rb") as f:
            await update.message.reply_document(
                document=f,
                filename=filename,
                caption=f"📊 Jami {len(transactions)} ta yozuv topildi.",
            )

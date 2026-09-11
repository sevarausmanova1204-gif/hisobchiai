import logging

from telegram import Update
from telegram.ext import ContextTypes

import config
from services import sheets_service

logger = logging.getLogger(__name__)


async def cancel_transaction(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = update.effective_user.id if update.effective_user else None

    if config.ALLOWED_USER_IDS and user_id not in config.ALLOWED_USER_IDS:
        await query.answer("Ruxsatingiz yo'q.", show_alert=True)
        return

    await query.answer()

    try:
        row_number = int(query.data.split(":", 1)[1])
    except (IndexError, ValueError):
        return

    try:
        sheets_service.delete_transaction(row_number)
    except Exception:
        logger.exception("Tranzaksiyani bekor qilishda xato")
        await query.edit_message_text("Bekor qilishda xatolik yuz berdi. Qayta urinib ko'ring.")
        return

    await query.edit_message_text("🗑 Bekor qilindi — yozuv o'chirildi.")

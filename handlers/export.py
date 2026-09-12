import logging
import os
import tempfile
from datetime import datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

import config
from handlers.access import restricted
from services import dashboard_service, excel_service, sheets_service

logger = logging.getLogger(__name__)

_ALL_PERIOD = "all"


def _period_keyboard(transactions: list[dict]) -> InlineKeyboardMarkup:
    months = dashboard_service.list_available_months(transactions)

    rows = [[InlineKeyboardButton("📊 Barcha davr", callback_data=f"reportp:{_ALL_PERIOD}")]]
    month_buttons = [
        InlineKeyboardButton(
            dashboard_service.month_label_uz(year, month),
            callback_data=f"reportp:{year:04d}-{month:02d}",
        )
        for year, month in months
    ]
    for i in range(0, len(month_buttons), 2):
        rows.append(month_buttons[i : i + 2])

    return InlineKeyboardMarkup(rows)


@restricted
async def export_excel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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

    await update.message.reply_text(
        "📊 Qaysi davr uchun hisobot kerak?",
        reply_markup=_period_keyboard(transactions),
    )


async def send_period_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = update.effective_user.id if update.effective_user else None
    if config.ALLOWED_USER_IDS and user_id not in config.ALLOWED_USER_IDS:
        await query.answer("Ruxsatingiz yo'q.", show_alert=True)
        return

    await query.answer()

    period = query.data.split(":", 1)[1]
    month_filter = None
    period_label = "Barcha davr"
    if period != _ALL_PERIOD:
        year_str, month_str = period.split("-")
        month_filter = (int(year_str), int(month_str))
        period_label = dashboard_service.month_label_uz(*month_filter)

    try:
        all_transactions = sheets_service.get_all_transactions()
    except Exception:
        logger.exception("Google Sheets'dan ma'lumot olishda xato")
        await query.edit_message_text("Google Sheets bilan bog'lanishda xatolik yuz berdi.")
        return

    transactions = dashboard_service.filter_transactions_by_month(all_transactions, month_filter)

    if not transactions:
        await query.edit_message_text(f"{period_label} uchun hech qanday yozuv topilmadi.")
        return

    await query.message.chat.send_action("upload_document")

    text_report = excel_service.build_text_report(transactions)
    for i in range(0, len(text_report), 4000):
        await query.message.reply_html(text_report[i : i + 4000])

    filename = f"hisobot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

    with tempfile.TemporaryDirectory() as tmp_dir:
        filepath = os.path.join(tmp_dir, filename)
        excel_service.build_excel(transactions, filepath)

        with open(filepath, "rb") as f:
            await query.message.reply_document(
                document=f,
                filename=filename,
                caption=f"📊 {period_label} — jami {len(transactions)} ta yozuv topildi.",
            )

    await query.edit_message_text(f"📊 {period_label} uchun hisobot yuborildi.")

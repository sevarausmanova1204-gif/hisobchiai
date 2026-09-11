import logging
import os
import tempfile

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

import config
from handlers.access import restricted
from services import dashboard_service, sheets_dashboard_service, sheets_service

logger = logging.getLogger(__name__)

_ALL_PERIOD = "all"


def _period_keyboard(transactions: list[dict]) -> InlineKeyboardMarkup:
    months = dashboard_service.list_available_months(transactions)

    rows = [[InlineKeyboardButton("📊 Barcha davr", callback_data=f"dashp:{_ALL_PERIOD}")]]
    month_buttons = [
        InlineKeyboardButton(
            dashboard_service.month_label_uz(year, month),
            callback_data=f"dashp:{year:04d}-{month:02d}",
        )
        for year, month in months
    ]
    for i in range(0, len(month_buttons), 2):
        rows.append(month_buttons[i : i + 2])

    return InlineKeyboardMarkup(rows)


@restricted
async def show_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
        "📈 Qaysi davr uchun dashboard kerak?",
        reply_markup=_period_keyboard(transactions),
    )


async def send_period_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
        transactions = sheets_service.get_all_transactions()
    except Exception:
        logger.exception("Google Sheets'dan ma'lumot olishda xato")
        await query.edit_message_text("Google Sheets bilan bog'lanishda xatolik yuz berdi.")
        return

    with tempfile.TemporaryDirectory() as tmp_dir:
        filepath = os.path.join(tmp_dir, "dashboard.png")
        try:
            dashboard_service.build_dashboard_image(transactions, filepath, month_filter=month_filter)
        except Exception:
            logger.exception("Dashboard rasmini yasashda xato")
            await query.edit_message_text("Dashboard yasashda xatolik yuz berdi. Qayta urinib ko'ring.")
            return

        with open(filepath, "rb") as f:
            await query.message.reply_photo(
                photo=f,
                caption=f"📈 {period_label} uchun dashboard.",
            )

    await query.edit_message_text(f"📈 {period_label} uchun dashboard yuborildi.")


@restricted
async def show_sheets_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.chat.send_action("typing")

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

    try:
        url = sheets_dashboard_service.build_sheets_dashboard(transactions)
    except Exception:
        logger.exception("Sheets dashboardini yasashda xato")
        await update.message.reply_text(
            "Google Sheets'da dashboard yasashda xatolik yuz berdi. Birozdan so'ng qayta urinib ko'ring."
        )
        return

    await update.message.reply_text(
        f"📄 Google Sheets'da \"Dashboard\" varag'i yangilandi:\n{url}"
    )

import logging
from datetime import time as dt_time

from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

import config
from handlers import (
    accountant,
    advisor,
    balance,
    budget,
    cancel,
    common,
    dashboard,
    export,
    maintenance,
)
from handlers.keyboard import (
    BTN_ADVISOR,
    BTN_BALANCE,
    BTN_DASHBOARD,
    BTN_FORECAST,
    BTN_HELP,
    BTN_REPORT,
    BTN_SAVINGS,
    BTN_SHEETS_DASHBOARD,
)
from services import sheets_service

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

MONTHLY_REPORT_TIME = dt_time(hour=9, minute=0)


async def _send_monthly_report(context) -> None:
    user_id = context.job.data["user_id"]
    try:
        transactions = sheets_service.get_all_transactions()
    except Exception:
        logger.exception("Oylik hisobot uchun Google Sheets'dan ma'lumot olishda xato")
        return

    report = budget.build_report_text(transactions)
    if report is None:
        return

    try:
        await context.bot.send_message(chat_id=user_id, text=report, parse_mode="HTML")
    except Exception:
        logger.exception("Oylik hisobotni %s foydalanuvchiga yuborishda xato", user_id)


def main() -> None:
    missing = config.validate_config()
    if missing:
        raise SystemExit(
            f".env faylida quyidagi sozlamalar to'ldirilmagan: {', '.join(missing)}"
        )

    application = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", common.start))
    application.add_handler(CommandHandler("help", common.help_command))
    application.add_handler(CommandHandler("excel", export.export_excel))
    application.add_handler(CommandHandler("balans", balance.show_balance))
    application.add_handler(CommandHandler("dashboard", dashboard.show_dashboard))
    application.add_handler(CommandHandler("sheetsdashboard", dashboard.show_sheets_dashboard))
    application.add_handler(CommandHandler("tozalash", maintenance.cleanup_duplicates))
    application.add_handler(CommandHandler("prognoz", advisor.spending_forecast))
    application.add_handler(CommandHandler("tejash", budget.savings_plan))

    application.add_handler(MessageHandler(filters.Text([BTN_REPORT]), export.export_excel))
    application.add_handler(MessageHandler(filters.Text([BTN_BALANCE]), balance.show_balance))
    application.add_handler(MessageHandler(filters.Text([BTN_DASHBOARD]), dashboard.show_dashboard))
    application.add_handler(
        MessageHandler(filters.Text([BTN_SHEETS_DASHBOARD]), dashboard.show_sheets_dashboard)
    )
    application.add_handler(MessageHandler(filters.Text([BTN_ADVISOR]), common.advisor_prompt))
    application.add_handler(MessageHandler(filters.Text([BTN_FORECAST]), advisor.spending_forecast))
    application.add_handler(MessageHandler(filters.Text([BTN_SAVINGS]), budget.savings_plan))
    application.add_handler(MessageHandler(filters.Text([BTN_HELP]), common.help_command))

    application.add_handler(MessageHandler(filters.Document.ALL, advisor.handle_document))
    application.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, accountant.handle_voice))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, accountant.handle_text))

    application.add_handler(
        CallbackQueryHandler(cancel.cancel_transaction, pattern=r"^cancel_tx:(Kirim|Chiqim):\d+$")
    )
    application.add_handler(
        CallbackQueryHandler(dashboard.send_period_dashboard, pattern=r"^dashp:")
    )
    application.add_handler(
        CallbackQueryHandler(export.send_period_report, pattern=r"^reportp:")
    )

    if application.job_queue is not None and config.ALLOWED_USER_IDS:
        for user_id in config.ALLOWED_USER_IDS:
            application.job_queue.run_monthly(
                _send_monthly_report,
                when=MONTHLY_REPORT_TIME,
                day=1,
                data={"user_id": user_id},
                name=f"monthly_report_{user_id}",
            )
        logger.info("Oylik avtomatik hisobot %s foydalanuvchi uchun sozlandi.", len(config.ALLOWED_USER_IDS))
    elif application.job_queue is None:
        logger.warning(
            "JobQueue mavjud emas (python-telegram-bot[job-queue] o'rnatilmagan), "
            "oylik avtomatik hisobot ishlamaydi."
        )
    else:
        logger.warning(
            "ALLOWED_USER_IDS bo'sh, oylik avtomatik hisobotni kimga yuborishni bilmayman."
        )

    logger.info("Bot ishga tushdi...")
    application.run_polling(allowed_updates=None)


if __name__ == "__main__":
    main()

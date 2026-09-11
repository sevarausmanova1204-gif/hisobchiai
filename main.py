import logging

from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

import config
from handlers import accountant, advisor, balance, cancel, common, dashboard, export
from handlers.keyboard import BTN_ADVISOR, BTN_BALANCE, BTN_DASHBOARD, BTN_HELP, BTN_REPORT

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


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

    application.add_handler(MessageHandler(filters.Text([BTN_REPORT]), export.export_excel))
    application.add_handler(MessageHandler(filters.Text([BTN_BALANCE]), balance.show_balance))
    application.add_handler(MessageHandler(filters.Text([BTN_DASHBOARD]), dashboard.show_dashboard))
    application.add_handler(MessageHandler(filters.Text([BTN_ADVISOR]), common.advisor_prompt))
    application.add_handler(MessageHandler(filters.Text([BTN_HELP]), common.help_command))

    application.add_handler(MessageHandler(filters.Document.ALL, advisor.handle_document))
    application.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, accountant.handle_voice))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, accountant.handle_text))

    application.add_handler(
        CallbackQueryHandler(cancel.cancel_transaction, pattern=r"^cancel_tx:(Kirim|Chiqim):\d+$")
    )

    logger.info("Bot ishga tushdi...")
    application.run_polling(allowed_updates=None)


if __name__ == "__main__":
    main()

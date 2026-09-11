import logging

from telegram import Update
from telegram.ext import ContextTypes

from handlers.access import restricted
from services import sheets_service

logger = logging.getLogger(__name__)


@restricted
async def cleanup_duplicates(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.chat.send_action("typing")
    await update.message.reply_text("🧹 Takroriy yozuvlar tekshirilmoqda, biroz kuting...")

    try:
        results = sheets_service.dedupe_all_sheets()
    except Exception:
        logger.exception("Takroriy yozuvlarni tozalashda xato")
        await update.message.reply_text(
            "Tozalashda xatolik yuz berdi. Birozdan so'ng qayta urinib ko'ring."
        )
        return

    total = sum(results.values())
    if total == 0:
        await update.message.reply_text("✅ Takroriy yozuv topilmadi, hammasi toza edi.")
        return

    lines = ["🧹 Takroriy yozuvlar tozalandi:"]
    for sheet_name, count in results.items():
        if count:
            lines.append(f"  • {sheet_name}: {count} ta o'chirildi")
    lines.append(f"\nJami: {total} ta takroriy qator o'chirildi.")

    await update.message.reply_text("\n".join(lines))

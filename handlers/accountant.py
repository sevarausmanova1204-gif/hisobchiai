import logging
import os
import tempfile

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from handlers.access import restricted
from services import ai_service, sheets_service

logger = logging.getLogger(__name__)


def _format_confirmation(data: dict) -> str:
    emoji = "🟢" if data["turi"] == "Kirim" else "🔴"
    summa = f"{data['summa']:,.0f}".replace(",", " ")
    return (
        f"{emoji} <b>{data['turi']}</b> qayd etildi\n\n"
        f"💰 Summa: {summa} {data['valyuta']}\n"
        f"🏷 Kategoriya: {data['kategoriya']}\n"
        f"📝 Tavsif: {data['tavsif']}\n"
        f"📅 Sana: {data['sana']}"
    )


async def _process_transaction_text(update: Update, text: str) -> None:
    data = ai_service.categorize_transaction(text)

    if not data:
        await update.message.reply_text(
            "Bu xabarni moliyaviy tranzaksiya sifatida tushunolmadim. "
            "Iltimos, xarajat yoki daromadni aniqroq yozing "
            "(masalan: \"Taksiga 15000 so'm sarfladim\")."
        )
        return

    user = update.effective_user
    username = f"@{user.username}" if user.username else user.full_name

    row_number = sheets_service.append_transaction(
        sana=data["sana"],
        turi=data["turi"],
        summa=data["summa"],
        valyuta=data.get("valyuta", "so'm"),
        kategoriya=data["kategoriya"],
        tavsif=data.get("tavsif", ""),
        foydalanuvchi=username,
    )

    reply_markup = None
    if row_number is not None:
        reply_markup = InlineKeyboardMarkup(
            [[InlineKeyboardButton("❌ Bekor qilish", callback_data=f"cancel_tx:{row_number}")]]
        )

    await update.message.reply_html(_format_confirmation(data), reply_markup=reply_markup)


@restricted
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text
    if not text:
        return

    await update.message.chat.send_action("typing")

    try:
        await _process_transaction_text(update, text)
    except Exception:
        logger.exception("Matnli tranzaksiyani qayta ishlashda xato")
        await update.message.reply_text(
            "Kechirasiz, xabaringizni qayta ishlashda xatolik yuz berdi. Birozdan so'ng qayta urinib ko'ring."
        )


@restricted
async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.chat.send_action("typing")

    voice = update.message.voice or update.message.audio
    if not voice:
        return

    tg_file = await context.bot.get_file(voice.file_id)

    with tempfile.TemporaryDirectory() as tmp_dir:
        local_path = os.path.join(tmp_dir, "voice.ogg")
        await tg_file.download_to_drive(local_path)

        try:
            text = ai_service.transcribe_voice(local_path)
        except Exception:
            logger.exception("Ovozni matnga o'girishda xato")
            await update.message.reply_text(
                "Ovozli xabarni matnga o'girib bo'lmadi. Iltimos, qayta urinib ko'ring."
            )
            return

    if not text:
        await update.message.reply_text("Ovozli xabardan matn aniqlanmadi.")
        return

    await update.message.reply_text(f"🎙 Aniqlangan matn: \"{text}\"")

    try:
        await _process_transaction_text(update, text)
    except Exception:
        logger.exception("Ovozli tranzaksiyani qayta ishlashda xato")
        await update.message.reply_text(
            "Kechirasiz, xabaringizni qayta ishlashda xatolik yuz berdi. Birozdan so'ng qayta urinib ko'ring."
        )

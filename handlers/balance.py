import logging

from telegram import Update
from telegram.ext import ContextTypes

from handlers.access import restricted
from services import sheets_service

logger = logging.getLogger(__name__)


def _format_amount(amount: float) -> str:
    return f"{amount:,.0f}".replace(",", " ")


@restricted
async def show_balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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

    totals: dict[str, dict[str, float]] = {}
    for row in transactions:
        valyuta = row.get("Valyuta") or "so'm"
        turi = row.get("Turi", "")
        try:
            summa = float(row.get("Summa", 0) or 0)
        except (TypeError, ValueError):
            summa = 0.0

        bucket = totals.setdefault(valyuta, {"Kirim": 0.0, "Chiqim": 0.0})
        if turi == "Kirim":
            bucket["Kirim"] += summa
        else:
            bucket["Chiqim"] += summa

    lines = ["💼 <b>Balans</b>\n"]
    for valyuta, bucket in totals.items():
        balans = bucket["Kirim"] - bucket["Chiqim"]
        emoji = "🟢" if balans >= 0 else "🔴"
        lines.append(
            f"<b>{valyuta}</b>\n"
            f"  Kirim: {_format_amount(bucket['Kirim'])}\n"
            f"  Chiqim: {_format_amount(bucket['Chiqim'])}\n"
            f"  {emoji} Balans: {_format_amount(balans)}"
        )

    lines.append(f"\n📋 Jami yozuvlar: {len(transactions)}")

    await update.message.reply_html("\n\n".join(lines))

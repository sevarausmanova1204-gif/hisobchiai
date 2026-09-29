import logging

from telegram import Update
from telegram.ext import ContextTypes

from handlers.access import restricted
from services import ai_service, budget_advisor_service, forecast_service, sheets_service

logger = logging.getLogger(__name__)

_DEFAULT_SAVING_RATIO = 0.10  # overspend aniqlanmasa, o'rtacha xarajatning 10%i taklif qilinadi


def _format_amount(amount: float) -> str:
    return f"{amount:,.0f}".replace(",", " ")


def _parse_custom_amount(args: list[str]) -> float | None:
    if not args:
        return None
    raw = args[0].replace(" ", "").replace("'", "").replace(",", "")
    try:
        value = float(raw)
    except ValueError:
        return None
    return value if value > 0 else None


def build_report_text(transactions: list[dict], custom_saving: float | None = None) -> str | None:
    """Ortiqcha xarajat tahlili + tejash rejasi + pul psixologiyasi maslahatidan
    iborat to'liq hisobot matnini tuzadi. Ma'lumot yetarli bo'lmasa None qaytaradi."""
    overspend = budget_advisor_service.analyze_month(transactions)
    if not overspend["has_data"]:
        return None

    forecast = forecast_service.compute_forecast(transactions)
    avg_monthly_expense = forecast.get("avg_monthly") if forecast.get("has_data") else None

    if custom_saving:
        monthly_saving = custom_saving
    elif overspend["total_overspend"] > 0:
        monthly_saving = overspend["total_overspend"]
    elif avg_monthly_expense:
        monthly_saving = avg_monthly_expense * _DEFAULT_SAVING_RATIO
    else:
        monthly_saving = 0

    savings = budget_advisor_service.project_savings(
        monthly_saving, avg_monthly_expense=avg_monthly_expense
    )

    try:
        advice = ai_service.generate_money_psychology_advice(overspend, savings)
    except Exception:
        logger.exception("Pul psixologiyasi maslahatini yasashda xato")
        advice = None

    lines = [f"💰 <b>Tejash rejasi</b> — {overspend['target_month_label']}\n"]

    if overspend["overspend"]:
        lines.append(
            f"⚠️ Bu oy oldingi {overspend['prior_months_count']} oy o'rtachasiga nisbatan "
            f"quyidagi kategoriyalarda <b>ortiqcha xarajat</b> qilgansiz:"
        )
        for o in overspend["overspend"][:6]:
            lines.append(
                f"  • {o['kategoriya']}: {_format_amount(o['joriy'])} so'm "
                f"(odatda {_format_amount(o['ortacha'])} so'm — {o['foiz']:.0f}% ko'p, "
                f"+{_format_amount(o['farq'])} so'm)"
            )
        lines.append(
            f"\nAgar shu kategoriyalarni odatiy darajaga qaytarsangiz, oyiga taxminan "
            f"<b>{_format_amount(overspend['total_overspend'])} so'm</b> tejashingiz mumkin edi."
        )
    else:
        lines.append(
            "✅ Bu oy hech bir kategoriyada sezilarli ortiqcha xarajat aniqlanmadi — yaxshi natija!"
        )
    lines.append("")

    if savings.get("has_data"):
        lines.append(
            f"📌 <b>Tejash maqsadi</b>: oyiga {_format_amount(savings['monthly_saving'])} so'm"
        )
        lines.append("Shuncha pulni muntazam tejasangiz, qancha vaqtda nechaga yetadi:")
        for p in savings["projections"]:
            lines.append(
                f"  • {p['oy']} oy: ~{_format_amount(p['oddiy_yigindi'])} so'm "
                f"(oddiy depozitda taxminan {_format_amount(p['depozit_bilan_taxminiy'])} so'm)"
            )
        if savings.get("reserve_months_per_year") and avg_monthly_expense:
            lines.append(
                f"\n🛟 Bir yilda bu — taxminan {savings['reserve_months_per_year']:.1f} oylik "
                f"xarajatingizga teng zaxira jamg'arma degani (o'rtacha oylik xarajatingiz "
                f"{_format_amount(avg_monthly_expense)} so'm asosida)."
            )
        lines.append(
            "\n<i>* Depozit bilan hisob 20% yillik taxminiy foiz asosida, aniq shartlar "
            "bankka qarab farq qilishi mumkin.</i>"
        )
        lines.append("")

    if advice:
        lines.append(f"🧠 <b>Pul psixologiyasi maslahati</b>\n{advice}")

    return "\n".join(lines)


@restricted
async def savings_plan(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.chat.send_action("typing")

    custom_saving = _parse_custom_amount(context.args)
    if context.args and custom_saving is None:
        await update.message.reply_text(
            "Tejash summasini to'g'ri kiriting, masalan: /tejash 500000"
        )
        return

    try:
        transactions = sheets_service.get_all_transactions()
    except Exception:
        logger.exception("Google Sheets'dan ma'lumot olishda xato")
        await update.message.reply_text(
            "Google Sheets bilan bog'lanishda xatolik yuz berdi. Sozlamalarni tekshiring."
        )
        return

    report = build_report_text(transactions, custom_saving=custom_saving)
    if report is None:
        await update.message.reply_text(
            "Hozircha tahlil qilish uchun xarajat tarixi yetarli emas."
        )
        return

    await update.message.reply_html(report)

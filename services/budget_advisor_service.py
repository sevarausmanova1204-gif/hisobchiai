import statistics
from collections import defaultdict
from datetime import datetime

# "Boshqa xarajatlar" — turli-tuman bir martalik xarajatlar uchun umumiy
# qop, shuning uchun ortiqcha xarajat tahlilida hisobga olinmaydi (har oy
# tarkibi butunlay boshqacha bo'lishi mumkin, solishtirish ma'nosiz).
_EXCLUDED_CATEGORIES = {"Boshqa xarajatlar", "Boshqa"}

# Kichik, tasodifiy og'ishlarni "ortiqcha xarajat" deb belgilamaslik uchun
# ikkala chegara ham bajarilishi kerak: mutlaq summa VA nisbiy foiz.
MIN_OVERSPEND_AMOUNT = 20_000
MIN_OVERSPEND_RATIO = 0.15

DEFAULT_LOOKBACK_MONTHS = 3
DEFAULT_SAVING_HORIZONS = (3, 6, 12, 24, 36)

_MONTHS_UZ_FULL = {
    1: "Yanvar", 2: "Fevral", 3: "Mart", 4: "Aprel", 5: "May", 6: "Iyun",
    7: "Iyul", 8: "Avgust", 9: "Sentyabr", 10: "Oktyabr", 11: "Noyabr", 12: "Dekabr",
}


def month_label_uz(year: int, month: int) -> str:
    return f"{_MONTHS_UZ_FULL[month]} {year}"


def _safe_float(value) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _parse_date(value):
    text = str(value or "").strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d.%m.%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def analyze_month(
    transactions: list[dict],
    target_month: tuple[int, int] | None = None,
    lookback: int = DEFAULT_LOOKBACK_MONTHS,
) -> dict:
    """Berilgan oy (yoki ma'lumotdagi oxirgi oy) xarajatlarini undan oldingi
    `lookback` oylik o'rtacha bilan kategoriya-kategoriya solishtiradi va
    sezilarli darajada ko'paygan ("ortiqcha xarajat qilingan") kategoriyalarni
    aniqlaydi."""
    rows = []
    for row in transactions:
        if row.get("Turi") != "Chiqim":
            continue
        valyuta = str(row.get("Valyuta") or "so'm").strip().lower()
        if valyuta not in ("so'm", "som", "sum", "so`m"):
            continue
        d = _parse_date(row.get("Sana"))
        if d is None:
            continue
        rows.append(
            {
                "sana": d,
                "summa": _safe_float(row.get("Summa")),
                "kategoriya": row.get("Kategoriya") or "Boshqa",
            }
        )

    if not rows:
        return {"has_data": False}

    by_month_cat: dict[tuple[int, int], dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for r in rows:
        by_month_cat[(r["sana"].year, r["sana"].month)][r["kategoriya"]] += r["summa"]

    month_keys = sorted(by_month_cat.keys())

    if target_month is None:
        target_month = month_keys[-1]
    elif target_month not in by_month_cat:
        return {"has_data": False}

    target_cats = by_month_cat[target_month]
    target_total = sum(target_cats.values())

    prior_keys = [k for k in month_keys if k < target_month][-lookback:]

    overspend = []
    if prior_keys:
        all_cats = set(target_cats.keys())
        for k in prior_keys:
            all_cats.update(by_month_cat[k].keys())

        for cat in all_cats:
            if cat in _EXCLUDED_CATEGORIES:
                continue
            prior_amounts = [by_month_cat[k].get(cat, 0.0) for k in prior_keys]
            avg_prior = statistics.mean(prior_amounts)
            if avg_prior <= 0:
                continue
            cur = target_cats.get(cat, 0.0)
            diff = cur - avg_prior
            ratio = diff / avg_prior
            if diff >= MIN_OVERSPEND_AMOUNT and ratio >= MIN_OVERSPEND_RATIO:
                overspend.append(
                    {
                        "kategoriya": cat,
                        "joriy": cur,
                        "ortacha": avg_prior,
                        "farq": diff,
                        "foiz": ratio * 100,
                    }
                )
    overspend.sort(key=lambda x: x["farq"], reverse=True)

    return {
        "has_data": True,
        "target_month": target_month,
        "target_month_label": month_label_uz(*target_month),
        "target_total": target_total,
        "prior_months_count": len(prior_keys),
        "overspend": overspend,
        "total_overspend": sum(o["farq"] for o in overspend),
    }


def project_savings(
    monthly_saving: float,
    avg_monthly_expense: float | None = None,
    horizons: tuple[int, ...] = DEFAULT_SAVING_HORIZONS,
    annual_rate: float = 0.20,
) -> dict:
    """Har oy `monthly_saving` miqdorida pul yig'ilsa, belgilangan oylar
    davomida qancha jamg'arma hosil bo'lishini hisoblaydi: oddiy yig'indi
    (faqat qo'shish) va taxminiy oddiy depozit foizi bilan (compound,
    `annual_rate` — bank shartlariga qarab farq qiladigan TAXMINIY foiz)."""
    if monthly_saving <= 0:
        return {"has_data": False}

    monthly_rate = annual_rate / 12
    projections = []
    for h in horizons:
        simple = monthly_saving * h
        compounded = 0.0
        for _ in range(h):
            compounded = (compounded + monthly_saving) * (1 + monthly_rate)
        projections.append({"oy": h, "oddiy_yigindi": simple, "depozit_bilan_taxminiy": compounded})

    reserve_months = None
    if avg_monthly_expense and avg_monthly_expense > 0:
        reserve_months = (monthly_saving * 12) / avg_monthly_expense

    return {
        "has_data": True,
        "monthly_saving": monthly_saving,
        "annual_rate": annual_rate,
        "projections": projections,
        "reserve_months_per_year": reserve_months,
    }

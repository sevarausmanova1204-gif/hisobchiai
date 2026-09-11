from collections import defaultdict
from datetime import datetime

HORIZONS = (1, 3, 5, 9, 12)

_MONTHS_UZ_FULL = {
    1: "Yanvar", 2: "Fevral", 3: "Mart", 4: "Aprel", 5: "May", 6: "Iyun",
    7: "Iyul", 8: "Avgust", 9: "Sentyabr", 10: "Oktyabr", 11: "Noyabr", 12: "Dekabr",
}


def _month_label_uz(year: int, month: int) -> str:
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


def compute_forecast(transactions: list[dict], recurring_min_months: int = 2) -> dict:
    """Chiqim tarixini tahlil qilib, doimiy xarajatlarni va kelajakdagi
    (1/3/5/9/12 oylik) taxminiy xarajatlarni hisoblaydi. Faqat so'm
    tranzaksiyalari hisobga olinadi (oxirgi 12 oylik ma'lumot asosida)."""
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
                "tavsif": (row.get("Tavsif") or "").strip() or (row.get("Kategoriya") or "Boshqa"),
            }
        )

    if not rows:
        return {"has_data": False}

    monthly_totals: dict[tuple[int, int], float] = defaultdict(float)
    for r in rows:
        key = (r["sana"].year, r["sana"].month)
        monthly_totals[key] += r["summa"]

    month_keys = sorted(monthly_totals.keys())
    recent_keys = month_keys[-12:]
    avg_monthly = sum(monthly_totals[k] for k in recent_keys) / len(recent_keys)

    last_key = month_keys[-1]

    by_name: dict[str, dict] = defaultdict(lambda: {"months": set(), "total": 0.0})
    for r in rows:
        key = (r["sana"].year, r["sana"].month)
        info = by_name[r["tavsif"]]
        info["months"].add(key)
        info["total"] += r["summa"]

    recurring = [
        {"name": name, "months": len(info["months"]), "avg": info["total"] / len(info["months"])}
        for name, info in by_name.items()
        if len(info["months"]) >= recurring_min_months
    ]
    recurring.sort(key=lambda x: x["avg"], reverse=True)

    forecasts = {h: avg_monthly * h for h in HORIZONS}

    return {
        "has_data": True,
        "avg_monthly": avg_monthly,
        "months_used": len(recent_keys),
        "last_month_label": _month_label_uz(*last_key),
        "last_month_total": monthly_totals[last_key],
        "recurring": recurring[:10],
        "forecasts": forecasts,
    }

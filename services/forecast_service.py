from collections import defaultdict
from datetime import datetime

HORIZONS = (1, 3, 5, 9, 12)

# "Boshqa xarajatlar" — bu turli-tuman, bir-biriga bog'liq bo'lmagan bir martalik
# xarajatlar uchun umumiy kategoriya, shuning uchun u hech qachon "doimiy xarajat"
# sifatida ko'rsatilmaydi (har oy boshqa-boshqa narsalar bo'lishi mumkin).
_EXCLUDED_RECURRING_CATEGORIES = {"Boshqa xarajatlar", "Boshqa"}

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


def compute_forecast(transactions: list[dict], recurring_ratio: float = 0.6) -> dict:
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

    # Kategoriya bo'yicha guruhlanadi (Tavsif emas) — chunki AI har safar tavsifni
    # biroz boshqacha so'zlar bilan yozadi ("Sport uchun xarajat" / "Sport uchun
    # xarajatlar" kabi), bu esa aslida bitta doimiy xarajatni ikkita alohida
    # qatorga bo'lib yuborardi. Kategoriya barqaror ro'yxatdan tanlangani uchun
    # ishonchliroq guruhlash mezoni.
    #
    # Faqat OXIRGI OYLAR OYNASI (avg_monthly hisoblangan davr) ichidagi va
    # ko'pchilik oylarda (recurring_ratio) takrorlangan kategoriyalar "doimiy
    # xarajat" deb hisoblanadi — bitta-ikkita marta tasodifan boshqa-boshqa
    # oyda uchragan bir martalik xaridlar (masalan turli kurslar) doimiy
    # xarajat sifatida ko'rsatilmasligi kerak. "Boshqa xarajatlar" kabi
    # aralash kategoriyalar umuman hisobga olinmaydi.
    recent_keys_set = set(recent_keys)
    by_category: dict[str, dict] = defaultdict(lambda: {"month_totals": {}, "examples": []})
    for r in rows:
        key = (r["sana"].year, r["sana"].month)
        if key not in recent_keys_set or r["kategoriya"] in _EXCLUDED_RECURRING_CATEGORIES:
            continue
        info = by_category[r["kategoriya"]]
        info["month_totals"][key] = info["month_totals"].get(key, 0.0) + r["summa"]
        if r["tavsif"] and r["tavsif"] not in info["examples"]:
            info["examples"].append(r["tavsif"])

    min_months_required = max(2, round(len(recent_keys) * recurring_ratio))

    recurring = []
    for kategoriya, info in by_category.items():
        amounts = list(info["month_totals"].values())
        if len(amounts) < min_months_required:
            continue
        recurring.append(
            {
                "name": kategoriya,
                "example": info["examples"][0] if info["examples"] else kategoriya,
                "months": len(amounts),
                "avg": sum(amounts) / len(amounts),
            }
        )
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

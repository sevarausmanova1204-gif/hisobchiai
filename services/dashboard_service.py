from collections import defaultdict
from datetime import date, datetime

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

_BG = "#EEECFB"
_CARD = "#FFFFFF"
_INDIGO = "#5B4FE9"
_INDIGO_DARK = "#3B2FB5"
_PINK = "#F15BB5"
_TEXT = "#241E42"
_MUTED = "#8B87A8"
_GREEN = "#22C55E"
_RED = "#EF4444"
_DONUT_COLORS = ["#5B4FE9", "#8B7BF0", "#B79CF2", "#F15BB5", "#FFB4C6", "#22C55E", "#C9C4EE"]

_MONTHS_UZ = {
    1: "Yan", 2: "Fev", 3: "Mar", 4: "Apr", 5: "May", 6: "Iyun",
    7: "Iyul", 8: "Avg", 9: "Sen", 10: "Okt", 11: "Noy", 12: "Dek",
}


def _safe_float(value) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _parse_date(value) -> date | None:
    text = str(value or "").strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d.%m.%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _format_amount(amount: float) -> str:
    return f"{amount:,.0f}".replace(",", " ")


def _card(ax, bg=_CARD):
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.add_patch(
        FancyBboxPatch(
            (0.02, 0.06), 0.96, 0.88,
            boxstyle="round,pad=0,rounding_size=0.08",
            linewidth=0, facecolor=bg, transform=ax.transAxes, clip_on=False,
        )
    )


def _stat_card(ax, label: str, value_text: str, delta_text: str | None, delta_positive: bool):
    _card(ax)
    ax.text(0.12, 0.68, label, fontsize=11, color=_MUTED, transform=ax.transAxes, va="center")
    ax.text(0.12, 0.42, value_text, fontsize=19, color=_TEXT, weight="bold",
            transform=ax.transAxes, va="center")
    if delta_text:
        color = _GREEN if delta_positive else _RED
        arrow = "▲" if delta_positive else "▼"
        ax.text(0.12, 0.20, f"{arrow} {delta_text}", fontsize=10, color=color,
                transform=ax.transAxes, va="center", weight="bold")


def build_dashboard_image(transactions: list[dict], filepath: str) -> str:
    som_rows = []
    other_currency_count = 0
    for row in transactions:
        valyuta = str(row.get("Valyuta") or "so'm").strip().lower()
        if valyuta not in ("so'm", "som", "sum", "so`m"):
            other_currency_count += 1
            continue
        d = _parse_date(row.get("Sana"))
        if d is None:
            continue
        som_rows.append(
            {
                "sana": d,
                "turi": row.get("Turi", "Chiqim"),
                "summa": _safe_float(row.get("Summa")),
                "kategoriya": row.get("Kategoriya") or "Boshqa",
            }
        )

    som_rows.sort(key=lambda r: r["sana"])

    total_kirim = sum(r["summa"] for r in som_rows if r["turi"] == "Kirim")
    total_chiqim = sum(r["summa"] for r in som_rows if r["turi"] == "Chiqim")
    umumiy_balans = total_kirim - total_chiqim

    today = date.today()
    cur_month_key = (today.year, today.month)
    if today.month == 1:
        prev_month_key = (today.year - 1, 12)
    else:
        prev_month_key = (today.year, today.month - 1)

    def _month_totals(month_key):
        kirim = sum(
            r["summa"] for r in som_rows
            if r["turi"] == "Kirim" and (r["sana"].year, r["sana"].month) == month_key
        )
        chiqim = sum(
            r["summa"] for r in som_rows
            if r["turi"] == "Chiqim" and (r["sana"].year, r["sana"].month) == month_key
        )
        return kirim, chiqim

    davr_kirim, davr_chiqim = _month_totals(cur_month_key)
    prev_kirim, prev_chiqim = _month_totals(prev_month_key)
    davr_farq = davr_kirim - davr_chiqim
    prev_farq = prev_kirim - prev_chiqim

    def _pct_change(cur, prev):
        if prev == 0:
            return None
        return (cur - prev) / abs(prev) * 100

    farq_pct = _pct_change(davr_farq, prev_farq)
    kirim_pct = _pct_change(davr_kirim, prev_kirim)
    chiqim_pct = _pct_change(davr_chiqim, prev_chiqim)

    balans_trend: list[tuple[date, float]] = []
    running = 0.0
    by_day: dict[date, float] = defaultdict(float)
    for r in som_rows:
        by_day[r["sana"]] += r["summa"] if r["turi"] == "Kirim" else -r["summa"]
    for d in sorted(by_day):
        running += by_day[d]
        balans_trend.append((d, running))
    if len(balans_trend) > 30:
        balans_trend = balans_trend[-30:]

    by_category: dict[str, float] = defaultdict(float)
    for r in som_rows:
        if r["turi"] == "Chiqim":
            by_category[r["kategoriya"]] += r["summa"]
    top_categories = sorted(by_category.items(), key=lambda x: x[1], reverse=True)
    if len(top_categories) > 6:
        rest_sum = sum(v for _, v in top_categories[6:])
        top_categories = top_categories[:6] + [("Boshqa", rest_sum)]

    monthly: dict[tuple[int, int], dict[str, float]] = defaultdict(lambda: {"Kirim": 0.0, "Chiqim": 0.0})
    for r in som_rows:
        key = (r["sana"].year, r["sana"].month)
        monthly[key][r["turi"]] += r["summa"]
    month_keys = sorted(monthly.keys())[-8:]

    fig = plt.figure(figsize=(12.5, 9), facecolor=_BG)
    gs = fig.add_gridspec(
        4, 4,
        height_ratios=[0.9, 1.15, 2.3, 2.1],
        hspace=0.55, wspace=0.35,
        left=0.045, right=0.965, top=0.965, bottom=0.045,
    )

    ax_title = fig.add_subplot(gs[0, :])
    ax_title.axis("off")
    ax_title.text(0, 0.75, "Moliyaviy Dashboard", fontsize=22, weight="bold", color=_TEXT)
    ax_title.text(
        0, 0.15,
        f"Bugungi holat — {today.strftime('%d.%m.%Y')}",
        fontsize=12, color=_MUTED,
    )

    ax1 = fig.add_subplot(gs[1, 0])
    _stat_card(ax1, "Umumiy balans", f"{_format_amount(umumiy_balans)} so'm", None, True)

    ax2 = fig.add_subplot(gs[1, 1])
    _stat_card(
        ax2, "Shu oy — farq", f"{_format_amount(davr_farq)} so'm",
        f"{abs(farq_pct):.0f}% o'tgan oyga" if farq_pct is not None else None,
        farq_pct is not None and farq_pct >= 0,
    )

    ax3 = fig.add_subplot(gs[1, 2])
    _stat_card(
        ax3, "Shu oy — chiqim", f"{_format_amount(davr_chiqim)} so'm",
        f"{abs(chiqim_pct):.0f}% o'tgan oyga" if chiqim_pct is not None else None,
        chiqim_pct is not None and chiqim_pct <= 0,
    )

    ax4 = fig.add_subplot(gs[1, 3])
    _stat_card(
        ax4, "Shu oy — daromad", f"{_format_amount(davr_kirim)} so'm",
        f"{abs(kirim_pct):.0f}% o'tgan oyga" if kirim_pct is not None else None,
        kirim_pct is not None and kirim_pct >= 0,
    )

    ax_trend = fig.add_subplot(gs[2, 0:3])
    _card(ax_trend)
    if balans_trend:
        inner = ax_trend.inset_axes([0.08, 0.14, 0.88, 0.72])
        xs = [d for d, _ in balans_trend]
        ys = [v for _, v in balans_trend]
        inner.plot(xs, ys, color=_INDIGO, linewidth=2.5, marker="o", markersize=3)
        inner.fill_between(xs, ys, min(ys + [0]) if ys else 0, color=_INDIGO, alpha=0.12)
        inner.set_title("Balans trendi", loc="left", fontsize=13, color=_TEXT, weight="bold", pad=10)
        inner.spines[["top", "right", "left"]].set_visible(False)
        inner.tick_params(axis="x", labelsize=8, colors=_MUTED, rotation=30)
        inner.tick_params(axis="y", labelsize=8, colors=_MUTED)
        inner.set_facecolor(_CARD)
        inner.grid(axis="y", color="#E4E1F5", linewidth=0.8)
    else:
        ax_trend.text(0.5, 0.5, "Hozircha ma'lumot yo'q", ha="center", va="center",
                       color=_MUTED, transform=ax_trend.transAxes)

    ax_donut = fig.add_subplot(gs[2, 3])
    _card(ax_donut)
    if top_categories:
        inner = ax_donut.inset_axes([0.10, 0.50, 0.80, 0.42])
        values = [v for _, v in top_categories]
        colors = _DONUT_COLORS[: len(values)]
        inner.pie(
            values, colors=colors, startangle=90,
            wedgeprops={"width": 0.42, "edgecolor": _CARD, "linewidth": 2},
        )
        total_chiqim_cat = sum(values) or 1
        inner.text(0, 0, f"{_format_amount(total_chiqim_cat)}\nso'm", ha="center", va="center",
                    fontsize=8.5, color=_TEXT, weight="bold")
        ax_donut.text(0.08, 0.96, "Xarajatlar taqsimoti", fontsize=12, color=_TEXT,
                       weight="bold", transform=ax_donut.transAxes)

        row_h = 0.052
        start_y = 0.44
        for i, (name, value) in enumerate(top_categories):
            y = start_y - i * row_h
            pct = value / total_chiqim_cat * 100
            ax_donut.add_patch(
                plt.Rectangle(
                    (0.08, y - 0.014), 0.028, 0.028,
                    transform=ax_donut.transAxes, facecolor=colors[i],
                    linewidth=0, clip_on=False,
                )
            )
            label = name if len(name) <= 16 else name[:15] + "…"
            ax_donut.text(
                0.125, y, f"{label} — {pct:.0f}%", fontsize=7.6, color=_TEXT,
                transform=ax_donut.transAxes, va="center",
            )
    else:
        ax_donut.text(0.5, 0.5, "Chiqim yo'q", ha="center", va="center",
                       color=_MUTED, transform=ax_donut.transAxes)

    ax_bar = fig.add_subplot(gs[3, :])
    _card(ax_bar)
    if month_keys:
        inner = ax_bar.inset_axes([0.05, 0.16, 0.9, 0.68])
        labels = [f"{_MONTHS_UZ[m]}" for _, m in month_keys]
        kirim_vals = [monthly[k]["Kirim"] for k in month_keys]
        chiqim_vals = [monthly[k]["Chiqim"] for k in month_keys]
        x = range(len(month_keys))
        width = 0.34
        inner.bar([i - width / 2 for i in x], kirim_vals, width=width, color=_INDIGO, label="Daromad")
        inner.bar([i + width / 2 for i in x], chiqim_vals, width=width, color=_PINK, label="Xarajat")
        inner.set_xticks(list(x))
        inner.set_xticklabels(labels, fontsize=9, color=_MUTED)
        inner.tick_params(axis="y", labelsize=8, colors=_MUTED)
        inner.spines[["top", "right", "left"]].set_visible(False)
        inner.set_facecolor(_CARD)
        inner.grid(axis="y", color="#E4E1F5", linewidth=0.8)
        inner.legend(loc="upper left", fontsize=8.5, frameon=False, labelcolor=_TEXT)
        ax_bar.text(0.02, 0.94, "Oylik daromad va xarajat", fontsize=13, color=_TEXT,
                     weight="bold", transform=ax_bar.transAxes)
    else:
        ax_bar.text(0.5, 0.5, "Hozircha ma'lumot yo'q", ha="center", va="center",
                     color=_MUTED, transform=ax_bar.transAxes)

    if other_currency_count:
        fig.text(
            0.045, 0.008,
            f"* Dashboard faqat so'm tranzaksiyalarini hisoblaydi "
            f"({other_currency_count} ta boshqa valyutadagi yozuv kiritilmadi).",
            fontsize=8, color=_MUTED,
        )

    fig.savefig(filepath, facecolor=_BG, dpi=170)
    plt.close(fig)
    return filepath

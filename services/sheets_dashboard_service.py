import logging
from collections import defaultdict
from datetime import date, datetime

import gspread
from gspread_formatting import CellFormat, TextFormat, format_cell_range

from services import sheets_service

logger = logging.getLogger(__name__)

_DASHBOARD_SHEET = "Dashboard"

_MONTHS_UZ_FULL = {
    1: "Yanvar", 2: "Fevral", 3: "Mart", 4: "Aprel", 5: "May", 6: "Iyun",
    7: "Iyul", 8: "Avgust", 9: "Sentyabr", 10: "Oktyabr", 11: "Noyabr", 12: "Dekabr",
}


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


def _aggregate(transactions: list[dict]):
    som_rows = []
    for row in transactions:
        valyuta = str(row.get("Valyuta") or "so'm").strip().lower()
        if valyuta not in ("so'm", "som", "sum", "so`m"):
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

    by_category: dict[str, float] = defaultdict(float)
    for r in som_rows:
        if r["turi"] == "Chiqim":
            by_category[r["kategoriya"]] += r["summa"]
    top_categories = sorted(by_category.items(), key=lambda x: x[1], reverse=True)[:12]

    monthly: dict[tuple[int, int], dict[str, float]] = defaultdict(lambda: {"Kirim": 0.0, "Chiqim": 0.0})
    for r in som_rows:
        key = (r["sana"].year, r["sana"].month)
        monthly[key][r["turi"]] += r["summa"]
    month_keys = sorted(monthly.keys())[-12:]

    return {
        "total_kirim": total_kirim,
        "total_chiqim": total_chiqim,
        "top_categories": top_categories,
        "month_keys": month_keys,
        "monthly": monthly,
    }


def _clear_existing_charts(spreadsheet, sheet_id: int) -> None:
    try:
        meta = spreadsheet.fetch_sheet_metadata()
    except Exception:
        return

    requests = []
    for sheet in meta.get("sheets", []):
        if sheet.get("properties", {}).get("sheetId") != sheet_id:
            continue
        for chart in sheet.get("charts", []):
            chart_id = chart.get("chartId")
            if chart_id is not None:
                requests.append({"deleteEmbeddedObject": {"objectId": chart_id}})

    if requests:
        spreadsheet.batch_update({"requests": requests})


def build_sheets_dashboard(transactions: list[dict]) -> str:
    """Google Sheets ichida jadval va diagrammalardan iborat "Dashboard" varag'ini yaratadi/yangilaydi."""
    spreadsheet = sheets_service._get_spreadsheet()  # noqa: SLF001

    try:
        worksheet = spreadsheet.worksheet(_DASHBOARD_SHEET)
    except gspread.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=_DASHBOARD_SHEET, rows=200, cols=12)
    else:
        _clear_existing_charts(spreadsheet, worksheet.id)
        worksheet.clear()

    agg = _aggregate(transactions)
    balans = agg["total_kirim"] - agg["total_chiqim"]

    worksheet.update("A1", [["MOLIYAVIY DASHBOARD"]])
    worksheet.update(
        "A2", [[f"Yangilangan: {datetime.now().strftime('%d.%m.%Y %H:%M')}"]]
    )
    worksheet.update(
        "A4",
        [
            ["Jami kirim (so'm)", agg["total_kirim"]],
            ["Jami chiqim (so'm)", agg["total_chiqim"]],
            ["Balans (so'm)", balans],
        ],
    )

    worksheet.update("A7", [["Kategoriya bo'yicha chiqimlar"]])
    cat_header_row = 8
    cat_rows = [["Kategoriya", "Summa"]]
    for name, amount in agg["top_categories"]:
        cat_rows.append([name, amount])
    worksheet.update(f"A{cat_header_row}", cat_rows)
    cat_count = len(agg["top_categories"])

    worksheet.update("D7", [["Oylik daromad va xarajat"]])
    month_header_row = 8
    month_rows = [["Oy", "Kirim", "Chiqim"]]
    for year, month in agg["month_keys"]:
        totals = agg["monthly"][(year, month)]
        month_rows.append(
            [f"{_MONTHS_UZ_FULL[month]} {year}", totals["Kirim"], totals["Chiqim"]]
        )
    worksheet.update(f"D{month_header_row}", month_rows)
    month_count = len(agg["month_keys"])

    try:
        format_cell_range(worksheet, "A1", CellFormat(textFormat=TextFormat(bold=True, fontSize=16)))
        format_cell_range(worksheet, "A7:F7", CellFormat(textFormat=TextFormat(bold=True)))
        format_cell_range(
            worksheet, f"A{cat_header_row}:B{cat_header_row}",
            CellFormat(textFormat=TextFormat(bold=True)),
        )
        format_cell_range(
            worksheet, f"D{month_header_row}:F{month_header_row}",
            CellFormat(textFormat=TextFormat(bold=True)),
        )
    except Exception:
        logger.exception("Dashboard formatlashda xato (e'tiborsiz qoldirildi)")

    chart_requests = []
    if cat_count:
        chart_requests.append(
            {
                "addChart": {
                    "chart": {
                        "spec": {
                            "title": "Xarajatlar taqsimoti",
                            "pieChart": {
                                "legendPosition": "RIGHT_LEGEND",
                                "domain": {
                                    "sourceRange": {
                                        "sources": [
                                            {
                                                "sheetId": worksheet.id,
                                                "startRowIndex": cat_header_row,
                                                "endRowIndex": cat_header_row + cat_count,
                                                "startColumnIndex": 0,
                                                "endColumnIndex": 1,
                                            }
                                        ]
                                    }
                                },
                                "series": {
                                    "sourceRange": {
                                        "sources": [
                                            {
                                                "sheetId": worksheet.id,
                                                "startRowIndex": cat_header_row,
                                                "endRowIndex": cat_header_row + cat_count,
                                                "startColumnIndex": 1,
                                                "endColumnIndex": 2,
                                            }
                                        ]
                                    }
                                },
                            },
                        },
                        "position": {
                            "overlayPosition": {
                                "anchorCell": {
                                    "sheetId": worksheet.id,
                                    "rowIndex": cat_header_row + cat_count + 2,
                                    "columnIndex": 0,
                                },
                                "widthPixels": 480,
                                "heightPixels": 320,
                            }
                        },
                    }
                }
            }
        )

    if month_count:
        chart_requests.append(
            {
                "addChart": {
                    "chart": {
                        "spec": {
                            "title": "Oylik daromad va xarajat",
                            "basicChart": {
                                "chartType": "COLUMN",
                                "legendPosition": "BOTTOM_LEGEND",
                                "domains": [
                                    {
                                        "domain": {
                                            "sourceRange": {
                                                "sources": [
                                                    {
                                                        "sheetId": worksheet.id,
                                                        "startRowIndex": month_header_row - 1,
                                                        "endRowIndex": month_header_row + month_count,
                                                        "startColumnIndex": 3,
                                                        "endColumnIndex": 4,
                                                    }
                                                ]
                                            }
                                        }
                                    }
                                ],
                                "series": [
                                    {
                                        "series": {
                                            "sourceRange": {
                                                "sources": [
                                                    {
                                                        "sheetId": worksheet.id,
                                                        "startRowIndex": month_header_row - 1,
                                                        "endRowIndex": month_header_row + month_count,
                                                        "startColumnIndex": 4,
                                                        "endColumnIndex": 5,
                                                    }
                                                ]
                                            }
                                        },
                                        "targetAxis": "LEFT_AXIS",
                                    },
                                    {
                                        "series": {
                                            "sourceRange": {
                                                "sources": [
                                                    {
                                                        "sheetId": worksheet.id,
                                                        "startRowIndex": month_header_row - 1,
                                                        "endRowIndex": month_header_row + month_count,
                                                        "startColumnIndex": 5,
                                                        "endColumnIndex": 6,
                                                    }
                                                ]
                                            }
                                        },
                                        "targetAxis": "LEFT_AXIS",
                                    },
                                ],
                                "headerCount": 1,
                            },
                        },
                        "position": {
                            "overlayPosition": {
                                "anchorCell": {
                                    "sheetId": worksheet.id,
                                    "rowIndex": cat_header_row + cat_count + 2,
                                    "columnIndex": 6,
                                },
                                "widthPixels": 560,
                                "heightPixels": 320,
                            }
                        },
                    }
                }
            }
        )

    if chart_requests:
        try:
            spreadsheet.batch_update({"requests": chart_requests})
        except Exception:
            logger.exception("Sheets diagrammalarini yaratishda xato (jadval baribir yaratildi)")

    return worksheet.url

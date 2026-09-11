import json
import re

import gspread
from google.oauth2.service_account import Credentials

import config

_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

_client = None
_spreadsheet = None
_worksheets: dict[str, object] = {}

_TAB_NAMES = {"Kirim": "Kirim", "Chiqim": "Chiqim"}


def _get_spreadsheet():
    global _client, _spreadsheet
    if _spreadsheet is not None:
        return _spreadsheet

    if config.GOOGLE_CREDENTIALS_JSON:
        creds_info = json.loads(config.GOOGLE_CREDENTIALS_JSON)
        creds = Credentials.from_service_account_info(creds_info, scopes=_SCOPES)
    else:
        creds = Credentials.from_service_account_file(
            config.GOOGLE_CREDENTIALS_FILE, scopes=_SCOPES
        )
    _client = gspread.authorize(creds)
    _spreadsheet = _client.open_by_key(config.SPREADSHEET_ID)
    return _spreadsheet


def get_worksheet(turi: str):
    """Kirim yoki Chiqim uchun alohida varaqni qaytaradi, mavjud bo'lmasa yaratadi."""
    tab_name = _TAB_NAMES.get(turi, "Chiqim")
    if tab_name in _worksheets:
        return _worksheets[tab_name]

    spreadsheet = _get_spreadsheet()
    try:
        worksheet = spreadsheet.worksheet(tab_name)
    except gspread.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(
            title=tab_name, rows=1000, cols=len(config.SHEET_HEADERS)
        )

    first_row = worksheet.row_values(1)
    if first_row != config.SHEET_HEADERS:
        worksheet.update("A1", [config.SHEET_HEADERS])

    _worksheets[tab_name] = worksheet
    return worksheet


def _get_legacy_worksheet():
    """Kirim/Chiqimga ajratilishidan oldingi umumiy "Tranzaksiyalar" varag'i, mavjud bo'lsa."""
    spreadsheet = _get_spreadsheet()
    try:
        return spreadsheet.worksheet(config.WORKSHEET_NAME)
    except gspread.WorksheetNotFound:
        return None


def append_transaction(
    sana: str,
    turi: str,
    summa: float,
    valyuta: str,
    kategoriya: str,
    tavsif: str,
    foydalanuvchi: str,
) -> int | None:
    worksheet = get_worksheet(turi)
    response = worksheet.append_row(
        [sana, turi, summa, valyuta, kategoriya, tavsif, foydalanuvchi],
        value_input_option="USER_ENTERED",
    )

    updated_range = response.get("updates", {}).get("updatedRange", "")
    match = re.search(r"![A-Z]+(\d+)", updated_range)
    return int(match.group(1)) if match else None


def delete_transaction(turi: str, row_number: int) -> None:
    worksheet = get_worksheet(turi)
    worksheet.delete_rows(row_number)


def _normalize_value(value):
    if isinstance(value, (int, float)):
        return round(float(value), 6)
    return str(value).strip()


def dedupe_all_sheets() -> dict[str, int]:
    """"Tranzaksiyalar" (eski), "Kirim" va "Chiqim" varaqlarini BIRGALIKDA
    tekshiradi va aynan bir xil (barcha ustunlari mos) takroriy qatorlarni
    o'chiradi — har bir noyob qatorning faqat birinchi uchragan nusxasini
    qoldiradi. Bu nafaqat bitta varaq ICHIDAGI, balki varaqlar ORASIDAGI
    takrorlarni ham topadi (masalan "Chiqim" varag'i "Tranzaksiyalar"
    varag'idagi eski yozuvlarning nusxasi bo'lib qolgan holatlar uchun).
    Har bir varaq uchun nechta qator o'chirilganini lug'at qilib qaytaradi."""
    sheets: list[tuple[str, object]] = []
    legacy = _get_legacy_worksheet()
    if legacy is not None:
        sheets.append((config.WORKSHEET_NAME, legacy))
    sheets.append(("Kirim", get_worksheet("Kirim")))
    sheets.append(("Chiqim", get_worksheet("Chiqim")))

    seen: set[tuple] = set()
    results: dict[str, int] = {}

    for name, worksheet in sheets:
        records = worksheet.get_all_records()
        rows_to_delete: list[int] = []
        for idx, record in enumerate(records, start=2):
            key = tuple(_normalize_value(v) for v in record.values())
            if key in seen:
                rows_to_delete.append(idx)
            else:
                seen.add(key)

        for row_num in sorted(rows_to_delete, reverse=True):
            worksheet.delete_rows(row_num)

        results[name] = len(rows_to_delete)

    return results


def get_all_transactions(username: str | None = None) -> list[dict]:
    records: list[dict] = []

    legacy = _get_legacy_worksheet()
    if legacy is not None:
        records.extend(legacy.get_all_records())

    records.extend(get_worksheet("Kirim").get_all_records())
    records.extend(get_worksheet("Chiqim").get_all_records())

    if username:
        records = [r for r in records if r.get("Foydalanuvchi") == username]
    return records

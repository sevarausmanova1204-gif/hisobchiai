import re

import gspread
from google.oauth2.service_account import Credentials

import config

_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

_worksheet = None


def get_worksheet():
    global _worksheet
    if _worksheet is not None:
        return _worksheet

    creds = Credentials.from_service_account_file(
        config.GOOGLE_CREDENTIALS_FILE, scopes=_SCOPES
    )
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(config.SPREADSHEET_ID)

    try:
        worksheet = spreadsheet.worksheet(config.WORKSHEET_NAME)
    except gspread.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(
            title=config.WORKSHEET_NAME, rows=1000, cols=len(config.SHEET_HEADERS)
        )

    first_row = worksheet.row_values(1)
    if first_row != config.SHEET_HEADERS:
        worksheet.update("A1", [config.SHEET_HEADERS])

    _worksheet = worksheet
    return _worksheet


def append_transaction(
    sana: str,
    turi: str,
    summa: float,
    valyuta: str,
    kategoriya: str,
    tavsif: str,
    foydalanuvchi: str,
) -> int | None:
    worksheet = get_worksheet()
    response = worksheet.append_row(
        [sana, turi, summa, valyuta, kategoriya, tavsif, foydalanuvchi],
        value_input_option="USER_ENTERED",
    )

    updated_range = response.get("updates", {}).get("updatedRange", "")
    match = re.search(r"![A-Z]+(\d+)", updated_range)
    return int(match.group(1)) if match else None


def delete_transaction(row_number: int) -> None:
    worksheet = get_worksheet()
    worksheet.delete_rows(row_number)


def get_all_transactions(username: str | None = None) -> list[dict]:
    worksheet = get_worksheet()
    records = worksheet.get_all_records()
    if username:
        records = [r for r in records if r.get("Foydalanuvchi") == username]
    return records

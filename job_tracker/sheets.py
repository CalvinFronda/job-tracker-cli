from datetime import date
from google.oauth2.credentials import Credentials
from .storage import _load_token, _token_valid, _refresh
from .shared import _TOKEN_URI, _CLIENT_ID, SCOPES
import gspread


# ---------------------------------------------------------------------------
# Sheet operations
# ---------------------------------------------------------------------------


def append_job(
    spreadsheet_id: str,
    company: str,
    title: str,
    url: str,
    notes: str = "",
    sheet_name: str = "",
    columns: str = "date,company,title,url,status,notes",
    date_format: str = "%Y-%m-%d",
) -> tuple[str, int]:
    """
    Append a job application row to the sheet.
    Returns (sheet_tab_name, row_number).
    """
    client = _get_client()
    spreadsheet = client.open_by_key(spreadsheet_id)
    worksheet = _resolve_worksheet(spreadsheet, sheet_name)

    all_fields = {
        "date": date.today().strftime(date_format),
        "company": company,
        "title": title,
        "url": url,
        "status": "Applied",
        "notes": notes,
    }
    col_list = [c.strip() for c in columns.split(",") if c.strip()]
    row = [all_fields.get(col, "") for col in col_list]

    end_col = chr(ord("A") + len(row) - 1)
    spreadsheet.values_append(
        f"{worksheet.title}!A:{end_col}",
        params={"valueInputOption": "USER_ENTERED", "insertDataOption": "INSERT_ROWS"},
        body={"values": [row]},
    )

    row_number = len(worksheet.get_all_values())
    return worksheet.title, row_number


def _resolve_worksheet(
    spreadsheet: gspread.Spreadsheet, sheet_name: str
) -> gspread.Worksheet:
    worksheets = spreadsheet.worksheets()
    if not worksheets:
        raise RuntimeError("Spreadsheet has no sheets.")

    if sheet_name:
        matches = [ws for ws in worksheets if ws.title == sheet_name]
        if not matches:
            available = ", ".join(f'"{ws.title}"' for ws in worksheets)
            raise ValueError(
                f'Sheet tab "{sheet_name}" not found.\n'
                f"Available tabs: {available}\n"
                "Update with: `job config set sheet_name <tab name>`"
            )
        return matches[0]

    return worksheets[-1]


def _get_client() -> gspread.Client:
    from .auth import get_credentials  # lazy import to avoid circular deps

    token = _load_token()

    if token and not _token_valid(token):
        token = _refresh(token)

    if not token or not _token_valid(token):
        get_credentials()
        token = _load_token()

    # Build a Credentials object for gspread using the valid access token.
    # expiry=None prevents gspread from trying its own refresh logic.
    creds = Credentials(
        token=token["access_token"],
        refresh_token=token.get("refresh_token"),
        token_uri=_TOKEN_URI,
        client_id=_CLIENT_ID,
        client_secret="",
        scopes=SCOPES,
    )
    return gspread.authorize(creds)

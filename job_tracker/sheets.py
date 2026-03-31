import json
import os
from dotenv import load_dotenv


from datetime import date
from pathlib import Path
from typing import Optional

import gspread
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

load_dotenv()

# Where the OAuth token is cached after first login
TOKEN_FILE = Path.home() / ".config" / "job-tracker" / "token.json"


_OAUTH_CLIENT_ID = os.getenv("_OAUTH_CLIENT_ID")
_OAUTH_CLIENT_SECRET = os.getenv("_OAUTH_CLIENT_SECRET")

_CLIENT_CONFIG = {
    "installed": {
        "client_id": _OAUTH_CLIENT_ID,
        "client_secret": _OAUTH_CLIENT_SECRET,
        "redirect_uris": ["http://localhost"],
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
    }
}


def authenticate() -> None:
    """
    Run the OAuth browser flow and cache the token locally.
    Safe to call repeatedly — if already authenticated it just confirms.
    """
    if (
        _OAUTH_CLIENT_ID == "YOUR_CLIENT_ID_HERE"
        or _OAUTH_CLIENT_SECRET == "YOUR_CLIENT_SECRET_HERE"
    ):
        raise RuntimeError(
            "OAuth credentials are not configured.\n"
            "Fill in _CLIENT_ID and _CLIENT_SECRET in job_tracker/sheets.py\n"
            "with your Google Cloud Console OAuth 2.0 Desktop app credentials."
        )

    creds = _load_or_refresh_token()
    if creds and creds.valid:
        print(f"✅ Already authenticated. Token cached at {TOKEN_FILE}")
        return

    flow = InstalledAppFlow.from_client_config(_CLIENT_CONFIG, SCOPES)
    creds = flow.run_local_server(port=0, prompt="consent")
    _save_token(creds)
    print(f"✅ Authenticated successfully. Token saved to {TOKEN_FILE}")


def _get_client() -> gspread.Client:
    """Return an authenticated gspread client, refreshing the token if needed."""
    creds = _load_or_refresh_token()

    if not creds or not creds.valid:
        raise RuntimeError(
            "Not authenticated or token expired.\n"
            "Run `job auth` to authenticate with Google."
        )

    return gspread.authorize(creds)


def _load_or_refresh_token() -> Optional[Credentials]:
    """Load cached token and refresh it if expired."""
    if not TOKEN_FILE.exists():
        return None

    with open(TOKEN_FILE) as f:
        token_data = json.load(f)

    creds = Credentials.from_authorized_user_info(token_data, SCOPES)

    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            _save_token(creds)
        except Exception:
            return None

    return creds


def _save_token(creds: Credentials) -> None:
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(TOKEN_FILE, "w") as f:
        f.write(creds.to_json())


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

    all_values = worksheet.get_all_values()
    row_number = len(all_values)

    return worksheet.title, row_number


def _resolve_worksheet(
    spreadsheet: gspread.Spreadsheet, sheet_name: str
) -> gspread.Worksheet:
    """Return the configured sheet tab, or the last tab if none is configured."""
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

import os
from datetime import date
from pathlib import Path
from typing import Optional

import gspread
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import json

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# Where gspread stores the cached OAuth token
TOKEN_FILE = Path.home() / ".config" / "job-tracker" / "token.json"


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def authenticate(credentials_file: str) -> None:
    """
    Run the OAuth browser flow and cache the token locally.
    Safe to call repeatedly — if already authenticated it just confirms.
    """
    creds_path = Path(credentials_file)
    if not creds_path.exists():
        raise FileNotFoundError(
            f"Credentials file not found at {credentials_file}\n\n"
            "To get credentials:\n"
            "  1. Go to https://console.cloud.google.com/\n"
            "  2. Create a project → Enable the Google Sheets API\n"
            "  3. Go to APIs & Services → Credentials\n"
            "  4. Create OAuth 2.0 credentials (Desktop app)\n"
            f"  5. Download the JSON and save it to: {credentials_file}"
        )

    creds = _load_or_refresh_token(credentials_file)
    if creds and creds.valid:
        print(f"✅ Already authenticated. Token cached at {TOKEN_FILE}")
        return

    # Run the browser flow
    flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
    creds = flow.run_local_server(port=0, prompt="consent")
    _save_token(creds)
    print(f"✅ Authenticated successfully. Token saved to {TOKEN_FILE}")


def _get_client(credentials_file: str) -> gspread.Client:
    """Return an authenticated gspread client, refreshing the token if needed."""
    creds = _load_or_refresh_token(credentials_file)

    if not creds or not creds.valid:
        raise RuntimeError(
            "Not authenticated or token expired.\n"
            "Run `job auth` to authenticate with Google."
        )

    return gspread.authorize(creds)


def _load_or_refresh_token(credentials_file: str) -> Optional[Credentials]:
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
    credentials_file: str,
    company: str,
    title: str,
    url: str,
    notes: str = "",
    sheet_name: str = "",
) -> tuple[str, int]:
    """
    Append a job application row to the sheet.
    Returns (sheet_tab_name, row_number).
    """
    client = _get_client(credentials_file)
    spreadsheet = client.open_by_key(spreadsheet_id)

    # Resolve which tab to write to
    worksheet = _resolve_worksheet(spreadsheet, sheet_name)

    row = [
        date.today().isoformat(),  # Date
        company,                   # Company
        title,                     # Title
        url,                       # URL
        "Applied",                 # Status
        notes,                     # Notes
    ]

    spreadsheet.values_append(
        f"{worksheet.title}!A:F",
        params={"valueInputOption": "USER_ENTERED", "insertDataOption": "INSERT_ROWS"},
        body={"values": [row]},
    )

    # Calculate the row number we just wrote to
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
        # Find the named tab
        matches = [ws for ws in worksheets if ws.title == sheet_name]
        if not matches:
            available = ", ".join(f'"{ws.title}"' for ws in worksheets)
            raise ValueError(
                f"Sheet tab \"{sheet_name}\" not found.\n"
                f"Available tabs: {available}\n"
                "Update with: `job config set sheet_name <tab name>`"
            )
        return matches[0]

    # Default: use the last tab (most recently created)
    return worksheets[-1]

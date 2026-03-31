import json

import time
from typing import Optional
import requests as http

from .shared import TOKEN_FILE, _TOKEN_URI, _CLIENT_ID

# ---------------------------------------------------------------------------
# Token storage / refresh
# ---------------------------------------------------------------------------


def _load_token() -> Optional[dict]:
    if not TOKEN_FILE.exists():
        return None
    try:
        with open(TOKEN_FILE) as f:
            return json.load(f)
    except (json.JSONDecodeError, ValueError):
        TOKEN_FILE.unlink(missing_ok=True)
        return None


def _token_valid(token: dict) -> bool:
    if not token.get("access_token"):
        return False
    expires_at = token.get("expires_at", 0)
    return expires_at > time.time() + 60  # treat as expired 60s early


def _refresh(token: dict) -> Optional[dict]:
    refresh_token = token.get("refresh_token")
    if not refresh_token:
        return None

    resp = http.post(
        _TOKEN_URI,
        data={
            "client_id": _CLIENT_ID,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
    )
    if not resp.ok:
        return None

    data = resp.json()
    if "error" in data:
        return None

    # Google doesn't always return a new refresh_token — preserve the old one
    data.setdefault("refresh_token", refresh_token)
    _save_token(data)
    return data


def _save_token(token_data: dict) -> None:
    if "expires_in" in token_data:
        token_data.setdefault("expires_at", time.time() + token_data["expires_in"])
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(TOKEN_FILE, "w") as f:
        json.dump(token_data, f, indent=2)

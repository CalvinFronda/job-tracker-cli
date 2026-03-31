from pathlib import Path

from platformdirs import user_config_dir


TOKEN_DIR = Path(user_config_dir("job-tracker"))
TOKEN_FILE = TOKEN_DIR / "token.json"


_TOKEN_URI = "https://oauth2.googleapis.com/token"

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

_CLIENT_ID = ""
_CLIENT_SECRET = ""

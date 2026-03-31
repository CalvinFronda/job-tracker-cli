from pathlib import Path

from platformdirs import user_config_dir


TOKEN_DIR = Path(user_config_dir("job-tracker"))
TOKEN_FILE = TOKEN_DIR / "token.json"


_TOKEN_URI = "https://oauth2.googleapis.com/token"

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

_CLIENT_ID = "678105632663-c0iavlk26d30o6cuhvj4fdor7mvfrgma.apps.googleusercontent.com"
_CLIENT_SECRET = ""

import json
import os
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "job-tracker"
CONFIG_FILE = CONFIG_DIR / "config.json"

VALID_KEYS = {"spreadsheet_id", "sheet_name", "credentials_file"}

DEFAULTS = {
    "spreadsheet_id": "",
    "sheet_name": "",           # blank = use last tab
    "credentials_file": str(CONFIG_DIR / "credentials.json"),
}


def config_dir() -> Path:
    return CONFIG_DIR


def load() -> dict:
    """Load config from disk. Raises if missing or spreadsheet_id not set."""
    if not CONFIG_FILE.exists():
        raise FileNotFoundError(
            f"No config found at {CONFIG_FILE}\n"
            "Run `job config init` to get started."
        )
    with open(CONFIG_FILE) as f:
        cfg = {**DEFAULTS, **json.load(f)}

    if not cfg.get("spreadsheet_id"):
        raise ValueError(
            "spreadsheet_id is not set.\n"
            "Run `job config set spreadsheet_id <your-sheet-id>`"
        )
    return cfg


def save(cfg: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)


def show() -> None:
    if not CONFIG_FILE.exists():
        print("No config found. Run `job config init` to set up.")
        return
    with open(CONFIG_FILE) as f:
        cfg = {**DEFAULTS, **json.load(f)}

    sheet_name = cfg.get("sheet_name") or "(last tab)"
    print(f"Config file:      {CONFIG_FILE}")
    print(f"spreadsheet_id:   {cfg.get('spreadsheet_id') or '(not set)'}")
    print(f"sheet_name:       {sheet_name}")
    print(f"credentials_file: {cfg.get('credentials_file')}")


def init_wizard() -> None:
    """Interactive setup wizard."""
    print("🛠  job-tracker setup\n")

    print("1. Open your Google Sheet and copy the ID from the URL:")
    print("   https://docs.google.com/spreadsheets/d/<SPREADSHEET_ID>/edit")
    spreadsheet_id = input("   Spreadsheet ID: ").strip()

    print("\n2. Sheet tab to write to (leave blank to always use the last tab):")
    sheet_name = input("   Sheet name: ").strip()

    default_creds = DEFAULTS["credentials_file"]
    print(f"\n3. Path to your Google OAuth credentials JSON")
    print(f"   (press enter to use default: {default_creds})")
    credentials_file = input("   Credentials file: ").strip() or default_creds

    cfg = {
        "spreadsheet_id": spreadsheet_id,
        "sheet_name": sheet_name,
        "credentials_file": credentials_file,
    }
    save(cfg)

    print(f"\n✅ Config saved to {CONFIG_FILE}")
    print("\nNext steps:")
    print("  1. Download OAuth credentials from Google Cloud Console")
    print(f"     and save to: {credentials_file}")
    print("  2. Run `job auth` to authenticate with Google")
    print("  3. Run `job <url>` to log your first application!")


def set_value(key: str, value: str) -> None:
    if key not in VALID_KEYS:
        raise ValueError(
            f"Unknown key '{key}'. Valid keys: {', '.join(sorted(VALID_KEYS))}"
        )
    cfg = {}
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            cfg = json.load(f)
    cfg[key] = value
    save(cfg)
    print(f"✅ Set {key} = {value}")

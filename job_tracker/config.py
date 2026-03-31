import json
from datetime import date
from pathlib import Path
from platformdirs import user_config_dir


CONFIG_DIR = Path(user_config_dir("job-tracker"))
CONFIG_FILE = CONFIG_DIR / "config.json"

KNOWN_FIELDS = {"date", "company", "title", "url", "status", "notes"}

VALID_KEYS = {"spreadsheet_id", "sheet_name", "columns", "date_format"}

DEFAULTS = {
    "spreadsheet_id": "",
    "sheet_name": "",  # blank = use last tab
    "columns": "date,company,title,url,status,notes",
    "date_format": "%Y-%m-%d",  # e.g. 2026-03-30
}


def load() -> dict:
    """Load config from disk. Raises if missing or spreadsheet_id not set."""
    from .cli import run_setup

    if not CONFIG_FILE.exists():
        run_setup()

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

    columns = [c.strip() for c in cfg.get("columns", DEFAULTS["columns"]).split(",")]
    date_fmt = cfg.get("date_format", DEFAULTS["date_format"])
    formatted_date = date.today().strftime(date_fmt)
    sheet_name = cfg.get("sheet_name") or "(last tab)"

    print(f"Config file:     {CONFIG_FILE}")
    print(f"spreadsheet_id:  {cfg.get('spreadsheet_id') or '(not set)'}")
    print(f"sheet_name:      {sheet_name}")
    print()
    print(f"Row format ({len(columns)} columns):")
    print(f"  {', '.join(columns)}")
    sample = {
        "date": formatted_date,
        "company": "Stripe",
        "title": "Software Engineer",
        "url": "https://jobs.stripe.com/...",
        "status": "Applied",
        "notes": "",
    }
    print(f"  → {' | '.join(sample[c] for c in columns if c in sample)}")
    print()
    print(f"date_format:     {date_fmt}  →  {formatted_date}")
    print()
    print("To customize:")
    print('  job config set columns "date,company,title,url"')
    print('  job config set date_format "%m/%d/%Y"')
    print(f"Available fields: {', '.join(sorted(KNOWN_FIELDS))}")


def init_wizard() -> None:
    """Interactive setup wizard."""
    print("🛠  job-tracker setup\n")

    print("1. Open your Google Sheet and copy the ID from the URL:")
    print("   https://docs.google.com/spreadsheets/d/<SPREADSHEET_ID>/edit")
    spreadsheet_id = input("   Spreadsheet ID: ").strip()

    print("\n2. Sheet tab to write to (leave blank to always use the last tab):")
    sheet_name = input("   Sheet name: ").strip()

    cfg = {
        "spreadsheet_id": spreadsheet_id,
        "sheet_name": sheet_name,
    }
    save(cfg)

    print(f"\n✅ Config saved to {CONFIG_FILE}")
    print("\nDefault row format: date, company, title, url, status, notes")
    print('Customize anytime with: job config set columns "date,company,title,url"')
    print("\nNext step: run `job auth` to connect your Google account.")


def set_value(key: str, value: str) -> None:
    if key not in VALID_KEYS:
        raise ValueError(
            f"Unknown key '{key}'. Valid keys: {', '.join(sorted(VALID_KEYS))}"
        )

    if key == "columns":
        fields = [c.strip() for c in value.split(",") if c.strip()]
        if not fields:
            raise ValueError("columns cannot be empty.")
        unknown = set(fields) - KNOWN_FIELDS
        if unknown:
            raise ValueError(
                f"Unknown field(s): {', '.join(sorted(unknown))}\n"
                f"Available fields: {', '.join(sorted(KNOWN_FIELDS))}"
            )
        value = ",".join(fields)

    if key == "date_format":
        try:
            preview = date.today().strftime(value)
        except Exception as e:
            raise ValueError(f"Invalid date format '{value}': {e}") from e
        print(f"  Preview: {preview}")

    cfg = {}
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            cfg = json.load(f)
    cfg[key] = value
    save(cfg)
    print(f"✅ Set {key} = {value}")

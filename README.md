# job-tracker

A minimal CLI to log job applications to Google Sheets with a single command.

```bash
$ job https://job-boards.greenhouse.io/postman/jobs/7359054003
🔍 Detecting job details from URL...
📋 Adding: Postman — Senior Software Engineer
✅ Added to sheet "2025" at row 14
```

---

## Installation

### Prerequisites
- Python 3.9+
- [pipx](https://pipx.pypa.io/stable/installation/)

### Install from GitHub

```bash
pipx install git+https://github.com/CalvinFronda/job-tracker-cli
```

### Install from source

```bash
git clone https://github.com/CalvinFronda/job-tracker-cli
cd job-tracker
pipx install .
```

---

## Google Sheets setup

### 1. Create a Google Cloud project

1. Go to [console.cloud.google.com](https://console.cloud.google.com/)
2. Create a new project (e.g. "job-tracker")
3. Navigate to **APIs & Services → Library**
4. Search for **Google Sheets API** → Enable it

### 2. Create OAuth 2.0 credentials

1. Go to **APIs & Services → Credentials**
2. Click **Create Credentials → OAuth client ID**
3. Application type: **Desktop app**
4. Click **Create**, then **Download JSON**
5. Save the file somewhere safe (e.g. `~/.config/job-tracker/credentials.json`)

### 3. Configure job-tracker

```bash
job config init
```

You'll be prompted for:
- Your **Spreadsheet ID** — from your sheet URL: `docs.google.com/spreadsheets/d/<ID>/edit`
- Which **sheet tab** to write to (leave blank to always use the last tab)
- Path to your **credentials JSON** from step 2

### 4. Authenticate

```bash
job auth
```

This opens a browser window. Sign in with Google, grant access, and you're done.
The token is cached locally — you only need to do this once.

---

## Usage

```bash
# Auto-detect company and title from the URL
job https://job-boards.greenhouse.io/postman/jobs/7359054003

# Override fields manually
job https://lever.co/stripe/abc-123 --company Stripe --title "Software Engineer II"

# Add a note
job https://example.com/jobs/123 --notes "Referral from Jane"
```

### Supported ATS platforms (company auto-detected from URL)

- Greenhouse
- Lever
- Ashby
- Workday
- Workable
- SmartRecruiters
- Any `jobs.<company>.com` or `careers.<company>.com` subdomain

For other URLs the tool fetches the page and extracts the company name from
meta tags and the page title. If it can't determine a field, it will prompt you.

---

## Sheet format

The tool appends a row with these columns:

| Date       | Company | Title                    | URL                       | Status  | Notes |
|------------|---------|--------------------------|---------------------------|---------|-------|
| 2025-05-01 | Postman | Senior Software Engineer | https://greenhouse.io/... | Applied |       |

You can add columns to the right freely — the tool only writes to A–F.

---

## Configuration reference

Config is stored at `~/.config/job-tracker/config.json`.

```bash
job config show                              # view current settings
job config set spreadsheet_id <id>           # update sheet ID
job config set sheet_name "June 2025"        # pin to a specific tab
job config set credentials_file ~/creds.json # update credentials path
```

---

## Contributing

PRs welcome. Some ideas for future features:

- `job list` — print recent applications from the sheet
- `job status <company> <status>` — update the status column for an entry
- Duplicate detection before appending
- Support for more ATS platforms in the URL scraper

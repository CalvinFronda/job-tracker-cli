# job-tracker

A minimal CLI to log job applications to Google Sheets with a single command.

```bash
$ job https://job-boards.greenhouse.io/postman/jobs/7359054003
🔍 Detecting job details from URL...
📋 Adding: Postman — Senior Software Engineer
✅ Added to sheet "2026" at row 14
```

---

## Installation

**Prerequisites:** Python 3.9+, [pipx](https://pipx.pypa.io/stable/installation/)

```bash
pipx install git+https://github.com/CalvinFronda/job-tracker-cli
```

---

## Setup

```bash
job config init   # enter your Google Sheet ID
job auth          # one-time browser sign-in with Google
```

That's it. After `job auth` completes, your token is cached locally and you never need to sign in again.

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

### Supported job boards (company + title auto-detected)

- Greenhouse, Lever, Ashby
- Workday, Workable, SmartRecruiters
- Any `jobs.<company>.com` or `careers.<company>.com` subdomain
- Fallback: fetches the page and parses meta tags + title

If a field can't be detected, the CLI will prompt you for it.

---

## Sheet format

Each `job <url>` appends one row. Default columns:

| Date       | Company | Title                    | URL                       | Status  | Notes |
|------------|---------|--------------------------|---------------------------|---------|-------|
| 2026-03-30 | Postman | Senior Software Engineer | https://greenhouse.io/... | Applied |       |

---

## Configuration

Config is stored at `~/.config/job-tracker/config.json`.

```bash
job config show                        # view current settings + a sample row
job config set spreadsheet_id <id>     # update sheet ID
job config set sheet_name "June 2026"  # pin to a specific tab (blank = last tab)
```

### Customize columns

Choose which fields appear and in what order:

```bash
job config set columns "date,company,title,url,status,notes"  # default
job config set columns "date,company,title,url"               # drop status + notes
job config set columns "company,title,date,notes"             # reorder
```

Available fields: `date`, `company`, `title`, `url`, `status`, `notes`

### Customize date format

```bash
job config set date_format "%Y-%m-%d"   # 2026-03-30  (default)
job config set date_format "%m/%d/%Y"   # 03/30/2026
job config set date_format "%B %d, %Y"  # March 30, 2026
```

`job config show` always prints a live preview so you can see exactly what the next row will look like.

---

## Ideas


- `job list` — print recent applications from the sheet
- `job status <company> <status>` — update the status column for an entry
- Duplicate detection before appending
- Support for more ATS platforms

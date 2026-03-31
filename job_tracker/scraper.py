import re
import requests
from typing import Optional

# Noise words to strip from the end of extracted company names
_COMPANY_SUFFIXES = re.compile(
    r"\s*[-|,]\s*(careers|jobs|hiring|talent|work with us|job board).*$",
    re.IGNORECASE,
)

# ATS platform names to strip from page titles
_ATS_NOISE = re.compile(
    r"\s*[\|–\-]\s*(lever|greenhouse|ashby|workday|workable|smartrecruiters"
    r"|icims|taleo|jobvite|breezy|recruitee|jazz ?hr|apply).*$",
    re.IGNORECASE,
)

# Legal suffixes that obscure the real brand name
_LEGAL_SUFFIXES = re.compile(
    r"\s*,?\s*(inc\.?|llc\.?|ltd\.?|corp\.?|co\.?|hq|group|technologies|tech)$",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class JobDetails:
    def __init__(self, company: str = "", title: str = ""):
        self.company = company
        self.title = title


def fetch(url: str) -> JobDetails:
    """
    Best-effort extraction of company name and job title from a job posting URL.
    Never raises — returns empty strings for fields it cannot determine.
    """
    details = JobDetails()

    # Stage 1: ATS URL slug (no network needed)
    details.company = _company_from_url(url)

    # If we already have a company name, try to get the title from the page
    # but don't make a network call just for the company name if we have it.
    if details.company and details.title:
        return details

    # Stage 2: Fetch the page for anything still missing
    body = _fetch_page(url)
    if not body:
        return details

    if not details.company:
        details.company = _company_from_og(body) or _company_from_title(body, url)

    if not details.title:
        details.title = _title_from_page(body)

    return details


# ---------------------------------------------------------------------------
# Stage 1: URL pattern matching
# ---------------------------------------------------------------------------

_ATS_PATTERNS = [
    # Greenhouse: job-boards.greenhouse.io/SLUG/jobs/ID
    #         or: boards.greenhouse.io/SLUG/jobs/ID
    re.compile(r"greenhouse\.io/([^/?#]+)/jobs/", re.IGNORECASE),
    # Lever: jobs.lever.co/SLUG/UUID
    re.compile(r"lever\.co/([^/?#]+)/", re.IGNORECASE),
    # Ashby: jobs.ashbyhq.com/SLUG/UUID
    re.compile(r"ashbyhq\.com/([^/?#]+)/", re.IGNORECASE),
    # Workday: SLUG.wd1.myworkdayjobs.com (or wd2, wd3, wd5...)
    re.compile(r"([^.]+)\.wd\d+\.myworkdayjobs\.com", re.IGNORECASE),
    # Workable: apply.workable.com/SLUG/
    re.compile(r"workable\.com/([^/?#]+)/", re.IGNORECASE),
    # SmartRecruiters: careers.smartrecruiters.com/SLUG/
    re.compile(r"smartrecruiters\.com/([^/?#]+)/", re.IGNORECASE),
    # Generic jobs subdomain: jobs.stripe.com, careers.notion.so
    re.compile(r"(?:jobs|careers)\.([^.]+)\.", re.IGNORECASE),
]


def _company_from_url(url: str) -> str:
    for pattern in _ATS_PATTERNS:
        m = pattern.search(url)
        if m:
            slug = m.group(1)
            return _slug_to_name(slug)
    return ""


def _slug_to_name(slug: str) -> str:
    """Convert a URL slug like 'my-company-inc' to 'My Company'."""
    # Replace separators with spaces
    name = slug.replace("-", " ").replace("_", " ").strip()
    # Strip legal suffixes (inc, llc, corp, etc.)
    name = _LEGAL_SUFFIXES.sub("", name).strip()
    # Title-case each word
    name = " ".join(w.capitalize() for w in name.split())
    return name


# ---------------------------------------------------------------------------
# Stage 2a: og:site_name meta tag
# ---------------------------------------------------------------------------

_OG_SITE_NAME = re.compile(
    r'<meta[^>]+property=["\']og:site_name["\'][^>]+content=["\'](.*?)["\']',
    re.IGNORECASE,
)
# Also handle content= before property=
_OG_SITE_NAME_ALT = re.compile(
    r'<meta[^>]+content=["\'](.*?)["\'][^>]+property=["\']og:site_name["\']',
    re.IGNORECASE,
)


def _company_from_og(body: str) -> str:
    for pattern in (_OG_SITE_NAME, _OG_SITE_NAME_ALT):
        m = pattern.search(body)
        if m:
            name = m.group(1).strip()
            name = _COMPANY_SUFFIXES.sub("", name).strip()
            name = _LEGAL_SUFFIXES.sub("", name).strip()
            if name:
                return name
    return ""


# ---------------------------------------------------------------------------
# Stage 2b: <title> tag parsing
# ---------------------------------------------------------------------------

_TITLE_TAG = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)


def _company_from_title(body: str, url: str) -> str:
    """
    Extract company name from a page <title> tag.
    Titles often look like:
      "Senior Engineer at Stripe | Lever"
      "Stripe - Senior Software Engineer"
      "Software Engineer | Careers at Notion"
    """
    m = _TITLE_TAG.search(body)
    if not m:
        return ""

    title = _decode_html_entities(m.group(1).strip())

    # Strip ATS platform noise from the end first
    title = _ATS_NOISE.sub("", title).strip()

    # Pattern: "Role at Company" or "Role @ Company"
    at_match = re.search(r"\bat\s+(.+)$", title, re.IGNORECASE)
    if at_match:
        candidate = at_match.group(1).strip()
        candidate = _COMPANY_SUFFIXES.sub("", candidate).strip()
        candidate = _LEGAL_SUFFIXES.sub("", candidate).strip()
        if candidate and len(candidate) < 60:
            return candidate

    # Pattern: "Company - Role" or "Company | Role" — company is first segment
    # Only use this if it looks like a company name (short, no verb-like words)
    parts = re.split(r"\s*[\|\-–]\s*", title)
    if len(parts) >= 2:
        first = parts[0].strip()
        # Heuristic: if the first segment is short and doesn't contain
        # job-title words, it's likely the company name
        job_title_words = re.compile(
            r"\b(engineer|developer|manager|director|analyst|designer|"
            r"lead|senior|junior|staff|principal|intern|contractor)\b",
            re.IGNORECASE,
        )
        if first and len(first) < 50 and not job_title_words.search(first):
            candidate = _COMPANY_SUFFIXES.sub("", first).strip()
            candidate = _LEGAL_SUFFIXES.sub("", candidate).strip()
            if candidate:
                return candidate

    return ""


# ---------------------------------------------------------------------------
# Job title extraction
# ---------------------------------------------------------------------------

def _title_from_page(body: str) -> str:
    """Extract job title from page <title> tag."""
    m = _TITLE_TAG.search(body)
    if not m:
        return ""

    title = _decode_html_entities(m.group(1).strip())

    # Strip ATS noise
    title = _ATS_NOISE.sub("", title).strip()

    # Pattern: "Role at Company" — role is everything before " at "
    at_match = re.search(r"^(.+?)\s+at\s+", title, re.IGNORECASE)
    if at_match:
        candidate = at_match.group(1).strip()
        if candidate and len(candidate) < 100:
            return candidate

    # Take the first pipe/dash segment if it looks like a job title
    parts = re.split(r"\s*[\|\-–]\s*", title)
    if parts:
        candidate = parts[0].strip()
        job_title_words = re.compile(
            r"\b(engineer|developer|manager|director|analyst|designer|"
            r"lead|senior|junior|staff|principal|intern|contractor|scientist|"
            r"architect|consultant|specialist|coordinator|recruiter)\b",
            re.IGNORECASE,
        )
        if candidate and job_title_words.search(candidate) and len(candidate) < 100:
            return candidate

    return ""


# ---------------------------------------------------------------------------
# HTTP helper
# ---------------------------------------------------------------------------

def _fetch_page(url: str) -> Optional[str]:
    try:
        resp = requests.get(
            url,
            timeout=8,
            headers={"User-Agent": "Mozilla/5.0 (compatible; job-tracker/1.0)"},
            # Don't follow too many redirects
            allow_redirects=True,
        )
        # Read only the first 64KB — enough to get <head> content
        # requests doesn't support partial reads directly so we use iter_content
        content = b""
        for chunk in resp.iter_content(chunk_size=4096):
            content += chunk
            if len(content) >= 65536:
                break
        return content.decode("utf-8", errors="replace")
    except Exception:
        return None


def _decode_html_entities(text: str) -> str:
    """Decode common HTML entities in extracted text."""
    replacements = {
        "&amp;": "&",
        "&lt;": "<",
        "&gt;": ">",
        "&quot;": '"',
        "&#39;": "'",
        "&apos;": "'",
        "&#x27;": "'",
        "&#x2F;": "/",
    }
    for entity, char in replacements.items():
        text = text.replace(entity, char)
    return text

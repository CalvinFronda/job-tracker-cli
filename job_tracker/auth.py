import base64
import hashlib
import secrets
import socket
import urllib.parse
import webbrowser
import requests as http

from http.server import BaseHTTPRequestHandler, HTTPServer

from .storage import _load_token, _token_valid, _save_token

from .shared import TOKEN_FILE, _TOKEN_URI, _CLIENT_ID, _CLIENT_SECRET, SCOPES


_AUTH_URI = "https://accounts.google.com/o/oauth2/v2/auth"


# ---------------------------------------------------------------------------
# PKCE helpers
# ---------------------------------------------------------------------------


def _pkce_pair() -> tuple[str, str]:
    """Return (code_verifier, code_challenge) per RFC 7636 S256."""
    verifier = (
        base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=").decode("utf-8")
    )
    digest = hashlib.sha256(verifier.encode("utf-8")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("utf-8")
    return verifier, challenge


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


def get_credentials() -> None:
    """
    Run the PKCE OAuth flow and cache the token locally.
    Safe to call repeatedly — confirms if already authenticated.
    """
    token = _load_token()
    if token and _token_valid(token):
        print(f"✅ Already authenticated. Token cached at {TOKEN_FILE}")
        return

    _run_pkce_flow()
    print(f"✅ Authenticated successfully. Token saved to {TOKEN_FILE}")


def _run_pkce_flow() -> None:
    code_verifier, code_challenge = _pkce_pair()

    # Pick a free localhost port for the redirect
    with socket.socket() as s:
        s.bind(("localhost", 0))
        port = s.getsockname()[1]
    redirect_uri = f"http://127.0.0.1:{port}"

    # Step 1 — build authorization URL (no client_secret)

    auth_url = (
        _AUTH_URI
        + "?"
        + urllib.parse.urlencode(
            {
                "client_id": _CLIENT_ID,
                "redirect_uri": redirect_uri,
                "response_type": "code",
                "scope": " ".join(SCOPES),
                "code_challenge": code_challenge,
                "code_challenge_method": "S256",
                "access_type": "offline",
                "prompt": "consent",
            }
        )
    )

    print("Opening browser for Google sign-in...")
    webbrowser.open(auth_url)

    # Step 2 — catch the redirect on localhost
    auth_code = _wait_for_code(port)

    # Step 3 — exchange code + verifier for tokens (no client_secret)
    resp = http.post(
        _TOKEN_URI,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "client_id": _CLIENT_ID,
            "client_secret": _CLIENT_SECRET,
            "grant_type": "authorization_code",
            "code": auth_code,
            "code_verifier": code_verifier,
            "redirect_uri": redirect_uri,
        },
    )
    token_data = resp.json()
    if not resp.ok or "error" in token_data:
        raise RuntimeError(
            f"Token exchange failed ({resp.status_code}): "
            f"{token_data.get('error_description') or token_data.get('error') or resp.text}"
        )

    _save_token(token_data)


def _wait_for_code(port: int) -> str:
    """Spin up a one-shot localhost server and return the authorization code."""
    received = [None]

    class _Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            received[0] = qs.get("code", [None])[0]
            self.send_response(200)
            self.end_headers()
            self.wfile.write(
                b"<html><body><h2>Authenticated!</h2>"
                b"<p>You can close this tab and return to the terminal.</p>"
                b"</body></html>"
            )

        def log_message(self, *_):
            pass  # silence request logs

    HTTPServer(("localhost", port), _Handler).handle_request()

    if not received[0]:
        raise RuntimeError("Authentication failed — no authorization code received.")
    return received[0]

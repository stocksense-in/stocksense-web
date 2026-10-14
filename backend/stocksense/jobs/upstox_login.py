"""
Upstox login — opens the Upstox sign-in page and stores the access token.

Starts a tiny local server on the redirect URI's port (8000 by default). After
you sign in, Upstox redirects to /callback and the token is saved to
backend/upstox_token.json. Tokens expire daily, so run this each morning.

    python -m stocksense upstox-login            # sign in now
    python -m stocksense upstox-login --status   # show token age
"""

from __future__ import annotations

import html
import threading
import webbrowser
from urllib.parse import urlparse

from flask import Flask, request

from ..config import get_settings
from ..log import get_logger
from ..sources import upstox

log = get_logger(__name__)

_PAGE = """<!doctype html><meta charset="utf-8"><title>StockSense · Upstox</title>
<body style="font:15px system-ui;margin:15vh auto;max-width:28rem;color:#14171F">{body}</body>"""


def status() -> None:
    age = upstox.token_age_hours()
    if age is None:
        print("No saved token. Run: python -m stocksense upstox-login")
    elif age < upstox.TOKEN_MAX_AGE_HOURS:
        print(f"Token is valid — saved {age:.1f} hours ago.")
    else:
        print(f"Token expired — saved {age:.1f} hours ago. Run: python -m stocksense upstox-login")


def run(show_status: bool = False) -> None:
    if show_status:
        status()
        return

    settings = get_settings()
    if not settings.upstox_api_key or not settings.upstox_api_secret:
        raise SystemExit(
            "Set UPSTOX_API_KEY and UPSTOX_API_SECRET in backend/.env "
            "(create an app at https://account.upstox.com/developer/apps)."
        )

    redirect = urlparse(settings.upstox_redirect_uri)
    app = Flask(__name__)
    done = threading.Event()

    @app.get(redirect.path or "/callback")
    def callback():
        code = request.args.get("code")
        if not code:
            return _PAGE.format(body=f"<h2>Sign-in failed</h2><p>{html.escape(request.args.get('error', 'No code returned.'))}</p>"), 400
        token = upstox.exchange_code(code)
        if "access_token" not in token:
            return _PAGE.format(body=f"<h2>Token exchange failed</h2><pre>{html.escape(str(token))}</pre>"), 400
        upstox.save_token(token)
        log.info("Upstox token saved.")
        done.set()
        return _PAGE.format(body="<h2>Signed in to Upstox</h2><p>You can close this tab.</p>")

    server = threading.Thread(
        target=lambda: app.run(host=redirect.hostname or "localhost", port=redirect.port or 8000),
        daemon=True,
    )
    server.start()
    print(f"Opening Upstox sign-in… if the browser doesn't open, visit:\n  {upstox.authorize_url()}")
    webbrowser.open(upstox.authorize_url())
    done.wait()

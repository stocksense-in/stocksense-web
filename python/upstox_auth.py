"""
upstox_auth.py
==============
Upstox token auto-refresh system.

Pehli baar:
    python upstox_auth.py --setup

Daily auto-refresh:
    python upstox_auth.py --refresh
"""

import os
import json
import webbrowser
import requests
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv
from flask import Flask, request, redirect

# ── Load env ──────────────────────────────────────────────
def _load_env():
    search = Path(__file__).resolve().parent
    for _ in range(4):
        for name in (".env.local", ".env"):
            if (search / name).exists():
                load_dotenv(search / name, override=True)
                return
        search = search.parent
    load_dotenv()

_load_env()

# ── Config ────────────────────────────────────────────────
API_KEY      = os.getenv("NEXT_PUBLIC_UPSTOX_API_KEY", "")  
API_SECRET   = os.getenv("NEXT_PUBLIC_UPSTOX_API_SECRET", "")
REDIRECT_URI = "http://localhost:8000/callback"
TOKEN_FILE   = Path(__file__).parent / "upstox_token.json"

# ── Save / Load token ─────────────────────────────────────
def save_token(token_data: dict):
    token_data["saved_at"] = datetime.now(timezone.utc).isoformat()
    TOKEN_FILE.write_text(json.dumps(token_data, indent=2))
    
    # .env mein bhi update karo
    env_path = None
    search = Path(__file__).resolve().parent
    for _ in range(4):
        for name in (".env.local", ".env"):
            candidate = search / name
            if candidate.exists():
                env_path = candidate
                break
        if env_path:
            break
        search = search.parent

    if env_path:
        lines = env_path.read_text().splitlines()
        new_lines = []
        token_updated = False
        for line in lines:
            if line.startswith("NEXT_PUBLIC_UPSTOX_ACCESS_TOKEN="):
                new_lines.append(f"NEXT_PUBLIC_UPSTOX_ACCESS_TOKEN={token_data['access_token']}")
                token_updated = True
            else:
                new_lines.append(line)
        if not token_updated:
            new_lines.append(f"NEXT_PUBLIC_UPSTOX_ACCESS_TOKEN={token_data['access_token']}")
        env_path.write_text("\n".join(new_lines) + "\n")
        print(f"  .env updated: {env_path}")


def load_token() -> dict | None:
    if TOKEN_FILE.exists():
        return json.loads(TOKEN_FILE.read_text())
    return None


def is_token_valid() -> bool:
    token = load_token()
    if not token:
        return False
    # Upstox token same day ka hai check karo
    saved = datetime.fromisoformat(token["saved_at"])
    now   = datetime.now(timezone.utc)
    hours_old = (now - saved).total_seconds() / 3600
    return hours_old < 23  # 23 hours — safe margin


# ── OAuth Flow ────────────────────────────────────────────
def get_auth_url() -> str:
    return (
        f"https://api.upstox.com/v2/login/authorization/dialog"
        f"?response_type=code"
        f"&client_id={API_KEY}"
        f"&redirect_uri={REDIRECT_URI}"
    )


def exchange_code_for_token(auth_code: str) -> dict:
    resp = requests.post(
        "https://api.upstox.com/v2/login/authorization/token",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "code":          auth_code,
            "client_id":     API_KEY,
            "client_secret": API_SECRET,
            "redirect_uri":  REDIRECT_URI,
            "grant_type":    "authorization_code",
        },
        timeout=10,
    )
    return resp.json()


# ── Flask callback server ─────────────────────────────────
app = Flask(__name__)

@app.route("/")
def index():
    auth_url = get_auth_url()
    return f"""
    <html>
    <body style="font-family:sans-serif; padding:40px; background:#080C14; color:#EEF2FF;">
        <h2 style="color:#00D4FF;">StockSense — Upstox Login</h2>
        <p>Neeche button click karo Upstox se login karne ke liye:</p>
        <a href="{auth_url}" style="
            background:#00D4FF; color:#000; padding:12px 24px;
            border-radius:8px; text-decoration:none; font-weight:700;
        ">
            Login with Upstox ↗
        </a>
    </body>
    </html>
    """

@app.route("/callback")
def callback():
    code  = request.args.get("code")
    error = request.args.get("error")

    if error or not code:
        return f"<h2 style='color:red'>Error: {error}</h2>"

    print(f"\nAuth code mila — token exchange ho raha hai...")
    token_data = exchange_code_for_token(code)

    if "access_token" not in token_data:
        return f"<h2 style='color:red'>Token error: {token_data}</h2>"

    save_token(token_data)
    print(f"Token save ho gaya!")

    return """
    <html>
    <body style="font-family:sans-serif; padding:40px; background:#080C14; color:#EEF2FF;">
        <h2 style="color:#00E676;">✓ Token saved successfully!</h2>
        <p>Ab yeh window band karo aur terminal dekho.</p>
        <p style="color:#8B9EC0;">Token automatically .env mein update ho gaya hai.</p>
        <script>setTimeout(() => window.close(), 3000)</script>
    </body>
    </html>
    """


def run_setup():
    """Browser mein login page kholo aur token lo."""
    print("Browser mein Upstox login page khul raha hai...")
    print("URL: http://localhost:8000\n")
    webbrowser.open("http://localhost:8000")
    app.run(port=8000, debug=False)


# ── Daily refresh check ───────────────────────────────────
def auto_refresh():
    """
    Token valid hai toh skip, expired hai toh browser kholo.
    Scheduler se call karo — har subah 8:45 AM.
    """
    if is_token_valid():
        token = load_token()
        saved = datetime.fromisoformat(token["saved_at"])
        hours = (datetime.now(timezone.utc) - saved).total_seconds() / 3600
        print(f"Token valid hai — {hours:.1f} hours purana")
        return True
    else:
        print("Token expired — browser mein login karo...")
        run_setup()
        return False


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--setup",   action="store_true", help="Pehli baar setup")
    parser.add_argument("--refresh", action="store_true", help="Token check/refresh")
    parser.add_argument("--status",  action="store_true", help="Token status dekho")
    args = parser.parse_args()

    if not API_KEY or not API_SECRET:
        print("ERROR: UPSTOX_API_KEY aur UPSTOX_API_SECRET .env mein add karo")
        print("Developer console: https://developer.upstox.com/")
        exit(1)

    if args.setup:
        run_setup()
    elif args.refresh:
        auto_refresh()
    elif args.status:
        token = load_token()
        if token:
            saved = datetime.fromisoformat(token["saved_at"])
            hours = (datetime.now(timezone.utc) - saved).total_seconds() / 3600
            valid = is_token_valid()
            print(f"Token status: {'✓ Valid' if valid else '✗ Expired'}")
            print(f"Saved: {saved.strftime('%Y-%m-%d %H:%M')} UTC")
            print(f"Age: {hours:.1f} hours")
        else:
            print("Token file nahi mili — pehle --setup run karo")
    else:
        parser.print_help()
"""
Upstox API — OAuth token storage, REST quotes, and the market-data WebSocket URL.

Upstox access tokens expire every day at ~3:30 AM IST. Run
`python -m stocksense upstox-login` each morning (the scheduler checks at 8:45).
The token is kept in backend/upstox_token.json, which is gitignored — never commit it.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from urllib.parse import urlencode

import requests

from ..config import BACKEND_DIR, get_settings

API = "https://api.upstox.com"
TOKEN_FILE = BACKEND_DIR / "upstox_token.json"
TOKEN_MAX_AGE_HOURS = 23

# Indices we always track, keyed by the symbol stored in `live_prices`.
INDEX_KEYS = {
    "NIFTY50": "NSE_INDEX|Nifty 50",
    "BANKNIFTY": "NSE_INDEX|Nifty Bank",
    "SENSEX": "BSE_INDEX|SENSEX",
    "INDIAVIX": "NSE_INDEX|India VIX",
}


def equity_key(isin: str) -> str:
    return f"NSE_EQ|{isin}"


# ── Token storage ─────────────────────────────────────────────────────────────


def save_token(token: dict) -> None:
    token["saved_at"] = datetime.now(timezone.utc).isoformat()
    TOKEN_FILE.write_text(json.dumps(token, indent=2))


def load_token() -> dict | None:
    return json.loads(TOKEN_FILE.read_text()) if TOKEN_FILE.exists() else None


def token_age_hours() -> float | None:
    token = load_token()
    if not token or "saved_at" not in token:
        return None
    saved = datetime.fromisoformat(token["saved_at"])
    return (datetime.now(timezone.utc) - saved).total_seconds() / 3600


def access_token() -> str:
    """The saved login token if it is fresh, else UPSTOX_ACCESS_TOKEN from the environment."""
    age = token_age_hours()
    if age is not None and age < TOKEN_MAX_AGE_HOURS:
        return load_token()["access_token"]
    token = get_settings().upstox_access_token
    if not token:
        raise RuntimeError("No valid Upstox token. Run: python -m stocksense upstox-login")
    return token


# ── OAuth ─────────────────────────────────────────────────────────────────────


def authorize_url() -> str:
    s = get_settings()
    params = {"response_type": "code", "client_id": s.upstox_api_key, "redirect_uri": s.upstox_redirect_uri}
    return f"{API}/v2/login/authorization/dialog?{urlencode(params)}"


def exchange_code(code: str) -> dict:
    s = get_settings()
    resp = requests.post(
        f"{API}/v2/login/authorization/token",
        headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
        data={
            "code": code,
            "client_id": s.upstox_api_key,
            "client_secret": s.upstox_api_secret,
            "redirect_uri": s.upstox_redirect_uri,
            "grant_type": "authorization_code",
        },
        timeout=10,
    )
    return resp.json()


# ── Market data ───────────────────────────────────────────────────────────────


def _headers() -> dict:
    return {"Authorization": f"Bearer {access_token()}", "Accept": "application/json"}


def ltp_quotes(instrument_keys: list[str]) -> dict[str, dict]:
    """
    {instrument_key: {"price": float, "change_pct": float}} using the LTP endpoint.
    Upstox accepts up to 500 keys per request.
    """
    out: dict[str, dict] = {}
    for start in range(0, len(instrument_keys), 500):
        batch = instrument_keys[start : start + 500]
        resp = requests.get(
            f"{API}/v3/market-quote/ltp",
            headers=_headers(),
            params={"instrument_key": ",".join(batch)},
            timeout=15,
        )
        resp.raise_for_status()
        for quote in resp.json().get("data", {}).values():
            key = quote.get("instrument_token")
            ltp, prev = quote.get("last_price"), quote.get("cp")
            if key and ltp:
                change = (ltp - prev) / prev * 100 if prev else 0.0
                out[key] = {"price": round(ltp, 2), "change_pct": round(change, 2)}
    return out


def websocket_url() -> str:
    resp = requests.get(f"{API}/v3/feed/market-data-feed/authorize", headers=_headers(), timeout=10)
    resp.raise_for_status()
    return resp.json()["data"]["authorizedRedirectUri"]

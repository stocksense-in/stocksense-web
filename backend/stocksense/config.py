"""
Environment and settings — the only place that reads environment variables.

Lookup order for the .env file: backend/.env, then the repo root .env.local / .env.
Old variable names (NEXT_PUBLIC_SUPABASE_SERVICE_KEY, NEXT_PUBLIC_UPSTOX_*) still
work so existing .env files keep running, but new setups should use the names
in backend/.env.example.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_DIR = BACKEND_DIR.parent
DATA_DIR = BACKEND_DIR / "data"

# Default snapshot location: the frontend reads this file when Supabase is not configured.
FRONTEND_SNAPSHOT = REPO_DIR / "frontend" / "data" / "snapshot.json"


def _load_dotenv_files() -> None:
    for candidate in (BACKEND_DIR / ".env", REPO_DIR / ".env.local", REPO_DIR / ".env"):
        if candidate.exists():
            # Earlier files win: override=False keeps values that are already set.
            load_dotenv(candidate, override=False)


def _first_env(*names: str) -> str:
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return ""


@dataclass(frozen=True)
class Settings:
    supabase_url: str
    supabase_service_key: str
    upstox_api_key: str
    upstox_api_secret: str
    upstox_redirect_uri: str
    upstox_access_token: str

    @property
    def has_supabase(self) -> bool:
        return bool(self.supabase_url and self.supabase_service_key)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    _load_dotenv_files()
    return Settings(
        supabase_url=_first_env("SUPABASE_URL", "NEXT_PUBLIC_SUPABASE_URL"),
        # Service-role key: bypasses row-level security, so it must never reach the browser.
        supabase_service_key=_first_env(
            "SUPABASE_SERVICE_KEY", "SUPABASE_KEY", "NEXT_PUBLIC_SUPABASE_SERVICE_KEY"
        ),
        upstox_api_key=_first_env("UPSTOX_API_KEY", "NEXT_PUBLIC_UPSTOX_API_KEY"),
        upstox_api_secret=_first_env("UPSTOX_API_SECRET", "NEXT_PUBLIC_UPSTOX_API_SECRET"),
        upstox_redirect_uri=_first_env("UPSTOX_REDIRECT_URI", "NEXT_PUBLIC_UPSTOX_REDIRECT_URI")
        or "http://localhost:8000/callback",
        upstox_access_token=_first_env("UPSTOX_ACCESS_TOKEN", "NEXT_PUBLIC_UPSTOX_ACCESS_TOKEN"),
    )

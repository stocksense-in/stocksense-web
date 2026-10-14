"""
Where pipeline results go.

Two destinations, usable together:
  • Supabase — the `stocks` and `live_prices` tables (see backend/schema.sql).
  • A JSON snapshot — frontend/data/snapshot.json by default. The website reads
    it when Supabase isn't configured, so it can show real numbers offline.

Jobs call store.upsert_stocks(rows) / store.upsert_prices(rows) and don't care
which destinations are active.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

from .config import get_settings
from .log import get_logger

log = get_logger(__name__)

# Supabase/PostgREST rejects very large payloads; 500 rows per request is safe.
UPSERT_CHUNK = 500


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@lru_cache(maxsize=1)
def supabase_client():
    from supabase import create_client

    settings = get_settings()
    if not settings.has_supabase:
        raise RuntimeError(
            "Supabase is not configured. Set SUPABASE_URL and SUPABASE_SERVICE_KEY "
            "in backend/.env (see backend/.env.example)."
        )
    return create_client(settings.supabase_url, settings.supabase_service_key)


def fetch_stock_rows(symbols: list[str]) -> dict[str, dict]:
    """Existing `stocks` rows keyed by symbol (used to re-score after partial updates)."""
    client = supabase_client()
    rows: dict[str, dict] = {}
    for start in range(0, len(symbols), 200):
        batch = symbols[start : start + 200]
        result = client.table("stocks").select("*").in_("symbol", batch).execute()
        rows.update({r["symbol"]: r for r in result.data})
    return rows


def _missing_column(exc: Exception) -> str | None:
    """Column name from PostgREST's "Could not find the 'x' column of 't'" error, if that's the error."""
    match = re.search(r"Could not find the '([^']+)' column", str(exc))
    return match.group(1) if match else None


class Store:
    def __init__(self, use_db: bool = True, snapshot_path: Path | None = None):
        self.use_db = use_db
        self.snapshot_path = snapshot_path
        if use_db:
            supabase_client()  # fail fast with a clear message if not configured

    # ── public API ──────────────────────────────────────────────────────────

    def upsert_stocks(self, rows: list[dict]) -> None:
        if not rows:
            return
        if self.use_db:
            self._upsert_db("stocks", rows)
        if self.snapshot_path:
            self._merge_snapshot("stocks", rows)

    def upsert_prices(self, rows: list[dict]) -> None:
        if not rows:
            return
        if self.use_db:
            self._upsert_db("live_prices", rows)
        if self.snapshot_path:
            self._merge_snapshot("prices", rows)

    def existing_stocks(self, symbols: list[str]) -> dict[str, dict]:
        """Current stored rows for these symbols, from Supabase or else the snapshot."""
        if self.use_db:
            return fetch_stock_rows(symbols)
        if self.snapshot_path and self.snapshot_path.exists():
            data = json.loads(self.snapshot_path.read_text(encoding="utf-8"))
            wanted = set(symbols)
            return {r["symbol"]: r for r in data.get("stocks", []) if r["symbol"] in wanted}
        return {}

    # ── internals ───────────────────────────────────────────────────────────

    # Columns the live database doesn't have yet (schema.sql migration not run).
    _missing_columns: set[str] = set()

    def _upsert_db(self, table: str, rows: list[dict]) -> None:
        from postgrest.exceptions import APIError

        client = supabase_client()
        # A bulk upsert needs every row to have the same columns. Jobs merge new
        # values over the stored row first, so filling gaps with None is safe.
        columns = {key for row in rows for key in row} - self._missing_columns
        for start in range(0, len(rows), UPSERT_CHUNK):
            while True:
                chunk = [{k: r.get(k) for k in columns} for r in rows[start : start + UPSERT_CHUNK]]
                try:
                    client.table(table).upsert(chunk, on_conflict="symbol").execute()
                    break
                except APIError as exc:
                    column = _missing_column(exc)
                    if column is None or column not in columns:
                        raise
                    log.warning(
                        f"`{table}` has no column `{column}` — skipping it. "
                        "Run backend/schema.sql in the Supabase SQL editor to add it."
                    )
                    self._missing_columns.add(column)
                    columns.discard(column)
        log.info(f"  → {len(rows)} rows saved to Supabase `{table}`")

    def _merge_snapshot(self, key: str, rows: list[dict]) -> None:
        path = self.snapshot_path
        data = (
            json.loads(path.read_text(encoding="utf-8"))
            if path.exists()
            else {"stocks": [], "prices": []}
        )
        merged = {r["symbol"]: r for r in data.get(key, [])}
        for row in rows:
            # Partial rows (e.g. only promoter holding) update fields, never erase them.
            merged[row["symbol"]] = {**merged.get(row["symbol"], {}), **row}
        data[key] = sorted(merged.values(), key=lambda r: r["symbol"])
        data["generated_at"] = now_iso()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        log.info(f"  → {len(rows)} rows merged into {path.name} [{key}]")

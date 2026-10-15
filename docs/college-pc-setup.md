# College PC setup — 14 October 2026

Phase 0 (M0.1–M0.3) on the college PC, the "engine" machine: data lake, GPU work,
scheduled jobs. The public site never depends on it.

## The machine

| | |
|---|---|
| OS | Windows 11 Pro 10.0.26200 |
| CPU | Intel Xeon W-2295, 18 cores / 36 threads, 3.0 GHz |
| RAM | 128 GB |
| GPU | NVIDIA RTX A5000, 24 GB, driver 596.51 (CUDA 13.2), WDDM mode; also drives the display |
| Disks | C: 476 GB (109 GB free) · D: 500 GB (29 GB free) · E: 454 GB (408 GB free) |
| Account | `PRO-LAB-2`, a member of Administrators but not elevated (UAC). Nothing here needed admin. |
| Network | Direct, no proxy (WinINET, WinHTTP and `HTTP(S)_PROXY` all unset) |
| Also running | AnyDesk, TeamViewer, eScan antivirus. No other user's processes on the GPU at setup time. |

Shared lab machine: the Windows account's global git identity belongs to someone else,
so the repo sets its own `user.name` / `user.email` (`git config --local`).

## What's installed, and where

Everything is per-user; no system packages, services or drivers were installed.

| What | Where | Notes |
|---|---|---|
| Repo | `C:\Users\PRO-LAB-2\stocksense-web` | cloned from `main` |
| Python 3.12.13 | `%APPDATA%\uv\python\cpython-3.12.13-windows-x86_64-none\` | via `uv python install 3.12` (uv 0.11 was already in `~\.local\bin`). The system Python is 3.14, not used. |
| API/pipeline env | `backend\.venv` | `requirements.txt` only, the same as the API container |
| ML env | `backend\.venv-ml` | `requirements-ml.txt` = `requirements.txt` + PyTorch 2.14.1+cu132 (~3 GB) |
| Node 24.21 / npm 11.19 | `C:\Program Files\nodejs` | already installed system-wide; meets "Node 22+", so no second copy |
| Data lake | `E:\stocksense\lake` | the only disk with real headroom; `STOCKSENSE_LAKE_DIR` in `backend\.env` |
| GitHub CLI 2.102.0 | `~\.local\bin\gh.exe` | official release zip, SHA-256 checked against the release's checksums file; for pushing and PRs. Run `gh auth logout` when you leave: this Windows account is shared. |

**curl on this network:** Windows' TLS layer (schannel) sometimes can't reach certificate
revocation servers from here (`CRYPT_E_REVOCATION_OFFLINE`, seen on GitHub's release
downloads). `curl --ssl-revoke-best-effort` still validates the certificate; verify
checksums for anything you download. Python (`httpx`, `requests`, `pip`) isn't affected.

**Why a separate ML env:** `backend\.venv` stays identical to what the API Docker image
installs, so tests there reflect production. ML libraries (transformers, sentence-transformers,
LightGBM, …) will add pins on numpy/pandas over time; keeping them in `.venv-ml` means they
can never break the API. `.venv-ml` is a superset, so ML jobs can still import `stocksense`.

## Using the environments

```powershell
cd C:\Users\PRO-LAB-2\stocksense-web\backend

# API, pipeline jobs, tests
.venv\Scripts\activate
pytest
python -m stocksense api --port 8000
python -m stocksense lake-prices

# GPU work
deactivate
.venv-ml\Scripts\activate
python ..\ml\gpu_check.py
```

Git Bash: `source .venv/Scripts/activate`. Recreate either env from scratch:

```powershell
uv venv .venv --python 3.12 --seed;    .venv\Scripts\python -m pip install -r requirements.txt
uv venv .venv-ml --python 3.12 --seed; .venv-ml\Scripts\python -m pip install -r requirements-ml.txt
```

Frontend: `cd frontend && npm ci && npm run build` (or `npm run dev`).

## Secrets

`backend\.env` and `frontend\.env.local` are created on this machine and gitignored (checked
with `git check-ignore`). Values are pasted by hand over AnyDesk, never through chat or git.
The frontend file holds the **anon** key only. Checked 14 Oct by presence and key role only
(no values printed): backend has the URL, service_role and anon keys and the Upstox keys and token;
the frontend has the URL and an anon-role key, matching the backend. Both build and run.

## Results

### Backend tests

`cd backend && pytest`: **71 passed** (58 existing + 13 new data-lake tests), offline, ~2 s.

### Frontend build

`npm ci && npm run build`: **builds**: 15 static routes, ~18 s. Lint not run (14 known
errors in the original code). npm 11 skips install scripts that aren't approved (`sharp`,
`unrs-resolver`); the build doesn't need them.

### API smoke test (M0.1)

`python -m stocksense api --port 8000` (bound to 127.0.0.1 only; stopped afterwards).
Times are for the first call to each endpoint, then a repeat served from the API's cache.
The `/health` row is warm: a readiness poll loaded the Supabase tables just before.

| Endpoint | HTTP | First / cached | What came back |
|---|---|---|---|
| `/health` | 200 | 62 / 30 ms | `data_source: supabase`, 2,646 stocks (41 stale, 2,383 scored) |
| `/market/overview` | 200 | 33 / 31 ms | NIFTY 50, SENSEX, BANK NIFTY, India VIX + breadth, sectors, movers, top scored |
| `/stocks/TCS` | 200 | 51 / 48 ms | score 69 "Strong" (6 of 6 metrics, per-metric breakdown), 6 peers, not stale |
| `/geopolitics` | 200 | 1,369 / 4 ms | 13 sectors' exposure from 12 live news events |
| `/ipos` | 200 | 1,831 / 2 ms | 4 open + 4 upcoming NSE issues |

Pipeline write: `python -m stocksense prices --symbols TCS INFY` saved **6 rows** to
`live_prices`: 4 indices (NIFTY50, SENSEX, BANKNIFTY, INDIAVIX) and the 2 stocks, in 16 s.
Read back through the anon key: all six `updated_at` within the last minute.

Supabase REST from this machine: HTTP 200 in 0.46–1.2 s (three reads).

### GPU (M0.2)

`backend\.venv-ml\Scripts\python ml\gpu_check.py`:

```
torch 2.14.1+cu132, built for CUDA 13.2
cuda available: True
device: NVIDIA RTX A5000 (compute 8.6, 64 SMs)
memory: 24.0 GiB total, 22.8 GiB free
cpu threads used by torch: 18

8192x8192 matmul
               ms/op  TFLOP/s  vs CPU
GPU fp32        67.3    16.35     10x
GPU tf32        26.1    42.20     26x
GPU fp16        13.5    81.34     51x
CPU fp32       686.4     1.60      1x
```

The GPU also drives the desktop (about 0.7 GB in use at idle), so plan on ~22 GB for
training. Use fp16/bf16 or TF32 for training; fp32 is 2.5–5× slower.

### Network reachability (M0.2)

Checked from this machine with the pipeline's own request headers (no proxy).

| Source | Result | HTTP | Latency (to first byte) |
|---|---|---|---|
| NSE archives `EQUITY_L.csv` | ✅ reachable | 200 | 395 ms |
| NSE API `ipo-current-issue` (browser-like headers) | ✅ reachable | 200 | 562 ms |
| Yahoo chart `^NSEI` | ✅ reachable | 200 | 388 ms |
| GDELT `lastupdate.txt` | ✅ reachable | 200 | 968 ms |
| RSS Economic Times — Markets | ✅ reachable | 200 | 596 ms |
| RSS Economic Times — Economy | ✅ reachable | 200 | 342 ms |
| RSS Livemint — Markets | ✅ reachable | 200 | 343 ms |
| RSS Business Standard — Markets | ✅ reachable* | 200 | 226–325 ms |
| RSS Google News | ✅ reachable | 200 | 723 ms |
| Supabase REST (project, anon read) | ✅ reachable | 200 | 461–1,222 ms |
| Hugging Face | ✅ reachable | 200 | 441 ms |
| PyPI | ✅ reachable | 200 | 200 ms |
| GitHub | ✅ reachable | 200 | 189 ms |
| *Extra:* NSE bhavcopy (new CM format, `nsearchives`) | ✅ reachable | 200 | 291 ms |
| *Extra:* SEBI, RBI, data.gov.in, Screener.in | ✅ reachable | 200 | 254–837 ms |
| *Extra:* Upstox API, PyTorch wheel index | ✅ reachable | 200 | 350 / 900 ms |
| *Extra:* BSE API (`api.bseindia.com`) | ⛔ blocked by BSE | 403 | 328 ms |

\* Business Standard's first attempt timed out in the TLS handshake; four retries (curl,
httpx ×3, requests) all returned 200 in ~0.3 s, so it was transient, not the campus network.

**BSE API:** the 403 is Akamai's "Access Denied" page, i.e. BSE's own bot protection, not
the college network. PLAN.md §1.5 rules out working around it, and no current job uses it.
For BSE data later, use BSE's public bulk downloads (bhavcopy, announcements archives) or
the NSE equivalents, which are all reachable.

Nothing needs a proxy or an IT exception today.

### Data lake (M0.3)

`backend/stocksense/lake.py`; layout and usage in `backend/README.md` → "Data lake".
Root: `E:\stocksense\lake`.

End to end against the real database:

```
> python -m stocksense lake-prices
Lake: wrote 2648 rows to clean/prices (1 day partition(s))
Saved 2648 live prices for 2026-10-14 to E:\stocksense\lake\clean\prices

> python -m stocksense lake-query "select date, count(*) as rows, count(distinct symbol) as symbols, max(updated_at) as latest_update from prices group by date"
      date  rows  symbols             latest_update
2026-10-14  2648     2648 2026-10-14 20:32:07+05:30
```

TCS, INFY and the four indices read back from Parquet with the same prices Supabase
holds. Running the job again the same day leaves one file and 2,648 rows (the day is
replaced, not appended). The lake is 320 KB so far.

## Needs you

1. Rotate the old Upstox token and Superdesign key if not done yet (PLAN.md §2). Upstox
   access tokens also expire daily (~3:30 AM IST): `python -m stocksense upstox-login`.
2. Before M0.4/M0.5: check the college IT policy on long-running personal jobs, a
   scheduled task on this machine, and remote access (Tailscale / Cloudflare Tunnel).
   Both milestones install background services, so they need your approval.
3. AnyDesk and TeamViewer both run on this PC and it now holds a database write key:
   protect both with a strong password and 2FA.
4. The lake has no backup yet (that's M0.4). A lab machine can be reimaged without
   notice; until then, treat `E:\stocksense\lake` as rebuildable, not precious.

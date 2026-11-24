"""
Analysis: what would change if the StockSense score judged each metric against the
company's sector peers instead of fixed curves?

    backend\\.venv\\Scripts\\python ml\\score_comparison.py      # from the repo root

Nothing in production changes. For every scored stock it compares:
  • current   — scoring.score_stock: fixed curves (with bank/new-age exceptions)
  • relative  — each metric's sub-score = share of sector peers it beats (direction-aware,
                benchmarks.peer_context), same weights and coverage rules; loss-making P/E
                scores 0, new-age P/E is skipped
  • blend     — 0.7 × relative + 0.3 × current: "good for its sector" without forgetting
                that some sectors are structurally weaker businesses

Writes ml/reports/score-comparison-<date>.md.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))

from stocksense import benchmarks as bm  # noqa: E402
from stocksense.market import MarketData  # noqa: E402
from stocksense.scoring import BALANCE_SHEET, MIN_METRICS, NEWAGE_SECTORS, WEIGHTS, score_stock  # noqa: E402
from stocksense.sectors import SECTOR_LABELS  # noqa: E402

BLEND = 0.7


def relative_score(stock, benches) -> int | None:
    parts = {}
    for metric in WEIGHTS:
        value = getattr(stock, metric)
        if value is None:
            continue
        if metric == "pe":
            if stock.sector in NEWAGE_SECTORS:
                continue
            if value <= 0:
                parts[metric] = 0.0
                continue
        ctx = bm.peer_context(metric, value, stock.sector, benches)
        if ctx and ctx["better_than_pct"] is not None:
            parts[metric] = float(ctx["better_than_pct"])
    if len(parts) < MIN_METRICS or not BALANCE_SHEET & parts.keys():
        return None
    total = sum(WEIGHTS[k] for k in parts)
    return round(sum(parts[k] * WEIGHTS[k] for k in parts) / total)


def verdict(score: float) -> str:
    return "Strong" if score >= 65 else "Fair" if score >= 45 else "Weak"


def main() -> None:
    stocks = [s for s in MarketData().fresh_stocks()]
    benches = bm.build(stocks)
    rows = []
    for s in stocks:
        metrics = {k: getattr(s, k) for k in WEIGHTS}
        current = score_stock(metrics, s.sector).composite
        rel = relative_score(s, benches)
        if current is None or rel is None:
            continue
        rows.append({"symbol": s.symbol, "name": s.name, "sector": SECTOR_LABELS.get(s.sector, s.sector),
                     "market_cap": s.market_cap or 0, "current": current, "relative": rel,
                     "blend": round(BLEND * rel + (1 - BLEND) * current)})
    df = pd.DataFrame(rows)
    df["change"] = df["blend"] - df["current"]
    corr = df["current"].rank().corr(df["blend"].rank())  # Spearman = Pearson on ranks (no scipy needed)

    by_sector = df.groupby("sector").agg(stocks=("symbol", "size"), current=("current", "mean"),
                                         blend=("blend", "mean")).round(1)
    by_sector["move"] = (by_sector["blend"] - by_sector["current"]).round(1)  # not "shift": that is a Series method
    by_sector = by_sector[by_sector["stocks"] >= 20].sort_values("move")

    flips = pd.crosstab(df["current"].map(verdict), df["blend"].map(verdict))
    large = df[df["market_cap"] >= 100_000]  # large caps (₹1 lakh crore+), the names beginners know
    up = large.sort_values("change", ascending=False).head(8)
    down = large.sort_values("change").head(8)

    def table(frame, cols):
        lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
        for r in frame.itertuples():
            lines.append("| " + " | ".join(str(getattr(r, c)) for c in cols) + " |")
        return lines

    lines = [
        f"# Sector-relative score — what would change ({date.today()})",
        "",
        f"{len(df)} scored NSE stocks. Current = fixed curves; relative = share of sector peers beaten",
        f"on each metric; **blend = {BLEND:.0%} relative + {1 - BLEND:.0%} current** (the candidate). Code:",
        "`ml/score_comparison.py`. Nothing in production has changed.",
        "",
        f"- Rank agreement between current and blend (Spearman): **{corr:.2f}**.",
        f"- Median absolute change: **{df['change'].abs().median():.0f} points**; "
        f"{(df['change'].abs() >= 15).mean():.0%} of stocks move 15+ points.",
        "",
        "## Sector averages (sectors with 20+ scored stocks)",
        "",
        "Fixed curves systematically favour some sectors (cheap-looking, high-margin businesses)",
        "and penalise others (FMCG's high P/Es, thin-margin industries). The blend evens that out.",
        "",
        "| Sector | Stocks | Current avg | Blend avg | Shift |",
        "|---|---|---|---|---|",
    ]
    lines += [f"| {sec} | {int(r.stocks)} | {r.current} | {r.blend} | {r.move:+} |" for sec, r in by_sector.iterrows()]
    lines += ["", "## Verdict changes (rows: current, columns: blend)", ""]
    lines += ["| current \\ blend | " + " | ".join(flips.columns) + " |", "|---|" + "---|" * len(flips.columns)]
    lines += [f"| {idx} | " + " | ".join(str(v) for v in row) + " |" for idx, row in flips.iterrows()]
    lines += ["", "## Large caps that gain most", ""] + table(up, ["symbol", "sector", "current", "relative", "blend"])
    lines += ["", "## Large caps that lose most", ""] + table(down, ["symbol", "sector", "current", "relative", "blend"])
    lines += [
        "",
        "## Reading this",
        "",
        "- A purely relative score answers \"how good is this company *for its sector*\" — every",
        "  sector then averages ~50, which hides that some industries are genuinely better",
        "  businesses. The blend keeps 30% of the absolute view for that reason.",
        "- Relative sub-scores need enough peers: sectors under 10 usable values use the whole",
        "  market (benchmarks.MIN_PEERS).",
        "- Decision needed before switching: blend weight, and whether the frontend's",
        "  `lib/scoring.ts` mirror moves to the API (it can't compute peer percentiles itself).",
        "",
    ]
    out = REPO / "ml" / "reports" / f"score-comparison-{date.today()}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"{len(df)} stocks; spearman {corr:.2f}; report: {out}")


if __name__ == "__main__":
    main()

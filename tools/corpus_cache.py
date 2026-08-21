#!/usr/bin/env python3
"""
T0-4  Cache economics over the user's REAL session corpus.

Round 1 established that whether the 1-hour prompt cache earns its premium
depends on the shape of the usage, not on the TTL price -- dense headless runs
never idle past 5 minutes, interactive sessions do. That was two data points.
This measures the actual mix across every session on this machine and prices
both TTLs against it.

Local only. Reads token accounting and timestamps; no message content leaves
this process, and nothing is written outside the bench directory.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pricing  # noqa: E402

PROJECTS = Path.home() / ".claude" / "projects"
GAP_5M = 300


def parse_session(path: Path) -> dict | None:
    seen: dict[str, dict] = {}
    for line in path.open(encoding="utf-8", errors="replace"):
        line = line.strip()
        if not line:
            continue
        try:
            o = json.loads(line)
        except json.JSONDecodeError:
            continue
        if o.get("type") != "assistant":
            continue
        msg = o.get("message") or {}
        u = msg.get("usage")
        if not u:
            continue
        key = o.get("requestId") or o.get("uuid")
        rec = {
            "model": msg.get("model"),
            "input": int(u.get("input_tokens") or 0),
            "cache_creation": int(u.get("cache_creation_input_tokens") or 0),
            "cache_read": int(u.get("cache_read_input_tokens") or 0),
            "output": int(u.get("output_tokens") or 0),
            "cc_1h": int((u.get("cache_creation") or {}).get("ephemeral_1h_input_tokens") or 0),
            "cc_5m": int((u.get("cache_creation") or {}).get("ephemeral_5m_input_tokens") or 0),
            "ts": o.get("timestamp"),
        }
        # keep-max per requestId (streaming partials, see analyze.py)
        if key in seen and rec["output"] <= seen[key]["output"]:
            continue
        seen[key] = rec
    if not seen:
        return None
    recs = list(seen.values())
    times = sorted(
        t for t in (
            datetime.fromisoformat(r["ts"].replace("Z", "+00:00")) if r["ts"] else None
            for r in recs) if t)
    gaps = [(times[i + 1] - times[i]).total_seconds() for i in range(len(times) - 1)]
    return {
        "requests": len(recs),
        "gaps": gaps,
        "expiries_5m": sum(1 for g in gaps if g > GAP_5M),
        "cost_actual": pricing.cost_of_records(recs),
        "cost_all_1h": pricing.cost_of_records(recs, force_ttl="1h"),
        "cost_all_5m": pricing.cost_of_records(recs, force_ttl="5m"),
        "cache_read": sum(r["cache_read"] for r in recs),
        "cache_write": sum(r["cache_creation"] for r in recs),
        "output": sum(r["output"] for r in recs),
    }


def main() -> None:
    files = sorted(PROJECTS.rglob("*.jsonl"), key=lambda p: p.stat().st_size, reverse=True)
    print(f"corpus: {len(files):,} session files, "
          f"{sum(f.stat().st_size for f in files)/1024/1024:,.0f} MB total\n")

    dense = []      # no gap over the 5-minute TTL -> a 5m cache never expires
    sparse = []     # at least one gap over it
    totals = {"actual": 0.0, "all_1h": 0.0, "all_5m": 0.0,
              "cache_read": 0, "cache_write": 0, "output": 0, "requests": 0}
    parsed = skipped = 0

    for f in files:
        try:
            s = parse_session(f)
        except (OSError, ValueError):
            skipped += 1
            continue
        if not s or s["requests"] < 2:
            skipped += 1
            continue
        parsed += 1
        (sparse if s["expiries_5m"] > 0 else dense).append(s)
        totals["actual"] += s["cost_actual"]
        totals["all_1h"] += s["cost_all_1h"]
        totals["all_5m"] += s["cost_all_5m"]
        for k in ("cache_read", "cache_write", "output", "requests"):
            totals[k] += s[k]

    print(f"parsed {parsed:,} sessions ({skipped:,} skipped: empty or single-request)\n")
    print(f"{'shape':34} {'sessions':>9} {'share':>7} {'cost@actual':>13}")
    for label, group in (("DENSE  (5m cache never expires)", dense),
                         ("SPARSE (5m cache would expire)", sparse)):
        share = len(group) / parsed * 100 if parsed else 0
        cost = sum(g["cost_actual"] for g in group)
        print(f"{label:34} {len(group):9,} {share:6.1f}% {cost:12,.2f}")

    print(f"\ntotal requests      : {totals['requests']:,}")
    print(f"cache_read tokens   : {totals['cache_read']:,}")
    print(f"cache_write tokens  : {totals['cache_write']:,}")
    print(f"output tokens       : {totals['output']:,}")
    print(f"\ncost as billed          : ${totals['actual']:,.2f}")
    print(f"cost if ALL writes 1h   : ${totals['all_1h']:,.2f}")
    print(f"cost if ALL writes 5m   : ${totals['all_5m']:,.2f}   "
          f"(delta {totals['all_5m']-totals['all_1h']:+,.2f}, "
          f"{(totals['all_5m']-totals['all_1h'])/totals['all_1h']*100:+.1f}%)")
    print("\nNOTE: the all-5m figure assumes an unchanged token pattern. That holds "
          "only for DENSE\nsessions; for SPARSE ones a 5-minute cache would expire and "
          "be re-written, so the\nfigure is a LOWER BOUND on what 5m would really cost.")

    if sparse:
        sparse_cost = sum(g["cost_actual"] for g in sparse)
        print(f"\nSparse sessions carry ${sparse_cost:,.2f} of the total "
              f"({sparse_cost/totals['actual']*100:.1f}%) -- that is the share where the "
              f"1-hour cache\ncan actually earn its premium.")


if __name__ == "__main__":
    main()

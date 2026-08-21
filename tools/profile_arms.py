#!/usr/bin/env python3
"""
Free analyses over transcripts already collected. No API cost.

Answers three questions the cost table could not:
  1. WHY did the Desktop arm issue 2.4x the requests? -> tool-call profile
  2. How much of the delegation penalty is the Sonnet routing rather than the
     architecture? -> re-price the delegated runs as if subagents ran Opus
  3. Does thinking-token share differ by arm?
"""

from __future__ import annotations

import json
import os
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pricing  # noqa: E402
from analyze import load_requests, transcript_files  # noqa: E402

# Live Claude Code session store. Not part of this repository -- this script only
# runs on the machine that produced the runs. Override with CLAUDE_PROJECTS_DIR.
PROJ = Path(os.environ.get("CLAUDE_PROJECTS_DIR",
                           Path.home() / ".claude" / "projects"))
ARMS = {
    "C1_cli_solo": [
        PROJ / "D--BenchRuns-PILOT-C1-01", PROJ / "D--BenchRuns-PILOT-C1-02",
        PROJ / "D--BenchRuns-PILOT-C1-03", PROJ / "D--BenchRuns-C1-04",
    ],
    "C3_cli_delegated": [
        PROJ / "D--BenchRuns-C3-01", PROJ / "D--BenchRuns-C3-02",
        PROJ / "D--BenchRuns-C3-03", PROJ / "D--BenchRuns-C3-04",
    ],
    "C2_desktop_solo": [PROJ / "D--BenchRuns-C2-01"],
}


def main_jsonl(project_dir: Path) -> Path | None:
    files = [p for p in project_dir.glob("*.jsonl")]
    return max(files, key=lambda p: p.stat().st_size) if files else None


def tool_calls(project_dir: Path) -> Counter:
    """Count tool_use blocks across the main transcript and its subagents."""
    main = main_jsonl(project_dir)
    if not main:
        return Counter()
    counts: Counter = Counter()
    seen_blocks: set[str] = set()
    for f in transcript_files(main):
        for line in f.open(encoding="utf-8", errors="replace"):
            try:
                o = json.loads(line)
            except json.JSONDecodeError:
                continue
            if o.get("type") != "assistant":
                continue
            for c in (o.get("message") or {}).get("content", []):
                if isinstance(c, dict) and c.get("type") == "tool_use":
                    bid = c.get("id")
                    if bid and bid in seen_blocks:
                        continue
                    if bid:
                        seen_blocks.add(bid)
                    counts[c.get("name", "?")] += 1
    return counts


def main() -> None:
    print("=" * 78)
    print("1. TOOL-CALL PROFILE  (why does one arm issue more requests?)")
    print("=" * 78)
    profiles = {}
    for arm, dirs in ARMS.items():
        agg: Counter = Counter()
        for d in dirs:
            agg += tool_calls(d)
        n = len(dirs)
        per_run = {k: v / n for k, v in agg.items()}
        profiles[arm] = per_run
        total = sum(per_run.values())
        print(f"\n{arm}  (mean per run, n={n})   TOTAL TOOL CALLS = {total:.1f}")
        for name, v in sorted(per_run.items(), key=lambda kv: -kv[1])[:12]:
            print(f"    {name:24} {v:8.1f}")

    print("\n" + "=" * 78)
    print("2. DELEGATION RE-PRICED AS IF SUBAGENTS RAN OPUS")
    print("   (separates the environment's Sonnet routing from the architecture)")
    print("=" * 78)
    for d in ARMS["C3_cli_delegated"]:
        main = main_jsonl(d)
        if not main:
            continue
        records, _ = load_requests(main)
        actual = pricing.cost_of_records(records)
        as_opus = pricing.cost_of_records(
            [{**r, "model": "claude-opus-5"} for r in records])
        sonnet_tok = sum(r["input"] + r["cache_creation"] + r["output"]
                         for r in records if (r["model"] or "").startswith("claude-sonnet"))
        print(f"  {d.name[-6:]}  actual=${actual:7.2f}   all-Opus=${as_opus:7.2f}   "
              f"x{as_opus/actual:4.2f}   sonnet fresh tokens={sonnet_tok:,}")

    print("\n" + "=" * 78)
    print("3. THINKING-TOKEN SHARE OF OUTPUT")
    print("=" * 78)
    for arm, dirs in ARMS.items():
        shares = []
        for d in dirs:
            main = main_jsonl(d)
            if not main:
                continue
            records, _ = load_requests(main)
            out = sum(r["output"] for r in records)
            think = sum(r["thinking"] for r in records)
            if out:
                shares.append(think / out * 100)
        if shares:
            print(f"  {arm:20} mean={sum(shares)/len(shares):5.1f}%   "
                  f"per-run={[round(s,1) for s in shares]}")


if __name__ == "__main__":
    main()

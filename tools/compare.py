#!/usr/bin/env python3
"""
Generic two-group comparison using the same pre-registered rules as stats.py:
exact Mann-Whitney (full enumeration), individual points always shown, one
primary metric tested, secondaries Holm-corrected among themselves with the
stop rule.

    python compare.py "high:PILOT-C1-01,PILOT-C1-02,..." "medium:M1-01,M1-02,..."
"""

from __future__ import annotations

import json
import sys
from itertools import combinations
from math import comb
from pathlib import Path
from statistics import mean, median, stdev

RESULTS = Path(r"results")
METRICS = [
    ("Y1b_fresh_tokens", "fresh tokens", True),
    ("Y1d_thinking", "thinking tokens", False),
    ("Y2b_peak_context", "peak context", False),
    ("Y3a_wall_seconds", "wall seconds", False),
    ("cost_usd", "cost USD", False),
    ("Y6_requests", "requests", False),
]


def load(ids):
    return [json.loads((RESULTS / i / "record.json").read_text("utf-8-sig")) for i in ids]


def mw_exact(a, b):
    n1, n2 = len(a), len(b)
    pool = a + b

    def u_of(ga, gb):
        return (sum(1 for x in ga for y in gb if x > y)
                + 0.5 * sum(1 for x in ga for y in gb if x == y))

    u_obs = u_of(a, b)
    extreme = sum(
        1 for idx in combinations(range(n1 + n2), n1)
        if abs(u_of([pool[i] for i in idx],
                    [pool[i] for i in range(n1 + n2) if i not in idx]) - n1 * n2 / 2)
        >= abs(u_obs - n1 * n2 / 2))
    return extreme / comb(n1 + n2, n1)


def desc(v):
    return (f"mean={mean(v):,.1f} median={median(v):,.1f} "
            f"sd={stdev(v):,.1f} CV={stdev(v)/mean(v)*100:.1f}%")


def main():
    (la, ida), (lb, idb) = (s.split(":", 1) for s in sys.argv[1:3])
    ga, gb = load(ida.split(",")), load(idb.split(","))
    print(f"{la} n={len(ga)}   vs   {lb} n={len(gb)}")
    print(f"minimum attainable two-sided p = {2/comb(len(ga)+len(gb), len(ga)):.4f}\n")

    secondary = []
    for key, label, primary in METRICS:
        a = [float(r[key]) for r in ga]
        b = [float(r[key]) for r in gb]
        p = mw_exact(a, b)
        sep = max(a) < min(b) or max(b) < min(a)
        tag = "PRIMARY" if primary else "secondary"
        print(f"--- {label} [{tag}] ---")
        print(f"  {la:8}: {desc(a)}")
        print(f"  {lb:8}: {desc(b)}")
        print(f"  points {la:8}: {[round(x, 2) for x in a]}")
        print(f"  points {lb:8}: {[round(x, 2) for x in b]}")
        print(f"  ratio {lb}/{la} = {mean(b)/mean(a):.3f}x   "
              f"exact p = {p:.4f}   complete separation: {sep}")
        if primary:
            print(f"  VERDICT: {'SIGNIFICANT' if p < 0.05 else 'NOT significant'}")
        else:
            secondary.append((p, label))
        print()

    print("--- Holm-Bonferroni across secondaries (with stop rule) ---")
    m = len(secondary)
    stopped = False
    for i, (p, label) in enumerate(sorted(secondary)):
        thr = 0.05 / (m - i)
        if stopped:
            v = "not rejected (Holm stopped earlier)"
        elif p <= thr:
            v = "passes"
        else:
            v = "DOES NOT PASS -> Holm stops here"
            stopped = True
        print(f"  {label:18} p={p:.4f}  threshold={thr:.4f}  {v}")


if __name__ == "__main__":
    main()

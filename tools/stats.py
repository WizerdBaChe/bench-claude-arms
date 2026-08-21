#!/usr/bin/env python3
"""
Pre-registered analysis for Experiment 2 (architecture: solo vs delegated).

Follows PROTOCOL S7:
  - ONE primary metric, tested at alpha=0.05.
  - Secondary metrics Holm-Bonferroni corrected AMONG THEMSELVES.
  - Exact Mann-Whitney U (no normal approximation: n=4 per group).
  - Individual data points always shown (small-n reporting rule).
"""

from __future__ import annotations

import json
from itertools import combinations
from math import comb
from pathlib import Path
from statistics import mean, median, stdev

RESULTS = Path(r"results")
C1 = ["PILOT-C1-01", "PILOT-C1-02", "PILOT-C1-03", "C1-04"]
C3 = ["C3-01", "C3-02", "C3-03", "C3-04"]

METRICS = [
    ("Y1b_fresh_tokens", "fresh tokens", True),      # True = PRIMARY
    ("Y2b_peak_context", "peak context", False),
    ("Y3a_wall_seconds", "wall seconds", False),
    ("cost_usd", "cost USD", False),
]


def load(ids: list[str]) -> list[dict]:
    # utf-8-sig: PowerShell's Set-Content -Encoding utf8 prepends a BOM.
    return [json.loads((RESULTS / i / "record.json").read_text("utf-8-sig")) for i in ids]


def mann_whitney_exact(a: list[float], b: list[float]) -> tuple[float, float]:
    """Exact two-sided p by full enumeration. Returns (U_a, p)."""
    n1, n2 = len(a), len(b)
    u_obs = sum(1 for x in a for y in b if x > y) + 0.5 * sum(1 for x in a for y in b if x == y)
    pool = a + b
    extreme = 0
    total = comb(n1 + n2, n1)
    for idx in combinations(range(n1 + n2), n1):
        ga = [pool[i] for i in idx]
        gb = [pool[i] for i in range(n1 + n2) if i not in idx]
        u = sum(1 for x in ga for y in gb if x > y) + 0.5 * sum(1 for x in ga for y in gb if x == y)
        if abs(u - n1 * n2 / 2) >= abs(u_obs - n1 * n2 / 2):
            extreme += 1
    return u_obs, extreme / total


def rank_biserial(a: list[float], b: list[float]) -> float:
    n1, n2 = len(a), len(b)
    wins = sum(1 for x in a for y in b if x > y)
    losses = sum(1 for x in a for y in b if x < y)
    return (wins - losses) / (n1 * n2)


def describe(vals: list[float]) -> str:
    return (f"n={len(vals)} mean={mean(vals):,.1f} median={median(vals):,.1f} "
            f"sd={stdev(vals):,.1f} CV={stdev(vals)/mean(vals)*100:.1f}% "
            f"range=[{min(vals):,.1f}, {max(vals):,.1f}]")


def main() -> None:
    solo, deleg = load(C1), load(C3)
    print(f"minimum attainable two-sided p at n1=n2=4 : {2/comb(8,4):.4f}\n")

    secondary = []
    for key, label, is_primary in METRICS:
        a = [float(r[key]) for r in solo]
        b = [float(r[key]) for r in deleg]
        _, p = mann_whitney_exact(a, b)
        r = rank_biserial(b, a)
        ratio = mean(b) / mean(a)
        tag = "PRIMARY" if is_primary else "secondary"
        print(f"--- {label}  [{tag}] ---")
        print(f"  solo      : {describe(a)}")
        print(f"  delegated : {describe(b)}")
        print(f"  points solo      : {[round(x) for x in a]}")
        print(f"  points delegated : {[round(x) for x in b]}")
        print(f"  ratio delegated/solo = {ratio:.2f}x")
        print(f"  exact two-sided p = {p:.4f}   rank-biserial r = {r:+.2f}")
        print(f"  complete separation: {max(a) < min(b) or max(b) < min(a)}")
        if is_primary:
            print(f"  VERDICT (alpha=0.05, single pre-registered primary): "
                  f"{'SIGNIFICANT' if p < 0.05 else 'not significant'}")
        else:
            secondary.append((p, label))
        print()

    print("--- Holm-Bonferroni across the 3 SECONDARY metrics ---")
    m = len(secondary)
    # Holm has a STOP RULE: at the first hypothesis that fails its threshold, every
    # remaining (larger-p) hypothesis is also not rejected. Reporting each line
    # independently would wrongly show a later metric "passing" at alpha/1.
    stopped = False
    for i, (p, label) in enumerate(sorted(secondary)):
        thr = 0.05 / (m - i)
        if stopped:
            verdict = "not rejected (Holm stopped at an earlier failure)"
        elif p <= thr:
            verdict = "passes"
        else:
            verdict = "DOES NOT PASS -> Holm stops here"
            stopped = True
        print(f"  {label:15} p={p:.4f}  threshold={thr:.4f}  {verdict}")
    print("\n  Note: the smallest p reachable at n=4 (0.0286) exceeds 0.05/3 = 0.0167,")
    print("  so NO secondary metric can pass Holm at this sample size regardless of")
    print("  how large the effect is. That is a property of n, not of the data.")
    print("  Secondary metrics are therefore reported descriptively only.")


if __name__ == "__main__":
    main()

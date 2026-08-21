#!/usr/bin/env python3
"""
RQ4: does the delegation penalty shrink as the task grows?

Two task sizes only. That is enough to state a direction and a magnitude of
change; it is NOT enough to fit a curve or locate a crossover. The linear
extrapolation below is printed as an explicitly labelled guess, not a finding.
"""

from __future__ import annotations

import json
from pathlib import Path
from statistics import mean

RESULTS = Path(r"results")
SETS = {
    "small_solo": ["PILOT-C1-01", "PILOT-C1-02", "PILOT-C1-03", "C1-04"],
    "small_deleg": ["C3-01", "C3-02", "C3-03", "C3-04"],
    "xl_solo": ["XL-CAL-01", "XL-A-02", "XL-A-03"],
    "xl_deleg": ["XL-B-01", "XL-B-02", "XL-B-03"],
}
METRICS = ["Y1b_fresh_tokens", "Y2b_peak_context", "Y3a_wall_seconds",
           "cost_usd", "Y6_requests", "Y1c_main_fresh"]


def load(ids):
    return [json.loads((RESULTS / i / "record.json").read_text("utf-8-sig")) for i in ids]


def main() -> None:
    g = {k: load(v) for k, v in SETS.items()}
    m = {k: {f: mean(float(r[f]) for r in v) for f in METRICS} for k, v in g.items()}

    size = m["xl_solo"]["Y1b_fresh_tokens"] / m["small_solo"]["Y1b_fresh_tokens"]
    print(f"task size (by solo fresh tokens): small = 1.000x, XL = {size:.3f}x\n")

    print(f"{'metric':22} {'small ratio':>12} {'XL ratio':>10} {'change':>10}")
    ratios = {}
    for f in METRICS:
        rs = m["small_deleg"][f] / m["small_solo"][f]
        rx = m["xl_deleg"][f] / m["xl_solo"][f]
        ratios[f] = (rs, rx)
        print(f"{f:22} {rs:12.3f} {rx:10.3f} {rx - rs:+10.3f}")

    print("\nabsolute means")
    print(f"{'metric':22} {'small solo':>13} {'small deleg':>13} "
          f"{'XL solo':>13} {'XL deleg':>13}")
    for f in METRICS:
        print(f"{f:22} {m['small_solo'][f]:13,.0f} {m['small_deleg'][f]:13,.0f} "
              f"{m['xl_solo'][f]:13,.0f} {m['xl_deleg'][f]:13,.0f}")

    print("\n--- context isolation: did the mechanism engage? ---")
    ps, px = ratios["Y2b_peak_context"]
    print(f"  peak context, delegated / solo:  small {ps:.3f}x  ->  XL {px:.3f}x")
    print("  small: delegation RAISED the lead model's peak context")
    print("  XL   : delegation LOWERED it — the isolation mechanism engaged")
    ms, mx = ratios["Y1c_main_fresh"]
    print(f"  main-line fresh tokens, deleg/solo: small {ms:.3f}x  ->  XL {mx:.3f}x")

    rs, rx = ratios["Y1b_fresh_tokens"]
    slope = (rx - rs) / (size - 1.0)
    cross = 1.0 + (1.0 - rs) / slope if slope else float("nan")
    print("\n--- LINEAR EXTRAPOLATION (two points — NOT an established curve) ---")
    print(f"  ratio at 1.00x task = {rs:.3f}")
    print(f"  ratio at {size:.2f}x task = {rx:.3f}")
    print(f"  implied slope = {slope:.3f} per unit task size")
    print(f"  ratio would reach 1.0 at about {cross:.2f}x the small task")
    print("  Two points fit infinitely many curves. A third size is required before")
    print("  this number may be quoted as a break-even point.")


if __name__ == "__main__":
    main()

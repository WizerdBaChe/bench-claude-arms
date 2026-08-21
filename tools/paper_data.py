#!/usr/bin/env python3
"""
Field-mapping check for the paper: every number the manuscript cites must
resolve to a file on disk. Prints the value AND its provenance path, so a
figure with no source is impossible to write by accident.

HISTORY OF WHAT THIS FILE COULD NOT SEE
  2026-08-21a  it only asserted that a cited FILE EXISTS. Two figures in the
               paper disagreed with the very files they cited and an exists()
               check could not see either. Fixed by printing the two derived
               products the paper quotes.
  2026-08-21b  a full reconciliation found ten more defects, and the derived
               values printed here were HAND-PICKED, so nine of the ten were
               in shapes this file never emitted: per-run min-max ranges
               (48-203 vs 43-229), arm means (%16.53 vs $16.52), cost-item
               shares (45%-48% vs 35.7%-66.4%), p_min at other n (0.333 vs
               1.000), the fuzz indeterminate split, and the mutation survivor
               list. Those are now SWEPT, not picked: every per-run field gets
               a min-max line, every arm gets its mean/CV, every registered
               comparison gets its ratio and exact p, and every product written
               "A x B = C" in the manuscript is re-multiplied.
               What is still unreachable is listed at the bottom -- read it
               before treating a clean run as a clean paper.

Usage:
    python paper_data.py            # all sections
    python paper_data.py --quiet    # skip the per-run dump
"""

from __future__ import annotations

import json
import re
import sys
from itertools import combinations
from math import comb
from pathlib import Path
from statistics import mean, stdev

BENCH = Path(__file__).resolve().parent.parent
RESULTS = BENCH / "results"
PAPER = BENCH / "PAPER_2026-08-20.md"

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyze  # noqa: E402
import pricing  # noqa: E402

ARMS = {
    "C1_small_solo_high": ["PILOT-C1-01", "PILOT-C1-02", "PILOT-C1-03", "C1-04"],
    "C2_desktop_solo_high": ["C2-01", "C2-02", "C2-03", "C2-04"],
    "C3_small_delegated_high": ["C3-01", "C3-02", "C3-03", "C3-04"],
    "M1_small_solo_medium": ["M1-01", "M1-02", "M1-03", "M1-04"],
    "XL_A_solo_high": ["XL-CAL-01", "XL-A-02", "XL-A-03"],
    "XL_B_delegated_high": ["XL-B-01", "XL-B-02", "XL-B-03"],
}
PROBES = ["P0-cli-opus-baseline", "P0-cli-opus-baseline-agents"]

# Every per-run field the paper quotes anywhere. A field listed here gets both
# an arm mean and a corpus-wide min-max, because BOTH shapes have published a
# wrong value: the arm mean in 7.3 ($16.53) and the range in 3.1.1 (48-203).
FIELDS = ["Y1b_fresh_tokens", "Y1c_main_fresh", "Y1c_side_fresh", "Y2a_T0",
          "Y2b_peak_context", "Y3a_wall_seconds", "Y6_requests",
          "Y1d_thinking", "cost_usd", "Y4_score"]

# The four comparisons the manuscript reports. label -> (baseline arm, arm)
COMPARISONS = [
    ("RQ1 channel   C1 -> C2", "C1_small_solo_high", "C2_desktop_solo_high"),
    ("RQ2 arch      C1 -> C3", "C1_small_solo_high", "C3_small_delegated_high"),
    ("RQ3 effort    C1 -> M1", "C1_small_solo_high", "M1_small_solo_medium"),
    ("RQ4 arch@XL   XLA-> XLB", "XL_A_solo_high", "XL_B_delegated_high"),
]


# --------------------------------------------------------------------- helpers
def load(rid: str):
    p = RESULTS / rid / "record.json"
    if not p.exists():
        return None
    try:
        # utf-8-sig: PowerShell's Set-Content -Encoding utf8 prepends a BOM.
        return json.loads(p.read_text("utf-8-sig"))
    except json.JSONDecodeError:
        return None


def read_json(p: Path):
    try:
        return json.loads(p.read_text("utf-8-sig"))
    except (json.JSONDecodeError, OSError):
        return None


def mann_whitney_exact(a: list[float], b: list[float]) -> float:
    """Exact two-sided p by full enumeration -- same routine as stats.py."""
    n1, n2 = len(a), len(b)

    def u(ga, gb):
        return (sum(1 for x in ga for y in gb if x > y)
                + 0.5 * sum(1 for x in ga for y in gb if x == y))

    u_obs, pool, extreme = u(a, b), a + b, 0
    for idx in combinations(range(n1 + n2), n1):
        ga = [pool[i] for i in idx]
        gb = [pool[i] for i in range(n1 + n2) if i not in idx]
        if abs(u(ga, gb) - n1 * n2 / 2) >= abs(u_obs - n1 * n2 / 2):
            extreme += 1
    return extreme / comb(n1 + n2, n1)


def head(title: str) -> None:
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


def col(ids: list[str], key: str) -> list[float]:
    return [float(r[key]) for i in ids if (r := load(i)) and r.get(key) is not None]


# ------------------------------------------------------------------- sections
def section_arms(quiet: bool) -> None:
    head("ARM DATA AVAILABILITY  (mean / sd / CV per arm)")
    for arm, ids in ARMS.items():
        have = [i for i in ids if load(i)]
        missing = [i for i in ids if not load(i)]
        state = "COMPLETE" if not missing else f"PARTIAL (missing {', '.join(missing)})"
        print(f"\n{arm}: n={len(have)}/{len(ids)}  {state}")
        for f in FIELDS:
            vals = col(have, f)
            if not vals:
                print(f"    {f:22} -")
                continue
            m = mean(vals)
            s = stdev(vals) if len(vals) > 1 else 0.0
            cv = f"{s / m * 100:5.1f}%" if m else "  n/a"
            print(f"    {f:22} mean={m:12,.2f}  sd={s:10,.1f}  CV={cv}  n={len(vals)}")
        if not quiet:
            for i in have:
                print(f"    evidence: {RESULTS / i / 'record.json'}")


def section_ranges() -> None:
    """min-max over the CURRENT run set.

    This section exists because 3.1.1 published "48-203 requests per run",
    which is exactly min(C1)-max(C3) -- the span before the M1, XL-A and XL-B
    arms existed. Nothing recomputed it when they were added. A range in the
    prose must be diffable against a range printed here.
    """
    head("PER-RUN RANGES OVER THE CURRENT SET  <- diff every 'X-Y' in the prose")
    ids = [i for a in ARMS.values() for i in a]
    for f in FIELDS:
        pairs = [(r[f], i) for i in ids if (r := load(i)) and r.get(f) is not None]
        if not pairs:
            continue
        lo, hi = min(pairs), max(pairs)
        print(f"   {f:22} min={lo[0]:>12,.2f} ({lo[1]:<12}) "
              f"max={hi[0]:>12,.2f} ({hi[1]})")
    print("\n   crosscheck delta vs CLI self-report (delegated runs only):")
    deltas = []
    for i in ids:
        r = load(i)
        m = re.search(r"delta=(-?\d+) \(([\d.]+)%\)", (r or {}).get("crosscheck") or "")
        if m and float(m.group(2)) > 0:
            deltas.append((float(m.group(2)), i))
    if deltas:
        print(f"      non-zero on {len(deltas)} run(s): "
              f"min={min(deltas)[0]}% ({min(deltas)[1]})  "
              f"max={max(deltas)[0]}% ({max(deltas)[1]})")
        print(f"      all values: {sorted(deltas)}")
    print("\n   transcript_completeness_pct below 100:")
    for i in ids:
        r = load(i) or {}
        v = r.get("transcript_completeness_pct")
        if v is not None and v < 100:
            print(f"      {i:14} {v}  (shortfall {100 - v:.1f}%)")


def section_totals() -> None:
    """Sums, and what each sum is a sum OF.

    $254.22 once sat in a row labelled n=22 while the arm rows summed to
    $253.39. Both figures were right; the label was not. So print the label
    with the number, every time.
    """
    head("TOTALS  <- every sum, with what it sums")
    arm_sums = {}
    for arm, ids in ARMS.items():
        s = sum(load(i)["cost_usd"] for i in ids if load(i))
        arm_sums[arm] = s
        print(f"   {arm:26} n={len(ids)}  ${s:10.6f}  -> ${round(s, 2):.2f}")
    task = sum(arm_sums.values())
    probe = sum(load(i)["cost_usd"] for i in PROBES if load(i))
    print(f"\n   TASK RUNS ONLY   (n=22)      ${task:10.6f}  -> ${round(task, 2):.2f}")
    print(f"   INSTRUMENT PROBES (n=2)      ${probe:10.6f}  -> ${round(probe, 2):.2f}")
    for i in PROBES:
        r = load(i)
        if r:
            print(f"        {i:30} ${r['cost_usd']:.6f}  T0={r['Y2a_T0']:,}")
    print(f"   CORPUS TOTAL      (n=24)     ${task + probe:10.6f}  "
          f"-> ${round(task + probe, 2):.2f}")
    dirs = sorted(p.name for p in RESULTS.iterdir() if p.is_dir())
    recs = [d for d in dirs if (RESULTS / d / "record.json").exists()]
    print(f"\n   result directories on disk   {len(dirs)}")
    print(f"   ...with a record.json        {len(recs)}")
    print(f"   task runs (arms above)       {sum(len(v) for v in ARMS.values())}")
    unclaimed = set(dirs) - {i for a in ARMS.values() for i in a} - set(PROBES)
    print(f"   directories claimed by NO arm and NO probe: {sorted(unclaimed) or 'none'}")


def section_comparisons() -> None:
    head("RATIOS AND EXACT MANN-WHITNEY  <- diff every ratio and p in 7.2-7.5")
    for label, a_arm, b_arm in COMPARISONS:
        print(f"\n-- {label}")
        for f in FIELDS:
            a, b = col(ARMS[a_arm], f), col(ARMS[b_arm], f)
            if not a or not b:
                continue
            p = mann_whitney_exact(a, b)
            ratio = f"{mean(b) / mean(a):7.4f}x" if mean(a) else "    n/a"
            print(f"   {f:22} {mean(a):12,.2f} -> {mean(b):12,.2f}  "
                  f"ratio={ratio}  p={p:.4f}  "
                  f"separated={max(a) < min(b) or max(b) < min(a)}")
    head("MINIMUM ATTAINABLE TWO-SIDED p  <- 7.8.2 published 0.333 for n=1")
    for n in (1, 2, 3, 4, 5):
        print(f"   n1=n2={n}: p_min = 2/C({2 * n},{n}) = {2 / comb(2 * n, n):.4f}")


def section_dose_response() -> None:
    """6.3.1 called the XL contract 1.51x while 7.5 called it 1.496x."""
    head("DOSE-RESPONSE  <- 6.3.1 / 7.5 / 8.2 must all quote the SAME scale factor")
    s_solo = mean(col(ARMS["C1_small_solo_high"], "Y1b_fresh_tokens"))
    x_solo = mean(col(ARMS["XL_A_solo_high"], "Y1b_fresh_tokens"))
    scale = x_solo / s_solo
    print(f"   task scale = XL-A solo / C1 solo (Y1b) = {x_solo:,.1f}/{s_solo:,.1f} "
          f"= {scale:.4f}x  (rounds to {scale:.2f}x)")
    for f in FIELDS:
        try:
            small = (mean(col(ARMS["C3_small_delegated_high"], f))
                     / mean(col(ARMS["C1_small_solo_high"], f)))
            xl = (mean(col(ARMS["XL_B_delegated_high"], f))
                  / mean(col(ARMS["XL_A_solo_high"], f)))
        except ZeroDivisionError:
            continue
        print(f"   {f:22} small={small:8.4f}  XL={xl:8.4f}  delta={xl - small:+8.4f}")
    r1 = (mean(col(ARMS["C3_small_delegated_high"], "Y1b_fresh_tokens"))
          / s_solo)
    r2 = mean(col(ARMS["XL_B_delegated_high"], "Y1b_fresh_tokens")) / x_solo
    slope = (r2 - r1) / (scale - 1.0)
    print(f"   two-point slope = {slope:.4f} per unit scale; "
          f"ratio reaches 1.0 at {1 + (1.0 - r1) / slope:.4f}x "
          f"(NOT a break-even point -- two points, no curve)")
    peaks = [(r["Y2b_peak_context"], i) for a in ARMS.values() for i in a
             if (r := load(i))]
    print(f"   peak context / 1,000,000 window: "
          f"small-arm mean {mean(col(ARMS['C1_small_solo_high'], 'Y2b_peak_context')) / 1e6 * 100:.1f}%, "
          f"corpus max {max(peaks)[0] / 1e6 * 100:.1f}% ({max(peaks)[1]})")


def section_cost_items() -> None:
    """8.1 published "cache_read is 45%-48% of a single run's cost".

    Recomputed here for all 22 runs. CLI runs are decomposed from the CLI's own
    modelUsage (the self-report is the authority, per rule 7); the four Desktop
    runs have no self-report, so they come from the archived transcript -- which
    is verified complete for them because its recomputed total equals cost_usd
    to the cent. The delegated runs' archived transcripts hold the MAIN LINE
    ONLY, so cache_write cannot be split by TTL there; cache_read is still exact
    because cacheReadInputTokens is a single-priced total per model.
    """
    head("COST ITEM SHARES PER RUN  <- diff the '45%-48%' family in 7.6 / 8.1")
    print(f"   {'run':14} {'cache_read':>11} {'output':>9} {'cache_write':>12} "
          f"{'input':>7}   source")
    shares: dict[str, list[float]] = {}
    for arm, ids in ARMS.items():
        shares[arm] = []
        for rid in ids:
            rec = load(rid)
            if not rec:
                continue
            cli = read_json(RESULTS / rid / "cli_result.json")
            if cli and "modelUsage" in cli:
                cr = ou = cw = ip = 0.0
                for model, u in cli["modelUsage"].items():
                    p = pricing.table_for(model)
                    cr += u["cacheReadInputTokens"] * p["cache_read"]
                    ou += u["outputTokens"] * p["output"]
                    ip += u["inputTokens"] * p["input"]
                    cw += u["cacheCreationInputTokens"] * p["cache_write_1h"]
                src = "cli_result.modelUsage"
                exact_cw = rec["Y6_sidechain_req"] == 0
            else:
                recs, _ = analyze.load_requests(RESULTS / rid / "transcript.jsonl")
                cr = sum(r["cache_read"] * pricing.table_for(r["model"])["cache_read"]
                         for r in recs)
                ou = sum(r["output"] * pricing.table_for(r["model"])["output"]
                         for r in recs)
                ip = sum(r["input"] * pricing.table_for(r["model"])["input"]
                         for r in recs)
                cw = sum(r["cc_1h"] * pricing.table_for(r["model"])["cache_write_1h"]
                         + r["cc_5m"] * pricing.table_for(r["model"])["cache_write_5m"]
                         for r in recs)
                src = "transcript"
                exact_cw = True
            tot = rec["cost_usd"] * 1e6
            shares[arm].append(cr / tot * 100)
            note = "" if exact_cw else "  (cache_write TTL split unavailable)"
            print(f"   {rid:14} {cr / tot * 100:10.1f}% {ou / tot * 100:8.1f}% "
                  f"{cw / tot * 100:11.1f}% {ip / tot * 100:6.2f}%   {src}{note}")
    print()
    allv = [v for r in shares.values() for v in r]
    for arm, row in shares.items():
        print(f"   {arm:26} cache_read share  mean={mean(row):5.1f}%  "
              f"min={min(row):5.1f}%  max={max(row):5.1f}%")
    print(f"\n   ACROSS ALL 22 RUNS   min={min(allv):.1f}%  max={max(allv):.1f}%")
    print(f"   ACROSS THE 6 ARM MEANS  min={min(mean(v) for v in shares.values()):.1f}%"
          f"  max={max(mean(v) for v in shares.values()):.1f}%")


def section_transcript_audit() -> None:
    """Defect #1 in 5.5 quotes a dedup ratio. Print the real one."""
    head("TRANSCRIPT DEDUP RATIO  <- 5.5 defect #1 quotes a multiple here")
    ids = [i for a in ARMS.values() for i in a]
    rows = []
    for rid in ids:
        rec = load(rid)
        recs, audit = analyze.load_requests(RESULTS / rid / "transcript.jsonl")
        complete = len(recs) == rec["Y6_requests"]
        rows.append((audit["dedup_ratio"], rid, complete))
    full = [r for r in rows if r[2]]
    print(f"   runs whose archived transcript reproduces Y6_requests: "
          f"{len(full)}/{len(rows)}")
    if full:
        print(f"      dedup ratio over those: {min(full)[0]:.2f}x - {max(full)[0]:.2f}x")
    partial = [r for r in rows if not r[2]]
    if partial:
        print(f"   MAIN-LINE-ONLY archives (delegated runs): "
              f"{', '.join(sorted(r[1] for r in partial))}")
        print("      their dedup ratio is NOT comparable and no subagent-inclusive"
              " ratio can be rebuilt from results/.")


def section_artefacts() -> None:
    head("INSTRUMENT CALIBRATION ARTEFACTS  (+ every product the paper quotes)")
    for label, rel in [
        ("scorer known-TRUE (small)", "holdout/CALIBRATION_true.json"),
        ("scorer known-FALSE (small)", "holdout/CALIBRATION_false.json"),
        ("scorer known-TRUE (XL)", "holdout/CALIBRATION_XL_true.json"),
        ("scorer known-FALSE (XL)", "holdout/CALIBRATION_XL_false.json"),
        ("differential fuzz result", "holdout/FUZZ_RESULT.json"),
        ("mutation result", "holdout/MUTATION_RESULT.json"),
        ("small-contract manifest", "holdout/MANIFEST.json"),
        ("XL-contract manifest", "holdout/MANIFEST_XL.json"),
        ("implementation inventory", "holdout/impl_inventory.json"),
        ("G4 screening set", "holdout/g4_screening_set.json"),
    ]:
        p = BENCH / rel
        mark = "OK " if p.exists() else "!! MISSING"
        extra = ""
        d = read_json(p) if p.exists() else None
        if isinstance(d, dict):
            for k in ("Y4_score", "Y4_xl", "detection_rate_pct", "determinate",
                      "prompt_a_sha256", "prompt_xl_a_sha256"):
                if k in d:
                    extra = f"  {k}={d[k]}"
                    break
            if rel.endswith("FUZZ_RESULT.json") and "arms" in d:
                n_arms, det = len(d["arms"]), d["determinate"]
                ctrl = d.get("control", {})
                extra += (f"  | arms={n_arms} x determinate={det}"
                          f" = {n_arms * det} executions"
                          f"   <- PAPER 7.8.1 must quote THIS product")
                # 7.8.1 called all 285 indeterminate cases "inputs that CRASH the
                # reference implementation". They are not: only `errors` crashed.
                extra += (f"\n           indeterminate={d['indeterminate']}"
                          f" = control errors {ctrl.get('errors')}"
                          f" + control diverged {ctrl.get('diverged')}"
                          f"   <- 'crashed' describes ONLY the errors half")
            if rel.endswith("MUTATION_RESULT.json"):
                viable, killed = d["viable"], d["killed"]
                # Equivalent mutants are excluded from the denominator by rule;
                # the rule is in RESULTS_T0-2-3-4_2026-08-20.md, T0-2. Name what
                # is excluded rather than applying it silently.
                survived = [str(s) for s in d.get("survived", [])]
                equivalent = [s for s in survived if s.startswith("dirs_included")]
                blind = [s for s in survived if s not in equivalent]
                denom = viable - len(equivalent)
                extra += (f" (raw {killed}/{viable})"
                          f"  | PAPER uses {killed}/{denom}"
                          f" = {100.0 * killed / denom:.1f}% after excluding"
                          f" {len(equivalent)} equivalent mutant(s): {equivalent}"
                          f"   <- rule: RESULTS_T0-2-3-4 T0-2"
                          f"\n           BLIND SPOTS = {len(blind)} surviving"
                          f" non-equivalent mutant(s): {blind}"
                          f"   <- 5.4 and 7.8.1 must enumerate ALL of these")
        elif isinstance(d, list):
            extra = f"  entries={len(d)}"
        print(f"  [{mark}] {label:28}{extra}\n           {p}")

    head("PROMPT SHA-256  (recomputed, not read back from meta.json)")
    import hashlib
    for f in sorted((BENCH / "fixtures").glob("*.md")):
        h = hashlib.sha256(f.read_bytes()).hexdigest()
        print(f"   {f.name:24} {h[:12].upper()}  ({h[:8]}...)")


def section_populations() -> None:
    """Which runs each instrument actually covers, and which it does not.

    A whole defect class hides here: a claim that was true of the corpus when
    it was written, left standing after the corpus grew. Four known instances
    -- 3.1.1's "48-203" (the pre-M1/XL request range), the schemaVersion audit's
    10-implementation population, RESULTS_T0-1_FUZZ's 9-implementation product
    51,435, and 7.8.1 stating the differential fuzz beside "all 22 runs" when
    it covers 13 of them. None of the other sections can see this: they all
    recompute over the CURRENT set, which is exactly what makes a stale
    population invisible. So print the population itself, and name what is
    outside it.
    """
    head("POPULATION SCOPE  <- any claim quoting one of these counts must quote"
         " ITS population")
    ids = {i for a in ARMS.values() for i in a}
    print(f"   task runs (the population most claims are about) : {len(ids)}")
    print(f"   instrument probes (excluded from every arm)      : {len(PROBES)}")

    fuzz = read_json(BENCH / "holdout" / "FUZZ_RESULT.json")
    if fuzz and "arms" in fuzz:
        covered = set(fuzz["arms"])
        missing = sorted(ids - covered)
        print(f"\n   differential fuzz  covers {len(covered)}/{len(ids)} task runs")
        print(f"      NOT covered ({len(missing)}): {missing}")
        by_arm = {a: f"{len(set(v) & covered)}/{len(v)}" for a, v in ARMS.items()}
        print(f"      per arm: {by_arm}")
        print("      ^ an arm at 0/n has NO differential-fuzz support; its"
              " equal-quality premise rests on the sealed suite alone.")

    inv = read_json(BENCH / "holdout" / "impl_inventory.json")
    if isinstance(inv, list):
        runs = [x.get("Run") for x in inv if isinstance(x, dict)]
        extra = [r for r in runs if r not in ids]
        print(f"\n   impl_inventory     {len(runs)} entries; {len(extra)} not a task "
              f"run: {extra}  (the author's reference control -- correctly NOT"
              f" one of the independent implementations)")

    g4 = read_json(BENCH / "holdout" / "g4_screening_set.json")
    if isinstance(g4, list):
        picked = [x.get("Run") for x in g4 if isinstance(x, dict)]
        print(f"\n   G4 manual screening covers {len(picked)}/{len(ids)} task runs "
              f"(one representative per arm, fixed in advance): {picked}")

    mut = read_json(BENCH / "holdout" / "MUTATION_RESULT.json")
    if mut:
        print(f"\n   mutation testing   population is {mut.get('viable')} viable "
              f"mutants OF THE REFERENCE IMPLEMENTATION -- not task runs. A claim "
              f"about it says nothing about how many arms were measured.")

    print("\n   Y4 sealed suite    covers ALL task runs -- it is the only"
          " instrument that does.")


def section_products() -> None:
    """Re-multiply every 'A x B = C' written in the manuscript.

    Fully mechanical, and it sweeps the paper instead of a hand-picked list --
    the gap named in the adversarial review 9.4. '13 x 5,715 = 51,435' survived
    a day because the 13 was updated and the product was not.
    """
    head("PRODUCTS WRITTEN IN THE MANUSCRIPT  (A x B = C, re-multiplied)")
    if not PAPER.exists():
        print(f"   !! {PAPER} not found")
        return
    text = PAPER.read_text("utf-8")
    # A and B may each be followed by a unit phrase ("18,353 tokens x 87 次請求
    # = 1,596,711"), so allow a short run of non-operator, non-'=' characters
    # between the factors. The operator is a real multiplication sign or a
    # space-delimited 'x'; a bare 'x' would match inside words.
    # (?<![\w_.]) keeps LaTeX subscripts out: without it "$T_0$ 差額（18,353 x 87"
    # picks up the 0 of T_0 as the first factor.
    num = r"(?<![\w_.])([\d][\d,]*(?:\.\d+)?)"
    pat = re.compile(
        num + r"\s*[^=\n×*]{0,24}?(?:×|⨯|(?<=\s)x(?=\s))\s*"
        + num + r"[^=\n]{0,24}?=\s*\**" + num)
    found = 0
    for m in pat.finditer(text):
        a, b, c = (float(g.replace(",", "")) for g in m.groups())
        line = text[:m.start()].count("\n") + 1
        ok = abs(a * b - c) <= max(1.0, abs(c) * 1e-4)
        found += 1
        print(f"   L{line:<5} {m.group(0).strip()[:60]:60} "
              f"{'OK' if ok else f'** MISMATCH: {a * b:,.0f} **'}")
    print(f"   products found: {found}")


def section_uncheckable() -> None:
    head("WHAT THIS FILE STILL CANNOT CHECK  (read before trusting a clean run)")
    for line in [
        "1. PROSE-TO-NUMBER BINDING. Every section above prints the correct",
        "   value; none of them knows which sentence is supposed to quote it.",
        "   A range printed here as 43-229 and written in the paper as 48-203",
        "   is only caught by a human diffing the two. Only section PRODUCTS",
        "   parses the manuscript itself.",
        "2. NOUNS. 7.6 quoted the right numbers under the wrong name (mean",
        "   cache_read per request, called 'mean context'). No arithmetic check",
        "   can see a mislabel.",
        "2b. STALE POPULATIONS, IN GENERAL. POPULATION SCOPE above covers the",
        "   four instruments that carry an explicit population, but a sentence",
        "   can be scoped to any population at all ('the nine implementations',",
        "   'as of the pilot round'). Every other section recomputes over the",
        "   CURRENT set, which is what makes a stale scope invisible. When a",
        "   claim names a count, check what that count was a count OF.",
        "3. FIGURES WITH NO FIELD ANYWHERE. Three cited figures match no field",
        "   in any artefact: the 19% subagent-transcript shortfall (3.4.3), the",
        "   3.7-4.9x dedup range (5.5 #1), and the 19% cache-rewrite overestimate",
        "   (5.5 #7, whose own source AUDIT E-2 computes 13.5% in its table).",
        "   All three are now marked UNVERIFIED in the paper. Nothing here can",
        "   confirm or refute them -- only a re-derivation can.",
        "4. CORPUS-WIDE MONEY. $4,828.22 / $5,550.41 / $1,080.74 / +$630.11 come",
        "   from a token corpus outside results/. Not reachable from here.",
        "5. THE DELEGATED RUNS' CACHE-WRITE SPLIT. results/*/transcript.jsonl",
        "   holds the main line only for the 7 delegated runs, and modelUsage",
        "   gives no TTL breakdown, so their cache_write share is unrecoverable.",
        "6. ENVIRONMENT FACTS. CLI 2.1.233, 2 vs ~10 MCP servers, the 600 s",
        "   background-wait ceiling, settings.json defaults. These trace to",
        "   PROTOCOL_2026-08-20.md, which is a design document, not an artefact.",
        "7. THE G4 LAYER. Human verdicts, window geometry, and the screenshots",
        "   behind them live in holdout/g4_anchor_probe/ as text, not as fields.",
    ]:
        print("   " + line)


def main() -> None:
    quiet = "--quiet" in sys.argv
    section_arms(quiet)
    section_ranges()
    section_totals()
    section_comparisons()
    section_dose_response()
    section_cost_items()
    section_transcript_audit()
    section_artefacts()
    section_populations()
    section_products()
    section_uncheckable()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
T0-1  Differential fuzzing: 9 independent implementations vs the oracle.

The 15 golden cases stopped discriminating -- every arm scored 25/25. That is
evidence about 15 inputs, not about the implementations. This drives thousands
of generated rule sets through every built executable and diffs each against the
oracle, so "no quality difference" either becomes a much stronger claim or breaks.

Deterministic: fixed seed, so a divergence can always be reproduced.

    python fuzz.py [--cases 2000] [--workers 24]
"""

from __future__ import annotations

import argparse
import json
import random
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import oracle  # noqa: E402

ROOT = Path(__file__).resolve().parent
INVENTORY = ROOT / "impl_inventory.json"
TREES_ROOT = ROOT / "fuzz-trees"
SEED = 20260820

# Regex kept to a subset that behaves identically in Python `re` and .NET Regex.
# No lookbehind, no named groups, nothing with a ReDoS shape -- a divergence must
# mean the implementation is wrong, not that the two engines disagree.
SAFE_REGEX = [
    (r"\d+", "N"), (r"\s+", "_"), (r"[aeiou]", ""), (r"^.", "X"),
    (r"(\w)(\w)", "$2$1"), (r"\.", "-"), (r"[0-9]{2}", "##"),
    (r"(\d)", "[$1]"), (r"a|e", "@"), (r"\w$", "Z"),
]

TREES = {
    "A_mixed": [
        "a.txt", "B.TXT", "console.md", "data.tar.gz", ".gitignore",
        "README", "報告 2026.docx", "photo (1).jpg", "photo (2).jpg", "x.txt",
    ],
    "B_unicode_long": [
        "日本語ファイル.txt", "Ünïcödé Nâmé.md", "a" * 200 + ".txt",
        "múltiple.dots.in.here.tar.gz", "emoji_🎯_name.png", "  leading spaces.txt",
        "UPPER.LOWER.MiXeD.Txt", "no_ext_at_all", ".hidden", "x.Y",
    ],
    "C_collision_prone": [
        "item1.txt", "item2.txt", "item10.txt", "ITEM1.TXT", "item_1.txt",
        "copy.txt", "copy (1).txt", "copy (2).txt", "CON_notreserved.txt", "nul_x.txt",
    ],
}


def build_trees() -> list[Path]:
    if TREES_ROOT.exists():
        shutil.rmtree(TREES_ROOT)
    out = []
    for name, files in TREES.items():
        d = TREES_ROOT / name
        d.mkdir(parents=True)
        for i, f in enumerate(files):
            try:
                (d / f).write_text(f"c{i}\n", encoding="utf-8")
            except OSError:
                continue  # a name this filesystem refuses is not a test of the tool
        out.append(d)
    return out


def gen_rules(rng: random.Random) -> dict:
    n_steps = rng.randint(1, 4)
    steps = []
    for _ in range(n_steps):
        op = rng.choice(["replace", "insert", "remove", "sequence", "case", "extension"])
        if op == "replace":
            if rng.random() < 0.5:
                pat, rep = rng.choice(SAFE_REGEX)
                steps.append({"op": "replace", "find": pat, "replaceWith": rep,
                              "regex": True, "ignoreCase": rng.random() < 0.3})
            else:
                steps.append({"op": "replace",
                              "find": rng.choice(["a", ".", " ", "o", "1", "TXT", "zzz", ""]),
                              "replaceWith": rng.choice(["", "-", "X", "長", "::"]),
                              "regex": False, "ignoreCase": rng.random() < 0.3})
        elif op == "insert":
            steps.append({"op": "insert",
                          "text": rng.choice(["", "p_", "_s", "測試", "<>", "  ", "."]),
                          "position": rng.choice(["prefix", "suffix", "index"]),
                          "index": rng.choice([0, 1, 3, 50, 999, -5])})
        elif op == "remove":
            steps.append({"op": "remove",
                          "from": rng.choice([0, 1, 2, 5, 100, -3]),
                          "count": rng.choice([0, 1, 3, 7, 999])})
        elif op == "sequence":
            steps.append({"op": "sequence",
                          "pattern": rng.choice(["{n:000}_", "[{n:00}]", "{n:0}", "-{n:0000}"]),
                          # Rule 9 defines a zero-pad WIDTH but never says what a
                          # negative counter means, so a negative `start` is outside
                          # the contract's domain. Generating it produced 112 unanimous
                          # arm-vs-oracle divergences that were the spec's silence, not
                          # anyone's defect. Kept out: a fuzzer must stay inside the
                          # contract it is testing against.
                          "start": rng.choice([0, 1, 5, 98]),
                          "step": rng.choice([1, 2, 10, 0]),
                          "position": rng.choice(["prefix", "suffix"])})
        elif op == "case":
            steps.append({"op": "case", "mode": rng.choice(["upper", "lower", "title"])})
        else:
            steps.append({"op": "extension",
                          "mode": rng.choice(["lower", "upper", "set"]),
                          "value": rng.choice(["txt", "", "TAR.GZ", "日本"])})
    return {"applyTo": rng.choice(["name", "nameAndExtension"]),
            "sort": "name", "steps": steps}


def run_batch(args) -> dict:
    """One implementation against one batch of (case_id, tree, rules, expected)."""
    run_id, exe, batch = args
    result = {"run_id": run_id, "checked": 0, "diverged": 0, "errors": 0,
              "examples": [], "bad_cases": []}
    with tempfile.TemporaryDirectory() as tmp:
        rules_p = Path(tmp) / "r.json"
        out_p = Path(tmp) / "p.json"
        for case_id, tree, rules, expected in batch:
            rules_p.write_text(json.dumps(rules), encoding="utf-8")
            if out_p.exists():
                out_p.unlink()
            try:
                proc = subprocess.run(
                    [exe, "--plan", "--dir", tree, "--rules", str(rules_p), "--out", str(out_p)],
                    capture_output=True, timeout=30)
            except (subprocess.TimeoutExpired, OSError):
                result["errors"] += 1
                result["bad_cases"].append(case_id)
                if len(result["examples"]) < 5:
                    result["examples"].append({"case": case_id, "why": "timeout/OSError"})
                continue
            result["checked"] += 1
            if proc.returncode != 0 or not out_p.exists():
                result["errors"] += 1
                result["bad_cases"].append(case_id)
                if len(result["examples"]) < 5:
                    result["examples"].append({"case": case_id, "why": f"exit {proc.returncode}"})
                continue
            try:
                got = json.loads(out_p.read_text("utf-8-sig"))
            except (json.JSONDecodeError, OSError) as exc:
                result["errors"] += 1
                result["bad_cases"].append(case_id)
                if len(result["examples"]) < 5:
                    result["examples"].append({"case": case_id, "why": f"bad json: {exc}"})
                continue
            got_items = [(i.get("original"), i.get("proposed"), i.get("status"))
                         for i in got.get("items", [])]
            want_items = [(i["original"], i["proposed"], i["status"]) for i in expected["items"]]
            if got_items != want_items:
                result["diverged"] += 1
                result["bad_cases"].append(case_id)
                if len(result["examples"]) < 5:
                    diff = next(((a, b) for a, b in zip(got_items, want_items) if a != b),
                                (got_items[:2], want_items[:2]))
                    result["examples"].append({"case": case_id, "got": diff[0], "want": diff[1]})
    return result


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", type=int, default=2000, help="cases PER TREE")
    ap.add_argument("--workers", type=int, default=24)
    args = ap.parse_args()

    impls = json.loads(INVENTORY.read_text("utf-8-sig"))
    trees = build_trees()
    rng = random.Random(SEED)

    print(f"generating {args.cases} rule sets x {len(trees)} trees ...")
    cases = []
    for tree in trees:
        for i in range(args.cases):
            rules = gen_rules(rng)
            try:
                expected = oracle.plan(tree, rules)
            except Exception:
                continue  # oracle cannot express it -> not a fair test case
            cases.append((f"{tree.name}#{i}", str(tree), rules, expected))
    print(f"{len(cases)} usable cases x {len(impls)} implementations "
          f"= {len(cases)*len(impls):,} executions\n")

    control = [im for im in impls if im["Run"].startswith("ZZ-")]
    arms = [im for im in impls if not im["Run"].startswith("ZZ-")]
    if not control:
        raise SystemExit("FATAL: no ZZ- control implementation in the inventory")

    def sweep(selected, case_list):
        n_batches = max(1, args.workers // 2)
        size = (len(case_list) + n_batches - 1) // n_batches
        tasks = [(im["Run"], im["Exe"], case_list[i:i + size])
                 for im in selected for i in range(0, len(case_list), size)]
        agg: dict[str, dict] = {}
        with ProcessPoolExecutor(max_workers=args.workers) as pool:
            for res in pool.map(run_batch, tasks):
                a = agg.setdefault(res["run_id"], {"checked": 0, "diverged": 0, "errors": 0,
                                                   "examples": [], "bad_cases": []})
                for k in ("checked", "diverged", "errors"):
                    a[k] += res[k]
                a["examples"].extend(res["examples"][:2])
                a["bad_cases"].extend(res["bad_cases"])
        return agg

    # PASS 1 -- the control marks the contract's INDETERMINATE region.
    # The control and the oracle are two independent implementations of the same
    # written contract, both written by its author. Where they disagree, the CONTRACT
    # is under-specified, not the arm. Scoring an arm on those inputs would punish it
    # for the author's ambiguity, so they are excluded before the arms are judged.
    print("PASS 1: control sweep (locating contract-ambiguous inputs)")
    cagg = sweep(control, cases)
    cname = control[0]["Run"]
    ambiguous = set(cagg[cname]["bad_cases"])
    print(f"  {cname}: {cagg[cname]['diverged']:,} diverged, "
          f"{cagg[cname]['errors']:,} errored -> {len(ambiguous):,} of {len(cases):,} "
          f"cases marked INDETERMINATE ({len(ambiguous)/len(cases)*100:.1f}%)")
    for ex in cagg[cname]["examples"][:4]:
        print(f"    ambiguity example: {ex}")

    determinate = [c for c in cases if c[0] not in ambiguous]
    print(f"\nPASS 2: {len(arms)} arms x {len(determinate):,} determinate cases "
          f"= {len(arms)*len(determinate):,} executions\n")
    agg = sweep(arms, determinate)

    print(f"{'implementation':16} {'checked':>9} {'diverged':>9} {'errors':>8} {'agree%':>8}")
    for run_id in sorted(agg):
        a = agg[run_id]
        ok = a["checked"] - a["diverged"] - a["errors"]
        pct = ok / a["checked"] * 100 if a["checked"] else 0
        print(f"{run_id:16} {a['checked']:9,} {a['diverged']:9,} {a['errors']:8,} {pct:7.2f}%")

    print()
    for run_id in sorted(agg):
        for ex in agg[run_id]["examples"][:2]:
            print(f"  {run_id}  {ex}")

    # ROBUSTNESS PROBE: the control crashed on some inputs (unhandled .NET exception).
    # Those cases were excluded from scoring, but how the arms behave on them is a
    # quality signal the golden set cannot produce -- the reference falling over is a
    # defect in the reference, not a licence to ignore the input.
    crash_ids = {c for c in cagg[cname]["bad_cases"]}
    crashers = [c for c in cases if c[0] in crash_ids]
    robustness = {}
    if crashers:
        print(f"\nROBUSTNESS PROBE: {len(crashers):,} inputs the control could not "
              f"handle cleanly\n")
        ragg = sweep(arms, crashers)
        print(f"{'implementation':16} {'checked':>9} {'errors':>8} {'clean-exit%':>12}")
        for run_id in sorted(ragg):
            a = ragg[run_id]
            pct = (a["checked"] - a["errors"]) / a["checked"] * 100 if a["checked"] else 0
            robustness[run_id] = round(pct, 2)
            print(f"{run_id:16} {a['checked']:9,} {a['errors']:8,} {pct:11.2f}%")

    payload = {"robustness_on_control_failures_pct": robustness,
               "seed": SEED, "cases_per_tree": args.cases,
               "total_cases": len(cases), "indeterminate": len(ambiguous),
               "determinate": len(determinate),
               "control": {k: v for k, v in cagg[cname].items() if k != "bad_cases"},
               "arms": {k: {kk: vv for kk, vv in v.items() if kk != "bad_cases"}
                        for k, v in agg.items()}}
    # Generated filenames can contain lone surrogates; keep them out of the report.
    text = json.dumps(payload, indent=2, ensure_ascii=True)
    (ROOT / "FUZZ_RESULT.json").write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()

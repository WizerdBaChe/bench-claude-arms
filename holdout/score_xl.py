#!/usr/bin/env python3
"""
Held-out scorer for the XL contract (14 ops + --explain trace).

    python score_xl.py <arm_project_dir> [--out result.json]

Gates: G0 build | G1 --plan contract | G2 plan correctness (20 golden cases +
determinism) | G3 --explain contract | G4 trace correctness | G5 deliverables.
GUI is NOT scored here (human UAT, see MANUAL_UAT.md).

Y4_xl uses a different denominator from the small-contract Y4. The two scores
are NOT comparable; only compare arms within the same contract.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TREE = ROOT / "xl-fixture-tree"
CASES = ROOT / "xl-cases"
EXP_PLAN = ROOT / "xl-expected-plan"
EXP_TRACE = ROOT / "xl-expected-trace"
BUILD_TIMEOUT = 900
RUN_TIMEOUT = 120


def tree_hash(folder: Path) -> str:
    return hashlib.sha256("\n".join(sorted(p.name for p in folder.iterdir()))
                          .encode("utf-8")).hexdigest()


def run(cmd: list[str], cwd: Path, timeout: int):
    try:
        p = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True,
                           timeout=timeout, encoding="utf-8", errors="replace")
        return p.returncode, p.stdout or "", p.stderr or ""
    except subprocess.TimeoutExpired:
        return -1, "", f"TIMEOUT after {timeout}s"
    except OSError as exc:
        return -2, "", f"OSError: {exc}"


def find_exe(arm: Path) -> Path | None:
    named = list(arm.rglob("bin/Release/**/BatchRenameStudio.exe"))
    if named:
        return named[0]
    others = [p for p in arm.rglob("bin/Release/**/*.exe")
              if p.name.lower() != "createdump.exe"]
    return others[0] if others else None


def cmp_plan(actual, expected) -> tuple[bool, str]:
    if not isinstance(actual, dict):
        return False, "not an object"
    a_items = actual.get("items")
    if not isinstance(a_items, list):
        return False, "items missing"
    e_items = expected["items"]
    if len(a_items) != len(e_items):
        return False, f"item count {len(a_items)} != {len(e_items)}"
    for i, (got, want) in enumerate(zip(a_items, e_items)):
        for k in ("original", "proposed", "status"):
            if str(got.get(k, "")) != want[k]:
                return False, (f"item[{i}].{k}: got {got.get(k)!r} want {want[k]!r} "
                               f"(original={want['original']!r})")
    a_sum = actual.get("summary") or {}
    for k, want in expected["summary"].items():
        if int(a_sum.get(k, -1)) != want:
            return False, f"summary.{k}: got {a_sum.get(k)} want {want}"
    return True, ""


def cmp_trace(actual, expected) -> tuple[bool, str]:
    if not isinstance(actual, dict):
        return False, "not an object"
    a_files = actual.get("files")
    if not isinstance(a_files, list):
        return False, "files missing"
    e_files = expected["files"]
    if len(a_files) != len(e_files):
        return False, f"file count {len(a_files)} != {len(e_files)}"
    for i, (got, want) in enumerate(zip(a_files, e_files)):
        for k in ("original", "proposed", "status"):
            if str(got.get(k, "")) != want[k]:
                return False, f"files[{i}].{k}: got {got.get(k)!r} want {want[k]!r}"
        gs, ws = got.get("steps") or [], want["steps"]
        if len(gs) != len(ws):
            return False, (f"files[{i}] ({want['original']!r}) step count "
                           f"{len(gs)} != {len(ws)}")
        for j, (g, w) in enumerate(zip(gs, ws)):
            for k in ("index", "op", "before", "after"):
                if str(g.get(k, "")) != str(w[k]):
                    return False, (f"files[{i}].steps[{j}].{k}: got {g.get(k)!r} "
                                   f"want {w[k]!r} (file={want['original']!r})")
    return True, ""


def _emit(result, out):
    text = json.dumps(result, indent=2, ensure_ascii=False)
    if out:
        Path(out).write_text(text + "\n", encoding="utf-8")
    print(text)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("arm")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    arm = Path(args.arm).resolve()
    result: dict = {"arm": str(arm), "contract": "XL"}

    code, out, err = run(["dotnet", "build", "-c", "Release", "--nologo"], arm, BUILD_TIMEOUT)
    result["G0"] = {"pass": code == 0, "exit": code,
                    "tail": (err or out).strip().splitlines()[-6:]}
    if code != 0:
        result["Y4_xl"] = 0.0
        result["note"] = "build failed"
        _emit(result, args.out)
        return 0

    exe = find_exe(arm)
    result["exe"] = str(exe) if exe else None
    if not exe:
        result["Y4_xl"] = 0.0
        result["note"] = "no executable under bin/Release"
        _emit(result, args.out)
        return 0

    names = sorted(p.stem for p in CASES.glob("*.json"))
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "xl-fixture-tree"
        shutil.copytree(TREE, work)
        before = tree_hash(work)

        g1 = {"exit_zero": False, "written": False, "stdout_single_line": False}
        g3 = {"exit_zero": False, "written": False, "stdout_single_line": False}
        plan_res, trace_res = {}, {}

        for idx, name in enumerate(names):
            rules = str(CASES / f"{name}.json")

            p_out = Path(tmp) / f"plan_{name}.json"
            code, sout, serr = run([str(exe), "--plan", "--dir", str(work),
                                    "--rules", rules, "--out", str(p_out)], arm, RUN_TIMEOUT)
            if idx == 0:
                g1.update(exit_zero=code == 0, written=p_out.exists(),
                          stdout_single_line=len([l for l in sout.strip().splitlines()
                                                  if l.strip()]) <= 1,
                          first_stderr=serr.strip()[:300])
            if not p_out.exists():
                plan_res[name] = {"pass": False, "why": f"no plan.json (exit {code})"}
            else:
                try:
                    got = json.loads(p_out.read_text("utf-8-sig"))
                    want = json.loads((EXP_PLAN / f"{name}.json").read_text("utf-8"))
                    ok, why = cmp_plan(got, want)
                    plan_res[name] = {"pass": ok, "why": why}
                except json.JSONDecodeError as exc:
                    plan_res[name] = {"pass": False, "why": f"invalid JSON: {exc}"}

            t_out = Path(tmp) / f"trace_{name}.json"
            code, sout, serr = run([str(exe), "--explain", "--dir", str(work),
                                    "--rules", rules, "--out", str(t_out)], arm, RUN_TIMEOUT)
            if idx == 0:
                g3.update(exit_zero=code == 0, written=t_out.exists(),
                          stdout_single_line=len([l for l in sout.strip().splitlines()
                                                  if l.strip()]) <= 1,
                          first_stderr=serr.strip()[:300])
            if not t_out.exists():
                trace_res[name] = {"pass": False, "why": f"no trace.json (exit {code})"}
            else:
                try:
                    got = json.loads(t_out.read_text("utf-8-sig"))
                    want = json.loads((EXP_TRACE / f"{name}.json").read_text("utf-8"))
                    ok, why = cmp_trace(got, want)
                    trace_res[name] = {"pass": ok, "why": why}
                except json.JSONDecodeError as exc:
                    trace_res[name] = {"pass": False, "why": f"invalid JSON: {exc}"}

        no_rename = tree_hash(work) == before
        g1["no_rename"] = no_rename
        g3["no_rename"] = no_rename

        det_a, det_b = Path(tmp) / "da.json", Path(tmp) / "db.json"
        for t in (det_a, det_b):
            run([str(exe), "--plan", "--dir", str(work),
                 "--rules", str(CASES / f"{names[0]}.json"), "--out", str(t)],
                arm, RUN_TIMEOUT)
        deterministic = (det_a.exists() and det_b.exists()
                         and det_a.read_bytes() == det_b.read_bytes())

    result["G1_plan_contract"] = {**g1, "pass_count": sum(
        1 for k in ("exit_zero", "written", "no_rename", "stdout_single_line") if g1[k]),
        "max": 4}
    result["G3_explain_contract"] = {**g3, "pass_count": sum(
        1 for k in ("exit_zero", "written", "no_rename", "stdout_single_line") if g3[k]),
        "max": 4}
    result["G2_plan_cases"] = {"cases": plan_res, "deterministic": deterministic,
                               "pass_count": sum(1 for v in plan_res.values() if v["pass"])
                               + int(deterministic), "max": len(names) + 1}
    result["G4_trace_cases"] = {"cases": trace_res,
                                "pass_count": sum(1 for v in trace_res.values() if v["pass"]),
                                "max": len(names)}

    checks = {
        "solution_builds": True,
        "plan_mode": g1["exit_zero"] and g1["written"],
        "explain_mode": g3["exit_zero"] and g3["written"],
        "gui_project_present": bool(list(arm.rglob("*.csproj"))),
        "decisions_doc": any(arm.rglob("docs/DECISIONS.md")),
        "readme": any(arm.rglob("README.md")),
    }
    result["G5_deliverables"] = {"checks": checks, "pass_count": sum(checks.values()),
                                 "max": 6}

    earned = sum(result[k]["pass_count"] for k in
                 ("G1_plan_contract", "G2_plan_cases", "G3_explain_contract",
                  "G4_trace_cases", "G5_deliverables"))
    total = sum(result[k]["max"] for k in
                ("G1_plan_contract", "G2_plan_cases", "G3_explain_contract",
                 "G4_trace_cases", "G5_deliverables"))
    result["Y4_xl"] = round(earned / total, 4)
    result["Y4_earned"] = earned
    result["Y4_total"] = total
    result["gui"] = "NOT SCORED — human UAT"
    _emit(result, args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""
Held-out scorer for one experiment arm.

    python score.py <arm_project_dir> [--out result.json]

Never modifies the arm's tree except by invoking `dotnet build`. Runs the arm's
executable against a fresh COPY of the fixture tree so that a tool which renames
despite --plan is detected rather than destroying the fixtures.

G0 build | G1 contract | G2 correctness (15 golden cases + determinism) | G3 deliverables
G4 (GUI) is NOT scored here -- it requires a human. See MANUAL_UAT.md.
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
TREE = ROOT / "fixture-tree"
CASES = ROOT / "cases"
EXPECTED = ROOT / "expected"
BUILD_TIMEOUT = 600
RUN_TIMEOUT = 120


def tree_hash(folder: Path) -> str:
    entries = sorted(p.name for p in folder.iterdir())
    return hashlib.sha256("\n".join(entries).encode("utf-8")).hexdigest()


def run(cmd: list[str], cwd: Path, timeout: int) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True,
                              timeout=timeout, encoding="utf-8", errors="replace")
        return proc.returncode, proc.stdout or "", proc.stderr or ""
    except subprocess.TimeoutExpired:
        return -1, "", f"TIMEOUT after {timeout}s"
    except OSError as exc:
        return -2, "", f"OSError: {exc}"


def find_exe(arm: Path) -> Path | None:
    named = list(arm.rglob("bin/Release/**/BatchRenameStudio.exe"))
    if named:
        return named[0]
    others = [p for p in arm.rglob("bin/Release/**/*.exe")
              if p.name.lower() not in {"createdump.exe"}]
    return others[0] if others else None


def compare_unordered(actual: dict, expected: dict) -> bool:
    """Order-insensitive secondary check.

    Y4 has a cliff: one ordering defect fails every case before the comparison
    reaches the interesting fields (measured on the seeded mutant: 14/15 cases
    failed on item order alone). This keyed comparison separates "wrong order
    only" from "wrong transform logic", so a single systemic bug is not read as
    total failure.
    """
    items = actual.get("items")
    if not isinstance(items, list):
        return False
    got = {str(i.get("original", "")): (str(i.get("proposed", "")), str(i.get("status", "")))
           for i in items if isinstance(i, dict)}
    want = {i["original"]: (i["proposed"], i["status"]) for i in expected["items"]}
    return got == want


def compare(actual: dict, expected: dict) -> tuple[bool, str]:
    if not isinstance(actual, dict):
        return False, "plan.json is not an object"
    a_items = actual.get("items")
    if not isinstance(a_items, list):
        return False, "items missing or not a list"
    e_items = expected["items"]
    if len(a_items) != len(e_items):
        return False, f"item count {len(a_items)} != expected {len(e_items)}"
    for i, (got, want) in enumerate(zip(a_items, e_items)):
        for key in ("original", "proposed", "status"):
            if str(got.get(key, "")) != want[key]:
                return False, (f"item[{i}].{key}: got {got.get(key)!r} "
                               f"want {want[key]!r} (original={want['original']!r})")
    a_sum = actual.get("summary") or {}
    for key, want in expected["summary"].items():
        if int(a_sum.get(key, -1)) != want:
            return False, f"summary.{key}: got {a_sum.get(key)} want {want}"
    return True, ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("arm")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    arm = Path(args.arm).resolve()

    result: dict = {"arm": str(arm), "G0": {}, "G1": {}, "G2": {}, "G3": {}}

    # ---- G0: build -------------------------------------------------------
    code, out, err = run(["dotnet", "build", "-c", "Release", "--nologo"], arm, BUILD_TIMEOUT)
    result["G0"] = {"pass": code == 0, "exit": code,
                    "tail": (err or out).strip().splitlines()[-6:]}
    if code != 0:
        result["Y4_score"] = 0.0
        result["note"] = "build failed -- G1/G2/G3 not scored (protocol S6.2)"
        _emit(result, args.out)
        return 0

    exe = find_exe(arm)
    result["G1"]["exe"] = str(exe) if exe else None
    if not exe:
        result["G1"]["pass_count"] = 0
        result["Y4_score"] = 0.0
        result["note"] = "no executable found under bin/Release"
        _emit(result, args.out)
        return 0

    # ---- G1 + G2: contract and correctness, against a COPY of the tree ----
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "fixture-tree"
        shutil.copytree(TREE, work)
        before = tree_hash(work)

        g1 = {"exit_zero": False, "plan_written": False, "no_rename": False,
              "stdout_single_line": False}
        case_results: dict[str, dict] = {}
        case_names = sorted(p.stem for p in CASES.glob("*.json"))

        for idx, name in enumerate(case_names):
            out_path = Path(tmp) / f"plan_{name}.json"
            code, sout, serr = run(
                [str(exe), "--plan", "--dir", str(work),
                 "--rules", str(CASES / f"{name}.json"), "--out", str(out_path)],
                arm, RUN_TIMEOUT)
            if idx == 0:
                g1["exit_zero"] = code == 0
                g1["plan_written"] = out_path.exists()
                g1["stdout_single_line"] = len(
                    [ln for ln in sout.strip().splitlines() if ln.strip()]) <= 1
                g1["first_stderr"] = serr.strip()[:400]
            if not out_path.exists():
                case_results[name] = {"pass": False, "why": f"no plan.json (exit {code})"}
                continue
            try:
                actual = json.loads(out_path.read_text("utf-8-sig"))
            except json.JSONDecodeError as exc:
                case_results[name] = {"pass": False, "why": f"invalid JSON: {exc}"}
                continue
            want = json.loads((EXPECTED / f"{name}.json").read_text("utf-8"))
            ok, why = compare(actual, want)
            case_results[name] = {"pass": ok, "why": why,
                                  "unordered_pass": compare_unordered(actual, want)}

        g1["no_rename"] = tree_hash(work) == before

        # Determinism: re-run the first case, require byte-identical output.
        det_a = Path(tmp) / "det_a.json"
        det_b = Path(tmp) / "det_b.json"
        first = case_names[0]
        for target in (det_a, det_b):
            run([str(exe), "--plan", "--dir", str(work),
                 "--rules", str(CASES / f"{first}.json"), "--out", str(target)],
                arm, RUN_TIMEOUT)
        deterministic = (det_a.exists() and det_b.exists()
                         and det_a.read_bytes() == det_b.read_bytes())

    result["G1"].update(g1)
    result["G1"]["pass_count"] = sum(
        1 for k in ("exit_zero", "plan_written", "no_rename", "stdout_single_line") if g1[k])
    result["G1"]["max"] = 4

    passed = sum(1 for v in case_results.values() if v["pass"])
    unordered = sum(1 for v in case_results.values() if v.get("unordered_pass"))
    result["G2"] = {"cases": case_results, "pass_count": passed + int(deterministic),
                    "max": len(case_names) + 1, "deterministic": deterministic,
                    "unordered_pass_count": unordered, "unordered_max": len(case_names)}

    # ---- G3: deliverables ------------------------------------------------
    checks = {
        "solution_builds": True,
        "headless_mode": g1["exit_zero"] and g1["plan_written"],
        "gui_project_present": bool(list(arm.rglob("*.csproj"))),
        "decisions_doc": any(arm.rglob("docs/DECISIONS.md")),
        "readme": any(arm.rglob("README.md")),
    }
    result["G3"] = {"checks": checks, "pass_count": sum(checks.values()), "max": 5}

    earned = (result["G1"]["pass_count"] + result["G2"]["pass_count"]
              + result["G3"]["pass_count"])
    total = result["G1"]["max"] + result["G2"]["max"] + result["G3"]["max"]
    result["Y4_score"] = round(earned / total, 4)
    result["Y4_earned"] = earned
    result["Y4_total"] = total
    result["G4_gui"] = "NOT SCORED -- requires human UAT, see MANUAL_UAT.md"

    _emit(result, args.out)
    return 0


def _emit(result: dict, out: str | None) -> None:
    text = json.dumps(result, indent=2, ensure_ascii=False)
    if out:
        Path(out).write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    raise SystemExit(main())

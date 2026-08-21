#!/usr/bin/env python3
"""
T0-2  Mutation testing of the held-out scorer.

Right now the strongest claim available about the scorer is "it caught the two
defects I happened to seed". That is an anecdote. This injects a systematic
population of single-point semantic defects into the reference implementation,
scores each mutant with the SAME held-out scorer the arms were judged by, and
reports a detection rate -- a number that can be defended, plus a map of the
blind spots.

A mutant that fails to compile is not a semantic defect and is discarded.
A mutant that no test distinguishes ("survivor") marks a gap in the suite.

    python mutate.py [--workers 8]
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REFIMPL = ROOT / "refimpl"
SCORER = ROOT / "score.py"
PYTHON = sys.executable

# (label, pattern, replacement) -- applied ONE OCCURRENCE AT A TIME so each mutant
# carries exactly one defect and detection can be attributed.
OPERATORS = [
    ("cmp_gt_to_ge", r"dot > 0", "dot >= 0"),
    ("cmp_ge_to_gt", r"ext\.Length > 0", "ext.Length >= 0"),
    ("len_gt_to_ge", r"proposed\.Length > 255", "proposed.Length >= 255"),
    ("len_boundary", r"proposed\.Length > 255", "proposed.Length > 256"),
    ("ctrl_char", r"c < 0x20", "c < 0x1F"),
    ("ordinal_to_ic", r"StringComparer\.Ordinal", "StringComparer.OrdinalIgnoreCase"),
    ("ic_to_ordinal", r"StringComparison\.OrdinalIgnoreCase", "StringComparison.Ordinal"),
    ("hashset_cmp", r"StringComparer\.OrdinalIgnoreCase", "StringComparer.Ordinal"),
    ("collision_count", r"counts\.GetValueOrDefault\(proposed\) > 1",
     "counts.GetValueOrDefault(proposed) > 2"),
    ("seq_index_off", r"start \+ i \* stepBy", "start + (i + 1) * stepBy"),
    ("seq_step_drop", r"start \+ i \* stepBy", "start"),
    ("clamp_from", r"Math\.Clamp\(s\[\"from\"\]\?\.GetValue<int>\(\) \?\? 0, 0, target\.Length\)",
     "s[\"from\"]?.GetValue<int>() ?? 0"),
    ("insert_prefix_suffix", r'if \(pos == "prefix"\) target = text \+ target;',
     'if (pos == "prefix") target = target + text;'),
    ("unchanged_before_collision", r'return string\.Equals\(proposed, original, StringComparison\.Ordinal\) \? "unchanged" : "ok";',
     'return "ok";'),
    ("drop_reserved", r"\|\| Reserved\.Contains\(b\)", ""),
    ("drop_illegal", r"\|\| proposed\.IndexOfAny\(Illegal\) >= 0", ""),
    ("drop_empty", r"proposed\.Length == 0\s*\n\s*\|\|", "false ||"),
    ("title_case_all", r"sb\.Append\(inRun \? char\.ToLowerInvariant\(ch\) : char\.ToUpperInvariant\(ch\)\);",
     "sb.Append(char.ToUpperInvariant(ch));"),
    ("upper_lower_swap", r'"upper" => target\.ToUpperInvariant\(\)', '"upper" => target.ToLowerInvariant()'),
    ("ext_lower_upper", r'"lower" => ext\.ToLowerInvariant\(\)', '"lower" => ext.ToUpperInvariant()'),
    ("sort_reverse", r"files\.OrderBy\(f => f\.Name, StringComparer\.Ordinal\)",
     "files.OrderByDescending(f => f.Name, StringComparer.Ordinal)"),
    ("dirs_included", r"new DirectoryInfo\(dir\)\.GetFiles\(\)",
     "new DirectoryInfo(dir).GetFileSystemInfos().OfType<FileInfo>().ToArray()"),
    ("regex_first_only", r"Regex\.Replace\(target, find, repl,", "ReplaceFirst(target, find, repl,"),
    ("summary_total", r"plan\.Summary\.Total\+\+;", ""),
    ("schema_version", r"SchemaVersion \{ get; set; \} = 1;", "SchemaVersion { get; set; } = 2;"),
]


def make_mutants(src: str) -> list[tuple[str, str]]:
    out = []
    for label, pat, rep in OPERATORS:
        for m in re.finditer(pat, src):
            mutated = src[:m.start()] + re.sub(pat, rep, m.group(0), count=1) + src[m.end():]
            if mutated != src:
                out.append((f"{label}@{m.start()}", mutated))
            break  # one mutant per operator: first occurrence only
    return out


def evaluate(job) -> dict:
    name, mutated_src = job
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "impl"
        shutil.copytree(REFIMPL, work, ignore=shutil.ignore_patterns("bin", "obj"))
        (work / "Program.cs").write_text(mutated_src, encoding="utf-8")
        build = subprocess.run(["dotnet", "build", "-c", "Release", "--nologo"],
                               cwd=str(work), capture_output=True, text=True,
                               timeout=600, encoding="utf-8", errors="replace")
        if build.returncode != 0:
            return {"mutant": name, "status": "did_not_compile"}
        try:
            proc = subprocess.run([PYTHON, str(SCORER), str(work)],
                                  capture_output=True, text=True, timeout=900,
                                  encoding="utf-8", errors="replace")
            data = json.loads(proc.stdout)
        except Exception as exc:  # noqa: BLE001
            return {"mutant": name, "status": "scorer_error", "why": str(exc)[:200]}
        score = data.get("Y4_score", 0.0)
        return {"mutant": name,
                "status": "KILLED" if score < 1.0 else "SURVIVED",
                "Y4": score,
                "G2": f"{data.get('G2', {}).get('pass_count')}/{data.get('G2', {}).get('max')}"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()

    src = (REFIMPL / "Program.cs").read_text(encoding="utf-8")
    mutants = make_mutants(src)
    print(f"generated {len(mutants)} single-defect mutants from "
          f"{len(OPERATORS)} operators\n")

    results = []
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        for r in pool.map(evaluate, mutants):
            results.append(r)
            print(f"  {r['mutant']:34} {r['status']:16} "
                  f"{r.get('G2', '')} {r.get('Y4', '')}")

    viable = [r for r in results if r["status"] in ("KILLED", "SURVIVED")]
    killed = [r for r in viable if r["status"] == "KILLED"]
    survived = [r for r in viable if r["status"] == "SURVIVED"]
    rate = len(killed) / len(viable) * 100 if viable else 0.0

    print(f"\n{'='*60}")
    print(f"viable (compiled) mutants : {len(viable)}")
    print(f"killed by the held-out suite: {len(killed)}")
    print(f"SURVIVED (suite blind spot) : {len(survived)}")
    print(f"DETECTION RATE              : {rate:.1f}%")
    if survived:
        print("\nblind spots -- defects the 15 golden cases cannot see:")
        for r in survived:
            print(f"  - {r['mutant']}")

    (ROOT / "MUTATION_RESULT.json").write_text(
        json.dumps({"detection_rate_pct": round(rate, 1),
                    "viable": len(viable), "killed": len(killed),
                    "survived": [r["mutant"] for r in survived],
                    "results": results}, indent=2),
        encoding="utf-8")


if __name__ == "__main__":
    main()

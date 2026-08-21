#!/usr/bin/env python3
"""
Held-out validation set for the XL contract: fixture tree, rule cases, golden
expectations for BOTH --plan and --explain, and the delegated prompt variant.

Run once, before any XL arm executes.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import oracle_xl

ROOT = Path(__file__).resolve().parent
BENCH = ROOT.parent
TREE = ROOT / "xl-fixture-tree"
CASES = ROOT / "xl-cases"
EXP_PLAN = ROOT / "xl-expected-plan"
EXP_TRACE = ROOT / "xl-expected-trace"

FILES = [
    "a.txt", "B.TXT", "console.md", "data.tar.gz", ".gitignore", "README",
    "報告 2026.docx", "photo (1).jpg", "photo (2).jpg", "x.txt",
    "IMG_0042.jpeg", "  spaced  name  .md", "aabbcc.txt", "Hello-World_v2.TXT",
]

CASES_DEF: dict[str, dict] = {
    # --- carried-over ops, re-checked under the XL contract -------------------
    "x01_sequence_own_params": {
        "applyTo": "name", "sort": "name",
        "steps": [{"op": "sequence", "pattern": "{n:00}", "start": 1, "step": 1,
                   "position": "prefix"},
                  {"op": "sequence", "pattern": "-{n:000}", "start": 5, "step": 10,
                   "position": "suffix"}],
    },
    "x02_empty_find_is_noop": {
        "applyTo": "name", "sort": "name",
        "steps": [{"op": "replace", "find": "", "replaceWith": "ZZ",
                   "regex": False, "ignoreCase": False}],
    },
    "x03_nameext_extension_inorder": {
        "applyTo": "nameAndExtension", "sort": "name",
        "steps": [{"op": "case", "mode": "lower"},
                  {"op": "extension", "mode": "upper", "value": ""},
                  {"op": "case", "mode": "title"}],
    },
    # --- new ops --------------------------------------------------------------
    "x04_pad_left": {
        "applyTo": "name", "sort": "name",
        "steps": [{"op": "pad", "length": 12, "fill": "_", "side": "left"}],
    },
    "x05_pad_bad_fill_noop": {
        "applyTo": "name", "sort": "name",
        "steps": [{"op": "pad", "length": 12, "fill": "ab", "side": "right"}],
    },
    "x06_trim_both": {
        "applyTo": "name", "sort": "name",
        "steps": [{"op": "trim", "chars": " _-", "side": "both"}],
    },
    "x07_trim_left_only": {
        "applyTo": "name", "sort": "name",
        "steps": [{"op": "trim", "chars": " ", "side": "left"}],
    },
    "x08_slug": {
        "applyTo": "name", "sort": "name",
        "steps": [{"op": "slug", "separator": "-"}],
    },
    "x09_slug_empty_sep": {
        "applyTo": "name", "sort": "name",
        "steps": [{"op": "slug", "separator": ""}],
    },
    "x10_translate_delete_tail": {
        "applyTo": "name", "sort": "name",
        "steps": [{"op": "translate", "from": "aeiou", "to": "12"}],
    },
    "x11_translate_dup_first_wins": {
        "applyTo": "name", "sort": "name",
        "steps": [{"op": "translate", "from": "aab", "to": "XYZ"}],
    },
    "x12_numberformat": {
        "applyTo": "name", "sort": "name",
        "steps": [{"op": "numberFormat", "width": 6}],
    },
    "x13_extract_group": {
        "applyTo": "name", "sort": "name",
        "steps": [{"op": "extract", "pattern": r"([a-zA-Z]+)", "group": 1}],
    },
    "x14_extract_nomatch_empty": {
        "applyTo": "name", "sort": "name",
        "steps": [{"op": "extract", "pattern": r"ZZZZ", "group": 0}],
    },
    "x15_template": {
        "applyTo": "name", "sort": "name",
        "steps": [{"op": "template", "format": "{n:0000}_{name}_{len}.{ext}"}],
    },
    "x16_template_unknown_token": {
        "applyTo": "name", "sort": "name",
        "steps": [{"op": "template", "format": "{name}-{nope}-{n:00}"}],
    },
    "x17_dedupe_chars": {
        "applyTo": "name", "sort": "name",
        "steps": [{"op": "dedupeChars"}],
    },
    # --- composition ----------------------------------------------------------
    "x18_chain_slug_pad_seq": {
        "applyTo": "name", "sort": "name",
        "steps": [{"op": "slug", "separator": "-"},
                  {"op": "pad", "length": 16, "fill": "0", "side": "left"},
                  {"op": "sequence", "pattern": "_{n:000}", "start": 0, "step": 3,
                   "position": "suffix"}],
    },
    "x19_chain_extract_template": {
        "applyTo": "name", "sort": "name",
        "steps": [{"op": "extract", "pattern": r"[0-9]+", "group": 0},
                  {"op": "template", "format": "N{name}-{ext}"}],
    },
    "x20_collision_via_extract": {
        "applyTo": "name", "sort": "name",
        "steps": [{"op": "extract", "pattern": r"photo", "group": 0}],
    },
}


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


DIRECTIVE_A = (
    "ARCHITECTURE DIRECTIVE: Do all of this yourself in this session. Do not\n"
    "delegate any part of it to a subagent.\n"
)
DIRECTIVE_B = (
    "ARCHITECTURE DIRECTIVE: You are the lead. Your own hands produce only the\n"
    "design and the acceptance: a detailed work card per implementation chunk,\n"
    "and the verification of what comes back. All implementation -- writing\n"
    "source files, building, fixing build errors -- is delegated to subagents.\n"
    "Use whatever subagent types this environment provides; choose them as you\n"
    "see fit. Do not write implementation source files yourself.\n"
)


def main() -> None:
    if TREE.exists():
        shutil.rmtree(TREE)
    TREE.mkdir(parents=True)
    for i, name in enumerate(FILES):
        try:
            (TREE / name).write_text(f"xl fixture {i}\n", encoding="utf-8")
        except OSError:
            continue
    (TREE / "subdir").mkdir()
    (TREE / "subdir" / "ignored.txt").write_text("must not appear\n", encoding="utf-8")

    for d in (CASES, EXP_PLAN, EXP_TRACE):
        d.mkdir(exist_ok=True)
    for name, rules in CASES_DEF.items():
        (CASES / f"{name}.json").write_text(
            json.dumps(rules, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        (EXP_PLAN / f"{name}.json").write_text(
            json.dumps(oracle_xl.plan(TREE, rules), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8")
        (EXP_TRACE / f"{name}.json").write_text(
            json.dumps(oracle_xl.explain(TREE, rules), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8")

    a = BENCH / "fixtures" / "TASK_PROMPT_XL_A.md"
    b = BENCH / "fixtures" / "TASK_PROMPT_XL_B.md"
    text = a.read_text(encoding="utf-8")
    if DIRECTIVE_A not in text:
        raise SystemExit("FATAL: directive A block not found verbatim")
    b.write_text(text.replace(DIRECTIVE_A, DIRECTIVE_B), encoding="utf-8")

    manifest = {
        "fixture_files": FILES,
        "cases": sorted(CASES_DEF),
        "prompt_xl_a_sha256": sha256(a),
        "prompt_xl_b_sha256": sha256(b),
        "oracle_xl_sha256": sha256(ROOT / "oracle_xl.py"),
    }
    (ROOT / "MANIFEST_XL.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

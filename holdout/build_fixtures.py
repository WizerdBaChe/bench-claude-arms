#!/usr/bin/env python3
"""
Builds the held-out validation set: fixture tree, rule cases, golden expectations.
Also derives TASK_PROMPT_B.md from TASK_PROMPT_A.md so the two differ ONLY in the
ARCHITECTURE DIRECTIVE paragraph, and records SHA-256 of both.

Run once, before any experiment arm executes. Re-running is idempotent.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import oracle

ROOT = Path(__file__).resolve().parent
BENCH = ROOT.parent
TREE = ROOT / "fixture-tree"
CASES = ROOT / "cases"
EXPECTED = ROOT / "expected"

# Files chosen to exercise: multi-dot extensions, dotfiles, no-extension, unicode,
# spaces, parentheses, reserved device names, and case-insensitive collisions.
FILES = [
    "a.txt",
    "B.TXT",
    "console.md",
    "data.tar.gz",
    ".gitignore",
    "README",
    "報告 2026.docx",
    "photo (1).jpg",
    "photo (2).jpg",
    "x.txt",
]

CASES_DEF: dict[str, dict] = {
    "01_sequence_prefix": {
        "applyTo": "name", "sort": "name",
        "steps": [{"op": "sequence", "pattern": "{n:000}_", "start": 1, "step": 1,
                   "position": "prefix"}],
    },
    "02_sequence_step_start": {
        "applyTo": "name", "sort": "name",
        "steps": [{"op": "sequence", "pattern": "[{n:00}]", "start": 5, "step": 10,
                   "position": "suffix"}],
    },
    "03_case_lower_and_ext_lower": {
        "applyTo": "name", "sort": "name",
        "steps": [{"op": "case", "mode": "lower"},
                  {"op": "extension", "mode": "lower"}],
    },
    "04_case_title": {
        "applyTo": "name", "sort": "name",
        "steps": [{"op": "case", "mode": "title"}],
    },
    "05_regex_collision": {
        "applyTo": "name", "sort": "name",
        "steps": [{"op": "replace", "find": r"\s*\(\d+\)", "replaceWith": "",
                   "regex": True, "ignoreCase": False}],
    },
    "06_regex_group_ref": {
        "applyTo": "name", "sort": "name",
        "steps": [{"op": "replace", "find": r"^(\w)", "replaceWith": "$1$1",
                   "regex": True, "ignoreCase": False}],
    },
    "07_remove_clamp": {
        "applyTo": "name", "sort": "name",
        "steps": [{"op": "remove", "from": 0, "count": 3}],
    },
    "08_remove_overrun_invalid": {
        "applyTo": "name", "sort": "name",
        "steps": [{"op": "remove", "from": 0, "count": 999}],
    },
    "09_insert_index": {
        "applyTo": "name", "sort": "name",
        "steps": [{"op": "insert", "text": "--", "position": "index", "index": 2}],
    },
    "10_illegal_char_invalid": {
        "applyTo": "name", "sort": "name",
        "steps": [{"op": "insert", "text": ":", "position": "suffix"}],
    },
    "11_extension_set": {
        "applyTo": "name", "sort": "name",
        "steps": [{"op": "extension", "mode": "set", "value": "txt"}],
    },
    "12_name_and_extension": {
        "applyTo": "nameAndExtension", "sort": "name",
        "steps": [{"op": "case", "mode": "upper"}],
    },
    "13_step_order_matters": {
        "applyTo": "name", "sort": "name",
        "steps": [{"op": "insert", "text": "zz", "position": "prefix"},
                  {"op": "case", "mode": "upper"},
                  {"op": "remove", "from": 0, "count": 1}],
    },
    "14_literal_replace_ignorecase": {
        "applyTo": "name", "sort": "name",
        "steps": [{"op": "replace", "find": "PHOTO", "replaceWith": "img",
                   "regex": False, "ignoreCase": True}],
    },
    # "console" -> "con" (reserved device name); short names exercise clamping.
    "15_reserved_device_name": {
        "applyTo": "name", "sort": "name",
        "steps": [{"op": "remove", "from": 3, "count": 999}],
    },
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_tree() -> None:
    if TREE.exists():
        shutil.rmtree(TREE)
    TREE.mkdir(parents=True)
    for i, name in enumerate(FILES):
        (TREE / name).write_text(f"fixture content {i}\n", encoding="utf-8")
    # A directory that MUST be excluded from every plan (contract rule 1).
    (TREE / "subdir").mkdir()
    (TREE / "subdir" / "ignored.txt").write_text("must not appear\n", encoding="utf-8")


def build_cases() -> None:
    CASES.mkdir(exist_ok=True)
    EXPECTED.mkdir(exist_ok=True)
    for name, rules in CASES_DEF.items():
        (CASES / f"{name}.json").write_text(
            json.dumps(rules, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        expected = oracle.plan(TREE, rules)
        (EXPECTED / f"{name}.json").write_text(
            json.dumps(expected, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )


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


def build_prompt_b() -> None:
    a_path = BENCH / "fixtures" / "TASK_PROMPT_A.md"
    b_path = BENCH / "fixtures" / "TASK_PROMPT_B.md"
    text = a_path.read_text(encoding="utf-8")
    if DIRECTIVE_A not in text:
        raise SystemExit("FATAL: directive A block not found verbatim in TASK_PROMPT_A.md")
    b_path.write_text(text.replace(DIRECTIVE_A, DIRECTIVE_B), encoding="utf-8")


def main() -> None:
    build_tree()
    build_cases()
    build_prompt_b()
    manifest = {
        "fixture_files": FILES,
        "cases": sorted(CASES_DEF),
        "prompt_a_sha256": sha256(BENCH / "fixtures" / "TASK_PROMPT_A.md"),
        "prompt_b_sha256": sha256(BENCH / "fixtures" / "TASK_PROMPT_B.md"),
        "oracle_sha256": sha256(ROOT / "oracle.py"),
    }
    (ROOT / "MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

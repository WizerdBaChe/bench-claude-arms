#!/usr/bin/env python3
"""
Reference implementation ("test oracle") of the Batch Rename Studio contract
defined in fixtures/TASK_PROMPT_A.md, rules 1-15.

This file generates the golden expectations. It is the operational definition
of the written contract -- if this file and the prompt disagree, the PROMPT is
authoritative and this file is the bug.

MUST NOT be readable by any experiment arm (held-out validation set).
"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

RESERVED = {"CON", "PRN", "AUX", "NUL"} | {f"COM{i}" for i in range(1, 10)} | {
    f"LPT{i}" for i in range(1, 10)
}
ILLEGAL = set('<>:"/\\|?*')


def split_name(name: str) -> tuple[str, str]:
    """Rule 2. Returns (base, ext); ext excludes the dot."""
    dot = name.rfind(".")
    if dot > 0:
        return name[:dot], name[dot + 1 :]
    return name, ""


def apply_title(text: str) -> str:
    """Rule 10: each maximal run of Unicode letters -> first upper, rest lower."""
    out: list[str] = []
    in_run = False
    for ch in text:
        is_letter = unicodedata.category(ch).startswith("L")
        if is_letter:
            out.append(ch.upper() if not in_run else ch.lower())
            in_run = True
        else:
            out.append(ch)
            in_run = False
    return "".join(out)


def render_sequence(pattern: str, n: int) -> str:
    """Rule 9: substitute the single {n:PAD} token."""
    match = re.search(r"\{n:(0+)\}", pattern)
    if not match:
        return pattern
    width = len(match.group(1))
    return pattern[: match.start()] + str(n).zfill(width) + pattern[match.end() :]


def apply_steps(target: str, ext: str, steps: list[dict], file_index: int,
                apply_to: str = "name") -> tuple[str, str]:
    """Apply the step list in ARRAY ORDER. Returns (target, ext) after all steps.

    Two bugs lived here until 2026-08-20, both found by differential fuzzing against
    the nine arm implementations -- not by the same-author reference control, which
    shared them:

      1. The sequence counter was computed ONCE from the FIRST sequence step and
         reused for every later one. Rule 9 makes `start`/`step` properties of each
         step, so a rule with several sequence steps needs a counter per step.
      2. Under applyTo="nameAndExtension", extension ops were hoisted out and run
         AFTER all other steps. Rule 4 says steps apply in array order; hoisting
         reorders them and changes the result.

    Nine independently written implementations all had this right. Where the author's
    two artifacts agree, they can still agree on a mistake -- the population of
    independent implementations was the better oracle.
    """
    for step in steps:
        op = step.get("op")
        if op == "replace":
            find = step.get("find", "")
            repl = step.get("replaceWith", "")
            if step.get("regex"):
                flags = re.IGNORECASE if step.get("ignoreCase") else 0
                # .NET uses $1; Python uses \1
                py_repl = re.sub(r"\$(\d+)", r"\\\1", repl)
                target = re.sub(find, py_repl, target, flags=flags)
            elif step.get("ignoreCase"):
                target = re.sub(re.escape(find), repl.replace("\\", "\\\\"), target,
                                flags=re.IGNORECASE)
            else:
                target = target.replace(find, repl)
        elif op == "insert":
            text = step.get("text", "")
            pos = step.get("position", "prefix")
            if pos == "prefix":
                target = text + target
            elif pos == "suffix":
                target = target + text
            else:
                idx = max(0, min(int(step.get("index", 0)), len(target)))
                target = target[:idx] + text + target[idx:]
        elif op == "remove":
            frm = max(0, min(int(step.get("from", 0)), len(target)))
            cnt = max(0, min(int(step.get("count", 0)), len(target) - frm))
            target = target[:frm] + target[frm + cnt :]
        elif op == "sequence":
            n = int(step.get("start", 1)) + file_index * int(step.get("step", 1))
            rendered = render_sequence(step.get("pattern", ""), n)
            if step.get("position", "prefix") == "prefix":
                target = rendered + target
            else:
                target = target + rendered
        elif op == "case":
            mode = step.get("mode")
            if mode == "upper":
                target = target.upper()
            elif mode == "lower":
                target = target.lower()
            elif mode == "title":
                target = apply_title(target)
        elif op == "extension":
            mode = step.get("mode")

            def _xf(e: str) -> str:
                if mode == "lower":
                    return e.lower()
                if mode == "upper":
                    return e.upper()
                if mode == "set":
                    return step.get("value", "")
                return e

            if apply_to == "name":
                ext = _xf(ext)
            else:
                # Rule 12: the target string IS the whole name here, so the extension
                # op acts on the trailing extension of the CURRENT target, in place,
                # at this point in the array order.
                b, e = split_name(target)
                e = _xf(e)
                target = f"{b}.{e}" if e else b
        else:
            raise ValueError(f"unknown op: {op}")
    return target, ext


def classify(proposed: str, original: str, existing_lower: set[str],
             proposed_counts: dict[str, int]) -> str:
    """Rule 13, in precedence order."""
    base, _ = split_name(proposed)
    if (
        proposed == ""
        or len(proposed) > 255
        or any(c in ILLEGAL or ord(c) < 0x20 for c in proposed)
        or base.upper() in RESERVED
    ):
        return "invalid"
    low = proposed.lower()
    hits_other_existing = low in existing_lower and low != original.lower()
    hits_other_proposed = proposed_counts.get(low, 0) > 1
    if hits_other_existing or hits_other_proposed:
        return "collision"
    if proposed == original:
        return "unchanged"
    return "ok"


def plan(folder: Path, rules: dict) -> dict:
    files = sorted([p for p in folder.iterdir() if p.is_file()], key=lambda p: p.name)
    sort_mode = rules.get("sort", "name")
    if sort_mode == "created":
        files.sort(key=lambda p: p.stat().st_ctime)
    elif sort_mode == "modified":
        files.sort(key=lambda p: p.stat().st_mtime)
    # "name" is already ordinal-ascending from the sorted() above.

    apply_to = rules.get("applyTo", "name")
    steps = rules.get("steps", [])

    proposals: list[tuple[str, str]] = []
    for i, path in enumerate(files):
        name = path.name
        if apply_to == "name":
            base, ext = split_name(name)
            new_base, new_ext = apply_steps(base, ext, steps, i, "name")
            proposed = f"{new_base}.{new_ext}" if new_ext else new_base
        else:
            proposed, _ = apply_steps(name, "", steps, i, "nameAndExtension")
        proposals.append((name, proposed))

    existing_lower = {p.name.lower() for p in files}
    counts: dict[str, int] = {}
    for _, prop in proposals:
        counts[prop.lower()] = counts.get(prop.lower(), 0) + 1

    items = []
    summary = {"total": 0, "ok": 0, "collision": 0, "unchanged": 0, "invalid": 0}
    for original, proposed in proposals:
        status = classify(proposed, original, existing_lower, counts)
        items.append({"original": original, "proposed": proposed, "status": status,
                      "reason": ""})
        summary["total"] += 1
        summary[status] += 1

    return {"schemaVersion": 1, "items": items, "summary": summary}


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("usage: oracle.py <folder> <rules.json>")
        raise SystemExit(2)
    result = plan(Path(sys.argv[1]), json.loads(Path(sys.argv[2]).read_text("utf-8")))
    print(json.dumps(result, indent=2, ensure_ascii=False))

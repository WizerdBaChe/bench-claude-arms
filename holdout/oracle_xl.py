#!/usr/bin/env python3
"""
Reference oracle for the XL contract (fixtures/TASK_PROMPT_XL_A.md):
14 operations, plus the --explain per-step trace.

The XL contract deliberately closes the two holes that differential fuzzing
exposed in the small contract: an empty `find` is specified as a no-op, and
`sequence.start` is specified as always >= 0. Those were the only inputs on
which nine independent implementations and this author's oracle disagreed.

If this file and the prompt disagree, the PROMPT is authoritative.
MUST NOT be readable by any experiment arm.
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
    dot = name.rfind(".")
    return (name[:dot], name[dot + 1:]) if dot > 0 else (name, "")


def title_case(text: str) -> str:
    out, in_run = [], False
    for ch in text:
        if unicodedata.category(ch).startswith("L"):
            out.append(ch.upper() if not in_run else ch.lower())
            in_run = True
        else:
            out.append(ch)
            in_run = False
    return "".join(out)


def render_seq(pattern: str, n: int) -> str:
    m = re.search(r"\{n:(0+)\}", pattern)
    if not m:
        return pattern
    return pattern[:m.start()] + str(n).zfill(len(m.group(1))) + pattern[m.end():]


def _regex_repl(repl: str) -> str:
    """.NET writes $1; Python wants \\1."""
    return re.sub(r"\$(\d+)", r"\\\1", repl)


def apply_op(step: dict, target: str, ext: str, orig_ext: str, idx: int,
             apply_to: str) -> tuple[str, str]:
    """Apply ONE step. Returns (target, ext)."""
    op = step.get("op")

    if op == "replace":
        find = step.get("find", "")
        if find == "":
            return target, ext                      # XL rule: empty find is a no-op
        repl = step.get("replaceWith", "")
        ic = bool(step.get("ignoreCase"))
        if step.get("regex"):
            return re.sub(find, _regex_repl(repl), target,
                          flags=re.IGNORECASE if ic else 0), ext
        if ic:
            return re.sub(re.escape(find), repl.replace("\\", "\\\\"), target,
                          flags=re.IGNORECASE), ext
        return target.replace(find, repl), ext

    if op == "insert":
        text = step.get("text", "")
        pos = step.get("position", "prefix")
        if pos == "prefix":
            return text + target, ext
        if pos == "suffix":
            return target + text, ext
        i = max(0, min(int(step.get("index", 0)), len(target)))
        return target[:i] + text + target[i:], ext

    if op == "remove":
        frm = max(0, min(int(step.get("from", 0)), len(target)))
        cnt = max(0, min(int(step.get("count", 0)), len(target) - frm))
        return target[:frm] + target[frm + cnt:], ext

    if op == "sequence":
        n = int(step.get("start", 1)) + idx * int(step.get("step", 1))
        r = render_seq(step.get("pattern", ""), n)
        return (r + target if step.get("position", "prefix") == "prefix"
                else target + r), ext

    if op == "case":
        mode = step.get("mode")
        if mode == "upper":
            return target.upper(), ext
        if mode == "lower":
            return target.lower(), ext
        if mode == "title":
            return title_case(target), ext
        return target, ext

    if op == "extension":
        mode = step.get("mode")

        def xf(e: str) -> str:
            if mode == "lower":
                return e.lower()
            if mode == "upper":
                return e.upper()
            if mode == "set":
                return step.get("value", "")
            return e

        if apply_to == "name":
            return target, xf(ext)
        b, e = split_name(target)
        e = xf(e)
        return (f"{b}.{e}" if e else b), ext

    if op == "pad":
        fill = step.get("fill", "")
        length = int(step.get("length", 0))
        if len(fill) != 1 or len(target) >= length:
            return target, ext
        padding = fill * (length - len(target))
        return ((padding + target) if step.get("side", "left") == "left"
                else (target + padding)), ext

    if op == "trim":
        chars = step.get("chars", "")
        if not chars:
            return target, ext
        side = step.get("side", "both")
        if side in ("both", "left"):
            target = target.lstrip(chars)
        if side in ("both", "right"):
            target = target.rstrip(chars)
        return target, ext

    if op == "slug":
        sep = step.get("separator", "-")
        low = target.lower()
        out = re.sub(r"[^a-z0-9]+", sep, low)
        if sep:
            out = out.strip(sep)
        return out, ext

    if op == "translate":
        frm, to = step.get("from", ""), step.get("to", "")
        table: dict[str, str | None] = {}
        for k, ch in enumerate(frm):
            if ch in table:
                continue                              # first mapping wins
            table[ch] = to[k] if k < len(to) else None
        return "".join(
            (table[c] if table[c] is not None else "") if c in table else c
            for c in target), ext

    if op == "numberFormat":
        width = int(step.get("width", 0))
        m = re.search(r"[0-9]+", target)
        if not m or len(m.group(0)) >= width:
            return target, ext
        return target[:m.start()] + m.group(0).zfill(width) + target[m.end():], ext

    if op == "extract":
        m = re.search(step.get("pattern", ""), target)
        if not m:
            return "", ext
        g = int(step.get("group", 0))
        try:
            return (m.group(g) or ""), ext
        except (IndexError, re.error):
            return "", ext

    if op == "template":
        fmt = step.get("format", "")

        def sub(m: re.Match) -> str:
            tok = m.group(1)
            if tok == "name":
                return target
            if tok == "ext":
                return orig_ext
            if tok == "len":
                return str(len(target))
            nm = re.fullmatch(r"n:(0+)", tok)
            if nm:
                return str(idx + 1).zfill(len(nm.group(1)))
            return m.group(0)                          # unknown token stays literal

        return re.sub(r"\{([^{}]*)\}", sub, fmt), ext

    if op == "dedupeChars":
        out = []
        for ch in target:
            if not out or out[-1] != ch:
                out.append(ch)
        return "".join(out), ext

    raise ValueError(f"unknown op: {op}")


def build(folder: Path, rules: dict) -> tuple[list[dict], list[dict]]:
    """Returns (plan items, explain files) so both contracts stay in lockstep."""
    files = sorted((p for p in folder.iterdir() if p.is_file()),
                   key=lambda p: p.name)
    sort_mode = rules.get("sort", "name")
    if sort_mode == "created":
        files.sort(key=lambda p: p.stat().st_ctime)
    elif sort_mode == "modified":
        files.sort(key=lambda p: p.stat().st_mtime)

    apply_to = rules.get("applyTo", "name")
    steps = rules.get("steps", [])

    proposals, traces = [], []
    for idx, path in enumerate(files):
        name = path.name
        base, ext = split_name(name)
        orig_ext = ext
        target = base if apply_to == "name" else name
        cur_ext = ext if apply_to == "name" else ""
        step_trace = []
        for si, step in enumerate(steps):
            before = target
            target, cur_ext = apply_op(step, target, cur_ext, orig_ext, idx, apply_to)
            step_trace.append({"index": si, "op": step.get("op"),
                               "before": before, "after": target})
        proposed = (f"{target}.{cur_ext}" if (apply_to == "name" and cur_ext)
                    else target)
        proposals.append((name, proposed))
        traces.append({"original": name, "steps": step_trace, "proposed": proposed})

    existing = {p.name.lower() for p in files}
    counts: dict[str, int] = {}
    for _, prop in proposals:
        counts[prop.lower()] = counts.get(prop.lower(), 0) + 1

    items = []
    for (original, proposed), tr in zip(proposals, traces):
        status = classify(proposed, original, existing, counts)
        items.append({"original": original, "proposed": proposed,
                      "status": status, "reason": ""})
        tr["status"] = status
    return items, traces


def classify(proposed: str, original: str, existing: set[str],
             counts: dict[str, int]) -> str:
    base, _ = split_name(proposed)
    if (proposed == "" or len(proposed) > 255
            or any(c in ILLEGAL or ord(c) < 0x20 for c in proposed)
            or base.upper() in RESERVED):
        return "invalid"
    low = proposed.lower()
    if (low in existing and low != original.lower()) or counts.get(low, 0) > 1:
        return "collision"
    return "unchanged" if proposed == original else "ok"


def plan(folder: Path, rules: dict) -> dict:
    items, _ = build(folder, rules)
    summary = {"total": len(items), "ok": 0, "collision": 0,
               "unchanged": 0, "invalid": 0}
    for it in items:
        summary[it["status"]] += 1
    return {"schemaVersion": 1, "items": items, "summary": summary}


def explain(folder: Path, rules: dict) -> dict:
    _, traces = build(folder, rules)
    return {"schemaVersion": 1, "files": traces}


if __name__ == "__main__":
    import sys
    mode = sys.argv[1]
    result = (plan if mode == "plan" else explain)(
        Path(sys.argv[2]), json.loads(Path(sys.argv[3]).read_text("utf-8")))
    print(json.dumps(result, indent=2, ensure_ascii=False))

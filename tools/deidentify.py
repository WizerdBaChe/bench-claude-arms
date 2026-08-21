#!/usr/bin/env python3
"""
De-identification control for this repository.

This repository is a de-identified copy of a private working tree on a personal
Windows machine. De-identification is itself a rewrite of evidence -- which is
exactly what rule 8 of CLAUDE.md forbids doing silently. So the rewrite is
expressed here as four properties of the ASSETS, and this script is both the
tool that applied them and the check that they still hold:

  P1  No file contains the author's Windows account name.
  P2  No file contains the author's absolute source-tree prefix.
  P3  No transcript `attachment` record whose type is in STRIP_TYPES still
      carries its payload. Those payloads were files and listings from OUTSIDE
      the study tree -- the author's private agent rules, installed-skill
      inventory, hook output -- injected as environment context at run time,
      never study data. The RECORD is kept (type field intact, plus a `redacted`
      note) so transcript structure and record counts are unchanged.
  P4  No transcript image block listed in BLOCKED_FRAMES still carries base64.
      Five of the 31 embedded screenshots caught an unrelated application window
      or real personal filenames. The other 26 are untouched.

Everything else is byte-for-byte the original. What was NOT changed, and the
proof that no measured value moved, are in DATA_NOTICE.md.

Usage:
    python tools/deidentify.py --check     # verify the four properties (exit 0/1)
    python tools/deidentify.py             # apply them (idempotent; a no-op here)

Calibration: on the untreated source tree this check reported 230 violations; on
this repository it reports 0. A checker that passes everything is an instrument
fault, so it was run against a known-bad input as well as a known-good one.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import re

REPO = pathlib.Path(__file__).resolve().parent.parent

# The account name is NOT stored here -- writing it into this file would put
# back exactly what P1 removes. Only its hash travels with the repository, so
# an operator who knows the name can confirm they are checking the right one.
#
# P1 therefore runs in two forms:
#   P1  (always)   no path of the form  Users\<name>  survives with <name>
#                  anything other than the placeholder. Anyone can run this.
#   P1x (opt-in)   exact token sweep for the account name, supplied via
#                  --account NAME or $BENCH_ACCOUNT and checked against the
#                  hash below. Only the author can run this, and only they
#                  need to.
ACCOUNT_SHA256 = "2b579073cbdc5e9145a0e7e0b416aee8603464538939fc2c50c19c469f4ccd46"
USER_SUB = "USER"
ACCOUNT_PATH_RE = re.compile(r"Users[\\/]+([A-Za-z0-9._-]+)")
SRC_PREFIX = r"D:\AIWork\_bench-claude-arms"

STRIP_TYPES = {
    "nested_memory",
    "skill_listing",
    "agent_listing_delta",
    "deferred_tools_delta",
    "mcp_instructions_delta",
    "hook_success",
    "hook_additional_context",
}
STRIP_NOTE = ("[redacted for publication: this record carried a file or listing "
              "from the author's private ~/.claude environment, not study data. "
              "The record itself is kept so the transcript's structure and "
              "record count are unchanged. See DATA_NOTICE.md]")

BLOCKED_FRAMES = {
    ("XL-CAL-01", 267): "full-screen capture that caught an unrelated application window",
    ("XL-CAL-01", 279): "app pointed at the author's real Documents folder; frame listed 104 personal filenames",
    ("C2-01", 391): "screen edges showed fragments of an unrelated application window",
    ("C2-01", 403): "screen edges showed fragments of an unrelated application window",
    ("M1-03", 196): "background behind the app window showed an unrelated application",
}
FRAME_NOTE = "[image removed for publication: {why}. See DATA_NOTICE.md]"

PREFIX_SUBS = [
    (SRC_PREFIX.replace("\\", "\\\\") + "\\\\", ""),
    (SRC_PREFIX + "\\", ""),
    (SRC_PREFIX.replace("\\", "/") + "/", ""),
    (SRC_PREFIX.replace("\\", "\\\\"), "<repo root>"),
    (SRC_PREFIX, "<repo root>"),
]

TEXT_EXT = {".md", ".html", ".json", ".py", ".ps1", ".cs", ".txt", ".jsonl",
            ".csproj", ".sln", ".cff", ".yml", ".yaml"}


_ACCOUNT_RE: "re.Pattern | None" = None      # set by main() from --account


def resolve_account(value: str | None) -> "re.Pattern | None":
    """Accept the account name only if it hashes to the recorded value."""
    if not value:
        return None
    import hashlib
    if hashlib.sha256(value.encode()).hexdigest() != ACCOUNT_SHA256:
        raise SystemExit("--account does not match the recorded hash for this "
                         "repository; refusing to sweep for the wrong token.")
    return re.compile(r"\b" + re.escape(value) + r"\b")


def apply_subs(text: str) -> str:
    if _ACCOUNT_RE is not None:
        text = _ACCOUNT_RE.sub(USER_SUB, text)
    for old, new in PREFIX_SUBS:
        text = text.replace(old, new)
    return text


def subs_in_json(node):
    """apply_subs over every string leaf EXCEPT a base64 image payload, so a
    text-level regex can never silently corrupt an image."""
    if isinstance(node, dict):
        is_b64 = node.get("type") == "base64" and "data" in node
        return {k: (v if (is_b64 and k == "data") else subs_in_json(v))
                for k, v in node.items()}
    if isinstance(node, list):
        return [subs_in_json(v) for v in node]
    if isinstance(node, str):
        return apply_subs(node)
    return node


def strip_images(node, note: str) -> int:
    n = 0
    if isinstance(node, dict):
        src = node.get("source")
        if (node.get("type") == "image" and isinstance(src, dict)
                and src.get("type") == "base64" and src.get("data")):
            src["data"] = ""
            src["redacted"] = note
            return 1
        for v in node.values():
            n += strip_images(v, note)
    elif isinstance(node, list):
        for v in node:
            n += strip_images(v, note)
    return n


def redact_transcript(path: pathlib.Path, run: str, stats: dict) -> None:
    with path.open("r", encoding="utf-8", newline="") as fh:
        raw_lines = fh.readlines()

    out, changed = [], False
    for lineno, raw in enumerate(raw_lines, 1):
        stripped = raw.rstrip("\r\n")
        newline = raw[len(stripped):]
        line = stripped

        has_b64 = '"type":"base64"' in line or '"type": "base64"' in line
        needs_json = line.startswith("{") and (
            '"type":"attachment"' in line or '"type": "attachment"' in line
            or (run, lineno) in BLOCKED_FRAMES or has_b64)

        obj = None
        if needs_json:
            try:
                obj = json.loads(line)
            except Exception:
                obj = None

        if obj is not None:
            touched = False
            att = obj.get("attachment")
            if isinstance(att, dict) and att.get("type") in STRIP_TYPES:
                kept = {"type": att.get("type")}
                for k in ("hookName", "hookEvent"):
                    if k in att:
                        kept[k] = att[k]
                kept["redacted"] = STRIP_NOTE
                obj["attachment"] = kept
                stats["attachments"] += 1
                touched = True

            if (run, lineno) in BLOCKED_FRAMES:
                n = strip_images(obj, FRAME_NOTE.format(why=BLOCKED_FRAMES[(run, lineno)]))
                stats["frames"] += n
                touched = touched or n > 0

            if has_b64:
                new_obj = subs_in_json(obj)
                touched = touched or new_obj != obj
                obj = new_obj

            if touched:
                line = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
                changed = True

        if not has_b64:
            new_line = apply_subs(line)
            if new_line != line:
                changed = True
                line = new_line
        out.append(line + newline)

    if changed:
        with path.open("w", encoding="utf-8", newline="") as fh:
            fh.write("".join(out))
        stats["files"] += 1


def redact_plain(path: pathlib.Path, stats: dict) -> None:
    try:
        with path.open("r", encoding="utf-8", newline="") as fh:
            text = fh.read()
    except UnicodeDecodeError:
        return
    new = apply_subs(text)
    if new != text:
        with path.open("w", encoding="utf-8", newline="") as fh:
            fh.write(new)
        stats["files"] += 1


def check() -> int:
    bad = 0
    exact = _ACCOUNT_RE is not None
    for p in sorted(REPO.rglob("*")):
        if not p.is_file() or ".git" in p.parts:
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        rel = p.relative_to(REPO)

        for name in set(ACCOUNT_PATH_RE.findall(text)):
            if name != USER_SUB:
                print(f"  P1 VIOLATION  {rel}  (Users\\{name})")
                bad += 1
        if exact and _ACCOUNT_RE.search(text):
            print(f"  P1x VIOLATION {rel}  (account name as a bare token)")
            bad += 1
        # This file holds SRC_PREFIX because it is the pattern being removed.
        # The exemption is narrow and declared, not silent: the prefix is a
        # folder path with no personal name in it, unlike the account name,
        # which is why only THAT one travels as a hash.
        if p.name != pathlib.Path(__file__).name and (
                SRC_PREFIX in text or SRC_PREFIX.replace("\\", "\\\\") in text):
            print(f"  P2 VIOLATION  {rel}")
            bad += 1

    for tr in sorted(REPO.glob("results/*/transcript.jsonl")):
        run = tr.parent.name
        for lineno, line in enumerate(tr.open(encoding="utf-8"), 1):
            if '"attachment"' in line:
                try:
                    o = json.loads(line)
                except Exception:
                    continue
                a = o.get("attachment", {})
                if isinstance(a, dict) and a.get("type") in STRIP_TYPES and "redacted" not in a:
                    print(f"  P3 VIOLATION  {run}:{lineno} ({a.get('type')})")
                    bad += 1
            if (run, lineno) in BLOCKED_FRAMES and '"data":""' not in line.replace(" ", ""):
                print(f"  P4 VIOLATION  {run}:{lineno}")
                bad += 1

    if bad == 0:
        print("  exemption: tools/deidentify.py itself is exempt from P2 -- it "
              "stores the source prefix because that is the pattern it removes")
        note = "" if exact else "  (P1x skipped: no --account supplied)"
        print(f"  all properties hold{note}")
    else:
        print(f"  {bad} violation(s)")
    return bad


def main() -> int:
    global _ACCOUNT_RE
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="verify the properties instead of applying them")
    ap.add_argument("--account", default=os.environ.get("BENCH_ACCOUNT"),
                    help="the Windows account name to sweep for; must match "
                         "ACCOUNT_SHA256. Optional for --check, required to apply.")
    args = ap.parse_args()
    _ACCOUNT_RE = resolve_account(args.account)

    if args.check:
        return 1 if check() else 0

    if _ACCOUNT_RE is None:
        raise SystemExit("applying the rewrite needs --account NAME (or "
                         "$BENCH_ACCOUNT). Use --check to verify only.")

    stats = {"files": 0, "attachments": 0, "frames": 0}
    for p in sorted(REPO.rglob("*")):
        if not p.is_file() or ".git" in p.parts:
            continue
        if p.suffix.lower() not in TEXT_EXT:
            continue
        if p.name == "transcript.jsonl":
            redact_transcript(p, p.parent.name, stats)
        else:
            redact_plain(p, stats)
    print(f"files rewritten: {stats['files']}")
    print(f"attachment payloads stripped: {stats['attachments']}")
    print(f"image frames removed: {stats['frames']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

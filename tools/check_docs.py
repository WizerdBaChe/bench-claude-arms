#!/usr/bin/env python3
"""
Index control for the repository root.

An index exists to stop things being silently dropped, so it is worth exactly
as much as the guarantee that it is still true. This script is that guarantee.
It checks two properties of the ASSETS themselves -- not of anyone's memory:

  1. LISTED    every root-level .md / .html appears verbatim in README.md
  2. LABELLED  every root-level .md carries a 文件層級 tier banner near the top,
               so a reader can tell in one line whether its numbers may be cited

Why this exists: on 2026-08-21 a full reconciliation found fifteen figures in
PAPER_2026-08-20.md that disagreed with the files on disk. One of them came
from copying a value out of a RESULTS_*.md, which is a round-by-round snapshot
and explicitly not an authority. The banners make that tier visible at the top
of every file instead of only in a rule nobody re-reads.

Exit code is 0 only when both properties hold for every non-exempt file.
PENDING entries are reported but do not fail the run; each carries a reason and
a date, so the debt is named rather than hidden.

Usage:
    python check_docs.py            # report
    python check_docs.py --quiet    # failures and pending only
"""

from __future__ import annotations

import sys
from pathlib import Path

BENCH = Path(__file__).resolve().parent.parent
README = BENCH / "README.md"
BANNER = "**文件層級**"

# Files that are deliberately outside one or both checks.
EXEMPT_LISTED: dict[str, str] = {
    "README.md": "is the index itself",
}
EXEMPT_LABELLED: dict[str, str] = {
    "README.md": "is the index itself",
    "CLAUDE.md": "is the project rule file, not a document in the corpus",
}

# Known debt: reported, does not fail. Remove the entry once handled.
PENDING: dict[str, str] = {}

DOC_SUFFIXES = {".md", ".html"}
LABEL_SUFFIXES = {".md"}          # a banner inside .html would render on the page
BANNER_WINDOW = 12                # lines from the top of the file


def root_docs() -> list[Path]:
    return sorted(
        p for p in BENCH.iterdir()
        if p.is_file() and p.suffix in DOC_SUFFIXES
    )


def main() -> int:
    quiet = "--quiet" in sys.argv
    if not README.exists():
        print(f"FAIL  README.md missing at {README}")
        return 1
    index = README.read_text("utf-8")

    failures: list[str] = []
    pending: list[str] = []
    ok: list[str] = []

    for path in root_docs():
        name = path.name
        notes = []

        if name in EXEMPT_LISTED:
            notes.append(f"listed: exempt ({EXEMPT_LISTED[name]})")
        elif f"`{name}`" in index or name in index:
            notes.append("listed: OK")
        else:
            failures.append(f"NOT LISTED in README.md: {name}")
            notes.append("listed: ** MISSING **")

        if path.suffix not in LABEL_SUFFIXES:
            notes.append("banner: n/a (html)")
        elif name in EXEMPT_LABELLED:
            notes.append(f"banner: exempt ({EXEMPT_LABELLED[name]})")
        else:
            head = path.read_text("utf-8").splitlines()[:BANNER_WINDOW]
            if any(BANNER in line for line in head):
                notes.append("banner: OK")
            elif name in PENDING:
                pending.append(f"{name}: {PENDING[name]}")
                notes.append("banner: PENDING")
            else:
                failures.append(
                    f"NO 文件層級 BANNER in the first {BANNER_WINDOW} lines: {name}")
                notes.append("banner: ** MISSING **")

        ok.append(f"  {name:42} {' | '.join(notes)}")

    # A stale entry in PENDING is its own kind of rot: it claims debt that no
    # longer exists, which trains the reader to ignore the list.
    for name in PENDING:
        if not (BENCH / name).exists():
            failures.append(f"PENDING names a file that does not exist: {name}")

    # README quotes the number of run directories; it is the one count in the
    # index that changes without a file being added or removed at root.
    results = BENCH / "results"
    if results.is_dir():
        n = sum(1 for p in results.iterdir() if p.is_dir())
        claim = f"{n} 個執行紀錄目錄"
        state = "OK" if claim in index else f"** README does not say '{claim}' **"
        line = f"  {'results/ directory count':42} {n} dirs -> {state}"
        ok.append(line)
        if state != "OK":
            failures.append(
                f"README.md must state the current run-directory count: {n}")

    if not quiet:
        print("=" * 78)
        print("ROOT DOCUMENT INDEX CHECK")
        print("=" * 78)
        for line in ok:
            print(line)
        print()

    for p in pending:
        print(f"PENDING  {p}")
    for f in failures:
        print(f"FAIL     {f}")

    total = len(root_docs())
    if failures:
        print(f"\n{len(failures)} failure(s) across {total} root document(s).")
        return 1
    print(f"\nAll {total} root document(s) listed and labelled"
          f"{f'; {len(pending)} pending' if pending else ''}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

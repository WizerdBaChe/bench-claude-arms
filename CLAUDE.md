# bench-claude-arms — project rules

A controlled measurement of LLM coding-agent execution cost in this user's real
Windows environment: execution channel, delegation architecture, reasoning
effort, and a two-point task-scale dose-response. 22 task runs + 2 instrument
probes, $254.22, all passing the pre-registered exclusion audit.

**START HERE: `HANDOFF_2026-08-21.md`** (this directory). It is the entry point —
a locator table for every artifact, the conclusions with their qualifiers, the
defects still live in the paper, and the open work lines each scoped to one
session. Read it before this file if you are new to the project.

Retrospective (written 2026-08-21, read these before large edits):
- Process-problem index: `RETRO_INDEX_2026-08-21.md` (this directory)
- Three further retrospective artifacts live in the author's private agent
  environment (`~/.claude/outputs/retrospectives/…`, `~/.claude/references/…`)
  and are **NOT published here**. Paths appear in this repository for
  provenance only; nothing in the study's conclusions depends on them.
  See `DATA_NOTICE.md`.

Authority order for any number: `results/*/record.json` and `holdout/*.json`
first, then `PAPER_2026-08-20.md`, then the `RESULTS_*.md` files. The RESULTS
files are round-by-round records and at least one of them is stale — see rule 5.

## Version control (new 2026-08-21 — this tree was unversioned until then)

- **This is the de-identified share copy.** Branch `main`, with a GitHub remote
  and a FRESH history that does not continue the private tree's local history:
  those commits contain the four classes of data `DATA_NOTICE.md` removes, so
  carrying the history over would republish them through `git log`.
- **Read `DATA_NOTICE.md` before regenerating anything under `results/` or
  `holdout/`.** New raw material arrives un-de-identified. After any such
  change `python tools/deidentify.py --check` must pass before pushing — it is
  the only thing standing between a re-run and a re-leak.
- **`core.longpaths=true` is required, not optional.** It is set in this repo's
  config. Without it `git add -A` aborts with "Filename too long" on
  `holdout/fuzz-trees/B_unicode_long/aaa…(200 chars).txt` — a 269-character path
  against Windows' 260 limit. That fixture is the fuzz corpus's long-filename
  case and must not be renamed away. Re-clone this tree and you must set the flag
  again.
- **`.gitattributes` pins `* -text`** — no end-of-line conversion in either
  direction. Prompts are hashed per run (SHA-256 recorded in each `meta.json`)
  and `tools/paper_data.py` parses values out of the result JSON, so a line-ending
  rewrite would alter evidence silently and without failing. Do not "fix" this to
  `text=auto`.
- `bin/`, `obj/` and `__pycache__` are ignored (1.8 MB, regenerable — `score.py`
  calls `dotnet build`). `results/**/transcript.jsonl` and `archive/` are tracked
  ON PURPOSE; the reasoning is in `.gitignore`'s trailing note.
- Several sessions have written into this tree concurrently. Before any git
  operation, run `git status` and commit only paths you own — never `git add -A`
  unless you have just checked that everything dirty is yours.

---

## Claims discipline — five rules a summary must not simplify away

1. **Never write "equal quality" unqualified — it is "equal quality AT THE
   CONTRACT LAYER".** The counterexample is in the data: XL-B-01 scored 55/55 on
   the sealed suite and shipped a GUI in which no folder can be loaded at all
   (`Anchor = Top|Right` children added to a still-unparented Panel capture a
   negative right-edge distance; Browse/Refresh land at x=1960 once the panel
   docks to 1180 px, and maximising cannot recover it).

2. **G4's 2/3 vs 0/3 is Fisher p=0.4 — descriptive only.** Never place it beside
   the n=4, p=0.0286 cost results and never present it as a comparison. The
   registered n=3 floor (exact MW p_min=0.100) applies.

3. **Never collapse the GUI finding into "delegation makes worse GUIs".** What
   was measured is WITHIN-ARM DISPERSION on an unmeasured dimension: the
   delegated arm produced both the least usable build in the study and the one
   the user rated best-looking.

4. **Never present effort's -33% thinking tokens as a saving.** Total cost falls
   only 5%; tokens (p=0.3429) and cost (p=0.8857) are statistically
   indistinguishable between high and medium.

5. **Every number must trace to a file. `tools/paper_data.py` only checks that
   the file EXISTS — it never compares the prose to the file's contents.** That
   gap published a stale product for a day: §7.8.1 read "13 implementations x
   5,715 = 51,435" while `holdout/FUZZ_RESULT.json` holds 13 arms x 5,715 =
   **74,295**. Corrected 2026-08-21 in the paper, this repo's HTML, and the
   phase-1 detail file; `RESULTS_T0-1_FUZZ_2026-08-20.md` carries a visible
   correction block with its original text preserved.

---

## Measurement rules (if any run is ever repeated or extended)

6. **Dedupe run records by keeping the MAX per `requestId`, never the first** —
   some repeats are streaming partials, and keep-first understated the delegated
   arm 52%, which inverts the conclusion.

7. **Take token totals from the CLI's self-report, not from the transcript.**
   Subagent transcripts are not always fully flushed; the main line always
   matched exactly.
   ⚠️ The shortfall figure needs care, and rule 5 applies to it. Three different
   numbers describe the SAME run (C3-04) against three different denominators,
   and only two of them trace to a file:
   - **12.73%** — crosscheck delta against total output tokens.
     `RUN_MANIFEST.md` line 47, `results/C3-04/record.json`. **Traceable.**
   - **3.7%** — from `transcript_completeness_pct: 96.3` in the same
     `record.json`. **Traceable.**
   - **19%** — "short 19% of Sonnet output". Appears ONLY in prose
     (`RESULTS_EXPERIMENT2_2026-08-20.md` line 47, paper §3.4.3). No field in
     any `record.json`, `RUN_MANIFEST.md` or `holdout/*.json` equals it, so
     `tools/paper_data.py` can never check it. **Treat as UNVERIFIED until
     someone re-derives it or finds its source.**
   All three can be true at once — they have different denominators — so this is
   not a claim that any of them is wrong. It is a claim that the paper quotes the
   largest one in the methods chapter and the smallest in the results chapter,
   with neither carrying its ruler. The operative rule above does not depend on
   which is right. Found by the adversarial review, C-13.

8. **Never retro-patch the scorer after scores are published.** A known
   unchecked field (`schemaVersion`) was deliberately left in place and audited
   instead: changing the denominator destroys comparability.
   **The audit is `RESULTS_T0-2-3-4_2026-08-20.md` §「對 `schemaVersion` 漏洞的
   處置」** — cite it, because for one day this exemption appeared in four
   documents with no pointer and the adversarial review could not find it (P-1).
   Two qualifiers travel with it: the audit was by the AUTHOR (not independent,
   as the paper originally said), and its population was the 10 implementations
   that existed on 2026-08-20, not the 22 the study ended with. Re-derived over
   all 22 on 2026-08-21 — all emit `schemaVersion = 1` as a compile-time
   constant, and `score_xl.py` does not check the field either. Conclusion
   unchanged; see `REVIEW_RULINGS_CLOSED_2026-08-21.md` §3.

9. **n=4 per arm is the hard floor.** Exact Mann-Whitney at n=3 has p_min=0.100,
   so p<0.05 is combinatorially unreachable regardless of effect size.

10. **The context window here is 1,000,000 tokens, not 200,000.** The 200,000
    figure came from a probe on a smaller model and was never re-checked, and it
    was load-bearing for most of the study. Small-contract peak 161,393 (16.1%);
    XL peak 244,255 (24.4%).

11. **Do not enforce a solo arm with `--disallowedTools`** — that flag alone
    shrinks the cached prompt prefix by 10,830 tokens (29.8%), which reads as a
    benefit of working solo. Enforce by prompt plus a post-hoc `isSidechain`
    audit.

12. **Do not use `entrypoint` to label an execution channel** — it is inherited
    through an environment variable, so a CLI-launched run self-reports
    `claude-desktop`. Use a pre-assigned `--session-id`.

13. **Keep collection cheap and idempotent, separate from evaluation.**
    `collect` calls `score.py`, which calls `dotnet build`, so a `cost_source`
    metadata backfill cost a full rebuild sweep and was never done.

---

## Environment facts that block verification (UNVERIFIED, not unfinished)

14. **pandoc is not installed on this machine** — the paper's docx conversion is
    untested. No new LaTeX constructs were introduced, so the risk is low.

15. **The Browser pane reports `clientWidth = 0`** — HTML layout and overflow
    cannot be measured here. Verify structure and theme tokens through the DOM;
    never claim appearance from a screenshot on this machine.

16. **`request_access` cannot authorise a loose `.exe`** — the resolver only
    matches Start-menu-registered applications, and the request never reaches the
    user. Do not route around it. Use `holdout/g4_anchor_probe/
    probe_reachability.ps1` instead (launch, `EnumChildWindows`, read every
    visible control's rect, terminate; no clicks, no input, no focus steal). Its
    README records what it can and cannot decide.

---

## Deliberately not claimed

17. **Whether XL-B's GUI failure is an arm property or a single-run fluke is
    DELIBERATELY NOT CLAIMED.** Stage 2 produced a third outcome the
    pre-registered rule did not cover (the user opened one build, judged the
    layout unchanged, and stopped investing — marked `n/t`). The study records
    the distribution and declines both registered branches. Do not resolve this
    by argument; only new runs can.

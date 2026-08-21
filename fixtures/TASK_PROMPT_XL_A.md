Build a Windows desktop tool: **Batch Rename Studio Pro**.

You own this end to end: ideation, design, and a working implementation.
Work autonomously to completion. Do not ask me questions. When a decision is
ambiguous, decide it yourself and record the decision and its reason in
`docs/DECISIONS.md`.

ARCHITECTURE DIRECTIVE: Do all of this yourself in this session. Do not
delegate any part of it to a subagent.

## Stack (fixed)

C# WinForms on .NET 8 (`net8.0-windows`). No external NuGet packages beyond
what the base SDK provides. Build must succeed with `dotnet build -c Release`.

## Free (your design — no constraints)

GUI layout and interaction, the rule editor, how preview and traces are
presented, the undo model, project structure, internal APIs, naming, and any
additional features you judge worthwhile.

## Fixed contract A — headless planning

    BatchRenameStudio.exe --plan --dir <folder> --rules <rules.json> --out <plan.json>

Exit 0 on success, write `<plan.json>` as UTF-8 (no BOM), print nothing to
stdout except a single summary line, and rename nothing.

### Input `rules.json`

```json
{
  "applyTo": "name" | "nameAndExtension",
  "sort": "name" | "created" | "modified",
  "steps": [ ... see the op list below ... ]
}
```

### Output `plan.json`

```json
{
  "schemaVersion": 1,
  "items": [{"original":"a.txt","proposed":"001_a.txt","status":"ok","reason":""}],
  "summary": {"total":0,"ok":0,"collision":0,"unchanged":0,"invalid":0}
}
```

## Fixed contract B — headless trace

    BatchRenameStudio.exe --explain --dir <folder> --rules <rules.json> --out <trace.json>

Same exit/stdout/no-rename rules as `--plan`.

```json
{
  "schemaVersion": 1,
  "files": [
    {
      "original": "a.txt",
      "steps": [{"index": 0, "op": "case", "before": "a", "after": "A"}],
      "proposed": "A.txt",
      "status": "ok"
    }
  ]
}
```

- One `files` entry per processed file, in processing order (rule 5).
- One `steps` entry per step in array order — **including steps that change
  nothing** (then `before` equals `after`).
- `before`/`after` are the **target string** (per `applyTo`) immediately before
  and after that step. For an `extension` step under `applyTo:"name"`, the
  target string is unchanged, so `before` equals `after`.
- `proposed` and `status` carry exactly the values `--plan` would produce.

## Exact semantics — implement these literally

1. **Scope.** Only regular files directly inside `<folder>`. Non-recursive.
   Directories are excluded entirely.
2. **Name split.** Let `dot` be the index of the LAST `.` in the file name.
   If `dot > 0`, `base` = name[0..dot) and `ext` = name[dot+1..] (no dot).
   Otherwise `base` = the whole name and `ext` = `""`.
   (So `.gitignore` has base `.gitignore` and ext `""`.)
3. **Target string.** `applyTo:"name"` → steps operate on `base`.
   `applyTo:"nameAndExtension"` → steps operate on the whole file name.
4. **Order.** Steps apply in array order, each to the result of the previous.
5. **Processing order.** `sort` ascending. `"name"` = **ordinal (codepoint)
   ascending, case-sensitive**. `"created"`/`"modified"` use filesystem times.
6. **Reassembly.** The proposed name is `base + "." + ext` when `ext` is
   non-empty, otherwise `base`. Under `applyTo:"nameAndExtension"` the target
   string IS the proposed name; an `extension` step there applies to the
   trailing extension of the current target, in place, at its position in the
   array order.
7. **Status — first match wins:**
   - `"invalid"` — proposed name is empty, longer than 255 characters, contains
     any of `< > : " / \ | ? *` or any character below U+0020, or its `base`
     (case-insensitive) is `CON`, `PRN`, `AUX`, `NUL`, `COM1`–`COM9`,
     `LPT1`–`LPT9`.
   - `"collision"` — equals (case-INsensitive) an existing file in `<folder>`
     other than this item, OR equals another item's proposed name.
   - `"unchanged"` — equals the original name exactly.
   - `"ok"` — otherwise.
8. **`items` / `files` order.** Same as processing order.
9. **Determinism.** Same inputs always produce byte-identical output.
10. `reason` may be any short string, or `""`. It is not checked.

## The 14 operations

### Carried over

- **`replace`** `{"op":"replace","find":"...","replaceWith":"...","regex":false,"ignoreCase":false}`
  Replaces ALL occurrences. `regex:true` uses .NET regex; `replaceWith` may use
  `$1` group references. An **empty `find` is a no-op** (do not throw).
- **`insert`** `{"op":"insert","text":"...","position":"prefix"|"suffix"|"index","index":0}`
  `index` is 0-based, clamped to `[0, length]`.
- **`remove`** `{"op":"remove","from":0,"count":3}`
  `from` clamped to `[0, length]`; `count` clamped to what remains.
- **`sequence`** `{"op":"sequence","pattern":"{n:000}_","start":1,"step":1,"position":"prefix"|"suffix"}`
  `pattern` may contain literal text plus exactly one `{n:PAD}` token, `PAD`
  being one or more `0` giving the zero-pad width. **Each sequence step uses
  its OWN `start`/`step`**: its counter is `start + i * step` where `i` is the
  file's 0-based position in processing order. `start` is always ≥ 0.
- **`case`** `{"op":"case","mode":"upper"|"lower"|"title"}`
  `title` = for each maximal run of Unicode letters, uppercase the first
  character and lowercase the rest; non-letters untouched.
- **`extension`** `{"op":"extension","mode":"lower"|"upper"|"set","value":"txt"}`
  Under `applyTo:"name"` it transforms `ext`. `set` replaces it with `value`
  (no leading dot); a file with no extension gains one.

### New

- **`pad`** `{"op":"pad","length":10,"fill":"_","side":"left"|"right"}`
  If the target is shorter than `length`, add copies of `fill` on `side` until
  it reaches exactly `length`. No change if the target is already that long, or
  if `fill` is not **exactly one character**.
- **`trim`** `{"op":"trim","chars":" _-","side":"both"|"left"|"right"}`
  Repeatedly remove characters from the given side(s) while they appear in the
  `chars` set. Empty `chars` is a no-op.
- **`slug`** `{"op":"slug","separator":"-"}`
  Lowercase the target (invariant), replace every maximal run of characters
  outside `[a-z0-9]` with a single `separator`, then remove leading and
  trailing separators. An empty `separator` removes those runs entirely.
- **`translate`** `{"op":"translate","from":"aeiou","to":"12345"}`
  Character-by-character: a character at index `k` of `from` becomes the
  character at index `k` of `to`. If `to` is shorter than `from`, characters
  mapped beyond its end are **deleted**. If `from` repeats a character, the
  **first** mapping wins. Characters not in `from` are untouched.
- **`numberFormat`** `{"op":"numberFormat","width":4}`
  Find the FIRST maximal run of `[0-9]` and left-pad it with `0` to `width`.
  No change if there is no digit run, or if the run is already ≥ `width`.
- **`extract`** `{"op":"extract","pattern":"\\d+","group":0}`
  Replace the whole target with the first regex match. `group` 0 is the whole
  match. **No match, or a group index out of range, yields an empty target.**
- **`template`** `{"op":"template","format":"{name}-{ext}-{n:000}"}`
  Replace the whole target with `format`, substituting:
  `{name}` = the current target, `{ext}` = the **original** file's extension
  (rule 2), `{len}` = the current target's length in decimal, and `{n:PAD}` =
  the file's 0-based processing index **plus one**, zero-padded to `PAD` width.
  Any other `{...}` sequence is left in place literally.
- **`dedupeChars`** `{"op":"dedupeChars"}`
  Collapse every run of the same character to one occurrence. Case-sensitive.

## Deliverables

1. A buildable solution; `dotnet build -c Release` succeeds with no errors.
2. Both headless contracts (`--plan` and `--explain`) working.
3. A GUI that launches, lets a human build a rule set from all 14 operations,
   see a preview of the proposed names, inspect a per-step trace, and apply the
   rename.
4. `docs/DECISIONS.md` — decisions you made and why.
5. `README.md` — how to build and run.

Stop when all five deliverables exist and `dotnet build -c Release` passes.

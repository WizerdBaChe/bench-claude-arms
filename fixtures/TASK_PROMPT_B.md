Build a Windows desktop tool: **Batch Rename Studio**.

You own this end to end: ideation, design, and a working implementation.
Work autonomously to completion. Do not ask me questions. When a decision is
ambiguous, decide it yourself and record the decision and its reason in
`docs/DECISIONS.md`.

ARCHITECTURE DIRECTIVE: You are the lead. Your own hands produce only the
design and the acceptance: a detailed work card per implementation chunk,
and the verification of what comes back. All implementation -- writing
source files, building, fixing build errors -- is delegated to subagents.
Use whatever subagent types this environment provides; choose them as you
see fit. Do not write implementation source files yourself.

## Stack (fixed)

C# WinForms on .NET 8 (`net8.0-windows`). No external NuGet packages beyond
what the base SDK provides. Build must succeed with `dotnet build -c Release`.

## Free (your design — no constraints)

GUI layout and interaction, the rule editor, how preview is presented, the
undo model, project structure, internal APIs, naming, and any additional
features you judge worthwhile.

## Fixed contract (must match exactly — this is how the tool is verified)

The built executable MUST support a headless planning mode:

    BatchRenameStudio.exe --plan --dir <folder> --rules <rules.json> --out <plan.json>

It MUST exit 0 on success, write `<plan.json>` as UTF-8 (no BOM), print nothing
to stdout except a single summary line, and MUST NOT rename anything in
`--plan` mode.

### Input `rules.json`

```json
{
  "applyTo": "name" | "nameAndExtension",
  "sort": "name" | "created" | "modified",
  "steps": [
    {"op":"replace",  "find":"...", "replaceWith":"...", "regex":false, "ignoreCase":false},
    {"op":"insert",   "text":"...", "position":"prefix"|"suffix"|"index", "index":0},
    {"op":"remove",   "from":0, "count":3},
    {"op":"sequence", "pattern":"{n:000}_", "start":1, "step":1, "position":"prefix"|"suffix"},
    {"op":"case",     "mode":"upper"|"lower"|"title"},
    {"op":"extension","mode":"lower"|"upper"|"set", "value":"txt"}
  ]
}
```

### Output `plan.json`

```json
{
  "schemaVersion": 1,
  "items": [
    {"original":"a.txt","proposed":"001_a.txt","status":"ok","reason":""}
  ],
  "summary": {"total":0,"ok":0,"collision":0,"unchanged":0,"invalid":0}
}
```

### Exact semantics — implement these literally

1. **Scope.** Only regular files directly inside `<folder>`. Non-recursive.
   Directories are excluded entirely.

2. **Name split.** Let `dot` be the index of the LAST `.` in the file name.
   If `dot > 0`, then `base` = name[0..dot) and `ext` = name[dot+1..] (the
   extension does NOT include the dot). Otherwise `base` = the whole name and
   `ext` = `""`. (So `.gitignore` has base `.gitignore` and ext `""`.)

3. **Target string.** `applyTo:"name"` → steps operate on `base`.
   `applyTo:"nameAndExtension"` → steps operate on the whole file name.

4. **Order.** Steps apply in array order, each to the result of the previous.

5. **Processing order.** Files are processed in `sort` ascending order.
   `"name"` means **ordinal (codepoint) ascending, case-sensitive**.
   `"created"`/`"modified"` use the filesystem timestamps ascending.

6. **`replace`.** Replaces ALL occurrences. `regex:true` uses .NET regex and
   `replaceWith` may use `$1` group references. `ignoreCase` applies to both
   literal and regex modes.

7. **`insert`.** `prefix` → before the target string; `suffix` → after it;
   `index` → at 0-based `index`, clamped to `[0, length]`.

8. **`remove`.** Removes `count` characters starting at 0-based `from`.
   `from` is clamped to `[0, length]`; `count` is clamped to what remains.

9. **`sequence`.** `pattern` may contain literal text plus exactly one token
   `{n:PAD}`, where `PAD` is one or more `0` characters giving the zero-pad
   width (`{n:000}` → width 3). The counter is `start` for the FIRST file in
   processing order and increases by `step` for each subsequent file — the
   counter advances for every file, regardless of that file's final status.
   `position` places the rendered pattern before (`prefix`) or after
   (`suffix`) the target string.

10. **`case`.** `upper`/`lower` transform the whole target string.
    `title` = for each maximal run of Unicode letters, uppercase the first
    character and lowercase the rest; non-letters are untouched.

11. **`extension`.** Always operates on `ext`, regardless of `applyTo`.
    `lower`/`upper` transform it. `set` replaces it with `value` (`value` has
    no leading dot). A file with no extension gains one under `set`.

12. **Reassembly.** The proposed name is `base + "." + ext` when `ext` is
    non-empty, otherwise `base`. Under `applyTo:"nameAndExtension"` the target
    string IS the proposed name; if an `extension` step is present it applies
    to the trailing extension of that resulting string.

13. **Status — evaluate in this precedence order, first match wins:**
    - `"invalid"` — the proposed name is empty, is longer than 255 characters,
      contains any of `< > : " / \ | ? *` or any character below U+0020, or its
      `base` (case-insensitive) is a Windows reserved device name: `CON`,
      `PRN`, `AUX`, `NUL`, `COM1`–`COM9`, `LPT1`–`LPT9`.
    - `"collision"` — the proposed name equals (case-INsensitive) an existing
      file in `<folder>` other than this item, OR equals another item's
      proposed name.
    - `"unchanged"` — the proposed name equals the original name exactly.
    - `"ok"` — otherwise.

14. **Ordering of `items`.** Same order as processing order (rule 5).

15. **Determinism.** The same inputs MUST always produce a byte-identical
    `plan.json`.

16. `reason` may be any short string, or `""`. It is not checked.

## Deliverables

1. A buildable solution; `dotnet build -c Release` succeeds with no errors.
2. The headless contract above, working.
3. A GUI that launches, lets a human build a rule set, see a preview of the
   proposed names, and apply the rename.
4. `docs/DECISIONS.md` — decisions you made and why.
5. `README.md` — how to build and run.

Stop when all five deliverables exist and `dotnet build -c Release` passes.

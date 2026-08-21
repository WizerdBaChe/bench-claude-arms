# SPEC-ENGINE — normative build specification (implementers read this file)

This file is the single source of truth for implementers. It restates the fixed
external contract and resolves every ambiguity in it. Where this file and your
intuition disagree, this file wins. Implement literally.

Language of this file: English (machine-read build spec).

---

## 0. Project layout (fixed — do not invent other paths)

```
BatchRenameStudio.sln
src/BatchRenameStudio/BatchRenameStudio.csproj
src/BatchRenameStudio/Program.cs
src/BatchRenameStudio/Cli/ConsoleBridge.cs
src/BatchRenameStudio/Cli/CommandLine.cs
src/BatchRenameStudio/Cli/HeadlessRunner.cs
src/BatchRenameStudio/Core/*.cs
src/BatchRenameStudio/Rename/*.cs
src/BatchRenameStudio/Gui/*.cs
docs/…            (owned by the lead — never modify)
tests/…           (owned by the lead — never modify)
```

`csproj` properties (exact):

```xml
<TargetFramework>net8.0-windows</TargetFramework>
<UseWindowsForms>true</UseWindowsForms>
<!-- Exe (console subsystem), NOT WinExe. A WinExe is PE subsystem 2, and cmd.exe /
     PowerShell deliberately do not WAIT for subsystem-2 processes: the shell returns
     immediately, $LASTEXITCODE is never set and stdout is never captured. That breaks
     the headless contract for every shell-mediated invocation. Measured on this repo:
     with WinExe, `& exe --plan ...` returned an empty $LASTEXITCODE, empty stdout and
     no plan.json until ~800 ms later. GUI mode calls FreeConsole() instead (§8). -->
<OutputType>Exe</OutputType>
<Nullable>enable</Nullable>
<ImplicitUsings>enable</ImplicitUsings>
<LangVersion>latest</LangVersion>
<AssemblyName>BatchRenameStudio</AssemblyName>
<RootNamespace>BatchRenameStudio</RootNamespace>
<EnableWindowsTargeting>true</EnableWindowsTargeting>
<InvariantGlobalization>false</InvariantGlobalization>
```

No `PackageReference` of any kind. No `global.json`. Treat warnings as
warnings (do NOT set `TreatWarningsAsErrors`).

Root namespace `BatchRenameStudio`; sub-namespaces `BatchRenameStudio.Core`,
`.Cli`, `.Rename`, `.Gui`.

---

## 1. Public internal API (fixed signatures — GUI and CLI both bind to these)

```csharp
namespace BatchRenameStudio.Core;

public enum ApplyToMode { Name, NameAndExtension }
public enum SortMode    { Name, Created, Modified }
public enum InsertPosition { Prefix, Suffix, Index }
public enum SeqPosition    { Prefix, Suffix }
public enum CaseMode       { Upper, Lower, Title }
public enum ExtensionMode  { Lower, Upper, Set }
public enum ItemStatus     { Ok, Collision, Unchanged, Invalid }

public abstract class RuleStep { public abstract string Op { get; } }

public sealed class ReplaceStep : RuleStep {
    public string Find = ""; public string ReplaceWith = "";
    public bool Regex; public bool IgnoreCase;
    public override string Op => "replace";
}
public sealed class InsertStep : RuleStep {
    public string Text = ""; public InsertPosition Position = InsertPosition.Prefix; public int Index;
    public override string Op => "insert";
}
public sealed class RemoveStep : RuleStep {
    public int From; public int Count;
    public override string Op => "remove";
}
public sealed class SequenceStep : RuleStep {
    public string Pattern = "{n:000}_"; public int Start = 1; public int Step = 1;
    public SeqPosition Position = SeqPosition.Prefix;
    public override string Op => "sequence";
}
public sealed class CaseStep : RuleStep {
    public CaseMode Mode = CaseMode.Lower;
    public override string Op => "case";
}
public sealed class ExtensionStep : RuleStep {
    public ExtensionMode Mode = ExtensionMode.Lower; public string Value = "";
    public override string Op => "extension";
}

public sealed class RuleSet {
    public ApplyToMode ApplyTo = ApplyToMode.Name;
    public SortMode Sort = SortMode.Name;
    public List<RuleStep> Steps = new();
}

public sealed record FileEntry(string Name, string FullPath, DateTime CreatedUtc, DateTime ModifiedUtc);

public sealed class PlanItem {
    public string Original = ""; public string Proposed = "";
    public ItemStatus Status; public string Reason = "";
}
public sealed class PlanSummary { public int Total, Ok, Collision, Unchanged, Invalid; }
public sealed class RenamePlan {
    public int SchemaVersion = 1;
    public List<PlanItem> Items = new();
    public PlanSummary Summary = new();
}

public static class RuleSetJson {
    public static RuleSet Parse(string json);            // throws RuleParseException on bad input
    public static string Serialize(RuleSet rules);       // round-trippable with Parse
}
public sealed class RuleParseException : Exception { public RuleParseException(string msg) : base(msg) {} }

public readonly record struct NameParts(string Base, string Ext) {
    public static NameParts Split(string fileName);      // rule 2 below
    public string Join();                                // rule 12 below
}

public static class FileScanner {
    public static List<FileEntry> Scan(string directory, SortMode sort);
}

public static class PlanBuilder {
    // Pure: no filesystem access. `files` MUST already be in processing order.
    public static RenamePlan Build(IReadOnlyList<FileEntry> files, RuleSet rules);
}

public static class NameValidator {
    // returns null when valid, otherwise a short reason string
    public static string? Validate(string proposedName);
}

public static class PlanWriter {
    public static string ToJson(RenamePlan plan);        // deterministic, LF-only newlines
    public static void WriteFile(string path, RenamePlan plan); // UTF-8 NO BOM
}
```

---

## 2. Name split (contract rule 2)

`dot` = index of the LAST `.` in the file name.
If `dot > 0` → `Base` = name[0..dot), `Ext` = name[dot+1..] (no dot).
Otherwise → `Base` = whole name, `Ext` = `""`.

So: `a.txt`→(`a`,`txt`) · `.gitignore`→(`.gitignore`,`""`) · `a.b.c`→(`a.b`,`c`)
· `noext`→(`noext`,`""`) · `a.`→(`a`,`""`) — note `a.` has dot=1>0 so
`Base`=`a`, `Ext`=`""`.

`Join()` = `Ext.Length > 0 ? Base + "." + Ext : Base`.

---

## 3. Step application

Per-file state during evaluation:

* `applyTo == Name` → `target` starts as `Base`; a separate `ext` variable holds `Ext`.
* `applyTo == NameAndExtension` → `target` starts as the WHOLE file name; there is no separate `ext`.

Steps run in array order, each on the previous result.

Every step except `extension` transforms `target`.
`extension` ALWAYS acts on an extension (contract rule 11):

* `applyTo == Name` → transform the separate `ext` variable.
* `applyTo == NameAndExtension` → `var p = NameParts.Split(target)`; transform
  `p.Ext`; `target = new NameParts(p.Base, newExt).Join()`.

Final proposed name:
* `applyTo == Name` → `new NameParts(target, ext).Join()`
* `applyTo == NameAndExtension` → `target`

### 3.1 replace
Replaces ALL occurrences.
* `regex == false`: if `Find == ""` → **no-op** (`string.Replace` would throw).
  Otherwise `target.Replace(Find, ReplaceWith, IgnoreCase ? StringComparison.OrdinalIgnoreCase : StringComparison.Ordinal)`.
  `ReplaceWith` is literal here (no `$1` expansion).
* `regex == true`: `new Regex(Find, RegexOptions.CultureInvariant | (IgnoreCase ? RegexOptions.IgnoreCase : None), TimeSpan.FromSeconds(2))`
  then `.Replace(target, ReplaceWith)` — `$1` group references work.
  A malformed pattern must surface at RULE PARSE time (see §6), not here.
  A `RegexMatchTimeoutException` at apply time → let it propagate; callers handle (§7/§8).

### 3.2 insert
* `Prefix` → `Text + target`
* `Suffix` → `target + Text`
* `Index`  → insert at `Math.Clamp(Index, 0, target.Length)`

### 3.3 remove
`from = Math.Clamp(From, 0, target.Length)`;
`count = Math.Clamp(Count, 0, target.Length - from)`;
`target = target.Remove(from, count)`.

### 3.4 sequence
Counter for the file at 0-based processing index `i`: `value = Start + Step * i`.
The counter advances for EVERY file regardless of that file's final status, and
regardless of whether the ruleset contains more than one sequence step (each
sequence step computes its own value from the same `i`).

Rendering `Pattern`: find the FIRST match of `\{n:(0+)\}`.
* match found → `width = group1.Length`; rendered = pattern with that one match
  replaced by `value.ToString(new string('0', width), CultureInfo.InvariantCulture)`.
  (Negative values render as e.g. `-001`.) Any further `{n:0…}` occurrences are
  left as literal text.
* no match → the pattern is used literally.

Then `Prefix` → `rendered + target`; `Suffix` → `target + rendered`.

### 3.5 case
* `Upper` → `target.ToUpperInvariant()`
* `Lower` → `target.ToLowerInvariant()`
* `Title` → walk the string char by char. A char is a letter iff `char.IsLetter(c)`.
  For each maximal run of letters: first char `char.ToUpperInvariant`, the rest
  `char.ToLowerInvariant`. Non-letter chars are copied unchanged and end the run.
  `"héllo wörld-2x"` → `"Héllo Wörld-2X"`.

### 3.6 extension
Operates on the extension string (WITHOUT the dot), per §3 above.
* `Lower` → `ext.ToLowerInvariant()`
* `Upper` → `ext.ToUpperInvariant()`
* `Set`   → `Value` verbatim (no leading dot expected; if `Value` starts with
  `.` keep it verbatim — do not strip).

A file with `Ext == ""` gains an extension under `Set` (because `Join()` then
emits `Base + "." + Value`). Under `Set` with `Value == ""` the extension is
removed.

---

## 4. Scanning & processing order (contract rules 1, 5, 14)

`FileScanner.Scan`:
* `new DirectoryInfo(dir).EnumerateFiles()` — non-recursive, files only.
  Directories are never included. Hidden/system files ARE included.
* `CreatedUtc = fi.CreationTimeUtc`, `ModifiedUtc = fi.LastWriteTimeUtc`.
* Sort ascending:
  * `Name` → `StringComparer.Ordinal` on `Name` (case-sensitive codepoint order).
  * `Created` → by `CreatedUtc`, tie-break by `Name` with `StringComparer.Ordinal`.
  * `Modified` → by `ModifiedUtc`, tie-break by `Name` with `StringComparer.Ordinal`.
* Plan `items` appear in exactly this order.

---

## 5. Status evaluation (contract rule 13 — precedence, first match wins)

Compute ALL proposed names first, then evaluate status for every item.

1. **invalid** — `NameValidator.Validate(proposed) != null`, i.e. any of:
   * `proposed.Length == 0` → reason `"empty name"`
   * `proposed.Length > 255` → reason `"name too long"`
   * contains any of `< > : " / \ | ? *` → reason `"illegal character"`
   * contains any char `< ' '` → reason `"control character"`
   * `NameParts.Split(proposed).Base` case-insensitively equals one of
     `CON PRN AUX NUL COM1..COM9 LPT1..LPT9` → reason `"reserved device name"`
   Check order inside `Validate` is exactly the order above.
2. **collision** — reason `"target name collides"`. True when either:
   * another item (different index) has a proposed name equal under
     `StringComparer.OrdinalIgnoreCase`; **all** items participate, including
     ones that are themselves invalid or unchanged; OR
   * some scanned file in the folder whose entry is NOT this item has a `Name`
     equal to `proposed` under `StringComparer.OrdinalIgnoreCase`.
   Identity is by index in the item list, not by name.
3. **unchanged** — `proposed == original` with ordinal (exact, case-sensitive)
   equality. Reason `""`.
4. **ok** — otherwise. Reason `""`.

`summary` = counts over the final statuses; `total` = item count.

---

## 6. rules.json parsing (`RuleSetJson.Parse`)

`System.Text.Json`, `JsonDocument` based (do NOT rely on polymorphic
deserialization). Rules:

* Property names case-insensitive; enum-ish string values compared with
  `OrdinalIgnoreCase`.
* Missing `applyTo` → `Name`. Missing `sort` → `Name`. Missing `steps` → empty list.
* Unknown `applyTo` / `sort` / `op` / `position` / `mode` value → throw
  `RuleParseException` with a short message.
* Missing optional per-step fields default to: strings `""`, bools `false`,
  ints `0`, `SequenceStep.Start = 1`, `SequenceStep.Step = 1`,
  `SequenceStep.Pattern = ""`, `InsertStep.Position = Prefix`,
  `SequenceStep.Position = Prefix`.
* `op:"replace"` with `regex:true` → compile the `Regex` during parse to
  validate; on `ArgumentException` throw `RuleParseException`. Cache the
  compiled `Regex` on the step (private field) so apply-time does not recompile.
* Root JSON that is not an object, or malformed JSON → `RuleParseException`.
* Extra unknown properties anywhere → ignored silently.

`RuleSetJson.Serialize` emits the same schema (used by the GUI's save-rules
feature) with indented output; it must round-trip through `Parse`.

---

## 7. plan.json writing (`PlanWriter`)

* Build with `Utf8JsonWriter` into a `MemoryStream`, options
  `{ Indented = true, Encoder = JavaScriptEncoder.UnsafeRelaxedJsonEscaping }`.
* Key order exactly: root `schemaVersion`, `items`, `summary`;
  item `original`, `proposed`, `status`, `reason`;
  summary `total`, `ok`, `collision`, `unchanged`, `invalid`.
* `status` values are the lowercase strings `"ok" | "collision" | "unchanged" | "invalid"`.
* Decode the bytes with `new UTF8Encoding(false)`, then
  `.Replace("\r\n", "\n")` so newlines are LF regardless of platform/runtime,
  and ensure the text ends with exactly one trailing `"\n"`.
* `WriteFile` → `File.WriteAllText(path, json, new UTF8Encoding(false))`
  (UTF-8, **no BOM**). Create the parent directory if missing.
* Byte-identical output for identical inputs is a hard requirement: no
  timestamps, no culture-dependent formatting, no hash-order iteration.

---

## 8. Headless CLI (`Program.cs`, `Cli/*`)

Invocation contract:

```
BatchRenameStudio.exe --plan --dir <folder> --rules <rules.json> --out <plan.json>
```

* Arguments may appear in any order. `--plan` is a flag; the other three take a
  value (either `--dir X` or `--dir=X`).
* If `args.Length == 0` → run the GUI (`Application.Run(new Gui.MainForm())`).
* If args contain `--plan` → headless mode. NEVER create a window, NEVER
  rename/create/delete/move any file in `<folder>`.
* Also accept `--help` / `-h` / `-?` → print usage to stdout, exit 0.
* Any other unrecognised argument set → usage to stderr, exit 2.

Exit codes: `0` success · `2` bad arguments or missing/unreadable `--dir` ·
`3` rules file missing / unreadable / `RuleParseException` · `4` failure while
writing `--out` · `5` any other unexpected exception. Non-zero paths print the
message to **stderr only**.

On success print to stdout EXACTLY one line, then exit 0:

```
total=12 ok=9 collision=1 unchanged=1 invalid=1
```

(single trailing newline; nothing else is ever written to stdout in `--plan`
mode — no banner, no progress, no warnings).

`Cli/ConsoleBridge.cs`: the app is a console-subsystem `Exe` (see §0 for why), so
stdout/stderr always exist and every shell waits for it and receives its exit code.

* Write stdout and stderr through
  `new StreamWriter(Console.OpenStandardOutput()/OpenStandardError(), new UTF8Encoding(false)) { AutoFlush = true }`
  and flush before exiting — this bypasses the console's OEM code page and never
  emits a BOM, in both the redirected and the attached-console case.
* GUI mode (no `--plan`) must call `FreeConsole()` as the FIRST statement of `Main`,
  before any Forms type is touched, so double-clicking the exe does not leave a
  console window behind:
  ```csharp
  [DllImport("kernel32.dll")] private static extern bool FreeConsole();
  ```
  Guard it in try/catch and ignore failures; a missing console is not an error.
* Set the exit code with `Environment.Exit(code)` after flushing.

`Program.Main` must be `[STAThread]`.

---

## 9. Rename execution (`Rename/*`, used by the GUI only)

* `RenameExecutor.Apply(string dir, RenamePlan plan)` renames only items whose
  status is `Ok`.
* Two-phase to survive swaps/cycles: phase 1 move every source to a unique
  temporary name (`<original>.brs-tmp-<index>` guaranteed not to exist), phase 2
  move each temp to its final proposed name.
* On any `IOException`/`UnauthorizedAccessException` mid-run: stop, roll back
  everything already moved in this batch, and report which item failed.
* Produce a `RenameJournal` (list of `(from,to)` in applied order) so the GUI
  can undo by replaying it backwards, also two-phase.
* Persist the journal as JSON under
  `%LOCALAPPDATA%\BatchRenameStudio\undo\<yyyyMMdd-HHmmss>.json`; keep at most
  the 20 newest. Failure to persist must NOT fail the rename (log to the GUI
  status bar only).

---

## 10. Non-negotiables checklist for the implementer

- [ ] `dotnet build -c Release` exits 0 with **no errors**.
- [ ] No `PackageReference`, no `global.json`.
- [ ] `--plan` writes UTF-8 without BOM and renames nothing.
- [ ] stdout in `--plan` mode is exactly one line.
- [ ] Two runs on identical input produce byte-identical `plan.json`.
- [ ] Every signature in §1 exists with that exact name and shape.

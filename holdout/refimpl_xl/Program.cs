// Calibration harness for score_xl.py — NOT an independent implementation.
//
// It satisfies the XL CLI contract by delegating the logic to oracle_xl.py. Its
// only job is to prove the scorer can AWARD points: exe discovery, argument
// passing, output comparison, the build gate, the no-rename check.
//
// Deliberately NOT a second hand-written implementation. On the small contract,
// the author's C# reference and the author's Python oracle shared the same two
// misreadings, so their agreement proved nothing — the nine independent arm
// implementations were what exposed the bugs. Contract implementability is
// therefore established by the arms, which is stronger evidence, not weaker.

using System.Diagnostics;
using System.Text;

// Both were absolute paths on the author's machine. Made resolvable elsewhere
// for publication: the interpreter comes from BENCH_PYTHON (default: whatever
// `python` is on PATH), the oracle from BENCH_ORACLE_XL, else from the repo
// two levels above this project. No logic below this line changed, and the
// scores in results/ were produced by the pre-edit binary. See DATA_NOTICE.md.
string Python = Environment.GetEnvironmentVariable("BENCH_PYTHON") ?? "python";
string Oracle = Environment.GetEnvironmentVariable("BENCH_ORACLE_XL")
    ?? Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "..", "oracle_xl.py");

var opts = new Dictionary<string, string>(StringComparer.Ordinal);
for (var i = 0; i < args.Length; i++)
{
    if (!args[i].StartsWith("--", StringComparison.Ordinal)) continue;
    var key = args[i][2..];
    var hasValue = i + 1 < args.Length && !args[i + 1].StartsWith("--", StringComparison.Ordinal);
    opts[key] = hasValue ? args[++i] : "";
}

var mode = opts.ContainsKey("plan") ? "plan" : opts.ContainsKey("explain") ? "explain" : null;
if (mode is null || !opts.TryGetValue("dir", out var dir)
    || !opts.TryGetValue("rules", out var rules) || !opts.TryGetValue("out", out var outPath))
{
    Console.Error.WriteLine(
        "usage: BatchRenameStudio.exe --plan|--explain --dir <folder> --rules <r.json> --out <o.json>");
    return 2;
}

var psi = new ProcessStartInfo(Python)
{
    RedirectStandardOutput = true,
    RedirectStandardError = true,
    StandardOutputEncoding = new UTF8Encoding(false),
    UseShellExecute = false,
};
foreach (var a in new[] { Oracle, mode, dir, rules }) psi.ArgumentList.Add(a);

using var proc = Process.Start(psi)!;
var json = proc.StandardOutput.ReadToEnd();
var stderr = proc.StandardError.ReadToEnd();
proc.WaitForExit();
if (proc.ExitCode != 0)
{
    Console.Error.WriteLine(stderr);
    return 3;
}

File.WriteAllText(outPath, json, new UTF8Encoding(false));
Console.WriteLine($"{mode}: wrote {outPath}");
return 0;

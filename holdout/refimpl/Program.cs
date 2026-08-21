// Reference implementation of the Batch Rename Studio contract
// (fixtures/TASK_PROMPT_A.md rules 1-15).
//
// PURPOSE: known-TRUE calibration input for holdout/score.py. A gate that
// rejects everything scores 100% on a one-sided calibration, so the scorer must
// be shown to AWARD points on a correct implementation before it is trusted to
// deny them to an arm.
//
// Held out from every experiment arm.

using System.Globalization;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using System.Text.RegularExpressions;

namespace BatchRenameStudio;

internal static class Program
{
    private static readonly HashSet<string> Reserved = new(StringComparer.OrdinalIgnoreCase)
    {
        "CON", "PRN", "AUX", "NUL",
        "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
        "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",
    };

    private static readonly char[] Illegal = { '<', '>', ':', '"', '/', '\\', '|', '?', '*' };

    private static int Main(string[] args)
    {
        var opts = ParseArgs(args);
        if (!opts.TryGetValue("plan", out _) ||
            !opts.TryGetValue("dir", out var dir) ||
            !opts.TryGetValue("rules", out var rulesPath) ||
            !opts.TryGetValue("out", out var outPath))
        {
            Console.Error.WriteLine(
                "usage: BatchRenameStudio.exe --plan --dir <folder> --rules <rules.json> --out <plan.json>");
            return 2;
        }

        var rules = JsonNode.Parse(File.ReadAllText(rulesPath, Encoding.UTF8))!.AsObject();
        var plan = BuildPlan(dir, rules);

        var json = JsonSerializer.Serialize(plan, new JsonSerializerOptions
        {
            WriteIndented = true,
            PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
            Encoder = System.Text.Encodings.Web.JavaScriptEncoder.UnsafeRelaxedJsonEscaping,
        });
        File.WriteAllText(outPath, json + "\n", new UTF8Encoding(false));

        var s = plan.Summary;
        Console.WriteLine(
            $"planned {s.Total} file(s): {s.Ok} ok, {s.Collision} collision, " +
            $"{s.Unchanged} unchanged, {s.Invalid} invalid");
        return 0;
    }

    private static Dictionary<string, string> ParseArgs(string[] args)
    {
        var map = new Dictionary<string, string>(StringComparer.Ordinal);
        for (var i = 0; i < args.Length; i++)
        {
            if (!args[i].StartsWith("--", StringComparison.Ordinal)) continue;
            var key = args[i][2..];
            var hasValue = i + 1 < args.Length && !args[i + 1].StartsWith("--", StringComparison.Ordinal);
            map[key] = hasValue ? args[++i] : "";
        }
        return map;
    }

    // Rule 2: dot must be at index > 0 for a real extension.
    private static (string Base, string Ext) SplitName(string name)
    {
        var dot = name.LastIndexOf('.');
        return dot > 0 ? (name[..dot], name[(dot + 1)..]) : (name, "");
    }

    private static Plan BuildPlan(string dir, JsonObject rules)
    {
        // Rule 1: files only, non-recursive.
        var files = new DirectoryInfo(dir).GetFiles().ToList();

        // Rule 5: ordinal ascending by default.
        var sort = rules["sort"]?.GetValue<string>() ?? "name";
        files = sort switch
        {
            "created" => files.OrderBy(f => f.CreationTimeUtc).ToList(),
            "modified" => files.OrderBy(f => f.LastWriteTimeUtc).ToList(),
            _ => files.OrderBy(f => f.Name, StringComparer.Ordinal).ToList(),
        };

        var applyTo = rules["applyTo"]?.GetValue<string>() ?? "name";
        var steps = rules["steps"]?.AsArray() ?? new JsonArray();

        var proposals = new List<(string Original, string Proposed)>();
        for (var i = 0; i < files.Count; i++)
        {
            var name = files[i].Name;
            string proposed;

            if (applyTo == "name")
            {
                var (b, e) = SplitName(name);
                var (nb, ne) = ApplySteps(b, e, steps, i, "name");
                proposed = ne.Length > 0 ? $"{nb}.{ne}" : nb;
            }
            else
            {
                (proposed, _) = ApplySteps(name, "", steps, i, "nameAndExtension");
            }
            proposals.Add((name, proposed));
        }

        var existing = new HashSet<string>(files.Select(f => f.Name), StringComparer.OrdinalIgnoreCase);
        var counts = new Dictionary<string, int>(StringComparer.OrdinalIgnoreCase);
        foreach (var (_, p) in proposals)
            counts[p] = counts.GetValueOrDefault(p) + 1;

        var plan = new Plan();
        foreach (var (original, proposed) in proposals)
        {
            var status = Classify(proposed, original, existing, counts);
            plan.Items.Add(new Item { Original = original, Proposed = proposed, Status = status });
            plan.Summary.Total++;
            switch (status)
            {
                case "ok": plan.Summary.Ok++; break;
                case "collision": plan.Summary.Collision++; break;
                case "unchanged": plan.Summary.Unchanged++; break;
                default: plan.Summary.Invalid++; break;
            }
        }
        return plan;
    }

    // Steps run in ARRAY ORDER (rule 4). `fileIndex` rather than a precomputed counter:
    // start/step belong to each sequence step (rule 9), so several sequence steps in one
    // rule set each advance on their own terms. Both of those were wrong here until
    // 2026-08-20; differential fuzzing against the nine arm implementations found them,
    // the same-author oracle did not -- it had the identical mistake.
    private static (string Target, string Ext) ApplySteps(
        string target, string ext, JsonArray steps, int fileIndex, string applyTo)
    {
        foreach (var raw in steps)
        {
            if (raw is not JsonObject s) continue;
            var op = s["op"]?.GetValue<string>();
            switch (op)
            {
                case "replace":
                {
                    var find = s["find"]?.GetValue<string>() ?? "";
                    var repl = s["replaceWith"]?.GetValue<string>() ?? "";
                    var isRegex = s["regex"]?.GetValue<bool>() ?? false;
                    var ic = s["ignoreCase"]?.GetValue<bool>() ?? false;
                    if (isRegex)
                        target = Regex.Replace(target, find, repl,
                            ic ? RegexOptions.IgnoreCase : RegexOptions.None);
                    else
                        target = target.Replace(find, repl,
                            ic ? StringComparison.OrdinalIgnoreCase : StringComparison.Ordinal);
                    break;
                }
                case "insert":
                {
                    var text = s["text"]?.GetValue<string>() ?? "";
                    var pos = s["position"]?.GetValue<string>() ?? "prefix";
                    if (pos == "prefix") target = text + target;
                    else if (pos == "suffix") target += text;
                    else
                    {
                        var idx = Math.Clamp(s["index"]?.GetValue<int>() ?? 0, 0, target.Length);
                        target = target[..idx] + text + target[idx..];
                    }
                    break;
                }
                case "remove":
                {
                    var from = Math.Clamp(s["from"]?.GetValue<int>() ?? 0, 0, target.Length);
                    var count = Math.Clamp(s["count"]?.GetValue<int>() ?? 0, 0, target.Length - from);
                    target = target.Remove(from, count);
                    break;
                }
                case "sequence":
                {
                    var n = (s["start"]?.GetValue<int>() ?? 1)
                            + fileIndex * (s["step"]?.GetValue<int>() ?? 1);
                    var rendered = RenderSequence(s["pattern"]?.GetValue<string>() ?? "", n);
                    target = (s["position"]?.GetValue<string>() ?? "prefix") == "prefix"
                        ? rendered + target
                        : target + rendered;
                    break;
                }
                case "case":
                {
                    target = (s["mode"]?.GetValue<string>()) switch
                    {
                        "upper" => target.ToUpperInvariant(),
                        "lower" => target.ToLowerInvariant(),
                        "title" => TitleCase(target),
                        _ => target,
                    };
                    break;
                }
                case "extension":
                {
                    var mode = s["mode"]?.GetValue<string>();
                    string Xf(string e) => mode switch
                    {
                        "lower" => e.ToLowerInvariant(),
                        "upper" => e.ToUpperInvariant(),
                        "set" => s["value"]?.GetValue<string>() ?? "",
                        _ => e,
                    };
                    if (applyTo == "name")
                    {
                        ext = Xf(ext);
                    }
                    else
                    {
                        // Rule 12: acts on the trailing extension of the CURRENT target,
                        // in place, at this position in the array order.
                        var (tb, te) = SplitName(target);
                        te = Xf(te);
                        target = te.Length > 0 ? $"{tb}.{te}" : tb;
                    }
                    break;
                }
            }
        }
        return (target, ext);
    }

    // Rule 9: exactly one {n:PAD} token, PAD is one or more '0'.
    private static string RenderSequence(string pattern, int n)
    {
        var m = Regex.Match(pattern, @"\{n:(0+)\}");
        if (!m.Success) return pattern;
        return pattern[..m.Index]
             + n.ToString(CultureInfo.InvariantCulture).PadLeft(m.Groups[1].Value.Length, '0')
             + pattern[(m.Index + m.Length)..];
    }

    // Rule 10: each maximal run of letters -> first upper, rest lower.
    private static string TitleCase(string text)
    {
        var sb = new StringBuilder(text.Length);
        var inRun = false;
        foreach (var ch in text)
        {
            if (char.IsLetter(ch))
            {
                sb.Append(inRun ? char.ToLowerInvariant(ch) : char.ToUpperInvariant(ch));
                inRun = true;
            }
            else
            {
                sb.Append(ch);
                inRun = false;
            }
        }
        return sb.ToString();
    }

    // Rule 13, in precedence order: invalid > collision > unchanged > ok.
    private static string Classify(
        string proposed, string original, HashSet<string> existing, Dictionary<string, int> counts)
    {
        var (b, _) = SplitName(proposed);
        if (proposed.Length == 0
            || proposed.Length > 255
            || proposed.IndexOfAny(Illegal) >= 0
            || proposed.Any(c => c < 0x20)
            || Reserved.Contains(b))
            return "invalid";

        var hitsExisting = existing.Contains(proposed)
            && !string.Equals(proposed, original, StringComparison.OrdinalIgnoreCase);
        if (hitsExisting || counts.GetValueOrDefault(proposed) > 1) return "collision";

        return string.Equals(proposed, original, StringComparison.Ordinal) ? "unchanged" : "ok";
    }
}

internal sealed class Plan
{
    public int SchemaVersion { get; set; } = 1;
    public List<Item> Items { get; } = new();
    public Summary Summary { get; } = new();
}

internal sealed class Item
{
    public string Original { get; set; } = "";
    public string Proposed { get; set; } = "";
    public string Status { get; set; } = "";
    public string Reason { get; set; } = "";
}

internal sealed class Summary
{
    public int Total { get; set; }
    public int Ok { get; set; }
    public int Collision { get; set; }
    public int Unchanged { get; set; }
    public int Invalid { get; set; }
}

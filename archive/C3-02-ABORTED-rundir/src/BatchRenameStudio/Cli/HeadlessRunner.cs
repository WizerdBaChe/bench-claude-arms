using BatchRenameStudio.Core;

namespace BatchRenameStudio.Cli;

public static class HeadlessRunner
{
    private const string UsageText =
        "BatchRenameStudio.exe --plan --dir <folder> --rules <rules.json> --out <plan.json>";

    public static int Run(ParsedArgs parsed)
    {
        if (parsed.Help)
        {
            ConsoleBridge.StdOut.Write(UsageText + "\n");
            return 0;
        }

        if (parsed.Unrecognized || !parsed.Plan || string.IsNullOrEmpty(parsed.Dir) ||
            string.IsNullOrEmpty(parsed.Rules) || string.IsNullOrEmpty(parsed.Out))
        {
            ConsoleBridge.StdErr.Write(UsageText + "\n");
            return 2;
        }

        try
        {
            if (!Directory.Exists(parsed.Dir))
            {
                ConsoleBridge.StdErr.Write("directory not found or unreadable: " + parsed.Dir + "\n");
                return 2;
            }

            List<FileEntry> files;
            RuleSet rules;

            string rulesJson;
            try
            {
                if (!File.Exists(parsed.Rules))
                {
                    ConsoleBridge.StdErr.Write("rules file not found: " + parsed.Rules + "\n");
                    return 3;
                }
                rulesJson = File.ReadAllText(parsed.Rules);
                rules = RuleSetJson.Parse(rulesJson);
            }
            catch (RuleParseException ex)
            {
                ConsoleBridge.StdErr.Write("rule parse error: " + ex.Message + "\n");
                return 3;
            }
            catch (IOException ex)
            {
                ConsoleBridge.StdErr.Write("rules file unreadable: " + ex.Message + "\n");
                return 3;
            }
            catch (UnauthorizedAccessException ex)
            {
                ConsoleBridge.StdErr.Write("rules file unreadable: " + ex.Message + "\n");
                return 3;
            }

            files = FileScanner.Scan(parsed.Dir, rules.Sort);
            var plan = PlanBuilder.Build(files, rules);

            try
            {
                PlanWriter.WriteFile(parsed.Out!, plan);
            }
            catch (Exception ex) when (ex is IOException or UnauthorizedAccessException)
            {
                ConsoleBridge.StdErr.Write("failed to write plan: " + ex.Message + "\n");
                return 4;
            }

            string summary = $"total={plan.Summary.Total} ok={plan.Summary.Ok} collision={plan.Summary.Collision} unchanged={plan.Summary.Unchanged} invalid={plan.Summary.Invalid}";
            ConsoleBridge.StdOut.Write(summary + "\n");
            return 0;
        }
        catch (Exception ex)
        {
            ConsoleBridge.StdErr.Write("unexpected error: " + ex.Message + "\n");
            return 5;
        }
    }
}

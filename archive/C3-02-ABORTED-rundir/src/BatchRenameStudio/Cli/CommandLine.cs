namespace BatchRenameStudio.Cli;

public sealed class ParsedArgs
{
    public bool Plan;
    public bool Help;
    public string? Dir;
    public string? Rules;
    public string? Out;
    public bool Unrecognized;
}

public static class CommandLine
{
    public static ParsedArgs Parse(string[] args)
    {
        var result = new ParsedArgs();

        int i = 0;
        while (i < args.Length)
        {
            string arg = args[i];

            if (arg == "--plan")
            {
                result.Plan = true;
                i++;
                continue;
            }
            if (arg == "--help" || arg == "-h" || arg == "-?")
            {
                result.Help = true;
                i++;
                continue;
            }

            string? name = null;
            string? value = null;

            int eq = arg.IndexOf('=');
            if (arg.StartsWith("--") && eq >= 0)
            {
                name = arg.Substring(0, eq);
                value = arg.Substring(eq + 1);
                i++;
            }
            else if (arg.StartsWith("--"))
            {
                name = arg;
                if (i + 1 < args.Length)
                {
                    value = args[i + 1];
                    i += 2;
                }
                else
                {
                    result.Unrecognized = true;
                    i++;
                    continue;
                }
            }
            else
            {
                result.Unrecognized = true;
                i++;
                continue;
            }

            switch (name)
            {
                case "--dir":
                    result.Dir = value;
                    break;
                case "--rules":
                    result.Rules = value;
                    break;
                case "--out":
                    result.Out = value;
                    break;
                default:
                    result.Unrecognized = true;
                    break;
            }
        }

        return result;
    }
}

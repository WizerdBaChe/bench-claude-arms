using System.Text.RegularExpressions;

namespace BatchRenameStudio.Core;

public abstract class RuleStep
{
    public abstract string Op { get; }
}

public sealed class ReplaceStep : RuleStep
{
    public string Find = "";
    public string ReplaceWith = "";
    public bool Regex;
    public bool IgnoreCase;
    public override string Op => "replace";

    // Cached compiled regex, set during parse when Regex == true.
    internal System.Text.RegularExpressions.Regex? CompiledRegex;
}

public sealed class InsertStep : RuleStep
{
    public string Text = "";
    public InsertPosition Position = InsertPosition.Prefix;
    public int Index;
    public override string Op => "insert";
}

public sealed class RemoveStep : RuleStep
{
    public int From;
    public int Count;
    public override string Op => "remove";
}

public sealed class SequenceStep : RuleStep
{
    public string Pattern = "{n:000}_";
    public int Start = 1;
    public int Step = 1;
    public SeqPosition Position = SeqPosition.Prefix;
    public override string Op => "sequence";
}

public sealed class CaseStep : RuleStep
{
    public CaseMode Mode = CaseMode.Lower;
    public override string Op => "case";
}

public sealed class ExtensionStep : RuleStep
{
    public ExtensionMode Mode = ExtensionMode.Lower;
    public string Value = "";
    public override string Op => "extension";
}

public sealed class RuleSet
{
    public ApplyToMode ApplyTo = ApplyToMode.Name;
    public SortMode Sort = SortMode.Name;
    public List<RuleStep> Steps = new();
}

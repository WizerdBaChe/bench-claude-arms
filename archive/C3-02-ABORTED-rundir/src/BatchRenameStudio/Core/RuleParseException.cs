namespace BatchRenameStudio.Core;

public sealed class RuleParseException : Exception
{
    public RuleParseException(string msg) : base(msg) { }
}

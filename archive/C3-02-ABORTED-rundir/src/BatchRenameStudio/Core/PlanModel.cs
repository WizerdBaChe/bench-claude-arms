namespace BatchRenameStudio.Core;

public sealed record FileEntry(string Name, string FullPath, DateTime CreatedUtc, DateTime ModifiedUtc);

public sealed class PlanItem
{
    public string Original = "";
    public string Proposed = "";
    public ItemStatus Status;
    public string Reason = "";
}

public sealed class PlanSummary
{
    public int Total, Ok, Collision, Unchanged, Invalid;
}

public sealed class RenamePlan
{
    public int SchemaVersion = 1;
    public List<PlanItem> Items = new();
    public PlanSummary Summary = new();
}

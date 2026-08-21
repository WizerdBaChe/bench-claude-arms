namespace BatchRenameStudio.Core;

public static class PlanBuilder
{
    // Pure: no filesystem access. `files` MUST already be in processing order.
    public static RenamePlan Build(IReadOnlyList<FileEntry> files, RuleSet rules)
    {
        int n = files.Count;
        var proposed = new string[n];
        for (int i = 0; i < n; i++)
        {
            proposed[i] = StepApplier.Apply(files[i].Name, rules, i);
        }

        var items = new List<PlanItem>(n);
        var summary = new PlanSummary { Total = n };

        for (int i = 0; i < n; i++)
        {
            string original = files[i].Name;
            string prop = proposed[i];

            ItemStatus status;
            string reason;

            string? invalidReason = NameValidator.Validate(prop);
            if (invalidReason != null)
            {
                status = ItemStatus.Invalid;
                reason = invalidReason;
            }
            else if (IsCollision(files, proposed, i))
            {
                status = ItemStatus.Collision;
                reason = "target name collides";
            }
            else if (string.Equals(prop, original, StringComparison.Ordinal))
            {
                status = ItemStatus.Unchanged;
                reason = "";
            }
            else
            {
                status = ItemStatus.Ok;
                reason = "";
            }

            items.Add(new PlanItem { Original = original, Proposed = prop, Status = status, Reason = reason });

            switch (status)
            {
                case ItemStatus.Ok: summary.Ok++; break;
                case ItemStatus.Collision: summary.Collision++; break;
                case ItemStatus.Unchanged: summary.Unchanged++; break;
                case ItemStatus.Invalid: summary.Invalid++; break;
            }
        }

        return new RenamePlan { Items = items, Summary = summary };
    }

    private static bool IsCollision(IReadOnlyList<FileEntry> files, string[] proposed, int i)
    {
        string prop = proposed[i];

        for (int j = 0; j < proposed.Length; j++)
        {
            if (j == i)
            {
                continue;
            }
            if (string.Equals(proposed[j], prop, StringComparison.OrdinalIgnoreCase))
            {
                return true;
            }
        }

        for (int j = 0; j < files.Count; j++)
        {
            if (j == i)
            {
                continue;
            }
            if (string.Equals(files[j].Name, prop, StringComparison.OrdinalIgnoreCase))
            {
                return true;
            }
        }

        return false;
    }
}

using BatchRenameStudio.Core;

namespace BatchRenameStudio.Rename;

public sealed class RenameResult
{
    public bool Success;
    public RenameJournal Journal = new();
    public string? FailedItem;
    public string? ErrorMessage;
}

public static class RenameExecutor
{
    /// <summary>
    /// Renames only items whose status is Ok. Two-phase (move-to-temp then
    /// move-to-final) so swaps/cycles survive. On any IOException or
    /// UnauthorizedAccessException mid-run, everything already moved in this
    /// batch is rolled back and the failing item is reported.
    /// </summary>
    public static RenameResult Apply(string dir, RenamePlan plan)
    {
        var okItems = plan.Items.Where(i => i.Status == ItemStatus.Ok).ToList();
        var journal = new RenameJournal();

        // Filesystem moves actually performed so far, in order (fsFrom, fsTo).
        // Used to roll back on failure by replaying in reverse.
        var appliedMoves = new List<(string From, string To)>();
        var tempPaths = new string[okItems.Count];

        try
        {
            // Phase 1: move every source to a unique temporary name.
            for (int idx = 0; idx < okItems.Count; idx++)
            {
                var item = okItems[idx];
                string srcPath = Path.Combine(dir, item.Original);
                string tempPath = UniqueTempPath(dir, item.Original, idx);

                try
                {
                    File.Move(srcPath, tempPath);
                }
                catch (Exception ex) when (ex is IOException or UnauthorizedAccessException)
                {
                    RollBack(appliedMoves);
                    return new RenameResult { Success = false, Journal = journal, FailedItem = item.Original, ErrorMessage = ex.Message };
                }

                appliedMoves.Add((srcPath, tempPath));
                tempPaths[idx] = tempPath;
            }

            // Phase 2: move each temp to its final proposed name.
            for (int idx = 0; idx < okItems.Count; idx++)
            {
                var item = okItems[idx];
                string tempPath = tempPaths[idx];
                string finalPath = Path.Combine(dir, item.Proposed);

                try
                {
                    File.Move(tempPath, finalPath);
                }
                catch (Exception ex) when (ex is IOException or UnauthorizedAccessException)
                {
                    RollBack(appliedMoves);
                    return new RenameResult { Success = false, Journal = journal, FailedItem = item.Original, ErrorMessage = ex.Message };
                }

                appliedMoves.Add((tempPath, finalPath));
                journal.Add(item.Original, item.Proposed);
            }

            return new RenameResult { Success = true, Journal = journal };
        }
        catch (Exception ex) when (ex is IOException or UnauthorizedAccessException)
        {
            RollBack(appliedMoves);
            return new RenameResult { Success = false, Journal = journal, ErrorMessage = ex.Message };
        }
    }

    /// <summary>
    /// Undoes a completed rename batch by replaying the journal backwards, two-phase.
    /// </summary>
    public static RenameResult Undo(string dir, RenameJournal journal)
    {
        var appliedMoves = new List<(string From, string To)>();
        var tempPaths = new string[journal.Entries.Count];

        try
        {
            // Reverse order: undo the last applied rename first.
            for (int idx = journal.Entries.Count - 1, i = 0; idx >= 0; idx--, i++)
            {
                var entry = journal.Entries[idx];
                string srcPath = Path.Combine(dir, entry.To);
                string tempPath = UniqueTempPath(dir, entry.To, i);

                try
                {
                    File.Move(srcPath, tempPath);
                }
                catch (Exception ex) when (ex is IOException or UnauthorizedAccessException)
                {
                    RollBack(appliedMoves);
                    return new RenameResult { Success = false, FailedItem = entry.To, ErrorMessage = ex.Message };
                }

                appliedMoves.Add((srcPath, tempPath));
                tempPaths[i] = tempPath;
            }

            for (int idx = journal.Entries.Count - 1, i = 0; idx >= 0; idx--, i++)
            {
                var entry = journal.Entries[idx];
                string tempPath = tempPaths[i];
                string finalPath = Path.Combine(dir, entry.From);

                try
                {
                    File.Move(tempPath, finalPath);
                }
                catch (Exception ex) when (ex is IOException or UnauthorizedAccessException)
                {
                    RollBack(appliedMoves);
                    return new RenameResult { Success = false, FailedItem = entry.To, ErrorMessage = ex.Message };
                }

                appliedMoves.Add((tempPath, finalPath));
            }

            return new RenameResult { Success = true };
        }
        catch (Exception ex) when (ex is IOException or UnauthorizedAccessException)
        {
            RollBack(appliedMoves);
            return new RenameResult { Success = false, ErrorMessage = ex.Message };
        }
    }

    private static string UniqueTempPath(string dir, string originalName, int index)
    {
        string tempName = originalName + ".brs-tmp-" + index;
        string tempPath = Path.Combine(dir, tempName);
        int suffix = 0;
        while (File.Exists(tempPath))
        {
            suffix++;
            tempPath = Path.Combine(dir, tempName + "-" + suffix);
        }
        return tempPath;
    }

    private static void RollBack(List<(string From, string To)> appliedMoves)
    {
        for (int i = appliedMoves.Count - 1; i >= 0; i--)
        {
            var (from, to) = appliedMoves[i];
            try
            {
                if (File.Exists(to) && !File.Exists(from))
                {
                    File.Move(to, from);
                }
            }
            catch
            {
                // best-effort rollback; nothing more we can do here.
            }
        }
    }
}

namespace BatchRenameStudio.Core;

public static class FileScanner
{
    public static List<FileEntry> Scan(string directory, SortMode sort)
    {
        var dirInfo = new DirectoryInfo(directory);
        var entries = new List<FileEntry>();
        foreach (var fi in dirInfo.EnumerateFiles())
        {
            entries.Add(new FileEntry(fi.Name, fi.FullName, fi.CreationTimeUtc, fi.LastWriteTimeUtc));
        }

        switch (sort)
        {
            case SortMode.Name:
                entries.Sort((a, b) => StringComparer.Ordinal.Compare(a.Name, b.Name));
                break;
            case SortMode.Created:
                entries.Sort((a, b) =>
                {
                    int cmp = a.CreatedUtc.CompareTo(b.CreatedUtc);
                    return cmp != 0 ? cmp : StringComparer.Ordinal.Compare(a.Name, b.Name);
                });
                break;
            case SortMode.Modified:
                entries.Sort((a, b) =>
                {
                    int cmp = a.ModifiedUtc.CompareTo(b.ModifiedUtc);
                    return cmp != 0 ? cmp : StringComparer.Ordinal.Compare(a.Name, b.Name);
                });
                break;
        }

        return entries;
    }
}

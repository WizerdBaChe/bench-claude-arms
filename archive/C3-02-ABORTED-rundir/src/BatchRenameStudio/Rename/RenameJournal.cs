using System.Text;
using System.Text.Encodings.Web;
using System.Text.Json;

namespace BatchRenameStudio.Rename;

public sealed record RenameJournalEntry(string From, string To);

public sealed class RenameJournal
{
    public List<RenameJournalEntry> Entries { get; } = new();

    public void Add(string from, string to)
    {
        Entries.Add(new RenameJournalEntry(from, to));
    }

    public string ToJson()
    {
        var options = new JsonWriterOptions
        {
            Indented = true,
            Encoder = JavaScriptEncoder.UnsafeRelaxedJsonEscaping,
        };

        using var stream = new MemoryStream();
        using (var writer = new Utf8JsonWriter(stream, options))
        {
            writer.WriteStartArray();
            foreach (var entry in Entries)
            {
                writer.WriteStartObject();
                writer.WriteString("from", entry.From);
                writer.WriteString("to", entry.To);
                writer.WriteEndObject();
            }
            writer.WriteEndArray();
        }

        var decoded = new UTF8Encoding(false).GetString(stream.ToArray());
        decoded = decoded.Replace("\r\n", "\n");
        return decoded.TrimEnd('\n') + "\n";
    }

    public static RenameJournal FromJson(string json)
    {
        var journal = new RenameJournal();
        using var doc = JsonDocument.Parse(json);
        foreach (var el in doc.RootElement.EnumerateArray())
        {
            string from = el.GetProperty("from").GetString() ?? "";
            string to = el.GetProperty("to").GetString() ?? "";
            journal.Entries.Add(new RenameJournalEntry(from, to));
        }
        return journal;
    }

    /// <summary>
    /// Persists the journal under %LOCALAPPDATA%\BatchRenameStudio\undo\&lt;yyyyMMdd-HHmmss&gt;.json,
    /// pruning to the 20 newest journals. Any failure is swallowed by the caller
    /// (persistence must never fail a rename operation).
    /// </summary>
    public string Persist(DateTime timestampUtc)
    {
        string baseDir = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
            "BatchRenameStudio", "undo");
        Directory.CreateDirectory(baseDir);

        string fileName = timestampUtc.ToString("yyyyMMdd-HHmmss") + ".json";
        string path = Path.Combine(baseDir, fileName);

        File.WriteAllText(path, ToJson(), new UTF8Encoding(false));

        PruneOldJournals(baseDir);

        return path;
    }

    private static void PruneOldJournals(string baseDir)
    {
        var files = new DirectoryInfo(baseDir).GetFiles("*.json");
        if (files.Length <= 20)
        {
            return;
        }

        Array.Sort(files, (a, b) => b.Name.CompareTo(a.Name));
        for (int i = 20; i < files.Length; i++)
        {
            try { files[i].Delete(); } catch { }
        }
    }
}

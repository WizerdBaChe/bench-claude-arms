using System.Text;
using System.Text.Encodings.Web;
using System.Text.Json;

namespace BatchRenameStudio.Core;

public static class PlanWriter
{
    public static string ToJson(RenamePlan plan)
    {
        var options = new JsonWriterOptions
        {
            Indented = true,
            Encoder = JavaScriptEncoder.UnsafeRelaxedJsonEscaping,
        };

        using var stream = new MemoryStream();
        using (var writer = new Utf8JsonWriter(stream, options))
        {
            writer.WriteStartObject();
            writer.WriteNumber("schemaVersion", plan.SchemaVersion);

            writer.WriteStartArray("items");
            foreach (var item in plan.Items)
            {
                writer.WriteStartObject();
                writer.WriteString("original", item.Original);
                writer.WriteString("proposed", item.Proposed);
                writer.WriteString("status", StatusToString(item.Status));
                writer.WriteString("reason", item.Reason);
                writer.WriteEndObject();
            }
            writer.WriteEndArray();

            writer.WriteStartObject("summary");
            writer.WriteNumber("total", plan.Summary.Total);
            writer.WriteNumber("ok", plan.Summary.Ok);
            writer.WriteNumber("collision", plan.Summary.Collision);
            writer.WriteNumber("unchanged", plan.Summary.Unchanged);
            writer.WriteNumber("invalid", plan.Summary.Invalid);
            writer.WriteEndObject();

            writer.WriteEndObject();
        }

        var decoded = new UTF8Encoding(false).GetString(stream.ToArray());
        decoded = decoded.Replace("\r\n", "\n");
        decoded = decoded.TrimEnd('\n') + "\n";
        return decoded;
    }

    public static void WriteFile(string path, RenamePlan plan)
    {
        string json = ToJson(plan);
        string? dir = Path.GetDirectoryName(path);
        if (!string.IsNullOrEmpty(dir) && !Directory.Exists(dir))
        {
            Directory.CreateDirectory(dir);
        }
        File.WriteAllText(path, json, new UTF8Encoding(false));
    }

    private static string StatusToString(ItemStatus status)
    {
        return status switch
        {
            ItemStatus.Ok => "ok",
            ItemStatus.Collision => "collision",
            ItemStatus.Unchanged => "unchanged",
            ItemStatus.Invalid => "invalid",
            _ => throw new InvalidOperationException("unknown status"),
        };
    }
}

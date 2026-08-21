using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;

namespace BatchRenameStudio.Core;

public static class RuleSetJson
{
    public static RuleSet Parse(string json)
    {
        JsonDocument doc;
        try
        {
            doc = JsonDocument.Parse(json);
        }
        catch (JsonException ex)
        {
            throw new RuleParseException("malformed JSON: " + ex.Message);
        }

        using (doc)
        {
            var root = doc.RootElement;
            if (root.ValueKind != JsonValueKind.Object)
            {
                throw new RuleParseException("root JSON must be an object");
            }

            var rules = new RuleSet();

            if (TryGetProperty(root, "applyTo", out var applyToEl))
            {
                rules.ApplyTo = ParseEnum<ApplyToMode>(applyToEl, "applyTo");
            }

            if (TryGetProperty(root, "sort", out var sortEl))
            {
                rules.Sort = ParseEnum<SortMode>(sortEl, "sort");
            }

            if (TryGetProperty(root, "steps", out var stepsEl))
            {
                if (stepsEl.ValueKind != JsonValueKind.Array)
                {
                    throw new RuleParseException("steps must be an array");
                }
                foreach (var stepEl in stepsEl.EnumerateArray())
                {
                    rules.Steps.Add(ParseStep(stepEl));
                }
            }

            return rules;
        }
    }

    private static RuleStep ParseStep(JsonElement stepEl)
    {
        if (stepEl.ValueKind != JsonValueKind.Object)
        {
            throw new RuleParseException("step must be an object");
        }

        if (!TryGetProperty(stepEl, "op", out var opEl) || opEl.ValueKind != JsonValueKind.String)
        {
            throw new RuleParseException("step missing 'op'");
        }
        string op = opEl.GetString() ?? "";

        if (string.Equals(op, "replace", StringComparison.OrdinalIgnoreCase))
        {
            var step = new ReplaceStep
            {
                Find = GetString(stepEl, "find", ""),
                ReplaceWith = GetString(stepEl, "replaceWith", ""),
                Regex = GetBool(stepEl, "regex", false),
                IgnoreCase = GetBool(stepEl, "ignoreCase", false),
            };
            if (step.Regex)
            {
                try
                {
                    step.CompiledRegex = new Regex(
                        step.Find,
                        RegexOptions.CultureInvariant | (step.IgnoreCase ? RegexOptions.IgnoreCase : RegexOptions.None),
                        TimeSpan.FromSeconds(2));
                }
                catch (ArgumentException ex)
                {
                    throw new RuleParseException("invalid regex in replace step: " + ex.Message);
                }
            }
            return step;
        }
        else if (string.Equals(op, "insert", StringComparison.OrdinalIgnoreCase))
        {
            return new InsertStep
            {
                Text = GetString(stepEl, "text", ""),
                Position = GetEnum<InsertPosition>(stepEl, "position", InsertPosition.Prefix, "position"),
                Index = GetInt(stepEl, "index", 0),
            };
        }
        else if (string.Equals(op, "remove", StringComparison.OrdinalIgnoreCase))
        {
            return new RemoveStep
            {
                From = GetInt(stepEl, "from", 0),
                Count = GetInt(stepEl, "count", 0),
            };
        }
        else if (string.Equals(op, "sequence", StringComparison.OrdinalIgnoreCase))
        {
            return new SequenceStep
            {
                Pattern = GetString(stepEl, "pattern", ""),
                Start = GetInt(stepEl, "start", 1),
                Step = GetInt(stepEl, "step", 1),
                Position = GetEnum<SeqPosition>(stepEl, "position", SeqPosition.Prefix, "position"),
            };
        }
        else if (string.Equals(op, "case", StringComparison.OrdinalIgnoreCase))
        {
            return new CaseStep
            {
                Mode = GetEnum<CaseMode>(stepEl, "mode", CaseMode.Lower, "mode"),
            };
        }
        else if (string.Equals(op, "extension", StringComparison.OrdinalIgnoreCase))
        {
            return new ExtensionStep
            {
                Mode = GetEnum<ExtensionMode>(stepEl, "mode", ExtensionMode.Lower, "mode"),
                Value = GetString(stepEl, "value", ""),
            };
        }
        else
        {
            throw new RuleParseException("unknown step op: " + op);
        }
    }

    private static bool TryGetProperty(JsonElement obj, string name, out JsonElement value)
    {
        foreach (var prop in obj.EnumerateObject())
        {
            if (string.Equals(prop.Name, name, StringComparison.OrdinalIgnoreCase))
            {
                value = prop.Value;
                return true;
            }
        }
        value = default;
        return false;
    }

    private static string GetString(JsonElement obj, string name, string defaultValue)
    {
        if (TryGetProperty(obj, name, out var el) && el.ValueKind == JsonValueKind.String)
        {
            return el.GetString() ?? defaultValue;
        }
        return defaultValue;
    }

    private static bool GetBool(JsonElement obj, string name, bool defaultValue)
    {
        if (TryGetProperty(obj, name, out var el) &&
            (el.ValueKind == JsonValueKind.True || el.ValueKind == JsonValueKind.False))
        {
            return el.GetBoolean();
        }
        return defaultValue;
    }

    private static int GetInt(JsonElement obj, string name, int defaultValue)
    {
        if (TryGetProperty(obj, name, out var el) && el.ValueKind == JsonValueKind.Number && el.TryGetInt32(out int v))
        {
            return v;
        }
        return defaultValue;
    }

    private static T ParseEnum<T>(JsonElement el, string fieldName) where T : struct, Enum
    {
        if (el.ValueKind != JsonValueKind.String)
        {
            throw new RuleParseException("invalid value for " + fieldName);
        }
        string s = el.GetString() ?? "";
        foreach (var name in Enum.GetNames<T>())
        {
            if (string.Equals(name, s, StringComparison.OrdinalIgnoreCase))
            {
                return Enum.Parse<T>(name);
            }
        }
        throw new RuleParseException("unknown " + fieldName + " value: " + s);
    }

    private static T GetEnum<T>(JsonElement obj, string name, T defaultValue, string fieldName) where T : struct, Enum
    {
        if (TryGetProperty(obj, name, out var el))
        {
            return ParseEnum<T>(el, fieldName);
        }
        return defaultValue;
    }

    public static string Serialize(RuleSet rules)
    {
        var opts = new JsonSerializerOptions { WriteIndented = true };
        using var stream = new MemoryStream();
        using (var writer = new Utf8JsonWriter(stream, new JsonWriterOptions { Indented = true }))
        {
            writer.WriteStartObject();
            writer.WriteString("applyTo", EnumToString(rules.ApplyTo));
            writer.WriteString("sort", EnumToString(rules.Sort));
            writer.WriteStartArray("steps");
            foreach (var step in rules.Steps)
            {
                WriteStep(writer, step);
            }
            writer.WriteEndArray();
            writer.WriteEndObject();
        }
        return Encoding.UTF8.GetString(stream.ToArray());
    }

    private static void WriteStep(Utf8JsonWriter writer, RuleStep step)
    {
        writer.WriteStartObject();
        writer.WriteString("op", step.Op);
        switch (step)
        {
            case ReplaceStep replace:
                writer.WriteString("find", replace.Find);
                writer.WriteString("replaceWith", replace.ReplaceWith);
                writer.WriteBoolean("regex", replace.Regex);
                writer.WriteBoolean("ignoreCase", replace.IgnoreCase);
                break;
            case InsertStep insert:
                writer.WriteString("text", insert.Text);
                writer.WriteString("position", EnumToString(insert.Position));
                writer.WriteNumber("index", insert.Index);
                break;
            case RemoveStep remove:
                writer.WriteNumber("from", remove.From);
                writer.WriteNumber("count", remove.Count);
                break;
            case SequenceStep seq:
                writer.WriteString("pattern", seq.Pattern);
                writer.WriteNumber("start", seq.Start);
                writer.WriteNumber("step", seq.Step);
                writer.WriteString("position", EnumToString(seq.Position));
                break;
            case CaseStep caseStep:
                writer.WriteString("mode", EnumToString(caseStep.Mode));
                break;
            case ExtensionStep extStep:
                writer.WriteString("mode", EnumToString(extStep.Mode));
                writer.WriteString("value", extStep.Value);
                break;
        }
        writer.WriteEndObject();
    }

    private static string EnumToString<T>(T value) where T : struct, Enum
    {
        return value.ToString();
        // Note: PascalCase enum member names (e.g. "Lower") are written verbatim.
        // Parse() compares case-insensitively so this round-trips through Parse.
    }
}

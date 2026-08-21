namespace BatchRenameStudio.Core;

public static class NameValidator
{
    private static readonly char[] IllegalChars = { '<', '>', ':', '"', '/', '\\', '|', '?', '*' };

    private static readonly HashSet<string> ReservedNames = new(StringComparer.OrdinalIgnoreCase)
    {
        "CON", "PRN", "AUX", "NUL",
        "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
        "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",
    };

    // returns null when valid, otherwise a short reason string
    public static string? Validate(string proposedName)
    {
        if (proposedName.Length == 0)
        {
            return "empty name";
        }
        if (proposedName.Length > 255)
        {
            return "name too long";
        }
        foreach (char c in proposedName)
        {
            if (Array.IndexOf(IllegalChars, c) >= 0)
            {
                return "illegal character";
            }
        }
        foreach (char c in proposedName)
        {
            if (c < ' ')
            {
                return "control character";
            }
        }
        var parts = NameParts.Split(proposedName);
        if (ReservedNames.Contains(parts.Base))
        {
            return "reserved device name";
        }
        return null;
    }
}

using System.Globalization;
using System.Text.RegularExpressions;

namespace BatchRenameStudio.Core;

internal static class StepApplier
{
    internal static readonly Regex SeqPatternRegex = new(@"\{n:(0+)\}", RegexOptions.Compiled);

    // Computes the proposed name for a single file at 0-based processing index `i`.
    internal static string Apply(string originalName, RuleSet rules, int i)
    {
        if (rules.ApplyTo == ApplyToMode.Name)
        {
            var parts = NameParts.Split(originalName);
            string target = parts.Base;
            string ext = parts.Ext;

            foreach (var step in rules.Steps)
            {
                if (step is ExtensionStep extStep)
                {
                    ext = ApplyExtension(extStep, ext);
                }
                else
                {
                    target = ApplyNonExtension(step, target, i);
                }
            }

            return new NameParts(target, ext).Join();
        }
        else
        {
            string target = originalName;

            foreach (var step in rules.Steps)
            {
                if (step is ExtensionStep extStep)
                {
                    var p = NameParts.Split(target);
                    string newExt = ApplyExtension(extStep, p.Ext);
                    target = new NameParts(p.Base, newExt).Join();
                }
                else
                {
                    target = ApplyNonExtension(step, target, i);
                }
            }

            return target;
        }
    }

    private static string ApplyNonExtension(RuleStep step, string target, int i)
    {
        switch (step)
        {
            case ReplaceStep replace:
                return ApplyReplace(replace, target);
            case InsertStep insert:
                return ApplyInsert(insert, target);
            case RemoveStep remove:
                return ApplyRemove(remove, target);
            case SequenceStep seq:
                return ApplySequence(seq, target, i);
            case CaseStep caseStep:
                return ApplyCase(caseStep, target);
            default:
                return target;
        }
    }

    private static string ApplyReplace(ReplaceStep step, string target)
    {
        if (!step.Regex)
        {
            if (step.Find.Length == 0)
            {
                return target;
            }
            return target.Replace(step.Find, step.ReplaceWith,
                step.IgnoreCase ? StringComparison.OrdinalIgnoreCase : StringComparison.Ordinal);
        }
        else
        {
            var regex = step.CompiledRegex ?? new Regex(
                step.Find,
                RegexOptions.CultureInvariant | (step.IgnoreCase ? RegexOptions.IgnoreCase : RegexOptions.None),
                TimeSpan.FromSeconds(2));
            return regex.Replace(target, step.ReplaceWith);
        }
    }

    private static string ApplyInsert(InsertStep step, string target)
    {
        switch (step.Position)
        {
            case InsertPosition.Prefix:
                return step.Text + target;
            case InsertPosition.Suffix:
                return target + step.Text;
            case InsertPosition.Index:
                int idx = Math.Clamp(step.Index, 0, target.Length);
                return target.Insert(idx, step.Text);
            default:
                return target;
        }
    }

    private static string ApplyRemove(RemoveStep step, string target)
    {
        int from = Math.Clamp(step.From, 0, target.Length);
        int count = Math.Clamp(step.Count, 0, target.Length - from);
        return target.Remove(from, count);
    }

    private static string ApplySequence(SequenceStep step, string target, int i)
    {
        long value = (long)step.Start + (long)step.Step * i;
        string rendered = RenderSequencePattern(step.Pattern, value);

        return step.Position switch
        {
            SeqPosition.Prefix => rendered + target,
            SeqPosition.Suffix => target + rendered,
            _ => target,
        };
    }

    internal static string RenderSequencePattern(string pattern, long value)
    {
        var match = SeqPatternRegex.Match(pattern);
        if (!match.Success)
        {
            return pattern;
        }

        int width = match.Groups[1].Length;
        string formatted = value.ToString(new string('0', width), CultureInfo.InvariantCulture);

        return pattern.Substring(0, match.Index) + formatted + pattern.Substring(match.Index + match.Length);
    }

    private static string ApplyCase(CaseStep step, string target)
    {
        switch (step.Mode)
        {
            case CaseMode.Upper:
                return target.ToUpperInvariant();
            case CaseMode.Lower:
                return target.ToLowerInvariant();
            case CaseMode.Title:
                return ApplyTitleCase(target);
            default:
                return target;
        }
    }

    private static string ApplyTitleCase(string target)
    {
        var chars = new char[target.Length];
        bool startOfRun = true;
        for (int i = 0; i < target.Length; i++)
        {
            char c = target[i];
            if (char.IsLetter(c))
            {
                chars[i] = startOfRun ? char.ToUpperInvariant(c) : char.ToLowerInvariant(c);
                startOfRun = false;
            }
            else
            {
                chars[i] = c;
                startOfRun = true;
            }
        }
        return new string(chars);
    }

    private static string ApplyExtension(ExtensionStep step, string ext)
    {
        switch (step.Mode)
        {
            case ExtensionMode.Lower:
                return ext.ToLowerInvariant();
            case ExtensionMode.Upper:
                return ext.ToUpperInvariant();
            case ExtensionMode.Set:
                return step.Value;
            default:
                return ext;
        }
    }
}

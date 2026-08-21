using System.Globalization;
using BatchRenameStudio.Core;

namespace BatchRenameStudio.Gui;

/// <summary>
/// Produces a human-readable, one-line Traditional-Chinese summary of a RuleStep
/// for display in the step ListView. Display-only: never used by the preview
/// pipeline, which always goes through PlanBuilder/StepApplier in Core.
/// </summary>
public static class StepDescriber
{
    public static string Describe(RuleStep step)
    {
        switch (step)
        {
            case ReplaceStep r:
                {
                    var mods = new List<string>();
                    if (r.Regex) mods.Add("regex");
                    if (r.IgnoreCase) mods.Add("忽略大小寫");
                    string modText = mods.Count > 0 ? $"（{string.Join(", ", mods)}）" : "";
                    return $"取代 (replace)：'{r.Find}' → '{r.ReplaceWith}'{modText}";
                }
            case InsertStep i:
                {
                    string pos = i.Position switch
                    {
                        InsertPosition.Prefix => "前置",
                        InsertPosition.Suffix => "後置",
                        InsertPosition.Index => $"位於索引 {i.Index}",
                        _ => i.Position.ToString(),
                    };
                    return $"插入 (insert)：'{i.Text}'，{pos}";
                }
            case RemoveStep rm:
                return $"刪除 (remove)：從位置 {rm.From} 起刪除 {rm.Count} 字";
            case SequenceStep s:
                {
                    string pos = s.Position == SeqPosition.Prefix ? "前置" : "後置";
                    string stepText = s.Step >= 0 ? "+" + s.Step.ToString(CultureInfo.InvariantCulture) : s.Step.ToString(CultureInfo.InvariantCulture);
                    return $"序號 (sequence)：{s.Pattern} 從 {s.Start} 每次 {stepText}，{pos}";
                }
            case CaseStep c:
                {
                    string mode = c.Mode switch
                    {
                        CaseMode.Upper => "全部大寫",
                        CaseMode.Lower => "全部小寫",
                        CaseMode.Title => "每字首大寫",
                        _ => c.Mode.ToString(),
                    };
                    return $"大小寫 (case)：{mode}";
                }
            case ExtensionStep e:
                {
                    string mode = e.Mode switch
                    {
                        ExtensionMode.Lower => "小寫",
                        ExtensionMode.Upper => "大寫",
                        ExtensionMode.Set => $"指定 '{e.Value}'",
                        _ => e.Mode.ToString(),
                    };
                    return $"副檔名 (extension)：{mode}";
                }
            default:
                return step.Op;
        }
    }
}

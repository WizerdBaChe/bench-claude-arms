using System.Globalization;
using System.Text.RegularExpressions;
using BatchRenameStudio.Core;

namespace BatchRenameStudio.Gui;

/// <summary>
/// Modal dialog used for both adding and editing a single RuleStep.
/// Purely a UI editor: it only ever constructs Core.RuleStep instances and
/// never evaluates or applies them.
///
/// Layout is entirely TableLayoutPanel/FlowLayoutPanel + AutoSize driven (no
/// pixel Location literals) so the dialog scales correctly at any DPI: every
/// row grows with the actual (already-scaled) font/control metrics instead
/// of an assumed 96dpi row height.
/// </summary>
public sealed class StepEditorForm : Form
{
    private readonly ComboBox _opCombo;
    private readonly TableLayoutPanel _rootTable;
    private Control? _currentOpPanel;

    // replace panel
    private readonly TableLayoutPanel _replacePanel;
    private readonly TextBox _replaceFind;
    private readonly TextBox _replaceWith;
    private readonly CheckBox _replaceRegex;
    private readonly CheckBox _replaceIgnoreCase;
    private readonly Label _replaceError;

    // insert panel
    private readonly TableLayoutPanel _insertPanel;
    private readonly TextBox _insertText;
    private readonly ComboBox _insertPosition;
    private readonly NumericUpDown _insertIndex;

    // remove panel
    private readonly TableLayoutPanel _removePanel;
    private readonly NumericUpDown _removeFrom;
    private readonly NumericUpDown _removeCount;

    // sequence panel
    private readonly TableLayoutPanel _sequencePanel;
    private readonly TextBox _seqPattern;
    private readonly NumericUpDown _seqStart;
    private readonly NumericUpDown _seqStep;
    private readonly ComboBox _seqPosition;
    private readonly Label _seqExample;
    private readonly Label _seqWarning;

    // case panel
    private readonly TableLayoutPanel _casePanel;
    private readonly ComboBox _caseMode;

    // extension panel
    private readonly TableLayoutPanel _extensionPanel;
    private readonly ComboBox _extMode;
    private readonly TextBox _extValue;

    private readonly Button _okButton;
    private readonly Button _cancelButton;

    private static readonly string[] OpLabels =
    {
        "取代 (replace)", "插入 (insert)", "刪除 (remove)", "序號 (sequence)", "大小寫 (case)", "副檔名 (extension)",
    };

    public RuleStep? Result { get; private set; }

    public StepEditorForm(RuleStep? existing)
    {
        // See MainForm for why we capture the current metrics as baseline
        // instead of a stale design-time (6,13) value: everything here is
        // already sized from the live (already-DPI-scaled) font/metrics via
        // AutoSize + LogicalToDeviceUnits, so we do not want a second,
        // independent rescale pass to run on top of that.
        AutoScaleMode = AutoScaleMode.Font;
        AutoScaleDimensions = CurrentAutoScaleDimensions;

        Text = existing == null ? "新增步驟" : "編輯步驟";
        FormBorderStyle = FormBorderStyle.FixedDialog;
        MinimizeBox = false;
        MaximizeBox = false;
        StartPosition = FormStartPosition.CenterParent;
        AutoSize = true;
        AutoSizeMode = AutoSizeMode.GrowAndShrink;
        KeyPreview = true;

        _rootTable = new TableLayoutPanel
        {
            Dock = DockStyle.Fill,
            AutoSize = true,
            AutoSizeMode = AutoSizeMode.GrowAndShrink,
            ColumnCount = 1,
            RowCount = 3,
            Padding = new Padding(12),
        };
        _rootTable.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100f));
        _rootTable.RowStyles.Add(new RowStyle(SizeType.AutoSize));
        _rootTable.RowStyles.Add(new RowStyle(SizeType.AutoSize));
        _rootTable.RowStyles.Add(new RowStyle(SizeType.AutoSize));
        Controls.Add(_rootTable);

        // ---- row 0: op selector ----
        var opRow = new FlowLayoutPanel { AutoSize = true, FlowDirection = FlowDirection.LeftToRight, WrapContents = false };
        opRow.Controls.Add(new Label { Text = "類型", AutoSize = true, Margin = new Padding(3, 6, 8, 3) });
        _opCombo = new ComboBox
        {
            DropDownStyle = ComboBoxStyle.DropDownList,
            Width = LogicalToDeviceUnits(280),
            Margin = new Padding(3),
        };
        _opCombo.Items.AddRange(OpLabels);
        opRow.Controls.Add(_opCombo);
        _rootTable.Controls.Add(opRow, 0, 0);

        // ---- row 1: op-specific fields (only one panel attached at a time) ----
        var placeholder = new Panel { AutoSize = true, Margin = new Padding(0) };
        _rootTable.Controls.Add(placeholder, 0, 1);
        _currentOpPanel = placeholder;

        // ---- row 2: OK / cancel ----
        var buttonRow = new FlowLayoutPanel
        {
            AutoSize = true,
            FlowDirection = FlowDirection.RightToLeft,
            WrapContents = false,
            Anchor = AnchorStyles.Right,
        };
        _cancelButton = new Button { Text = "取消", AutoSize = true, Margin = new Padding(3), DialogResult = DialogResult.Cancel };
        _okButton = new Button { Text = "確定", AutoSize = true, Margin = new Padding(3), DialogResult = DialogResult.OK };
        buttonRow.Controls.Add(_cancelButton);
        buttonRow.Controls.Add(_okButton);
        _rootTable.Controls.Add(buttonRow, 0, 2);
        AcceptButton = _okButton;
        CancelButton = _cancelButton;
        _okButton.Click += (_, _) => OnOk();

        // ---- build each op panel ----
        _replacePanel = NewFieldsPanel();
        _replaceFind = new TextBox { Width = LogicalToDeviceUnits(300) };
        _replaceWith = new TextBox { Width = LogicalToDeviceUnits(300) };
        AddRow(_replacePanel, Lbl("尋找"), _replaceFind);
        AddRow(_replacePanel, Lbl("取代為"), _replaceWith);
        _replaceRegex = new CheckBox { Text = "使用正規表示式 (regex)", AutoSize = true };
        _replaceIgnoreCase = new CheckBox { Text = "忽略大小寫", AutoSize = true };
        AddFullRow(_replacePanel, _replaceRegex);
        AddFullRow(_replacePanel, _replaceIgnoreCase);
        AddFullRow(_replacePanel, new Label { Text = "regex 模式下可用 $1 引用群組", AutoSize = true, ForeColor = SystemColors.GrayText });
        _replaceError = new Label { Text = "", AutoSize = true, ForeColor = Color.DarkRed, MaximumSize = LogicalToDeviceUnits(new Size(380, 0)) };
        AddFullRow(_replacePanel, _replaceError);
        _replaceFind.TextChanged += (_, _) => ValidateReplace();
        _replaceRegex.CheckedChanged += (_, _) => ValidateReplace();

        _insertPanel = NewFieldsPanel();
        _insertText = new TextBox { Width = LogicalToDeviceUnits(300) };
        AddRow(_insertPanel, Lbl("文字"), _insertText);
        _insertPosition = new ComboBox { DropDownStyle = ComboBoxStyle.DropDownList, Width = LogicalToDeviceUnits(220) };
        _insertPosition.Items.AddRange(new object[] { "前置 (prefix)", "後置 (suffix)", "指定位置 (index)" });
        AddRow(_insertPanel, Lbl("位置"), _insertPosition);
        _insertIndex = new NumericUpDown { Width = LogicalToDeviceUnits(100), Minimum = 0, Maximum = 9999 };
        AddRow(_insertPanel, Lbl("索引"), _insertIndex);
        _insertPosition.SelectedIndexChanged += (_, _) => _insertIndex.Enabled = _insertPosition.SelectedIndex == 2;

        _removePanel = NewFieldsPanel();
        _removeFrom = new NumericUpDown { Width = LogicalToDeviceUnits(100), Minimum = 0, Maximum = 9999 };
        AddRow(_removePanel, Lbl("起始位置"), _removeFrom);
        _removeCount = new NumericUpDown { Width = LogicalToDeviceUnits(100), Minimum = 0, Maximum = 9999 };
        AddRow(_removePanel, Lbl("刪除字數"), _removeCount);

        _sequencePanel = NewFieldsPanel();
        _seqPattern = new TextBox { Width = LogicalToDeviceUnits(300), Text = "{n:000}_" };
        AddRow(_sequencePanel, Lbl("樣式"), _seqPattern);
        var startStepFlow = new FlowLayoutPanel { AutoSize = true, WrapContents = false, FlowDirection = FlowDirection.LeftToRight };
        startStepFlow.Controls.Add(new Label { Text = "起始值", AutoSize = true, Margin = new Padding(0, 6, 4, 3) });
        _seqStart = new NumericUpDown { Width = LogicalToDeviceUnits(90), Minimum = -9999, Maximum = 9999, Value = 1, Margin = new Padding(0, 3, 16, 3) };
        startStepFlow.Controls.Add(_seqStart);
        startStepFlow.Controls.Add(new Label { Text = "間隔", AutoSize = true, Margin = new Padding(0, 6, 4, 3) });
        _seqStep = new NumericUpDown { Width = LogicalToDeviceUnits(90), Minimum = -9999, Maximum = 9999, Value = 1, Margin = new Padding(0, 3, 0, 3) };
        startStepFlow.Controls.Add(_seqStep);
        AddFullRow(_sequencePanel, startStepFlow);
        _seqPosition = new ComboBox { DropDownStyle = ComboBoxStyle.DropDownList, Width = LogicalToDeviceUnits(150) };
        _seqPosition.Items.AddRange(new object[] { "前置", "後置" });
        AddRow(_sequencePanel, Lbl("位置"), _seqPosition);
        _seqExample = new Label { Text = "", AutoSize = true };
        AddFullRow(_sequencePanel, _seqExample);
        _seqWarning = new Label
        {
            Text = "樣式中沒有 {n:000} 這類序號標記，將被當作固定文字",
            AutoSize = true,
            MaximumSize = LogicalToDeviceUnits(new Size(380, 0)),
            ForeColor = Color.DarkOrange,
            Visible = false,
        };
        AddFullRow(_sequencePanel, _seqWarning);
        _seqPattern.TextChanged += (_, _) => UpdateSequencePreview();
        _seqStart.ValueChanged += (_, _) => UpdateSequencePreview();
        _seqStep.ValueChanged += (_, _) => UpdateSequencePreview();
        _seqPosition.SelectedIndexChanged += (_, _) => UpdateSequencePreview();

        _casePanel = NewFieldsPanel();
        _caseMode = new ComboBox { DropDownStyle = ComboBoxStyle.DropDownList, Width = LogicalToDeviceUnits(250) };
        _caseMode.Items.AddRange(new object[] { "全部大寫 (upper)", "全部小寫 (lower)", "每字首大寫 (title)" });
        AddRow(_casePanel, Lbl("模式"), _caseMode);

        _extensionPanel = NewFieldsPanel();
        _extMode = new ComboBox { DropDownStyle = ComboBoxStyle.DropDownList, Width = LogicalToDeviceUnits(200) };
        _extMode.Items.AddRange(new object[] { "小寫 (lower)", "大寫 (upper)", "指定 (set)" });
        AddRow(_extensionPanel, Lbl("模式"), _extMode);
        _extValue = new TextBox { Width = LogicalToDeviceUnits(200) };
        AddRow(_extensionPanel, Lbl("副檔名"), _extValue);
        AddFullRow(_extensionPanel, new Label { Text = "不要輸入前面的點", AutoSize = true, ForeColor = SystemColors.GrayText });
        _extMode.SelectedIndexChanged += (_, _) => _extValue.Enabled = _extMode.SelectedIndex == 2;

        _opCombo.SelectedIndexChanged += (_, _) => ShowPanelForSelectedOp();

        LoadFrom(existing);
    }

    private static Label Lbl(string text) => new Label { Text = text, AutoSize = true };

    private TableLayoutPanel NewFieldsPanel()
    {
        var p = new TableLayoutPanel
        {
            AutoSize = true,
            AutoSizeMode = AutoSizeMode.GrowAndShrink,
            ColumnCount = 2,
            RowCount = 0,
            Padding = new Padding(0, 6, 0, 0),
        };
        p.ColumnStyles.Add(new ColumnStyle(SizeType.AutoSize));
        p.ColumnStyles.Add(new ColumnStyle(SizeType.AutoSize));
        return p;
    }

    private static void AddRow(TableLayoutPanel panel, Control label, Control control)
    {
        int row = panel.RowCount;
        panel.RowCount = row + 1;
        panel.RowStyles.Add(new RowStyle(SizeType.AutoSize));
        label.Margin = new Padding(3, 6, 8, 3);
        control.Margin = new Padding(3, 3, 3, 3);
        control.Anchor = AnchorStyles.Left;
        panel.Controls.Add(label, 0, row);
        panel.Controls.Add(control, 1, row);
    }

    private static void AddFullRow(TableLayoutPanel panel, Control full)
    {
        int row = panel.RowCount;
        panel.RowCount = row + 1;
        panel.RowStyles.Add(new RowStyle(SizeType.AutoSize));
        full.Margin = new Padding(3, 3, 3, 3);
        panel.Controls.Add(full, 0, row);
        panel.SetColumnSpan(full, 2);
    }

    private void LoadFrom(RuleStep? existing)
    {
        // Defaults for every panel.
        _insertPosition.SelectedIndex = 0;
        _insertIndex.Enabled = false;
        _seqPosition.SelectedIndex = 0;
        _caseMode.SelectedIndex = 1;
        _extMode.SelectedIndex = 0;
        _extValue.Enabled = false;

        int opIndex = existing switch
        {
            ReplaceStep => 0,
            InsertStep => 1,
            RemoveStep => 2,
            SequenceStep => 3,
            CaseStep => 4,
            ExtensionStep => 5,
            _ => 0,
        };

        switch (existing)
        {
            case ReplaceStep r:
                _replaceFind.Text = r.Find;
                _replaceWith.Text = r.ReplaceWith;
                _replaceRegex.Checked = r.Regex;
                _replaceIgnoreCase.Checked = r.IgnoreCase;
                break;
            case InsertStep i:
                _insertText.Text = i.Text;
                _insertPosition.SelectedIndex = (int)i.Position;
                _insertIndex.Value = Math.Clamp(i.Index, 0, 9999);
                _insertIndex.Enabled = i.Position == InsertPosition.Index;
                break;
            case RemoveStep rm:
                _removeFrom.Value = Math.Clamp(rm.From, 0, 9999);
                _removeCount.Value = Math.Clamp(rm.Count, 0, 9999);
                break;
            case SequenceStep s:
                _seqPattern.Text = s.Pattern;
                _seqStart.Value = Math.Clamp(s.Start, -9999, 9999);
                _seqStep.Value = Math.Clamp(s.Step, -9999, 9999);
                _seqPosition.SelectedIndex = (int)s.Position;
                break;
            case CaseStep c:
                _caseMode.SelectedIndex = (int)c.Mode;
                break;
            case ExtensionStep e:
                _extMode.SelectedIndex = (int)e.Mode;
                _extValue.Text = e.Value;
                _extValue.Enabled = e.Mode == ExtensionMode.Set;
                break;
            default:
                _replaceFind.Text = "";
                _replaceWith.Text = "";
                break;
        }

        _opCombo.SelectedIndex = opIndex;
        ShowPanelForSelectedOp();
        ValidateReplace();
        UpdateSequencePreview();
    }

    private void ShowPanelForSelectedOp()
    {
        Control next = _opCombo.SelectedIndex switch
        {
            0 => _replacePanel,
            1 => _insertPanel,
            2 => _removePanel,
            3 => _sequencePanel,
            4 => _casePanel,
            5 => _extensionPanel,
            _ => _replacePanel,
        };

        if (!ReferenceEquals(next, _currentOpPanel))
        {
            _rootTable.SuspendLayout();
            if (_currentOpPanel != null)
            {
                _rootTable.Controls.Remove(_currentOpPanel);
            }
            next.Dock = DockStyle.Fill;
            _rootTable.Controls.Add(next, 0, 1);
            _currentOpPanel = next;
            _rootTable.ResumeLayout(true);
        }

        ValidateReplace();
    }

    private void ValidateReplace()
    {
        if (_opCombo.SelectedIndex != 0)
        {
            _okButton.Enabled = true;
            return;
        }

        if (!_replaceRegex.Checked)
        {
            _replaceError.Text = "";
            _okButton.Enabled = true;
            return;
        }

        try
        {
            _ = new Regex(_replaceFind.Text, RegexOptions.CultureInvariant, TimeSpan.FromSeconds(2));
            _replaceError.Text = "";
            _okButton.Enabled = true;
        }
        catch (ArgumentException ex)
        {
            _replaceError.Text = "regex 錯誤：" + ex.Message;
            _okButton.Enabled = false;
        }
    }

    private void UpdateSequencePreview()
    {
        if (_opCombo.SelectedIndex != 3)
        {
            return;
        }

        string pattern = _seqPattern.Text;
        var match = Regex.Match(pattern, @"\{n:(0+)\}");
        string rendered;
        if (match.Success)
        {
            int width = match.Groups[1].Length;
            int value = (int)_seqStart.Value;
            rendered = pattern.Substring(0, match.Index)
                + value.ToString(new string('0', width), CultureInfo.InvariantCulture)
                + pattern.Substring(match.Index + match.Length);
            _seqWarning.Visible = false;
        }
        else
        {
            rendered = pattern;
            _seqWarning.Visible = true;
        }

        _seqExample.Text = $"第 1 個檔案會得到：{rendered}";
    }

    private void OnOk()
    {
        try
        {
            Result = _opCombo.SelectedIndex switch
            {
                0 => BuildReplace(),
                1 => BuildInsert(),
                2 => BuildRemove(),
                3 => BuildSequence(),
                4 => BuildCase(),
                5 => BuildExtension(),
                _ => null,
            };
        }
        catch (Exception ex)
        {
            MessageBox.Show(this, ex.Message, "無法建立步驟", MessageBoxButtons.OK, MessageBoxIcon.Error);
            DialogResult = DialogResult.None;
        }
    }

    private RuleStep BuildReplace() => new ReplaceStep
    {
        Find = _replaceFind.Text,
        ReplaceWith = _replaceWith.Text,
        Regex = _replaceRegex.Checked,
        IgnoreCase = _replaceIgnoreCase.Checked,
    };

    private RuleStep BuildInsert() => new InsertStep
    {
        Text = _insertText.Text,
        Position = (InsertPosition)_insertPosition.SelectedIndex,
        Index = (int)_insertIndex.Value,
    };

    private RuleStep BuildRemove() => new RemoveStep
    {
        From = (int)_removeFrom.Value,
        Count = (int)_removeCount.Value,
    };

    private RuleStep BuildSequence() => new SequenceStep
    {
        Pattern = _seqPattern.Text,
        Start = (int)_seqStart.Value,
        Step = (int)_seqStep.Value,
        Position = (SeqPosition)_seqPosition.SelectedIndex,
    };

    private RuleStep BuildCase() => new CaseStep
    {
        Mode = (CaseMode)_caseMode.SelectedIndex,
    };

    private RuleStep BuildExtension() => new ExtensionStep
    {
        Mode = (ExtensionMode)_extMode.SelectedIndex,
        Value = _extValue.Text,
    };
}

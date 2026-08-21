using System.Text;
using BatchRenameStudio.Core;
using BatchRenameStudio.Rename;

namespace BatchRenameStudio.Gui;

/// <summary>
/// DataGridView with double buffering turned on via the protected property
/// (not exposed publicly by the base control) to keep repaints smooth when
/// filling thousands of rows.
/// </summary>
public sealed class PreviewGrid : DataGridView
{
    public PreviewGrid()
    {
        DoubleBuffered = true;
    }
}

public sealed class MainForm : Form
{
    // ---- top bar controls ----
    private readonly TextBox _txtFolder;
    private readonly Button _btnBrowse;
    private readonly Button _btnRescan;
    private readonly ComboBox _cmbApplyTo;
    private readonly ComboBox _cmbSort;

    // ---- left: steps ----
    private readonly ListView _lvSteps;
    private readonly Button _btnAdd;
    private readonly ContextMenuStrip _addMenu;
    private readonly Button _btnEditStep;
    private readonly Button _btnDeleteStep;
    private readonly Button _btnMoveUp;
    private readonly Button _btnMoveDown;
    private readonly Button _btnClearSteps;
    private readonly Button _btnLoadRules;
    private readonly Button _btnSaveRules;

    // ---- right: preview ----
    private readonly PreviewGrid _grid;

    // ---- bottom bar ----
    private readonly Label _lblCounters;
    private readonly Label _lblMessage;
    private readonly Button _btnApply;
    private readonly Button _btnUndo;

    // ---- state ----
    private string? _folder;
    private List<FileEntry> _scannedFiles = new();
    private readonly List<RuleStep> _steps = new();
    private RenamePlan? _lastPlan;
    private string? _undoDir;
    private RenameJournal? _undoJournal;

    // Colors kept desaturated on purpose so text stays readable (per work card).
    private static readonly Color UnchangedBack = Color.FromArgb(240, 240, 240);
    private static readonly Color UnchangedFore = Color.FromArgb(110, 110, 110);
    private static readonly Color CollisionBack = Color.FromArgb(255, 236, 196);
    private static readonly Color InvalidBack = Color.FromArgb(248, 214, 214);

    public MainForm()
    {
        // Layout is content/AutoSize driven (see below), so we do not want the
        // base Form autoscale engine to ALSO rescale our already-DPI-scaled
        // literals against a stale design-time baseline (that would double
        // scale). Capturing CurrentAutoScaleDimensions as the baseline makes
        // the initial ratio 1:1 while still letting WinForms react correctly
        // if the window is later dragged to a monitor with a different DPI.
        AutoScaleMode = AutoScaleMode.Font;
        AutoScaleDimensions = CurrentAutoScaleDimensions;

        Text = "Batch Rename Studio";
        StartPosition = FormStartPosition.CenterScreen;
        Size = LogicalToDeviceUnits(new Size(1100, 700));
        MinimumSize = LogicalToDeviceUnits(new Size(900, 560));
        KeyPreview = true;

        // ================= TOP BAR =================
        var topPanel = new FlowLayoutPanel
        {
            Dock = DockStyle.Top,
            FlowDirection = FlowDirection.LeftToRight,
            WrapContents = true,
            AutoSize = true,
            AutoSizeMode = AutoSizeMode.GrowAndShrink,
            Padding = new Padding(6),
        };

        var lblFolder = new Label { Text = "資料夾", AutoSize = true, Margin = new Padding(3, 9, 3, 3) };
        _txtFolder = new TextBox { ReadOnly = true, Width = LogicalToDeviceUnits(300), Margin = new Padding(3, 5, 3, 3) };
        _btnBrowse = new Button { Text = "瀏覽…", AutoSize = true, Margin = new Padding(3, 3, 3, 3) };
        _btnRescan = new Button { Text = "重新掃描 (F5)", AutoSize = true, Margin = new Padding(3, 3, 12, 3) };

        var lblApplyTo = new Label { Text = "套用範圍", AutoSize = true, Margin = new Padding(3, 9, 3, 3) };
        _cmbApplyTo = new ComboBox { DropDownStyle = ComboBoxStyle.DropDownList, Width = LogicalToDeviceUnits(190), Margin = new Padding(3, 5, 12, 3) };
        _cmbApplyTo.Items.AddRange(new object[] { "僅檔名 (name)", "檔名＋副檔名 (nameAndExtension)" });
        _cmbApplyTo.SelectedIndex = 0;

        var lblSort = new Label { Text = "排序", AutoSize = true, Margin = new Padding(3, 9, 3, 3) };
        _cmbSort = new ComboBox { DropDownStyle = ComboBoxStyle.DropDownList, Width = LogicalToDeviceUnits(150), Margin = new Padding(3, 5, 3, 3) };
        _cmbSort.Items.AddRange(new object[] { "名稱 (name)", "建立時間 (created)", "修改時間 (modified)" });
        _cmbSort.SelectedIndex = 0;

        topPanel.Controls.AddRange(new Control[]
        {
            lblFolder, _txtFolder, _btnBrowse, _btnRescan, lblApplyTo, _cmbApplyTo, lblSort, _cmbSort,
        });
        Controls.Add(topPanel);

        // ================= BOTTOM BAR =================
        var bottomPanel = new TableLayoutPanel
        {
            Dock = DockStyle.Bottom,
            AutoSize = true,
            AutoSizeMode = AutoSizeMode.GrowAndShrink,
            ColumnCount = 2,
            RowCount = 1,
            Padding = new Padding(6),
        };
        bottomPanel.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100f));
        bottomPanel.ColumnStyles.Add(new ColumnStyle(SizeType.AutoSize));
        bottomPanel.RowStyles.Add(new RowStyle(SizeType.AutoSize));

        var infoFlow = new FlowLayoutPanel
        {
            Dock = DockStyle.Fill,
            AutoSize = true,
            WrapContents = true,
            FlowDirection = FlowDirection.LeftToRight,
        };
        _lblCounters = new Label
        {
            AutoSize = true,
            Margin = new Padding(3, 7, 18, 3),
            Text = "共 0 個 · 可執行 0 · 撞名 0 · 未變更 0 · 不合法 0",
        };
        _lblMessage = new Label { AutoSize = true, Margin = new Padding(3, 7, 3, 3), Text = "尚未選擇資料夾" };
        infoFlow.Controls.Add(_lblCounters);
        infoFlow.Controls.Add(_lblMessage);

        // RightToLeft so buttons anchor to the right edge and never run off it;
        // the first control added lands rightmost.
        var buttonFlowBottom = new FlowLayoutPanel
        {
            AutoSize = true,
            FlowDirection = FlowDirection.RightToLeft,
            WrapContents = false,
            Anchor = AnchorStyles.Right,
        };
        _btnApply = new Button { Text = "套用重新命名", AutoSize = true, Margin = new Padding(3) };
        _btnUndo = new Button { Text = "復原上一批", AutoSize = true, Margin = new Padding(3), Enabled = false };
        buttonFlowBottom.Controls.Add(_btnApply);
        buttonFlowBottom.Controls.Add(_btnUndo);

        bottomPanel.Controls.Add(infoFlow, 0, 0);
        bottomPanel.Controls.Add(buttonFlowBottom, 1, 0);
        Controls.Add(bottomPanel);

        // ================= CENTRE SPLIT =================
        var split = new SplitContainer
        {
            Dock = DockStyle.Fill,
            Orientation = Orientation.Vertical,
            SplitterWidth = LogicalToDeviceUnits(6),
        };

        // ---- LEFT: steps group ----
        var leftGroup = new GroupBox { Text = "規則步驟", Dock = DockStyle.Fill };
        _lvSteps = new ListView
        {
            Dock = DockStyle.Top,
            Height = LogicalToDeviceUnits(280),
            View = View.Details,
            FullRowSelect = true,
            HideSelection = false,
            MultiSelect = false,
        };
        _lvSteps.Columns.Add("#", LogicalToDeviceUnits(32));
        _lvSteps.Columns.Add("步驟", LogicalToDeviceUnits(260));
        _lvSteps.Resize += (_, _) =>
        {
            int fit = _lvSteps.ClientSize.Width - _lvSteps.Columns[0].Width - LogicalToDeviceUnits(4);
            if (fit > LogicalToDeviceUnits(80))
            {
                _lvSteps.Columns[1].Width = fit;
            }
        };

        var buttonFlow = new FlowLayoutPanel
        {
            Dock = DockStyle.Fill,
            FlowDirection = FlowDirection.TopDown,
            WrapContents = false,
            AutoSize = true,
            AutoSizeMode = AutoSizeMode.GrowAndShrink,
            Padding = new Padding(4),
        };

        _addMenu = new ContextMenuStrip();
        _addMenu.Items.Add("取代 (replace)", null, (_, _) => AddStep(new ReplaceStep()));
        _addMenu.Items.Add("插入 (insert)", null, (_, _) => AddStep(new InsertStep()));
        _addMenu.Items.Add("刪除 (remove)", null, (_, _) => AddStep(new RemoveStep()));
        _addMenu.Items.Add("序號 (sequence)", null, (_, _) => AddStep(new SequenceStep()));
        _addMenu.Items.Add("大小寫 (case)", null, (_, _) => AddStep(new CaseStep()));
        _addMenu.Items.Add("副檔名 (extension)", null, (_, _) => AddStep(new ExtensionStep()));

        var stepButtonSize = LogicalToDeviceUnits(new Size(150, 0));

        _btnAdd = new Button { Text = "新增 ▾", AutoSize = true, MinimumSize = stepButtonSize, Margin = new Padding(3) };
        _btnAdd.Click += (_, _) => _addMenu.Show(_btnAdd, new Point(0, _btnAdd.Height));
        _btnEditStep = new Button { Text = "編輯…", AutoSize = true, MinimumSize = stepButtonSize, Margin = new Padding(3) };
        _btnEditStep.Click += (_, _) => EditSelectedStep();
        _btnDeleteStep = new Button { Text = "刪除", AutoSize = true, MinimumSize = stepButtonSize, Margin = new Padding(3) };
        _btnDeleteStep.Click += (_, _) => DeleteSelectedStep();
        _btnMoveUp = new Button { Text = "▲ 上移", AutoSize = true, MinimumSize = stepButtonSize, Margin = new Padding(3) };
        _btnMoveUp.Click += (_, _) => MoveSelectedStep(-1);
        _btnMoveDown = new Button { Text = "▼ 下移", AutoSize = true, MinimumSize = stepButtonSize, Margin = new Padding(3) };
        _btnMoveDown.Click += (_, _) => MoveSelectedStep(1);
        _btnClearSteps = new Button { Text = "清空", AutoSize = true, MinimumSize = stepButtonSize, Margin = new Padding(3) };
        _btnClearSteps.Click += (_, _) => ClearSteps();
        _btnLoadRules = new Button { Text = "載入規則…", AutoSize = true, MinimumSize = stepButtonSize, Margin = new Padding(3) };
        _btnLoadRules.Click += (_, _) => LoadRules();
        _btnSaveRules = new Button { Text = "儲存規則…", AutoSize = true, MinimumSize = stepButtonSize, Margin = new Padding(3) };
        _btnSaveRules.Click += (_, _) => SaveRules();

        buttonFlow.Controls.AddRange(new Control[]
        {
            _btnAdd, _btnEditStep, _btnDeleteStep, _btnMoveUp, _btnMoveDown, _btnClearSteps, _btnLoadRules, _btnSaveRules,
        });

        // Dock ordering matters: edge-docked controls (_lvSteps, Dock=Top)
        // must be added BEFORE the Dock=Fill control (buttonFlow), matching
        // the same top/bottom-before-fill convention used for the Form
        // itself below. Adding Fill first made it claim the whole GroupBox
        // client area before the ListView carved its Top slice out of it,
        // producing an overlapping/clipped header render at high DPI.
        leftGroup.Controls.Add(_lvSteps);
        leftGroup.Controls.Add(buttonFlow);
        split.Panel1.Controls.Add(leftGroup);

        // ---- RIGHT: preview grid ----
        var rightGroup = new GroupBox { Text = "預覽", Dock = DockStyle.Fill };
        _grid = new PreviewGrid
        {
            Dock = DockStyle.Fill,
            ReadOnly = true,
            AllowUserToAddRows = false,
            AllowUserToDeleteRows = false,
            AllowUserToResizeRows = false,
            RowHeadersVisible = false,
            SelectionMode = DataGridViewSelectionMode.FullRowSelect,
            AutoSizeColumnsMode = DataGridViewAutoSizeColumnsMode.Fill,
            AutoSizeRowsMode = DataGridViewAutoSizeRowsMode.None,
            EditMode = DataGridViewEditMode.EditProgrammatically,
        };
        _grid.Columns.Add(new DataGridViewTextBoxColumn { Name = "col_idx", HeaderText = "#", FillWeight = 6 });
        _grid.Columns.Add(new DataGridViewTextBoxColumn { Name = "col_orig", HeaderText = "原始名稱", FillWeight = 28 });
        _grid.Columns.Add(new DataGridViewTextBoxColumn { Name = "col_new", HeaderText = "新名稱", FillWeight = 28 });
        _grid.Columns.Add(new DataGridViewTextBoxColumn { Name = "col_status", HeaderText = "狀態", FillWeight = 10 });
        _grid.Columns.Add(new DataGridViewTextBoxColumn { Name = "col_reason", HeaderText = "說明", FillWeight = 28 });
        rightGroup.Controls.Add(_grid);
        split.Panel2.Controls.Add(rightGroup);

        Controls.Add(split);

        // Panel1MinSize/SplitterDistance need the container to have a real
        // width; setting them right after the control tree is attached
        // (rather than before Panel1/Panel2 have content) keeps them inside
        // the valid range at every DPI.
        split.Panel1MinSize = LogicalToDeviceUnits(280);
        split.SplitterDistance = LogicalToDeviceUnits(360);

        // ================= WIRE-UP =================
        _btnBrowse.Click += (_, _) => BrowseFolder();
        _btnRescan.Click += (_, _) => RescanAndPreview();
        _cmbApplyTo.SelectedIndexChanged += (_, _) => UpdatePreview();
        _cmbSort.SelectedIndexChanged += (_, _) => RescanAndPreview();
        _lvSteps.DoubleClick += (_, _) => EditSelectedStep();
        _lvSteps.KeyDown += (_, e) =>
        {
            if (e.KeyCode == Keys.Delete)
            {
                DeleteSelectedStep();
                e.Handled = true;
            }
        };
        _btnApply.Click += (_, _) => ApplyRename();
        _btnUndo.Click += (_, _) => UndoLastBatch();

        KeyDown += (_, e) =>
        {
            if (e.KeyCode == Keys.F5)
            {
                RescanAndPreview();
                e.Handled = true;
            }
        };

        RefreshStepsList();
        UpdatePreview();
    }

    // ================= FOLDER / SCAN =================

    private void BrowseFolder()
    {
        try
        {
            using var dlg = new FolderBrowserDialog();
            if (!string.IsNullOrEmpty(_folder))
            {
                dlg.SelectedPath = _folder;
            }
            if (dlg.ShowDialog(this) == DialogResult.OK)
            {
                _folder = dlg.SelectedPath;
                _txtFolder.Text = _folder;
                RescanAndPreview();
            }
        }
        catch (Exception ex)
        {
            ShowErrorStatus("選擇資料夾失敗：" + ex.Message);
        }
    }

    private void RescanAndPreview()
    {
        if (string.IsNullOrEmpty(_folder))
        {
            _scannedFiles = new List<FileEntry>();
            UpdatePreview();
            return;
        }

        try
        {
            var sort = (SortMode)_cmbSort.SelectedIndex;
            _scannedFiles = FileScanner.Scan(_folder, sort);
        }
        catch (Exception ex)
        {
            ShowErrorStatus("掃描資料夾失敗：" + ex.Message);
            return;
        }

        UpdatePreview();
    }

    // ================= PREVIEW =================

    private RuleSet BuildRuleSet()
    {
        return new RuleSet
        {
            ApplyTo = (ApplyToMode)_cmbApplyTo.SelectedIndex,
            Sort = (SortMode)_cmbSort.SelectedIndex,
            Steps = new List<RuleStep>(_steps),
        };
    }

    private void UpdatePreview()
    {
        if (string.IsNullOrEmpty(_folder))
        {
            _lastPlan = null;
            RepaintGrid(null);
            _lblMessage.ForeColor = SystemColors.ControlText;
            _lblMessage.Text = "尚未選擇資料夾";
            UpdateCounters(null);
            return;
        }

        try
        {
            var rules = BuildRuleSet();
            var plan = PlanBuilder.Build(_scannedFiles, rules);
            _lastPlan = plan;
            RepaintGrid(plan);
            UpdateCounters(plan);

            _lblMessage.ForeColor = SystemColors.ControlText;
            _lblMessage.Text = _scannedFiles.Count == 0 ? "這個資料夾沒有檔案" : "";
        }
        catch (Exception ex)
        {
            // Keep the previous preview on screen; surface the failure without crashing.
            ShowErrorStatus("預覽計算失敗：" + ex.Message);
        }
    }

    private void ShowErrorStatus(string message)
    {
        _lblMessage.ForeColor = Color.DarkRed;
        _lblMessage.Text = message;
    }

    private void UpdateCounters(RenamePlan? plan)
    {
        if (plan == null)
        {
            _lblCounters.Text = "共 0 個 · 可執行 0 · 撞名 0 · 未變更 0 · 不合法 0";
            return;
        }
        var s = plan.Summary;
        _lblCounters.Text = $"共 {s.Total} 個 · 可執行 {s.Ok} · 撞名 {s.Collision} · 未變更 {s.Unchanged} · 不合法 {s.Invalid}";
    }

    private void RepaintGrid(RenamePlan? plan)
    {
        _grid.SuspendLayout();
        try
        {
            _grid.Rows.Clear();
            if (plan == null || plan.Items.Count == 0)
            {
                return;
            }

            var rows = new DataGridViewRow[plan.Items.Count];
            for (int i = 0; i < plan.Items.Count; i++)
            {
                var item = plan.Items[i];
                var row = new DataGridViewRow();
                row.CreateCells(_grid, (i + 1).ToString(), item.Original, item.Proposed, StatusText(item.Status), ReasonText(item));
                ApplyRowStyle(row, item.Status);
                rows[i] = row;
            }
            _grid.Rows.AddRange(rows);
        }
        finally
        {
            _grid.ResumeLayout();
        }
    }

    private static void ApplyRowStyle(DataGridViewRow row, ItemStatus status)
    {
        switch (status)
        {
            case ItemStatus.Unchanged:
                row.DefaultCellStyle.BackColor = UnchangedBack;
                row.DefaultCellStyle.ForeColor = UnchangedFore;
                break;
            case ItemStatus.Collision:
                row.DefaultCellStyle.BackColor = CollisionBack;
                break;
            case ItemStatus.Invalid:
                row.DefaultCellStyle.BackColor = InvalidBack;
                break;
        }
    }

    private static string StatusText(ItemStatus status) => status switch
    {
        ItemStatus.Ok => "可執行",
        ItemStatus.Unchanged => "未變更",
        ItemStatus.Collision => "撞名",
        ItemStatus.Invalid => "不合法",
        _ => status.ToString(),
    };

    private static string ReasonText(PlanItem item) => item.Reason switch
    {
        "" => "",
        "target name collides" => "目標名稱與其他項目或現有檔案衝突",
        "empty name" => "名稱空白",
        "name too long" => "名稱過長（超過 255 字）",
        "illegal character" => "含有不合法字元",
        "control character" => "含有控制字元",
        "reserved device name" => "保留裝置名稱",
        _ => item.Reason,
    };

    // ================= STEP LIST MANAGEMENT =================

    private void RefreshStepsList()
    {
        _lvSteps.BeginUpdate();
        _lvSteps.Items.Clear();
        for (int i = 0; i < _steps.Count; i++)
        {
            var lvi = new ListViewItem((i + 1).ToString());
            lvi.SubItems.Add(StepDescriber.Describe(_steps[i]));
            _lvSteps.Items.Add(lvi);
        }
        _lvSteps.EndUpdate();
    }

    private void AddStep(RuleStep template)
    {
        try
        {
            using var dlg = new StepEditorForm(template);
            if (dlg.ShowDialog(this) == DialogResult.OK && dlg.Result != null)
            {
                _steps.Add(dlg.Result);
                RefreshStepsList();
                _lvSteps.Items[^1].Selected = true;
                UpdatePreview();
            }
        }
        catch (Exception ex)
        {
            ShowErrorStatus("新增步驟失敗：" + ex.Message);
        }
    }

    private void EditSelectedStep()
    {
        if (_lvSteps.SelectedIndices.Count == 0)
        {
            return;
        }
        int idx = _lvSteps.SelectedIndices[0];
        try
        {
            using var dlg = new StepEditorForm(_steps[idx]);
            if (dlg.ShowDialog(this) == DialogResult.OK && dlg.Result != null)
            {
                _steps[idx] = dlg.Result;
                RefreshStepsList();
                _lvSteps.Items[idx].Selected = true;
                UpdatePreview();
            }
        }
        catch (Exception ex)
        {
            ShowErrorStatus("編輯步驟失敗：" + ex.Message);
        }
    }

    private void DeleteSelectedStep()
    {
        if (_lvSteps.SelectedIndices.Count == 0)
        {
            return;
        }
        int idx = _lvSteps.SelectedIndices[0];
        _steps.RemoveAt(idx);
        RefreshStepsList();
        UpdatePreview();
    }

    private void MoveSelectedStep(int delta)
    {
        if (_lvSteps.SelectedIndices.Count == 0)
        {
            return;
        }
        int idx = _lvSteps.SelectedIndices[0];
        int target = idx + delta;
        if (target < 0 || target >= _steps.Count)
        {
            return;
        }
        (_steps[idx], _steps[target]) = (_steps[target], _steps[idx]);
        RefreshStepsList();
        _lvSteps.Items[target].Selected = true;
        UpdatePreview();
    }

    private void ClearSteps()
    {
        if (_steps.Count == 0)
        {
            return;
        }
        _steps.Clear();
        RefreshStepsList();
        UpdatePreview();
    }

    // ================= RULE FILES =================

    private void LoadRules()
    {
        try
        {
            using var dlg = new OpenFileDialog { Filter = "JSON files (*.json)|*.json|All files (*.*)|*.*" };
            if (dlg.ShowDialog(this) != DialogResult.OK)
            {
                return;
            }

            string json;
            try
            {
                json = File.ReadAllText(dlg.FileName);
            }
            catch (Exception ex)
            {
                MessageBox.Show(this, ex.Message, "讀取檔案失敗", MessageBoxButtons.OK, MessageBoxIcon.Error);
                return;
            }

            RuleSet parsed;
            try
            {
                parsed = RuleSetJson.Parse(json);
            }
            catch (RuleParseException ex)
            {
                MessageBox.Show(this, ex.Message, "規則檔解析失敗", MessageBoxButtons.OK, MessageBoxIcon.Error);
                return; // current rules left untouched
            }

            _steps.Clear();
            _steps.AddRange(parsed.Steps);
            _cmbApplyTo.SelectedIndex = (int)parsed.ApplyTo;
            _cmbSort.SelectedIndex = (int)parsed.Sort;
            RefreshStepsList();
            RescanAndPreview();
            _lblMessage.ForeColor = SystemColors.ControlText;
            _lblMessage.Text = "已載入規則";
        }
        catch (Exception ex)
        {
            ShowErrorStatus("載入規則失敗：" + ex.Message);
        }
    }

    private void SaveRules()
    {
        try
        {
            using var dlg = new SaveFileDialog { Filter = "JSON files (*.json)|*.json|All files (*.*)|*.*", FileName = "rules.json" };
            if (dlg.ShowDialog(this) != DialogResult.OK)
            {
                return;
            }

            string json = RuleSetJson.Serialize(BuildRuleSet());
            try
            {
                File.WriteAllText(dlg.FileName, json, new UTF8Encoding(false));
                _lblMessage.ForeColor = SystemColors.ControlText;
                _lblMessage.Text = "已儲存規則";
            }
            catch (Exception ex)
            {
                MessageBox.Show(this, ex.Message, "儲存檔案失敗", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }
        catch (Exception ex)
        {
            ShowErrorStatus("儲存規則失敗：" + ex.Message);
        }
    }

    // ================= APPLY / UNDO =================

    private void ApplyRename()
    {
        try
        {
            if (string.IsNullOrEmpty(_folder) || _lastPlan == null)
            {
                MessageBox.Show(this, "請先選擇資料夾。", "無法套用", MessageBoxButtons.OK, MessageBoxIcon.Information);
                return;
            }

            int okCount = _lastPlan.Summary.Ok;
            if (okCount == 0)
            {
                MessageBox.Show(this, "目前沒有可執行的重新命名項目。", "無法套用", MessageBoxButtons.OK, MessageBoxIcon.Information);
                return;
            }

            int problemCount = _lastPlan.Summary.Collision + _lastPlan.Summary.Invalid;
            if (problemCount > 0)
            {
                int skipped = _lastPlan.Summary.Total - okCount;
                var result = MessageBox.Show(
                    this,
                    $"將重新命名 {okCount} 個項目，略過 {skipped} 個項目（撞名或不合法）。是否繼續？",
                    "確認套用",
                    MessageBoxButtons.YesNo,
                    MessageBoxIcon.Question);
                if (result != DialogResult.Yes)
                {
                    return;
                }
            }

            RenameResult renameResult;
            try
            {
                renameResult = RenameExecutor.Apply(_folder, _lastPlan);
            }
            catch (Exception ex)
            {
                MessageBox.Show(this, ex.Message, "套用重新命名時發生錯誤", MessageBoxButtons.OK, MessageBoxIcon.Error);
                return;
            }

            if (!renameResult.Success)
            {
                string detail = renameResult.FailedItem != null
                    ? $"失敗項目：{renameResult.FailedItem}\n{renameResult.ErrorMessage}"
                    : renameResult.ErrorMessage ?? "未知錯誤";
                MessageBox.Show(this, detail, "套用重新命名失敗（已回滾）", MessageBoxButtons.OK, MessageBoxIcon.Error);
                RescanAndPreview();
                return;
            }

            try
            {
                renameResult.Journal.Persist(DateTime.UtcNow);
            }
            catch (Exception ex)
            {
                // Persistence failure must not fail the rename; report to the status bar only.
                ShowErrorStatus("復原紀錄寫入失敗（改名已成功）：" + ex.Message);
            }

            _undoDir = _folder;
            _undoJournal = renameResult.Journal;
            _btnUndo.Enabled = true;

            RescanAndPreview();
            _lblMessage.ForeColor = SystemColors.ControlText;
            _lblMessage.Text = $"已重新命名 {okCount} 個項目";
        }
        catch (Exception ex)
        {
            ShowErrorStatus("套用重新命名失敗：" + ex.Message);
        }
    }

    private void UndoLastBatch()
    {
        try
        {
            if (_undoJournal == null || string.IsNullOrEmpty(_undoDir))
            {
                return;
            }

            RenameResult result;
            try
            {
                result = RenameExecutor.Undo(_undoDir, _undoJournal);
            }
            catch (Exception ex)
            {
                MessageBox.Show(this, ex.Message, "復原時發生錯誤", MessageBoxButtons.OK, MessageBoxIcon.Error);
                return;
            }

            if (!result.Success)
            {
                string detail = result.FailedItem != null
                    ? $"失敗項目：{result.FailedItem}\n{result.ErrorMessage}"
                    : result.ErrorMessage ?? "未知錯誤";
                MessageBox.Show(this, detail, "復原失敗（已回滾）", MessageBoxButtons.OK, MessageBoxIcon.Error);
                RescanAndPreview();
                return;
            }

            _undoJournal = null;
            _undoDir = null;
            _btnUndo.Enabled = false;

            RescanAndPreview();
            _lblMessage.ForeColor = SystemColors.ControlText;
            _lblMessage.Text = "已復原上一批";
        }
        catch (Exception ex)
        {
            ShowErrorStatus("復原失敗：" + ex.Message);
        }
    }
}

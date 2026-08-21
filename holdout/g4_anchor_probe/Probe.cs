// Minimal reproduction of the XL-B-01 top-bar defect.
//
// Scenario A replicates XL-B-01's construction order exactly:
//   BuildTopBar() creates a local Panel (unparented, default width),
//   adds Anchor=Top|Right children at absolute coordinates,
//   and only afterwards is the panel added to the form (Dock=Top -> width 1180).
//
// Scenario B is the same layout built in the safe order (panel parented first).
//
// Coordinates are copied verbatim from
//   D:\BenchRuns\XL-B-01\src\BatchRenameStudio\Ui\MainForm.cs  lines 98, 146-181.

using System;
using System.Drawing;
using System.Windows.Forms;

static class Probe
{
    const int ClientW = 1180;   // MainForm.cs:98  ClientSize = new Size(1180, 760)
    const int ClientH = 760;

    static Panel BuildTopBar(Form? parentFirst)
    {
        var panel = new Panel { Dock = DockStyle.Top, Height = 84 };
        if (parentFirst != null) parentFirst.Controls.Add(panel);   // scenario B

        var txtFolder = new TextBox();
        txtFolder.Location = new Point(70, 8);
        txtFolder.Size = new Size(900, 24);
        txtFolder.Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right;

        var btnBrowse = new Button { Text = "browse", Name = "btnBrowse" };
        btnBrowse.Location = new Point(980, 6);
        btnBrowse.Size = new Size(90, 28);
        btnBrowse.Anchor = AnchorStyles.Top | AnchorStyles.Right;

        var btnRefresh = new Button { Text = "refresh", Name = "btnRefresh" };
        btnRefresh.Location = new Point(1076, 6);
        btnRefresh.Size = new Size(90, 28);
        btnRefresh.Anchor = AnchorStyles.Top | AnchorStyles.Right;

        txtFolder.Name = "txtFolder";
        panel.Controls.Add(txtFolder);
        panel.Controls.Add(btnBrowse);
        panel.Controls.Add(btnRefresh);
        return panel;
    }

    static void Report(string label, Form form, Panel panel)
    {
        form.PerformLayout();
        Console.WriteLine($"--- {label} ---");
        Console.WriteLine($"  panel.Width = {panel.Width}");
        foreach (Control c in panel.Controls)
        {
            bool visible = c.Left >= 0 && c.Right <= panel.Width;
            Console.WriteLine(
                $"  {c.Name,-10} x={c.Left,6}  right={c.Right,6}  " +
                $"{(visible ? "REACHABLE" : "OFF-PANEL")}");
        }
    }

    [STAThread]
    static void Main()
    {
        Console.WriteLine($"runtime = {Environment.Version}");
        Console.WriteLine($"AnchorLayoutV2 switch present = " +
            AppContext.TryGetSwitch("System.Windows.Forms.AnchorLayoutV2", out var v) + $" (value={v})");
        Console.WriteLine($"form client width = {ClientW}\n");

        // Scenario A: XL-B-01's order.
        var fa = new Form { ClientSize = new Size(ClientW, ClientH) };
        var pa = BuildTopBar(null);
        fa.Controls.Add(pa);                 // MainForm.cs:113 Controls.Add(TopBarPanel!)
        _ = fa.Handle;
        Report("A  children added BEFORE panel is parented  (= XL-B-01)", fa, pa);

        Console.WriteLine();

        // Scenario B: safe order.
        var fb = new Form { ClientSize = new Size(ClientW, ClientH) };
        var pb = BuildTopBar(fb);
        _ = fb.Handle;
        Report("B  panel parented FIRST, then children      (control)", fb, pb);
    }
}

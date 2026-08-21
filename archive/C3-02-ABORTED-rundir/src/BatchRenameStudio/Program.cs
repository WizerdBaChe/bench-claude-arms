using BatchRenameStudio.Cli;

namespace BatchRenameStudio;

internal static class Program
{
    [STAThread]
    private static void Main(string[] args)
    {
        if (args.Length == 0)
        {
            ConsoleBridge.DetachConsoleForGui();
            Application.SetHighDpiMode(HighDpiMode.PerMonitorV2);
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            Application.Run(new Gui.MainForm());
            return;
        }

        var parsed = CommandLine.Parse(args);

        if (parsed.Plan || parsed.Help)
        {
            int code = HeadlessRunner.Run(parsed);
            Environment.Exit(code);
            return;
        }

        // args present but neither --plan nor --help nor recognized as such
        ConsoleBridge.StdErr.Write("BatchRenameStudio.exe --plan --dir <folder> --rules <rules.json> --out <plan.json>\n");
        Environment.Exit(2);
    }
}

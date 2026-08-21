using System.Runtime.InteropServices;
using System.Text;

namespace BatchRenameStudio.Cli;

public static class ConsoleBridge
{
    [DllImport("kernel32.dll")]
    private static extern bool FreeConsole();

    private static StreamWriter? _stdout;
    private static StreamWriter? _stderr;

    /// <summary>
    /// Detaches the process's console so GUI mode does not leave a console
    /// window behind. Must be called before any System.Windows.Forms type is
    /// touched. A missing/failed detach is not an error.
    /// </summary>
    public static void DetachConsoleForGui()
    {
        try { FreeConsole(); } catch { }
    }

    public static StreamWriter StdOut
    {
        get
        {
            _stdout ??= new StreamWriter(Console.OpenStandardOutput(), new UTF8Encoding(false)) { AutoFlush = true };
            return _stdout;
        }
    }

    public static StreamWriter StdErr
    {
        get
        {
            _stderr ??= new StreamWriter(Console.OpenStandardError(), new UTF8Encoding(false)) { AutoFlush = true };
            return _stderr;
        }
    }
}

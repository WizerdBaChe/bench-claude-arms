# WinForms layout probe -- read-only structural inspection of a running desktop app.
#
# v2 (2026-08-21) adds SIBLING-OVERLAP detection. v1 checked OFF-CLIENT only and
# passed XL-B-02, whose real defect is an overlap, not an escape (see README.md).
#
# TWO INDEPENDENT CHECKS, both derived from live window geometry:
#
#   [A] OFF-CLIENT   a visible control whose rectangle falls outside the
#                    top-level window's client area -> unreachable by the user.
#                    This is how XL-B-01 failed G4 item 2.
#
#   [B] OVERLAP      two visible controls that share the same immediate parent
#                    and whose rectangles intersect -> they paint over each other.
#                    This is how XL-B-02's menu bar and rule-action buttons collide.
#                    Only SIBLINGS are compared, so a container legitimately
#                    holding children never registers.
#
# This script is READ-ONLY with respect to the target's state: it launches the
# exe, reads window geometry, and terminates it. It never clicks, types, focuses,
# or sends any input. It is therefore NOT a substitute for the manual acceptance
# pass -- see "What it cannot decide" below.
#
# WHAT IT CAN DECIDE
#   * REFUTE a reachability claim: controls outside the client area cannot be operated.
#   * REFUTE a "layout is clean" claim: overlapping siblings are a rendering defect.
#
# WHAT IT CANNOT DECIDE
#   * That a reachable control WORKS when clicked.
#   * Clipping INSIDE a control (truncated label text, squeezed columns). Those
#     stay within the control's own rectangle, so geometry cannot see them.
#     M1-01 reports 0 findings here and still had text clipping in manual testing.
#   * Anything about usability, information density, or colour.
#
# A clean result means "not refuted by geometry", never "passes".
#
# Usage:
#   powershell -File probe_reachability.ps1 -Exe <path-to-exe> [-SettleSeconds 5]

param(
    [Parameter(Mandatory = $true)][string]$Exe,
    [int]$SettleSeconds = 5,
    [int]$MinOverlapPx = 2
)

Add-Type -TypeDefinition @'
using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Text;

public struct RECT { public int Left, Top, Right, Bottom; }

public static class Win32
{
    public delegate bool EnumProc(IntPtr hWnd, IntPtr lParam);

    [DllImport("user32.dll")] public static extern bool EnumChildWindows(IntPtr h, EnumProc cb, IntPtr p);
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
    [DllImport("user32.dll")] public static extern bool GetClientRect(IntPtr h, out RECT r);
    [DllImport("user32.dll")] public static extern bool ClientToScreen(IntPtr h, ref System.Drawing.Point p);
    [DllImport("user32.dll")] public static extern IntPtr GetParent(IntPtr h);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)] public static extern int GetClassName(IntPtr h, StringBuilder s, int n);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)] public static extern int GetWindowTextW(IntPtr h, StringBuilder s, int n);
    [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);

    public static List<IntPtr> Children(IntPtr parent)
    {
        var list = new List<IntPtr>();
        EnumChildWindows(parent, delegate(IntPtr h, IntPtr p) { list.Add(h); return true; }, IntPtr.Zero);
        return list;
    }

    public static string ClassOf(IntPtr h)
    { var sb = new StringBuilder(256); GetClassName(h, sb, sb.Capacity); return sb.ToString(); }

    public static string TextOf(IntPtr h)
    { var sb = new StringBuilder(512); GetWindowTextW(h, sb, sb.Capacity); return sb.ToString(); }
}
'@ -ReferencedAssemblies System.Drawing

if (-not (Test-Path $Exe)) { Write-Output "MISSING EXE: $Exe"; exit 1 }

$proc = Start-Process -FilePath $Exe -PassThru
Start-Sleep -Seconds $SettleSeconds
$proc.Refresh()

if ($proc.HasExited) {
    Write-Output "PROCESS EXITED before a window appeared (exit=$($proc.ExitCode))"
    exit 1
}

$hwnd = $proc.MainWindowHandle
$cr = New-Object RECT
[void][Win32]::GetClientRect($hwnd, [ref]$cr)
$origin = New-Object System.Drawing.Point 0, 0
[void][Win32]::ClientToScreen($hwnd, [ref]$origin)
$clientW = $cr.Right - $cr.Left
$clientH = $cr.Bottom - $cr.Top

Write-Output "exe          : $Exe"
Write-Output "window title : $($proc.MainWindowTitle)"
Write-Output ("client area  : {0} x {1}  (origin {2},{3})" -f $clientW, $clientH, $origin.X, $origin.Y)
Write-Output ""

# ---- collect visible controls -------------------------------------------------

$ctrls = @()
foreach ($h in [Win32]::Children($hwnd)) {
    if (-not [Win32]::IsWindowVisible($h)) { continue }
    $r = New-Object RECT
    if (-not [Win32]::GetWindowRect($h, [ref]$r)) { continue }
    $x = $r.Left - $origin.X; $y = $r.Top - $origin.Y
    $right = $r.Right - $origin.X; $bottom = $r.Bottom - $origin.Y
    if (($right - $x) -le 0 -or ($bottom - $y) -le 0) { continue }

    $txt = [Win32]::TextOf($h)
    if ($txt.Length -gt 32) { $txt = $txt.Substring(0, 32) }

    $ctrls += [pscustomobject]@{
        H = $h; Parent = [Win32]::GetParent($h)
        Class = ([Win32]::ClassOf($h) -replace '^WindowsForms10\.([A-Za-z0-9]+).*$', '$1')
        Text = $txt; X = $x; Y = $y; R = $right; B = $bottom
        Inside = ($x -lt $clientW) -and ($y -lt $clientH) -and ($right -gt 0) -and ($bottom -gt 0)
    }
}

# ---- [A] OFF-CLIENT -----------------------------------------------------------

Write-Output "[A] OFF-CLIENT -- visible controls outside the window's client area"
Write-Output ("{0,-16} {1,-34} {2,7} {3,7} {4,7} {5,7}  {6}" -f "class", "text", "x", "y", "right", "bottom", "verdict")
Write-Output ("-" * 104)
foreach ($c in $ctrls) {
    $v = if ($c.Inside) { "on-screen" } else { "OFF-CLIENT" }
    Write-Output ("{0,-16} {1,-34} {2,7} {3,7} {4,7} {5,7}  {6}" -f $c.Class, $c.Text, $c.X, $c.Y, $c.R, $c.B, $v)
}
$off = @($ctrls | Where-Object { -not $_.Inside })
Write-Output ""
Write-Output ("    visible controls: {0}    OFF-CLIENT: {1}" -f $ctrls.Count, $off.Count)
Write-Output ""

# ---- [B] SIBLING OVERLAP ------------------------------------------------------

Write-Output "[B] OVERLAP -- pairs of same-parent controls whose rectangles intersect"
Write-Output ("-" * 104)
$pairs = @()
for ($i = 0; $i -lt $ctrls.Count; $i++) {
    for ($j = $i + 1; $j -lt $ctrls.Count; $j++) {
        $a = $ctrls[$i]; $b = $ctrls[$j]
        if ($a.Parent -ne $b.Parent) { continue }
        $ox = [Math]::Min($a.R, $b.R) - [Math]::Max($a.X, $b.X)
        $oy = [Math]::Min($a.B, $b.B) - [Math]::Max($a.Y, $b.Y)
        if ($ox -le 0 -or $oy -le 0) { continue }
        $pairs += [pscustomobject]@{ A = $a; B = $b; W = $ox; H = $oy }
    }
}
# A 1-pixel overlap in one dimension is adjacency, not collision: two controls
# placed flush share a border pixel. Across the ten G4 builds every benign case
# measured EXACTLY 1 px in one dimension and every real defect measured >= 15 px,
# with nothing in between -- so this threshold is a natural break in the data,
# not a value fitted to produce a desired verdict. Raw pairs are printed either
# way so the judgement can be re-made by a reader who disagrees.
$material = @($pairs | Where-Object { $_.W -ge $MinOverlapPx -and $_.H -ge $MinOverlapPx })

if ($pairs.Count -eq 0) {
    Write-Output "    none"
} else {
    foreach ($p in $pairs) {
        $tag = if ($p.W -ge $MinOverlapPx -and $p.H -ge $MinOverlapPx) { "MATERIAL" } else { "adjacency" }
        Write-Output ("    [{0,-9}] {1}[{2}] ({3},{4})-({5},{6})  X  {7}[{8}] ({9},{10})-({11},{12})   overlap {13}x{14}" -f `
            $tag, $p.A.Class, $p.A.Text, $p.A.X, $p.A.Y, $p.A.R, $p.A.B,
            $p.B.Class, $p.B.Text, $p.B.X, $p.B.Y, $p.B.R, $p.B.B, $p.W, $p.H)
    }
}
Write-Output ""
Write-Output ("    OVERLAPPING PAIRS: {0} raw, {1} material (both dimensions >= {2} px)" -f $pairs.Count, $material.Count, $MinOverlapPx)
Write-Output ""

# ---- verdict ------------------------------------------------------------------

Write-Output ("SUMMARY  controls={0}  off-client={1}  overlaps={2} raw / {3} material" -f $ctrls.Count, $off.Count, $pairs.Count, $material.Count)
if ($off.Count -eq 0 -and $material.Count -eq 0) {
    Write-Output "VERDICT: not refuted by geometry (this is NOT a pass -- see header)."
} else {
    Write-Output "VERDICT: REFUTED -- the layout has a structural defect visible in window geometry."
}

Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue

# Capture a PNG of a process's main window (works while the window is in the background).
# Usage: powershell -File tools\winshot.ps1 -ProcessId <pid> -Out <file.png> [-Scale 0.5]
param([Parameter(Mandatory = $true)][int]$ProcessId, [Parameter(Mandatory = $true)][string]$Out, [double]$Scale = 1.0)
Add-Type -AssemblyName System.Drawing
Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class WinShot {
  [StructLayout(LayoutKind.Sequential)] public struct RECT { public int L, T, R, B; }
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
  [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr h, IntPtr hdc, uint flags);
  [DllImport("user32.dll")] public static extern IntPtr SetThreadDpiAwarenessContext(IntPtr ctx);
}
"@
[WinShot]::SetThreadDpiAwarenessContext([IntPtr](-4)) | Out-Null   # PER_MONITOR_AWARE_V2
$p = Get-Process -Id $ProcessId
$h = $p.MainWindowHandle
if ($h -eq [IntPtr]::Zero) { throw "no main window" }
$r = New-Object WinShot+RECT
[WinShot]::GetWindowRect($h, [ref]$r) | Out-Null
$w = $r.R - $r.L; $ht = $r.B - $r.T
$bmp = New-Object System.Drawing.Bitmap $w, $ht
$g = [System.Drawing.Graphics]::FromImage($bmp)
$hdc = $g.GetHdc()
[WinShot]::PrintWindow($h, $hdc, 2) | Out-Null   # PW_RENDERFULLCONTENT
$g.ReleaseHdc($hdc)
if ($Scale -ne 1.0) {
  $sw = [int]($w * $Scale); $sh = [int]($ht * $Scale)
  $small = New-Object System.Drawing.Bitmap $sw, $sh
  $g2 = [System.Drawing.Graphics]::FromImage($small)
  $g2.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBilinear
  $g2.DrawImage($bmp, 0, 0, $sw, $sh)
  $small.Save($Out, [System.Drawing.Imaging.ImageFormat]::Png); $g2.Dispose(); $small.Dispose()
} else {
  $bmp.Save($Out, [System.Drawing.Imaging.ImageFormat]::Png)
}
$g.Dispose(); $bmp.Dispose()
"$Out ${w}x${ht} title='$($p.MainWindowTitle)'"

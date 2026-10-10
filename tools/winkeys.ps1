# Post key presses to a sandbox PCSX2 window without focusing it.
# Usage: powershell -File tools\winkeys.ps1 -ProcessId <pid> -Seq "Return:150,wait:2000,K:150"
#   item = <Key>:<holdMs>  or  wait:<ms>.  Keys are System.Windows.Forms.Keys names (Return, K, Up, Down...).
#   -List prints the child windows instead.
param([Parameter(Mandatory = $true)][int]$ProcessId, [string]$Seq = "", [switch]$List)
Add-Type -AssemblyName System.Windows.Forms
Add-Type @"
using System;
using System.Text;
using System.Collections.Generic;
using System.Runtime.InteropServices;
public static class WinKeys {
  public delegate bool EnumProc(IntPtr h, IntPtr l);
  [DllImport("user32.dll")] public static extern bool EnumChildWindows(IntPtr p, EnumProc cb, IntPtr l);
  [DllImport("user32.dll")] public static extern int GetClassName(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] public static extern bool PostMessage(IntPtr h, uint m, IntPtr w, IntPtr l);
  [DllImport("user32.dll")] public static extern uint MapVirtualKey(uint c, uint t);
  [StructLayout(LayoutKind.Sequential)] public struct RECT { public int L, T, R, B; }
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
  public static List<IntPtr> Children(IntPtr p) {
    var l = new List<IntPtr>();
    EnumChildWindows(p, (h, x) => { l.Add(h); return true; }, IntPtr.Zero);
    return l;
  }
}
"@
$p = Get-Process -Id $ProcessId
$main = $p.MainWindowHandle
$targets = @($main) + [WinKeys]::Children($main)
if ($List) {
  foreach ($h in $targets) {
    $c = New-Object System.Text.StringBuilder 256; [WinKeys]::GetClassName($h, $c, 256) | Out-Null
    $t = New-Object System.Text.StringBuilder 256; [WinKeys]::GetWindowText($h, $t, 256) | Out-Null
    $r = New-Object WinKeys+RECT; [WinKeys]::GetWindowRect($h, [ref]$r) | Out-Null
    "{0} class={1} text='{2}' size={3}x{4}" -f $h, $c, $t, ($r.R - $r.L), ($r.B - $r.T)
  }
  return
}
function Send($vk, $down) {
  $scan = [WinKeys]::MapVirtualKey($vk, 0)
  # arrows, Insert/Delete, Home/End, PageUp/PageDown need the extended-key bit or Qt sees numpad keys
  if (@(33, 34, 35, 36, 37, 38, 39, 40, 45, 46) -contains $vk) { $scan = $scan -bor 0x100 }
  if ($down) { $l = 1 -bor ($scan -shl 16); $m = 0x100 } else { $l = 1 -bor ($scan -shl 16) -bor (3 -shl 30); $m = 0x101 }
  foreach ($h in $targets) { [WinKeys]::PostMessage($h, $m, [IntPtr]$vk, [IntPtr]$l) | Out-Null }
}
foreach ($item in $Seq.Split(",")) {
  $k, $ms = $item.Split(":")
  if ($k -eq "wait") { Start-Sleep -Milliseconds ([int]$ms); continue }
  $vk = [int][System.Windows.Forms.Keys]$k
  Send $vk $true; Start-Sleep -Milliseconds ([int]$ms); Send $vk $false; Start-Sleep -Milliseconds 120
}

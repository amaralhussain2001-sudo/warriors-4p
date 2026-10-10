# Record a sandbox PCSX2 window frame by frame, together with the game's view count and frame counter (PINE).
# Usage: powershell -File tools\framecap.ps1 -ProcessId <pid> -PinePort <port> -OutDir <dir> [-Seconds 20]
#          [-Width 320] [-Around 12] [-Every 0] [-Screen]
# Writes <OutDir>\frames.csv (every capture: time, views, game frame, quadrant brightness, change from previous)
# and PNGs for captures within -Around of a view-count change (plus every -Every-th capture when > 0).
# Default capture is PrintWindow (works while the window is covered); -Screen copies from the screen instead.
param([Parameter(Mandatory = $true)][int]$ProcessId, [Parameter(Mandatory = $true)][int]$PinePort,
      [Parameter(Mandatory = $true)][string]$OutDir, [double]$Seconds = 20, [int]$Width = 320, [int]$Around = 12,
      [int]$Every = 0, [switch]$Screen)
Add-Type -AssemblyName System.Drawing
Add-Type -ReferencedAssemblies System.Drawing @"
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.Drawing.Imaging;
using System.IO;
using System.Net.Sockets;
using System.Runtime.InteropServices;
using System.Text;

public static class FrameCap {
  [StructLayout(LayoutKind.Sequential)] public struct RECT { public int L, T, R, B; }
  [StructLayout(LayoutKind.Sequential)] public struct POINT { public int X, Y; }
  public delegate bool EnumProc(IntPtr h, IntPtr l);
  [DllImport("user32.dll")] static extern bool EnumChildWindows(IntPtr p, EnumProc cb, IntPtr l);
  [DllImport("user32.dll")] static extern bool GetWindowRect(IntPtr h, out RECT r);
  [DllImport("user32.dll")] static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll")] static extern bool PrintWindow(IntPtr h, IntPtr hdc, uint flags);
  [DllImport("user32.dll")] public static extern IntPtr SetThreadDpiAwarenessContext(IntPtr ctx);

  static NetworkStream ns;

  static byte[] ReadN(int n) {
    byte[] b = new byte[n]; int got = 0;
    while (got < n) { int k = ns.Read(b, got, n - got); if (k <= 0) throw new Exception("PINE closed"); got += k; }
    return b;
  }

  // PINE batch: u32 total size, then per op u8 opcode (2 = read32) + u32 address; reply u32 size, u8 result, values.
  static uint[] Read32(uint[] addrs) {
    byte[] msg = new byte[4 + 5 * addrs.Length];
    BitConverter.GetBytes((uint)msg.Length).CopyTo(msg, 0);
    for (int i = 0; i < addrs.Length; i++) { msg[4 + 5 * i] = 2; BitConverter.GetBytes(addrs[i]).CopyTo(msg, 5 + 5 * i); }
    ns.Write(msg, 0, msg.Length);
    int size = BitConverter.ToInt32(ReadN(4), 0);
    byte[] body = ReadN(size - 4);
    if (body[0] != 0) throw new Exception("PINE error " + body[0]);
    uint[] r = new uint[addrs.Length];
    for (int i = 0; i < addrs.Length; i++) r[i] = BitConverter.ToUInt32(body, 1 + 4 * i);
    return r;
  }

  // The game picture is the largest visible child window of the main window.
  static RECT DisplayRect(IntPtr main) {
    RECT best = new RECT(); long bestArea = 0;
    EnumChildWindows(main, delegate(IntPtr h, IntPtr l) {
      RECT r; if (IsWindowVisible(h) && GetWindowRect(h, out r)) {
        long a = (long)(r.R - r.L) * (r.B - r.T); if (a > bestArea) { bestArea = a; best = r; } }
      return true; }, IntPtr.Zero);
    if (bestArea == 0) GetWindowRect(main, out best);
    return best;
  }

  static double[] Metrics(Bitmap bmp, byte[] prev, out byte[] lum) {
    int w = bmp.Width, h = bmp.Height;
    BitmapData d = bmp.LockBits(new Rectangle(0, 0, w, h), ImageLockMode.ReadOnly, PixelFormat.Format32bppArgb);
    byte[] px = new byte[d.Stride * h]; Marshal.Copy(d.Scan0, px, 0, px.Length); bmp.UnlockBits(d);
    lum = new byte[w * h]; double[] q = new double[4]; long diff = 0;
    for (int y = 0; y < h; y++) for (int x = 0; x < w; x++) {
      int o = y * d.Stride + 4 * x;
      int L = (px[o + 2] * 299 + px[o + 1] * 587 + px[o] * 114) / 1000;
      lum[y * w + x] = (byte)L;
      q[(y < h / 2 ? 0 : 2) + (x < w / 2 ? 0 : 1)] += L;
      if (prev != null) diff += Math.Abs(L - prev[y * w + x]);
    }
    double n = (w / 2.0) * (h / 2.0);
    return new double[] { q[0] / n, q[1] / n, q[2] / n, q[3] / n, prev == null ? 0 : (double)diff / (w * h) };
  }

  public static string Run(int pid, int port, double seconds, string outDir, int width, int around, int every, bool screen) {
    SetThreadDpiAwarenessContext((IntPtr)(-4));
    IntPtr main = Process.GetProcessById(pid).MainWindowHandle;
    RECT win; GetWindowRect(main, out win);
    RECT disp = DisplayRect(main);
    int dw = disp.R - disp.L, dh = disp.B - disp.T, ww = win.R - win.L, wh = win.B - win.T;
    int sw = width, sh = Math.Max(1, (int)Math.Round((double)width * dh / dw));
    TcpClient tc = new TcpClient("127.0.0.1", port); tc.NoDelay = true; ns = tc.GetStream();
    uint[] addrs = new uint[] { 0x0050B198, 0x0050C654 };
    Bitmap full = new Bitmap(screen ? dw : ww, screen ? dh : wh);
    Graphics gf = Graphics.FromImage(full);
    List<Bitmap> frames = new List<Bitmap>(); List<double> times = new List<double>();
    List<uint[]> mem = new List<uint[]>();
    Stopwatch sw0 = Stopwatch.StartNew();
    while (sw0.Elapsed.TotalSeconds < seconds) {
      double t = sw0.Elapsed.TotalMilliseconds;
      uint[] m = Read32(addrs);
      if (screen) gf.CopyFromScreen(disp.L, disp.T, 0, 0, new Size(dw, dh));
      else { IntPtr hdc = gf.GetHdc(); PrintWindow(main, hdc, 2); gf.ReleaseHdc(hdc); }
      Bitmap small = new Bitmap(sw, sh, PixelFormat.Format32bppArgb);
      using (Graphics gs = Graphics.FromImage(small)) {
        gs.InterpolationMode = System.Drawing.Drawing2D.InterpolationMode.Bilinear;
        Rectangle src = screen ? new Rectangle(0, 0, dw, dh) : new Rectangle(disp.L - win.L, disp.T - win.T, dw, dh);
        gs.DrawImage(full, new Rectangle(0, 0, sw, sh), src, GraphicsUnit.Pixel);
      }
      frames.Add(small); times.Add(t); mem.Add(m);
    }
    tc.Close();
    Directory.CreateDirectory(outDir);
    HashSet<int> keep = new HashSet<int>();
    for (int i = 1; i < frames.Count; i++)
      if (mem[i][0] != mem[i - 1][0]) for (int k = Math.Max(0, i - around); k <= Math.Min(frames.Count - 1, i + around); k++) keep.Add(k);
    StringBuilder csv = new StringBuilder("idx,t_ms,views,game_frame,lum_tl,lum_tr,lum_bl,lum_br,diff_prev,saved\n");
    byte[] prev = null;
    for (int i = 0; i < frames.Count; i++) {
      byte[] lum; double[] q = Metrics(frames[i], prev, out lum); prev = lum;
      bool save = keep.Contains(i) || (every > 0 && i % every == 0);
      if (save) frames[i].Save(Path.Combine(outDir, string.Format("f{0:D5}.png", i)), ImageFormat.Png);
      csv.AppendFormat(System.Globalization.CultureInfo.InvariantCulture, "{0},{1:F1},{2},{3},{4:F1},{5:F1},{6:F1},{7:F1},{8:F2},{9}\n",
        i, times[i], mem[i][0], mem[i][1], q[0], q[1], q[2], q[3], q[4], save ? 1 : 0);
    }
    File.WriteAllText(Path.Combine(outDir, "frames.csv"), csv.ToString());
    double fps = frames.Count / seconds;
    return string.Format("{0} captures in {1:F0} s ({2:F1} per second), display {3}x{4}, saved {5} PNGs",
      frames.Count, seconds, fps, dw, dh, keep.Count);
  }
}
"@
[FrameCap]::Run($ProcessId, $PinePort, $Seconds, $OutDir, $Width, $Around, $Every, $Screen.IsPresent)

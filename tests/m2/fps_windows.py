"""Frame rate from a W4P log: polls per second between consecutive 10-second stats lines (one poll per game frame).

Usage: python -I tests/m2/fps_windows.py <log> [from_poll]
"""
import re
import sys

txt = open(sys.argv[1], encoding="utf-8", errors="replace").read()
start = int(sys.argv[2]) if len(sys.argv) > 2 else 0
st = [(float(a) / 1000.0, int(p)) for a, p in re.findall(r"^\[(\d+\.\d+)\] stats: poll (\d+)", txt, re.M)]
vals = sorted((b[1] - a[1]) / (b[0] - a[0]) for a, b in zip(st, st[1:]) if a[1] >= start)
if not vals:
    sys.exit("no windows")
print(f"windows {len(vals)} median {vals[len(vals) // 2]:.2f} p10 {vals[len(vals) // 10]:.2f} min {vals[0]:.2f} "
      f"share>=29.5 {100 * sum(v >= 29.5 for v in vals) / len(vals):.0f}%")

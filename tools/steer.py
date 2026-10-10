"""Walk player 1 (or 2) toward a world (x, y) target using short stick pulses and PINE position feedback.

The game's movement is camera-relative, so each step probes how the four stick keys map to world
directions and picks the best one. Bot-driven helper for sandbox navigation only.

Usage: python -I tools/steer.py <inst> <pine_slot> <x> <y> [--p2] [--tol 1.5] [--max 60]
"""
import math
import os
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from pine import Pine  # noqa: E402

KEYS_P1 = {"up": "W", "down": "S", "left": "A", "right": "D"}
KEYS_P2 = {"up": "Y", "down": "N", "left": "B", "right": "M"}


def main():
    inst, slot = int(sys.argv[1]), int(sys.argv[2])
    tx, ty = float(sys.argv[3]), float(sys.argv[4])
    p2 = "--p2" in sys.argv
    tol = float(sys.argv[sys.argv.index("--tol") + 1]) if "--tol" in sys.argv else 1.5
    mx = int(sys.argv[sys.argv.index("--max") + 1]) if "--max" in sys.argv else 60
    keys = KEYS_P2 if p2 else KEYS_P1
    p = Pine(slot)
    mgr = p.read32(0x0051489C)
    h = p.read32(mgr + 0x228 + (4 if p2 else 0))
    obj = p.read32(0x006EBD38 + (h >> 16) * 8)

    def pos():
        return [struct.unpack("<f", struct.pack("<I", p.read32(obj + 0x10 + 4 * k)))[0] for k in range(2)]

    def press(k, ms):
        subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                        os.path.join(HERE, "winkeys.ps1"), "-ProcessId",
                        open(os.path.join(HERE, "..", "local", "pcsx2", f"inst{inst}", "pid.txt")).read().strip(),
                        "-Seq", f"{k}:{ms},wait:150"], capture_output=True)

    dirs = {}
    for step in range(mx):
        x, y = pos()
        d = math.hypot(tx - x, ty - y)
        print(f"step {step}: pos=({x:.2f},{y:.2f}) dist={d:.2f}", flush=True)
        if d < tol:
            return
        if step % 6 == 0 or not dirs:
            dirs = {}
            for name, k in keys.items():
                a = pos()
                press(k, 180)
                b = pos()
                v = (b[0] - a[0], b[1] - a[1])
                n = math.hypot(*v)
                if n > 0.05:
                    dirs[name] = (v[0] / n, v[1] / n)
        want = ((tx - x) / d, (ty - y) / d)
        best = max(dirs.items(), key=lambda kv: kv[1][0] * want[0] + kv[1][1] * want[1], default=None)
        if not best:
            print("no movement detected")
            return
        press(keys[best[0]], int(min(1200, 120 * d)))
    print("gave up")


if __name__ == "__main__":
    main()

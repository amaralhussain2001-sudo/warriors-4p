"""Walk a player toward a world (x, y) target using in-game input injection (requires experiment patch v2/v3).

Probes the camera-relative mapping of the four stick directions, then pulses the best one. Bot helper for sandbox
navigation only. Usage: python -I tools/steer_inject.py <pine_slot> <x> <y> [--pad 0] [--player 0] [--tol 1.0]
"""
import math
import os
import struct
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import inject  # noqa: E402
from pine import Pine  # noqa: E402


def main():
    slot, tx, ty = int(sys.argv[1]), float(sys.argv[2]), float(sys.argv[3])
    pad = int(sys.argv[sys.argv.index("--pad") + 1]) if "--pad" in sys.argv else 0
    pl = int(sys.argv[sys.argv.index("--player") + 1]) if "--player" in sys.argv else 0
    tol = float(sys.argv[sys.argv.index("--tol") + 1]) if "--tol" in sys.argv else 1.0
    p = Pine(slot)
    mgr = p.read32(0x0051489C)
    h = p.read32(mgr + 0x228 + 4 * pl)
    obj = p.read32(0x006EBD38 + (h >> 16) * 8)

    def pos():
        return [struct.unpack("<f", struct.pack("<I", p.read32(obj + 0x10 + 4 * k)))[0] for k in range(2)]

    def hold(lx, ly, frames):
        rows = []
        for _ in range(frames):
            row = bytearray(64)
            for k in range(8):
                row[k * 8:(k + 1) * 8] = inject.entry(0, lx, ly) if k == pad else inject.entry()
            rows.append(bytes(row))
        now = p.read32(0x0050C654)
        inject.arm(p, b"".join(rows), now + 2, 1 << pad)
        while p.read32(0x0050C654) < now + 2 + frames:
            time.sleep(0.02)

    dirs = {"up": (0x7F, 0x00), "down": (0x7F, 0xFF), "left": (0x00, 0x7F), "right": (0xFF, 0x7F)}
    learned = {}
    for step in range(80):
        x, y = pos()
        d = math.hypot(tx - x, ty - y)
        print(f"step {step}: ({x:.2f},{y:.2f}) dist {d:.2f}", flush=True)
        if d < tol:
            p.write32(inject.CTRL, 0)
            return
        if step % 5 == 0:
            learned = {}
            for name, (lx, ly) in dirs.items():
                a = pos()
                hold(lx, ly, 6)
                b = pos()
                v = (b[0] - a[0], b[1] - a[1])
                n = math.hypot(*v)
                if n > 0.02:
                    learned[name] = (v[0] / n, v[1] / n)
        if not learned:
            print("no movement detected")
            return
        want = ((tx - x) / d, (ty - y) / d)
        best = max(learned, key=lambda k: learned[k][0] * want[0] + learned[k][1] * want[1])
        hold(*dirs[best], int(min(40, 6 * d + 2)))
    p.write32(inject.CTRL, 0)


if __name__ == "__main__":
    main()

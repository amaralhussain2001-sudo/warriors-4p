"""Live check that injected left-stick input moves player 1 (Stage 1 sanity check for E1/E3).
Assumes sandbox inst1 runs e1_v2.pnach and is in gameplay. Usage: python -I walk_check.py <pine_slot>
"""
import os
import struct
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "tools"))
import inject  # noqa: E402
from pine import Pine  # noqa: E402

p = Pine(int(sys.argv[1]))
mgr = p.read32(0x0051489C)
h = p.read32(mgr + 0x228)
obj = p.read32(0x006EBD38 + (h >> 16) * 8)


def pos():
    return [round(struct.unpack("<f", struct.pack("<I", p.read32(obj + 0x10 + 4 * k)))[0], 2) for k in range(3)]


rows = []
for f in range(240):
    lx, ly = (0x7F, 0x00) if f < 120 else (0xFF, 0x7F)   # 4 s up, then 4 s right
    row = bytearray(64)
    row[0:8] = inject.entry(0, lx, ly)
    for k in range(1, 8):
        row[k * 8:(k + 1) * 8] = inject.entry()
    rows.append(bytes(row))
now = p.read32(0x0050C654)
inject.arm(p, b"".join(rows), now + 15, 0x1)
print("player obj", hex(obj), "start", pos())
for i in range(9):
    time.sleep(1)
    print(i, p.read32(0x0050C654) - now, pos())

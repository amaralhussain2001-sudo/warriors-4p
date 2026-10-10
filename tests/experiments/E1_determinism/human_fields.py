"""Which offsets inside human objects differ between the two dumps of a run (counts across humans).
Usage: python -I human_fields.py <tag>
"""
import collections
import os
import struct
import sys

PROJ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
tag = sys.argv[1]
a = open(os.path.join(PROJ, "local", "e1", tag, "inst2.bin"), "rb").read()
b = open(os.path.join(PROJ, "local", "e1", tag, "inst3.bin"), "rb").read()
cnt = collections.Counter()
examples = {}
for k in range(-40, 30):
    o = 0x00640C80 + k * 0x6D0
    px = struct.unpack_from("<f", a, o + 0x10)[0]
    if not (abs(px) < 1e4 and abs(px) > 0.01):
        continue
    for off in range(0, 0x6D0, 4):
        wa, wb = a[o + off:o + off + 4], b[o + off:o + off + 4]
        if wa != wb:
            cnt[off] += 1
            examples.setdefault(off, (hex(o), wa.hex(), wb.hex(), round(struct.unpack("<f", wa)[0], 4), round(struct.unpack("<f", wb)[0], 4)))
for off, n in sorted(cnt.items()):
    print(f"+0x{off:03x}: {n:2d} humans  e.g. {examples[off]}")

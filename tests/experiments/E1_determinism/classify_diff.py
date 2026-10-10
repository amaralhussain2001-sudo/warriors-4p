"""Classify differing bytes between the two RAM dumps of an E1/E2 run by region, and compare human objects.
Usage: python -I classify_diff.py <tag>
Human pool hypothesis (F-0023/F-0053): objects of 0x6D0 bytes from 0x00640C80 (both directions), position at +0x10.
"""
import collections
import os
import struct
import sys

PROJ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
tag = sys.argv[1]
a = open(os.path.join(PROJ, "local", "e1", tag, "inst2.bin"), "rb").read()
b = open(os.path.join(PROJ, "local", "e1", tag, "inst3.bin"), "rb").read()

REGIONS = [
    (0x00000000, 0x00080000, "EE kernel area"),
    (0x00080000, 0x00100000, "kernel/unused (experiment cave+input table at 0x98000-0xF0FFF)"),
    (0x00100000, 0x004F6580, "ELF .text"),
    (0x0050A880, 0x00546390, "ELF .data"),
    (0x00546480, 0x00596500, "ELF .rodata"),
    (0x00596B00, 0x00597200, "ELF .sdata/.sbss"),
    (0x00597200, 0x00640000, ".bss (below human pool)"),
    (0x00640000, 0x00680000, ".bss human pool area (hyp.)"),
    (0x00680000, 0x00715B5C, ".bss (above human pool)"),
    (0x00715B5C, 0x02000000, "heap"),
]
per = collections.Counter()
heap_blocks = collections.Counter()
for page in range(0, len(a), 4096):
    pa, pb = a[page:page + 4096], b[page:page + 4096]
    if pa == pb:
        continue
    n = sum(1 for x, y in zip(pa, pb) if x != y)
    for lo, hi, name in REGIONS:
        if lo <= page < hi:
            per[name] += n
            break
    if page >= 0x00715B5C:
        heap_blocks[page & ~0xFFFF] += n
print("differing bytes by region:")
for name, n in per.most_common():
    print(f"  {n:9d}  {name}")
print("top heap 64 KiB blocks:", [(hex(k), v) for k, v in heap_blocks.most_common(12)])

f = lambda m, o: struct.unpack_from("<f", m, o)[0]  # noqa: E731
diffh = 0
for k in range(-40, 120):
    o = 0x00640C80 + k * 0x6D0
    if o < 0x00597200 or o + 0x6D0 > 0x00715B5C:
        continue
    pa = [f(a, o + 0x10 + 4 * i) for i in range(3)]
    pb = [f(b, o + 0x10 + 4 * i) for i in range(3)]
    if not all(abs(x) < 1e4 for x in pa):
        continue
    if a[o:o + 0x6D0] != b[o:o + 0x6D0]:
        nd = sum(1 for x, y in zip(a[o:o + 0x6D0], b[o:o + 0x6D0]) if x != y)
        diffh += 1
        print(f"human {o:08x} pidx={struct.unpack_from('<b', a, o + 0x1B0)[0]} bytes differ={nd} posA={[round(x, 2) for x in pa]} posB={[round(x, 2) for x in pb]}")
print("humans differing:", diffh)

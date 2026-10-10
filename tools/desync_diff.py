"""Compare the RAM dumps written by the W4P fork when a desync is detected (DumpDir, w4p_slot<N>_t<T>.bin).

Prints differing ranges grouped by region and the human objects that differ (same classification as the Stage 1
experiments). Usage: python -I tools/desync_diff.py <dump_a.bin> <dump_b.bin>
"""
import collections
import struct
import sys

REGIONS = [
    (0x00000000, 0x00080000, "EE kernel area"),
    (0x00080000, 0x00100000, "kernel/unused (mod code cave 0xF0000-0xF0FFF)"),
    (0x00100000, 0x004F6580, "ELF .text"),
    (0x0050A880, 0x00546390, "ELF .data"),
    (0x00546480, 0x00597200, "ELF .rodata/.sdata/.sbss"),
    (0x00597200, 0x00715B5C, "ELF .bss (incl. human pool)"),
    (0x00715B5C, 0x02000000, "heap"),
]


def main():
    a = open(sys.argv[1], "rb").read()
    b = open(sys.argv[2], "rb").read()
    per = collections.Counter()
    first = None
    for page in range(0, min(len(a), len(b)), 4096):
        if a[page:page + 4096] == b[page:page + 4096]:
            continue
        for i in range(page, page + 4096):
            if a[i] != b[i]:
                if first is None:
                    first = i
                for lo, hi, name in REGIONS:
                    if lo <= i < hi:
                        per[name] += 1
                        break
    print("first differing byte:", hex(first) if first is not None else None)
    for name, n in per.most_common():
        print(f"{n:9d}  {name}")
    f = lambda m, o: struct.unpack_from("<f", m, o)[0]  # noqa: E731
    for k in range(-40, 120):
        o = 0x00640C80 + k * 0x6D0
        if o < 0x00597200 or o + 0x6D0 > 0x00715B5C or a[o:o + 0x6D0] == b[o:o + 0x6D0]:
            continue
        pa = [round(f(a, o + 0x10 + 4 * i), 2) for i in range(3)]
        pb = [round(f(b, o + 0x10 + 4 * i), 2) for i in range(3)]
        print(f"human {o:08x} pidx {struct.unpack_from('<b', a, o + 0x1B0)[0]}: posA {pa} posB {pb}")


if __name__ == "__main__":
    main()

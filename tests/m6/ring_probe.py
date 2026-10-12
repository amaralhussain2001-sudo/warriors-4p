"""Player 3's missing Select ring (F-0194 open point): per player, the four skip tests at the top of the marker loop
FUN_0024B780 (0x0024B90C-0x0024B944: FUN_00227F90, FUN_00227D28, FUN_00223C10, FUN_00227E60 on the human; any non-zero
-> no ring), FUN_00228340, the 'always marked' byte 0x00622E10[i], the pad record (FUN_0021D3E8: 0x00660F50 +
human[+0x92]*0x2C, +0x19 pad, +0x1B has pad) and the ring timing table 0x006C72D8 (4 x 12 bytes, count 0x0051055C).
nav_probe.py --probe ring_probe:ring:<poll>. Calls the predicates through the test-call mailbox (read-only functions,
HYPOTHESIS: no side effects). Function names are OUR labels; static addresses, SLUS-21215 v1.03."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "m2"))
import inv_tests as it  # noqa: E402

SKIP = (0x00227F90, 0x00227D28, 0x00223C10, 0x00227E60, 0x00228340)


def ring(p):
    out = {"poll": it._poll(p), "marked_622e10": [it._r8(p, 0x00622E10 + i) for i in range(4)],
           "flags_510530": [it._r8(p, 0x00510530 + i) for i in range(4)], "debug_5104f8": p.read32(0x005104F8),
           "count_51055c": p.read32(0x0051055C), "views": p.read32(0x0050B198),
           "table": [[hex(p.read32(0x006C72D8 + 12 * k + 4 * j)) for j in range(3)] for k in range(4)], "players": []}
    for i in range(4):
        h, o = it._player(p, i)
        if not o:
            out["players"].append(None)
            continue
        rec = 0x00660F50 + it._s16(p.read32(o + 0x90) >> 16) * 0x2C
        row = {"handle": hex(h), "obj": hex(o), "pidx": it._r8(p, o + 0x1B0), "pad": it._r8(p, rec + 0x19),
               "has_pad": it._r8(p, rec + 0x1B), "skip": {}}
        for fn in SKIP:
            row["skip"][hex(fn)] = it._call(p, fn, o)["v0"]
        out["players"].append(row)
    return out

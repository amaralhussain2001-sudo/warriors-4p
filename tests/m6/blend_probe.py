"""Blend hand-over check (camD/camA regression: after a blended CameraMakeActive a view keeps the blend camera): per view
the active/render/blend arrays (relocated 0x000F0800 / 0x000F0810 / 0x000F0870) and, for a blend camera, from +0x210,
to +0x214, duration +0x218, elapsed +0x21C, progress +0x220 and its own player index byte +0x1D8 (vtable +0x27C getter
0x004DB238 'lb v0,0x1d8(a0)'), which the blend update FUN_00143590 passes to FUN_0011EE08 for the hand-over.
Read-only. nav_probe.py --probe blend_probe:read:<poll>."""
import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "m2"))
import inv_tests as it  # noqa: E402

ACTIVE, RENDER, FOLLOW, BLEND = 0x000F0800, 0x000F0810, 0x000F0820, 0x000F0870


def _f(v):
    return round(struct.unpack("<f", struct.pack("<I", v))[0], 3)


def read(p):
    out = {"poll": it._poll(p), "views": p.read32(0x0050B198), "cameras": p.read32(0x0050B19C)}
    for i in range(4):
        b = p.read32(BLEND + 4 * i)
        d = {"active": hex(p.read32(ACTIVE + 4 * i)), "render": hex(p.read32(RENDER + 4 * i)),
             "follow": hex(p.read32(FOLLOW + 4 * i)), "blend": hex(b)}
        if 0x00100000 <= b < 0x02000000:
            d.update(idx=it._r8(p, b + 0x1D8), frm=hex(p.read32(b + 0x210)), to=hex(p.read32(b + 0x214)),
                     dur=_f(p.read32(b + 0x218)), elapsed=_f(p.read32(b + 0x21C)), progress=_f(p.read32(b + 0x220)))
        a = p.read32(ACTIVE + 4 * i)
        if 0x00100000 <= a < 0x02000000:
            d["active_idx"] = it._r8(p, a + 0x1D8)
        out[i] = d
    return out

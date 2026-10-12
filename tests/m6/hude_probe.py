"""hudE (docs/research/m6_hud_parity.md): read-only probes for the per-player HUD items of players 3-4, plus one
TEST-ONLY write (arcs_on, from marker_probe). nav_probe.py --probe hude_probe:<function>:<poll>.

hud(p): per player index 0-3: handle, pad record, squad pointer (0x006D53F0 + human[+0x92]*0x2F0, +0x20C; FUN_001AA9B0
reads +0x5E8/+0x5F0 there), PlayerHUD (T_A 0x000E0848[i], B1) +0x411C show time, +0x4104, +0x40F8 active, +0x40FC shown;
radars 1-4 (HUD+0x15D0, HUD+0x3F10, 0x000A9500, 0x000ABE40): +0/+4/+8/+0xC flags, zoom +0x2920, vector +0x2930;
arc widgets HUD+0x177D0/HUD+0x18280: +0xA90 player index, +0xA94/+0xA98, fractions +0x38/+0x148/+0x258/+0x368,
smoothing +0x3C/+0x14C/+0x25C/+0x36C, positions +0x20/+0x130/+0x240/+0x350 (first 3 floats); LOOK9 copies 0x000E8A00;
the always-marked bytes 0x00622E10[0..3]; ring table 0x006C72D8; non-zero words in the RAM ranges hudE uses.
Function names are OUR labels; static addresses (SLUS-21215 v1.03)."""
import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "m2"))
import inv_tests as it  # noqa: E402
import marker_probe as mp  # noqa: E402

HUD = 0x00600840
RADARS = (HUD + 0x15D0, HUD + 0x3F10, 0x000A9500, 0x000ABE40)
WIDGETS = (HUD + 0x177D0, HUD + 0x18280)


def _f(v):
    return round(struct.unpack("<f", struct.pack("<I", v & 0xFFFFFFFF))[0], 4)


def _nz(p, lo, hi):
    return [hex(a) for a in range(lo, hi, 4) if p.read32(a)]


def hud(p):
    gm = p.read32(0x0051489C)
    out = {"poll": it._poll(p), "views": p.read32(0x0050B198), "layout": p.read32(0x0050B1A4),
           "count": it._s16(p.read32(gm + 0x224) & 0xFFFF), "clock": p.read32(p.read32(0x0050B734) + 0x48),
           "marked_622e10": [it._r8(p, 0x00622E10 + i) for i in range(4)],
           "ring_table": [[hex(p.read32(0x006C72D8 + 12 * k + 4 * j)) for j in range(3)] for k in range(4)],
           "ring_count": p.read32(0x0051055C), "look9": [hex(p.read32(0x000E8A00)), hex(p.read32(0x000E8A04))],
           "players": [], "radars": [], "widgets": []}
    for i in range(4):
        h, o = it._player(p, i)
        row = {"handle": hex(h)}
        if o:
            idx = it._s16(p.read32(o + 0x90) >> 16)
            rec = 0x00660F50 + idx * 0x2C
            brain = 0x006D53F0 + idx * 0x2F0
            row.update(obj=hex(o), pidx=it._r8(p, o + 0x1B0), slot=it._s32(p.read32(o + 0x380)),
                       pad=it._r8(p, rec + 0x19), has_pad=it._r8(p, rec + 0x1B), squad=hex(p.read32(brain + 0x20C)),
                       draw_2b4=(p.read32(p.read32(o + 0xD8) + 0x2B4) if 0x00100000 <= p.read32(o + 0xD8) < 0x02000000 else None),
                       pos=it._pos(p, o))
        ph = p.read32(0x000E0848 + 4 * i)
        if ph:
            row["phud"] = {"ptr": hex(ph), "411c": p.read32(ph + 0x411C), "4104": p.read32(ph + 0x4104),
                           "40f8": p.read32(ph + 0x40F8), "40fc": p.read32(ph + 0x40FC)}
        out["players"].append(row)
    for r in RADARS:
        out["radars"].append({"base": hex(r), "flags": [p.read32(r + 4 * k) for k in range(4)],
                              "zoom": _f(p.read32(r + 0x2920)), "vec": [_f(p.read32(r + 0x2930 + 4 * k)) for k in range(4)]})
    for w in WIDGETS:
        out["widgets"].append({"base": hex(w), "a90": p.read32(w + 0xA90), "a94": p.read32(w + 0xA94),
                               "a98": p.read32(w + 0xA98),
                               "frac": [_f(p.read32(w + o)) for o in (0x38, 0x148, 0x258, 0x368)],
                               "smooth": [_f(p.read32(w + o)) for o in (0x3C, 0x14C, 0x25C, 0x36C)],
                               "pos": [[_f(p.read32(w + o + 4 * k)) for k in range(3)] for o in (0x20, 0x130, 0x240, 0x350)]})
    out["nonzero_E0CB0_E1000"] = _nz(p, 0x000E0CB0, 0x000E1000)
    out["nonzero_E8158_E82C0"] = _nz(p, 0x000E8158, 0x000E82C0)
    return out


def arcs_on(p):
    """TEST ONLY (PINE write): marker_probe.arcs_on (squad timers +0x5E8/+0x5F0 = clock + 9.5 s), then hud()."""
    out = {"arcs_on": mp.arcs_on(p)}
    out["hud"] = hud(p)
    return out

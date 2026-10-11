"""60 fps mode measured with four views (M2 criterion 6): the scripted boot only works at 30 fps (R-22), so the
[warriors-4p 60fps] words are written into memory mid-mission (the same writes PCSX2's patch engine makes; the group's
lines are read from mod/w4p_m1.pnach). Run with --ee 2 (EE 180 %, required by the 60 fps patch, F-0100). Used by
nav_probe.py --probe sixty_probe:enable:<poll>; single instance, test only."""
import os
import re

PNACH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "mod", "w4p_m1.pnach")


def _lines():
    txt = open(PNACH, encoding="utf-8", errors="replace").read().replace("\r", "")
    grp = txt.split("[warriors-4p 60fps]", 1)[1].split("\n[", 1)[0]
    return re.findall(r"^patch=\d,EE,([0-9A-Fa-f]{8}),(word|byte),([0-9A-Fa-f]+)", grp, re.M)


def enable(p):
    out = []
    for addr, kind, val in _lines():
        a, v = int(addr, 16), int(val, 16)
        if kind == "byte":
            w = p.read32(a & ~3)
            sh = 8 * (a & 3)
            p.write32(a & ~3, (w & ~(0xFF << sh)) | (v << sh))
        else:
            p.write32(a, v)
        out.append((addr, kind, val, hex(p.read32(a & ~3))))
    return {"poll": p.read32(0x000F0500), "written": out}

"""M17 crash (F-0181): which ScreenEffects object holds the overlay effect whose camera index (+0x28) is garbage?
Read-only. Dumps the ScreenEffects pointer arrays (mirror 0x000F0890[4], original 0x005FDEB8[2]), the array at
0x005FDEC0 (25 words, filled by FUN_0018BE58), every ScreenEffects object's view (+0x212) and overlay-effect slots
(+0x154 + k*0x10: object, +0x15C/+0x160 flags), every overlay object's vtable (+0x94) and camera index (+0x28), the view
count 0x0050B198 and the render camera table 0x005D9148-0x005D9167.
Used by nav_probe.py --probe fx_crash_probe:snap:<poll> and fx_crash_probe:after_stall:<poll> (waits until the poll
counter stops for 4 s, max 90 s, then dumps)."""
import time


def _obj(p, a):
    if not (0x00100000 <= a < 0x02000000):
        return None
    return {"vt94": hex(p.read32(a + 0x94)), "cam28": hex(p.read32(a + 0x28)), "w4": hex(p.read32(a + 4))}


def _se(p, a):
    if not (0x00100000 <= a < 0x02000000):
        return None
    out = {"addr": hex(a), "view212": p.read32(a + 0x210) >> 16, "slots": []}
    for k in range(4):
        b = a + 0x154 + 0x10 * k
        o = p.read32(b)
        out["slots"].append({"obj": hex(o), "f15c": p.read32(b + 8), "f160": p.read32(b + 12), "o": _obj(p, o)})
    return out


def snap(p):
    mirror = [p.read32(0x000F0890 + 4 * i) for i in range(4)]
    orig = [p.read32(0x005FDEB8 + 4 * i) for i in range(2)]
    dec0 = [p.read32(0x005FDEC0 + 4 * i) for i in range(25)]
    return {"poll": p.read32(0x000F0500), "views": p.read32(0x0050B198),
            "players": p.read32(p.read32(0x0051489C) + 0x224) & 0xFFFF,
            "mirror": [hex(v) for v in mirror], "orig": [hex(v) for v in orig],
            "dec0": [hex(v) for v in dec0], "dec0_objs": [_obj(p, v) for v in dec0 if v],
            "cams_5d9148": [hex(p.read32(0x005D9148 + 4 * i)) for i in range(8)],
            "se": [_se(p, a) for a in mirror]}


def after_stall(p):
    last, since, t0 = p.read32(0x000F0500), time.time(), time.time()
    while time.time() - t0 < 90:
        time.sleep(0.5)
        cur = p.read32(0x000F0500)
        if cur != last:
            last, since = cur, time.time()
        elif time.time() - since > 4:
            break
    out = snap(p)
    out["stalled"] = time.time() - since > 4
    return out


def _dump(p, a0, a1):
    return {hex(a): hex(p.read32(a)) for a in range(a0, a1, 4)}


def region(p):
    """Words around view 3's room-smoke object (0x00C97B00 in fxc_m17) to find the neighbouring allocation."""
    se2 = p.read32(0x000F0890 + 8)
    oe = p.read32(se2 + 0x184) if 0x00100000 <= se2 < 0x02000000 else 0
    out = {"poll": p.read32(0x000F0500), "oe_view3": hex(oe)}
    if 0x00100000 <= oe < 0x02000000:
        out["words"] = _dump(p, oe - 0x500, oe + 0x100)
    return out


def region_after_stall(p):
    out = after_stall(p)
    out["region"] = region(p)
    return out


def particles(p):
    """Each view's room-smoke object: its particle list (+4 begin, +8 end) and the first 0x40 words of each particle."""
    out = {"poll": p.read32(0x000F0500), "views": []}
    for i in range(4):
        se = p.read32(0x000F0890 + 4 * i)
        oe = p.read32(se + 0x184) if 0x00100000 <= se < 0x02000000 else 0
        v = {"se": hex(se), "oe": hex(oe)}
        if 0x00100000 <= oe < 0x02000000:
            b, e = p.read32(oe + 4), p.read32(oe + 8)
            v.update({"list_begin": hex(b), "list_end": hex(e), "list_cap": hex(p.read32(oe + 0xC)),
                      "oe_head": [hex(p.read32(oe + 4 * k)) for k in range(16)]})
            parts = []
            if 0x00100000 <= b < 0x02000000 and 0 <= e - b <= 0x40:
                for a in range(b, e, 4):
                    pp = p.read32(a)
                    parts.append({"ptr": hex(pp), "words": [hex(p.read32(pp + 4 * k)) for k in range(0x40)]
                                  if 0x00100000 <= pp < 0x02000000 else None})
            v["particles"] = parts
        out["views"].append(v)
    return out


def particles_after_stall(p):
    out = after_stall(p)
    out["particles"] = particles(p)
    return out

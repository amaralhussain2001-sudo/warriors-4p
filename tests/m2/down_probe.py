"""Single downed player (F-0148 risk, docs/STATE.md step 2): down ONE player with the game's HuKill core FUN_00237E70
(health 1, down state; FUN_002302A8) through the test-call mailbox, then read the view layout and what each PC's crop
would show. Used by nav_probe.py --probe module:function:poll; needs the "warriors-4p test call" group; test only."""
import time

PADS = (0, 4, 1, 2)  # session slot -> game pad (nav_probe default --pads)


def _r16(p, a):
    return (p.read32(a & ~3) >> (8 * (a & 2))) & 0xFFFF


def _r8(p, a):
    return (p.read32(a & ~3) >> (8 * (a & 3))) & 0xFF


def _human(p, h):
    if h in (0, 0xFFFFFFFF):
        return 0
    obj = p.read32(0x006EBD38 + 8 * (h >> 16))
    return obj if obj and _r16(p, 0x006EBD38 + 8 * (h >> 16) + 4) == (h & 0xFFFF) else 0


def _down(p, idx):
    gm = p.read32(0x0051489C)
    h = p.read32(gm + 0x228 + 4 * idx)
    if h in (0, 0xFFFFFFFF):
        return {"error": f"no player {idx + 1}"}
    p.batch_write32([(0x000F0304, h), (0x000F0308, 0), (0x000F030C, 0), (0x000F0310, 0), (0x000F0318, 0),
                     (0x000F0300, 0x00237E70)])
    for _ in range(80):
        if p.read32(0x000F0318) == 1:
            break
        time.sleep(0.05)
    return {"handle": hex(h), "done": p.read32(0x000F0318), "poll": p.read32(0x000F0500)}


def down_p1(p):
    return _down(p, 0)


def down_p2(p):
    return _down(p, 1)


def views(p):
    """Layout (views, cols x rows), merge flags, per player: state flags, health, active camera and its +0x1D6 byte,
    and per PC the player index that its crop uses (pad owner +0x42, CropFor in W4P.cpp)."""
    gm = p.read32(0x0051489C)
    out = {"poll": p.read32(0x000F0500), "views": p.read32(0x0050B198), "cameras": p.read32(0x0050B19C),
           "cols": _r16(p, 0x0050B1A8), "rows": _r16(p, 0x0050B1AA),
           "merge": [p.read32(0x0050B1E8), p.read32(0x0050B1EC)], "players": p.read32(gm + 0x224) & 0xFFFF,
           "focus": hex(p.read32(0x005D91B8)), "gameover": p.read32(gm + 0x14C)}
    pl = []
    for i in range(4):
        h = p.read32(gm + 0x228 + 4 * i)
        hu = _human(p, h)
        row = {"handle": hex(h)}
        if hu:
            st = p.read32(hu + 0xD4)
            row.update({"flags": hex(p.read32(st) | (p.read32(st + 4) << 32)),
                        "health": _r16(p, st + 0x144), "index": _r8(p, hu + 0x1B0)})
        cam = p.read32(0x000F0800 + 4 * i)  # active camera per player with the 4p group (moved from 0x005D9148)
        if i < 2 and not cam:  # 2-player runs without the 4p group
            cam = p.read32(0x005D9148 + 4 * i)
        row.update({"camera": hex(cam), "cam_1d6": _r8(p, cam + 0x1D6) if cam else None})
        pl.append(row)
    out["player"] = pl
    out["crop_index_per_slot"] = [_r16(p, 0x005DD810 + pad * 0x50 + 0x42) for pad in PADS]
    return out

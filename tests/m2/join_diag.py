"""Why does a drop-in join not happen (M6 smoke: missions without players 3-4)? Read-only: GameMgr join fields
(UpdateJoin FUN_0041A460 conditions: +0x56E8 join flag, +0x158 mode in {0,3}, +0x224 count, +0x56EC 2-player flag),
cinematic flag +0x410, level / checkpoint, pad owners and connected flags, top game mode, players' handles.
Used by nav_probe.py --probe join_diag:read:<poll>."""


def _r16(p, a):
    return (p.read32(a & ~3) >> (8 * (a & 2))) & 0xFFFF


def _s16(v):
    return v - 0x10000 if v & 0x8000 else v


def read(p):
    gm = p.read32(0x0051489C)
    top = p.read32(0x0050C784)
    lvl_idx = _r16(p, gm + 0x56DC)
    return {"poll": p.read32(0x000F0500), "count": p.read32(gm + 0x224) & 0xFFFF,
            "join_56e8": p.read32(gm + 0x56E8), "mode_158": p.read32(gm + 0x158), "mp_56ec": p.read32(gm + 0x56EC),
            "cine_410": p.read32(gm + 0x410), "levelend_14c": p.read32(gm + 0x14C),
            "level": p.read32(gm + 0x14D4 + lvl_idx * 0x84 + 4), "cp": _r16(p, gm + 0x33A),
            "top_mode": hex(p.read32(0x005E66A0 + 4 * top)) if top < 64 else None,
            "handles": [hex(p.read32(gm + 0x228 + 4 * i)) for i in range(4)],
            "pad_owner": [_s16(_r16(p, 0x005DD810 + pad * 0x50 + 0x42)) for pad in range(8)],
            "pause_cooldown": p.read32(0x0063083C)}


def _call(p, fn, *args):
    import time
    vals = [a & 0xFFFFFFFF for a in args] + [0] * (4 - len(args))
    p.batch_write32([(0x000F0304, vals[0]), (0x000F0308, vals[1]), (0x000F030C, vals[2]), (0x000F0310, vals[3]),
                     (0x000F0318, 0), (0x000F0300, fn)])
    for _ in range(80):
        if p.read32(0x000F0318) == 1:
            break
        time.sleep(0.05)
    return {"fn": hex(fn), "done": p.read32(0x000F0318), "v0": hex(p.read32(0x000F0314))}


def pick(p):
    """PickJoinCompanion FUN_0022A770(gang of player 1, 0): which human would a join take (0 = none)."""
    gm = p.read32(0x0051489C)
    h = p.read32(gm + 0x228)
    obj = p.read32(0x006EBD38 + 8 * (h >> 16))
    brain = 0x006D53F0 + 0x2F0 * _s16(_r16(p, obj + 0x92))
    gang = p.read32(brain + 0x20C)
    r = _call(p, 0x0022A770, gang, 0)
    return {"poll": p.read32(0x000F0500), "gang": hex(gang), "pick": r}


def join_pad1(p):
    """UpdateJoin FUN_0041A460(GameMgr, 1): the game's drop-in join for pad 1, called directly."""
    gm = p.read32(0x0051489C)
    r = _call(p, 0x0041A460, gm, 1)
    return {"call": r, "after": read(p)}

"""T2c: world pick-up by player 3 or 4 with nobody else near. In invt2 the Flash dropped at player 3's feet was taken by
player 2 standing next to him; in invt2b the "Flash objects" used as teleport targets were items carried by enemies
(pockets), so standing on them picked nothing up. Here the OTHER three players are moved far away with the game's
Lua Teleport core FUN_00385BB8 (to the position of the farthest carried Flash, a valid floor point 65-80 units from the
start, seen in invt2b), then inv_tests.t2_setup_p3 / _p4 drops a Flash at the tested player's feet and the
invt_t2 scripts walk him out and back. Used by nav_probe.py --probe inv_t2c:<function>:<poll>; test only."""
import struct

import inv_tests as T

SCRATCH = 0x000E5D00  # free low RAM (no pnach line uses 0x000E5Dxx)


def _away(p, keep, also=()):
    objs = T._objs_list(T._find_objs(p))
    ppos = [T._pos(p, x) for x in (T._player(p, k)[1] for k in range(4)) if x]
    if not objs or not ppos:
        return {"error": "no far target"}
    best = max(objs, key=lambda ob: min(T._dist(ob["pos"], q) for q in ppos))
    p.batch_write32([(SCRATCH + 4 * k, struct.unpack("<I", struct.pack("<f", v))[0]) for k, v in enumerate(best["pos"])])
    out = {"poll": T._poll(p), "target": best["pos"], "moved": {}}
    for k in range(4):
        if k == keep or k in also:
            continue
        h, o = T._player(p, k)
        if o:
            out["moved"][k + 1] = T._call(p, T.TELEPORT, h, SCRATCH, 0xFFFFFFFF)["done"]
    o = T._player(p, keep)[1]
    me = T._pos(p, o)
    out["dist_to_tested"] = {k + 1: T._dist(me, T._pos(p, T._player(p, k)[1])) for k in range(4) if k != keep and T._player(p, k)[1]}
    return out


def away_for_p3(p):
    return _away(p, 2)


def away_for_p4(p):
    return _away(p, 3)


def away_for_34(p):
    """Revive test without obstruction: players 1-2 far away, players 3-4 stay (the revive's sight sweep
    FUN_0021C0A8 refuses when anything, a teammate included, is between reviver and downed player)."""
    return _away(p, 2, also=(3,))


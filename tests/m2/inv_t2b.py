"""T2b (docs/research/m2_inventory_tests.md T2 follow-up): world pick-up of a Flash by player 3 or 4 ALONE.
In invt2 the Flash dropped at player 3's feet was collected by player 2 standing next to him (and the second one by
player 1). Here the player is moved with the game's Lua Teleport core FUN_00385BB8(handle, float[3]*, -1) onto the
Flash object ("dyn_revival", powerup_item) that is farthest from all players, so nobody else can touch it first.
Used by nav_probe.py --probe inv_t2b:<function>:<poll>; single instance, test only. Scratch vector at 0x000E5D00
(free low RAM, no pnach line uses 0x000E5Dxx)."""
import struct

import inv_tests as T

SCRATCH = 0x000E5D00


def _go(p, i):
    h, o = T._player(p, i)
    if not o:
        return {"error": f"no player {i + 1}"}
    objs = T._objs_list(T._find_objs(p))
    ppos = [T._pos(p, x) for x in (T._player(p, k)[1] for k in range(4)) if x]
    if not objs or not ppos:
        return {"error": "no Flash object or no players", "objects": objs}
    best = max(objs, key=lambda ob: min(T._dist(ob["pos"], q) for q in ppos))
    p.batch_write32([(SCRATCH + 4 * k, struct.unpack("<I", struct.pack("<f", v))[0]) for k, v in enumerate(best["pos"])])
    before = T._all_counts(p)
    r = T._call(p, T.TELEPORT, h, SCRATCH, 0xFFFFFFFF)
    return {"poll": T._poll(p), "player": i + 1, "target": best, "teleport": r, "counts_before": before,
            "pos_after": T._pos(p, o), "nearest_other": min(T._dist(best["pos"], q) for q in ppos)}


def go_p3(p):
    return _go(p, 2)


def go_p4(p):
    return _go(p, 3)


def read(p):
    pos = {}
    for k in range(4):
        o = T._player(p, k)[1]
        pos[k + 1] = T._pos(p, o) if o else None
    return {"poll": T._poll(p), "counts": T._all_counts(p), "flash_objects": T._find_objs(p), "pos": pos}

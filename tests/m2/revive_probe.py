"""Partner revive for any pair (follow-up of T4, docs/research/m2_inventory_tests.md): the downed player is downed with
HuKill FUN_00237E70, the reviver gets exactly one Flash and is moved within the 3.0-unit radius, then presses D-pad
Left (script) and, if the downed player is still down, the button action FUN_00286BA8(reviver human) is called
directly. Pairs (game player index downed, reviver): ctrl = (1, 0) the original 2-player pair; p3 = (2, 0) player 1
revives player 3; p4by3 = (3, 2). Used by nav_probe.py --probe revive_probe:<pair>_<step>:<poll>; test only."""
import inv_tests as T

PAIRS = {"ctrl": (1, 0), "p3": (2, 0), "p4by3": (3, 2), "p1by3": (0, 2), "p3by4": (2, 3)}
REVIVE_ACTION = 0x00286BA8


def _setup(p, pair):
    d, r = PAIRS[pair]
    hd, od = T._player(p, d)
    hr, orv = T._player(p, r)
    if not (od and orv):
        return {"error": "players missing"}
    sd, sr = T._s32(p.read32(od + 0x380)), T._s32(p.read32(orv + 0x380))
    gm = T._gm(p)
    T._SNAP.setdefault(f"rv_{pair}", {"sd": sd, "sr": sr, "before": T._all_counts(p)})
    p.write32(T._count_addr(gm, sr, 1), 1)
    p.write32(T._count_addr(gm, sd, 1), 0)
    out = {"poll": T._poll(p), "pair": [d + 1, r + 1], "slots": [sd, sr]}
    out["kill"] = T._once(p, f"rv_kill_{pair}", T.HU_KILL, hd)
    out["downed"], out["reviver"] = T._human(p, od), T._human(p, orv)
    return out


def _move(p, pair):
    d, r = PAIRS[pair]
    hd, od = T._player(p, d)
    hr, orv = T._player(p, r)
    out = {"poll": T._poll(p), "dist_before": T._dist(T._pos(p, od), T._pos(p, orv))}
    if out["dist_before"] > 2.5:
        out["teleport_onto"] = T._once(p, f"rv_tp_{pair}", T.TELEPORT, hr, T.POS_TABLE + T._bidx(p, od) * 0x20, 0xFFFFFFFF)
        out["dist_after"] = T._dist(T._pos(p, od), T._pos(p, orv))
    out["preconditions"] = T._revive_pre(p, od, orv)
    return out


def _direct(p, pair):
    d, r = PAIRS[pair]
    od, orv = T._player(p, d)[1], T._player(p, r)[1]
    a = T._human(p, od)
    if not a.get("down"):
        return {"poll": T._poll(p), "skipped": "downed player is up already"}
    return {"poll": T._poll(p), "preconditions": T._revive_pre(p, od, orv),
            "revive_try": T._once(p, f"rv_direct_{pair}", REVIVE_ACTION, orv)}


def _read(p, pair):
    d, r = PAIRS[pair]
    od, orv = T._player(p, d)[1], T._player(p, r)[1]
    snap = T._SNAP.get(f"rv_{pair}", {})
    c = T._all_counts(p)
    a = T._human(p, od)
    return {"poll": T._poll(p), "downed": a, "reviver": T._human(p, orv), "counts": c,
            "result": {"down": a.get("down"), "hp": a.get("hp"),
                       "flash_reviver": c[snap["sr"]]["flash"] if snap else None,
                       "pass": a.get("down") is False and (a.get("hp") or 0) > 1}}


def _make(pair):
    return (lambda p: _setup(p, pair), lambda p: _move(p, pair), lambda p: _direct(p, pair), lambda p: _read(p, pair))


for _pair in PAIRS:
    globals()[f"{_pair}_setup"], globals()[f"{_pair}_move"], globals()[f"{_pair}_direct"], globals()[f"{_pair}_read"] = _make(_pair)


FIND_DOWNED = 0x00279078   # (reviver) -> downed human in 3.0 units passing FUN_00278FA0, or 0
SIGHT = 0x0021C0A8         # (reviver, downed) -> nonzero lets the revive go on; else needs downed+0x1B0 != -1 and brain+4 == 3


def _diag(p, pair):
    """Which step of FUN_00286BA8 refuses: the candidate search, then FUN_0021C0A8, then the brain+4 == 3 branch."""
    d, r = PAIRS[pair]
    od, orv = T._player(p, d)[1], T._player(p, r)[1]
    found = T._call(p, FIND_DOWNED, orv)
    sight = T._call(p, SIGHT, orv, od)
    return {"poll": T._poll(p), "pair": [d + 1, r + 1], "downed_obj": hex(od),
            "find_downed_v0": hex(found["v0"] & 0xFFFFFFFF), "found_is_downed": (found["v0"] & 0xFFFFFFFF) == od,
            "sight_v0": sight["v0"], "downed_1b0": T._r8(p, od + 0x1B0),
            "reviver_brain4": T._s32(p.read32(T.BRAINS + T._bidx(p, orv) * T.BRAIN_SIZE + 4)),
            "preconditions": T._revive_pre(p, od, orv)}


def p3_diag(p):
    return _diag(p, "p3")


def ctrl_diag(p):
    return _diag(p, "ctrl")


def p3by4_diag(p):
    return _diag(p, "p3by4")

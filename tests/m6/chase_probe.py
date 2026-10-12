"""D24 chase stretches with 4 players (docs/research/m6_chase4p.md): read-only state of the M18 car escape (level84 cp2)
and the M8 cart chase (level81 cp3) for nav_probe.py --probe chase_probe:<function>:<poll> (one instance) and for
tests/m6/chase4p_run.py (PINE samples of one of four lockstep instances).

Read-only (no writes, no game calls) except lua_markers(), which runs a short Lua text through LUARUN like
tests/m2/x6fix_probe.py (result through player 1's money, restored). Function names are OUR labels (the ELF is stripped);
static addresses, SLUS-21215 v1.03. Human fields (VERIFIED static, docs/research/m6_chase4p.md section 1):
  *(human+0xD4) -> u64 status flags; bit 44 (0x100000000000) = button-tap mode (FUN_00234318),
  human+0x670 / +0x674 tap counters, +0x678 index of the next tap path flag, +0x67C.. flags, +0x6BC car handle,
  human+0xD0 char id, +0x1B0 player index, +0x380 HUD slot.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "m2"))
import inv_tests as it  # noqa: E402

N_CALL, N_OK, LAST_PAD = 0x000ED3E0, 0x000ED3E4, 0x000ED3E8   # W4P_JoinAs counters ([warriors-4p missions], D24)
WANT = 0x000E25A0                                            # X2W's wanted human ([4p spawn], D24)
LC_N, LC_LOG = 0x000E7AFC, 0x000E7B00
VIEWS = 0x0050B198
MODE_TOP, MODE_STACK = 0x0050C784, 0x005E66A0
TAP_BIT = 1 << 44
CHARS = {9: "Swan(chase)", 36: "Snow(chase)", 16: "Cochise", 27: "Vermin", 5: "Swan", 33: "Snow", 4: "Cleon(chase)",
         1: "Cleon", 11: "Ajax", 12: "Ajax(gen)", 34: "Snow(gen)", 19: "Cowboy", 31: "Rembrandt", 222: "Mercy"}


def _flags(p, o):
    st = p.read32(o + 0xD4)
    if not 0x00100000 <= st < 0x02000000:
        return None
    return p.batch_read64([st])[0]


def _runner(p, o):
    fl = _flags(p, o)
    hp = None
    st = p.read32(o + 0xD4)
    if 0x00100000 <= st < 0x02000000:
        hp = it._s16(p.read32(st + 0x144))
    cid = p.read32(o + 0xD0) & 0xFFFF
    b = p.read32(o + 0x1B0) & 0xFF
    return {"obj": hex(o), "char": cid, "name": CHARS.get(cid), "pidx": b - 256 if b & 0x80 else b,
            "hud": it._s32(p.read32(o + 0x380)), "tap": bool(fl is not None and fl & TAP_BIT),
            "down": bool(fl is not None and fl & 0x40000), "dead": bool(fl is not None and fl >> 32 & 1),
            "hp": hp, "c670": it._s32(p.read32(o + 0x670)), "c674": it._s32(p.read32(o + 0x674)),
            "flag_idx": it._s32(p.read32(o + 0x678)), "pos": [round(v, 2) for v in it._pos(p, o)],
            "gang": hex(p.read32(it.BRAINS + it._bidx(p, o) * it.BRAIN_SIZE + 0x20C))}


def state(p):
    gm = it._gm(p)
    out = {"poll": it._poll(p), "checkpoint": it._r16(p, gm + 0x33A), "level": it._cstr(p, gm + 0x124, 16),
           "count": it._s16(p.read32(gm + 0x224)), "join_flag": p.read32(gm + 0x56E8), "cin_410": p.read32(gm + 0x410),
           "gm_14c": p.read32(gm + 0x14C), "views": p.read32(VIEWS),
           "mode_top": hex(p.read32(MODE_STACK + 4 * p.read32(MODE_TOP))) if p.read32(MODE_TOP) < 16 else None,
           "joinas": [p.read32(N_CALL), p.read32(N_OK), it._s32(p.read32(LAST_PAD))], "want": hex(p.read32(WANT)),
           "pads": it._pads(p), "players": {}}
    for i in range(4):
        h, o = it._player(p, i)
        if o:
            out["players"][i + 1] = dict(_runner(p, o), handle=hex(h))
    n = p.read32(LC_N)
    out["lc_names"] = [it._cstr(p, LC_LOG + 32 * ((n - 1 - j) & 7), 32) for j in range(min(n, 4))]
    return out


def lua_markers(p):
    """Rows present? helpers (W4P_O.h), M18 chase row (W4P_O.m18c), M8 chase row (W4P_O.m8c) -> three digits 1/0."""
    import x6fix_probe as xf
    return xf._markers(p, f"d24mk_{it._poll(p)}", ["W4P_O and W4P_O.h", "W4P_O and W4P_O.m18c", "W4P_O and W4P_O.m8c"])


def lua_runners(p):
    """M18: runner slots W4P_RN[1] (Cochise) / [2] (Vermin) joined, their tap and done marks -> W4P_R = 6 digits."""
    import x6fix_probe as xf
    checks = ["W4P_RN and W4P_RN[1]", "W4P_RN and W4P_RN.t1", "W4P_RN and W4P_RN.d1"]
    t = it._poll(p)
    a = xf._markers(p, f"d24rn1_{t}", checks)
    b = xf._markers(p, f"d24rn2_{t}", [c.replace("1", "2") for c in checks])
    return {"cochise": a, "vermin": b}


def cams(p):
    """Per-view cameras (relocated 4-entry arrays of the 4p group: render 0x000F0810, follow 0x000F0820, rail 0x000F0830)
    and the players, for the M18 beach rail cameras of players 3-4 (D24)."""
    import x6fix_probe as xf
    gm = it._gm(p)
    return {"poll": it._poll(p), "checkpoint": it._r16(p, gm + 0x33A), "views": p.read32(VIEWS), "join_flag": p.read32(gm + 0x56E8),
            "count": it._s16(p.read32(gm + 0x224)), "cams": xf._cams(p), "players": xf._players(p)}


HUMANS0, HUMAN_SIZE = 0x00640C80, 0x6D0     # human array (nav_probe.py humans scan)


def humans(p, ids=(1, 4, 5, 9, 11, 12, 33, 34, 16, 27, 36)):
    """Every human whose char id is in ids: char, player index, position, health, down/tap flags (M8 lanes, D24)."""
    out = []
    for k in range(-40, 120):
        o = HUMANS0 + k * HUMAN_SIZE
        if not (0x00597200 <= o and o + HUMAN_SIZE <= 0x00715B5C):
            continue
        st = p.read32(o + 0xD4)
        if not 0x00100000 <= st < 0x02000000:
            continue
        cid = p.read32(o + 0xD0) & 0xFFFF
        if cid not in ids:
            continue
        r = _runner(p, o)
        out.append({k2: r[k2] for k2 in ("obj", "name", "char", "pidx", "tap", "down", "hp", "pos", "flag_idx")})
    return {"poll": it._poll(p), "checkpoint": it._r16(p, it._gm(p) + 0x33A), "humans": out}


M8_FLAGS = ([f"fChase1Path[{i}]" for i in range(1, 11)] + [f"fChase2Path[{i}]" for i in range(1, 11)]
            + ["fCCleon", "fCSwan", "fCSwan2", "fCSnow", "fCAjax", "fJSwan", "fJSnow", "fJAjax", "fChaseEnd"])


def m8_flags(p):
    """M8 cp3 lane flags through Lua GetFlagPos: each coordinate as (v + 2000) * 10 through player 1's money (read-only
    for the game except the money, restored by _q)."""
    import x6fix_probe as xf
    n = len(M8_FLAGS)
    src = ("W4P_V = {} local t = {" + ", ".join(M8_FLAGS) + "} "
           f"for i = 1, {n} do local q = t[i] and GetFlagPos(t[i]) "
           "if q then W4P_V[i * 3 - 2] = (q.x + 2000) * 10 W4P_V[i * 3 - 1] = (q.y + 2000) * 10 "
           "W4P_V[i * 3] = (q.z + 2000) * 10 end end W4P_R = 1")
    names = tuple(f"W4P_V[{j}]" for j in range(1, 3 * n + 1))
    r = xf._q(p, f"m8fl_{it._poll(p)}", src, names=names)
    flags = {}
    for i, nm in enumerate(M8_FLAGS):
        v = [r["values"].get(f"W4P_V[{3 * i + k}]") for k in (1, 2, 3)]
        flags[nm] = [round(x / 10 - 2000, 1) if isinstance(x, int) and x != 998 else x for x in v]
    return {"poll": r["poll"], "status": r["status"], "flags": flags}

"""Camera parity agent camD (local/m6/cam/BRIEF.md): runtime checks of the camD LUACH rows (local/m6/cam/camD/rows):
M3 cp5 stealth tutorial locked camera (m3t), M10 cp5 sneak corner cameras (m10s), M5 cp1 clinic intro (m5i),
M11 cp6 Birdie secondary target (m11b), M13 subway (m13s), and the HUD action-cycle objects (HUD 2/3 check).

Used by tests/m2/nav_probe.py --probe cam_camD_probe:<function>:<poll> (one instance, SINGLE-PC, scripted bots).
Lua test text runs through LUARUN like tests/m2/x6fix_probe.py (results through player 1's money, 0..999, restored);
handles are read in three 3-digit parts. PINE reads: per-view camera arrays of the [warriors-4p 4p] relocation
(active 0x000F0800, render 0x000F0810, follow 0x000F0820, rail 0x000F0830, blend 0x000F0870, +4*view), the locked
camera's 2-entry lock list (+0x20C/+0x210, FUN_001358D0 / FUN_004DB928), the rail target (+0x340, RAILTGT),
the follow camera's secondary target (+0x320 handle, +0x3FC flag; FUN_0011DCF0).
Test-only game changes are named in each function's docstring. Function names are OUR labels (the ELF is stripped);
static addresses, SLUS-21215 v1.03.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "m2"))
import inv_tests as it  # noqa: E402
import x6fix_probe as xf  # noqa: E402

ACTIVE, RENDER, FOLLOW, RAIL, BLEND = 0x000F0800, 0x000F0810, 0x000F0820, 0x000F0830, 0x000F0870
VIEWS = 0x0050B198
LOCKED_VT, RAIL_VT = 0x005362D0, 0x00536DD0
LC_N, LC_LOG = 0x000E7AFC, 0x000E7B00
HUD = 0x00600840
HUD_TGT, HUD_TGT_STRIDE = 0x6B40, 0x590


def _hx(v):
    return hex(v) if v else 0


def _pn(p, h):
    """Handle -> player number 1-4, 0 = none, 9 = other human."""
    if h in (0, 0xFFFFFFFF):
        return 0
    for i in range(4):
        if p.read32(it._gm(p) + 0x228 + 4 * i) == h:
            return i + 1
    return 9


def _optr(p, o):
    """Object pointer -> player number 1-4 (by object), 0 = none, 9 = other."""
    if not o:
        return 0
    for i in range(4):
        if it._player(p, i)[1] == o:
            return i + 1
    return 9


def cams(p):
    out = {"poll": it._poll(p), "views": p.read32(VIEWS), "checkpoint": it._r16(p, it._gm(p) + 0x33A)}
    for i in range(4):
        r, f, rl = p.read32(RENDER + 4 * i), p.read32(FOLLOW + 4 * i), p.read32(RAIL + 4 * i)
        d = {"active": _hx(p.read32(ACTIVE + 4 * i)), "render": _hx(r), "follow": _hx(f), "rail": _hx(rl),
             "blend": _hx(p.read32(BLEND + 4 * i))}
        kind = "none"
        if r:
            vt = p.read32(r)
            kind = ("follow" if r == f else "rail" if r == rl else "locked" if vt == LOCKED_VT else
                    "blend" if r == p.read32(BLEND + 4 * i) else hex(vt))
            if vt == LOCKED_VT:
                d["lock_list_players"] = [_pn(p, p.read32(r + 0x20C)), _pn(p, p.read32(r + 0x210))]
        d["kind"] = kind
        if kind == "blend":
            to = p.read32(r + 0x214)
            d["blend_to"] = _hx(to)
            d["blend_to_kind"] = ("follow" if to == f else "rail" if to == rl else
                                  "locked" if to and p.read32(to) == LOCKED_VT else hex(p.read32(to)) if to else "none")
            d["blend_progress"] = _f32(p.read32(r + 0x220))
            if to and p.read32(to) == LOCKED_VT:
                d["lock_list_players"] = [_pn(p, p.read32(to + 0x20C)), _pn(p, p.read32(to + 0x210))]
        if 0x00100000 <= f < 0x02000000:
            d["follow_secondary_320"] = _hx(p.read32(f + 0x320))
            d["follow_secondary_on_3fc"] = p.read32(f + 0x3FC)
        if 0x00100000 <= rl < 0x02000000:
            d["rail_target_340"] = _optr(p, p.read32(rl + 0x340))
        out[i] = d
    return out


def snap(p):
    n = p.read32(LC_N)
    return {"poll": it._poll(p), "gm": it._gmfields(p), "cams": cams(p), "players": xf._players(p),
            "lc_names_newest_first": [it._cstr(p, LC_LOG + 32 * ((n - 1 - j) & 7), 32) for j in range(min(n, 8))],
            "pads": it._pads(p)}


def _join_pad(p, pad):
    gm = it._gm(p)
    out = {"poll": it._poll(p), "count_before": it._s16(p.read32(gm + 0x224)), "cinematic_410": p.read32(gm + 0x410),
           "gm_14c": p.read32(gm + 0x14C)}
    if out["cinematic_410"] or out["gm_14c"]:
        out["skipped"] = "not quiet"
        return out
    if it._s16(it._r16(p, xf.PAD_OWNER + pad * 0x50 + 0x42)) == -1:
        out["call"] = it._call(p, xf.UPDATE_JOIN, gm, pad)
    out["count_after"] = it._s16(p.read32(gm + 0x224))
    out["pads"] = it._pads(p)
    return out


def join3(p):
    """Player 3 joins (pad 1) through the game's UpdateJoin (what W4P X11 does), only in quiet gameplay."""
    return _join_pad(p, 1)


def join4(p):
    """Player 4 joins (pad 2), later than player 3 (tests the rows' 500 ms / 250 ms ticks)."""
    return _join_pad(p, 2)


def join34(p):
    return xf.join34(p)


def _k(p, base):
    return f"{base}_{it._poll(p)}"


SPLIT = ("function W4P_SPL(v) local a, b = 0, 0 if v == nil then return 999, 999, 999 end "
         "while v >= 1000000 do v = v - 1000000 a = a + 1 end while v >= 1000 do v = v - 1000 b = b + 1 end "
         "return a, b, v end ")


def _handles(p, key, exprs):
    """Read Lua handle values (exprs) in 3-digit parts -> {expr: int or None}."""
    names = []
    src = SPLIT
    for j, e in enumerate(exprs):
        src += f"W4P_H{j}a, W4P_H{j}b, W4P_H{j}c = W4P_SPL({e}) "
        names += [f"W4P_H{j}a", f"W4P_H{j}b", f"W4P_H{j}c"]
    r = xf._q(p, key, src + "W4P_R = 1", tuple(names))
    out = {}
    for j, e in enumerate(exprs):
        a, b, c = (r["values"].get(f"W4P_H{j}{s}") for s in "abc")
        out[e] = None if 999 in (a, b, c) or not all(isinstance(x, int) for x in (a, b, c)) else a * 1000000 + b * 1000 + c
    return out


def _ptrs(p, hs):
    return {e: (_hx(it._resolve(p, h)) if h else None) for e, h in hs.items()}


def _run(p, key, src, names=("W4P_R",)):
    return xf._q(p, key, src, names)


# ---------------------------------------------------------------- M3 cp5 (level87_chap5_club.lua, row m3t)
def m3_mark(p):
    """Rows present: helpers (W4P_O.h), m3t marker, MoveToNextBox wrapped (W4P_O.d3 ~= ch5.MoveToNextBox) -> 111."""
    return xf._markers(p, _k(p, "m3mk"), ["W4P_O and W4P_O.h", "W4P_O and W4P_O.d3m",
                                           "W4P_O and W4P_O.d3 and W4P_O.d3 ~= ch5.MoveToNextBox"])


def m3_prep(p):
    """Real call of ch5.DestractTutorial02 (09225 main_31): split off, Warriors teleported to fWarpDest, Tutorial02Cam
    created and made active on view 0; schedules DestractTutorial03 (pads of players 1-2 locked)."""
    r = _run(p, _k(p, "m3prep"), "W4P_PC(ch5.DestractTutorial02) W4P_R = 100 W4P_R2 = (Tutorial02Cam and 1 or 0)",
             ("W4P_R", "W4P_R2"))
    r["snap"] = snap(p)
    return r


M3_VIEWS = ("W4P_V = 0 for v = 0, 3 do local c = CameraGetActive(v) local d = 0 if c == Tutorial02Cam then d = 1 end "
            "if W4P_D3C and c == W4P_D3C[2] then d = 2 end if W4P_D3C and c == W4P_D3C[3] then d = 3 end "
            "W4P_V = W4P_V * 10 + d end W4P_R = W4P_V - 1000 * W4P_SPL3(W4P_V) W4P_R2 = W4P_SPL3(W4P_V) ")
SPL3 = "function W4P_SPL3(v) local a = 0 while v >= 1000 do v = v - 1000 a = a + 1 end return a end "


def _m3_state(p, key):
    """R2*1000 + R = one digit per view 0..3 (CameraGetActive(v)): 1 = Tutorial02Cam (players 1-2's object),
    2/3 = W4P_D3C[2]/[3] (the copies of players 3/4), 0 = other (follow etc.); plus handles -> object pointers."""
    r = _run(p, key, SPL3 + M3_VIEWS, ("W4P_R", "W4P_R2"))
    v = r["values"]
    if isinstance(v.get("W4P_R"), int) and isinstance(v.get("W4P_R2"), int):
        r["view_digits"] = f"{v['W4P_R2'] * 1000 + v['W4P_R']:04d}"
    hs = _handles(p, key + "_h", ["Tutorial02Cam", "W4P_D3C[2]", "W4P_D3C[3]", "MainCam"])
    r["handles"] = {e: _hx(h) for e, h in hs.items()}
    r["objects"] = _ptrs(p, hs)
    r["snap"] = snap(p)
    return r


def m3_state(p):
    return _m3_state(p, _k(p, "m3st"))


def m3_orig(p):
    """'Before' evidence: the ORIGINAL ch5.MoveToNextBox (W4P_O.d3) only."""
    r = _run(p, _k(p, "m3orig"), "W4P_PC(W4P_O.d3) W4P_R = 100")
    r["state"] = m3_state(p)
    return r


def m3_add(p):
    """'After' evidence: exactly what the wrapper adds after the original (W4P_D3ON = 1, W4P_D3G(), tick start)."""
    r = _run(p, _k(p, "m3add"), "W4P_D3ON = 1 W4P_D3G() if W4P_D3K == nil then W4P_D3K = 1 ScheduleFunc(\"W4P_D3T\", 500) end W4P_R = 100")
    r["state"] = m3_state(p)
    return r


def m3_wrap(p):
    """Integrated path: the WRAPPED ch5.MoveToNextBox (original + players 3-4 copies + tick)."""
    r = _run(p, _k(p, "m3wrap"), "W4P_PC(ch5.MoveToNextBox) W4P_R = 100 + (W4P_D3ON or 0)")
    r["state"] = m3_state(p)
    return r


def m3_back(p):
    """Real call of the wrapped ch5.AfterS03WalksBack (09225 main_42): split on, MainCam for players 1-2 (original),
    then W4P_D3B(0): players 3-4 back to their follow camera, lock released."""
    r = _run(p, _k(p, "m3back"), "W4P_PC(ch5.AfterS03WalksBack) W4P_R = 100 + (W4P_D3ON or 0)")
    r["state"] = m3_state(p)
    return r


def m3_moveback(p):
    """Real flow after the next box: ch5.DistractMoveBack(nil) (09225 main_39, the objective callback) -> 500 ms ->
    the wrapped DistractMoveBackTutorial (split off, Dest4Cam on view 0; then W4P_D3B: players 3-4 follow camera,
    hidden) -> Stealth03 walks back -> the game calls the wrapped AfterS03WalksBack (split on, MainCam)."""
    r = _run(p, _k(p, "m3mb"), "W4P_PC(ch5.DistractMoveBack) W4P_R = 100 + (W4P_D3ON or 0)")
    r["snap"] = snap(p)
    return r


# ---------------------------------------------------------------- M10 cp5 (level93_chapter5.lua, row m10s)
def m10_mark(p):
    return xf._markers(p, _k(p, "m10mk"), ["W4P_O and W4P_O.h", "W4P_O and W4P_O.d10m",
                                            "W4P_O and W4P_O.d10 and W4P_O.d10.sc ~= SetupLCChase"])


def m10_keep(p):
    """TEST ONLY: keep the stealth chase alive while bots stand still: C5.maxDistance = 9999,
    MAX_TIME_OVER_MAX_DISTANCE = 1e9 (no 'lost him' fail). Safe to call before SetupLCChase (C5 exists from the
    chunk's main)."""
    return _run(p, _k(p, "m10keep"), "if C5 then C5.maxDistance = 9999 end MAX_TIME_OVER_MAX_DISTANCE = 1000000000 "
                                     "W4P_R = 100 + (C5 and 10 or 0) + (W4P_D10ON or 0)")


def m10_freeze(p):
    """TEST ONLY (after SetupLCChase): the LC stops at the next flag it reaches (look/move chain fLC1..fLC4 removed,
    scheduled LCMove2..5 flushed), LC sight and damage fails off, so LC_FLAG_DESTINATION stays where it is and the
    remaining boxes stay live. R = 100 + 10*tick running + chase on; R2 = LC_FLAG_DESTINATION."""
    r = _run(p, _k(p, "m10frz"), "SetMsgHandler(fLC1, 8, nil) SetMsgHandler(fLC2, 8, nil) SetMsgHandler(fLC3, 8, nil) "
                                 "SetMsgHandler(fLC4, 8, nil) FlushScheduledFuncs(\"LCMove2\") FlushScheduledFuncs(\"LCMove3\") "
                                 "FlushScheduledFuncs(\"LCMove4\") FlushScheduledFuncs(\"LCMove5\") "
                                 "SetMsgHandler(hLC, 11, nil) SetMsgHandler(hLC, 1, nil) "
                                 "W4P_R = 100 + 10 * (W4P_D10K or 0) + (W4P_D10ON or 0) W4P_R2 = LC_FLAG_DESTINATION",
             ("W4P_R", "W4P_R2"))
    r["snap"] = snap(p)
    return r


M10_VIEWS = (SPL3 + "W4P_V = 0 for v = 0, 3 do local c = CameraGetActive(v) local d = 0 "
             "local L = {SneakCam1, SneakCam2, SneakCam3, SneakCam4} for n = 1, 4 do if L[n] and c == L[n] then d = n end end "
             "for i = 2, 3 do for n = 1, 4 do if c == W4P_D10S[\"c\" .. i .. n] then d = 4 + (i - 2) * 4 + n end end end "
             "if d > 9 then d = 9 end W4P_V = W4P_V * 10 + d end W4P_R = W4P_V - 1000 * W4P_SPL3(W4P_V) W4P_R2 = W4P_SPL3(W4P_V) "
             "W4P_R3 = (W4P_D10S[2] or 0) * 100 + (W4P_D10S[3] or 0) * 10 + (W4P_D10ON or 0) ")


def _m10_state(p, key):
    """view_digits: per view 0..3: 1-4 = shared SneakCam1-4 (players 1-2's objects), 5-8 = player 3's copy 1-4,
    9 = player 4's copy, 0 = other; R3 = (box of player 3's copy)*100 + (box of player 4's)*10 + tick on."""
    r = _run(p, key, M10_VIEWS, ("W4P_R", "W4P_R2", "W4P_R3"))
    v = r["values"]
    if isinstance(v.get("W4P_R"), int) and isinstance(v.get("W4P_R2"), int):
        r["view_digits"] = f"{v['W4P_R2'] * 1000 + v['W4P_R']:04d}"
    r["snap"] = snap(p)
    return r


def m10_state(p):
    r = _m10_state(p, _k(p, "m10st"))
    hs = _handles(p, _k(p, "m10h"), ['W4P_D10S["c21"]', 'W4P_D10S["c22"]', 'W4P_D10S["c23"]', 'W4P_D10S["c24"]',
                                     'W4P_D10S["c31"]', 'W4P_D10S["c32"]'])
    objs = _ptrs(p, hs)
    r["copies"] = objs
    shown = {}
    c = r["snap"]["cams"]
    for i in range(4):
        cam = c[i]["blend_to"] if c[i]["kind"] == "blend" else c[i]["render"]
        shown[i] = next((e for e, o in objs.items() if o and o == cam), c[i].get("blend_to_kind") or c[i]["kind"])
    r["shown"] = shown
    return r


def m10_stub_in(p):
    """TEST ONLY: W4P_D10IB (the row's IsInsideBox) answers 'inside vLCTrigger[n]' for player 3, n = the first box
    whose enter is still live (LC_FLAG_DESTINATION, R = 100 + n); real answer for everybody else. The row's tick then
    does what C5.LCTriggerNEnter does, with player 3's own copy."""
    r = _run(p, _k(p, "m10in"), "W4P_D10TB = LC_FLAG_DESTINATION if W4P_D10TB > 4 then W4P_D10TB = 4 end "
                                "W4P_D10OB = W4P_D10OB or IsInsideBox W4P_D10IB = function(b, h) "
                                "if b == vLCTrigger[W4P_D10TB] and h == HuGetPlayer(2) then return 1 end return W4P_D10OB(b, h) end "
                                "W4P_R = 100 + W4P_D10TB")
    r["before"] = cams(p)
    return r


def m10_stub_out(p):
    """TEST ONLY: real IsInsideBox again -> player 3 'leaves' box 1 -> MainCam (his follow camera) back."""
    r = _run(p, _k(p, "m10out"), "if W4P_D10OB then W4P_D10IB = W4P_D10OB end W4P_R = 100")
    r["before"] = cams(p)
    return r


def m10_boxpos(p):
    """Box positions through GetPosition(vLCTrigger[n]) (object position; (v + 2000) * 10 through money), and whether
    players 1 and 3 are inside each box (IsInsideBox): R digits."""
    names = []
    src = "W4P_V = {} for n = 1, 4 do local q = call(GetPosition, {vLCTrigger[n]; n = 1}, \"x\") if q then W4P_V[n * 3 - 2] = (q.x + 2000) * 10 W4P_V[n * 3 - 1] = (q.y + 2000) * 10 W4P_V[n * 3] = (q.z + 2000) * 10 end end "
    src += "W4P_R = 0 for n = 1, 4 do W4P_R = W4P_R * 2 + (IsInsideBox(vLCTrigger[n], player) and 1 or 0) end "
    src += "W4P_R2 = 0 for n = 1, 4 do W4P_R2 = W4P_R2 * 2 + (IsInsideBox(vLCTrigger[n], HuGetPlayer(2)) and 1 or 0) end "
    for j in range(1, 13):
        names.append(f"W4P_V[{j}]")
    src += "W4P_R3 = LC_FLAG_DESTINATION if W4P_R3 > 4 then W4P_R3 = 4 end "
    r = xf._q(p, _k(p, "m10pos"), src, tuple(["W4P_R", "W4P_R2", "W4P_R3"] + names))
    pos = {}
    for n in range(1, 5):
        v = [r["values"].get(f"W4P_V[{3 * n - 3 + k}]") for k in (1, 2, 3)]
        pos[n] = [round(x / 10 - 2000, 1) if isinstance(x, int) and x != 998 else x for x in v]
    r["box_pos"] = pos
    r["players"] = xf._players(p)
    return r


def _tp_p3(p, key, x, y, z):
    return _run(p, key, f"Teleport(HuGetPlayer(2), {{{x}, {y}, {z}}}, -1) W4P_R = 100")


def m10_walk(p):
    """Real walk-in check (only if box 1's position is known and within 60 units of player 1): player 3 is put at the
    box position at player 1's height (or 1 unit above the box floor, whichever is higher); the row's tick must see
    him with the REAL IsInsideBox (type-2 box) and give him his copy of SneakCam1."""
    bp = m10_boxpos(p)
    n = bp["values"].get("W4P_R3")
    n = n if isinstance(n, int) and 1 <= n <= 4 else 4
    q = bp["box_pos"].get(n)
    _, o1 = it._player(p, 0)
    x1, y1, z1 = it._pos(p, o1)
    if not q or not all(isinstance(v, float) for v in q):
        return {"skipped": "box position unknown", "boxpos": bp}
    d = ((q[0] - x1) ** 2 + (q[1] - y1) ** 2) ** 0.5
    if d > 60:
        return {"skipped": f"box {n} {d:.1f} units from player 1", "boxpos": bp}
    z = max(z1, q[2] + 1.0)
    r = _tp_p3(p, _k(p, "m10walk"), round(q[0], 2), round(q[1], 2), round(z, 2))
    r.update(boxpos=bp, box=n, dist_p1=round(d, 1), target=[q[0], q[1], z])
    return r


def m10_walk_back(p):
    """Player 3 back next to player 1 (3 units, same height) -> leaves box 1 -> MainCam back."""
    _, o1 = it._player(p, 0)
    x1, y1, z1 = it._pos(p, o1)
    r = _tp_p3(p, _k(p, "m10wb"), round(x1 + 3, 2), round(y1, 2), round(z1, 2))
    r["players"] = xf._players(p)
    return r


def m10_inside(p):
    """R = IsInsideBox(vLCTrigger[1..4], player 3) as 4 decimal digits 1/0 (real geometric test, type-2 boxes)."""
    r = _run(p, _k(p, "m10ins"), "W4P_R = 0 for n = 1, 4 do W4P_R = W4P_R * 10 + (IsInsideBox(vLCTrigger[n], HuGetPlayer(2)) and 1 or 0) end")
    r["players"] = xf._players(p)
    return r


def m10_cleanup(p):
    """Real call of the wrapped Cleanup (09379 main_40) while player 3 shows his copy (stub in first): players 3-4
    MainCam back, copies deleted, then the original cleanup (end of the test: the chapter's handlers are gone)."""
    r = _run(p, _k(p, "m10cu"), "W4P_PC(Cleanup) W4P_R = 100 + (W4P_D10ON or 0) W4P_R2 = 0 "
                                "for i = 2, 3 do for n = 1, 4 do if W4P_D10S[\"c\" .. i .. n] then W4P_R2 = W4P_R2 + 1 end end end",
             ("W4P_R", "W4P_R2"))
    r["snap"] = snap(p)
    return r


# ---------------------------------------------------------------- M11 cp6 (level31_Birdie.lua, row m11b)
def m11_mark(p):
    return xf._markers(p, _k(p, "m11mk"), ["W4P_O and W4P_O.h", "W4P_O and W4P_O.d11m",
                                            "W4P_O and W4P_O.d11 and W4P_O.d11 ~= P6.NewWarrior"])


_M11 = {"calls": 0}


def m11_call_any(p):
    """Like m11_call, but also with fewer than 4 players (last resort / 2-player regression)."""
    _M11["any"] = True
    return m11_call(p)


def m11_call(p):
    """Real call of the wrapped P6.NewWarrior(Warriors.Cody) (a chain Warrior death handler, 07911 main_9; Cody is not
    a player here): original -> CamSetSecondary(Birdie, 0, 1) for player 2, KillCam on view 0, next Warrior added;
    the row repeats the CamSetSecondary for players 3-4 (index 2/3). Follow secondary (+0x320) before/after."""
    n = it._s16(p.read32(it._gm(p) + 0x224))
    if _M11["calls"] >= 2 or (n < 4 and not _M11.get("any")):
        return {"skipped": f"players {n}, calls so far {_M11['calls']}", "poll": it._poll(p)}
    _M11["calls"] += 1
    before = cams(p)
    hs = _handles(p, _k(p, "m11h"), ["Birdie.Birdie", "Warriors.Cody", "KilledWarriors[2]"])
    r = _run(p, _k(p, "m11call"), "W4P_PC(P6.NewWarrior, Warriors.Cody) W4P_R = 100 + (killCount or 0)")
    r.update(before=before, after=cams(p), handles={e: _hx(h) for e, h in hs.items()}, players=xf._players(p))
    return r


def m11_orig_note(p):
    return {"poll": it._poll(p), "cams": cams(p)}


# ---------------------------------------------------------------- M5 cp1 (level2.lua, row m5i)
def m5_mark(p):
    return xf._markers(p, _k(p, "m5mk"), ["W4P_O and W4P_O.h", "W4P_O and W4P_O.d5m",
                                           "W4P_O and W4P_O.d5 and c1Intro and W4P_O.d5.kl ~= c1Intro.Kill"])


def _m5_stub(p, key, k):
    """TEST ONLY: W4P_D5IB answers 'inside box k' (1-2 vbIntroCam, 3-4 vbLeadRail, 5 vbSideRail) for player 3."""
    t = ["vbIntroCam[1]", "vbIntroCam[2]", "vbLeadRail[1]", "vbLeadRail[2]", "vbSideRail"][k - 1]
    r = _run(p, key, f"W4P_D5OB = W4P_D5OB or IsInsideBox W4P_D5IB = function(b, h) if b == {t} and h == HuGetPlayer(2) "
                     "then return 1 end return W4P_D5OB(b, h) end W4P_R = 100 + (W4P_D5ON or 0)")
    r["before"] = cams(p)
    return r


def m5_in_cam(p):
    return _m5_stub(p, _k(p, "m5ic"), 1)


def m5_in_lead(p):
    return _m5_stub(p, _k(p, "m5il"), 3)


def m5_in_side(p):
    return _m5_stub(p, _k(p, "m5is"), 5)


def m5_unstub(p):
    return _run(p, _k(p, "m5un"), "if W4P_D5OB then W4P_D5IB = W4P_D5OB end W4P_R = 100")


M5_STATE = ("local s = W4P_D5S[2] W4P_R = 0 W4P_R2 = 0 W4P_R3 = 0 if s then "
            "W4P_R = (s.ic or 0) * 100 + (s.tr or 0) * 10 + (s.cb or 0) W4P_R2 = (s.on or 0) * 100 + (s.lk and 10 or 0) + (s.r and 1 or 0) end "
            "local c = CameraGetActive(2) if s and s.lk and c == s.lk then W4P_R3 = 1 elseif s and s.r and c == s.r then W4P_R3 = 2 "
            "elseif c1Intro and c == c1Intro.StartLock then W4P_R3 = 3 end "
            "W4P_R4 = 0 if c1Intro and CameraGetActive(0) == c1Intro.StartLock then W4P_R4 = 1 end ")


def m5_state(p):
    """Player 3's row state: R = ICamOn*100 + TrailOn*10 + CurBox, R2 = shown*100 + copy*10 + rail; R3 = what view 3
    (index 2) shows: 1 = his StartLock copy, 2 = his rail, 3 = players 1-2's StartLock object, 0 = other;
    R4 = 1 if view 1 (index 0) shows c1Intro.StartLock."""
    r = _run(p, _k(p, "m5st"), M5_STATE, ("W4P_R", "W4P_R2", "W4P_R3", "W4P_R4"))
    r["snap"] = snap(p)
    return r


def m5_kill(p):
    """Real call of the wrapped c1Intro.Kill (07708 main_94; normally from P1.EnterStreets): players 3-4 MainCam back,
    StartLock copies deleted, then the original (boxes off, StartLock deleted, c1Intro = nil)."""
    r = _run(p, _k(p, "m5kill"), "W4P_PC(c1Intro.Kill) W4P_R = 100 + (c1Intro and 1 or 0) W4P_R2 = 0 "
                                 "if W4P_D5S[2] then W4P_R2 = (W4P_D5S[2].on or 0) * 10 + (W4P_D5S[2].lk and 1 or 0) end",
             ("W4P_R", "W4P_R2"))
    r["snap"] = snap(p)
    return r


def m5_boxinfo(p):
    """Whether players 1 and 3 are inside the five intro boxes (real IsInsideBox): two 5-digit binary numbers."""
    src = ("local t = {vbIntroCam[1], vbIntroCam[2], vbLeadRail[1], vbLeadRail[2], vbSideRail} W4P_R = 0 W4P_R2 = 0 "
           "for k = 1, 5 do W4P_R = W4P_R * 2 + (IsInsideBox(t[k], player) and 1 or 0) "
           "W4P_R2 = W4P_R2 * 2 + (IsInsideBox(t[k], HuGetPlayer(2)) and 1 or 0) end")
    r = _run(p, _k(p, "m5bx"), src, ("W4P_R", "W4P_R2"))
    r["players"] = xf._players(p)
    return r


# ---------------------------------------------------------------- M13 (level9.lua, row m13s)
def m13_mark(p):
    return xf._markers(p, _k(p, "m13mk"), ["W4P_O and W4P_O.h", "W4P_O and W4P_O.d13m", "W4P_D13K"])


def _m13_stub(p, key, expr):
    r = _run(p, key, f"W4P_D13OB = W4P_D13OB or IsInsideBox W4P_D13IB = function(b, h) if b == {expr} and h == HuGetPlayer(2) "
                     "then return 1 end return W4P_D13OB(b, h) end W4P_R = 100 + (W4P_D13K or 0)")
    r["before"] = cams(p)
    return r


def m13_in_train(p):
    """TEST ONLY: player 3 'inside vbInTrain[1]' -> the tick gives him the subway rail on rail index 2."""
    return _m13_stub(p, _k(p, "m13it"), "vbInTrain[1]")


def m13_in_main(p):
    """TEST ONLY: player 3 'inside vbMainCam[1]' (left the train) -> MainCam + follow pos/zoom on index 2."""
    return _m13_stub(p, _k(p, "m13im"), "vbMainCam[1]")


def m13_unstub(p):
    return _run(p, _k(p, "m13un"), "if W4P_D13OB then W4P_D13IB = W4P_D13OB end W4P_R = 100")


def m13_state(p):
    r = _run(p, _k(p, "m13st"), "local s = W4P_D13S[2] W4P_R = 0 if s then W4P_R = (s.m or 0) * 100 + (s[1] and 10 or 0) + (s[4] and 1 or 0) end "
                                "W4P_R2 = (bMainCam or 0) * 10 + (bMainCam2 or 0)", ("W4P_R", "W4P_R2"))
    r["snap"] = snap(p)
    f2 = p.read32(FOLLOW + 8)
    if 0x00100000 <= f2 < 0x02000000:
        r["follow2_words_240_270"] = [hex(p.read32(f2 + o)) for o in (0x240, 0x244, 0x248, 0x270, 0x274, 0x278)]
    f0 = p.read32(FOLLOW)
    if 0x00100000 <= f0 < 0x02000000:
        r["follow0_words_240_270"] = [hex(p.read32(f0 + o)) for o in (0x240, 0x244, 0x248, 0x270, 0x274, 0x278)]
    return r


# ---------------------------------------------------------------- HUD action-cycle objects (prompt check)
def hud_objs(p):
    """Read-only: the HUD's target/pickup objects HUD+0x6B40+i*0x590 (FUN_001B3DD0 / FUN_0019F270 work on them).
    Objects 0 and 1 are built by FUN_001AD588 (loop bound 2 at 0x001ADB78); 'object' 2/3 would be HUD+0x7660 /
    HUD+0x7BF0. Shows the first words and the anim fields +0x440..+0x45C each FUN_0019F270 call writes."""
    out = {"poll": it._poll(p)}
    for i in range(4):
        a = HUD + HUD_TGT + i * HUD_TGT_STRIDE
        out[i] = {"addr": hex(a), "first": [hex(p.read32(a + 4 * k)) for k in range(4)],
                  "anim_440_45c": [hex(p.read32(a + 0x440 + 4 * k)) for k in range(8)]}
    out["code_0x001ADB78"] = hex(p.read32(0x001ADB78))
    return out


def hud_on1(p):
    """Positive control: HUDTurnOnActionCycleAnim(3, 0.15, 2, 73, 73, 1) = the M16 fence hint on HUD 1 (player 2)."""
    r = _run(p, _k(p, "hud1"), "HUDTurnOnActionCycleAnim(3, 0.15, 2, 73, 73, 1) W4P_R = 100")
    r["objs"] = hud_objs(p)
    return r


def hud_off1(p):
    r = _run(p, _k(p, "hud1off"), "HUDTurnOffActionCycleAnim(1) W4P_R = 100")
    r["objs"] = hud_objs(p)
    return r


def hud_on2(p):
    """DESTRUCTIVE TEST (last in a run): the same call for HUD 2 (player 3). FUN_001B3DD0 -> FUN_0019F270 on
    HUD+0x7660, which is not a target object: shows what it overwrites (the run's emulog shows any TLB miss)."""
    before = hud_objs(p)
    r = _run(p, _k(p, "hud2"), "HUDTurnOnActionCycleAnim(3, 0.15, 2, 73, 73, 2) W4P_R = 100")
    r.update(before=before, after=hud_objs(p))
    return r


# ---------------------------------------------------------------- blend cameras on views 1-4 (finding from camD_m10b)
def _f32(v):
    import struct
    return round(struct.unpack("<f", struct.pack("<I", v))[0], 3)


def blend_read(p):
    """Per view: active/render and the view's blend camera (array 0x000F0870): from +0x210, to +0x214, duration +0x218,
    elapsed +0x21C, progress +0x220 (FUN_00143078 / update FUN_00143590, which hands the view to 'to' once
    elapsed >= duration)."""
    out = {"poll": it._poll(p)}
    for i in range(4):
        b = p.read32(BLEND + 4 * i)
        d = {"active": _hx(p.read32(ACTIVE + 4 * i)), "render": _hx(p.read32(RENDER + 4 * i)),
             "follow": _hx(p.read32(FOLLOW + 4 * i)), "blend": _hx(b)}
        if 0x00100000 <= b < 0x02000000:
            d.update(frm=_hx(p.read32(b + 0x210)), to=_hx(p.read32(b + 0x214)), dur=_f32(p.read32(b + 0x218)),
                     elapsed=_f32(p.read32(b + 0x21C)), progress=_f32(p.read32(b + 0x220)))
        out[i] = d
    return out


def _blend_go(p, key, who):
    r = _run(p, key, f"CameraMakeActive(MainCam, 0.85, nil, {who}, {who}) W4P_R = 100")
    r["blend"] = blend_read(p)
    return r


def blend_go1(p):
    """Control on view 2 (index 1): CameraMakeActive(MainCam, 0.85, nil, player2, player2) (what C5.LCTriggerNExit does
    for player 2): a blend from his follow camera to his follow camera."""
    return _blend_go(p, _k(p, "bg1"), "player2")


def blend_go2(p):
    """The same for player 3 (view 3, index 2)."""
    return _blend_go(p, _k(p, "bg2"), "HuGetPlayer(2)")


def m11_god(p):
    """TEST ONLY: god mode for the players present (keeps idle bots alive in the Birdie fight; IntroOver turns player 1's
    god mode off again at the start of the fight)."""
    return _run(p, _k(p, "m11god"), "for i = 0, 3 do local h = HuGetPlayer(i) if h and HuIsAPlayer(h) then HuSetGodMode(h, true) end end W4P_R = 100")


# M10 box corners/sizes from AddVolumeBox (09321:1656-1663; all RotateVolumeBox(-1, 0, 0, -1))
M10_BOX = {1: (427.1, -103.7, 6, 6), 2: (444.2, -72.9, 8.5, 9.4), 3: (405.6, -63.8, 10, 11.6), 4: (365.8, -68.6, 9, 8)}


def m10_walk2(p):
    """Real walk-in (no stub): player 3 is put into vLCTrigger[1] at player 1's height; the AddVolumeBox vector may be
    a corner with the box on either side (180-degree rotation), so two candidate centres are tried, each checked with the
    real IsInsideBox (R). Only within 60 units of player 1."""
    import time
    _, o1 = it._player(p, 0)
    x1, y1, z1 = it._pos(p, o1)
    bx, by, w, d = M10_BOX[1]
    out = {"p1": [x1, y1, z1], "tries": []}
    for cx, cy in ((bx + w / 2, by + d / 2), (bx - w / 2, by - d / 2)):
        dist = ((cx - x1) ** 2 + (cy - y1) ** 2) ** 0.5
        if dist > 60:
            out["tries"].append({"skipped": round(dist, 1)})
            continue
        tp = _tp_p3(p, _k(p, f"m10w2_{cx:.0f}"), round(cx, 2), round(cy, 2), round(z1, 2))
        time.sleep(1.0)
        ins = m10_inside(p)
        out["tries"].append({"target": [cx, cy, z1], "tp": tp.get("status"), "inside_1234": ins["values"].get("W4P_R"),
                             "players": ins.get("players")})
        if isinstance(ins["values"].get("W4P_R"), int) and ins["values"]["W4P_R"] >= 1000:
            break
    return out


# ---------------------------------------------------------------- blend override control (view 2 = player 2, view 3 = player 3)
def _ctl(p, key, who, idx):
    """TEST ONLY: a locked camera 6 units above the player (created once per player), made active WITHOUT blend for
    him; R = 1 if CameraGetActive(view) == that camera right away; the next blend_read shows whether it stayed."""
    src = (f"local h = {who} if W4P_CTL == nil then W4P_CTL = {{}} end if W4P_CTL[{idx}] == nil then "
           f"local q = call(GetPosition, {{h; n = 1}}, \"x\") or {{x = 407, y = -137, z = 3}} W4P_CTL[{idx}] = CameraCreateLocked(\"W4PCTL\", {{q.x + 4, q.y + 4, q.z + 6}}, 65, 0, -30, 0, 0.1, 75) end "
           f"CameraMakeActive(W4P_CTL[{idx}], 0, nil, h, h) W4P_R = (CameraGetActive({idx}) == W4P_CTL[{idx}]) and 1 or 0")
    r = _run(p, key, src)
    r["blend"] = blend_read(p)
    return r


def ctl1(p):
    return _ctl(p, _k(p, "ctl1"), "player2", 1)


def ctl2(p):
    return _ctl(p, _k(p, "ctl2"), "HuGetPlayer(2)", 2)


def ctl_read(p):
    """R = digit per view 1..3: 1 if CameraGetActive(view) is that view's W4PCTL camera."""
    r = _run(p, _k(p, "ctlr"), "W4P_R = 0 for v = 1, 3 do W4P_R = W4P_R * 10 + ((W4P_CTL and W4P_CTL[v] and CameraGetActive(v) == W4P_CTL[v]) and 1 or 0) end")
    r["blend"] = blend_read(p)
    return r


def main0_1(p):
    """Back to the follow camera, no blend, for players 2 and 3."""
    r = _run(p, _k(p, "mc01"), "CameraMakeActive(MainCam, 0, nil, player2, player2) CameraMakeActive(MainCam, 0, nil, HuGetPlayer(2), HuGetPlayer(2)) W4P_R = 100")
    r["blend"] = blend_read(p)
    return r


# ---------------------------------------------------------------- M10 real chapter end
def m10_inside3(p):
    """R = 100 + inside(vLCTrigger[1..2], player 3) as 2 digits (no money cap issue); R2 = row state of player 3."""
    r = _run(p, _k(p, "m10i3"), "W4P_R = 100 + 10 * (IsInsideBox(vLCTrigger[1], HuGetPlayer(2)) and 1 or 0) + (IsInsideBox(vLCTrigger[2], HuGetPlayer(2)) and 1 or 0) "
                                "W4P_R2 = (W4P_D10S[2] or 0) * 10 + (W4P_D10S[\"i2\"] or 0)", ("W4P_R", "W4P_R2"))
    r["snap"] = snap(p)
    return r


def m10_tp_box1(p):
    """Real walk-in: player 3 to the inside point of vLCTrigger[1] found in run camD_m10c (430.1, -100.7) at player 1's
    height (the AddVolumeBox vector is the box's lower corner)."""
    _, o1 = it._player(p, 0)
    x1, y1, z1 = it._pos(p, o1)
    r = _tp_p3(p, _k(p, "m10tp1"), 430.1, -100.7, round(z1, 2))
    r["p1"] = [x1, y1, z1]
    return r


def m10_end(p):
    """Real end of the chapter: HideoutGateTriggered(vHideoutGateTrigger, player) (09379 main_33; normally the gate box):
    flushes the scheduled functions, fade, NextMission after 1 s -> Cleanup (wrapped) -> chapter 6."""
    r = _run(p, _k(p, "m10end"), "W4P_PC(HideoutGateTriggered, vHideoutGateTrigger, player) W4P_R = 100 + (W4P_D10S[2] or 0)")
    r["snap"] = snap(p)
    return r


def m11_orig_call(p):
    """'Before' evidence: the ORIGINAL P6.NewWarrior (W4P_O.d11) for Cody with 4 players: only player 2's camera gets
    Birdie as secondary target."""
    n = it._s16(p.read32(it._gm(p) + 0x224))
    if n < 4:
        return {"skipped": f"players {n}", "poll": it._poll(p)}
    before = cams(p)
    r = _run(p, _k(p, "m11orig"), "W4P_PC(W4P_O.d11, Warriors.Cody) W4P_R = 100 + (killCount or 0)")
    r.update(before=before, after=cams(p))
    return r

"""X6 fix rows (docs/research/m6_x6_fixes.md): runtime checks of the LUACH rows for M16, M18, M11 and tagging (M3, M6, M13).

Used by nav_probe.py --probe x6fix_probe:<function>:<poll> after a level jump (CallAt SetCheckPoint + MenuLoadLevel).
SINGLE-PC, one instance, scripted bots, test only:
- Lua test text is written over PINE into 0x000EF000-0x000EFFFF (free low RAM, test only, not in the pnach) and run
  with LUARUN (0x000E79A0, group [warriors-4p missions]) through the test-call mailbox (inv_tests._call);
- results come back through player 1's money (InvSetMoney(v, 1), read from the inventory; restored afterwards),
  as in x4x6_probe.py; money is capped at 999, so every result is a number 0..999;
- the rows themselves come from the pnach (no PINE writes to the LUACH table); W4P_O.* = originals and row markers
  that the rows store in the level's Lua state.
Function names are OUR labels (the ELF is stripped). Static addresses, build SLUS-21215 v1.03.
"""
import inv_tests as it

LUARUN = 0x000E79A0
BUF, BUF_SIZE = 0x000EF000, 0x1000
LC_RUNS, LC_N, LC_LOG, LC_TAB = 0x000E7AF8, 0x000E7AFC, 0x000E7B00, 0x000E7F00
UPDATE_JOIN = 0x0041A460        # UpdateJoin(GameMgr, pad): the game's drop-in join (what W4P X11 calls in sessions)
PAD_OWNER = 0x005DD810          # s16 owner at +pad*0x50+0x42
FOLLOW_CAMS, RENDER_CAMS, RAIL_CAMS = 0x000F0820, 0x000F0810, 0x000F0830   # relocated per-view arrays (4p group)
_DONE = {}

# Test prelude: player number (1-4) of a handle, 9 = not a player
PN = ("function W4P_PN(h) for i = 0, 3 do if HuGetPlayer(i) == h then return i + 1 end end return 9 end "
      "function W4P_PC(f, a, b) return call(f, {a, b; n = 2}, \"x\") end ")   # protected test call


def _money(p, slot):
    return it._s32(p.read32(it._count_addr(it._gm(p), slot, 2)))


def _spray(p, slot):
    return it._s32(p.read32(it._count_addr(it._gm(p), slot, 3)))


def _run(p, src):
    data = src.encode("latin-1") + b"\0"
    assert len(data) <= BUF_SIZE, len(data)
    data += b"\0" * (-len(data) % 4)
    p.batch_write32([(BUF + i, int.from_bytes(data[i:i + 4], "little")) for i in range(0, len(data), 4)])
    return it._call(p, LUARUN, BUF, 0)


def _q(p, key, src, names=("W4P_R",)):
    """Run src once (per nav_probe process), then read the given Lua globals through player 1's money."""
    if key in _DONE:
        return dict(_DONE[key], repeated=True)
    m0 = _money(p, 0)
    r = _run(p, "W4P_R = nil W4P_R2 = nil " + PN + src)
    vals = {}
    for n in names:
        r2 = _run(p, f"InvSetMoney({n} or 998, 1)")
        vals[n] = _money(p, 0) if r2["v0"] == 0 else ("lua status", r2["v0"])
    _run(p, f"InvSetMoney({m0}, 1)")
    res = {"poll": it._poll(p), "status": r["v0"], "done": r["done"], "values": vals, "src": src}
    _DONE[key] = res
    return res


def _cams(p):
    out = {}
    for i in range(4):
        f = p.read32(FOLLOW_CAMS + 4 * i)
        out[i] = {"render": hex(p.read32(RENDER_CAMS + 4 * i)), "follow": hex(f), "rail": hex(p.read32(RAIL_CAMS + 4 * i)),
                  "follow_240": [hex(p.read32(f + 0x240 + 4 * k)) for k in range(4)] if 0x00100000 <= f < 0x02000000 else None,
                  "follow_270": [hex(p.read32(f + 0x270 + 4 * k)) for k in range(4)] if 0x00100000 <= f < 0x02000000 else None}
    return out


def _players(p):
    gm = it._gm(p)
    out = {"count": it._s16(p.read32(gm + 0x224))}
    for i in range(4):
        h, o = it._player(p, i)
        out[i + 1] = {"handle": hex(h), "obj": hex(o), "hud_slot": it._s32(p.read32(o + 0x380)) if o else None,
                      "pidx": (p.read32(o + 0x1B0) & 0xFF) if o else None,
                      "pos": it._pos(p, o) if o else None}
    return out


def _has_p3(p):
    return it._s16(p.read32(it._gm(p) + 0x224)) >= 3


# ---------------------------------------------------------------- general
def state(p):
    n = p.read32(LC_N)
    names = {k: it._cstr(p, LC_LOG + 32 * k, 32) for k in range(8)}
    tab = []
    for r in range(12):
        nm, src = p.read32(LC_TAB + 8 * r), p.read32(LC_TAB + 8 * r + 4)
        tab.append([it._cstr(p, nm, 24) if nm else "*", hex(src)])
        if src == 0:
            break
    return {"poll": it._poll(p), "gm": it._gmfields(p), "lc_n": n, "lc_runs": p.read32(LC_RUNS),
            "names_newest_first": [names[(n - 1 - j) & 7] for j in range(min(n, 8))], "table": tab,
            "luach_hook": p.read32(0x00356AD8) == 0x0C039E80, "players": _players(p),
            "money": [_money(p, s) for s in range(4)], "spray": [_spray(p, s) for s in range(4)], "cams": _cams(p),
            "pads_owner": it._pads(p)}


def join34(p):
    """X11 stand-in: for pads 1 and 2 (W4P slots 3 and 4) without a character, call the game's UpdateJoin
    (FUN_0041A460(GameMgr, pad)) on the game thread, as the W4P session layer does (F-0183)."""
    gm = it._gm(p)
    out = {"poll": it._poll(p), "before": it._pads(p), "count_before": it._s16(p.read32(gm + 0x224)), "calls": [],
           "cinematic_410": p.read32(gm + 0x410), "gm_14c": p.read32(gm + 0x14C), "join_flag_56e8": it._r8(p, gm + 0x56E8)}
    if out["cinematic_410"] or out["gm_14c"]:   # X11's quiet-gameplay rule (F-0183): no join during scenes/level end
        out["skipped"] = "not quiet"
        return out
    for pad in (1, 2):
        if it._s16(it._r16(p, PAD_OWNER + pad * 0x50 + 0x42)) == -1:
            out["calls"].append(it._call(p, UPDATE_JOIN, gm, pad))
    out["after"] = it._pads(p)
    out["count_after"] = it._s16(p.read32(gm + 0x224))
    return out


def _markers(p, key, checks):
    """checks: list of (Lua condition) -> digit 1/0, read as one decimal number (most significant first; at most 3)."""
    assert len(checks) <= 3
    expr = " ".join(f"W4P_R = W4P_R * 10 + (({c}) and 1 or 0)" for c in checks)
    return _q(p, key, "W4P_R = 0 " + expr)


H = "W4P_O and W4P_O.h"


def markers_m16(p):
    """helpers, CamSwitcher wrapped, GatePicked wrapped (expect 111)."""
    return _markers(p, "mk16", [H, "W4P_O and W4P_O.m16a and W4P_O.cs ~= chase.CamSwitcher",
                                "W4P_O and W4P_O.m16b and W4P_O.gp ~= ch2.GatePicked"])


def markers_m18(p):
    return _markers(p, "mk18", [H, "W4P_O and W4P_O.m18 and W4P_O.mi ~= C5.MoveInFOV and W4P_O.mo ~= C5.MoveOUTFOV"])


def markers_m11(p):
    return _markers(p, "mk11", [H, "W4P_O and W4P_O.m11 and W4P_O.gm ~= P2.GotMoney"])


def markers_m3(p):
    return _markers(p, "mk3", [H, "W4P_O and W4P_O.m3 and W4P_O.t3 ~= SpotGettingTagged"])


def markers_m6a(p):
    return _markers(p, "mk6a", [H, "W4P_O and W4P_O.m6a and W4P_O.t6a ~= C1.WarrTagStart"])


def markers_m6b(p):
    return _markers(p, "mk6b", [H, "W4P_O and W4P_O.m6b and W4P_O.t6b ~= C5.WarrTagStart"])


def markers_m13(p):
    return _markers(p, "mk13", [H, "W4P_O and W4P_O.m13t and W4P_O.t13 ~= WarriorTagging", "W4P_G34"])


# ---------------------------------------------------------------- spy on CamSetupRail during one call
SPY_RAIL = ("W4P_N = 0 W4P_X = 0 W4P_T = 0 local o = CamSetupRail "
            "CamSetupRail = function(n, t, a, b, c, d, i) W4P_N = W4P_N + 1 W4P_X = (i or -1) + 1 W4P_T = W4P_PN(t) "
            "return %o(n, t, a, b, c, d, i) end ")
SPY_RAIL_END = "CamSetupRail = o W4P_R = 100 + W4P_N * 100 + W4P_X * 10 + W4P_T "


def _rail_call(p, key, call):
    """R = 100 + calls*100 + (rail index + 1)*10 + target player number (100 = CamSetupRail not called)."""
    if not _has_p3(p):
        return {"skipped": "no player 3", "players": _players(p)}
    before = _cams(p)
    r = _q(p, key, SPY_RAIL + call + " " + SPY_RAIL_END)
    r.update(cams_before=before, cams_after=_cams(p))
    return r


# M16 (level54 cp2): chase.CamSwitcher, camswitch[5] = CamSetupRail("rail1", A1, ..., L2) + CameraMakeActive(railCam, 1, nil, A1)
def cs_p3(p):
    """Guarded handler, player 3 -> blocked (expect 100)."""
    return _rail_call(p, "cs_p3", "W4P_PC(chase.CamSwitcher, camswitch[5], HuGetPlayer(2))")


def cs_orig_p3(p):
    """Control: the original handler for player 3 -> CamSetupRail index 0 (player 1's) on player 3 (expect 213)."""
    return _rail_call(p, "cs_orig_p3", "W4P_PC(W4P_O.cs, camswitch[5], HuGetPlayer(2))")


def cs_p1(p):
    """Positive control: guarded handler for player 1 -> index 0 on player 1 (expect 211)."""
    return _rail_call(p, "cs_p1", "W4P_PC(chase.CamSwitcher, camswitch[5], player)")


# M16 ch2.GatePicked: spies on the camera calls, side effects stubbed
GP_STUB = ("local s1, s2, s3, s4, s5, s6, s7, s8, s9 = ObjectiveComplete, CamGhostDoor, W_StartStopWatch, ScheduleFunc, "
           "HuClearLook, HuUseAnim, BrFlush, GoalDevilRun, HuSetFastClimber local nop = function() end "
           "ObjectiveComplete, CamGhostDoor, W_StartStopWatch, ScheduleFunc, HuClearLook, HuUseAnim, BrFlush, GoalDevilRun, "
           "HuSetFastClimber = nop, nop, nop, nop, nop, nop, nop, nop, nop "
           "local fp, wa, go, su = chase.FinalPursuit, ch2.WarsAtEnd, chase.Goals, chase.SPEED_UP_RANGE ")
GP_UNSTUB = ("ObjectiveComplete, CamGhostDoor, W_StartStopWatch, ScheduleFunc, HuClearLook, HuUseAnim, BrFlush, GoalDevilRun, "
             "HuSetFastClimber = s1, s2, s3, s4, s5, s6, s7, s8, s9 "
             "chase.FinalPursuit, ch2.WarsAtEnd, chase.Goals, chase.SPEED_UP_RANGE = fp, wa, go, su ")
GP_SPY = ("W4P_GA, W4P_FP, W4P_FZ, W4P_MA = 0, 0, 0, 0 local c1, c2, c3, c4 = CameraGetActive, CamSetFollowPos, "
          "CamSetFollowZoom, CameraMakeActive "
          "CameraGetActive = function(i) W4P_GA = (i or -1) + 1 return %c1(i) end "
          "CamSetFollowPos = function(q, i) W4P_FP = (i or -1) + 1 end "
          "CamSetFollowZoom = function(q, i) W4P_FZ = (i or -1) + 1 end "
          "CameraMakeActive = function(c, b, f, h) W4P_MA = W4P_PN(h) end ")
GP_UNSPY = ("CameraGetActive, CamSetFollowPos, CamSetFollowZoom, CameraMakeActive = c1, c2, c3, c4 "
            "W4P_R = W4P_GA * 100 + W4P_FP * 10 + W4P_FZ W4P_R2 = W4P_MA ")


def _gp(p, key, call):
    if not _has_p3(p):
        return {"skipped": "no player 3", "players": _players(p)}
    return _q(p, key, GP_STUB + GP_SPY + call + " " + GP_UNSPY + GP_UNSTUB, ("W4P_R", "W4P_R2"))


def gp_p3(p):
    """Fixed handler, player 3: camera calls on his own view index 2 (expect R 333, R2 = 3)."""
    return _gp(p, "gp_p3", "W4P_PC(ch2.GatePicked, HuGetPlayer(2), nil)")


def gp_orig_p3(p):
    """Control: original handler, player 3 -> player 1's view index 0 (expect R 111, R2 3)."""
    return _gp(p, "gp_orig_p3", "W4P_PC(W4P_O.gp, HuGetPlayer(2), nil)")


def gp_p1(p):
    """Positive control: fixed handler, player 1 -> index 0 (expect R 111, R2 1)."""
    return _gp(p, "gp_p1", "W4P_PC(ch2.GatePicked, player, nil)")


def gp_real_p3(p):
    """Fixed handler for player 3 with the real camera calls (side effects stubbed): follow camera of view 3 (index 2)
    changes, view 1's does not."""
    if not _has_p3(p):
        return {"skipped": "no player 3", "players": _players(p)}
    before = _cams(p)
    r = _q(p, "gp_real_p3", GP_STUB + "W4P_PC(ch2.GatePicked, HuGetPlayer(2), nil) " + GP_UNSTUB + "W4P_R = 100")
    r.update(cams_before=before, cams_after=_cams(p))
    return r


# ---------------------------------------------------------------- M18 (level84 cp3)
def mi_p3(p):
    """Guarded C5.MoveInFOV, player 3 -> no rail (expect 100)."""
    return _rail_call(p, "mi_p3", "W4P_PC(C5.MoveInFOV, vFOVZoom, HuGetPlayer(2))")


def mo_p3(p):
    """Guarded C5.MoveOUTFOV, player 3 -> no rail (expect 100)."""
    return _rail_call(p, "mo_p3", "W4P_PC(C5.MoveOUTFOV, vFOVZoom, HuGetPlayer(2))")


def mi_orig_p3(p):
    """Control: original MoveInFOV for player 3 -> CamSetupRail index 1 (player 2's) on player 3 (expect 223)."""
    return _rail_call(p, "mi_orig_p3", "W4P_PC(W4P_O.mi, vFOVZoom, HuGetPlayer(2))")


def mi_p1(p):
    """Positive control: guarded MoveInFOV for player 1 -> index 0 on player 1 (expect 211)."""
    return _rail_call(p, "mi_p1", "W4P_PC(C5.MoveInFOV, vFOVZoom, player)")


# ---------------------------------------------------------------- M11 (level31 cp2): cash objective
def _setcash(p, key, m):
    return _q(p, key, f"InvSetMoney({m[0]}, 1) InvSetMoney({m[1]}, 2) InvSetMoney({m[2]}, 3) InvSetMoney({m[3]}, 4) "
                      "W4P_R = W4P_IGM2(2)")


def m11_sum(p):
    """Money 0/0/40/40 for players 1-4; the sum helper W4P_IGM2(2) = players 2+3+4 (expect 80)."""
    r = _q(p, "m11_set", "InvSetMoney(0, 2) InvSetMoney(40, 3) InvSetMoney(40, 4) W4P_R = W4P_IGM2(2) W4P_R2 = InvGetMoney(2)",
           ("W4P_R", "W4P_R2"))
    _run(p, "InvSetMoney(0, 1)")
    r.update(money=[_money(p, s) for s in range(4)], gm=it._gmfields(p), players=_players(p))
    return r


def m11_orig(p):
    """Control: the original P2.GotMoney(nil, true) with players 1-2 at 0 and players 3-4 at 40 each -> not enough
    (players 1-2 only): no payment, checkpoint stays 2."""
    before = [_money(p, s) for s in range(4)]
    r = _q(p, "m11_orig", "W4P_PC(W4P_O.gm, nil, true) W4P_R = 100")
    r.update(money_before=before, money_after=[_money(p, s) for s in range(4)], gm=it._gmfields(p))
    return r


def m11_fix(p):
    """Fixed P2.GotMoney(nil, true): 0 + (0 + 40 + 40) >= 75 -> pays 75 from players 2, 3, 4 (P3 40 -> 0, P4 40 -> 5),
    SetCheckPoint(3), preLoadFile("level31_gclub")."""
    _run(p, "InvSetMoney(0, 1) InvSetMoney(0, 2) InvSetMoney(40, 3) InvSetMoney(40, 4)")
    before = [_money(p, s) for s in range(4)]
    r = _q(p, "m11_fix", "W4P_PC(P2.GotMoney, nil, true) W4P_R = 100")
    r.update(money_before=before, money_after=[_money(p, s) for s in range(4)], gm=it._gmfields(p))
    return r


def m11_after(p):
    r = state(p)
    r["money"] = [_money(p, s) for s in range(4)]
    return r


# ---------------------------------------------------------------- tagging: which spray count does a tag start check?
TAG_STUB = ("local t1, t2, t3, t4, t5, t6, t7, t8, t9, t10 = HuTag, SoundPlayCommand, SetMsgHandler, SetMsgHandlerEx, "
            "HuSetPushable, W_StartStopWatch, SuperRunScene, HuSpeakNI, ObjHide, CfgTagStartCallback "
            "local o = W4P_IGSC local g = InvGetSpraycanCharges W4P_HT, W4P_SP, W4P_IG = 0, 0, 0 local nop = function() end "
            "HuTag = function(h, w, a) W4P_HT = W4P_PN(h) end SoundPlayCommand = function(h, n, a, b) W4P_SP = W4P_PN(h) end "
            "SetMsgHandler, SetMsgHandlerEx, HuSetPushable, W_StartStopWatch, SuperRunScene, HuSpeakNI, ObjHide, "
            "CfgTagStartCallback = nop, nop, nop, nop, nop, nop, nop, nop "
            "W4P_IGSC = function(p) W4P_IG = p or 1 return %o(p) end "
            "InvGetSpraycanCharges = function(p) W4P_IG = (p or 1) + 10 return %g(p) end ")
TAG_UNSTUB = ("HuTag, SoundPlayCommand, SetMsgHandler, SetMsgHandlerEx, HuSetPushable, W_StartStopWatch, SuperRunScene, "
              "HuSpeakNI, ObjHide, CfgTagStartCallback = t1, t2, t3, t4, t5, t6, t7, t8, t9, t10 "
              "W4P_IGSC = o InvGetSpraycanCharges = g "
              "W4P_R = W4P_HT * 100 + W4P_SP * 10 W4P_R2 = W4P_IG ")


def _tag(p, key, sprays, call, pre=""):
    """sprays = (player 1, player 3) charges set first (player 3 by his HUD slot + 1). R = (player number given to
    HuTag)*100 + (player number that got the no-paint sound)*10; R2 = player number whose spray count the check read
    (n = through W4P_IGSC = the row's own-spray path; 10 + n = through the global InvGetSpraycanCharges(n))."""
    if not _has_p3(p):
        return {"skipped": "no player 3", "players": _players(p)}
    src = (f"InvSetSpraycanCharges({sprays[0]}, 1) InvSetSpraycanCharges({sprays[1]}, HuGetHUD(HuGetPlayer(2)) + 1) "
           + pre + TAG_STUB + call + " " + TAG_UNSTUB)
    r = _q(p, key, src, ("W4P_R", "W4P_R2"))
    r.update(spray=[_spray(p, s) for s in range(4)], players=_players(p))
    return r


M3_SPOT = ("W4P_K = nil for k = 1, 20 do local t = tagflag[k] if t and master[t] and master[t].wtag and not master[t].done "
           "and k ~= 3 and k ~= 9 then W4P_K = k break end end ")


def m3_tag_p3(p):
    """Fixed SpotGettingTagged, player 1 spray 0, player 3 spray 3 -> HuTag for player 3 (expect R 300, R2 3)."""
    return _tag(p, "m3_tag_p3", (0, 3), "W4P_PC(SpotGettingTagged, tagflag[W4P_K], HuGetPlayer(2))", M3_SPOT)


def m3_orig_p3(p):
    """Control: original, same sprays -> checks player 1's 0 -> no-paint sound for player 3 (expect R 30, R2 11)."""
    return _tag(p, "m3_orig_p3", (0, 3), "W4P_PC(W4P_O.t3, tagflag[W4P_K], HuGetPlayer(2))", M3_SPOT)


def m3_tag_p3_empty(p):
    """Fixed, player 1 spray 3, player 3 spray 0 -> no-paint sound (expect R 30, R2 3)."""
    return _tag(p, "m3_tag_p3_empty", (3, 0), "W4P_PC(SpotGettingTagged, tagflag[W4P_K], HuGetPlayer(2))", M3_SPOT)


def m3_orig_p3_empty(p):
    """Control: original, player 1 spray 3, player 3 spray 0 -> HuTag for player 3 on player 1's paint (expect R 300,
    R2 11; the engine then refuses: it checks his own count, all_03.c FUN_00238DB0)."""
    return _tag(p, "m3_orig_p3_empty", (3, 0), "W4P_PC(W4P_O.t3, tagflag[W4P_K], HuGetPlayer(2))", M3_SPOT)


def m3_tag_p1(p):
    """Positive control: fixed, player 1 with spray 3 -> HuTag for player 1 (expect R 100, R2 11)."""
    return _tag(p, "m3_tag_p1", (3, 0), "W4P_PC(SpotGettingTagged, tagflag[W4P_K], player)", M3_SPOT)


def m3_real_p3(p):
    """Fixed handler for real (no stubs): player 1 spray 0, player 3 spray 3 -> player 3 starts tagging (HuIsTagging)."""
    if not _has_p3(p):
        return {"skipped": "no player 3", "players": _players(p)}
    r = _q(p, "m3_real_p3", "InvSetSpraycanCharges(0, 1) InvSetSpraycanCharges(3, HuGetHUD(HuGetPlayer(2)) + 1) " + M3_SPOT
           + "W4P_PC(SpotGettingTagged, tagflag[W4P_K], HuGetPlayer(2)) W4P_R = W4P_K", ("W4P_R",))
    r.update(spray=[_spray(p, s) for s in range(4)])
    return r


def m3_real_read(p):
    r = _q(p, "m3_real_read", "W4P_R = (HuIsTagging(HuGetPlayer(2)) and 1 or 0) * 10 + (HuIsTagging(player) and 1 or 0)")
    r.update(spray=[_spray(p, s) for s in range(4)], players=_players(p))
    return r


M6_PRE = "C1.WarrTag = C1.WarrTag or {} C1.WarrTagCtr = C1.WarrTagCtr or 0 local lf = C1.LockFlag "
M6_POST = " C1.LockFlag = lf"


def m6_tag_p3(p):
    """M6 cp2 fixed C1.WarrTagStart, player 1 spray 0, player 3 spray 3 -> HuTag for player 3 (expect R 300, R2 3)."""
    return _tag(p, "m6_tag_p3", (0, 3), "W4P_PC(C1.WarrTagStart, fWarrTag, HuGetPlayer(2))" + M6_POST, M6_PRE)


def m6_orig_p3(p):
    """Control: original asks player number 0 -> no paint (expect R 30, R2 10)."""
    return _tag(p, "m6_orig_p3", (0, 3), "W4P_PC(W4P_O.t6a, fWarrTag, HuGetPlayer(2))" + M6_POST, M6_PRE)


M13_SPOT = "W4P_A = nil "


def m13_tag_p3(p):
    """M13 cp1 fixed WarriorTagging with no tag object (A0 nil): only the spray check matters here; the rest of the
    handler fails on the nil object inside call(..., "x") (expect R2 3: player 3's own count was read)."""
    return _tag(p, "m13_tag_p3", (0, 3), "W4P_PC(WarriorTagging, nil, HuGetPlayer(2))")


def m13_orig_p3(p):
    """Control: original -> player 1's count (expect R2 11, R 30: no-paint sound)."""
    return _tag(p, "m13_orig_p3", (0, 3), "W4P_PC(W4P_O.t13, nil, HuGetPlayer(2))")

def m6b_tag_p3(p):
    """M6 cp5 fixed C5.WarrTagStart (gallery), player 1 spray 0, player 3 spray 3 -> HuTag for player 3 (expect R 300,
    R2 3)."""
    return _tag(p, "m6b_tag_p3", (0, 3), "W4P_PC(C5.WarrTagStart, fTagGallery[1], HuGetPlayer(2))")


def m6b_orig_p3(p):
    """Control: original asks player number 0 -> no paint (expect R 30, R2 10)."""
    return _tag(p, "m6b_orig_p3", (0, 3), "W4P_PC(W4P_O.t6b, fTagGallery[1], HuGetPlayer(2))")

# ---------------------------------------------------------------- walk-in into an existing box (safe teleport)
# FAILED TEST METHOD (run x6f_m16b): creating boxes at runtime with AddVolumeBox crashed the game (38 TLB misses,
# pc 0x004128E8 with object 0: the level's box pool is sized at level load, FUN_004125B8 then gets no object).
# Run x6f_m16 (first try) teleported player 3 into camswitch[12] far from the players: he fell through the world
# (z -234), GameMgr+0x14C became 1 and the test-call mailbox stopped. So: existing boxes only, and a teleport only to
# a point near player 1 (< 12 units) at player 1's own height.
def _near_tp(p, key, who, cx, cy, maxd=12.0):
    _, o1 = it._player(p, 0)
    x1, y1, z1 = it._pos(p, o1)
    d = ((cx - x1) ** 2 + (cy - y1) ** 2) ** 0.5
    if d > maxd:
        return {"skipped": f"box centre {d:.1f} units from player 1 (> {maxd})", "players": _players(p)}
    r = _q(p, key, f"Teleport({who}, {{{cx}, {cy}, {z1}}}, -1) W4P_R = 100")
    r.update(dist_p1=round(d, 2), players=_players(p))
    return r


# M16 cp2: camswitch[7] = AddVolumeBox("camswitch_07", 2, {-588.6, -29.9, -1.2}, {8, 6, 15}) (08262:1528), next to the
# cp2 start (players at about (-584, -21, 0)); handler path L3 == 7 sets the alley rail cameras of player/player2.
CS7 = (-584.6, -26.9)


def walk7_setup(p):
    """Spy on chase.CamSwitcher callers, (re)enable camswitch[7] with its handler as chase main_95 does, then put
    player 3 into it (4 units from player 1, same height)."""
    if not _has_p3(p):
        return {"skipped": "no player 3", "players": _players(p)}
    r0 = _q(p, "walk7_spy", "W4P_WN = 0 W4P_WP = 0 W4P_W3 = 0 local o = chase.CamSwitcher "
                            "chase.CamSwitcher = function(a0, a1) local k = W4P_PN(a1) W4P_WN = W4P_WN + 1 W4P_WP = k "
                            "if k == 3 then W4P_W3 = W4P_W3 + 1 end return %o(a0, a1) end "
                            "EnableVolumeBox(camswitch[7], 1) SetMsgHandler(camswitch[7], 3, \"chase.CamSwitcher\") W4P_R = 100")
    r = _near_tp(p, "walk7_p3", "HuGetPlayer(2)", *CS7)
    r["spy"] = r0
    return r


def walk7_read1(p):
    """R = inside(player 3)*100 + calls by player 3 *10 + all calls (expect 100: inside, never reported)."""
    r = _q(p, "walk7_read1", "W4P_R = 100 * (IsInsideBox(camswitch[7], HuGetPlayer(2)) and 1 or 0) + 10 * W4P_W3 + W4P_WN")
    r["players"] = _players(p)
    return r


def walk7_p1(p):
    return _near_tp(p, "walk7_p1", "player", *CS7)


def walk7_read2(p):
    """R = inside(player 1)*100 + calls*10 + last caller (expect 111: player 1 inside, his enter reported)."""
    r = _q(p, "walk7_read2", "W4P_R = 100 * (IsInsideBox(camswitch[7], player) and 1 or 0) + 10 * W4P_WN + W4P_WP "
                             "W4P_R2 = W4P_W3", ("W4P_R", "W4P_R2"))
    r["players"] = _players(p)
    return r


# M18 cp3: vFOVZoom = AddVolumeBox("vFOVZoom", 0, {-471.1, -229.9, -0.9}, {14, 24, 6}) (09030:1412), type 0
FOV = (-464.1, -217.9)


def fov2_setup(p):
    """Spies on C5.MoveInFOV callers and on CamSetupRail; handlers registered as C5.SetRailCam does; player 3 put into
    vFOVZoom only if it is near player 1."""
    if not _has_p3(p):
        return {"skipped": "no player 3", "players": _players(p)}
    r0 = _q(p, "fov2_spy",
            "W4P_H = {0, 0, 0, 0, 0, 0, 0, 0, 0} W4P_RN = 0 W4P_RX = 0 W4P_RT = 0 "
            "local o1, o3 = C5.MoveInFOV, CamSetupRail "
            "C5.MoveInFOV = function(a0, a1) local k = W4P_PN(a1) W4P_H[k] = W4P_H[k] + 1 return %o1(a0, a1) end "
            "CamSetupRail = function(n, t, a, b, c, d, i) W4P_RN = W4P_RN + 1 W4P_RX = (i or -1) + 1 W4P_RT = W4P_PN(t) "
            "return %o3(n, t, a, b, c, d, i) end "
            "SetMsgHandler(vFOVZoom, 3, \"C5.MoveInFOV\") SetMsgHandler(vFOVZoom, 4, \"C5.MoveOUTFOV\") W4P_R = 100")
    r = _near_tp(p, "fov2_p3", "HuGetPlayer(2)", *FOV, maxd=30.0)
    r["spy"] = r0
    return r


def fov2_read1(p):
    """R = inside(P3)*100 + MoveInFOV calls by P3 *10 + CamSetupRail calls (expect 110: reported for player 3 - a
    type-0 box -, guard stops the rail); R2 = last rail (index+1)*10 + target."""
    r = _q(p, "fov2_read1", "W4P_R = 100 * (IsInsideBox(vFOVZoom, HuGetPlayer(2)) and 1 or 0) + 10 * W4P_H[3] + W4P_RN "
                            "W4P_R2 = W4P_RX * 10 + W4P_RT", ("W4P_R", "W4P_R2"))
    r["players"] = _players(p)
    return r


def fov2_p1(p):
    return _near_tp(p, "fov2_p1", "player", *FOV, maxd=30.0)


def fov2_read2(p):
    """R = inside(P1)*100 + calls by P1 *10 + CamSetupRail calls; R2 = last rail (index+1)*10 + target (expect R 111,
    R2 11: player 1's own rail index 0)."""
    r = _q(p, "fov2_read2", "W4P_R = 100 * (IsInsideBox(vFOVZoom, player) and 1 or 0) + 10 * W4P_H[1] + W4P_RN "
                            "W4P_R2 = W4P_RX * 10 + W4P_RT", ("W4P_R", "W4P_R2"))
    r["players"] = _players(p)
    return r


# Run x6f_m18 skipped fov2_setup: vFOVZoom is 125 units from the cp3 start (players at about (-339, -217, -0.24), same
# y and height). fov3_* allow that distance (teleport at player 1's height along the same line); a run that uses them
# puts them last, because a fall through the world stops the test mailbox (GameMgr+0x14C = 1, run x6f_m16).
def fov3_setup(p):
    if not _has_p3(p):
        return {"skipped": "no player 3", "players": _players(p)}
    r0 = _q(p, "fov3_spy",
            "W4P_H = {0, 0, 0, 0, 0, 0, 0, 0, 0} W4P_RN = 0 W4P_RX = 0 W4P_RT = 0 "
            "local o1, o3 = C5.MoveInFOV, CamSetupRail "
            "C5.MoveInFOV = function(a0, a1) local k = W4P_PN(a1) W4P_H[k] = W4P_H[k] + 1 return %o1(a0, a1) end "
            "CamSetupRail = function(n, t, a, b, c, d, i) W4P_RN = W4P_RN + 1 W4P_RX = (i or -1) + 1 W4P_RT = W4P_PN(t) "
            "return %o3(n, t, a, b, c, d, i) end "
            "SetMsgHandler(vFOVZoom, 3, \"C5.MoveInFOV\") SetMsgHandler(vFOVZoom, 4, \"C5.MoveOUTFOV\") W4P_R = 100")
    r = _near_tp(p, "fov3_p3", "HuGetPlayer(2)", *FOV, maxd=140.0)
    r["spy"] = r0
    return r


def fov3_read1(p):
    """Expect R 110 (player 3 inside, reported by the type-0 box, no rail: guard), R2 0."""
    return _fov_read(p, "fov3_read1", "HuGetPlayer(2)", 3)


def fov3_p1(p):
    return _near_tp(p, "fov3_p1", "player", *FOV, maxd=140.0)


def fov3_read2(p):
    """Expect R 111 (player 1 inside, reported, one rail), R2 11 (index 0, player 1)."""
    return _fov_read(p, "fov3_read2", "player", 1)


def _fov_read(p, key, who, k):
    """R = inside*100 + MoveInFOV calls by that player *10 + CamSetupRail calls; R2 = last rail (index+1)*10 + target."""
    r = _q(p, key, f"W4P_R = 100 * (IsInsideBox(vFOVZoom, {who}) and 1 or 0) + 10 * W4P_H[{k}] + W4P_RN "
                   "W4P_R2 = W4P_RX * 10 + W4P_RT", ("W4P_R", "W4P_R2"))
    r["players"] = _players(p)
    return r


# M13 with a real tag object: the handlers are set on master[..][..][..].Left (09720 disassembly main.1 #3-19)
M13_OBJ = ("W4P_A = nil for a, b in master do if type(b) == \"table\" then for c, d in b do if type(d) == \"table\" then "
           "for e, f in d do if type(f) == \"table\" and f.Left then W4P_A = f.Left end end end end end end ")


def m13_tag2_p3(p):
    """Fixed WarriorTagging on a real tag object, player 1 spray 0, player 3 spray 3 -> HuTag for player 3
    (expect R 300, R2 3)."""
    return _tag(p, "m13_tag2_p3", (0, 3), "W4P_PC(WarriorTagging, W4P_A, HuGetPlayer(2))", M13_OBJ)


def m13_orig2_p3(p):
    """Control: original on the same object -> player 1's count -> no-paint sound (expect R 30, R2 11)."""
    return _tag(p, "m13_orig2_p3", (0, 3), "W4P_PC(W4P_O.t13, W4P_A, HuGetPlayer(2))", M13_OBJ)

"""camC camera parity (docs/research/m6_cam_camC.md): the tracked-humans list 0x005D91A8 and the per-view cameras for
nav_probe.py --probe cam_camC_probe:<function>:<poll> (one instance, test only).

- trk(): read-only snapshot: the 4 list handles (who: P1..P4 = game player 1-4, else 'ai<char id>'), per view the
  render camera (0x000F0810+4i), the follow camera (0x000F0820+4i) with its primary target (+0x314 human, +0x31C
  handle, +0x444 target count) and its secondary target (+0x320 handle, +0x3FC weight), the rail camera
  (0x000F0830+4i) with its targets (+0x340/+0x344 humans, +0x348 count), views 0x0050B198, LUACH chunk names.
- action probes run Lua through LUARUN like tests/m2/x6fix_probe.py (x6fix_probe._q: result through player 1's
  money, restored). Originals are kept by the camC rows in W4PC.* (o[1..4] = M17 ObjShowive/Multiplayer/DoorDestroyed/Cleanup,
  cc/bw = M8, p3[...] = M1; the first test runs used W4PC.os/mp/dd/cl).
Function names are OUR labels (the ELF is stripped). Static addresses, SLUS-21215 v1.03. Field offsets: follow picker
FUN_001282A0 (all_00.c:27285-27360), CamSetSecondary core FUN_0011DCF0 (+0x320 handle, +0x3FC weight; binding
0x003670C0 arg order h, weight, index), rail picker FUN_0013B7B8 + RAILTGT (mod/m2/camtarget.txt).
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "m2"))
import inv_tests as it  # noqa: E402
import x6fix_probe as xf  # noqa: E402

TRK = 0x005D91A8
NILH = 0x006EBD30           # address of the invalid handle value
RENDER, FOLLOW, RAIL = 0x000F0810, 0x000F0820, 0x000F0830
VIEWS = 0x0050B198
LC_N, LC_LOG = 0x000E7AFC, 0x000E7B00


def _f(v):
    return round(struct.unpack("<f", struct.pack("<I", v & 0xFFFFFFFF))[0], 3)


def _pobjs(p):
    return [it._player(p, i)[1] for i in range(4)]


def _who_obj(p, o, pobjs):
    if not o:
        return None
    if o in pobjs:
        return f"P{pobjs.index(o) + 1}"
    if not 0x00100000 <= o < 0x02000000:
        return f"?{o:#x}"
    b = p.read32(o + 0x1B0) & 0xFF
    return f"ai{p.read32(o + 0xD0) & 0xFFFF}" + ("" if b == 0xFF else f"(pidx{b})")


def _who_h(p, h, pobjs):
    if h in (0, 0xFFFFFFFF, p.read32(NILH)):
        return None
    o = it._resolve(p, h)
    return _who_obj(p, o, pobjs) if o else f"stale{h:#x}"


def trk(p):
    pobjs = _pobjs(p)
    gm = it._gm(p)
    lst = [p.read32(TRK + 4 * k) for k in range(4)]
    out = {"poll": it._poll(p), "checkpoint": it._r16(p, gm + 0x33A), "count": it._s16(p.read32(gm + 0x224)),
           "views": p.read32(VIEWS), "list": [_who_h(p, h, pobjs) for h in lst], "list_raw": [hex(h) for h in lst],
           "players": {i + 1: hex(o) for i, o in enumerate(pobjs)},
           "pos": {i + 1: [round(v, 1) for v in it._pos(p, o)] for i, o in enumerate(pobjs) if o}, "cams": {}}
    for i in range(4):
        r, f, rl = p.read32(RENDER + 4 * i), p.read32(FOLLOW + 4 * i), p.read32(RAIL + 4 * i)
        c = {"render": hex(r), "render_is": "follow" if r and r == f else "rail" if r and r == rl else ("none" if not r else "other")}
        if 0x00100000 <= f < 0x02000000:
            c.update(f_tgt=_who_obj(p, p.read32(f + 0x314), pobjs), f_tgt2=_who_obj(p, p.read32(f + 0x318), pobjs),
                     f_last=_who_h(p, p.read32(f + 0x31C), pobjs), f_cnt=it._r16(p, f + 0x444),
                     f_sec=_who_h(p, p.read32(f + 0x320), pobjs), f_secw=_f(p.read32(f + 0x3FC)))
        if 0x00100000 <= rl < 0x02000000:
            c.update(r_tgt=_who_obj(p, p.read32(rl + 0x340), pobjs), r_tgt2=_who_obj(p, p.read32(rl + 0x344), pobjs),
                     r_cnt=p.read32(rl + 0x348))
        if 0x00100000 <= r < 0x02000000:   # base camera: eye +0x10 (vtable +0x21C = 0x004DB1C8), look point +0x20 (+0x224)
            c.update(eye=[_f(p.read32(r + 0x10 + 4 * k)) for k in range(3)], look=[_f(p.read32(r + 0x20 + 4 * k)) for k in range(3)])
        out["cams"][i] = c
    o0 = it._resolve(p, lst[0])
    out["list0_pos"] = [round(v, 1) for v in it._pos(p, o0)] if o0 else None
    n = p.read32(LC_N)
    out["lc_names"] = [it._cstr(p, LC_LOG + 32 * ((n - 1 - j) & 7), 32) for j in range(min(n, 8))]
    out["lc_runs"] = p.read32(0x000E7AF8)
    return out


def _act(p, name, src, names=("W4P_R",)):
    """Run src (Lua; sets W4P_R) once per poll key, then snapshot."""
    r = xf._q(p, f"camC_{name}_{it._poll(p) // 100}", src, names)
    r["trk_after"] = trk(p)
    return r


# ---------------------------------------------------------------- common
def markers(p):
    """Rows present: camC helpers, M17 row, M8 row, M1 row (each digit 1/0) -> W4P_R (helpers*1000 is too big: two
    reads)."""
    a = xf._markers(p, f"camC_mk1_{it._poll(p)}", ["W4PC and W4PC.h", "W4PC and W4PC.o and C3 and W4PC.o[1] ~= C3.ObjShowive",
                                                   "W4P_O and W4P_O.h"])
    b = xf._markers(p, f"camC_mk2_{it._poll(p)}", ["W4PC and W4PC.cc and C5 and W4PC.cc ~= C5.ChatterCam",
                                                   "W4PC and W4PC.p3 and P3 and W4PC.p3.EndChapterScene ~= P3.EndChapterScene",
                                                   "W4PC_TW and W4PC_SW"])
    return {"m17_helpers_x6": a, "m8_m1_fn": b, "trk": trk(p)}


def god(p):
    """Test aid: god mode for every current player (bots stand still in boss fights)."""
    return _act(p, "god", "for i = 0, 3 do local h = HuGetPlayer(i) if h and HuIsAPlayer(h) then HuSetGodMode(h, true) end end "
                          "W4P_R = 1")


SET4 = ("CamTarget(2, 0, 0) for i = 0, 3 do local h = HuGetPlayer(i) if h and HuIsAPlayer(h) then CamTarget(0, 0, h) end end ")


def set4(p):
    """Tracked list = P1, P2, P3, P4 (what UpdateJoin(-1) builds after a clear: the list a chapter starts with when 4
    players are in the game)."""
    return _act(p, "set4", SET4 + "W4P_R = 1")


def split_on(p):
    return _act(p, "split_on", "CamEnable(3, true) W4P_R = 1")


# ---------------------------------------------------------------- M17 cp2 (level55_lizziesattack.lua)
ST17 = "local s1, s2 = ScenePreload, HuSpeakNI local nop = function() end ScenePreload, HuSpeakNI = nop, nop "
UN17 = "ScenePreload, HuSpeakNI = s1, s2 "


def m17_orig(p):
    """Original C3.ObjShowive with the original C3.Multiplayer (scene preload and speech stubbed) on the current list."""
    return _act(p, "m17_orig", ST17 + "local m = C3.Multiplayer C3.Multiplayer = W4PC.o[2] W4P_PC(W4PC.o[1]) C3.Multiplayer = m "
                + UN17 + "W4P_R = 1")


def m17_fix(p):
    """camC-wrapped C3.ObjShowive (same stubs) on the current list."""
    return _act(p, "m17_fix", ST17 + "W4P_PC(C3.ObjShowive) " + UN17 + "W4P_R = 1")


def m17_set4_orig(p):
    return _act(p, "m17_s4o", SET4 + ST17 + "local m = C3.Multiplayer C3.Multiplayer = W4PC.o[2] W4P_PC(W4PC.o[1]) "
                "C3.Multiplayer = m " + UN17 + "W4P_R = 1")


def m17_set4_fix(p):
    return _act(p, "m17_s4f", SET4 + ST17 + "W4P_PC(C3.ObjShowive) " + UN17 + "W4P_R = 1")


LL34 = ("CamTarget(2, 0, 0) local z = Lizzie01[\"101\"] CamTarget(0, 0, z) CamTarget(0, 0, z) "
        "for i = 2, 3 do local h = HuGetPlayer(i) if h and HuIsAPlayer(h) then CamTarget(0, 0, h) end end ")
STDD = "local s3 = PlayL55RemSmash PlayL55RemSmash = function() end "
UNDD = "PlayL55RemSmash = s3 "


def m17_dd_orig(p):
    """List = Lizzie, Lizzie, P3, P4 (the 4-player boss list after the fix), then the original C3.DoorDestroyed (its
    scene PlayL55RemSmash stubbed): split off, shared camera."""
    return _act(p, "m17_ddo", "CamEnable(3, true) " + LL34 + STDD + "W4P_PC(W4PC.o[3], Doors.Liz, player) " + UNDD + "W4P_R = 1")


def m17_dd_fix(p):
    return _act(p, "m17_ddf", "CamEnable(3, true) " + LL34 + STDD + "W4P_PC(C3.DoorDestroyed, Doors.Liz, player) " + UNDD
                + "W4P_R = 1")


def m17_boss_back(p):
    """After the door tests: split on, the boss list again (Lizzie, Lizzie, P3, P4)."""
    return _act(p, "m17_back", "CamEnable(3, true) CamEnable(4, false) " + LL34 + "W4P_R = 1")


def m17_next(p):
    """Natural chapter change: NextMission() (cp1 -> cp2 when called in cp1)."""
    return _act(p, "m17_next", "NextMission() W4P_R = 1")


# ---------------------------------------------------------------- M8 cp5 (level81_chatterbox.lua)
def m8_cc_orig(p):
    return _act(p, "m8_cco", "W4P_PC(W4PC.cc) W4P_R = 1")


def m8_bw_orig(p):
    return _act(p, "m8_bwo", "W4P_PC(W4PC.bw) W4P_R = 1")


def m8_cc_fix(p):
    return _act(p, "m8_ccf", "W4P_PC(C5.ChatterCam) W4P_R = 1")


def m8_bw_fix(p):
    return _act(p, "m8_bwf", "W4P_PC(C5.CamBackToWarriors) W4P_R = 1")


def m8_set4_cc_orig(p):
    return _act(p, "m8_s4cco", SET4 + "W4P_PC(W4PC.cc) W4P_R = 1")


def m8_set4_cc_fix(p):
    return _act(p, "m8_s4ccf", SET4 + "W4P_PC(C5.ChatterCam) W4P_R = 1")


# ---------------------------------------------------------------- M1 (level99)
def m1_combat_over(p):
    """cp1 -> cp2 the way the game does it: P1.CombatOver (scene l99_c6, ReturnFunc P1.Cleanup: wheelScene = 1,
    SetCheckPoint(2), preLoadFile("level99_lesson1", "P2.SetupLesson1"))."""
    return _act(p, "m1_co", "bAshIntro = false P1.CombatOver() W4P_R = 1")


def m1_vj_orig(p):
    """Original P3.VerminJumped(nil, Teacher.Vermin): clears the secondary target of views 1-2 (HUD calls run too)."""
    return _act(p, "m1_vjo", "W4P_PC(W4PC.p3.VerminJumped, nil, Teacher.Vermin) W4P_R = 1")


def m1_vj_fix(p):
    return _act(p, "m1_vjf", "W4P_PC(P3.VerminJumped, nil, Teacher.Vermin) W4P_R = 1")


ST1 = ("local s1, s2, s3, s4 = HuSpeakNI, GoalMoveToFlag, SetMsgHandler, HUDSetTutorialText local nop = function() end "
       "HuSpeakNI, GoalMoveToFlag, SetMsgHandler, HUDSetTutorialText = nop, nop, nop, nop ")
UN1 = "HuSpeakNI, GoalMoveToFlag, SetMsgHandler, HUDSetTutorialText = s1, s2, s3, s4 "


def m1_ecs_orig(p):
    """Original P3.EndChapterScene (speech, goal, handlers, tutorial text stubbed): Vermin as secondary for views 1-2."""
    return _act(p, "m1_ecso", ST1 + "W4P_PC(W4PC.p3.EndChapterScene) " + UN1 + "W4P_R = 1")


def m1_ecs_fix(p):
    return _act(p, "m1_ecsf", ST1 + "W4P_PC(P3.EndChapterScene) " + UN1 + "W4P_R = 1")


# ---------------------------------------------------------------- audit 5.6: leave path and the tracked list
LEAVE = 0x000E7100   # session LEAVE(index) cave ([warriors-4p session] S5)


def leave4(p):
    """Session LEAVE of game player 4 (index 3) through the test-call mailbox; list before and after."""
    before = trk(p)
    o4 = it._player(p, 3)[1]
    h4 = p.read32(it._gm(p) + 0x228 + 12)
    r = it._once(p, f"camC_leave4_{it._poll(p) // 100}", LEAVE, 3)
    after = trk(p)
    raw_after = [p.read32(TRK + 4 * k) for k in range(4)]
    return {"before": before, "call": r, "p4_handle": hex(h4), "p4_obj": hex(o4),
            "p4_handle_still_in_list": h4 in raw_after, "after": after}


# ---------------------------------------------------------------- M17 views 3-4 framing (visual comparison)
def near34(p):
    """Test aid: players 3 and 4 put next to players 1 and 2 (the game's HuTeleportNearHuman, as X4 does)."""
    return _act(p, "near34", "local a, b = HuGetPlayer(2), HuGetPlayer(3) if a and HuIsAPlayer(a) then HuTeleportNearHuman(a, player) end "
                             "if b and HuIsAPlayer(b) then HuTeleportNearHuman(b, player2) end W4P_R = 1")


def m17_sec34_off(p):
    """Views 3-4 without the boss secondary target (= what the original gives players 3-4)."""
    return _act(p, "m17_s34off", "for i = 2, 3 do CamSetSecondary(NilHandle, 0, i) end W4P_R = 1")


def m17_sec34_on(p):
    return _act(p, "m17_s34on", "for i = 2, 3 do CamSetSecondary(Lizzie01[\"101\"], 0, i) end W4P_R = 1")


def m17_sec34_own(p):
    """BOSSTGT feasibility (local/m6/cam/camC/bosstgt.py, test-only PINE pokes): views 3-4 get their own player as
    secondary target, exactly as the script does for views 1-2 (CamSetSecondary(player, 0, 0))."""
    return _act(p, "m17_s34own", "for i = 2, 3 do local h = HuGetPlayer(i) if h and HuIsAPlayer(h) then CamSetSecondary(h, 0, i) end end "
                                 "W4P_R = 1")


def cave(p):
    """Read back the BOSSTGT test cave and the camtarget redirect words."""
    return {"poll": it._poll(p), "f0b9c": hex(p.read32(0x000F0B9C)), "f0ba0": hex(p.read32(0x000F0BA0)),
            "cave": [hex(p.read32(0x000EFC00 + 4 * k)) for k in range(34)]}

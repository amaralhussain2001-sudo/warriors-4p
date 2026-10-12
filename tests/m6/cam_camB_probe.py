"""camB camera-parity probes (docs/research/m6_cam_camB.md): M6 cp4 rooftop chase rails (level3_chase.lua) and M9 cp4
cage cameras (level86_chapter4.lua) for players 3-4.

Used by nav_probe.py --probe cam_camB_probe:<function>:<poll> after a level jump (CallAt SetCheckPoint + MenuLoadLevel).
SINGLE-PC, one instance, scripted bots, test only. Readers are read-only; the Lua probes run short test texts through
LUARUN (x6fix_probe._q: text in 0x000EF000.., results through player 1's money, restored). Function and structure names
are OUR labels (the ELF is stripped); static addresses, SLUS-21215 v1.03.

Camera objects (VERIFIED code, docs/research/m6_camera_parity.md 1.1-1.2, all_00.c): per-view arrays relocated by the
4p group: render 0x000F0810, follow 0x000F0820, rail 0x000F0830 (+4*view). Rail camera (vtable 0x00536DD0): target
human handle +0x340 (count +0x348, picked by FUN_0013B7B8 / RAILTGT for views 3-4), point count s16 +0x350,
CamModifyRail target values: k=2 (fov) +0x3A0, k=1 +0x3A4, k=0 +0x3A8 (FUN_0011D228). Tracked humans list 0x005D91A8.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "m2"))
import inv_tests as it  # noqa: E402
import x6fix_probe as xf  # noqa: E402

RENDER, FOLLOW, RAIL = 0x000F0810, 0x000F0820, 0x000F0830
RAIL_VT = 0x00536DD0
BLEND_VT = 0x00537610   # per-view camera made by CameraMakeActive with a blend time (runs cb6base2/cb9base2)
TRACKED = 0x005D91A8
VIEWS = 0x0050B198
LC_N, LC_LOG = 0x000E7AFC, 0x000E7B00
LC_TAB = 0x000EEC00


def _fl(p, a):
    return it._f(p.read32(a))


def _rail(p, r):
    """Rail camera fields (run cb6base: MainRail's CamModifyRail values 78 / 5.5 / 4 / -8 / 6 / 2 sit at +0x374 / +0x378 /
    +0x37C / +0x380 / +0x384 / +0x398 = k2 (fov), k0, k1, k3, k4, k9; +0x340 = target human OBJECT pointer)."""
    if not 0x00100000 <= r < 0x02000000:
        return None
    return {"tgt": hex(p.read32(r + 0x340)), "tcount": p.read32(r + 0x348), "points": it._s16(p.read32(r + 0x350)),
            "fov": _fl(p, r + 0x374), "k0": _fl(p, r + 0x378), "k1": _fl(p, r + 0x37C), "k3": _fl(p, r + 0x380),
            "k4": _fl(p, r + 0x384), "k9": _fl(p, r + 0x398),
            "pts_xyz": [[_fl(p, r + 0x1E0 + 16 * k + 4 * j) for j in range(3)] for k in range(2)]}   # FUN_0013B780


def cams(p):
    """Per view: render / follow / rail pointers, what the render camera is, the rail's target and framing values."""
    out = {}
    objs = {hex(it._player(p, i)[1]): i + 1 for i in range(4) if it._player(p, i)[1]}
    for v in range(4):
        rd, fo, ra = p.read32(RENDER + 4 * v), p.read32(FOLLOW + 4 * v), p.read32(RAIL + 4 * v)
        def kind_of(c):
            return ("follow" if c == fo and c else "rail" if c == ra and c else "rail0" if c and c == p.read32(RAIL) else
                    "none" if not c else "other")
        kind = kind_of(rd)
        if kind == "other" and 0x00100000 <= rd < 0x02000000 and p.read32(rd) == BLEND_VT:
            kind = "blend->" + kind_of(p.read32(rd + 0x214))   # blend camera: target at +0x214 (FUN_0011EAF0 case 5)
        ri = _rail(p, ra)
        if ri:
            ri["tgt_player"] = objs.get(ri["tgt"])
        out[v] = {"render": hex(rd), "kind": kind, "render_vt": hex(p.read32(rd)) if 0x00100000 <= rd < 0x02000000 else None,
                  "follow": hex(fo), "rail": hex(ra), "rail_info": ri}
    return out


def st(p):
    gm = it._gm(p)
    n = p.read32(LC_N)
    return {"poll": it._poll(p), "checkpoint": it._r16(p, gm + 0x33A), "level": it._cstr(p, gm + 0x124, 16),
            "count": it._s16(p.read32(gm + 0x224)), "views": p.read32(VIEWS), "cin_410": p.read32(gm + 0x410),
            "gm_14c": p.read32(gm + 0x14C), "join_flag": it._r8(p, gm + 0x56E8),
            "tracked": [hex(p.read32(TRACKED + 4 * k)) for k in range(6)],
            "lc_names": [it._cstr(p, LC_LOG + 32 * ((n - 1 - j) & 7), 32) for j in range(min(n, 6))],
            "lc_runs": p.read32(0x000E7AF8), "players": xf._players(p), "cams": cams(p), "pads": it._pads(p)}


def join(p):
    """X11 stand-in (x6fix_probe.join34): UpdateJoin for pads 1 and 2 without a character, only in quiet gameplay."""
    gm = it._gm(p)
    if it._s16(p.read32(gm + 0x224)) >= 4:
        return {"skipped": "4 players", "poll": it._poll(p)}
    return xf.join34(p)


def _lua(p, key, src, names=("W4P_R",)):
    return xf._q(p, f"{key}_{it._poll(p)}", src, names)


def god(p):
    """Test only: god mode for every player (the bots stand still; the chase mimes / cage Destroyers would down them)."""
    return _lua(p, "god", "W4P_R = 0 for i = 0, 3 do local h = HuGetPlayer(i) if HuIsAPlayer(h) then "
                          "HuSetGodMode(h, true) W4P_R = W4P_R + 1 end end")


def _tp(p, key, idx, dx, dy):
    """Test only: player idx (2/3 = players 3/4) next to player 1 at his height (never far: m6_x6_fixes.md neg. 2)."""
    _, o1 = it._player(p, 0)
    if not o1:
        return {"skipped": "no player 1"}
    x, y, z = it._pos(p, o1)
    r = _lua(p, key, f"local h = HuGetPlayer({idx}) if HuIsAPlayer(h) then Teleport(h, {{{x + dx}, {y + dy}, {z}}}, -1) "
                     "W4P_R = 100 else W4P_R = 0 end")
    r["p1_pos"] = [x, y, z]
    return r


def tp3(p):
    return _tp(p, "tp3", 2, 1.5, 0.0)


def tp4(p):
    return _tp(p, "tp4", 3, -1.5, 0.0)


def tp34(p):
    return {"p3": tp3(p), "p4": tp4(p), "after": xf._players(p)}


def lua_state(p):
    """camB rows: helpers (W4BW) / M6 row (W4B6) / M9 row (W4B9) present -> 3 digits; camB rail owners W4BR[2], [3]
    as player numbers (0 = none, 9 = not a player)."""
    r = _lua(p, "lst", "W4P_R = 100 * ((W4BW and 1) or 0) + 10 * ((W4B6 and 1) or 0) + ((W4B9 and 1) or 0) "
                       "W4P_R2 = 10 * ((W4BR and W4BR[2] and W4P_PN(W4BR[2])) or 0) + "
                       "((W4BR and W4BR[3] and W4P_PN(W4BR[3])) or 0) "
                       "W4P_R3 = ((W4B6 and W4B6.t and 1) or 0) + 10 * ((W4B9 and W4B9.p) or 0)", ("W4P_R", "W4P_R2", "W4P_R3"))
    return r


def snap(p):
    """State + Lua state in one probe."""
    return {"st": st(p), "lua": lua_state(p)}


def _cmp(p, key, src, names=("W4P_R",)):
    """Cameras before, run the Lua text, cameras after (direct-call tests)."""
    if not xf._has_p3(p) and key not in ("m6sr", "m9p2", "m6t1", "m6mr", "m6end"):
        return {"skipped": "no player 3", "players": xf._players(p)}
    before = cams(p)
    r = _lua(p, key, src, names)
    r.update(cams_before=before, cams_after=cams(p))
    return r


# ---------------------------------------------------------------- M6 cp4 (level3_chase.lua, 08022)
# hazards (m6_camera_parity.md section 3, M6 rows 2-3): the handlers on type-0 boxes run for players 3-4 by walking
def m6_top_orig_p3(p):
    """Original ch4.EnterTopRail for player 3 (index -1 = every rail): expect rails 0/1 framing changed (k1 -> 20)."""
    return _cmp(p, "m6to", "W4P_PC((W4P_O and W4P_O.et) or ch4.EnterTopRail, vTopRail[14], HuGetPlayer(2)) W4P_R = 100")


def m6_top_p3(p):
    """Current ch4.EnterTopRail (wrapped by the camB row) for player 3: expect only rail 2 changed."""
    return _cmp(p, "m6tf", "W4P_PC(ch4.EnterTopRail, vTopRail[14], HuGetPlayer(2)) W4P_R = 100")


def m6_main_p1(p):
    """Restore players 1-2's MainRail framing after a control call (what Setup / StartRail give them)."""
    return _cmp(p, "m6mr", "ch4.MainRail(player) if HuIsAPlayer(player2) then ch4.MainRail(player2) end W4P_R = 100")


def m6_exit_orig_p3(p):
    """Original ch4.ExitFixCam for player 3: CameraMakeActive(ch4.railCam, 1, nil, P3)."""
    return _cmp(p, "m6xo", "W4P_PC((W4P_O and W4P_O.xf) or ch4.ExitFixCam, vFixCam[14], HuGetPlayer(2)) W4P_R = 100")


def m6_exit_p3(p):
    return _cmp(p, "m6xf", "W4P_PC(ch4.ExitFixCam, vFixCam[14], HuGetPlayer(2)) W4P_R = 100")


def m6_follow_p3(p):
    """Test only: player 3 back on his follow camera (to repeat a hazard test from a clean state)."""
    return _cmp(p, "m6fo", "CameraMakeActive(MainCam, 0, nil, HuGetPlayer(2)) W4P_R = 100")


def m6_boxes(p):
    """How many chase camera boxes (vSideRail, vMainRail, vBigRail, vTopRail, vFixCam) each player is inside:
    R = players 1-2 (two digits), R2 = players 3-4, R3 = player 1 inside vbStartRail (1/0) (money reads cap at 999)."""
    src = ("W4P_V = {} local t = {vSideRail, vMainRail, vBigRail, vTopRail, vFixCam} "
           "for i = 0, 3 do local h = HuGetPlayer(i) local n = 0 if HuIsAPlayer(h) then for j = 1, 5 do "
           "for k, b in t[j] do if IsInsideBox(b, h) then n = n + 1 end end end end W4P_V[i] = n end "
           "W4P_R = W4P_V[0] * 10 + W4P_V[1] W4P_R2 = W4P_V[2] * 10 + W4P_V[3] "
           "W4P_R3 = (IsInsideBox(vbStartRail, player) and 1 or 0)")
    r = _lua(p, "m6bx", src, ("W4P_R", "W4P_R2", "W4P_R3"))
    r["players"] = xf._players(p)
    return r


# ---------------------------------------------------------------- M9 cp4 (level86_chapter4.lua, 09166)
def m9_info(p):
    """R = rail phase digits: railCam_start set, railCam set, C4 present; R2 = players 1-2, R3 = players 3-4: one digit
    each = inside vHammerBox (1) + vSecondVanBox (2) + vClipBox (4), 8 = not a player (money reads cap at 999)."""
    src = ("W4P_R = 100 * ((railCam_start and 1) or 0) + 10 * ((railCam and 1) or 0) + ((C4 and 1) or 0) "
           "W4P_V = {} for i = 0, 3 do local h = HuGetPlayer(i) local d = 8 if HuIsAPlayer(h) then d = 0 "
           "if IsInsideBox(vHammerBox, h) then d = d + 1 end if IsInsideBox(vSecondVanBox, h) then d = d + 2 end "
           "if IsInsideBox(vClipBox, h) then d = d + 4 end end W4P_V[i] = d end "
           "W4P_R2 = W4P_V[0] * 10 + W4P_V[1] W4P_R3 = W4P_V[2] * 10 + W4P_V[3]")
    r = _lua(p, "m9i", src, ("W4P_R", "W4P_R2", "W4P_R3"))
    r["players"] = xf._players(p)
    return r


def m9_zr2_orig_p3(p):
    """Original C4.ZoomRail2 for player 3 (leave of the type-0 vSecondVanBox): CameraMakeActive(railCam, 0.8, nil, P3)."""
    return _cmp(p, "m9zo", "W4P_PC((W4P_O and W4P_O.zr2) or C4.ZoomRail2, vSecondVanBox, HuGetPlayer(2)) W4P_R = 100")


def m9_zr2_p3(p):
    return _cmp(p, "m9zf", "W4P_PC(C4.ZoomRail2, vSecondVanBox, HuGetPlayer(2)) W4P_R = 100")


def m9_phase2(p):
    """Test only: start the second cage stage directly (C4.StartRailCam, normally the return of the molotov scene)."""
    return _cmp(p, "m9p2", "W4P_PC(C4.StartRailCam) W4P_R = 100")


def m9_follow_p3(p):
    return _cmp(p, "m9fo", "CameraMakeActive(MainCam, 0, nil, HuGetPlayer(2)) W4P_R = 100")


def _lc_has(p, name):
    n = p.read32(LC_N)
    return any(it._cstr(p, LC_LOG + 32 * ((n - 1 - j) & 7), 32) == name for j in range(min(n, 8)))


def god_wait(p, table="ch4", chunk="level3_chase.lua", timeout=120.0):
    """Test only: wait (blocking, up to timeout s) until the chapter table exists in the level's Lua state, then god mode
    for every player (the chase / cage kills standing bots within seconds: run cb6base, GAME OVER 'You got wrecked'
    about 140 polls after the cp4 load)."""
    import time
    t0, n = time.time(), 0
    while time.time() - t0 < timeout:
        n += 1
        if not _lc_has(p, chunk) or not it._player(p, 0)[1]:
            time.sleep(0.3)
            continue
        m0 = xf._money(p, 0)
        r = xf._run(p, f"W4P_R = 0 if {table} then for i = 0, 3 do local h = HuGetPlayer(i) if HuIsAPlayer(h) then "
                       "HuSetGodMode(h, true) W4P_R = W4P_R + 1 end end end InvSetMoney(W4P_R + 500, 1)")
        v = xf._money(p, 0)
        xf._run(p, f"InvSetMoney({m0 if m0 < 500 else 0}, 1)")
        if r.get("done") == 1 and 501 <= v <= 504:
            return {"poll": it._poll(p), "players_god": v - 500, "tries": n, "secs": round(time.time() - t0, 1)}
        time.sleep(0.3)
    return {"poll": it._poll(p), "timeout": True, "tries": n}


def god6(p):
    return god_wait(p, "ch4")


def god9(p):
    return god_wait(p, "C4", "level86_chapter4.lua")


# ---------------------------------------------------------------- actions with the camB rows (fixed versions)
SAVE01 = "W4P_A0 = CameraGetActive(0) W4P_A1 = CameraGetActive(1) "


def chk01(p):
    """R = players 1-2's active cameras unchanged since the last SAVE01 (11 = both unchanged); R2 = view 3 (index 2)
    active camera: 1 = his copy of the last copied locked camera W4P_CC, 2 = that locked camera itself, 0 = other."""
    r = _lua(p, "chk01", "W4P_R = 10 * ((CameraGetActive(0) == W4P_A0 and 1) or 0) + ((CameraGetActive(1) == W4P_A1 and 1) or 0) "
                         "local c = CameraGetActive(2) W4P_R2 = 0 if W4P_CC then if c == W4P_CC then W4P_R2 = 2 end "
                         "if W4BC[W4P_CC] and c == W4BC[W4P_CC][2] then W4P_R2 = 1 end end", ("W4P_R", "W4P_R2"))
    r["cams"] = cams(p)
    return r


def m6_fix_p3(p):
    """EnterFixCam for player 3 at vFixCam[1] (stunt camera FixCam[1], blend 0) with HuIsAlive stubbed to 'partner down'
    (the only case the original runs it) and HuSetSlowMo stubbed (global slow motion). Then chk01: expect R 11, R2 1."""
    return _cmp(p, "m6fx", SAVE01 + "W4P_CC = ch4.FixCam[1] local a, s = HuIsAlive, HuSetSlowMo "
                "HuIsAlive = function(h) return nil end HuSetSlowMo = function(a, b) end "
                "W4P_PC(ch4.EnterFixCam, vFixCam[1], HuGetPlayer(2)) HuIsAlive, HuSetSlowMo = a, s W4P_R = 100")


def m6_fix_orig_p3(p):
    """Same with the original handler (baseline run): expect R2 2 = FixCam[1] itself (the object players 1-2 use)."""
    return m6_fix_p3(p)


def m6_fixexit_p3(p):
    """ExitFixCam for player 3 at vFixCam[1] (blend 0): expect his own rail (render[2] == rail[2])."""
    return _cmp(p, "m6fxx", SAVE01 + "W4P_PC(ch4.ExitFixCam, vFixCam[1], HuGetPlayer(2)) W4P_R = 100")


def m9_zin_p3(p):
    """ZoomInRail for player 3 (vHammerBox enter, stage 1): his copy of LockRailCam2 (blend 0.75; read with chk01)."""
    return _cmp(p, "m9zi", SAVE01 + "W4P_CC = Cameras.LockRailCam2 W4P_PC(C4.ZoomInRail, vHammerBox, HuGetPlayer(2)) W4P_R = 100")


def m9_zout_p3(p):
    """ZoomOutRail for player 3 (vHammerBox leave): his own rail back (or follow camera without a camB rail)."""
    return _cmp(p, "m9zo2", SAVE01 + "W4P_PC(C4.ZoomOutRail, vHammerBox, HuGetPlayer(2)) W4P_R = 100")


def m9_van_p3(p):
    """ZoomVan2 for player 3 (vSecondVanBox enter): his copy of SecondVanCam2 (blend 0.6; read with chk01)."""
    return _cmp(p, "m9zv", SAVE01 + "W4P_CC = SecondVanCam2 W4P_PC(C4.ZoomVan2, vSecondVanBox, HuGetPlayer(2)) W4P_R = 100")


def m9_zr2s_p3(p):
    """ZoomRail2 for player 3 with players 1-2's actives saved first (read with chk01)."""
    return _cmp(p, "m9zr2s", SAVE01 + "W4P_PC(C4.ZoomRail2, vSecondVanBox, HuGetPlayer(2)) W4P_R = 100")


def m9_p2s_p3(p):
    """Player-2 callback run for a player 3 leave (C4.Player2Start(P3, false)): R = 10 * (LockRailCam was the 2P version
    before) + (it still is after). Original: 10 (swapped back to the 1P version); camB: 11."""
    return _lua(p, "m9p2s", "local b = ((Cameras.LockRailCam == LockRailCam_2P) and 1) or 0 "
                            "W4P_PC(C4.Player2Start, HuGetPlayer(2), false) "
                            "W4P_R = 10 * b + (((Cameras.LockRailCam == LockRailCam_2P) and 1) or 0)")


def m9_p2s_fix(p):
    """Test only: put players 1-2's 2P zoom cameras back after m9_p2s_p3 on the original (what Player2Start(h, true) does)."""
    return _lua(p, "m9p2f", "Cameras.LockRailCam = LockRailCam_2P Cameras.LockRailCam2 = LockRailCam2_2P W4P_R = 100")


def m6_startrail(p):
    """Test only: what player 1 entering the type-2 vbStartRail does (ch4.StartRail(box, player)); with level-jump
    starts the intro auto-run does not happen (cb6base2: players 1-2 stay at x -261..-269), so the rail never starts."""
    return _cmp(p, "m6sr", "W4P_PC(ch4.StartRail, vbStartRail, player) W4P_R = 100")


def m6_end(p):
    """Test only: what players 1-2 entering the type-2 vbEnterGallery do at the chase end (ch4.EnterGallery: KillHandlers,
    jump scene, then cp5). camB: players 3-4 get their follow cameras back in KillHandlers."""
    return _cmp(p, "m6end", "W4P_PC(ch4.EnterGallery, vbEnterGallery, player) W4P_R = 100")


# ---------------------------------------------------------------- diagnostics (handles -> objects, error capture)
def luafn(p):
    """Which Lua library functions the game registered: R = floor, format, strbyte (digits); R2 = mod, strlen."""
    return _lua(p, "lfn", "W4P_R = 100 * ((floor and 1) or 0) + 10 * ((format and 1) or 0) + ((strbyte and 1) or 0) "
                          "W4P_R2 = 10 * ((mod and 1) or 0) + ((strlen and 1) or 0)", ("W4P_R", "W4P_R2"))


def _h2o(p, key, expr):
    """Lua handle expression -> (handle, object pointer): the handle is split by subtraction (no math library needed)."""
    r = _lua(p, key, f"local h = {expr} W4P_R = 0 W4P_R2 = 0 W4P_R3 = 0 W4P_R4 = 0 if h then local i = 0 "
                     "while h >= 65536 do h = h - 65536 i = i + 1 end local a = 0 while i >= 100 do i = i - 100 a = a + 1 end "
                     "local b = 0 while h >= 1000 do h = h - 1000 b = b + 1 end W4P_R = a W4P_R2 = i W4P_R3 = b W4P_R4 = h end",
             ("W4P_R", "W4P_R2", "W4P_R3", "W4P_R4"))
    v = r["values"]
    try:
        h = ((v["W4P_R"] * 100 + v["W4P_R2"]) << 16) | (v["W4P_R3"] * 1000 + v["W4P_R4"])
        return {"expr": expr, "handle": hex(h), "obj": hex(it._resolve(p, h)), "poll": r["poll"]}
    except Exception as e:  # noqa: BLE001
        return {"expr": expr, "error": repr(e), "raw": r}


def _blend_tgt(p, v):
    rd = p.read32(RENDER + 4 * v)
    return hex(p.read32(rd + 0x214)) if 0x00100000 <= rd < 0x02000000 and p.read32(rd) == BLEND_VT else hex(rd)


def ident(p, exprs):
    """Object pointers of Lua camera handles vs what each view shows (render, or the blend camera's target)."""
    return {"views": {v: _blend_tgt(p, v) for v in range(4)}, "objs": [_h2o(p, f"id{k}", e) for k, e in enumerate(exprs)]}


def m6_ident(p):
    return ident(p, ["ch4.FixCam[1]", "W4BC and W4BC[ch4.FixCam[1]] and W4BC[ch4.FixCam[1]][2]", "ch4.railCam"])


def m9_ident(p):
    return ident(p, ["Cameras.LockRailCam2", "W4BC and W4BC[Cameras.LockRailCam2] and W4BC[Cameras.LockRailCam2][2]",
                     "SecondVanCam2", "W4BC and W4BC[SecondVanCam2] and W4BC[SecondVanCam2][2]",
                     "Cameras.LockRailCam", "railCam or railCam_start"])


ERRCAP = ("W4P_EM = nil local em = _ERRORMESSAGE _ERRORMESSAGE = function(m) W4P_EM = m end "
          "W4P_NA = 0 W4P_NC = 0 local ba, bc = W4BA, W4BCP "
          "if ba then W4BA = function(c, t, n, h) W4P_NA = W4P_NA + 1 return %ba(c, t, n, h) end end "
          "if bc then W4BCP = function(c, v) W4P_NC = W4P_NC + 1 return %bc(c, v) end end ")
ERRCAP_END = (" _ERRORMESSAGE = em if ba then W4BA = ba end if bc then W4BCP = bc end "
              "W4P_R = 100 * ((W4P_EM and 1) or 0) + 10 * W4P_NC + W4P_NA W4P_R2 = (W4P_EM and strlen and strlen(W4P_EM)) or 0 "
              "for k = 1, 24 do setglobal(\"W4P_E\" .. k, (W4P_EM and strbyte and strbyte(W4P_EM, k)) or 0) end ")
ENAMES = ("W4P_R", "W4P_R2") + tuple(f"W4P_E{k}" for k in range(1, 25))


def _decode(r):
    v = r.get("values", {})
    r["errtext"] = "".join(chr(v.get(f"W4P_E{k}") or 0) for k in range(1, 25) if isinstance(v.get(f"W4P_E{k}"), int) and v.get(f"W4P_E{k}"))
    return r


def m6_fixdiag(p):
    """EnterFixCam for player 3 (stubs as in m6_fix_p3) with an error trap and spies on the camB camera calls:
    R = error? *100 + copies asked *10 + CameraMakeActive calls; R2 = error length; errtext = first 24 characters."""
    r = _cmp(p, "m6fd", ERRCAP + "W4P_CC = ch4.FixCam[1] local a, s = HuIsAlive, HuSetSlowMo "
             "HuIsAlive = function(h) return nil end HuSetSlowMo = function(a, b) end "
             "call(ch4.EnterFixCam, {vFixCam[1], HuGetPlayer(2); n = 2}, \"x\") HuIsAlive, HuSetSlowMo = a, s" + ERRCAP_END, ENAMES)
    return _decode(r)


def m6_topdiag(p):
    """EnterTopRail for player 3 with the same trap (control: expect R 0 = no error, no copies, no CameraMakeActive)."""
    r = _cmp(p, "m6td", ERRCAP + "call(ch4.EnterTopRail, {vTopRail[14], HuGetPlayer(2); n = 2}, \"x\")" + ERRCAP_END, ENAMES)
    return _decode(r)


def _ma(p, key, src, exprs):
    """Views (render or blend target) and 0x000F0800 entries before/after a Lua text; object pointers of exprs."""
    def views():
        return {v: [_blend_tgt(p, v), hex(p.read32(0x000F0800 + 4 * v))] for v in range(4)}
    b = views()
    r = _lua(p, key, src + " W4P_R = 100")
    return {"before": b, "after": views(), "lua": r.get("values"), "poll": r.get("poll"),
            "objs": [_h2o(p, f"{key}o{k}", e) for k, e in enumerate(exprs)]}


def m6_ma_p1_0(p):
    """Test: locked FixCam[2] on player 1's view with blend 0 (does a blend-0 switch replace the blended rail?)."""
    return _ma(p, "ma10", "CameraMakeActive(ch4.FixCam[2], 0, nil, player)", ["ch4.FixCam[2]"])


def m6_ma_p1_rail(p):
    """Test: player 1 back on his rail (as ExitFixCam / StartRail do, blend 0.5)."""
    return _ma(p, "ma1r", "CameraMakeActive(ch4.railCam, 0.5, nil, player)", ["ch4.railCam"])


def m6_ma_p3_0(p):
    """Test: locked FixCam[11] on player 3's view with blend 0."""
    return _ma(p, "ma30", "CameraMakeActive(ch4.FixCam[11], 0, nil, HuGetPlayer(2))", ["ch4.FixCam[11]"])


def m6_ma_p3_01(p):
    """Test: locked FixCam[11] on player 3's view with blend 0.1."""
    return _ma(p, "ma31", "CameraMakeActive(ch4.FixCam[11], 0.1, nil, HuGetPlayer(2))", ["ch4.FixCam[11]"])


def m6_ma_p3_rail(p):
    return _ma(p, "ma3r", "CameraMakeActive(ch4.railCam, 0.5, nil, HuGetPlayer(2))", ["ch4.railCam"])


def m9_zin_p1(p):
    """2-player regression: ZoomInRail for player 1 (original branch: LockRailCam on view 0, blend 0.75)."""
    return _ma(p, "m9zi1", "W4P_PC(C4.ZoomInRail, vHammerBox, player)", ["Cameras.LockRailCam", "railCam_start"])


def m9_zout_p1(p):
    """2-player regression: ZoomOutRail for player 1 (rail back, blend 0.75)."""
    return _ma(p, "m9zo1", "W4P_PC(C4.ZoomOutRail, vHammerBox, player)", ["railCam_start"])


def m6_top_p1(p):
    """2-player regression: EnterTopRail for player 1 (index 0 only: rail 0 framing k1 20)."""
    return _cmp(p, "m6t1", "W4P_PC(ch4.EnterTopRail, vTopRail[14], player) W4P_R = 100")


# ---------------------------------------------------------------- round 2 probes (cb6rows2 / cb9rows2)
def m6_fix11_p3(p):
    """EnterFixCam for player 3 at vFixCam[11] (stunt camera FixCam[11], blend 1: the stunt boxes with blend 0 never
    replace a blended rail, cb6base3 m6_ma_p1_0), HuIsAlive -> 'partner down', HuSetSlowMo stubbed."""
    return _ma(p, "m6f11", "local a, s = HuIsAlive, HuSetSlowMo HuIsAlive = function(h) return nil end "
               "HuSetSlowMo = function(a, b) end W4P_PC(ch4.EnterFixCam, vFixCam[11], HuGetPlayer(2)) "
               "HuIsAlive, HuSetSlowMo = a, s",
               ["ch4.FixCam[11]", "W4BC and W4BC[ch4.FixCam[11]] and W4BC[ch4.FixCam[11]][2]", "ch4.railCam"])


def m6_fixexit11_p3(p):
    """ExitFixCam for player 3 at vFixCam[11] (blend 1): his own rail back."""
    return _ma(p, "m6x11", "W4P_PC(ch4.ExitFixCam, vFixCam[11], HuGetPlayer(2))", ["ch4.railCam"])


def m6_exit_norail_p3(p):
    """Hazard path: ExitFixCam for a player 3 without a camB rail (W4BR[2] cleared for the test): his follow camera,
    never the chase rail object (the 500/250 ms tick then gives him his rail again)."""
    return _ma(p, "m6xn", "W4BR[2] = nil W4P_PC(ch4.ExitFixCam, vFixCam[11], HuGetPlayer(2))", ["MainCam", "ch4.railCam"])


def m9_clip_p3(p):
    """Near-plane box (vClipBox enter = SetNearPlaneOut) for player 3: R = CameraSetClipping calls *10 + (1 if the
    call was on players 1-2's railCam). Original: 11 (player 1's rail clipped); camB: 0."""
    return _lua(p, "m9cl", "W4P_N = 0 W4P_X = 0 local o = CameraSetClipping CameraSetClipping = function(c, a, b) "
                           "W4P_N = W4P_N + 1 if c == railCam then W4P_X = 1 end end "
                           "W4P_PC(SetNearPlaneOut, vClipBox, HuGetPlayer(2)) CameraSetClipping = o W4P_R = 10 * W4P_N + W4P_X")


def m9_zr2_norail_p3(p):
    """Hazard path: ZoomRail2 for a player 3 without a camB rail (W4BR[2] cleared): his follow camera, never railCam."""
    return _ma(p, "m9zn", "W4BR[2] = nil W4P_PC(C4.ZoomRail2, vSecondVanBox, HuGetPlayer(2))", ["MainCam", "railCam"])


# ---------------------------------------------------------------- TLB investigation (cb9rows2: 50 TLB misses at
# pc 0x00356E08 addr 0x3C888888 about 20-40 polls after m9_zout_p3)
def _zz(p, key, fn, who):
    return _ma(p, key, f"W4P_PC(C4.{fn}, vHammerBox, {who})", ["railCam_start"])


def m9_zin_p2(p):
    return _zz(p, "m9zi2", "ZoomInRail", "player2")


def m9_zout_p2(p):
    return _zz(p, "m9zo2b", "ZoomOutRail", "player2")


def m9_zin_p4(p):
    return _zz(p, "m9zi4", "ZoomInRail", "HuGetPlayer(3)")


def m9_zout_p4(p):
    return _zz(p, "m9zo4", "ZoomOutRail", "HuGetPlayer(3)")


def m9b_rail_p3(p):
    """Baseline (no camB): player 3's view straight onto his rail copy (blend 0), as camB's stage tick does."""
    return _ma(p, "m9br3", "CameraMakeActive(railCam_start, 0, nil, HuGetPlayer(2))", ["railCam_start"])


def m9b_lock_p3(p):
    """Baseline (no camB): a new locked camera with LockRailCam2_2P's arguments on player 3's view, blend 0.75 (what
    camB's copy does)."""
    return _ma(p, "m9bl3", "W4P_LC = CameraCreateLocked(\"LockRailCam2\", {30.82, 54.029, 6.706}, 53, -108.33504486, "
                           "-17.58205223, 0, 2, 70) CameraMakeActive(W4P_LC, 0.75, nil, HuGetPlayer(2))", ["W4P_LC"])


def m9b_back_p3(p):
    """Baseline (no camB): player 3's rail back with blend 0.75 (what ZoomOutRail does for player2)."""
    return _ma(p, "m9bb3", "CameraMakeActive(railCam_start, 0.75, nil, HuGetPlayer(2))", ["railCam_start"])

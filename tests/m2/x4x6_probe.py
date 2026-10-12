"""X4 teleport follow and X6 Lua runner tests (docs/research/m6_x4_x6.md section 4).

Used by nav_probe.py --probe x4x6_probe:<function>:<poll> in the standard Mission 13 four-player run (level jump to
level9 cp1, players 3-4 join by Start from poll 7000). SINGLE-PC, one instance, scripted bots, test only:
- Lua source strings are written over PINE into the test buffer 0x000E7C00-0x000E7EFF (free low RAM, not in the pnach);
- LUARUN (0x000E79A0, group [warriors-4p missions]) is called on the game thread through the test-call mailbox
  (group [warriors-4p test call]; same writes and done-flag wait as inv_tests._call);
- X4 is switched off/on for the control step by writing X4_ON (0x000E7980, a startup-only data word).
Teleports are issued as Lua (TeleportToFlag / Teleport), so they go through the game's own bindings, where X4 hooks.
Function names are OUR labels (the ELF is stripped). Static addresses, build SLUS-21215 v1.03.
"""
import inv_tests as it

SCRIPT_MGR = 0x00512B04          # ScriptLua object pointer (FUN_00356390); lua_State at object+4 (FUN_003564D8)
LUARUN = 0x000E79A0              # LUARUN(source, name) -> lua_dobuffer status
X4_ON, X4_DIST, X4_N = 0x000E7980, 0x000E7984, 0x000E7988
BUF = 0x000E7C00                 # test-only Lua string buffer (0x300 bytes)
CODE = {"x4_teleport_hook": (0x0036CC58, 0x0C039E08), "x4_flag_hook": (0x0036CDC0 + 0x74, 0x0C039E0B),
        "x4f_first_word": (0x000E7870, 0x27BDFFC0), "luarun_first_word": (LUARUN, 0x27BDFFF0),
        "test_call": (0x00158CD0, 0x0C03C000)}
_DONE = {}


def _money(p, slot):
    return it._s32(p.read32(it._count_addr(it._gm(p), slot, 2)))


def _players(p):
    gm = it._gm(p)
    n = it._s16(p.read32(gm + 0x224))
    out = {}
    for i in range(4):
        h, o = it._player(p, i)
        out[i + 1] = {"handle": hex(h), "obj": hex(o), "pos": it._pos(p, o) if o else None}
    p1 = out[1]["pos"]
    for i in range(2, 5):
        if p1 and out[i]["pos"]:
            out[i]["dist_to_p1"] = it._dist(p1, out[i]["pos"])
    return n, out


def _lua(p, key, src):
    """Run Lua source once per nav_probe process (a retried probe does not repeat it)."""
    if key in _DONE:
        return dict(_DONE[key], repeated=True)
    data = src.encode("latin-1") + b"\0"
    assert len(data) <= 0x300
    data += b"\0" * (-len(data) % 4)
    p.batch_write32([(BUF + i, int.from_bytes(data[i:i + 4], "little")) for i in range(0, len(data), 4)])
    r = it._call(p, LUARUN, BUF, 0)
    r["src"] = src
    _DONE[key] = r
    return r


def state(p):
    mgr = p.read32(SCRIPT_MGR)
    n, pl = _players(p)
    return {"poll": it._poll(p), "gm": it._gmfields(p), "code": {k: p.read32(a) == v for k, (a, v) in CODE.items()},
            "script_mgr": hex(mgr), "lua_state": hex(p.read32(mgr + 4)) if mgr else None,
            "mgr_vtable": hex(p.read32(mgr)) if mgr else None,
            "x4_on": p.read32(X4_ON), "x4_dist": it._f(p.read32(X4_DIST)), "x4_n": p.read32(X4_N),
            "count": n, "players": pl, "money": [_money(p, s) for s in range(4)], "cinematic_410": p.read32(it._gm(p) + 0x410)}


# ---------------------------------------------------------------- X6: Lua runner
def lua_set(p):
    """Defines a global in the level's Lua state; nothing visible yet (status only)."""
    before = [_money(p, s) for s in range(4)]
    r = _lua(p, "set", "W4P_T = 432")
    return {"poll": it._poll(p), "call": r, "money_before": before, "money_after": [_money(p, s) for s in range(4)]}


def lua_get(p):
    """Reads the global back in a second chunk and makes it visible as player 1's money (InvSetMoney binding;
    money is capped at 999, run x4x6a used 4321 and saw 999, so the values here stay below it)."""
    before = [_money(p, s) for s in range(4)]
    r = _lua(p, "get", "InvSetMoney(W4P_T + 1, 1)")
    return {"poll": it._poll(p), "call": r, "money_before": before, "money_after": [_money(p, s) for s in range(4)],
            "expect_p1": 433}


def lua_level(p):
    """Uses the mission's own globals (player, player2 set by the level9 script): proves it is the level's state."""
    before = [_money(p, s) for s in range(4)]
    r = _lua(p, "level", "if HuIsAPlayer(player) and HuIsAPlayer(player2) then InvSetMoney(440, 1) else InvSetMoney(441, 1) end")
    return {"poll": it._poll(p), "call": r, "money_before": before, "money_after": [_money(p, s) for s in range(4)],
            "expect_p1": 440}


def lua_err(p):
    """A syntax error: non-zero status, the game goes on (_ERRORMESSAGE/_ALERT are no-ops 0x00357BA8/0x00357BB0)."""
    r = _lua(p, "err", "this is not lua (")
    r2 = _lua(p, "restore", "InvSetMoney(0, 1)")
    return {"poll": it._poll(p), "call": r, "restore": r2, "money_after": [_money(p, s) for s in range(4)]}


# ---------------------------------------------------------------- X4: teleport follow
def _tp(p, key, src, x4_on):
    if key in _DONE:
        return dict(_DONE[key], repeated=True)
    p.write32(X4_ON, x4_on)
    n0 = p.read32(X4_N)
    _, before = _players(p)
    r = _lua(p, key + "_lua", src)
    _, after = _players(p)
    res = {"poll": it._poll(p), "x4_on": x4_on, "call": r, "x4_n_before": n0, "x4_n_after": p.read32(X4_N),
           "before": before, "after": after}
    p.write32(X4_ON, 1)
    _DONE[key] = res
    return res


def tp_off(p):
    """Control: X4 off, script-style TeleportToFlag of player 1 ~100 units away -> players 3-4 stay behind."""
    return _tp(p, "tp_off", "TeleportToFlag(player, fPScout[2], -1)", 0)


def tp_on(p):
    """X4 on, Teleport (vector) of player 1 to a known open spot (inv_t2c target) -> players 3-4 follow."""
    return _tp(p, "tp_on", "Teleport(player, {23.3, 319.6, 1.4}, -1)", 1)


def tp_near(p):
    """X4 on, player 1 moved 2 units: players 3-4 are within 15 units -> not moved (X4_N unchanged)."""
    return _tp(p, "tp_near", "Teleport(player, {25.3, 319.6, 1.4}, -1)", 1)


def tp_p2(p):
    """X4 on, TeleportToFlag of player 2 only: players 3-4 near player 1 -> not moved; player 2 moved."""
    return _tp(p, "tp_p2", "TeleportToFlag(player2, fPScout[1], -1)", 1)


def tp_flag(p):
    """X4 on, TeleportToFlag of player 1 (the TFW hook) ~66 units away -> players 3-4 follow."""
    return _tp(p, "tp_flag", "TeleportToFlag(player, fPScout[1], -1)", 1)


# ---------------------------------------------------------------- X6: chunk hook LUACH (test2 pnach) and guards
LC_RUNS, LC_N, LC_LOG, LC_TAB = 0x000E7AF8, 0x000E7AFC, 0x000E7B00, 0x000E7F00


def _wstr(p, addr, s):
    data = s.encode("latin-1") + b"\0"
    data += b"\0" * (-len(data) % 4)
    p.batch_write32([(addr + i, int.from_bytes(data[i:i + 4], "little")) for i in range(0, len(data), 4)])


def lc_setup(p):
    """Before the level jump: table row 0 = every chunk -> W4P_AUTO += 1; row 1 = chunk "@level9_chap1_radio.lua"
    (M13 cp1 chapter, preLoadFile(Chapter[1]) 09229:2076/3452) -> W4P_CH1 += 1; row 2 = end."""
    if "lc_setup" in _DONE:
        return dict(_DONE["lc_setup"], repeated=True)
    _wstr(p, 0x000E7F80, "W4P_AUTO = (W4P_AUTO or 0) + 1")
    _wstr(p, 0x000E7FC0, "W4P_CH1 = (W4P_CH1 or 0) + 1")
    _wstr(p, 0x000E7FE0, "@level9_chap1_radio.lua")
    p.batch_write32([(LC_TAB + 0x10, 0), (LC_TAB + 0x14, 0), (LC_TAB + 0x08, 0x000E7FE0), (LC_TAB + 0x0C, 0x000E7FC0),
                     (LC_TAB + 0x00, 0), (LC_TAB + 0x04, 0x000E7F80)])
    r = {"poll": it._poll(p), "lc_n": p.read32(LC_N), "lc_runs": p.read32(LC_RUNS),
         "tab": [hex(p.read32(LC_TAB + 4 * k)) for k in range(6)]}
    _DONE["lc_setup"] = r
    return r


def lc_read(p):
    """Chunk names logged by LUACH and the counters the auto-run sources kept in this level's Lua state."""
    n = p.read32(LC_N)
    names = {k: it._cstr(p, LC_LOG + 32 * k, 32) for k in range(8)}
    order = [names[(n - 1 - j) & 7] for j in range(min(n, 8))]  # newest first
    r = _lua(p, "lc_read", "InvSetMoney((W4P_AUTO or 0) * 10 + (W4P_CH1 or 0), 1)")
    m = _money(p, 0)
    r2 = _lua(p, "lc_restore", "InvSetMoney(0, 1)")
    return {"poll": it._poll(p), "lc_n": n, "lc_runs": p.read32(LC_RUNS), "names_newest_first": order, "call": r,
            "p1_money_auto_x10_plus_ch1": m, "restore": r2}


GUARD = ("function W4P_G34(f) return function(a0, a1) if HuIsAPlayer(a1) and a1 ~= player and a1 ~= player2 then "
         "return end return %f(a0, a1) end end ")


def g1(p):
    """Guard wrapper (Lua 4.0 upvalue %f) around a test function; called for player 1 -> runs (money 111)."""
    r = _lua(p, "g1", GUARD + "function W4P_F(a0, a1) InvSetMoney(a0, 1) end W4P_F = W4P_G34(W4P_F) W4P_F(111, player)")
    return {"poll": it._poll(p), "call": r, "money": [_money(p, s) for s in range(4)], "expect_p1": 111}


def g2(p):
    """Same wrapper called for player 3 (HuGetPlayer(2)) -> blocked (money stays 111)."""
    r = _lua(p, "g2", "W4P_F(222, HuGetPlayer(2))")
    return {"poll": it._poll(p), "call": r, "money": [_money(p, s) for s in range(4)], "expect_p1": 111}


def g3(p):
    """HuGetPlayer(2) is a human player other than player/player2 (why g2 was blocked) -> 333."""
    r = _lua(p, "g3", "local h = HuGetPlayer(2) if HuIsAPlayer(h) and h ~= player and h ~= player2 then "
                      "InvSetMoney(333, 1) else InvSetMoney(334, 1) end")
    return {"poll": it._poll(p), "call": r, "money": [_money(p, s) for s in range(4)], "expect_p1": 333}


def g4(p):
    """M13 camera guard on the real handler EnterGraveTrain (09229 main_99, volume handler by name): a call for
    player 3 must not build the subway rail camera (global subrail stays nil) -> 444."""
    r = _lua(p, "g4", "W4P_EGT = EnterGraveTrain EnterGraveTrain = W4P_G34(EnterGraveTrain) subrail = nil "
                      "EnterGraveTrain(0, HuGetPlayer(2)) if subrail == nil then InvSetMoney(444, 1) else InvSetMoney(445, 1) end")
    return {"poll": it._poll(p), "call": r, "money": [_money(p, s) for s in range(4)], "expect_p1": 444,
            "render_cams": [hex(p.read32(0x000F0810 + 4 * i)) for i in range(4)]}


def g5(p):
    """Control, last: the original handler for player 3 builds the rail camera and makes it active with player 3's
    human (the hijack the guard prevents) -> 447. Screenshots after this poll show the effect on the views."""
    r = _lua(p, "g5", "subrail = nil W4P_EGT(0, HuGetPlayer(2)) if subrail == nil then InvSetMoney(446, 1) else InvSetMoney(447, 1) end")
    return {"poll": it._poll(p), "call": r, "money": [_money(p, s) for s in range(4)], "expect_p1": 447,
            "render_cams": [hex(p.read32(0x000F0810 + 4 * i)) for i in range(4)]}


def nat_arrive(p):
    """Natural script teleport: X4 off, player 1 put on fArrive (vbCutscene2, ch1.ArriveObj 09720:127) -> trainyard
    scene -> ch1.StartTheLevel (09720 main_7): Teleport(player, Pos(player), 147), TeleportToFlag(fox, ...),
    HuDelete(fox). X4 is switched on again right after the synthetic teleport, so only the script's own teleport
    can pull players 3-4."""
    return _tp(p, "nat_arrive", "TeleportToFlag(player, fArrive, -1)", 0)


# ---------------------------------------------------------------- run x4x6c: rows keyed by the real chunk names
# Run x4x6b logged the names DoBuffer gets: "level9.lua", "level9_chap1_radio.lua", "global.lua", "config_normal.lua"
# (no "@": the disc build formats "%s.lua" without a "/", so DoFile's "/" -> "@" step finds nothing).
def lc_setup2(p):
    """Rows: 0 every chunk -> W4P_AUTO += 1; 1 "level9_chap1_radio.lua" -> W4P_CH1 += 1; 2 "level9.lua" -> the M13
    camera guard (EnterGraveTrain wrapped, the delivery a real fix would use); 3 end."""
    if "lc_setup2" in _DONE:
        return dict(_DONE["lc_setup2"], repeated=True)
    _wstr(p, 0x000E7E00, GUARD + "EnterGraveTrain = W4P_G34(EnterGraveTrain)")  # away from the LUARUN buffer
    _wstr(p, 0x000E7F80, "W4P_AUTO = (W4P_AUTO or 0) + 1")
    _wstr(p, 0x000E7FA0, "W4P_CH1 = (W4P_CH1 or 0) + 1")
    _wstr(p, 0x000E7FC0, "level9_chap1_radio.lua")
    _wstr(p, 0x000E7FE0, "level9.lua")
    p.batch_write32([(LC_TAB + 0x18, 0), (LC_TAB + 0x1C, 0),
                     (LC_TAB + 0x10, 0x000E7FE0), (LC_TAB + 0x14, 0x000E7E00),
                     (LC_TAB + 0x08, 0x000E7FC0), (LC_TAB + 0x0C, 0x000E7FA0),
                     (LC_TAB + 0x00, 0), (LC_TAB + 0x04, 0x000E7F80)])
    r = {"poll": it._poll(p), "lc_n": p.read32(LC_N), "lc_runs": p.read32(LC_RUNS),
         "tab": [hex(p.read32(LC_TAB + 4 * k)) for k in range(8)]}
    _DONE["lc_setup2"] = r
    return r


def lc_read2(p):
    """W4P_AUTO * 10 + W4P_CH1 (expected 41: 4 chunks in the level9 state, the chapter row once)."""
    n = p.read32(LC_N)
    names = {k: it._cstr(p, LC_LOG + 32 * k, 32) for k in range(8)}
    order = [names[(n - 1 - j) & 7] for j in range(min(n, 8))]
    r = _lua(p, "lc_read2", "InvSetMoney((W4P_AUTO or 0) * 10 + (W4P_CH1 or 0), 1)")
    m = _money(p, 0)
    return {"poll": it._poll(p), "lc_n": n, "lc_runs": p.read32(LC_RUNS), "names_newest_first": order, "call": r,
            "p1_money_auto_x10_plus_ch1": m, "expect": 41}


def gauto_p3(p):
    """The guard came from the table row at the level9.lua load (no wrapping here): player 3 -> blocked -> 444."""
    r = _lua(p, "gauto_p3", "subrail = nil EnterGraveTrain(0, HuGetPlayer(2)) if subrail == nil then "
                            "InvSetMoney(444, 1) else InvSetMoney(445, 1) end")
    return {"poll": it._poll(p), "call": r, "money": [_money(p, s) for s in range(4)], "expect_p1": 444,
            "render_cams": [hex(p.read32(0x000F0810 + 4 * i)) for i in range(4)]}


def gauto_p1(p):
    """Positive control, last: the guarded handler still works for player 1 (rail camera built) -> 449."""
    r = _lua(p, "gauto_p1", "subrail = nil EnterGraveTrain(0, player) if subrail == nil then "
                            "InvSetMoney(448, 1) else InvSetMoney(449, 1) end")
    return {"poll": it._poll(p), "call": r, "money": [_money(p, s) for s in range(4)], "expect_p1": 449,
            "render_cams": [hex(p.read32(0x000F0810 + 4 * i)) for i in range(4)]}


# ---------------------------------------------------------------- run x4x6d: the pnach's own table (no PINE writes)
def lc_log(p):
    """LUACH counters, log and table as the pnach set them (missions.txt: row 0 "level9.lua" -> M13 guard)."""
    n = p.read32(LC_N)
    names = {k: it._cstr(p, LC_LOG + 32 * k, 32) for k in range(8)}
    return {"poll": it._poll(p), "lc_n": n, "lc_runs": p.read32(LC_RUNS),
            "names_newest_first": [names[(n - 1 - j) & 7] for j in range(min(n, 8))],
            "tab": [hex(p.read32(LC_TAB + 4 * k)) for k in range(4)], "row0_name": it._cstr(p, 0x000E7F40, 16),
            "row0_source": it._cstr(p, 0x000E7E00, 200)}

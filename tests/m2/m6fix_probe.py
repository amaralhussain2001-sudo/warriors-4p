"""Probes for the M6 mission fixes X1/X2/X3/X5/X8 (docs/research/m6_fixes.md, design m6_missions.md section 2).

Used by nav_probe.py --probe m6fix_probe:<function>:<poll> (one instance, SINGLE-PC, scripted input, test only).
Read-only functions: snap, squad. Test aids (PINE writes / test-call mailbox of "warriors-4p test call", never in
sessions): x2_fox_row_off, tele_cut2, gang_delete_*, x5_reset, x5_leaveloop. patch=2 code words are re-applied by
PCSX2 every frame, so code changes for A/B tests are made in pnach variants (local/m6), not by PINE.
Static addresses, SLUS-21215 v1.03; function names are OUR labels (stripped ELF).
"""
import struct
import time

import inv_tests as T
import sp_probe as S

GM_PTR = 0x0051489C
POLL = 0x000F0500
BRAINS, BRAIN_SIZE = 0x006D53F0, 0x2F0     # FUN_0021D408
OBJ_TABLE = 0x006EBD38
GANGS, GANG_SIZE = 0x005E6E30, 0xB10       # FUN_0016C388
X2_TABLE = 0x000E1E00                      # [4p spawn] X2 do-not-take table
X2_HOOK = 0x000E1B44                       # PX's picker call (X2: jal 0x000E1C60)
PIN_ID = 0x000E1C00
SCRATCH = 0x000E5D00                       # test scratch (free; also used by inv_t2b/inv_t2c)
TELEPORT = 0x00385BB8                      # Lua Teleport core (handle, float[3]*, -1)
GANG_CREATE = 0x0016A1C8                   # GangCreate core (type, name) -> gang id
GANG_ADD = 0x0016A3F8                      # GangAddMember core (gang id, 0, handle)
GANG_DELETE = 0x0016A1E8                   # GangDelete/RemoveGang core (gang id) -> FUN_0016D068 (X1 hook 0x0016D0C0)
UPDATE_JOIN = 0x0041A460                   # (GameMgr, pad); pad -1 + 2P flag off = the game's leave loop
SET_2P = 0x00419AC0                        # (GameMgr, flag): 2-player flag GameMgr+0x56EC
X5_SKIP, X5_EV = 0x000E12B4, 0x000E12AC    # X5EV paths (spawn_leave.txt)
X5_CNT_EV, X5_CNT_SKIP = 0x000E5D38, 0x000E5D3C


def _s8(v):
    return v - 256 if v & 0x80 else v


def _s16(v):
    v &= 0xFFFF
    return v - 0x10000 if v & 0x8000 else v


def _f2u(v):
    return struct.unpack("<I", struct.pack("<f", v))[0]


def _level(p):
    gm = p.read32(GM_PTR)
    idx = T._r16(p, gm + 0x56DC)
    return p.read32(gm + 0x14D4 + idx * 0x84 + 4), T._r16(p, gm + 0x33A)


def _hinfo(p, o):
    """Identity of a human: char ids, priority, player index, gang (object, id, type), downed/arrested flags."""
    if not o:
        return None
    b = T._bidx(p, o)
    gang = p.read32(BRAINS + b * BRAIN_SIZE + 0x20C) if 0 <= b < 0x200 else 0
    st = p.read32(o + 0xD4)
    fl = p.batch_read64([st])[0] if 0x00100000 <= st < 0x02000000 else 0
    gid = _s16(p.read32(gang + 0x30)) if gang else None
    return {"obj": hex(o), "char_d0": p.read32(o + 0xD0), "base_cc": p.read32(o + 0xCC),
            "prio_1b1": T._r8(p, o + 0x1B1), "pidx_1b0": _s8(T._r8(p, o + 0x1B0)),
            "name_80": T._cstr(p, o + 0x80, 16), "gang": hex(gang), "gang_id": gid,
            "gang_type": p.read32(gang + 0x2C) if gang else None, "flags": hex(fl),
            "downed": bool(fl & 0x40000), "arrested": bool(fl & 0x20000), "hud_slot": T._s32(p.read32(o + 0x380))}


def _gang_members(p, gang):
    out = []
    for i in range(16):
        h = p.read32(gang + 0x48 + 4 * i)
        o = T._resolve(p, h)
        if o:
            out.append(dict(_hinfo(p, o), slot=i, handle=hex(h)))
    return out


def squad(p):
    """Player 1's gang members and every AI human in a type-0 gang (what the original picker's fallback scans), plus
    what the original PickJoinCompanion(gang of player 1, 0) would return now (emulated, FUN_0022A770 rules)."""
    gm = p.read32(GM_PTR)
    h1, o1 = T._player(p, 0)
    out = {"poll": T._poll(p), "level_cp": _level(p)}
    if not o1:
        return dict(out, error="no player 1")
    gang = p.read32(BRAINS + T._bidx(p, o1) * BRAIN_SIZE + 0x20C)
    mem = _gang_members(p, gang)
    out["p1_gang"] = hex(gang)
    out["members"] = mem
    ai = []
    for slot in range(60):
        o = p.read32(OBJ_TABLE + 8 * slot)
        if not 0x00100000 <= o < 0x02000000:
            continue
        info = _hinfo(p, o)
        if info["pidx_1b0"] == -1 and info["gang_type"] == 0 and info["gang"] != "0x0":
            ai.append(dict(info, objslot=slot))
    out["ai_type0_humans"] = ai

    def pick(cands):
        first = best = None
        for c in cands:
            if first is None:
                first = c
            if c["prio_1b1"] and (best is None or _s8(c["prio_1b1"]) < _s8(best["prio_1b1"])):
                best = c
        return best or first
    gang_ai = [m for m in mem if m["pidx_1b0"] == -1]
    if gang_ai:
        out["original_pick"] = dict(pick(gang_ai), source="gang")
    elif out["level_cp"][0] != 99 and p.read32(gm + 0x158) == 0:
        w = pick(ai)
        out["original_pick"] = dict(w, source="fallback") if w else None
    else:
        out["original_pick"] = None
    return out


def snap(p):
    """Players (identity, gang, pad), pad owners, views, cameras, count, scenes (sp_probe.snap) + level/cp, PIN_ID."""
    out = S.snap(p)
    out["level_cp"] = _level(p)
    out["pin_id"] = p.read32(PIN_ID)
    out["x2_table"] = [hex(p.read32(X2_TABLE + 4 * k)) for k in range(4)]
    out["x2_hook"] = hex(p.read32(X2_HOOK))
    ids = []
    for i in range(4):
        h, o = T._player(p, i)
        ids.append(dict(_hinfo(p, o), handle=hex(h)) if o else {"handle": hex(h)})
    out["ids"] = ids
    out["x5_counts"] = {"event": p.read32(X5_CNT_EV), "skip": p.read32(X5_CNT_SKIP)}
    return out


def x2_fox_row_off(p):
    """Test aid for the X1 run: turn the level9 Fox row of the X2 table into a level99 row (no effect), so player 3
    takes Fox as in the M2 runs and the script's HuDelete(fox) hits a player."""
    before = p.read32(X2_TABLE + 8)
    p.write32(X2_TABLE + 8, (before & 0xFFFFFF00) | 0x63)
    return {"poll": T._poll(p), "row3_before": hex(before), "row3_after": hex(p.read32(X2_TABLE + 8))}


def _tele_p1(p, xyz):
    p.batch_write32([(SCRATCH + 4 * k, _f2u(v)) for k, v in enumerate(xyz)])
    h, o = T._player(p, 0)
    before = T._pos(p, o) if o else None
    call = T._call(p, TELEPORT, h, SCRATCH, 0xFFFFFFFF)
    time.sleep(0.3)
    return {"poll": T._poll(p), "before": before, "call": call, "after": T._pos(p, o) if o else None}


def tele_cut2(p):
    """Mission 13 ch1: player 1 to the vbCutscene2 position (09229:1633 AddVolumeBox("vbCutscene2", 2, {53, 306, 1.4},
    {14, 11, 7})); entering it completes ch1.ArriveObj (09720:127, any player, 04106 main_142) -> ch1.SecondCutscene
    (trainyard scene) -> ch1.StartTheLevel -> HuDelete(fox) (09720:148-158). Lua Teleport core FUN_00385BB8(handle,
    float[3]*, -1) through the test-call mailbox."""
    return _tele_p1(p, (53.0, 306.0, 1.4))


def tele_arrive(p):
    """Player 1 to the objective flag fArrive (09229:1652 AddFlag("fArrive", {64, 314.3, 2.9}))."""
    return _tele_p1(p, (64.0, 314.3, 2.9))


def _new_gang(p, name):
    raw = name.encode() + b"\0" * (8 - len(name) % 4)
    p.batch_write32([(SCRATCH + 0x80 + k, struct.unpack_from("<I", raw.ljust(16, b"\0"), k)[0]) for k in range(0, 16, 4)])
    return T._call(p, GANG_CREATE, 0, SCRATCH + 0x80, 0, 0)


def gang_delete_test(p, index=3):
    """X1 gang path: a new type-0 gang (GangCreate core), the human of player index `index` moved into it
    (GangAddMember core), then GangDelete core FUN_0016A1E8 -> FUN_0016D068 -> X1G (0x0016D0C0)."""
    out = {"poll": T._poll(p), "before": snap(p)}
    h, o = T._player(p, index)
    out["target"] = dict(_hinfo(p, o), handle=hex(h)) if o else {"handle": hex(h)}
    if not o:
        return dict(out, error=f"no player index {index}")
    c = _new_gang(p, "W4PTEST")
    out["create"] = c
    gid = c["v0"]
    if not 0 <= gid < 32:
        return dict(out, error="GangCreate failed")
    out["add"] = T._call(p, GANG_ADD, gid, 0, h)
    out["moved"] = _hinfo(p, o)
    out["gang_members"] = _gang_members(p, GANGS + gid * GANG_SIZE)
    out["delete"] = T._call(p, GANG_DELETE, gid)
    time.sleep(0.5)
    out["handle_resolves_after"] = bool(T._resolve(p, h))
    out["after"] = snap(p)
    return out


def gang_delete_p4(p):
    return gang_delete_test(p, 3)


def gang_delete_p3(p):
    return gang_delete_test(p, 2)


def x5_reset(p):
    """Zero the TEST-ONLY X5 counters (the counting caves are in the test pnach variant local/m6/dev_x5cnt.pnach:
    x5_ev -> 0x000E5D40 counts at 0x000E5D38 then j 0x0041B148; x5_skip -> 0x000E5D60 counts at 0x000E5D3C)."""
    p.batch_write32([(X5_CNT_EV, 0), (X5_CNT_SKIP, 0)])
    return {"poll": T._poll(p), "x5_ev": hex(p.read32(X5_EV)), "x5_skip": hex(p.read32(X5_SKIP))}


def x5_leaveloop(p):
    """The game's own drop-out ("continue in 1 player mode", FUN_001DF3A8): 2-player flag off, UpdateJoin(GM, -1),
    which runs the leave loop 0x0041A7D8-0x0041A890 for every index >= 1 (LEAVEHOOK -> X5EV)."""
    gm = p.read32(GM_PTR)
    out = {"poll": T._poll(p), "before": snap(p)}
    out["flag_off"] = T._call(p, SET_2P, gm, 0)
    out["update_join"] = T._call(p, UPDATE_JOIN, gm, 0xFFFFFFFF)
    time.sleep(0.5)
    out["after"] = snap(p)
    out["counts"] = {"event": p.read32(X5_CNT_EV), "skip": p.read32(X5_CNT_SKIP)}
    return out


def x8_read(p):
    """After t7_setup (money 10/20/30/40) and t7_launch (FUN_0015D420(4)): bank, live counts and checkpoint copy of
    slots 2-3 (copy at 0x000E4020 + slot*0x3F4 + item*0x2C with [4p inventory])."""
    gm = p.read32(GM_PTR)
    snap7 = T._SNAP.get("t7", {})
    bank = p.read32(gm + 0x480)
    return {"poll": T._poll(p), "gm": T._gmfields(p), "bank0": snap7.get("bank0"), "bank": bank,
            "bank_delta": (bank - snap7["bank0"]) & 0xFFFFFFFF if "bank0" in snap7 else None,
            "counts": T._all_counts(p), "copies": T._copies(p),
            "x8_cave": [hex(p.read32(0x000E5000 + 4 * k)) for k in range(11)], "hook_15d3f4": hex(p.read32(0x0015D3F4))}


def brief(p):
    """Light snapshot: count, players (identity, gang), pad owners, views, level/cp, mode top, GameMgr+0x14C."""
    gm = p.read32(GM_PTR)
    top = p.read32(S.MODE_TOP)
    ids = []
    for i in range(4):
        h, o = T._player(p, i)
        if o:
            x = _hinfo(p, o)
            ids.append([i, x["char_d0"], x["prio_1b1"], x["pidx_1b0"], x["name_80"], x["gang_id"], x["hud_slot"], hex(h)])
        else:
            ids.append([i, hex(h)])
    return {"poll": T._poll(p), "count": _s16(p.read32(gm + 0x224)), "ids": ids, "pads": T._pads(p),
            "views": p.read32(0x0050B198), "level_cp": _level(p), "gm_14c": p.read32(gm + 0x14C),
            "mode_top": hex(p.read32(S.MODE_STACK + 4 * top)) if top < 8 else top, "cine_410": T._r8(p, gm + 0x410),
            "join_56e8": p.read32(gm + 0x56E8), "dropin_456": hex(T._r16(p, gm + 0x456)), "pin_id": p.read32(PIN_ID)}


def w4p_humans(p):
    """Every live human whose join priority is 7 (added by W4P SPAWN) or whose name is "W4PAdded", with player index and
    gang: after X3's LEAVE the old W4P Warriors must be gone (LV deletes them), not left behind as AI."""
    out = []
    for slot in range(60):
        o = p.read32(OBJ_TABLE + 8 * slot)
        if not 0x00100000 <= o < 0x02000000:
            continue
        ser = p.read32(OBJ_TABLE + 8 * slot + 4) & 0xFFFF
        x = _hinfo(p, o)
        if x["prio_1b1"] == 7 or x["name_80"] == "W4PAdded":
            out.append(dict(x, objslot=slot, handle=hex((slot << 16) | ser)))
    return {"poll": T._poll(p), "count": _s16(p.read32(p.read32(GM_PTR) + 0x224)), "w4p": out,
            "players": [hex(p.read32(p.read32(GM_PTR) + 0x228 + 4 * i)) for i in range(4)]}


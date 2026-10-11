"""Inventory tests T2 (pick-up), T4 (partner revive), T5 (checkpoint), T7 (money bank) for players 3-4.

Plan, evidence and command lines: docs/research/m2_inventory_tests.md (test list: m2_inventory34.md section 9).
Used by nav_probe.py --probe inv_tests:<function>:<poll>; every function gets a Pine object and returns a JSON-able
dict (results in local/m2/<tag>/probes.json). SINGLE-PC, one instance, scripted bots, test only:
- some steps write RAM through PINE (item counts, money), like inv_probe._hurt;
- game functions are called on the game thread through the test-call mailbox of the "warriors-4p test call" group,
  exactly as gameover_probe.py does (function 0x000F0300, a0..a3 0x000F0304..0x000F0310, v0 0x000F0314,
  done 0x000F0318). Only addition: a call that did not start within 4 s is cancelled (0x000F0300 = 0).
Function names in comments are OUR labels (the ELF is stripped). Static addresses, build SLUS-21215 v1.03.

Who is who in the standard Mission 13 run (pad owner u16 at 0x005DD810 + pad*0x50 + 0x42, VERIFIED in
local/m2/{inv2,inv3,go1,go3,fight8}/state.txt): game player 3 (index 2, Fox) owns pad 2 = W4P slot 3 = --script4;
game player 4 (index 3, spawned Warrior) owns pad 1 = W4P slot 2 = --script3.

Action probes keep a module-level record of the game calls they made (_DONE), so a probe that nav_probe retries after
a PINE error does not repeat a drop, a kill, a checkpoint or a level load.
"""
import math
import struct
import time

import inv_probe

GM_PTR = 0x0051489C
POLL = 0x000F0500
OBJ_TABLE, OBJ_COUNT, HUMAN_SLOTS = 0x006EBD38, 0xB00, 60   # FUN_0038FE28 (0xB00 slots), FUN_0038FE88 (humans < 0x3C)
POS_TABLE = 0x00714B00                                      # human position: POS_TABLE + human[+0x92]*0x20
BRAINS, BRAIN_SIZE = 0x006D53F0, 0x2F0                      # FUN_0021D408
OBJ_DEFS_PTR = 0x00512C04   # object type table: def = *ptr + id*0x90 (FUN_00391330); count at *ptr+0x34BC0 (FUN_00391340)
PADS = 0x005DD810
COPY = 0x000E4000           # checkpoint copy with [warriors-4p 4p inventory] (m2_inventory34.md A3/A4)
MB_FN, MB_ARGS, MB_V0, MB_DONE = 0x000F0300, 0x000F0304, 0x000F0314, 0x000F0318
ITEMS = {1: "flash", 2: "money", 3: "spray", 6: "key"}

# Game functions called through the mailbox (our labels; arguments as documented in m2_inventory_tests.md)
HU_KILL = 0x00237E70            # (handle) HuKill core: health 1, down state (FUN_002302A8)
HU_TELEPORT_NEAR = 0x0023B138   # (mover handle, target handle) HuTeleportNearHuman core; no-op below 3.6 units
TELEPORT = 0x00385BB8           # (handle, float[3]*, -1) Lua Teleport core; -1 keeps the heading
HU_POCKET = 0x00238190          # (handle, item, count) HuPutItemInPocket core: human+0x250 = item, +0x254 = count
DROP_LOOT = 0x00232C60          # (human*, count, 1) knock-out drop (FUN_002674C0 calls it with (human, 1, 1))
PICKUP = 0x0023BF00             # (human*, object*) typed pick-up: gives the item, returns 1
PICKUP_DONE = 0x003924D8        # (object*) removes the pick-up's collision (what FUN_00395510 does after a pick-up)
INV_GIVE_REVIVE = 0x0041EDB8    # (n, player number) Lua InvGiveRevive core: InvAdd(p-1, 1, n, notify 1)
REVIVE_TRY = 0x00286BA8         # (reviver human*) partner-revive check + start (button action 39 = D-pad Left)
SET_CHECKPOINT = 0x0041ABC0     # (n) Lua SetCheckPoint core -> FUN_0041CE98: GM+0x33A = n, InvSaveCheckpoint
INV_RESTORE = 0x0041E168        # (Inv = GM+0x480) InvRestoreCheckpoint
MENU_LOAD_LEVEL = 0x00160D78    # (char* level name) Lua MenuLoadLevel core; the retry path calls it with GM+0x124
LAUNCH_MISSION_COMPLETE = 0x0015D420  # (choice) Lua HUDLaunchMissionComplete core; choice != 0 -> money banked

# Code words that show which patch groups are active (read from RAM)
CODE_CHECKS = {
    "inventory_A1": (0x0041E3D8, 0x2CA20004),
    "inventory_A3_copy_to_E4000": (0x0041E0B8, 0x3C05000E),
    "inventory_A4_restore_from_E4000": (0x0041E16C, 0x3C03000E),
    "inventory_B_bank_slots_2_3": (0x0015D3F4, 0x0C039400),
    "test_call": (0x00158CD0, 0x0C03C000),
}

_DONE = {}   # key -> result of a game call already made in this nav_probe process
_SNAP = {}   # snapshots shared between the probes of one run


# ---------------------------------------------------------------- small readers
def _s16(v):
    v &= 0xFFFF
    return v - 0x10000 if v & 0x8000 else v


def _s32(v):
    return v - (1 << 32) if v & 0x80000000 else v


def _r8(p, a):
    return (p.read32(a & ~3) >> (8 * (a & 3))) & 0xFF


def _r16(p, a):
    return (p.read32(a & ~3) >> (8 * (a & 2))) & 0xFFFF


def _f(v):
    return round(struct.unpack("<f", struct.pack("<I", v & 0xFFFFFFFF))[0], 3)


def _bytes(p, a, n):
    a0 = a & ~7
    return p.dump(a0, (a - a0) + n)[a - a0:a - a0 + n]


def _cstr(p, a, n=32):
    return _bytes(p, a, n).split(b"\0")[0].decode("latin-1")


def _poll(p):
    return p.read32(POLL)


def _gm(p):
    return p.read32(GM_PTR)


def _count_addr(gm, s, k):
    return gm + 0x480 + 0x24 + s * 0x3F4 + k * 0x2C


def _copy_addr(s, k):
    return COPY + 0x20 + s * 0x3F4 + k * 0x2C


def _counts(p, s):
    gm = _gm(p)
    return {ITEMS[k]: _s32(p.read32(_count_addr(gm, s, k))) for k in ITEMS}


def _all_counts(p):
    return {s: _counts(p, s) for s in range(4)}


def _copies(p):
    return {s: {ITEMS[k]: _s32(p.read32(_copy_addr(s, k))) for k in ITEMS} for s in range(4)}


def _resolve(p, h):
    if h in (0, 0xFFFFFFFF):
        return 0
    idx = (h >> 16) & 0xFFFF
    if idx >= OBJ_COUNT:
        return 0
    if p.read32(OBJ_TABLE + 8 * idx + 4) & 0xFFFF != h & 0xFFFF:
        return 0
    return p.read32(OBJ_TABLE + 8 * idx)


def _player(p, i):
    """Game player index i (0..3) -> (handle, human object or 0)."""
    h = p.read32(_gm(p) + 0x228 + 4 * i)
    return h, _resolve(p, h)


def _bidx(p, o):
    return _s16(p.read32(o + 0x90) >> 16)


def _pos(p, o):
    b = _bidx(p, o)
    return [_f(p.read32(POS_TABLE + b * 0x20 + 4 * k)) for k in range(3)]


def _dist(a, b):
    return round(math.sqrt(sum((a[k] - b[k]) ** 2 for k in range(3))), 3)


def _human(p, o):
    """Health, stats flags (64-bit at stats+0; 0x40000 down, 0x20000 arrested, 0x80000000 beaten, bit 32 dead),
    stats+8 word, position, brain fields, player index, HUD slot, +0xE0 (bit 2 = revivable), pocket item."""
    st = p.read32(o + 0xD4)
    info = {"obj": hex(o)}
    if 0x00100000 <= st < 0x02000000:
        hp = p.read32(st + 0x144)
        fl = p.batch_read64([st])[0]
        info.update(hp=_s16(hp), max=_s16(hp >> 16), flags=hex(fl), st8=hex(p.read32(st + 8)),
                    down=bool(fl & 0x40000), dead=bool(fl >> 32 & 1))
    b = _bidx(p, o)
    brain = BRAINS + b * BRAIN_SIZE
    pidx = p.read32(o + 0x1B0) & 0xFF
    info.update(pos=_pos(p, o), brain4=_s32(p.read32(brain + 4)), brain26c=_s32(p.read32(brain + 0x26C)),
                gang=hex(p.read32(brain + 0x20C)), pidx=pidx - 256 if pidx & 0x80 else pidx,
                hud_slot=_s32(p.read32(o + 0x380)), e0=hex(p.read32(o + 0xE0)),
                pocket=[p.read32(o + 0x250), _r8(p, o + 0x254)])
    return info


def _pads(p):
    """Owner (game player index, -1 free) of pads 0, 1, 2, 4."""
    return {pad: _s16(_r16(p, PADS + pad * 0x50 + 0x42)) for pad in (0, 1, 2, 4)}


def _gmfields(p):
    gm = _gm(p)
    return {"gm": hex(gm), "players": _s16(p.read32(gm + 0x224)), "checkpoint": _r16(p, gm + 0x33A),
            "level_idx": _r16(p, gm + 0x56DC), "gm_14c": p.read32(gm + 0x14C),
            "powerup_full_hp_ok_56e5": _r8(p, gm + 0x56E5), "bank": p.read32(gm + 0x480),
            "level_name_124": _cstr(p, gm + 0x124, 16)}


def _code(p):
    return {k: p.read32(a) == v for k, (a, v) in CODE_CHECKS.items()}


# ---------------------------------------------------------------- mailbox
def _call(p, fn, *args):
    """Call fn(a0..a3) on the game thread (same writes and done-flag wait as gameover_probe.py)."""
    vals = [a & 0xFFFFFFFF for a in args] + [0] * (4 - len(args))
    p.batch_write32([(MB_ARGS, vals[0]), (MB_ARGS + 4, vals[1]), (MB_ARGS + 8, vals[2]), (MB_ARGS + 12, vals[3]),
                     (MB_DONE, 0), (MB_FN, fn)])
    for _ in range(80):
        if p.read32(MB_DONE) == 1:
            break
        time.sleep(0.05)
    done = p.read32(MB_DONE)
    if done != 1:
        p.write32(MB_FN, 0)  # cancel: never let a stale request run later
    return {"fn": hex(fn), "args": [hex(v) for v in vals], "done": done, "v0": _s32(p.read32(MB_V0)), "poll": _poll(p)}


def _once(p, key, fn, *args):
    if key in _DONE:
        return dict(_DONE[key], repeated=True)
    r = _call(p, fn, *args)
    _DONE[key] = r
    return r


# ---------------------------------------------------------------- object scan (pick-ups)
def _find_objs(p, name="dyn_revival"):
    """Non-human objects (object table slots >= 60) whose type definition name is `name`.
    Type id = u16 at object+0x112 (FUN_0023BF00); def = *0x00512C04 + id*0x90, name at def+0x28, class at def+0x43,
    kind (OBJECT.TYPE_*) at def+0x86, own id at def+0x60 (FUN_00390F18, FUN_00391778, FUN_003917A0, FUN_00391340).
    Object fields reported (HYPOTHESIS meanings): +0x10 position, +0x54 flags (0x8000 = may be picked up, checked by
    FUN_0023BF00), +0x117 first-check done, +0x118 collision (cleared by FUN_003924D8 after a pick-up),
    +0x120 expiry time (FUN_00395D20), +0x124 money amount."""
    base = p.read32(OBJ_DEFS_PTR)
    if not 0x00100000 <= base < 0x02000000:
        return {"error": f"object type table pointer {hex(base)}"}
    count = p.read32(base + 0x34BC0)
    if not 0 < count < 0x4000:
        return {"error": f"object type count {count}"}
    table = p.dump(OBJ_TABLE, OBJ_COUNT * 8)
    cands = []
    for idx in range(HUMAN_SLOTS, OBJ_COUNT):
        ptr, ser = struct.unpack_from("<II", table, idx * 8)
        if 0x00100000 <= ptr < 0x02000000 and not ptr & 3:
            cands.append((idx, ptr, ser & 0xFFFF))
    if not cands:
        return []
    vals = p.batch_read64([(ptr + 0x112) & ~7 for _, ptr, _ in cands])
    defs, found = {}, []
    for (idx, ptr, ser), v in zip(cands, vals):
        tid = (v >> (8 * ((ptr + 0x112) & 7))) & 0xFFFF
        if tid >= count:
            continue
        if tid not in defs:
            d = base + tid * 0x90
            defs[tid] = (_cstr(p, d + 0x28, 26), _r16(p, d + 0x60), _cstr(p, d + 0x43, 20), _r8(p, d + 0x86))
        nm, own, cls, kind = defs[tid]
        if nm != name or own != tid:
            continue
        found.append({"slot": idx, "handle": hex((idx << 16) | ser), "obj": hex(ptr), "type_id": tid, "class": cls,
                      "kind": kind, "pos": [_f(p.read32(ptr + 0x10 + 4 * k)) for k in range(3)],
                      "flags_54": hex(p.read32(ptr + 0x54)), "b117": _r8(p, ptr + 0x117),
                      "col_118": hex(p.read32(ptr + 0x118)), "t120": p.read32(ptr + 0x120),
                      "amount_124": p.read32(ptr + 0x124)})
    return found


def _objs_list(r):
    return r if isinstance(r, list) else []


# ---------------------------------------------------------------- general read
def state(p):
    """Read-only overview: patch groups active, GameMgr fields, pads, players, inventory (inv_probe.inventory)."""
    out = {"poll": _poll(p), "code": _code(p), "gm": _gmfields(p), "pads": _pads(p), "players": {}}
    for i in range(4):
        h, o = _player(p, i)
        out["players"][i + 1] = dict(_human(p, o), handle=hex(h)) if o else {"handle": hex(h)}
    out["inventory"] = inv_probe.inventory(p)
    out["flash_objects"] = _find_objs(p, "dyn_revival")
    return out


# ---------------------------------------------------------------- T2 pick-up
def _t2_setup(p, i):
    """Real pick-up path: give the player a Flash "in the pocket" (what the Mission 13 script does to Moonrunners with
    HuPutItemInPocket), let the game's own knock-out drop function spawn it as a dyn_revival pick-up at the player's
    feet, empty the pocket again. The pick-up is then collected by the game's touch code (object side FUN_00395510
    or human side FUN_00219D50 -> FUN_0023BF00 -> InvAdd(HUD slot, 1, +1)); the script walks the player out and back."""
    out = {"poll": _poll(p), "player": i + 1}
    h, o = _player(p, i)
    if not o:
        return dict(out, error=f"no player {i + 1}")
    gm = _gm(p)
    slot = _s32(p.read32(o + 0x380))
    if slot not in range(4):
        return dict(out, error=f"player {i + 1} HUD slot {slot}")
    objs0 = _objs_list(_find_objs(p, "dyn_revival"))
    snap = _SNAP.setdefault(f"t2_{i}", {"slot": slot, "before": _all_counts(p),
                                        "handles_before": [x["handle"] for x in objs0]})
    out.update(slot=slot, code=_code(p), gm=_gmfields(p), pads=_pads(p), counts_before=snap["before"],
               human_before=_human(p, o), flash_objects_before=objs0)
    if _r8(p, gm + 0x56E5) == 0:  # CfgPowerupPickup(false): a player at full health ignores Flash pick-ups
        st = p.read32(o + 0xD4)
        w = p.read32(st + 0x144)
        p.write32(st + 0x144, (w & 0xFFFF0000) | max(1, ((w >> 16) & 0xFFFF) - 100))
        out["hp_lowered_to"] = max(1, ((w >> 16) & 0xFFFF) - 100)
    out["pocket_put"] = _once(p, f"t2_pocket_{i}", HU_POCKET, h, 1, 1)
    out["pocket_after_put"] = [p.read32(o + 0x250), _r8(p, o + 0x254)]
    out["drop"] = _once(p, f"t2_drop_{i}", DROP_LOOT, o, 1, 1)
    out["pocket_clear"] = _once(p, f"t2_pocket_clear_{i}", HU_POCKET, h, 0, 0)
    out["pocket_after_clear"] = [p.read32(o + 0x250), _r8(p, o + 0x254)]
    me = _pos(p, o)
    new = [dict(x, dist_to_player=_dist(x["pos"], me)) for x in _objs_list(_find_objs(p, "dyn_revival"))
           if x["handle"] not in snap["handles_before"]]
    out["flash_objects_new"] = new
    out["counts_after_drop"] = _all_counts(p)
    return out


def t2_setup_p3(p):
    return _t2_setup(p, 2)


def t2_setup_p4(p):
    return _t2_setup(p, 3)


def t2_read(p):
    """Counts of all slots against the snapshot of each t2_setup that ran; dyn_revival objects left in the level."""
    out = {"poll": _poll(p), "counts": _all_counts(p), "flash_objects": _find_objs(p, "dyn_revival"), "result": {}}
    for i in (2, 3):
        h, o = _player(p, i)
        if o:
            out[f"player{i + 1}"] = _human(p, o)
        snap = _SNAP.get(f"t2_{i}")
        if not snap:
            continue
        s, b, now = snap["slot"], snap["before"], out["counts"]
        gain = now[s]["flash"] - b[s]["flash"]
        same = {t: now[t] == b[t] for t in range(4) if t != s}
        out["result"][f"player{i + 1}"] = {"slot": s, "flash_before": b[s]["flash"], "flash_now": now[s]["flash"],
                                            "flash_gain": gain, "other_slots_unchanged": same,
                                            "via": _SNAP.get(f"t2_via_{i}", "game pick-up (no fallback call made)"),
                                            "pass": gain == 1 and all(same.values())}
    return out


def _t2_fallback(p, i):
    """Only if the game did not hand the Flash over: (b) direct pick-up FUN_0023BF00(player human, nearest new
    dyn_revival object) + FUN_003924D8(object); (c) if still nothing, InvGiveRevive core FUN_0041EDB8(1, player)."""
    out = {"poll": _poll(p), "player": i + 1}
    snap = _SNAP.get(f"t2_{i}")
    if not snap:
        return dict(out, error="t2_setup did not run for this player")
    h, o = _player(p, i)
    if not o:
        return dict(out, error=f"no player {i + 1}")
    s, before = snap["slot"], snap["before"][snap["slot"]]["flash"]
    if _counts(p, s)["flash"] > before:
        _SNAP.setdefault(f"t2_via_{i}", "game pick-up (real path)")
        return dict(out, note="Flash already collected by the game path; nothing called", counts=_all_counts(p))
    me = _pos(p, o)
    objs = sorted((x for x in _objs_list(_find_objs(p, "dyn_revival")) if x["handle"] not in snap["handles_before"]),
                  key=lambda x: _dist(x["pos"], me))
    out["candidates"] = objs[:4]
    if objs:
        ob = int(objs[0]["obj"], 16)
        r = _once(p, f"t2_pickup_{i}", PICKUP, o, ob)
        out["direct_pickup"] = r
        if r.get("v0") == 1:
            out["pickup_done"] = _once(p, f"t2_pickup_done_{i}", PICKUP_DONE, ob)
            _SNAP[f"t2_via_{i}"] = "direct FUN_0023BF00 (game pick-up function, no touch)"
    if _counts(p, s)["flash"] <= before:
        out["inventory_add"] = _once(p, f"t2_invadd_{i}", INV_GIVE_REVIVE, 1, i + 1)
        _SNAP[f"t2_via_{i}"] = "direct FUN_0041EDB8 (inventory only)"
    out["counts"] = _all_counts(p)
    return out


def t2_fallback_p3(p):
    return _t2_fallback(p, 2)


def t2_fallback_p4(p):
    return _t2_fallback(p, 3)


# ---------------------------------------------------------------- T4 partner revive
def _revive_pre(p, o3, o4):
    """Static conditions of the revive by player 4 of downed player 3 (FUN_00286BA8, FUN_00279078 -> FUN_0029CC78
    radius 3.0 with predicate FUN_00278FA0)."""
    st3, st4 = p.read32(o3 + 0xD4), p.read32(o4 + 0xD4)
    f3, f4 = p.batch_read64([st3])[0], p.batch_read64([st4])[0]
    s3, s4 = _s32(p.read32(o3 + 0x380)), _s32(p.read32(o4 + 0x380))
    d = _dist(_pos(p, o3), _pos(p, o4))
    gang3 = p.read32(BRAINS + _bidx(p, o3) * BRAIN_SIZE + 0x20C)
    gang4 = p.read32(BRAINS + _bidx(p, o4) * BRAIN_SIZE + 0x20C)
    pre = {"reviver_st8_zero": p.read32(st4 + 8) == 0,
           "reviver_flags_free_0x7BF9E9F7FF0": (f4 & 0x7BF9E9F7FF0) == 0,
           "downed_st8_zero": p.read32(st3 + 8) == 0,
           "downed_0x40000": bool(f3 & 0x40000), "downed_not_0x20000": not f3 & 0x20000,
           "downed_not_0x80000000": not f3 & 0x80000000, "downed_not_dead": not f3 >> 32 & 1,
           "downed_revivable_e0_bit2": bool(p.read32(o3 + 0xE0) & 4), "same_gang": gang3 == gang4,
           "distance": d, "within_3": d <= 3.0,
           "flash_reviver": _counts(p, s4)["flash"] if s4 in range(4) else None,
           "flash_downed": _counts(p, s3)["flash"] if s3 in range(4) else None,
           "reviver_brain4": _s32(p.read32(BRAINS + _bidx(p, o4) * BRAIN_SIZE + 4))}
    pre["all_ok"] = all(pre[k] for k in pre if k not in ("distance", "flash_reviver", "flash_downed",
                                                          "reviver_brain4")) and bool(
        (pre["flash_reviver"] or 0) + (pre["flash_downed"] or 0))
    return pre


def t4_setup(p):
    """Player 4 gets exactly one Flash, player 3 none (PINE writes, slot = HUD slot), then player 3 is downed with
    HuKill FUN_00237E70(handle) as in gameover_probe.kill_p3 (single down: no game over, local/m2/go1)."""
    out = {"poll": _poll(p)}
    h3, o3 = _player(p, 2)
    h4, o4 = _player(p, 3)
    if not (o3 and o4):
        return dict(out, error="players 3-4 not both present")
    s3, s4 = _s32(p.read32(o3 + 0x380)), _s32(p.read32(o4 + 0x380))
    if s3 not in range(4) or s4 not in range(4):
        return dict(out, error=f"HUD slots {s3}/{s4}")
    gm = _gm(p)
    _SNAP.setdefault("t4", {"s3": s3, "s4": s4, "before": _all_counts(p)})
    p.write32(_count_addr(gm, s4, 1), 1)
    p.write32(_count_addr(gm, s3, 1), 0)
    out.update(code=_code(p), gm=_gmfields(p), pads=_pads(p), slots=[s3, s4])
    out["kill_p3"] = _once(p, "t4_kill", HU_KILL, h3)
    out["p3"], out["p4"] = _human(p, o3), _human(p, o4)
    out["counts"] = _all_counts(p)
    return out


def t4_move(p):
    """Bring player 4 within the 3.0-unit revive radius of player 3: HuTeleportNearHuman (only moves when the two are
    3.6 or more apart), then, if still farther than 2.5, the Lua Teleport core onto player 3's position."""
    out = {"poll": _poll(p)}
    h3, o3 = _player(p, 2)
    h4, o4 = _player(p, 3)
    if not (o3 and o4):
        return dict(out, error="players 3-4 not both present")
    d = _dist(_pos(p, o3), _pos(p, o4))
    out["dist_before"] = d
    if d > 2.5:
        out["teleport_near"] = _once(p, "t4_tp_near", HU_TELEPORT_NEAR, h4, h3)
        d = _dist(_pos(p, o3), _pos(p, o4))
        out["dist_after_near"] = d
    if d > 2.5:
        out["teleport_onto"] = _once(p, "t4_tp_onto", TELEPORT, h4, POS_TABLE + _bidx(p, o3) * 0x20, 0xFFFFFFFF)
        out["dist_after_onto"] = _dist(_pos(p, o3), _pos(p, o4))
    out["p3"], out["p4"] = _human(p, o3), _human(p, o4)
    out["preconditions"] = _revive_pre(p, o3, o4)
    return out


def t4_read(p):
    out = {"poll": _poll(p), "gm": _gmfields(p)}
    snap = _SNAP.get("t4")
    h3, o3 = _player(p, 2)
    h4, o4 = _player(p, 3)
    if not (snap and o3 and o4):
        return dict(out, error="t4_setup did not run or players missing")
    a = _human(p, o3)
    c = _all_counts(p)
    out.update(p3=a, p4=_human(p, o4), counts=c)
    out["result"] = {"p3_down": a.get("down"), "p3_hp": a.get("hp"), "flash_p4": c[snap["s4"]]["flash"],
                     "flash_p3": c[snap["s3"]]["flash"], "slots_0_1_unchanged": all(c[t] == snap["before"][t]
                                                                                    for t in (0, 1)),
                     "via": _SNAP.get("t4_via", "D-pad Left press (real path), no direct call made"),
                     "pass": (a.get("down") is False and (a.get("hp") or 0) > 1 and c[snap["s4"]]["flash"] == 0
                              and c[snap["s3"]]["flash"] == 0)}
    return out


def t4_direct(p):
    """Fallback only while player 3 is still down: call the button handler's action FUN_00286BA8(player 4 human)
    directly (same checks and same revive start FUN_002752A0, no button). v0 = 1: revive started."""
    out = {"poll": _poll(p)}
    h3, o3 = _player(p, 2)
    h4, o4 = _player(p, 3)
    if not (o3 and o4):
        return dict(out, error="players 3-4 not both present")
    if not _human(p, o3).get("down"):
        return dict(out, skipped="player 3 is not down (revived by the button press or never downed)")
    out["preconditions"] = _revive_pre(p, o3, o4)
    out["revive_try"] = _once(p, "t4_direct", REVIVE_TRY, o4)
    if out["revive_try"].get("v0") == 1:
        _SNAP["t4_via"] = "direct FUN_00286BA8 (no button)"
    return out


# ---------------------------------------------------------------- T5 checkpoint copy and retry
T5_GIVE = {2: {1: 2, 2: 40, 6: 1}, 3: {1: 1, 2: 25, 3: 3}}    # slot -> item -> count before the checkpoint
T5_SPEND = {2: {1: 0, 2: 5, 6: 0}, 3: {1: 0, 2: 0, 3: 0}}     # after the checkpoint


def _live_vs_copy(p):
    """Byte compare of the live records Inv+4..+0xFD3 with the copy 0x000E4000..0x000E4FCF."""
    gm = _gm(p)
    live = _bytes(p, gm + 0x484, 0xFD0)
    copy = p.dump(COPY, 0xFD0)
    diffs = [i for i in range(0, 0xFD0, 4) if live[i:i + 4] != copy[i:i + 4]]
    first = [{"slot": i // 0x3F4, "item": (i % 0x3F4) // 0x2C, "field": hex((i % 0x3F4) % 0x2C),
              "live": hex(struct.unpack_from("<I", live, i)[0]), "copy": hex(struct.unpack_from("<I", copy, i)[0])}
             for i in diffs[:8]]
    return {"equal": not diffs, "diff_words": len(diffs), "first_diffs": first}


def _write_counts(p, table):
    gm = _gm(p)
    for s, items in table.items():
        for k, v in items.items():
            p.write32(_count_addr(gm, s, k), v)


def t5_give(p):
    """Items for slots 2-3 before the checkpoint (PINE writes; scripts never give players 3-4 anything)."""
    _write_counts(p, T5_GIVE)
    return {"poll": _poll(p), "code": _code(p), "gm": _gmfields(p), "counts": _all_counts(p), "copy": _copies(p)}


def t5_checkpoint(p):
    """The game's checkpoint save: Lua SetCheckPoint(2) core FUN_0041ABC0(2) -> FUN_0041CE98 -> InvSaveCheckpoint."""
    out = {"poll": _poll(p)}
    out["set_checkpoint"] = _once(p, "t5_cp", SET_CHECKPOINT, 2)
    out["gm"] = _gmfields(p)
    live = _all_counts(p)
    snap = _SNAP.setdefault("t5_cp", live)
    out.update(counts=live, copy=_copies(p), live_vs_copy=_live_vs_copy(p))
    out["pass"] = out["live_vs_copy"]["equal"] and out["gm"]["checkpoint"] == 2 and out["copy"] == snap
    return out


def t5_spend(p):
    """Change slots 2-3 after the checkpoint (PINE writes); the copy must not change."""
    _write_counts(p, T5_SPEND)
    snap = _SNAP.get("t5_cp")
    cp = _copies(p)
    return {"poll": _poll(p), "counts": _all_counts(p), "copy": cp,
            "copy_unchanged": (cp == snap) if snap else None, "live_vs_copy": _live_vs_copy(p)}


def t5_restore_direct(p):
    """T5a: InvRestoreCheckpoint FUN_0041E168(GM+0x480) directly (the call the retry path makes)."""
    out = {"poll": _poll(p)}
    snap = _SNAP.get("t5_cp")
    out["restore"] = _once(p, "t5_restore", INV_RESTORE, _gm(p) + 0x480)
    out.update(counts=_all_counts(p), live_vs_copy=_live_vs_copy(p))
    out["pass"] = bool(snap) and out["counts"] == snap and out["live_vs_copy"]["equal"]
    return out


def t5_retry(p):
    """T5b: spend again, then restart the level at the saved checkpoint the way the retry path does
    (FUN_00155408 at 0x001555F4-0x001555FC: MenuLoadLevel(GameMgr+0x124)). The level start FUN_00418C68 then runs
    InvClear(clear = checkpoint < 2) and InvRestoreCheckpoint for checkpoint >= 2."""
    _write_counts(p, T5_SPEND)
    gm = _gm(p)
    out = {"poll": _poll(p), "gm": _gmfields(p), "counts_before_retry": _all_counts(p), "copy": _copies(p)}
    ptr, name = gm + 0x124, _cstr(p, gm + 0x124, 16)
    if name != "level9":  # fall back to the level table's own entry string (level_jump.md, idx 13)
        alt = gm + 0x14E8 + 13 * 0x84
        out["level_table_name"] = _cstr(p, alt, 16)
        if out["level_table_name"] == "level9":
            ptr = alt
        else:
            return dict(out, error=f"no 'level9' string at GM+0x124 ({name!r}) or in the level table")
    out["name_ptr"] = hex(ptr)
    out["menu_load_level"] = _once(p, "t5_retry", MENU_LOAD_LEVEL, ptr)
    return out


def t5_read(p):
    """After the level restart: checkpoint 2, level 13, in gameplay; live slots 2-3 equal the checkpoint values."""
    out = {"poll": _poll(p), "gm": _gmfields(p), "counts": _all_counts(p), "copy": _copies(p),
           "live_vs_copy": _live_vs_copy(p), "pads": _pads(p), "players": {}}
    for i in range(4):
        h, o = _player(p, i)
        out["players"][i + 1] = {"handle": hex(h), "hud_slot": _s32(p.read32(o + 0x380)) if o else None}
    snap = _SNAP.get("t5_cp")
    if snap:
        g = out["gm"]
        out["result"] = {"checkpoint_2": g["checkpoint"] == 2, "level_13": g["level_idx"] == 13,
                         "in_game": g["gm_14c"] == 0,
                         "slots_2_3_live_equal_checkpoint": all(out["counts"][s] == snap[s] for s in (2, 3)),
                         "slots_2_3_copy_equal_checkpoint": all(out["copy"][s] == snap[s] for s in (2, 3)),
                         "slots_0_1_live_vs_checkpoint": {s: out["counts"][s] == snap[s] for s in (0, 1)}}
        r = out["result"]
        r["pass"] = (r["checkpoint_2"] and r["level_13"] and r["slots_2_3_live_equal_checkpoint"]
                     and r["slots_2_3_copy_equal_checkpoint"])
    return out


# ---------------------------------------------------------------- T7 money bank
T7_MONEY = {0: 10, 1: 20, 2: 30, 3: 40}


def t7_setup(p):
    """Money for all four slots (PINE writes) and the bank before."""
    gm = _gm(p)
    for s, v in T7_MONEY.items():
        p.write32(_count_addr(gm, s, 2), v)
    snap = _SNAP.setdefault("t7", {"bank0": p.read32(gm + 0x480)})
    return {"poll": _poll(p), "code": _code(p), "gm": _gmfields(p), "bank0": snap["bank0"], "counts": _all_counts(p)}


def t7_launch(p):
    """Lua HUDLaunchMissionComplete(4) core FUN_0015D420(4) (the level-skip handler WAD 4106 main_61 makes the same
    call): pushes the mission-complete state 0x005E5DF8 with choice +0x24 = 4; its update FUN_0015D160 banks the
    money of slots 0-1 (0x0015D3B0-0x0015D3F0) and, with Block B, slots 2-3, then starts the save sequence
    FUN_00155308."""
    out = {"poll": _poll(p), "counts": _all_counts(p), "bank": p.read32(_gm(p) + 0x480)}
    out["launch"] = _once(p, "t7_launch", LAUNCH_MISSION_COMPLETE, 4)
    out["choice_5e5e1c"] = p.read32(0x005E5E1C)
    out["state_top_50c784"] = p.read32(0x0050C784)
    return out


def t7_read(p):
    gm = _gm(p)
    snap = _SNAP.get("t7")
    bank = p.read32(gm + 0x480)
    block_b = _code(p)["inventory_B_bank_slots_2_3"]
    out = {"poll": _poll(p), "gm": _gmfields(p), "bank": bank, "counts": _all_counts(p), "block_b_active": block_b,
           "choice_5e5e1c": p.read32(0x005E5E1C), "state_top_50c784": p.read32(0x0050C784)}
    if snap:
        delta = (bank - snap["bank0"]) & 0xFFFFFFFF
        expected = sum(T7_MONEY.values()) if block_b else T7_MONEY[0] + T7_MONEY[1]
        out["result"] = {"bank0": snap["bank0"], "delta": delta, "expected": expected, "pass": delta == expected}
    return out

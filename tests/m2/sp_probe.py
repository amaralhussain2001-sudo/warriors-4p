"""Session-policy probes (docs/research/session_policies.md): pause, cutscene skip, player leave, checkpoint restart.

Used by tests/m2/nav_probe.py --probe sp_probe:<function>:<poll> (one instance, SINGLE-PC, scripted input).
snap/strings/scan are read-only PINE reads. kill_p1, leave_p2/p3/p4 and reload write the test-call mailbox
(group "warriors-4p test call"); leave_* also write a TEST-ONLY code cave at 0x000E6000 (free RAM, STATE.md).
Never used in online sessions: PINE writes are not part of the lockstep.
All addresses are EE virtual addresses, static unless noted; names are OUR labels (stripped ELF).
"""
import struct
import time

GM_PTR = 0x0051489C          # GameMgr pointer (F-0020)
MODE_TOP = 0x0050C784        # game-mode stack top index (F-0045, level_jump.md 1.3)
MODE_STACK = 0x005E66A0      # game-mode stack (u32 object pointers)
PAUSE_MODE = 0x005E6550      # pause mode object (mode id 10; pushed by FUN_00154F28)
PAUSE_MENU = 0x0062E790      # story pause menu object (*(0x0050EDDC)); levels 60-69 use 0x006239D0
GAME_CLOCK_PTR = 0x0050B734  # GameClock object pointer; +0x48 game time in ms (F-0047)
FRAME_COUNTER = 0x0050C654   # FrameStats counter (F-0046)
POLL = 0x000F0500            # W4P guest poll counter
HUD = 0x00600840             # HUD manager; +0/+4 = menu controller records of players 1/2 (FUN_001AE898)
PADS = 0x005DD810            # pad state structs, 0x50 each: +0x42 owner player, +0x4C connected (F-0031)
SCENES = 0x006EBA18          # scene slot table, 12 x 0x40 (FUN_00353298); +0x24 = scene player object
MOVIE_FRAMES = 0x0051545C    # Bink movie frames shown (reset by FUN_00429FE8)
HUD_STRINGS = 0x00600048     # HUD string pointer table (FUN_0019EE70)
MAILBOX = 0x000F0300         # test-call mailbox (make_pnach.py "warriors-4p test call")
CAVE = 0x000E6000            # TEST-ONLY leave cave (free RAM; no pnach line uses 0x000E6xxx)


def _u32(b, o):
    return struct.unpack_from("<I", b, o)[0]


def _s32(b, o):
    return struct.unpack_from("<i", b, o)[0]


def _u16(b, o):
    return struct.unpack_from("<H", b, o)[0]


def _s16(b, o):
    return struct.unpack_from("<h", b, o)[0]


def _s8(b, o):
    return struct.unpack_from("<b", b, o)[0]


def _ok(a):
    return 0x00100000 <= a < 0x02000000


def _dump(p, addr, n):
    a0 = addr & ~3
    n0 = ((addr + n + 3) & ~3) - a0
    b = p.dump(a0, n0)
    return b[addr - a0: addr - a0 + n]


def _resolve(p, h):
    if h in (0, 0xFFFFFFFF):
        return 0
    return p.read32(0x006EBD38 + 8 * ((h >> 16) & 0xFFFF))


def _cstr(p, addr, n=48):
    if not _ok(addr):
        return None
    return _dump(p, addr, n).split(b"\0")[0].decode("latin1")


def snap(p):
    """Pause, cutscene and player state at this moment (read-only)."""
    gm = p.read32(GM_PTR)
    out = {"poll": p.read32(POLL), "frame": p.read32(FRAME_COUNTER)}
    clk = p.read32(GAME_CLOCK_PTR)
    out["game_ms"] = p.read32(clk + 0x48) if _ok(clk) else None
    top = struct.unpack("<i", struct.pack("<I", p.read32(MODE_TOP)))[0]
    stack = [p.read32(MODE_STACK + 4 * i) for i in range(max(0, min(top + 1, 8)))]
    out["mode_top"] = top
    out["modes"] = [hex(m) for m in stack]
    out["paused"] = bool(stack) and stack[-1] == PAUSE_MODE
    g = _dump(p, gm, 0x5700)
    out["gm"] = {"count": _s16(g, 0x224), "handles": [hex(_u32(g, 0x228 + 4 * i)) for i in range(4)],
                 "end_state_14c": _u32(g, 0x14C), "forced_pause_11c": _u32(g, 0x11C), "cine_410": g[0x410],
                 "b_411": g[0x411], "dropin_mask_456": hex(_u16(g, 0x456)), "b_56e0": g[0x56E0],
                 "skipall_56e4": g[0x56E4], "join_56e8": _u32(g, 0x56E8), "mp_56ec": _u32(g, 0x56EC),
                 "checkpoint_33a": _u16(g, 0x33A),
                 "level_name_124": g[0x124:0x134].split(b"\0")[0].decode("latin1")}
    m = _dump(p, PAUSE_MENU, 0x20B8)
    ctrl = _u32(m, 0x40)
    out["menu"] = {"owner_1bc0": _s32(m, 0x1BC0), "cooldown_20ac": _u32(m, 0x20AC), "ctrl_40": hex(ctrl),
                   "ctrl_pad": _s8(_dump(p, ctrl, 0x20), 0x19) if _ok(ctrl) else None,
                   "open_10": _u32(m, 0x10), "closing_1b80": _u32(m, 0x1B80), "b_1b88": _u32(m, 0x1B88),
                   "res_1b70_74_78": [_u32(m, 0x1B70), _u32(m, 0x1B74), _u32(m, 0x1B78)]}
    hudc = []
    for i in range(2):
        c = p.read32(HUD + 4 * i)
        if _ok(c):
            cb = _dump(p, c, 0x20)
            hudc.append({"rec": hex(c), "pad_19": _s8(cb, 0x19), "on_1b": cb[0x1B]})
        else:
            hudc.append({"rec": hex(c)})
    out["hud_menu_ctrl"] = hudc
    pb = _dump(p, PADS, 8 * 0x50)
    out["pads"] = [{"pad": i, "conn": _u32(pb, i * 0x50 + 0x4C), "owner": _s16(pb, i * 0x50 + 0x42),
                    "btn": hex(_u16(pb, i * 0x50 + 0x1C + 2 * (_u32(pb, i * 0x50 + 0x2C) & 7)))}
                   for i in range(8) if _u32(pb, i * 0x50 + 0x4C) or _s16(pb, i * 0x50 + 0x42) != -1]
    players = []
    for i in range(4):
        h = _u32(g, 0x228 + 4 * i)
        o = _resolve(p, h)
        if not _ok(o):
            continue
        hb = _dump(p, o, 0x400)
        st = _u32(hb, 0xD4)
        flags = p.batch_read64([st])[0] if _ok(st) else 0
        ctl = 0x00660F50 + _s16(hb, 0x92) * 0x2C
        cb = _dump(p, ctl, 0x2C)
        players.append({"idx": i, "human": hex(o), "pidx_1b0": _s8(hb, 0x1B0), "prio_1b1": hb[0x1B1],
                        "char_d0": _u32(hb, 0xD0), "hud_slot_380": _s32(hb, 0x380), "pad_19": _s8(cb, 0x19),
                        "ctrl_1b": cb[0x1B], "flags": hex(flags), "downed": bool(flags & 0x40000),
                        "hp": _s16(_dump(p, st, 0x148), 0x144) if _ok(st) else None,
                        "pos": [round(struct.unpack_from("<f", hb, 0x10 + 4 * k)[0], 2) for k in range(3)]})
    out["players"] = players
    out["scenes"] = scan(p)
    out["movie_frames"] = p.read32(MOVIE_FRAMES)
    out["views"] = p.read32(0x0050B198)
    out["cameras"] = p.read32(0x0050B19C)
    cb = _dump(p, 0x000F0800, 0x30)  # relocated camera arrays (m2_pads_cameras.md 2.1): active, render list, follow
    out["cams"] = {"active": [hex(_u32(cb, 4 * i)) for i in range(4)],
                   "render": [hex(_u32(cb, 0x10 + 4 * i)) for i in range(4)],
                   "follow": [hex(_u32(cb, 0x20 + 4 * i)) for i in range(4)]}
    return out


def scan(p):
    """Active scene slots (FUN_00353298 table): state (+0x1C of the scene data) and the scene player's skip fields."""
    t = _dump(p, SCENES, 12 * 0x40)
    res = []
    for k in range(12):
        data, player = _u32(t, k * 0x40), _u32(t, k * 0x40 + 0x24)
        if not data and not player:
            continue
        e = {"slot": k, "data": hex(data), "player": hex(player), "flags_2c": hex(_u32(t, k * 0x40 + 0x2C))}
        if _ok(data):
            d = _dump(p, data, 0x24)
            e["state_1c"] = _u16(d, 0x1C)
            e["n_humans_20"] = d[0x20]
        if _ok(player):
            s = _dump(p, player, 0x100)
            e["skip"] = {"countdown_e0": _s32(s, 0xE0), "skipping_e4": s[0xE4], "skippable_e5": s[0xE5],
                         "e6": s[0xE6], "chain_e8": s[0xE8], "startskip_e9": s[0xE9], "eb": s[0xEB],
                         "cinematic_ed": s[0xED], "ee": s[0xEE], "ef": s[0xEF], "f0": s[0xF0]}
        res.append(e)
    return res


def strings(p):
    """HUD strings used by the pause menu and the cinematic skip (FUN_001DBEE0, FUN_001DF700, FUN_001DDCF8)."""
    ids = [0x19, 0x1A, 0x1E, 0x3B, 0x3C, 0xD0, 0xD1, 0xD2, 0xE7, 0xE8, 0xE9] + list(range(0xF7, 0x117)) + [0x173]
    return {hex(i): _cstr(p, p.read32(HUD_STRINGS + 4 * i)) for i in ids}


def _call(p, fn, a0=0, a1=0, a2=0, a3=0, wait=4.0):
    p.batch_write32([(MAILBOX + 4, a0), (MAILBOX + 8, a1), (MAILBOX + 12, a2), (MAILBOX + 16, a3),
                     (MAILBOX + 0x18, 0), (MAILBOX, fn)])
    t0 = time.time()
    while time.time() - t0 < wait:
        if p.read32(MAILBOX + 0x18) == 1:
            break
        time.sleep(0.03)
    return {"fn": hex(fn), "args": [hex(a0), hex(a1), hex(a2), hex(a3)], "done": p.read32(MAILBOX + 0x18),
            "v0": hex(p.read32(MAILBOX + 0x14)), "poll": p.read32(POLL)}


def menu_dbg(p):
    """Pause menu state words for the Quit-dialog test: list widget menu+0x2B00 (FUN_001D4110 fields), flags
    +0x1B70..+0x1BBC and the tab/dialog words +0x3A74..+0x3A80 (FUN_001DE6C0, FUN_001DF5E8)."""
    m = _dump(p, PAUSE_MENU + 0x1B70, 0x50)
    lst = _dump(p, PAUSE_MENU + 0x2B00, 0xC8)
    tab = _dump(p, PAUSE_MENU + 0x3A74, 0x10)
    return {"poll": p.read32(POLL), "paused": snap_paused(p),
            "flags_1b70": {hex(0x1B70 + 4 * i): _u32(m, 4 * i) for i in range(20)},
            "list_2b00": {hex(4 * i): _u32(lst, 4 * i) for i in range(0x32) if _u32(lst, 4 * i)},
            "tab_3a74": [_u32(tab, 4 * i) for i in range(4)]}


def snap_paused(p):
    top = p.read32(MODE_TOP)
    return p.read32(MODE_STACK + 4 * top) == PAUSE_MODE if top < 8 else False


def fmv(p):
    """FMV flag cave of the TEST group in local/m2/sp_test.pnach (proposal in session_policies.md): 0x000E70F0 = flag
    (non-zero only while the movie loop's pad read runs), 0x000E70F4 = number of movie-loop pad reads."""
    return {"poll": p.read32(POLL), "frame": p.read32(FRAME_COUNTER), "flag": p.read32(0x000E70F0),
            "movie_pad_reads": p.read32(0x000E70F4), "movie_frames": p.read32(MOVIE_FRAMES),
            "mode_top": hex(p.read32(MODE_STACK + 4 * p.read32(MODE_TOP)))}


def kill_p1(p):
    """Player 1 downed with the game's HuKill core FUN_00237E70(handle) (as gameover_probe.kill_p3)."""
    gm = p.read32(GM_PTR)
    h = p.read32(gm + 0x228)
    return {"call": _call(p, 0x00237E70, h), "after": snap(p)}


def reload(p):
    """Restart from the current checkpoint: MenuLoadLevel(GameMgr+0x124) = FUN_00160D78, as the GAME OVER menu's
    'Last checkpoint' (FUN_00155408) and F-0155."""
    gm = p.read32(GM_PTR)
    before = snap(p)
    return {"before": before, "call": _call(p, 0x00160D78, gm + 0x124)}


# ---- TEST-ONLY leave cave: the body of the game's own leave loop (FUN_0041A460, 0x0041A7D8-0x0041A890) for ONE
# player index a0: drop-in pad bit check (GameMgr+0x456), camera removal (FUN_00122248 / FUN_0011ED60 /
# FUN_00122438), FUN_00258A88, ReleasePlayer FUN_0022A2A8(h,1,1), clear the bit, leave event through LEAVEHOOK
# 0x000E1240 (group "4p spawn leave": FUN_0041B148 + DESPAWN of a W4P-added Warrior), then the tracked-list count
# (0x0050B194) and LayoutViewports FUN_00122ED0, as the loop does after every player.
# v0 = 0 no human, 1 released, 2 not a drop-in player (bit clear, nothing done).
LEAVE_SRC = """
  addiu sp, sp, -48
  sd ra, 0(sp)
  sd s0, 8(sp)
  sd s1, 16(sp)
  sd s2, 24(sp)
  lui v0, 0x0051
  lw s1, 0x489c(v0)
  sll t0, a0, 2
  addu t0, t0, s1
  jal 0x00390268
  addiu a0, t0, 0x228
  beq v0, zero, out
  daddu s2, zero, zero
  move s0, v0
  jal 0x0021d3e8
  move a0, s0
  lb t1, 0x19(v0)
  lhu t2, 0x456(s1)
  srlv t2, t2, t1
  andi t2, t2, 1
  beq t2, zero, out
  addiu s2, zero, 2
  jal 0x00122248
  move a0, s0
  addiu at, zero, 1
  bne v0, at, nocam
  nop
  jal 0x0011ed60
  lb a0, 0x1b0(s0)
  move a0, s0
  jal 0x00122438
  addiu a1, zero, 1
nocam:
  jal 0x00258a88
  move a0, s0
  move a0, s0
  addiu a1, zero, 1
  jal 0x0022a2a8
  addiu a2, zero, 1
  jal 0x0021d3e8
  move a0, s0
  lb t1, 0x19(v0)
  addiu t2, zero, 1
  sllv t2, t2, t1
  nor t2, t2, zero
  lhu t3, 0x456(s1)
  and t3, t3, t2
  sh t3, 0x456(s1)
  move a0, s1
  move a1, s0
  jal 0x000e1240
  daddu a2, zero, zero
  lui a0, 0x005d
  jal 0x004dad40
  ori a0, a0, 0x91a8
  lui at, 0x0051
  sw v0, -0x4e6c(at)
  jal 0x00122ed0
  nop
  addiu s2, zero, 1
out:
  move v0, s2
  ld ra, 0(sp)
  ld s0, 8(sp)
  ld s1, 16(sp)
  ld s2, 24(sp)
  jr ra
  addiu sp, sp, 48
"""

# ---- TEST-ONLY leave cave v2 (the proposal of session_policies.md 3.5), 0x000E6200, a0 = game player index:
# as LEAVE_SRC, plus: the Lua leave event only for player indices 0-1 (mirrors the join-event guard, joinevent.txt),
# for index >= 2 only LV (0x000E1BAC: DESPAWN of a W4P-added Warrior + extra-model pin release); the cameras of the
# players that RemovePlayer (FUN_00419C68) moved down are removed, every remaining player's pad owner (+0x42) is set
# to its new index, and UpdateJoin(GameMgr, -1) (FUN_0041A460) rebuilds cameras and layout when more than one player
# is left (with one player left it would re-create a player 2 from a companion). The layout (tracked-list count +
# LayoutViewports) is redone right after the camera removal and BEFORE UpdateJoin: run C2 (first version, layout only
# after UpdateJoin) crashed at pc 0x00120270 (FUN_00120230 walks the render list, which still counted the removed
# cameras).
# v0 = 0 no human, 1 released, 2 not a drop-in player.
CAVE2 = 0x000E6200
LEAVE2_SRC = """
  addiu sp, sp, -64
  sd ra, 0(sp)
  sd s0, 8(sp)
  sd s1, 16(sp)
  sd s2, 24(sp)
  sd s3, 32(sp)
  sd s4, 40(sp)
  sd s5, 48(sp)
  move s4, a0
  lui v0, 0x0051
  lw s1, 0x489c(v0)
  lh s5, 0x224(s1)
  sll t0, a0, 2
  addu t0, t0, s1
  lw s3, 0x228(t0)
  jal 0x00390268
  addiu a0, t0, 0x228
  beq v0, zero, out
  daddu s2, zero, zero
  move s0, v0
  jal 0x0021d3e8
  move a0, s0
  lb t1, 0x19(v0)
  lhu t2, 0x456(s1)
  srlv t2, t2, t1
  andi t2, t2, 1
  beq t2, zero, out
  addiu s2, zero, 2
  jal 0x00122248
  move a0, s0
  addiu at, zero, 1
  bne v0, at, nocam
  nop
  jal 0x0011ed60
  move a0, s4
  move a0, s0
  jal 0x00122438
  addiu a1, zero, 1
nocam:
  jal 0x00258a88
  move a0, s0
  move a0, s0
  addiu a1, zero, 1
  jal 0x0022a2a8
  addiu a2, zero, 1
  slti at, s4, 2
  beq at, zero, noevent
  nop
  move a0, s1
  move a1, s0
  jal 0x000e1240
  daddu a2, zero, zero
  beq zero, zero, cams
  nop
noevent:
  lbu t0, 0x1b1(s0)
  addiu at, zero, 7
  bne t0, at, cams
  nop
  jal 0x000e1bac
  move a0, s3
cams:
  addiu s2, s4, 1
camloop:
  slt at, s2, s5
  beq at, zero, owners
  nop
  jal 0x0011ed60
  move a0, s2
  beq zero, zero, camloop
  addiu s2, s2, 1
owners:
  daddu s2, zero, zero
ownloop:
  lh t0, 0x224(s1)
  slt at, s2, t0
  beq at, zero, rebuild
  nop
  sll t0, s2, 2
  addu t0, t0, s1
  jal 0x00390268
  addiu a0, t0, 0x228
  jal 0x0021d3e8
  move a0, v0
  lb t1, 0x19(v0)
  bltz t1, ownnext
  sll t3, t1, 6
  sll t4, t1, 4
  addu t3, t3, t4
  lui t4, 0x005e
  addiu t4, t4, -0x27f0
  addu t3, t3, t4
  sh s2, 0x42(t3)
ownnext:
  beq zero, zero, ownloop
  addiu s2, s2, 1
rebuild:
  lui a0, 0x005d
  jal 0x004dad40
  ori a0, a0, 0x91a8
  lui at, 0x0051
  sw v0, -0x4e6c(at)
  jal 0x00122ed0
  nop
  lh t0, 0x224(s1)
  slti at, t0, 2
  bne at, zero, done
  nop
  move a0, s1
  jal 0x0041a460
  addiu a1, zero, -1
done:
  addiu s2, zero, 1
out:
  move v0, s2
  ld ra, 0(sp)
  ld s0, 8(sp)
  ld s1, 16(sp)
  ld s2, 24(sp)
  ld s3, 32(sp)
  ld s4, 40(sp)
  ld s5, 48(sp)
  jr ra
  addiu sp, sp, 64
"""

_R = {n: i for i, n in enumerate(
    "zero at v0 v1 a0 a1 a2 a3 t0 t1 t2 t3 t4 t5 t6 t7 s0 s1 s2 s3 s4 s5 s6 s7 t8 t9 k0 k1 gp sp fp ra".split())}
_MEM = {"lb": 0x20, "lh": 0x21, "lw": 0x23, "lbu": 0x24, "lhu": 0x25, "sb": 0x28, "sh": 0x29, "sw": 0x2B,
        "ld": 0x37, "sd": 0x3F}


def assemble(src, origin):
    """Minimal R5900 assembler for the test cave (labels, explicit delay slots)."""
    items, labels, pc = [], {}, origin
    for raw in src.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.endswith(":"):
            labels[line[:-1]] = pc
            continue
        items.append((pc, line))
        pc += 4
    words = []
    for pc, line in items:
        op, _, rest = line.partition(" ")
        a = [x.strip() for x in rest.split(",")] if rest else []

        def r(x):
            return _R[x]

        def i16(x):
            return int(x, 0) & 0xFFFF

        def mem(x):
            off, base = x.split("(")
            return int(off, 0) & 0xFFFF, _R[base.rstrip(")")]

        def rr(rs, rt, rd, sa, fn):
            return (rs << 21) | (rt << 16) | (rd << 11) | (sa << 6) | fn
        if op == "nop":
            w = 0
        elif op == "move":
            w = rr(r(a[1]), 0, r(a[0]), 0, 0x2D)
        elif op in ("addu", "and", "nor", "daddu", "slt"):
            w = rr(r(a[1]), r(a[2]), r(a[0]), 0, {"addu": 0x21, "and": 0x24, "nor": 0x27, "daddu": 0x2D, "slt": 0x2A}[op])
        elif op == "bltz":
            w = (1 << 26) | (r(a[0]) << 21) | (((labels[a[1]] - (pc + 4)) >> 2) & 0xFFFF)
        elif op in ("sllv", "srlv"):
            w = rr(r(a[2]), r(a[1]), r(a[0]), 0, 4 if op == "sllv" else 6)
        elif op == "sll":
            w = rr(0, r(a[1]), r(a[0]), int(a[2], 0), 0)
        elif op in ("addiu", "andi", "ori", "slti"):
            w = ({"addiu": 9, "andi": 0xC, "ori": 0xD, "slti": 0xA}[op] << 26) | (r(a[1]) << 21) | (r(a[0]) << 16) | i16(a[2])
        elif op == "lui":
            w = (0xF << 26) | (r(a[0]) << 16) | i16(a[1])
        elif op in _MEM:
            off, base = mem(a[1])
            w = (_MEM[op] << 26) | (base << 21) | (r(a[0]) << 16) | off
        elif op in ("beq", "bne"):
            off = ((labels[a[2]] - (pc + 4)) >> 2) & 0xFFFF
            w = ((4 if op == "beq" else 5) << 26) | (r(a[0]) << 21) | (r(a[1]) << 16) | off
        elif op == "jal":
            w = (3 << 26) | ((int(a[0], 0) >> 2) & 0x3FFFFFF)
        elif op == "jr":
            w = rr(r(a[0]), 0, 0, 0, 8)
        else:
            raise ValueError(line)
        words.append(w)
    return words


def _install(p):
    words = assemble(LEAVE_SRC, CAVE)
    p.batch_write32([(CAVE + 4 * i, w) for i, w in enumerate(words)])
    return len(words)


def _leave(p, idx):
    n = _install(p)
    before = snap(p)
    call = _call(p, CAVE, idx)
    time.sleep(0.5)
    return {"cave_words": n, "index": idx, "before": before, "call": call, "after": snap(p)}


def leave_p4(p):
    """Player index 3 leaves (the last index: no shift of the GameMgr player array)."""
    return _leave(p, 3)


def leave_p3(p):
    """Player index 2 leaves while index 3 exists (RemovePlayer FUN_00419C68 shifts index 3 down to 2)."""
    return _leave(p, 2)


def rejoin_cams(p):
    """UpdateJoin(GameMgr, -1) = FUN_0041A460: with the 2-player flag set and count > 1 it only makes sure every player
    is tracked and has a camera, then lays out the views (the level-start call, level_jump.md 1.3)."""
    gm = p.read32(GM_PTR)
    call = _call(p, 0x0041A460, gm, 0xFFFFFFFF)
    time.sleep(0.3)
    return {"call": call, "after": snap(p)}


def leave_p2(p):
    """Player index 1 (player 2) leaves while players 3-4 exist."""
    return _leave(p, 1)


def _leave2(p, idx):
    words = assemble(LEAVE2_SRC, CAVE2)
    p.batch_write32([(CAVE2 + 4 * i, w) for i, w in enumerate(words)])
    before = snap(p)
    call = _call(p, CAVE2, idx)
    time.sleep(0.5)
    return {"cave2_words": len(words), "index": idx, "before": before, "call": call, "after": snap(p)}


def mp_off(p):
    """2-player flag off: FUN_00419AC0(GameMgr, 0) (as the original drop-out FUN_001DF3A8 does first), so the next
    level start does not re-create player 2 from the companion (session_policies.md 4.3)."""
    gm = p.read32(GM_PTR)
    call = _call(p, 0x00419AC0, gm, 0)
    return {"call": call, "mp_56ec": p.read32(gm + 0x56EC)}


def leave2_p2(p):
    """v2 cave: player index 1 (player 2) leaves while players 3-4 exist (both move down one index)."""
    return _leave2(p, 1)


def leave2_idx2(p):
    """v2 cave: player index 2 leaves."""
    return _leave2(p, 2)

"""D23 experiment (TEST ONLY): generate the pnach groups for the "true single view" experiment.

Groups (written to stdout, append them to a copy of mod/w4p_m1.pnach under local/m6/oneview/):
  [warriors-4p test oneview pN]  N = 0..3: the game itself renders ONE full-screen view = player N's camera
      (ViewsRendered 0x0050B198 = 1, render camera list 0x000F0810 = [active camera of N], layout 1x1) whenever it
      would render 2+ views. All cameras keep their camera update (FUN_0011E878 walks a shadow copy of the list the
      game computed) and the "1 -> n views" transition in LayoutViewports reads the shadow count, so camera objects
      get the same update calls as on a normal PC. Everything else that reads the view count / render list sees the
      single view (that is the question of the experiment).
  [warriors-4p test oneview shim]  (variant S1, used together with a pN group) four human/pad readers of the view
      count / render list (FUN_001454A8, FUN_00244770, FUN_0023DC58, FUN_0024B3D8) read the shadow values instead.
  [warriors-4p test drawonly pN]  (variant R) normal multi-view game state; only the per-view world draw FUN_0040E8D8
      and sprite flush FUN_00185B38 are skipped for views other than N.
  [warriors-4p test fixedlod]  0x0050C698 = 0 (no frame-time-adaptive draw distance; prepared, not run).
  [warriors-4p test simsnap]  snapshot function SNAP(slot) at 0x000E2600 for W4P CallAt: copies/hashes simulation
      state (players, all 60 humans, AI brains, GameMgr, RNGs, camera vectors/objects) into a ring at 0x000E9800 (20 x 0x200).
      Enable it on EVERY instance (identical code), so it cannot cause a difference itself.
Usage: python -I tests/m6/oneview_patch.py > local/m6/oneview/groups.txt
Our labels: OV_CAVE, SHGET, SNAP, HASHR. Nothing here is game code; "was" words are checked against the ELF.
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(PROJ, "tools"))
from mips_asm import assemble, r as reg  # noqa: E402

ELF = os.path.join(PROJ, "local", "disc", "SLUS_212.15")

OV_CAVE = 0x000E5E00  # one-view cave (free range 0x000E5D10-0x000E6FFF)
SHGET = 0x000E5E80    # shadow render-list getter
SH_VIEWS = 0x000E5F00  # shadow: views count the game computed
SH_LIST = 0x000E5F10   # shadow: render list the game computed (4 words)
SHIM = 0x000E5F40      # variant S code
SNAP = 0x000E2600      # snapshot function (free range 0x000E2580-0x000E2FFF)
SNAPBUF = 0x000E9800   # 20 records x 0x200 (free range 0x000E9800-0x000EBFFF)
REC = 0x200


def elf_word(addr, _c={}):
    if "d" not in _c:
        d = open(ELF, "rb").read()
        phoff = struct.unpack_from("<I", d, 0x1C)[0]
        phnum = struct.unpack_from("<H", d, 0x2C)[0]
        segs = []
        for i in range(phnum):
            t, off, va, pa, fs, ms = struct.unpack_from("<6I", d, phoff + i * 32)
            if t == 1:
                segs.append((va, off, fs))
        _c["d"], _c["s"] = d, segs
    for va, off, fs in _c["s"]:
        if va <= addr < va + fs:
            return struct.unpack_from("<I", _c["d"], off + addr - va)[0]
    return None


def asm(src, origin):
    """mips_asm plus: xor rd,rs,rt; sltiu rt,rs,imm; .word X (one line = one instruction, so labels stay right)."""
    lines, extra = [], {}
    n = 0
    for raw in src.splitlines():
        line = raw.split("#")[0].strip()
        labs = []
        while ":" in line:
            lab, line = line.split(":", 1)
            labs.append(lab.strip())
            line = line.strip()
        op, _, rest = line.partition(" ")
        a = [s.strip() for s in rest.split(",")] if rest else []
        if op == "xor":
            extra[n] = (reg(a[1]) << 21) | (reg(a[2]) << 16) | (reg(a[0]) << 11) | 0x26
            line = "nop"
        elif op == "sltiu":
            extra[n] = (0x0B << 26) | (reg(a[1]) << 21) | (reg(a[0]) << 16) | (int(a[2], 0) & 0xFFFF)
            line = "nop"
        elif op == ".word":
            extra[n] = int(a[0], 0) & 0xFFFFFFFF
            line = "nop"
        lines.append("".join(f"{x}: " for x in labs) + line)
        if line:
            n += 1
    words, labels = assemble("\n".join(lines), origin)
    for i, w in extra.items():
        words[i] = w
    return words, labels


def j(t):
    return 0x08000000 | ((t >> 2) & 0x3FFFFFF)


def jal(t):
    return 0x0C000000 | ((t >> 2) & 0x3FFFFFF)


def site(addr, new, was, note):
    old = elf_word(addr)
    assert old == was, f"{addr:08X}: ELF has {old:08X}, expected {was:08X}"
    return f"patch=2,EE,{addr:08X},word,{new:08X} // was {was:08X}: {note}"


def cave(words, origin, notes=None):
    return [f"patch=2,EE,{origin + 4 * i:08X},word,{w:08X}" for i, w in enumerate(words)]


def oneview(n):
    src = f"""
  lui t0, 0x51
  lw t1, -0x4E68(t0)        # real views 0x0050B198
  lui t2, 0x000E
  sw t1, {SH_VIEWS & 0xFFFF:#x}(t2)
  lui t3, 0x000F
  lw t4, 0x810(t3)
  sw t4, {SH_LIST & 0xFFFF:#x}(t2)
  lw t4, 0x814(t3)
  sw t4, {(SH_LIST + 4) & 0xFFFF:#x}(t2)
  lw t4, 0x818(t3)
  sw t4, {(SH_LIST + 8) & 0xFFFF:#x}(t2)
  lw t4, 0x81C(t3)
  sw t4, {(SH_LIST + 12) & 0xFFFF:#x}(t2)
  sltiu at, t1, 2
  bne at, zero, done        # 0 or 1 view: leave the game's layout alone (cut-scenes, menus, one player)
  nop
  lw t5, {0x800 + 4 * n:#x}(t3)  # active camera of player {n}
  beq t5, zero, done
  nop
  sw t5, 0x810(t3)          # render list = [camera of player {n}]
  sw zero, 0x814(t3)
  sw zero, 0x818(t3)
  sw zero, 0x81C(t3)
  addiu t6, zero, 1
  sw t6, -0x4E68(t0)        # views = 1
  lw t7, -0x4E60(t0)        # split orientation 0x0050B1A0
  sw t7, -0x4E5C(t0)        # layout mode 0x0050B1A4 = orientation (what the game sets for one view)
  sh t6, -0x4E58(t0)        # 0x0050B1A8 = 1
  sh t6, -0x4E56(t0)        # 0x0050B1AA = 1
done:
  .word 0x7BB100B0          # lq s1,0xb0(sp) (original 0x00123390)
  j 0x00123398
  nop
"""
    w, _ = asm(src, OV_CAVE)
    assert OV_CAVE + 4 * len(w) <= SHGET
    g = [f"[warriors-4p test oneview p{n}]", "author=warriors-4p",
         f"description=TEST ONLY (D23 experiment): render one full-screen view = player {n + 1}'s camera; all cameras keep updating.", ""]
    g.append(site(0x00123390, j(OV_CAVE), 0x7BB100B0, f"lq s1,0xb0(sp) -> j 0x{OV_CAVE:08X} (LayoutViewports epilogue; delay slot lq s2 kept)"))
    g.append(site(0x00122EDC, 0x3C03000E, 0x3C030051, "lui v1,0x51 -> lui v1,0xe"))
    g.append(site(0x00122EE8, 0x8C630000 | (SH_VIEWS & 0xFFFF), 0x8C63B198, "previous views from the shadow (keeps the 1 -> n transition as on a normal PC)"))
    g.append(site(0x0011E8A4, jal(SHGET), 0x0C047E6C, "camera update: first camera from the shadow list"))
    g.append(site(0x0011E908, 0x3C03000E, 0x3C030051, "lui v1,0x51 -> lui v1,0xe (s1 = shadow base)"))
    g.append(site(0x0011E90C, 0x8C620000 | (SH_VIEWS & 0xFFFF), 0x8C62B198, "camera update loop bound = shadow views"))
    g.append(site(0x0011E920, jal(SHGET), 0x0C047E6C, "camera update loop: cameras from the shadow list"))
    g.append(site(0x0011E948, 0x8E220000 | (SH_VIEWS & 0xFFFF), 0x8E22B198, "camera update loop bound = shadow views"))
    g += cave(w, OV_CAVE)
    g += cave(shget_words(), SHGET)
    return g


def shget_words():
    src = f"""
  lui v0, 0x000E
  sll t0, a0, 2
  addu t1, v0, t0
  lw v0, {SH_LIST & 0xFFFF:#x}(t1)   # shadow[i]
  beq v0, zero, real
  nop
  lui t2, 0x000F
  lw t3, 0x800(t2)
  beq t3, v0, ok            # still an active camera of some player?
  nop
  lw t3, 0x804(t2)
  beq t3, v0, ok
  nop
  lw t3, 0x808(t2)
  beq t3, v0, ok
  nop
  lw t3, 0x80C(t2)
  beq t3, v0, ok
  nop
real:
  lui t2, 0x000F
  addu t2, t2, t0
  lw v0, 0x810(t2)          # the game's real render list
ok:
  jr ra
  nop
"""
    w, _ = asm(src, SHGET)
    assert SHGET + 4 * len(w) <= SH_VIEWS
    return w


def shim():
    """Variant S1: the four human/pad functions known to branch on the view count (PadUpdateAll FUN_001454A8,
    player movement FUN_00244770, camera auto-follow FUN_0023DC58, FUN_0024B3D8) read the shadow (multi-view) count
    and the shadow render list. Drawing code still sees the single view."""
    g = ["[warriors-4p test oneview shim]", "author=warriors-4p",
         "description=TEST ONLY (D23 experiment, use with a oneview pN group): 4 human/pad functions read the shadow view count and render list.", ""]
    shim_p = SHIM
    w, _ = asm(f"""
  lui v1, 0x000E
  lw v1, {SH_VIEWS & 0xFFFF:#x}(v1)
  j 0x00145504
  nop
""", shim_p)
    camskip2 = shim_p + 4 * len(w)
    w2, _ = asm(f"""
  lui v0, 0x000E
  lw v0, {SH_VIEWS & 0xFFFF:#x}(v0)
  sltu at, a0, v0
  beq at, zero, skip
  lui v0, 0x000E
  sll at, a0, 2
  addu at, at, v0
  lw v0, {SH_LIST & 0xFFFF:#x}(at)
  bne v0, zero, ret
  nop
skip:
  lui ra, 0x0024
  ori ra, ra, 0x4BB0
ret:
  jr ra
  nop
""", camskip2)
    assert camskip2 + 4 * len(w2) <= 0x000E5FC0
    g.append(site(0x001454FC, j(shim_p), 0x8FC3B198, "PadUpdateAll: views from the shadow (cave; delay slot lw v0 cams kept)"))
    for a in (0x00145514, 0x00145594, 0x001455A4):
        g.append(site(a, jal(SHGET), 0x0C047E6C, "PadUpdateAll: render camera from the shadow list"))
    g.append(site(0x00244A68, 0x3C03000E, 0x3C030051, "FUN_00244770: lui v1,0x51 -> 0xe"))
    g.append(site(0x00244A70, 0x8C650000 | (SH_VIEWS & 0xFFFF), 0x8C65B198, "FUN_00244770: views == cameras test reads the shadow"))
    g.append(f"patch=2,EE,00244A80,word,{jal(camskip2):08X} // [4p] sets 0C03C3D0 (CAMSKIP): CAMSKIP2 = CAMSKIP with the shadow count/list (TEST: overrides the [4p] word)")
    g.append(site(0x0023DDE8, 0x3C03000E, 0x3C030051, "FUN_0023DC58: lui v1,0x51 -> 0xe"))
    g.append(site(0x0023DDF0, 0x8C650000 | (SH_VIEWS & 0xFFFF), 0x8C65B198, "FUN_0023DC58: player count == views test reads the shadow"))
    g.append(site(0x0023DE10, jal(SHGET), 0x0C047E6C, "FUN_0023DC58: player's render camera from the shadow list"))
    g.append(site(0x0024B3D8, 0x3C02000E, 0x3C020051, "FUN_0024B3D8: lui v0,0x51 -> 0xe"))
    g.append(site(0x0024B3E0, 0x8C450000 | (SH_VIEWS & 0xFFFF), 0x8C45B198, "FUN_0024B3D8: views from the shadow"))
    g.append(site(0x0024B510, jal(SHGET), 0x0C047E6C, "FUN_0024B3D8: render camera 0 from the shadow list"))
    return g + cave(w, shim_p) + cave(w2, camskip2)


DRAWGATE = 0x000E6000  # variant R gates (free range 0x000E5D10-0x000E6FFF)


def drawonly(n):
    """Variant R ("draw only my view"): the game keeps its normal multi-view state (view count, render list, layout,
    HUD, cameras: identical to a normal PC); only the per-view world draw FUN_0040E8D8(world, v) and sprite flush
    FUN_00185B38(mgr, v) are skipped for every view v != n while 2+ views are shown. Tests whether drawing fewer views
    changes the simulation."""
    out = []
    for k, (target, sites) in enumerate(((0x0040E8D8, (0x001564C4, 0x001565F0)), (0x00185B38, (0x001564EC, 0x0015661C)))):
        gate = DRAWGATE + 0x40 * k
        w, _ = asm(f"""
  addiu at, zero, {n}
  beq a1, at, go
  nop
  lui at, 0x51
  lw at, -0x4E68(at)        # views 0x0050B198
  sltiu at, at, 2
  bne at, zero, go          # one view: draw it
  nop
  jr ra                     # another player's view: skip drawing it
  nop
go:
  j {target:#x}
  nop
""", gate)
        assert len(w) * 4 <= 0x40
        for a in sites:
            out.append(site(a, jal(gate), jal(target), f"per-view draw call -> gate (view {n} only)"))
        out += cave(w, gate)
    return [f"[warriors-4p test drawonly p{n}]", "author=warriors-4p",
            f"description=TEST ONLY (D23 experiment): normal multi-view game state, but only view {n} (player {n + 1}) is drawn (world + sprites).", ""] + out


def fixedlod():
    """Variant R3 helper (both instances): switch off the game's frame-time-adaptive draw distance (0x0050C698 = 0;
    FUN_0040E8D8 otherwise moves render camera 0's far distance (+0x58, setter FUN_00122128) with the measured
    frame rate 0x0050C680 from FrameStats FUN_001569C0)."""
    return ["[warriors-4p test fixedlod]", "author=warriors-4p",
            "description=TEST ONLY (D23 experiment): no frame-time-adaptive draw distance (0x0050C698 = 0 every vsync).", "",
            "patch=1,EE,0050C698,word,00000000 // dynamic draw distance flag, 1 in M13 (dump ov1_pure)"]


ROT = lambda x: f"  sll at, {x}, 5\n  srl {x}, {x}, 27\n  or {x}, {x}, at\n"  # noqa: E731


def simsnap():
    src = f"""
  addiu sp, sp, -16
  sw ra, 0(sp)
  sll t0, a0, 9             # slot * 0x200
  lui t9, 0x000E
  ori t9, t9, {SNAPBUF & 0xFFFF:#x}
  addu t9, t9, t0           # t9 = record
  sw zero, 0x1FC(t9)        # marker cleared until the record is complete
  lui t0, 0x000F
  lw t1, 0x500(t0)
  sw t1, 0(t9)              # w0 poll counter
  lui t0, 0x0051
  lw t8, 0x489C(t0)         # GameMgr
  sw t8, 4(t9)              # w1
  beq t8, zero, nogm
  nop
  lw t1, 0x224(t8)
  sw t1, 8(t9)              # w2 player count word
  lw t1, 0x338(t8)
  sw t1, 12(t9)             # w3 checkpoint word (+0x33A)
  lw t1, 0x56DC(t8)
  sw t1, 16(t9)             # w4 level index word
  lw t1, 0x14C(t8)
  sw t1, 20(t9)             # w5 level end / game over
nogm:
  lui t0, 0x0051
  lw t1, 0x69EC(t0)         # newlib reent pointer 0x005169EC
  lw t1, 0x58(t1)
  sw t1, 24(t9)             # w6 rand() state
  lui t0, 0x006F
  lw t1, -0x4758(t0)        # 0x006EB8A8 static RNG object (table index)
  sw t1, 28(t9)             # w7
  addiu t7, zero, 0
ploop:
  sll t0, t7, 2
  addu t1, t9, t0
  addiu t2, zero, 0
  beq t8, zero, phave
  nop
  addu t3, t8, t0
  lw t2, 0x228(t3)
phave:
  sw t2, 32(t1)             # w8+i handle
  addiu t4, zero, 0
  beq t2, zero, pres
  nop
  addiu t3, zero, -1
  beq t2, t3, pres
  nop
  srl t3, t2, 16
  sll t3, t3, 3
  lui t5, 0x006F
  addu t5, t5, t3
  lw t4, -0x42C8(t5)        # object table 0x006EBD38
pres:
  sll t3, t7, 3
  addu t3, t3, t0
  addu t3, t3, t9           # record + 12 i
  addiu t5, zero, 0
  addiu t6, zero, 0
  addiu a1, zero, 0
  addiu a2, zero, 0
  beq t4, zero, pst
  nop
  lw t5, 0x10(t4)
  lw t6, 0x14(t4)
  lw a1, 0x18(t4)
  lw a3, 0xD4(t4)
  srl a0, a3, 20
  beq a0, zero, pst
  nop
  sltiu a0, a0, 0x20
  beq a0, zero, pst
  nop
  lw a2, 0x144(a3)
pst:
  sw t5, 48(t3)             # w12+3i position
  sw t6, 52(t3)
  sw a1, 56(t3)
  sw a2, 96(t1)             # w24+i health word
  addiu t7, t7, 1
  sltiu a0, t7, 4
  bne a0, zero, ploop
  nop
  addiu v0, zero, 0
  addiu v1, zero, 0
  addiu t7, zero, 0
  lui t4, 0x0064
  ori t4, t4, 0x0C80        # human pool 0x00640C80, 60 x 0x6D0
hloop:
  lw t0, 0x10(t4)
  lw t1, 0x14(t4)
  lw t2, 0x18(t4)
  lw t3, 0x1B0(t4)
  addiu t5, zero, 0
  lw t6, 0xD4(t4)
  srl a0, t6, 20
  beq a0, zero, hnohp
  nop
  sltiu a1, a0, 0x20
  beq a1, zero, hnohp
  nop
  lw t5, 0x144(t6)
hnohp:
  move a2, t0
{ROT('a2')}  xor a2, a2, t1
{ROT('a2')}  xor a2, a2, t2
{ROT('a2')}  xor a2, a2, t3
{ROT('a2')}  xor a2, a2, t5
  sll a3, t7, 2
  addu a3, a3, t9
  sw a2, 128(a3)            # w32+k per-human hash (position, +0x1B0, health)
{ROT('v0')}  xor v0, v0, a2
{ROT('v1')}  xor v1, v1, t5
  addiu t4, t4, 0x6D0
  addiu t7, t7, 1
  sltiu a0, t7, 60
  bne a0, zero, hloop
  nop
  sw v0, 112(t9)            # w28 all humans
  sw v1, 116(t9)            # w29 all health
  lui a0, 0x006D
  ori a0, a0, 0x53F0        # brains 0x006D53F0, 60 x 0x2F0
  addiu a1, zero, 11280
  jal hashr
  nop
  sw v0, 120(t9)            # w30
  addiu v0, zero, 0
  beq t8, zero, nogm2
  nop
  move a0, t8
  addiu a1, zero, 5632      # GameMgr 0x5800 bytes
  jal hashr
  nop
nogm2:
  sw v0, 124(t9)            # w31
  lui a0, 0x0064
  ori a0, a0, 0x0C80
  addiu a1, zero, 26160     # whole human pool (includes animation state)
  jal hashr
  nop
  sw v0, 368(t9)            # w92
  lui a0, 0x006F
  addiu a0, a0, -0x42C8     # object table 0x006EBD38, 64 x 8
  addiu a1, zero, 128
  jal hashr
  nop
  sw v0, 372(t9)            # w93
  lui t0, 0x0051
  lw t1, -0x39AC(t0)        # 0x0050C654 game frame counter
  sw t1, 376(t9)            # w94
  lui a0, 0x005E
  addiu a0, a0, -0x2370     # 0x005DDC90 per-player camera vectors used by PadUpdateAll (4 x 16 bytes)
  addiu t7, zero, 0
cvloop:
  sll t0, t7, 2
  addu t1, a0, t0
  lw t2, 0(t1)
  addu t3, t9, t0
  sw t2, 384(t3)            # w96..w111
  addiu t7, t7, 1
  sltiu t0, t7, 16
  bne t0, zero, cvloop
  nop
  addiu t7, zero, 0
camloop:
  sll t0, t7, 2
  lui t1, 0x000F
  addu t1, t1, t0
  lw a0, 0x800(t1)          # active camera of player i (0x000F0800)
  addiu v0, zero, 0
  beq a0, zero, camnone
  nop
  jal hashr
  addiu a1, zero, 288       # 0x480 bytes
camnone:
  sll t0, t7, 2
  addu t3, t9, t0
  sw v0, 448(t3)            # w112..w115 camera object hashes
  addiu t7, t7, 1
  sltiu t0, t7, 4
  bne t0, zero, camloop
  nop
  lui a0, 0x0071
  ori a0, a0, 0x4B00        # 0x00714B00 per-human 0x20 table (60 entries)
  jal hashr
  addiu a1, zero, 480
  sw v0, 464(t9)            # w116
  lui t1, 0x534E
  ori t1, t1, 0x4150
  sw t1, 0x1FC(t9)          # w127 marker 'SNAP'
  lw ra, 0(sp)
  addiu v0, zero, 1
  jr ra
  addiu sp, sp, 16
hashr:
  addiu v0, zero, 0
hr_loop:
  beq a1, zero, hr_done
  nop
  lw a2, 0(a0)
{ROT('v0')}  xor v0, v0, a2
  addiu a0, a0, 4
  addiu a1, a1, -1
  beq zero, zero, hr_loop
  nop
hr_done:
  jr ra
  nop
"""
    w, labels = asm(src, SNAP)
    assert SNAP + 4 * len(w) <= 0x000E3000, hex(SNAP + 4 * len(w))
    g = ["[warriors-4p test simsnap]", "author=warriors-4p",
         f"description=TEST ONLY (D23 experiment): simulation snapshot SNAP(slot) at 0x{SNAP:08X} for W4P CallAt (ring 0x{SNAPBUF:08X}).", ""]
    return g + cave(w, SNAP)


def main():
    out = []
    for n in range(4):
        out += oneview(n) + [""]
    out += shim() + [""]
    for n in range(4):
        out += drawonly(n) + [""]
    out += fixedlod() + [""]
    out += simsnap() + [""]
    sys.stdout.write("\r\n".join(out) + "\r\n")


if __name__ == "__main__":
    main()

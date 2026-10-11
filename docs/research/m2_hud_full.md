# M2 research: full HUD for four players, option (B) (static analysis, 2026-10-11)

Task: give players 3-4 a radar and a health/rage panel in their own (bottom-row) quarters; make every HUD element look
like a single-player HUD inside each player's quarter after the 2x presentation crop (including the rage panel of
players 1-2, F-0103, and centred text); say what changes in the interim guards (A); order the work into small testable
steps.

Sources and conventions:
- **Static analysis only; nothing was run.** Build: SLUS-21215 v1.03 (`local/disc/SLUS_212.15`). Addresses are static
  (ELF) unless marked.
- Function names are OUR labels. HUD = the static HUD manager at **0x00600840**; PlayerHUD = the per-player HUD object.
- Every "was" word in the appendices was read from the ELF. `python -I tools/note_patches.py check` with the current
  `mod/w4p_m1.pnach` minus the 6 lines that (B) deliberately supersedes (section 4) plus both fragments: **1,447
  addresses in 3 files, 0 problems**. With the full pnach the checker reports exactly those 6 intended conflicts.
- Builds on `m2_hud_players34.md` (crash chain, option (A), option (B) outline, split-view addenda), `m2_hud_scripts.md`
  (per-view HUD idea), `hud_scale.md` (HUD cameras, radar formula 2A, patch 2B) and `m2_pads_cameras.md` section 4
  (camera entries 2-3 at 0x000F0900/0x000F0920).

---

## 1. Findings this design rests on

### 1.1 PlayerHUD objects (VERIFIED, decompile + disassembly)
| Item | Value | Evidence |
|---|---|---|
| Normal PlayerHUD class | constructor `FUN_00211CA0`, size 0x4A50, vtable pointer at +0x4120 = **0x0053EDF8** | HUD constructor `FUN_001ACEE0` loop constructs 2 at HUD+0x19130 (stride 0x4A50) |
| Levels 60-69 class | heap objects of 0x4620 bytes, constructor `FUN_0020FD80`, vtable 0x0053ECC0 | `FUN_001AD588` 0x001AE1F8-0x001AE258 (game allocator `*(0x005127E4)` vtable +0x54) |
| Vtable (normal) | +0x14 Init(slot) = `FUN_00212840`; +0x24 Activate = `FUN_0020DB98` (+0x40F8 = 1); +0x2C Deactivate = `FUN_0020DBC0`; +0x34 Bind(human) = `FUN_0020DC98`; +0x44 Update = `FUN_00214138` | ELF words at 0x0053EDF8.. (entries are 8 bytes: s16 this-adjust, function) |
| Pointer table | HUD+8 / HUD+0xC (0x00600848/0x0060084C), filled by the loop 0x001AE1F0-0x001AE27C | listing |
| Slot claim | MakePlayer loops slots with `sltiu v0,s0,2` (0x00229E84) around `FUN_001B2200(HUD, human, slot)`; that function refuses slot >= 2 (0x001B2220), runs Init if +0x4100 == 0, then Activate, Bind, and returns the slot, which MakePlayer stores in human+0x380 | listings 0x00229E60-0x00229ECC, 0x001B2200-0x001B22E8 |
| Per-frame update | HudUpdate calls Update (vtable +0x44) for exactly 2 PlayerHUDs: fixed loop 0x001B0FA4-0x001B10B8 (`slti v0,s0,2`), together with the 2-entry inventory/weapon/special/target objects | listing |

### 1.2 The slot field +0x40F4 and a free field +0x40F0 (VERIFIED, exhaustive immediate scan of the ELF)
- Init stores the slot at +0x40F4 (0x00212884). The 8 normal-class functions load +0x40F4 **127 times**:
  - **112 loads are layout-table indices** (the value is multiplied by 0x240, 0xC0, 0x90 or 16 into the static tables
    0x0050FA10 / 0x0050FA40 / 0x0050FEC0), including two compares that only select the right-hand layout
    (0x002137D0, 0x002141AC);
  - **1 identity compare**: the Update loop that finds the player human with human+0x380 == +0x40F4 (0x002142E4);
  - **1 colour choice** (0x002128A8: slot 1 gets the swapped name colours);
  - **13 argument loads** that pass the slot to child objects (identity searches by slot, inventory queries).
- **+0x40F0 is never read** by any code: the only accesses with that immediate are the stores of -1 in the two
  constructors and the two Inits (0x0020FF88, 0x00210844, 0x00211E94, 0x00212888). It is a free word in every PlayerHUD.
- The static layout tables have exactly 2 entries; entry 0 is the left-aligned (P1/single-player) layout and entry 1 the
  mirrored right-aligned one (11 differing words in the 0x240-byte element table, all x offsets/alignment). Entry 2/3
  would read and write the following tables and globals (0x0050FEC0.., 0x00510040..).
- `FUN_00211EF8` (called at the top of every Update, before the "active" checks) writes the table entry of its index
  every frame. For a never-initialised PlayerHUD (+0x40F4 = -1) the original game therefore writes table index -1 every
  frame in single-player.

### 1.3 Children that use the slot (VERIFIED)
| Child (offset in PlayerHUD) | Uses the slot for | Effect of slot 2/3 |
|---|---|---|
| +0x70 (`FUN_001C7730`), +0x40 of `FUN_001BEA00`, `FUN_001AAF88`, +0xF0 of the +0x3480 child | identity: find the human with human+0x380 == stored slot | correct only with the real slot |
| inventory queries `FUN_001C68E8`, `FUN_001C96E0`, `FUN_001AADF0` | `FUN_0041E420(GameMgr+0x480, slot, n)` | return 0 for slot > 1 (no items shown), safe |
| `FUN_001C6950`, `FUN_001C9748`, `FUN_001AB038`, `FUN_001AAE58` | write `*(0x00600848[slot] + 0x411C) = 0` | **out-of-range write** unless redirected |
| +0x3480 child `FUN_001BF7E0(child, slot)` | static table 0x00622E50 + slot*0x90 (2 entries) | out-of-range read unless given the column |

### 1.4 Radar (VERIFIED)
- Radar objects are plain structs (no vtable), 0x2940 bytes, at HUD+0x15D0/+0x3F10. The HUD constructor only sets
  fields: +0x20 = +0x28 = 50.0, +0x24 = 75.0, +0x18 = 1, and for 128 entries at +0x920 (stride 0x40) +0x10 = +0x24 = -1.
- Per level: `FUN_001C3DE0(radar, index)` when radar+0 == 0 (`FUN_001C42E0` returns +0). +0x90 = index = **player
  index** (the radar fetches its human via GameMgr+0x228+4*index), +4 = visible, `FUN_001C4388` shows its markers.
- Per frame: HudUpdate sets the position vector +0x2930 = (x, depth, z, 1) and calls `FUN_001C5210(radar, camera
  entry)`; the camera entry is the per-player 0x20-byte record built by the main loop (entries 2-3 are in the static
  buffer at **0x000F0900/0x000F0920** since `m2_pads_cameras.md` section 4). Draw: `FUN_001B1688` calls
  `FUN_001C60B0(radar)` for P1, and for P2 only in split view (0x001B1A20). The radar draws immediately on the global
  HUD camera (not through the sprite flush).

### 1.5 How a HUD element gets its view (VERIFIED)
- Element init `FUN_001A1DB8` stores its view argument at element+0xF9 (0x001A1E10) and allocates its sprite at once
  (`FUN_001A2918(element, -1)`), which passes +0xF9 down to `FUN_001828E0`; that stores it in the sprite item at +0x42
  (0x0018296C). Panel elements are created inside PlayerHUD Init, i.e. inside `FUN_001B2200`.
- The sprite flush `FUN_00185D20`: item view v < views -> per-view HUD camera v (camera manager vtable +0x7C, then
  begin +0x64 / draw `FUN_00197168(item, v)` / end +0x6C); otherwise the global HUD camera path (0x00185EE8/0x00185EEC).

---

## 2. Design

### 2.1 Players 3-4: real slots 2-3, a 4-entry pointer table, layout by column
- **Two more normal PlayerHUDs and two more radars in free low RAM** (F-0050 range, all zero in the ELF image and in
  gameplay dumps; that nothing else ever uses it is a HYPOTHESIS):

  | Range | Use |
  |---|---|
  | 0x000A0000-0x000A4A4F | PlayerHUD 2 (normal class) |
  | 0x000A4A50-0x000A949F | PlayerHUD 3 |
  | 0x000A9500-0x000ABE3F | radar 3 (player index 2) |
  | 0x000ABE40-0x000AE77F | radar 4 (player index 3) |
  | 0x000E0000-0x000E000F | **T_B**[4] PlayerHUD pointers (for `FUN_001B2200`) |
  | 0x000E0010 | **CUR**: current HUD player context (-1 = none; place-0 data line) |
  | 0x000E0014/0x000E0018 | one-time radar marker activation flags (index 2/3) |
  | 0x000E0100-0x000E05EF | B1 caves (316 words) |
  | 0x000E0844 | must stay 0 (T_A[-1], so slot -1 yields a null PlayerHUD) |
  | 0x000E0848-0x000E0857 | **T_A**[4] PlayerHUD pointers (same low half 0x0848 as 0x00600848) |
  | 0x000E0900-0x000E0A57 | B2 caves (86 words) |

  59,168 bytes of objects in total. The heap alternative (the game allocator call used for the levels 60-69
  PlayerHUDs) is possible, but its headroom is unknown, so static free RAM is used here.
- **Why two tables:** sites that build `0x00600840 + 8 + 4*slot` from `lui rX,0x0060` need only that lui changed to
  0x000E to read T_A (0x000E0848); `FUN_001B2200` builds the address from the HUD argument plus 8, so its `addiu v1,s2,8`
  becomes `lui v1,0x000E` and reads T_B (0x000E0000). Both tables are written together by B_INIT.
- **Layout by column:** the 112 layout loads of +0x40F4 become loads of +0x40F0 (one immediate each). B_INIT writes the
  column there (PlayerHUD 0/2 -> 0, PlayerHUD 1/3 -> 1); Init no longer overwrites it (0x00212888 -> nop). So players
  3/4 reuse the P1/P2 table entries (in range), while +0x40F4 stays the real slot for identity and for the children. The
  +0x3480 child gets the column for its own 2-entry table (0x00212FB0) and the real slot written back after Init
  (POSTINIT writes child+0xF0 = +0x3570).
- **B_INIT** (hooked after the pointer loop in `FUN_001AD588`, 0x001AE284): fills T_A/T_B, constructs PlayerHUD 2/3
  and the radar defaults once (guarded by the vtable word / the 50.0 marker), writes the columns, releases PlayerHUD 2/3
  if still active (level start), and runs the per-level radar init `FUN_001C3DE0(radar, 2/3)`.
- **Slot claim:** MakePlayer (0x00229E84) and `FUN_001B2200` (0x001B2220) accept slots 0..3; Init accepts slots 0..3
  (0x0021285C). CLAIM/CLRCUR set and clear the HUD player context for the whole claim; POSTINIT gives players 3/4 their
  own name colours (blue 0xFFE0A040/0xFFBC5323, green 0xFF60D860/0xFF208A20; byte order as the game's own constants
  at 0x002128D4-0x002128F8).
- **Per frame:** UPD34 (hooked after HudUpdate's fixed PlayerHUD loop, 0x001B10C4) updates PlayerHUD slots 2/3 with the
  context set, and positions/updates radars 3/4 (2A formula, bottom row: x = xs -/+ d*W, z = zs - d*Wz, depth = 2d, with
  d = [0x0050D42C], xs = [0x0050D428], zs = [0x0050D430], S = [0x0050B20C], A = [0x0050B208], Wz = S/2, W = A*S/2;
  visibility mirrors P1's radar at 0x00601E14). RDRAW (0x001B1A20) draws radars 3/4 after P2's radar in split view.
- **Redirected table users (19 one-word luis + 2 in-place rewrites + 2 words of the EnableCommand window):** the four
  +0x411C writers, `FUN_001C7928` x2, `FUN_001BECB0`, `FUN_0022A2A8` (release), `FUN_002843F8` x2, the four +0x3480
  updaters, `FUN_0041EEB8`, the Lua bindings `FUN_001B3F58`/`FUN_001B4438`/`FUN_001B46A0`/`FUN_001B4948`, and
  `FUN_001B23D0`/`FUN_001B2400` (show/hide by slot; rewritten in place with a slot < 0 check). Each lui was checked to
  feed only the table access (register-tracking scan + listings).

### 2.2 Per-view HUD (task 2)
- **Patch 2B** (`hud_scale.md`; 0x00196370 -> 46000506, 0x00196398 -> 460003C6): the per-view HUD cameras keep the
  full-screen window, so a view-tagged item is drawn at half size, at its single-player relative position, inside its
  quarter. After the 2x crop it looks like the single-player HUD.
- **Tag player-owned items with their view:** while CUR >= 0, an untagged (0xFF) element/sprite gets view = CUR:
  - ETAG at the element (0x001A1E0C; the original `sb v0,0xF9(s0)` stays in the delay slot), so later sprite
    re-allocations keep the tag;
  - VTAG at the sprite item (0x0018296C), for widget classes that do not use `FUN_001A1DB8`.
- **Context:** CUR = HUD slot during the claim (`FUN_001B2200`), during PlayerHUD 0/1 Update (VCALL01 around the jalr at
  0x001B0FB4) and during PlayerHUD 2/3 Update (UPD34). HYPOTHESIS: **view index = HUD slot = player index** (true while
  all players are rendered in order; see section 5).
- **Shared items in every quarter:** SHARED replaces the global-camera path of the flush (0x00185EEC/0x00185EF0). In
  layout mode 2 ([0x0050B1A4] == 2) with 2+ views, an untagged item is drawn once per view through that view's HUD
  camera (same begin/state/draw/end sequence as the original per-view path); otherwise the original path runs. Centred
  text, objectives, prompts and subtitles then appear as half-size single-player copies in every quarter instead of
  across the quarter corners.
- Merged view or cutscenes (views 1): view 0 items use per-view camera 0 (full screen, unchanged look); items tagged 1-3
  fall back to the global camera at their table position, as in the original.
- The radar is drawn on the global HUD camera directly, so it keeps the 2A positioning (P1/P2 by `[warriors-4p hud]`,
  P3/P4 by RADAR_UPDATE).

---

## 3. Small testable steps (all HYPOTHESIS until run)
| Step | Apply | Expected | Checks (PINE / log) |
|---|---|---|---|
| B0 | W4P: move `kGameRamStart` (`emulator/pcsx2/pcsx2/W4P/W4P.cpp:54`) from 0x000F0000 to 0x00090000 | the new objects and tables count as game memory in the desync hash | hash streams still equal in a 2-player run |
| B1a | fragment B1 without the UPD34/RDRAW hooks (drop the lines 0x001B10C4 and 0x001B1A20) | 2-player game unchanged; with 4 players: human+0x380 = 2/3 for players 3/4, no crash, no TLB miss | T_A 0x000E0848.. and T_B 0x000E0000.. = 4 non-zero pointers; read32(T[2]+0x4120) = 0x0053EDF8; +0x40F4 = slot, +0x40F0 = column, +0x40F8 = 1 after the claim; read32(0x000E0010) = 0xFFFFFFFF between frames; DebugWatch on HUD+0x10..0x17 silent |
| B1b | + the UPD34 hook | players 3/4 panels update (health follows their own human); without B2 they overlap P1/P2's panels (same column positions) | screenshot; player 3's health bar changes when player 3 is hit |
| B1c | + the RDRAW hook | radars 3/4 drawn in the bottom quarters at single-player size in split view | radar3+0 != 0, +0x2930 = (x, 2d, z, 1); screenshot |
| B2a | fragment B2 without the SHARED lines | every player's panel half size in its own quarter (players 1-2 too: fixes F-0103) | 4 cropped screenshots |
| B2b | + SHARED (0x00185EEC/0x00185EF0) | centred hints/objectives appear in each quarter | screenshot of a tutorial hint |
| B3 | 4-instance lockstep run with B1+B2 (`tests/m2/m2_run4.py --crop`) | 0 hash mismatches | hash logs |

---

## 4. What changes in the interim guards (A) when (B) is applied (task 3)
| (A) part | With (B) |
|---|---|
| MIN2 clamp of the three HUD count loops (0x001B1450/5C, 0x001B15D4/E4, 0x001B1B7C/80) | **keep**: those loops index HUD-level 2-entry arrays (target objects HUD+0x6B40, HUD+0x177BC, slot table 0x0050EA90) |
| Main-loop pause/prompt cave (0x00158ECC/D4) | **keep**: players 3-4 still cannot open the pause menu (the session pause policy will own pause) |
| Marker words 0x0024A2D4 / 0x0024ABD8 | **keep** (marker globals stay 2 entries; no 3P/4P art) |
| S1-S7 slot guards (`slot < 2`) | **keep**: inventory panels, weapon panels, special-move panels and the radar API stay 2 entries; players 3-4 have none of these |
| V1-V4 PlayerHUD-pointer guards | **replace** (the 4 entry words 0x001C0648, 0x001C7890, 0x001A6D28, 0x001A6C38 now jump to B's V1-V4): reject only a pointer derived from an empty table entry (a0 == offset); the old caves at 0x000F0DD0-0x000F0EC7 become dead code |
| `m2_player_control.md` P-2 EnableCommand window | **change 2 of its words**: 0x0041DC44 limit 2 -> 4 (`2CA20004`), 0x0041DC50 lui 0x0060 -> 0x000E (`3C03000E`) |

Remove the 6 superseded lines (0x001C0648, 0x001C7890, 0x001A6D28, 0x001A6C38 from `mod/m2/hud34.txt`; 0x0041DC44,
0x0041DC50 from `mod/m2/control.txt`) when the B1 fragment is added.

---

## 5. What stays wrong or needs runtime proof
- **Players 3-4 still lack:** inventory/pickup panel, weapon and special-move panels (S-guards), the +0x3480 API
  `FUN_001B28B8`/`FUN_001B28E8`/`FUN_001B2918` (own `sltiu ...,2`, HUD-relative; needs 3 small entry rewrites like
  `FUN_001B23D0`'s plus limit 4, so rage/special updates from combat code are partly missing), `FUN_001557F8` (game
  mode 0xD, fixed P1/P2), the per-player widget at HUD+0x177D0/0x18280, and the 1P/2P marker (no 3P/4P art).
- **View = slot = player index** is assumed by the tagging (HYPOTHESIS). After a player leaves (D7 compaction) a slot
  can belong to a different view; a later fix is to tag by the owner's player index (human+0x1B0) instead of the slot.
- **Merged view with 3-4 players:** players 3/4 panels fall back to P1/P2 positions on the global camera (overlap).
- **Free RAM:** 0x000A0000-0x000AE77F and 0x000E0000-0x000E0A57 rely on F-0050 (zero in gameplay); that nothing else
  uses them is a HYPOTHESIS. The level-start release (DEACT) assumes HUD init runs before MakePlayer in every level
  (HYPOTHESIS).
- **Behaviour change:** an inactive PlayerHUD 1 in single-player now writes layout entry 1 instead of -1 every frame
  (`FUN_00211EF8`); deterministic, and arguably a fix.
- **Cost:** SHARED draws every shared item once per view (begin/end per draw, as the original per-view path).
- Full-screen shared items (pause menu, fades, letterboxing) are replicated per quarter.
- Levels 60-69 (heap PlayerHUD class) and AotN are not covered (optional per D3).

---

## Appendix A: B1 cave source (assembled at 0x000E0100)
```
# ---------- B_INIT: called from FUN_001AD588 at 0x001AE284 (s5 = HUD); delay slot did 'lui v1,0x51'
B_INIT:
  addiu sp,sp,-32
  sw ra,0(sp)
  sw v1,4(sp)
  lui t0,0x000E
  addiu at,zero,-1
  sw at,0x0010(t0)            # CUR = -1 (no HUD player context)
  lw at,8(s5)
  sw at,0x0848(t0)            # T_A[0] = HUD+8
  sw at,0x0000(t0)            # T_B[0]
  lw at,12(s5)
  sw at,0x084C(t0)            # T_A[1] = HUD+0xC
  sw at,0x0004(t0)            # T_B[1]
  lui a0,10
  addiu a0,a0,0
  sw a0,0x0850(t0)            # T_A[2]
  sw a0,0x0008(t0)            # T_B[2]
  lw v0,0x4120(a0)
  lui at,84
  addiu at,at,-4616
  beq v0,at,c2done            # constructed already
  nop
  jal 0x00211CA0              # PlayerHUD constructor (normal class, 0x4A50 bytes)
  nop
c2done:
  lui t0,0x000E
  lui a0,10
  addiu a0,a0,19024
  sw a0,0x0854(t0)            # T_A[3]
  sw a0,0x000C(t0)            # T_B[3]
  lw v0,0x4120(a0)
  lui at,84
  addiu at,at,-4616
  beq v0,at,c3done
  nop
  jal 0x00211CA0
  nop
c3done:
  lui t0,0x000E               # layout (column) index at PlayerHUD+0x40F0 (field never read by the original code)
  lw a0,0x0848(t0)
  beq a0,zero,l1
  nop
  sw zero,0x40F0(a0)
l1:
  lw a0,0x084C(t0)
  beq a0,zero,l2
  addiu at,zero,1
  sw at,0x40F0(a0)
l2:
  lw a0,0x0850(t0)
  sw zero,0x40F0(a0)
  lw a0,0x0854(t0)
  addiu at,zero,1
  sw at,0x40F0(a0)
  lui t0,0x000E               # level start: no player 3-4 yet, so release PlayerHUD 2-3 if still active
  jal DEACT
  lw a0,0x0850(t0)
  lui t0,0x000E
  jal DEACT
  lw a0,0x0854(t0)
  lui a0,11           # radar 3 (player index 2)
  addiu a0,a0,-27392
  jal RCONSTRUCT
  addiu a1,zero,2
  lui a0,11           # radar 4 (player index 3)
  addiu a0,a0,-16832
  jal RCONSTRUCT
  addiu a1,zero,3
  lw v1,4(sp)
  lw ra,0(sp)
  lui v0,0x0001               # replaced instruction at 0x001AE284
  jr ra
  addiu sp,sp,32

# ---------- DEACT(a0 = PlayerHUD): if active (+0x40F8), tail-call vtable +0x2C (FUN_0020DBC0: +0x40F8 = 0, hide)
DEACT:
  lw v0,0x40F8(a0)
  beq v0,zero,d_ret
  nop
  lw v0,0x4120(a0)
  lh at,0x28(v0)
  lw v1,0x2C(v0)
  jr v1
  addu a0,a0,at
d_ret:
  jr ra
  nop

# ---------- RCONSTRUCT(a0 = radar, a1 = player index): HUD-constructor defaults once, then per-level init
RCONSTRUCT:
  addiu sp,sp,-16
  sw ra,0(sp)
  lui at,0x4248               # 50.0f
  lw v0,0x20(a0)
  beq v0,at,rinit
  nop
  sw at,0x20(a0)
  sw at,0x28(a0)
  lui at,0x4296               # 75.0f
  sw at,0x24(a0)
  addiu at,zero,1
  sw at,0x18(a0)
  addiu v0,a0,0x920
  addiu v1,zero,128
  addiu at,zero,-1
rloop:
  sw at,0x10(v0)
  sw at,0x24(v0)
  addiu v1,v1,-1
  bgtz v1,rloop
  addiu v0,v0,0x40
rinit:
  lw v0,0(a0)                 # initialised for this level?
  bne v0,zero,rdone
  nop
  lui at,0x000E               # re-arm the one-time marker activation
  sll v0,a1,2
  addu at,at,v0
  sw zero,0x000C(at)          # flag[index] at 0x000E0014 (index 2) / 0x000E0018 (index 3)
  jal 0x001C3DE0              # radar init(radar, index)
  nop
rdone:
  lw ra,0(sp)
  jr ra
  addiu sp,sp,16

# ---------- CLAIM: FUN_001B2200 at 0x001B222C (was sll v0,s1,2); sets the HUD player context
CLAIM:
  lui at,0x000E
  sw s1,0x0010(at)            # CUR = slot
  jr ra
  sll v0,s1,2

# ---------- POSTINIT: FUN_001B2200 at 0x001B2268 (was jalr ra,v1 = PlayerHUD::Init(this, slot))
POSTINIT:
  addiu sp,sp,-16
  sw ra,0(sp)
  jalr v1
  nop
  lw a2,0(s0)                 # PlayerHUD (T_B[slot])
  sw s1,0x3570(a2)            # +0x3480 child keeps the real slot (its tables used the column, see 0x00212FB0)
  sltiu at,s1,2
  bne at,zero,pdone
  addiu at,zero,2
  bne s1,at,p4
  nop
  lui at,0xFFE1               # player 3 name colours (RGBA bytes 40 A0 E0 FF / 23 53 BC FF)
  addiu at,at,-0x5FC0
  sw at,0x4144(a2)
  lui at,0xFFBC
  addiu at,at,0x5323
  beq zero,zero,pdone
  sw at,0x4148(a2)
p4:
  lui at,0xFF61               # player 4 name colours (60 D8 60 FF / 20 8A 20 FF)
  addiu at,at,-0x27A0
  sw at,0x4144(a2)
  lui at,0xFF21
  addiu at,at,-0x75E0
  sw at,0x4148(a2)
pdone:
  lw ra,0(sp)
  jr ra
  addiu sp,sp,16

# ---------- CLRCUR: FUN_001B2200 at 0x001B22D0 (was lq s0,64(sp)); clears the context on every exit
CLRCUR:
  lui at,0x000E
  addiu v1,zero,-1
  sw v1,0x0010(at)
  jr ra
  .word 0x7BB00040            # lq s0,64(sp) (original)

# ---------- UPD34: HudUpdate at 0x001B10C4 (was jal 0x00390268; delay slot set a0); players 3-4 HUD per frame
UPD34:
  addiu sp,sp,-48
  sw ra,0(sp)
  sw a0,4(sp)
  lui v0,0x0051
  lw v0,0x489C(v0)
  lh v0,0x224(v0)
  sw v0,8(sp)
  slti at,v0,3
  bne at,zero,u_done
  nop
  jal PHUD_UPDATE
  addiu a0,zero,2
  jal RADAR_UPDATE
  addiu a0,zero,2
  lw v0,8(sp)
  slti at,v0,4
  bne at,zero,u_done
  nop
  jal PHUD_UPDATE
  addiu a0,zero,3
  jal RADAR_UPDATE
  addiu a0,zero,3
u_done:
  lw a0,4(sp)
  lw ra,0(sp)
  j 0x00390268
  addiu sp,sp,48

# ---------- PHUD_UPDATE(a0 = HUD slot): PlayerHUD::Update (vtable +0x44 = FUN_00214138) with the HUD player context
PHUD_UPDATE:
  addiu sp,sp,-16
  sw ra,0(sp)
  lui t0,0x000E
  sw a0,0x0010(t0)
  sll a0,a0,2
  addu a0,t0,a0
  lw a0,0x0848(a0)
  beq a0,zero,pu_done
  nop
  lw v0,0x4120(a0)
  lh at,0x40(v0)
  lw v1,0x44(v0)
  jalr v1
  addu a0,a0,at
pu_done:
  lui t0,0x000E
  addiu at,zero,-1
  sw at,0x0010(t0)
  lw ra,0(sp)
  jr ra
  addiu sp,sp,16

# ---------- RADAR_UPDATE(a0 = player index 2/3): position in the bottom row (hud_scale.md 2A), visibility, update
RADAR_UPDATE:
  addiu sp,sp,-32
  sw ra,0(sp)
  sw a0,12(sp)
  lui t0,11
  addiu t0,t0,-27392
  addiu at,zero,3
  bne a0,at,ru1
  nop
  lui t0,11
  addiu t0,t0,-16832
ru1:
  sw t0,8(sp)
  lw v0,0(t0)                 # initialised this level?
  beq v0,zero,ru_done
  nop
  lui at,0x0060
  lw v0,0x1E14(at)            # P1 radar visible flag (HUD+0x15D4)
  sw v0,4(t0)
  lui at,0x0051
  lwc1 f0,-0x2BD4(at)         # d  = [0x0050D42C]
  lwc1 f6,-0x2BD8(at)         # xs = [0x0050D428]
  lwc1 f7,-0x2BD0(at)         # zs = [0x0050D430]
  lwc1 f3,-0x4DF4(at)         # S  = [0x0050B20C]
  lwc1 f4,-0x4DF8(at)         # A  = [0x0050B208]
  lui at,0x3F00
  mtc1 at,f5
  mul.s f3,f3,f5              # Wz = S/2
  mul.s f4,f4,f3              # W  = A*S/2
  mul.s f8,f0,f4
  mul.s f9,f0,f3
  sub.s f2,f7,f9              # z = zs - d*Wz (bottom row)
  add.s f10,f0,f0             # depth = 2d
  addiu at,zero,3
  beq a0,at,xplus
  add.s f1,f6,f8              # x = xs + d*W (right column, player 4)
  sub.s f1,f6,f8              # x = xs - d*W (left column, player 3)
xplus:
  swc1 f1,0x2930(t0)
  swc1 f10,0x2934(t0)
  swc1 f2,0x2938(t0)
  lui at,0x3F80
  sw at,0x293C(t0)
  lui at,0x000E               # one-time marker activation (FUN_001C4388), like P2's flag HUD+0x225D4
  sll v0,a0,2
  addu at,at,v0
  lw v0,0x000C(at)
  bne v0,zero,ru_upd
  addiu v0,zero,1
  sw v0,0x000C(at)
  jal 0x001C4388
  daddu a0,t0,zero
ru_upd:
  lw a0,8(sp)
  lw a1,12(sp)
  addiu a1,a1,-2
  sll a1,a1,5
  lui at,0x000F
  addiu at,at,0x0900          # per-player camera entries 2-3 (static buffer from m2_pads_cameras.md section 4)
  jal 0x001C5210
  addu a1,a1,at
ru_done:
  lw ra,0(sp)
  jr ra
  addiu sp,sp,32

# ---------- RDRAW: FUN_001B1688 at 0x001B1A20 (was jal 0x001C60B0 for P2's radar; delay slot set a0)
RDRAW:
  addiu sp,sp,-16
  sw ra,0(sp)
  jal 0x001C60B0
  nop
  lui v0,0x0051
  lw v0,0x489C(v0)
  lh v0,0x224(v0)
  sw v0,4(sp)
  slti at,v0,3
  bne at,zero,rd_done
  nop
  lui a0,11
  addiu a0,a0,-27392
  lw v0,0(a0)
  beq v0,zero,rd4
  nop
  jal 0x001C60B0
  nop
rd4:
  lw v0,4(sp)
  slti at,v0,4
  bne at,zero,rd_done
  nop
  lui a0,11
  addiu a0,a0,-16832
  lw v0,0(a0)
  beq v0,zero,rd_done
  nop
  jal 0x001C60B0
  nop
rd_done:
  lw ra,0(sp)
  jr ra
  addiu sp,sp,16

# ---------- V-guards (replace option (A) V1-V4): reject only pointers that came from an empty table entry
V1:
  addiu v1,zero,0x3480
  beq a0,v1,v1rej
  nop
  .word 0x27BDFF30
  j 0x001C0650
  .word 0x0080382D
v1rej:
  jr ra
  nop
V2:
  addiu v1,zero,0x70
  beq a0,v1,v2rej
  nop
  .word 0x27BDFFC0
  j 0x001C7898
  .word 0x0000282D
v2rej:
  jr ra
  nop
V3:
  addiu v1,zero,0x1EF0
  beq a0,v1,v3rej
  nop
  .word 0x27BDFF70
  j 0x001A6D30
  .word 0x7FB20060
v3rej:
  jr ra
  nop
V4:
  addiu v1,zero,0x1EF0
  beq a0,v1,v4rej
  nop
  .word 0x27BDFFF0
  j 0x001A6C40
  .word 0xFFBF0000
v4rej:
  jr ra
  nop
```

## Appendix B: B2 cave source (assembled at 0x000E0900)
```
# ---------- VTAG: FUN_001828E0 at 0x0018296C (was sb s5,0x42(s6)); untagged sprites created in a HUD player context
VTAG:
  addiu v0,zero,0xFF
  bne s5,v0,vt_store
  lui v1,0x000E
  lw v0,0x0010(v1)
  bltz v0,vt_store
  nop
  jr ra
  sb v0,0x42(s6)
vt_store:
  jr ra
  sb s5,0x42(s6)

# ---------- ETAG: FUN_001A1DB8 at 0x001A1E0C (was sw a2,0(sp)); the delay slot already did sb v0,0xF9(s0)
ETAG:
  sw a2,0(sp)
  addiu at,zero,0xFF
  bne v0,at,et_done
  lui at,0x000E
  lw at,0x0010(at)
  bltz at,et_done
  nop
  sb at,0xF9(s0)
et_done:
  jr ra
  nop

# ---------- VCALL01: HudUpdate at 0x001B0FB4 (was jalr ra,v1 = PlayerHUD 0/1 update); s0 = loop index
VCALL01:
  addiu sp,sp,-16
  sw ra,0(sp)
  lui at,0x000E
  sw s0,0x0010(at)
  jalr v1
  nop
  lui at,0x000E
  addiu v1,zero,-1
  sw v1,0x0010(at)
  lw ra,0(sp)
  jr ra
  addiu sp,sp,16

# ---------- SHARED: FUN_00185D20 at 0x00185EEC/F0 (global-camera path, a1 = camera manager); in the 2x2 mode with
# 2+ views draw the shared item once per view through that view's HUD camera, else the original path
SHARED:
  addiu at,zero,0xFF          # only untagged (shared) items; a tagged item without its view keeps the original path
  bne s1,at,sh_orig
  nop
  lui v0,0x0051
  lw v0,-0x4E5C(v0)           # layout mode 0x0050B1A4
  addiu at,zero,2
  bne v0,at,sh_orig
  nop
  jal 0x0011EAE0              # views
  nop
  sltiu at,v0,2
  bne at,zero,sh_reload
  nop
  daddu s1,zero,zero
sh_loop:
  lui v0,0x0051
  lw a2,-0x324C(v0)           # camera manager [0x0050CDB4]
  daddu a1,s1,zero
  lw v1,8(a2)
  lh a0,120(v1)
  lw v0,124(v1)
  jalr v0                     # per-view HUD camera (vtable +0x7C)
  addu a0,a2,a0
  daddu s0,v0,zero
  lw v1,0(s0)
  lh a0,96(v1)
  lw v0,100(v1)
  jalr v0                     # begin
  addu a0,s0,a0
  beq v0,zero,sh_next
  nop
  lw v0,16(fp)
  addiu a0,zero,8
  jalr v0                     # render state (as the original)
  daddu a1,zero,zero
  lw a0,0(s2)
  jal 0x00197168              # draw the item for view s1
  daddu a1,s1,zero
  lw v1,0(s0)
  lh a0,104(v1)
  lw v0,108(v1)
  jalr v0                     # end
  addu a0,s0,a0
sh_next:
  jal 0x0011EAE0
  addiu s1,s1,1
  sltu at,s1,v0
  bne at,zero,sh_loop
  nop
  j 0x00185F6C
  lw v0,6296(s5)
sh_reload:
  lui v0,0x0051
  lw a1,-0x324C(v0)
sh_orig:
  lw v1,8(a1)                 # original 0x00185EEC
  j 0x00185EF4
  lh a0,112(v1)               # original 0x00185EF0
```

## Appendix C: fragment B1 (players 3-4 PlayerHUD and radar; 482 patch lines)
```
// HUD option (B) step B1: PlayerHUD 3-4 + radars 3-4 (docs/research/m2_hud_full.md). Static design, untested.
patch=0,EE,000E0010,word,FFFFFFFF // CUR (HUD player context) = -1 at startup
patch=2,EE,000E0100,word,27BDFFE0
patch=2,EE,000E0104,word,AFBF0000
patch=2,EE,000E0108,word,AFA30004
patch=2,EE,000E010C,word,3C08000E
patch=2,EE,000E0110,word,2401FFFF
patch=2,EE,000E0114,word,AD010010
patch=2,EE,000E0118,word,8EA10008
patch=2,EE,000E011C,word,AD010848
patch=2,EE,000E0120,word,AD010000
patch=2,EE,000E0124,word,8EA1000C
patch=2,EE,000E0128,word,AD01084C
patch=2,EE,000E012C,word,AD010004
patch=2,EE,000E0130,word,3C04000A
patch=2,EE,000E0134,word,24840000
patch=2,EE,000E0138,word,AD040850
patch=2,EE,000E013C,word,AD040008
patch=2,EE,000E0140,word,8C824120
patch=2,EE,000E0144,word,3C010054
patch=2,EE,000E0148,word,2421EDF8
patch=2,EE,000E014C,word,10410003
patch=2,EE,000E0150,word,00000000
patch=2,EE,000E0154,word,0C084728
patch=2,EE,000E0158,word,00000000
patch=2,EE,000E015C,word,3C08000E
patch=2,EE,000E0160,word,3C04000A
patch=2,EE,000E0164,word,24844A50
patch=2,EE,000E0168,word,AD040854
patch=2,EE,000E016C,word,AD04000C
patch=2,EE,000E0170,word,8C824120
patch=2,EE,000E0174,word,3C010054
patch=2,EE,000E0178,word,2421EDF8
patch=2,EE,000E017C,word,10410003
patch=2,EE,000E0180,word,00000000
patch=2,EE,000E0184,word,0C084728
patch=2,EE,000E0188,word,00000000
patch=2,EE,000E018C,word,3C08000E
patch=2,EE,000E0190,word,8D040848
patch=2,EE,000E0194,word,10800002
patch=2,EE,000E0198,word,00000000
patch=2,EE,000E019C,word,AC8040F0
patch=2,EE,000E01A0,word,8D04084C
patch=2,EE,000E01A4,word,10800002
patch=2,EE,000E01A8,word,24010001
patch=2,EE,000E01AC,word,AC8140F0
patch=2,EE,000E01B0,word,8D040850
patch=2,EE,000E01B4,word,AC8040F0
patch=2,EE,000E01B8,word,8D040854
patch=2,EE,000E01BC,word,24010001
patch=2,EE,000E01C0,word,AC8140F0
patch=2,EE,000E01C4,word,3C08000E
patch=2,EE,000E01C8,word,0C038084
patch=2,EE,000E01CC,word,8D040850
patch=2,EE,000E01D0,word,3C08000E
patch=2,EE,000E01D4,word,0C038084
patch=2,EE,000E01D8,word,8D040854
patch=2,EE,000E01DC,word,3C04000B
patch=2,EE,000E01E0,word,24849500
patch=2,EE,000E01E4,word,0C03808E
patch=2,EE,000E01E8,word,24050002
patch=2,EE,000E01EC,word,3C04000B
patch=2,EE,000E01F0,word,2484BE40
patch=2,EE,000E01F4,word,0C03808E
patch=2,EE,000E01F8,word,24050003
patch=2,EE,000E01FC,word,8FA30004
patch=2,EE,000E0200,word,8FBF0000
patch=2,EE,000E0204,word,3C020001
patch=2,EE,000E0208,word,03E00008
patch=2,EE,000E020C,word,27BD0020
patch=2,EE,000E0210,word,8C8240F8
patch=2,EE,000E0214,word,10400006
patch=2,EE,000E0218,word,00000000
patch=2,EE,000E021C,word,8C824120
patch=2,EE,000E0220,word,84410028
patch=2,EE,000E0224,word,8C43002C
patch=2,EE,000E0228,word,00600008
patch=2,EE,000E022C,word,00812021
patch=2,EE,000E0230,word,03E00008
patch=2,EE,000E0234,word,00000000
patch=2,EE,000E0238,word,27BDFFF0
patch=2,EE,000E023C,word,AFBF0000
patch=2,EE,000E0240,word,3C014248
patch=2,EE,000E0244,word,8C820020
patch=2,EE,000E0248,word,1041000F
patch=2,EE,000E024C,word,00000000
patch=2,EE,000E0250,word,AC810020
patch=2,EE,000E0254,word,AC810028
patch=2,EE,000E0258,word,3C014296
patch=2,EE,000E025C,word,AC810024
patch=2,EE,000E0260,word,24010001
patch=2,EE,000E0264,word,AC810018
patch=2,EE,000E0268,word,24820920
patch=2,EE,000E026C,word,24030080
patch=2,EE,000E0270,word,2401FFFF
patch=2,EE,000E0274,word,AC410010
patch=2,EE,000E0278,word,AC410024
patch=2,EE,000E027C,word,2463FFFF
patch=2,EE,000E0280,word,1C60FFFC
patch=2,EE,000E0284,word,24420040
patch=2,EE,000E0288,word,8C820000
patch=2,EE,000E028C,word,14400007
patch=2,EE,000E0290,word,00000000
patch=2,EE,000E0294,word,3C01000E
patch=2,EE,000E0298,word,00051080
patch=2,EE,000E029C,word,00220821
patch=2,EE,000E02A0,word,AC20000C
patch=2,EE,000E02A4,word,0C070F78
patch=2,EE,000E02A8,word,00000000
patch=2,EE,000E02AC,word,8FBF0000
patch=2,EE,000E02B0,word,03E00008
patch=2,EE,000E02B4,word,27BD0010
patch=2,EE,000E02B8,word,3C01000E
patch=2,EE,000E02BC,word,AC310010
patch=2,EE,000E02C0,word,03E00008
patch=2,EE,000E02C4,word,00111080
patch=2,EE,000E02C8,word,27BDFFF0
patch=2,EE,000E02CC,word,AFBF0000
patch=2,EE,000E02D0,word,0060F809
patch=2,EE,000E02D4,word,00000000
patch=2,EE,000E02D8,word,8E060000
patch=2,EE,000E02DC,word,ACD13570
patch=2,EE,000E02E0,word,2E210002
patch=2,EE,000E02E4,word,14200010
patch=2,EE,000E02E8,word,24010002
patch=2,EE,000E02EC,word,16210008
patch=2,EE,000E02F0,word,00000000
patch=2,EE,000E02F4,word,3C01FFE1
patch=2,EE,000E02F8,word,2421A040
patch=2,EE,000E02FC,word,ACC14144
patch=2,EE,000E0300,word,3C01FFBC
patch=2,EE,000E0304,word,24215323
patch=2,EE,000E0308,word,10000007
patch=2,EE,000E030C,word,ACC14148
patch=2,EE,000E0310,word,3C01FF61
patch=2,EE,000E0314,word,2421D860
patch=2,EE,000E0318,word,ACC14144
patch=2,EE,000E031C,word,3C01FF21
patch=2,EE,000E0320,word,24218A20
patch=2,EE,000E0324,word,ACC14148
patch=2,EE,000E0328,word,8FBF0000
patch=2,EE,000E032C,word,03E00008
patch=2,EE,000E0330,word,27BD0010
patch=2,EE,000E0334,word,3C01000E
patch=2,EE,000E0338,word,2403FFFF
patch=2,EE,000E033C,word,AC230010
patch=2,EE,000E0340,word,03E00008
patch=2,EE,000E0344,word,7BB00040
patch=2,EE,000E0348,word,27BDFFD0
patch=2,EE,000E034C,word,AFBF0000
patch=2,EE,000E0350,word,AFA40004
patch=2,EE,000E0354,word,3C020051
patch=2,EE,000E0358,word,8C42489C
patch=2,EE,000E035C,word,84420224
patch=2,EE,000E0360,word,AFA20008
patch=2,EE,000E0364,word,28410003
patch=2,EE,000E0368,word,1420000D
patch=2,EE,000E036C,word,00000000
patch=2,EE,000E0370,word,0C0380EC
patch=2,EE,000E0374,word,24040002
patch=2,EE,000E0378,word,0C038100
patch=2,EE,000E037C,word,24040002
patch=2,EE,000E0380,word,8FA20008
patch=2,EE,000E0384,word,28410004
patch=2,EE,000E0388,word,14200005
patch=2,EE,000E038C,word,00000000
patch=2,EE,000E0390,word,0C0380EC
patch=2,EE,000E0394,word,24040003
patch=2,EE,000E0398,word,0C038100
patch=2,EE,000E039C,word,24040003
patch=2,EE,000E03A0,word,8FA40004
patch=2,EE,000E03A4,word,8FBF0000
patch=2,EE,000E03A8,word,080E409A
patch=2,EE,000E03AC,word,27BD0030
patch=2,EE,000E03B0,word,27BDFFF0
patch=2,EE,000E03B4,word,AFBF0000
patch=2,EE,000E03B8,word,3C08000E
patch=2,EE,000E03BC,word,AD040010
patch=2,EE,000E03C0,word,00042080
patch=2,EE,000E03C4,word,01042021
patch=2,EE,000E03C8,word,8C840848
patch=2,EE,000E03CC,word,10800006
patch=2,EE,000E03D0,word,00000000
patch=2,EE,000E03D4,word,8C824120
patch=2,EE,000E03D8,word,84410040
patch=2,EE,000E03DC,word,8C430044
patch=2,EE,000E03E0,word,0060F809
patch=2,EE,000E03E4,word,00812021
patch=2,EE,000E03E8,word,3C08000E
patch=2,EE,000E03EC,word,2401FFFF
patch=2,EE,000E03F0,word,AD010010
patch=2,EE,000E03F4,word,8FBF0000
patch=2,EE,000E03F8,word,03E00008
patch=2,EE,000E03FC,word,27BD0010
patch=2,EE,000E0400,word,27BDFFE0
patch=2,EE,000E0404,word,AFBF0000
patch=2,EE,000E0408,word,AFA4000C
patch=2,EE,000E040C,word,3C08000B
patch=2,EE,000E0410,word,25089500
patch=2,EE,000E0414,word,24010003
patch=2,EE,000E0418,word,14810003
patch=2,EE,000E041C,word,00000000
patch=2,EE,000E0420,word,3C08000B
patch=2,EE,000E0424,word,2508BE40
patch=2,EE,000E0428,word,AFA80008
patch=2,EE,000E042C,word,8D020000
patch=2,EE,000E0430,word,1040002C
patch=2,EE,000E0434,word,00000000
patch=2,EE,000E0438,word,3C010060
patch=2,EE,000E043C,word,8C221E14
patch=2,EE,000E0440,word,AD020004
patch=2,EE,000E0444,word,3C010051
patch=2,EE,000E0448,word,C420D42C
patch=2,EE,000E044C,word,C426D428
patch=2,EE,000E0450,word,C427D430
patch=2,EE,000E0454,word,C423B20C
patch=2,EE,000E0458,word,C424B208
patch=2,EE,000E045C,word,3C013F00
patch=2,EE,000E0460,word,44812800
patch=2,EE,000E0464,word,460518C2
patch=2,EE,000E0468,word,46032102
patch=2,EE,000E046C,word,46040202
patch=2,EE,000E0470,word,46030242
patch=2,EE,000E0474,word,46093881
patch=2,EE,000E0478,word,46000280
patch=2,EE,000E047C,word,24010003
patch=2,EE,000E0480,word,10810002
patch=2,EE,000E0484,word,46083040
patch=2,EE,000E0488,word,46083041
patch=2,EE,000E048C,word,E5012930
patch=2,EE,000E0490,word,E50A2934
patch=2,EE,000E0494,word,E5022938
patch=2,EE,000E0498,word,3C013F80
patch=2,EE,000E049C,word,AD01293C
patch=2,EE,000E04A0,word,3C01000E
patch=2,EE,000E04A4,word,00041080
patch=2,EE,000E04A8,word,00220821
patch=2,EE,000E04AC,word,8C22000C
patch=2,EE,000E04B0,word,14400004
patch=2,EE,000E04B4,word,24020001
patch=2,EE,000E04B8,word,AC22000C
patch=2,EE,000E04BC,word,0C0710E2
patch=2,EE,000E04C0,word,0100202D
patch=2,EE,000E04C4,word,8FA40008
patch=2,EE,000E04C8,word,8FA5000C
patch=2,EE,000E04CC,word,24A5FFFE
patch=2,EE,000E04D0,word,00052940
patch=2,EE,000E04D4,word,3C01000F
patch=2,EE,000E04D8,word,24210900
patch=2,EE,000E04DC,word,0C071484
patch=2,EE,000E04E0,word,00A12821
patch=2,EE,000E04E4,word,8FBF0000
patch=2,EE,000E04E8,word,03E00008
patch=2,EE,000E04EC,word,27BD0020
patch=2,EE,000E04F0,word,27BDFFF0
patch=2,EE,000E04F4,word,AFBF0000
patch=2,EE,000E04F8,word,0C07182C
patch=2,EE,000E04FC,word,00000000
patch=2,EE,000E0500,word,3C020051
patch=2,EE,000E0504,word,8C42489C
patch=2,EE,000E0508,word,84420224
patch=2,EE,000E050C,word,AFA20004
patch=2,EE,000E0510,word,28410003
patch=2,EE,000E0514,word,14200013
patch=2,EE,000E0518,word,00000000
patch=2,EE,000E051C,word,3C04000B
patch=2,EE,000E0520,word,24849500
patch=2,EE,000E0524,word,8C820000
patch=2,EE,000E0528,word,10400003
patch=2,EE,000E052C,word,00000000
patch=2,EE,000E0530,word,0C07182C
patch=2,EE,000E0534,word,00000000
patch=2,EE,000E0538,word,8FA20004
patch=2,EE,000E053C,word,28410004
patch=2,EE,000E0540,word,14200008
patch=2,EE,000E0544,word,00000000
patch=2,EE,000E0548,word,3C04000B
patch=2,EE,000E054C,word,2484BE40
patch=2,EE,000E0550,word,8C820000
patch=2,EE,000E0554,word,10400003
patch=2,EE,000E0558,word,00000000
patch=2,EE,000E055C,word,0C07182C
patch=2,EE,000E0560,word,00000000
patch=2,EE,000E0564,word,8FBF0000
patch=2,EE,000E0568,word,03E00008
patch=2,EE,000E056C,word,27BD0010
patch=2,EE,000E0570,word,24033480
patch=2,EE,000E0574,word,10830004
patch=2,EE,000E0578,word,00000000
patch=2,EE,000E057C,word,27BDFF30
patch=2,EE,000E0580,word,08070194
patch=2,EE,000E0584,word,0080382D
patch=2,EE,000E0588,word,03E00008
patch=2,EE,000E058C,word,00000000
patch=2,EE,000E0590,word,24030070
patch=2,EE,000E0594,word,10830004
patch=2,EE,000E0598,word,00000000
patch=2,EE,000E059C,word,27BDFFC0
patch=2,EE,000E05A0,word,08071E26
patch=2,EE,000E05A4,word,0000282D
patch=2,EE,000E05A8,word,03E00008
patch=2,EE,000E05AC,word,00000000
patch=2,EE,000E05B0,word,24031EF0
patch=2,EE,000E05B4,word,10830004
patch=2,EE,000E05B8,word,00000000
patch=2,EE,000E05BC,word,27BDFF70
patch=2,EE,000E05C0,word,08069B4C
patch=2,EE,000E05C4,word,7FB20060
patch=2,EE,000E05C8,word,03E00008
patch=2,EE,000E05CC,word,00000000
patch=2,EE,000E05D0,word,24031EF0
patch=2,EE,000E05D4,word,10830004
patch=2,EE,000E05D8,word,00000000
patch=2,EE,000E05DC,word,27BDFFF0
patch=2,EE,000E05E0,word,08069B10
patch=2,EE,000E05E4,word,FFBF0000
patch=2,EE,000E05E8,word,03E00008
patch=2,EE,000E05EC,word,00000000
patch=2,EE,001AE284,word,0C038040 // was 3C020001 lui v0,0x0001; FUN_001AD588: after the PlayerHUD pointer loop -> B_INIT
patch=2,EE,00229E84,word,2E020004 // was 2E020002 sltiu v0,s0,2; MakePlayer: HUD slot search 0..3
patch=2,EE,001B2220,word,2A220004 // was 2A220002 slti v0,s1,2; FUN_001B2200: slot limit 4
patch=2,EE,001B222C,word,0C0380AE // was 00111080 sll v0,s1,2; FUN_001B2200: CLAIM (CUR = slot; v0 = slot*4)
patch=2,EE,001B2230,word,3C03000E // was 26430008 addiu v1,s2,8; FUN_001B2200: slot pointer from T_B (0x000E0000) instead of HUD+8
patch=2,EE,001B2268,word,0C0380B2 // was 0060F809 jalr ra,v1; FUN_001B2200: Init via POSTINIT (child slot, P3/P4 colours)
patch=2,EE,001B22D0,word,0C0380CD // was 7BB00040 lq s0,64(sp); FUN_001B2200: exit clears CUR (cave re-does lq s0)
patch=2,EE,0021285C,word,2EA20004 // was 2EA20002 sltiu v0,s5,2; PlayerHUD::Init accepts slots 0..3
patch=2,EE,00212888,word,00000000 // was AFD040F0 sw s0,16624(fp); PlayerHUD::Init no longer overwrites +0x40F0 (column set by B_INIT)
patch=2,EE,00212FB0,word,8FC540F0 // was 02A0282D daddu a1,s5,zero; PlayerHUD::Init: +0x3480 child tables indexed by column (lw a1,0x40F0(fp))
patch=2,EE,001B10C4,word,0C0380D2 // was 0C0E409A jal 0x00390268; HudUpdate: after the fixed PlayerHUD loop -> UPD34 (tail-calls 0x00390268)
patch=2,EE,001B1A20,word,0C03813C // was 0C07182C jal 0x001c60b0; FUN_001B1688: P2 radar draw -> RDRAW (+ radars 3-4)
patch=2,EE,001C0648,word,0803815C // was 27BDFF30 addiu sp,sp,-208; V1 (replaces option A's j 0x000F0DD0)
patch=2,EE,001C7890,word,08038164 // was 27BDFFC0 addiu sp,sp,-64; V2 (replaces option A's j 0x000F0E10)
patch=2,EE,001A6D28,word,0803816C // was 27BDFF70 addiu sp,sp,-144; V3 (replaces option A's j 0x000F0E50)
patch=2,EE,001A6C38,word,08038174 // was 27BDFFF0 addiu sp,sp,-16; V4 (replaces option A's j 0x000F0E90)
patch=2,EE,001B23D0,word,27BDFFF0 // was 27BDFFF0 addiu sp,sp,-16; in-place rewrite: PlayerHUD[slot] from T_A, slot -1 rejected
patch=2,EE,001B23D4,word,04A00006 // was 2402FFFF addiu v0,zero,-1; in-place rewrite: PlayerHUD[slot] from T_A, slot -1 rejected
patch=2,EE,001B23D8,word,FFBF0000 // was 10A20005 beq a1,v0,0x001b23f0; in-place rewrite: PlayerHUD[slot] from T_A, slot -1 rejected
patch=2,EE,001B23DC,word,00051080 // was FFBF0000 sd ra,0(sp); in-place rewrite: PlayerHUD[slot] from T_A, slot -1 rejected
patch=2,EE,001B23E0,word,3C04000E // was 00051080 sll v0,a1,2; in-place rewrite: PlayerHUD[slot] from T_A, slot -1 rejected
patch=2,EE,001B23E4,word,00821021 // was 00821021 addu v0,a0,v0; in-place rewrite: PlayerHUD[slot] from T_A, slot -1 rejected
patch=2,EE,001B23E8,word,0C08380A // was 0C08380A jal 0x0020e028; in-place rewrite: PlayerHUD[slot] from T_A, slot -1 rejected
patch=2,EE,001B23EC,word,8C440848 // was 8C440008 lw a0,8(v0); in-place rewrite: PlayerHUD[slot] from T_A, slot -1 rejected
patch=2,EE,001B2400,word,27BDFFF0 // was 27BDFFF0 addiu sp,sp,-16; in-place rewrite: PlayerHUD[slot] from T_A, slot -1 rejected
patch=2,EE,001B2404,word,04A00006 // was 2402FFFF addiu v0,zero,-1; in-place rewrite: PlayerHUD[slot] from T_A, slot -1 rejected
patch=2,EE,001B2408,word,FFBF0000 // was 10A20005 beq a1,v0,0x001b2420; in-place rewrite: PlayerHUD[slot] from T_A, slot -1 rejected
patch=2,EE,001B240C,word,00051080 // was FFBF0000 sd ra,0(sp); in-place rewrite: PlayerHUD[slot] from T_A, slot -1 rejected
patch=2,EE,001B2410,word,3C04000E // was 00051080 sll v0,a1,2; in-place rewrite: PlayerHUD[slot] from T_A, slot -1 rejected
patch=2,EE,001B2414,word,00821021 // was 00821021 addu v0,a0,v0; in-place rewrite: PlayerHUD[slot] from T_A, slot -1 rejected
patch=2,EE,001B2418,word,0C083816 // was 0C083816 jal 0x0020e058; in-place rewrite: PlayerHUD[slot] from T_A, slot -1 rejected
patch=2,EE,001B241C,word,8C440848 // was 8C440008 lw a0,8(v0); in-place rewrite: PlayerHUD[slot] from T_A, slot -1 rejected
patch=2,EE,00212058,word,8F0240F0 // was 8F0240F4 lw v0,16628(t8); FUN_00211ef8: layout index from +0x40F0 (column)
patch=2,EE,002120BC,word,8F0240F0 // was 8F0240F4 lw v0,16628(t8); FUN_00211ef8: layout index from +0x40F0 (column)
patch=2,EE,00212120,word,8F0340F0 // was 8F0340F4 lw v1,16628(t8); FUN_00211ef8: layout index from +0x40F0 (column)
patch=2,EE,0021213C,word,8F0240F0 // was 8F0240F4 lw v0,16628(t8); FUN_00211ef8: layout index from +0x40F0 (column)
patch=2,EE,00212180,word,8F0240F0 // was 8F0240F4 lw v0,16628(t8); FUN_00211ef8: layout index from +0x40F0 (column)
patch=2,EE,00212190,word,8F0340F0 // was 8F0340F4 lw v1,16628(t8); FUN_00211ef8: layout index from +0x40F0 (column)
patch=2,EE,002121A0,word,8F0240F0 // was 8F0240F4 lw v0,16628(t8); FUN_00211ef8: layout index from +0x40F0 (column)
patch=2,EE,002121B0,word,8F0340F0 // was 8F0340F4 lw v1,16628(t8); FUN_00211ef8: layout index from +0x40F0 (column)
patch=2,EE,002121C0,word,8F0240F0 // was 8F0240F4 lw v0,16628(t8); FUN_00211ef8: layout index from +0x40F0 (column)
patch=2,EE,002121D0,word,8F0340F0 // was 8F0340F4 lw v1,16628(t8); FUN_00211ef8: layout index from +0x40F0 (column)
patch=2,EE,002121E0,word,8F0440F0 // was 8F0440F4 lw a0,16628(t8); FUN_00211ef8: layout index from +0x40F0 (column)
patch=2,EE,00212200,word,8F0240F0 // was 8F0240F4 lw v0,16628(t8); FUN_00211ef8: layout index from +0x40F0 (column)
patch=2,EE,00212210,word,8F0340F0 // was 8F0340F4 lw v1,16628(t8); FUN_00211ef8: layout index from +0x40F0 (column)
patch=2,EE,00212220,word,8F0240F0 // was 8F0240F4 lw v0,16628(t8); FUN_00211ef8: layout index from +0x40F0 (column)
patch=2,EE,00212230,word,8F0340F0 // was 8F0340F4 lw v1,16628(t8); FUN_00211ef8: layout index from +0x40F0 (column)
patch=2,EE,00212348,word,8F0240F0 // was 8F0240F4 lw v0,16628(t8); FUN_00211ef8: layout index from +0x40F0 (column)
patch=2,EE,002123C4,word,8F0240F0 // was 8F0240F4 lw v0,16628(t8); FUN_00211ef8: layout index from +0x40F0 (column)
patch=2,EE,00212414,word,8F0240F0 // was 8F0240F4 lw v0,16628(t8); FUN_00211ef8: layout index from +0x40F0 (column)
patch=2,EE,00212468,word,8F0340F0 // was 8F0340F4 lw v1,16628(t8); FUN_00211ef8: layout index from +0x40F0 (column)
patch=2,EE,00212478,word,8F0240F0 // was 8F0240F4 lw v0,16628(t8); FUN_00211ef8: layout index from +0x40F0 (column)
patch=2,EE,00212488,word,8F0340F0 // was 8F0340F4 lw v1,16628(t8); FUN_00211ef8: layout index from +0x40F0 (column)
patch=2,EE,00212498,word,8F0240F0 // was 8F0240F4 lw v0,16628(t8); FUN_00211ef8: layout index from +0x40F0 (column)
patch=2,EE,002124A8,word,8F0340F0 // was 8F0340F4 lw v1,16628(t8); FUN_00211ef8: layout index from +0x40F0 (column)
patch=2,EE,002124B8,word,8F0240F0 // was 8F0240F4 lw v0,16628(t8); FUN_00211ef8: layout index from +0x40F0 (column)
patch=2,EE,002124C8,word,8F0340F0 // was 8F0340F4 lw v1,16628(t8); FUN_00211ef8: layout index from +0x40F0 (column)
patch=2,EE,002124D8,word,8F0240F0 // was 8F0240F4 lw v0,16628(t8); FUN_00211ef8: layout index from +0x40F0 (column)
patch=2,EE,002125A8,word,8F0240F0 // was 8F0240F4 lw v0,16628(t8); FUN_00211ef8: layout index from +0x40F0 (column)
patch=2,EE,00212628,word,8F0240F0 // was 8F0240F4 lw v0,16628(t8); FUN_00211ef8: layout index from +0x40F0 (column)
patch=2,EE,00212670,word,8F0240F0 // was 8F0240F4 lw v0,16628(t8); FUN_00211ef8: layout index from +0x40F0 (column)
patch=2,EE,002126D4,word,8F0340F0 // was 8F0340F4 lw v1,16628(t8); FUN_00211ef8: layout index from +0x40F0 (column)
patch=2,EE,00212708,word,8F0240F0 // was 8F0240F4 lw v0,16628(t8); FUN_00211ef8: layout index from +0x40F0 (column)
patch=2,EE,00212718,word,8F0340F0 // was 8F0340F4 lw v1,16628(t8); FUN_00211ef8: layout index from +0x40F0 (column)
patch=2,EE,00212728,word,8F0240F0 // was 8F0240F4 lw v0,16628(t8); FUN_00211ef8: layout index from +0x40F0 (column)
patch=2,EE,00212738,word,8F0340F0 // was 8F0340F4 lw v1,16628(t8); FUN_00211ef8: layout index from +0x40F0 (column)
patch=2,EE,00212748,word,8F0240F0 // was 8F0240F4 lw v0,16628(t8); FUN_00211ef8: layout index from +0x40F0 (column)
patch=2,EE,00212758,word,8F0340F0 // was 8F0340F4 lw v1,16628(t8); FUN_00211ef8: layout index from +0x40F0 (column)
patch=2,EE,00212768,word,8F0240F0 // was 8F0240F4 lw v0,16628(t8); FUN_00211ef8: layout index from +0x40F0 (column)
patch=2,EE,00212778,word,8F0340F0 // was 8F0340F4 lw v1,16628(t8); FUN_00211ef8: layout index from +0x40F0 (column)
patch=2,EE,002127F0,word,8F0240F0 // was 8F0240F4 lw v0,16628(t8); FUN_00211ef8: layout index from +0x40F0 (column)
patch=2,EE,00212800,word,8F0340F0 // was 8F0340F4 lw v1,16628(t8); FUN_00211ef8: layout index from +0x40F0 (column)
patch=2,EE,00212810,word,8F0240F0 // was 8F0240F4 lw v0,16628(t8); FUN_00211ef8: layout index from +0x40F0 (column)
patch=2,EE,00212820,word,8F0340F0 // was 8F0340F4 lw v1,16628(t8); FUN_00211ef8: layout index from +0x40F0 (column)
patch=2,EE,00212954,word,8FC440F0 // was 8FC440F4 lw a0,16628(fp); FUN_00212840: layout index from +0x40F0 (column)
patch=2,EE,00212A0C,word,8FC240F0 // was 8FC240F4 lw v0,16628(fp); FUN_00212840: layout index from +0x40F0 (column)
patch=2,EE,00212A74,word,8FC540F0 // was 8FC540F4 lw a1,16628(fp); FUN_00212840: layout index from +0x40F0 (column)
patch=2,EE,00212B68,word,8FCB40F0 // was 8FCB40F4 lw t3,16628(fp); FUN_00212840: layout index from +0x40F0 (column)
patch=2,EE,00212C28,word,8FC240F0 // was 8FC240F4 lw v0,16628(fp); FUN_00212840: layout index from +0x40F0 (column)
patch=2,EE,00212CA8,word,8FC640F0 // was 8FC640F4 lw a2,16628(fp); FUN_00212840: layout index from +0x40F0 (column)
patch=2,EE,00212D64,word,8FC640F0 // was 8FC640F4 lw a2,16628(fp); FUN_00212840: layout index from +0x40F0 (column)
patch=2,EE,00212E20,word,8FCC40F0 // was 8FCC40F4 lw t4,16628(fp); FUN_00212840: layout index from +0x40F0 (column)
patch=2,EE,00212ECC,word,8FC440F0 // was 8FC440F4 lw a0,16628(fp); FUN_00212840: layout index from +0x40F0 (column)
patch=2,EE,002130CC,word,8E2240F0 // was 8E2240F4 lw v0,16628(s1); FUN_00213060: layout index from +0x40F0 (column)
patch=2,EE,00213718,word,8C8340F0 // was 8C8340F4 lw v1,16628(a0); FUN_00213718: layout index from +0x40F0 (column)
patch=2,EE,002137A8,word,8E0240F0 // was 8E0240F4 lw v0,16628(s0); FUN_00213770: layout index from +0x40F0 (column)
patch=2,EE,002137D0,word,8E0640F0 // was 8E0640F4 lw a2,16628(s0); FUN_00213770: layout index from +0x40F0 (column)
patch=2,EE,0021384C,word,8E0340F0 // was 8E0340F4 lw v1,16628(s0); FUN_00213770: layout index from +0x40F0 (column)
patch=2,EE,00213860,word,8E0240F0 // was 8E0240F4 lw v0,16628(s0); FUN_00213770: layout index from +0x40F0 (column)
patch=2,EE,00213870,word,8E0340F0 // was 8E0340F4 lw v1,16628(s0); FUN_00213770: layout index from +0x40F0 (column)
patch=2,EE,00213880,word,8E0240F0 // was 8E0240F4 lw v0,16628(s0); FUN_00213770: layout index from +0x40F0 (column)
patch=2,EE,00213890,word,8E0340F0 // was 8E0340F4 lw v1,16628(s0); FUN_00213770: layout index from +0x40F0 (column)
patch=2,EE,002138A0,word,8E0240F0 // was 8E0240F4 lw v0,16628(s0); FUN_00213770: layout index from +0x40F0 (column)
patch=2,EE,002138B0,word,8E0340F0 // was 8E0340F4 lw v1,16628(s0); FUN_00213770: layout index from +0x40F0 (column)
patch=2,EE,002138D4,word,8E0340F0 // was 8E0340F4 lw v1,16628(s0); FUN_00213770: layout index from +0x40F0 (column)
patch=2,EE,00213928,word,8E0340F0 // was 8E0340F4 lw v1,16628(s0); FUN_00213770: layout index from +0x40F0 (column)
patch=2,EE,0021394C,word,8E0240F0 // was 8E0240F4 lw v0,16628(s0); FUN_00213770: layout index from +0x40F0 (column)
patch=2,EE,0021395C,word,8E0340F0 // was 8E0340F4 lw v1,16628(s0); FUN_00213770: layout index from +0x40F0 (column)
patch=2,EE,0021396C,word,8E0240F0 // was 8E0240F4 lw v0,16628(s0); FUN_00213770: layout index from +0x40F0 (column)
patch=2,EE,0021397C,word,8E0340F0 // was 8E0340F4 lw v1,16628(s0); FUN_00213770: layout index from +0x40F0 (column)
patch=2,EE,002139A0,word,8E0340F0 // was 8E0340F4 lw v1,16628(s0); FUN_00213770: layout index from +0x40F0 (column)
patch=2,EE,002139F0,word,8E0340F0 // was 8E0340F4 lw v1,16628(s0); FUN_00213770: layout index from +0x40F0 (column)
patch=2,EE,00213A14,word,8E0240F0 // was 8E0240F4 lw v0,16628(s0); FUN_00213770: layout index from +0x40F0 (column)
patch=2,EE,00213A24,word,8E0340F0 // was 8E0340F4 lw v1,16628(s0); FUN_00213770: layout index from +0x40F0 (column)
patch=2,EE,00213A34,word,8E0240F0 // was 8E0240F4 lw v0,16628(s0); FUN_00213770: layout index from +0x40F0 (column)
patch=2,EE,00213A44,word,8E0340F0 // was 8E0340F4 lw v1,16628(s0); FUN_00213770: layout index from +0x40F0 (column)
patch=2,EE,00213A68,word,8E0340F0 // was 8E0340F4 lw v1,16628(s0); FUN_00213770: layout index from +0x40F0 (column)
patch=2,EE,00213ABC,word,8E0340F0 // was 8E0340F4 lw v1,16628(s0); FUN_00213770: layout index from +0x40F0 (column)
patch=2,EE,00213AE0,word,8E0240F0 // was 8E0240F4 lw v0,16628(s0); FUN_00213770: layout index from +0x40F0 (column)
patch=2,EE,00213AF0,word,8E0340F0 // was 8E0340F4 lw v1,16628(s0); FUN_00213770: layout index from +0x40F0 (column)
patch=2,EE,00213B00,word,8E0240F0 // was 8E0240F4 lw v0,16628(s0); FUN_00213770: layout index from +0x40F0 (column)
patch=2,EE,00213B10,word,8E0340F0 // was 8E0340F4 lw v1,16628(s0); FUN_00213770: layout index from +0x40F0 (column)
patch=2,EE,00213B20,word,8E0240F0 // was 8E0240F4 lw v0,16628(s0); FUN_00213770: layout index from +0x40F0 (column)
patch=2,EE,00213B30,word,8E0340F0 // was 8E0340F4 lw v1,16628(s0); FUN_00213770: layout index from +0x40F0 (column)
patch=2,EE,00213B64,word,8E0340F0 // was 8E0340F4 lw v1,16628(s0); FUN_00213770: layout index from +0x40F0 (column)
patch=2,EE,00213BB8,word,8E0640F0 // was 8E0640F4 lw a2,16628(s0); FUN_00213770: layout index from +0x40F0 (column)
patch=2,EE,00213C24,word,8E0640F0 // was 8E0640F4 lw a2,16628(s0); FUN_00213770: layout index from +0x40F0 (column)
patch=2,EE,00213C7C,word,8E0340F0 // was 8E0340F4 lw v1,16628(s0); FUN_00213770: layout index from +0x40F0 (column)
patch=2,EE,00213CE8,word,8E0640F0 // was 8E0640F4 lw a2,16628(s0); FUN_00213770: layout index from +0x40F0 (column)
patch=2,EE,00213D40,word,8E0340F0 // was 8E0340F4 lw v1,16628(s0); FUN_00213770: layout index from +0x40F0 (column)
patch=2,EE,00213DAC,word,8E0640F0 // was 8E0640F4 lw a2,16628(s0); FUN_00213770: layout index from +0x40F0 (column)
patch=2,EE,00213E04,word,8E0340F0 // was 8E0340F4 lw v1,16628(s0); FUN_00213770: layout index from +0x40F0 (column)
patch=2,EE,00213EB4,word,8E2340F0 // was 8E2340F4 lw v1,16628(s1); FUN_00213e68: layout index from +0x40F0 (column)
patch=2,EE,00213F78,word,8E2240F0 // was 8E2240F4 lw v0,16628(s1); FUN_00213e68: layout index from +0x40F0 (column)
patch=2,EE,00213FBC,word,8E2240F0 // was 8E2240F4 lw v0,16628(s1); FUN_00213e68: layout index from +0x40F0 (column)
patch=2,EE,00213FF8,word,8E2240F0 // was 8E2240F4 lw v0,16628(s1); FUN_00213e68: layout index from +0x40F0 (column)
patch=2,EE,00214020,word,8E2240F0 // was 8E2240F4 lw v0,16628(s1); FUN_00213e68: layout index from +0x40F0 (column)
patch=2,EE,00214198,word,8E6440F0 // was 8E6440F4 lw a0,16628(s3); FUN_00214138: layout index from +0x40F0 (column)
patch=2,EE,002141AC,word,8E6440F0 // was 8E6440F4 lw a0,16628(s3); FUN_00214138: layout index from +0x40F0 (column)
patch=2,EE,00214308,word,8E6240F0 // was 8E6240F4 lw v0,16628(s3); FUN_00214138: layout index from +0x40F0 (column)
patch=2,EE,00214328,word,8E6240F0 // was 8E6240F4 lw v0,16628(s3); FUN_00214138: layout index from +0x40F0 (column)
patch=2,EE,0021442C,word,8E6740F0 // was 8E6740F4 lw a3,16628(s3); FUN_00214138: layout index from +0x40F0 (column)
patch=2,EE,00214470,word,8E6740F0 // was 8E6740F4 lw a3,16628(s3); FUN_00214138: layout index from +0x40F0 (column)
patch=2,EE,002144E8,word,8E6640F0 // was 8E6640F4 lw a2,16628(s3); FUN_00214138: layout index from +0x40F0 (column)
patch=2,EE,00214550,word,8E6340F0 // was 8E6340F4 lw v1,16628(s3); FUN_00214138: layout index from +0x40F0 (column)
patch=2,EE,00214570,word,8E6340F0 // was 8E6340F4 lw v1,16628(s3); FUN_00214138: layout index from +0x40F0 (column)
patch=2,EE,002146AC,word,8E6540F0 // was 8E6540F4 lw a1,16628(s3); FUN_00214138: layout index from +0x40F0 (column)
patch=2,EE,002146C8,word,8E6540F0 // was 8E6540F4 lw a1,16628(s3); FUN_00214138: layout index from +0x40F0 (column)
patch=2,EE,0021475C,word,8E6240F0 // was 8E6240F4 lw v0,16628(s3); FUN_00214138: layout index from +0x40F0 (column)
patch=2,EE,0021477C,word,8E6240F0 // was 8E6240F4 lw v0,16628(s3); FUN_00214138: layout index from +0x40F0 (column)
patch=2,EE,002147FC,word,8E6740F0 // was 8E6740F4 lw a3,16628(s3); FUN_00214138: layout index from +0x40F0 (column)
patch=2,EE,00214AF0,word,8E6640F0 // was 8E6640F4 lw a2,16628(s3); FUN_00214138: layout index from +0x40F0 (column)
patch=2,EE,00214B6C,word,8E6240F0 // was 8E6240F4 lw v0,16628(s3); FUN_00214138: layout index from +0x40F0 (column)
patch=2,EE,00214BE4,word,8E0240F0 // was 8E0240F4 lw v0,16628(s0); FUN_00214bc8: layout index from +0x40F0 (column)
patch=2,EE,001C697C,word,3C02000E // was 3C020060 lui v0,0x0060; FUN_001c6950: PlayerHUD table -> T_A (0x000E0848)
patch=2,EE,001C9774,word,3C02000E // was 3C020060 lui v0,0x0060; FUN_001c9748: PlayerHUD table -> T_A (0x000E0848)
patch=2,EE,001AB064,word,3C02000E // was 3C020060 lui v0,0x0060; FUN_001ab038: PlayerHUD table -> T_A (0x000E0848)
patch=2,EE,001AAE84,word,3C02000E // was 3C020060 lui v0,0x0060; FUN_001aae58: PlayerHUD table -> T_A (0x000E0848)
patch=2,EE,001C7A2C,word,3C02000E // was 3C020060 lui v0,0x0060; FUN_001c7928: PlayerHUD table -> T_A (0x000E0848)
patch=2,EE,001C7D74,word,3C02000E // was 3C020060 lui v0,0x0060; FUN_001c7928: PlayerHUD table -> T_A (0x000E0848)
patch=2,EE,001BEF54,word,3C03000E // was 3C030060 lui v1,0x0060; FUN_001becb0: PlayerHUD table -> T_A (0x000E0848)
patch=2,EE,0022A458,word,3C04000E // was 3C040060 lui a0,0x0060; FUN_0022a2a8: PlayerHUD table -> T_A (0x000E0848)
patch=2,EE,00284540,word,3C02000E // was 3C020060 lui v0,0x0060; FUN_002843f8: PlayerHUD table -> T_A (0x000E0848)
patch=2,EE,002845AC,word,3C03000E // was 3C030060 lui v1,0x0060; FUN_002843f8: PlayerHUD table -> T_A (0x000E0848)
patch=2,EE,002834EC,word,3C03000E // was 3C030060 lui v1,0x0060; FUN_002833c0: PlayerHUD table -> T_A (0x000E0848)
patch=2,EE,00283B3C,word,3C03000E // was 3C030060 lui v1,0x0060; FUN_00283a30: PlayerHUD table -> T_A (0x000E0848)
patch=2,EE,00285858,word,3C04000E // was 3C040060 lui a0,0x0060; FUN_002856b8: PlayerHUD table -> T_A (0x000E0848)
patch=2,EE,0028661C,word,3C03000E // was 3C030060 lui v1,0x0060; FUN_00286550: PlayerHUD table -> T_A (0x000E0848)
patch=2,EE,0041EEC0,word,3C02000E // was 3C020060 lui v0,0x0060; FUN_0041eeb8: PlayerHUD table -> T_A (0x000E0848)
patch=2,EE,001B3F58,word,3C02000E // was 3C020060 lui v0,0x0060; FUN_001b3f58: PlayerHUD table -> T_A (0x000E0848)
patch=2,EE,001B46A4,word,3C02000E // was 3C020060 lui v0,0x0060; FUN_001b46a0: PlayerHUD table -> T_A (0x000E0848)
patch=2,EE,001B4948,word,3C02000E // was 3C020060 lui v0,0x0060; FUN_001b4948: PlayerHUD table -> T_A (0x000E0848)
patch=2,EE,001B4474,word,3C02000E // was 3C020060 lui v0,0x0060; FUN_001b4438: PlayerHUD table -> T_A (0x000E0848)
patch=2,EE,0041DC44,word,2CA20004 // was 80C201B0 in the ELF; supersedes mod/m2/control.txt line 2CA20002: EnableCommand PlayerHUD call for players 0..3
patch=2,EE,0041DC50,word,3C03000E // was 0200282D in the ELF; supersedes mod/m2/control.txt line 3C030060: lw a0,0x848(v1) now reads T_A[p]
```

## Appendix D: fragment B2 (per-view HUD; 93 patch lines)
```
// HUD option (B) step B2: per-view HUD (each element in its owner's quarter; shared items in every quarter)
patch=2,EE,00196370,word,46000506 // was 46160502 cop1 46160502; hud_scale.md 2B: per-view HUD window undivided (x)
patch=2,EE,00196398,word,460003C6 // was 461703C2 cop1 461703c2; hud_scale.md 2B: per-view HUD window undivided (y)
patch=2,EE,000E0900,word,240200FF
patch=2,EE,000E0904,word,16A20006
patch=2,EE,000E0908,word,3C03000E
patch=2,EE,000E090C,word,8C620010
patch=2,EE,000E0910,word,04400003
patch=2,EE,000E0914,word,00000000
patch=2,EE,000E0918,word,03E00008
patch=2,EE,000E091C,word,A2C20042
patch=2,EE,000E0920,word,03E00008
patch=2,EE,000E0924,word,A2D50042
patch=2,EE,000E0928,word,AFA60000
patch=2,EE,000E092C,word,240100FF
patch=2,EE,000E0930,word,14410005
patch=2,EE,000E0934,word,3C01000E
patch=2,EE,000E0938,word,8C210010
patch=2,EE,000E093C,word,04200002
patch=2,EE,000E0940,word,00000000
patch=2,EE,000E0944,word,A20100F9
patch=2,EE,000E0948,word,03E00008
patch=2,EE,000E094C,word,00000000
patch=2,EE,000E0950,word,27BDFFF0
patch=2,EE,000E0954,word,AFBF0000
patch=2,EE,000E0958,word,3C01000E
patch=2,EE,000E095C,word,AC300010
patch=2,EE,000E0960,word,0060F809
patch=2,EE,000E0964,word,00000000
patch=2,EE,000E0968,word,3C01000E
patch=2,EE,000E096C,word,2403FFFF
patch=2,EE,000E0970,word,AC230010
patch=2,EE,000E0974,word,8FBF0000
patch=2,EE,000E0978,word,03E00008
patch=2,EE,000E097C,word,27BD0010
patch=2,EE,000E0980,word,240100FF
patch=2,EE,000E0984,word,16210031
patch=2,EE,000E0988,word,00000000
patch=2,EE,000E098C,word,3C020051
patch=2,EE,000E0990,word,8C42B1A4
patch=2,EE,000E0994,word,24010002
patch=2,EE,000E0998,word,1441002C
patch=2,EE,000E099C,word,00000000
patch=2,EE,000E09A0,word,0C047AB8
patch=2,EE,000E09A4,word,00000000
patch=2,EE,000E09A8,word,2C410002
patch=2,EE,000E09AC,word,14200025
patch=2,EE,000E09B0,word,00000000
patch=2,EE,000E09B4,word,0000882D
patch=2,EE,000E09B8,word,3C020051
patch=2,EE,000E09BC,word,8C46CDB4
patch=2,EE,000E09C0,word,0220282D
patch=2,EE,000E09C4,word,8CC30008
patch=2,EE,000E09C8,word,84640078
patch=2,EE,000E09CC,word,8C62007C
patch=2,EE,000E09D0,word,0040F809
patch=2,EE,000E09D4,word,00C42021
patch=2,EE,000E09D8,word,0040802D
patch=2,EE,000E09DC,word,8E030000
patch=2,EE,000E09E0,word,84640060
patch=2,EE,000E09E4,word,8C620064
patch=2,EE,000E09E8,word,0040F809
patch=2,EE,000E09EC,word,02042021
patch=2,EE,000E09F0,word,1040000D
patch=2,EE,000E09F4,word,00000000
patch=2,EE,000E09F8,word,8FC20010
patch=2,EE,000E09FC,word,24040008
patch=2,EE,000E0A00,word,0040F809
patch=2,EE,000E0A04,word,0000282D
patch=2,EE,000E0A08,word,8E440000
patch=2,EE,000E0A0C,word,0C065C5A
patch=2,EE,000E0A10,word,0220282D
patch=2,EE,000E0A14,word,8E030000
patch=2,EE,000E0A18,word,84640068
patch=2,EE,000E0A1C,word,8C62006C
patch=2,EE,000E0A20,word,0040F809
patch=2,EE,000E0A24,word,02042021
patch=2,EE,000E0A28,word,0C047AB8
patch=2,EE,000E0A2C,word,26310001
patch=2,EE,000E0A30,word,0222082B
patch=2,EE,000E0A34,word,1420FFE0
patch=2,EE,000E0A38,word,00000000
patch=2,EE,000E0A3C,word,080617DB
patch=2,EE,000E0A40,word,8EA21898
patch=2,EE,000E0A44,word,3C020051
patch=2,EE,000E0A48,word,8C45CDB4
patch=2,EE,000E0A4C,word,8CA30008
patch=2,EE,000E0A50,word,080617BD
patch=2,EE,000E0A54,word,84640070
patch=2,EE,0018296C,word,0C038240 // was A2D50042 sb s5,66(s6); FUN_001828E0: sprite view byte via VTAG
patch=2,EE,001A1E0C,word,0C03824A // was AFA60000 sw a2,0(sp); FUN_001A1DB8: element view byte via ETAG (delay slot keeps the original sb)
patch=2,EE,001B0FB4,word,0C038254 // was 0060F809 jalr ra,v1; HudUpdate: PlayerHUD 0/1 update with CUR = index
patch=2,EE,00185EEC,word,08038260 // was 8CA30008 lw v1,8(a1); FUN_00185D20: global-camera path -> SHARED
patch=2,EE,00185EF0,word,00000000 // was 84640070 lh a0,112(v1); FUN_00185D20: delay slot (original moved into SHARED)
```

## Summary
Option (B) is designed and encoded as two fragments (B1 482 words, B2 93 words; checker: 0 problems apart from 6
intended supersedes of (A)/P-2 lines). All of it is untested (static analysis only).
- **Players 3-4 HUD (B1):** two more normal PlayerHUDs (constructor `FUN_00211CA0`) and two radars in free low RAM;
  a 4-entry pointer table (T_A at 0x000E0848 for 19 one-word lui redirects, T_B at 0x000E0000 for the claim function);
  slot limits raised (MakePlayer 0x00229E84, `FUN_001B2200` 0x001B2220, Init 0x0021285C). The 2-entry layout tables need
  no relocation: the 112 layout loads of +0x40F4 read the never-used field +0x40F0 instead, set to the column, so
  player 3 uses P1's layout and player 4 P2's, while +0x40F4 stays the real slot for identity. Updates/draws for slots
  2-3 and radars 3-4 are added after HudUpdate's fixed loop and after P2's radar draw.
- **Per-view HUD (B2):** patch 2B, a "current HUD player" context, element/sprite view tagging (ETAG/VTAG) and a per-view
  replay of shared items in the flush (SHARED): every panel (including players 1-2's rage panel) is half size inside its
  quarter, and centred text appears in every quarter.
- **(A):** keep MIN2, the pause cave, the marker words and S1-S7; replace V1-V4; change 2 words of P-2.
- Confidence: high for the code facts and encodings; medium for the visual result (view = slot assumption, merged-view
  overlap, free-RAM assumption). Test order: B0, B1a, B1b, B1c, B2a, B2b, then a 4-instance lockstep run.


---

## Addendum: runtime results 1 (2026-10-11)

**The run (reported by the coordinator).** SINGLE-PC, one instance, scripted input, MTVU off. Build w4p-m3-4 with
`kGameRamStart` = 0x000A0000. Groups: own view, hud, 4p, 4p hud B1, 4p hud B2.
- **Mission 1 with 4 players works (F-0126).**
- **Mission 13 (level9):** loaded from Mission 1 with `MenuLoadLevel`; the game's own drop-in made Fox player 3
  (F-0127). The game ran 3 views in the 2x2 layout.
- **The T_A table check passes:** entry 2 has slot 2, column 0, and is active.
- **The problem:** player 3's quarter shows **no radar and no panel** (`local/m2/m13b/f00003.png` to `f00006.png`).

This addendum explains why and gives the fix. It is static analysis only; nothing was run for it.

### A1. Diagnosis
| # | Question | Finding | Label |
|---|---|---|---|
| 1 | Panel | **Player 3's panel is never drawn. This is the cause of the missing panel.** `FUN_001B1688` (HUD draw) calls PlayerHUD Draw (vtable +0x3C = `FUN_00213290`) only for HUD+8 and HUD+0xC, in a fixed 2-pass loop at 0x001B1B90-0x001B1BC0 (`addiu s1,zero,1` ... `bgezl s1`). B1 added the per-frame Update for slots 2-3 (UPD34) but no Draw. | VERIFIED (disassembly, decompile) |
| 2 | Panel only shown on events | **The panel appears only after an event, for all players.** `FUN_00213290` draws only while +0x4138 (updated once), +0x40FC (shown) and +0x40F8 (active) are all set. It then draws for 2000 time units (0x00510070 = 0x7D0) after its timer +0x411C restarts, and fades out over 1000 more (0x00510074 = 0x3E8). After that it returns without drawing. The timer restarts when +0x411C = 0. That happens on the first draw after Init, when the health/inventory children write +0x411C = 0, and every frame while +0x4104 = 1 (`ForceShowPlayerHud`, `FUN_001B20E0`). **This is why players 1-2 show no panel either** in f00003-f00006: there was no recent event. After fix R1, player 3's panel will also appear only on events. HYPOTHESIS: the time unit is milliseconds. | VERIFIED (decompile, ELF words, screenshots) |
| 3 | Radar 3 | **The radar did not re-initialise in level9 and kept Mission 1's textures and sprite handles.** RDRAW does call `FUN_001C60B0(radar 3)`: P2's radar is drawn (so 0x001B1A20 runs), the count is 3 and +0 = 1. RADAR_UPDATE's one-time `FUN_001C4388` also makes the flag checks (+0, +4, +8, !+0xC) pass. What remains is the disc sprite check: `FUN_00185AB0(0x0050CD4C, +0x96)` must return a sprite whose byte +0x11 != 0. **Most likely, the stale Mission 1 handle fails this check, so nothing is drawn.** How it got stale: radar init `FUN_001C3DE0` sets +0 = 1 whether or not that player exists, and B_INIT ran it in Mission 1. Radars are released only at HUD level exit (`FUN_001AE980`, which calls `FUN_001C41A0` for HUD+0x15D0 and HUD+0x3F10 only, at 0x001AEB2C/0x001AEB34). RCONSTRUCT (like `FUN_001AD588` for radars 1-2) re-initialises only when +0 == 0, so in level9 it skipped radar 3. The old handles are the textures at +0x48..+0x60, the map sprite +0x94 and the disc sprite +0x96. | VERIFIED (mechanism) / HYPOTHESIS (that the stale handle is the failing check; see A3) |
| 4 | Radar on/off | **Radars 3-4 ignore every later on/off change.** RADAR_UPDATE switches radar 3 on once per init and copies only +4 from P1. `HideHud`/`ShowHud` (`FUN_001B1F38`/`FUN_001B20F8`), `HUDTurnOffRadar` and the merged-view path (`FUN_001C4448` on P2's radar) never touch radars 3-4. So radar 3 would stay visible in cutscenes and in merged view. Not the cause here; fix R3 covers it. | VERIFIED (decompile) |
| 5 | Latent bug, same family | **Player 3's panel would break in every level after the first one where they joined.** `FUN_001AE980` shuts down only PlayerHUD 0-1, through vtable +0x1C = `FUN_002131F0`, which calls `FUN_0020DBE0` (+0x40F8 = +0x40FC = +0x4100 = 0, sprites released). PlayerHUD 2-3 keep +0x4100 = 1 into the next level, so the next claim skips Init and uses stale elements. Not the cause in m13b, because PlayerHUD 2 was first claimed in level9. | VERIFIED (decompile) |
| 6 | Not causes | UPD34 runs (count 3). Update needs +0x40FC, which MakePlayer sets through `FUN_001B23D0(HUD, human+0x380)` at 0x0022A160 (B1 rewrote it to read T_A). `ForceShowPlayerHud` (scripts pass 0/1) and the 2-pass loops in `HideHud`/`ShowHud`, `FUN_001B2030`/`FUN_001B2088` (+0x4108) and `FUN_001B2330`/`FUN_001B2380` (show/hide all) never touch PlayerHUD 2. They don't hide player 3, they just don't control them (A4). Human +0x380 = 2 follows from the claim. | VERIFIED (code) / HYPOTHESIS (the +0x380 value; PINE in A3) |
| 7 | Large disc on P1/P2 | **Expected: this is the single-player-size radar.** With 2A each disc is centred about 85 % across and 80 % down its quarter, and is about 1/3 of the quarter wide (about 80 of 247 px in f00003). The cropped single-player-size radar in `local/m3/v1_hud2/slot0_end.png` (F-0103) is also about 1/3 of the view wide. The disc contents (map texture, blips) were not checked. | VERIFIED (screenshots, approximate pixel measurement) |

### A2. Fix R1-R3
- **R1, draw the panels of players 3-4.**
  - Site: 0x001B1BC4, the `jal 0x001BB1C0` right after the PlayerHUD 0-1 draw loop, now calls DRAW34.
  - DRAW34: if the player count (GameMgr+0x224) is >= 3, Draw PlayerHUD 2; if >= 4, Draw PlayerHUD 3. Each Draw
    runs with CUR = slot. It then jumps to the original call.
- **R2, level exit for players 3-4.**
  - Site: 0x001AEB34, the `jal 0x001C41A0` that releases radar 2, now calls LEXIT.
  - LEXIT runs the original call, then:
    - vtable +0x1C on PlayerHUD 2-3, if constructed (vtable 0x0053EDF8);
    - `FUN_001C41A0` on radars 3-4, if +0 != 0.
  - Each level then re-initialises them exactly as for players 1-2. This fixes both A1.3 and A1.5.
- **R3, radars 3-4 follow P2's radar.** Two words of B1's RADAR_UPDATE (0x000E04A0/0x000E04A4) now jump to RMIRROR.
  RMIRROR:
  - copies P2's +4 (0x00604754);
  - if P2's radar is drawn (+8 set, +0xC clear) and this one is not, calls `FUN_001C4388` (show);
  - in the opposite case, calls `FUN_001C4448` (hide, as HudUpdate does for P2 in merged view).
  - It replaces the one-time switch-on; the flags at 0x000E0014/0x000E0018 become unused.
  - Why P2 and not P1: P2's radar is the one the game hides in merged view.
- **Space:** caves at 0x000E0600-0x000E07AF (108 words), below T_A[-1] at 0x000E0844. No patch line used
  0x000E0600-0x000E0843 before.
- **Checks** (`python -I tools/note_patches.py check ...`):

  | Files checked | Result | Meaning |
  |---|---|---|
  | `mod/w4p_m1.pnach` alone | 6 problems | the existing group A vs B1 alternatives: 0x001C0648, 0x001C7890, 0x001A6D28, 0x001A6C38, 0x0041DC44, 0x0041DC50 |
  | pnach + the add fragment | the same 6 | the add fragment introduces no new conflicts |
  | pnach + add fragment + the 2 replacement lines | 8 | the 6 above + the intended 0x000E04A0/0x000E04A4 |
  | pnach with the 2 old B1 lines removed + both parts | 6 | only the A/B1 alternatives |

  - Extracting this note now also gives the same 2 intended conflicts: Appendix C still holds the old words.
  - Every "was" word was read from `local/disc/SLUS_212.15`, and the caves were disassembled back from the encoded
    words.
- **Test order (all HYPOTHESIS until run):**
  1. **R1:** player 3's panel appears for about 3 s when they join. To keep it on screen, write32(0x000A4104, 1)
     (test only; write 0 afterwards).
  2. **R2:** repeat the m13b path (Mission 1, then level9). Radar 3 should be drawn bottom-right in player 3's
     quarter.
  3. **R3:** in a cutscene, radar 3 should hide together with P2's radar.

### A3. PINE reads (static addresses unless marked)
| Address | Field | Expected now (m13b state) | Expected after R1-R3 |
|---|---|---|---|
| 0x000A0000+0x40F8 / +0x40FC / +0x4100 / +0x4108 | PlayerHUD 2: active / shown / inited / enabled | 1 / 1 / 1 / 1 | same in play. During loading after a level exit: 0 / 0 / 0 |
| 0x000A0000+0x4138 | Update ran past its early returns | 1 | 1 |
| 0x000A0000+0x411C | panel timer start | **0** (Draw never ran). PlayerHUD 0 (0x00619970+0x411C) has a time value | a time value from the first frame after the claim |
| 0x000A0000+0x4104 | force show | 0 | 0 (test aid: 1) |
| 0x000A9500 +0x00 / +0x04 / +0x08 / +0x0C / +0x90 | radar 3: inited / visible / shown / off / player index | 1 / 1 / 1 / 0 / 2 | 1 / =P2 / =P2 / =P2 / 2 (P2 = radar 2 at 0x00604750+4/+8/+0xC) |
| u16 0x000A9500+0x94 / +0x96 | radar 3 map / disc sprite handles | **unchanged since Mission 1** (read them at the end of Mission 1 and again in level9) | change at every level |
| u16 0x00601E10+0x96, 0x00604750+0x96 | radar 1 / radar 2 disc sprite | fresh level9 handles, for comparison | same |
| float 0x000A9500+0x2930..+0x293C | position | (xs - d*W, 2d, zs - d*Wz, 1.0); with the ELF values (A 4/3, S 1.0, xs 0.49, d 1.0, zs -0.31): (-0.177, 2.0, -0.81, 1.0) | same |
| 0x000E0014 | old one-time flag, index 2 | 1 | not used |
| 0x00641A20+0x380 (dynamic, from state.txt) | player 3's HUD slot | 2 | 2 |

**How to read the results:**
- If radar 3 shows +0..+0xC = 1/1/1/0 and the handles are unchanged since Mission 1, the stale-handle diagnosis
  (A1.3) holds.
- If they changed, the radar cause is elsewhere and A1.3 stays open.

### A4. Still open after R1-R3
- **Players 3-4 do not follow these script controls:** `HideHud`/`ShowHud` (for the panels), `ForceShowPlayerHud`,
  the +0x4108 enable, and show/hide all.
  - Each is a 2-pass loop from HUD+8: `FUN_001B1F38`, `FUN_001B20F8`, `FUN_001B2030`, `FUN_001B2088`, `FUN_001B2330`,
    `FUN_001B2380`.
  - Fix idea (R4, not encoded): set the loop base to T_B (`lui sX,0x000E`) and the count to 3.
  - R4 also needs place-0 data lines that point T_A/T_B[2..3] at the zeroed objects, so that these loops are safe
    before the first B_INIT.
- **HUD-level per-player panels are still 2 entries** (inventory/weapon/special at HUD+0xEBC0/0xF420/0xFEA0/0x114C0;
  S-guards).
- **The dark band (F-0126) is not analysed here.**

### Fragment R1-R3, part 1: add to `[warriors-4p 4p hud B1]` (110 lines)
```
// HUD option (B) fix 1 (R1-R3), add to [warriors-4p 4p hud B1] (docs/research/m2_hud_full.md addendum). Static design, untested.
patch=2,EE,000E0600,word,27BDFFF0
patch=2,EE,000E0604,word,AFBF0000
patch=2,EE,000E0608,word,AFA40004
patch=2,EE,000E060C,word,3C020051
patch=2,EE,000E0610,word,8C42489C
patch=2,EE,000E0614,word,84420224
patch=2,EE,000E0618,word,AFA20008
patch=2,EE,000E061C,word,28410003
patch=2,EE,000E0620,word,14200009
patch=2,EE,000E0624,word,00000000
patch=2,EE,000E0628,word,0C038196
patch=2,EE,000E062C,word,24040002
patch=2,EE,000E0630,word,8FA20008
patch=2,EE,000E0634,word,28410004
patch=2,EE,000E0638,word,14200003
patch=2,EE,000E063C,word,00000000
patch=2,EE,000E0640,word,0C038196
patch=2,EE,000E0644,word,24040003
patch=2,EE,000E0648,word,8FA40004
patch=2,EE,000E064C,word,8FBF0000
patch=2,EE,000E0650,word,0806EC70
patch=2,EE,000E0654,word,27BD0010
patch=2,EE,000E0658,word,27BDFFF0
patch=2,EE,000E065C,word,AFBF0000
patch=2,EE,000E0660,word,3C08000E
patch=2,EE,000E0664,word,00041080
patch=2,EE,000E0668,word,01021021
patch=2,EE,000E066C,word,8C420848
patch=2,EE,000E0670,word,1040000A
patch=2,EE,000E0674,word,00000000
patch=2,EE,000E0678,word,AD040010
patch=2,EE,000E067C,word,8C434120
patch=2,EE,000E0680,word,84610038
patch=2,EE,000E0684,word,8C63003C
patch=2,EE,000E0688,word,0060F809
patch=2,EE,000E068C,word,00412021
patch=2,EE,000E0690,word,3C08000E
patch=2,EE,000E0694,word,2401FFFF
patch=2,EE,000E0698,word,AD010010
patch=2,EE,000E069C,word,8FBF0000
patch=2,EE,000E06A0,word,03E00008
patch=2,EE,000E06A4,word,27BD0010
patch=2,EE,000E06A8,word,27BDFFF0
patch=2,EE,000E06AC,word,AFBF0000
patch=2,EE,000E06B0,word,0C071068
patch=2,EE,000E06B4,word,00000000
patch=2,EE,000E06B8,word,0C0381BB
patch=2,EE,000E06BC,word,24040002
patch=2,EE,000E06C0,word,0C0381BB
patch=2,EE,000E06C4,word,24040003
patch=2,EE,000E06C8,word,3C04000B
patch=2,EE,000E06CC,word,0C0381CC
patch=2,EE,000E06D0,word,24849500
patch=2,EE,000E06D4,word,3C04000B
patch=2,EE,000E06D8,word,0C0381CC
patch=2,EE,000E06DC,word,2484BE40
patch=2,EE,000E06E0,word,8FBF0000
patch=2,EE,000E06E4,word,03E00008
patch=2,EE,000E06E8,word,27BD0010
patch=2,EE,000E06EC,word,3C08000E
patch=2,EE,000E06F0,word,00041080
patch=2,EE,000E06F4,word,01021021
patch=2,EE,000E06F8,word,8C440848
patch=2,EE,000E06FC,word,1080000A
patch=2,EE,000E0700,word,00000000
patch=2,EE,000E0704,word,8C824120
patch=2,EE,000E0708,word,3C010054
patch=2,EE,000E070C,word,2421EDF8
patch=2,EE,000E0710,word,14410005
patch=2,EE,000E0714,word,00000000
patch=2,EE,000E0718,word,84410018
patch=2,EE,000E071C,word,8C43001C
patch=2,EE,000E0720,word,00600008
patch=2,EE,000E0724,word,00812021
patch=2,EE,000E0728,word,03E00008
patch=2,EE,000E072C,word,00000000
patch=2,EE,000E0730,word,8C820000
patch=2,EE,000E0734,word,10400003
patch=2,EE,000E0738,word,00000000
patch=2,EE,000E073C,word,08071068
patch=2,EE,000E0740,word,00000000
patch=2,EE,000E0744,word,03E00008
patch=2,EE,000E0748,word,00000000
patch=2,EE,000E074C,word,3C010060
patch=2,EE,000E0750,word,8C224754
patch=2,EE,000E0754,word,AD020004
patch=2,EE,000E0758,word,8C224758
patch=2,EE,000E075C,word,8C23475C
patch=2,EE,000E0760,word,0002102B
patch=2,EE,000E0764,word,2C630001
patch=2,EE,000E0768,word,00431024
patch=2,EE,000E076C,word,8D030008
patch=2,EE,000E0770,word,8D01000C
patch=2,EE,000E0774,word,0003182B
patch=2,EE,000E0778,word,2C210001
patch=2,EE,000E077C,word,00611824
patch=2,EE,000E0780,word,10430009
patch=2,EE,000E0784,word,00000000
patch=2,EE,000E0788,word,14400005
patch=2,EE,000E078C,word,0100202D
patch=2,EE,000E0790,word,0C071112
patch=2,EE,000E0794,word,00000000
patch=2,EE,000E0798,word,08038131
patch=2,EE,000E079C,word,00000000
patch=2,EE,000E07A0,word,0C0710E2
patch=2,EE,000E07A4,word,00000000
patch=2,EE,000E07A8,word,08038131
patch=2,EE,000E07AC,word,00000000
patch=2,EE,001B1BC4,word,0C038180 // was 0C06EC70 jal 0x001bb1c0; FUN_001B1688 after the PlayerHUD 0-1 draw loop -> DRAW34 (PlayerHUD 2-3 draw)
patch=2,EE,001AEB34,word,0C0381AA // was 0C071068 jal 0x001c41a0; FUN_001AE980 radar-2 release -> LEXIT (level exit for PlayerHUD 2-3, radars 3-4)
```

### Fragment R1-R3, part 2: replace these 2 lines of `[warriors-4p 4p hud B1]` (the old words are in the comments)
```
patch=2,EE,000E04A0,word,080381D3 // RADAR_UPDATE: B1 had 3C01000E (lui at,0x000E); j RMIRROR
patch=2,EE,000E04A4,word,00000000 // RADAR_UPDATE: B1 had 00041080 (sll v0,a0,2); nop (delay slot)
```

### Cave source (assembled at 0x000E0600)
```
# ---------- DRAW34: FUN_001B1688 at 0x001B1BC4 (was jal 0x001BB1C0; delay slot set a0 = s5), right after the loop that
# draws PlayerHUD 0-1 (vtable +0x3C, FUN_00213290); draws PlayerHUD 2-3 the same way
DRAW34:
  addiu sp,sp,-16
  sw ra,0(sp)
  sw a0,4(sp)
  lui v0,0x0051
  lw v0,0x489C(v0)
  lh v0,0x224(v0)             # player count (GameMgr+0x224), same gate as UPD34
  sw v0,8(sp)
  slti at,v0,3
  bne at,zero,dr_done
  nop
  jal PHUD_DRAW
  addiu a0,zero,2
  lw v0,8(sp)
  slti at,v0,4
  bne at,zero,dr_done
  nop
  jal PHUD_DRAW
  addiu a0,zero,3
dr_done:
  lw a0,4(sp)
  lw ra,0(sp)
  j 0x001BB1C0
  addiu sp,sp,16

# ---------- PHUD_DRAW(a0 = HUD slot): PlayerHUD::Draw with the HUD player context (it returns at once unless the
# PlayerHUD is active +0x40F8 and shown +0x40FC)
PHUD_DRAW:
  addiu sp,sp,-16
  sw ra,0(sp)
  lui t0,0x000E
  sll v0,a0,2
  addu v0,t0,v0
  lw v0,0x0848(v0)            # T_A[slot]
  beq v0,zero,pd_done
  nop
  sw a0,0x0010(t0)            # CUR = slot
  lw v1,0x4120(v0)
  lh at,0x38(v1)
  lw v1,0x3C(v1)
  jalr v1
  addu a0,v0,at
  lui t0,0x000E
  addiu at,zero,-1
  sw at,0x0010(t0)            # CUR = -1
pd_done:
  lw ra,0(sp)
  jr ra
  addiu sp,sp,16

# ---------- LEXIT: FUN_001AE980 (HUD level exit) at 0x001AEB34 (was jal 0x001C41A0 = release radar 2; delay slot set
# a0 = HUD+0x3F10). Does the same level-exit work for PlayerHUD 2-3 and radars 3-4 as the game does for 0-1
LEXIT:
  addiu sp,sp,-16
  sw ra,0(sp)
  jal 0x001C41A0              # radar 2 (original call)
  nop
  jal PHUD_SHUT
  addiu a0,zero,2
  jal PHUD_SHUT
  addiu a0,zero,3
  lui a0,0x000B
  jal RREL
  addiu a0,a0,-27392          # radar 3 (0x000A9500)
  lui a0,0x000B
  jal RREL
  addiu a0,a0,-16832          # radar 4 (0x000ABE40)
  lw ra,0(sp)
  jr ra
  addiu sp,sp,16

# PHUD_SHUT(a0 = slot): vtable +0x1C (FUN_002131F0: clears active/shown/inited, releases the sprites) if constructed
PHUD_SHUT:
  lui t0,0x000E
  sll v0,a0,2
  addu v0,t0,v0
  lw a0,0x0848(v0)
  beq a0,zero,ps_ret
  nop
  lw v0,0x4120(a0)
  lui at,0x0054
  addiu at,at,-4616           # 0x0053EDF8 (normal PlayerHUD vtable)
  bne v0,at,ps_ret
  nop
  lh at,0x18(v0)
  lw v1,0x1C(v0)
  jr v1
  addu a0,a0,at
ps_ret:
  jr ra
  nop

# RREL(a0 = radar): FUN_001C41A0 (sets +0 = 0, frees the textures) if initialised, so the next level re-inits it
RREL:
  lw v0,0(a0)
  beq v0,zero,rr_ret
  nop
  j 0x001C41A0
  nop
rr_ret:
  jr ra
  nop

# ---------- RMIRROR: entered from RADAR_UPDATE (0x000e04a0, replaces the one-time activation; t0 = radar 3/4).
# Radars 3-4 follow P2's radar (HUD+0x3F10 = 0x00604750): visible +4, shown +8, off +0xC
RMIRROR:
  lui at,0x0060
  lw v0,0x4754(at)            # P2 radar +4
  sw v0,4(t0)
  lw v0,0x4758(at)            # P2 radar +8 (shown)
  lw v1,0x475C(at)            # P2 radar +0xC (off)
  sltu v0,zero,v0
  sltiu v1,v1,1
  and v0,v0,v1                # P2 radar drawn?
  lw v1,8(t0)
  lw at,0xC(t0)
  sltu v1,zero,v1
  sltiu at,at,1
  and v1,v1,at                # this radar drawn?
  beq v0,v1,rm_done
  nop
  bne v0,zero,rm_on
  daddu a0,t0,zero
  jal 0x001C4448              # hide (+8 = 0), as HudUpdate does for P2's radar in merged view
  nop
  j 0xe04c4
  nop
rm_on:
  jal 0x001C4388              # show (+0xC = 0, +8 = 1; needs +4)
  nop
rm_done:
  j 0xe04c4
  nop
```

### Summary (addendum 1)
- **Panel (VERIFIED):** the HUD draw function calls PlayerHUD Draw only for slots 0-1, and B1 added only Update for
  slots 2-3. Player 3's panel was never drawn.
- **Panels only appear on events (VERIFIED):** each panel shows for 2000 units after an event, then fades over 1000.
  That is why players 1-2 have no panel in the screenshots either.
- **Radar 3:** it was initialised in Mission 1 and never released, because the level exit releases only radars 1-2.
  So level9 skipped its init and kept Mission 1's sprite handles. The draw is called; most likely the stale disc
  sprite fails its check (HYPOTHESIS; PINE reads in A3).
- **Latent:** PlayerHUD 2-3 are also never shut down at level exit, which would break later levels.
- **Fix, 110 new lines + 2 replaced B1 words:**
  - R1 draws PlayerHUD 2-3 after the 0-1 draw loop (0x001B1BC4);
  - R2 shuts down PlayerHUD 2-3 and releases radars 3-4 at level exit (0x001AEB34);
  - R3 makes radars 3-4 follow P2's radar on/off state.
- **Checks:** no new conflicts besides the 2 intended replacements.
- **The large P1/P2 discs are the expected single-player-size radar** (about 1/3 of the quarter, as in F-0103).

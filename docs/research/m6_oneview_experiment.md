# D23 experiment: can one PC run a true single view and stay in sync?

Date 2026-10-12. Build: fork binary w4p-m6-2 (`emulator/pcsx2/bin`), game SLUS-21215 v1.03, pnach = `mod/make_pnach.py`
output of today plus the TEST-ONLY groups below (`local/m6/oneview/test*.pnach`). Environment of every run: **SINGLE-PC,
2 instances, loopback, scripted boot + seeded random bots, MTVU off, 2x internal resolution, no impairment**.
Function and variable names are OUR labels (stripped ELF). Addresses are static unless marked "runtime".

## 1. Verdict: NOT FEASIBLE (VERIFIED)

**In plain English:** the game's simulation depends on what each PC draws. If one PC shows (and draws) something
different from the other PCs, the two games drift apart within seconds, even with identical controller input.

Example from the main run (`ov1_pure`): two PCs, same inputs. PC A runs today's mode (the game draws both players'
views, the emulator shows A its own quarter). PC B makes the game believe there is one full-screen view = player 2's
camera, like single player. Result:
- within about 3 s after the mission intro, both players already stand in slightly different places on B (0.001-0.006
  units);
- after about 13 s player 1 has 880 health on B but 900 on A (he lost 20 health only on B);
- after about 2 min 10 s player 1 stands 24 units and player 2 84 units away from where A has them.

The milder variants fail too:
- B keeps the game's normal two-view state and only **skips drawing** player 1's quarter (`ov3_draw`): positions differ
  after about 1 s.
- **Each PC draws only its own quarter**, so both do the same amount of drawing (`ov4_drawboth`, repeated as `ov5`):
  AI and character timers differ after about 1 s, positions and the random-number state after about 23 s.

The control run with identical patches on both PCs (`ov0_ctrl`) stayed identical in all 46 snapshots and all 18
full-RAM hash points, so the measurement itself is sound.

**Consequence for D23:** the switch condition ("switch only if the single-view instance stays in sync") is not met.
The safe arrangement is today's: every PC computes **and draws** all players' views, and only the emulator decides which
part of the finished picture to show (F-0071 E2, F-0082, F-0101: emulator-side presentation is free, game-side is not).
Recommendation: keep the current method and keep fixing split-screen leftovers (section 8).

## 2. Method

### 2.1 Test-only patch groups (`tests/m6/oneview_patch.py` -> `local/m6/oneview/groups.txt`; not in `mod/`)
| Group | What it does | Words |
|---|---|---|
| `[warriors-4p test oneview pN]` (N = 0..3, alternatives) | Hook at the end of `LayoutViewports` 0x00122ED0 (0x00123390 -> cave OV_CAVE 0x000E5E00). The cave saves what the game computed (views 0x0050B198 and the render list 0x000F0810[4]) into a shadow (0x000E5F00 / 0x000E5F10) and then, whenever the game would draw 2+ views, sets views = 1, render list = [active camera of player N (0x000F0800+4N)], layout mode 0x0050B1A4 = split orientation 0x0050B1A0, 0x0050B1A8/AA = 1. **All cameras keep updating:** the camera update loop `FUN_0011E878` (called from SimStep) walks the shadow list (0x0011E8A4/0x0011E920 -> SHGET 0x000E5E80, which falls back to the real list if a shadow camera is no longer an active camera; bounds 0x0011E90C/0x0011E948 read the shadow count). The "1 -> n views" camera setter in `LayoutViewports` reads the shadow previous count (0x00122EDC/0x00122EE8), so it fires exactly as on a normal PC | 8 sites + 56-word cave |
| `[warriors-4p test oneview shim]` (variant S1, with a pN group) | The four human/pad functions found to branch on the view count read the shadow count and shadow render list: `PadUpdateAll` FUN_001454A8 (0x001454FC via cave, 3 getter calls), player movement FUN_00244770 (0x00244A68/70, CAMSKIP2 replacing the [4p] word at 0x00244A80), camera auto-follow FUN_0023DC58 (0x0023DDE8/F0, 0x0023DE10), FUN_0024B3D8 (0x0024B3D8/E0, 0x0024B510) | 13 sites + 18-word cave |
| `[warriors-4p test drawonly pN]` (variant R) | Game state untouched (normal multi-view). Only the per-view draw calls of the frame render (`FUN_00156408`/`FUN_00156540`) to the world draw `FUN_0040E8D8(world, v)` and the sprite flush `FUN_00185B38(mgr, v)` go through a gate that returns at once for every view v != N while 2+ views are shown | 4 sites + 2 x 12-word caves 0x000E6000 |
| `[warriors-4p test fixedlod]` | (prepared, not run) adaptive draw distance off (0x0050C698 = 0) | 1 |
| `[warriors-4p test simsnap]` (on **every** instance) | SNAP(slot) at 0x000E2600, called through W4P CallAt at the same session polls on every instance (test-call mailbox, executed in FrameStats). Writes a 0x200-byte record into a 20-slot ring at 0x000E9800: poll, GameMgr fields (count, checkpoint, level, level end), rand() state (`*(*0x005169EC+0x58)`), static RNG object 0x006EB8A8, the 4 player handles, positions, health (`*(human+0xD4)+0x144`), a hash per human slot (60 slots of 0x6D0 at 0x00640C80: position, +0x1B0, health), hashes of all humans, all health, the AI brain array 0x006D53F0 (60 x 0x2F0), GameMgr (0x5800 bytes), the whole human pool, the object table 0x006EBD38, the game frame counter 0x0050C654, the 4 per-player camera vectors 0x005DDC90 (used by PadUpdateAll), hashes of the 4 active camera objects (0x480 bytes) and of the per-human table 0x00714B00 | 215-word function |

Runs `ov0`/`ov1` used the first SNAP version (0x180-byte records, 26 slots, no camera fields; `test.pnach`); runs
`ov2`-`ov5` the version above.
Checks: every "was" word is asserted against the ELF by the generator; `tools/note_patches.py check` on
`local/m6/oneview/test3.pnach`: the 6 known problems plus the intended alternatives (pN groups, drawonly pN groups) and
the intended override of 0x00244A80 (VERIFIED). Caves use free RAM from the STATE map (0x000E2600-0x000E295B,
0x000E5E00-0x000E5F87, 0x000E6000-0x000E606F, ring 0x000E9800-0x000EBFFF).

### 2.2 Runner `tests/m6/oneview_run.py`
Two sandbox instances in a W4P session on loopback (instances 2/3, 4/5, 1/20; never 6-11 or 15), fresh boot,
boot scripts `tests/m2/nav/boot_to_m1_2p.txt` + `p2_join.txt`, level jump CallAt `3999:0041ABC0:1,4009:00160D78:0x01FD9F9C`
(Mission 13), seeded random bots from session poll 5000, all M2-M6 groups (`own view`, `hud`, `4p`, `4p hud B1/B2`,
`4p spawn`, `spawn leave`, `inventory`, `fx`, `markers`, `session`, `missions`, `session call`) + `test call` + `test simsnap`
on both; slot 1 (player 2) also gets the variant group (in `ov4`/`ov5` both slots: `drawonly p0` on A, `p1` on B). The runner sets no W4P PatchSet string (empty on both), so the
W4P handshake accepts the pair although the pnach groups differ (log: "player 1 matches").
- The W4P full-RAM hash mismatches from the first hash point on purpose (the patch code itself is in RAM).
- **Simulation comparison** = SNAP records with the same poll on both instances (exact: taken at the same emulated
  moment), read through PINE every 6-40 s. Snapshots every 300 polls from session poll 4500, dense (every 10-20 polls)
  around the mission start in runs 2-5.
- **RAM dumps** of both instances at the same poll: W4P DumpRam writes at (first mismatching hash point + 8 x
  HashInterval); because the first hash point already differs, HashInterval H gives a dump at session poll 9H
  (H = 1000 -> guest poll 9001; H = 567 -> 5104). Compared with `tools/desync_diff.py` and a field-level diff.
- Poll -> time: the intro movie ends and gameplay starts at guest poll ~5004; 30 polls = 1 s of game time.

## 3. Results

| Run | PC B differs from PC A by | Snapshots identical | First difference (guest poll, game time after the intro) | State at the dump |
|---|---|---|---|---|
| `ov0_ctrl` (control) | nothing | **46 / 46**; W4P hash 18 / 18 equal | none | (no dump: no mismatch) |
| `ov1_pure` | true single view of player 2 (`oneview p1`) | 1 / 46 | 5101 (~3 s): both players' positions, human/brain/GameMgr hashes, frame counter (-1); player 1 health from 5401 (~13 s: 900 vs 880); rand() from 5701; RNG object from 6901 | poll 9001: player 1 24 units, player 2 84 units, AI companion 17 units apart; 1.29 MB heap + 7.2 KB .bss differ |
| `ov2_shim` | true single view + the 4 known logic readers on shadow values (S1) | 0 / 68 | **5004 (first gameplay frame): camera vectors 0x005DDC90 and both camera objects**; positions 5038 (~1 s); rand() 5201; health 5341 | 9001: player 1 35 units, player 2 52 units apart |
| `ov3_draw` | normal 2-view state, B draws only view 1 (R) | 1 / 68 | 5038 (~1 s): positions (0.01-0.15 units), brains; frame counter -2 at 5041 (intro cut-scene); rand() 5201; RNG object 5701 | 9001: player 2 53 units apart; 0.94 MB heap differs |
| `ov4_drawboth` | A draws only view 0, B draws only view 1 (same amount of drawing) | 1 / 69 | 5038 (~1 s): human-pool and AI-brain hashes; camera object 0 from 5181; AI human slot 6 from 5281; positions and RNG object 5701 (~23 s); rand() 6901 | 8101: player 1 42 units apart; 9001: 0.84 MB heap differs |
| `ov5_drawboth_dump` | as `ov4`, dump at 5104 | 2 / 27 | identical to `ov4` (deterministic) | 5104: see 4.3 |

All runs: 0 TLB misses on every instance (emulator logs copied to each run folder). Each instance is deterministic on
its own: B "draws only view 1" reached the same state in `ov3` and `ov4` (player 2 at 80.82, 344.68 at poll 9001 in both
dumps), and A in normal mode reached the same state in `ov0`-`ov3` (player 1 at 82.71, 380.77). So every difference is
caused by the per-PC draw/view difference, not by noise.
Evidence: `evidence/M6/oneview_<run>.json` (rows = every compared snapshot), `local/m6/oneview/<run>/` (snaps.json,
live.json, W4P logs, ini, bot files, dumps `w4p_slot*_t*.bin`, screenshots `s<slot>_t<s>.png`, emulogs).

## 4. Why: three separate ways the drawing feeds the simulation

### 4.1 Game logic reads the view layout (affects the true single view; VERIFIED code, VERIFIED effect)
In the original game "one view" means "co-op with a merged, shared camera", and the logic changes accordingly:
- `PadUpdateAll` FUN_001454A8 (0x001454FC): if views != cameras, the stick of every pad whose player is not on his
  plain follow camera is turned with render camera 0 instead of the player's own camera.
- Player movement FUN_00244770 (0x00244A70): the player's own-camera direction is used only if views == cameras.
- Camera auto-follow FUN_0023DC58 (0x0023DDF0): only if player count == views.
- Human LOD distance: FUN_0023D660 stores at human+0x334 the distance to the **nearest drawn camera**
  (`FUN_00120230`, loop over views) and passes it to the model/animation streamer `FUN_0018A430`.
- Particle/blood/debris/paint effects spawn only if visible in a drawn view (`FUN_003A51F8` loops over the views with
  the frustum test `FUN_003A50E0`; callers 0x003A7D58-0x003D9D50 use names like blood_splatter, sub_sweat_effect,
  dyn_paintcan_brk) and the effect code draws from the RNG object that gameplay shares (F-0058).
- AI code uses render camera 0 (= "the" camera) directly, e.g. FUN_002A4230 (with RNG 0x006EB880), FUN_0021D928,
  FUN_00232230, FUN_0028C1A8.
S1 shows that patching four of these is not enough: the camera objects already differ at the first gameplay frame,
because the camera module itself reads the view count/layout in about 30 places (section 5).

### 4.2 What is drawn changes emulated time (affects every variant; VERIFIED)
Drawing costs EE time. The game keeps its logic at a fixed 30 Hz, but several things run on the **emulated real-time
clock**:
- `SimAdvance` 0x003A2EA0 runs a logic tick only when enough GameClock time has passed (sixty_fps.md), so rendered
  frames per tick depend on the draw cost (frame counter 0x0050C654 differed by 1-2 at the same poll in `ov1`/`ov3`).
- FrameStats `FUN_001569C0` measures the frame rate (0x0050C680) from a millisecond timer; with the adaptive draw
  distance on (0x0050C698 = 1 at runtime in every dump), `FUN_0040E8D8` moves the far distance (+0x58, setter
  `FUN_00122128`) of render camera 0 with it. The far plane is part of the frustum used by the effect visibility test.
  Seen at runtime only in `ov1_pure` (player 2's camera: far distance 40.0 on A, where it is not render camera 0, and
  115.0 on B, where it is); in the draw-only runs the far distances were equal at the dumps (VERIFIED code, effect on
  sync not isolated: the prepared `fixedlod` group was not run).
- The human update copies a clock value (`*(DAT_0050B734+0x48)`) into every human (+0x2A0, `FUN_0023D660`, VERIFIED
  code). AI brains hold the same value at +0x30 (HYPOTHESIS: the same clock; equal values 0x9C6/0x9C5 in 4.3).

### 4.3 Proof that 4.2 alone breaks sync (`ov5`, both PCs draw one view each, dump at poll 5104)
Only these differ at 5104 (field diff of the two dumps):
- human +0x2A0 in all 10 live humans: 0x9C6 on A vs 0x9C5 on B (one clock unit; slot 5: 0x7F2 vs 0x7D1); +0x294 in 3
  humans (one unit, e.g. 0xDAE vs 0xDAD); slot 5 also +0x50 (2.017 vs 1.983) and +0x334 (camera distance, last bits);
- AI brain +0x30 in all 10 (0x9C6 vs 0x9C5), +0x160 in 2;
- FrameStats timer 0x0050C688 (differs by 433), counters 0x0050C42C/0x0050C430/0x0050C44C and copies in 0x005E2xxx
  (differ by 2), one slot of the measured-frame-rate ring 0x005E53D8 (0x005E5400: 30.03 vs 30.12);
- positions, health, RNGs, GameMgr: still equal.
So drawing a different quarter (view 0 vs view 1: different scenery = different cost) shifted the emulated clock by one
unit within about one second; the AI then acts on different timers and positions follow (~23 s in `ov4`).
This is the same effect as Stage 1's E3 (waiting inside the game breaks determinism even with the fixed-step clock).

## 5. Readers of the view count / render camera list (the desync risks a true single view would have to neutralise)
Direct loads of ViewsRendered 0x0050B198 / ActiveCameras 0x0050B19C / layout 0x0050B1A4-0x0050B1AA (ELF scan with
`lui` tracking; VERIFIED sites, roles from decompile where stated, otherwise by code region = HYPOTHESIS):
- **Game logic (camera module, cameras feed the simulation, F-0071):** FUN_0011C0B8, 0011C470, 0011E440 (camera
  delete), 0011E878 (camera update), 0011EE08 (set active camera), 00120A98 (camera view window, layout mode),
  00121888 (merge state), 00124000, 001254F0, 00125588, 00125CC0, 001260E8, 00126C40 (follow camera update), 001276A0,
  00127AC8, 001282A0 (camera target picker), 00128CF0, 00129050 (camera stick input, layout mode), 0012AE58, 0012DED8,
  00130990, 001361A8, 00137E08, 0013B5D8, 0013B7B8, 0013BAD0, 0013C710, 0013CCD8, 0013CF20.
- **Game logic (input/humans):** 001454A8 PadUpdateAll; 0023DC58 camera auto-follow; 00244770 movement direction;
  0024B3D8 (with ScreenEffects 0 state); 00214138 (layout mode); 00101DD8 (large engine function, unclassified).
- **Drawing/HUD:** 00122ED0 (writer), 001567F8, 00195C78 (viewport rectangle), 001AF010 (HUD); unclassified:
  001673B8 / 001679E8 (camera eye height, callers 0x001681A0).
- Through the getter `FUN_0011EAE0` (40 functions): drawing 00156408/00156540 (frame render), 0017FD78, 00184568,
  00185D20, 0018B058, 0018DAC0, 00190588, 00195400, 00195C78, 001968C0, 00196B58, 001AB348, 001AF010, 001B1640,
  001B1688, 001B26A8, 001B2790, 001C5210; logic or mixed: 00120230 (nearest-camera distance, used for human LOD),
  001202E8, 00120380, 00158728 (in-game update: listener buffer and HUD loop), 00214138, 0023EAB8, 00249CB0, 0024A230,
  0024B2A8 (player tint in a shared view), 0024B780, 003A51F8 (effect visibility), 003A87D8, 003CA9D8, 003CAED8
  (effect budget scaled by views), 003D70E8.
- Render camera getter `FUN_0011F9B0` (297 call sites in 162 functions; by code region): engine/script 6, camera module
  28, pads 2, game modes/frame 20, render/sprites/fx/HUD 39, **humans/AI/combat 30** (e.g. 0021D928, 00232230,
  0023DC58, 00244770, 0024A230, 0024B780, 0028C1A8, 002A4230), Lua/world 5, particles/effects 17, world render/other 15.
  Many use index 0 as "the camera" or "views > 1 ? player index : 0".
- Not covered by the scan: gp-relative or computed accesses; per-view state that is not addressed through these
  globals (per-view light slots, ScreenEffects per view, HUD per view).

## 6. What the single view looked like (`ov1_pure`, screenshots `local/m6/oneview/ov1_pure/s1_t*.png`, 2x)
- One full-screen 4:3 view at the full internal resolution (1280x896 at 2x), no crop (W4P crops only with 2+ views).
- Radar at single-player size in the bottom-right corner, with the game's 'W' markers (no "2P" icon as in A's quarter).
- Camera: player 2's camera framed the scene oddly (player 2 small at the left edge, hidden behind a wall at t=420 s);
  HYPOTHESIS: with one view the camera logic falls into the shared co-op camera rules (target picker FUN_001282A0 and the
  follow update read the view count).
- No name/health panel was visible at the captured moments (also not in A's quarter).
- Would still need work even if it stayed in sync: the camera rules above, the HUD of a shared view (the game's merged
  co-op HUD, player tint FUN_0024B2A8), players 3-4.
Not run: the 4-player variant. A 2-player failure already decides the question, and the coordinator asked for at most
2 emulators at a time during the network measurements.

## 7. What a full implementation would need (and why it is not recommended)
To let each PC draw only its own view, the simulation must stop depending on drawing in all three ways:
1. Every logic reader of the view layout/render list (section 5: about 30 camera functions, 6+ human/pad functions,
   about 30 human/AI functions using render camera 0, effect visibility) would read a "logical" multi-view state,
   while the drawing side gets the single view. Some functions mix both (in-game update, effects).
2. Effects that use the shared RNG would need their own random stream (or be gated by logical, not drawn, views).
3. Every use of the emulated real-time clock in game logic (SimAdvance's frame pacing, FrameStats timer and the adaptive
   draw distance, the clock copied into humans and AI brains, and whatever else reads GameClock: Stage 1's E3 already
   showed that the fixed-step clock mode alone is not enough) would have to become identical on every PC, either by
   patching each clock read to a tick-derived value or by an emulator change that gives every PC the same guest time per
   poll regardless of draw cost (no such W4P option exists today; it would have to fake the timers/vsync counters the
   game reads, which is a deep change).
Effort: open-ended; several weeks at least, with a high risk that more time paths remain (audio, streaming, CD timing).
Every step would need long lockstep runs to prove. Point 3 alone defeats even "each PC draws only its own quarter".

## 8. Recommendation and options for the user
- **A (recommended): keep today's method** (every PC runs and draws all views; the emulator shows the own quarter, D8).
  Keep fixing the split-screen leftovers in a way that is identical on every PC (FOV fix F-0198, radar, HUD, labels).
  Picture sharpness of the cropped quarter can be raised with the emulator's internal resolution, which does not affect
  sync (F-0101).
- B: a time-boxed research spike (about 1-2 days) on point 3 only: list every GameClock/timer read, patch them to the
  logic tick, and retest "each PC draws only its own quarter" (`ov4`). Only worth it if the user strongly wants full
  single-player rendering; even a success there leaves points 1-2.
- C: drop the idea.

## 9. Files
- Generator `tests/m6/oneview_patch.py` (groups, assembler extension for xor/sltiu/.word), runner `tests/m6/oneview_run.py`.
- Test pnachs `local/m6/oneview/base.pnach` (make_pnach output), `groups.txt`, `test.pnach` (runs 0-1), `test2.pnach`
  (runs 2-4), `test3.pnach` (run 5; adds `fixedlod`).
- Runs `local/m6/oneview/ov0_ctrl`, `ov1_pure`, `ov2_shim`, `ov3_draw`, `ov4_drawboth`, `ov5_drawboth_dump`; summaries
  `evidence/M6/oneview_<run>.json`.

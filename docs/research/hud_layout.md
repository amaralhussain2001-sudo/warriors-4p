# HUD layout per player/view: static analysis (2026-10-11)

Scope: where the HUD (radar, rage/health panel, widgets, markers, text) gets its screen position, why the radar ends
up outside each player's quarter with the 2x2 layout patch (F-0095), the smallest patch to fix it for 2 views, what
4 players need, and whether any of this touches the simulation.
Build: SLUS-21215 v1.03 (`local/disc/SLUS_212.15`). Method: Ghidra decompile (`local/analysis/all/*.c`), our own
disassembly of the ELF for the patch site (small R5900 decoder, scratch script), initial data values read from the ELF.
Function names are OUR labels (stripped ELF). No runtime test was done for this note.

## 1. How positions are computed

### 1.1 Viewports (for reference)
- `ViewportRect` (our label, FUN_00195c78, virtual): for view `i`, rect = (i % C * W/C, i / C * H/R, W/C, H/R) with
  **C = u16 at 0x0050B1A8 (columns)** and **R = u16 at 0x0050B1AA (rows)**. It also gives each view a second object
  whose 2D size is (W/C, H/R). VERIFIED (decompile 0x00195C78).
- `LayoutViewports` (0x00122ED0) sets mode 0x0050B1A4: 0 → C=2,R=1 (side by side, the original 2-player layout);
  1 → C=1,R=2 (top/bottom); 2 → 2x2. Our patch at 0x00123300 makes mode 2 from 2 views. VERIFIED (decompile).
- **Naming bug in our code (outside this note's scope, please check):** `W4P.cpp` uses kLayoutRows = 0x0050B1A8 and
  kLayoutCols = 0x0050B1AA, which is swapped. Harmless with 2x2 (both 2), wrong for side-by-side or top/bottom.

### 1.2 The HUD does NOT use the viewport rectangles
The HUD manager (static object 0x00600840, F-0030) is updated every frame by `HudUpdate` (our label, FUN_001AF010,
called twice from the in-game update FUN_00158728). It places each player's HUD from **hard-coded constants chosen by
the split mode 0x0050B1A4**, and only distinguishes mode 1 from "everything else". Mode 2 (our 2x2) takes the mode-0
(side-by-side) branch. VERIFIED (decompile + disassembly 0x001AFEF8-0x001AFFD0).

| Element | Objects | Position source | 2x2 with 2 players |
|---|---|---|---|
| **Radar** (RadarHUD; FUN_001C5210 sits among RadarHUD.cpp functions 0x001C41A0-0x001C6730) | HUD+0x15D0 (P1), HUD+0x3F10 (P2), stride 0x2940; position vec4 stored at object+0x2930 | 3D HUD-camera vector (x, y, z, 1). Mode ≠ 1: P1 = (0x0050D434, 0x0050D438, 0x0050D430), P2 = (0x0050D428, 0x0050D42C, 0x0050D430). Mode 1: P1 = (D428, D438, **0.15**), P2 = (D428, D42C, **-0.33**). x = horizontal, z = vertical (mode 1 separates top/bottom only by z). Initial values: D428 0.49, D434 -0.51, D42C/D438 1.0, D430 -0.31 (never written; overwritten x/y per display flags each frame, e.g. ±0.47/0.48, ±0.61) | **WRONG**: z = -0.31 = bottom of the full screen, i.e. in the bottom quarters (matches F-0095) |
| Per-player widget (unidentified; same function uses strings "%s %02d", "Spray", "Flash", "Blades", "Give Money") | HUD+0x177D0 (P1), HUD+0x18280 (P2) | same vector, but `WidgetSetPos` (FUN_001AA630) **forces z = -0.31** (`lui at,0xbe9e; ori at,0xb852; swc1 f0,8(sp)` at 0x001AA638-0x001AA648) | **WRONG** (bottom of full screen) |
| Rage/health panel (FUN_00214138 uses "vags/interface/rage_indicator_02") | per player index | normalized full-screen [0,1] table 0x0050FA10 + idx*16: P1 (0.10, 0.05) top-left, P2 (0.785, 0.05) top-right; mode-1 override for P2 at 0x0050FA30 (0.04, 0.56). FUN_00211EF8 adjusts per display flags (e.g. 0.13/0.79, y 0.17) | **OK** (both inside their top quarters) |
| Split divider (19 pieces, HUD+0x137E0, stride 0x100) | shared | mode 0: vertical line (pieces stacked at x 0.5); mode ≠ 0: horizontal line at z 0.5, pieces rotated pi/2 | mode 2 draws only the horizontal centre line (cosmetic; may appear at the bottom edge of each crop) — HYPOTHESIS |
| Per-player label objects HUD+0x135E0/0x136E0 (loop `< 2`, shown when that player's stick leaves 64..176 and camera type ∈ {0,1,5,9}) | 2 | not traced | unknown — HYPOTHESIS |
| World markers ("2P" over player 2, F-0085) | per view | HYPOTHESIS: drawn through the per-view 2D layer set up by ViewportRect, so they follow each view automatically (consistent with F-0085: marker appears inside player 1's view) | probably OK |
| Objective/tutorial/message text (MessageHUD, TutorialHUD) | full screen | not traced; FUN_00122D48 adjusts [0,1] x for the HUD aspect (CamSetHUDAspect → 0x0050B208 = 4/3) | unknown: centred/bottom text may land between or below the top quarters — needs a runtime look |

Lua can also move HUD pieces: `HUDCenterComponents` (0x0036EF50 → FUN_001B5DD8, 10 x/y pairs) and `CamSetHUDScale`
(0x0050B20C), `CamSetHUDAspect` (0x0050B208). VERIFIED (bindings). Which missions call them: not checked.

## 2. Smallest patch for 2 views in the 2x2 grid (each HUD inside its own quarter)

Idea: when mode == 2, keep the mode-0 x positions (P1 left column, P2 right column) and use the mode-1 *top-row*
height (z = 0.15, the value the developers use for the radar of the top view in top/bottom split) for both players.
Mode 0 and mode 1 behave exactly as before.

**Patch A (radar, conditional on mode 2) — code cave at 0x000F0600** (region observed all-zero, F-0050; M1 uses
0x000F0400-0x000F045C and 0x000F0500). At the site, v1 = mode (loaded at 0x001AFEFC) and v0 = 0x00510000 (set in the
branch delay slot at 0x001AFF04); `at` is free.

```
patch=2,EE,001AFF30,word,0803C180 // was 3C030051 (lui v1,0x51) -> j 0x000F0600
patch=2,EE,001AFF34,word,00000000 // was C455D430 (lwc1 f21,d430) -> nop (delay slot)
patch=2,EE,000F0600,word,C455D430 // lwc1 f21,-0x2bd0(v0)   z = D430 (default)
patch=2,EE,000F0604,word,24010002 // addiu at,zero,2
patch=2,EE,000F0608,word,14610004 // bne v1,at,+4 (-> 0x000F061C)
patch=2,EE,000F060C,word,C441D434 // lwc1 f1,-0x2bcc(v0)    P1 x = D434 (delay slot, always)
patch=2,EE,000F0610,word,3C013E19 // lui at,0x3e19
patch=2,EE,000F0614,word,3421999A // ori at,at,0x999a      0.15
patch=2,EE,000F0618,word,4481A800 // mtc1 at,f21            z = 0.15 when mode == 2
patch=2,EE,000F061C,word,C454D428 // lwc1 f20,-0x2bd8(v0)   P2 x = D428
patch=2,EE,000F0620,word,0806BFD2 // j 0x001AFF48 (common code)
patch=2,EE,000F0624,word,4600A886 // mov.s f2,f21           P1 z = P2 z (delay slot)
```
Encodings checked against the game's own instructions (C455D430, C454D428, 4481A800, 4600A886 occur verbatim at
0x001AFF34/40/24/44). After the cave v1 holds the mode instead of 0x00510000; v1 is reloaded at 0x001AFF9C before its
next use. VERIFIED (code reading) / HYPOTHESIS (visual result, exact height 0.15 may need tuning).

**Patch B (widget follows the radar height):** `patch=2,EE,001AA648,word,00000000` (was E7A00008 `swc1 f0,8(sp)`), so
`WidgetSetPos` keeps the caller's z. Its only callers are the three sites in HudUpdate (0x001AFF80, 0x001AFFCC and the
single-view path); in single view and mode 0 the caller's z is D430 = -0.31, the same value that was forced, so those
cases are unchanged; mode 1 widgets would follow their radar. VERIFIED (code) / HYPOTHESIS (indirect callers: none
found by grep of direct calls only).

Rage/health panel: no patch for 2 players. Text messages: check at runtime first.

Both patches only make sense together with the 2x2 layout patch (0x00123300) and only during online sessions (R-18).

## 3. Four players
Everything above is built for exactly two HUDs:
- 2 RadarHUD objects (HUD+0x15D0/+0x3F10, stride 0x2940; the next slot would overlap other HUD fields such as
  +0x6850/+0x7660), 2 widgets (+0x177D0/+0x18280), P1/P2 handled by unrolled code in HudUpdate, loops `< 2`.
- Rage panel table has 2 entries; index 2 would read the mode-1 override at 0x0050FA30, index 3 unknown data.
- `MakePlayer` tries 2 HUD slots (F-0056).
Option 4A (recommended): create HUD objects for players 3/4 in free RAM (0x00096000-0x000EFFFF observed zero, F-0050;
2 radars ≈ 21 KB), construct/update/draw them from a cave next to the P1/P2 calls (FUN_001C4388/FUN_001C4448 init,
FUN_001C5210 update, FUN_001AA630 widget), and give each player position = own quarter (x: D434/D428 by column,
z: 0.15 top row / -0.33 bottom row, mirroring modes 0 and 1); relocate the rage table to 4 entries
((0.10,0.05),(0.785,0.05),(0.10,0.55),(0.785,0.55)). Large; belongs to M2/M3.
Option 4B (not recommended): each PC shows only its local player's HUD. HUD memory would then differ between PCs
(hash mismatches) and Lua reads some HUD state (e.g. `HUDANGetCredit`, `HUDCheckTutorialText`), so it risks desync.

## 4. Does HUD layout affect the simulation?
- The position constants 0x0050D428-0x0050D438 are referenced only by HUDInterface functions (FUN_001AD588,
  FUN_001AF010); the rage table only by FUN_00211EF8/00212840/00214138/00214BC8 (HUD panel code). VERIFIED (grep of
  decompiled code; direct references only).
- HudUpdate runs inside the in-game update and writes HUD-manager memory, which our full-RAM hash covers. A patch
  applied identically on every PC keeps all instances identical. VERIFIED (call site 0x00158728) / HYPOTHESIS that no
  gameplay code reads HUD positions (no reader found).
- Conclusion: render-side, deterministic if every PC applies the same patch. Any per-PC difference in HUD state
  (option 4B) is not safe.

## Open items
1. Runtime check of patches A+B in 2x2 nocrop/crop screenshots (radar and widget inside the top quarters; height).
2. Locate objective/tutorial/message text placement and test it in 2x2.
3. Identify the per-player label objects at HUD+0x135E0/0x136E0 and the widget at +0x177D0.
4. Fix the rows/columns naming in `W4P.cpp` (0x0050B1A8 = columns, 0x0050B1AA = rows).

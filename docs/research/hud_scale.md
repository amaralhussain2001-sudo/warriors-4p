# HUD scale in the 2x2 layout (static analysis, 2026-10-11)

Scope: after the presentation crop magnifies a player's quarter 2x, the HUD looks twice as big as in single-player
(runtime `local/m3/h2_hud_crop/slot0_end.png`, patch group `[warriors-4p hud]`). This note explains how HUD size and
position work and proposes patches. Static analysis only; nothing was run. Function names are OUR labels (stripped ELF).
Build: SLUS-21215 v1.03. All "was" words below were read from `local/disc/SLUS_212.15`; new encodings were checked
field by field with a script.

## 1. How HUD scale and position work

### 1.1 Two kinds of HUD camera (VERIFIED, decompile)
The camera manager (pointer at static 0x0050CDB4) owns:
- **One global HUD camera** (vtable +0x74). `FUN_00195400` sets it up every frame with:
  - view window (half-extents) `(S*A*0.5, S*0.5)`, where **S = HUD scale at 0x0050B20C** and
    **A = HUD aspect at 0x0050B208**;
  - near clip 0.5, far clip 1e7, identity matrix (0x005117A0).
  - Its viewport is the whole screen.
- **One per-view HUD camera per view** (vtable +0x7C(i)). `FUN_00195400` creates them with the same window.
  `ViewportRect` (`FUN_00195C78`) then gives each one:
  - **viewport = that view's rectangle** (pixels; columns C = 0x0050B1A8, rows R = 0x0050B1AA);
  - **view window = global window / (C, R)**: `mul.s f20,f0,f22` at 0x00196370 (f22 = 1/C) and
    `mul.s f15,f0,f23` at 0x00196398 (f23 = 1/R).

  So anything drawn through a per-view HUD camera has the **same pixel size as on a full screen**, which is why it
  looks 2x big after our crop.

### 1.2 Where S and A come from (VERIFIED, decompile `FUN_00194558` and `FUN_00194E28`)
| Display mode (camera manager flags) | S | A | Camera aspect (0x0050B204) |
|---|---|---|---|
| 4:3 | 1.0 | 1.45 (0x3FB9999A) | 1.3333 |
| widescreen (flag 4) | 1.1 (0x3F8CCCCD) | 1.6667 (0x3FD5551D) | 1.6667 |
| flag 0x20 mode | 1.0 | 1.59 (0x3FCB851F) | 1.59 |

- Lua can change both values: `CamSetHUDScale` (binding 0x00367350) writes S, `CamSetHUDAspect` writes A.
- The ELF's static values (S 1.0, A 1.3333) are overwritten at runtime.
- **Which row applies at runtime is a HYPOTHESIS:** 4:3 for the user's setup.

There is **no per-player or per-view HUD scale.** S and A are global.

### 1.3 Which HUD elements use which camera
| Element | Drawn with | Coordinates | Status |
|---|---|---|---|
| **Radar** (`FUN_001C60B0` draw, `FUN_001C5210` update; objects at HUD+0x15D0 and HUD+0x3F10) | global HUD camera (`BeginUpdate` via vtable +0x74/+0x60) | camera space. The position vec4 at object+0x2930 is (x, depth, z). The disc is drawn around (x, z, −depth) with radius `0x0050E9BC (0.9) × 0.19 × …`. Blips are placed at (x+dx, depth, z+dz) with dx/dz scaled by `0.9 × 0.12` | VERIFIED |
| Per-player widget (HUD+0x177D0, +0x18280) | built from the same (x, depth, z) vector by `FUN_001AA630` (z forced to −0.31 unless patch B) | same | VERIFIED (vector) / HYPOTHESIS (camera) |
| Rage/health panel, text (widget system `FUN_001B9480` position at +0x1C0, text `FUN_001B9600`) | 2D path | normalized [0,1] full-screen coordinates. Table 0x0050FA10 (P1 (0.10, 0.05), P2 (0.785, 0.05)). `FUN_00122D48` adjusts x for aspect and y by the camera manager's vtable +0xC4 value | VERIFIED (coordinates) / HYPOTHESIS (that [0,1] maps to the full screen) |
| Sprite items (sprite manager at 0x0050CD4C, flushed by `FUN_00185D20`) | each item has a **view byte at +0x42** (set by `FUN_001828E0`, its 10th argument). 0..views−1 is drawn with that view's per-view HUD camera; 0xFF is drawn with the global HUD camera | VERIFIED |
| "1P"/"2P" world markers (F-0085) | probably view-tagged sprites (they appear inside each view; `local/m3/c3b_merge/sheet.png`) | | HYPOTHESIS |

**What single-player uses (VERIFIED, HudUpdate single-HUD path at 0x001B0108):**
- The only radar sits at (x = D428 = +0.51, depth = D42C = 1.0, z = D430 = −0.31), which is **bottom-right**.
- In 4:3 that is NDC (0.703, −0.62): about 85 % from the left and 81 % from the top.
- The task statement assumed bottom-left. The game's single-player radar is bottom-right. (In 2-player mode 0, P1's
  radar uses D434 = −0.525, bottom-left.)
- The radar position constants depend on the display mode:
  - 4:3: D434 −0.525 / D428 0.51, depth 1.0;
  - widescreen: depth 0.95 with x ±0.67;
  - another mode: depth 1.3 with x 0.48 / −0.47.

  The developers changing *depth* per mode suggests the HUD camera is **perspective**, so depth changes apparent size
  (**HYPOTHESIS, likely**; not proven statically).

## 2. Smallest patches for 2 players in layout mode 2

**There is no single global switch.** All elements that belong to one player (radar, widget, rage panel, text) are
drawn in **one full-screen pass with one global camera**. A per-player 2D transform therefore has to be applied per
element. Two separate pieces:

### 2A. Radar + widget: one cave, driven by the game's own S and A (recommended)
Map the single-player radar into each player's quarter at half size.

**Formula:**
- W = S·A/2 and Wz = S/2 (read at runtime, so widescreen and Lua changes are handled).
- d = the radar depth constant.
- Single-player position: xs = D428, zs = D430.
- Player 1 (top-left): x = xs − d·W, z = zs + d·Wz, depth = 2d.
- Player 2 (top-right): x = xs + d·W, z = zs + d·Wz, depth = 2d.

Under perspective, doubling the depth halves the size of the disc, the map, the blips and the widget. The x and z
offsets put the single-player layout into the quarter. Proof: NDC' = 0.5·NDC_sp ± 0.5.

**How it hooks in:**
- The cave hooks the common join of all 2-player paths at 0x001AFF48 and returns to 0x001AFF58.
- Player 2's depth is passed in **f23**. HudUpdate saves f23 in its prologue (0x001AF064) and first writes it at
  0x001B06AC, so f23 is free here (VERIFIED, disassembly of 0x001AF010-0x001B1640).
- Modes 0 and 1 run the original logic: same x, z and depth values.

**This replaces the current `[warriors-4p hud]` patch A.** Drop its lines 0x001AFF30/0x001AFF34 so those words return
to their originals; the old cave words are overwritten. Keep patch B.

```
patch=2,EE,001AFF48,word,0803C180 // was 3C020051 (lui v0,0x51) -> j 0x000F0600
patch=2,EE,001AFF4C,word,00000000 // was 3C013F80 (lui at,0x3f80) -> nop (delay slot)
patch=2,EE,001AFFA4,word,4600B806 // was C460D42C (lwc1 f0,D42C) -> mov.s f0,f23 (P2 depth from the cave)
patch=2,EE,001AA648,word,00000000 // patch B unchanged: was E7A00008; widget keeps the caller's z
patch=2,EE,000F0600,word,3C020051 // lui v0,0x51
patch=2,EE,000F0604,word,3C013F80 // lui at,0x3f80
patch=2,EE,000F0608,word,4481B000 // mtc1 at,f22              (1.0, as the original 0x001AFF50)
patch=2,EE,000F060C,word,C440D438 // lwc1 f0,D438(v0)         P1 depth d1 (as the original 0x001AFF54)
patch=2,EE,000F0610,word,C457D42C // lwc1 f23,D42C(v0)        P2 depth d2
patch=2,EE,000F0614,word,8C43B1A4 // lw v1,B1A4(v0)           layout mode
patch=2,EE,000F0618,word,24010002 // addiu at,zero,2
patch=2,EE,000F061C,word,14610013 // bne v1,at,0x000F066C     not the 2x2 mode: keep original values
patch=2,EE,000F0620,word,00000000 // nop
patch=2,EE,000F0624,word,C443B20C // lwc1 f3,B20C(v0)         S
patch=2,EE,000F0628,word,C444B208 // lwc1 f4,B208(v0)         A
patch=2,EE,000F062C,word,3C013F00 // lui at,0x3f00            0.5
patch=2,EE,000F0630,word,44812800 // mtc1 at,f5
patch=2,EE,000F0634,word,460518C2 // mul.s f3,f3,f5           Wz = S/2
patch=2,EE,000F0638,word,46032102 // mul.s f4,f4,f3           W = A*S/2
patch=2,EE,000F063C,word,C446D428 // lwc1 f6,D428(v0)         xs (single-player radar x)
patch=2,EE,000F0640,word,C447D430 // lwc1 f7,D430(v0)         zs
patch=2,EE,000F0644,word,46040202 // mul.s f8,f0,f4
patch=2,EE,000F0648,word,46083041 // sub.s f1,f6,f8           P1 x = xs - d1*W
patch=2,EE,000F064C,word,46030202 // mul.s f8,f0,f3
patch=2,EE,000F0650,word,46083880 // add.s f2,f7,f8           P1 z = zs + d1*Wz
patch=2,EE,000F0654,word,46000000 // add.s f0,f0,f0           P1 depth = 2*d1
patch=2,EE,000F0658,word,4604BA02 // mul.s f8,f23,f4
patch=2,EE,000F065C,word,46083500 // add.s f20,f6,f8          P2 x = xs + d2*W
patch=2,EE,000F0660,word,4603BA02 // mul.s f8,f23,f3
patch=2,EE,000F0664,word,46083D40 // add.s f21,f7,f8          P2 z = zs + d2*Wz
patch=2,EE,000F0668,word,4617BDC0 // add.s f23,f23,f23        P2 depth = 2*d2
patch=2,EE,000F066C,word,0806BFD6 // j 0x001AFF58             (stores f1,f0,f2,f22 then the P2 path)
patch=2,EE,000F0670,word,00000000 // nop
```

**Register safety:**
- At the join, f3-f8 are scratch registers: caller-saved, with no value live up to the `jal` at 0x001AFF80.
- v1 is reloaded or unused before its next read.
- The mode-1 path reaches the join through `b 0x001AFF48` (0x001AFF28), so it also gets f23 = D42C.

VERIFIED (disassembly) / HYPOTHESIS (visual result).

**Runtime check:**
- (a) The radar should be about half the size it is now, in the bottom-right of each quarter.
- (b) If the radar keeps its size but moves, the projection is parallel. Then use instead:
  - x = 0.5·xs ∓ 0.5·W and z = 0.5·zs + 0.5·Wz at the original depth;
  - in mode 2, halve the radar size constant `0x0050E9BC` (0.9 → 0.45; read only by the radar, at 0x001C60B0 and
    0x001C5210);
  - blip sprites (`0x0050E9CC`) would then stay full size.
- If bottom-left is preferred, load xs from D434 instead of D428: 0x000F063C `C446D434`.

### 2B. View-tagged sprites (markers): undivided per-view HUD window (optional, unconditional)
```
patch=2,EE,00196370,word,46000506 // was 46160502 (mul.s f20,f0,f22) -> mov.s f20,f0
patch=2,EE,00196398,word,460003C6 // was 461703C2 (mul.s f15,f0,f23) -> mov.s f15,f0
```
- Each per-view HUD camera keeps the full-screen window, so view-tagged sprites become half size in their quarter.
- This distorts per-view HUD items in the original modes 0 and 1 (C ≠ R). It is safe only in online sessions with the
  2x2 patch, where 2+ views always means C = R = 2, and 1 view means C = R = 1 (no change).
- HYPOTHESIS: the marker positions are computed from the per-view camera, so they stay on the characters. Check at
  runtime.

### 2C. Rage/health panel and text: not solved statically
- In 2x2 the rage panel is already inside each player's top quarter (table 0x0050FA10), but at 2x size after the crop.
- Positions could be remapped as p' = 0.5·p_sp + (column·0.5, 0): P1 (0.05, 0.025), P2 (0.55, 0.025) in table
  entries 0x0050FA10/18 and 0x0050FA20/28.
- The panel's size control was not traced. `FUN_001B94E0` multiplies the position vector by the widget field +0x1D0,
  which might be that widget's scale; HYPOTHESIS.
- **Centred full-screen text** (objectives, subtitles, button prompts using [0,1] full-screen coordinates) would be
  drawn around the screen centre, where the four quarters meet. After the crop, each player would see only a corner of
  it. HYPOTHESIS; this needs a runtime look and is the largest remaining HUD problem.

## 3. What stays wrong, and what 4 players need
- **Remaining for 2 players:**
  - rage panel size;
  - shared centred text and prompts (2C);
  - the split-divider pieces (HUD+0x137E0, horizontal line at z 0.5 in mode ≠ 0), which may show at a quarter edge;
  - per-player label objects HUD+0x135E0/0x136E0 (not traced).
- **4 players:**
  - The game has 2 radar objects, 2 widgets and 2 rage entries (docs/research/hud_layout.md §3). Two more radar
    objects need building in free RAM.
  - The 2A formula extends naturally to the bottom row: z = zs − d·Wz.
  - The cave would loop over 4 objects, and the rage table needs 4 entries.
  - Text needs a per-quarter copy or a different policy.

## 4. Simulation effect
- HudUpdate runs inside the in-game update and writes HUD memory, which our full-RAM hash covers.
- The patches are deterministic when every PC applies the same patch group.
- No gameplay reader of the radar vector, HUD scale or view windows was found. HYPOTHESIS; direct references only.

## 5. Out of scope, but noticed
**`FUN_00120A98` also derives the split mode.** It is the per-camera FOV and view-window update:
`sltiu v0,v0,3` at **0x00120B8C** (word 2C420003, unpatched).
- With 2 views it sets mode = `CamSetSplitMode` value (0), and gives 3D cameras side-by-side view windows (x halved,
  y full).
- Our 2x2 patch only changed 0x00123300 in `LayoutViewports`.
- If this function runs after `LayoutViewports`, the 3D picture in each quarter could be horizontally stretched 2x.
  HYPOTHESIS. The h1/h2 runtime suggests HudUpdate sees mode 2.
- Check one character's proportions in a crop against single view. If stretched, apply
  `patch=2,EE,00120B8C,word,2C420002`.

## Summary
- **Two HUD camera kinds.** A global HUD camera has window (S·A/2, S/2): S = 0x0050B20C (1.0 in 4:3, 1.1
  widescreen), A = 0x0050B208 (1.45 / 1.6667 / 1.59). Per-view HUD cameras have viewport = view rect and window =
  global/(C,R), set at 0x00196370/0x00196398. So per-view items keep full-screen pixel size, which is 2x after our
  crop. There is no per-player or per-view HUD scale.
- **Radar and widget** are drawn with the global camera in camera space (x, depth, z). The single-player radar is
  bottom-right (0.51, 1.0, −0.31). That is the code, not the bottom-left the task assumed.
- **Proposed radar fix (2A):** a cave at 0x000F0600 hooked at 0x001AFF48, with P2's depth via f23 at 0x001AFFA4. In
  mode 2 it computes P1/P2 = (xs ∓ d·W, 2d, zs + d·Wz) from the game's own S and A. Under perspective this halves the
  radar, map, blips and widget and puts them bottom-right in each quarter. It replaces the current patch A and keeps
  patch B. All words were verified against the ELF and field-checked.
- **Optional 2B** (2 words) halves view-tagged sprites such as the 1P/2P markers.
- **Not solved:** rage panel size, and centred shared text, which is likely split across the quarter corner.
- **4 players** need 2 new radar objects; the formula extends to the bottom row.
- **Also noticed:** 0x00120B8C may need the same `sltiu 3→2` change as 0x00123300.
- **Confidence:** high on the mechanism; medium that depth halves size (perspective). The runtime test in 2A tells
  which way it is.

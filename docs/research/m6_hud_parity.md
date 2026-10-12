# M6: HUD parity for players 3-4 - Select ring, status panel, timer arcs, radar zoom, blob decal (2026-10-12, agent hudE)

**Status (coordinator, 2026-10-12 21:40):** merged into mod/ (hud_b1.txt, markers34.txt). Placeholders F-HUD-1..7 are summarized in **F-0229** (cause of the P3 ring: F-0222).

## Plain-English summary
- **Negative results first.**
  - (N1) The earlier explanation of the missing Select status panel was wrong. `docs/research/m6_markers_map.md` 2.4
    said B1's slot guard S1 on `FUN_001B28A0` blocks it. That function only writes a byte table that nothing reads
    (immediate scan of the ELF: no reader). S1 must stay anyway: for slot 2 the write would hit the HUD's checkpoint copy
    (HUD+0x225D2). The real switch is `PlayerHUD+0x411C`; its Select reset runs in a HUD loop that our own guard limits
    to 2 players (section 3).
  - (N2) A game with the new patch does not play out frame-for-frame like the same scripted game with the old patch.
    The game's timers advance with the emulated work per frame, and the hooks add a few instructions per frame even
    when they do nothing (e.g. MARK34 for players 1-2, LOOK9 passing items 9/10 through). Evidence: runs with the same
    patch are identical (the timestamps of the panels shown when players 3/4 joined: 329759 / 334031 ms in both
    baseline runs hE_b13 and hE_b13b, 329727 / 333915 in both fixed runs hE_a13 and hE_a13b). Runs with different
    patches agree up to player 2's join (160370 and 316938 in all four) and then drift: in M13 at poll 9300 the game clock
    is 91133 ms without and 91115 ms with the fix. Player 1 then stood at (73.13, 382.78) without and (73.45, 381.52)
    with the fix. In the 2-player M12 run the clocks also drift, by about 340 ms at poll 10500, although players 1-2 stood
    still and every picture matched. This is not a rule change for players 1-2: their ring, panel, radar and arcs
    behave the same. It does not affect the lockstep, because every PC runs the same pnach. Any pnach change does the
    same (HYPOTHESIS for other patches: not measured). Measurements: VERIFIED. Cause (extra emulated instructions
    shift the game's timer reads): HYPOTHESIS.
  - (N3) The blob decal under characters is too dark to see on the dark M13 floor at the test resolution. The proof
    that it now draws in views 3-4 comes from a diagnostic run that paints it white (TEST ONLY, section 5).
  - (N4) The radar zoom of M14 (0.5 in chapters 2a/3) was not run. The M8 run (0.35) uses the same setter.
- **1. Player 3's Select ring (fixed).** The game keeps an "always show this player's ring" byte for exactly 2
  players (0x00622E10). Player 3 read the byte after the table, which is 1 at runtime. So the game treated him as
  "always marked": his ring showed for about 4 s when he joined, then faded out and could never come back. Select did
  nothing for him. Player 4 reads a 0 there by luck, which is why his ring worked. Now players 3-4 are never "always
  marked", so they get the ring from Select (or low health) like players 1-2.
  Example (M13, run hE_a13b): player 3 presses Select at poll 10400. At poll 10587 the green ring is around his feet
  in views 3 and 4 (`local/m6/hudE/z_a13b_p10587_all.png`). Without the fix (run hE_b13b, poll 10579) there is no ring
  in any view (`local/m6/hudE/z_b13b_t0898_p10579_all.png`).
- **2. Timer arcs around radars 3-4 (fixed).** The orange/blue ring (the squad's 10-second timers, F-0203) was drawn
  only around radars 1-2. All four players are in the same squad (runtime: squad 0x5E6E30 for all four), so the same
  arcs are now drawn around radars 3 and 4 too. They are half size like radars 1-2 (RARC), and only in the 2x2 layout
  with 3+ views. Results: section 4.
- **3. Select status panel of players 3-4 (fixed).** Pressing Select shows your name, health bar, money and items for
  about 2 s. It now works for players 3-4: player 3's "SWAN" panel in view 3 at poll 10557 (run hE_a13b), player 4's
  "AJAX" panel in view 4 at poll 10091. Without the fix nothing appears.
- **4. Radar zoom for radars 3-4 (fixed).** Missions 8 and 14 zoom the radar (`HUDSetRadarZoomScale`: M8 0.35 at every
  start; M14 0.5 in chapters 2a and 3, back to 1 later). The game wrote only radars 1-2. Now radars 3-4 get the same
  value. Results: section 6.
- **5. Dark blob under the player characters (fixed).** When the game draws a player's character in views 1-2, it
  also draws a soft dark spot on the ground under him (`FUN_00174320`, sprite frame 0x28, colour 0x800A0A0A). It did
  this for views 1-2 only, so views 3-4 showed the players without it. Now views 3-4 draw it too, using the per-view
  sprite copies that R7 LOOK9 already makes. Results: section 5.
- **Players 1-2, 2-player and single-player:** P1's ring and panel and P4's ring (the positive controls of
  m6_markers_map.md) look the same before and after. Radars 1-2 and their arcs are unchanged. A 2-player M12 game and
  a single-player M12 game look the same before and after (section 7).
- Everything here: SINGLE-PC, one emulator instance per run (sandboxes 32 and 33), scripted bots, no impairment,
  MTVU off, test-only level jump. No humans. No 4-instance lockstep run.

Build: The Warriors SLUS-21215 v1.03 (`local/disc/SLUS_212.15`, read-only); fork build w4p-m6-3 (not rebuilt,
`emulator/` untouched). Function and structure names are OUR labels (the ELF is stripped). Addresses are static unless
marked dynamic. Patch sources: work copy `local/m6/hudE/mod/` (copy of `mod/` taken at 16:57, incl. the then
uncommitted D24 changes). Changed group files: `m2/hud_b1.txt` (`[warriors-4p 4p hud B1]`) and `m2/markers34.txt`
(`[warriors-4p 4p markers]`). Cave sources: `local/m6/hudE/src/b1_add.s`, `src/mk_add.s`. Generator:
`local/m6/hudE/tools/build_hude.py` (it checks every hook's "was" word against the ELF and round-trips every cave word
through an independent disassembler). Test pnach: `local/m6/hudE/test.pnach`. `python -I tools/note_patches.py check`:
**7366 addresses, 6 problems** (the 6 known `[4p hud A]`/`[4p hud B1]` alternatives). Baseline: `local/m6/hudE/base.pnach`
= `mod/w4p_m1.pnach` as of 16:57 (7214 addresses). Merge check against the committed `mod/` of 18:20 (HEAD 5c9d0b5;
its `hud_b1.txt`, `markers34.txt` and `make_pnach.py` are byte-identical to my base copies): the two changed files
copied into a fresh copy of `mod/` build to `local/m6/hudE/merge/merged.pnach` = **7566 addresses, 6 problems**
(7414 + 152 new addresses; no overlap with the D24/M7 additions). Unified diff: `local/m6/hudE/hude.diff`
(`git apply --check` passes on the working tree).

## Summary table
| # | Item | Cause | Fix | Label | Evidence |
|---|---|---|---|---|---|
| 1 | P3 Select ring missing | 0x00622E10 'always marked' byte array has 2 entries; index 2 reads 1 -> P3 permanently marked, his ring-table entry (0x006C72D8) frozen (t_first 0x10EE9, t_mark 0x110C4), ring alpha 0 after 4.5 s | MARK34: index >= 2 never 'always marked' | **VERIFIED** (cause: ring_p3a, hE_b13, hE_b13b; fix: hE_a13, hE_a13b) | section 2 |
| 2 | No timer arcs around radars 3-4 | only P1/P2 widgets (HUD+0x177D0/+0x18280) exist and draw at radars 1-2 | ARC34: after P2's arcs, draw the same widgets again at radar 3/4's position (positions and smoothing restored) | **VERIFIED** (hE_b12/hE_a12, arcs forced by a test write) | section 4 |
| 3 | No Select status panel for P3/P4 | the Select reset `PlayerHUD[i]+0x411C = 0` is in HudUpdate loop 2, clamped to 2 players by MIN2 (hud34) | SEL34: same pad test + reset for slots 2-3 in UPD34 | **VERIFIED** (hE_a13b: +0x411C of P3/P4 renewed by Select; SWAN/AJAX panels shown) | section 3 |
| 4 | Radar zoom not on radars 3-4 | setter `FUN_001B40E0` writes radar 1/2 +0x2920 only | ZOOM34: also radar 3/4 +0x2920 | **VERIFIED** (M8: hE_b8d 1.0 vs hE_a8d 0.35 on radars 3-4) | section 6 |
| 5 | Blob decal only in views 1-2 | `FUN_00174320` tests view < 2 and uses sprite item view+9 | DECAL34: view < 4, lookup through LOOK9 | **VERIFIED** (diagnostic white decal: hE_b8d views 1-2 only, hE_a8d all four views) | section 5 |

## 1. Patch parts
| Part | Group (file) | Game words patched (was -> new) | Cave / RAM | What it does |
|---|---|---|---|---|
| MARK34 | 4p markers (`markers34.txt`) | 0x0024BA20 3C080062 `lui t0,0x62` -> `j 0x000E8160`; 0x0024BA24 25082E10 -> nop | 0x000E8160-0x000E818B (11 words) | player index < 2: the original byte test; index >= 2: not marked. Both exits redo the original delay-slot load `lw v1,0x58(sp)` and jump to the original targets (0x0024BA38 marked, 0x0024BA64 not marked) |
| DECAL34 | 4p markers | 0x0017472C 2EC20002 `sltiu v0,s6,2` -> 2EC20004 (`< 4`); 0x00174760 0C0616AC `jal 0x00185AB0` -> 0C03A200 `jal LOOK9` | none (LOOK9 0x000E8800 of R7) | views 2-3 also draw the player blob decal, with LOOK9's per-view copies of sprite item 9 (views 0-1 unchanged: LOOK9 passes item 9/10 to the original lookup) |
| SEL34 | 4p hud B1 (`hud_b1.txt`) | B1 cave words 0x000E0370 / 0x000E0390 `jal PHUD_UPDATE` (0C0380EC) -> `jal SEL34` (0C038340) | 0x000E0D00-0x000E0DA3 | for slot 2/3: human = GameMgr+0x228+4*slot, pad record `FUN_0021D3E8`, if it has a pad and `FUN_00144BF0(0x005DD810 + pad*0x50, 0x100)` (Select edge, as 0x001B14C0-0x001B14F8) -> `T_A[slot] + 0x411C = 0`; then PHUD_UPDATE(slot) as before |
| ARC34 | 4p hud B1 | 0x001B1A30 0C06AAEA `jal 0x001AABA8` (P2 widget arcs, split view) -> 0C038370 `jal ARC34` | 0x000E0DC0-0x000E0E53, ARCR 0x000E0E80-0x000E0F53 | original call; then in layout mode 2 with >= 3 views: radar 3 (count >= 3) with widget HUD+0x177D0, radar 4 (count >= 4) with widget HUD+0x18280, each only if the disc is drawn (radar +0/+4/+8 set, +0xC clear, the test of `FUN_001C60B0`). ARCR saves the widget's 4 arc positions and 4 smoothing words, writes the radar vector +0x2930 into the positions, calls `FUN_001AABA8`, restores |
| ZOOM34 | 4p hud B1 | 0x001B40EC 03E00008 `jr ra` -> 080383E0 `j ZOOM34` (delay slot = radar 1 store, kept) | 0x000E0F80-0x000E0F8F | f12 also to radar 3 +0x2920 (0x000ABE20) and radar 4 +0x2920 (0x000AE760) |

- **Free RAM (VERIFIED):** no pnach line (base 7214 addresses) and no cave instruction with base 0x000E references
  0x000E0CB0-0x000E0FFF or 0x000E8150-0x000E82BF (scan of `base.pnach`). At runtime both ranges were all zero in the
  baseline runs (probe `nonzero_*`, hE_b13 poll 9500, hE_b13b polls 9300-10900). With the fix only the cave words are
  non-zero (131 + 10 words; the zero words are nops). Not used by the reserved camera ranges
  (0x000E9800-0x000EBFFF, 0x000E5D10-0x000E6FFF).
- **Groups:** all parts need `4p hud B1` (radars 3-4, T_A, UPD34) or `4p markers` (LOOK9), which are always used
  together with `hud`, `4p`, `4p hud B2` in the 4-player list (STATE "Full 4-player group list"). Order in the pnach:
  the hudE blocks sit at the end of each group file between `// ---- hudE begin` and `// ---- hudE end`.

## 2. Player 3's Select ring (item 1)
### 2.1 Cause (VERIFIED: static code + runtime ring_p3a / hE_b13 / hE_b13b)
- The marker loop `FUN_0024B780` (our label) runs per player: the four skip tests (0x0024B90C-0x0024B944), then the
  'marked' decision. A player is marked if he has a pad and Select has an edge (`FUN_00144BF0(pad, 0x100)`,
  0x0024BA10), **or if the byte 0x00622E10[player index] != 0** (0x0024BA20-0x0024BA30). Marked: the stack entry's
  t_mark = now (0x0024BA60), `FUN_001B28A0(HUD, i, 0)`.
- `FUN_0024B190` (our label RingTableLookup) copies the entry from the previous frame's table 0x006C72D8. Once the
  entry is older than 500 ms it also copies the **old** t_mark (entry+8) over the new one. The alpha is computed from
  now - t_mark: 4.0-4.5 s after t_mark the ring fades out, then alpha 0. A player who is marked in every frame never
  leaves the table, so t_first and t_mark stay frozen and his ring never returns. Select only sets t_mark, which the
  lookup overwrites.
- 0x00622E10 has 2 entries (players 1-2). The only reference in the ELF is this read (immediate scan: 0x0024BA24; no
  pointer to 0x00622Dxx-0x00622Exx in the ELF image). Runtime bytes [0..3] = 0, 0, **1**, 0 in every sample. So player 3
  is always marked and player 4 is not.
- Runtime (ring_p3a, the coordinator's run, and hE_b13b): all four skip tests 0 for every player, pads fine (P3 pad 2,
  P4 pad 1). Table entry 0 = P3's handle 0x3023B with t_first 0x10EE9 and t_mark 0x110C4 in every sample from poll 9300
  to 11700, while the clock went from 91133 to 144803 ms. P4's entry appears only while he holds Select (poll 10080:
  0x40267, 0x1B932, 0x1BB05). Identical values in three baseline runs (deterministic).
- What writes 0x00622E10[0..1] was not found (no immediate reference). HYPOTHESIS: unused or written through a pointer.
  At runtime they are 0 in M13.

### 2.2 Fix MARK34 and result (VERIFIED, hE_a13 / hE_a13b)
- Index >= 2 is never 'always marked'; index 0-1 run the original test (same byte, same branches; t0/v0 differ but are
  dead at both targets: 0x0024BA38 reloads v0 and t0, 0x0024BA64 calls `FUN_00228340`).
- hE_a13b ring table: empty at 9300 (no stuck entry); P1 at 9620 (0x162), P4 at 10080 (0x40244), **P3 at 10500
  (0x3023B, t_first 0x1F3E1)** and again at 10620 (new entry 0x208D6 after the first ring ended), empty at 10900.
  Screenshots: P3's ring in views 3 and 4 at poll 10587 (`local/m2/hE_a13b/t0890_p10587.png`, zoom
  `local/m6/hudE/z_a13b_p10587_all.png`). Baseline at the same time: no ring, no panel
  (`local/m2/hE_b13b/t0898_p10579.png`, zoom `z_b13b_t0898_p10579_all.png`).
- Positive controls unchanged: P1's ring in views 1, 2 and 4 plus his "REMBRANDT" panel in view 1 (after: poll 9737
  `z_a13b_t0790_p9737_all.png`; before: poll 9717 `z_b13b_t0798_p9717_all.png`); P4's ring in all views (after: poll
  10091 `z_a13b_t0832_p10091_all.png`; before: poll 10230 `z_b13b_t0857_p10230_all.png`).

## 3. Select status panel of players 3-4 (item 3)
### 3.1 Cause (VERIFIED static; runtime hE_b13b)
- The panel is the PlayerHUD's name/health/money/items block. `PlayerHUD::Draw` `FUN_00213290` (0x00213328-0x00213384):
  if +0x411C == 0 it stores the timer (`*(0x0050B8B8)` vtable +0x34, ms) there and shows the panel. Afterwards it shows
  it for [0x00510070] = 2000 ms and fades it over [0x00510074] = 1000 ms. +0x4104 != 0 keeps it shown.
- Select resets +0x411C in **HudUpdate loop 2** (0x001B1498-0x001B15F0, store at 0x001B14F8), for player index i with
  the PlayerHUD of index i. That loop also indexes 2-entry HUD arrays (target objects HUD+0x6B40), so the MIN2 guard of
  hud34 (0x001B15D4/0x001B15E4) clamps it to 2 players: players 3-4 never get the reset.
- `FUN_001B28A0(HUD, i, 0)` from the marker loop writes byte HUD+0x225D0+i. **No reader** of 0x225D0-0x225D3 exists
  (immediate scan: only the init at 0x001ADC68 and the setter 0x001B28A4; the other setter call is `FUN_00284280` with
  value 1). For i = 2 the byte would land in the u16 HUD+0x225D2 (checkpoint copy, written at 0x001AE36C). So S1
  (`slot < 2`) is correct and stays. It is not what hid the panel (corrects m6_markers_map.md 2.4).
- hE_b13b: P3/P4 +0x411C stayed 329759 / 334031 (their join) through all their Select presses; P1's moved
  160370 -> 360357 -> 365797 with his presses.

### 3.2 Fix SEL34 and result (VERIFIED, hE_a13b)
- For slots 2/3, in UPD34 before each PlayerHUD 2/3 update: the same pad test as loop 2, then `T_A[slot] + 0x411C = 0`.
  It runs only while the player count is >= 3 / >= 4 (UPD34's own test).
- hE_a13b: P4 +0x411C 333915 -> 375573 (poll 10080, presses 9950-10190) -> 381013; P3 329727 -> 390889 (10500) ->
  393624 (10620) -> 396329 (10900; last press 10640). Players 1-2 unchanged in behaviour (P1 160370 -> 360226 ->
  365697 with his presses).
- Screenshots: player 3's blue "SWAN" panel (name, health bar, money, spray count) top-left of view 3 at polls
  10557-10616 (`local/m6/hudE/z_a13b_t0886_p10557_q3.png`, `z_a13b_p10587_all.png`); player 4's green "AJAX" panel
  top-right of view 4 at poll 10091 (`z_a13b_t0832_p10091_all.png`). Player 4's panel is right-aligned because B1
  gives PlayerHUD 3 the right-hand (player 2) layout column. Baseline: no panel in views 3-4.

## 4. Timer arcs around radars 3-4 (item 2)
### 4.1 Static (VERIFIED)
- `FUN_001AABA8` (RadarArcsDraw) draws up to 4 arc objects of a widget, at +0x10, +0x120, +0x230, +0x340. This corrects
  F-0203's "+0x0/+0x220": `addiu a0,s0,16` at 0x001AABD0, radii written at +0x230/+0x234 and +0x340/+0x344. Fields per
  arc: +0 inner radius, +4 outer radius, +0x10 position, +0x20 colour, +0x28 fraction (from the squad timers,
  `FUN_001AA9B0`), **+0x2C smoothed fraction (moved 5 % towards +0x28 on every `FUN_001A5E38` call)**, +0x30 enabled.
- `FUN_001A5E38` -> `FUN_0017B8A8` builds the fan on the stack and sends it at once, so drawing the same widget twice
  with different positions gives two separate rings.
- Positions: HudUpdate writes the radar's vector (HUD+0x3F00 = radar 1 +0x2930, HUD+0x6840 = radar 2 +0x2930) into the
  widget with `FUN_001AA630` (+0x20/+0x130/+0x240/+0x350; the hud patch at 0x001AA648 keeps the caller's height).
  Radars 3-4 have the same vector at +0x2930 (B1 RADAR_UPDATE): (-0.215, 2.0, -0.81) and (1.235, 2.0, -0.81) at
  runtime (hE_a13b).
- Both widgets read their player's squad (widget +0xA90 = 0 / 1, `FUN_0021D408(human)+0x20C`); all four players have
  squad 0x5E6E30 (hE_b13b/hE_a13b, all polls). So radars 3-4 show the same timers as radars 1-2.
- ARC34 restores the 4 smoothing words after the extra draws, so radars 1-2's arcs animate exactly as before.

### 4.2 Runtime (VERIFIED, M12, runs hE_b12 / hE_a12)
- Setup as m6_markers_map.md 10.4. The arcs are forced with the TEST-ONLY PINE write `hude_probe:arcs_on` (squad
  0x5E6E30 timers +0x5E8/+0x5F0 = clock + 9.5 s) at polls 9600, 10400 and 11200. 4 players, 4 views, layout 2.
- Before: arcs around radars 1-2 only. After: the same orange/blue arcs, at the same half size, around all four radars.
  Images: `local/m6/hudE/z_12_before_after_all.png` (before poll 9725 left, after poll 9766 right),
  `z_12_before_after_all_p113.png` (third forcing: before 11338, after 11299). Radar zooms `z_12_r1_ba.png` ..
  `z_12_r4_ba.png`: radar 3 has none before and the arcs after; radar 1 looks the same in both.
- Players 1-2 unchanged (probe after every forcing): the widgets' 4 arc positions are the radar 1/2 vectors in every
  sample of both runs, i.e. ARC34's restore works. The smoothing lag (smoothed - target) is the same size before and
  after: 0.065/0.063/0.067 before, 0.067/0.063/0.063 after (polls 9700/10500/11300). A second smoothing step per
  frame would have roughly halved it.

## 5. Blob decal under player characters (item 5)
- `FUN_00174320` (our label HumanDraw; called per view by `FUN_0040E8D8` with s6 = view, and once with 0xFF) draws a
  human model. For a human whose draw object has +0x2B4 set (set every frame for each player by the marker loop at
  0x0024B958), and only when **view < 2** (0x0017472C), it also draws a ground decal from sprite item view+9
  (0x00174760), frame 0x28, colour 0x800A0A0A (0x0017492C-0x00174944), i.e. a soft dark spot under the player.
- Views 2-3 (players 3-4) never drew it. Items 11/12 would be the wrong sprites (m6_markers_map.md 2.4), so DECAL34 uses
  LOOK9's copies of item 9 for views 2/3 (LOOK9 makes them on first use; in hE_a13 both copies existed by poll 9500,
  in the baseline only the view-2 copy).
- The marker loop and LOOK9 already create sprites inside the render pass (`FUN_003A31A8` calls `FUN_0024B780`), so the
  decal path creating the copies there is the same phase.
- Runtime (VERIFIED with a TEST-ONLY diagnostic, M8, runs hE_b8d / hE_a8d): the decal is dark grey at half alpha and
  cannot be seen on the dark M13 floor in the screenshots (N3). The diagnostic group `[warriors-4p test decal bright]`
  (0x0017492C 2403000A -> 240300FF: colour 255 instead of 10, alpha unchanged; added only to
  `local/m6/hudE/base_diag.pnach` / `test_diag.pnach`, never to the mod) paints it white. Before (poll 9993): white
  spots under the characters in views 1-2 only; views 3-4 none. After (poll 10014): white spots in all four views, e.g.
  under the standing character in view 3 and under the downed player in view 4. Images
  `local/m6/hudE/z_b8d_p9993_all.png`, `z_a8d_p10014_all.png`.

## 6. Radar zoom for radars 3-4 (item 4)
- `HUDSetRadarZoomScale` (binding 0x00370728) -> `FUN_001B40E0`: `swc1 f12` to 0x00607070 (radar 2 +0x2920) and
  0x00604730 (radar 1 +0x2920). `FUN_001C60B0` multiplies the disc range by +0x2920 (decompile all_01.c:58739).
  `FUN_001C3DE0` (per-level radar init, called for radars 1-2 at HUD level init `FUN_001AD588` and for 3-4 by B_INIT in
  the same function) resets it to 1.0.
- Users (Lua disassembly): M8 main 08780 `main_65` (`HUDSetRadarZoomScale(0.35)` after `RestoreHud()`, every start)
  and its copy 08842; M14 08183 (ch2a: 0.5, then 1 at the door) and 08184 (ch3: 0.5, 1 at the end); 08912 (0.35) and
  10632 (0.5) not mapped to a mission here.
- Runtime (VERIFIED, M8 cp1, runs hE_b8d / hE_a8d; the M8 main script sets 0.35 at the start): radar +0x2920 at poll
  6502 (2 players, before players 3-4 join), 9800 and 10600 (4 players): before 0.35, 0.35, **1.0, 1.0**; after 0.35 on
  all four radars, already at poll 6502 (radars 3-4 are initialised at the HUD level init, before the Lua main runs).
  The radar picture shows it: radar 3 before = small map at scale 1.0, after = the same large map shapes as radar 1
  (`local/m6/hudE/z_8_r1_ba.png` .. `z_8_r4_ba.png`, before left, after right).
- Not run: M14 (0.5 / 1 in chapters 2a and 3). It calls the same setter, so the same mirror applies (HYPOTHESIS).

## 7. Players 1-2, 2-player and single-player
- By construction: MARK34 changes nothing for index 0-1. DECAL34 only adds views 2-3. SEL34 runs only from UPD34
  (count >= 3). ARC34 draws extra arcs only in layout 2 with >= 3 views. ZOOM34 only writes radars 3-4's RAM (no
  visible effect without them).
- 2-player (VERIFIED, M12, runs hE_b12_2p / hE_a12_2p, players 3-4 never join, arcs forced at 9600 and 10400): 2 views,
  arcs around radars 1-2 in both, the same scene and the same player positions ((-23.409, 22.006) and (-23.614, 21.31) in
  every sample of both runs). Widget positions are the radar 1/2 vectors and radars 3-4 stay hidden (flags 1,1,0,1).
  Image: `local/m6/hudE/z_12_2p_before_after.png` (before poll 9759 left, after poll 9748 right). The clocks drift
  (N2).
- Single player (VERIFIED, M12, runs hE_b12_1p / hE_a12_1p, W4P 1 player, boot
  `local/m6/hudE/scripts/boot_1p_m12.txt` = `local/m7/scripts/reg_1p.txt` up to poll 3850, arcs forced at 9600/10400):
  1 view, layout 0, full-size radar with full-size arcs and the same hint text in both; P1 at (-23.409, 22.006) in every
  sample; radar 1 vector (0.51, 1.0, -0.31); radars 3-4 hidden. The clocks agree within the poll jitter (poll 10402:
  113587 ms before, poll 10400: 113487 ms after, about 33 ms per poll). Image `local/m6/hudE/z_12_1p_before_after.png`
  (before poll 9765 left, after poll 9745 right).
- FAILED TEST METHOD (not a game result): two first single-player attempts (`--players 1` with the 2-player boot
  script, then 2 players with slot 2 idle) stopped in the profile name screen, because the 2-player boot script needs
  player 2's Start at poll 2300; they were stopped and replaced by the runs above.

## 8. Tests (SINGLE-PC, one instance each, sandboxes 32/33, scripted bots, no impairment, MTVU off)
Common: `tests/m2/nav_probe.py` with the 13 standard groups (own view; hud; 4p; test call; 4p hud B1; 4p hud B2; 4p
spawn; 4p spawn leave; 4p inventory; 4p fx; 4p markers; session; missions), `--ini EmuCore/Speedhacks/vuThread=false`,
probes `tests/m6/hude_probe.py` (new). "before" = `local/m6/hudE/base.pnach`, "after" = `local/m6/hudE/test.pnach`.
TLB misses counted in copies of `local/pcsx2/inst<N>/PCSX2/logs/emulog.txt` saved as `local/m6/hudE/emulog_<tag>.txt`.
Probe results: `local/m2/<tag>/probes.json`, copied to `evidence/M6/<tag>_probes.json`. Every run ended by its time
limit, with no crash.

| Run | Inst | Pnach | Setup | Purpose | Result | TLB |
|---|---|---|---|---|---|---|
| ring_p3a | 31 | mod/w4p_m1.pnach | coordinator's run, M13, `tests/m6/ring_probe.py` | cause of item 1 | P3 'always marked', frozen table entry (2.1) | not checked by me |
| hE_b13 | 32 | before | M13 cp1 (CallAt `3999:0041ABC0:1,4009:00160D78:0x01FD9F9C`), boot `local/m6/hud34/boot_sel.txt`, slot 2 `mk_p3s.txt`, slot 3 `mk_p4s.txt`, 1x, 1050 s | baseline | ended at poll 10013 (machine load; Select windows not reached); poll 9500: stuck P3 entry, RAM ranges zero | 0 |
| hE_a13 | 33 | after | same | first after run | ended at poll 10051; poll 9500: no stuck entry, LOOK9 copies 0x1C/0x22, only cave words non-zero | 0 |
| hE_b13b | 32 | before | M13 cp1, scripts `local/m6/hudE/scripts/boot_sel_e.txt` (P1 Select 9500-9740), `s2_p4sel.txt` (P4 Select 9950-10190), `s3_p3sel.txt` (P3 Select 10400-10640), 2x internal, 1700 s | items 1/3 before | P1 ring + panel; P4 ring, no panel; P3 nothing; P3/P4 +0x411C never renewed | 0 |
| hE_a13b | 33 | after | same | items 1/3/5 after | P1 ring + panel; P4 ring + AJAX panel; P3 ring + SWAN panel | 0 |
| hE_b12 | 32 | before | M12 cp1 (CallAt `4000:0041ABC0:1,4010:00160D78:0x01FD9F18`), boot `boot_to_m1_2p.txt`, `p2_join.txt`, `cal_p3.txt`, `cal_p4.txt`, 2x, `arcs_on` at 9600/10400/11200, 1250 s | item 2 before | arcs around radars 1-2 only | 0 |
| hE_a12 | 33 | after | same | item 2 after | arcs around all four radars; P1/P2 widget positions and smoothing as before | 0 |
| hE_b8d | 32 | before + `[warriors-4p test decal bright]` (`base_diag.pnach`) | M8 cp1 (CallAt `3999:0041ABC0:1,4009:00160D78:0x01FD9D08`), `boot_to_m1_2p.txt`, `p2_join.txt`, `cal_p3.txt`, `cal_p4.txt`, `x6fix_probe:join34` at 9000/9400 (4 players already), 2x, 1100 s | items 4/5 before | zoom 0.35/0.35/1.0/1.0; white decal views 1-2 only | 0 |
| hE_a8d | 33 | after + diagnostic (`test_diag.pnach`) | same | items 4/5 after | zoom 0.35 on all four radars; white decal in all views | 0 |
| hE_b12_2p | 32 | before | M12 as hE_b12 but slots 3-4 `empty.txt` (2 players), `arcs_on` 9600/10400, 950 s | 2-player regression before | 2 views, arcs on radars 1-2 | 0 |
| hE_a12_2p | 33 | after | same | 2-player regression after | same picture and positions as before | 0 |
| hE_b12_1p | 32 | before | M12, W4P 1 player, boot `boot_1p_m12.txt`, `arcs_on` 9600/10400, 900 s | single-player regression before | 1 view, full-size radar and arcs | 0 |
| hE_a12_1p | 33 | after | same | single-player regression after | identical picture, position and radar values | 0 |

## 9. Not done / open
- No 4-instance lockstep run with these parts (only instances 32-33 were available to this agent). Determinism per patch
  is shown by repeated single-instance runs (N2), not by a hash comparison across PCs.
- M14's radar zoom (0.5) not run (N4). The arcs were forced by a test write; the real game event that starts the squad
  timers (F-0203 open point) is still not traced.
- The blob decal was proven only with the white diagnostic colour; with the real dark colour it is barely visible in
  the tested scenes, as it is in views 1-2.
- What writes 0x00622E10[0..1] ('always marked' for players 1-2) is unknown (no immediate reference). If the game ever
  sets it for player 1 or 2, players 3-4 do not get the same permanent ring (they are never 'always marked').
- After a player leaves (D7 compaction) B1 assumes slot = player index = view (m2_hud_full.md 5); SEL34 and ARC34 use
  the same assumption (not tested with a leave).
- Widescreen, 60 fps and the hub were not tested with these parts.

## 10. Draft findings (placeholder IDs; the coordinator assigns F-numbers)
- **F-HUD-1 (VERIFIED, supersedes the FAILED TEST part of F-0194):** player 3's missing Select ring is caused by the
  2-entry 'always marked' byte array 0x00622E10 read with player index 2 in `FUN_0024B780` (0x0024BA20-0x0024BA30): the
  foreign byte reads 1, player 3 is marked every frame, `FUN_0024B190` keeps his ring-table entry (0x006C72D8) with
  frozen t_first 0x10EE9 / t_mark 0x110C4, the ring fades out 4-4.5 s after he joins and never returns (ring_p3a,
  hE_b13, hE_b13b). Fix MARK34 (`[warriors-4p 4p markers]`, 0x0024BA20/24 -> cave 0x000E8160): index >= 2 never
  'always marked'. hE_a13b: P3 ring in views 3-4 after Select (poll 10587), table cleared, P1/P4 rings unchanged. 0 TLB.
- **F-HUD-2 (VERIFIED, corrects m6_markers_map.md 2.4):** the Select status panel is `PlayerHUD+0x411C` (show timer of
  `FUN_00213290`: 2000 ms + 1000 ms fade), reset by Select in HudUpdate loop 2 (store 0x001B14F8), which hud34's MIN2
  limits to 2 players. B1's S1 guard on `FUN_001B28A0` is not the cause: that byte table HUD+0x225D0 has no reader, and
  S1 must stay (slot 2 would overwrite the checkpoint copy HUD+0x225D2). Fix SEL34 (`[warriors-4p 4p hud B1]`, UPD34's
  two PHUD_UPDATE calls -> cave 0x000E0D00): the same pad edge test and reset for slots 2-3. hE_a13b: P3 "SWAN" and P4
  "AJAX" panels on Select, P3/P4 +0x411C renewed with each press; before (hE_b13b) never. 0 TLB.
- **F-HUD-3 (VERIFIED, extends F-0203):** the squad-timer arcs are now drawn around radars 3-4 too (ARC34, hook 0x001B1A30
  -> cave 0x000E0DC0/0x000E0E80): after P2's arcs, in layout 2 with >= 3 views, P1's widget is drawn again at radar 3's
  vector and P2's at radar 4's, positions and smoothing restored. All four players share squad 0x5E6E30. hE_a12 (M12,
  arcs forced by a test write): arcs on all four radars; radars 1-2 unchanged (positions = radar vectors, same smoothing
  lag). Also: the arc objects are at widget +0x10/+0x120/+0x230/+0x340 (F-0203 said +0x0/+0x220). 0 TLB.
- **F-HUD-4 (VERIFIED):** `HUDSetRadarZoomScale` (M8 0.35, M14 0.5) now also sets radars 3-4 (ZOOM34, 0x001B40EC ->
  cave 0x000E0F80). M8 hE_b8d: radars 3-4 1.0 while 1-2 are 0.35; hE_a8d: 0.35 on all four from the level start. M14 not
  run. 0 TLB.
- **F-HUD-5 (VERIFIED with a TEST-ONLY diagnostic colour):** `FUN_00174320` draws a ground decal (frame 0x28 of the
  view+9 sprite, colour 0x800A0A0A) under player characters only in views 0-1. DECAL34 (0x0017472C limit 4, 0x00174760
  lookup through LOOK9) draws it in views 2-3 too. With the decal painted white: before only views 1-2, after all four
  (hE_b8d, hE_a8d, M8). 0 TLB.
- **F-HUD-6 (VERIFIED measurement, cause HYPOTHESIS):** a scripted game with a different pnach drifts in time from the same
  game with the old pnach. Runs with the same patch are identical (panel timestamps of players 3-4 at their join equal in
  two runs each). With the new patch the timeline is equal up to player 2's join, then drifts: M13 game clock 91115
  vs 91133 ms at poll 9300 and slightly different player positions; also in a 2-player M12 run (about 340 ms by poll
  10500, same picture). Rules and visuals for players 1-2 are unchanged and every PC runs the same pnach, so the
  lockstep is not affected. Likely cause: extra emulated instructions shift the game's timer reads.
- **F-HUD-7 (VERIFIED):** 2-player regression (M12, hE_b12_2p/hE_a12_2p): same picture, same arcs on radars 1-2, same
  positions, 0 TLB. Single player (M12, hE_b12_1p/hE_a12_1p): identical picture, radar and arcs, no clock drift, 0 TLB.

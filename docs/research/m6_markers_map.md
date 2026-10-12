# M6: overhead markers, radar and map with 4 players (2026-10-12)

## Plain-English summary
- **Update 2026-10-12 (section 9): players 3 and 4 now show as "3P" (red) and "4P" (green) on every other player's
  radar**, in the style of the game's "1P"/"2P". The labels are built at runtime inside the game's own radar icon
  picture from the game's "2P" art and HUD font; nothing from the game is shipped. The "red/green 2P" text below is
  the earlier state (superseded where marked).
- **The yellow "2P 2P 2P" were not overhead markers. They were the radar's player icons, drawn in the wrong place.**
  Every radar draws small icons for the other people around you: "1P"/"2P" for the players, a red "W" for a Warriors
  companion, an arrow or letter for an objective. Our per-view HUD patch (`[warriors-4p 4p hud B2]`) copies every
  "shared" HUD item into all four quarters at half size. The radar icons are shared items, but they are positioned for
  the radar disc in one corner of the full 2x2 picture, so the copies landed in the middle of the scene, at the same
  spot in every quarter: far down a corridor, or on somebody's chest. Example: in Mission 13 every quarter showed a
  "2P" and a red "W" about 40 % across and 35 % down, whatever that player's camera looked at.
- **Fixed** (new group `[warriors-4p 4p markers]`, `mod/m2/markers34.txt`): radar icons are now drawn with the same
  full-screen HUD camera as the radar disc, so they sit on the disc of their own radar and only there. Players 3 and 4
  now also get icons on their radars (before, radars 3-4 showed only the map, no icons at all), and players 3 and 4 have
  their own colours on every radar: player 2 = yellow "2P", **player 3 = red "2P", player 4 = green "2P"** (the game has
  no "3P"/"4P" art, see below; superseded by section 9: now red "3P" and green "4P"). Example: player 1's radar shows a yellow, a red and a green "2P" around his own arrow.
- **How the original 2-player split screen does it** (the rule we copied): in split screen there is **no text above
  anyone's head**. You find your partner with the radar: on player 1's radar player 2 is a "2P" label, on player 2's
  radar player 1 is a "1P" label, your own blip is an arrow. Labels above the heads ("1P"/"2P", effects `dyn_p_one`,
  `dyn_p_two`) appear only when the two views are merged into one. Pressing Select shows your health ring on the ground
  around your feet (visible in every view) and your status panel.
- **Map: there is no full map inside a mission.** The pause menu has Objectives, Stats, Options, Controls, Restart,
  Resume and Quit, no map; no button opens one. The game's "map" is the level-select map of the hideout hub (after the
  story, "press START to access map", unlockable "QuickMap"); it shows missions, not player positions. So during a
  mission every player's way to see the others is his own radar, which now works for all four players. In an online
  session the pause menu belongs to the host (D17); nobody can open a map in a mission anyway.
- **Players 3 and 4 spawn on the same spot**: right after joining they stand exactly at the same position
  (74.87, 381.28, 4.80) in Mission 13, which is why the two bottom quarters looked identical. Report only, not changed.
- **Also fixed:** pressing Select shows a coloured health ring around your feet. Players 3-4 asked for the wrong
  picture for it (sprite items 11/12 instead of the per-view items 9/10); they now get their own copies (R7). Player 4's
  ring appears (screenshot `local/m2/mk_e/t0409_p10925.png`, bottom right); player 3's still does not.
- **Open:** "3P"/"4P" labels do not exist in the game (colour instead; superseded by section 9: built at runtime); the Select status panel is still missing for
  players 3-4; the Select health ring now shows for player 4 but still not for player 3 (FAILED TEST, cause not
  found); no 4-instance lockstep run yet; all tests are SINGLE-PC, one emulator instance, scripted bots, Mission 13 only.

Build: The Warriors SLUS-21215 v1.03 (`local/disc/SLUS_212.15`, read-only); fork build w4p-m6-1 (not rebuilt,
`emulator/` untouched). Function and structure names are OUR labels (the ELF is stripped); addresses static unless
marked dynamic. **Tests: SINGLE-PC, one instance (sandbox 15), scripted bots, no impairment, MTVU off**, Mission 13
(level9 cp1) via the standard level jump, players 3-4 join with Start (`tests/m2/nav/mk_p3.txt`, `mk_p4.txt`: like
`cal_p3/4` up to poll 8800, then a short walk so the four players stand apart), screenshots at 2x internal resolution,
scale 1.0; runs mk_c-mk_g add Select presses (`local/m6/hud34/boot_sel.txt`, `tests/m2/nav/mk_p3s.txt`, `mk_p4s.txt`).
Careful: the slot-2 script (`mk_p3*`, pad 1) drives **player 4** and the slot-3 script (`mk_p4*`, pad 2) drives **player 3**
(pad owners read at runtime, section 2.4). `mod/w4p_m1.pnach` was NOT regenerated (a 4-instance batch uses it); test
pnachs in `local/m6/hud34/` (final: `final2.pnach`).

## Summary table
| Item | Finding / change | Label | Evidence |
|---|---|---|---|
| Floating "2P"/"W"/"A" labels | radar icons drawn in every quarter by B2's SHARED (they use shared sprite items, view 0xFF) instead of on their radar disc | **VERIFIED** | mk_b: radar tables (probe `radars@9400`), all player icons in sprite item 2; tagging item 2 removed every floating "2P"/"A" (`local/m2/mk_b/t0363_p9566.png` before, `t0376_p9932.png` after) |
| Fix R1-R3 | player icons get an own sprite item (copy of item 2, view 0xFE), every radar's dot sprites view 0xFE, 0xFE drawn like 0xFF | **VERIFIED** | mk_c `local/m2/mk_c/t0363_p9564.png`: icons on the radar discs, none in the scene; probe `radar_tex`: item 0x16 view 254, 28 dot sprites view 254 |
| Radars 3-4 | had no icons at all (0 blips) | **VERIFIED** (before) | mk_b probe: r3/r4 0 blips |
| Fix R5 FAN | radar-2 calls repeated for radars 3-4 | **VERIFIED** | mk_d probe: r3/r4 6 blips each; `local/m2/mk_d/t0376_p9925.png`, zooms `local/m6/hud34/z_d_r1.png` .. `z_d_r4.png` |
| Players 3-4 icon | was the same "2P" as player 2 on radar 1 and player 2's own arrow on radar 2 | **VERIFIED** (before) | mk_c zooms `local/m6/hud34/z_c1.png`, `z_c2.png` |
| Fix R4 PICON | P3 red, P4 green; other players shown with the game's own "other player" frames on every radar, own player keeps his arrow | **VERIFIED** (final, mk_g); first version FAILED TEST (wrong flag field, mk_d) | mk_g probe frames/colours; `local/m2/mk_g/t0364_p9578.png`, zooms `local/m6/hud34/z_g_r1.png` .. `z_g_r4.png` |
| "3P"/"4P" art | not referenced by any code; no label effect for it in the data | **VERIFIED** (code, effect names) / HYPOTHESIS (unused atlas frames not surveyed) | section 3 |
| "3P"/"4P" art (survey) | none of the 0x173 part_page0 frames is a 3P/4P label (decoded atlas); the picture is re-uploaded from EE RAM every frame | **VERIFIED** (supersedes the HYPOTHESIS above) | 9.1, p34a/p34b |
| Fix L1-L4 | "3P"/"4P" (and "3"/"4") built at runtime in free texels from the game's 2P art and font; virtual frames 0xFFF3-0xFFF6 | **VERIFIED** (l34a, l34c, l34e) | 9.2-9.4, `local/m6/p34/z_l34e_p9915_r1..r4.png` |
| Fix L5 | radar keeps the new labels upright (first version turned them with the heading: FAILED TEST l34b) | **VERIFIED** (l34c, l34e) | 9.3, 9.4 |
| Merged-view labels (`dyn_p_one/two`) | only with 1 view; players 3-4 would get "2P" and it is never cleared | **VERIFIED** (static); R6 fix **untested at runtime** | section 2.3 |
| Select ring of players 3-4 | not drawn (they ask for sprite items 11/12, which are other sprites) | **VERIFIED** (P1 ring shown, players 3-4 none) | mk_c `t0388_p10292.png`; mk_d `t0412_p11016.png`, `t0424_p11380.png` |
| Fix R7 LOOK9 | own per-view copies of item 9 for views 2-3 | **VERIFIED** for player 4 (index 3); **FAILED TEST** for player 3 (index 2): still no ring | mk_e |
| Full map | none inside missions; the hub's map is a level select | **VERIFIED** (menu code, scripts) / HYPOTHESIS (hub map content) | section 5 |
| Players 3-4 join position | identical position after joining | **VERIFIED** (dynamic) | mk_b probe `snap@8800` |

## 1. What the yellow labels were (VERIFIED)
- **Runtime (mk_b, poll 9400, PINE).** Radar 1 (HUD+0x15D0 = 0x00601E10) and radar 2 (HUD+0x3F10 = 0x00604750) each
  hold 6 active blips (table at +0x920, 128 entries of 0x40 bytes; +0x951 active, +0x94C type, +0x930 human handle,
  +0x948 widget):
  - players 1-4: type 9, a HUD widget with frame (+0xC8) 0x16A for player 1 and 0x16B for players 2, 3 and 4;
  - the AI Warrior: type 7, a "hud_radar_dot" effect (string 0x005551E0) with icon 0x16D = the red "W";
  - an objective: type 10 (icon 0x1B).
  - **Every player widget uses sprite item 2** (widget +0xC4 = 2; item 2 = "part_page0", view 0xFF, made at boot by
    `FUN_00184918` at 0x00184B04-0x00184B2C). The widget positions are in the radar's camera space (widget +0x30 = the
    radar's +0x2930 vector, e.g. (-0.215, 2.0, 0.24) for radar 1).
- **Why every quarter.** View-0xFF items go through B2's SHARED (`m2_hud_full.md` 2.2 and Appendix B), which draws each
  of them once per view through that view's HUD camera with the undivided window (patch 2B). The radar disc itself is
  drawn directly with the global HUD camera (`FUN_001C60B0`), so disc and icons disagree: the icons of both radars
  appear in all four quarters at the same relative spot, far from the discs. That is the user's "2P 2P 2P" (players 2,
  3 and 4 all used the 2P icon) and the red "W".
- **Experiment.** At poll 9700 the test wrote view 0xFE into item 2 (`marker_probe.tag_widgets_fe`; before R1 a 0xFE
  item is not drawn at all): the yellow "2P"/"A" icons disappeared from all four quarters while the red "W" dots stayed
  (`local/m2/mk_b/t0376_p9932.png`). So the floating labels are exactly these widgets. The "W" dots are separate objects
  with the radar's own sprites (fixed by R3).
- **Not the cause:** the label effects `dyn_p_one`/`dyn_p_two` (human +0x360 was the null handle 0xFFFFFFFF for all four
  players, mk_a polls 7500-10900; removing effects with `FUN_00227388` at polls 10500/10510 changed nothing,
  `local/m2/mk_a/t0408_p10913.png`), and the Select ring `FUN_0024A230` (a ring on the ground, section 2.4).
- **Original look:** in the original 2-player split (no B2) these items use the global HUD camera like the disc, so
  they sit on the disc. The fix restores exactly that, for all four radars.

## 2. Markers in the original 2-player split screen and with 4 players
### 2.1 Radar icons (VERIFIED static `FUN_001B3020`, `FUN_001C5210`; runtime mk_c/mk_d)
- Every frame `FUN_00249108` calls `FUN_001B3020(HUD, handle, 0)` (our label RadarAddHuman, 0x001B3020) for every human in
  a player's squad. It sets the blip type (9 for players, 7 for AI) and the icon on **radars 1 and 2 only**: 0x16A for
  player index 0, 0x16B for any other player index, 0x16D for an AI Warrior.
- The radar update `FUN_001C5210` changes, in split view, on radar index 0 the icon 0x16B to 0x169 (0x15F when
  GameMgr+0x120 != 0) and on radar index 1 the icon 0x16A to 0x168 (0x15E) (disassembly 0x001C5E44-0x001C5ED0; the
  decompile shows the flag as `DAT_0051489c[0x24]` on an 8-byte pointer type). Result in the 2-player split: on your own
  radar you are an arrow and your partner is a "1P"/"2P" label (Mission 13: GameMgr+0x120 = 0, frames 0x168/0x169).
- **With 4 players before the fix:** radars 3 and 4 had no blips at all (they are B1's radars; every blip API call goes to
  HUD+0x15D0 and HUD+0x3F10 only). Players 3 and 4 had the player-2 icon everywhere; on radar 2 they kept the unswapped
  0x16B, i.e. **player 2's own arrow** (`local/m6/hud34/z_c2.png`).
- **After R4/R5:** all four radars hold the same blips; on radar r the own player keeps his arrow, player 1 is shown with
  0x168/0x15E, players 2-4 with 0x169/0x15F; player 3 is red (widget colour +0xB4 = 0xFF2020FF), player 4 green
  (0xFF20FF20), others the default 0xFFB2B2B2 (mk_g probe `radars@9400`, e.g. radar 3: P1 0x168, P2 0x169, P3 0x16B own,
  P4 0x169 green). Example (`local/m6/hud34/z_g_r3.png`): player 3's radar shows his red arrow, a green "2P" (player 4),
  the yellow "2P" of player 2 and the red "W" (player 1's "1P" lies under the others: all stand close together).
- **FAILED TEST, corrected:** the first PICON (mk_d) read the flag from GameMgr+0x90 instead of +0x120 and therefore
  showed the alternative "1"/"2" digit frames 0x15E/0x15F (`local/m6/hud34/z_d_r1.png` .. `z_d_r4.png`). Fixed in the
  final fragment; mk_g shows the game's "1P"/"2P" labels (`z_g_r1.png` .. `z_g_r4.png`).

### 2.2 Does a player see his own marker?
- Radar: yes, as the arrow in the middle of his own radar (original rule, kept).
- Above the head: nobody has a marker above the head in split view, in the original either (2.3).
- Select: the ring at your own feet is visible in every view (2.4).

### 2.3 Labels above the heads only in merged view (VERIFIED static)
- `FUN_0024B2A8` (our label MergedPlayerLabel) attaches the effect "dyn_p_one" (player index 0) or "dyn_p_two" (any other
  index) only when the level is not a special level, views < 2 and the player count > 1 (0x0024B2C8-0x0024B308).
  `FUN_0024B3D8` adds the labels of players 1 and 2 when views + cameras == 3 (merged view with 2 players) and otherwise
  removes them, **for GameMgr+0x228 and +0x22C only** (0x0024B694-0x0024B748).
- With 4 players a merged moment could give players 3-4 a "2P" label that is never removed. R6 (0x0024B2F0) lets
  `FUN_0024B2A8` label only player indices 0-1 (the same "index < 2" test as the existing marker patch 0x0024A2D4).
  **Not tested at runtime** (needs a merged view while the marker condition fires).
- The effect library in the WAD has only `dyn_p_one`, `dyn_p_two` (plus `dyn_alert_p_one/two`, `dyn_arrow_p1/p2`,
  `dyn_member_p1/p2`, `dyn_cuffs_p_one/two`), no three/four variants (string search of `local/disc/WARRIORS.WAD`).

### 2.4 The Select ring and the target marker (VERIFIED, mk_c/mk_d)
- `FUN_0024A230` (the coordinator's "marker"; our label HealthRing) is called by the marker loop `FUN_0024B780` when a
  player presses Select (pad flag 0x100, edge test `FUN_00144BF0`) or has low health, with the 5th argument = **view
  index** (player index when views > 1, else 0). It takes texture and UV from sprite item view + 9 and draws a coloured
  ring on the ground. Items 9/10 are the per-view items of views 0/1 (runtime mk_a: items 7/8 and 9/10 views 0/1; 11 and
  12 view 0xFF with other textures 0x00C062E0/0x00C06220; 13-15 B2's per-view copies).
- P1 pressing Select (polls 10200-10440): ring around P1's feet in views 1, 2 and 3 and his status panel
  (`local/m2/mk_c/t0388_p10292.png`). Player 4 (Select at 10700-11020) and player 3 (11300-11620) before R7: no ring, no
  panel (`local/m2/mk_d/t0412_p11016.png`, `t0424_p11380.png`). The panel is blocked by B1's slot guard S1 on `FUN_001B28A0`
  (slot < 2); the ring asks for items 11/12.
- `FUN_0024AF78` (target marker above a grabbed/targeted human, frame 0 of the same item) has the same view + 9 lookup.
- R7 LOOK9 replaces both lookups (0x0024A298, 0x0024AFA4): views 2/3 get own copies of item 9 (same page and arguments as
  `FUN_00184918` makes items 9/10, view 2/3). Result (mk_e, mk_f): the copies are made (data 0x000E8A00 = 0x1C (view 2), 0x000E8A04 = 0x22
  (view 3), state at the end of mk_e); **player 4's ring now appears** around his feet in his view, the same green ring
  as player 1's (`local/m2/mk_e/t0409_p10925.png`, `t0403_p10742.png`, `t0415_p11109.png`). Without R7 the same press
  gave a blurred yellow-green patch there (item 12's texture, `local/m6/hud34/z_t0412_p11023_v3.png`, mk_c) or nothing
  (mk_d). **Player 3's ring still does not appear** (mk_e/mk_f polls 11300-11690, e.g. `local/m2/mk_f/t0429_p11536.png`);
  player 1's ring is unchanged (`local/m2/mk_f/t0388_p10305.png`). HYPOTHESIS for player 3: the marker loop also reads
  the 2-entry byte array 0x00622E10 with the player index; 0x00622E12 (index 2) read 1 at runtime (mk_f probe `pads`),
  index 3 reads 0, so player 3 takes the "always marked" branch with other 2-entry state. Not investigated further.
  Note on the test scripts: the slot-2 script (`mk_p3s.txt`, pad 1) drives **player 4** (pad 1 owner = player index 3)
  and the slot-3 script (`mk_p4s.txt`, pad 2) drives **player 3** (mk_f probe `pads`: pad 1 -> 3, pad 2 -> 2), so the
  Select presses at polls 10700-11020 are player 4's and those at 11300-11620 player 3's.

## 3. "3P"/"4P" labels: options and choice
(Superseded 2026-10-12 by section 9: option (a) was built after all, by writing the labels into the texture at runtime.)
- (a) "3P"/"4P" from existing art or the HUD font: **not feasible cheaply.** No code path uses a 3P/4P frame (the radar
  code uses 0x15E/0x15F and 0x168-0x16D only) and there are no label effects for players 3-4 (2.3). Building a "3"/"4"
  from font glyphs would need a second widget per blip and per radar (HYPOTHESIS: possible, not attempted).
- (b) **Recolour (chosen):** player 3 red, player 4 green on every radar; player 2 keeps the game's yellow. The icon shape
  follows the original rule (own arrow, others' label). Example: on player 1's radar the three "2P" are yellow (P2), red
  (P3) and green (P4) (`local/m6/hud34/z_g_r1.png`).
- (c) Hide players 3-4: rejected; they would be invisible on everybody's radar.

## 4. Fix: `mod/m2/markers34.txt`, group `[warriors-4p 4p markers]` (after `4p hud B2`)
| Part | Patched game words (was) | Caves / data | What it does |
|---|---|---|---|
| R1 | 0x00197180 (384200FF `xori v0,v0,0xFF` -> `sltiu v0,v0,0xFE`) | | `FUN_00197168` draws view 0xFE like 0xFF; SHARED copies only 0xFF, so 0xFE items take the original global-camera path |
| R2 BINIT/BMK | 0x001C4B60, 0x001C4EB0 (0040F809 `jalr ra,v0`, the blip widget init in `FUN_001C4A40`/`FUN_001C4D00`) | BINIT 0x000E82C0, BMK 0x000E86C0, data 0x000E83F0-0x000E83FB (saved ra, widget, BLIPIDX) | after the init, the widget's sprite index +0xC4 becomes BLIPIDX: a copy of item 2 with view 0xFE, made on first use and re-made after the level unload (`FUN_00185AE0` frees items 13-254) |
| R3 RTAG | 0x001C4160 (AE400044 `sw zero,0x44(s2)`, end of radar init `FUN_001C3DE0`) | 0x000E8100 | the radar's 7 dot sprites (+0x48..+0x60, index << 16, made by `FUN_0039C388` with view 0xFF) get view 0xFE |
| R4 PICON | 0x001B3148, 0x001B31C8 (0C06CB28 `jal 0x001B2CA0`, icon 0x16B / 0x16A) | 0x000E8180 (moved to 0x000E8DE0 by L4, section 9.3) | after the original call, with 2+ views: on each of the 4 radars the human's widget gets the player-3/4 colour and, unless it is that radar's own player, the other-player frame (0x168/0x169, or 0x15E/0x15F when GameMgr+0x120 != 0, as the game at 0x001C5E64) |
| R5 FAN | entries of `FUN_001C4528`, `4640`, `4690`, `4768`, `48C0`, `49D0`, `4A40`, `4BE0`, `4D00`, `4FF8`, `5108`, `4500` (2 words each -> `j stub; nop`) | FANCORE 0x000E8400, stubs 0x000E8500-0x000E869F | a call with radar 2 (0x00604750) from outside the radar module (ra not in 0x001C3000-0x001C6FFF) runs for radar 2, then for radars 3 (0x000A9500) and 4 (0x000ABE40); returns radar 2's v0; internal calls are not repeated |
| R6 | 0x0024B2F0 (00041027 `nor v0,zero,a0` -> `sltiu v0,a0,2`) | | merged-view label only for player index 0-1 |
| R7 LOOK9 | 0x0024A298, 0x0024AFA4 (0C0616AC `jal 0x00185AB0`) | 0x000E8800, data 0x000E8A00-0x000E8A07 | sprite lookups 11/12 (views 2/3) get own copies of item 9 with view 2/3 |

- Checks: `python -I tools/note_patches.py check local/m6/hud34/final2.pnach` (current `mod/make_pnach.py`, incl. the
  coordinator's restored session hooks): **4173 addresses, 6 problems** (the 6 known
  `[4p hud A]`/`[4p hud B1]` alternatives). Every "was" word was read from the ELF and asserted by the generator. No
  branch or jump in the ELF targets entry+4/+8 of a FAN function and no data word points at their entries (scan). Every
  FAN function starts with `addiu sp,sp,-N; sq ...` (position-independent), except `FUN_001C4500`, whose branch is
  rebuilt in its stub (delay slot 0x001C4508 kept). None of the FAN functions takes stack arguments.
- Free RAM used: 0x000E8100-0x000E8A07 (before, only 0x000E8000-0x000E80B3 = RHALF was used in the 0x000E8xxx page).
- Determinism: every part reads only game state; the sprite copies are made at the same frame on every instance. Not yet
  run in a 4-instance lockstep (open).
- Without B1/B2 the group is harmless: FAN targets zero memory (every radar function returns when its +0 == 0).
- Generator (scratch, not committed): the cave sources are in Appendix A; the fragment was produced from them with
  `asm5900`-style assembly and checked by disassembly of the generated pnach.

## 5. The full map (task 3)
- **No in-mission map (VERIFIED).** The story pause menu items are Objectives, Stats, Options, Controls, Restart, Resume,
  Quit (`FUN_001DE6C0`, strings read at runtime; `session_policies.md` 1.5). No mission script or pad handler opens a
  map (search for map strings in all extracted Lua: only the hub).
- **The game's "map" is the hub's level select (VERIFIED scripts):** "press <ST> to access map" exists only in the
  `LEVEL95.ACTC` texts of the hub scripts (`local/analysis/lua/09401_4808de63.txt` line 9110, `09528_b749f4f7.txt` line
  296); "QuickMap" is an unlockable (`UT[3]`, `09401` line 555, `09512` line 78) and `DoQuickMap` is defined in the hub
  script `09401`; "Select and replay levels from the map" is the post-story level select. "Game Map" and "Subway Map" in
  the ELF are resource chunk names (0x00549820, 0x005498E8). HYPOTHESIS (not run): the hub map shows missions, not
  player positions.
- **Who can open what in a session:** the pause menu belongs to the host (D17); the others can only resume. Nobody can
  open a map inside a mission. Each player sees the others on **his own radar** (now including players 3-4).

## 6. Players 3 and 4 after joining (report only)
- mk_b `snap@8800` (both joined, not yet walking): player 3 at (74.87, 381.275, 4.795) and player 4 at exactly the same
  position (players 1 and 2 at (73.37, 381.28) and (74.14, 382.26)). Their cameras therefore showed the same picture.
  After the test walk (polls 9000-9230) they stood about 10 units apart. Cause not investigated (spawn/companion
  placement, `m2_spawn_companion.md`).

## 7. Open points
- "3P"/"4P" art does not exist; players 3-4 are coloured "2P" icons (section 3). Superseded: section 9 ("3P"/"4P" built at runtime).
- Select status panel for players 3-4 (B1 S-guard on `FUN_001B28A0`).
- R6 untested at runtime; 2-player sessions with B2, widescreen and other missions not re-checked; no 4-instance lockstep
  run with the new group.
- `FUN_001C4500` (radar mode +0x38, used for the disc colour) is now mirrored to radars 3-4 by FAN; the visible effect was
  not checked.
- `FUN_00174320` (a per-character decal from sprite item view + 9, only for views 0-1) still skips views 2-3
  (HYPOTHESIS: a shadow-like decal under characters is missing in views 3-4; not checked).

## 8. Tests (SINGLE-PC, one instance, sandbox 15, scripted bots, no impairment, MTVU off, Mission 13)
| Run | Pnach / groups | Purpose | Result |
|---|---|---|---|
| mk_a | `local/m6/hud34/base.pnach` (current mod incl. RHALF), the standard 4p groups | diagnosis: positions, effects, sprite items; CallAt `FUN_00227388` on P3/P4 humans at 10500/10510 | labels unchanged after the CallAt; human +0x360 null for all players; items 9/10 views 0/1, 11/12 0xFF |
| mk_b | base.pnach | radar tables; item 2 set to view 0xFE at 9700 | 6 blips on radars 1-2, 0 on radars 3-4; floating "2P"/"A" gone after the write; P3 = P4 position at 8800. (Its `tag_dots_fe` step read a wrong field and wrote nothing useful; ignore it.) |
| mk_c | `c2.pnach` + `4p markers` (R1-R3 and a first tint for radars 1-2, no FAN) | first fix | icons on discs 1-2, nothing floating; radars 3-4 still empty; P1 Select ring in 3 views |
| mk_d | `c4.pnach` + `4p markers` (R1-R6) | full radar fix | 6 blips on all 4 radars, colours as designed; frames 0x15E/0x15F because PICON read the wrong flag (FAILED TEST, fixed in mk_g); P3/P4 Select: no ring |
| mk_e | `c5.pnach` + `4p markers` (R1-R7) | LOOK9 | copies for views 2/3 made; player 4's Select ring shown, player 3's not; player 1's unchanged; 0 TLB misses (emulog of mk_e). |
| mk_f | same pnach as mk_e | regression P1 ring, pad owners | P1 ring and panel as before; radars as in mk_d; pad 1 -> player index 3, pad 2 -> 2; 0x00622E12 = 1; 0 TLB misses |
| mk_g | `local/m6/hud34/final.pnach` + `4p markers` (final fragment, R1-R7, PICON flag GameMgr+0x120) | final check | icons on all 4 discs, nothing floating; frames 0x168/0x169 for others, own arrow 0x16A/0x16B, P3 red, P4 green (`local/m2/mk_g/t0364_p9578.png`, zooms `z_g_r1..r4.png`); BLIPIDX 0x16 view 254; LOOK9 copies 0x1C/0x22; 0 TLB misses |

All runs ended by timeout (450-490 s); the test runner's PINE reads reported a few "error code 255" while the game was
loading (no effect on the probes listed).

## 9. "3P" and "4P" labels for players 3 and 4 (2026-10-12, parts L1-L5)

### Plain English
- **Players 3 and 4 now show as "3P" and "4P" on the radars**, in the same style as the game's "1P"/"2P" (number first,
  bold yellow digit with a dark outline, then the game's own "P"), and still in their own colours: player 3 red, player 4
  green. Player 1 ("1P") and player 2 ("2P", yellow) are unchanged, and everyone still sees himself as an arrow.
  Example (run l34e, `local/m6/p34/z_l34e_p9915_r1.png`): player 1's radar shows a yellow "2P", a red "3P" and a green
  "4P" around his own arrow; player 3's radar (`z_l34e_p9915_r3.png`) shows his red arrow, "1P", "2P" and a green "4P".
- **How, without shipping any game art:** the game has no "3P"/"4P" picture, so the patch draws the two labels itself,
  once, while the game runs. All radar icons come from one picture in the console's memory (the HUD texture page
  "part_page0"), and the game sends that picture to the graphics chip again every frame. The patch writes two new
  small labels into an empty corner of that picture: the "P" is copied from the game's own "2P" label, the shape of the
  "3" and "4" comes from the game's own small HUD font (which also has digits), and the colours (yellow fill, light
  top/bottom edge, dark outline, grey-blue bottom line) are taken from the game's "2" label. Nothing from the game is
  stored in the patch file; it only contains code and the graphics chip's memory layout tables.
- **Also fixed on the way (L5):** the radar turns arrows with the player's heading but keeps "1P"/"2P" labels upright.
  At first the new labels were turned like arrows (they showed upside down when a player walked south, FAILED TEST l34b);
  they are now kept upright like the game's own labels.
- **Safe fallback:** before writing anything the patch checks the picture (size, format, the "2P" art where expected,
  the target corner really empty). If any check fails, players 3 and 4 keep the coloured "2P" from before.
- **The game's other radar mode** (single digits "1"/"2" instead of "1P"/"2P", chosen by GameMgr+0x120) also gets
  "3"/"4" (tested by forcing the flag, l34c).
- **Open:** tested on one PC, one emulator instance, Mission 13, bots only; not yet in a 4-instance lockstep run;
  labels can still overlap when players stand close together (same as the game's "1P"/"2P").

Build: The Warriors SLUS-21215 v1.03 (`local/disc/SLUS_212.15`, read-only); fork build w4p-m6-1 (not rebuilt,
`emulator/` untouched). Addresses static unless marked dynamic; function names are OUR labels. Tests: **SINGLE-PC, one
instance (sandbox 13), scripted bots, no impairment, MTVU off**, Mission 13 via the standard level jump, 2x internal
resolution, screenshots at scale 1.0. `mod/w4p_m1.pnach` was NOT regenerated (a 4-instance batch uses it); test pnachs
in `local/m6/p34/` (final: `l34c.pnach`). Extracted texture data and decoded pictures stay in `local/m6/p34/`.

### 9.1 The radar icon picture (VERIFIED, runtime p34a, EE dump `local/m6/p34/ee_9405.bin`)
| Fact | Value | Evidence |
|---|---|---|
| Blip sprite item | BLIPIDX item 0x16 and global item 2 use page "part_page0" (item +0x0C = page 0x00C063A0, dynamic) | probe `icon34_probe.survey@9300` |
| Frame table | page +0x0C -> resource (+4 count 0x173, +8 font base 0x5E, +0x0C table 0x00FDCA14); 16 bytes per frame (u0, v0, u1, v1, normalised); `FUN_00181E38(page, frame)` returns table + frame * 16 | survey; disassembly 0x00181E38 |
| Texture | page +0x14 -> RenderWare texture -> raster 0x00A61C68: 512 x 256, 8 bit (TEX0 PSM 0x13, TBW 8, CLUT PSMCT32 CSM1); pixels raster+4 = 0x00FBC550, palette raster+8 = 0x00FDC5D0 (dynamic) | survey, TEX0 decode |
| EE copy format | the 8-bit picture is stored ready for upload as PSMCT32 256 x 128 (BITBLTBUF DBW 4), palette as PSMCT32 16 x 16 at DBP +0x200, behind a DMA chain at raster +0x24 (0x00FBC400) | GIF tags at 0x00FBC400-0x00FBC54F |
| Upload | **every frame**: TEX0 TBP alternates 0x3960 / 0x3480 every 1-3 polls | p34b `tex_watch@9300` (40 samples) |
| Labels in the atlas | 0x169 "2P" texels (318,144)-(336,155): the "2" = 9 texels, the "P" = 10 texels; 0x15F "2" alone (338,144) (104 of 108 texels equal to the "2" of "2P"); 0x15E "1"; 0x168 "1P" (297,233) | frame table, decoded atlas `local/m6/p34/atlas_part_page0.png` |
| Digits in the same picture | part_page0 also holds a small white font: frame = 0x5E + character, cells 9 x 18 texels, glyphs 10 rows; '3' = 0x91 at (70,215), '4' = 0x92 at (60,215). Other digits: big 3D digits 0x0D-0x13 (wide, other style); `big_font` (item 6) is a separate slab-serif page | frame table, atlas |
| Free texels | no frame rectangle (+1 texel) and alpha 0 in x 85-277, y 234-247 | offline scan of all 0x173 frames |
| No "3P"/"4P" art | none of the 0x173 frames shows a 3P/4P label (decoded atlas) | `atlas_part_page0.png` |

**Re-upload test (VERIFIED, p34b):** at poll 9504 a test probe copied the "1P" texels over the "2P" texels in the EE copy
(`icon34_probe.tex_test`, PINE, single instance). Every "2P" label on the radars turned into a "1P" in the next
screenshot (`local/m6/p34/zb_before_r1.png` from `local/m2/p34b/t0357_p9364.png`, `zb_after_r1.png` from
`t0363_p9549.png`). So a texel written into the EE copy is on screen in the next frame; no upload call is needed.

### 9.2 How the labels are built (L2 GEN, runs once per texture copy)
1. Find the raster through item 2 -> page -> texture -> raster; require 512 x 256 x 8 bit, frame count >= 0x16A and the
   font digits inside the table.
2. Read the "2P" (0x169) and "2" (0x15F) positions from the frame table (float u/v x 512/256); require the same row and
   at most 12 of 108 texels different between the "2" of "2P" and the standalone "2" (4 differ in SLUS-21215).
3. Take the palette indices from the standalone "2": fill (+5,+2) = 0x7B, highlight (+2,+10) = 0xEF, outline (+8,+3) =
   0x09, bottom line (+3,+11) = 0x9B, clear (-1,0) = 0x07 (must be transparent).
4. Check that x 88-161, y 234-249 is fully transparent (otherwise stop: coloured "2P" stays).
5. For '3' and '4': the font glyph's mask (palette alpha >= 0x60 and red >= 0x80) over 10 rows from its first row,
   trimmed to its used columns, placed right-aligned in an 11 x 12 cell; each cell texel becomes highlight (glyph texel
   at the top or bottom edge of a stroke), fill (other glyph texels), bottom line (row 11 next to the glyph), outline
   (next to the glyph) or clear. The cell is written twice: as the digit of the label and as the digit-only frame.
6. The 10 x 12 "P" texels of "2P" are copied right of the digit.
Result: "3P" at (90,236) and "4P" at (113,236), 21 x 12 texels; "3" at (136,236), "4" at (149,236), 11 x 12. The
virtual frames 0xFFF3/0xFFF4/0xFFF5/0xFFF6 point at these rectangles (VTAB, same half-texel insets as the game's frames).
Texel address in the EE copy: GS address of the PSMT8 texel (block/column tables), mapped back through the PSMCT32
upload layout (inverse block/column tables); the four tables (384 bytes) come from the GS memory layout in
`emulator/pcsx2/pcsx2/GS/GSTables.cpp` (hardware layout, not game data). Offline check: the mapping reproduces the whole
decoded atlas (0 mismatches, `ee_offsets` in `tests/m2/icon34_probe.py`).
Example (palette indices, "3P", run l34a, identical to the scratch simulation):
```
07 07 07 09 09 09 09 09 07 07 07 5e 09 9b 09 09 9b 09 ae b8 01
07 09 09 09 ef ef ef 09 09 09 07 69 7b 7b 7b 7b 7b 7b 94 99 e4
07 09 ef ef ef ef ef ef ef 09 07 a1 94 7b 7b 7b 7b 7b 7b 7b 09
07 09 ef ef 09 09 09 7b 7b 09 07 59 09 7b ef 3d 63 9b 7b ef 1b
...
07 9b 9b 9b 9b 9b 9b 9b 9b 9b 07 ae 0d 9b 9b 9b 2a 7d 07 07 07
```

### 9.3 Patch parts (added to `mod/m2/markers34.txt`, group `[warriors-4p 4p markers]`)
| Part | Patched game words (was) | Caves / data | What it does |
|---|---|---|---|
| L1 VFR | 0x00181E38 (8C83000C `lw v1,0xC(a0)` -> `j VFR`; 0x00181E3C `andi a1,a1,0xFFFF` kept as delay slot) | VFR 0x000E8F40, VTAB 0x000E8B60-0x000E8C5F | `FUN_00181E38` (frame -> UV record): frames 0xFFF0-0xFFFF come from VTAB (3 "3P", 4 "4P", 5 "3", 6 "4"; others zero); all other frames unchanged |
| L2 GEN | | GEN 0x000E92E8, helpers OFF/PXR/PXW/ALPHA/MASKPX/FXY/RAS/CLASS 0x000E8F78-0x000E924F, tables 0x000E8C60-0x000E8DDF, data 0x000E8A10-0x000E8B55 | builds the labels (9.2) |
| L3 ENSURE | | 0x000E9250 | returns 1 when the labels exist: same pixel buffer as last time and the marker texel (first P column of "3P") equal to the 2P source; otherwise runs GEN once (a buffer that failed GEN is not retried) |
| L4 | PICON moved: 0x001B3148, 0x001B31C8 now `jal 0x000E8DE0` (was `jal 0x000E8180`; game word 0C06CB28 `jal 0x001B2CA0`) | PICON 0x000E8DE0 | as R4, plus: players 3-4 call ENSURE once per call; on other players' radars their widget frame becomes 0xFFF3/0xFFF4 (digit-only mode 0xFFF5/0xFFF6) instead of 0x169/0x15F; colours unchanged |
| L5 LBLCHK | 0x001C5F08 (5482000A `bnel a0,v0` -> `j LBLCHK`; delay slot 0x001C5F0C `lw v0,0x948(s2)` kept) | 0x000E976C | in the radar update `FUN_001C5210` (0x001C5ED8-0x001C5F2C) frames 0x19, 0x1A, 0x168, 0x169, 0x15E, 0x15F get rotation 0 (upright) and all others turn with the heading; L5 adds 0xFFF0-0xFFFF to the upright set |

- RAM: 0x000E8A10-0x000E9793 (new). The old PICON range 0x000E8180-0x000E82BF is no longer written (free again).
- Checks: `python -I tools/note_patches.py check local/m6/p34/l34c.pnach` (current `mod/make_pnach.py` and the other
  fragments, 2026-10-12): **5650 addresses, 6 problems** = the 6 known `[4p hud A]`/`[4p hud B1]` alternatives
  (0x001C0648, 0x001C7890, 0x001A6D28, 0x001A6C38, 0x0041DC44, 0x0041DC50). Every "was" word is read from the ELF and
  asserted by the generator.
- Scratch simulation (not in the repo): the generated words run in a small R5900 interpreter on the EE dump: VFR returns
  the original pointer for 0x169 and VTAB+0x30 for 0xFFF3; ENSURE builds the labels in 196,108 instructions (once) and
  then answers in 145; s-registers and sp preserved; output identical to a Python prototype of the same rules.
- Determinism (HYPOTHESIS until a lockstep run): GEN reads only game memory and writes only the texture copy and its own
  data, on the first frame a player 3/4 icon is set, so every instance builds the same texels at the same frame.
- Costs: GEN about 0.2 M instructions once; per frame 2 ENSURE calls (a few hundred instructions); 3 extra instructions
  per `FUN_00181E38` call.
- Risks (HYPOTHESIS): a caller of `FUN_00181E38` that passes frame 0xFFF0-0xFFFF on purpose would now get VTAB (none
  found; menu and HUD texts render normally in l34a-l34e); another texture page with the same layout but different art
  fails the checks and falls back to "2P".

### 9.4 Tests (SINGLE-PC, one instance, sandbox 13, scripted bots, no impairment, MTVU off, Mission 13)
Command (template): `python -I tests/m2/nav_probe.py <tag> <p1 script> --inst 13 --players 4 --script2 <p2> --script3
<slot 2 = player 4> --script4 <slot 3 = player 3> --groups "<local/m6/p34/groups.txt>" --ini EmuCore/Speedhacks/vuThread=false
--ini EmuCore/GS/upscale_multiplier=2 --shot-scale 1.0 --every 5 --callat "4000:0041ABC0:1,4010:00160D78:0x01FD9F9C"
--probe icon34_probe:... --patch local/m6/p34/<pnach> --seconds 420`.

| Run | Pnach / scripts | Purpose | Result |
|---|---|---|---|
| p34a | `base.pnach` (before L1-L5), cal_p3/cal_p4 | survey + 32 MB EE dump | 9.1 table; `ee_9405.bin`, decoded `atlas_part_page0.png`, `atlas_big_font.png` (local only) |
| p34b | `base.pnach` | re-upload test | TBP alternates every frame; "2P" -> "1P" after the EE write (9.1); **VERIFIED** |
| l34a | `l34a.pnach` (L1-L4), cal_p3/cal_p4 | first runtime test | GENOK = 1 at poll 8700, texels identical to the simulation; radar frames 0xFFF3/0xFFF4 with VTAB UVs on the other players' radars, own arrows 0x16B, P1/P2 frames 0x168/0x169/0x16A/0x16B as before; 0 TLB misses; players stood together, labels overlapped (`z_l34a_r1..r4.png`) |
| l34b | `l34a.pnach`, players walk apart (`walk_p1..p4.txt`), poke GameMgr+0x120 = 1 at 10600-11200 | spacing, digit-only mode | **FAILED TEST**: "3P"/"4P" turned with the player's heading (upside down/sideways, `z_l34b_p9784_r1..r3.png`) -> L5. Digit-only mode showed "3"/"4" (also turned) |
| l34c | `l34c.pnach` (L1-L5), same scripts | L5 | labels upright (`z_l34c_p9776_r1..r4.png`); digit-only mode "1", "3", "4" upright (`z_l34c_p10863_r1.png`, `_r2.png`); 0 TLB |
| l34d | `l34c.pnach`, wider walks (`w2_*.txt`) | readable crops | `z_l34d_p9866_r1..r4.png`; some labels still overlap |
| l34e | `l34c.pnach`, P2 walks 220 polls, players 3/4 320/420 polls (`w2_p2.txt`, `w3_s2.txt`, `w3_s3.txt`) | final check | **all four radars** (`local/m2/l34e/t0380_p9915.png`; zooms `local/m6/p34/z_l34e_p9915_r1..r4.png`): r1 (P1) 2P yellow, 3P red, 4P green, own arrow; r2 (P2) 1P, 3P, 4P, own arrow; r3 (P3) own red arrow, 1P, 2P, 4P green; r4 (P4) 1P, 2P, 3P red, own green arrow. Nothing floating in the scene; 0 TLB misses (`local/pcsx2/inst13/PCSX2/logs/emulog.txt`, run l34e) |

All runs ended by timeout; the runner's PINE reads reported a few "error code 255" while the game was loading (no effect
on the probes listed). Probe module: `tests/m2/icon34_probe.py` (read-only except the TEST ONLY `tex_test`).

### 9.5 Open points
- No 4-instance lockstep run with L1-L5 yet (determinism HYPOTHESIS, 9.3); not run in other missions, the hub, widescreen
  or a 2-player session (L1-L5 do nothing there: GEN runs only for player index 2-3, VFR/LBLCHK are pass-through for the
  game's own frames).
- Overlapping labels when players stand close (as with the game's own labels); player 4's label is drawn on top.
- `mod/make_pnach.py`'s description of the group still says "coloured red/green" (not changed: the file is shared).

## Appendix A: cave sources
R5900, assembled at the addresses in section 4. Constants filled by the generator: TINT3 = 0xFF2020FF (player 3, red),
TINT4 = 0xFF20FF20 (player 4, green), DATA = 0x000E83F0, DATA9 = 0x000E8A00, FANCORE_AT = 0x000E8400;
`jalr_v0`, `jalr_t9`, `mtc1_at_f12`, `swc1_f12_80`, `swc1_f13_84` are emitted as raw words (0040F809, 0320F809, 44816000,
E7AC0050, E7AD0054).

### RTAG
```
RTAG:
  sw zero,0x44(s2)          # replaced instruction (FUN_001C3DE0 end; s2 = radar)
  lui t0,0x51
  lw t0,-0x32B4(t0)         # sprite manager [0x0050CD4C]
  beq t0,zero,rt_ret
  addiu t1,s2,0x48          # dot textures +0x48..+0x60 (sprite index << 16)
  addiu t2,s2,0x64
  addiu t7,zero,0xFF
rt_loop:
  lhu t3,2(t1)
  beq t3,zero,rt_next
  sltu at,t3,t7
  beq at,zero,rt_next
  sll t5,t3,7
  sll t6,t3,3
  subu t5,t5,t6             # index * 0x78
  addu t5,t5,t0
  addiu t6,zero,0xFE
  sb t6,0x18DE(t5)          # item +0x42 (item = manager + 0x189C + index*0x78) = 0xFE
rt_next:
  addiu t1,t1,4
  bne t1,t2,rt_loop
  nop
rt_ret:
  jr ra
  nop
```

### PICON
```
PICON:
  addiu sp,sp,-48
  sw ra,0(sp)
  sw a0,4(sp)               # HUD
  sw a1,8(sp)               # human handle
  jal 0x1B2CA0              # original call: icon a2 (0x16A / 0x16B) on radars 1 and 2 (3 and 4 through FAN)
  sw s2,12(sp)              # human
  lui at,0x51
  lw v0,-0x4E68(at)         # views 0x0050B198
  sltiu at,v0,2
  bne at,zero,pc_ret        # merged view: icons as the game sets them
  lw t0,12(sp)
  lb t1,0x1B0(t0)           # player index p
  bltz t1,pc_ret
  slti at,t1,4
  beq at,zero,pc_ret
  sw t1,28(sp)
  sw zero,20(sp)            # r = 0
pc_loop:
  lw t3,20(sp)
  lw a0,4(sp)
  addiu a0,a0,0x15D0        # radar 1 (HUD+0x15D0)
  beq t3,zero,pc_r
  addiu at,zero,1
  beq t3,at,pc_r
  addiu a0,a0,0x2940        # radar 2 (HUD+0x3F10)
  lui a0,0x000B
  addiu at,zero,2
  beq t3,at,pc_r
  addiu a0,a0,-0x6B00       # radar 3 (0x000A9500, 4p hud B1)
  lui a0,0x000B
  addiu a0,a0,-0x41C0       # radar 4 (0x000ABE40)
pc_r:
  sw a0,24(sp)
  lw a1,8(sp)
  jal 0x1C5188              # blip slot of the handle (-1 = none)
  daddu a2,zero,zero
  addiu at,zero,-1
  beq v0,at,pc_next
  sll v0,v0,6
  lw a0,24(sp)
  addu v0,v0,a0
  lw v1,0x948(v0)           # blip widget
  beq v1,zero,pc_next
  lw t1,28(sp)
  slti at,t1,2
  bne at,zero,pc_frame
  addiu at,zero,2
  lui t2,{TINT4 >> 16:#x}
  bne t1,at,pc_tint
  ori t2,t2,{TINT4 & 0xFFFF:#x}
  lui t2,{TINT3 >> 16:#x}
  ori t2,t2,{TINT3 & 0xFFFF:#x}
pc_tint:
  sw t2,0xB4(v1)            # players 3 / 4: own colour
pc_frame:
  lw t3,20(sp)
  beq t3,t1,pc_next         # own radar: keep the own-player icon
  lui at,0x51
  lw t4,0x489C(at)          # GameMgr
  lw t4,0x120(t4)           # GameMgr+0x120 (the game's choice 0x168/0x169 vs 0x15E/0x15F, 0x001C5E64)
  addiu t5,zero,0x169       # other player: "2P" label (players 2-4)
  bne t1,zero,pc_sel
  addiu t6,zero,0x15F
  addiu t5,zero,0x168       # player 1: "1P" label
  addiu t6,zero,0x15E
pc_sel:
  beq t4,zero,pc_st
  nop
  daddu t5,t6,zero
pc_st:
  sw t5,0xC8(v1)            # widget frame (FUN_001A2910 stores +0xC8)
pc_next:
  lw t3,20(sp)
  addiu t3,t3,1
  sw t3,20(sp)
  addiu at,zero,4
  bne t3,at,pc_loop
  nop
pc_ret:
  lw ra,0(sp)
  jr ra
  addiu sp,sp,48
```

### BINIT
```
BINIT:
  lui at,0x000F
  sw ra,{DATA - 0xF0000}(at)
  sw a0,{DATA + 4 - 0xF0000}(at)
  jalr_v0                   # original call
  nop
  lui at,0x000F
  lw t0,{DATA + 8 - 0xF0000}(at)   # BLIPIDX
  addiu t1,zero,0xFF
  beq t0,t1,bi_ret          # manager was full: keep sprite 2
  lui t2,0x51
  lw t2,-0x32B4(t2)         # sprite manager
  beq t0,zero,bi_make
  sll t3,t0,7
  sll t4,t0,3
  subu t3,t3,t4
  addu t3,t3,t2             # item - 0x189C
  lbu t4,0x18DC(t3)         # valid (+0x40)
  beq t4,zero,bi_make
  lbu t4,0x18DE(t3)         # view (+0x42)
  addiu t5,zero,0xFE
  beq t4,t5,bi_set
  nop
bi_make:
  jal BMK                   # (re)create the blip sprite; level unload frees items 13-254
  nop
  lui at,0x000F
  lw t0,{DATA + 8 - 0xF0000}(at)
  addiu t1,zero,0xFF
  beq t0,t1,bi_ret
  nop
bi_set:
  lui at,0x000F
  lw a0,{DATA + 4 - 0xF0000}(at)
  sw t0,0xC4(a0)            # widget sprite index -> blip sprite (view 0xFE, global HUD camera)
bi_ret:
  lui at,0x000F
  lw ra,{DATA - 0xF0000}(at)
  jr ra
  nop
```

### BMK
```
BMK:
  addiu sp,sp,-64
  sd ra,32(sp)
  sw zero,16(sp)            # vec (0, 0, 0, 1.0) as FUN_00184918
  sw zero,20(sp)
  sw zero,24(sp)
  lui at,0x3F80
  sw at,28(sp)
  lui a0,0x005E
  addiu a0,a0,-0x6E20       # 0x005D91E0
  lui a1,0x0055
  jal 0x00143F68            # page resource "part_page0"
  addiu a1,a1,0x2B78
  daddu a1,v0,zero
  lui v0,0x0051
  lw a0,-0x32B4(v0)
  addiu a2,zero,0x80        # instances
  daddu a3,zero,zero
  daddu t0,zero,zero
  addiu t1,zero,1
  addiu t2,zero,2
  addiu t3,sp,16
  addiu at,zero,0xFE
  sw at,0(sp)               # 9th argument: view 0xFE
  lui at,0x462B
  ori at,at,0xE000
  mtc1_at_f12               # 11000.0 as sprite 2
  jal 0x0018AEC0
  nop
  lui at,0x000F
  sw v0,{DATA + 8 - 0xF0000}(at)
  addiu at,zero,0xFF
  beq v0,at,mk_ret
  daddu a1,v0,zero
  lui v0,0x0051
  jal 0x00185AB0
  lw a0,-0x32B4(v0)
  daddu a0,v0,zero
  jal 0x001972B0            # activate
  addiu a1,zero,1
mk_ret:
  ld ra,32(sp)
  jr ra
  addiu sp,sp,64
```

### FANCORE
```
FANCORE:
  lui at,0x0060
  ori at,at,0x4750
  bne a0,at,fc_orig
  lui at,0x001C
  ori at,at,0x3000
  sltu at,ra,at
  bne at,zero,fc_go
  lui at,0x001C
  ori at,at,0x7000
  sltu at,ra,at
  bne at,zero,fc_orig
  nop
fc_go:
  addiu sp,sp,-128
  sd ra,0(sp)
  sd t9,8(sp)
  sd a0,16(sp)
  sd a1,24(sp)
  sd a2,32(sp)
  sd a3,40(sp)
  sd t0,48(sp)
  sd t1,56(sp)
  sd t2,64(sp)
  sd t3,72(sp)
  swc1_f12_80
  swc1_f13_84
  jalr_t9                   # radar 2 (original call)
  nop
  sd v0,88(sp)
  sw zero,96(sp)
fc_loop:
  ld a1,24(sp)
  ld a2,32(sp)
  ld a3,40(sp)
  ld t0,48(sp)
  ld t1,56(sp)
  ld t2,64(sp)
  ld t3,72(sp)
  lwc1 f12,80(sp)
  lwc1 f13,84(sp)
  lw at,96(sp)
  lui a0,0x000B
  beq at,zero,fc_call
  addiu a0,a0,-0x6B00       # radar 3
  lui a0,0x000B
  addiu a0,a0,-0x41C0       # radar 4
fc_call:
  ld t9,8(sp)
  jalr_t9
  nop
  lw at,96(sp)
  addiu at,at,1
  sw at,96(sp)
  addiu v1,zero,2
  bne at,v1,fc_loop
  nop
  ld v0,88(sp)              # radar 2's result
  ld ra,0(sp)
  jr ra
  addiu sp,sp,128
fc_orig:
  jr t9
  nop
```

### LOOK9
```
LOOK9:
  addiu at,zero,11
  sltu at,a1,at
  bne at,zero,lk_orig
  addiu at,zero,13
  sltu at,a1,at
  beq at,zero,lk_orig
  nop
  addiu sp,sp,-80
  sd ra,32(sp)
  sd a0,40(sp)
  sd a1,48(sp)
  lui t0,0x000F
  sll t1,a1,2
  addu t0,t0,t1
  lw t1,{DATA9 - 0xF0000 - 44}(t0)    # copy index for view a1-9
  addiu at,zero,0xFF
  beq t1,at,lk_none
  nop
  beq t1,zero,lk_make
  sll t2,t1,7
  sll t3,t1,3
  subu t2,t2,t3
  addu t2,t2,a0
  lbu t3,0x18DC(t2)                   # valid
  beq t3,zero,lk_make
  lbu t3,0x18DE(t2)                   # view
  addiu t4,a1,-9
  beq t3,t4,lk_use
  nop
lk_make:
  sw zero,16(sp)
  sw zero,20(sp)
  sw zero,24(sp)
  lui at,0x3F80
  sw at,28(sp)
  lui a0,0x005E
  addiu a0,a0,-0x6E20
  lui a1,0x0055
  jal 0x00143F68                      # page "part_page1" (as item 9)
  addiu a1,a1,0x2B68
  daddu a1,v0,zero
  lui v0,0x0051
  lw a0,-0x32B4(v0)
  addiu a2,zero,0x20
  addiu a3,zero,1
  daddu t0,zero,zero
  addiu t1,zero,2
  addiu t2,zero,1
  addiu t3,sp,16
  ld at,48(sp)
  addiu at,at,-9
  sw at,0(sp)                          # view 2 / 3
  lui at,0x462B
  ori at,at,0xE000
  mtc1_at_f12
  jal 0x0018AEC0
  nop
  ld t0,48(sp)
  lui at,0x000F
  sll t0,t0,2
  addu at,at,t0
  sw v0,{DATA9 - 0xF0000 - 44}(at)
  addiu at,zero,0xFF
  beq v0,at,lk_none
  daddu t1,v0,zero
  sd t1,56(sp)
  lui v0,0x0051
  lw a0,-0x32B4(v0)
  jal 0x00185AB0
  daddu a1,t1,zero
  daddu a0,v0,zero
  jal 0x001972B0                       # activate
  addiu a1,zero,1
  ld t1,56(sp)
lk_use:
  ld a0,40(sp)
  daddu a1,t1,zero
  ld ra,32(sp)
  j 0x00185AB0
  addiu sp,sp,80
lk_none:
  ld ra,32(sp)
  addiu sp,sp,80
  jr ra
  daddu v0,zero,zero
lk_orig:
  j 0x00185AB0
  nop
```

FAN stub per function F (12 functions): `lui t9,hi(T); j FANCORE; ori t9,t9,lo(T)`; T: the two original entry words of F, `j F+8; nop`. For `FUN_001C4500` T rebuilds its entry branch: `lw v1,0x38(a0); bne a1,v1,c; lui v0,0x51; j 0x001C4520; nop; c: j 0x001C450C; nop`.

## Appendix B: cave sources of L1-L5 (section 9)
R5900, assembled from 0x000E8DE0 in this order: PICON (Appendix A's PICON with the L4 changes below), VFR, the helpers, ENSURE, GEN, LBLCHK. Offsets like `-29168(t9)` are data addresses relative to t9 / s7 = 0x000F0000 (L34 data 0x000E8A10: +0 GENPIX, +4 GENOK, +8 FT, +0x0C PIX, +0x10 PAL, +0x14 BASE, +0x18 P2X, +0x1C P2Y, +0x20..+0x24 indices fill, highlight, outline, bottom line, clear; MASK 0x000E8A40, FILL 0x000E8AA0 (14 x 13), VTAB 0x000E8B60, block/column tables 0x000E8C60, 0x000E8C80, 0x000E8CA0, 0x000E8CE0). `nop #@RAWW w` lines are emitted as the raw word w (FPU instructions).

### PICON changes (L4)
```
  sw t1,28(sp)
  sw zero,16(sp)            # L34: virtual "3P"/"4P" frames usable (players 3-4 only)
  slti at,t1,2
  bne at,zero,pc_go
  nop
  jal ENSURE
  nop
  sw v0,16(sp)
pc_go:
  sw zero,20(sp)            # r = 0
  ...
pc_sel:
  lw t7,16(sp)
  beq t7,zero,pc_alt
  nop
  ori t5,zero,0xFFF1
  addu t5,t5,t1             # players 3 / 4: 0xFFF3 / 0xFFF4
  ori t6,zero,0xFFF3
  addu t6,t6,t1             # digit-only alternative 0xFFF5 / 0xFFF6
pc_alt:
  beq t4,zero,pc_st
  nop
  daddu t5,t6,zero
pc_st:
```

### VFR (L1)
```
VFR:
  ori at,zero,0xFFF0
  sltu at,a1,at             # a1 = frame (masked by the original andi in the hook's delay slot)
  beq at,zero,vf_v
  lw v1,0xC(a0)             # original: page +0x0C
  sll a1,a1,4
  lw v0,0xC(v1)             # original: frame table + frame * 16
  jr ra
  addu v0,v0,a1
vf_v:
  andi a1,a1,0xF            # virtual frames 0xFFF0..0xFFFF -> VTAB
  sll a1,a1,4
  lui v0,0xe
  ori v0,v0,0x8b60
  jr ra
  addu v0,v0,a1
```
### OFF, PXR, PXW, ALPHA, MASKPX, FXY, RAS, CLASS (L2 helpers)
```
OFF:                        # a0 = x, a1 = y (PSMT8 512 x 256, TBW 8) -> v0 = byte offset in the EE upload buffer (PSMCT32 256 x 128, DBW 4)
  lui t9,0x000F
  srl t0,a1,6
  sll t0,t0,2
  srl t1,a0,7
  addu t0,t0,t1             # page
  andi t1,a1,0x30
  srl t1,t1,1
  andi t2,a0,0x70
  srl t2,t2,4
  addu t1,t1,t2
  addu t1,t1,t9
  lbu t1,-29600(t1)      # PSMT8 block in page
  sll t0,t0,5
  addu t0,t0,t1
  sll t0,t0,8
  andi t1,a1,15
  sll t1,t1,4
  andi t2,a0,15
  addu t1,t1,t2
  addu t1,t1,t9
  lbu t1,-29472(t1)      # byte in block
  addu t0,t0,t1             # GS byte address
  srl t1,t0,8
  andi t2,t1,31             # PSMCT32 block
  srl t1,t1,5               # PSMCT32 page
  addu t2,t2,t9
  lbu t2,-29568(t2)    # (by << 3) | bx
  srl t3,t0,2
  andi t3,t3,63
  addu t3,t3,t9
  lbu t3,-29536(t3)    # (cy << 3) | cx
  andi v0,t1,3
  sll v0,v0,6
  andi v1,t2,7
  sll v1,v1,3
  addu v0,v0,v1
  andi v1,t3,7
  addu v0,v0,v1             # X
  srl v1,t1,2
  sll v1,v1,5
  srl t1,t2,3
  sll t1,t1,3
  addu v1,v1,t1
  srl t1,t3,3
  addu v1,v1,t1             # Y
  sll v1,v1,8
  addu v0,v0,v1
  sll v0,v0,2
  andi t0,t0,3
  jr ra
  addu v0,v0,t0
PXR:                        # a0 = x, a1 = y -> v0 = palette index (PIX from L34D)
  move t7,ra
  jal OFF
  nop
  lw t0,-30180(t9)
  addu t0,t0,v0
  jr t7
  lbu v0,0(t0)
PXW:                        # a0 = x, a1 = y, a2 = palette index
  move t7,ra
  jal OFF
  nop
  lw t0,-30180(t9)
  addu t0,t0,v0
  jr t7
  sb a2,0(t0)
ALPHA:                      # a0 = palette index -> v0 = alpha, v1 = red (CLUT stored CSM1-swizzled)
  andi t0,a0,0xE7
  andi t1,a0,0x08
  sll t1,t1,1
  or t0,t0,t1
  andi t1,a0,0x10
  srl t1,t1,1
  or t0,t0,t1
  sll t0,t0,2
  lui t9,0x000F
  lw t1,-30176(t9)
  addu t0,t0,t1
  lbu v1,0(t0)
  jr ra
  lbu v0,3(t0)
MASKPX:                     # a0 = x, a1 = y -> v0 = 1 for a glyph pixel (alpha >= 0x60, red >= 0x80)
  move t6,ra
  jal PXR
  nop
  jal ALPHA
  move a0,v0
  sltiu t0,v0,0x60
  bne t0,zero,mp_no
  sltiu t0,v1,0x80
  bne t0,zero,mp_no
  nop
  jr t6
  addiu v0,zero,1
mp_no:
  jr t6
  move v0,zero
FXY:                        # a0 = frame -> v0 = x0 = (int)(u0 * 512), v1 = y0 = (int)(v0 * 256)
  lui t9,0x000F
  lw t8,-30184(t9)
  sll a0,a0,4
  addu t8,t8,a0
  lwc1 f0,0(t8)
  lwc1 f1,4(t8)
  lui at,0x4400
  nop  #@RAWW 0x44811000 mtc1 at,f2 (512.0)
  lui at,0x4380
  nop  #@RAWW 0x44811800 mtc1 at,f3 (256.0)
  nop  #@RAWW 0x46020002 mul.s f0,f0,f2
  nop  #@RAWW 0x46030842 mul.s f1,f1,f3
  nop  #@RAWW 0x46000024 cvt.w.s f0,f0
  nop  #@RAWW 0x46000864 cvt.w.s f1,f1
  nop  #@RAWW 0x44020000 mfc1 v0,f0
  jr ra
  nop  #@RAWW 0x44030800 mfc1 v1,f1
RAS:                        # -> v0 = part_page0 raster (item 2 -> page -> texture -> raster), v1 = page; v0 = 0 if not valid
  lui v0,0x51
  lw t0,-0x32B4(v0)
  lui t2,0x0200
  beq t0,zero,rs_no
  sltu t1,t0,t2
  beq t1,zero,rs_no
  nop
  lw t0,0x1998(t0)          # item 2 (+0x189C + 2 * 0x78) +0x0C = page
  beq t0,zero,rs_no
  sltu t1,t0,t2
  beq t1,zero,rs_no
  nop
  lw t3,0x14(t0)            # texture
  beq t3,zero,rs_no
  sltu t1,t3,t2
  beq t1,zero,rs_no
  nop
  lw v0,0(t3)               # raster
  beq v0,zero,rs_no
  sltu t1,v0,t2
  beq t1,zero,rs_no
  nop
  jr ra
  move v1,t0
rs_no:
  jr ra
  move v0,zero
CLASS:                      # a0 = x (0..10), a1 = y (0..11) of the digit cell -> v0 = palette index (fill/highlight/outline/bevel/clear)
  lui t9,0x000F
  addiu t0,a1,1
  sll t1,t0,3
  sll t2,t0,2
  addu t0,t0,t1
  addu t0,t0,t2             # (y + 1) * 13
  addu t0,t0,a0
  addu t0,t0,t9
  lbu t1,-30047(t0)
  beq t1,zero,cl_out
  nop
  lbu t2,-30060(t0)
  lbu t3,-30034(t0)
  and t2,t2,t3
  beq t2,zero,cl_h
  nop
  jr ra
  lbu v0,-30160(t9)
cl_h:
  jr ra
  lbu v0,-30159(t9)
cl_out:
  lbu t1,-30061(t0)
  lbu t2,-30060(t0)
  or t1,t1,t2
  lbu t2,-30059(t0)
  or t1,t1,t2
  lbu t2,-30048(t0)
  or t1,t1,t2
  lbu t2,-30046(t0)
  or t1,t1,t2
  lbu t2,-30035(t0)
  or t1,t1,t2
  lbu t2,-30034(t0)
  or t1,t1,t2
  lbu t2,-30033(t0)
  or t1,t1,t2
  bne t1,zero,cl_edge
  nop
  jr ra
  lbu v0,-30156(t9)
cl_edge:
  addiu t1,zero,11
  beq a1,t1,cl_b
  nop
  jr ra
  lbu v0,-30158(t9)
cl_b:
  jr ra
  lbu v0,-30157(t9)
```
### ENSURE (L3)
```
ENSURE:                     # -> v0 = 1 when "3P"/"4P" are in the part_page0 texture (generates them once per texture copy)
  addiu sp,sp,-16
  sd ra,0(sp)
  jal RAS
  nop
  beq v0,zero,en_no
  lui t9,0x000F
  lw t0,4(v0)               # pixel buffer
  lw t1,-30192(t9)
  bne t0,t1,en_gen
  lw t1,-30188(t9)
  beq t1,zero,en_no         # this buffer failed the checks: keep the coloured "2P"
  nop
  lw a0,-30168(t9)        # marker: first P column of "3P" equals the 2P source
  lw a1,-30164(t9)
  addiu a0,a0,9
  jal PXR
  addiu a1,a1,1
  sd v0,8(sp)
  addiu a0,zero,101
  jal PXR
  addiu a1,zero,237
  ld t0,8(sp)
  beq v0,t0,en_ok
  nop
en_gen:
  jal GEN
  nop
  lui t9,0x000F
  lw t1,-30188(t9)
  beq t1,zero,en_no
  nop
en_ok:
  ld ra,0(sp)
  addiu v0,zero,1
  jr ra
  addiu sp,sp,16
en_no:
  ld ra,0(sp)
  move v0,zero
  jr ra
  addiu sp,sp,16
```
### GEN (L2)
```
GEN:                        # builds "3P", "4P", "3", "4" in free texels of part_page0 from the game's own "2P" art and font
  addiu sp,sp,-96
  sd ra,0(sp)
  sd s0,8(sp)
  sd s1,16(sp)
  sd s2,24(sp)
  sd s3,32(sp)
  sd s4,40(sp)
  sd s5,48(sp)
  sd s6,56(sp)
  sd s7,64(sp)
  lui s7,0x000F
  sw zero,-30188(s7)
  jal RAS
  nop
  beq v0,zero,gn_ret
  move s0,v0                # raster
  move s1,v1                # page
  lw t0,4(s0)               # pixels (PSMT8 data uploaded as PSMCT32)
  sw t0,-30192(s7)
  sw t0,-30180(s7)
  lw t1,8(s0)               # palette (CSM1)
  sw t1,-30176(s7)
  beq t0,zero,gn_ret
  nop
  beq t1,zero,gn_ret
  nop
  lw t2,0xC(s0)
  addiu t3,zero,512
  bne t2,t3,gn_ret
  lw t2,0x10(s0)
  addiu t3,zero,256
  bne t2,t3,gn_ret
  lw t2,0x14(s0)
  addiu t3,zero,8
  bne t2,t3,gn_ret
  lw t0,0xC(s1)             # page resource
  beq t0,zero,gn_ret
  nop
  lw t1,0xC(t0)             # frame table
  sw t1,-30184(s7)
  lw t2,4(t0)               # frame count
  lw t3,8(t0)               # font base frame (frame = base + character)
  sw t3,-30172(s7)
  sltiu t4,t2,0x16A
  bne t4,zero,gn_ret
  addiu t4,t3,0x35
  sltu t4,t2,t4
  bne t4,zero,gn_ret
  nop
  jal FXY
  addiu a0,zero,0x169       # "2P"
  sw v0,-30168(s7)
  sw v1,-30164(s7)
  move s2,v0
  move s3,v1
  jal FXY
  addiu a0,zero,0x15F       # "2" (digit-only alternative)
  move s4,v0
  move s0,zero              # texels that differ (the two copies differ in a few palette entries)
  bne v1,s3,gn_ret
  move s5,zero
gv_y:                       # the "2" of "2P" must match the standalone "2" (9 x 12 texels): the P starts 9 texels in
  move s6,zero
gv_x:
  addu a0,s2,s6
  jal PXR
  addu a1,s3,s5
  sd v0,72(sp)
  addu a0,s4,s6
  jal PXR
  addu a1,s3,s5
  ld t0,72(sp)
  beq v0,t0,gv_same
  addiu s6,s6,1
  addiu s0,s0,1
gv_same:
  sltiu t0,s6,9
  bne t0,zero,gv_x
  nop
  addiu s5,s5,1
  sltiu t0,s5,12
  bne t0,zero,gv_y
  nop
  sltiu t0,s0,13            # at most 12 of 108 texels differ (4 in SLUS-21215)
  beq t0,zero,gn_ret
  nop
  addiu a0,s4,5             # palette indices of the "2" art: fill, highlight, outline, bevel, clear
  jal PXR
  addiu a1,s3,2
  sb v0,-30160(s7)
  addiu a0,s4,2
  jal PXR
  addiu a1,s3,10
  sb v0,-30159(s7)
  addiu a0,s4,8
  jal PXR
  addiu a1,s3,3
  sb v0,-30158(s7)
  addiu a0,s4,3
  jal PXR
  addiu a1,s3,11
  sb v0,-30157(s7)
  addiu a0,s4,-1
  jal PXR
  move a1,s3
  sb v0,-30156(s7)
  jal ALPHA
  move a0,v0
  bne v0,zero,gn_ret        # "clear" must be transparent
  addiu s5,zero,234
gd_y:                       # target texels must be unused (transparent)
  addiu s6,zero,88
gd_x:
  move a0,s6
  jal PXR
  move a1,s5
  jal ALPHA
  move a0,v0
  bne v0,zero,gn_ret
  addiu s6,s6,1
  sltiu t0,s6,162
  bne t0,zero,gd_x
  nop
  addiu s5,s5,1
  sltiu t0,s5,250
  bne t0,zero,gd_y
  nop
  addiu s0,zero,3           # digit 3, then 4
gd_digit:
  lw a0,-30172(s7)
  addu a0,a0,s0
  jal FXY
  addiu a0,a0,0x30          # font frame of '3' / '4'
  move s1,v0
  move s2,v1
  move s5,zero
gt_y:                       # first glyph row of the 9 x 18 cell
  move s6,zero
gt_x:
  addu a0,s1,s6
  jal MASKPX
  addu a1,s2,s5
  bne v0,zero,gt_found
  addiu s6,s6,1
  sltiu t0,s6,9
  bne t0,zero,gt_x
  nop
  addiu s5,s5,1
  sltiu t0,s5,18
  bne t0,zero,gt_y
  nop
  beq zero,zero,gn_ret
  nop
gt_found:
  addu s2,s2,s5
  move s5,zero
gm_y:                       # mask of 10 glyph rows x 9 columns
  move s6,zero
gm_x:
  addu a0,s1,s6
  jal MASKPX
  addu a1,s2,s5
  sll t0,s5,3
  addu t0,t0,s5
  addu t0,t0,s6
  addu t0,t0,s7
  sb v0,-30144(t0)
  addiu s6,s6,1
  sltiu t0,s6,9
  bne t0,zero,gm_x
  nop
  addiu s5,s5,1
  sltiu t0,s5,10
  bne t0,zero,gm_y
  nop
  addiu s3,zero,-1          # first used column
  addiu s4,zero,-1          # last used column
  move s6,zero
gc_x:
  move s5,zero
  move t1,zero
gc_y:
  sll t0,s5,3
  addu t0,t0,s5
  addu t0,t0,s6
  addu t0,t0,s7
  lbu t0,-30144(t0)
  or t1,t1,t0
  addiu s5,s5,1
  sltiu t0,s5,10
  bne t0,zero,gc_y
  nop
  beq t1,zero,gc_next
  nop
  move s4,s6
  bgez s3,gc_next
  nop
  move s3,s6
gc_next:
  addiu s6,s6,1
  sltiu t0,s6,9
  bne t0,zero,gc_x
  nop
  bltz s3,gn_ret
  move t0,zero
gf_clr:
  addu t1,t0,s7
  sb zero,-30048(t1)
  addiu t0,t0,1
  sltiu t1,t0,182
  bne t1,zero,gf_clr
  nop
  addiu t5,zero,9
  subu t5,t5,s4             # cell column = mask column + 9 - last (digit right-aligned against the P)
  move s5,zero
gk_y:
  move s6,s3
gk_x:
  sll t0,s5,3
  addu t0,t0,s5
  addu t0,t0,s6
  addu t0,t0,s7
  lbu t2,-30144(t0)
  addiu t3,s5,2             # fill map row = glyph row + 1 (cell) + 1 (border)
  sll t4,t3,3
  sll t6,t3,2
  addu t4,t4,t6
  addu t4,t4,t3             # * 13
  addu t4,t4,s6
  addu t4,t4,t5
  addu t4,t4,s7
  sb t2,-30047(t4)
  addiu s6,s6,1
  slt t0,s4,s6
  beq t0,zero,gk_x
  nop
  addiu s5,s5,1
  sltiu t0,s5,10
  bne t0,zero,gk_y
  nop
  addiu t0,zero,3
  addiu s1,zero,113
  bne s0,t0,gd_w
  addiu s2,zero,149
  addiu s1,zero,90
  addiu s2,zero,136
gd_w:
  move s5,zero
gw_y:                       # digit cell 11 x 12 -> "dP" label and digit-only frame
  move s6,zero
gw_x:
  move a0,s6
  jal CLASS
  move a1,s5
  sd v0,72(sp)
  addu a0,s1,s6
  addiu a1,s5,236
  jal PXW
  move a2,v0
  ld a2,72(sp)
  addu a0,s2,s6
  jal PXW
  addiu a1,s5,236
  addiu s6,s6,1
  sltiu t0,s6,11
  bne t0,zero,gw_x
  nop
  addiu s5,s5,1
  sltiu t0,s5,12
  bne t0,zero,gw_y
  nop
  move s5,zero
gp_y:                       # the P of "2P" (10 x 12 texels) right of the digit
  move s6,zero
gp_x:
  lw a0,-30168(s7)
  lw a1,-30164(s7)
  addu a0,a0,s6
  addiu a0,a0,9
  jal PXR
  addu a1,a1,s5
  addu a0,s1,s6
  addiu a0,a0,11
  addiu a1,s5,236
  jal PXW
  move a2,v0
  addiu s6,s6,1
  sltiu t0,s6,10
  bne t0,zero,gp_x
  nop
  addiu s5,s5,1
  sltiu t0,s5,12
  bne t0,zero,gp_y
  nop
  addiu s0,s0,1
  sltiu t0,s0,5
  bne t0,zero,gd_digit
  nop
  addiu t0,zero,1
  sw t0,-30188(s7)
gn_ret:
  ld ra,0(sp)
  ld s0,8(sp)
  ld s1,16(sp)
  ld s2,24(sp)
  ld s3,32(sp)
  ld s4,40(sp)
  ld s5,48(sp)
  ld s6,56(sp)
  ld s7,64(sp)
  jr ra
  addiu sp,sp,96
```
### LBLCHK (L5)
```
LBLCHK:                     # L5: radar update FUN_001C5210 keeps label frames upright (rotation 0); a0 = widget frame
  addiu at,zero,0x15F       # the replaced test: frame == 0x15F
  beq a0,at,lc_lab
  ori at,zero,0xFFF0
  sltu at,a0,at
  bne at,zero,lc_no         # frames 0xFFF0-0xFFFF ("3P", "4P", "3", "4") are labels too
  nop
lc_lab:
  j 0x001C5F10              # label: rotation 0
  nop
lc_no:
  j 0x001C5F34              # other icons (arrows): rotation by heading, as before; v0 = widget (delay slot of the hook)
  nop
```

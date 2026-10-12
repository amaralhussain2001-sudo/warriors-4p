# M6 camera parity camB: M6 cp4 rooftop chase and M9 cp4 cage cameras for players 3-4 (LUACH rows, 2026-10-12)

**Status (coordinator, 2026-10-12 21:40):** merged into mod/ (LUACH rows 13-15). Placeholders F-CAM-camB-1..12 are summarized in **F-0226**. The engine behaviour 'a blend-0 switch does not replace a camera that is still blending in' was the `[4p]` relocation bug **F-0223 (LUIFIX)** and is fixed.

Agent camB (coordinator brief `local/m6/cam/BRIEF.md`). Numbering in this note: players, views and rails 1-4 =
game player / view index 0-3 (probe output and code use the index). Audit rows: `docs/research/m6_camera_parity.md` section 3 (M6 and
M9), priority items 4 and 8. Build: The Warriors SLUS-21215 v1.03 (`local/disc/SLUS_212.15`, read-only), fork build
w4p-m6-3 (emulator not touched), patch set = the current `mod/` (copied by `tools/lua_rows.py`) + 3 camB rows. Function
and structure names are OUR labels (the ELF is stripped); addresses static unless marked dynamic. Labels: VERIFIED
(pointer), HYPOTHESIS, BLOCKED, FAILED TEST. Every test: SINGLE-PC, one instance (sandboxes 21 and 22), scripted bots
(players 3-4 joined through the game's own UpdateJoin = what W4P X11 does), no impairment, MTVU off, no human play.
`mod/` and `mod/w4p_m1.pnach` were NOT changed (the coordinator integrates the rows).

## Plain-English summary
- **M6 "Writer's Block", rooftop chase (checkpoint 4).** Players 1-2 see the chase from the side (a "rail" camera that
  slides along the street). Players 3-4 used to keep their normal close camera behind their own back for the whole chase.
  **Now** every player 3/4 gets the same side-scrolling camera on his own screen, also when he joins in the middle of
  the chase (a check every 250 ms gives it to him), and his camera changes framing at the same places as players 1-2's
  (wider over the gaps, higher on the "top" stretches). Example (run cb6rows): players 3-4 joined at poll 5402; at the next
  snapshot (poll 6000) all four screens showed the side rail, each following its own player (rail targets = players
  1, 2, 3, 4).
  Screenshot `local/m2/cb6rows/t0750_p6991.png`: the four quarters look alike.
- **M6 hazard fixed (reachable by walking).** The "top" camera boxes are noticed for every player. Before, a player 3/4
  walking into one changed **every** player's chase camera (index -1 = all rails). Example (run cb6base3): player 3's
  call changed the framing value k1 from 4 to 20 on rails 1, 2, 3 and 4. Now only player 3's own rail changes (cb6rows:
  rail 3 k1 4 -> 20, rails 1, 2, 4 unchanged).
- **M6 second hazard (leaving a stunt-camera box): smaller than the audit feared.** The audit expected "player 1's rail
  object moved to view 3". At runtime the game's own join already builds a rail for view 3/4 as a copy of player 1's
  (cb6base2), so the original only switched the player 3/4 to that copy (seen naturally: player 4 teleported out of a
  stunt box, view 4 went from his follow camera to the rail, cb6base2 poll 8000). camB now does it deliberately: his
  own rail if camB gave him one, otherwise his follow camera - never a rail he does not have.
- **M9 "Payin' The Cost", cage (checkpoint 4).** The audit said players 3-4 are "outside the cage by script". At
  runtime they are not: the script deletes Vermin and Snow (the companions players 3-4 would take) when the cage fight
  starts (`C4.CleanupScene3`, 09166:504-516), and players 3-4 who join after that are created as Warriors **next to
  player 1 inside the cage** (cb9base2, cb9base3: player 3 at (47.2, 51.4), player 4 at (53.5, 54.3), player 1 at
  (50.5, 52.3); the joins tried before the delete did not succeed in these runs). A player 3/4 who held Vermin/Snow
  before the delete is released by X1 and re-joins the same way (F-0180; not re-tested here). So the
  right equivalent is the same cage camera as players 1-2. **Now** players 3-4 get the cage rail of the current stage
  (first stage x = 32 line, second stage x = 53.75 line), their own copies of the zoom cameras (hammer lock, second van)
  and their own rail back when they leave a zoom box. Example: before (cb9base3 `t0524_p7627.png`) "two good screens
  and two close-up screens"; after (cb9rows `t0889_p8519.png`) all four quarters show the cage from the same angle.
- **M9 hazard: player 3/4 leaving the second-van box.** Original: switched him to his rail copy (harmless to players
  1-2 because the join already made that copy, cb9base3). camB: his own stage rail, or his follow camera if he has none.
- **M9 extra harm found and fixed:** the player-2 join callback (`C4.Player2Start`) also runs when a player 3/4 leaves
  (game path "continue in 1-player mode"); it then swaps players 1-2's zoom cameras back to the 1-player versions
  (cb9base3: 2P version before, 1P after = R 10). camB runs it only for player 2 (cb9rows: R 11 = unchanged).
- **M9 near-plane boxes:** a player 3/4 in the clipping box changed **player 1's** rail near plane (the script uses the
  rail handle of player 1): original R 11 = one clipping call on player 1's rail (cb9base4); camB R 0 (cb9rows2).
- **Players 1-2 are unchanged**: every wrapper calls the original unchanged for players 1-2; the 2-player runs with the
  rows (cb6two, cb9two) show the same cameras and values as the baseline runs (rails, framing, zoom camera objects).
- **Not possible / not done:** the M6 jump-warning button prompt for players 3-4 (the HUD prompt object exists only for
  HUD 1-2, D24 finding `m6_chase4p.md` 1.4); M9 `C4.LockBroken1` (final scene) needs nothing (one shared view).
- **One unexplained event:** one M9 run with the rows (cb9rows2) logged 50 TLB misses in a 3.4 s burst after a
  test call of the zoom-out handler for player 3; the game kept running. The same sequence repeated (cb9tlb, rows) and
  without camB (cb9tlbb) gave 0. Cause not found (section 5) - reported as a FAILED TEST signal, not hidden.
- **Engine fact found on the way (VERIFIED runtime):** a camera switch with blend time 0 does NOT replace a view's
  camera while that view shows a blended camera (cb6base3: `CameraMakeActive(FixCam[2], 0, nil, player)` left view 1 on
  its blended rail; the same call on player 3's follow camera worked). So in the original game the blend-0 stunt cameras
  of the chase (and, on our test path to the gallery, the "follow camera again" at checkpoint 5) do not take effect for
  players 1-2 after their 0.5 s rail blend; camB keeps the same blend times for players 3-4, so they behave identically (parity by construction).

## Negative results and open points (read these first)
1. **FAILED TEST (method), cb6base / cb9base: standing bots are killed within seconds** (M6: GAME OVER "You got wrecked"
   about 140 polls after the cp4 load; M9: after the cage starts). All later runs set god mode for every player as soon
   as the chapter file is in the LUACH log (`cam_camB_probe.god_wait`, test only).
2. **M6 cp4 by level jump: the intro auto-run does not happen** (players 1-2 stay at x -261..-269), but `ch4.StartRail`
   fires anyway at the chapter start (players 1-2 are inside the type-2 `vbStartRail` from the spawn; cb6rows snap 5000:
   camB's StartRail hook had already run). The chase itself (running, jumping over gaps) was not played by the bots; the
   framing boxes were exercised by teleporting players 3-4 next to player 1 and by players 3-4 joining inside a box.
3. **Stunt cameras (M6 `EnterFixCam`) for players 3-4 only run when player 1 is down** (the original's partner rule for
   any non-player-2 human); tested with `HuIsAlive` stubbed (test only). The blend-0 stunt boxes do not show for anyone
   after the blended rail (engine fact above, VERIFIED for player 1 in cb6base3); the blend-1 boxes 11/14 were used
   for the positive test (cb6rows2).
4. **M6 checkpoint 5 (gallery):** with the direct `ch4.EnterGallery` test call, players 1-2 keep their chase rails in
   the gallery in the original too (cb6base3: views 1-2 still blended rails at cp5, the cp5 `CameraMakeActive(MainCam,
   0, ...)` has no effect, engine fact above). camB makes the same follow-camera call for players 3-4 at the chase end
   (`ch4.KillHandlers`), with the same (no) effect. Whether a real run to the gallery ends differently is HYPOTHESIS.
5. **Players 3-4 join where their AI character stands.** In M6 that was 220-310 units ahead of player 1 (cb6rows: x
   -19.9 / -13.6; cb6diag: x -44 / -38); the side rail there can look at a wall (`cb6rows/t0591_p6064.png`, view 3) -
   the same rail camera players 1-2 would have at that spot. After the teleport next to player 1 all four views match.
6. **Region size:** the three rows (names + sources) use 0x000EA400-0x000EAFE7 = 3048 of the 3072 bytes of the region; the readable sources
   (`local/m6/cam/camB/src/*.lua`) are compacted by `local/m6/cam/camB/minify.py` (spaces next to punctuation removed;
   no `--` can appear). Any growth needs a bigger region.
7. **CameraCreateLocked is wrapped in every level** (helpers row): it records the arguments of every locked camera
   (one Lua table per camera) so camB can build copies; the camera itself is created exactly as before. Memory cost:
   one small table per locked camera per level (not measured).
8. Not exercised: real chase play to the gallery, mission failure/restart with the rows (the rows run again at every
   level load: m6_x4_x6.md 2.3), sessions with 4 PCs, player 3/4 leaving and re-joining mid-chase (the tick forgets a
   player who is no longer a player and gives the re-joined one his rail again - code path tested only by clearing
   the owner in cb6rows2/cb9rows2).

## 1. Static and runtime facts that decide the fixes
1. **The join builds rails for views 3-4 (VERIFIED code + runtime).** UpdateJoin `FUN_0041A460` -> for a joiner not in
   the tracked list: `FUN_001222B0` (add) + `FUN_0011EAF0(index)` (all_07.c:10826-10829): follow/rail/type-11 camera of
   the new view are created and the rail is copied from rail[0] with `FUN_0013B358` (points, offsets, fov, framing);
   then the new view starts on its follow camera (disassembly 0x0011ECCC-0x0011ED00: the switch result is overwritten
   by follow[i]). Runtime cb6base2 snap 6505: rails of views 3/4 exist with player 1's MainRail values (78 / 5.5 / 4 /
   -8 / 6 / 2) and 2 points; views 3/4 show their follow cameras. So the audit's "player 1's rail object moved to view
   3" needs a joiner already in the tracked list (not seen). RAILTGT makes those rails track their own player (cb6rows
   tgtP 3/4).
2. **Rail camera fields (VERIFIED runtime cb6base2 + decompile `FUN_0011D228`)**: values of `CamModifyRail(k, v, t, i)`
   sit at rail+0x374 (k2 fov), +0x378 (k0), +0x37C (k1), +0x380 (k3), +0x384 (k4), +0x398 (k9); points at +0x1E0 + 16*n
   (`FUN_0013B780`); target human object at +0x340. `CamSetupRail` clears the points (`FUN_0013B2B8` -> `FUN_0013B770`)
   and adds the human to the tracked list (`FUN_001222B0`, no duplicates for players).
3. **Blend cameras (VERIFIED runtime)**: `CameraMakeActive` with a blend time puts a per-view blend object (vtable
   0x00537610) into both view arrays (0x000F0800 / 0x000F0810 + 4*view); it keeps showing its target (+0x214) after the
   blend. A later blend-0 switch does not replace it (cb6base3 `m6_ma_p1_0`: view 1 unchanged), a blended switch
   retargets it (cb6base3 `m6_ma_p3_01`, cb9rows `m9_zout_p3`).
4. **Volume boxes:** `IsInsideBox(box, h)` = binding 0x0037AFB8 -> `FUN_00413198` -> geometric test `FUN_004129C0` /
   `FUN_00412A18` on the human's position: works for any human (VERIFIED code; runtime cb6diag: the poll found players
   3-4 in `vSideRail[2]` and applied its framing, fov 65 / k0 8 / k1 2 / k3 2 / k4 0). Box types (07856:1825-1959,
   09117:1869-1907): M6 `vFixCam[*]` 0, `vTopRail[11..15,19]` 0, `vTopRail[2]` 2, `vSideRail`, `vMainRail`, `vBigRail`,
   `vbJumpWarn`, `vbStartRail`, `vbEnterGallery` 2; M9 `vHammerBox`, `vSecondVanBox`, `vClipBox` 0.
5. **Chunk names VERIFIED in the LUACH log:** "level3_chase.lua" (cb6base snap 6000) and "level86_chapter4.lua"
   (cb9base snap 6000).
6. **Lua library in the game state (runtime cb6diag `luafn`):** `floor`, `format`, `strbyte`, `mod`, `strlen` exist;
   `true = 1`, `false = nil` (04106 main); vararg functions (`...`/`arg`) and `call(f, t)` used by the helpers row.

## 2. The rows (`local/m6/cam/camB/rows/`, readable sources in `local/m6/cam/camB/src/`)
| Row | Chunk | Size | What |
|---|---|---|---|
| camBh | "global.lua" (second row after the coordinator's helpers) | 917 | `CameraCreateLocked` records its arguments (`W4BK`); `W4BCP(c, v)` = per-view copy of a locked camera; `W4BW(f)` handler wrapper (players 1-2: original; player 3/4 at index v: original with `player2 = a1`, `CamModifyRail` index 1/-1/nil -> v (0 dropped), `CameraMakeActive` of the mission rail -> his own camB rail or his follow camera, of a recorded locked camera -> his copy); `W4BT(g)` gives a camB camera to each player 3/4 who has none and forgets one who left |
| m6r | "level3_chase.lua" | 1070 | `EnterTopRail`, `ExitFixCam`, `EnterFixCam` through `W4BW`; after `ch4.StartRail` a 250 ms tick gives each player 3/4 the SetupRailCam rail on index v (same points, fov 78), MainRail framing on v, made active with blend 0.5 (as StartRail for player2), and polls `vSideRail` / `vMainRail` / `vBigRail` / `vTopRail` with `IsInsideBox` (entering one runs the original handler through `W4BW`); `ch4.KillHandlers` also makes the follow camera active for players 3-4 and stops the poll; the tick stops when `ch4` is gone |
| m9r | "level86_chapter4.lua" | 981 | `ZoomInRail`, `ZoomOutRail`, `ZoomVan2`, `ZoomRail2` through `W4BW`; `SetNearPlaneIn/Out` through `W4P_G34`; `C4.Player2Start` only for player 2 (`hSwan`/`player2`); after `C4.StartFirstRailCam` / `C4.StartRailCam` a 500 ms tick gives each player 3/4 the stage rail on index v (stage 1: `CamModifyRail(8, -30)`, points (32, 75/45, 8.5); stage 2: `(8, 0)`, points (53.75, 45/75, 2.5)), blend 0 as for player2, plus his `SecondVanCam2` copy if he is in `vSecondVanBox` at stage 2 |

Build: `python -I tools/lua_rows.py build --base mod --region 0x000EA400:0x000EB000 --work local/m6/cam/camB --out
local/m6/cam/camB/test.pnach --title "camB camera rows" local/m6/cam/camB/rows/camb_helpers.lua
local/m6/cam/camB/rows/m6r.lua local/m6/cam/camB/rows/m9r.lua` -> rows at 0x000EA440-0x000EAFE7, "6 problems" (the known
`[4p hud A]`/`[4p hud B1]` alternatives). Tested pnach: `local/m6/cam/camB/test_r1.pnach` (same rows; mod/ of 17:30).

## 3. Per-fix table (F-CAM-camB-n = draft finding IDs)
| # | Mission / chunk | Function (script line) | Change | Test (run, probe) | Result | Label |
|---|---|---|---|---|---|---|
| F-CAM-camB-1 | M6 cp4 "level3_chase.lua" | `ch4.StartRail` (08022:293-320, type-2 `vbStartRail`) + 250 ms tick | each player 3/4 (also later joiners) gets the SetupRailCam rail on his index, MainRail framing, made active (blend 0.5) | cb6rows snap 6000 / 6300 / 6800; screenshot `t0750_p6991` | before (cb6base2): views 3-4 follow cameras the whole chase. after: all 4 views blended rails, rail targets players 1/2/3/4, framing 78 / 5.5 / 4 / -8 / 6 / 2 on all four; four quarters alike after the teleport | **VERIFIED** (SINGLE-PC, bots) |
| F-CAM-camB-2 | M6 cp4 | type-2 framing boxes `EnterSideRail` / `EnterMainRail` / `EnterBigCam` (08022:450-471, 573-603, 625-677) + `vTopRail` | polled for players 3-4 with `IsInsideBox`; entry runs the original through `W4BW` on his index | cb6diag snap 5900 | players 3-4 joined inside `vSideRail[2]`: rails 3-4 got its framing (fov 65, k0 8, k1 2, k3 2, k4 0), rails 1-2 kept MainRail | **VERIFIED** |
| F-CAM-camB-3 | M6 cp4 | `ch4.EnterTopRail` (08022:604-624, type 0) **hazard** | `W4BW`: index -1 -> his index | cb6base3 `m6_top_orig_p3` vs cb6rows `m6_top_p3` | original for player 3: k1 4 -> 20 on rails 1, 2, 3, 4 (players 1-2's chase cameras changed). camB: only rail 3 (k1 20, k3 0, k4 0); rails 1, 2, 4 unchanged. Player 1's own call still changes only rail 1 (cb6rows2 `m6_top_p1`, cb6two) | **VERIFIED** |
| F-CAM-camB-4 | M6 cp4 | `ch4.ExitFixCam` (08022:538-572, type 0) **hazard** | `W4BW`: his own camB rail, else his follow camera | cb6rows2 `m6_fixexit11_p3`, `m6_exit_norail_p3`; cb6base2 snap 8000 | with a camB rail: view 3 back to rail 3; without (owner cleared for the test): view 3 -> follow 3 (0xd15c00), never rail 1; the tick then gave rail 3 again. Original: the join-made rail copy (cb6base2: player 4 teleported out of `vFixCam[13]` -> view 4 to his rail copy, views 1-2 unchanged) | **VERIFIED**; the audit's "rail 1 moved" variant not observed (rails 3-4 exist from the join, section 1.1) |
| F-CAM-camB-5 | M6 cp4 | `ch4.EnterFixCam` (08022:472-519, type 0) | `W4BW`: his own copy of the stunt camera (no MakeActive of FixCam objects players 1-2 use) | cb6rows2 `m6_fix11_p3` (HuIsAlive / HuSetSlowMo stubbed) | view 3 shows the copy 0xd17800 (FixCam[11] itself is 0xc52800); views 1, 2, 4 unchanged | **VERIFIED** (stubbed condition; blend-0 boxes show for nobody, section 1.3) |
| F-CAM-camB-6 | M6 cp4 | `ch4.KillHandlers` (chase end, 08022:717) | follow camera call for players 3-4 (the same call cp5 makes for players 1-2) and poll off | cb6rows / cb6rows2 / cb6two `m6_end` | cp5 reached; all views keep the blended chase rails, same as players 1-2 in the original (cb6base3); camB owners cleared | **VERIFIED** (parity incl. the engine's no-effect) |
| F-CAM-camB-7 | M9 cp4 "level86_chapter4.lua" | `C4.StartFirstRailCam` / `C4.StartRailCam` (09166:249-268, 279-323) + 500 ms tick | stage rail on his index (stage 1: points (32, 75/45, 8.5), `CamModifyRail(8, -30)`; stage 2: (53.75, 45/75, 2.5), `(8, 0)`), blend 0 as for player2; stage 2 also his SecondVanCam copy if inside | cb9rows snap 7300 / 7800 / 9100, cb9rows2 snap 7700 | before (cb9base3): views 3-4 follow in both stages. after: rails 3-4 target players 3-4 with the stage's points (stage 2 points on all four rails); screenshot `cb9rows/t0889_p8519.png` | **VERIFIED** |
| F-CAM-camB-8 | M9 cp4 | `C4.ZoomInRail` / `ZoomOutRail` (09166:343-372, `vHammerBox` type 0) | `W4BW` as player2's branch: his copy of `Cameras.LockRailCam2`; rail back | cb9rows2 `m9_zin_p3` + `m9_ident`, `m9_zout_p3`; cb9rows | view 3 shows the copy 0xd26400 (LockRailCam2 = 0xc54800); back to rail 3 (blend 0.75); views 1-2 unchanged. Original: no camera change for player 3 (cb9base3) | **VERIFIED** (see the TLB note, section 5) |
| F-CAM-camB-9 | M9 cp4 | `C4.ZoomVan2` (09166:397-407, `vSecondVanBox` enter) | `W4BW`: his copy of `SecondVanCam2` | cb9rows2 `m9_van_p3` + `m9_ident` | view 3 shows the copy 0xd16400 (SecondVanCam2 = 0xd2ec00) | **VERIFIED** |
| F-CAM-camB-10 | M9 cp4 | `C4.ZoomRail2` (09166:273-278, leave) **hazard** | `W4BW`: own camB rail, else follow | cb9base3 `m9_zr2_orig_p3`; cb9rows2 `m9_zr2_norail_p3`, cb9rows `m9_zr2s_p3` | original: view 3 to his rail copy (views 1-2 unchanged); camB with rail: rail 3; without: follow 3 (0xce2000), not railCam | **VERIFIED** |
| F-CAM-camB-11 | M9 cp4 | `C4.Player2Start` (09166:187-200; player-2 join callback, also run on leaves) | only for `hSwan`/`player2` | cb9base3 vs cb9rows `m9_p2s_p3` | original `Player2Start(player 3, false)`: players 1-2's zoom cameras swapped back to the 1P versions (R 10). camB: unchanged (R 11) | **VERIFIED** (direct call; the game calls it on a player 3/4 leave through "continue in 1-player mode", `m6_missions.md` 1.1) |
| F-CAM-camB-12 | M9 cp4 | `SetNearPlaneIn/Out` (09166:307-308, `vClipBox` type 0) | `W4P_G34` (players 3-4 ignored) | cb9base4 vs cb9rows2 `m9_clip_p3` | original: 1 `CameraSetClipping` on player 1's `railCam` (R 11); camB: none (R 0). Players 3-4's own rails keep the default near plane (player 2's rail is never clipped either) | **VERIFIED** |
| - | M6 cp4 | `ch4.JumpWarnOn` (08022:755-774, type 2) HUD prompt | not changed | static | `HUDTurnOnActionCycleAnim` has objects for HUD 1-2 only (`m6_chase4p.md` 1.4) | BLOCKED (engine) |
| - | M9 cp4 | `C4.LockBroken1` (09166:565-591) | not changed | static | splits the screen off (`CamEnable(3, false)`) and plays the final scene: one shared view | not needed |

## 4. Tests (SINGLE-PC, one instance each, bots, no impairment, MTVU off)
Command (`local/m6/cam/camB/run.sh <tag> <inst> <cp> <entry> <pnach> <seconds> <probes...>`): `python -I tests/m2/nav_probe.py
<tag> tests/m2/nav/boot_to_m1_2p.txt --inst <21|22> --players 4 --script2 tests/m2/nav/p2_join.txt --script3
tests/m2/nav/empty.txt --script4 tests/m2/nav/empty.txt --groups "<the brief's 13 groups>" --ini
EmuCore/Speedhacks/vuThread=false --callat "3999:0041ABC0:4,4009:00160D78:<entry>" --patch <pnach> --probe
cam_camB_probe:<f>:<poll> ... --seconds <s> --every 4`. Entries: M6 0x01FD9C00, M9 0x01FD9D8C (checkpoint 4 both).
`base.pnach` = mod/ without camB rows, `test_r1.pnach` = with them (both from `tools/lua_rows.py`). Probes:
`tests/m6/cam_camB_probe.py`. Evidence: `evidence/M6/camB_<tag>_probes.json`; screenshots `local/m2/<tag>/`; consoles and
emulogs `local/m6/cam/camB/runs/`. Players 3-4 joined through `x6fix_probe.join34` (the game's UpdateJoin); god mode
test only. The host was loaded by other agents' emulators (5-20 fps), so runs reached only polls 8000-18000.

| Run | Inst | Level | pnach | Players 3-4 joined | Main probes -> result | TLB |
|---|---|---|---|---|---|---|
| cb6base | 21 | M6 cp4 | base | - | GAME OVER at ~5050 (bots wrecked, no god mode yet); LUACH log "level3_chase.lua" | 0 |
| cb9base | 22 | M9 cp4 | base | - | GAME OVER ~8000; LUACH log "level86_chapter4.lua"; cage stage at ~6700 | 0 |
| cb6base2 | 21 | M6 cp4 | base | 6003 | before: views 3-4 follow, rails 3-4 = join copies; natural ExitFixCam of player 4 -> his rail copy | 0 |
| cb9base2 | 22 | M9 cp4 | base | 7100 / 7400 | before: views 3-4 follow; players 3-4 spawned in the cage next to player 1 | 0 |
| cb6rows | 21 | M6 cp4 | test_r1 | 5402 | F-1 rails 1-4, four alike (t0750_p6991); F-3; first EnterFixCam test used a blend-0 box (no visible change, section 1.3) | 0 |
| cb9rows | 22 | M9 cp4 | test_r1 | 7001 / 7201 | F-7 stage 1 + 2 rails; F-8 zoom in/out; F-11 R 11; F-9 / F-10 | 0 |
| cb6diag | 21 | M6 cp4 | test_r1 | 5303 | F-2 box poll framing; EnterFixCam trace: no Lua error, 1 copy, 1 CameraMakeActive; Lua library check | 0 |
| cb9base3 | 22 | M9 cp4 | base | 7100 / 7301 | originals: ZoomInRail / ZoomVan2 no camera for player 3, Player2Start R 10, ZoomRail2 -> rail copy | 0 |
| cb6base3 | 21 | M6 cp4 | base | 5300 | original EnterTopRail -> all 4 rails changed; blend-0 switch ignored on a blended view (player 1); cp5 keeps rails | 0 |
| cb9two | 22 | M9 cp4 | test_r1 | none | 2-player regression: rails / LockRailCam (original object) / rail back / stage 2 as in the baselines | 0 |
| cb6rows2 | 21 | M6 cp4 | test_r1 | 5303 | F-5 copy 0xd17800; F-4 own rail / follow fallback + tick re-give; player 1's EnterTopRail only rail 1; cp5 | 0 |
| cb9rows2 | 22 | M9 cp4 | test_r1 | 7101 / 7301 | F-8 copy identity, F-12 R 0, F-9 copy identity, F-10 follow fallback | **50** (section 5) |
| cb6two | 21 | M6 cp4 | test_r1 | none | 2-player regression: same rails / framing as cb6base3; player 1's EnterTopRail only rail 1; cp5 | 0 |
| cb9base4 | 22 | M9 cp4 | base | 7108 / 7314 | F-12 original R 11; original ZoomInRail no camera | 0 |
| cb9tlb | 22 | M9 cp4 | test_r1 | 7106 / 7303 | repeat of cb9rows2's ZoomInRail -> ZoomOutRail for player 3 (same polls), then player 2 and player 4: player 2 uses the original LockRailCam2 object (0xc54800) while player 3 has his copy (0xd25c00), player 4 another copy (0xd26400); all back to their rails | 0 |
| cb9tlbb | 21 | M9 cp4 | base | 7103 / 7303 | the same camera sequence for player 3 without camB (rail blend 0 -> new locked camera blend 0.75 -> rail blend 0.75), then player 2's zoom in/out | 0 |

Proof that players 1-2's cameras do not change because of players 3-4: every action probe records views 1-2 (render
pointer, blend target, rail fields) before and after the player 3/4 call (`cams_before` / `cams_after` and `before` /
`after` in `evidence/M6/camB_*_probes.json`); in the camB runs they are unchanged in every player 3/4 action (cb6rows,
cb6rows2, cb9rows, cb9rows2, cb9tlb), while the baseline shows the original changing them (cb6base3 EnterTopRail: all
rails; cb9base3 Player2Start: zoom cameras; cb9base4 near plane: player 1's rail).

Screenshots (whole 2x2 window; top left = player 1, top right = player 2, bottom left = player 3, bottom right = player 4):
- M6 before: `local/m2/cb6base2/t0721_p7611.png` (views 3-4 follow cameras far from the chase rail framing).
- M6 after: `local/m2/cb6rows/t0750_p6991.png` (four side-scrolling views alike; players 3-4 teleported next to player 1);
  `local/m2/cb6rows/t0591_p6064.png` (players 3-4 just joined far ahead: their side rails; view 3 behind a wall).
- M9 before: `local/m2/cb9base3/t0524_p7627.png` (two cage-rail views, two close follow views).
- M9 after: `local/m2/cb9rows/t0889_p8519.png` (four cage-rail views alike).

## 5. FAILED TEST signal: 50 TLB misses in cb9rows2 (not reproduced, cause not found)
- cb9rows2 (camB rows, 4 players, M9 cp4): 50 `TLB Miss, pc=0x356e08 addr=0x3c888888 [load]` in 3.4 s (emulator time
  473.5-476.9 s, about poll 8320-8345), 20-40 polls after the probe's direct `C4.ZoomOutRail(vHammerBox, player 3)`
  call; the game kept running (polls to 18000, later probes normal). `local/m6/cam/camB/runs/cb9rows2_emulog.txt`.
- pc 0x00356E08 = `FUN_00356E08` (script-manager method, vtable word 0x00544A04): it walks a dotted Lua name
  ("C4.Foo") character by character; addr 0x3C888888 = the float 1/60, so the engine passed a float where a name pointer
  was expected (HYPOTHESIS: a stale name pointer of some callback).
- Not reproduced: cb9tlb repeated the same probe sequence at the same polls with the rows (0 TLB), cb9tlbb did the same
  camera moves without camB (0 TLB); no other camB run (14) and no other emulog under `local/` has this signature
  (grep 2026-10-12). Whether camB contributes is **not established** - flagged so that the coordinator's 4-instance
  runs of M9 cp4 look for `pc=0x356e08`.

## 6. Files
- Rows (deliverable): `local/m6/cam/camB/rows/camb_helpers.lua`, `m6r.lua`, `m9r.lua` (compact); readable sources
  `local/m6/cam/camB/src/*.lua`; compactor `local/m6/cam/camB/minify.py` (run `python -I minify.py` in that folder
  after editing a source). Tested pnach `local/m6/cam/camB/test_r1.pnach` (= the build command above at 17:30);
  baseline `local/m6/cam/camB/base.pnach`.
- Probes: `tests/m6/cam_camB_probe.py` (new). Run helpers: `local/m6/cam/camB/run.sh`, `waitpoll.sh`, `summ.py`.
- Evidence: `evidence/M6/camB_<tag>_probes.json` (14 runs); consoles / emulogs `local/m6/cam/camB/runs/`.
- Not changed: `mod/`, `mod/w4p_m1.pnach`, emulator, shared probe files.

## 7. Could not do / left open
1. Real chase play (running and jumping the rooftops, reaching the gallery by running) and real cage play (24 lock
   hits): bots cannot; the camera paths were driven by direct handler calls and teleports next to player 1.
2. The M6 jump-warning HUD prompt for players 3-4 (engine has HUD prompt objects only for HUD 1-2).
3. Stunt cameras with blend 0 for anyone after the blended chase rail (engine fact, section 1.3) - unchanged, parity.
4. The cb9rows2 TLB burst (section 5): cause unknown, one occurrence.
5. A window of up to 500 ms at the M9 stage-2 start: a player 3/4 leaving `vSecondVanBox` in that window gets his follow
   camera (no camB rail yet), and the following blend-0 rail give does not replace a blended camera (section 1.3); he
   keeps the follow camera until his next zoom box. Fix would need about 40 more bytes (region full).
6. Mission restart/checkpoint reload with the rows, 4-PC sessions, LAN/internet, human play: not tested.

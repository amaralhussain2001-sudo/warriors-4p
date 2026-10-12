# M6 camera parity, agent camA: M16 "Home Run" chase cameras for players 3-4 (2026-10-12)

**Status (coordinator, 2026-10-12 21:40):** merged into mod/ (LUACH row 12). Placeholders F-CAM-camA-1..10 are summarized in **F-0225**. Negative result 1 (the M16 cp1 street rail broken for everybody) was the `[4p]` relocation bug **F-0223 (LUIFIX)** and is fixed: luifix_m16dbg5 shows the street rails on views 1-2.

## Plain-English summary
- **What this is.** In Mission 16 the game gives players 1-2 a side-scrolling "rail" camera during the street and alley
  chase (checkpoints 1-2) and the park chase (checkpoint 3). Players 3-4 kept the normal close camera behind their back
  ("2 good screens and 2 zoomed-in screens"). One new LUACH row for "level54.lua" (`local/m6/cam/camA/rows/m16q.lua`,
  1960 characters) now gives players 3-4 the same cameras on their own screens.
- **How (one rule, no per-box code).** Every camera call the mission makes **for player 2** is done again for player 3
  and player 4 with their own screen number (index 2/3) and their own character. Player 1's and player 2's calls run
  first and unchanged. Example: when player 2 crosses the alley camera box, the script builds "rail1" with index 1
  around Snow; right after it the row builds the same rail with index 2 around player 3 and index 3 around player 4,
  and when the script switches player 2's screen to that rail, players 3-4's screens switch to their own rails.
  Example from run camA_c3b (park): players 1-4 each see a park rail that follows **themselves** (camera arrays: render
  = rail on all four views, rail targets P1, P2, P3, P4).
- **Players who join later** (the usual case: X11 brings players 3-4 in after the chapter start) get what player 2
  has at that moment: the row keeps a short record of player 2's last rail set-up and replays it with the new
  player's index; if player 2's screen shows that rail, the new player's screen does too, otherwise he gets his normal
  camera. Example (camA_c3b): players 3-4 joined in the park 80-230 polls after `ch3.ContinueLevel` and got park rails.
- **End of the chase.** Whatever the script does to player 2's screen at the end (the alley `BackToMainCam`, the
  park `AjaxScraps`) is repeated, and a player 3/4 who joins after the chase gets the normal camera. Example
  (camA_c3b): after the park chase players 3-4 were sent out by the game's gang change (X3), joined again (poll 7233)
  and all four screens showed the normal follow camera. (The alley `BackToMainCam` is mirrored like player 2's call but
  its effect was not shown at runtime, section 5.4.)
- **Nothing players 3-4 do changes players 1-2's cameras**: the row only reacts to player 2's calls, never uses index
  0/1 and never moves a locked or fixed camera (a fixed camera made for player 2 is created again for players 3-4).
  Checked at runtime: replaying the join set-up for players 3-4 left players 1-2's camera objects and rail settings
  identical (A/B in every scenario run), and the 2-player runs with and without the row match step by step.
- **Negative results first (details in section "Negative results")**:
  1. **The M16 street rail (cp1, first 200 units of the chase) does not appear even for players 1-2 in the current
     full build**: the street box fires (`chase.CamSwitcher` called with box 1, spy in camA_dbg3) but the screen keeps
     the start camera. With a minimal patch set (2 players, groups test call + session + missions) the same box gives
     both players their street rails (camA_dbg4). Runtime bisect: the `[warriors-4p 4p]` group alone causes it
     (section 5). Not caused by this row (same in the runs without it). Players 3-4 get what player 2 gets there
     (with 4 players in: player 1's quarter shows the start camera, players 2-4 their follow cameras, camA_c1c).
  2. Two test methods failed: teleports with a 1.2-unit side offset dropped players 3-4 through the alley walls
     (camA_c1a/c1b), and teleports down the sloping park dropped all four through the ground (camA_c3a, level end).
  3. Players 3-4 switch rails when **player 2** crosses a camera box, not when they cross it themselves (the boxes only
     notice players 1-2). A player 3/4 far behind player 2 sees his rail from its starting end until he catches up.
- Everything: SINGLE-PC, one instance (sandboxes 19/20), 4 W4P players with scripted bots (players 3-4 idle), no
  impairment, MTVU off, no human play. Function names are OUR labels (the ELF is stripped); addresses static.

Build: The Warriors SLUS-21215 v1.03 (`local/disc/SLUS_212.15`, read-only), fork build w4p-m6-3 (not rebuilt), current
`mod/` with the D24 RAILTGT patch. Test pnach `local/m6/cam/camA/test.pnach` = `tools/lua_rows.py` build of the current
`mod/` plus the row; "before" runs use `local/m6/cam/camA/base.pnach` = the same build without the row (identical to
`mod/w4p_m1.pnach` at the time, sorted-line diff 0).

## 1. Static facts that decide the design (VERIFIED code/script unless marked; script lines `WAD:line` = pseudo-Lua)

### 1.1 Where M16 gives players 1-2 a chase camera (audit section 3, M16 rows)
| Stretch | Script | What players 1-2 get | Trigger (box type) |
|---|---|---|---|
| cp1 street | 08355 main.7 #98-148 (`ch1.StartTheLevel`): loop over `Warriors`, index 1 for `player2` else 0: `CamSetupRail("rail1", h, 85, {0,0,1.8}, 0.5, 75, i)`, `CamModifyRail(0, 4.5, i)` and `(1, 1, i)` (3 arguments: the index lands in the "t" slot, so these two act on **all** rails; binding 0x003668E8, argument 4 default -1), 2 points | rails built; made active by `chase.CamSwitcher` box 1 (08262 main.97 #13-100: `CameraMakeActive(railCam, 1, "ch1.OtherRailStart", player)`), whose callback `ch1.OtherRailStart` (08355 main.8) does it for `player2` | `camswitch[1]` type 2 (08262:1522) |
| cp1 alley | `chase.CamSwitcher` box 2 (shared locked camera, split off), box 3 (rail "alley" per player, 6 points, `CamLeadRail(chase.CUR_LEAD_DIST, 0, 1, i)`), `ch1.ReturnPlayerBrain` (08355 main.14 #9-26: split on, `CameraMakeActive(railCam, 0, nil, h)` for every `Warriors` player), `chase.LeadOut/LeadIn` (08262 main.106/107), box 4 (fixed camera `leadtrans1/2` per player), box 5 (rail "platforms" + activate), `ch1.TightenSideScroller` (08355 main.24) | per-player rails | boxes type 2 (08262:1522-1592, 1836); `vbGoGoGo` type 0 (08262:1801) |
| cp1 end, cp2 | `ch1.StartTrailTransition` (shared fixed camera), box 7 (rails for `{player, player2}` index 0/1 + split on), `ch2.BackToMainCam` (08349 main.12: `CameraMakeActive(MainCam, 0, nil, h)` for every `Warriors` member) ends this rail; box 9 (rail "street 2" per player), box 10, box 11 (`RailDown/RailUp`), box 14 (`ChangeCam(MainCam, 1)` = view 0 only: in the original player 2 keeps his rail) | per-player rails | type 2 |
| cp3 park | `ch3.ContinueLevel` (08352 main.5): loop over `{player, player2 if human}`: `CamSetupRail("rail1", h, 34, ..., i)`, `CamLeadRail(8, 0, 1, i)`, 2 points, `CamModifyRail(1, 2, 0, i)`, `CameraMakeActive(railCam, 0, nil, h)`; ended by `ch3.AjaxScraps` (`ChangeCam(MainCam, 0)` + `CameraMakeActive(MainCam, 0, nil, player2)`) after `HuChangePlayerGang(GangAjax)` (X3 sends players 3-4 out first) | rails | scene return |
| no auto lock-on | `HuSetNoAutoLock(player/player2, 1)` 08355:161-162 (cp1), 08349:159-160 (cp2), `(..., nil)` 08352:87-88 (cp3) | bit 39 of the u64 at human+0xE0 (core `FUN_002340A8`, binding 0x003587B0) | chapter start |

Every one of these camera calls is made **for player 2 with an explicit index 1** or with the human `player2`, apart
from the two all-rail `CamModifyRail` calls and `ChangeCam(MainCam, x)` (no human = view 0 only). That is what makes
one generic rule possible.

### 1.2 Engine facts used
- `CamSetupRail(..., i)` core `FUN_0011CCE8` (all_00.c:19209): creates or reuses rail[i] (`FUN_0011FBB0(i, 1)`), adds
  the human to the tracked list (`FUN_001222B0(h, 1)`) and returns the rail's handle. The tracked-list add skips a
  player who is already in the list (all_00.c:22686-22691: player index != -1 and `FUN_004DAE60` finds him), so a player
  3/4 (put in the list by UpdateJoin) does not change list entries 0-1 (players 1-2's camera targets, audit 1.3).
- `CamAddRailPoint` / `CamModifyRail` / `CamLeadRail` with index i >= 0 touch rail[i] only and do nothing when it does
  not exist (`FUN_0011FBB0(i, 0)` == 0 guard in `FUN_0011D098` all_00.c:19351, `FUN_0011CF70` 19299, `FUN_0011D228` 19426); index -1 = all rails.
- `CamLeadRail` argument 3 is read by `FUN_00409318(L, 3, 1)`: an explicit nil (the script's `false`) gives 0, a
  missing argument gives the default 1 (all_06.c `FUN_00409318`: type nil -> 0). The row keeps the argument table and
  its count `n`, so a repeated call means exactly what player 2's call meant.
- `CameraMakeActive(cam, blend, name, h1, h2)` takes the view from h1's player index (`FUN_0011B770`); a rail of
  another view is replaced by the view's own rail when it exists, otherwise the object is **moved** to that view (audit
  1.1). The row therefore never passes another view's rail or a locked/fixed camera for a player 3/4: `railCam` is
  replaced by his own rail handle (`W4Q.r[i]`, the return of his own `CamSetupRail`), a fixed camera by the copy made
  for him, `MainCam` (player 1's follow camera, 08262 main_78) is substituted by the engine with his own follow camera
  (as W4P_GPW relies on, m6_x6_fixes.md row 2); anything else (locked cameras) is not repeated.
- A blended `CameraMakeActive` (blend > 0) puts a per-view blend camera into the render array; it points to the new
  camera at +0x214 (runtime: camA_dbg2, camA_dbg4). The probe reports such a view as "rail(blend)".
- `ScheduleFuncArg1(name, n, ms)` (binding 0x0036D7B0) passes an integer; `FlushScheduledFuncs(name)` (0x0036D848)
  flushes everything when the name is nil or missing (`FUN_00409220(L, 1, 0)` -> 0); `ch2.TheyTakeOff` calls it
  without a name (08349:350), so the row restarts its tick after such a flush.
- The rail target of views 3-4 comes from the D24 RAILTGT patch (`mod/m2/camtarget.txt`, cave 0x000F0940): a rail of
  view 2/3 targets that player's own human (runtime here: rail targets of views 3/4 = players 3/4, camA_c1a, camA_c3b).

### 1.3 The `ReturnPlayerBrain` hazard (audit row 2) is not reachable
`ch1.ReturnPlayerBrain` loops over `Warriors` (08355 main.14 #9-26). At cp1 `Warriors` = `Warriors1` = {swan}
(08262 main_39); the only script that adds to it is the player-2 join callback `AnotherPlayer` (08262 main_89:
`Warriors["snow"] = A0`), and the W4P join-event guard skips the Lua join event for player index >= 2 (F-0183). So a
player 3/4 is never in `Warriors`: VERIFIED (script); runtime: `HuGetPlayer(1) == player2` was true in every run with
the row (probe `state_lua`). Even if it were reached, the row builds players 3-4's rails as soon as player 2's rail is
built, so the engine would pick his own rail instead of moving player 1's.

## 2. The row (`local/m6/cam/camA/rows/m16q.lua`, chunk "level54.lua" from the LUACH log, 1960 characters)
One row, run after the level's main file (08262) at every level load of level54 (all five checkpoints):
- `W4Q.W(f, p, x, k)` wraps a binding: the original runs first with unchanged arguments and its result is returned.
  If the call was made for player 2 (argument x == 1 for the bindings with an index: `CamSetupRail` 7,
  `CamAddRailPoint` 2, `CamModifyRail` 4, `CamLeadRail` 4; argument p == `player2` for `CameraMakeActive` 4,
  `CameraCreateFixed` 2, `HuSetNoAutoLock` 1), `W4Q.D` repeats it for each human player 3/4 (`HuGetPlayer(2/3)`,
  `HuIsAPlayer`) with every `player2` argument replaced by his human and the index set to 2/3.
- `CameraMakeActive` repeats: `railCam` -> his own rail `W4Q.r[i]`; a fixed camera from a repeated
  `CameraCreateFixed` -> his copy (`W4Q.m`); `MainCam` -> unchanged (the engine takes his follow camera); any other
  camera (e.g. the locked `ch2.AltPitCam`) is not repeated. The name callback is never repeated.
- Record for later joiners: player 2's rail calls (index 1) and all-rail calls (no index) since player 2's last
  `CamSetupRail(..., 1)` are kept in `W4Q.q`; `HuSetNoAutoLock(player2, v)` keeps v in `W4Q.a`.
- Tick `W4QT` every 500 ms (`ScheduleFuncArg1` with a generation number, so only one chain runs): a player 3/4 human
  not seen before gets `W4Q.R`: the record replayed with his index; then his rail is made active if player 2's view
  shows player 2's rail now (`CameraGetActive(1) == W4Q.r1`), else `CameraMakeActive(MainCam, 0, nil, h)` (his follow
  camera); his no-auto-lock flag is set like player 2's. The tick starts at level load and restarts at every
  `HuSetNoAutoLock(player2, ...)` (each chase chapter start) and after `FlushScheduledFuncs()`.
- Players 1-2: no call of theirs is changed, delayed or repeated with index 0/1 or with their humans; every repeated
  call carries index 2/3 or a player 3/4 human.
- The existing row 2 (`chase.CamSwitcher = W4P_G34(...)`, m6_x6_fixes.md) stays and keeps blocking direct calls for
  players 3-4 (its boxes never fire for them); this row neither needs nor conflicts with it.

The first design (own trigger: a 250 ms `IsInsideBox` poll for players 3-4 on the per-player boxes, rail data per spec
and wrappers on 8 chapter functions; `local/m6/cam/camA/old_design/`) needed 6066 characters and did not fit the
3072-byte region; it was not run. `IsInsideBox` is a pure position test (`FUN_00413198` -> `FUN_004129C0` ->
`FUN_00412A18`, no enabled check), noted for future use.

## 3. Per-fix table
| # | Mission / stretch | Chunk (LUACH name) | Function(s) | Change for players 3-4 | Test | Result | Label |
|---|---|---|---|---|---|---|---|
| F-CAM-camA-1 | M16 cp1 alley (box 3 + `ch1.ReturnPlayerBrain`) | "level54.lua" (log) | `CamSetupRail`/`CamAddRailPoint`/`CamLeadRail` for index 1, `CameraMakeActive(railCam, 0, nil, player2)` | same alley rail on index 2/3 around their own human, made active together with player 2's | camA_c1c (after) vs camA_c1b (before) | after: render = rail on views 1-4, rail targets P1-P4 (poll 8994-9816); before: views 3-4 follow camera | **VERIFIED** |
| F-CAM-camA-2 | M16 cp1 alley `chase.LeadOut/LeadIn`, box 4 (fixed camera), box 5 (rail "platforms", blend 1) | "level54.lua" | `CamLeadRail`/`CamModifyRail` index 1, `CameraCreateFixed(..., player2, ...)` + `CameraMakeActive(fixed, 0, nil, player2, player2)`, rail set-up + `CameraMakeActive(railCam, 1, nil, player2)` | same, on their own index; fixed camera = a new copy per player 3/4 (never player 2's object) | camA_c1c, camA_c1a | box 4: views 1-4 render new fixed-camera objects (0xD32C00 / 0xD1C000 / 0xD34000 / 0xD34400), screenshot `local/m2/camA_c1a/camA_10_after_camswitch4_p9725.png` shows the same high angle on views 1-3; box 5: views 1-4 rail(blend) (+0x214 = own rail), rail words +0x370..+0x384 identical on rails 1-4 (fov 85, 4.25, 6.25, 3.0) | **VERIFIED** |
| F-CAM-camA-3 | M16 cp2 box 7 (rails for players 1-2, split on) | "level54.lua" | loop `{player, player2}` index 0/1 | rails "alley north" on index 2/3 + activation (blend 1) | camA_c2b (after) vs camA_c2base (before), box 7 by direct call `chase.CamSwitcher(camswitch[7], player)` (cp2 reload has no handler on box 7) | after: views 1-4 rail(blend), targets P1-P4, screenshot `camA_02_after_camswitch7_call_p4810.png`: four identical alley views; before: views 3-4 follow (`camA_c2base/camA_02_after_camswitch7_call_p4809.png`: 2 rail + 2 close cameras) | **VERIFIED** (direct call) |
| F-CAM-camA-4 | M16 cp2 box 9 / box 14 | "level54.lua" | box 9 for player 2 (rail "street 2", blend 1.5); box 14 for player 1 (`ChangeCam(MainCam, 1)` = view 0 only) | box 9 mirrored; box 14 not (players 3-4 keep the rail like player 2 does) | camA_c2b / c2base (direct calls) | after box 9: views 1-4 rail(blend) targets P1-P4; after box 14: view 1 follow, views 2-4 rail (before: view 1 follow, view 2 rail, views 3-4 follow) | **VERIFIED** (direct calls) |
| F-CAM-camA-5 | M16 cp3 park chase | "level54.lua" | `ch3.ContinueLevel` loop index 1 calls | park rail on index 2/3 | camA_c3b (after) vs camA_c3base (before) | after: players 3-4 joined 80-230 polls after `ContinueLevel` (4505 -> 4582/4737) and got the park rail by the join replay (views 1-4 render = rail, targets P1-P4, screenshot `camA_03_park_run_p5112.png`: four side views of the same fight); before: views 3-4 follow | **VERIFIED** |
| F-CAM-camA-6 | M16 end of the chases | "level54.lua" | `ch3.AjaxScraps` (`CameraMakeActive(MainCam, 0, nil, player2)`), join after the chase | follow camera for players 3-4 | camA_c3b | `ch3.StartSplit` called -> scenes -> X3 sent players 3-4 out (count 2) -> `AjaxScraps` -> players 1-2 follow; players 3-4 re-joined (poll 7233): views 3-4 render = their follow camera (`camA_07_rejoined_after_chase_p7480.png`); the same without the row (camA_c3base), so nobody is left on a rail | **VERIFIED** |
| F-CAM-camA-7 | M16 cp1-cp3 no auto lock-on | "level54.lua" | `HuSetNoAutoLock(player2, v)` | same flag for players 3-4, also for later joiners | camA_c2b / c2base, camA_c1c | bit 39 of human+0xE0 (word +0xE4 bit 7): after: players 1-4 = 1 at cp1/cp2; before: players 3-4 = 0 | **VERIFIED** (flag); effect on lock-on not observed |
| F-CAM-camA-8 | players 1-2 untouched | "level54.lua" | all | - | A/B replay in camA_c1a/c1c/c2b/c3b; 2-player runs camA_r2p3 vs camA_r2p3base (cp3), camA_r2p2 vs camA_r2p2base (cp2) | replaying the join set-up for players 3-4 left players 1-2's render/follow/rail objects and rail words identical (`p12_diff` empty, 4 runs); 2-player regression: players 1-2 identical at every step in cp2 and cp3, row markers present, 0 TLB | **VERIFIED** |
| F-CAM-camA-9 | `ch1.ReturnPlayerBrain` hazard (audit) | - | - | none needed | static (section 1.3) + runtime `HuGetPlayer(1) == player2` | players 3-4 are never in `Warriors` | **VERIFIED** (not reachable) |
| F-CAM-camA-10 | M16 cp1 street rail (box 1) | - | - | none possible yet: players 1-2 do not get it either in the full build | camA_dbg1-5, bisect runs | see section 5: the `[warriors-4p 4p]` group stops box 1's rail switch for everybody | **FAILED TEST** (pre-existing, not this row) |
| - | M16 cp2 `ch2.BackToMainCam` | - | `CameraMakeActive(MainCam, 0, nil, player2)` (mirrored) | follow | camA_c2b / c2base (direct call while all views showed a blend camera) | no view changed, with or without the row (players 1-2 kept their rail too); the real call follows `BreakBridge`'s camera changes, not reproduced | **HYPOTHESIS** (equal to player 2 by construction, not shown at runtime) |

## 4. Tests (SINGLE-PC, one instance each, sandboxes 19/20, scripted bots, no impairment, MTVU off)
Command (`local/m6/cam/camA/run.sh <tag> <inst> <pnach> <cp> <scenario>`; `run_g.sh` = same with a chosen group list and
player count, `run_min.sh` = 2 players with groups test call + session + missions):
```
python -I tests/m2/nav_probe.py <tag> tests/m2/nav/boot_to_m1_2p.txt --inst <19|20> --players 4
  --script2 tests/m2/nav/p2_join.txt --script3 tests/m2/nav/empty.txt --script4 tests/m2/nav/empty.txt
  --groups "warriors-4p own view;warriors-4p hud;warriors-4p 4p;warriors-4p test call;warriors-4p 4p hud B1;
  warriors-4p 4p hud B2;warriors-4p 4p spawn;warriors-4p 4p spawn leave;warriors-4p 4p inventory;warriors-4p 4p fx;
  warriors-4p 4p markers;warriors-4p session;warriors-4p missions" --ini EmuCore/Speedhacks/vuThread=false
  --callat "3999:0041ABC0:<cp>,4009:00160D78:0x01FDA128" --patch local/m6/cam/camA/<test|base>.pnach
  --probe cam_camA_probe:<scenario>:4100 --probe chase_probe:state:4090 --seconds 600 --every 6
```
M16 = level jump entry 0x01FDA128; checkpoint n = chapter n (`Chapter[1..5]` = streets, alley, park, popsicle, boss,
08262 main_114; LUACH log in the chase_probe state: "level54_park.lua", "level54.lua", "global.lua"). Players 3-4 join
through `x6fix_probe.join34` (the game's UpdateJoin, what X11 does). The scenario probe (`tests/m6/cam_camA_probe.py`)
blocks and writes `local/m2/<tag>/camA_log.jsonl` and `camA_<nn>_<label>_p<poll>.png` (whole 2x2 window, scale 0.6).
Players' god mode is a test aid. TLB = `TLB Miss` lines in `local/pcsx2/inst<N>/PCSX2/logs/emulog.txt` (copied to
`local/m6/cam/camA/<tag>_emulog.txt`).

| Run | Inst | Jump | Pnach / groups | Players 3-4 | What it shows (poll: result) | TLB |
|---|---|---|---|---|---|---|
| camA_c1b | 20 | cp1 | base | joined 7467 | before: alley rails for players 1-2 only (8907: views 1-2 rail targets P1/P2, views 3-4 follow; screenshot `camA_07_after_gogogo_p8907.png`); street: start camera on view 1 for everybody; players 3-4 fell through the alley wall at 8907 (test method), level end at ~9490 (player 1 beaten: `ReturnPlayerBrain` clears god mode) | 0 |
| camA_c1a | 19 | cp1 | test | joined 7511 | markers 111 (helpers, row, `HuGetPlayer(1) == player2`), record 5 calls, both rails known after the join (R2 11); after `vbGoGoGo` (9023) views 1-4 rail, targets P1-P4; box 4 (9725) fixed cameras on views 1-4; box 5 (9826) rail(blend) on 1-4; A/B replay: players 1-2 unchanged; players 3-4 fell through walls (method) | 0 |
| camA_c1c | 19 | cp1 | test | joined 7505/7658 | same as c1a with the tighter teleport cluster: 8994-9816 views 1-4 rail, targets P1-P4 (`camA_08_after_leadout1_p9353.png`: views 1, 2, 4 the same alley view; view 3 = player 3, who fell at a hole near x -306 three runs in a row); box 4 (9899) fixed cameras 1-4; box 5 (10051) rail(blend) 1-4; no-auto-lock bit 1 for players 1-4; A/B unchanged | 0 |
| camA_c2b | 20 | cp2 | test | joined 4463 | joiners get player 2's camera (follow at a cp2 reload; record 7 replayed: rails built, not active); box 7 direct call (4809): views 1-4 rail(blend) targets P1-P4 (`camA_02_after_camswitch7_call_p4810.png`); box 9 for players 1-2 (5004): views 1-4 rail S9; box 14 for player 1 (5080): view 1 follow, views 2-4 rail; no-auto-lock 1 for players 1-4; A/B unchanged | 0 |
| camA_c2base | 19 | cp2 | base | joined 4464 | before: box 7 -> views 1-2 rail, 3-4 follow (`camA_02_after_camswitch7_call_p4809.png`: "2 good, 2 zoomed-in"); no-auto-lock 0 for players 3-4 | 0 |
| camA_c3b | 19 | cp3 | test | joined 4737 | park rails for players 3-4 by the join replay (4953: views 1-4 rail, targets P1-P4; `camA_03_park_run_p5112.png`); A/B unchanged; `ch3.StartSplit` -> scenes -> count 2 (X3) -> `AjaxScraps` (7228: views 1-2 follow) -> rejoin 7233 -> views 3-4 follow (7480) | 0 |
| camA_c3base | 19 | cp3 | base | joined 4744 | before: views 3-4 follow during the park chase while 1-2 rail; after the chase all follow | 0 |
| camA_c3a | 19 | cp3 | test | joined 4893 | joiners got park rails (5117), then **FAILED TEST (method)**: teleports down the park slope dropped all four (z -235), level end; later probes did not run | 0 |
| camA_c2a | 20 | cp2 | test | joined | box 7 direct call: views 1-4 rail(blend) (as c2b); then **FAILED TEST (method)**: teleports north of the cp2 start dropped everybody (z -234), level end | 0 |
| camA_r2p3 / camA_r2p3base | 19 / 20 | cp3 | test / base | never (2-player regression) | players 1-2 at every step (park start 4563, park run 4716, A/B 4752, `StartSplit` 4819, after `AjaxScraps` 6796): same view count, same camera kinds, rail targets and rail words with and without the row; markers 111 (row ran, no Lua error stopped it), record 5, no rails for views 3-4 | 0 / 0 |
| camA_r2p2 / camA_r2p2base | 19 / 20 | cp2 | test / base | never (2-player regression) | players 1-2 at every step (cp2 start 4319, box 7 4432, `BackToMainCam` 4508, box 9 4621, box 14 4697, A/B 4743): identical view count, camera kinds (rail / rail(blend) / follow(blend)), rail targets and rail words with and without the row; no-auto-lock 1/1 in both; markers 111, record 7 then 6 | 0 / 0 |
| camA_r2p / camA_r2pbase | 19 / 20 | cp1 | test / base | never | **FAILED TEST (method)**: the street hops from box 1 dropped players 1-2 through the street (z -235) in both runs identically; stopped by me (own sandboxes) | 0 / 0 |
| camA_dbg1, dbg2, dbg3 | 20 | cp1 | test | none | street investigation: box 1 fires (spy: `chase.CamSwitcher` called once with box 1 by player 2 at ~7550), view 1 keeps the start camera; a direct `CameraMakeActive(railCam, 1, nil, player)` 250 polls later does switch (dbg2) | 0 |
| camA_dbg4 | 20 | cp1 | base, 2 players, test call + session + missions | - | box 1 by player 1 at ~7558: views 1-2 rail (blend, then rail), views 2 | 0 |
| bisect | 19/20 | cp1 | base, see section 5 | - | street rail works without `[warriors-4p 4p]`, fails with it | 0 |

## 5. Negative results and open points (read these first)
1. **FAILED TEST (pre-existing, affects players 1-2): the M16 cp1 street rail never appears in the full patch set.**
   After `ch1.StartTheLevel` the players auto-run (AI goals to `fUberHack[2]`, 08355 main.7 #148-182) through box 1;
   `chase.CamSwitcher` runs for box 1 (spy, camA_dbg3/dbg5: one call, box 1) and does
   `CameraMakeActive(railCam, 1, "ch1.OtherRailStart", player)`, but view 1 keeps the start camera (render object
   unchanged, views 1) for the whole street; only box 2 (shared alley camera) and `vbGoGoGo` (alley rails) change the
   picture. Runtime bisect, all with `base.pnach` (no camA row), player 1 or 2 forced into box 1 right after the start:
   | Run | Groups (besides M1) | W4P players | Street rail on views 1-2 |
   |---|---|---|---|
   | camA_dbg4 | test call, session, missions | 2 | **yes** (box 1 by player 1, 7558) |
   | camA_bisB3 | + own view | 2 | **yes** |
   | camA_dbg5min_p2 | test call, session, missions; player 2 forced first | 2 | **yes** |
   | camA_bisF | test call, session, missions | 4 | **yes** |
   | camA_bisA3 | full list without own view | 4 | no |
   | camA_dbg5full_p1 | full list (run.sh); player 1 forced first | 4 | no |
   | camA_bisC | 4p, test call, session, missions | 4 | no |
   | camA_bisD | 4p, 4p fx, test call, session, missions | 4 | no |
   | camA_bisE | 4p, test call, session, missions | 2 | no |
   So **`[warriors-4p 4p]` alone breaks it** (bisE vs dbg4/bisF), independent of the W4P player count, of who enters
   first and of "own view". VERIFIED (runtime). Which patch of `[4p]` and why: **HYPOTHESIS** - the per-view camera
   arrays relocated by `[4p]` (render 0x005D9150 -> 0x000F0810, active 0x005D9148 ...) while view 1 shows the locked
   start camera in single-view mode (views 1; `FUN_00122ED0` copies active[0] to render[0] when the view is not split,
   all_00.c:23260-23284) - a plain `CameraMakeActive(railCam, 1, nil, player)` 250 polls later did switch (camA_dbg2),
   the script's call right after the start does not. Not investigated further (outside this mission; the D24 RAILTGT
   part of `[4p]` was read and replicates the original path for views 1-2 exactly, 0x0013B944-0x0013B988 vs cave
   0x000F0940-0x000F0994). **Effect for players 3-4:** none to mirror - player 2 gets no street rail either, so the
   mirror gives players 3-4 the same as player 2 (their follow camera). Once `[4p]` is fixed, the row mirrors
   `ch1.OtherRailStart`'s `CameraMakeActive(railCam, 0, nil, player2)` with no change (players 3-4's street rails are
   already built from the `StartTheLevel` record).
2. **FAILED TEST (method): teleports.** A cluster with 1.2-unit side offsets put players 3-4 inside the alley walls
   (camA_c1a/c1b: z -191 at `vbGoGoGo`); with 0.9/0.3-unit offsets player 3 still fell at x -306 (camA_c1c, the same
   spot in three runs: a hole or gap in the collision there). Hops down the sloping park (camA_c3a) and north of the
   cp2 start (camA_c2a) dropped all four through the ground (z -235) and ended the level (GameMgr+0x14C = 1). The final
   cp2/cp3 tests use direct calls of the chapter functions instead of walking. None of this is part of the fix.
3. **Mirror on player 2, not on the player's own position.** The camera boxes are type 2 (only players 1-2 fire them,
   m6_x6_fixes.md 1.1), so players 3-4 switch when **player 2** switches (the coordinator's F6 (i)). A player 3/4 far
   from player 2 sees his own rail from its nearest end until he catches up; a player 3/4 never switches if player 2
   has left the session (then `player2` is an AI and its calls are not made). A position-based version (own box poll)
   was designed (old_design/) but needs ~6 KB of Lua and did not fit the region.
4. **`ch2.BackToMainCam` not shown at runtime.** The direct call (camA_c2b/c2base) changed no view, also for players
   1-2 (all views showed a blend camera at that moment); in the game it runs after `ch2.BreakBridge`'s locked camera
   on view 1. Players 3-4 receive exactly player 2's `CameraMakeActive(MainCam, 0, nil, player2)` (HYPOTHESIS that the
   result matches player 2's in the real sequence).
5. **Box 14 (cp2 end): player 2 keeps his rail in the original** (`ChangeCam(MainCam, 1)` has no human = view 1 only,
   08262 main.97 #979-993); players 3-4 therefore keep theirs too until the cp3 scene and `ContinueLevel`'s park rail
   (as player 2). Shown in camA_c2b (views 2-4 rail after box 14).
6. Not exercised: the real `ch1.OtherRailStart` (see 1), M16 cp4/cp5 (no rail there; the row's only effects are
   `CameraMakeActive(MainCam, 0, nil, player2)` mirrors after scenes, e.g. 08353:93, and join replays giving the follow
   camera), a session with 4 PCs, human play, checkpoint reload in the middle of a chase with players 3-4 already in
   (the record is rebuilt from the chapter start; expected to work, HYPOTHESIS).
7. The probe's "kind" for a blended camera: the render array then holds a per-view blend camera (+0x210 = from,
   +0x214 = to); earlier probe versions (camA_c1a, camA_c2a) printed "other"/"follow(blend)" for views whose blend
   target was already the rail; the log keeps the raw references (`refs`).

## 6. Files
- `local/m6/cam/camA/rows/m16q.lua` (the row; chunk "level54.lua", name m16q). Built into
  `local/m6/cam/camA/test.pnach` with the command below: row 12 of the LUACH table (0x000EEC60/64), name
  "level54.lua" at 0x000E9800, source 0x000E9810-0x000E9FBB (1960 characters) in my region 0x000E9800-0x000EA3FF
  (1092 bytes left). `python -I tools/note_patches.py check` -> 7910 addresses, 6 problems (the known `[4p hud A]` /
  `[4p hud B1]` alternatives).
  ```
  python -I tools/lua_rows.py build --base mod --region 0x000E9800:0x000EA400 --work local/m6/cam/camA --out local/m6/cam/camA/test.pnach --title "camA camera rows" local/m6/cam/camA/rows/m16q.lua
  ```
- `local/m6/cam/camA/base.pnach`: the same build without rows (sorted-line diff to `mod/w4p_m1.pnach` at build time: 0).
- `tests/m6/cam_camA_probe.py` (new): scenarios `c1_4p`, `c1_2p`, `c2_4p`, `c2_2p`, `c3_4p`, `c3_2p`, investigation
  probes `dbg1`-`dbg5_*`, helpers `cams` (per-view render/follow/rail, blend target, rail target), `ab_replay`.
- `local/m6/cam/camA/run.sh`, `run_g.sh`, `run_min.sh` (run wrappers; retry while the previous emulator still holds the
  sandbox), consoles and emulog copies `local/m6/cam/camA/<tag>_console.txt`, `<tag>_emulog.txt`.
- Evidence: `local/m2/camA_<tag>/camA_log.jsonl`, `probes.json`, screenshots `camA_*.png`; copies of the logs of the
  runs in sections 4-5 in `evidence/M6/camA_<tag>_log.jsonl` (20 files).
- Not changed: `mod/`, `mod/w4p_m1.pnach`, shared probe files, emulator.

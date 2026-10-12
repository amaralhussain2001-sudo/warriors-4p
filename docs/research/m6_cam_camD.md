# M6 camera parity camD: M3 stealth tutorial, M10 sneak corners, M11 Birdie, M5 clinic intro, M13 subway, HUD prompts (LUACH rows, 2026-10-12)

**Status (coordinator, 2026-10-12 21:40):** merged into mod/ (LUACH rows 20-24). Placeholders F-CAM-camD-1..9 are summarized in **F-0228**. Negative result 2 ('blend cameras stay with our patch set') is the `[4p]` relocation bug **F-0223 (LUIFIX)**: six delay-slot `lui`s; fixed, blendw3 shows the hand-over and a later no-blend camera taken.

Agent camD (coordinator brief `local/m6/cam/BRIEF.md`). Audit rows: `docs/research/m6_camera_parity.md` section 3 (M3,
M5, M10, M11, M13), priority items 10-11 and section 5 point 8 (HUD prompts). Build: The Warriors SLUS-21215 v1.03
(`local/disc/SLUS_212.15`, read-only), fork build w4p-m6-3 (emulator not touched), patch set = the current `mod/`
(copied by `tools/lua_rows.py` at each build) + 5 camD rows. Function and structure names are OUR labels (the ELF is
stripped); addresses static unless marked dynamic. Labels: VERIFIED (pointer), HYPOTHESIS, BLOCKED, FAILED TEST. Every
test: SINGLE-PC, one instance (sandboxes 25 and 26), scripted bots (players 3-4 joined through the game's own
UpdateJoin = what W4P X11 does), no impairment, MTVU off, no human play. `mod/` and `mod/w4p_m1.pnach` were NOT changed
(the coordinator integrates the rows). Script lines `WAD:line` = `local/analysis/pseudo/<WAD>_*.lua`. Screens and
"views" are numbered 1-4 as the players see them (view N = camera array index N-1 = player N).

## Plain-English summary
- **M3 "Payback", stealth tutorial (checkpoint 5).** When players 1-2 sneak to the next hiding place, the game switches
  both their screens to one fixed corner camera and keeps them inside its picture. Players 3-4 kept their normal camera
  behind their own back. **Now** each player 3/4 gets his own copy of that corner camera (same position and angle) and
  is kept inside its picture like players 1-2; a player who joins during that stretch gets it within half a second.
  Example (run camD_m3b): after the call, screens 1-2 show the game's camera object, screens 3-4 their copies, all four
  quarters look alike (`local/m2/camD_m3b/t0645_p7488.png`); when the guard has walked back the game itself gives
  players 1-2 their normal cameras again and the row does the same for players 3-4 (`t0692_p8119.png`, four follow
  cameras). Before (run camD_m3a, original function only): screen 3 still showed player 3's normal camera
  (`local/m2/camD_m3a/t0846_p9071.png`).
- **M10 "Destroyed", stealth tail (checkpoint 5).** Four "corner" boxes switch a player's screen to a fixed corner
  camera while he is inside. The boxes only ever notice players 1-2. **Now** a check every 250 ms notices players 3-4
  too and gives them their own copy of that corner camera; leaving the box gives the normal camera back. Example (run
  camD_m10d / camD_m10e, real walk-in): player 3 put into corner 1 -> his screen shows the corner camera, players 1, 2
  and 4 unchanged (`local/m2/camD_m10e/t0269_p6382.png`); put back next to player 1 -> his normal camera again; the real
  end of the chapter (hideout gate) still loads chapter 6 without any error.
- **M11 "Boys In Blue", Birdie fight (checkpoint 6).** When one of the Warriors dies, the game makes player 2's camera
  keep Birdie in the picture (a "secondary target"). **Now** players 3-4's cameras get the same target. Example (run
  camD_m11a): secondary target before = none on all four cameras; after one death call = Birdie on cameras 2, 3 and 4;
  camera 1 (player 1) unchanged, exactly as in the original. Control (camD_m11c): the original function alone gives
  Birdie only to camera 2.
- **M5 "Real Heavy Rep", clinic intro (checkpoint 1).** On the way down from the subway exit the game gives players
  1-2 a fixed opening camera and then a rail camera that follows each of them down the stairs and along the side. The
  boxes only notice players 1-2. **Now** players 3-4 get the same cameras on their own screens: their own copy of the
  opening camera, their own rail (index 3/4) that follows them (rail target = player 3 in the test), and the normal
  camera back when the street scene starts. Example (run camD_m5a): players 3-4 joined standing in the opening box ->
  screens 1, 3, 4 show the opening camera (`local/m2/camD_m5a/t0299_p6659.png`); player 3 "entering" the lead box ->
  his rail (target player 3, `t0328_p7342.png`); street start -> follow cameras (`t0365_p8360.png`).
- **M13 "All-City", subway train.** Inside the graveyard train the game gives players 1-2 a rail camera, at the exits
  a fixed follow position. **Now** the same for players 3-4 (their own rail index and follow camera, never player 1's).
  Tested by direct calls only (run camD_m13a: rail on view 3 targeting player 3; then the exit view on his own follow
  camera, player 1's follow camera unchanged); a real walk into the train was not done.
- **Button prompts (HUD) for players 3-4: not possible without an engine change.** The game builds exactly two
  "button prompt" objects (players 1-2). Example (run camD_m11a): the prompt call for player 3's HUD wrote its 8 values
  into a different HUD object (vtable 0x0053A348 instead of the prompt class 0x00539270). Nothing implemented; details
  in section 5 (the M8 cp3 and M18 spots are reported to the coordinator, they belong to D24).
- **New finding for the coordinator (it also changes player 2 compared with the original game).** With our full
  patch set, after a camera change with a blend time (e.g. 0.85 s) the screen keeps the game's "blend camera" for good
  (it shows the target camera at 100 %), and later camera changes WITHOUT blend on that screen are ignored. Example: run
  camD_ctl_4p2 (our patch set, only 2 players): player 2's test camera is taken before a blend, ignored after one. The
  same test with only the 2-player base groups (camD_ctl_orig2: `[warriors-4p M1]`, test call, missions; original
  camera code) takes the camera after the blend too, so one of our 4-player groups causes it. Deleting a camera that such a blend still points at crashed the game (camD_m10b). The rows
  therefore use the same blend times as the original uses for player 2, never delete their camera copies, and give the
  normal camera back with a blend where they used one before. Root cause not found (section 6).

## Negative results and open points (read first)
1. **FAILED TEST (row version 1), camD_m10b: 22 TLB misses, game stopped.** The first M10 row deleted player 3's corner
   copy in `Cleanup` while view 3's finished blend camera still pointed at it (blend `to` +0x214); the next frame read
   the deleted camera in the blend getter `FUN_004DC848` (pc 0x004DC848, addr 0x0/0x1F0/0x1F4, then pc 0)
   (`local/m6/cam/camD/camD_m10b_emulog.txt`). Mechanism (VERIFIED code, HYPOTHESIS that this is the exact path):
   `CamDelete` -> `FUN_0011E440(cam, 0)` clears a blend's from/to only on the deleted camera's own player index, and a
   camera made active only through the blend path keeps player index 0 (the index rewrite at the end of
   `FUN_0011EE08` is on the non-blend path only). **Fix: the rows never delete their copies** (like the original's
   `Tutorial02Cam`, which is never deleted either); runs camD_m10c/d/e, 0 TLB misses in the real chapter end.
2. **Blend cameras stay with our patch set (VERIFIED runtime; not so without the 4-player groups, see the controls).** After a blended `CameraMakeActive`
   the view's active/render camera stays the blend camera (array 0x000F0870) with progress 1.0 and elapsed time growing
   (camD_m10c: view 2 elapsed 2.0 -> 10.1 -> 23.7 s; camD_m13a: views 2 and 3; camD_m11a: view 1 after the original
   Birdie intro). Afterwards a NON-blended `CameraMakeActive` on that view has no effect: camD_m13a control: player 2's
   test camera `W4PCTL` taken at once before any blend (`ctl_read` 100, 110 with player 3), not taken after one blend
   (`ctl1`/`ctl2` R 0, `ctl_read` 0 for 500+ polls); camD_m10c at poll 7756: player 3's corner copy (blend 0) not
   shown after an earlier blend (`local/m2/camD_m10c/t0597_p7854.png` shows his follow camera). A blended change always
   works (the blend's `to` is replaced; camD_m10b/e). **Controls (M10 cp5, 2 players, the same probes):** our full
   patch set (camD_ctl_4p2): player 2's blend camera 0x00C49400 stays (elapsed 0.17 -> 18.3 s, progress 1.0, active =
   render = blend) and `W4PCTL` is not taken after it (`ctl1` R 0, `ctl_read` 0 at 5806/6006), taken before it (100);
   only `[warriors-4p M1]` + `test call` + `missions` (camD_ctl_orig2, no 4-player groups): `W4PCTL` is taken after the
   blend as well (`ctl1` R 1, `ctl_read` 100 at 5809 and 6009). So **this is a difference of our patch set, also for
   player 2** (VERIFIED runtime, M10 cp5; root cause not found; a group bisection was inconclusive, section 6). Consequence for all camera agents until it
   is fixed: for a player 3/4 use the blend time the original uses for player 2 at the same spot, and if the row itself
   blended a view, give the follow camera back with a blend too.
3. **camD_m10c: 3 TLB misses** at poll ~8000 (pc 0x00323B98, 0x003327B4 = Lua table reads through the binding helper
   `FUN_004093A0` on a missing table) right after calling `Cleanup` directly in the middle of the chase (test only;
   the chase functions scheduled every 100 ms still ran against the removed LC gang). The real end path
   (`HideoutGateTriggered` flushes the scheduled functions first, then `NextMission` -> `Cleanup`) gave 0 TLB misses
   with player 3 inside a corner (camD_m10d, camD_m10e) and with 2 players (camD_reg2p_b). The direct call is therefore
   not used as evidence; HYPOTHESIS that the 3 misses come from the original chase functions, not from the row.
4. **camD_m10a: no result.** The bots stand still, so the stealth chase was lost ("GAME OVER - You lost LC",
   `local/m2/camD_m10a/t0237_p5896.png`) before the first probe; the test-call mailbox is not served on the game-over
   screen. Later runs set test-only values (`C5.maxDistance = 9999`, LC look/move chain and sight/damage fails removed)
   - they are in the probe, not in the row.
5. **M11:** the death handler was called directly for a non-player chain Warrior (Cody); no real Warrior death was
   observed. In camD_m11a the call came at the end of the Birdie intro (one shared view); camD_m11c repeated it in the
   fight with the original first (before: only player 2's camera gets Birdie, `t0260_p6580.png`) and the row second
   (after: players 3-4 too, `t0268_p6816.png`: screen 3 now frames Birdie on the walkway).
6. **M13:** only direct calls (the row's inside test replaced for one box, `W4P_D13IB`); no player walked into the
   train: at the cp1 start the players stand at about (73, 381) and `vbInTrain[1]` is about 118 units away, and far
   teleports dropped a player through the world before (x6f_m16). Because player 3 was not in the train, his screen
   showed the subway rail looking at him from the train area (a wall, `local/m2/camD_m13a/t0447_p9041.png`) - expected
   for this test, the arrays are the evidence. The early marker probes (polls 4600/6000) did not run (mailbox not served during the intro movie); the row's
   own state table (`W4P_D13S[2]`, R 100 at poll 8705) shows the row loaded and ticking; the 2-player run camD_reg2p_c
   read the markers (111) later in the level. Only player 3 joined in that run (player 4's
   join calls did not add him; cause not investigated).
7. **M5:** players 3-4 who appear inside an opening-camera box (they join there) get the opening camera at once;
   player 2, who stands in the same box from the start, keeps his follow camera until he enters another box (the
   engine sends no "enter" for a player who is already inside when the handlers are registered). Players 1-2 are not
   affected. The final M5 row (original blend times) was run once (camD_m5b): same result as camD_m5a, the views show the
   copies/rails as the target of their blend cameras.
8. **M3:** players 3-4's pads are not locked during the distraction lesson (only players 1-2, `09225` main_33) and they
   are not teleported by `MakeSure` unless they hold a `Warriors` member - not a camera item, not changed. In the tests
   player 3 (Cowboy) stood at his `fWarpDest` flag and player 4 (spawned) next to player 1, both inside the corner
   camera's picture, so the frame lock did not move them (positions unchanged, camD_m3b).
9. **HUD 2/3 button prompts are unsafe** (section 5): the call writes into another HUD object; not implemented.
10. The audit's warning "a locked camera made active for a player 3/4 is MOVED and player 2's view loses it": the
    original gives player 2 the **same** object (`CameraMakeActive(Tutorial02Cam, 0, nil, player2)`); at runtime both
    views 1-2 then render that one object (camD_m3a: render[0] = render[1] = 0x00CE0800). The rows nevertheless follow
    the coordinator's rule and use separate copies; this also matters because the locked camera's lock list has only
    two slots (section 1.2), which players 1-2 already fill.

## 1. Static facts that decide the fixes (VERIFIED code unless marked)

### 1.1 Camera activation (`CameraMakeActive` binding 0x003656A0 -> `FUN_0011B770` -> `FUN_0011EE08`)
- The view is the player index (+0x1B0) of the 4th argument; the 5th argument only selects the "from" camera for a
  blend. Non-blend path: `active[view] = render[view] = cam` (arrays relocated to 0x000F0800 / 0x000F0810 by
  `[warriors-4p 4p]`, pnach 0x0011F110-0x0011F178), then the camera's player index is rewritten (vtable +0x274) if it
  differs (`all_00.c` 20751-20756). A locked camera (type 1) is not substituted by a per-view camera (only types 2 =
  follow, 9 = rail and 11 are substituted, 20655-20693).
- Blend path (blend time > 0 and a blend camera `FUN_0011FAC8(view, 1)`, array 0x000F0870): `FUN_00143078` stores
  from +0x210, to +0x214, duration +0x218; the blend camera becomes active/render (20712-20745). Runtime behaviour in
  negative result 2.
- `CamDelete` (0x00365818 -> `FUN_0011B888` -> `FUN_0011E440(cam, 0)`) refuses only cameras active on view 0 or 1
  (`active[0] == cam || (cameras > 1 && active[1] == cam)`, 2-player check): a camera on view 3/4 is not protected. The
  rows never delete.

### 1.2 Locked cameras (`CameraCreateLocked` 0x00365D38 -> `FUN_0011BC48`, class vtable 0x005362D0)
- Constructor `FUN_001352F0`: lock list at +0x20C with **2 slots** (+0x20C/+0x210); `CamLockLocked(cam, h, on)` ->
  `FUN_001358D0` adds with `FUN_004DB928` (loop bound 2: a third human is not added) or removes.
- Update (vtable +0x134 = `FUN_00135680`) calls `FUN_00135CA8`, which walks the lock list, tests each human against the
  camera's view (`FUN_00135960`) and sets his position back (vtable +0x6C) when he is outside: "locked" humans cannot
  leave the picture (HYPOTHESIS for the exact rule; the code path is VERIFIED). Players 1-2 fill both slots of
  `Tutorial02Cam` (09225:576-577), so players 3-4 need their own camera (the rows lock each player 3/4 into his copy).

### 1.3 Volume boxes and `IsInsideBox`
- `vLCTrigger[1..4]` (09321:1656-1663), `vbIntroCam[1..2]`, `vbLeadRail[1..2]` (07708:1424-1429), `vbSideRail`
  (07708:1554), `vbInTrain[1..3]`, `vbMainCam[1..2]` (09229:1502-1527) are all **type 2** (only players 1-2 fire them,
  loop bound 2 at 0x004136B0, `m6_x6_fixes.md` 1.1).
- `IsInsideBox` (0x0037AFB8 -> `FUN_00413198` -> `FUN_004129C0` -> `FUN_00412A18`) is a geometric test of the object's
  position (vtable +0xAC) against the box; it does not use the box's 2-entry inside list. Runtime: VERIFIED for player 3
  in type-2 boxes (x6f_m16c camswitch[7]; camD_m10d/e vLCTrigger[1]: R 110 = inside box 1, not box 2).

### 1.4 Secondary target (`CamSetSecondary(h, f, i)` 0x003670C0 -> `FUN_0011DCF0`)
- Writes follow[i]+0x320 = h, +0x3FC = f and the type-7 camera of view i (+0x1E8); both arrays are relocated to 4
  entries (follow 0x000F0820; type 7 0x000F0850, pnach 0x0011FDB4/0x0011FDC4/0x0011FE3C), so index 2/3 are valid.

### 1.5 Script facts per spot
- M3 cp5 (`09225`): `DestractTutorial02` (main_31) creates `Tutorial02Cam` and shows it on view 0 with split off;
  `MoveToNextBox` (main_37) turns split on, makes the same object active for player 2 and locks player/player2;
  players 1-2 get `MainCam` back in `Stealth3Damaged` (main_34), `AfterS03WalksBack` (main_42), `Stealth03Damage`
  (main_44, every `Warriors` member who is a player, blend 1) and `Tag9CamOut` (main_49); `DistractMoveBackTutorial`
  (main_40) turns split off for `Dest4Cam` (shared, class b*).
- M10 cp5 (`09379`): `SetupLCChase` (main_7) registers the four enter handlers; `RunSneakCamN` creates the shared
  `SneakCamN` once and makes it active for the entering player with `C5.TRANSITION_TIME` (0.85); the exit handler is
  registered at the first enter and stays; `LCMove2..5` remove box 1..4's enter handler and raise
  `LC_FLAG_DESTINATION`; `Cleanup` (main_40, from `NextMission` 09321 main_102) deletes `SneakCam1..4`.
- M11 cp6 (`07911`): `P6.NewWarrior` (main_9) is the death handler of player2 and the chain Warriors; per call
  `CamSetSecondary(Birdie.Birdie, 0, 1)` (line 217) and `CfgMultiplayerJoin(false)` at the first death (205).
- M5 cp1 (`07708` main_89-94, called from `07849`): `F.MattsCams` creates `c1Intro.StartLock`; `c1Intro.Handlers` from
  `P1.EndIntroScene`; `StartCamOn` (blend 1), `TrailRail` (`CamSetupRail(..., index 1 for player2 else 0)`, blend 1 or
  0.25), `SideRail` (index 1 for player2 else 0, blend 0.25); `c1Intro.Kill` from `P1.EnterStreets` (type-0
  `vEnterStreet`).
- M13 (`09229` main_99/100, registered in every chapter 09720/09721/09722, never removed): `EnterGraveTrain`
  (`CamSetupRail("subrail", player, ...)` default index = all rails, made active for the entering player, blend 0),
  `LeaveSub` (MainCam + `CamSetFollowPos(p, 1 for player2 else 0)` + `CamSetFollowZoom(0, same)`, blend 0).

## 2. The rows (`local/m6/cam/camD/rows/`)
All rows keep players 1-2 on the original code (the original function runs unchanged first, or the row only adds a
tick that looks at `HuGetPlayer(2)` / `HuGetPlayer(3)`), use own globals `W4P_D3*`, `W4P_D10*`, `W4P_D11*`, `W4P_D5*`,
`W4P_D13*` and `W4P_O.d3/d10/d11/d5` (originals) plus markers `W4P_O.d3m/d10m/d11m/d5m/d13m`.

| Row file | Chunk (LUACH log) | Size | What it does |
|---|---|---|---|
| `m3t.lua` | "level87_chap5_club.lua" (VERIFIED, marker 111 in camD_m3a/b, reg2p_a) | 1321 | wraps `ch5.MoveToNextBox`: original, then `W4P_D3G()` gives each player 3/4 his own `CameraCreateLocked("Tutorial02Cam", same parameters)` copy, `CameraMakeActive(copy, 0, nil, h)` (blend 0 as for player 2), `CamLockLocked(copy, h, 1)`; 500 ms tick `W4P_D3T` for late joiners while the stretch lasts; `Stealth3Damaged`, `DistractMoveBackTutorial`, `Stealth03Damage`, `AfterS03WalksBack`, `Tag9CamOut` wrapped: original, then `W4P_D3B(0)` (unlock, `MainCam` for the player); copies never deleted |
| `m10s.lua` | "level93_chapter5.lua" (VERIFIED, camD_m10b-e) | 1562 | wraps `SetupLCChase` (starts a 250 ms tick `W4P_D10T`) and `Cleanup`; the tick finds the box each player 3/4 is inside (`IsInsideBox`, first of 1..4), and on a change: `MainCam` back if he had a copy, then his own copy of `SneakCamN` (parameters table `W4P_D10P`) if box n's enter is still live (n >= `LC_FLAG_DESTINATION`); blend `C5.TRANSITION_TIME` as the original; `Cleanup` gives `MainCam` back (blended) before the original |
| `m11b.lua` | "level31_Birdie.lua" (VERIFIED, camD_m11a, reg2p_b) | 407 | wraps `P6.NewWarrior`: during the original call `CamSetSecondary` is replaced by `W4P_D11M`, which repeats a call for index 1 for every player 3/4 with index 2/3; restored after the protected call |
| `m5i.lua` | "level2.lua" (VERIFIED, camD_m5a, reg2p_b) | 1925 | wraps `c1Intro.Handlers` (starts a 250 ms tick `W4P_D5T`) and `c1Intro.Kill`; on entering one of the five boxes the tick runs `W4P_D5A` = the handler's steps for that player with his own index (StartLock copy, `CamSetupRail("introRail", h, ..., i)` + points + `CamLeadRail`/`CamModifyRail` with index i) and his own ICamOn/TrailOn/CurBox; original blend times; `Kill` gives `MainCam` back (blend 0.25) first |
| `m13s.lua` | "level9.lua" (existing row name; marker 111 in camD_reg2p_c) | 1035 | a 250 ms tick for the whole level: entering `vbInTrain[k]` -> `CamSetupRail("subrail", h, 50, {0, 0, 1.4}, 0.5, 75, i)` + the 3 points + `CamLeadRail(4, 0, nil, i)` + `CameraMakeActive(rail, 0, nil, h)`; entering `vbMainCam[k]` after the train -> `MainCam` + `CamSetFollowPos(p, i)` + `CamSetFollowZoom(0, i)`; the X6 row 0 guard on `EnterGraveTrain` stays |

Build command (two builds, one region each; region 1 holds only M3, region 2 the rest; M13 was tested in a third
pnach that reuses region 1):
```
python -I tools/lua_rows.py build --base mod --region 0x000EBA00:0x000EC000 --work local/m6/cam/camD --out local/m6/cam/camD/testA.pnach --title "camD camera rows A" local/m6/cam/camD/rows/m3t.lua
python -I tools/lua_rows.py build --base mod --region 0x000E5D10:0x000E7000 --work local/m6/cam/camD --out local/m6/cam/camD/testB.pnach --title "camD camera rows B" local/m6/cam/camD/rows/m10s.lua local/m6/cam/camD/rows/m5i.lua local/m6/cam/camD/rows/m11b.lua
python -I tools/lua_rows.py build --base mod --region 0x000EBA00:0x000EC000 --work local/m6/cam/camD --out local/m6/cam/camD/testC.pnach --title "camD camera rows C" local/m6/cam/camD/rows/m13s.lua local/m6/cam/camD/rows/m11b.lua
```
Each: `6 problems` (the known `[4p hud A]`/`[4p hud B1]` alternatives). Rows 12-14 of the LUACH table 0x000EEE00.
Sizes together 6250 characters (+ names): they do not fit one of the two camD regions; the coordinator places them.

## 3. Per-fix table
| # | Mission | Chunk | Function(s) | Change | Test | Result | Label |
|---|---|---|---|---|---|---|---|
| 1 | M3 cp5 | level87_chap5_club.lua | `ch5.MoveToNextBox` + 5 restores | own locked copy per player 3/4, locked to him; MainCam back where players 1-2 get it | camD_m3a (original + addition, P4 late join), camD_m3b (wrapper, real move-back flow), camD_reg2p_a | m3a: original only -> views 1-2 `Tutorial02Cam` 0x00CE0800 (lock list P1, P2), view 3 follow; + addition -> view 3 = copy 0x00CE1400 (lock P3), views 1-2 and the lock list unchanged; P4 joined 9600 -> his copy by the tick (4 quarters alike, t0946_p9835). m3b: wrapper -> views `1123` (P1/P2 object, P3 copy 0x00CE1400, P4 copy 0x00CE1800); `DistractMoveBack` -> split off, Dest4Cam; game calls `AfterS03WalksBack` -> 4 follow cameras (0x00C42000, 0x00CD9400, 0x00D0E000, 0x00D0F000). reg2p_a (2 players): `1100`, then follow, identical to the original | **VERIFIED** |
| 2 | M10 cp5 | level93_chapter5.lua | `SetupLCChase`, `Cleanup` + tick | own corner copy per player 3/4 via `IsInsideBox` poll | camD_m10c (blend 0 version), camD_m10d, camD_m10e (final), camD_reg2p_b | m10e: stub box 1 -> view 3 shows P3's copy (blend `to` = copy 0x00C4E400), views 1, 2, 4 follow; out -> follow; **real walk-in** (P3 at 430.1, -100.7): `IsInsideBox` box 1 = 1 -> copy shown, back next to P1 -> follow (3 cycles); real chapter end with P3 in a corner -> checkpoint 6, "level93_chapter6.lua", 0 TLB. reg2p_b: tick on, no player 3/4, chapter end -> cp 6, 0 TLB | **VERIFIED** (walk-in for box 1 only) |
| 3 | M11 cp6 | level31_Birdie.lua | `P6.NewWarrior` | `CamSetSecondary(.., 1)` repeated with index 2/3 | camD_m11a, camD_m11c, camD_reg2p_b | m11c (4 players): original alone -> Birdie only on view 2; + row -> views 3-4 too. m11a (4 players): follow +0x320 before 0xFFFFFFFF on all; after = 0x00070167 (= `Birdie.Birdie` handle) on views 2, 3, 4, view 1 unchanged; R 102 (killCount 2); second call idempotent. reg2p_b (2 players): only view 2 (player 2) = Birdie, as the original | **VERIFIED** (field); framing on screen HYPOTHESIS |
| 4 | M5 cp1 | level2.lua | `c1Intro.Handlers`, `c1Intro.Kill` + tick | own StartLock copy / rail index 2-3 / state per player 3/4 | camD_m5a (blend 0 version), camD_m5b (final), camD_reg2p_b | m5a: P3/P4 joined inside the opening boxes (real `IsInsideBox`: boxes 1-2) -> own copies (views 1, 3, 4 opening camera, view 2 follow); lead box -> view 3 = rail 0x00C9F400 with target **player 3** (RAILTGT); side box -> same rail re-set (CurBox 3); `Kill` -> views 3-4 follow, view 1 unchanged (StartLock, as the original leaves it until the scene); 0 TLB. m5b (final, blended): views 3-4 = blend to their StartLock copies 0x00D29800 / 0x00D2A000; lead -> view 3 blend to rail 0x00C9E400, target player 3; side -> CurBox 3; `Kill` -> views 3-4 blend to their follow cameras 0x00D28000 / 0x00D28C00; views 1-2 unchanged; 0 TLB | **VERIFIED** (lead/side boxes by direct inside-test replacement) |
| 5 | M13 | level9.lua | tick (whole level) | own subway rail / exit follow position for players 3/4 | camD_m13a, camD_reg2p_c | train box -> view 3 = rail 0x00C55800, target player 3; exit box -> view 3 follow, its +0x244 changed (CamSetFollowPos index 2), player 1's follow fields unchanged; 0 TLB | **VERIFIED** (direct inside-test replacement only); walk-in not tested |
| - | M8 cp3, M18, M6, M14, M16 | - | HUD prompts | none (unsafe, section 5) | camD_m11a | HUD 2 call writes into another HUD object | FAILED (by design: not implementable without engine work) |

## 4. Tests (SINGLE-PC, sandboxes 25/26, scripted bots, MTVU off)
Common command (`local/m6/cam/camD/run.sh <tag> <inst> <pnach> <players> <seconds> <callat> <probe:poll>...`):
```
python -I tests/m2/nav_probe.py <tag> tests/m2/nav/boot_to_m1_2p.txt --inst <25|26> --players <4|2>
  --script2 tests/m2/nav/p2_join.txt --script3 tests/m2/nav/empty.txt --script4 tests/m2/nav/empty.txt
  --groups "warriors-4p own view;warriors-4p hud;warriors-4p 4p;warriors-4p test call;warriors-4p 4p hud B1;
  warriors-4p 4p hud B2;warriors-4p 4p spawn;warriors-4p 4p spawn leave;warriors-4p 4p inventory;warriors-4p 4p fx;
  warriors-4p 4p markers;warriors-4p session;warriors-4p missions" --ini EmuCore/Speedhacks/vuThread=false
  --callat "3999:0041ABC0:<cp>,4009:00160D78:<entry>" --patch local/m6/cam/camD/test<A|B|C>.pnach
  --probe cam_camD_probe:<function>:<poll> ... --seconds <s> --every 4
```
Probes: `tests/m6/cam_camD_probe.py` (new). Evidence: `local/m2/<tag>/probes.json` and screenshots, consoles and
emulogs `local/m6/cam/camD/<tag>_console.txt`, `<tag>_emulog.txt`; probes copied to `evidence/M6/<tag>_probes.json`.

| Run (inst) | Pnach / players | Level jump | Players 3-4 | Probes (poll: result) | TLB |
|---|---|---|---|---|---|
| camD_m3a (25) | A v1 / 4 | M3 cp5 `0x01FD9A74` | P3 6500, P4 9600 (late) | mark 111; prep (DestractTutorial02) split off, view 1 = Tutorial02Cam; orig `1100`; add `1120`; join4 -> tick -> 4 quarters alike (t0946_p9835); back/state after 9835 not reached (run ended) | 0 |
| camD_m3b (26) | A v1 / 4 | M3 cp5 | both 5801 | mark 111; wrap `1123` (copies 0x00CE1400 / 0x00CE1800, locks P3 / P4); moveback -> split off; 8104: game's AfterS03WalksBack -> 4 follow | 0 |
| camD_m10a (26) | B v1 / 4 | M10 cp5 `0x01FD9E10` | none | chase lost before the first probe; mailbox not served on the game-over screen | 0 |
| camD_m10b (25) | B v1 / 4 | M10 cp5 | 5201 | blend 0.85 version: stub box 3 -> corner copy shown (t0597_p6110), out -> follow; GetPosition on a box gives nothing (walk skipped); **direct Cleanup with deletion -> crash** | **22** |
| camD_m10c (25) | B v2 / 4 | M10 cp5 | 5202 | blend 0 version: stub box 1 -> `0050` (copy 0x00C4E400); out -> follow; walk candidate 1 inside (R capped 999), candidate 2 outside; blend experiment views 2-3 (stay); non-blend after blend ignored (7756); direct Cleanup (3 Lua TLB, negative result 3) | 3 |
| camD_m10d (26) | B v2 / 4 | M10 cp5 | 5206 | stub in/out ok; **real walk-in** box 1 inside (110) -> copy shown, back -> follow; real end (HideoutGateTriggered) -> cp 6, "level93_chapter6.lua" | 0 |
| camD_m10e (25) | B final / 4 | M10 cp5 | 5203 | blended final row: 3 enter/exit cycles (stub, walk-in, stub), copy shown as blend `to`, P1/P2/P4 unchanged; real end -> cp 6 | 0 |
| camD_m11a (26) | B / 4 | M11 cp6 `0x01FD9E94` | both 5311 | mark 111 (4608, 5010); NewWarrior(Cody) -> secondary Birdie on views 2-4; blend experiment; HUD objects + HUD 1 control + HUD 2 write | 0 |
| camD_m11c (25) | B final / 4 | M11 cp6 | P3 5305, P4 5607 | ORIGINAL `W4P_O.d11` first: +0x320 Birdie only on view 2 (views 3-4 0xFFFFFFFF); then the row's wrapper: views 2, 3, 4 = 0x00070167; view 1 unchanged | 0 |
| camD_m5a (25) | B v2 / 4 | M5 cp1 `0x01FD9B7C` | both 5203 | mark 111; joined inside boxes 1-2 -> copies; lead -> rail target P3; side; Kill -> follow | 0 |
| camD_m5b (26) | B final / 4 | M5 cp1 | both 5203 | final row: copies, rail target P3, Kill -> follow (all as blend targets) | 0 |
| camD_m13a (25) | C / 4 | M13 cp1 `0x01FD9F9C` | P3 8503 | train -> rail target P3; exit -> follow pos index 2 only; blend control views 2-3 | 0 |
| camD_reg2p_b (26) | B v2 / **2** | M10 cp5 -> M11 cp6 -> M5 cp1 (3 jumps) | - | M10 marks 111, tick on, real end -> cp 6; M11 marks 111, NewWarrior -> view 2 only (original); M5 mark 111, Kill wrapper R 100 | 0 |
| camD_reg2p_a (26) | A final / **2** | M3 cp5 | - | marks 111; wrap `1100` (= original); moveback -> Dest4Cam; game's AfterS03WalksBack -> follow 0x00C42000 / 0x00CD9400 | 0 |
| camD_reg2p_c (25) | C / **2** | M13 cp1 | - | marks 111 at 8514 and 9506 (helpers, row, tick running); row state empty (no player 3/4); players 1-2 follow cameras 0x00CC6000 / 0x00CF9800 unchanged | 0 |
| camD_ctl_orig2 (26) | B / 2, groups `M1;test call;missions` only | M10 cp5 | - | blend control: test camera taken before AND after a blend (100 / 100) | 0 |
| camD_ctl_4p2 (26) | B / 2, all groups | M10 cp5 | - | blend control: taken before a blend (100), NOT after (0, blend camera stays, elapsed 18.3 s) | 0 |
| camD_ctl_orig (25) | - | - | - | FAILED (method): the `GROUPS` shell variable is reserved in Git Bash, only `[warriors-4p M1]` was enabled; no result | - |
| camD_ctl_g4p (26) | B / 2, groups `4p;test call;missions` | M10 cp5 | - | bisection: test camera taken before a blend (100); the blended change itself then **crashed** in `FUN_00120230` (loop over the render cameras, null entry: pc 0x00120270 addr 0x0/0x218/0x21C) - `[4p]` alone is not a working subset | **22** |
| camD_ctl_no4p (25) | B / 2, all groups except `4p` | M10 cp5 | - | bisection: crashed during boot (pc 0x0018CC60, 50 TLB misses) - the other groups need `[4p]`; no result | **50** |

Row versions: A v1 = `m3t` with `Stealth03Damage` restore blend 1 (now 0; that path was not exercised); B v1 = M10/M5
with blends and copy deletion; B v2 = blend 0 and no deletion; B final = original blend times, no deletion (the
current files). M11 and M13 rows unchanged since the first build.

## 5. HUD button prompts on HUD 2/3 (brief item 6)
- **Static (VERIFIED code):** `HUDTurnOnActionCycleAnim(a, t, n, b1, b2, hud)` (0x0036FC80) -> `FUN_001B5A90` ->
  `FUN_001B3DD0`: `a0 = HUD + hud*0x590 + 0x6B40` with no bound check (0x001B3DD0-0x001B3DE8), then `FUN_0019F270` writes
  +0x440..+0x45C and calls `FUN_001A2120`/`FUN_001A2910`/`FUN_001E7300` on it; `HUDTurnOffActionCycleAnim(hud)` ->
  `FUN_001B3DF8` writes +0x45C = 0. The prompt ("target/pickup") objects are built only for i < 2 (`FUN_001AD588`,
  `sltiu v0,s2,2` at 0x001ADB78, not patched) and drawn/updated only for 2 (HudUpdate loops clamped by MIN2 in
  `[4p hud B1]`, `m2_hud_full.md` line 164). No pnach line touches 0x001B3DD0/0x001B3DF8/0x0019F270.
- **Runtime (camD_m11a, VERIFIED):** objects at 0x00607380 and 0x00607910 have vtable 0x00539270; "object 2" at
  0x00607EA0 has vtable **0x0053A348** (another HUD object). `HUDTurnOnActionCycleAnim(3, 0.15, 2, 73, 73, 1)` (control)
  set HUD 1's fields (0x49, 0x49, 3, 1, 0, 4, 2, 1); the same call with hud 2 wrote 0x49, 0x49, 3, 0, 0, 0, 2, 1 into
  0x00607EA0+0x440..+0x45C (all 0 before). No TLB miss in the remaining ~600 polls and nothing visible on player 3's
  quarter (the object is never drawn as a prompt). So a prompt for player 3/4 needs two more prompt objects plus
  widened HUD loops (the full HUD plan B in `m2_hud_players34.md` 4.1-4.2) - an engine change, not a Lua row.
- **The 5 spots** (all on type-2 boxes or 2-player stretches; none can give players 3-4 their own prompt today):

| Spot | Script | HUD index used | Players 3-4 today | Own prompt possible? |
|---|---|---|---|---|
| M6 cp4 `ch4.JumpWarnOn` / `JumpWarnOff` | 08022:755-790 (main_36-38, `vbJumpWarn` type 2) | 0 player, 1 player2, else 0 | never fired for them | no (engine) |
| M8 cp3 `StartChase` (D24) | 08838:197-199 | 0 and 1 | D24 row draws only HUD 0 (one shared icon, the user's choice) | no; D24 decision stands |
| M14 `C7.ShowButtonTri/X` (08186) + `C9.ReadyRollingStart` (08187) | 08186:414-426 (main_23-25, `Trig[*]` type 2), 08187:296-298 | 0 player, **else 1** | never fired for them (a direct call for P3 would light player 2's prompt) | no (engine) |
| M16 `chase.FenceHint` / `ManualHintOff` | 08262:3129-3147 (main_103-105, `vbHint` type 2) | 1 player2, else 0 | never fired for them | no (engine) |
| M18 cp2 `C1.Random2` (D24) | 09110:429-446 | 0 and 1 | D24 row draws only HUD 0 | no; D24 decision stands |

Report to the coordinator (M8 cp3 and M18 are D24's): `HUDTurnOnActionCycleAnim`/`HUDTurnOffActionCycleAnim` must
never be called with 2 or 3 (it writes into an unrelated HUD object); the D24 rows already keep `f == 0` only.

## 6. What could not be done / open questions
- M13: no real walk into the train (only the inside test replaced; the train is ~118 units from the cp1 start);
  player 4 did not join in that run.
- M11: no real Warrior death observed (direct call); the on-screen framing with Birdie as secondary target for player
  3/4 is HYPOTHESIS beyond the field value (camD_m11c `t0268_p6816.png`: screen 3 frames Birdie on the walkway after
  the call, not before at `t0260_p6580.png`).
- Root cause of the "blend stays / non-blend ignored" difference (negative result 2): not found. The blend camera's
  update `FUN_00143590` hands the view back with `FUN_0011EE08(f21, to, 0, own index, -1)` once elapsed >= duration
  (`c.ole.s` at 0x001438A4, call at 0x001438E8); a scan of the ELF for `lui 0x5E` + camera-array offsets
  (0x9148-0x918F) finds all 67 references patched by `[warriors-4p 4p]` except 0x0011E844, which the patch jumps over.
  Group bisection (camD_ctl_g4p, camD_ctl_no4p) was inconclusive: `[warriors-4p 4p]` alone crashed on the blended change
  (`FUN_00120230` reads a null render camera), and all groups without `[4p]` crash at boot. Suggested next step for the
  coordinator: watch active/render/blend of view 2 across one blend in the original 2-player build (arrays
  0x005D9148/0x005D9150/0x005D9180) and in ours (0x000F0800/0x000F0810/0x000F0870) to see where the hand-over differs.
- M3 restore through `Stealth03Damage` and `Tag9CamOut` and M3/M5/M10 late joins after the stretch were not exercised
  separately (same `W4P_D3B` / tick code as the tested paths).
- Open question for the coordinator: with the current patch set, rows that blend a player 3/4's view (M10, M5) leave a
  finished blend camera on that view, as the original scripts' blended changes now do on player 2's view; any later
  non-blended camera change on that view (original script or another agent's row) then has no effect. This is a
  difference to the unmodified game (F-CAM-camD-7) and should be fixed at engine level; the camD rows only avoid
  making it worse (same blend times as for player 2, blended restores after their own blends).

## 7. Files
- `local/m6/cam/camD/rows/m3t.lua`, `m10s.lua`, `m11b.lua`, `m5i.lua`, `m13s.lua` (the rows); `testA/B/C.pnach`,
  `missions_A/B/C.txt` (builds); `run.sh`, `run_groups.sh` (run helpers); consoles/emulogs per run.
- `tests/m6/cam_camD_probe.py` (new probe module).
- `evidence/M6/camD_*_probes.json` (copies of the runs' probes.json).
- Not changed: `mod/`, `mod/w4p_m1.pnach`, emulator, other probe files, nav_probe.

## 8. Draft findings (placeholder IDs; the coordinator assigns F-numbers)
| ID | Claim | Label | Evidence |
|---|---|---|---|
| F-CAM-camD-1 | M3 cp5: players 3-4 get their own copy of the stealth-tutorial locked camera (locked to themselves) when players 1-2 get `Tutorial02Cam`, also when joining during the stretch, and their follow camera back at the original's restore points; players 1-2 unchanged (same object, same lock list) | VERIFIED | camD_m3a, camD_m3b, camD_reg2p_a (section 3 row 1) |
| F-CAM-camD-2 | M10 cp5: `IsInsideBox` sees player 3 inside a type-2 box; a 250 ms tick gives players 3-4 their own sneak-corner camera on entering and the follow camera on leaving; real chapter end unaffected | VERIFIED (walk-in box 1; boxes 2-4 not walked) | camD_m10d, camD_m10e, camD_reg2p_b |
| F-CAM-camD-3 | M11 cp6: `P6.NewWarrior` gives players 3-4's follow cameras Birdie as secondary target like player 2's | VERIFIED (camera field); on-screen framing HYPOTHESIS | camD_m11a, camD_m11c, camD_reg2p_b |
| F-CAM-camD-4 | M5 cp1: players 3-4 get the clinic-intro opening camera (own copy), their own intro rails (index 2/3, target = themselves) and the follow camera back at the street scene | VERIFIED (opening boxes real; lead/side boxes by inside-test replacement) | camD_m5a, camD_m5b, camD_reg2p_b |
| F-CAM-camD-5 | M13: players 3-4 get the subway rail (own index) in the train and the exit follow position on their own follow camera | VERIFIED by direct inside-test replacement only | camD_m13a |
| F-CAM-camD-6 | `HUDTurnOnActionCycleAnim`/`HUDTurnOffActionCycleAnim` with HUD 2/3 write into an unrelated HUD object (only 2 prompt objects exist); no player 3/4 prompt is possible without an engine change | VERIFIED (static + runtime) | section 5, camD_m11a |
| F-CAM-camD-7 | With the full patch set a finished blend camera stays on the view and later non-blended camera changes are ignored (player 2 included); with only the 2-player base groups they are not ignored | VERIFIED (runtime difference); cause open | camD_ctl_4p2, camD_ctl_orig2, camD_m13a, camD_m10c |
| F-CAM-camD-8 | Deleting a camera that a finished blend still references crashes the game; `CamDelete` protects only cameras active on views 1-2 | FAILED TEST (row v1) / VERIFIED code | camD_m10b (22 TLB), `FUN_0011E440` |
| F-CAM-camD-9 | The original gives player 2 the same locked camera object as player 1 (both views render it); a locked camera's lock list has 2 slots | VERIFIED | camD_m3a (render[0] = render[1] = 0x00CE0800), `FUN_004DB928` |

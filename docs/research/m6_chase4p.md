# M6 D24: players 3-4 play the 2-player chase stretches (M18 car escape, M8 cart chase) (2026-10-12)

## Plain-English summary
- **What D24 asked.** In two story stretches the game lets only players 1-2 play: the Mission 18 car escape (players 1-2
  tap a button to outrun the Rogues' car while the computer runs Cochise and Vermin) and the Mission 8 cart chase
  (players 1-2 tap to outrun a runaway cart while the computer runs Snow and Ajax). D24: players 3-4 join there **on
  exactly those characters** and play them **the same way as players 1-2**.
- **Baseline first (before any change):** with the mod as it was, two tapping bots **won the 2-player escape**
  (checkpoint 2 -> 3 after about 23 s, 4 instances in lockstep, 0 hash mismatches, 0 TLB misses). Players 3-4 could not
  be in it (the script switches joining off) and joined only later on the beach (round 2).
- **Mission 18 now:** at the start of the escape player 3 becomes **Cochise** and player 4 **Vermin** (the game's own
  join, aimed at those two humans), they run in the chase gang and **tap exactly like players 1-2** (same button for
  everybody, the game's rule: it changes when any runner reaches one of three marks). If anybody is caught the group
  fails as with 2 players ("You got wrecked"), and the retry revives and places all four. Example from the tests:
  all four runners tapping -> escape won, checkpoint 3.
- **Two game limits had to be fixed for 4 runners:** (1) when one runner reached the end, the game removed the tap
  command from **everybody** unless exactly 2 players were in the game - A/B test: without our fix the 4-runner escape
  failed every time (the last runners froze and were caught); with it, it is won; (2) the beach-fight cameras of players
  3-4 had no target (a wall instead of the fight) - fixed in the engine (RAILTGT), and players 3-4 now get the same wide
  beach cameras as players 1-2 on their own screens.
- **Tap icon:** the game showed the button icon twice (one per player HUD) on the one shared picture. Now exactly one
  icon (player 1's HUD) is shown, the same on every PC (the user's final choice: one button for everyone, one icon).
- **Mission 8 now:** players 3-4 join at the start of the cart chase as **Snow and Ajax** and tap-run in front of the
  cart on the two lanes of players 1-2 (like M18, where the AI already shares the lanes). The tunnel exit, the scares and
  the smoke jets still react only to players 1-2 (as in the original, where only the two players could reach them).
- **After the stretches:** the game itself swaps the squad (M18 beach, M8 escape scene); players 3-4 leave there (our
  earlier X3 wrapper) and come back as soon as the game opens joining again: M8 at checkpoint 4, M18 at beach round 2.
- Everything: SINGLE-PC, bots, no humans, no impairment. Human play and LAN/internet are not tested.

Build: The Warriors SLUS-21215 v1.03 (`local/disc/SLUS_212.15`, read-only), fork build w4p-m6-3 (no emulator change).
Function and structure names are OUR labels (the ELF is stripped); addresses static unless marked dynamic. Labels:
VERIFIED (pointer), HYPOTHESIS, FAILED TEST. Script lines `WAD:line` = `local/analysis/pseudo/<WAD>_*.lua`.

## 1. Static facts (VERIFIED code/script unless marked)

### 1.1 Tap control
- `HuSetButtonTapControl(h, on, flags[16], car)` binding 0x00358930 -> core `FUN_00234318`: on = u64 status flags at
  `*(human+0xD4)` bit 44 (0x100000000000, set/test `FUN_002265D0`/`FUN_002265F0`), movement behaviour `FUN_00242CE0`,
  counters human+0x670/+0x674 cleared (`FUN_002445F8`), up to 16 path flags copied to human+0x67C with the next index at
  +0x678 (`FUN_00244640`), car handle +0x6BC (`FUN_002446A8`), the player's other commands off (`FUN_001463E0(h, 0)`),
  command 45 added with `FUN_00147430(45, 2, 0x40, 0)`. The binding copies the flag table back into the Lua table
  unchanged, so two runners can share one table.
- `FUN_00242CE0` runs the tap logic only for a player-controlled brain (brain+0x1B != 0); a runner who is
  dead/downed (`FUN_00227E60`) leaves tap mode.
- **Commands** (`FUN_00147430` = Lua `AddCommand(id, type, button, threshold)`, binding 0x00369518): one table per type
  (type 2 at 0x005DDDD0, count u32 0x0050B744, 12-byte entries: u16 pad-enable mask +0 (0xFF at creation), u32 id +4,
  u16 button +8, u16 pressure threshold +0xA). `AddCommand` first removes an existing entry with the same id
  (`FUN_00147218` / `FUN_00146B90`), so the game keeps **one** entry per id. The 4th argument is a **pressure threshold**,
  not a controller: `FUN_00147940` (per brain, pad = brain+0x19) fires an entry for pad p when the pad-mask bit p is set,
  the button was just pressed (type 2: `FUN_00144BF0`) and, if the threshold is non-zero, the button's analog pressure
  (`FUN_001476F0`: pad state +0x34 + button index) is above it. Per-runner buttons would therefore need several id-45
  entries with single-pad masks written by our own code (feasible at table level, not through the game's API); not
  built because the user chose one button for everybody.
- **2-player assumption (the bug D24 hit):** tap off in `FUN_00234318` (0x00234490-0x0023451C): `if count == 2`, keep
  command 45 for the partner (per-player removal `FUN_001467A8(h, 45, 0)`) when the partner (the other of players 1/2)
  is present, not downed and still tapping; **any other count -> `FUN_00146B90(45)` = removed for everybody**.

### 1.2 M18 car escape (09110 = "level84_chase.lua", cp2; main 09030)
- `InitChase` 09110:181-205: `HuChangePlayerGang(GangWarChase)` (Swan 9 prio 3, Snow 36 prio 4, 09030:1220-1223); Cochise
  16 / Vermin 27 in `GangWarRun` (type 0, 09030:1228-1231); then `C1.StartLevel` (BrDead players, `SetMsgHandler` of
  every `VCarChaseTrig` box (type 0, 09030:1355-1364) -> "C1.CAMChange", `C1.PlayCar`: `CfgMultiplayerJoin(false)`,
  car scene). `C1.StartTheRun` (scene callback): AI `GoalRunCarrotRun(Vermin, Path_fSnRun_01)` / `(Cochise,
  Path_fSwRun_01)`, players `GoalTravelPath`, `GangSetMsg(GangWarChase, 18, "C1.KillButtons")`; 2 s + 1 s later
  `C1.Random2` (one `C1.chaser` for all, icon on HUD 0 and HUD 1), 1 s later `C1.StartMash` (players tap on,
  `DelCommand(45); AddCommand(45, 2, {16,32,128,64}[chaser], 0)`).
- `C1.CAMChange` 09110:326-391: player at `VCarChaseTrig[5]` -> auto-run to `Path_flag_01`, tap off - **a non-`player`
  takes player 2's branch** (turns off player 2's tapping); `[10..12]` (first player only) -> `C1.Random2`; `[1..3]`
  shared view-0 cameras.
- Fail: gang message 18 on `GangWarChase` -> `C1.KillButtons` -> `StopTheGame` -> `EndCar` with `C1Failed` ->
  `RunMissionFailed` ("You got wrecked"); `EndCar` also fails if `player`/`player2` is not alive. Retry =
  `C1.RestartCarChase` (revives/teleports `player`/`player2`, teleports `Vermin`/`Cochise` by name). Win: `EndCar` ->
  `StartTheBeach` -> `HuChangePlayerGang(GangWarriors)` -> `NextMission` (checkpoint 3, "level84_final.lua").
- The gang message receiver `FUN_00164C20` has player-specific handling of messages 17/18 (downed/revive with a Flash in
  the inventory); which event sends 18 here is HYPOTHESIS ("a member was knocked out"); the runtime behaviour is what
  counts (section 3).

### 1.3 M8 cart chase (08838 = "level81_chase.lua", cp3; main 08780)
- Players 1-2 **run on foot in front of a runaway cart** with tap control (`PlayerControl` 08838:232-243:
  `HuSetButtonTapControl(hCleon, true, C3.WarriorPath1, Objects.dyn_coney_car_a)` and player 2 with `WarriorPath2`);
  objective "MOVE! Don't get run down by the cart". AI Snow/Ajax only follow blockers (`StartChase` 08838:170-176).
- Joining is off for the whole stretch (`GameStart` 08838:83 ... `Cleanup` 08838:668). `GameStart` loops over
  `Warriors` (bytecode main.1: `GETGLOBAL 'Warriors'`) and BrDeads everybody; `PlayerControl` frees only Cleon/Swan.
- `C3.ChaseCam` (main.11) at `vChaseCam[6]` loops over `Warriors` and teleports `hSnow`/`hAjax` to the jump flags with
  `BrDead(true)` without a player check. `vChaseCam[*]` are **type-2** boxes (08780:1237-1242: only players 1-2 fire
  them, m6_x6_fixes.md 1.1), so `RunCam2..7` never run for players 3-4. `vTunnelExit`, `vSpider`, `vTera`, `vSpook`,
  `vStrobe*`, `vSmoke*` are type 0 (any human); their handlers check only `HuIsAPlayer`.
- End: `C3.TunnelExited` -> `RunEscapeScene`: tap off for Cleon/Swan, `HuChangePlayerGang(GangWarAfterChase)` (X3:
  players 3-4 leave), escape scene, `NextMission` (cp4); `Cleanup` switches joining on (X11 re-joins 3-4 in cp4).

### 1.4 HUD icon
`HUDTurnOnActionCycleAnim(..., hud)` (binding 0x0036FC80 -> `FUN_001B5A90` -> `FUN_001B3DD0(HUD 0x00600840, hud)`)
draws on the target/pickup object HUD+0x6B40 + hud*0x590; only two exist (0xB20 bytes, built by `FUN_001AD588`,
m2_hud_players34.md table) - HUD 2/3 would hit HUD+0x7660, which is not such an object. Not used.

### 1.5 Rail cameras on views 3-4 (beach fight, m6_camera_parity.md 1.2)
The rail target picker `FUN_0013B7B8` (vtable +0x134 update `FUN_0013D010`) collects targets from tracked-list entries
0-1 only and keeps slot [player index] only if index < count (0x0013B948); a rail of view 3/4 gets no target. VERIFIED
code; runtime: d24dev2 (no RAILTGT) beach views 3-4 showed a wall (`local/m2/d24dev2/t0404_p10749.png`).

## 2. What was changed
`mod/m2/missions.txt` (`[warriors-4p missions]`), `mod/m2/spawn.txt` (`[4p spawn]`), `mod/m2/camtarget.txt`
(`[warriors-4p 4p]`); `mod/w4p_m1.pnach` regenerated (**7414 addresses, 6 problems** = the known `[4p hud A]`/`[4p hud
B1]` alternatives; byte-identical to `local/m6/d24/test5.pnach`, the pnach of the final runs). Generator and sources of the new words: session scratchpad `d24/` (gen.py, apply.py, *.s, *.lua).

| Part | Where | What |
|---|---|---|
| **W4P_JoinAs(handle)** (new Lua C function) | REGW 0x000ED000 (hook 0x0037D6C8, was 0C102824 `jal 0x0040A090`, the registration of HuSetButtonTapControl in `FUN_0037D420`); JOINAS 0x000ED040-0x000ED18C; counters N_CALL 0x000ED3E0, N_OK 0x000ED3E4, LAST_PAD 0x000ED3E8 | registers a second global "W4P_JoinAs" in every level's Lua state; the first pad 0-7 that is connected (pad state 0x005DD810 + pad*0x50, +0x4C) and has no character (+0x42 = -1) joins through the game's UpdateJoin `FUN_0041A460(GameMgr, pad)` with the join flag GameMgr+0x56E8 set for that call only (restored; no `CfgMultiplayerJoin`, so no camera refresh), and PX takes exactly the given AI human; only for players 3-4 (count 2-3 before); returns 1 or nil |
| X2W | `spawn.txt`: 0x000E1B44 `jal 0x000E2580` (was `jal 0x000E1C60` X2SEL); X2W 0x000E2580-0x000E2594; WANT 0x000E25A0 | WANT != 0 -> PX takes that human; else X2SEL as before |
| **TAPOFF** | hook 0x00234490 `j 0x000ED200` (was 24030002), 0x00234494 nop (was 8E44489C); cave 0x000ED200-0x000ED284 | tap off keeps command 45 (per-player removal) while **any** other player is present, not downed and still tapping; else removes it (original). Identical to the original for 1-2 players |
| **RAILTGT** | `camtarget.txt`: 0x0013B944 `j 0x000F0940` (was 8E030348), 0x0013B948 nop (was 0043102A); cave 0x000F0940-0x000F0994 | rail camera of player index 2/3: target = that player's own human (GameMgr+0x228+4*i), like the follow-camera fix; views 1-2 run the original instructions (m6_camera_parity.md 2.4) |
| LUACH table moved | 0x000E7A70/74 `lui s2,0x000F; addiu s2,s2,-4608` (was 0x000E7F00) | rows at **0x000EEE00** (64 rows to 0x000EEFFF; rows 13-63 free); 0x000E7F00-0x000E7F7F free again; `tests/m2/x6fix_probe.py` LC_TAB updated |
| Row 10 "level84_chase.lua" (new) | source 0x000ED400 (3313 characters) | M18 escape, section 2.1 |
| Row 11 "level81_chase.lua" (new) | source 0x000EE100 (1916 characters) | M8 cart chase, section 2.2 |
| Row 4 "level84_final.lua" (replaced) | source 0x000EE880 (1147 characters; was the m18 guard at 0x000EC7A0-0x000EC82B, now free) | M18 beach cameras for players 3-4, section 2.3 |

### 2.1 M18 escape row (wrappers; players 1-2 keep the original code)
- `C1.StartLevel` (InitChase and every retry): for Cochise then Vermin (`WarRun` humans): if AI -> `W4P_JoinAs(h)`; a
  joined runner moves into `GangWarChase` (the fail gang), `BrSetReactToViolence(false)`, `HuSetNoReact(true)`,
  `BrDead(true)`, `HuSetTireless(true)` (what InitChase/StartLevel do for players 1-2); a 500 ms tick starts.
- `C1.StartTheRun`: runners get `BrFlush` + `GoalTravelPath` on the AI's own lanes (Cochise `Path_fSwRun_01`, Vermin
  `Path_fSnRun_01`) instead of the AI carrot run.
- `C1.StartMash`: before the original (so the original's `DelCommand/AddCommand(45, chaser)` stays last), runners get
  `BrDead(false)`/`BrFlush` on the first call and `HuSetButtonTapControl(h, 1, FlagTable1/2, car)`.
- `C1.Random2`: during the original call `HUDTurnOnActionCycleAnim` draws only for HUD 0 -> **one icon**.
- `C1.CAMChange`: a runner at `VCarChaseTrig[5]` gets player 2's treatment on himself (auto-run, tap off); a runner at
  `[10..12]` runs the original (button change for everybody, like a player); other boxes and any other player 3/4
  are ignored (they took player 2's branch before).
- `C1.KillButtons` / `C1.EndCar`: runners' tap off; `EndCar` also fails the run if a runner is not alive (parity with
  `player`/`player2`). `C1.RestartCarChase`: runners revived, normal mode, health 1800 before the original (which
  teleports Cochise/Vermin by name; X4 pulls them near player 1 first).
- Tick: a runner who is no longer a player (left the session) gets tap off, back into `GangWarRun`, BrDead off and, if
  the run is on, the AI carrot run of the original (like `C1.SetPlayerOff` for player 2).

### 2.2 M8 cart-chase row
- `GameStart`: Snow then Ajax `W4P_JoinAs` before the original (which BrDeads all `Warriors`).
- `StartChase` (the moment the AI Snow/Ajax start running; the icon appears here too): after the original, a player 3/4
  Snow/Ajax gets `BrFlush`, `BrDead(false)` and `HuSetButtonTapControl(h, true, WarriorPath1 (Snow) / WarriorPath2
  (Ajax), Objects.dyn_coney_car_a)` - the lanes of players 1-2 (the AI also runs 1-5 units beside them; the coordinator's
  2-player lane run d24m8lanes). `PlayerControl` (players 1-2 get control 3.5 s later) repeats it for anybody not yet
  tapping. First version gave players 3-4 control only at `PlayerControl`: FAILED TEST (section 3, d24dev_m8c).
- `RunEscapeScene`: runners' tap off before the original. `StartChase`: one icon (HUD 0).
- `C3.ChaseCam` at `vChaseCam[6]`: during the original `hSnow`/`hAjax` read -1 for a tapping player 3/4, so they are not
  teleported/frozen at the jump flags (players 1-2 are not either).
- `C3.TunnelExited`, `SpiderTriggered`, `TeraTriggered`, `SpookTriggered`, `Strobe1-4Triggered`, `RunJets1-3`:
  `W4P_G34` (only players 1-2, as in the 2-player original).

### 2.3 M18 beach cameras row ("level84_final.lua")
`C5.SetRailCam`, `C5.MoveInFOV`, `C5.MoveOUTFOV` map the camera index player -> 0, player2 -> 1, players 3/4 -> 2/3
(`W4P_P34`): a player 3/4 gets `C5.SetupRail2/3(t, h, 2/3)` (fov 80/65, the fRail points) on his own view; every
`SetRailCam(player)` of the script also sets up players 3-4; a 500 ms tick gives a newly joined player 3/4 his rail once
players 1-2 use theirs. Needs RAILTGT.

## 3. Tests
All SINGLE-PC, scripted bots (tapping = all four face buttons every 3 polls held 2 polls, or Cross only in M8), no
humans, no impairment, MTVU off. 4-instance runs: `tests/m6/chase4p_run.py` (lockstep on loopback, SessionPolicies on,
PINE samples of the second instance every 3 s -> `local/m2/<tag>/chase_samples.json`, summary `evidence/M6/<tag>.json`);
single-instance runs: `tests/m2/nav_probe.py` with `tests/m6/chase_probe.py` probes (`evidence/M6/<tag>_probes.json`;
"errors" there are PINE reads before boot/after the stop). Several runs shared the PC with 8-17 other emulators (other
agents), so speed was 20-100 %; lockstep results do not depend on speed.

| Run | Setup | Result | Hash points / mismatches / TLB |
|---|---|---|---|
| **d24base_m18** (4 inst., before any D24 change, mod pnach 5666) | M18 from cp1, players 1-2 tap from poll 8000, players 3-4 no input | **2-player escape won**: cp2 at poll 8286, tap mode on 8467, finish 8739/8830, **cp3 at 8972**; players 3-4 joined only at beach round 2 (13681, X11, as spawned Warriors) | 696 / **0** / 0 |
| d24dev1 (1 inst., first rows) | M18 cp2 jump, all four tap | **Cochise = player 3 (index 2, HUD 2), Vermin = player 4 (index 3, HUD 3)**, W4P_JoinAs 2 calls / 2 joins (last pad 2), all four in gang 0x5E8450 (WarChase), all four tap (flag index 3 -> 5/6), players 1-2 finished first (6600) and players 3-4 kept tapping to the end (6750); **cp3 at 6900** (won); count 4 -> 2 at the beach swap (X3); 'views' 1 throughout | - |
| d24dev2 (1 inst.) | + one icon, beach row without RAILTGT | escape won again (cp3 ~6900); **one icon** `t0256_p6474.png` (before, d24dev1: two icons `t0251_p6347.png`, `t0257_p6528.png`); beach: players 3-4 got rail cameras (render = rail[2]/[3]) but **no target: views 3-4 show a wall** (`t0404_p10749.png`) | - |
| **d24ab_notapoff** (1 inst., A/B) | final rows, **TAPOFF hook removed** | attempt 1: player 1 finishes (6550) -> players 2-4 lose the tap command (tap off at flag 5, not at the end) -> Vermin caught (hp 1, down), mission failed (mode 0x005E5DC0, 6850); attempt 2 the same (Cochise caught, 7750). **FAILED TEST of the original rule with 4 runners** | - |
| d24dev3_beach (1 inst.) | M18 cp3 jump, players 3-4 join by UpdateJoin probe at 6300, RAILTGT + beach row | stage 2 (from ~10050): views 4, render = rail for all four views; **views 3-4 frame their own players on the beach** (`t0420_p11339.png`) | - |
| **d24fin_m18win** (4 inst., test4 pnach) | M18 from cp1, all four tap from 8000 | cp2 at 8020 with **4 players** (W4P_JoinAs 2/2), all four tap (flag index to 5), **cp3 at 8731** (won); beach round 2: players 3-4 back at 11324 (X11), **players 3/4's own PCs show the wide beach rail** (`s2_t0560.png`, `s3_t0570.png`; before D24: close follow cameras, `local/m2/d24base_m18/s2_t0570.png`, `s3_t0544.png`); player 3's PC during the escape: the shared chase picture without the waiting message (`s2_t0334.png`) | 491 / **0** / 0 |
| d24fin_m18loss (4 inst., test5) | M18 "cp2" jump, slot 2 gap 5000-6800 | the gap missed the chase (the jump's checkpoint was not honoured, see 4.5: the level loaded at cp1 and the intro played until 6884), so all four tapped: **won** (cp2 6884 -> cp3 7567) | 411 / **0** / 0 |
| d24fin_m18loss2 (4 inst., test5) | same, gap 6800-7600 | intro skipped by the four players' votes, chase at 5313 -> gap missed again; **won** (cp3 6006) | 383 / **0** / 0 |
| d24dev_m8c (1 inst., first M8 row) | M8 cp3 jump, all four tap Cross | players 3-4 joined as Snow/Ajax but got tap control only at `PlayerControl` (3.5 s after the AI starts): **run down at their start spots before moving (hp 1, down, flag 0) - FAILED TEST**; players 1-2 escaped, cp4 | - |
| **d24dev_m8d** (1 inst., final M8 row) | same, control at `StartChase` | **all four tap-run side by side** (flag index 3 -> 4 -> 5 -> 8, nobody down), players 3-4 not teleported at `vChaseCam[6]`; escape scene, players 3-4 released (X3, tap off), **cp4 at 5400**; one Cross icon per quarter (`t0353_p4997.png`; before: two per quarter, `local/m2/d24dev_m8b/t0268_p6501.png`) | 0 TLB (inst13 emulog) |
| d24fin_m8 (4 inst.) | M8 "cp3" jump | **invalid**: the level loaded at cp1 (brawl, 4.5); 0 mismatches over 227 points | 227 / 0 / 0 |
| **d24fin_m18loss3** (4 inst., test5 = final pnach) | M18 cp2 jump (movie-skip fix), all four tap from 4000, **player 3 does not tap 4000-6999** | **loss/restart like 2 players:** six times player 3 (Cochise) is caught (down) -> "GAME OVER - You got wrecked" (`s3_t0408.png`), 'Last checkpoint' = the script's retry callback `C1.RestartCarChase` (no level reload: still 4 players, the same Cochise/Vermin; the caught player 3 is revived: down flag cleared in the next attempt); the 6th attempt (player 3 tapping again from 7000 but already behind) fails too; **7th attempt won: cp3 at 8179** | 494 / **0** / 0 |
| **d24fin_m8b** (4 inst., test5 = final pnach) | M8 cp3 jump (movie-skip fix), all four tap Cross from 4400 | attempt 1: the chase began before the bots tapped -> all four run down -> GAME OVER -> 'Last checkpoint' = level reload (count 0 at 4599); players 3-4 re-joined **as Snow and Ajax** at `GameStart` (W4P_JoinAs 4 calls / 4 joins in total), **all four tap-run** (flag index 1 -> 8, nobody down), escape scene at 5315, **cp4 at 5362**, players 3-4 back at 5398 (X11: player 3 Ajax, player 4 Snow) | 269 / **0** / 0 |

## 4. Open points and negative results (read these first)
1. **FAILED TEST (original rule), d24ab_notapoff:** without TAPOFF, a 4-runner escape always fails (the first runner to
   finish removes command 45 for everybody, `FUN_00234318` 'count == 2' branch). TAPOFF is required for D24.
2. **FAILED TEST (first M8 design), d24dev_m8c:** players 3-4 given control at `PlayerControl` like players 1-2 were run
   down at their start spots (the AI they replace starts running 3.5 s earlier, at `StartChase`). Fixed: control at
   `StartChase` (d24dev_m8d, d24fin_m8b).
3. **Test-tool errors (method, not the game):** (a) the M8 level-table entry given in the task (0x01FD9D2C) is not an
   entry (`0x01FD996C + 7*0x84 = 0x01FD9D08`; with 0x01FD9D2C the game loaded "level100", run d24dev_m8); (b) in
   4-instance runs with SessionPolicies a single player cannot skip the Mission 1 intro movie, so the level jump came
   during the movie and the jump's `SetCheckPoint` was overwritten (levels loaded at checkpoint 1: d24fin_m18loss,
   d24fin_m18loss2, d24fin_m8; HYPOTHESIS: Mission 1's own start after the movie sets checkpoint 1). Fixed in
   `tests/m6/chase4p_run.py`: every slot votes to skip the movie (3650-3750); d24fin_m18loss3/d24fin_m8b loaded the
   asked checkpoint. (c) d24fin_m18loss/loss2 missed the loss window for that reason (they count as extra 4-player wins).
4. **Players 3-4 leave at the end of each stretch** (the game's own squad swaps, X3) and re-join when the game opens
   joining: M18 at beach round 2 (`C5.StartRound2`; in d24fin_m18win 2593 polls = about 86 s after the escape), M8 at
   checkpoint 4 (d24fin_m8b: 36 polls after cp4). At the beach they become spawned Warriors (player 1's gang has no AI
   member then), not Cochise/Vermin - keeping them on Cochise/Vermin through the beach would need the beach script's
   companion handling (they are scene actors / ring spectators there); not done.
5. **M8 cameras of players 3-4:** their own follow cameras (views 3-4); the cart-chase rails `RunCam1` (and the
   section cameras `RunCam2-7`, type-2 boxes = players 1-2 only) are not mirrored for them (m6_camera_parity.md M8 rows;
   left to the camera-parity work). M18 escape: one shared view for everybody (views 1), nothing to mirror.
6. **One icon:** the game's own icon of HUD 0 (player 1's HUD position) is the only tap icon in M18 and M8; HUD 2/3 icons
   are impossible without new HUD target objects (1.4). In M8's split views the per-view HUD shows that one icon in every
   quarter, players 3-4's included (they tap the same Cross).
7. **Per-runner buttons (user option B, not chosen):** possible only with our own command-table entries (1.1); not built.
8. **Leaving mid-chase** (M18 tick: the runner turns into an AI runner like `C1.SetPlayerOff`) and **joining with only
   one extra player** are implemented but not exercised by a run. Human play, LAN/internet: not tested.
9. **Tracked-humans list (m6_camera_parity.md 1.3):** not changed; the M18 escape uses one shared rail on player 1, the
   beach rails take their target from RAILTGT (views 3-4) and from list entries 0-1 (views 1-2, unchanged).
10. `chase_probe.m8_flags` (added by the coordinator) returned Lua status 1 in its run (cause not checked); the money
    channel it uses is capped at 999, so its scaled coordinates cannot come back that way. Not used for any result here.

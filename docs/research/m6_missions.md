# M6 research: missions 1-18 and the hub interludes with players 3-4 (static analysis, 2026-10-12)

Build: The Warriors SLUS-21215 v1.03 (`local/disc/SLUS_212.15`, opened read-only). **Static analysis only: no emulator,
no test runner and no build was started for this note** (instances 6-9 and the package self-test were running).
Sources: pseudo-Lua `local/analysis/pseudo/` (cited as `WAD:line`, e.g. `09229:1172` = `09229_c05eacb5.lua` line 1172),
decompile `local/analysis/all/all_*.c`, `local/analysis/callers.pkl`, `local/analysis/lua_bindings.tsv`, the ELF
(addresses static unless marked), `tools/mission_scan.py` / `evidence/missions/mission_scan.json`.
Function and structure names are OUR labels (the ELF is stripped). Labels: VERIFIED (script text or code, with a
pointer), HYPOTHESIS (runtime effect not observed), BLOCKED. Script facts are VERIFIED as text; what they do at runtime
with four players is HYPOTHESIS until `tests/m6/mission_smoke.py` and the human playthroughs run.
Builds on `m2_spawn_companion.md`, `m2_spawn_name.md`, `m2_extra_model.md`, `m2_inventory34.md`,
`session_policies.md`, `level_jump.md` and decisions D3, D4, D7, D13, D14.

Script files per mission (main script + chapter/scene/string chunks; main scripts found by
`preLoadFile("levelNN_scenetest")` and their `Chapter[]`/`preLoadFile` tables; the mission scan puts some main
scripts under "shared" because they use no `lNN_` scene ids, so its per-level counts are incomplete; which chunk
is which checkpoint is given in each mission heading of section 3):

| # | Level | Main | Chapter / scene / string chunks |
|---|---|---|---|
| 1 | 99 | 09607 | 09653, 09654, 09655, 09657 (scenes) |
| 2 | 80 | 08730 | 08774-08777 |
| 3 | 87 | 09171 | 09221-09225, 09227 (scenes) |
| 4 | 34 | 07920 | 07965, 07967, 07968, 07969 (scenes) |
| 5 | 2 | 07708 | 07849, 07850, 07851, 07853 (scenes), 07854 |
| 6 | 3 | 07856 | 08021-08024, 08026, 08027 (strings) |
| 7 | 5 | 08029 | 08481-08484, 08486 (scenes) |
| 8 | 81 | 08780 | 08837-08841, 08842, 08844 (strings) |
| 9 | 86 | 09117 | 09163-09166, 09168 (scenes), 09169 (strings) |
| 10 | 93 | 09321 | 09375-09380 |
| 11 | 31 | 07860 | 07911, 07912, 07914, 07915, 07916 (scenes), 07917, 07918 |
| 12 | 14 | 07655 | 07695, 07696, 07698 |
| 13 | 9 | 09229 | 09720, 09721, 09722, 09724 (scenes) |
| 14 | 51 | 08031 | 08181-08187, 08189 (scenes) |
| 15 | 52 | 08191 | 08255-08259 |
| 16 | 54 | 08262 | 08349, 08350, 08352-08355 |
| 17 | 55 | 08357 | 08400, 08401, 08403-08407 |
| 18 | 84 | 09030 | 09110-09113, 09115 |
| hub | 95 | 09401 | 09500-09511 (= `level95_chapter1,10,11,12,2..9`, section 6), 09512 (clubhouse), 09513 (Coney roam) |

## Summary
- **Who players 3-4 become.** A free squad companion (the game's own picker) in most missions for at least part of the
  mission; spawned Warriors (clone of player 1 for player 3, own model through the pin for player 4) in M1, M12, M15
  (policy) and in single checkpoints elsewhere. Per-mission answer: section 3, table in section 7.
- **New hazard 1 (VERIFIED script + code, effect HYPOTHESIS): scripts delete the companions players 3-4 take.**
  `HuDelete` / `RemoveGang` of squad members in M2, M3, M7, M8, M9, M10, M11, M13, M16, M18; neither delete path
  releases a player first (1.4). Fix X1.
- **New hazard 2 (VERIFIED): the picker's fallback scan takes any AI human of any type-0 gang**, including civilians
  (Scopes M6, Tony M9), Mercy (M15, M16 intro, M18 cp3), and scripted, downed or arrested Warriors (M2 Ajax before his
  recruit scene, M13 rooftop Fox, M14 pit-fight Ajax and rescue Vermin, M15 the scattered six, M16 god-mode chase
  NPCs). Fix X2 (players 3-4 only from player 1's own gang, else spawn).
- **New hazard 3 (VERIFIED code): `HuChangePlayerGang`** (M1, M6, M8, M14, M16, M17, M18) releases and re-makes all
  players; players 3-4 are dropped, re-seated on other pads, or put on humans the script deletes next. Fix X3.
- **Mission 13 (the M2 test mission):** the script deletes Fox, whom player 3 took in the M2 four-player runs, when player 1 reaches
  the trainyard scene (`09720:157`, again `09721:159`); the M2 bot runs never got there (open point 8.1).
- **Joining windows:** no mission keeps players 3-4 out for the whole mission. After a reload they cannot join during
  M8 cp3, the M14 cp6-7 chases, M18 cp1-2 (a 2-player car chase by design) and the M11 final fight (X13, decision).
  They must re-join after every level load (X11).
- **Player-1/2-only scripts:** mostly harmless (players 3-4 are ignored). Harmful: warps that strand spawned players
  (M7, M10, M14), the M1 window counter, the M11 cash objective, camera helpers (M13, M16, M18), leave callbacks (X5).
- **Script fixes are feasible in principle:** the ELF contains the Lua 4.0 compiler and registers `dostring`
  (`FUN_003256F0` -> lua_dobuffer `FUN_003290D0`); BLOCKED only on finding the lua_State pointer (X6).
- **Starting items:** only levels 87, 5, 9, 51 and 84 give items (`MS`, WAD 4106); design S1 = a small C table at the
  join of player 3/4 (X7).
- **Mission end:** `UnlockAndLoad` zeroes players 1-2's money before the game banks it, which explains F-0158's +70
  exactly; `[4p inventory]` Block B should become "clear slots 2-3" (X8). Players 3-4 are destroyed with the level and
  re-join in the next one.
- **Hub:** 10 required interludes (hub checkpoints 1-10), all inside the clubhouse with joining off, except the
  checkpoint-3 burner tagging outside; W4P rule `level == 95 and 1 <= cp <= 10` (section 6, X12).
- **Outlook:** easy - M4, M5, M12 (M1 once X3/X11 exist); needs work - M2, M3, M6, M7, M9, M10, M11, M13, M15, M16,
  M17; partly blocked - M8 (cp3), M14 (cp6-7 after a reload), M18 (cp1-2). Status of all: NOT YET TESTED.

## 1. Rules that apply to every mission

### 1.1 Who a joining player 3/4 becomes (VERIFIED code unless marked)
- **Drop-in path:** Start on a free connected pad in gameplay -> UpdateJoin `FUN_0041A460(GameMgr, pad)` -> picker
  **PickJoinCompanion `FUN_0022A770(gang of player 1, 0)`** (decompile all_02.c:54405) -> MakePlayer `FUN_00229C40`.
  With `[4p spawn]`: if the picker returns 0, `SPAWNPICK`/`PX` (0x000E1000/0x000E1B38) spawns a Warrior (`SPAWN`
  0x000E1080, name from `CHOOSE` 0x000E1400, player 4 gated on the extra-model pin `GATE`/`ENSURE` 0x000E19E8/0x000E17C8).
- **Picker order** (exact): over the 16 member slots of player 1's gang (gang+0x48), AI humans only (+0x1B0 == -1):
  the one with the **lowest non-zero join priority** (+0x1B1, HuCreate arg 6); if none has a non-zero priority, the
  **first AI member, priority 0 included**. Only when player 1's gang has **no AI member at all**, and the level is not
  99, and GameMgr+0x158 == 0: a **fallback scan of all 60 human slots** for an AI human whose gang has **type 0**
  (gang+0x2C = GangCreate arg 1), again lowest non-zero priority first, else the first found.
- **New finding (VERIFIED script text + code): the fallback is unsafe for players 3-4.** Type 0 is not "Warriors
  only": `GangCreate(0, ...)` is used 248 times and also builds scene, escort and rescue groups, e.g. the civilian
  "Scopes" (char 425) in M6 (`07856:1398-1400`) and in M13's Cleon gang (`09229:1197-1200`), the civilian Tony
  (char 450) and "DeadAsh" in M9 (`09117:1394-1403`), Mercy in M15 (`08191:1482-1484`), M16 (`08262:1090-1097`) and
  M18 (`09030:1085`, filled at `09112:199-205`), soldiers in M10 (`09321:1262-1474`), and scripted Warriors waiting
  in their own type-0 gang (M2 Ajax before recruitment, M13 rooftop Fox, M14 pit-fight Ajax and rescue Vermin, M15
  the six scattered Warriors, M16 god-mode chase NPCs). UpdateJoin calls the picker with param 0, so **downed or
  arrested humans are not excluded** either (its state tests `FUN_00227E60`, `FUN_00227DD8` = downed,
  `FUN_00223B70`, `FUN_00227EB0`, `FUN_00227E18` run only for param != 0).
  Whenever player 1's gang has no AI member left, players 3-4 can be given such a human (per mission in section 3).
  Fix X2 (section 2).
- **Which squad member is player 2:** scripts set the globals `player` / `player2` themselves (e.g. `09229:3458-3461`);
  the picker takes the lowest non-zero priority, which the scripts give to `player2` (priority 2) in the squads read
  here. Players 3-4 get the next priorities (3, 4, ...), then priority-0 members.
- **Model rule (VERIFIED, m2_spawn_name.md 2.1):** priority >= 1 and an unflagged id -> the base Warrior model
  (`warr_xx`); priority 0, or a flagged id (3, 4, 7-10, 13, 14, 20, 25, 32, 35-37: `_cv`, `_ghost`, `_chase`) -> that
  id's own model (`warr_xx_gen`, `_cv` ...). `CHOOSE` only finds base models, so a Warrior created with priority 0
  (e.g. `warr_cl_gen`) does not make his base model resident.
- **Join-event guard** (`mod/m2/joinevent.txt`, 0x0041B180 -> 0x000F0ED0): the Lua join event (`InventoryPlayer2` ->
  the mission's `SetPlayer2Callback` function, `04106:4686-4698`) runs only for player indices 0-1; **leave events
  run for every index**, so the game's own "continue in 1 player mode" (which releases all drop-in players) calls the
  mission's player-2 callback with player 3/4's handle and `false` (session_policies.md 3.2).
- **HuIsAPlayer(h)** = human+0x1B0 != -1 (`FUN_00235758`), true for players 3-4 too; `HuGetPlayer(i)` reads
  GameMgr+0x228+i*4 (`FUN_00234FB8`). Scripts never call HuGetPlayer (0 uses); they track only `player`/`player2` and
  named handles.

### 1.2 Joining windows (VERIFIED code)
- Join flag GameMgr+0x56E8: set to 1 at every level (re)load by ResetLevel `FUN_001607B8` (F-0066); Lua
  `CfgMultiplayerJoin(b)` (binding 0x0035E818 -> `FUN_0041DA08` -> `FUN_0041A430`) sets it; a 0 -> 1 change also calls
  UpdateJoin(GameMgr, -1), which (2-player flag GameMgr+0x56EC set, count <= 1) **re-creates player 2 from a companion
  on a free connected pad**, or (count > 1) only refreshes cameras. It never adds players 3-4.
  `CheckMultiplayer()` (0x0036E468 -> `FUN_0041DD90`) = UpdateJoin(-1) as well (used once, hub `09401:6929`).
- In-game drop-in block of `FUN_00158728` (0x00159090-0x00159290; decompile all_00.c:61087-61147): needs a camera
  whose type (vtable +0x1EC) is 2, 9 or 0 (or, special case, camera 0 of type 1 in level 0x54 = 84 at checkpoint 4,
  0x001591B8/0x001591D0), **no screen effect running** (ScreenEffects[0]+0x1E8/+0x1EC == 0, 0x0015913C/0x00159148:
  fades block joining), GameMgr+0x14C == 0 (0x001591F4), a connected pad with Start held, and no cinematic
  (session_policies.md 2.1). Meaning of the camera types: HYPOTHESIS (2/9/0 = player-follow cameras, 1 = scripted).
- **Players 3-4 must join again after every level load** (mission start, checkpoint reload, next mission): the level
  teardown destroys all humans; player 2 is re-created automatically by UpdateJoin(-1) at the in-game enter
  (`FUN_001582E0`, level_jump.md 1.3), players 3-4 only by a new Start press (VERIFIED runtime F-0160, sp_leave C/C3).
  So a stretch with `CfgMultiplayerJoin(false)` at the start of a checkpoint keeps players 3-4 out of that stretch after
  a reload. **Proposed W4P rule (X11, design):** after each level load, the session layer injects a Start press for every
  connected slot 3/4 that is not a player yet, once per 300 polls while the join conditions hold (input goes through
  the lockstep, so all instances join at the same poll).
- Cutscenes: no join and no pause during a cinematic (GameMgr+0x410 != 0) or a movie (session_policies.md 2.1).

### 1.3 Script logic that knows only players 1-2 (VERIFIED script text; general patterns)
- `HuIsAPlayer(player2)` branches (209 in all scripts): almost all are "player 2 is AI -> suspend/teleport/heal/order
  him; player 2 is human -> skip". Players 3-4 are never `player2`, so their companions get the AI treatment in those
  branches only if the script names them; most of these branches therefore **ignore** players 3-4. Where a script
  orders a named companion (GoalMoveToFlag, TeleportToFlag, HuDelete, scene "Humans" list) and that companion is now
  player 3/4, the human loses control briefly or is moved (HYPOTHESIS) - listed per mission.
- Both-in-box objectives `IsInsideBox(box, player) and IsInsideBox(box, player2)`: players 3-4 are not tested; they can
  be left behind when the script then warps/teleports only `player`/`player2` (per mission).
- Shared helpers in WAD 4106: score at mission end sums only `player` + `player2` (`04106:1713-1741`), money/items are
  cleared only for `player`/`player2` (`04106:1695-1711`, section 5), POIZO dialogue skip listens to pads 0 and 4 only
  (`04106:1651-1667`; session_policies.md 2.1), the per-player inventory callbacks pass only 1/2 (m2_inventory34.md).
- **How a script fix can be applied (feasibility):**
  - (L) **Run Lua source in the game:** the shipped ELF contains the Lua 4.0 compiler (parser strings at file
    0x00475A18-0x00476E80) and registers the base library including `dostring` (luaL_reg table 0x00574D78: `dostring`
    -> `FUN_003256F0`, which calls `FUN_003290D0` = lua_dobuffer (our label); registered by `FUN_00326548` <-
    `FUN_003564D8` <- `FUN_00356390`). A cave on the game thread can therefore run a short Lua string that redefines a
    mission function (e.g. `ch1["X"] = function(...) ... end`) or loops over all players. VERIFIED code presence;
    HYPOTHESIS that it works at runtime (needs the lua_State pointer, presumably inside the script manager
    `*(0x00512B04)`, offset not yet identified). **Recommended route (X6)** for the script changes of section 3: one generic
    "run Lua string" cave + per-mission strings, triggered at a known point (level start after RunLevel, or by W4P's
    call mailbox at an agreed poll).
  - (B) Same-size bytecode edits of the loaded chunk (change a constant, flip a branch): possible but needs the chunk's
    heap address per load; not recommended.
  - (C) Hooks on bindings (e.g. make `IsInsideBox` count all players): global side effects; only for narrow cases.

### 1.4 Script operations that hit the humans players 3-4 hold (VERIFIED code; effects HYPOTHESIS)
- **`HuDelete`** (binding 0x00358608, call `jal 0x00233EF0` at 0x00358624): the core `FUN_00233EF0` has no player
  check and no ReleasePlayer (0x00233EF0-0x00233F5C). Story scripts delete companions at chapter/scene ends (M2, M3,
  M7, M8, M9, M10, M11, M13, M18, section 3); they never delete `player`/`player2` there. A player 3/4 holding that
  companion loses his human while still registered as a player: crash, dead slot or stale view (HYPOTHESIS; not yet
  observed - the M2 bot runs never reached such a point).
- **`RemoveGang`/`GangDelete`** (binding 0x00373200 -> `FUN_0016A1E8` -> `FUN_0016D068` -> `FUN_00164738`, member
  cleanup call at 0x0016478C -> `FUN_0021C7C8`): the cleanup's player branch releases the HUD slot (`FUN_001B22F0`),
  frees the pad owner and calls RemovePlayer `FUN_00419C68` (jal at 0x0021CAF8), but **not ReleasePlayer** (no camera
  removal, no drop-in mask, no inventory slot release) - the class of defect seen in run C (session_policies.md 3.3).
- **`HuChangePlayerGang`** (binding 0x0035D1A8 -> `FUN_00239B80`, decompile all_03.c:2852): if player 1's gang is not
  the target gang, it releases (`FUN_0022A2A8(h, 0, 1)`) every player whose gang is player 1's gang, highest index
  first, saving their pads in a stack array at sp+0 (4 entries fit: ra is saved at sp+0x10, 0x00239BC0/0x00239C84,
  so 4 players do not overflow it - VERIFIED disassembly); re-makes players already in the target gang on their saved
  pads; then for each remaining released player calls PickJoinCompanion(target, 0) + MakePlayer(h, pad -1)
  (0x00239D68 / 0x00239D84): pad -1 = the HUD menu pad for indices 0-1, the first free connected pad otherwise, so
  players 3-4 can swap seats/pads; when the target gang is short the fallback scan returns any AI type-0 human
  (including ones the script deletes next) or nobody (that player is simply dropped). Calls in story scripts: 09654:61
  (M1), 08021:200-221 (M6), 08838:277-298 and 08841:325-347 (M8), 08187:49-51 (M14, cp7 reload, before joins),
  08352:201 and 08353:31-56 (M16), 08404:81-83 (M17), 09110:181-200/402 and 09111:263/316 (M18).
- **Teleports/freezes name players 1-2 only:** scripts move `player`, `player2` and named handles (Lua `Teleport`
  0x0036CBC0, `TeleportToFlag` 0x0036CDC0, per-mission `WarpPlayers`/`Warper` helpers). Spawned players 3-4 are never
  moved (left behind, sometimes behind doors the script closes: M7, M10, M14); companion-players move with their name.
  `DeactivateWarriors`/`ActivateWarriors` (`04106:920-945`) BrDead only `player`/`player2` and `GangSuspend` the squad
  gang (players 3-4 are in it: effect on a player-controlled human HYPOTHESIS); `HuLockPad`/`HuSetButtonTapControl`
  only P1/P2.
- **Camera helpers** that pick the view by "`player2` -> view 1, anyone else -> view 0" (M13 `EnterGraveTrain`
  09229:2667-2720, M16 `chase.CamSwitcher`/`GatePicked` 08349:464-480, M18 `C5.SetRailCam` 09112:683): a trigger
  entered by player 3/4 re-targets player 1's or player 2's camera (HYPOTHESIS).
- **Leave callbacks assume the leaver is player 2** (M14 `C7/C9.SetPlayerOff` 08186:177-186/08187:185, M16
  `AnotherPlayer` 08262:2654-2680, M17 `PARTY.Multiplayer` 08403:225-234, M18 `C1.SetPlayerOff` 09110:84-92): a player
  3/4 leave that reaches Lua corrupts mission state. The session LEAVE cave skips it for index >= 2; the game's own
  pause-menu drop-out (`LEAVEHOOK` 0x000E1240) still passes it.
- **Lists and sums of two players:** `Warriors`-table checks (`ObjectiveGoodToGo` 04106 main_145, `CheckWarParty`
  09722:249-262) count named companions only (a companion-player must walk there; spawned players never count or
  block); money/spray sums use player numbers 1-2 (M4 07968:273, M11 07918:554-683; tagging M3 09171:3650-3657, M6
  08023:562-574/08024:164-174, M13 09229:2279-2290).
- **Companion-players moved into other gangs** by scripts (M10 `09378:236-241`, M11 `07911:96-131`, M14
  `08186:36-49`, M18 `09112:199-205`) leave player 1's gang: gang commands (D13) and the picker no longer see them
  (effect HYPOTHESIS).

## 2. Fix catalogue (design; nothing applied; sizes are estimates)

| ID | Fix | Where | Label / size | Missions |
|---|---|---|---|---|
| **X1** | **Delete guard:** if a script deletes a human whose +0x1B0 >= 2, first run LEAVE(index) (session cave 0x000E7100, run C3 path), then let the delete go on the now-AI human; W4P re-joins the player (X11) as another companion or a spawned Warrior. Alternative (X1b): skip the delete, put the human back in player 1's gang next to player 1 (`FUN_00166308`, `FUN_0023B138`) - but scripts that re-create the same Warrior later (M13 Fox) would then duplicate him | hooks at 0x00358624 (`jal 0x00233EF0`) and 0x0016478C (`jal 0x0021C7C8`) | ~25 words; HYPOTHESIS that LEAVE is safe inside a Lua binding call (game thread) | M2, M3, M7, M8, M9, M10, M11, M13, M16, M18 (+ M1 clones via RemoveGang) |
| **X2** | **Pick filter for players 3-4:** for a real Start press with count >= 2 at entry (player 2 and the level-start path keep the original picker), replace the picker call in `PX` (0x000E1B38) by our own loop over player 1's gang (gang+0x48, 16 slots): AI, not downed (`FUN_00227DD8` == 0), not on a per-level/checkpoint "do not take" table, lowest non-zero priority else first; **never the fallback scan**; nothing found -> `SPAWN`. Table (scripted actors only; companions that are merely deleted later are left to X1 + X11): level52 cp1-3 all (C2 scatters them), level55 cp1 Cochise (kiss-trap cinematic), level9 cp1-2 Fox (deleted minutes into ch1/ch2; avoids a forced re-join) | `PX` 0x000E1B38 (`m2_extra_model.md` 4.3), table in free RAM | ~45 words + ~20 data words; VERIFIED rules of `FUN_0022A770` | M2, M6, M9, M10, M11, M13, M14, M15, M16, M17, M18 |
| **X3** | **HuChangePlayerGang wrapper:** if the count is > 2, LEAVE index 3 then 2 (0x000E7100), call `FUN_00239B80` (now <= 2 players, original behaviour), then W4P re-joins them (X11) | the binding 0x0035D1A8's call of `FUN_00239B80` | ~20 words; HYPOTHESIS | M1, M6, M8, M14, M16, M17, M18 |
| **X4** | **Teleport follow:** after a script teleports player 1, place every player with index >= 2 that is farther than ~15 units next to player 1 (`HuTeleportNearHuman` core `FUN_0023B138`); skip while a scene runs | hook in the `Teleport`/`TeleportToFlag` cores (`FUN_00385BB8` is the Teleport core, F-0156; the TeleportToFlag core is not yet identified) | ~30 words; HYPOTHESIS (scene interference) | M1, M3, M7, M10, M13, M14, M15 |
| **X5** | **No Lua leave event for index >= 2 on any path** (the game's own pause-menu drop-out included), or hide that menu item in sessions | `LEAVEHOOK` 0x000E1240 (event call 0x0041A868) | ~5 words; VERIFIED path | M1, M9, M10, M14, M16, M17, M18 |
| **X6** | **Run Lua source** (route L, 1.3) for script-level fixes: camera guards (M13, M16, M18), M1 window counter, M11 cash sum incl. players 3-4, tagging spray of the tagging player (M3, M6, M13), starting items S2 | cave calling lua_dobuffer `FUN_003290D0(L, str, len, name)` on the game thread | **BLOCKED** until the lua_State pointer is found; then ~20 words + strings | M1, M3, M6, M11, M13, M16, M18 |
| **X7** | **Starting items for players 3-4** (section 4, S1) | join-event guard cave 0x000F0ED0 + table | ~40 + 20 words | M3, M7, M13, M14, M18 (non-zero `MS`) |
| **X8** | **Mission end:** replace `[4p inventory]` Block B (bank slots 2-3) by "clear slots 2-3" (`FUN_0041EC60` for 2 and 3, live + copy) - parity with `LiquidizeAssets` | 0x0015D3F4 -> cave 0x000E5000 | ~10 words; VERIFIED flow (section 5) | all |
| **X9** | **Per-level CHOOSE order** (data 0x000E1580): story fit (no Cleon after level 9: M14 cp6-7 and M15 would pick him) | data words | data only; needs a user decision | M14, M15, (M17, M18) |
| **X10** | **Own model for player 3 too** when he has no companion (today a clone of player 1): GATE/ENSURE also at count 2 = two extra models | `JS` 0x000E1A9C | ~10 words; memory R-28 (two pins); needs a user decision | M1, M7 cp3, M10 cp6, M11 cp1-3, M12, M13 cp1-2, M14 cp1, M15 |
| **X11** | **Auto re-join (W4P):** after each level load and after X1/X3 releases, inject Start for every connected slot 3/4 that is not a player, every 300 polls while joining is possible (1.2) | W4P session layer | fork change; lockstep-safe (input) | all |
| **X12** | **Hub interlude handling (W4P):** detect, mask input, waiting screen, pads 2-4 reported disconnected, reconnect player 2's pad first (section 6) | W4P | fork change | hub cp1-10 |
| **X13** | **Join-off stretches:** keep (players already in stay; after a reload players 3-4 sit out until the script switches joining on) or let X11 join them in the short window between level start and the script's `CfgMultiplayerJoin(false)` | - | needs a user decision (M18 cp1-2 is a 2-player car chase by design) | M8 cp3, M11 final fight, M14 cp6-7, M18 cp1-2 |

## 3. Per mission (questions 1-3; starting items and end per mission)

Per mission: squad per checkpoint, free companions in picker order, mission-critical companions, spawn path,
joining windows, player-1/2-only logic, starting items, end. "P3/P4" = players 3/4. Fix IDs X1-X13: section 2.
Risk rows: section 7.

### M1 - level99 "New Blood" (main 09607; chapters 09653 = level99_combat cp1, 09654 = level99_lesson1 cp2, 09655 = level99_lesson2 cp3; scene test 09657)
**Squad.** `tMission` 09607:1696-1698: cp1 AddWarriors2 (09607:181-184: Rembrandt 32 prio 1 [flagged cv -> `warr_re_cv`], Ash 40 prio 2), cp2 AddWarriors (09607:144-147: Rembrandt 30 p1 `warr_re`, Ash 38 p2 `warr_ty`), cp3 AddWarriors1 (09607:173-176, same). `player`/`player2` = Rembrandt/Ash (09607:1709-1710). VERIFIED. Two members only.
**Free companions.** None for P3/P4 (F-0109, VERIFIED runtime). Fallback scan never runs in level 99 (FUN_0022A770 level != 99 test). Other type-0 gangs exist but are unreachable: Teacher (Vermin 26 p0, 09607:152-154), SCleon (Cleon 2, 09607:214-216), FenceWarriors1/2 (generic ids 58-60, 09607:245-259). -> P3 and P4 always SPAWN.
**Mission-critical.** Ash only as player2 (Ash intro scene P1.AddPlayer2 09653:184-225 on P2 join). Teacher Vermin (god mode, guide) and Cleon are never companions. Taking over: n/a.
**Spawn path.** Base models resident: cp2-3 Rembrandt 30 (present), Teacher Vermin 26 prio 0 = base id -> `warr_ve` (present); cp1 only variant models (32 `warr_re_cv`, Vermin 27 / Cleon 2 `_gen`). CHOOSE finds no resident+absent Warrior (HYPOTHESIS until survey) -> P3 = clone of P1 (char 32 in cp1, 30 later); P4 = Swan through the pin (ENSURE at P3's join). Ash (38, HUD index 9) is not a CHOOSE candidate.
**In-level squad swap (09654:61-62, cp1 -> cp2 when continuing from the combat chapter).** `HuChangePlayerGang(GangWarriors02)` = binding 0x0035D1A8 -> FUN_00239B80 (our label "ChangePlayerGang"): ReleasePlayer FUN_0022A2A8(h,0,1) for every player of P1's old gang (W4P clones included), then re-makes as many players from the new gang with PickJoinCompanion(new gang) + MakePlayer FUN_00229C40(h,-1,..). The new gang holds only Rembrandt + Ash, so **players 3-4 are dropped** (VERIFIED code, runtime HYPOTHESIS); `RemoveGang(GangWarriors2)` then runs GangDelete FUN_0016D068 -> FUN_00164738 = human cleanup FUN_0021C7C8 on every member (VERIFIED code) -> the released clones are deleted. No UpdateJoin leave loop, so no LEAVEHOOK/LV (pin and GameMgr+0x456 bit stay; HYPOTHESIS harmless). P3/P4 must press Start again (new SPAWN). MakePlayer(pad -1): index < 2 takes its HUD menu-controller pad (FUN_001AE898), others the first free connected pad (VERIFIED code).
**Joining windows.** 09653:309 off (P1.DoneCamera, before Rudy intro l99_t1) -> 09653:346 on (P1.DoneRudyIntro); 09653:932 off (P1.SetupRageMode) -> 09653:1044 on (P1.RageDone). Locked cameras (FenceCam 09655:118, JumpCam 09655:301) briefly block joins (join needs a follow-type camera, FUN_00158728). Never blocked for a whole checkpoint. VERIFIED script.
**Player-1/2-only logic.** (a) ~30 `HuIsAPlayer(player2)` branches put player2 into scene `Humans` lists only (09653:329-333 l99_t1, 09654:95-99 l99_c2, 09655:653-657 final l99_c9) -> P3/P4 not in scenes (HYPOTHESIS: left standing, harmless). (b) `TeleportToFlag(player2, ...)` before tutorial stages (09653:852, 09654:200/260/278/347, 09655:250/313/433/495/554) -> P3/P4 left behind on the roof/fence route (can walk; fix = leash/teleport hook, cross-mission). (c) DemiGod only for player/player2 (09607:1714-1715) -> P3/P4 can die in the tutorial (HYPOTHESIS). (d) Window jump P3.ReachWindow 09655:336-350: every player entering the volume is frozen (`BrDead(A1, true)`) and counts `pCount`; at 2 -> P3.Player2Jumps. With 3-4 players the count completes without player 2 and a 3rd/4th arrival stays frozen (HYPOTHESIS: per-player softlock). Minimal fix: Lua patch `if A1 ~= player and A1 ~= player2 then return end` (needs an in-memory Lua bytecode patcher - not built) or a hook that releases BrDead on P3/P4. (e) Callbacks F.Player2Join (09607:1505-1525) and P1.AddPlayer2 (09653:184-225) act on global `player2`, ignore A0: a LEAVE event of P3/P4 would suspend + teleport Ash. Reached only via the game's own leave loop (pause -> 1-player mode, releases everybody anyway); the session LEAVE cave skips Lua events for index >= 2 (session_policies 3.4). (f) Tutorial triggers test `A1 == player` (P3/P4 cannot advance or block); store/radio/navigation triggers use `HuIsAPlayer(A1)` (09654:154, 228, 383) -> any player.
**Starting items.** MS[99] all 0 (04106:4640). GiveMoney(50) to P1 at cp3 (09607:1726); Flash lesson InvSetMoney(20, 1) (09655:479-480), checks P1's Flash only (09655:603). P3/P4 nothing (fine).
**End.** Final scene l99_c9 (09655:659 `Final`) -> PreCashTheWorld -> HUDLaunchMissionComplete -> runNextMission: level80 cp1 (no hub).

### M2 - level80 "Real Live Bunch" (main 08730; chapters 08774 cp1, 08775 cp2, 08776 cp3, 08777 cp4)
**Squad.** `PlayerGang = {AddWarriors, AddWarriors2, AddWarriors3, AddWarriors4}` 08730:61, run by Main 08730:1048; `player = hCleon`, `player2 = hVermin` 08730:1058-1059. cp1 (08730:89-93): Cleon 1 p1 (`warr_cl`), Vermin 26 p2 (`warr_ve`), Rembrandt 31 p0 (`warr_re_gen`). cp2 (08730:221-226): + Ajax 12 p0. cp3 (08730:231-238): Cowboy 19, Rembrandt 31, Vermin, Cleon, Snow 34, Ajax 12. cp4 (08730:243-251): + Fox 22 p0. All extra members prio 0 -> `_gen` models. Chapters chain in-level: NextMission = SetCheckPoint(CHAPTER+1) + RunMission (08730:1078-1084), no reload.
**Recruiting (scripted additions).** Ajax: own type-0 gang (08730:115-117) created in Setup2 (08774:97), added 08774:270; Snow+Cowboy (gang 08730:171-174, type 0) arrested, added 08775:147-148; Fox (08730:122-124) added 08776:511; Cochise+Swan (08730:187-190) added 08777:243-244. Removed: **`HuDelete` of Ajax, Fox, Rembrandt, Snow, Swan, Cochise at 08777:374-379** (PreloadDestroyerScene, after the last squad scene, before the Final scene) - Cleon/Vermin/Cowboy kept.
**Free companions (member order, prio 0 = first AI member).** cp1: P3 = Rembrandt; P4 = none in P1's gang -> fallback scan -> **Ajax** in his own type-0 gang (once Setup2 ran; join is off before). cp2: P3 Rembrandt, P4 Ajax. cp3: P3 Cowboy, P4 Rembrandt. cp4: P3 Snow, P4 Rembrandt. (VERIFIED script + FUN_0022A770 rules; runtime HYPOTHESIS.)
**Mission-critical.** cp1 Ajax before recruitment: kiss cinematic `GoalJoinCinematic(hAjax, ...)` 08774:238 and recruit scene l80_c4 (08774:259) -> taking him as P4 via the fallback is NOT safe (HYPOTHESIS: scene/goal on a player). Command tutorial 08774:169-190: all 3 squad members (incl. Rembrandt = P3) must be inside vWarriorsTrigger -> P3 must walk there (as player 2 must for Vermin). Squad members get scripted TeleportToFlag/GoalMoveToFlag (08775 main_9, 08776:208-216, 08777 main_6) - teleports move P3/P4 along (OK), AI goals on a player (HYPOTHESIS ignored). **HuDelete 08777:374-379 deletes whoever P3/P4 hold in cp4 (Snow/Rembrandt by the order above) while they are players** (VERIFIED script; effect HYPOTHESIS: stale handle in GameMgr+0x228.., crash or ghost player). The designers never delete player/player2 (Cleon, Vermin) there.
**Spawn path.** Base models resident: only Cleon (`warr_cl`) and Vermin (`warr_ve`), both present; everyone else `_gen`. CHOOSE finds none -> pin (Swan) if a spawn is ever needed (not with the companions above). No SetCharacterModel in the level.
**Joining windows.** 08774:33 off (cp1 Setup: intro l80_c1 + Cleon's command tutorial) -> 08774:216 on (EndStartCam); 08776:207 off (EndFoxScene: Fox hide / cop search / throw tutorial) -> 08776:518 on (EndFoxScene2). cp2/cp4 no switch. A cp1 reload re-runs the off stretch. Not blocked for a whole checkpoint.
**Player-1/2-only logic.** `HuIsAPlayer(hVermin)` checks (08774:94/161, 08775:182/223, 08776:592-691) treat Vermin as "the other human"; P3/P4 ignored (store front/back objective markers shown/hidden only for Cleon/Vermin; lock picking `HuIsAPlayer(A0)` 08776:638/714 works for anyone). Throw tutorial 08776:274-290: a trigger by P3/P4 is treated like Vermin's; only Cleon/Vermin are locked into it (ThrowCam on view 0). Loops `if HuIsAPlayer(L) then skip` (08777:188, 274) already handle P3/P4 correctly. No P2 callback, no Inv calls.
**Starting items.** MS[80] all 0 (04106:4633). None in scripts.
**End.** Final scene l80_c3_b (08777:397 `Final`) -> mission complete -> level87 cp1 (no hub). No MissionFailed in the scripts.

### M3 - level87 "Payback" (main 09171; chapters 09221 cp1 tutorial, 09222 cp2, 09223 cp3, 09224 cp4, 09225 cp5 club; scenes 09227)
**Squad.** loader 09171:4357-4398: AddWarriors1..5 by `mState`; `player = Rembrandt` 09171:4371, `player2 = Vermin` 09171:4373 (cp>=2) / 09221:39 (cp1). cp1: P1's gang = Rembrandt 30 p1 only (09171:2016-2018); Vermin 26 p2, Cowboy 19 p0, Ajax 12 p0 sit in type-0 gang WarriorsCh1 (09171:2229-2233) until `ch1.Voltron` adds them (09221:210-219). cp2-5: AddWarriors2..5 (09171:2238-2263, 2317-2322) = Rembrandt p1, Vermin p2, Cowboy p0, Ajax p0 (`_gen` models for Cowboy/Ajax). Chapters chain in-level (SetCheckPoint 09221:264, 09222:274, 09223:263, 09224:874).
**Free companions.** cp1: P1's gang has no AI member -> fallback scan: P2 gets Vermin (lowest non-zero prio), P3/P4 get Cowboy/Ajax (first AI in object-slot order). cp2: P3 Cowboy, P4 Ajax; cp3 Ajax/Cowboy; cp4 Cowboy/Ajax; cp5 Ajax/Cowboy (member order). Exactly two free companions -> no spawn needed. Other type-0 gang: Ajax (11, base model) re-added in cp5 (09171:2355-2357 via 09225:768) for the last scenes.
**Mission-critical.** **cp5: `HuDelete(ajax)` 09225:154** (ch5.OpenLastTag, start of the stealth chapter) - Ajax is P3 in cp5 by member order -> deleting a player human (same hazard as M2; HYPOTHESIS crash/ghost). cp1 tally (ch1.Ch1WarriorReady 09221:127-135): all 3 WarriorsCh1 members must enter vbRembrandtGo; AI is sent there by GoalMoveToFlag (09221:119), a human P3/P4 must walk there himself or the tutorial waits (HYPOTHESIS stall; same as player 2 in 2P).
**Spawn path.** Base models: Rembrandt (`warr_re`), Vermin (`warr_ve`), Ajax 11 only in cp5 late (`warr_aj`, present). CHOOSE none -> pin (only if a companion is missing, e.g. after the cp5 delete). SetCharacterModel(439/431/428) cp2-4 (09171:4388-4391, non-Warriors) -> pool pressure (R-28).
**Joining windows.** No CfgMultiplayerJoin in the mission; only scenes/locked cameras (IntroCam/GateCam/puke cams) briefly. Not blocked.
**Player-1/2-only logic.** (a) Tagging SpotGettingTagged 09171:3650-3657: any player may start a tag, but the spray check uses player number 1 unless `A1 == player2` -> P3/P4 tag on P1's spray count (HYPOTHESIS: may start with 0 own charges; engine consumption per HUD slot unclear). Fix: Lua patch to map A1 -> player number (no binding exists; would need a new helper) - low priority. (b) ObjectiveExit 09171:1827-1831 (GoodToGo boxes) resets only for player/player2 leaving -> P3/P4 ignored (harmless). ObjectiveEnter 09171:1789 accepts any player (good). (c) Stealth cp5: player/player2 teleported to watch the puker (09225:365-366), distract tutorial locks only player/player2 pads (09225:497-520), Freedom unlocks the same (09225:901-915) -> P3/P4 free to roam; puker sight `ch5.PukerSawPlayer` (09225:350/356) and wanted check (09225:834) -> HUDLaunchMissionFailed 09225:898 (HYPOTHESIS: P3/P4 easily get the team spotted). Fix: include P3/P4 in the teleport/lock (hook) or accept as gameplay. (d) P2 callback HumanPlayerChange (09171:4161-4167): on P2 join in cp1, spray 0 + god mode for A0; not run for P3/P4 (guard) -> P3/P4 keep 0 spray anyway, no tutorial god mode.
**Starting items.** MS[87] paint 1, money 15 (04106:4643) -> P1 at cp0/1, P2 on first join (then zeroed spray 09221:103, 09171:4164). Script: P1 spray +1 retries (09221:248, 09171:3783), InvSetSpraycanCharges(9) debug `z` (09171:4006). P3/P4: nothing -> no spray for tags until they buy/pick up (spray dealer spawner 09171:2025).
**End.** Final chained scene l87_c2 (09225:822 `Final`) -> level95 cp1 (hub). MissionFailed: spotted in cp5 (09225:892-899).

### M4 - level34 "Blackout" (main 07920; chapters 07968 riot cp1-3, 07965 gate cp4, 07967 park cp5; scenes 07969)
**Squad.** `tMission` 07920:1921-1925: AddWarriors1..5 (07920:228-232, 415-421, 424-429, 331-336, 518-523) all = Vermin 26 p1 (`warr_ve`), Snow 33 p2 (`warr_sn`), Ash 38 p0 (`warr_ty`). `player = Vermin`, `player2 = Snow` 07920:1946-1947. No scripted additions/removals of squad members.
**Free companions.** P3 = Ash. P4: no AI member left -> fallback scan finds no other type-0 gang (07920 creates only Warriors1-5 with type 0) -> SPAWN. VERIFIED script.
**Mission-critical.** None for Ash (scene actor in CarFlip scene 07968:266 like the others; no delete, no escort). Safe to take over.
**Spawn path.** Resident base models: Vermin, Snow (both present); Ash = `warr_ty` (not a candidate). CHOOSE none -> P4 = Swan via the pin started when P3 took Ash (ENSURE). **Memory risk:** the riot and gate chapters pin 9 extra character models (07968:74-82, 07965:11-19; released 07965:97-105 at ReachPark) -> the Swan pin may not fit -> FITCHK -> P4 = clone of Vermin (R-28, HYPOTHESIS until survey).
**Joining windows.** No CfgMultiplayerJoin in the mission. Scenes/locked cameras only. Not blocked.
**Player-1/2-only logic.** (a) Loot objective: start value `lootTotal = InvGetMoney(1) + InvGetMoney(2)` (07968:273); later loot counted by the money callback F.UpdateLoot (07920:1468-1494, `CfgMoneyCallback` 07968:278) - HYPOTHESIS: the callback fires for slots 2-3 too (InvAdd widened by `[4p inventory]`), then P3/P4 loot counts; only money held before the objective is lost. Checkpoint reload zeroes only P1/P2 money (07968:575-576, 592-593). (b) Mug bonus callbacks only on player/player2 (07965:73-74, 07920:1381-1382) -> P3/P4 muggings do not count (bonus only). (c) Riot meter / store / looter triggers use `HuIsAPlayer(A1)` (07920:1293, 07968:214-1100) -> any player counts (good). No P2 callback, no player2 teleports, no both-in-box.
**Starting items.** MS[34] all 0 (04106:4629). Only the money resets above.
**End.** Final subway scene (07967:260 `Final`) -> level95 cp2 (hub). No MissionFailed in the scripts.

### M5 - level2 "Real Heavy Rep" (main 07708; chapters 07849 clinic cp1, 07854 tenement cp2, 07850 clubhouse cp3, 07851 junkyard cp4; scene test 07853)
**Squad.** `tMission[cp]` 07708:2746-2749 picks AddWarriors / AddWarriors1 / AddWarriors2 / AddWarriors3; `player = Warriors.Cleon` (char 1, prio 1), `player2 = Warriors.Fox` (21, prio 2) 07708:2758-2759. Every squad also has Rhino (52, `warr_so_vb1`), Ash (38, `warr_ty`), Terrance (54), West (53), all priority 0, own models (07708:1085-1090, 1177-1182, 1189-1194, 1277-1282). The squad is created once per level load (chapters keep `GangWarriors`). VERIFIED (script).
**Free companions.** 4 per checkpoint; with no non-zero priority left the picker takes the first AI member in gang-list order: cp1 Rhino, Ash; cp2 Terrance, West; cp3 Ash, Terrance; cp4 West, Ash. Only Warriors gangs are type 0 (07708:1083/1175/1187/1275): no fallback exposure. VERIFIED script / HYPOTHESIS runtime order.
**Mission-critical.** None deleted, escorted or failed-on-death. All six are in every scene Humans list (07849:157, 227, 600; 07850:113, 168; 07851:72, 213; 07854:76, 262) exactly like player2 (Fox) - same path as the original 2P (HYPOTHESIS OK). Ash has one voice line `HuSpeakNI(Warriors.Ash, "l2_c7_000")` 07850:69 (cosmetic). Safe: all four extras.
**Spawn path.** Not needed (4 free companions).
**Joining windows.** No `CfgMultiplayerJoin` in any level2 file -> on by default (F-0066). No long locked stretch found.
**Player-1/2-only scripts.** (a) After the street scene `CameraMakeActive(MainCam, 0, nil, player)` and, if `HuIsAPlayer(player2)`, the same for player2 (07849:262-266) - P3/P4 cameras untouched (HYPOTHESIS: keep their own follow camera). (b) Gate-bum POIZO 07849:470-489: `gateHuman = A1` for any player (also P3/P4); `CamSetSecondary(GateBum)` + `CamEnable(0,false)`; skip input only on P1/P2 pads (session_policies 2.1). (c) All other triggers test `HuIsAPlayer(A1)` (07849:187, 558, 681; 07850:60, 67, 103; 07851:177, 186; 07854:192, 199) = any player. No player2 teleports, no both-in-box. Fix: none needed.
**Starting items.** MS[2] all 0 (04106:4619); no mission Inv call; dealers `StartFactory` 07708:2783 (Flash/Paint for sale).
**End.** Final scene 07851:213 (`Final = true`) and `HUDLaunchMissionComplete()` in its ReturnFunc 07851:220 -> 2 -> level95 cp3.

### M6 - level3 "Writer's Block" (main 07856; chapters 08026 C0 street cp1, 08023 C1 comp cp2, 08021 C2 balcony cp3, 08022 ch4 chase cp4, 08024 C5 gallery cp5; strings 08027)
**Squad.** `PlayerGang` 07856:395, `Mission[1..5]` 07856:398-402; `player` = Rembrandt (30, prio 1) in cp1-2, Snow (33, prio 1) in cp3-5; `player2 = Ajax` (11, prio 2) 07856:2030-2035. cp1 AddWarriors01 07856:1309-1311 and cp2 AddWarriors02 1318-1320: + Cowboy (19, prio 0 -> `warr_cb_gen`). cp3 AddWarriors03 1328-1331: + Cowboy 19, Rembrandt 31 (prio 0, `warr_re_gen`). cp4 AddWarriors04 1584-1587 (= 1691-1694): + Cowboy 18, Rembrandt 30 (prio 0). cp5 AddWarriors05 1476-1479: Rembrandt 30, Ajax, Cowboy 18, Snow. VERIFIED.
**Free companions.** cp1/cp2: 1 (Cowboy) -> P4 has none. cp3/cp4: Cowboy then Rembrandt; cp5: Rembrandt then Cowboy (list order).
**Squad swap (played through cp2 -> cp3).** 08021:200-221: `AddWarriors03()`, `HuChangePlayerGang(GangWarriors03)`, old members teleported to z -50, `RemoveGang(old)`. HuChangePlayerGang = binding 0x0035D1A8 -> FUN_00239B80 (VERIFIED decompile): releases every player whose gang is P1's old gang (ReleasePlayer 0x00239C80/0x00239D00, last index first), then for each released player calls PickJoinCompanion(new gang) at 0x00239D68 and MakePlayer(h, pad -1) at 0x00239D84. So P3/P4 are re-seated on Cowboy / Rembrandt-gen; for index >= 2 MakePlayer takes the first free connected pad (0x00229C40 search loop), so P3/P4 may swap pads/characters (HYPOTHESIS). `RemoveGang` -> GangDelete -> FUN_00164738 runs human cleanup FUN_0021C7C8 on every member (call 0x0016478C): a W4P-spawned P3/P4 is released first, then deleted as AI (OK).
**Fallback exposure (R-26).** Type-0 gang "Scopes" (07856:1398-1400): civilian char 425, the competition host, created in cp2 (08023:166) and cp3 (08021:80). In cp2 P1's gang has no AI member after P3 took Cowboy, so P4's join reaches the fallback scan and can take **Scopes** (HYPOTHESIS: first AI type-0 human). Scopes is scripted (TeleportToFlag/GoalMoveToFlag/HuSpeak 08023:224, 479-497, 689; scene Humans 08023:167, 08021:124). Not safe.
**Spawn path.** cp1 (and cp2 before Scopes exists) P4: Cowboy uses `warr_cb_gen`, Snow not created before cp3 -> CHOOSE likely finds no resident absent base model -> extra-model pin (Swan) via GATE. Level pins are non-Warrior ids (07856:170-177). HYPOTHESIS until survey.
**Joining windows.** No `CfgMultiplayerJoin`. Chase (cp4) is POIZO/rail-camera heavy but join stays on.
**Player-1/2-only scripts.** (a) Camera restore after scenes for player/player2 only (08023:178-180, 08024:66-68). (b) Chase cp4 08022: intro POIZO freezes player/player2 (`BrDead` 08022:238-240), AI runners skip any player (08022:231, 272) -> P3/P4 neither frozen nor driven; rail camera only for player/player2 (StartRail 08022:314-316); fixed-cam slow-mo stunts run only while player2 is not human (08022:473-482, parity); kill box: any player falling -> MissionFailed MF_4 (08022:345, 362). (c) Tag competition 08023:562-574 and gallery 08024:164-174: spray count read for player number 1/2 else 0 -> `InvGetSpraycanCharges(0)` = slot -1 -> P3/P4 can never tag (they get the "need paint" text); P1/P2 still can, not blocking. (d) P2 callback `ch4.Multiplayer` 08022:94 (body 08022:325-337): on a P3/P4 leave -> `BrDead` + `GoalDevilRun` (correct AI fallback). Fixes: (c) optional Lua constant patch; others none.
**Starting items.** MS[3] all 0 (04106:4621); comp `InvSetSpraycanCharges(1)` 08023:455 and gallery `InvSetSpraycanCharges(9, 1)` 08024:139 (player 1 only).
**End.** `HUDLaunchMissionComplete()` 08024:330; fails 08026:170 (broke truce), 08022:362, 08023:910, 08024:101, 08024:319 (out of time). 3 -> level95 cp4.

### M7 - level5 "Adios Amigo" (main 08029; chapters 08481 ch1 cp1, 08482 ch1a bar cp2, 08483 ch2 chase cp3, 08484 ch3 Diago cp4; scene tests 08486)
**Squad.** `PlayerGang` 08029:253 = {AddWarriors, AddWarriors05, AddWarriors01, AddWarriors04}, `Mission` 08029:255-258; `player = Ajax` (11, prio 1), `player2 = Cochise` (15, prio 2), globals `Rembrandt`/`Snow` 08029:1988-1991. cp1 08029:1174-1177 and cp2 1486-1489: + Rembrandt 31, Snow 34 (prio 0, `warr_re_gen`/`warr_sn_gen`). cp3 08029:1184-1185 and cp4 1208-1209: Ajax + Cochise only. cp4 Setup adds Rembrandt/Snow from type-0 TempWars02 (08484:68-73, `GangAddMember` 71-72). VERIFIED.
**Free companions.** cp1 Rembrandt, Snow; cp2 Snow, Rembrandt; cp3 none; cp4 Rembrandt, Snow (after Setup). Fallback: TempWars01 is empty (08029:1338), TempWars02 exists only inside cp4 Setup -> nothing in cp3 -> spawn.
**Mission-critical (R-26).** Bar end `EndBar` 08482:150-151: `HuDelete(Rembrandt)`, `HuDelete(Snow)` - exactly the two humans P3/P4 take in cp1/cp2 (VERIFIED script). Deleting a player-owned human without ReleasePlayer (m2_spawn_companion 4) = HYPOTHESIS crash or dead player slot. Not safe in cp1-cp2.
**Spawn path.** cp3 (and after the bar deletes): CHOOSE sees Ajax/Cochise present, Snow/Rembrandt only as gen models -> no candidate (HYPOTHESIS) -> P3 = clone of Ajax, P4 = Swan via pin/GATE. Level pins are non-Warrior ids (08029:2001-2004, 08481:33-37, 08484:53-57).
**Joining windows.** No `CfgMultiplayerJoin`.
**Player-1/2-only scripts.** (a) Chase cp3: `WarpPlayers` (calls 08483:198, 273, 441; body 08483:697-708) teleports only player and player2 -> spawned P3/P4 left behind at every chase warp; chase distance uses min(player, player2) only (08029:3658-3659) -> P3/P4 cannot keep the chase alive. (b) Scripted warps of player, player2, Rembrandt, Snow only: 08481:134-137, 216-219, 297-308; bar 08482:66-69; Diago fight 08484:148-151 with `CloseDoor(Doors.Stl00)` 08484:143 in the same function -> spawned P3/P4 kept from cp3 stay outside the boss room (HYPOTHESIS). (c) GoodToGo objective exit 08029:3391-3395 cancels only for player/player2; `ObjectiveEnter` 08029:3353 accepts any player -> P3/P4 may complete objectives, never block them. (d) POIZO cam rage/normal mode only for player/player2 (08029:3781-3784). (e) P2 callback `C5.SwitchCamGuys` 08484:123 (body 08484:615-630): a P3/P4 leave retargets the shared `DiegoCam` to Diego (cosmetic); boss cam targets player/player2 only (08484:184, 474-484, 568-581). Fix for (a)/(b): X4 teleport-follow hook.
**Starting items.** MS[5] paint 2 (04106:4622): P1 at cp0/1, P2 on first join; no mission Inv call.
**End.** Final scene 08484:285 (`Final = true`) -> HUDLaunchMissionComplete; fail = chase lost 08029:3708/3711. 5 -> level95 cp5.

### M8 - level81 "Encore" (main 08780; chapters 08837 brawl cp1, 08841 horror_house cp2, 08838 chase cp3, 08840 cracker cp4, 08839 chatterbox cp5; 08842 second Main copy, not traced; strings 08844)
**Squad.** `WarriorGangs` 08780:81, `tChapters` 08780:83-87, Main 08780:1731-1745: `player = hCleon` (Cleon, prio 1), `player2 = hSwan` (Swan, prio 2). cp1 AddWarriors1 08780:997-1004: + Ajax 11, Cowboy 18, Fox 21, Rembrandt 30, Snow 33, Vermin 26 (all prio 0, base models). cp2 AddWarriors2 1069-1072: + Ajax 12 (`warr_aj_gen`), Snow 34 (`warr_sn_gen`). cp3 AddWarriors3 1161-1164: Cleon 4 / Swan 9 (chase variants) + Snow 33, Ajax 11. cp4/cp5 1104-1107 / 1114-1117: Cleon, Swan + Snow, Ajax. VERIFIED.
**Free companions.** cp1: 6, picker order Ajax then Cowboy; cp2-cp5: Ajax/Snow (2). Type-0 gangs are Warriors gangs only (08780:995-1212, 08838:170) -> fallback can only return Warriors.
**Mission-critical (R-26).** (a) Brawl end `RunRegroupScene` 08837:343-351: `HuDelete` of Cowboy, Fox, Rembrandt, Vermin -> P4 (Cowboy by list order) is deleted while player-controlled (VERIFIED script, HYPOTHESIS crash). P3 (Ajax) survives. (b) cp2->cp3 `RunCartIntroScene` 08841:325-347 and cp3->cp4 `RunEscapeScene` 08838:277-298: with a human player2 the script creates a 2-member type-0 gang (WarriorsChase / WarAfterChase 08780:1201-1212), calls `HuChangePlayerGang`, then `HuDelete(hCleon)`, `HuDelete(hSwan)`. FUN_00239B80 releases all 4 players and re-seats 4: Cleon and Swan from the new gang, then two PickJoinCompanion calls (0x00239D68) on a gang without AI members -> fallback scan by slot order over AI type-0 humans = the just-released old hCleon/hSwan, Snow, Ajax -> HYPOTHESIS: P3/P4 land on old hCleon/hSwan (created first) which the script deletes next. Safe takeover: Ajax/Snow only.
**Spawn path.** Normally not needed. cp1 has every named base model except Cochise present -> CHOOSE none -> pin if ever needed.
**Joining windows.** `CfgMultiplayerJoin(false)` 08838:83 (chase `GameStart`) ... `CfgMultiplayerJoin(true)` 08838:668 (chase `Cleanup`): **the whole cp3 is closed to new joins**. Players 3-4 dropped at the cp2->cp3 swap, or after any cp3 reload, are BLOCKED until cp4. Setting the flag back on calls UpdateJoin(-1) (FUN_0041A430), which with the 2-player flag set only re-creates cameras (FUN_0041A460 top block) - harmless.
**Player-1/2-only scripts.** Chase cp3 08838: non-player companions go to TempWarriors and follow blockers, players skipped (08838:170-176); cart button-tap control only for hCleon/player2 (08838:235-239) -> P3/P4 run on foot; at `vChaseCam[6]` hSnow/hAjax are teleported to jump flags without a player check (08838:359, 366) -> P3/P4 are pulled forward; `TunnelExited` accepts any player (08838:245); start/rail cams only for player/player2 (08838:378-386). Cracker cp4 freezes only player/player2 (08840:41-57, 138-146). Power switch both-in-box 08841:194/205 only hides/shows a radar marker (cosmetic). Chatterbox zoom cams player/player2 only (08839:165-194, 395, 405).
**Starting items.** MS[81] all 0 (04106:4634); no Inv call.
**End.** Final scene 08839:371 (`Final = 1`) -> HUDLaunchMissionComplete; 81 -> level95 cp6.

### M9 - level86 "Payin' The Cost" (main 09117; chapters 09163 C1, 09164 C2, 09165 C3, 09166 C4; scene test 09168; strings 09169)
**Squad.** `PlayerGang = {AddWarriors1, AddWarriors04, AddWarriors04, AddWarriors3}` indexed by `CHAPTER = GetCheckPoint()` (09117:298, :305, :2595); `player = hCleon`, `player2 = hSwan` (09117:2605-2606). VERIFIED (script).
- cp1 AddWarriors1 (09117:1349-1353): Cleon 1 prio 1 (warr_cl), Swan 5 prio 2 (warr_sw), Vermin 27 prio 0 (own model warr_ve_gen). C1 later adds Snow 34 prio 0 (warr_sn_gen, own gang "Snow" type 0, 09117:1489-1491, created by C1.SnowAdd 09163:607) to GangWarriors1 after the Destroyer cutscene (09163:681).
- cp2/cp3 AddWarriors04 (09117:1671-1676): Cleon, Swan, Vermin 27 p0, Snow 34 p0. cp4 AddWarriors3 (09117:1479-1484): Cleon, Vermin, Snow, Swan.
**Free companions.** P3 = Vermin (first AI member, all cps); P4 = Snow (cp2-4; cp1 only after 09163:681). cp1 before that: P1's gang has no AI member -> fallback scan: type-0 gangs present then = Scene1Warriors (Ash 38/Snow 34, created for the intro scene, HuDelete at 09163:157-158), later GangSnow (Snow AI, BrDead, waiting for the "meet Snow" trigger 09163:607-620). Other type-0 gangs in the level: Tony (civilian char 450, 09117:1394-1396, cp4), DeadAsh (char 40, 09117:1401-1403, cp4), WarriorsExtra (char 43, 09117:1641-1651; its creator SetupExtraFights 09117:146 has no caller), StoreAlertSpawner (soldier spawner, 09117:1458-1460; AlertCleon has no caller). VERIFIED (script text + grep).
**Mission-critical.** cp4 `C4.CleanupScene3` (09166:504-516, called from C4.EscapeTheTrap 09166:441) does `HuDelete` on hSnow, hVermin, hDeadAsh, hTony, hVirgil -> **the two companions P3/P4 control are deleted** (VERIFIED script; crash/softlock HYPOTHESIS). cp4 trap: only player and hSwan are teleported into the cage (09166:183-184), rail/locked cameras are set for player and player2/hSwan only (09166:187-197, 256-257, 312-320, 567-569). Vermin/Snow are scene actors (09163 C1.Scene1, DestroyerCutscene 09163:627ff; 09166:149) and are teleported with the group in C2 (09164 main_5) - harmless for a player (HYPOTHESIS). Safe to take: Vermin/Snow in cp1-3; NOT in cp4.
**Spawn path.** Base models resident: Cleon (warr_cl), Swan (warr_sw); Vermin/Snow use gen models (prio 0). CHOOSE finds nothing resident+absent (Swan/Cleon present) -> clone of Cleon for a spawned P3; P4 pin target = Ajax (first absent candidate after Swan). Pins in level: 180/192/194/43 (Destroyers, warr_ma) 09164:22-25, 09165:42-44. Residency HYPOTHESIS.
**Joining windows.** No CfgMultiplayerJoin in any level86 file (grep, VERIFIED). cp4 runs long locked/rail-camera stretches (09166:109-123, 236-320); whether join is possible under those cameras depends on the camera-type test in FUN_00158728 (types 2/9/0) - HYPOTHESIS. Not blocked for the whole mission.
**Player-1/2-only scripts.**
- C1 protection money: `C1.CleonWantsCash` acts only for player/player2 (09163:396-440, GiveMoney to slot 1/2 09163:430/437); P3/P4 pressing Talk on an owner is ignored -> objective still completable by P1/P2. Hot dogs: player/player2 only (09163:698-706). LOW.
- `SendInDestroyersWave` run-or-teleport distance uses player/human player2 only (09117:3726-3729). LOW (gameplay).
- `StopGangsVandalizing` both-in-box (09117:4034-4037) has no caller (grep) -> dead code.
- cp4 P2 callback `C4.Player2Start(h, joined)` (set 09166:108, body 09166:187-197): on a P3/P4 LEAVE it runs with joined = 0 and switches LockRailCam back to the 1-player versions while player 2 is still in. LOW cosmetic. Fix: leave-event guard for index >= 2 (the session LEAVE cave already skips the Lua event for index >= 2, session_policies 3.4).
**Starting items.** MS[86] all 0 (04106:4636). C1 `GiveMoney(25)` to player 1 (09163:79); `GiveMoney(25, 0)` (09163:575) is rejected (slot -1).
**End.** C4.LockBroken1 -> final scene l86_c4 (`Final`, 09166:588) -> PreCashTheWorld -> HUDLaunchMissionComplete; runNextMission 86 -> level93 cp1 directly (no hub). Fails: shop owner killed (09117:2631-2646), store destroyed (09117:3293-3305), Cleon trashing a store 12x (09163:220).

### M10 - level93 "Destroyed" (main 09321; chapters 09375 C1 .. 09380 C6)
**Squad.** `PlayerGang = {AddWarriors1..6}[CHAPTER]` (09321:217, :2680); `player = hCleon`, `player2 = hVermin` (09321:2693-2694, repeated in the scene-test runners 09321:3291-3530). cp1-3 (09321:1137-1166): Cleon 1 p1, Ajax 12 p0 (warr_aj_gen), Vermin 26 p2 (warr_ve), Snow 34 p0 (gen). cp4/cp5 (09321:1171-1186): same but Snow 33 p0 (base warr_sn). cp6 AddWarriors6 (09321:1191-1194): **Cleon + Vermin only**.
- cp4: clubhouse Warriors Cowboy 19, Fox 21, Cochise 16, Swan 6 (all p0, gang ClubhouseWarriors type 0, 09321:1386-1391) are added to GangWarriors (09378:51-56), then after the door scene moved to GangTempWarriors type 0 (09378:236-241). cp5 scene gang LCWarriors (Swan/Cochise/Cowboy/Rembrandt, 09321:1584-1589) removed at 09379:106.
- Other type-0 gangs: soldier groups Roof/Store/Corner/House/Rally Warriors (chars 49/50 warr_so, 09321:1262-1474), IntroWarriors (09321:1563-1568), LieutenantFighter (09321:1630).
**Free companions.** cp1-5: P3 = Ajax, P4 = Snow (creation order; cp5 reload order Snow then Ajax). cp4 extra candidates: clubhouse four. cp6 none -> fallback (continuous play from cp4: GangTempWarriors AI) else spawn.
**Mission-critical.** cp5 `EndLCScene` `HuDelete(hSnow)`, `HuDelete(hAjax)` (09379:108-109) -> **P3/P4 deleted** (VERIFIED script). cp5 is a stealth tail: the Lieutenant's "see enemy" message (09379:178) or damage -> mission failed (09379:401-438); the chase bar measures Cleon/Vermin only (09379:337-366); only Cleon/Vermin are teleported (09379:132-133) and frozen (DeactivateWarriors). cp6 boss rooms: SetUpWarrior02/WarpToLeaveToStage03/SetUpWarrior03 teleport only hCleon/hVermin and close barricades (09380:339-343, 511-525) -> P3/P4 stranded in the previous room (HYPOTHESIS, HIGH). C6.RestartChapter (custom fail callback) revives and teleports player/player2 only (09380:78-119). Safe to take: Ajax/Snow in cp1-4 only.
**Spawn path.** Base models resident: Cleon, Vermin, Snow (cp4-5), Fox (cp4 clubhouse, 21 p0 = base id). cp6: only Cleon/Vermin created -> CHOOSE finds nothing unless Snow's model stayed cached after 09379:108 (HYPOTHESIS) -> clone of Cleon for P3; P4 pin = Swan. Pins: 208/209, 417/418/420, 49/50 (09375:142, 09376:107-120, 09377:60-64, 09378:41-43).
**Joining windows.** No CfgMultiplayerJoin in level93 (VERIFIED grep). cp5 starts with a scene, cp6 has rail/locked cams per room (09380 main_38/main_40) - camera-type join test HYPOTHESIS. Not blocked.
**Player-1/2-only scripts.**
- C1 store entry (Pharmacy/Liquor) reacts to Cleon or human Vermin only (09375:589-640, 886-931). LOW.
- StartTag spray check: anyone but player2 checks player 1's spray count (09321:2750-2765). LOW.
- P2 callback `HumanPlayerChange(h, joined)` (09321:2695, body 09321:2913-2930): a P3/P4 leave resets MULTIPLAYER_MODE and damage modifiers of player 1 (only on GetPlatform() == 1). cp6 `Multiplayer` callback (09380:588-600) re-targets player2's camera only. LOW.
- cp6 ZoomIn/Out (09380:626-649) and HuIsAPlayer(hVermin) grab block (09380:543): player-2 logic only. LOW.
**Starting items.** MS[93] all 0 (04106:4644). Car trunks hold a Flash/crowbar/bottle (09321:2712-2717).
**End.** Final scene (`Final`, 09380:671) -> HUDLaunchMissionComplete; runNextMission 93 -> level95 cp7 (hub, 09509 -> mission 31). Fails: LC lost/sees enemy (09379:368, 438).

### M11 - level31 "Boys In Blue" (main 07860; chapters P1 07914 Platform, P2 07918 Streets, P3 07912 gclub, P4 07917 Sewers, P5 07915 RedDevil, P6 07911 Birdie; scene test 07916)
**Squad.** `tMission[cp] = {AddWarriorsN, "CheckpointN", file}` (07860:2926-2931), RunLevel `player = Warriors.Cochise`, `player2 = Warriors.Vermin` (07860:2945-2946). cp1-4 (07860:1122-1153): Cochise 15 p1 (warr_co), Vermin 26 p2 (warr_ve), Cowboy 19 p0 (warr_cb_gen). cp5 (07860:1418-1427): + Ajax 12 p0, soldiers Rhino 49, Cody 50, Terrance 54, Ace 52 (warr_so, p0), Cowboy last. cp6 (07860:1526-1534): Cochise, Ace, Terrance, Vermin, Cody, Rhino, Ajax 11 p0 (base warr_aj).
- Scripted changes: hired bums are added to GangWarriors by player/player2 payment (07917:199-235), later moved to GangBumTemp and `RemoveGang` (07917:390-404); P5 (continuous) adds DevilWarriors (Ajax + soldiers) to GangWarriors (07915:98-108) and `HuDelete(Warriors.Cowboy)` (07915:176); P6 moves player2 + Ajax + soldiers into GangBossWar01 type 0 as a "next Warrior" chain (07911:96-131), one returns to GangWarriors per death (07911:216).
- Other type-0 gangs: RDSceneWarriors (Snow 34, Fox 22) created at P4 start and **killed but revivable** (07917:88-93), removed at P5 (07915:177); DevilWarriors (07860:1576-1582, cp5); BossWar01 (cp6); SceneCleon (07860:1302-1308, no caller).
**Free companions.** cp1-4: P3 = Cowboy; P4: no AI member -> fallback: cp1-3 nothing (spawn/pin), cp4 the downed RDScene Fox/Snow or a hired bum (fallback and the main picker do not skip downed humans: FUN_0022A770 checks FUN_00227DD8 etc. only when param_2 != 0; UpdateJoin passes 0, 0x0041A52C) VERIFIED code. cp5 reload: P3 = Ajax, P4 = Rhino (generic soldier). cp6: P3 = Ace, P4 = Terrance (soldiers).
**Mission-critical.** Cowboy is deleted at P5 start (07915:176) -> **P3 deleted in continuous play from cp1-4**. `RemoveGang` = GangDelete -> FUN_0016D068 -> FUN_00164738, which runs FUN_0021C7C8 on every member (VERIFIED code) -> a P4 holding an RDScene Warrior or a bum is destroyed (07915:177, 07917:404). Cowboy is also teleported in the bum poizo (07917:139-145, fine for a player). P6 chain: P3/P4 as chain soldiers are teleported to hiding spots, GangSuspend'ed and act as "lives" (07911:96-140) - MED.
**Spawn path.** Base models resident: Cochise, Vermin; Ajax base only in cp6 (present). CHOOSE: nothing -> clone of Cochise for a spawned P3; P4 pin = Swan. Pins: 156/259/101/102 (07912:25-28, 07918:49-52, released 07917:41-44). Soldiers 49-54 have no named HUD index (m2_spawn_name.md 1.2: other ids -> index 12 / 20+player index, asset 0x31) - name panel HYPOTHESIS.
**Joining windows.** One call: `CfgMultiplayerJoin(false)` in `P6.NewWarrior` (07911:205) at the first Warrior death of the Birdie boss fight (with the SCATTER tutorial); never re-enabled in level31 (grep). P3/P4 who have not joined by then are locked out until a reload (GAME OVER / level load re-enables, F-0066). Only the final fight; not the whole mission. VERIFIED script.
**Player-1/2-only scripts.**
- P2 cash objective: `InvGetMoney(1) + InvGetMoney(2) >= 75` (07918:554, 568, 592, 625), payment from slot 1 then 2 (07918:666-673); money picked up by P3/P4 (nearest player picks up, F-0156) does not count -> objective can stall if level money runs short (HYPOTHESIS, MED). Minimal fix: in this level redirect item-2 InvAdd for slots 2-3 to slot 0 (cave at the InvAdd slot check 0x0041E5E0), or a Lua patch adding InvGetMoney(3)+(4) (harder: bytecode growth).
- Bum hiring needs player/player2 money (07917:199-230): P3/P4 ignored. LOW.
- P1 `TurnbullsRun` advances if player or human player2 alive (07914:166). LOW. Scene cast with player2 branch (07918:148-160). LOW.
- `CamSetSecondary(Birdie, 0, 1)` (07911:217) targets player 2's secondary camera only (HYPOTHESIS).
**Starting items.** MS[31] all 0 (04106:4628); Flash/paint dealers (07860 RunLevel StartFactory).
**End.** P6 final scene (`Final`, 07911:388) -> ReturnFromBirdieFall -> `HUDLaunchMissionComplete()` (07911:394; PreCashTheWorld also calls it); runNextMission 31 -> level95 cp8 (09510 -> mission 14). Fail: all chain Warriors / player killed (07911:233).

### M12 - level14 "Set Up" (main 07655; chapters 07698 RadiosAndStores (table C2), 07695 dirtycop (C3), 07696 JSB (C4))
**Squad.** `PlayerGang = {AddWarriors02, AddWarriors02, AddWarriors04}` (07655:254); `player = Cowboy` (= Warriors.Cowboy), `player2 = Warriors.Cochise` (07655:2113-2115). Squad = **Cowboy 18 p1 (warr_cb) + Cochise 15 p0 (warr_co)** only (07655:1178-1181, 1199-1202). Player 2 takes Cochise (only AI member).
**Free companions.** None. Fallback: no other type-0 gang in level14 (GangCreate list: only Warriors01-04 are type 0; 07655 grep) -> SPAWN for P3 and P4. VERIFIED script.
**Mission-critical.** Cochise is a scene actor and the AI-thief branch (`TheftCallback` counts loot when Cochise is NOT a player, 07698:139-147) - unaffected by P3/P4. No deletes of squad members.
**Spawn path.** Base models resident: Cowboy, Cochise (present). CHOOSE finds nothing -> **P3 = clone of Cowboy** (body and HUD COWBOY), P4 = pinned Swan (ENSURE at P3's join). Level pins 253/254/156/157/369/370/372-374 (07655:244-252, non-Warriors). Memory for the Swan pin HYPOTHESIS (survey X0 per level).
**Joining windows.** No CfgMultiplayerJoin in 07655/07695/07696/07698 (VERIFIED grep). The scan's "level14 join off 2" are the hub scripts 09401:6314 and 09512:3456, assigned to level14 by scene prefix. Not blocked.
**Player-1/2-only scripts.**
- Radios/loot are counted through `CfgHuInventoryCallback("C2.Stolen")` (07698:43, 127-139) for any slot; only the speech differs (07698:149-163). P3/P4 thefts count if the callback fires for slots 2-3 (HYPOTHESIS, inventory patch). `C2.MONEY` = P1+P2 money is computed but not used for the objective (07698:162). LOW.
- cp2: 5 radios given to player 1 (07695:41), removed after the trunk plant (07695:154); any player can plant (07695:100). LOW.
- `RadioStolen` car event only when player2 is not human (07655:2071). LOW.
- cp3 JSB stealth: any GangWarriors member seen/hurting JSB -> mission failed (07696:120-130), timer fail (07696:314): P3/P4 must sneak too. MED (gameplay, human test).
**Starting items.** MS[14] all 0 (04106:4626).
**End.** cp3 final scene l14_c3 (`Final`, 07696:546) -> HUDLaunchMissionComplete; runNextMission 14 -> level95 cp9 (09511 -> mission 13). Fails: car destroyed (07655:2003), cops take loot (07698:120), JSB (07696:124-129, 314).

### M13 - level9 "All-City" (main 09229, chapters 09720 ch1 / 09721 ch2 / 09722 ch3, scene tester 09724; hub cp script 09511)
**Squad (per checkpoint).** Loader `main_131` (09229:3445-3492): `mState = GetCheckPoint()`, `{AddWarriors1, AddWarriors2, AddWarriors3, AddWarriors4}[mState]` (AddWarriors4 is undefined -> cp 1-3 only), `player = Warriors.Rembrandt` (3458), `fox`, `snow`, `player2 = Warriors.Snow` (3461), `SetPlayer2Callback(TwoPlayerMode)` (3485). Every AddWarriors (09229:1170-1192): Rembrandt 30 prio 1 (`warr_re`), Snow 33 prio 2 (`warr_sn`), Fox 22 prio 3 (unflagged -> base 21 `warr_fo`). VERIFIED (script).
- Scripted changes: ch1 `StartTheLevel` (09720:148-158) `TeleportToFlag(fox, fPScout[4])` + **`HuDelete(fox)`** + `Warriors.Fox = nil`; ch2 start `AddFoxMid` (own type-0 gang, 09721:40-42), mid scene, then `RemoveGang(GangFoxMid)`/`HuDelete(fox)` (09721:155-159); ch2 `AddFox` (type-0 `GangFox`, suspended, rooftop objective, `GoalAreaWalker(fox)`, 09721:247-270); ch2 end `GangAddMember(GangWarriors, 0, fox)` (09721:293); ch3 Fox = radar secondary objective (09722:156-158). VERIFIED.
- Type-0 side gangs: `GangCleon` = Cleon char 2 prio 0 **and civilian "scopes" char 425** (09229:1197-1200), created in ch1 Setup (09720:52), destroyed by `RemoveGang` in `NextScene` = ReturnFunc of the intro cinematic l9_c1 (09720:134). RemoveGang -> GangDelete -> `FUN_00164738` runs `FUN_0021C7C8` on every member (VERIFIED code), so Cleon/scopes are gone before gameplay; exposure only during the intro cinematic, where joins are blocked (HYPOTHESIS: none in practice). `GangFoxMid`, `GangFox` are type 0; `GangScopes`/`GangFinalScopes` are type 2 (09229:1244, 1251).
**Free companions for P3/P4.** ch1 before `StartTheLevel`: Fox (prio 3) - what the M2 runs took (F-0154/F-0160). After it and in ch2 until 09721:293: P1's gang = Rembrandt+Snow -> fallback scan -> after `AddFox` it grabs the **scripted rooftop Fox** (type-0 GangFox); before that SPAWN. ch3: Fox free (prio 3). Player 4: always SPAWN.
**Mission-critical.** Fox is NOT safe in ch1/ch2: HuDelete core `FUN_00233EF0` (0x00233EF0-0x00233F5C) has **no player check and no ReleasePlayer** -> deleting a P3-controlled Fox destroys a live player's human (HYPOTHESIS: crash or dead player slot; bot runs probably never reached `vbCutscene2`). ch3 Fox is safe (only goals/scenes/radar, like `player2` Snow). Rembrandt/Snow = P1/P2.
**Spawn path.** Resident Warrior bodies: Rembrandt, Snow, Fox (+ `warr_cl_gen`) (F-0143). CHOOSE finds none -> spawned P3 = Rembrandt clone (if Fox's `warr_fo` stays cached after his deletion CHOOSE may pick Fox -> duplicate Fox when the script re-creates him, HYPOTHESIS); P4 = Swan via pin (F-0154 VERIFIED one instance, F-0160 lockstep). ch3 pins 8 more non-Warrior chars (09722:38-51) -> less pool room at cp3 (R-28, HYPOTHESIS).
**Joining windows.** No `CfgMultiplayerJoin` in any level9 file (VERIFIED). Blocked only by the L9_IN movie and cinematics (l9_c1, trainyard, mintro, cops, arrest, l9_c1_a, l9_c3, l9_c4). Never blocked for a whole checkpoint.
**Player 1-2 only logic.**
- `WarriorTagging` (09229:2279-2290): spray check uses number 2 only for `player2`, else 1 -> P3/P4 tag against **P1's** spray count (HYPOTHESIS: engine then uses their own empty slot; MS[9] paint goes to P1/P2 only). Fix: give P3/P4 the level's starting spray (no Lua change).
- `EnterGraveTrain`/`LeaveSub` (09229:2667-2720): any player triggers; the rail cam is built on `player`, and for P3/P4 P1's follow-cam slot/flag (L3 = 0, `bMainCam`) is changed (HYPOTHESIS: P1 camera disturbed). Fix (Lua): skip unless `A1 == player or A1 == player2`.
- ch1 `CopSceneDone` (09720:269-282): whoever entered `vbTriggerBeast` (no player check, 09720:249-250) is teleported to Snow's flag if not `player`, plus `CameraMakeActive(MainCam, 0, nil, that human)` (263, 279) (HYPOTHESIS: camera confusion only).
- ch2 `ContinueLevel` (09721:129-163): cameras re-activated only for `player`/`player2` (137-142); `Warper(Warriors, fCh2Warp)` (163) moves only the `Warriors` table -> spawned P3/P4 left behind (open area, HYPOTHESIS).
- ch3 end `CheckWarParty` (09722:249-262; loop over `Warriors`, disassembly `local/analysis/lua/09722_c33a118d.txt` main.11): Rembrandt, Snow, Fox must stand in `vbFinalObj` -> a P3-controlled Fox must walk there; spawned P3/P4 ignored. OK.
- `TwoPlayerMode` (09229:3026-3036): a leave of ANY index sets `TunnelEffectsAllowed = 1`; harmless while the W4P LEAVE cave skips the Lua event for index >= 2.
**Starting items.** MS[9] = paint 6 (04106:4624) to P1 and to P2 on first join; P3/P4 get nothing in a tagging mission.
**End.** ch3 `MissionOver` -> `HUDLaunchMissionComplete()` directly (09722:310-311); next level95 cp10. No MissionFailed call.

### M14 - level51 "Desperate Dudes" (main 08031; chapters 08181 ch1, 08182 ch2, 08183 ch2a, 08184 ch3, 08185 ch5, 08186 ch8, 08187 ch9; scene tester 08189; hub cp script 09501)
**Squad (per checkpoint).** `PlayerGang = {AddWarriors, AddWarriors01, AddWarriors02a, AddWarriors02, AddWarriors04, AddWarriors05, AddWarriors07}` (08031:176, cp1-7), `Mission[1..7]` = chapter1, 2, 2a, 3, 5, 8, 9 (08031:178-184); `Main` (08031:1274-1290): `player = Warriors.Swan`, `player2 = Warriors.Snow`. Swan 5 prio 1 (`warr_sw`; cp7 id 9 = flagged chase body), Snow 33 prio 2 (cp7 id 36 flagged). Every other Warrior is created with **priority 0 and a `_gen` id** (Ajax 12, Vermin 27, Fox 22, Rembrandt 31, Cowboy 19, Cochise 16) -> own `_gen` bodies. cp1/cp2: Swan+Snow only (08031:415-427); cp3/cp4: + Ajax (433-435, 603-607); cp5: + Ajax, Vermin (440-445); cp6/cp7: all 8 (509-518, 776-785). VERIFIED.
- Scripted additions: ch1 `StartToRun` creates type-0 `WarrSplit02` Ajax, suspended in a pit fight (08181 main_5); ch2 `AjaxAddToWarriors`/`AjaxFightTB2` -> Ajax into GangWarriors (08182:107, 150); ch3 Vermin rescue in type-0 `WarrSplit01` (radar objective, god mode, 08184 RunVermin) -> `VerminAddToWarriors` (08184:551); ch5 `GladToSeeYa` adds Cochise, Cowboy, Fox, Rembrandt from type-0 `WarrSplit` (08185:721); ch8/ch9 move all six companions into type-0 `GangWarRun` (08186:36-49; 08187:45, 228). The cp7-reload path runs `HuChangePlayerGang(GangWarriors07)` + `RemoveGang(GangWarriors)` in Setup (08187:49-51), before any join (HYPOTHESIS: harmless for P3/P4).
**Free companions for P3/P4.** cp1 after StartToRun: none in P1's gang -> **fallback grabs the pit-fight Ajax** (suspended type-0 gang); P4 -> SPAWN. cp2: before his fight ends again the pit Ajax via fallback. cp3/cp4: Ajax (first AI member); P4 in cp4 -> fallback could grab the **rescue target Vermin**. cp5: Ajax, Vermin. cp6/7: six free. VERIFIED rule/script, runtime HYPOTHESIS.
**Mission-critical.** Pit-fight Ajax (until `AjaxAddToWarriors`) and rescue target Vermin (ch3) must not be taken. Squad companions are handled like `player2` (teleported with the group 08183:141-144, 08184:119-121, 08185:190-195; scenes) -> safe to take. Chases: companion-players are moved to GangWarRun, `DeactivateBrain(Warriors)` and teleported to `flgRunEnd` (08186:200-210) -> parked at the end while P1/P2 run (HYPOTHESIS: they spectate).
**Spawn path.** Only `warr_sw`/`warr_sn` bodies resident by construction; pins: chars 100-103, 12, 27 (08031:1314), Vermin base 26 in ch3 (08184:57). CHOOSE: no resident absent Warrior -> spawned P3 = Swan clone; P4 pin = first absent name (cp6/7: all 8 present -> **Cleon**, story-odd; CHOOSE order is data at 0x000E1580).
**Joining windows.** `CfgMultiplayerJoin(false)` `C7.InitChase` (08186:187) -> `true` `C7.GoFinalRun` (08186:340) -> `false` `C9.SetEnd` (08187:186) -> `true` `C9.FinishMission` (08187:495, mission end). After a reload at cp6/cp7 the flag goes off at gameplay start (`C7.StartLevel` 08186 main_6 -> InitChase(1); ch9 StartLevel -> SetUpBusChase -> SetEnd) -> **P3/P4 BLOCKED until the mission ends** (VERIFIED script). Players already in stay in; a GAME OVER "Last checkpoint" in a chase releases them.
**Player 1-2 only logic.**
- Chapter warps teleport `player`, `player2` and named companions only (08181:88-89, 08182:72-73, 08183:141-147 then `CloseDoor` ChA03/ChA04, 08184:117-121, 08185:190-195, 08186:136/212-215, 08187:118) -> spawned P3/P4 **left behind**, possibly behind closed doors (HYPOTHESIS). Fix: hook "teleport W4P-spawned humans (+0x1B1 == 7) next to player 1 whenever player 1 is teleported" (HuTeleportNearHuman core `FUN_0023B138`); medium.
- Chases: rail cam (08186:360-363), QTE taps `HuSetButtonTapControl(player/player2)` (08187 main_6/15/16/17), tireless/goals only for P1/P2 (08186 main_11/15). Spawned P3/P4 stay in GangWarriors at the chase start; any GangWarriors member's msg 18 calls `C7.KillButtons` -> StopTheGame (08186 main_2) -> **possible spurious chase failure** (HYPOTHESIS). Fix: park P3/P4 for the chase (W4P humans into GangWarRun + teleport to `flgRunEnd`), or a W4P "sit-out" (leave/rejoin around the join-off window) - needs a user decision.
- `ChangeRangeTo3` both-in-box (08183:451-457, 08184:483-489, 08185:602-608): stealth hearing reset once P1 and P2 left; P3/P4 ignored -> slightly easier. No fix.
- Clubhouse wrecking (08184:325-402): bar active while P1/P2 inside; P3/P4 alone pause it (objects still count). Minor.
- P2 callbacks `C3.CheckPlayer2CH` (08184:330), `C7.SetPlayerOff` (08186:186), `C9.SetPlayerOff` (08187:185) move/teleport `player2` on a leave of ANY index (08186:177-181) -> safe only while the W4P LEAVE cave skips the Lua event for index >= 2 (session_policies 3.4).
- POIZO cams (08031:2623-2660, 2738-2756) switch only view 0 and reset P1/P2 modes. Minor.
**Starting items.** MS[51] = revive 1, paint 1 (04106:4631). Chase starts remove P1's Flash (`InvGiveRevive(-InvNumberRevives())`, default player 1: 08186:200-201, 08187:241-242).
**End.** `C9.FinishMission` -> scene l51_c10 `Final = true` (08187:496) -> PreCashTheWorld -> HUDLaunchMissionComplete; next level52 cp1. Failure: `LanchMissionFailed` (08186:399, 08187:481), retry callbacks `C7.RestartCH7`/`C9.RestartCH9`.

### M15 - level52 "No Permits, No Parley" (main 08191; chapters 08255 C1 / 08256 C2 / 08257 C3 / 08258 C4; 08259 duplicates the CW/PK code, no loader found - HYPOTHESIS unused)
**Squad (per checkpoint).** `PlayerGang = {AddWarriors1..4}` (08191:283), `Mission[1..4]` (285-288); `Main` (08191:2450-2470): `player = hSwan`, `player2 = hSnow`. All four squads (08191:1196-1205, 1235-1244, 1448-1457, 1506-1515) = all 8 Warriors: Swan 5 prio 1, Snow 33 prio 2, the other six **priority 0 with `_gen` ids**. VERIFIED.
**Free companions for P3/P4.** cp1: first AI members in creation order = **Ajax, then Cowboy** (08191:1198, 1201). cp2/cp3 (scatter phase): P1's gang = Swan+Snow -> **fallback scan** over the type-0 gangs `CW.Gang<Name>` (six scattered Warriors, 08191:2529-2621) and `ParkGang` (3347); UpdateJoin calls `FUN_0022A770` with param_2 = 0, so downed/arrested humans are NOT excluded (VERIFIED code) -> P3/P4 take a scattered rescue target (e.g. the downed Fox). cp4: squad present (scenes only). `FinalMercy` = Mercy char 221 in a type-0 gang (08191:1482-1484, 08258:14): non-Warrior fallback exposure only if P1's gang had no AI member.
**Mission-critical.** C2/C3 = "find the scattered Warriors": `SetupPrimaryEvents` (08191:2525-2634; called by C2 Setup 08256:92-97 and C3 Setup 08257:31-33) teleports each named companion, **`HuKill(hFox)`/`HuKill(hCowboy)`** (2528, 2592), `BrDead` Rembrandt/Ajax, arrests Cochise/Vermin, moves each into its own type-0 gang; `PickupX` (2638-2876) re-adds them when a player reaches them. C1 continues into C2 inside the level (`OrphanGateTriggered` -> `ScheduleFunc("NextMission")` 08255:571-580) -> **P3/P4 who took Ajax/Cowboy in C1 are scattered: P3 captured (BrDead), P4 knocked down and re-ganged** (VERIFIED script; effect HYPOTHESIS). No companion is safe in C1-C3.
**Spawn path.** Only `warr_sw`/`warr_sn` bodies resident by construction; pins are non-Warrior chars (08255:70-73, 08256:24-31). All 8 named Warriors present -> P3 = Swan clone, P4 pin = **Cleon** (only absent name; story-odd). Spawned W4P humans are untouched by `SetupPrimaryEvents` (named handles only) -> spawn is the safe path here.
**Joining windows.** No `CfgMultiplayerJoin` in level52 files (VERIFIED). C4 (08258) is cutscene-only (l52_c2 -> final l52_c6). Not blocked otherwise.
**Player 1-2 only logic.**
- Pickups/events gate on `HuIsAPlayer(A1)` (08191:2638-3191, 3488) -> P3/P4 can collect Warriors and trigger events (works).
- Park exit (08191:3488-3541): scripted walk/camera for hSwan/hSnow only; `WarriorsExitPark`/`NumWarriorsInBox` skip players (3519, 3697) -> companion-players are never parked (AI ones are used; fine). GoodToGo gate objective (`GTDistance` 20, 08191:3383; loop over `Warriors` in 04106 main_145) needs companion-players near the gate; spawned ones ignored.
- Teleports name hSwan/hSnow/companions (08255:216-226, 456-472; 08257:15-17): spawned P3/P4 left behind (HYPOTHESIS; open area).
- `EndOrphanScene` `BrFlush(player2)` only if human (08255:460). No P2 callback, no both-in-box, no per-player Inv calls.
**Starting items.** MS[52] all zero (04106:4620).
**End.** C4 `RunFinalScene`: scene l52_c6 `Final = true` (08258:83) -> PreCashTheWorld -> HUDLaunchMissionComplete; next level54 cp1. No MissionFailed call.

### M16 - level54 "Home Run" (main 08262, chapters 08355 ch1 streets, 08349 ch2 alley, 08352 ch3 park, 08353 ch4 popsicle, 08350 ch5 boss; scenes 08354)
**Squad.** Loader 08262:3274-3307 (`main_114`): `L0 = {AddWarriors1..5}[GetCheckPoint()]`, `player = Warriors.swan` (08262:3289), `SetPlayer2Callback(AnotherPlayer)` (08262:3298). P1's gang holds **only Swan** (char 5, prio 1, warr_sw) at cp1-cp3 (`AddWarriors1/2/3`, 08262:1078/1410/1085). The other Warriors run in separate type-0 "AltWar" gangs per chapter: Snow (33, prio 2, warr_sn), Cowboy (19, prio 0 -> warr_cb_gen), Ajax (12, prio 0 -> warr_aj_gen) (`AddAltWar`/`AddAltWar2`/`AddAltWar3`, 08262:1124-1126/1401-1403/1269-1271; `player2 = AltWar*.snow` 08355:39, 08349:77, 08352:31). Player 2's join callback `AnotherPlayer` (08262:2654-2680) moves the joiner into P1's gang (`GangAddMember(GangWarriors,0,A0)`) and teleports it to Swan. cp3 mid-chapter `AjaxFacesUp` (08352:187-213; HuChangePlayerGang 08352:201): `AddAjax` (Ajax 11 prio 2 warr_aj, Cowboy 18 prio 3 warr_cb, gang type 0), **`HuChangePlayerGang(GangAjax)`** (player = ajax, player2 = cowboy), then `RemoveGang(GangWarriors)` and `RemoveGang(CUR_WAR_GANG)`. cp4 Setup (08353:31-56): `AddFinalWarriors` (Snow 33 prio 3, Swan 5 prio 2), `HuChangePlayerGang(GangWarriors)` back to Swan, `GangDelete(GangAjax)` (if giStart ~= 4), `AddAjaxFinal` (Ajax 12 / Cowboy 19 prio 0, type 0), `FoundThem` adds them to P1's gang (08353:198). cp5 `AddWarriors5` (Swan p1, Snow p2, Ajax 12 p0, Cowboy 19 p0 all in P1's gang, 08262:1452-1455). Intro-only gang `WarriorsC` (Cochise 16, Rembrandt 31, Fox 22, Vermin 27 prio 0, **Mercy 221 `orph_me`**, type 0; 08262:1090-1097) is removed after the intro scene (08355:140).
**Free companions for P3/P4.** cp1-cp3: none in P1's gang (Swan + joined Snow) -> PickJoinCompanion fallback scan of type-0 gangs -> AltWar **Ajax/Cowboy** (prio 0, first in human-slot order) (VERIFIED logic FUN_0022A770 + script; runtime HYPOTHESIS). cp4 after `FoundThem` and cp5: Ajax, Cowboy in P1's gang (normal pick).
**Mission-critical.** AltWar Ajax/Cowboy are chase NPCs: god mode, `GoalDevilRun`/`TeleportToFlag`/`Warper(CUR_GANG_TABLE)` (08355:60-90, 08262 main_97), cowboy `HuKill` (08352:224). Taken by P3/P4 they stay in the AltWar gang (join event skipped for index>=2), keep god mode, get AI goals. **Not safe:** `AjaxFacesUp` `RemoveGang(CUR_WAR_GANG)` (08352:207) deletes the AltWar3 humans -> GangDelete core FUN_00164738 calls the human cleanup FUN_0021C7C8 (jal at 0x0016478C) whose player branch only frees the pad owner and calls RemovePlayer (jal 0x0021CAF8) - no ReleasePlayer, no camera/view/drop-in-mask/inventory cleanup (VERIFIED code; effect HYPOTHESIS: stale view or crash, same class as run C). `HuChangePlayerGang` core FUN_00239B80 (VERIFIED decompile all_03.c:2852) releases only players whose gang == P1's gang, re-makes the others' count with PickJoinCompanion(new gang) + MakePlayer(h, pad -1) (pad by free-pad scan, not the recorded pad). In ch4 Setup with 4 released players the 3rd/4th picks fall back to the just-released GangAjax Ajax/Cowboy (prio 2/3, type 0), which `GangDelete(GangAjax)` (08353:43) then deletes while they are players (HYPOTHESIS, same defect).
**Spawn path.** Base models created: warr_sw, warr_sn always; warr_aj/warr_cb only cp3 (GangAjax) to ch4; everything else only `_gen` variants (prio 0). CHOOSE: Swan/Ajax/Snow/Cowboy present, Cochise/Vermin/Fox/Rembrandt/Cleon base models not created -> clone or pin (HYPOTHESIS until survey). No SetCharacterModel pins.
**Joining windows.** No CfgMultiplayerJoin in level54 (join on all level). Chase sections use per-player rail cameras (`CamSetupRail(..., index 0/1)` 08355:194, 08352:128); join needs a follow-type camera (type 2/9/0) - rail camera type unknown (HYPOTHESIS; the original lets P2 join mid-chase, `AnotherPlayer` handles `chase`).
**P1/P2-only scripts.** (a) `chase.CamSwitcher` (08262 main_97) and ch2 `GatePicked` (08349:464-480): camera index = 1 only for `player2`, else 0 -> a P3/P4 entering a cam volume rebuilds **P1's** rail camera on himself (HYPOTHESIS: volumes fire for any player). Fix: Lua patch `if A1 ~= player and A1 ~= player2 then return end` (feasible) or map to index 2/3. (b) Rail cameras, `HuSetNoAutoLock`, `HuMakeGrounded` (08349:258-293), `HuIsAPlayer(snow)` (08355:275, 08352:89) only for P1/P2: P3/P4 keep follow cams (cosmetic). (c) `AnotherPlayer` on a P3/P4 **leave** (game's own drop-out path; the session LEAVE cave skips Lua leave events for index>=2): sets `CUR_GANG_TABLE["snow"] = A0`, `Warriors["snow"] = nil`, re-goals the real Snow (human P2) -> corrupts the chase tables (VERIFIED script). (d) `ch4.CheckIfFightStart` (08353:154) checks only player/player2 for attackers. (e) No both-in-box, no Inv*(...,2). `YouAreGoingTheWrongWay` -> FAIL_3 (08355:343) is never registered (dead code, VERIFIED grep).
**Starting items.** MS[54] all 0 (04106:4630). No mission Inv* calls. World pick-up `Objects.ExtraRevive` destroyed below difficulty 2 (spawned 08262:2023, destroyed 08262:3305).
**End.** ch5 final scene `l54_c3_c` `Final = 1` (08350:202) -> PreCashTheWorld -> HUDLaunchMissionComplete; runNextMission 54 -> 55 cp1 (04106:1761).

### M17 - level55 "Friendly Faces" (main 08357, chapters 08403 party cp1, 08401 lizzies attack cp2, 08404 punk fight cp3; 08400/08405/08406/08407 not referenced by `Mission[]`)
**Squad.** `PlayerGang = {AddWarriors01, AddWarriors02, AddWarriors04}` and `Mission[1..3]` (08357:108-112); `Main` (08357:1455-1470): player = Rembrandt (cp1-2) / Swan (cp3), `player2 = Warriors.Vermin`. cp1/cp2 gang: Cochise 16 prio 0 (warr_co_gen), Rembrandt 30 prio 1 (warr_re), Vermin 26 prio 2 (warr_ve) (08357:1016-1038). cp3 `AddWarriors04` (08357:1045-1051): Cochise 16 p0, Vermin 26 p2, Rembrandt 31 p0 (warr_re_gen), Swan 5 p1 (warr_sw), Cowboy 19 p0 (warr_cb_gen), Snow 34 p0 (warr_sn_gen), **Mercy 222 (`orph_me`, non-Warrior) p0**. Continuous play into cp3: `AddWarriors04` + **`HuChangePlayerGang(GangWarriors04)`** + `RemoveGang(GangWarriors)` (08404:81-83).
**Free companions.** cp1-2: P3 = **Cochise** (only AI member); P4 = none -> SPAWN. cp3: P3 = Cochise, P4 = Rembrandt(31) (member order; Mercy is 7th, so not taken with <= 4 players - VERIFIED order, HYPOTHESIS runtime). No other type-0 gangs with AI humans except `GangCochise` (08357:1241, Cochise01) if created.
**Mission-critical.** cp1 party: Cochise is the scripted bait - `GoalJoinCinematic(Warriors.Cochise, PARTY.KISSSCENE, ...)` + `ScenePlayCinematic(PARTY.KISSSCENE, ..., "PARTY.BossSceneComplete", ...)` (08403:215-218), dialogue flag `fCochiseTalk`/`HuSpeak(Warriors.Cochise, ...)` (08403:540-556), teleport to `fCochiseTalk` (08403:188). The game only exempts player2 (Vermin's kiss scene is skipped when `HuIsAPlayer(player2)`, 08403:204-213). **Taking Cochise in cp1 is NOT safe** (AI cinematic goal on a player, HYPOTHESIS: P3 locked or scene broken). cp2: Cochise only in scene Humans lists / boss target mark (OK, like player2 in 2P). cp3: **Mercy escort** - `MercyDied` -> HUDLaunchMissionFailed(MERCYDIED) (08404:484); Mercy must never be taken (safe by order).
**Spawn path.** cp1-2 base models: warr_re, warr_ve only (Cochise is `_gen`); Swan/Ajax/Snow/Fox/Cleon/Cowboy base not created -> CHOOSE finds nothing -> P4 needs the **extra-model pin** (GATE pins Swan first). If Cochise is excluded in cp1 (fix below), P3 also spawns -> clone of Rembrandt unless the pin is extended to P3. Pins in level: Lizzie chars 237-243 only (08403:16-22, 08401:4-10; released 08404:4-10).
**Joining windows.** No CfgMultiplayerJoin in level55. Party (cp1) runs looping in-world kiss cinematics (`ScenePlayCinematic(..., looping true)`, 08403:212-218, 442, 453); FUN_0039D870 sets the cinematic block GameMgr+0x410 only when the scene player's +0xED == 1 (VERIFIED code) - whether these scenes set it is unknown: **HYPOTHESIS that join/pause are blocked for the whole party** (check GameMgr+0x410 in cp1).
**P1/P2-only scripts.** (a) Callbacks: `PARTY.Multiplayer` (08403:225-234): on a **leave** (A1 == 0, any index via the game's drop-out path) re-registers `fVerminTalk` and reloads kiss2 -> `KissReloaded` puts `Warriors.Vermin` (= human P2) into `GoalJoinCinematic` (VERIFIED script) -> a P3/P4 drop-out would hijack P2; `C3.Multiplayer` (08401:223-234) leave no-op; `C5.Multiplayer` empty (08404 main_6). (b) cp2 boss camera `CamSetSecondary(player,0,0)` / `(player2,0,1)` and `HuSetAutoCombat` (08401:147-207, 226, 242, 287) - P3/P4 get normal follow cams (cosmetic). (c) cp3 `HuLockPad(player/player2)` + `PadSetHandlerEx("C5.OpenAllDoors")` (08404:211-234): P3/P4 not locked during the stall ambush; `BrDead(player/player2)` in Reinforcements/BackToFollow (08404:384-410) leaves P3/P4 free; `RailCamIn/Out` switch view 0 for any player (08404:657-663). All cosmetic/minor; fix optional (Lua: add the P3/P4 handles). (d) Party Lizzie dialogue picks a line for player/player2 only (08403:355-378): P3/P4 get no line (harmless).
**Starting items.** MS[55] all 0 (04106:4632). `InvGiveRevive(1)` = player 1 only at the bathroom (08404:187).
**End.** cp3 final scene `l55_c9` `["Final"] = true` (08404:725) -> HUDLaunchMissionComplete; runNextMission 55 -> 84 cp1 (04106:1762). Fail: Mercy dies.

### M18 - level84 "Come Out To Play" (main 09030, chapters 09113 intro cp1, 09110 chase cp2, 09112 final cp3, 09111 end/credits cp4; scenes 09115)
**Squad.** `PlayerGang = {AddWarriorsSC, AddWarriors, AddWarriors02, AddWarriors02}`, `Mission[1..4]` (09030:~100-105), `Main` 09030:1624-1650: player = Swan, player2 = Snow. All three squads put **7 humans in P1's gang**: Swan 5 p1 (warr_sw), Snow 33 p2 (warr_sn), Rembrandt 31, Cowboy 19, Vermin 27, Cochise 16 (prio 0 -> `_gen` models), **Mercy 222 (`orph_me`) p0** (09030:1074-1080, 1133-1139, 1171-1177). cp2 `InitChase` (09110:181-200): **`HuChangePlayerGang(GangWarChase)`** (Swan 9 p3 / Snow 36 p4 chase variants, 2 members, 09030:1222-1223); Cochise/Vermin in `WarRun` (type 0); `StartTheBeach` `HuChangePlayerGang(GangWarriors)` (09110:402). cp3 `FinalFight` moves Cochise/Vermin/Cowboy/Rembrandt into **GangTempWars (type 6)** and Mercy into **GangMerci (type 0)** (09112:199-205; gangs 09030:1066, 1085); `StartTheEnd` puts them back (09112:975). cp4 `FadeToBlack` **`HuDelete` Mercy, Vermin, Cochise, Rembrandt, Cowboy** (09111:126-136), then `HuChangePlayerGang(GangRiff01, true)` (09111:263, players become Riffs for the credits fight) and `HuChangePlayerGang(GangWarriors)` (09111:316).
**Free companions.** cp1-2 order: SC/AddWarriors -> P3 Rembrandt, P4 Cowboy; cp3-4 (AddWarriors02 order) -> P3 Cowboy, P4 Vermin. Mercy is 5th-7th -> not taken while the 4 Warriors are in P1's gang. **During cp3 rounds 1-2** (companions in type-6 TempWars) P1's gang has no AI member -> fallback scan of type-0 gangs finds **Mercy (GangMerci)** -> **P3 = Mercy** (VERIFIED logic, HYPOTHESIS runtime); P4 then spawns (CHOOSE: Swan/Snow/Cochise/Vermin/Cowboy/Rembrandt present, Ajax/Fox/Cleon not resident -> clone or pin).
**Mission-critical.** Mercy (god mode, suspended, in every final scene, 09112:146, 222, 992-1000). Companions are scene actors and ring spectators (OK). cp4 deletes the companions -> **human P3/P4 deleted** by `HuDelete` (core FUN_00233EF0 only flags + destroys; whether it reaches the cleanup FUN_0021C7C8 is unknown - HYPOTHESIS crash/ghost player).
**Spawn path.** P1's gang always has >= 4 Warriors except cp3 rounds 1-2; pins in level are Rogues only (81/82/83, 78/79, 09030:1641-1645, 09112:66-70).
**Joining windows.** `CfgMultiplayerJoin(false)` in `SceneRun1` (09113:28, intro start), again `C1.PlayCar` (09110:226); `RunSceneC3` (09112:134-135) only if player2 is AI; **on again only in `C5.StartRound2`** (09112:314); `FinalScene` off if player2 is AI (09112:992-993). Level start sets join on (ResetLevel 0x001607B8). => **P3/P4 are BLOCKED for all of cp1-cp2** (intro + 2-player button-tap car chase `HuSetButtonTapControl(player/player2)` 09110:117-120, 355-360, 458-460), and in continuous play for cp3 round 1. Code exception: the in-game drop-in allows joining in level 0x54 at checkpoint 4 even with a type-1 camera (0x001591B4 `li v1,0x84`, 0x001591B8 `li a0,0x54`, 0x001591D0 `lh v0,0x33A(v1)`, 0x001591D4 `xori v0,v0,4`, 0x001591D8 `movz s6,s3,v0`; VERIFIED disassembly) = the credits fight, where joiners become Riffs.
**P1/P2-only scripts.** (a) cp2 chase: callback `C1.SetPlayerOff` (09110:84-92) on any **leave** moves `player2` into WarRun and AI-runs the leaver (drop-out path only). `C1.CAMChange` both-in-box `IsInsideBox(VCarChaseTrig[13], player/player2)` (09110:362-363) -> fade; P3/P4 absent here anyway. (b) cp3 `C5.SetRailCam` (09112:683) uses camera index 1 for every non-`player` -> a P3/P4 entering `vFOVZoom` (MoveInFOV/OUT 09112:664-674) rebuilds **P2's** rail camera on himself (HYPOTHESIS). Fix: Lua guard `A0 == player or A0 == player2`. (c) `KnifeThrower`/POIZO (09112:500-560, 09030:1696/1809), `DeactivateWarriors` (04106 main_5: `BrDead(player/player2)` + `GangSuspend(GangWarriors)`) - P3/P4 are not frozen by BrDead (HYPOTHESIS: suspended through the gang); POIZO skip only on P1/P2 pads. (d) `C5.SetPlayer2Fight` gives `InvGiveRevive(1, 2)` on P2's first join (09112:304). (e) cp2 Restart/RunMissionFailed (09110:133-170, 275) revive/teleport only player/player2.
**Starting items.** MS[84] revive 1 (04106:4635) -> P1 at cp0/1 (main_150), P2 at first join (main_153); cp3 `InvGiveRevive(1, 2)` for P2.
**End.** cp4 `FinishMissionNow`: `HuChangePlayerGang(GangWarriors)` + `HUDLaunchMissionComplete()` (09111:316-317); runNextMission 84 -> 95 cp11 (post-game hub, 04106:1763). With 4 players the 3rd/4th re-make picks find nobody (fallback empty after the deletes) -> P3/P4 simply dropped (VERIFIED code: MakePlayer only if the picker returns non-zero). Fail: `LEVEL84.KO` car chase (09110:275).

## 4. Starting items for players 3-4 (question 4; design only)

**How the game does it (VERIFIED, WAD 4106):** `InventorySetup` (main_149, `04106:4616-4651`) fills `MS[level]`;
`SetupLevelInventory` (main_150, `04106:4653-4680`) copies `MS[Level]` to the global `p2Inventory` and, **only at
checkpoint 0 or 1**, gives it to player 1 (`InvGiveRevive`, `InvSetSpraycanCharges`, `InvSetMoney`, `InvGiveSkeletonKey`,
`InvGiveItem(5, ...)` with player 1); it registers `InventoryPlayer2` as the multiplayer callback. `InventoryPlayer2`
(main_152, `04106:4686-4699`) runs on a **join** at checkpoint 0/1 and calls `SetPlayer2Inventory` (main_153,
`04106:4700-4708`), which gives the same values to player 2 and then deletes itself (first join per level load only).
Players 3-4 get nothing: the join-event guard skips the Lua event for index >= 2, and the functions hard-code 1 and 2.

Non-zero `MS` entries of the 18 story levels (`04106:4618-4649`; all others are 0):

| Level (mission) | revive (Flash) | paint (spray charges) | money |
|---|---|---|---|
| 87 (M3) | 0 | 1 | 15 |
| 5 (M7) | 0 | 2 | 0 |
| 9 (M13) | 0 | 6 | 0 |
| 51 (M14) | 1 | 1 | 0 |
| 84 (M18) | 1 | 0 | 0 |

Mission scripts also give items themselves (per-mission sections, "Starting items"); those calls use player 1 and/or 2.

**Smallest way to give players 3-4 the same (recommended: option S1 = fix X7):**
- **S1 (C cave, no Lua):** extend the join-event guard cave (0x000F0ED0, where s0 = joining human, s3 = joined): for
  player index 2/3, joined = 1, GameMgr+0x33A <= 1 and a per-slot "already given in this level load" byte not set, look
  up the level number (`*(G+0x14D4 + (u16)*(G+0x56DC)*0x84 + 4)`) in a 5-row table (values above) and call the cores
  directly with player number p = HUD slot + 1: `FUN_0041EDB8(n, p)` (InvGiveRevive), `FUN_0041F030(n, p)`
  (InvSetSpraycanCharges), `FUN_0041EEB8(n, p)` (InvSetMoney). Clear the bytes in the level-teardown hook that already
  exists (`CLRPIN` 0x000E1600). About 40 words + 20 data words. Deterministic (runs inside the synchronised join).
  Mission-specific gives (calls in the mission scripts) are not covered; where they matter (per-mission sections) use
  S2 for that mission.
- **S2 (Lua, needs route L of 1.3):** at the join of player 3/4 run
  `InvGiveRevive(p2Inventory.revive,p) InvSetSpraycanCharges(p2Inventory.paint,p) InvSetMoney(p2Inventory.money,p)
  InvGiveSkeletonKey(p2Inventory.cuffkeys,p) InvGiveItem(5,p2Inventory.cuffs,p)` - exact parity with player 2 including
  future table values (`p2Inventory` survives `MS = nil`, `04106:4658-4663`). Depends on the unproven Lua-string cave.
- Parity rule to keep: only at checkpoint 0/1 and only on the first join of that slot per level load (like
  `SetPlayer2Inventory = nil`); later checkpoints restore slots 2-3 from the checkpoint copy (`[4p inventory]`, F-0155).

## 5. Mission end and the next mission (question 5)

### 5.1 The flow (VERIFIED code and script text; runtime as marked)
1. **Trigger.** Normally the last scene: a scene table with `Final` -> `PreCashTheWorld` (`04106:2970-3017`, main_127)
   -> `HUDLaunchMissionComplete()`; a few chapter scripts call `HUDLaunchMissionComplete()` directly (e.g. `07851:220`,
   `07911:394`, `08024:330`, `08407:131`, `09111:317`, `09722:310-311`). The Lua binding `MissionComplete` (0x0036DF28 ->
   `FUN_00160D00`: GameMgr+0x14C = 2, loading index = GameMgr+0x56DC + 1) is not called by any shipped script; the
   in-game update would answer 0x14C == 2 with `FUN_0015D420(0)` (all_00.c:60933).
2. **`FUN_0015D420(param)`** (binding `HUDLaunchMissionComplete` 0x0036F218): if the top mode is not id 0xB, push the
   **mission-complete mode** object 0x005E5DF8 (vtable 0x00538658: id getter 0x004DDE40 = 0xB, enter `FUN_0015CF70`,
   exit `FUN_0015D128`, resume `FUN_0015D0F0`, update `FUN_0015D160`); param 0 sets 0x0050C754 = 1; mode+0x24 = param.
3. **Enter `FUN_0015CF70`** (next mode-loop step; enter and update run in the same call, `FUN_00156100`/`FUN_00155F78`):
   mode+0x24 = 0; every AI human (+0x1B0 == -1) is cleaned up (`FUN_0021C7C8(h, 0)`), every player human is frozen
   (brain+0x1B = 0, flags); then it calls the Lua global named at 0x0054F528 = **`UnlockAndLoad`** (`04106:1695-1711`):
   - `MissionCompleteUnlocks` (`04106:1713-1741`): unlocks; rank points = score of `player` + `player2` only;
   - `LiquidizeAssets(player, true, true, true, false)` and, if `player2` is a human player, the same for `player2`
     (`04106:1861-1878`): **money set to 0 and Flash/spray/keys/cuffs removed for players 1 and 2 only**;
   - `runNextMission(1)` (`04106:1743-1781`): `SetCheckPoint(next cp)` (FUN_0041ABC0 -> checkpoint copy of all four
     inventory slots with `[4p inventory]`), `SoundStopMusicTrack()`, `MenuLoadLevel("level"..next)` (FUN_00160D78:
     GameMgr+0x14C = 3 + loading index), `HUDLaunchMissionComplete(4)` (top is 0xB now, so only mode+0x24 = 4).
     Table: 99->80, 80->87, 87->95 cp1, 34->95 cp2, 2->95 cp3, 3->95 cp4, 5->95 cp5, 81->95 cp6, 86->93, 93->95 cp7,
     31->95 cp8, 14->95 cp9, 9->95 cp10, 51->52, 52->54, 54->55, 55->84, 84->95 cp11 (all missions at checkpoint 1).
4. **Update `FUN_0015D160`** (same frame, mode+0x24 = 4): pops itself, pops the in-game mode (id 1, vtable 0x00538480),
   **adds the money of slots 0 and 1 to the bank** (0x0015D3B0-0x0015D3F0) - already 0 because of step 3 - then
   `FUN_00155308` (start of the save sequence, mode 0x005E5810). The loading mode (id 8) loads the next level.
5. **Next level start:** ResetLevel (join on), the level script, then UpdateJoin(-1) re-creates player 2 from a
   companion if the 2-player flag GameMgr+0x56EC is set (it survives the level change, level_jump.md 2) - except in the
   hub, where the clubhouse switches joining off first (`09401:6314`; F-0066 runtime: 1 player in the clubhouse).

### 5.2 What happens to players 3-4 across the transition
- Frozen at step 3, destroyed with the level (F-0158: player count 0 after the mission-complete entry, no crash with
  R8; W4P-added Warriors and the extra-model pin go with the level, `CLRPIN`). **They must join again in the next
  mission** (Start press, rule in 1.2); D7 is not involved (nobody "leaves").
- Their inventory slots 2-3 are **not** cleared by `LiquidizeAssets` (players 1-2 only) and are copied into the
  checkpoint copy by the `SetCheckPoint` of step 3. Next level at checkpoint 1 (every mission start) -> InvClear
  (`FUN_00418C68`) -> zero, so nothing carries into the next mission (VERIFIED code). Hub (checkpoint >= 2) ->
  InvRestoreCheckpoint brings slots 2-3 back in the hub, where nobody owns them (harmless with D4 A; R-29 stays open
  for D4 B).

### 5.3 F-0158 (money bank) explained
F-0158 measured bank 0 -> 70 with money 10/20/30/40 and `[4p inventory]` Block B. The static flow above explains it
exactly: `UnlockAndLoad` zeroes slots 0-1 before `FUN_0015D160` banks them, so only Block B's slots 2-3 (30 + 40)
reached the bank. The "shortcut" `FUN_0015D420(4)` takes the same path as the real `HUDLaunchMissionComplete()`
(push, enter, Lua, update); only 0x0050C754 differs (set by param 0). VERIFIED code / consistent with the F-0158
measurement; supersedes F-0158's HYPOTHESIS ("players 1-2 released before banking").
Consequence: in the original game **mission money is never banked** for players 1-2 (it is discarded); Block B makes
players 3-4's money the only money that reaches the saved bank. **Fix X8:** replace Block B (0x0015D3F4 -> 0x000E5000)
by "clear slots 2-3" = `FUN_0041EC60` (InvReleaseSlot: live and checkpoint copy) for slots 2 and 3, then
`j 0x00155308` - parity with `LiquidizeAssets` and it also closes R-29 for the mission-end path. ~10 words.

## 6. Hub interludes (question 6, D4 A)

### 6.1 What the host has to do (VERIFIED script text)
After missions 3, 4, 5, 6, 7, 8, 10, 11, 12 and 13 (levels 87, 34, 2, 3, 5, 81, 93, 31, 14, 9) the game loads level95
at checkpoint 1-10 (`runNextMission`). `Main` (`09401:6601-6623`) loads `level95_chapter<cp>`; `RunLevel` (`09401:6624-6645`)
starts in the **clubhouse**: `clubhouse.Setup` switches **joining off** (`09401:6314`) and removes player 1's
cuffs (`09401:6361`). The chapter script defines an action chain run by `story.RunMissionAction` (`09401:2986-3159`):

| Hub cp | WAD | Next mission | Required chain |
|---|---|---|---|
| 1 | 09500 | 34 (M4) | red circle at Vermin (`fVermin[4]`) -> scene l34_c5_a -> clean war party -> collapse -> scene l34_c5_b -> load |
| 2 | 09504 | 2 (M5) | red circle at the menu flag (`fMenu[5]`) -> scenes wonderwheel_95 / l2_c1 -> ... -> l2_subentr -> load |
| 3 | 09505 | 3 (M6) | red circle at Cleon -> scene l3_c8_a -> **hub objective `CM_BURNER`**: tag burners outside (`09505:130-136`: objective "TAG" 2/5, `InvSetSpraycanCharges(2)` for player 1, `env.LeaveClubhouse`) -> scene -> back into the clubhouse -> scenes -> load |
| 4 | 09506 | 5 (M7) | red circle at Ajax -> scene l5_c1 -> ... -> l5_c8_a -> load |
| 5 | 09507 | 81 (M8) | red circle at the menu flag -> scene l81_c1 -> load |
| 6 | 09508 | 86 (M9) | red circle at the menu flag -> scene l86_c5 -> load |
| 7 | 09509 | 31 (M11) | red circle at Cleon -> l31_c1 -> ... -> l31_c7 -> load |
| 8 | 09510 | 14 (M12) | red circle at Cleon -> l14_c6_a -> ... -> l14_c6_b -> load |
| 9 | 09511 | 9 (M13) | red circle at Cleon -> l9_c4_a -> ... -> l9_c4_b -> load |
| 10 | 09501 | 51 (M14) | red circle at Cleon -> scene l51_c11 -> load |
| 11 / 12 | 09502 / 09503 | none (post-game, after 84 / after Armies stage 5) | red circle, `MA_LOADLEVEL` with no level = nothing |

(`fRunMission` `09401:78-90`; the WAD order is alphabetical: 9500 = chapter1, 9501 = chapter10, 9502/9503 = 11/12,
9504-9511 = chapters 2-9, confirmed by the scene ids and the scene-test table `09401:7030-7058` in main_247.) Correction:
docs/MISSIONS.md says the `CM_BURNER` objective is at checkpoint 4; it is checkpoint 3 (WAD 9505; its objective string
is `LEVEL95.MS_C4_1`, `09505:59`, which may be where "4" came from).
The red circle reacts to any human player (`story.EndMissionActionFlag`, `09401:3201-3233`: `HuIsAPlayer(A1)`).
`MA_LOADLEVEL` -> `story.LoadLevel` (`09401:3298-3312`): `LiquidizeAssets(player, true, true, true, true)`,
`SetCheckPoint(1)`, `SSMC_StartSaveSequence()` (memory-card save), `MenuLoadLevel("level"..N)`. Before the red circle
the host may also roam Coney and play side activities (optional; outside, `coney.Setup` switches joining **on**,
`09513:2867`, and leaving the clubhouse calls `CheckMultiplayer()` `09401:6929`, which re-creates player 2 from a
companion in the original 2-player game; minigames switch it off/on, `09513:731`/`755`).

### 6.2 Players 2-4 waiting in sync (design, X12)
- All four instances keep running the hub in lockstep; only the host's input reaches the game. W4P masks slots 2-4 to
  neutral input (no Start: joining is on outside the clubhouse, and a Start would make them players), and shows on
  their screens "Host is in the hideout - next: Mission N <name>" instead of the game picture (D8: they have no own
  view; no streamed view). Pause (D17/D18) and the skip vote stay available; for hub scenes the vote should count only
  the host (players 2-4 are not in the scene).
- **Keep player 2 out of the hub:** in the original, player 2 comes back automatically outside the clubhouse
  (`CheckMultiplayer`, `CfgMultiplayerJoin(true)` -> UpdateJoin(-1) -> MakePlayer on a free **connected** pad). W4P
  should report the pads of slots 2-4 as disconnected during the interlude (port +0x10C = 0, the same trick as
  session_policies.md 3.4) and reconnect them when the next level starts loading, **player 2's pad first**, so the
  level-start UpdateJoin(-1) rebinds player 2 to his own pad (level_jump.md 4: otherwise it may take pad 1). HYPOTHESIS
  until tested.
- After the load: player 2 is re-created by the game; players 3-4 re-join by the auto-Start rule of 1.2.

### 6.3 What W4P can read to know "hub interlude in progress" (VERIFIED addresses)
| Read | Address | Meaning |
|---|---|---|
| level number | `*(G + 0x14D4 + (u16)*(G + 0x56DC) * 0x84 + 4)`, G = `*(0x0051489C)` | 95 = hub (same expression as `FUN_0022A770`, 0x001591B8 test) |
| level name | string at G+0x124 | "level95" (read in every session-policy run) |
| checkpoint | u16 G+0x33A | 1-10 = required interlude before the next story mission; 11/12 = post-game |
| leaving | s32 G+0x14C | 3 = MenuLoadLevel requested (interlude ends; reconnect pads) |
| mode stack top | `*(0x005E66A0 + 4 * *(0x0050C784))` | 0x005E5D90 loading (id 8), 0x005E56B8 in-game (id 1), 0x005E5DF8 mission complete (id 0xB), 0x005E6550 pause (id 10), 0x005E5810 save sequence |
| join flag | s32 G+0x56E8 | 0 in the clubhouse, 1 outside |

Rule: `interlude = level == 95 and 1 <= cp <= 10 and G+0x14C == 0`. Flashback missions started from the hub (levels
82, 92, 83, 20, 11, `MA_LOADFBLEVEL`) are D3 (original 1-2 player behaviour): players 3-4 keep waiting there too.

## 7. Per-mission risk table (question 7)

Joining: "companion" = the game's picker gives player 3/4 a squad member; "spawn" = `SPAWN` (clone of player 1 unless
`CHOOSE` finds a resident absent Warrior) and, for player 4, the extra-model pin (Swan first); "blocked" = scripts keep
joining off. Status of every mission: **NOT YET TESTED** (four-player). Smoke = `python -I tests/m6/mission_smoke.py
--missions N` (4 instances, bots, checkpoint 1); later checkpoints by the same level jump with `SetCheckPoint(cp)`
(`--callat "4000:0041ABC0:<cp>,4010:00160D78:<entry>"`, entry = 0x01FD996C + (N-1)*0x84 while GameMgr = 0x01FD8400).

| M | Level | Joining (P3 / P4) | Main risks | Proposed fix | Test to run |
|---|---|---|---|---|---|
| 1 | 99 | spawn: clone of Rembrandt / pin Swan | squad swap cp1->cp2 (`HuChangePlayerGang` 09654:61) drops P3/P4 and `RemoveGang` deletes their clones (VERIFIED code, HYPOTHESIS runtime); window jump counter freezes a 3rd/4th player (09655:336-350, HYPOTHESIS); P3/P4 not teleported with P2 in the tutorial | X3, X11, X4; X6 for the window counter | smoke cp1 through the combat chapter into cp2; human run of the roof/window part |
| 2 | 80 | companions Rembrandt, Cowboy, Snow (cp1 P4 = Ajax via fallback before his recruit scene) | `HuDelete` of six companions at 08777:374-379 hits P3/P4 (VERIFIED script, crash HYPOTHESIS); Ajax taken before 08774:238/259 | X1, X2 | 4-player run cp1-cp4; PINE GameMgr+0x224/+0x228.. around 08777:374 |
| 3 | 87 | companions Cowboy, Ajax (cp1 through the fallback from WarriorsCh1, like player 2) | `HuDelete(ajax)` at cp5 start (09225:154); cp1 tally needs P3/P4 in the box; stealth fail by roaming P3/P4 (HYPOTHESIS); tagging uses P1's spray (09171:3650-3657) | X1, X7, (X4) | run through cp1 tutorial and cp5 start; count/handles at 09225:154 |
| 4 | 34 | companion Ash / pin Swan | pin may not fit while riot/gate pin 9 models (07968:74-82, 07965:11-19; R-28 HYPOTHESIS); loot start sum P1+P2 (07968:273) | accept FITCHK fallback or pin at level start | smoke cp1 and cp4 with extra_survey; N_NOFIT, pool free |
| 5 | 2 | companions Rhino, Ash, Terrance, West (prio 0) | none found; HUD names of generic ids 52-54 (HYPOTHESIS) | none | smoke, screenshots of P3/P4 name panels |
| 6 | 3 | companions cp3-5 (Cowboy, Rembrandt); cp1-2 P4 spawn, or civilian Scopes via fallback in cp2 | Scopes (char 425) as player (HYPOTHESIS, R-26); `HuChangePlayerGang` cp2->cp3 (08021:200-221) re-seats P3/P4; P3/P4 cannot tag (spray of player 0) | X2, X3, X6 (tagging) | cp2 join of P4 (char id must not be 425); cp2->cp3 play-through, pad owners |
| 7 | 5 | companions Rembrandt, Snow cp1-2 / spawn (clone Ajax + pin) cp3 / companions cp4 | bar end `HuDelete(Rembrandt/Snow)` 08482:150-151; `WarpPlayers` 08483:697-708 and boss warps leave spawned P3/P4 behind a closed door (08484:143) | X1, X4 | cp1 to the bar end (emulog, count); cp3 chase positions; cp4 boss room reachable |
| 8 | 81 | companions Ajax+Cowboy (cp1), Ajax+Snow (cp2-5); **joining blocked in cp3** (08838:83-668) | brawl end deletes Cowboy (08837:343-351); two `HuChangePlayerGang` + `HuDelete(hCleon/hSwan)` transitions (08841:325-347, 08838:277-298) can seat P3/P4 on the deleted humans | X1, X3, X13 (cp3) | cp1 brawl end; cp2->cp3 and cp3->cp4 transitions; cp3 reload + Start presses |
| 9 | 86 | companions Vermin, Snow (cp1 before 09163:681: fallback or spawn) | cp4 `C4.CleanupScene3` deletes Vermin/Snow (09166:504-511); P3/P4 outside the cp4 cage and rail cameras (HYPOTHESIS); type-0 civilians Tony/DeadAsh (09117:1394-1403) | X1, X2 | continuous cp1 -> cp4; cp4 reload with 4 players |
| 10 | 93 | companions Ajax, Snow (cp1-5) / spawn (clone Cleon + pin) cp6 | cp5 `HuDelete(hSnow/hAjax)` (09379:108-109); stealth tail fails on any Warrior seen (HYPOTHESIS); cp6 room warps of Cleon/Vermin only + barricades (09380:339-525) strand P3/P4 | X1, X4 | continuous cp4 -> cp6; cp6 reload; human run of the stealth tail |
| 11 | 31 | companion Cowboy (cp1-4) / spawn+pin cp1-3, fallback (downed scene Warrior or bum) cp4; soldiers cp5-6 | `HuDelete(Cowboy)` at cp5 start (07915:176), `RemoveGang` of scene/bum gangs (07915:177, 07917:404); cash objective sums P1+P2 (07918:554-683); join off for the rest of the Birdie fight (07911:205) | X1, X2, X6 (cash), X13 | cp4 with P4 joining; cp4 -> cp5; human run of the cash objective |
| 12 | 14 | spawn: clone of Cowboy / pin Swan | no companion at all; stealth fail by P3/P4 (gameplay) | X10 (optional) | smoke cp1 (names, pin, memory); human run of cp3 |
| 13 | 9 | P3: Fox (ch1 before the trainyard scene, ch3), else spawn; P4: pin Swan (VERIFIED F-0154/F-0160) | **`HuDelete(fox)` 09720:157 / 09721:159 while P3 holds Fox** (VERIFIED script; the M2 runs never reached it); fallback takes the scripted rooftop Fox in ch2; P3/P4 tag with P1's spray; subway rail cam guard | X2 (Fox cp1-2), X1, X7, X6 | P1 scripted into vbCutscene2 with P3 = Fox: TLB miss? count? P3 playable? |
| 14 | 51 | cp1 spawn (fallback would take the pit-fight Ajax), companions cp2-7; **join blocked after a reload in cp6-7** (08186:187-340, 08187:186-495) | fallback takes pit Ajax / rescue Vermin; 7 chapter warps leave spawned P3/P4 behind (08183:141-147 + doors); chase KO of any squad member may fail it (HYPOTHESIS) | X2, X4, X13, X9 | 4 bots from cp1 and cp6; positions after 08183 main_5; chase with P3/P4 |
| 15 | 52 | **spawn only** (clone Swan / pin Cleon) | companions are scattered/knocked down by C2 setup (08191:2525-2634); fallback grabs downed rescue targets and Mercy (08191:1482-1484) | X2 (level52: no companions), X9 | cp1 to the orphan gate (C1->C2): P3/P4 playable; cp2 reload + late joins |
| 16 | 54 | fallback AltWar Ajax/Cowboy (god-mode chase NPCs) cp1-3 / normal companions cp4-5 | `HuChangePlayerGang` + `RemoveGang`/`GangDelete` at 08352:201-207 and 08353:31-56 delete human P3/P4; P1 rail cam hijack (CamSwitcher, HYPOTHESIS) | X2, X3, X1, X6 | cp1 -> cp3 `AjaxFacesUp` and cp3 -> cp4 with 4 players; count, views, TLB miss |
| 17 | 55 | P3 Cochise (cp1 = kiss-trap bait), P4 spawn+pin (cp1-2); Cochise + Rembrandt cp3 | Cochise cinematic goal on a player (08403:215-218, HYPOTHESIS); party cinematics may block join (GameMgr+0x410, HYPOTHESIS); `HuChangePlayerGang` cp2->cp3 (08404:81-83) | X2 (Cochise cp1), X3, X5 | cp1 party with 4 players (GameMgr+0x410, P3 state); cp2 -> cp3 pad owners |
| 18 | 84 | **blocked cp1-cp2** (09113:28 ... 09112:314; 2-player car chase); companions cp3-4, but **Mercy** via fallback in cp3 rounds 1-2; credits: joiners become Riffs (code exception 0x001591B4-0x001591D8) | Mercy as player 3 (VERIFIED logic); credits `HuDelete` of companions (09111:126-136) and two `HuChangePlayerGang`; P2 rail cam hijack (09112:683) | X2, X1, X3, X13 (decision), X6 | cp3 reload + Start in round 1 (who is P3); cp3 -> cp4 credits with 4 players |
| hub | 95 | none (D4 A: players 2-4 wait) | auto re-creation of player 2 outside the clubhouse; cp3 burner objective outside | X12, X11 | hub cp1 and cp3 with 4 instances: inputs masked, no join, next mission loads, P2-P4 back |

## 8. Open points and runtime checks (for the coordinator)
1. **Effect of deleting a player-held companion** (X1 priority): one single-instance run, Mission 13 with P3 = Fox, player 1
   scripted into `vbCutscene2` (09720:127) - expect a crash or a dead slot (HYPOTHESIS). This also limits the M2 Mission
   13 evidence (F-0154/F-0160) to the stretch before that trigger.
2. Extra-model fit per level (R-28): `extra_survey` at M4 cp1/cp4, M3 cp2-4, M13 cp3 (heavy level pins).
3. Join under rail/locked cameras (camera-type test of 1.2): M9 cp4, M10 cp6, M16 chases; GameMgr+0x410 during the M17
   party cinematics.
4. `ObjectiveGoodToGo` (04106 main_145) loops over a list the pseudo-Lua lost: read the bytecode (`tools/lua40_dump.py`)
   to see whether it is the mission's `Warriors` table (sections 3 M14/M15) or the gang list.
5. lua_State pointer for X6 (static: script manager `*(0x00512B04)` and the callers of `FUN_003290D0`).
6. The core of `TeleportToFlag` (binding 0x0036CDC0) for X4.
7. Hub: pad "disconnected" trick during the interlude and the pad player 2 gets back (section 6.2).
8. Corrections to `docs/MISSIONS.md` (not edited here): the `CM_BURNER` hub objective is at checkpoint 3 (WAD 9505), not
   4; the scan's "level14 join off 2" come from the hub scripts 09401:6314 and 09512:3456; per-level scan counts miss the
   main scripts the scan files under "shared" (07920, 08031, 09030, 09607 ...).

# Mission inventory (BRIEF §4.1, §4.2, §8.4)

Build: SLUS-21215 v1.03. Status at the end of Stage 1 (2026-10-10). Every mission is **NOT YET TESTED** in any
four-player sense; nothing here claims four-player support works.

## How missions were identified (evidence)
1. In-memory level table at GameMgr+0x14D4 (runtime dump, F-0009): entries 1-18 named "1:Coney" ... "18:Coney",
   entries 19-23 named "A:" ... "E:", entries 24-28 levels 60-64, entry 29 level95, then unnamed levels.
2. Mission names table GSTRING.MISSIONNAME (WAD 3776, English; F-0063) and the in-game Replay Levels map (screenshots).
3. Script cheat "unlock everything" list (WAD 4106) contains exactly the 28 levels of entries 1-28 (F-0009).
4. Hub story scripts (WAD 9401, 9500-9512; F-0064): `fRunMission` (main missions launched by required hub
   story steps), `FBMission` (flashback missions chosen by the player, no prerequisites), Armies of the Night stage 1
   gated on all five flashbacks.
5. `GameMgr+0x56DC + 1` is the next level index after "mission complete" (0x00160D00), so levels 1-18 follow in table
   order; mid-story missions are launched through hub action chains (`MA_LOADLEVEL`).

## Classification

| Class | Levels | Evidence |
|---|---|---|
| **MAIN STORY** | 99, 80, 87, 34, 2, 3, 5, 81, 86, 93, 31, 14, 9, 51, 52, 54, 55, 84 (missions 1-18) | numbered 1-18 in the level table and name tables; launched by mission-complete chaining or by required hub action chains (`fRunMission`) |
| **MAIN STORY (transition / hub interludes)** | level95 hub action chains (12 checkpoint scripts WAD 9500-9511) | required between missions: walk to a red-circle marker, cutscenes, cleanup, sometimes a hub objective (e.g. `CM_BURNER` tagging at checkpoint 4), then `MA_LOADLEVEL` to the next mission |
| **OPTIONAL/NON-STORY (proposed)** | Flashback missions A-E: 82 Roots, 92 The Best, 83 Heavy Muscle, 20 Scout's Honor, 11 Sharp Dressed Man | launched only by the player from clubhouse flashback spots (`MA_LOADFBLEVEL` only in WAD 9512); no story step requires them; they unlock Armies of the Night. **Needs the user's decision** (they are story-themed). |
| **OPTIONAL/NON-STORY** | Armies of the Night stages 60-64 ("Stage 1"-"Stage 5") | arcade machine in the clubhouse, gated on the flashbacks; separate minigame |
| **OPTIONAL/NON-STORY** | level95 free-roam activities (`roam.mini` minigames, side jobs) | started by the player in the hub; not in the required action chains |
| **OPTIONAL/NON-STORY** | Rumble arenas 101-137 ("Junkyard", "Fight Pen" ...) | Quick Rumble / Rumble menu (`PlayRumbleModeLevel`, `CfgRumble*`); "Fight Pen" = level102 observed |
| **UNRESOLVED (probably cut)** | level7 "Graveyard Shift" ("17:Prospect Park") | name strings only; no level scripts; not in level table entries 0-39 (F-0065) |
| **NOT CONTENT (developer/test)** | levels 90, 91, 94, 96, 97, 98, 70-73 ... (unnamed table entries) | no names; not reachable from menus seen |

## Main-story missions (preliminary per-mission facts)

Columns: script facts are counts from `tools/mission_scan.py` (evidence: `evidence/missions/mission_scan.json`).
"Join on/off" = `CfgMultiplayerJoin(true/false)` calls in that mission's scripts; join is ON by default at level start
(F-0066). "P2 human?" = number of `HuIsAPlayer(player2)` branches (scripts that behave differently when a second
human plays). "Both-in-box" = objective checks that test `player2` inside a trigger volume. "Named Warriors" =
companions referenced by name in the mission's scripts (count of references; roles NOT yet classified).
"Opposition" is OUR reading of abbreviated gang global names in the scripts (e.g. `GangStreetDestroyers`, `HurrA`,
`PFurBack`, `TBConHang`); the expansions (Destroyers, Hurricanes, Furies, Turnbull ACs ...) are HYPOTHESES until
confirmed in game.

| # | Level | Name (area) | Join on/off | P2 human? | Both-in-box | P2 teleports | Named Warriors in scripts | Opposition (gang globals) | Original 2P support |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 99 | New Blood (Coney) | 2/2 | 30 | 0 | 12 | Vermin, Cleon, Rembrandt, Ash | CombatEnemy (tutorial) | 2P VERIFIED partially: second human controlled Ash as player 2 after choosing 2 PLAYER (F-0024/F-0025, E4) |
| 2 | 80 | Real Live Bunch (Coney) | 2/2 | 0 | 0 | 0 | Fox, Ajax, Snow, Cowboy, Cleon, Vermin | Destroyers, cops | HYPOTHESIS: join after the Ajax objective (script); not observed |
| 3 | 87 | Payback (East Coney) | 0/0 | 8 | 1 | 1 | Rembrandt, Ajax, Vermin, Cowboy | dancing/club crowd, spawners | HYPOTHESIS (default on) |
| 4 | 34 | Blackout (Riverside) | 0/0 | 0 | 0 | 0 | Ash, Snow | Moonrunners, Rogues, Panzers, cops | HYPOTHESIS (default on; few player2 refs) |
| 5 | 2 | Real Heavy Rep (Tremont) | 0/0 | 1 | 0 | 0 | Fox, Cleon, Ash, Mercy | Orphans, Clinic gangs | HYPOTHESIS |
| 6 | 3 | Writer's Block (Soho) | 0/0 | 16 | 0 | 0 | Snow, Rembrandt, Ajax, Cowboy | Hi-Hats, Pursuit | HYPOTHESIS |
| 7 | 5 | Adios Amigo (East Harlem) | 0/0 | 9 | 1 | 9 | Snow, Rembrandt, Ajax, Cochise | Hurricanes | HYPOTHESIS (uses WarpPlayers 3x) |
| 8 | 81 | Encore (Coney) | 1/1 | 17 | 2 | 0 | Cleon, Swan, Ajax, Snow, Vermin, Rembrandt | Hi-Hats, Cracker Jack | HYPOTHESIS |
| 9 | 86 | Payin' The Cost (Coney) | 0/0 | 6 | 1 | 0 | Snow, Cleon, Swan, Vermin, Ash | Marcello, Twiggy | HYPOTHESIS |
| 10 | 93 | Destroyed (East Coney) | 0/0 | 7 | 0 | 1 | Swan, Cochise, Cowboy, Cleon, Vermin, Ajax | Destroyers | HYPOTHESIS |
| 11 | 31 | Boys In Blue (Pelham) | 0/1 | 2 | 0 | 2 | Cochise, Vermin, Snow, Cowboy, Fox, Ajax | Bulls, cops, bums | HYPOTHESIS (join off at a tutorial step) |
| 12 | 14 | Set Up (Bensonhurst) | 0/2 | 4 | 0 | 1 | Cochise, Cleon, Cowboy, Swan, Ajax, Vermin | party/Riffs scene | HYPOTHESIS |
| 13 | 9 | All-City (Trainyard) | 0/0 | 1 | 0 | 0 | Fox, Snow, Rembrandt, Cleon | Moonrunners, arresters | HYPOTHESIS |
| 14 | 51 | Desperate Dudes (Gunhill) | 2/2 | 20 | 5 | 10 | Ajax, Vermin, Cochise, Rembrandt, Cowboy, Fox | Turnbull ACs (vehicle chase) | HYPOTHESIS |
| 15 | 52 | No Permits, No Parley (Tremont) | 0/0 | 1 | 0 | 0 | Ajax, Vermin, Cochise, Rembrandt, Cowboy, Fox | Orphans, cops | HYPOTHESIS |
| 16 | 54 | Home Run (Riverside) | 0/0 | 6 | 0 | 0 | Ajax, Cowboy | Baseball Furies | HYPOTHESIS |
| 17 | 55 | Friendly Faces (Bowery) | 0/0 | 11 | 0 | 1 | Mercy, Cochise, Vermin, Rembrandt, Swan, Snow | Punks, Lizzies, Riffs scenes | HYPOTHESIS (CamSetSecondary used 7x) |
| 18 | 84 | Come Out To Play (Coney) | 1/4 | 18 | 1 | 4 | Cochise, Vermin, Mercy, Cowboy, Rembrandt, Swan | Rogues (finale) | HYPOTHESIS |

For every row the following are still open (resolution in Stage 2 M6 unless noted):
- the character each player controls, and each companion's role and evidence (replace vs preserve-and-add, §4.4);
- scripting that assumes a particular character or player count (the counts above are where to look; each
  `HuIsAPlayer(player2)` branch and both-in-box check needs a 3/4-player meaning);
- planned strategy for players 3 and 4 (default per §4.4: replace a companion without mission-critical duties
  using the same `MakePlayer` mechanism the game uses for player 2; otherwise preserve the NPC and add a player-2
  template character);
- fallback: **none proposed**;
- test status: **NOT YET TESTED** (all missions).

## Companion analysis method (planned)
For each mission, list every Warriors human the scripts create or reference, then classify by evidence:
mission-critical if the script gives it objectives, unique dialogue (`HuSpeak` with mission voice lines), escort
goals, scene roles (`SuperRunScene` Humans lists), or game-over conditions (death callbacks). Otherwise "replaceable".
`player2` is already a companion that the second human takes over (F-0024); the same mechanism is the default for
players 3 and 4 (F-0062 showed the engine binding a companion to a new pad).

## M2 note (2026-10-11): Mission 13 is the four-player test mission
Mission 13 (level9, All-City) was used for every M2 four-player test (SINGLE-PC, bots): four players via the game's own
Start-join (Fox taken over, player 4 spawned as Swan with his own model, F-0154), combat for players 3-4, items
(pick-up, Flash, revive, checkpoint copy), game over, level restart and checkpoint reload, 33-minute 4-instance lockstep
(F-0160). This is **not** a final mission status: per-mission work and statuses are M6.

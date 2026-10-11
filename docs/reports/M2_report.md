# M2 report — four genuine players (2026-10-11)

**Result: all 7 M2 exit criteria have test evidence on SINGLE-PC** (`docs/plan/M2.md`), with one caveat on criterion 6
(30 fps mode dips below 29 in one heavy Mission 1 scene). Everything here is one PC, scripted or random bot input,
Mission 13 ("level9") as the test mission. It does **not** prove: two or more real PCs (E6 still waits for your second
PC), internet play, human play with 4 people, or any mission other than Mission 13 (that is M6).

Environment: Ryzen 9 9950X3D, RTX 5090, Windows 11; our PCSX2 build w4p-m3-7 (v2.9.115 + W4P patches 0001-0013);
MTVU **off**; native resolution in the test sandboxes; four instances on loopback UDP for lockstep tests, one instance
with the other three players simulated (W4P LocalBot) for feature tests. Evidence: `evidence/M2/*.json`, logs and
screenshots in `local/m2/<tag>/` (not committed), findings F-0108 to F-0161 in `docs/FINDINGS.md`.

## Completed work (commits)
| Item | Where |
|---|---|
| Engine extension for 4 players: GameMgr per-player records, pads 0-7, cameras/views/ScreenEffects tables relocated, HUD for players 3-4 (B1/B2), radar per view, own health panel per view | `mod/m2/*.txt`, commits ab63e13 … 4327c5f, a24249b, 73398d8 |
| Players 3-4 join through the game's own Start-join (take over a companion, or a spawned Warrior when none is free) | `mod/m2/spawn*.txt`, eaa3081, 2f8e0f7 |
| Only player 1 commands the gang (D13) | caae24e, 755826b |
| Combat, Flash, items, checkpoint copy for players 3-4 (`[4p inventory]`) | 7c78b6b, 73398d8 |
| Game-over fade on all four views (`[4p fx]`) | 7c78b6b |
| Deterministic MTVU attempt (fork 0011/0013) - **failed**, MTVU stays off | bdb2c52, F-0150 |
| **This session:** downed player keeps own view (2 words), level-end crash fix R8 (18 words), player 4 gets his own Warrior model and name (your option A, 404 lines), test tools (probes, savestate start, random bots, rotating screenshots) | 64a235c and the report commit |

## Test results (exit criteria)
| # | Criterion | Evidence | Verdict |
|---|---|---|---|
| 1 | Four players exist | count 4, four valid handles in every 4-player run, e.g. q15 at the end on all four instances (F-0111, F-0128, F-0160) | **PASS** |
| 2 | Independent input | one player moves at a time, the others stay put (F-0112) | **PASS** |
| 3 | Same systems as players 1-2 | players 3 and 4: take damage, knocked down and get up, targeted by enemies, land hits, grab (F-0139, F-0142, F-0144); Flash heal (F-0141); world pick-up (F-0156); partner revive (F-0157) | **PASS** |
| 4 | Four views + own HUD per view | own view, radar and name panel per quarter (F-0130, F-0137); a downed player keeps his view (F-0151); GAME OVER text in all four quarters (F-0152) | **PASS** |
| 5 | 4 instances, ≥ 30 min, 0 mismatches, no crash/softlock | **q15**: 2007 s, 1,876 hash points, **0 mismatches, 0 crashes**, survived a GAME OVER and a level restart, final patch set (F-0160). Earlier q14 (0 mismatches) **crashed** at a level end - fixed by R8 (F-0153) | **PASS** (q15) |
| 6 | ≥ 29 fps in 30 fps mode; 60 fps measured | 30 fps mode, Mission 13, 4 views: median 29.37-29.97, lowest window 29.17 (F-0146, F-0161). **Caveat:** heavy Mission 1 4-view scene median 29.07-29.37 but lowest windows 27.4-28.7 (F-0146/F-0147). **60 fps mode with 4 views: median 59.84, lowest 59.14** (F-0161) | **PASS** for Mission 13 / caveat for the heavy scene |
| 7 | Originals unchanged | 20 files (ISO, all four BIOS sets, original pcsx2-qt.exe), 0 changed (`evidence/hashes/inputs_2026-10-11_m2b.json`) | **PASS** |

## New verified findings this session (F-0150 to F-0161)
- **MTVU is not safe for online play (F-0150).** With "multi-threaded VU" on, one of four emulators went out of step
  in the start-up menus, even with our deterministic version. MTVU stays off for good (the package has it off).
- **A downed player kept losing his screen (F-0151).** Example: player 1 goes down -> the game removes his view ->
  with 4 players every PC then showed the *wrong* player. Fixed: everyone keeps their own view (also in 2-player).
- **Every level end crashed with 4 players (F-0153)** - restart after GAME OVER, "Last checkpoint", mission complete.
  Cause: one HUD function still used the old 2-player table. Fixed (R8); q15 then ran 33 min including a restart.
- **Player 4 is now a real Warrior (F-0154, your option A).** In Mission 13 he joins as **SWAN** - Swan's own body
  and name - instead of a second Rembrandt. The game loads Swan's model when player 3 joins (about 370 KB, it fits:
  0.9 MB stayed free), so player 4 can join at once. Same result in the 4-PC sync test (F-0160).
- **Items for players 3-4:** pick-ups work (F-0156); checkpoint save/restore of their items works, also after a level
  reload (F-0155); partner revive works (F-0157) - see question Q1 below about teammates blocking it.
- **60 fps with four views holds (F-0161):** about 59.8 frames per second on your PC.

## Failed tests and open questions (reported as prominently as the passes)
- **Money bank at mission end (T7): inconclusive (F-0158).** Through the shortcut we can trigger, the bank got 70
  instead of 100. Most likely that shortcut empties players 1-2's pockets before banking, so it is not the real
  end-of-mission path. The real path (mission summary screen) is still to be tested.
- **Players 3-4's pockets are not emptied when they leave at a level end (F-0158)** - could let money/items carry over.
  Open, to check in M6.
- **Players 3-4 start every level with no items** (only players 1-2 get the level's starting items). Open (script work).
- In one test the GAME OVER menu ignored player 1's Cross presses (go5); in other runs random Cross presses did
  restart. Cause unknown (F-0155).
- 60 fps: whether every game timer runs at the right speed at 60 fps is still not audited (R-22).
- Cross-PC sync (E6), human play with 4 people, other missions: not tested.

## Changes to the mission status table
No final status changes (that is M6). Mission 13 (level9) is the 4-player test mission: four players, combat, items,
game over and level restart tested on SINGLE-PC with bots. Noted in `docs/MISSIONS.md`.

## Risks and blockers
- No blockers. Main risks: other missions have different companions and scripts (M6); the extra-model trick needs the
  model memory to fit in each level (it falls back to a copy of player 1 if not); 30 fps dips in heavy 4-view scenes.
- Recommendation for the dips (to test, no decision needed): run 4-player sessions with the emulated CPU at 180 %
  also in 30 fps mode - the 60 fps test shows the emulated console has enough room at that speed.

## Deviations from the approved plan
- MTVU off permanently (plan assumed your settings with MTVU on).
- Player 4's character: your decision D14 (load an extra Warrior model).
- 60 fps measured from a saved game state instead of a scripted boot (the boot script does not work at 180 % CPU speed).

## Questions for you (short answers like "Q1 A, Q2 A" are enough)
**Q1. Revive blocked by a teammate.** The game only allows a revive if nothing stands between the two players - in the
original 2-player game that was rarely a problem. With four players bunched together it happens more: example, player 2
stands between player 4 and downed player 3 -> player 4's revive button does nothing until he steps around.
- (A) Keep the original rule (recommended: it is the game's own behaviour; just step aside).
- (B) Let teammates not block the revive (small patch, slightly changes the original rule).

**Q2. Widescreen on by default (D11)** - still waiting for your OK.
- (A) Yes, widescreen (16:9) on by default (recommended).
- (B) No, keep 4:3 by default (players can still switch it on).

## Next steps
1. Session policies from your brief: pause by any player ("Paused by Player 3"), cutscene skip vote ("2/4 want to
   skip"), disconnect freeze with a 60-second countdown, host leaving.
2. Connection layer for real networks (D5), then a 4-player test package and lobby.
3. M6: enable and test all story missions one by one (companions, scripts, starting items for players 3-4).
4. Open items above (money bank via the real summary screen, pocket clearing, GAME OVER menu input).

## Tests you can do
- **E6 (2-PC test) is still the most important one**, with `dist/warriors-4p-test.zip` (2 players) and the steps in
  its README. Please send back: the `logs` folder from both PCs, each PC's CPU and GPU, and how controls and 60 fps
  felt. Note: that package does not contain today's fixes - on purpose, so your test result stays comparable.

## Originals
ISO and BIOS hashes re-checked on 2026-10-11 evening: 20 files compared, 0 changed
(`evidence/hashes/inputs_2026-10-11_m2b.json`, `docs/HASHES.md`).

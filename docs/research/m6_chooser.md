# M6 chooser: which Warrior an added player 3/4 becomes (XC table, X9 A, two model pins X10 A, X7 b) (2026-10-12)

Build: The Warriors SLUS-21215 v1.03 (`local/disc/SLUS_212.15`, read-only), fork builds w4p-m5-1 and w4p-m6-1
(the coordinator rebuilt the fork during this work, section 5; `emulator/` not touched here). Builds on
`m2_spawn_name.md` (CHOOSE), `m2_extra_model.md` (pin, GATE/ENSURE/RELEASE, data words 0x000E1C00-0x000E1C4B), `m6_missions.md` sections 1-3 and X9/X10, `m6_fixes.md` (X1-X8; section 6 findings 2-4).
Function and structure names are OUR labels (the ELF is stripped); addresses are static unless marked. Labels:
VERIFIED (with pointer), HYPOTHESIS, FAILED TEST. **All runtime tests: SINGLE-PC, one instance, scripted bot input, no
impairment**, groups as in `m6_fixes.md` (`warriors-4p own view;...;warriors-4p session;warriors-4p session call;
warriors-4p missions`), MTVU off, patch `local/m6/ch1.pnach` (generated with `python -I mod/make_pnach.py`;
**`mod/w4p_m1.pnach` was NOT regenerated** because the smoke batch on instances 6-9 reads it). Decisions applied as the
coordinator's defaults: X9 A, X10 A, X7 (b); the user may still change X9/X10 (data words, section 2.5).

**Follow-up (2026-10-12, later the same day; sources committed by the coordinator as 336c6a4 before it):** (1) option (b)
of finding 3 (re-pin a stalled pin after 8 s, KICK) implemented and tested: **it did not help** (chs_m12k), so it is
off by default; the cause was diagnosed (chs_m12d: the loaded parts are evicted before anything references them) and
fixed with a per-frame pin service PINSVC/PINFIX (section 2.6): **M12 now gives players 3 and 4 their own models**
(chs_m12s); (2) Ajax rows added for M17, M18 and the post-game hub (X9 A, script evidence in 2.1); the Fox rows stay
HYPOTHESIS; (3) M17's crash at the third join (finding 4) was fixed by the coordinator (F-0184, FXCAM in
`mod/m2/fx34.txt`). Only `mod/m2/spawn.txt` changed in the follow-up (`missions.txt` belongs to another agent now).
Follow-up runs use `local/m6/ch2.pnach` (KICK) and `local/m6/ch3.pnach` (KICK off + PINSVC), both generated from
the committed sources (HEAD 336c6a4/c287aac) with only `spawn.txt` replaced.

**Follow-up 2 (F-0195, players 3-4 standing on the same spot):** SPAWN put every added Warrior at player 1's position
+ 1.5 units in x, so two Warriors spawned close together overlapped exactly. Now SPAWN creates him 4 units beside player 1
and a new routine PLACE moves him with the game's own HuTeleportNearHuman core to a free spot 3.6 units from player 1
(fallback: player 1 +/- 1.5 units, per player index). VERIFIED in M13 and M12 (section 2.7, runs chs_pl13/chs_pl12).
A taken-over companion keeps his own position (MakePlayer has no teleport). Test pnach `local/m6/ch4.pnach` (HEAD
2124ac8 + this `spawn.txt`): **4257 addresses, 6 problems** (the known 6).

## Summary
| # | Problem | Change | Where | Result |
|---|---|---|---|---|
| 1 | M13: after the script deleted Fox (player 3), the re-join spawned player 3 **as Fox**, whom ch2 re-creates (m6_fixes.md finding 3) | **XC table**: per level and checkpoint range, the Warriors that the level's scripts create later, delete and re-create, or use as scripted actors; CHOOSE gives them status 6 and never picks or pins them (25 rows, from m6_missions.md section 3 + script greps) | `[4p spawn]`: CHOOSE 0x000E1400 (+5 words), XCHK 0x000E1FA8, table 0x000E1E10 | **VERIFIED** (chs_m13fox: Fox status 6 at the re-join, player 3 became Ajax); the 25 rows also checked by simulation |
| 2 | X9 A: never a Warrior the story has removed | XC rows: Cleon in levels 51, 52, 54, 55, 84 (M14-M18) and the post-game hub (level 95 cp >= 11); Fox from M16 (HYPOTHESIS, 2.1); **Ajax in M17, M18 and the post-game hub (follow-up, VERIFIED script, 2.1)** | same table | **VERIFIED** for M15 (chs_m15b: Cleon status 6, no pin; the old order would pin Cleon); other levels, the Ajax rows (follow-up) and the Fox rows by simulation only |
| 3 | Only one pin (PIN_ID): a second spawn moved the pin from Swan (still player 4) to Fox (m6_fixes.md finding 4) | **Two pin slots**; a pin is released only when no W4P-added Warrior of that name plays any more (USED), on his leave/delete (UNPIN), after the last join if unused (SWEEP), on timeout/no-fit, at teardown. **X10 A**: the 3rd player also waits for his own model (OWN3 = 1); no second model -> clone as before | `[4p spawn]` block 0x000E1600-0x000E1AB8, PX/LV at their old addresses, helpers 0x000E1E80-0x000E2173, slot 1 at 0x000E1C50 | **VERIFIED** in M13 (chs_m13fox: Swan's pin and model kept 5.4 min while Ajax got slot 1; chs_reg, chs_m13s: P3 Swan + P4 Ajax with own models). First version **FAILED TEST in M12** (chs_m12, chs_m12b: player 3's first pin never got an instance before the GATE timeout -> clone, finding 3); **follow-up VERIFIED in M12 with PINSVC** (chs_m12s: P3 Swan, P4 Ajax with own models, 1 refused press, no timeout; 2.6) |
| 4 | X7 (b): a script-forced leave (X1/X3) emptied the player's inventory slot and he did not get his starting items back | **LVOWE**: the forced leave marks the slot's X7 byte "owed" (2) if he had them; X7J gives them again at his next join at any checkpoint; normal leaves keep "given" (1): no second gift | `[missions]`: REL34 and X3W call LVOWE 0x000E7790; X7J 0x000E7640 rewritten | **VERIFIED** (chs_m13fox: spray 6 -> 0 at the forced leave, 6 again at the re-join; no second gift for the other player) |
| - | Regression: M13, 4 players, random bots | all groups | - | **VERIFIED** (chs_reg and, with PINSVC, chs_m13s; build w4p-m6-1: 4 players / 4 views, 0 TLB misses, 302-303 s of random play). Separately: M17 cp1 crashed at the 3rd join with any chooser (finding 4; fixed by the coordinator, F-0184) |

Follow-up test pnach `local/m6/ch3.pnach`: **3476 addresses, 6 problems** (the known 6). First version:
`python -I tools/note_patches.py check local/m6/ch1.pnach`: **3340 addresses, 6 problems** = exactly the 6 known
`[4p hud A]` vs `[4p hud B1]` alternatives (`local/m6/dev2.pnach` of m6_fixes.md: 3122 addresses, 6 problems). The five
changed or depended-on sources alone (`missions.txt spawn.txt spawn_leave.txt inventory.txt session.txt`): **1356
addresses, 0 problems**. 742 code words in the changed ranges disassembled, compared with their comments and
re-assembled: 0 mismatches (section 3).

## 1. Where the code is
| Address | Source / group | Content |
|---|---|---|
| 0x000E1400-0x000E1570 | `spawn.txt` `[4p spawn]` | CHOOSE (was -0x000E155C): + `lh a0,2(s3)`, `jal XCHK`, `bne v0,zero,reject` with status 6 at the top of the candidate loop; everything else unchanged |
| 0x000E15C0-0x000E15E0 | `[4p spawn]` (patch=0) | CHOOSE statuses: new value 6 = excluded here (XC) |
| 0x000E1600-0x000E1AB8 | `[4p spawn]` | CLRPIN 0x000E1600 (both slots), INLIST 0x000E161C, PRESENT 0x000E1648, RELEASE(slot) 0x000E16A0, POKE 0x000E1708, FITCHK 0x000E1770, ENSURE 0x000E1804 (old block 0x000E1600-0x000E1BEF rewritten) |
| 0x000E1B38-0x000E1BA8 | `[4p spawn]` | PX at its old address (4th player took a companion -> SWEEP instead of RELEASE); X2 hook word 0x000E1B44 unchanged |
| 0x000E1BAC-0x000E1BD4 | `[4p spawn]` | LV at its old address (callers 0x000E1274 LEAVEHOOK, 0x000E71E4 session LEAVE unchanged): DESPAWN, then UNPIN(char id) |
| 0x000E1C00-0x000E1C5C | `[4p spawn]` (patch=0) | slot 0 (ID, OWN, MI, T0) at 0x000E1C00 (= the old PIN_ID/PIN_OWN/PIN_MI/PIN_T0), codes/counters 0x000E1C10-0x000E1C38 as before, **EN_SLOT 0x000E1C3C**, config 0x000E1C40-0x000E1C48 as before, **OWN3 0x000E1C4C** (X10, 1), **slot 1 at 0x000E1C50** |
| 0x000E1E10-0x000E1E74 | `[4p spawn]` (patch=0) | XC table (25 rows + end) |
| 0x000E1E80-0x000E2230 | `[4p spawn]` | SLOTP 0x000E1E80, USED 0x000E1E9C, UNPIN 0x000E1EE8, SWEEP 0x000E1F4C, XCHK 0x000E1FA8, GATE 0x000E2028, JS 0x000E2108 (was 0x000E20E8 before the follow-up), KICK 0x000E2194 (2.6) |
| 0x000E2300-0x000E2310 | `[4p spawn]` (patch=0) | follow-up 2.6: KICK_MS (0 = off), KICK_T, N_KICK, SVC_T, N_FIX |
| 0x000E2320-0x000E2438 | `[4p spawn]` | follow-up 2.6: PINSVC 0x000E2320, PINFIX 0x000E2374 |
| 0x0023D6BC | `[4p spawn]` | follow-up 2.6: the human update's model request call -> `jal 0x000E2320` PINSVC (was 0C06290C `jal 0x0018A430`) |
| 0x000E10CC | `[4p spawn]` | follow-up 2.7: SPAWN's x offset `lui at, 0x4080` (4.0 units; pnach had 3C013FC0 = 1.5) |
| 0x000E2314-0x000E2318 | `[4p spawn]` (patch=0) | follow-up 2.7: N_PLACE, N_PLACE_FB |
| 0x000E2440-0x000E257C | `[4p spawn]` | follow-up 2.7: PLACE 0x000E2440, PLPOS 0x000E2560; JS calls PLACE after a successful spawn (JS still at 0x000E2108, KICK now 0x000E219C) |
| 0x000E103C | `[4p spawn]` | SPAWNPICK's spawn call -> `jal 0x000E2108` JS (pnach had `jal 0x000E1A9C`; first version `jal 0x000E20E8`) |
| 0x001898C8 | `[4p spawn]` | streamer pin fit test -> `jal 0x000E1770` FITCHK (was 0C05DD76 `jal 0x001775D8`; pnach had `jal 0x000E1758`) |
| 0x00188AEC, 0x00189734 | `[4p spawn]` | unchanged (`jal 0x000E1600` CLRPIN) |
| 0x000E7400-0x000E7454 | `missions.txt` `[missions]` | REL34 (was -0x000E7470): W4P-added Warrior -> UNPIN(char id) instead of "release if PIN_ID"; LEAVE through LVOWE |
| 0x000E75EC | `[missions]` | X3W's `jal 0x000E7100` (LEAVE) -> `jal 0x000E7790` LVOWE (delay slot `addiu a0,a0,-1` kept) |
| 0x000E7640-0x000E7730 | `[missions]` | X7J (was -0x000E7724): given byte 2 = owed -> give at any checkpoint |
| 0x000E7790-0x000E7810 | `[missions]` | LVOWE(index) |

New low RAM: 0x000E1C3C, 0x000E1C4C-0x000E1C5F, 0x000E1E10-0x000E2233 (follow-up: up to 0x000E2237), 0x000E2300-0x000E243F (follow-up), 0x000E7728-0x000E7733 (X7J grew by 3 words),
0x000E7790-0x000E7813. Grepped free before use in `mod/w4p_m1.pnach`, `local/m6/dev2.pnach`, `mod/m2/*`, `tests/`, `tools/`,
`emulator/patches/`, `net/` (only the X2 table 0x000E1E00-0x000E1E0F was near). Freed: 0x000E1ABC-0x000E1B37 and
0x000E1BD8-0x000E1BFF (old ENSURE/GATE/JS tail and LV tail; not referenced). `docs/STATE.md`'s RAM map is not edited here
(coordinator): spawn/chooser now 0x000E1000-0x000E1C5F, 0x000E1C60-0x000E2237 and 0x000E2300-0x000E243F, missions 0x000E7400-0x000E7813.
Callers outside `spawn.txt`/`missions.txt` are unchanged: `spawn_leave.txt` 0x000E1274 `jal 0x000E1BAC` (LV) and
`session.txt` 0x000E71E4 `jal 0x000E1BAC` (LV). `tests/m2/m6fix_probe.py` still reads PIN_ID = slot 0 ID (0x000E1C00).

## 2. Design

### 2.1 XC table (problem 1 and X9 A)
- **Rule.** CHOOSE (and through its statuses ENSURE's "which model to load" loop) skips a candidate whose HUD name index
  (`FUN_00229570` index: Swan 0, Cochise 1, Cowboy 2, Ajax 3, Rembrandt 4, Fox 5, Vermin 6, Snow 7, Cleon 8;
  m2_spawn_name.md 1.2) is set in the mask of any row whose level equals the current level number and whose checkpoint
  range contains GameMgr+0x33A (the checkpoint X2 and X7 also read). Status 6 = excluded. A Warrior who is **in** the level
  is already refused by CHOOSE's presence test (status 4, any variant id through the name index), so a row is only needed
  for a Warrior who is **absent when players 3-4 join and appears later in the same level load**: created by a later
  chapter in continuous play (chapters chain in-level), deleted and re-created, or a scripted actor created mid-chapter.
  Spawned W4P Warriors survive in-level checkpoint changes, so a row covers "this checkpoint and every earlier one".
- **Rows** (byte level, byte first cp << 4 | last cp, u16 mask). Script pointers as `WAD:line` of `local/analysis/pseudo/`
  (VERIFIED as script text; the creation call sites were grepped for this note unless they come from m6_missions.md):

| Level (mission) | Checkpoints | Excluded | Why (script) |
|---|---|---|---|
| 99 (M1) | all | Vermin, Cleon | teachers: `AddCombatTeacher` (Vermin 27, Cleon 2) 09653:127, `RemoveGang` 09653:1273; `AddTeacher` (Vermin 26) 09654:84, 09655:65; `AddSCleon` (Cleon 2) 09654:85, `RemoveGang` 09654:106 |
| 80 (M2) | <= 1 | Ajax | `AddAjax()` 08774:97 (own type-0 gang 08730:115-117), recruited 08774:270 |
| 80 (M2) | <= 2 | Snow, Cowboy | `AddSnowCowboy()` 08775:35, recruited 08775:147-148 |
| 80 (M2) | <= 3 | Fox | `AddFox()` 08776:80, recruited 08776:511 |
| 80 (M2) | <= 4 | Swan, Cochise | `AddCochiseSwan()` 08777:31, recruited 08777:243-244 |
| 87 (M3) | <= 5 | Ajax | `HuDelete(ajax)` 09225:154, re-created for the last scenes (09171:2355-2357 via 09225:768) |
| 3 (M6) | <= 2 | Snow | first created by `AddWarriors03` at the cp2 -> cp3 swap (08021:200-221) |
| 5 (M7) | <= 4 | Rembrandt, Snow | `HuDelete` 08482:150-151, re-created in cp4 Setup 08484:68-73 |
| 86 (M9) | <= 1 | Snow | intro gang Scene1Warriors (deleted 09163:157-158), then `C1.SnowAdd` 09163:607 |
| 93 (M10) | <= 4 | Swan, Cochise, Cowboy, Fox | `AddClubhouseWarriors()` 09377:156 (cp3), 09378:35 (cp4) |
| 93 (M10) | <= 5 | Swan, Cochise, Cowboy, Rembrandt | `AddLCWarriors()` 09379:78, removed 09379:106 (also `AddIntroWarriors` 09375:204/216) |
| 31 (M11) | <= 4 | Fox, Snow | RDSceneWarriors at P4 start 07917:88-93 |
| 31 (M11) | <= 5 | Ajax | DevilWarriors 07915:98-108 |
| 9 (M13) | <= 2 | Fox | `HuDelete(fox)` 09720:157; `AddFoxMid` 09721:40-42, `AddFox` 09721:247-270, into the squad 09721:293 |
| 51 (M14) | <= 2 | Ajax | pit fight `StartToRun` (08181 main_5), `AjaxAddToWarriors` 08182:107 |
| 51 (M14) | <= 4 | Vermin | rescue gang WarrSplit01 (08184 RunVermin), `VerminAddToWarriors` 08184:551 |
| 51 (M14) | <= 5 | Cochise, Cowboy, Fox, Rembrandt | WarrSplit, `GladToSeeYa` 08185:721 |
| 51, 52, 54, 55, 84 (M14-M18) | all | Cleon | **X9 A** (below) |
| 54 (M16) | <= 4 | Swan, Cowboy, Ajax, Snow | AltWar gangs per chapter (08262:1124-1126, 1401-1403, 1269-1271); `AjaxFacesUp` deletes GangWarriors (Swan) 08352:187-213; `AddFinalWarriors`/`AddAjaxFinal` 08353:31-56 |
| 54, 55, 84 (M16-M18) | all | Fox | **X9 A, HYPOTHESIS** (below) |
| 55, 84 (M17-M18) | all | Ajax | **X9 A (follow-up), VERIFIED script**: removed at the end of M16 (below) |
| 55 (M17) | <= 2 | Swan, Cowboy, Snow | `AddWarriors04` + `HuChangePlayerGang` at the cp2 -> cp3 swap 08404:81-83 (08357:1045-1051) |
| 95 (hub) | 11-15 | Cleon, Fox, Ajax | post-game hub (`runNextMission` 84 -> 95 cp11, 04106:1763); X9 A, HYPOTHESIS for the hub |

  No row for M4 (34), M5 (2), M8 (81), M12 (14): their scripts create no Warrior later that could be absent at a join
  (M4/M5/M12 squads are created once per level load; M8's later Cleon/Swan chase variants replace humans that are present,
  and its brawl-end deletes are not followed by a re-creation) - VERIFIED script text (m6_missions.md section 3; M12:
  `HuCreate` of Warriors only Cochise/Cowboy, 07655:1163-1202).
- **X9 A, story deaths.** Cleon: the hub interlude before M14 still shows him (`CleonWarriors[1]` in scene l51_c11,
  09501:40-44); **no M14-M18 script creates a Cleon** (grep of 08031, 08181-08187, 08191, 08255-08258, 08262, 08349-08355,
  08357, 08400-08404, 09030, 09110-09113: only the HUD bar label `LEVEL54.CLEON` 08262:1883 / 08350:136). That he is killed
  at the conclave between M13 and M14 is the game's story (HYPOTHESIS as far as this project's evidence goes: the conclave
  is not in a script). Fox: M16's opening subway scene l54_c1 has Fox with two cops, a baton and subway train objects in its
  cast (08355:131-133), his gang is removed right after (08355:139-140), and no later script (M16 08262/0834x-0835x, M17,
  M18) creates a Fox (grep: 1 reference, the scene cast). HYPOTHESIS that this scene is his death; the row only removes Fox
  from the choice there (cost: one candidate fewer). No more direct script evidence for Fox was found (string tables: only
  flashback/menu texts), so the Fox rows stay HYPOTHESIS. **Ajax (follow-up, the user's X9 A = no Warriors the story has
  removed):** M16's last scenes are `l54_c3_b` with the cast `player` (Swan), Cowboy, Ajax, Snow, `LCop.lcop` (char 260,
  08262:1214), two cops (chars 253/257) and the objects baton, car, `Cuff1`, `Cuff2` and a whistle spawned at Ajax's position (08350:181-185,
  `AddLCop`/`AddC3ACops` 08350:163-164), then `l54_c3_c` (`Final` = 1, mission end) with the cops and Ajax (08350:199-202);
  **no M17 or M18 script creates Ajax** (grep: 0 references in 08357, 08400-08404, 09030, 09110-09113). VERIFIED script:
  Ajax is removed at the end of M16 (handcuffed in the final scene - the scene content itself is HYPOTHESIS, the cast and
  objects are script text). Rows: level55 and level84 all checkpoints, hub cp >= 11 (masks 0x128 = Ajax, Fox, Cleon).
  In level54 itself Ajax stays allowed after cp4 (he is in the squad until the final scene, so CHOOSE's presence test
  refuses him anyway).
- **Not covered:** flashback missions (levels 82, 92, 83, 20, 11) and rumbles - story-earlier or not story; no rows.
  Levels 60-64: ENSURE/CHOOSE behave as before (+0x114 model field).

### 2.2 Two model pins (problem 3, X10 A)
- **Data.** Slot k at 0x000E1C00 + 0x50*k (k = 0, 1): ID, OWN, MI, T0 (slot 0 = the old PIN_ID, PIN_OWN, PIN_MI, PIN_T0).
  EN_SLOT 0x000E1C3C = the slot ENSURE last targeted (GATE waits on its T0). OWN3 0x000E1C4C (X10): 1 = the 3rd player
  also goes through GATE.
- **USED(id)** (leaf): a live human (object table slots 0..59) with +0xD0 == id and +0x1B1 == 7 (W4P-added). "In play"
  therefore means a W4P-added Warrior of that char id exists; a level human of the same Warrior does not need our pin.
- **ENSURE** (as m2_extra_model.md 4.3, changes in bold): skip checks as before; **for both slots** forget a pin that left
  the game's pin list; CHOOSE (now with XC); target = CHOOSE's pick (resident) or the first status-3 absent candidate
  (status 3 can no longer be an excluded Warrior); NOFIT check; **target already in a slot -> that slot (code 3); else a
  free slot; else a slot whose Warrior is not USED (RELEASE it); else code 5** (both pins in use; result 1 if resident,
  else 2 = clone); pin into that slot (OWN only if not pinned before by the level), T0; **EN_SLOT = slot**; POKE when not
  resident; if FITCHK unpinned it meanwhile -> code 7, result 2. It never releases a pin that a W4P player uses.
- **GATE**: as before, but the timeout uses T0 of slot EN_SLOT and releases that slot only.
- **JS** (SPAWNPICK's spawn call, real Start press, nobody to take over, count 2 or 3 at entry): **count 3, or count 2 with
  OWN3 = 1 -> GATE** (refused press returns 0 = nobody to join); SPAWN (CHOOSE inside); **if spawned -> SWEEP**; count 2
  and PRELOAD_AT3 -> ENSURE (preload for the 4th player, which now goes into the other slot).
- **PX** (picker found a companion): count 2 -> ENSURE (preload); count 3 -> **SWEEP** (was RELEASE).
- **LV** (leave of a W4P-added Warrior, LEAVEHOOK and session LEAVE): DESPAWN, then **UNPIN(char id)**.
- **UNPIN(id)**: if not USED(id), RELEASE every slot holding id. **SWEEP**: RELEASE every slot whose Warrior is not USED.
- **REL34** (X1, before a script deletes player 3/4): marker cleared as before, then **UNPIN(char id)** (the human still
  exists but without marker, so USED is false unless another W4P Warrior of that name plays).
- **FITCHK**: the failing entry is compared with both slots; the matching slot is released and NOFIT set (the other slot
  is kept). **CLRPIN**: both slots, OWN words and NOFIT cleared, then the game's clear-all.
- **Memory.** Two extra Warrior models (Swan 374,767 + Ajax 296,991 bytes by the static table of m2_extra_model.md 3.1)
  can be pinned at once. A model that does not fit is caught by FITCHK -> NOFIT -> that player gets the clone (old
  behaviour); the other pin stays.
- **Order of targets** is still the candidate table 0x000E1580 (Swan, Ajax, Snow, Cochise, Vermin, Fox, Rembrandt, Cleon,
  Cowboy). With X10 A and no free companion the 3rd player normally becomes Swan and the 4th Ajax.

### 2.3 X7 (b): starting items after a forced leave
- **LVOWE(index)** replaces the LEAVE call of REL34 (X1 HuDelete/GangDelete paths) and of X3W (HuChangePlayerGang): reads the
  player's HUD slot (+0x380) before the release, calls LEAVE(index) and, if LEAVE returned 1 and the slot is 2/3 with X7
  byte 1 ("given in this level load"), sets the byte to 2 ("owed"). Returns LEAVE's v0 (X3W's loop tests it).
- **X7J**: byte 2 -> give the level's MS values at any checkpoint and set 1; byte 0 -> give only at checkpoint 0/1 (as
  before) and set 1; byte 1 -> nothing (no second gift on a normal re-join). X7R still clears all bytes at every level
  load. The forced release empties the slot first (ReleasePlayer -> InvReleaseSlot, m6_fixes.md finding 2), so the re-gift
  restores, it does not double (InvGiveRevive adds Flash to 0; spray and money are set).
- The re-joining player takes the lowest free HUD slot; after X1 that is the slot the forced leaver had (m6x1b: pad 2 back
  to the freed index); VERIFIED in test chs_m13fox (section 5) for one case.

### 2.4 Lockstep
All decisions read game RAM on the game thread inside synchronised code (UpdateJoin on a synchronised Start, the
streamer, Lua deletes, ResetLevel). The new words (0x000E1C3C-0x000E1C5F, 0x000E1E10-0x000E1E74) lie in the hashed range
(from 0x000A0000, F-0125). HYPOTHESIS: deterministic as the rest; not run on 4 instances here.

### 2.5 What the user can change without code (patch=0 data; PINE can change them for tests)
- X10: OWN3 0x000E1C4C = 0 -> the 3rd player gets the clone at once (old behaviour); the 4th player still waits.
- X9 / problem 1: XC rows 0x000E1E10.. (delete a row = allow that Warrior there; e.g. the Fox rows if the user does not
  want the HYPOTHESIS rows, or add an Ajax row for M17/M18).
- Candidate order 0x000E1580 (patch=2 words in `spawn.txt`), TIMEOUT_MS, PRELOAD_AT3, POKE_EN as before.
- KICK_MS 0x000E2300 (follow-up 2.6): 0 = off (default); e.g. 8000 = re-pin a pin still loading after 8 s.

### 2.6 Stalled pins in busy levels (follow-up 2026-10-12: option (b) KICK, diagnosis, pin service PINSVC)
- **Problem (finding 3, M12):** player 3's first pin of Swan never got an instance before the GATE timeout.
- **Option (b), KICK (implemented, tested, default OFF):** `KICK` (0x000E2194), called from GATE's refuse path: when the
  waited-for pin is at least KICK_MS (0x000E2300) old and the last re-pin is at least KICK_MS ago, RELEASE that slot and
  ENSURE again (new pin + POKE), keeping the first T0 so the 20 s timeout still counts from the first pin; ENSURE result
  1/2 -> the press joins (GATE code 5). Data: KICK_T 0x000E2304, N_KICK 0x000E2308. **Result chs_m12k (KICK_MS = 8,000):
  the re-pin at 8 s did not help** (still not resident at the next presses; timeout at 20 s -> clone), so KICK_MS is 0 in
  the source; the code stays available as a config word.
- **Diagnosis (chs_m12d: KICK off, TIMEOUT 60 s, `extra_survey` every ~200 polls; VERIFIED runtime):** the load itself
  works - Swan's three parts were **resident with refcount 0 at poll 7500 and again at 8700**, but **evicted in between**
  (7700: animation and model gone; 7900: requested again, loads pending 3). The pin's instance (the reference that keeps
  the parts) is built only by the streamer `FUN_001897A8` when it services a pin whose model is resident (pin loop
  0x00189874-0x00189934); the scheduler `FUN_0040F8A0` does not call the streamer for pins alone (all request priorities
  at FLT_MAX in every sample, dict+0xBC4 = -1: H1 of m2_extra_model.md confirmed), and our POKE runs only at a Start press
  every ~5 s. In M12 (39-43 live humans, 9 level pins, largest free block 171-265 KB) the fit tests of other streaming
  evict unreferenced character parts (LRU, `FUN_00187D28`) before a press comes. In M13 the parts stay long enough. The
  "re-pin after the timeout works" observation of chs_m12/m12b came from the clone spawn and preload ENSURE happening
  while the parts happened to be resident (8700 in chs_m12d).
- **Fix, PINSVC/PINFIX (0x000E2320/0x000E2374, hook 0x0023D6BC):** the human update's per-human model request call
  `jal 0x0018A430` (FUN_0023D660, every human every frame; the call's result is not used, 0x0023D6C4 reloads v0) goes
  through PINSVC: the original call, then **once per game-clock value (= once per frame)** and only while slot 0 or 1 holds
  a pin, PINFIX: for each slot whose game pin-list entry has no instance and whose model is resident
  (`FUN_001774D0(dict, entry, 0, 0)`), build the instance with the streamer's own call `FUN_00177B80(dict, entry, 0)` and
  store it in the pin-list entry (as the streamer does, 0x00189E84 path). From then on the parts are referenced and cannot
  be evicted; the next press finds the Warrior resident. Data: SVC_T 0x000E230C, N_FIX 0x000E2310. Cost per frame: one
  clock compare; with a pin pending, two 32-entry list scans and up to two residency tests. Lockstep: game RAM only, on the
  game thread (human update), once per frame (HYPOTHESIS deterministic as the rest).
- **Release paths unchanged:** RELEASE's `FUN_0018AD40(dict, id, 1)` drops the instance PINFIX built (it clears every
  entry with that model index and releases its instance, m2_extra_model.md 1.2).

### 2.7 Each added Warrior on his own spot (follow-up 2, F-0195)
- **Where the position came from (VERIFIED code):** SPAWN (0x000E1080, `[4p spawn]`) reads player 1's position
  (human+0x10/+0x14/+0x18) and adds 1.5 units in x (`lui at, 0x3FC0` at 0x000E10CC, `add.s` 0x000E10D4) before the human
  create core `FUN_00233D60`; nothing moves him afterwards. Two Warriors spawned within a few seconds (players 3 and 4) got
  the same point: F-0195's 74.87 = 73.37 (player 1's x in M13) + 1.5.
- **Companion take-over (VERIFIED static):** MakePlayer `FUN_00229C40` calls no teleport (no `FUN_0023B138`, no vtable
  +0x6C position set in its call list); the joining player keeps the companion's own position. For players 3-4 the Lua
  join event is suppressed (`joinevent.txt`, index >= 2), so the levels' player-2 callbacks (which call
  `HuTeleportNearHuman(player2, player)`) do not move them either.
- **Placement helper (VERIFIED static, decompile `FUN_0023B138`, binding `HuTeleportNearHuman` 0x0035B480, arguments (mover,
  target)):** only if the mover is at least 3.6 units (squared 12.96) from the target, it tries 32 directions (step
  0.196 rad, start index from the game clock word timer+0x48) at 3.6 units around the target, shortens each by a ray test
  against the level (`FUN_0024F718`), rejects spots too close to walls or to other humans (`FUN_002274A8` neighbours), adjusts
  to the ground (`FUN_0040DB88`) and sets the position through the human's vtable (+0xAC / +0x6C, as the Lua `Teleport`
  core `FUN_00385BB8`). No free spot: no move.
- **Change:** SPAWN creates the Warrior 4.0 units beside player 1 (0x000E10CC `lui at, 0x4080`) so the helper's distance
  test passes; JS calls **PLACE(count)** right after a successful SPAWN: `FUN_0023B138(new handle, player 1's handle)`; if
  neither copy of his x (human+0x10 and the position table 0x00714B00 + 0x20 * human+0x92, which the helper itself reads)
  changed, the Lua Teleport core puts him at player 1's position + 1.5 (3rd player) or - 1.5 (4th player) units in x (the
  old offset, now per index). Counters N_PLACE 0x000E2314, N_PLACE_FB 0x000E2318. The 4.0-unit creation point is used only
  between creation and PLACE inside the same join call (no game update in between).
- **Lockstep:** game RAM only, inside UpdateJoin on a synchronised Start; the helper's start direction comes from the game
  clock (HYPOTHESIS deterministic as the rest).
- **Select ring of player 3 (F-0194 open item, described only):** the marker loop `FUN_0024B780` reads one byte per
  player index from `0x00622E10` (`(&DAT_00622e10)[index]`, 0x0024BA24 `addiu t0, t0, 0x2E10`; the only access to that
  address in the ELF by an address scan); for index 2 it reads 0x00622E12, which belongs to the next field, so player 3
  takes the "always marked" branch (sets his per-player time and calls `FUN_001B28A0(HUD, index, 0)`). The same loop also
  indexes 2-entry stack arrays (`uStack_110`/`uStack_108`, 12-byte stride) by view. A fix needs a 4-entry copy of the byte
  array (redirect the read at 0x0024BA24, and find who writes 0x00622E10/11 - no direct writer found by the address scan,
  so it is written through a base pointer, HYPOTHESIS the HUD manager 0x00600840 + 0x225D0) and a check of the stack arrays.
  Not trivial; not changed. Observation (not a claim): in chs_pl12 `t0359_p9364.png` rings are drawn under all four
  players while the random bots press Select.

## 3. Checks
- **Assembly round trip.** All new and rewritten code was written as assembly source and assembled with a scratch R5900
  assembler; an independent field decoder disassembled every word and the disassembly was re-assembled to the same word.
  The decoder/encoder pair was first checked on the game ELF: 720,238 decodable words in 0x00100000-0x003FFFFF re-encode
  to themselves (0 mismatches), and on the existing W4P sources (`missions.txt` 179, `spawn_leave.txt` 29, `session.txt`
  142 cave words: 0 mismatches; in `spawn.txt` only the FPU word `add.s` of SPAWN and the candidate data words are outside
  the subset). Follow-up 2: **945 code words, 0 mismatches** (adds PLACE/PLPOS 0x000E2440-0x000E257C and 0x000E10CC;
  the scratch assembler/decoder gained `add.s`/`sub.s`: 724,671 ELF words round-trip, 0 mismatches). Follow-up: the same
  independent pass over the follow-up `spawn.txt`/`missions.txt` gives **863 code words, 0
  mismatches** (adds 0x000E2300-0x000E25FF and the hook 0x0023D6BC `jal 0x000E2320`, whose `was 0C06290C` matches the
  ELF; `missions.txt` read from the committed version, range 0x000E7790-0x000E7813, because another agent now adds code
  from 0x000E7820 in the working copy). First version: independent pass over the final sources: **742 code words** in 0x000E1400-0x000E157F, 0x000E1600-0x000E1BFF,
  0x000E1E80-0x000E21FF, 0x000E7400-0x000E747F, 0x000E75EC, 0x000E7640-0x000E773F, 0x000E7790-0x000E7813: the comment's
  instruction text equals the disassembly and re-assembles to the word: **0 mismatches**. Hooks re-read from the sources:
  0x000E103C `jal 0x000E20E8`, 0x001898C8 `jal 0x000E1770`, 0x000E1008 `jal 0x000E1B38`, 0x000E1274 and 0x000E71E4
  `jal 0x000E1BAC`, 0x000E10BC `jal 0x000E1400`, 0x00188AEC/0x00189734 `jal 0x000E1600`, 0x000E75EC `jal 0x000E7790`.
- **Unchanged code kept.** Old vs new instruction sequences (branch targets masked): CHOOSE differs only by the 5 inserted
  words; INLIST, PRESENT and POKE are identical; PX differs only in the SWEEP call target; REL34 and X7J differ exactly by the
  changes of sections 2.2/2.3.
- **Simulation (scratch interpreter, mock game state, game functions stubbed; static evidence, not a runtime test).** The
  exact source words were run on a small R5900 interpreter with a mock GameMgr, model dictionary, pin list, char table,
  object table and timer (stubs: handle resolve, HUD index, residency, the pin core with "last free slot", streamer calling
  FITCHK, fit test, SPAWN = CHOOSE + a marker-7 human, DESPAWN, LEAVE, X2SEL, inventory cores); callee-saved registers and
  sp were checked after every call. Follow-up 2: **75 checks, 0 failures** (adds PLACE: moved by the helper (human copy or
  table copy changed) -> no fallback; not moved -> Teleport core to player 1 x + 1.5 (count 2) / - 1.5 (count 3); the
  interpreter gained lwc1/swc1/mtc1/add.s/sub.s). Follow-up: **71 checks, 0 failures** (`ch_simtest.py` 70, `ch_simtest2.py` 1; adds XCHK
  for the Ajax rows, KICK: no re-pin before 8 s, re-pin at 8.5 s keeping the first T0, no second re-pin within 8 s, timeout
  still 20 s after the first pin, join after a re-pin made the model resident; PINSVC: once per clock value, no instance
  while not resident, instance built with the streamer's call on the next frame once resident, then nothing more, no pin
  -> only the original call). First version: 54 checks, 0 failures (`ch_simtest.py` 53, `ch_simtest2.py` 1): XCHK for 23 level/checkpoint/Warrior cases (incl. M13 cp1-3 Fox,
  M14 cp1/5/6/7, hub cp10/11, M1, M2 cp1-5, M16 cp4/5); CHOOSE in M13 cp1 with Fox resident -> clone, Fox status 6; M13 cp3
  -> Fox; M15 with Cleon resident -> clone, Cleon status 6; the m6x1b sequence (P3 = Fox companion, preload Swan in slot 0,
  P4 = Swan, REL34(Fox) keeps slot 0, re-join refused while Ajax loads into slot 1, joins as Ajax, both pins kept; LV(Ajax)
  releases slot 1 only; REL34 of the W4P Swan releases slot 0); X10 A (P3 refused then Swan, preload Ajax, P4 refused then
  Ajax); no-fit (P4 = clone, NOFIT = Ajax, P3's pin kept); timeout (GT 4, clone, P3's pin kept); PX count 3 releases only
  the unused preload; a level's own pin of the same model is never released (OWN 0); CLRPIN; X7J for bytes 0/1/2 at cp 1/3;
  LVOWE after a gift (byte 2) and without one (byte 0); X3W with 4 players (LVOWE(3), LVOWE(2), owed byte for the gifted slot only, then the original core with 2 players).
- **`note_patches.py check`** (pnach generated to `local/m6/ch1.pnach`, `mod/w4p_m1.pnach` untouched):
```
CONFLICT 001C0648: ch1.pnach:1829 sets 0803C374, ch1.pnach:2509 sets 0803815C
CONFLICT 001C7890: ch1.pnach:1831 sets 0803C384, ch1.pnach:2511 sets 08038164
CONFLICT 001A6D28: ch1.pnach:1833 sets 0803C394, ch1.pnach:2513 sets 0803816C
CONFLICT 001A6C38: ch1.pnach:1835 sets 0803C3A4, ch1.pnach:2515 sets 08038174
CONFLICT 0041DC44: ch1.pnach:1837 sets 2CA20002, ch1.pnach:2811 sets 2CA20004
CONFLICT 0041DC50: ch1.pnach:1839 sets 3C030060, ch1.pnach:2813 sets 3C03000E
checked 3340 addresses in 1 files: 6 problems
```
  Follow-up `local/m6/ch3.pnach` (committed sources + follow-up `spawn.txt`):
```
CONFLICT 001C0648: ch3.pnach:1833 sets 0803C374, ch3.pnach:2513 sets 0803815C
CONFLICT 001C7890: ch3.pnach:1835 sets 0803C384, ch3.pnach:2515 sets 08038164
CONFLICT 001A6D28: ch3.pnach:1837 sets 0803C394, ch3.pnach:2517 sets 0803816C
CONFLICT 001A6C38: ch3.pnach:1839 sets 0803C3A4, ch3.pnach:2519 sets 08038174
CONFLICT 0041DC44: ch3.pnach:1841 sets 2CA20002, ch3.pnach:2815 sets 2CA20004
CONFLICT 0041DC50: ch3.pnach:1843 sets 3C030060, ch3.pnach:2817 sets 3C03000E
checked 3476 addresses in 1 files: 6 problems
```
  Follow-up 2 `local/m6/ch4.pnach` (HEAD 2124ac8 + this `spawn.txt`):
```
CONFLICT 001C0648: ch4.pnach:1917 sets 0803C374, ch4.pnach:2597 sets 0803815C
CONFLICT 001C7890: ch4.pnach:1919 sets 0803C384, ch4.pnach:2599 sets 08038164
CONFLICT 001A6D28: ch4.pnach:1921 sets 0803C394, ch4.pnach:2601 sets 0803816C
CONFLICT 001A6C38: ch4.pnach:1923 sets 0803C3A4, ch4.pnach:2603 sets 08038174
CONFLICT 0041DC44: ch4.pnach:1925 sets 2CA20002, ch4.pnach:2899 sets 2CA20004
CONFLICT 0041DC50: ch4.pnach:1927 sets 3C030060, ch4.pnach:2901 sets 3C03000E
checked 4257 addresses in 1 files: 6 problems
```
  and `python -I tools/note_patches.py check mod/m2/missions.txt mod/m2/spawn.txt mod/m2/spawn_leave.txt mod/m2/inventory.txt
  mod/m2/session.txt`: `checked 1356 addresses in 5 files: 0 problems`. The checker's cave test covers only
  0x000F0000-0x000F0FFF; the new ranges were checked separately (no ELF segment below 0x00100000; grep as in section 1).
- **Files**: `mod/m2/spawn.txt` 924 lines, `mod/m2/missions.txt` 239 lines, both CRLF only (checked byte-wise); edited with
  Python. Scratch tools (not in the repo): assembler/decoder, applier, verifier, interpreter and its tests in the session
  scratch directory.

## 4. Patch fragments (as in the sources)
### `mod/m2/spawn.txt` (`[warriors-4p 4p spawn]`): changed lines (JS hook, CHOOSE, FITCHK hook, SPAWN x offset, PINSVC hook, pin block, data, XC table, helpers, KICK, pin service, PLACE)
Unchanged lines between them (SPAWN, DESPAWN, candidate table 0x000E1580, statuses, game hooks 0x00188AEC/0x00189734, X2) are not repeated; the status comments now list 6.
```
patch=2,EE,000E103C,word,0C038842 // [warriors-4p 4p spawn]: jal 0x000E2108 JS (pnach had 0C038420 jal 0x000E1080 SPAWN); delay slot kept
patch=2,EE,000E10CC,word,3C014080 // lui at,0x4080  ; F-0195: SPAWN creates the Warrior 4 units beside player 1 (pnach had 3C013FC0 = 1.5 units), so PLACE can move him with HuTeleportNearHuman (needs >= 3.6 units)
// named-Warrior chooser CHOOSE (m2_spawn_name.md section 5.3, m6_chooser.md): first allowed, resident, absent Warrior; else player 1's char. Allowed = not excluded by the XC table (0x000E1E10, XCHK) for this level and checkpoint
patch=2,EE,000E1400,word,27BDFFA0 // CHOOSE: addiu sp, sp, -96  ; CHOOSE: in s0 = player 1 human; out s1 = char id; reloads f0
patch=2,EE,000E1404,word,FFBF0000 // sd ra, 0x0(sp)
patch=2,EE,000E1408,word,7FB30010 // sq s3, 0x10(sp)
patch=2,EE,000E140C,word,7FB40020 // sq s4, 0x20(sp)
patch=2,EE,000E1410,word,7FB50030 // sq s5, 0x30(sp)
patch=2,EE,000E1414,word,7FB60040 // sq s6, 0x40(sp)
patch=2,EE,000E1418,word,7FB70050 // sq s7, 0x50(sp)
patch=2,EE,000E141C,word,8E1100D0 // lw s1, 0xD0(s0)  ; fallback = player 1's original char id (old behaviour)
patch=2,EE,000E1420,word,3C13000E // lui s3, 0x000E
patch=2,EE,000E1424,word,26731580 // addiu s3, s3, 5504  ; s3 = candidate table
patch=2,EE,000E1428,word,0260102D // daddu v0, s3, zero
patch=2,EE,000E142C,word,8C430000 // ch_clr: lw v1, 0x0(v0)  ; clear the status word of every table entry
patch=2,EE,000E1430,word,AC400040 // sw zero, 0x40(v0)
patch=2,EE,000E1434,word,1460FFFD // bne v1, zero, 0x000E142C
patch=2,EE,000E1438,word,24420004 // addiu v0, v0, 4
patch=2,EE,000E143C,word,3C010051 // lui at, 0x0051
patch=2,EE,000E1440,word,8C34CD4C // lw s4, -0x32B4(at)  ; s4 = model dictionary *(0x0050CD4C)
patch=2,EE,000E1444,word,12800040 // beq s4, zero, 0x000E1548
patch=2,EE,000E1448,word,8C22489C // lw v0, 0x489C(at)  ; GameMgr *(0x0051489C)
patch=2,EE,000E144C,word,944356DC // lhu v1, 0x56DC(v0)  ; current level slot (FUN_004DAB50)
patch=2,EE,000E1450,word,000321C0 // sll a0, v1, 7
patch=2,EE,000E1454,word,00031880 // sll v1, v1, 2
patch=2,EE,000E1458,word,00831821 // addu v1, a0, v1  ; slot * 0x84
patch=2,EE,000E145C,word,00431021 // addu v0, v0, v1
patch=2,EE,000E1460,word,8C4214D8 // lw v0, 0x14D8(v0)  ; level number (FUN_004DAB58 table +4)
patch=2,EE,000E1464,word,2442FFC4 // addiu v0, v0, -60
patch=2,EE,000E1468,word,2C420005 // sltiu v0, v0, 5  ; levels 60-64: human init reads +0x114
patch=2,EE,000E146C,word,00021040 // sll v0, v0, 1
patch=2,EE,000E1470,word,24550112 // addiu s5, v0, 274  ; s5 = model field offset 0x112 / 0x114
patch=2,EE,000E1474,word,86650000 // ch_cand: lh a1, 0x0(s3)  ; candidate char id (0 = end of table)
patch=2,EE,000E1478,word,10A00033 // beq a1, zero, 0x000E1548
patch=2,EE,000E147C,word,86640002 // lh a0, 0x2(s3)  ; candidate HUD (name) index
patch=2,EE,000E1480,word,0C0387EA // jal 0x000E1FA8  ; X9/problem 1: excluded in this level and checkpoint? (XC table 0x000E1E10)
patch=2,EE,000E1484,word,00000000 // nop
patch=2,EE,000E1488,word,1440002C // bne v0, zero, 0x000E153C
patch=2,EE,000E148C,word,24080006 // addiu t0, zero, 6  ; status 6: excluded here (dead in the story, or the level script creates him later)
patch=2,EE,000E1490,word,240301AC // addiu v1, zero, 428
patch=2,EE,000E1494,word,00A31018 // mult v0, a1, v1
patch=2,EE,000E1498,word,3C030068 // lui v1, 0x0068
patch=2,EE,000E149C,word,24634620 // addiu v1, v1, 17952
patch=2,EE,000E14A0,word,00431021 // addu v0, v0, v1  ; char table entry 0x00684620 + id*0x1AC
patch=2,EE,000E14A4,word,84430116 // lh v1, 0x116(v0)  ; CfgChar arg 6 (1800/600); 0 = entry never configured
patch=2,EE,000E14A8,word,18600024 // blez v1, 0x000E153C
patch=2,EE,000E14AC,word,24080001 // addiu t0, zero, 1  ; status 1: char not configured
patch=2,EE,000E14B0,word,00551021 // addu v0, v0, s5
patch=2,EE,000E14B4,word,94450000 // lhu a1, 0x0(v0)  ; model index (u16, as FUN_00218008 reads it)
patch=2,EE,000E14B8,word,8E830084 // lw v1, 0x84(s4)  ; dictionary entry count (FUN_001780D0)
patch=2,EE,000E14BC,word,00A3182B // sltu v1, a1, v1
patch=2,EE,000E14C0,word,1060001E // beq v1, zero, 0x000E153C
patch=2,EE,000E14C4,word,24080002 // addiu t0, zero, 2  ; status 2: no model index (0xFFFF or out of range)
patch=2,EE,000E14C8,word,8E820088 // lw v0, 0x88(s4)
patch=2,EE,000E14CC,word,00052940 // sll a1, a1, 5
patch=2,EE,000E14D0,word,00452821 // addu a1, v0, a1  ; entry = FUN_001780D8(dict, index)
patch=2,EE,000E14D4,word,0280202D // daddu a0, s4, zero
patch=2,EE,000E14D8,word,0000302D // daddu a2, zero, zero
patch=2,EE,000E14DC,word,0C05DD34 // jal 0x001774D0  ; load state, same call/arguments as FUN_00218008
patch=2,EE,000E14E0,word,0000382D // daddu a3, zero, zero
patch=2,EE,000E14E4,word,10400015 // beq v0, zero, 0x000E153C
patch=2,EE,000E14E8,word,24080003 // addiu t0, zero, 3  ; status 3: model not resident
patch=2,EE,000E14EC,word,86770002 // lh s7, 0x2(s3)  ; s7 = candidate HUD index
patch=2,EE,000E14F0,word,0000B02D // daddu s6, zero, zero
patch=2,EE,000E14F4,word,001610C0 // ch_scan: sll v0, s6, 3  ; live humans: object table slots 0..59
patch=2,EE,000E14F8,word,3C03006F // lui v1, 0x006F
patch=2,EE,000E14FC,word,00431021 // addu v0, v0, v1
patch=2,EE,000E1500,word,8C44BD38 // lw a0, -0x42C8(v0)  ; *(0x006EBD38 + slot*8)
patch=2,EE,000E1504,word,10800005 // beq a0, zero, 0x000E151C
patch=2,EE,000E1508,word,00000000 // nop
patch=2,EE,000E150C,word,0C08A55C // jal 0x00229570  ; HUD index of that human (pure leaf)
patch=2,EE,000E1510,word,00000000 // nop
patch=2,EE,000E1514,word,10570009 // beq v0, s7, 0x000E153C
patch=2,EE,000E1518,word,24080004 // addiu t0, zero, 4  ; status 4: this Warrior is already in the level
patch=2,EE,000E151C,word,26D60001 // ch_next: addiu s6, s6, 1
patch=2,EE,000E1520,word,2AC2003C // slti v0, s6, 60
patch=2,EE,000E1524,word,1440FFF3 // bne v0, zero, 0x000E14F4
patch=2,EE,000E1528,word,00000000 // nop
patch=2,EE,000E152C,word,86710000 // lh s1, 0x0(s3)  ; chosen
patch=2,EE,000E1530,word,24080005 // addiu t0, zero, 5  ; status 5: chosen
patch=2,EE,000E1534,word,10000004 // beq zero, zero, 0x000E1548
patch=2,EE,000E1538,word,AE680040 // sw t0, 0x40(s3)
patch=2,EE,000E153C,word,AE680040 // ch_reject: sw t0, 0x40(s3)
patch=2,EE,000E1540,word,1000FFCC // beq zero, zero, 0x000E1474
patch=2,EE,000E1544,word,26730004 // addiu s3, s3, 4
patch=2,EE,000E1548,word,3C01000E // ch_done: lui at, 0x000E
patch=2,EE,000E154C,word,AC3115F0 // sw s1, 0x15F0(at)  ; last result (char id) for PINE
patch=2,EE,000E1550,word,DFBF0000 // ld ra, 0x0(sp)
patch=2,EE,000E1554,word,7BB30010 // lq s3, 0x10(sp)
patch=2,EE,000E1558,word,7BB40020 // lq s4, 0x20(sp)
patch=2,EE,000E155C,word,7BB50030 // lq s5, 0x30(sp)
patch=2,EE,000E1560,word,7BB60040 // lq s6, 0x40(sp)
patch=2,EE,000E1564,word,7BB70050 // lq s7, 0x50(sp)
patch=2,EE,000E1568,word,C6000010 // lwc1 f0, 0x10(s0)  ; SPAWN's delay slot loaded f0 before the call; reload it
patch=2,EE,000E156C,word,03E00008 // jr ra
patch=2,EE,000E1570,word,27BD0060 // addiu sp, sp, 96
// [warriors-4p 4p spawn] + [warriors-4p 4p spawn leave]: extra Warrior models for players 3-4 (m2_extra_model.md; two pin slots, m6_chooser.md): a pin is kept while a W4P-added Warrior of that name plays (USED) and released on his leave/delete (UNPIN), after the last join if nobody uses it (SWEEP), on timeout, on no-fit and at teardown
patch=2,EE,001898C8,word,0C0385DC // was 0C05DD76 jal 0x001775D8 (pin fit test) in FUN_001897A8 -> jal 0x000E1770 FITCHK; delay slot kept
patch=2,EE,0023D6BC,word,0C0388C8 // was 0C06290C jal 0x0018A430 (model request, every human every frame) in the human update FUN_0023D660 -> jal 0x000E2320 PINSVC (pin service, m6_chooser.md 2.6); delay slot sw v1,0x2A0(s0) kept
patch=2,EE,000E1600,word,3C0A000E // CLRPIN: lui t2, 0x000E  ; CLRPIN: called instead of FUN_0018AB20 (level teardown clears all pins)
patch=2,EE,000E1604,word,AD401C00 // sw zero, 0x1C00(t2)  ; slot 0 ID: our pins are gone with the others
patch=2,EE,000E1608,word,AD401C04 // sw zero, 0x1C04(t2)  ; slot 0 OWN
patch=2,EE,000E160C,word,AD401C50 // sw zero, 0x1C50(t2)  ; slot 1 ID
patch=2,EE,000E1610,word,AD401C54 // sw zero, 0x1C54(t2)  ; slot 1 OWN
patch=2,EE,000E1614,word,08062AC8 // j 0x0018AB20  ; tail jump: a0 and ra unchanged
patch=2,EE,000E1618,word,AD401C34 // sw zero, 0x1C34(t2)  ; NOFIT: next level, try again
patch=2,EE,000E161C,word,248200B4 // INLIST: addiu v0, a0, 180  ; INLIST(dict, model index): pin list dict+0xB4, stride 8
patch=2,EE,000E1620,word,24080020 // addiu t0, zero, 32
patch=2,EE,000E1624,word,8C430000 // il_loop: lw v1, 0x0(v0)
patch=2,EE,000E1628,word,10650005 // beq v1, a1, 0x000E1640
patch=2,EE,000E162C,word,2508FFFF // addiu t0, t0, -1
patch=2,EE,000E1630,word,1500FFFC // bne t0, zero, 0x000E1624
patch=2,EE,000E1634,word,24420008 // addiu v0, v0, 8
patch=2,EE,000E1638,word,03E00008 // jr ra
patch=2,EE,000E163C,word,0000102D // daddu v0, zero, zero
patch=2,EE,000E1640,word,03E00008 // il_yes: jr ra
patch=2,EE,000E1644,word,24020001 // addiu v0, zero, 1
patch=2,EE,000E1648,word,27BDFFF0 // PRESENT: addiu sp, sp, -16  ; PRESENT(HUD index); t3/t4 survive FUN_00229570 (leaf: a0,a1,v0,v1)
patch=2,EE,000E164C,word,FFBF0000 // sd ra, 0x0(sp)
patch=2,EE,000E1650,word,0080602D // daddu t4, a0, zero
patch=2,EE,000E1654,word,0000582D // daddu t3, zero, zero
patch=2,EE,000E1658,word,000B10C0 // pr_loop: sll v0, t3, 3
patch=2,EE,000E165C,word,3C03006F // lui v1, 0x006F
patch=2,EE,000E1660,word,00431021 // addu v0, v0, v1
patch=2,EE,000E1664,word,8C44BD38 // lw a0, -0x42C8(v0)  ; *(0x006EBD38 + slot*8), 0 = free
patch=2,EE,000E1668,word,10800005 // beq a0, zero, 0x000E1680
patch=2,EE,000E166C,word,00000000 // nop
patch=2,EE,000E1670,word,0C08A55C // jal 0x00229570  ; HUD index of that human
patch=2,EE,000E1674,word,00000000 // nop
patch=2,EE,000E1678,word,104C0006 // beq v0, t4, 0x000E1694
patch=2,EE,000E167C,word,24020001 // addiu v0, zero, 1
patch=2,EE,000E1680,word,256B0001 // pr_next: addiu t3, t3, 1
patch=2,EE,000E1684,word,2962003C // slti v0, t3, 60
patch=2,EE,000E1688,word,1440FFF3 // bne v0, zero, 0x000E1658
patch=2,EE,000E168C,word,00000000 // nop
patch=2,EE,000E1690,word,0000102D // daddu v0, zero, zero
patch=2,EE,000E1694,word,DFBF0000 // pr_out: ld ra, 0x0(sp)
patch=2,EE,000E1698,word,03E00008 // jr ra
patch=2,EE,000E169C,word,27BD0010 // addiu sp, sp, 16
patch=2,EE,000E16A0,word,27BDFFE0 // RELEASE: addiu sp, sp, -32  ; RELEASE(slot 0/1): unpin our model of that pin slot; no-op if the slot is empty
patch=2,EE,000E16A4,word,FFBF0000 // sd ra, 0x0(sp)
patch=2,EE,000E16A8,word,7FB00010 // sq s0, 0x10(sp)
patch=2,EE,000E16AC,word,0C0387A0 // jal 0x000E1E80
patch=2,EE,000E16B0,word,00000000 // nop
patch=2,EE,000E16B4,word,0040802D // daddu s0, v0, zero  ; s0 = pin slot (ID, OWN, MI, T0)
patch=2,EE,000E16B8,word,8E050000 // lw a1, 0x0(s0)  ; ID
patch=2,EE,000E16BC,word,10A0000E // beq a1, zero, 0x000E16F8
patch=2,EE,000E16C0,word,8E030004 // lw v1, 0x4(s0)  ; OWN
patch=2,EE,000E16C4,word,1060000A // beq v1, zero, 0x000E16F0  ; the level script pinned it first: never release someone else's pin
patch=2,EE,000E16C8,word,3C010051 // lui at, 0x0051
patch=2,EE,000E16CC,word,8C24CD4C // lw a0, -0x32B4(at)  ; dict *(0x0050CD4C)
patch=2,EE,000E16D0,word,10800007 // beq a0, zero, 0x000E16F0
patch=2,EE,000E16D4,word,00000000 // nop
patch=2,EE,000E16D8,word,0C062B50 // jal 0x0018AD40  ; SetCharacterModel core, release
patch=2,EE,000E16DC,word,24060001 // addiu a2, zero, 1
patch=2,EE,000E16E0,word,3C0A000E // lui t2, 0x000E
patch=2,EE,000E16E4,word,8D421C2C // lw v0, 0x1C2C(t2)
patch=2,EE,000E16E8,word,24420001 // addiu v0, v0, 1
patch=2,EE,000E16EC,word,AD421C2C // sw v0, 0x1C2C(t2)  ; N_RELEASE
patch=2,EE,000E16F0,word,AE000000 // rl_clear: sw zero, 0x0(s0)
patch=2,EE,000E16F4,word,AE000004 // sw zero, 0x4(s0)
patch=2,EE,000E16F8,word,DFBF0000 // rl_out: ld ra, 0x0(sp)
patch=2,EE,000E16FC,word,7BB00010 // lq s0, 0x10(sp)
patch=2,EE,000E1700,word,03E00008 // jr ra
patch=2,EE,000E1704,word,27BD0020 // addiu sp, sp, 32
patch=2,EE,000E1708,word,27BDFFF0 // POKE: addiu sp, sp, -16  ; POKE(): FUN_001897A8 services pinned models first
patch=2,EE,000E170C,word,FFBF0000 // sd ra, 0x0(sp)
patch=2,EE,000E1710,word,3C0A000E // lui t2, 0x000E
patch=2,EE,000E1714,word,8D421C48 // lw v0, 0x1C48(t2)  ; POKE_EN
patch=2,EE,000E1718,word,10400012 // beq v0, zero, 0x000E1764
patch=2,EE,000E171C,word,3C01005E // lui at, 0x005E
patch=2,EE,000E1720,word,8C245340 // lw a0, 0x5340(at)  ; loader *(0x005E5340)
patch=2,EE,000E1724,word,1080000F // beq a0, zero, 0x000E1764
patch=2,EE,000E1728,word,00000000 // nop
patch=2,EE,000E172C,word,0C05529A // jal 0x00154A68  ; queued loader requests (leaf); FUN_0040F8A0 returns early if != 0
patch=2,EE,000E1730,word,00000000 // nop
patch=2,EE,000E1734,word,1440000B // bne v0, zero, 0x000E1764
patch=2,EE,000E1738,word,3C010051 // lui at, 0x0051
patch=2,EE,000E173C,word,8C24CD4C // lw a0, -0x32B4(at)  ; dict
patch=2,EE,000E1740,word,10800008 // beq a0, zero, 0x000E1764
patch=2,EE,000E1744,word,00000000 // nop
patch=2,EE,000E1748,word,0C0625EA // jal 0x001897A8  ; model streamer
patch=2,EE,000E174C,word,00000000 // nop
patch=2,EE,000E1750,word,3C0A000E // lui t2, 0x000E
patch=2,EE,000E1754,word,AD421C1C // sw v0, 0x1C1C(t2)  ; POKE_RES
patch=2,EE,000E1758,word,8D421C30 // lw v0, 0x1C30(t2)
patch=2,EE,000E175C,word,24420001 // addiu v0, v0, 1
patch=2,EE,000E1760,word,AD421C30 // sw v0, 0x1C30(t2)  ; N_POKE
patch=2,EE,000E1764,word,DFBF0000 // pk_out: ld ra, 0x0(sp)
patch=2,EE,000E1768,word,03E00008 // jr ra
patch=2,EE,000E176C,word,27BD0010 // addiu sp, sp, 16
patch=2,EE,000E1770,word,27BDFFD0 // FITCHK: addiu sp, sp, -48  ; FITCHK(dict, entry, 0, 1): the streamer's pin fit test
patch=2,EE,000E1774,word,FFBF0000 // sd ra, 0x0(sp)
patch=2,EE,000E1778,word,7FB00010 // sq s0, 0x10(sp)
patch=2,EE,000E177C,word,7FB10020 // sq s1, 0x20(sp)
patch=2,EE,000E1780,word,00A0802D // daddu s0, a1, zero  ; entry being tested
patch=2,EE,000E1784,word,0C05DD76 // jal 0x001775D8  ; original fit test (evicts unreferenced assets if needed)
patch=2,EE,000E1788,word,00000000 // nop
patch=2,EE,000E178C,word,14400018 // bne v0, zero, 0x000E17F0  ; fits: unchanged
patch=2,EE,000E1790,word,0000882D // daddu s1, zero, zero  ; pin slot 0, 1
patch=2,EE,000E1794,word,0C0387A0 // fc_loop: jal 0x000E1E80
patch=2,EE,000E1798,word,0220202D // daddu a0, s1, zero
patch=2,EE,000E179C,word,8C450000 // lw a1, 0x0(v0)  ; ID
patch=2,EE,000E17A0,word,10A0000E // beq a1, zero, 0x000E17DC
patch=2,EE,000E17A4,word,8C430008 // lw v1, 0x8(v0)  ; MI
patch=2,EE,000E17A8,word,3C010051 // lui at, 0x0051
patch=2,EE,000E17AC,word,8C24CD4C // lw a0, -0x32B4(at)  ; dict
patch=2,EE,000E17B0,word,8C840088 // lw a0, 0x88(a0)  ; dictionary entries
patch=2,EE,000E17B4,word,00031940 // sll v1, v1, 5
patch=2,EE,000E17B8,word,00831821 // addu v1, a0, v1  ; this slot's entry (FUN_001780D8)
patch=2,EE,000E17BC,word,14700007 // bne v1, s0, 0x000E17DC  ; a level pin or our other slot failed: unchanged
patch=2,EE,000E17C0,word,3C0A000E // lui t2, 0x000E
patch=2,EE,000E17C4,word,AD451C34 // sw a1, 0x1C34(t2)  ; NOFIT: this Warrior does not fit in this level, do not try again
patch=2,EE,000E17C8,word,8D421C38 // lw v0, 0x1C38(t2)
patch=2,EE,000E17CC,word,24420001 // addiu v0, v0, 1
patch=2,EE,000E17D0,word,AD421C38 // sw v0, 0x1C38(t2)  ; N_NOFIT
patch=2,EE,000E17D4,word,0C0385A8 // jal 0x000E16A0  ; unpin (the streamer returns right after this call, the list change is safe)
patch=2,EE,000E17D8,word,0220202D // daddu a0, s1, zero
patch=2,EE,000E17DC,word,26310001 // fc_next: addiu s1, s1, 1
patch=2,EE,000E17E0,word,2A280002 // slti t0, s1, 2
patch=2,EE,000E17E4,word,1500FFEB // bne t0, zero, 0x000E1794
patch=2,EE,000E17E8,word,00000000 // nop
patch=2,EE,000E17EC,word,0000102D // daddu v0, zero, zero  ; report "does not fit" as the original did
patch=2,EE,000E17F0,word,DFBF0000 // fc_out: ld ra, 0x0(sp)
patch=2,EE,000E17F4,word,7BB00010 // lq s0, 0x10(sp)
patch=2,EE,000E17F8,word,7BB10020 // lq s1, 0x20(sp)
patch=2,EE,000E17FC,word,03E00008 // jr ra
patch=2,EE,000E1800,word,27BD0030 // addiu sp, sp, 48
patch=2,EE,000E1804,word,27BDFF90 // ENSURE: addiu sp, sp, -112  ; ENSURE(): frame 112, s0-s4 saved, 96/100/104 locals; v0 1 resident, 0 loading, 2 nothing to wait for
patch=2,EE,000E1808,word,FFBF0000 // sd ra, 0x0(sp)
patch=2,EE,000E180C,word,7FB00010 // sq s0, 0x10(sp)
patch=2,EE,000E1810,word,7FB10020 // sq s1, 0x20(sp)
patch=2,EE,000E1814,word,7FB20030 // sq s2, 0x30(sp)
patch=2,EE,000E1818,word,7FB30040 // sq s3, 0x40(sp)
patch=2,EE,000E181C,word,7FB40050 // sq s4, 0x50(sp)
patch=2,EE,000E1820,word,24130002 // addiu s3, zero, 2  ; result 2 unless shown otherwise
patch=2,EE,000E1824,word,24090006 // addiu t1, zero, 6  ; code 6: skipped (no dictionary, levels 60-64, no player 1)
patch=2,EE,000E1828,word,3C010051 // lui at, 0x0051
patch=2,EE,000E182C,word,8C32CD4C // lw s2, -0x32B4(at)  ; s2 = dict *(0x0050CD4C)
patch=2,EE,000E1830,word,12400097 // beq s2, zero, 0x000E1A90
patch=2,EE,000E1834,word,8C22489C // lw v0, 0x489C(at)  ; GameMgr *(0x0051489C)
patch=2,EE,000E1838,word,944356DC // lhu v1, 0x56DC(v0)  ; level slot
patch=2,EE,000E183C,word,000321C0 // sll a0, v1, 7
patch=2,EE,000E1840,word,00031880 // sll v1, v1, 2
patch=2,EE,000E1844,word,00831821 // addu v1, a0, v1
patch=2,EE,000E1848,word,00431821 // addu v1, v0, v1
patch=2,EE,000E184C,word,8C6314D8 // lw v1, 0x14D8(v1)  ; level number
patch=2,EE,000E1850,word,2463FFC4 // addiu v1, v1, -60
patch=2,EE,000E1854,word,2C630005 // sltiu v1, v1, 5
patch=2,EE,000E1858,word,1460008D // bne v1, zero, 0x000E1A90  ; levels 60-64: humans read +0x114, the pin core reads +0x112
patch=2,EE,000E185C,word,00000000 // nop
patch=2,EE,000E1860,word,0C0E409A // jal 0x00390268  ; player 1 human from GameMgr+0x228
patch=2,EE,000E1864,word,24440228 // addiu a0, v0, 552
patch=2,EE,000E1868,word,0040802D // daddu s0, v0, zero  ; s0 = player 1 (CHOOSE input)
patch=2,EE,000E186C,word,12000088 // beq s0, zero, 0x000E1A90
patch=2,EE,000E1870,word,24090006 // addiu t1, zero, 6  ; (code 6 again: the call may have changed t1)
patch=2,EE,000E1874,word,0000A02D // daddu s4, zero, zero
patch=2,EE,000E1878,word,0C0387A0 // en_chk: jal 0x000E1E80  ; both pin slots: still in the game's pin list?
patch=2,EE,000E187C,word,0280202D // daddu a0, s4, zero
patch=2,EE,000E1880,word,0040882D // daddu s1, v0, zero
patch=2,EE,000E1884,word,8E220000 // lw v0, 0x0(s1)  ; ID
patch=2,EE,000E1888,word,10400007 // beq v0, zero, 0x000E18A8
patch=2,EE,000E188C,word,0240202D // daddu a0, s2, zero
patch=2,EE,000E1890,word,0C038587 // jal 0x000E161C
patch=2,EE,000E1894,word,8E250008 // lw a1, 0x8(s1)  ; MI
patch=2,EE,000E1898,word,14400003 // bne v0, zero, 0x000E18A8
patch=2,EE,000E189C,word,00000000 // nop
patch=2,EE,000E18A0,word,AE200000 // sw zero, 0x0(s1)  ; removed behind our back (e.g. a script released it): forget it
patch=2,EE,000E18A4,word,AE200004 // sw zero, 0x4(s1)
patch=2,EE,000E18A8,word,26940001 // en_chknext: addiu s4, s4, 1
patch=2,EE,000E18AC,word,2A820002 // slti v0, s4, 2
patch=2,EE,000E18B0,word,1440FFF1 // bne v0, zero, 0x000E1878
patch=2,EE,000E18B4,word,00000000 // nop
patch=2,EE,000E18B8,word,0C038500 // jal 0x000E1400  ; CHOOSE: s1 = chosen char or player 1's; statuses at 0x000E15C0
patch=2,EE,000E18BC,word,00000000 // nop
patch=2,EE,000E18C0,word,8E0200D0 // lw v0, 0xD0(s0)
patch=2,EE,000E18C4,word,16220015 // bne s1, v0, 0x000E191C  ; a resident, absent, allowed Warrior exists
patch=2,EE,000E18C8,word,24130001 // addiu s3, zero, 1
patch=2,EE,000E18CC,word,24130000 // addiu s3, zero, 0  ; otherwise: the first not-resident, absent candidate (table order)
patch=2,EE,000E18D0,word,3C11000E // lui s1, 0x000E
patch=2,EE,000E18D4,word,26311580 // addiu s1, s1, 5504
patch=2,EE,000E18D8,word,86220000 // en_p2: lh v0, 0x0(s1)  ; candidate char id, 0 = end
patch=2,EE,000E18DC,word,1040000C // beq v0, zero, 0x000E1910
patch=2,EE,000E18E0,word,8E230040 // lw v1, 0x40(s1)  ; its CHOOSE status
patch=2,EE,000E18E4,word,2463FFFD // addiu v1, v1, -3
patch=2,EE,000E18E8,word,14600005 // bne v1, zero, 0x000E1900  ; only status 3: configured, valid model index, not excluded, not resident
patch=2,EE,000E18EC,word,00000000 // nop
patch=2,EE,000E18F0,word,0C038592 // jal 0x000E1648
patch=2,EE,000E18F4,word,86240002 // lh a0, 0x2(s1)  ; HUD index
patch=2,EE,000E18F8,word,10400003 // beq v0, zero, 0x000E1908
patch=2,EE,000E18FC,word,00000000 // nop
patch=2,EE,000E1900,word,1000FFF5 // en_p2next: beq zero, zero, 0x000E18D8
patch=2,EE,000E1904,word,26310004 // addiu s1, s1, 4
patch=2,EE,000E1908,word,10000004 // en_p2hit: beq zero, zero, 0x000E191C
patch=2,EE,000E190C,word,86310000 // lh s1, 0x0(s1)  ; target char id
patch=2,EE,000E1910,word,24130002 // en_none: addiu s3, zero, 2
patch=2,EE,000E1914,word,1000005E // beq zero, zero, 0x000E1A90
patch=2,EE,000E1918,word,24090004 // addiu t1, zero, 4  ; code 4: no Warrior left to load
patch=2,EE,000E191C,word,3C0A000E // en_target: lui t2, 0x000E  ; s1 = target, s3 = 1 (resident) or 0 (needs a load)
patch=2,EE,000E1920,word,8D421C34 // lw v0, 0x1C34(t2)  ; NOFIT
patch=2,EE,000E1924,word,14510005 // bne v0, s1, 0x000E193C
patch=2,EE,000E1928,word,24090007 // addiu t1, zero, 7  ; code 7: this Warrior did not fit in this level
patch=2,EE,000E192C,word,16600058 // bne s3, zero, 0x000E1A90  ; resident now anyway: CHOOSE picks it
patch=2,EE,000E1930,word,00000000 // nop
patch=2,EE,000E1934,word,10000056 // beq zero, zero, 0x000E1A90
patch=2,EE,000E1938,word,24130002 // addiu s3, zero, 2
patch=2,EE,000E193C,word,8D421C00 // en_fitok: lw v0, 0x1C00(t2)  ; already pinned in slot 0 or 1?
patch=2,EE,000E1940,word,10510043 // beq v0, s1, 0x000E1A50
patch=2,EE,000E1944,word,0000A02D // daddu s4, zero, zero
patch=2,EE,000E1948,word,8D421C50 // lw v0, 0x1C50(t2)
patch=2,EE,000E194C,word,10510040 // beq v0, s1, 0x000E1A50
patch=2,EE,000E1950,word,24140001 // addiu s4, zero, 1
patch=2,EE,000E1954,word,8D421C00 // lw v0, 0x1C00(t2)  ; a free slot
patch=2,EE,000E1958,word,10400016 // beq v0, zero, 0x000E19B4
patch=2,EE,000E195C,word,0000A02D // daddu s4, zero, zero
patch=2,EE,000E1960,word,8D421C50 // lw v0, 0x1C50(t2)
patch=2,EE,000E1964,word,10400013 // beq v0, zero, 0x000E19B4
patch=2,EE,000E1968,word,24140001 // addiu s4, zero, 1
patch=2,EE,000E196C,word,0000A02D // daddu s4, zero, zero  ; else a slot whose Warrior no W4P-added player uses any more
patch=2,EE,000E1970,word,0C0387A0 // en_free: jal 0x000E1E80
patch=2,EE,000E1974,word,0280202D // daddu a0, s4, zero
patch=2,EE,000E1978,word,0C0387A7 // jal 0x000E1E9C
patch=2,EE,000E197C,word,8C440000 // lw a0, 0x0(v0)  ; that slot's Warrior
patch=2,EE,000E1980,word,1040000A // beq v0, zero, 0x000E19AC
patch=2,EE,000E1984,word,00000000 // nop
patch=2,EE,000E1988,word,26940001 // addiu s4, s4, 1
patch=2,EE,000E198C,word,2A820002 // slti v0, s4, 2
patch=2,EE,000E1990,word,1440FFF7 // bne v0, zero, 0x000E1970
patch=2,EE,000E1994,word,00000000 // nop
patch=2,EE,000E1998,word,24090005 // addiu t1, zero, 5  ; code 5: both pins in use, or the game's pin list is full
patch=2,EE,000E199C,word,1660003C // en_nopin: bne s3, zero, 0x000E1A90  ; resident anyway: CHOOSE will pick it
patch=2,EE,000E19A0,word,00000000 // nop
patch=2,EE,000E19A4,word,1000003A // beq zero, zero, 0x000E1A90
patch=2,EE,000E19A8,word,24130002 // addiu s3, zero, 2  ; cannot load: let the join fall back (clone)
patch=2,EE,000E19AC,word,0C0385A8 // en_rel: jal 0x000E16A0  ; free that slot
patch=2,EE,000E19B0,word,0280202D // daddu a0, s4, zero
patch=2,EE,000E19B4,word,240301AC // en_slot: addiu v1, zero, 428  ; s4 = free slot
patch=2,EE,000E19B8,word,02231018 // mult v0, s1, v1
patch=2,EE,000E19BC,word,3C030068 // lui v1, 0x0068
patch=2,EE,000E19C0,word,24634620 // addiu v1, v1, 17952
patch=2,EE,000E19C4,word,00431021 // addu v0, v0, v1  ; char table entry 0x00684620 + id*0x1AC
patch=2,EE,000E19C8,word,94450112 // lhu a1, 0x112(v0)  ; model index as FUN_0018AD40 reads it (+0x112)
patch=2,EE,000E19CC,word,AFA50060 // sw a1, 0x60(sp)
patch=2,EE,000E19D0,word,0C038587 // jal 0x000E161C
patch=2,EE,000E19D4,word,0240202D // daddu a0, s2, zero
patch=2,EE,000E19D8,word,AFA20064 // sw v0, 0x64(sp)  ; 1 = pinned before us (by the level)
patch=2,EE,000E19DC,word,0240202D // daddu a0, s2, zero
patch=2,EE,000E19E0,word,0220282D // daddu a1, s1, zero
patch=2,EE,000E19E4,word,0C062B50 // jal 0x0018AD40  ; SetCharacterModel(target, 0) core: pin (instance now if resident)
patch=2,EE,000E19E8,word,0000302D // daddu a2, zero, zero
patch=2,EE,000E19EC,word,0240202D // daddu a0, s2, zero
patch=2,EE,000E19F0,word,0C038587 // jal 0x000E161C
patch=2,EE,000E19F4,word,8FA50060 // lw a1, 0x60(sp)
patch=2,EE,000E19F8,word,1040FFE8 // beq v0, zero, 0x000E199C  ; not listed: the game's pin list is full
patch=2,EE,000E19FC,word,24090005 // addiu t1, zero, 5
patch=2,EE,000E1A00,word,0C0387A0 // jal 0x000E1E80
patch=2,EE,000E1A04,word,0280202D // daddu a0, s4, zero
patch=2,EE,000E1A08,word,AC510000 // sw s1, 0x0(v0)  ; ID
patch=2,EE,000E1A0C,word,8FA30064 // lw v1, 0x64(sp)
patch=2,EE,000E1A10,word,2C630001 // sltiu v1, v1, 1
patch=2,EE,000E1A14,word,AC430004 // sw v1, 0x4(v0)  ; OWN: we own it only if it was not pinned before
patch=2,EE,000E1A18,word,8FA30060 // lw v1, 0x60(sp)
patch=2,EE,000E1A1C,word,AC430008 // sw v1, 0x8(v0)  ; MI
patch=2,EE,000E1A20,word,3C010051 // lui at, 0x0051
patch=2,EE,000E1A24,word,8C23B734 // lw v1, -0x48CC(at)  ; timer object *(0x0050B734)
patch=2,EE,000E1A28,word,10600002 // beq v1, zero, 0x000E1A34
patch=2,EE,000E1A2C,word,0000202D // daddu a0, zero, zero
patch=2,EE,000E1A30,word,8C640038 // lw a0, 0x38(v1)  ; game clock (ms)
patch=2,EE,000E1A34,word,AC44000C // en_t0: sw a0, 0xC(v0)  ; T0
patch=2,EE,000E1A38,word,3C0A000E // lui t2, 0x000E
patch=2,EE,000E1A3C,word,8D431C20 // lw v1, 0x1C20(t2)
patch=2,EE,000E1A40,word,24630001 // addiu v1, v1, 1
patch=2,EE,000E1A44,word,AD431C20 // sw v1, 0x1C20(t2)  ; N_PIN
patch=2,EE,000E1A48,word,10000002 // beq zero, zero, 0x000E1A54
patch=2,EE,000E1A4C,word,24090002 // addiu t1, zero, 2  ; code 2: new pin
patch=2,EE,000E1A50,word,24090003 // en_have: addiu t1, zero, 3  ; code 3: existing pin (s4 = its slot)
patch=2,EE,000E1A54,word,3C0A000E // en_poke: lui t2, 0x000E
patch=2,EE,000E1A58,word,AD541C3C // sw s4, 0x1C3C(t2)  ; EN_SLOT: the slot GATE waits on
patch=2,EE,000E1A5C,word,1660000C // bne s3, zero, 0x000E1A90  ; resident: nothing to stream
patch=2,EE,000E1A60,word,00000000 // nop
patch=2,EE,000E1A64,word,AFA90068 // sw t1, 0x68(sp)
patch=2,EE,000E1A68,word,0C0385C2 // jal 0x000E1708
patch=2,EE,000E1A6C,word,00000000 // nop
patch=2,EE,000E1A70,word,0C0387A0 // jal 0x000E1E80
patch=2,EE,000E1A74,word,0280202D // daddu a0, s4, zero
patch=2,EE,000E1A78,word,8FA90068 // lw t1, 0x68(sp)
patch=2,EE,000E1A7C,word,8C420000 // lw v0, 0x0(v0)
patch=2,EE,000E1A80,word,14400003 // bne v0, zero, 0x000E1A90  ; still pinned: waiting for the load
patch=2,EE,000E1A84,word,00000000 // nop
patch=2,EE,000E1A88,word,24130002 // addiu s3, zero, 2  ; FITCHK unpinned it during the poke: does not fit
patch=2,EE,000E1A8C,word,24090007 // addiu t1, zero, 7
patch=2,EE,000E1A90,word,3C0A000E // en_code: lui t2, 0x000E
patch=2,EE,000E1A94,word,AD491C10 // sw t1, 0x1C10(t2)  ; EN_LAST
patch=2,EE,000E1A98,word,0260102D // daddu v0, s3, zero
patch=2,EE,000E1A9C,word,DFBF0000 // ld ra, 0x0(sp)
patch=2,EE,000E1AA0,word,7BB00010 // lq s0, 0x10(sp)
patch=2,EE,000E1AA4,word,7BB10020 // lq s1, 0x20(sp)
patch=2,EE,000E1AA8,word,7BB20030 // lq s2, 0x30(sp)
patch=2,EE,000E1AAC,word,7BB30040 // lq s3, 0x40(sp)
patch=2,EE,000E1AB0,word,7BB40050 // lq s4, 0x50(sp)
patch=2,EE,000E1AB4,word,03E00008 // jr ra
patch=2,EE,000E1AB8,word,27BD0070 // addiu sp, sp, 112
patch=2,EE,000E1B38,word,27BDFFE0 // PX: addiu sp, sp, -32  ; PX(gang, 0)
patch=2,EE,000E1B3C,word,FFBF0000 // sd ra, 0x0(sp)
patch=2,EE,000E1B40,word,7FB00010 // sq s0, 0x10(sp)
patch=2,EE,000E1B44,word,0C038718 // jal 0x000E1C60  ; X2SEL (X2 picker; player 2 / level start: original PickJoinCompanion)
patch=2,EE,000E1B48,word,00000000 // nop
patch=2,EE,000E1B4C,word,0040802D // daddu s0, v0, zero
patch=2,EE,000E1B50,word,12000011 // beq s0, zero, 0x000E1B98  ; nobody: SPAWNPICK goes on to JS
patch=2,EE,000E1B54,word,00000000 // nop
patch=2,EE,000E1B58,word,0640000F // bltz s2, 0x000E1B98  ; level start / script join: unchanged
patch=2,EE,000E1B5C,word,24030002 // addiu v1, zero, 2
patch=2,EE,000E1B60,word,16630008 // bne s3, v1, 0x000E1B84
patch=2,EE,000E1B64,word,3C0A000E // lui t2, 0x000E
patch=2,EE,000E1B68,word,8D421C44 // lw v0, 0x1C44(t2)  ; PRELOAD_AT3
patch=2,EE,000E1B6C,word,1040000A // beq v0, zero, 0x000E1B98
patch=2,EE,000E1B70,word,00000000 // nop
patch=2,EE,000E1B74,word,0C038601 // jal 0x000E1804  ; 3rd player took a companion: start the 4th player's Warrior now
patch=2,EE,000E1B78,word,00000000 // nop
patch=2,EE,000E1B7C,word,10000006 // beq zero, zero, 0x000E1B98
patch=2,EE,000E1B80,word,00000000 // nop
patch=2,EE,000E1B84,word,24030003 // px_four: addiu v1, zero, 3
patch=2,EE,000E1B88,word,16630003 // bne s3, v1, 0x000E1B98
patch=2,EE,000E1B8C,word,00000000 // nop
patch=2,EE,000E1B90,word,0C0387D3 // jal 0x000E1F4C  ; 4th player took a companion: release pins no W4P-added player uses
patch=2,EE,000E1B94,word,00000000 // nop
patch=2,EE,000E1B98,word,0200102D // px_out: daddu v0, s0, zero
patch=2,EE,000E1B9C,word,DFBF0000 // ld ra, 0x0(sp)
patch=2,EE,000E1BA0,word,7BB00010 // lq s0, 0x10(sp)
patch=2,EE,000E1BA4,word,03E00008 // jr ra
patch=2,EE,000E1BA8,word,27BD0020 // addiu sp, sp, 32
patch=2,EE,000E1BAC,word,27BDFFE0 // LV: addiu sp, sp, -32  ; LV(handle): s0 = the leaving W4P-added human (LEAVEHOOK / session LEAVE)
patch=2,EE,000E1BB0,word,FFBF0000 // sd ra, 0x0(sp)
patch=2,EE,000E1BB4,word,7FB10010 // sq s1, 0x10(sp)
patch=2,EE,000E1BB8,word,0C038460 // jal 0x000E1180  ; DESPAWN(handle) (original call)
patch=2,EE,000E1BBC,word,8E1100D0 // lw s1, 0xD0(s0)  ; char id of the leaving Warrior, read before it is deleted
patch=2,EE,000E1BC0,word,0C0387BA // jal 0x000E1EE8  ; release his pin unless another W4P-added Warrior still uses that Warrior
patch=2,EE,000E1BC4,word,0220202D // daddu a0, s1, zero
patch=2,EE,000E1BC8,word,DFBF0000 // ld ra, 0x0(sp)
patch=2,EE,000E1BCC,word,7BB10010 // lq s1, 0x10(sp)
patch=2,EE,000E1BD0,word,03E00008 // jr ra
patch=2,EE,000E1BD4,word,27BD0020 // addiu sp, sp, 32
patch=0,EE,000E1C00,word,00000000 // slot 0 ID: char id of our first model pin (0 = none) (startup only)
patch=0,EE,000E1C04,word,00000000 // slot 0 OWN: 1 = we created the pin (only then we release it) (startup only)
patch=0,EE,000E1C08,word,00000000 // slot 0 MI: model index of the pin (startup only)
patch=0,EE,000E1C0C,word,00000000 // slot 0 T0: game clock (ms) when pinned (startup only)
patch=0,EE,000E1C10,word,00000000 // EN_LAST: last ENSURE code (1 resident,2 new pin,3 existing pin,4 none left,5 no free slot or list full,6 skipped,7 no fit) (startup only)
patch=0,EE,000E1C14,word,00000000 // GT_LAST: last GATE code (1 go resident,2 go nothing to wait,3 refused,4 go after timeout,5 go after a re-pin) (startup only)
patch=0,EE,000E1C18,word,00000000 // GT_T: ms since the pin at the last refused/timed-out GATE (startup only)
patch=0,EE,000E1C1C,word,00000000 // POKE_RES: last FUN_001897A8 result (startup only)
patch=0,EE,000E1C20,word,00000000 // N_PIN: pins made (startup only)
patch=0,EE,000E1C24,word,00000000 // N_REFUSE: join presses refused (startup only)
patch=0,EE,000E1C28,word,00000000 // N_TIMEOUT: timeouts (startup only)
patch=0,EE,000E1C2C,word,00000000 // N_RELEASE: pins released (startup only)
patch=0,EE,000E1C30,word,00000000 // N_POKE: streamer calls (startup only)
patch=0,EE,000E1C34,word,00000000 // NOFIT: char id whose model did not fit in this level (cleared at teardown) (startup only)
patch=0,EE,000E1C38,word,00000000 // N_NOFIT: fit failures of our pins (startup only)
patch=0,EE,000E1C3C,word,00000000 // EN_SLOT: pin slot (0/1) of ENSURE's last target, the one GATE waits on (startup only)
patch=0,EE,000E1C40,word,00004E20 // TIMEOUT_MS: config: give up waiting after this many ms (then clone) (startup only)
patch=0,EE,000E1C44,word,00000001 // PRELOAD_AT3: config: 1 = start loading the 4th player's Warrior when the 3rd player joins, 0 = only on the 4th join (startup only)
patch=0,EE,000E1C48,word,00000001 // POKE_EN: config: 1 = call the streamer after pinning, 0 = wait for the game's scheduler (startup only)
patch=0,EE,000E1C4C,word,00000001 // OWN3: config (X10 A): 1 = the 3rd player also waits for his own Warrior model when no companion is free, 0 = clone at once (old) (startup only)
patch=0,EE,000E1C50,word,00000000 // slot 1 ID: char id of our second model pin (0 = none) (startup only)
patch=0,EE,000E1C54,word,00000000 // slot 1 OWN (startup only)
patch=0,EE,000E1C58,word,00000000 // slot 1 MI (startup only)
patch=0,EE,000E1C5C,word,00000000 // slot 1 T0 (startup only)
// XC (m6_chooser.md, problems 1-2 / X9 A): Warriors CHOOSE and ENSURE never give to players 3-4 in a level and checkpoint
// range, because the level script creates (or deletes and re-creates) them later, or because they are dead in the story.
// Rows: byte level number, byte (first checkpoint << 4 | last checkpoint), u16 mask of HUD name indices (FUN_00229570: Swan 0,
// Cochise 1, Cowboy 2, Ajax 3, Rembrandt 4, Fox 5, Vermin 6, Snow 7, Cleon 8). Checkpoint = GameMgr+0x33A. 0 ends the table.
// Warriors present in the level are already refused by CHOOSE's own presence test (status 4).
patch=0,EE,000E1E10,word,01400F63 // XC row: level 99, cp 0-15, mask 0x140 = Vermin,Cleon; M1 level99, all checkpoints: Vermin, Cleon (teachers created and removed per chapter: AddCombatTeacher 09653:127 / RemoveGang 09653:1273, AddTeacher 09654:84 and 09655:65, AddSCleon 09654:85 / RemoveGang 09654:106) (startup only)
patch=0,EE,000E1E14,word,00080150 // XC row: level 80, cp 0-1, mask 0x008 = Ajax; M2 level80 cp <= 1: Ajax (AddAjax 08774:97, recruited 08774:270) (startup only)
patch=0,EE,000E1E18,word,00840250 // XC row: level 80, cp 0-2, mask 0x084 = Cowboy,Snow; M2 level80 cp <= 2: Snow, Cowboy (AddSnowCowboy 08775:35, recruited 08775:147-148) (startup only)
patch=0,EE,000E1E1C,word,00200350 // XC row: level 80, cp 0-3, mask 0x020 = Fox; M2 level80 cp <= 3: Fox (AddFox 08776:80, recruited 08776:511) (startup only)
patch=0,EE,000E1E20,word,00030450 // XC row: level 80, cp 0-4, mask 0x003 = Swan,Cochise; M2 level80 cp <= 4: Swan, Cochise (AddCochiseSwan 08777:31, recruited 08777:243-244) (startup only)
patch=0,EE,000E1E24,word,00080557 // XC row: level 87, cp 0-5, mask 0x008 = Ajax; M3 level87 cp <= 5: Ajax (HuDelete(ajax) 09225:154, re-created for the last scenes 09225:768) (startup only)
patch=0,EE,000E1E28,word,00800203 // XC row: level 3, cp 0-2, mask 0x080 = Snow; M6 level3 cp <= 2: Snow (first created by AddWarriors03 at the cp2 -> cp3 swap, 08021:200-221) (startup only)
patch=0,EE,000E1E2C,word,00900405 // XC row: level 5, cp 0-4, mask 0x090 = Rembrandt,Snow; M7 level5 cp <= 4: Rembrandt, Snow (HuDelete 08482:150-151, re-created in cp4 Setup 08484:68-73) (startup only)
patch=0,EE,000E1E30,word,00800156 // XC row: level 86, cp 0-1, mask 0x080 = Snow; M9 level86 cp <= 1: Snow (intro gang Scene1Warriors, then C1.SnowAdd 09163:607) (startup only)
patch=0,EE,000E1E34,word,0027045D // XC row: level 93, cp 0-4, mask 0x027 = Swan,Cochise,Cowboy,Fox; M10 level93 cp <= 4: Swan, Cochise, Cowboy, Fox (AddClubhouseWarriors 09377:156, 09378:35) (startup only)
patch=0,EE,000E1E38,word,0017055D // XC row: level 93, cp 0-5, mask 0x017 = Swan,Cochise,Cowboy,Rembrandt; M10 level93 cp <= 5: Swan, Cochise, Cowboy, Rembrandt (AddLCWarriors 09379:78, removed 09379:106) (startup only)
patch=0,EE,000E1E3C,word,00A0041F // XC row: level 31, cp 0-4, mask 0x0A0 = Fox,Snow; M11 level31 cp <= 4: Fox, Snow (RDSceneWarriors 07917:88-93) (startup only)
patch=0,EE,000E1E40,word,0008051F // XC row: level 31, cp 0-5, mask 0x008 = Ajax; M11 level31 cp <= 5: Ajax (DevilWarriors 07915:98-108) (startup only)
patch=0,EE,000E1E44,word,00200209 // XC row: level 9, cp 0-2, mask 0x020 = Fox; M13 level9 cp <= 2: Fox (HuDelete(fox) 09720:157; AddFoxMid 09721:40-42, AddFox 09721:247-270) (startup only)
patch=0,EE,000E1E48,word,00080233 // XC row: level 51, cp 0-2, mask 0x008 = Ajax; M14 level51 cp <= 2: Ajax (pit fight StartToRun 08181 main_5, AjaxAddToWarriors 08182:107) (startup only)
patch=0,EE,000E1E4C,word,00400433 // XC row: level 51, cp 0-4, mask 0x040 = Vermin; M14 level51 cp <= 4: Vermin (rescue gang WarrSplit01, 08184 RunVermin, VerminAddToWarriors 08184:551) (startup only)
patch=0,EE,000E1E50,word,00360533 // XC row: level 51, cp 0-5, mask 0x036 = Cochise,Cowboy,Rembrandt,Fox; M14 level51 cp <= 5: Cochise, Cowboy, Fox, Rembrandt (WarrSplit, GladToSeeYa 08185:721) (startup only)
patch=0,EE,000E1E54,word,01000F33 // XC row: level 51, cp 0-15, mask 0x100 = Cleon; M14 level51: Cleon (X9 A: dead in the story after M13; no M14-M18 script creates him) (startup only)
patch=0,EE,000E1E58,word,01000F34 // XC row: level 52, cp 0-15, mask 0x100 = Cleon; M15 level52: Cleon (X9 A) (startup only)
patch=0,EE,000E1E5C,word,008D0436 // XC row: level 54, cp 0-4, mask 0x08D = Swan,Cowboy,Ajax,Snow; M16 level54 cp <= 4: Swan, Cowboy, Ajax, Snow (AltWar gangs per chapter, AddAjax 08352:187-213, AddFinalWarriors/AddAjaxFinal 08353:31-56) (startup only)
patch=0,EE,000E1E60,word,01200F36 // XC row: level 54, cp 0-15, mask 0x120 = Fox,Cleon; M16 level54: Cleon (X9 A), Fox (X9 A, HYPOTHESIS: dies in the opening subway scene l54_c1, cast 08355:131; no later script creates him) (startup only)
patch=0,EE,000E1E64,word,00850237 // XC row: level 55, cp 0-2, mask 0x085 = Swan,Cowboy,Snow; M17 level55 cp <= 2: Swan, Cowboy, Snow (AddWarriors04 at the cp2 -> cp3 swap, 08404:81-83) (startup only)
patch=0,EE,000E1E68,word,01280F37 // XC row: level 55, cp 0-15, mask 0x128 = Ajax,Fox,Cleon; M17 level55: Cleon, Fox (X9 A), Ajax (X9 A: arrested at the end of M16 - final scenes l54_c3_b/c with the cop lcop (char 260), two cops and the objects Cuff1/Cuff2 08350:181-202; no M17/M18 script creates Ajax) (startup only)
patch=0,EE,000E1E6C,word,01280F54 // XC row: level 84, cp 0-15, mask 0x128 = Ajax,Fox,Cleon; M18 level84: Cleon, Fox, Ajax (X9 A) (startup only)
patch=0,EE,000E1E70,word,0128BF5F // XC row: level 95, cp 11-15, mask 0x128 = Ajax,Fox,Cleon; hub level95 cp >= 11 (post-game, 04106:1763): Cleon, Fox, Ajax (X9 A, HYPOTHESIS for the hub) (startup only)
patch=0,EE,000E1E74,word,00000000 // XC table end (startup only)
// Helpers at 0x000E1E80 (pin slot k at 0x000E1C00 + 0x50*k: ID, OWN, MI, T0): SLOTP, USED, UNPIN, SWEEP, XCHK, GATE, JS, KICK (re-pin of a stalled pin, data 0x000E2300)
patch=2,EE,000E1E80,word,00041100 // SLOTP: sll v0, a0, 4  ; SLOTP(k) leaf: v0 = pin slot k (0/1) = 0x000E1C00 + 0x50*k; uses v0, v1
patch=2,EE,000E1E84,word,00041980 // sll v1, a0, 6
patch=2,EE,000E1E88,word,00431021 // addu v0, v0, v1
patch=2,EE,000E1E8C,word,3C03000E // lui v1, 0x000E
patch=2,EE,000E1E90,word,24631C00 // addiu v1, v1, 7168
patch=2,EE,000E1E94,word,03E00008 // jr ra
patch=2,EE,000E1E98,word,00431021 // addu v0, v0, v1
patch=2,EE,000E1E9C,word,3C08006F // USED: lui t0, 0x006F  ; USED(char id) leaf: v0 = 1 if a live W4P-added Warrior (+0x1B1 = 7) has this char id (+0xD0)
patch=2,EE,000E1EA0,word,2508BD38 // addiu t0, t0, -17096  ; object table 0x006EBD38 (slots 0..59 = humans)
patch=2,EE,000E1EA4,word,2409003C // addiu t1, zero, 60
patch=2,EE,000E1EA8,word,240C0007 // addiu t4, zero, 7
patch=2,EE,000E1EAC,word,8D0A0000 // us_loop: lw t2, 0x0(t0)  ; human or 0
patch=2,EE,000E1EB0,word,11400007 // beq t2, zero, 0x000E1ED0
patch=2,EE,000E1EB4,word,00000000 // nop
patch=2,EE,000E1EB8,word,8D4B00D0 // lw t3, 0xD0(t2)  ; char id
patch=2,EE,000E1EBC,word,15640004 // bne t3, a0, 0x000E1ED0
patch=2,EE,000E1EC0,word,00000000 // nop
patch=2,EE,000E1EC4,word,914B01B1 // lbu t3, 0x1B1(t2)  ; join priority; 7 = added by W4P SPAWN
patch=2,EE,000E1EC8,word,116C0005 // beq t3, t4, 0x000E1EE0
patch=2,EE,000E1ECC,word,24020001 // addiu v0, zero, 1
patch=2,EE,000E1ED0,word,2529FFFF // us_next: addiu t1, t1, -1
patch=2,EE,000E1ED4,word,1520FFF5 // bne t1, zero, 0x000E1EAC
patch=2,EE,000E1ED8,word,25080008 // addiu t0, t0, 8
patch=2,EE,000E1EDC,word,0000102D // daddu v0, zero, zero
patch=2,EE,000E1EE0,word,03E00008 // us_out: jr ra
patch=2,EE,000E1EE4,word,00000000 // nop
patch=2,EE,000E1EE8,word,27BDFFE0 // UNPIN: addiu sp, sp, -32  ; UNPIN(char id): release our pin of that Warrior when no W4P-added Warrior uses it any more
patch=2,EE,000E1EEC,word,FFBF0000 // sd ra, 0x0(sp)
patch=2,EE,000E1EF0,word,7FB00010 // sq s0, 0x10(sp)
patch=2,EE,000E1EF4,word,0080802D // daddu s0, a0, zero
patch=2,EE,000E1EF8,word,12000010 // beq s0, zero, 0x000E1F3C
patch=2,EE,000E1EFC,word,00000000 // nop
patch=2,EE,000E1F00,word,0C0387A7 // jal 0x000E1E9C
patch=2,EE,000E1F04,word,0200202D // daddu a0, s0, zero
patch=2,EE,000E1F08,word,1440000C // bne v0, zero, 0x000E1F3C  ; still in use: keep
patch=2,EE,000E1F0C,word,3C0A000E // lui t2, 0x000E
patch=2,EE,000E1F10,word,8D421C00 // lw v0, 0x1C00(t2)  ; slot 0
patch=2,EE,000E1F14,word,14500004 // bne v0, s0, 0x000E1F28
patch=2,EE,000E1F18,word,00000000 // nop
patch=2,EE,000E1F1C,word,0C0385A8 // jal 0x000E16A0
patch=2,EE,000E1F20,word,0000202D // daddu a0, zero, zero
patch=2,EE,000E1F24,word,3C0A000E // lui t2, 0x000E
patch=2,EE,000E1F28,word,8D421C50 // up_one: lw v0, 0x1C50(t2)  ; slot 1
patch=2,EE,000E1F2C,word,14500003 // bne v0, s0, 0x000E1F3C
patch=2,EE,000E1F30,word,00000000 // nop
patch=2,EE,000E1F34,word,0C0385A8 // jal 0x000E16A0
patch=2,EE,000E1F38,word,24040001 // addiu a0, zero, 1
patch=2,EE,000E1F3C,word,DFBF0000 // up_out: ld ra, 0x0(sp)
patch=2,EE,000E1F40,word,7BB00010 // lq s0, 0x10(sp)
patch=2,EE,000E1F44,word,03E00008 // jr ra
patch=2,EE,000E1F48,word,27BD0020 // addiu sp, sp, 32
patch=2,EE,000E1F4C,word,27BDFFE0 // SWEEP: addiu sp, sp, -32  ; SWEEP(): release every pin whose Warrior no W4P-added player uses
patch=2,EE,000E1F50,word,FFBF0000 // sd ra, 0x0(sp)
patch=2,EE,000E1F54,word,7FB00010 // sq s0, 0x10(sp)
patch=2,EE,000E1F58,word,0000802D // daddu s0, zero, zero  ; slot 0, 1
patch=2,EE,000E1F5C,word,0C0387A0 // sw_loop: jal 0x000E1E80
patch=2,EE,000E1F60,word,0200202D // daddu a0, s0, zero
patch=2,EE,000E1F64,word,8C440000 // lw a0, 0x0(v0)  ; ID
patch=2,EE,000E1F68,word,10800007 // beq a0, zero, 0x000E1F88
patch=2,EE,000E1F6C,word,00000000 // nop
patch=2,EE,000E1F70,word,0C0387A7 // jal 0x000E1E9C
patch=2,EE,000E1F74,word,00000000 // nop
patch=2,EE,000E1F78,word,14400003 // bne v0, zero, 0x000E1F88  ; in use: keep
patch=2,EE,000E1F7C,word,00000000 // nop
patch=2,EE,000E1F80,word,0C0385A8 // jal 0x000E16A0
patch=2,EE,000E1F84,word,0200202D // daddu a0, s0, zero
patch=2,EE,000E1F88,word,26100001 // sw_next: addiu s0, s0, 1
patch=2,EE,000E1F8C,word,2A080002 // slti t0, s0, 2
patch=2,EE,000E1F90,word,1500FFF2 // bne t0, zero, 0x000E1F5C
patch=2,EE,000E1F94,word,00000000 // nop
patch=2,EE,000E1F98,word,DFBF0000 // ld ra, 0x0(sp)
patch=2,EE,000E1F9C,word,7BB00010 // lq s0, 0x10(sp)
patch=2,EE,000E1FA0,word,03E00008 // jr ra
patch=2,EE,000E1FA4,word,27BD0020 // addiu sp, sp, 32
patch=2,EE,000E1FA8,word,3C030051 // XCHK: lui v1, 0x0051  ; XCHK(HUD index) leaf: v0 = 1 if the XC table excludes this Warrior at the current level and checkpoint; keeps a0-a3
patch=2,EE,000E1FAC,word,8C63489C // lw v1, 0x489C(v1)  ; GameMgr *(0x0051489C)
patch=2,EE,000E1FB0,word,1060001B // beq v1, zero, 0x000E2020
patch=2,EE,000E1FB4,word,0000102D // daddu v0, zero, zero
patch=2,EE,000E1FB8,word,946856DC // lhu t0, 0x56DC(v1)  ; level index
patch=2,EE,000E1FBC,word,000849C0 // sll t1, t0, 7
patch=2,EE,000E1FC0,word,00084080 // sll t0, t0, 2
patch=2,EE,000E1FC4,word,01284021 // addu t0, t1, t0  ; index * 0x84
patch=2,EE,000E1FC8,word,01034021 // addu t0, t0, v1
patch=2,EE,000E1FCC,word,8D0814D8 // lw t0, 0x14D8(t0)  ; level number
patch=2,EE,000E1FD0,word,9469033A // lhu t1, 0x33A(v1)  ; checkpoint
patch=2,EE,000E1FD4,word,3C0A000E // lui t2, 0x000E
patch=2,EE,000E1FD8,word,254A1E10 // addiu t2, t2, 7696  ; XC table: byte level, byte first cp << 4 | last cp, u16 mask of HUD indices
patch=2,EE,000E1FDC,word,914B0000 // xc_loop: lbu t3, 0x0(t2)  ; level, 0 = end
patch=2,EE,000E1FE0,word,1160000F // beq t3, zero, 0x000E2020
patch=2,EE,000E1FE4,word,914C0001 // lbu t4, 0x1(t2)
patch=2,EE,000E1FE8,word,1568000B // bne t3, t0, 0x000E2018
patch=2,EE,000E1FEC,word,000C5902 // srl t3, t4, 4  ; first checkpoint
patch=2,EE,000E1FF0,word,012B582B // sltu t3, t1, t3
patch=2,EE,000E1FF4,word,15600008 // bne t3, zero, 0x000E2018  ; before the row's first checkpoint
patch=2,EE,000E1FF8,word,318C000F // andi t4, t4, 0xF  ; last checkpoint
patch=2,EE,000E1FFC,word,0189602B // sltu t4, t4, t1
patch=2,EE,000E2000,word,15800005 // bne t4, zero, 0x000E2018  ; after the row's last checkpoint
patch=2,EE,000E2004,word,00000000 // nop
patch=2,EE,000E2008,word,954B0002 // lhu t3, 0x2(t2)  ; mask
patch=2,EE,000E200C,word,008B5806 // srlv t3, t3, a0
patch=2,EE,000E2010,word,316B0001 // andi t3, t3, 0x1
patch=2,EE,000E2014,word,004B1025 // or v0, v0, t3
patch=2,EE,000E2018,word,1000FFF0 // xc_next: beq zero, zero, 0x000E1FDC
patch=2,EE,000E201C,word,254A0004 // addiu t2, t2, 4
patch=2,EE,000E2020,word,03E00008 // xc_out: jr ra
patch=2,EE,000E2024,word,00000000 // nop
patch=2,EE,000E2028,word,27BDFFF0 // GATE: addiu sp, sp, -16  ; GATE(): 1 = go, 0 = refuse this press
patch=2,EE,000E202C,word,FFBF0000 // sd ra, 0x0(sp)
patch=2,EE,000E2030,word,0C038601 // jal 0x000E1804
patch=2,EE,000E2034,word,00000000 // nop
patch=2,EE,000E2038,word,3C0A000E // lui t2, 0x000E
patch=2,EE,000E203C,word,10400008 // beq v0, zero, 0x000E2060
patch=2,EE,000E2040,word,24090001 // addiu t1, zero, 1  ; code 1: go, a Warrior is resident
patch=2,EE,000E2044,word,24030001 // addiu v1, zero, 1
patch=2,EE,000E2048,word,10430002 // beq v0, v1, 0x000E2054
patch=2,EE,000E204C,word,00000000 // nop
patch=2,EE,000E2050,word,24090002 // addiu t1, zero, 2  ; code 2: go, nothing to wait for (clone)
patch=2,EE,000E2054,word,AD491C14 // gt_go: sw t1, 0x1C14(t2)
patch=2,EE,000E2058,word,10000028 // beq zero, zero, 0x000E20FC
patch=2,EE,000E205C,word,24020001 // addiu v0, zero, 1
patch=2,EE,000E2060,word,0C0387A0 // gt_wait: jal 0x000E1E80
patch=2,EE,000E2064,word,8D441C3C // lw a0, 0x1C3C(t2)  ; EN_SLOT: the slot being loaded
patch=2,EE,000E2068,word,3C0A000E // lui t2, 0x000E
patch=2,EE,000E206C,word,3C010051 // lui at, 0x0051
patch=2,EE,000E2070,word,8C23B734 // lw v1, -0x48CC(at)  ; timer object
patch=2,EE,000E2074,word,10600009 // beq v1, zero, 0x000E209C  ; no clock: do not wait
patch=2,EE,000E2078,word,00000000 // nop
patch=2,EE,000E207C,word,8C630038 // lw v1, 0x38(v1)
patch=2,EE,000E2080,word,8C48000C // lw t0, 0xC(v0)  ; that slot's T0
patch=2,EE,000E2084,word,00681823 // subu v1, v1, t0  ; ms since the pin
patch=2,EE,000E2088,word,AD431C18 // sw v1, 0x1C18(t2)  ; GT_T
patch=2,EE,000E208C,word,8D481C40 // lw t0, 0x1C40(t2)  ; TIMEOUT_MS
patch=2,EE,000E2090,word,0068182B // sltu v1, v1, t0
patch=2,EE,000E2094,word,1460000B // bne v1, zero, 0x000E20C4
patch=2,EE,000E2098,word,00000000 // nop
patch=2,EE,000E209C,word,0C0385A8 // gt_tmo: jal 0x000E16A0  ; timed out: stop waiting; CHOOSE falls back to the clone
patch=2,EE,000E20A0,word,8D441C3C // lw a0, 0x1C3C(t2)
patch=2,EE,000E20A4,word,3C0A000E // lui t2, 0x000E
patch=2,EE,000E20A8,word,8D421C28 // lw v0, 0x1C28(t2)
patch=2,EE,000E20AC,word,24420001 // addiu v0, v0, 1
patch=2,EE,000E20B0,word,AD421C28 // sw v0, 0x1C28(t2)  ; N_TIMEOUT
patch=2,EE,000E20B4,word,24090004 // addiu t1, zero, 4  ; code 4: go after timeout (clone)
patch=2,EE,000E20B8,word,AD491C14 // sw t1, 0x1C14(t2)
patch=2,EE,000E20BC,word,1000000F // beq zero, zero, 0x000E20FC
patch=2,EE,000E20C0,word,24020001 // addiu v0, zero, 1
patch=2,EE,000E20C4,word,0C038867 // gt_refuse: jal 0x000E219C  ; still loading: re-pin it if it is older than KICK_MS (M12 first-pin stall, m6_chooser.md 2.6)
patch=2,EE,000E20C8,word,00000000 // nop
patch=2,EE,000E20CC,word,3C0A000E // lui t2, 0x000E
patch=2,EE,000E20D0,word,10400004 // beq v0, zero, 0x000E20E4
patch=2,EE,000E20D4,word,24090005 // addiu t1, zero, 5  ; code 5: go after a re-pin (the model became resident, or nothing to wait for)
patch=2,EE,000E20D8,word,AD491C14 // sw t1, 0x1C14(t2)
patch=2,EE,000E20DC,word,10000007 // beq zero, zero, 0x000E20FC
patch=2,EE,000E20E0,word,24020001 // addiu v0, zero, 1
patch=2,EE,000E20E4,word,8D421C24 // gt_ref2: lw v0, 0x1C24(t2)
patch=2,EE,000E20E8,word,24420001 // addiu v0, v0, 1
patch=2,EE,000E20EC,word,AD421C24 // sw v0, 0x1C24(t2)  ; N_REFUSE
patch=2,EE,000E20F0,word,24090003 // addiu t1, zero, 3  ; code 3: refused, model still streaming
patch=2,EE,000E20F4,word,AD491C14 // sw t1, 0x1C14(t2)
patch=2,EE,000E20F8,word,0000102D // daddu v0, zero, zero
patch=2,EE,000E20FC,word,DFBF0000 // gt_out: ld ra, 0x0(sp)
patch=2,EE,000E2100,word,03E00008 // jr ra
patch=2,EE,000E2104,word,27BD0010 // addiu sp, sp, 16
patch=2,EE,000E2108,word,27BDFFD0 // JS: addiu sp, sp, -48  ; JS(char, prio): SPAWNPICK's spawn call; s3 = count at UpdateJoin entry (2 or 3)
patch=2,EE,000E210C,word,FFBF0000 // sd ra, 0x0(sp)
patch=2,EE,000E2110,word,7FB00010 // sq s0, 0x10(sp)
patch=2,EE,000E2114,word,AFA40020 // sw a0, 0x20(sp)
patch=2,EE,000E2118,word,AFA50024 // sw a1, 0x24(sp)
patch=2,EE,000E211C,word,24020003 // addiu v0, zero, 3
patch=2,EE,000E2120,word,12620004 // beq s3, v0, 0x000E2134  ; the 4th player: gate on his model
patch=2,EE,000E2124,word,3C0A000E // lui t2, 0x000E
patch=2,EE,000E2128,word,8D421C4C // lw v0, 0x1C4C(t2)  ; OWN3 (X10): the 3rd player gets his own model too
patch=2,EE,000E212C,word,10400005 // beq v0, zero, 0x000E2144
patch=2,EE,000E2130,word,00000000 // nop
patch=2,EE,000E2134,word,0C03880A // js_gate: jal 0x000E2028
patch=2,EE,000E2138,word,00000000 // nop
patch=2,EE,000E213C,word,10400012 // beq v0, zero, 0x000E2188  ; refuse this press: v0 = 0 = nobody to join
patch=2,EE,000E2140,word,0000802D // daddu s0, zero, zero
patch=2,EE,000E2144,word,8FA40020 // js_spawn: lw a0, 0x20(sp)
patch=2,EE,000E2148,word,0C038420 // jal 0x000E1080  ; SPAWN(-1, 7) as before (CHOOSE inside)
patch=2,EE,000E214C,word,8FA50024 // lw a1, 0x24(sp)
patch=2,EE,000E2150,word,10400005 // beq v0, zero, 0x000E2168  ; spawn failed: keep the pins for the next press
patch=2,EE,000E2154,word,0040802D // daddu s0, v0, zero
patch=2,EE,000E2158,word,0C038910 // jal 0x000E2440  ; F-0195: his own free spot next to player 1
patch=2,EE,000E215C,word,0260202D // daddu a0, s3, zero
patch=2,EE,000E2160,word,0C0387D3 // jal 0x000E1F4C  ; release pins no W4P-added player uses (other Warrior chosen, or clone after a timeout)
patch=2,EE,000E2164,word,00000000 // nop
patch=2,EE,000E2168,word,24020002 // js_pre: addiu v0, zero, 2
patch=2,EE,000E216C,word,16620006 // bne s3, v0, 0x000E2188
patch=2,EE,000E2170,word,3C0A000E // lui t2, 0x000E
patch=2,EE,000E2174,word,8D421C44 // lw v0, 0x1C44(t2)  ; PRELOAD_AT3
patch=2,EE,000E2178,word,10400003 // beq v0, zero, 0x000E2188
patch=2,EE,000E217C,word,00000000 // nop
patch=2,EE,000E2180,word,0C038601 // jal 0x000E1804  ; 3rd player spawned: start the 4th player's Warrior now (second slot)
patch=2,EE,000E2184,word,00000000 // nop
patch=2,EE,000E2188,word,0200102D // js_out: daddu v0, s0, zero
patch=2,EE,000E218C,word,DFBF0000 // ld ra, 0x0(sp)
patch=2,EE,000E2190,word,7BB00010 // lq s0, 0x10(sp)
patch=2,EE,000E2194,word,03E00008 // jr ra
patch=2,EE,000E2198,word,27BD0030 // addiu sp, sp, 48
patch=2,EE,000E219C,word,27BDFFE0 // KICK: addiu sp, sp, -32  ; KICK(): refused press, pin EN_SLOT still loading: if KICK_MS != 0, the pin is at least KICK_MS old and the last re-pin at least KICK_MS ago, release and pin again (ENSURE) keeping the first T0; v0 = ENSURE's result (1/2 = go), 0 = refuse
patch=2,EE,000E21A0,word,FFBF0000 // sd ra, 0x0(sp)
patch=2,EE,000E21A4,word,7FB00010 // sq s0, 0x10(sp)
patch=2,EE,000E21A8,word,3C0A000E // lui t2, 0x000E
patch=2,EE,000E21AC,word,8D482300 // lw t0, 0x2300(t2)  ; KICK_MS (config, 0 = off)
patch=2,EE,000E21B0,word,1100001E // beq t0, zero, 0x000E222C
patch=2,EE,000E21B4,word,3C010051 // lui at, 0x0051
patch=2,EE,000E21B8,word,8C23B734 // lw v1, -0x48CC(at)  ; timer object *(0x0050B734)
patch=2,EE,000E21BC,word,1060001B // beq v1, zero, 0x000E222C
patch=2,EE,000E21C0,word,00000000 // nop
patch=2,EE,000E21C4,word,8C630038 // lw v1, 0x38(v1)  ; game clock (ms)
patch=2,EE,000E21C8,word,8D492304 // lw t1, 0x2304(t2)  ; KICK_T: clock of the last re-pin
patch=2,EE,000E21CC,word,00694823 // subu t1, v1, t1
patch=2,EE,000E21D0,word,0128482B // sltu t1, t1, t0
patch=2,EE,000E21D4,word,15200015 // bne t1, zero, 0x000E222C  ; re-pinned less than KICK_MS ago
patch=2,EE,000E21D8,word,8D491C18 // lw t1, 0x1C18(t2)  ; GT_T: ms since this pin (GATE stored it just before)
patch=2,EE,000E21DC,word,0128482B // sltu t1, t1, t0
patch=2,EE,000E21E0,word,15200012 // bne t1, zero, 0x000E222C  ; pin younger than KICK_MS
patch=2,EE,000E21E4,word,00000000 // nop
patch=2,EE,000E21E8,word,AD432304 // sw v1, 0x2304(t2)  ; KICK_T = now
patch=2,EE,000E21EC,word,8D422308 // lw v0, 0x2308(t2)
patch=2,EE,000E21F0,word,24420001 // addiu v0, v0, 1
patch=2,EE,000E21F4,word,AD422308 // sw v0, 0x2308(t2)  ; N_KICK
patch=2,EE,000E21F8,word,0C0387A0 // jal 0x000E1E80
patch=2,EE,000E21FC,word,8D441C3C // lw a0, 0x1C3C(t2)  ; EN_SLOT
patch=2,EE,000E2200,word,8C50000C // lw s0, 0xC(v0)  ; first T0 of this pin: the timeout keeps counting from it
patch=2,EE,000E2204,word,3C0A000E // lui t2, 0x000E
patch=2,EE,000E2208,word,0C0385A8 // jal 0x000E16A0  ; unpin
patch=2,EE,000E220C,word,8D441C3C // lw a0, 0x1C3C(t2)
patch=2,EE,000E2210,word,0C038601 // jal 0x000E1804  ; pin again (resident now -> 1; else a new pin and POKE -> 0)
patch=2,EE,000E2214,word,00000000 // nop
patch=2,EE,000E2218,word,14400005 // bne v0, zero, 0x000E2230  ; 1 or 2: GATE lets this press join
patch=2,EE,000E221C,word,3C0A000E // lui t2, 0x000E
patch=2,EE,000E2220,word,0C0387A0 // jal 0x000E1E80
patch=2,EE,000E2224,word,8D441C3C // lw a0, 0x1C3C(t2)  ; the slot ENSURE pinned into
patch=2,EE,000E2228,word,AC50000C // sw s0, 0xC(v0)  ; keep the first T0 (bounded wait: TIMEOUT_MS from the first pin)
patch=2,EE,000E222C,word,0000102D // kk_no: daddu v0, zero, zero
patch=2,EE,000E2230,word,DFBF0000 // kk_out: ld ra, 0x0(sp)
patch=2,EE,000E2234,word,7BB00010 // lq s0, 0x10(sp)
patch=2,EE,000E2238,word,03E00008 // jr ra
patch=2,EE,000E223C,word,27BD0020 // addiu sp, sp, 32
// KICK data (m6_chooser.md 2.6): a refused join press whose pin is at least KICK_MS old (and the last re-pin at least
// KICK_MS ago) releases and pins that Warrior again; the timeout still counts from the first pin.
patch=0,EE,000E2300,word,00000000 // KICK_MS: config: re-pin a stalled pin after this many ms (0 = off, default: off - tested, did not help in M12; PINSVC below fixes the stall) (startup only)
patch=0,EE,000E2304,word,00000000 // KICK_T: game clock (ms) of the last re-pin (startup only)
patch=0,EE,000E2308,word,00000000 // N_KICK: re-pins made (startup only)
patch=0,EE,000E230C,word,00000000 // SVC_T: game clock (ms) of the last pin service (startup only)
patch=0,EE,000E2310,word,00000000 // N_FIX: pin instances built by PINFIX (startup only)
patch=0,EE,000E2314,word,00000000 // N_PLACE: spawned Warriors moved by HuTeleportNearHuman (PLACE) (startup only)
patch=0,EE,000E2318,word,00000000 // N_PLACE_FB: spawned Warriors put at player 1 +/- 1.5 units (no free spot) (startup only)
// PINSVC/PINFIX (m6_chooser.md 2.6, M12 runs chs_m12d/chs_m12k): a pinned model whose three parts arrive is
// unreferenced until the streamer builds the pin's instance, and the scheduler does not call the streamer for pins
// alone (H1), so busy levels evict the parts again (LRU). Once per frame (game-clock tick) PINFIX builds the missing
// instance of our pins as soon as the model is resident (the streamer's own call FUN_00177B80).
patch=2,EE,000E2320,word,27BDFFF0 // PINSVC: addiu sp, sp, -16  ; PINSVC(f12, dict, human): replaces the human update's model request call 0x0023D6BC (FUN_0018A430, every human every frame)
patch=2,EE,000E2324,word,FFBF0000 // sd ra, 0x0(sp)
patch=2,EE,000E2328,word,0C06290C // jal 0x0018A430  ; the replaced call (f12, a0, a1 unchanged; it returns nothing)
patch=2,EE,000E232C,word,00000000 // nop
patch=2,EE,000E2330,word,3C010051 // lui at, 0x0051
patch=2,EE,000E2334,word,8C23B734 // lw v1, -0x48CC(at)  ; timer object *(0x0050B734)
patch=2,EE,000E2338,word,1060000B // beq v1, zero, 0x000E2368
patch=2,EE,000E233C,word,3C0A000E // lui t2, 0x000E
patch=2,EE,000E2340,word,8C630038 // lw v1, 0x38(v1)  ; game clock (ms)
patch=2,EE,000E2344,word,8D48230C // lw t0, 0x230C(t2)  ; SVC_T: clock of the last service
patch=2,EE,000E2348,word,10680007 // beq v1, t0, 0x000E2368  ; once per clock value (per frame), not per human
patch=2,EE,000E234C,word,8D481C00 // lw t0, 0x1C00(t2)  ; slot 0 ID
patch=2,EE,000E2350,word,8D491C50 // lw t1, 0x1C50(t2)  ; slot 1 ID
patch=2,EE,000E2354,word,01094025 // or t0, t0, t1
patch=2,EE,000E2358,word,11000003 // beq t0, zero, 0x000E2368  ; no pin of ours
patch=2,EE,000E235C,word,AD43230C // sw v1, 0x230C(t2)  ; SVC_T = now
patch=2,EE,000E2360,word,0C0388DD // jal 0x000E2374
patch=2,EE,000E2364,word,00000000 // nop
patch=2,EE,000E2368,word,DFBF0000 // ps_out: ld ra, 0x0(sp)
patch=2,EE,000E236C,word,03E00008 // jr ra
patch=2,EE,000E2370,word,27BD0010 // addiu sp, sp, 16
patch=2,EE,000E2374,word,27BDFFC0 // PINFIX: addiu sp, sp, -64  ; PINFIX(): for each pin slot whose pin-list entry has no instance: if its model is resident, build the instance as the streamer does (FUN_00177B80), so the loaded data is referenced before LRU eviction removes it again
patch=2,EE,000E2378,word,FFBF0000 // sd ra, 0x0(sp)
patch=2,EE,000E237C,word,7FB00010 // sq s0, 0x10(sp)
patch=2,EE,000E2380,word,7FB10020 // sq s1, 0x20(sp)
patch=2,EE,000E2384,word,0000802D // daddu s0, zero, zero  ; pin slot 0, 1
patch=2,EE,000E2388,word,0C0387A0 // pf_loop: jal 0x000E1E80
patch=2,EE,000E238C,word,0200202D // daddu a0, s0, zero
patch=2,EE,000E2390,word,8C480000 // lw t0, 0x0(v0)  ; ID
patch=2,EE,000E2394,word,11000021 // beq t0, zero, 0x000E241C
patch=2,EE,000E2398,word,8C450008 // lw a1, 0x8(v0)  ; MI
patch=2,EE,000E239C,word,3C010051 // lui at, 0x0051
patch=2,EE,000E23A0,word,8C24CD4C // lw a0, -0x32B4(at)  ; dict *(0x0050CD4C)
patch=2,EE,000E23A4,word,10800021 // beq a0, zero, 0x000E242C
patch=2,EE,000E23A8,word,249100B4 // addiu s1, a0, 180  ; pin list dict+0xB4, stride 8
patch=2,EE,000E23AC,word,24090020 // addiu t1, zero, 32
patch=2,EE,000E23B0,word,8E2A0000 // pf_find: lw t2, 0x0(s1)
patch=2,EE,000E23B4,word,11450005 // beq t2, a1, 0x000E23CC
patch=2,EE,000E23B8,word,2529FFFF // addiu t1, t1, -1
patch=2,EE,000E23BC,word,1520FFFC // bne t1, zero, 0x000E23B0
patch=2,EE,000E23C0,word,26310008 // addiu s1, s1, 8
patch=2,EE,000E23C4,word,10000015 // beq zero, zero, 0x000E241C  ; not in the list (ENSURE forgets it at the next join)
patch=2,EE,000E23C8,word,00000000 // nop
patch=2,EE,000E23CC,word,8E2A0004 // pf_hit: lw t2, 0x4(s1)  ; instance
patch=2,EE,000E23D0,word,15400012 // bne t2, zero, 0x000E241C  ; built already
patch=2,EE,000E23D4,word,8C8B0088 // lw t3, 0x88(a0)  ; dictionary entries
patch=2,EE,000E23D8,word,00056140 // sll t4, a1, 5
patch=2,EE,000E23DC,word,016C2821 // addu a1, t3, t4  ; entry = FUN_001780D8(dict, mi)
patch=2,EE,000E23E0,word,AFA50030 // sw a1, 0x30(sp)
patch=2,EE,000E23E4,word,0000302D // daddu a2, zero, zero
patch=2,EE,000E23E8,word,0C05DD34 // jal 0x001774D0  ; all three parts resident? (the streamer's and CHOOSE's test)
patch=2,EE,000E23EC,word,0000382D // daddu a3, zero, zero
patch=2,EE,000E23F0,word,1040000A // beq v0, zero, 0x000E241C  ; still loading
patch=2,EE,000E23F4,word,3C010051 // lui at, 0x0051
patch=2,EE,000E23F8,word,8C24CD4C // lw a0, -0x32B4(at)  ; dict
patch=2,EE,000E23FC,word,8FA50030 // lw a1, 0x30(sp)
patch=2,EE,000E2400,word,0C05DEE0 // jal 0x00177B80  ; instance (the streamer's own call for a resident pin)
patch=2,EE,000E2404,word,0000302D // daddu a2, zero, zero
patch=2,EE,000E2408,word,AE220004 // sw v0, 0x4(s1)  ; pin-list entry instance: the model data is referenced from now on
patch=2,EE,000E240C,word,3C0A000E // lui t2, 0x000E
patch=2,EE,000E2410,word,8D432310 // lw v1, 0x2310(t2)
patch=2,EE,000E2414,word,24630001 // addiu v1, v1, 1
patch=2,EE,000E2418,word,AD432310 // sw v1, 0x2310(t2)  ; N_FIX
patch=2,EE,000E241C,word,26100001 // pf_next: addiu s0, s0, 1
patch=2,EE,000E2420,word,2A080002 // slti t0, s0, 2
patch=2,EE,000E2424,word,1500FFD8 // bne t0, zero, 0x000E2388
patch=2,EE,000E2428,word,00000000 // nop
patch=2,EE,000E242C,word,DFBF0000 // pf_out: ld ra, 0x0(sp)
patch=2,EE,000E2430,word,7BB00010 // lq s0, 0x10(sp)
patch=2,EE,000E2434,word,7BB10020 // lq s1, 0x20(sp)
patch=2,EE,000E2438,word,03E00008 // jr ra
patch=2,EE,000E243C,word,27BD0040 // addiu sp, sp, 64
// PLACE (F-0195, m6_chooser.md 2.7): after JS spawned a Warrior (4 units beside player 1), HuTeleportNearHuman core
// FUN_0023B138(new, player 1) picks a free spot 3.6 units from player 1 (32 directions from a clock-based start, ray test
// against walls, other humans avoided) - the call the levels' player-2 join callbacks use. If it does not move him
// (no free spot), the Lua Teleport core puts him at player 1 + 1.5 (3rd player) or - 1.5 (4th player) units in x.
patch=2,EE,000E2440,word,27BDFFA0 // PLACE: addiu sp, sp, -96  ; PLACE(count at UpdateJoin entry): move the Warrior SPAWN just created (handle 0x000E1210; SPAWN now creates him 4 units beside player 1) with the game's HuTeleportNearHuman core
patch=2,EE,000E2444,word,FFBF0000 // sd ra, 0x0(sp)
patch=2,EE,000E2448,word,7FB00010 // sq s0, 0x10(sp)
patch=2,EE,000E244C,word,7FB10020 // sq s1, 0x20(sp)
patch=2,EE,000E2450,word,7FB20030 // sq s2, 0x30(sp)
patch=2,EE,000E2454,word,0080902D // daddu s2, a0, zero  ; 2 = the 3rd player, 3 = the 4th
patch=2,EE,000E2458,word,3C08000E // lui t0, 0x000E
patch=2,EE,000E245C,word,8D101210 // lw s0, 0x1210(t0)  ; handle of the Warrior just spawned
patch=2,EE,000E2460,word,3C020051 // lui v0, 0x0051
patch=2,EE,000E2464,word,8C49489C // lw t1, 0x489C(v0)  ; GameMgr
patch=2,EE,000E2468,word,8D310228 // lw s1, 0x228(t1)  ; player 1's handle
patch=2,EE,000E246C,word,AFB00040 // sw s0, 0x40(sp)
patch=2,EE,000E2470,word,0C0E409A // jal 0x00390268  ; his human
patch=2,EE,000E2474,word,27A40040 // addiu a0, sp, 64
patch=2,EE,000E2478,word,10400033 // beq v0, zero, 0x000E2548
patch=2,EE,000E247C,word,00000000 // nop
patch=2,EE,000E2480,word,0C038958 // jal 0x000E2560  ; v0 = x word of human+0x10, v1 = x word of his position-table entry (0x00714B00 + 0x20 * human+0x92)
patch=2,EE,000E2484,word,0040202D // daddu a0, v0, zero
patch=2,EE,000E2488,word,AFA20044 // sw v0, 0x44(sp)
patch=2,EE,000E248C,word,AFA30048 // sw v1, 0x48(sp)
patch=2,EE,000E2490,word,0200202D // daddu a0, s0, zero
patch=2,EE,000E2494,word,0C08EC4E // jal 0x0023B138  ; HuTeleportNearHuman core (mover, target): 32 directions at 3.6 units, wall ray test, other humans avoided
patch=2,EE,000E2498,word,0220282D // daddu a1, s1, zero
patch=2,EE,000E249C,word,0C0E409A // jal 0x00390268
patch=2,EE,000E24A0,word,27A40040 // addiu a0, sp, 64
patch=2,EE,000E24A4,word,10400028 // beq v0, zero, 0x000E2548
patch=2,EE,000E24A8,word,00000000 // nop
patch=2,EE,000E24AC,word,0C038958 // jal 0x000E2560
patch=2,EE,000E24B0,word,0040202D // daddu a0, v0, zero
patch=2,EE,000E24B4,word,8FA80044 // lw t0, 0x44(sp)
patch=2,EE,000E24B8,word,1448001F // bne v0, t0, 0x000E2538  ; either copy of his x changed: he was moved to a free spot
patch=2,EE,000E24BC,word,8FA80048 // lw t0, 0x48(sp)
patch=2,EE,000E24C0,word,1468001D // bne v1, t0, 0x000E2538
patch=2,EE,000E24C4,word,00000000 // nop
patch=2,EE,000E24C8,word,AFB10040 // sw s1, 0x40(sp)  ; no free spot: player 1's position + 1.5 (3rd player) or - 1.5 (4th) in x (the old offset)
patch=2,EE,000E24CC,word,0C0E409A // jal 0x00390268  ; player 1's human
patch=2,EE,000E24D0,word,27A40040 // addiu a0, sp, 64
patch=2,EE,000E24D4,word,1040001C // beq v0, zero, 0x000E2548
patch=2,EE,000E24D8,word,3C013FC0 // lui at, 0x3FC0  ; 1.5f
patch=2,EE,000E24DC,word,44810800 // mtc1 at, f1
patch=2,EE,000E24E0,word,C4400010 // lwc1 f0, 0x10(v0)
patch=2,EE,000E24E4,word,24080002 // addiu t0, zero, 2
patch=2,EE,000E24E8,word,12480004 // beq s2, t0, 0x000E24FC
patch=2,EE,000E24EC,word,00000000 // nop
patch=2,EE,000E24F0,word,46010001 // sub.s f0, f0, f1
patch=2,EE,000E24F4,word,10000002 // beq zero, zero, 0x000E2500
patch=2,EE,000E24F8,word,00000000 // nop
patch=2,EE,000E24FC,word,46010000 // pl_plus: add.s f0, f0, f1
patch=2,EE,000E2500,word,E7A00050 // pl_set: swc1 f0, 0x50(sp)
patch=2,EE,000E2504,word,8C480014 // lw t0, 0x14(v0)
patch=2,EE,000E2508,word,AFA80054 // sw t0, 0x54(sp)
patch=2,EE,000E250C,word,8C480018 // lw t0, 0x18(v0)
patch=2,EE,000E2510,word,AFA80058 // sw t0, 0x58(sp)
patch=2,EE,000E2514,word,0200202D // daddu a0, s0, zero
patch=2,EE,000E2518,word,27A50050 // addiu a1, sp, 80
patch=2,EE,000E251C,word,0C0E16EE // jal 0x00385BB8  ; Lua Teleport core (handle, float[3]*, -1)
patch=2,EE,000E2520,word,2406FFFF // addiu a2, zero, -1
patch=2,EE,000E2524,word,3C0A000E // lui t2, 0x000E
patch=2,EE,000E2528,word,8D432318 // lw v1, 0x2318(t2)
patch=2,EE,000E252C,word,24630001 // addiu v1, v1, 1
patch=2,EE,000E2530,word,10000005 // beq zero, zero, 0x000E2548
patch=2,EE,000E2534,word,AD432318 // sw v1, 0x2318(t2)  ; N_PLACE_FB
patch=2,EE,000E2538,word,3C0A000E // pl_moved: lui t2, 0x000E
patch=2,EE,000E253C,word,8D432314 // lw v1, 0x2314(t2)
patch=2,EE,000E2540,word,24630001 // addiu v1, v1, 1
patch=2,EE,000E2544,word,AD432314 // sw v1, 0x2314(t2)  ; N_PLACE
patch=2,EE,000E2548,word,DFBF0000 // pl_out: ld ra, 0x0(sp)
patch=2,EE,000E254C,word,7BB00010 // lq s0, 0x10(sp)
patch=2,EE,000E2550,word,7BB10020 // lq s1, 0x20(sp)
patch=2,EE,000E2554,word,7BB20030 // lq s2, 0x30(sp)
patch=2,EE,000E2558,word,03E00008 // jr ra
patch=2,EE,000E255C,word,27BD0060 // addiu sp, sp, 96
patch=2,EE,000E2560,word,8C820010 // PLPOS: lw v0, 0x10(a0)  ; PLPOS(human) leaf: v0 = x word at human+0x10, v1 = x word of his position-table entry
patch=2,EE,000E2564,word,84880092 // lh t0, 0x92(a0)
patch=2,EE,000E2568,word,00084140 // sll t0, t0, 5
patch=2,EE,000E256C,word,3C090071 // lui t1, 0x0071
patch=2,EE,000E2570,word,25294B00 // addiu t1, t1, 19200  ; position table 0x00714B00 (the one FUN_0023B138 reads)
patch=2,EE,000E2574,word,01094021 // addu t0, t0, t1
patch=2,EE,000E2578,word,03E00008 // jr ra
patch=2,EE,000E257C,word,8D030000 // lw v1, 0x0(t0)
```

### `mod/m2/missions.txt` (`[warriors-4p missions]`, as committed in 336c6a4): REL34, X3W's LEAVE call, X7J, X7 bytes comment, LVOWE
```
// X7 (b) (m6_chooser.md): LVOWE(index) = LEAVE for a script-forced leave (X1, X3); if the player got the starting items in
//    this level load (given byte 1), the byte becomes 2 = owed, and X7J gives them again at his next join, at any
//    checkpoint (the forced release emptied his inventory slot). Normal leaves keep byte 1: no second gift.
// Free RAM used: 0x000E7400-0x000E7BFF (code, data, LUACH log) and 0x000E7E00-0x000E7F7F (LUACH table and row data); 0x000E7C00-0x000E7DFF is a test-only Lua string buffer (written over PINE by tests/m2/x4x6_probe.py, not in the pnach).
patch=2,EE,000E7400,word,27BDFFE0 // REL34: addiu sp, sp, -32  ; REL34(human): release player 3/4 (index >= 2) with LEAVE before a script deletes him
patch=2,EE,000E7404,word,FFBF0000 // sd ra, 0x0(sp)
patch=2,EE,000E7408,word,7FB00010 // sq s0, 0x10(sp)
patch=2,EE,000E740C,word,0080802D // daddu s0, a0, zero
patch=2,EE,000E7410,word,820401B0 // lb a0, 0x1B0(s0)  ; player index (-1 = AI)
patch=2,EE,000E7414,word,28880002 // slti t0, a0, 2
patch=2,EE,000E7418,word,1500000B // bne t0, zero, 0x000E7448  ; AI, player 1 or player 2: nothing to do
patch=2,EE,000E741C,word,0000102D // daddu v0, zero, zero
patch=2,EE,000E7420,word,920801B1 // lbu t0, 0x1B1(s0)  ; join priority; 7 = Warrior added by W4P (SPAWN)
patch=2,EE,000E7424,word,24090007 // addiu t1, zero, 7
patch=2,EE,000E7428,word,15090005 // bne t0, t1, 0x000E7440
patch=2,EE,000E742C,word,00000000 // nop
patch=2,EE,000E7430,word,A20001B1 // sb zero, 0x1B1(s0)  ; added Warrior: clear the marker so LEAVE's LV does not delete him too (the caller deletes)
patch=2,EE,000E7434,word,0C0387BA // jal 0x000E1EE8  ; UNPIN(char id): his model pin is released unless another W4P-added Warrior uses that Warrior
patch=2,EE,000E7438,word,8E0400D0 // lw a0, 0xD0(s0)
patch=2,EE,000E743C,word,820401B0 // lb a0, 0x1B0(s0)  ; index again for LEAVE
patch=2,EE,000E7440,word,0C039DE4 // r34_leave: jal 0x000E7790  ; LVOWE(index): LEAVE + X7 starting items owed again
patch=2,EE,000E7444,word,00000000 // nop
patch=2,EE,000E7448,word,DFBF0000 // r34_out: ld ra, 0x0(sp)
patch=2,EE,000E744C,word,7BB00010 // lq s0, 0x10(sp)
patch=2,EE,000E7450,word,03E00008 // jr ra
patch=2,EE,000E7454,word,27BD0020 // addiu sp, sp, 32
patch=2,EE,000E75EC,word,0C039DE4 // jal 0x000E7790  ; LVOWE(count-1): LEAVE the last index first (nobody moves down); X7 items owed again
patch=2,EE,000E7640,word,27BDFFD0 // X7J: addiu sp, sp, -48  ; X7J(GameMgr, human, 1): replaces UpdateJoin's call of the join event FUN_0041B148 (0x0041A5C0)
patch=2,EE,000E7644,word,FFBF0000 // sd ra, 0x0(sp)
patch=2,EE,000E7648,word,7FB00010 // sq s0, 0x10(sp)
patch=2,EE,000E764C,word,7FB10020 // sq s1, 0x20(sp)
patch=2,EE,000E7650,word,0C106C52 // jal 0x0041B148  ; the replaced call (guard 0x0041B180: no Lua event for index >= 2)
patch=2,EE,000E7654,word,00A0802D // daddu s0, a1, zero  ; joining human
patch=2,EE,000E7658,word,820801B0 // lb t0, 0x1B0(s0)  ; player index
patch=2,EE,000E765C,word,29080002 // slti t0, t0, 2
patch=2,EE,000E7660,word,1500002F // bne t0, zero, 0x000E7720  ; players 1-2: Lua SetupLevelInventory / InventoryPlayer2 (WAD 4106 main_150/152)
patch=2,EE,000E7664,word,8E090380 // lw t1, 0x380(s0)  ; HUD slot = inventory slot (2/3 with [4p hud B1])
patch=2,EE,000E7668,word,252AFFFE // addiu t2, t1, -2
patch=2,EE,000E766C,word,2D4A0002 // sltiu t2, t2, 2
patch=2,EE,000E7670,word,1140002B // beq t2, zero, 0x000E7720
patch=2,EE,000E7674,word,3C020051 // lui v0, 0x0051
patch=2,EE,000E7678,word,8C4B489C // lw t3, 0x489C(v0)  ; GameMgr
patch=2,EE,000E767C,word,3C0D000E // lui t5, 0x000E
patch=2,EE,000E7680,word,01A96821 // addu t5, t5, t1
patch=2,EE,000E7684,word,91AE7780 // lbu t6, 0x7780(t5)  ; given byte of this slot: 0 not yet, 1 given in this level load, 2 owed after a forced leave (LVOWE)
patch=2,EE,000E7688,word,240F0002 // addiu t7, zero, 2
patch=2,EE,000E768C,word,11CF0005 // beq t6, t7, 0x000E76A4  ; owed: give them again, at any checkpoint
patch=2,EE,000E7690,word,956C033A // lhu t4, 0x33A(t3)  ; checkpoint
patch=2,EE,000E7694,word,15C00022 // bne t6, zero, 0x000E7720  ; already given in this level load (SetPlayer2Inventory = nil): no second gift
patch=2,EE,000E7698,word,2D8C0002 // sltiu t4, t4, 2
patch=2,EE,000E769C,word,11800020 // beq t4, zero, 0x000E7720  ; like main_150/152: checkpoint 0 or 1 only
patch=2,EE,000E76A0,word,00000000 // nop
patch=2,EE,000E76A4,word,240E0001 // x7_give: addiu t6, zero, 1
patch=2,EE,000E76A8,word,A1AE7780 // sb t6, 0x7780(t5)
patch=2,EE,000E76AC,word,956F56DC // lhu t7, 0x56DC(t3)  ; level index
patch=2,EE,000E76B0,word,000FC1C0 // sll t8, t7, 7
patch=2,EE,000E76B4,word,000FC880 // sll t9, t7, 2
patch=2,EE,000E76B8,word,03197821 // addu t7, t8, t9
patch=2,EE,000E76BC,word,01EB7821 // addu t7, t7, t3
patch=2,EE,000E76C0,word,8DEF14D8 // lw t7, 0x14D8(t7)  ; level number
patch=2,EE,000E76C4,word,3C11000E // lui s1, 0x000E
patch=2,EE,000E76C8,word,26317760 // addiu s1, s1, 30560
patch=2,EE,000E76CC,word,92380000 // x7_tab: lbu t8, 0x0(s1)  ; row: level, Flash, spray, money (0 = end)
patch=2,EE,000E76D0,word,13000013 // beq t8, zero, 0x000E7720
patch=2,EE,000E76D4,word,00000000 // nop
patch=2,EE,000E76D8,word,170FFFFC // bne t8, t7, 0x000E76CC
patch=2,EE,000E76DC,word,26310004 // addiu s1, s1, 4  ; next row (on a match s1 = row + 4)
patch=2,EE,000E76E0,word,25300001 // addiu s0, t1, 1  ; player number = slot + 1 (Lua-style wrappers use p - 1)
patch=2,EE,000E76E4,word,9224FFFD // lbu a0, -0x3(s1)
patch=2,EE,000E76E8,word,10800003 // beq a0, zero, 0x000E76F8
patch=2,EE,000E76EC,word,00000000 // nop
patch=2,EE,000E76F0,word,0C107B6E // jal 0x0041EDB8  ; FUN_0041EDB8 InvGiveRevive(n, p)
patch=2,EE,000E76F4,word,0200282D // daddu a1, s0, zero
patch=2,EE,000E76F8,word,9224FFFE // x7_paint: lbu a0, -0x2(s1)
patch=2,EE,000E76FC,word,10800003 // beq a0, zero, 0x000E770C
patch=2,EE,000E7700,word,00000000 // nop
patch=2,EE,000E7704,word,0C107C0C // jal 0x0041F030  ; FUN_0041F030 InvSetSpraycanCharges(n, p)
patch=2,EE,000E7708,word,0200282D // daddu a1, s0, zero
patch=2,EE,000E770C,word,9224FFFF // x7_money: lbu a0, -0x1(s1)
patch=2,EE,000E7710,word,10800003 // beq a0, zero, 0x000E7720
patch=2,EE,000E7714,word,00000000 // nop
patch=2,EE,000E7718,word,0C107BAE // jal 0x0041EEB8  ; FUN_0041EEB8 InvSetMoney(n, p)
patch=2,EE,000E771C,word,0200282D // daddu a1, s0, zero
patch=2,EE,000E7720,word,DFBF0000 // x7_out: ld ra, 0x0(sp)
patch=2,EE,000E7724,word,7BB00010 // lq s0, 0x10(sp)
patch=2,EE,000E7728,word,7BB10020 // lq s1, 0x20(sp)
patch=2,EE,000E772C,word,03E00008 // jr ra
patch=2,EE,000E7730,word,27BD0030 // addiu sp, sp, 48
patch=0,EE,000E7780,word,00000000 // X7 given flags, byte per HUD slot (+2, +3): 0 not yet, 1 given, 2 owed (LVOWE); cleared by X7R at every level load (startup only)
patch=2,EE,000E7790,word,27BDFFE0 // LVOWE: addiu sp, sp, -32  ; LVOWE(index): LEAVE(index) for a script-forced leave (X1 REL34, X3W); returns LEAVE's v0
patch=2,EE,000E7794,word,FFBF0000 // sd ra, 0x0(sp)
patch=2,EE,000E7798,word,7FB00010 // sq s0, 0x10(sp)
patch=2,EE,000E779C,word,0080802D // daddu s0, a0, zero  ; index
patch=2,EE,000E77A0,word,3C020051 // lui v0, 0x0051
patch=2,EE,000E77A4,word,8C42489C // lw v0, 0x489C(v0)  ; GameMgr
patch=2,EE,000E77A8,word,00104080 // sll t0, s0, 2
patch=2,EE,000E77AC,word,01024021 // addu t0, t0, v0
patch=2,EE,000E77B0,word,0C0E409A // jal 0x00390268  ; his human (GameMgr+0x228+4*index) or 0
patch=2,EE,000E77B4,word,25040228 // addiu a0, t0, 552
patch=2,EE,000E77B8,word,10400002 // beq v0, zero, 0x000E77C4
patch=2,EE,000E77BC,word,2408FFFF // addiu t0, zero, -1  ; no human: no X7 byte
patch=2,EE,000E77C0,word,8C480380 // lw t0, 0x380(v0)  ; HUD slot = inventory slot, read before the release
patch=2,EE,000E77C4,word,AFA80008 // lo_leave: sw t0, 0x8(sp)
patch=2,EE,000E77C8,word,0C039C40 // jal 0x000E7100  ; LEAVE(index): release, cameras, pad owners, layout (session group)
patch=2,EE,000E77CC,word,0200202D // daddu a0, s0, zero
patch=2,EE,000E77D0,word,24080001 // addiu t0, zero, 1
patch=2,EE,000E77D4,word,1448000B // bne v0, t0, 0x000E7804  ; not released: nothing owed
patch=2,EE,000E77D8,word,8FA80008 // lw t0, 0x8(sp)
patch=2,EE,000E77DC,word,2509FFFE // addiu t1, t0, -2
patch=2,EE,000E77E0,word,2D290002 // sltiu t1, t1, 2
patch=2,EE,000E77E4,word,11200007 // beq t1, zero, 0x000E7804  ; HUD slot 2/3 only (X7 bytes 0x000E7782/83)
patch=2,EE,000E77E8,word,3C0A000E // lui t2, 0x000E
patch=2,EE,000E77EC,word,01485021 // addu t2, t2, t0
patch=2,EE,000E77F0,word,914B7780 // lbu t3, 0x7780(t2)
patch=2,EE,000E77F4,word,240C0001 // addiu t4, zero, 1
patch=2,EE,000E77F8,word,156C0002 // bne t3, t4, 0x000E7804  ; he did not get the starting items in this level load: nothing owed
patch=2,EE,000E77FC,word,240C0002 // addiu t4, zero, 2
patch=2,EE,000E7800,word,A14C7780 // sb t4, 0x7780(t2)  ; X7(b): 2 = owed, X7J gives them again at his re-join (the release emptied his slot)
patch=2,EE,000E7804,word,DFBF0000 // lo_out: ld ra, 0x0(sp)
patch=2,EE,000E7808,word,7BB00010 // lq s0, 0x10(sp)
patch=2,EE,000E780C,word,03E00008 // jr ra
patch=2,EE,000E7810,word,27BD0020 // addiu sp, sp, 32
```

## 5. Tests (SINGLE-PC, one instance each, scripted bots, no impairment)
Common: `python -I tests/m2/nav_probe.py <tag> <p1 script> --inst N --players 4 --script2 tests/m2/nav/p2_join.txt
--script3 local/m6/start_p3.txt --script4 local/m6/start_p4.txt --groups "<groups as in m6_fixes.md>" --patch
local/m6/ch1.pnach --ini EmuCore/Speedhacks/vuThread=false --callat "4000:0041ABC0:<cp>,4010:00160D78:<0x01FD996C +
(mission-1)*0x84>"` (instances 10-12; `start_p3/p4` press Start every 300 polls from 7000/7150 = join and re-join,
standing in for W4P X11). Probes: `tests/m2/chooser_probe.py` (new; `state`, `brief` read-only; test aids `x2_fox_row_off`,
`tele_cut2`, `tele_arrive` from `m6fix_probe.py`), `tests/m2/extra_survey.py` `survey_mem` (model pool; now also reads
slot 1). Results: `local/m2/<tag>/probes.json`, console `local/m6/<tag>_console.txt`, emulator log copied to
`local/m2/<tag>/emulog.txt`. Builds: runs started before 03:12 used fork build w4p-m5-1, later runs the rebuilt w4p-m6-1 (coordinator; no SessionPolicies in these runs, so X11/X12 are inactive). PINE timeouts while the level loads (`errors` in probes.json,
"PINE error code 255") are the usual loading-time errors; every probe listed below returned data.

| Tag (build) | Setup | What was done | Result | Label |
|---|---|---|---|---|
| chs_m13fox (w4p-m5-1) | M13 cp1 (entry 0x01FD9F9C), P1 `local/m6/x1_p1.txt`; test aid `x2_fox_row_off` at 6000 (X2's level9 Fox row off, so player 3 takes Fox as in m6x1b; the XC table is separate and stays on) | joins; 9200 `tele_cut2`, 9600 `tele_arrive` -> trainyard scene -> `ch1.StartTheLevel` -> script `HuDelete(fox)`; Start every 300 polls (re-join); 760 s | **8800**: P3 = Fox (companion, char 22, prio 3, HUD slot 2), P4 = W4P Swan (char 5, marker 7) with slot 0 = Swan pinned (instance 0xC45C00); X7 bytes 1/1, spray 6/6. **9800**: count 3, Swan moved to index 2 (HUD slot 3, pad 1 -> 2), slot 2's X7 byte **2 (owed)**, spray of slot 2 = 0 (forced release). **9900**: re-join press refused (GATE 3); CHOOSE statuses Swan 4, **Fox 6** (Fox's model is resident: survey 11000), Snow/Rembrandt 4, others 3 -> clone; ENSURE pinned **Ajax in slot 1**, slot 0 Swan kept. **10200**: P3 re-joined as **Ajax** (char 11, marker 7, HUD slot 2, +0xD8 0xCFF800), **spray of slot 2 = 6 again**, byte 1. To the end (poll 21406; game clock 147.8 s at 11000, 428.2 s at 19400 = **280 s after the re-join, 5.4 min after Fox's deletion**): both pins in the game's pin list with instances (0xC45C00 Swan, 0xCFE400 Ajax), both players' +0xD8 unchanged, N_RELEASE 0, count 4, views 4; **0 TLB misses** | **VERIFIED** problems 1, 3 and 4 (X7 b) in M13 |
| chs_m12 (w4p-m5-1) | M12 cp1 (entry 0x01FD9F18), P1 `boot_to_m1_2p.txt` | joins (squad Cowboy + Cochise only: both P3/P4 must spawn) | P3's presses 7000-7450 refused (16 refusals, Swan pinned in slot 0, never resident); **7600: GATE timeout (GT_T 20,020 ms) -> slot 0 released -> P3 = clone of Cowboy** (char 18, marker 7); the preload ENSURE right after re-pinned Swan and it was resident within 50 polls -> **P4 = Swan with own model** (7800, instance 0xD21400). Slot 1 unused. Count 4 / views 4 to poll 12386, 0 TLB misses | **FAILED TEST** for X10 A in M12 (P3 got the documented fallback, the clone); fallback itself VERIFIED. **Superseded by chs_m12s** |
| chs_m12b (w4p-m6-1) | as chs_m12, `--poke 6000:0x000E1C40:40000` (TIMEOUT_MS 40 s, PINE test aid) | same | 32 refusals; **8250: timeout after 40,040 ms -> P3 = clone of Cowboy**; the re-pin was resident within 150 polls -> **P4 = Swan** (instance 0xCCD800). To poll 14688: count 4, views 4, 0 TLB misses | **FAILED TEST** (same outcome with 40 s; finding 3). Superseded by chs_m12s |
| chs_m15 (w4p-m5-1) | M15 cp1 (entry 0x01FDA0A4), P1 `boot_to_m1_2p.txt` | joins | no join until 10,500: the level-start in-engine scene waited for a skip input (single view, screenshot `t0396_p10500.png`); CHOOSE never ran | not a chooser result (test setup); re-run as chs_m15b |
| chs_m15b (w4p-m6-1) | as chs_m15, P1 `local/m6/skip_p1.txt` (Cross held every 100 polls from 5000 to 9500) | joins | by 7200: **P3 and P4 = clones of Swan** (char 5, marker 7); CHOOSE statuses Swan/Snow 4, Ajax/Cochise/Vermin/Fox/Rembrandt/Cowboy 3 (their `_gen` humans are present; PRESENT refuses them for loading), **Cleon 6**; ENSURE code 4 (nothing to load), no pin made, slots empty (the old order would have pinned **Cleon**, m6_missions.md M15). To poll 15473: count 4, views 4, 0 TLB misses | **VERIFIED** X9 A (Cleon never chosen or pinned in M15) |
| chs_m17 (w4p-m6-1) | M17 cp1 (entry 0x01FDA1AC), P1 `skip_p1.txt` (coordinator's request after the smoke crash) | joins | 7000: P3 refused (Ajax pinned in slot 0); statuses **Swan/Snow/Cowboy/Fox/Cleon 6** (XC rows level55), Vermin/Rembrandt 4, Ajax/Cochise 3; Cochise (handle 0x73) stays AI (X2 row level55 cp <= 1). **7150: a W4P-spawned Warrior joined (handle 0x8014B, prio 7, index 2; players 3, views 3, cameras 3) and the game crashed at poll 7153**: 23 TLB misses, first pc=0x0011F9B0 addr=0xF0866DEC, then pc=0x0019B090 addr 0/0x220/0x224, then pc=0 (`local/m2/chs_m17/emulog.txt` line 5105) - the same signature as the smoke batch's M17 crash, where player 3 had taken Cochise with the old chooser | **FAILED TEST (M17 cp1 crashes when any 3rd player joins; not caused by the chooser - finding 4)** |
| chs_reg (w4p-m6-1) | M13 cp1, `local/m6/rnd_p1..p4.txt` (seeded random walk/attack/grab from poll 9000; slots 3/4 Start every 300 polls), X2 Fox row on | 4 players, random bots, 900 s | 7000-8400: 8 refusals; **P3 = Swan, P4 = Ajax, both W4P-spawned with their own models** (slot 0 Swan instance 0xCD1000, slot 1 Ajax 0xC53400; +0xD8 0xC52000 / 0xCDC000); no timeout. Poll 9000 (clock 81.2 s) to 24229: count 4, views 4, both pins kept; clock 383.7 s at 18000 = **302 s of random play** by then; **0 TLB misses** | **VERIFIED** regression and X10 A in M13 (two Warriors with own models) |
| chs_m12k (w4p-m6-1, follow-up) | M12 cp1 as chs_m12, `local/m6/ch2.pnach` (KICK_MS = 8,000) | joins | 7000-7450: refused; re-pin at about 8 s (N_PIN 1 -> 2, N_RELEASE 1), still not resident at the next presses; **7600: timeout 20,020 ms from the first pin -> P3 = clone of Cowboy**; preload -> P4 = Swan (own model). 0 TLB misses | **FAILED TEST** for option (b): the re-pin does not fix the stall |
| chs_m12d (w4p-m6-1, follow-up, diagnosis) | M12 cp1, `ch2.pnach` with KICK_MS = 0 and TIMEOUT_MS = 60,000 (PINE pokes at 6000), `extra_survey` at 6950, 7100, 7300, 7500, 7700, 7900, 8300, 8700 | joins | Swan pinned at 7000 (slot 22, instance 0 the whole time); Swan's parts: 7100 texture only, 7300 none (loads pending 3), **7500 all three resident with refcount 0**, **7700 animation and model evicted**, 7900 requested again, 8300 animation + texture, **8700 all three resident**; request priorities FLT_MAX and dict+0xBC4 = -1 in every sample (no human request, so the scheduler does not call the streamer); timeout at about 8850 -> P3 = Cowboy clone, the preload re-pin found the parts resident -> P4 = Swan. 0 TLB misses | **VERIFIED** diagnosis (section 2.6) |
| chs_m12s (w4p-m6-1, follow-up) | M12 cp1, `local/m6/ch3.pnach` (KICK off, PINSVC/PINFIX on) | joins, 540 s | **7000: one refused press; by 7050 the Swan pin has an instance (0xD62000)**; **P3 = Swan** at the next press (count 3 at 7200, +0xD8 0xD65400); the preload pinned Ajax (instance 0xD21000 by 7200); **P4 = Ajax** (7350, +0xD8 0xCAA800). Swan and Ajax parts resident with refcount 2 from 7300 to 12000; N_PIN 2, N_REFUSE 4 (one press), N_TIMEOUT 0, N_RELEASE 0, NOFIT 0; count 4, views 4 to poll 14149; 0 TLB misses | **VERIFIED** X10 A in M12 (both players own models) |
| chs_m13s (w4p-m6-1, follow-up) | M13 cp1, `ch3.pnach`, `local/m6/rnd_p1..p4.txt` (random from 9000), 800 s | 4 players, random bots | 8500: one refused press; **P3 = Swan, P4 = Ajax** (own models, instances 0xC45C00 / 0xCDC000); clock 81.1 s at 9000 -> 384.2 s at 18000 = **303 s of random play**, count 4, views 4 to poll 21066, both pins kept, N_TIMEOUT 0; **0 TLB misses** | **VERIFIED** regression with PINSVC |
| chs_pl13 (w4p-m6-1, follow-up 2) | M13 cp1, `local/m6/ch4.pnach`, `local/m6/rnd_p1..p4.txt` (players 3-4 Start every 300 polls from 7000, random input from 9000), 620 s | joins, then random play | 8800 (both joined, no input yet): P1 Rembrandt (73.37, 381.27, 4.79), P2 Snow (74.14, 382.25), **P3 Swan (76.90, 381.98), P4 Ajax (70.38, 379.27)**: P3 and P4 each **3.6 units** from P1 on opposite sides, **7.06 apart**; N_PLACE 2, N_PLACE_FB 0 (both moved by HuTeleportNearHuman); N_FIX 2. From 9000 all four move freely (e.g. P3 to (70.0, 396.2) at 9300, P4 to (82.7, 382.7)): nobody stuck. Screenshot `t0342_p8928.png`: four different views. 4 players to the end, **0 TLB misses** | **VERIFIED** F-0195 fix in M13 |
| chs_pl12 (w4p-m6-1, follow-up 2) | M12 cp1, `ch4.pnach`, rnd scripts, 600 s | joins, then random play | 7300: P1 Cowboy (-23.41, 22.01, 0), P2 Cochise (-23.61, 21.31), **P3 Swan (-25.41, 19.01), P4 clone of Cowboy (-20.08, 23.38)**: 3.6 units from P1 each, **6.89 apart**; N_PLACE 2, N_PLACE_FB 0. All four move from 9000 (P4 7.2 units by 9300). **Player 4 got the clone, not Ajax: FITCHK reported Ajax's model does not fit** (NOFIT 11, N_NOFIT 1, slot 1 released, EN_LAST 7) - the first runtime use of the no-fit fallback; in chs_m12s Ajax did fit. Swan's instance built by PINFIX (N_FIX 1). Screenshots `t0301_p7648.png`, `t0359_p9364.png`. **0 TLB misses** | **VERIFIED** F-0195 fix in M12; VERIFIED no-fit fallback; second model in M12 borderline (finding 10) |

### 5.1 Pool memory (extra_survey, Sector Pool `*(0x006EB9C8)`, capacity 17,208,320 bytes)
| Run | Poll | Bytes used | Total free | Largest possible block | Our pins | Live humans (without model) |
|---|---|---|---|---|---|---|
| chs_m13fox | 8800 (P4 = Swan) | 16,063,136 | 943,456 | 889,856 | warr_sw | 9 (0) |
| chs_m13fox | 11000 (after re-join as Ajax) | 16,426,528 (+363,392) | 580,064 | 520,192 | warr_sw, warr_aj | 9 (0) |
| chs_m13fox | 19400 | 16,426,528 | 580,064 | 520,192 | warr_sw, warr_aj | 9 (0) |
| chs_reg | 9000 / 18000 / 24000 | 16,356,000 / 16,415,648 / 16,422,432 | 650,592 / 590,944 / 584,160 | 591,872 / 452,608 / 452,608 | warr_sw, warr_aj | 10 / 9 / 9 (0) |
| chs_m12 | 6900 / 9300 / 11400 | 15,874,720 / 16,338,848 / 16,351,136 | 1,131,872 / 667,744 / 655,456 | 265,216 / 171,008 / 171,008 | - / warr_sw / warr_sw | 39 / 43 / 43 (0) |
| chs_m12s (follow-up, PINSVC) | 6950 / 7300 / 7700 / 12000 | - | 1,139,040 / 371,808 / 364,640 / 359,520 | 265,216 (all four) | - / warr_aj, warr_sw (both with instances) | - |
| chs_m13s (follow-up) | 9000 / 18000 | 16,356,000 / 16,356,000 | 650,592 / 650,592 | 591,872 / 591,872 | warr_sw, warr_aj | 10 / 10 (0) |
| chs_m15b | 8000 / 12600 | 16,558,144 / 16,558,144 | 448,448 | 177,152 | none | 20 (0) |
| chs_m17 | 6900 (before the joins) | 15,805,408 | 1,201,184 | 809,984 | none | 18 (0) |

Two extra Warrior models fit in M13 (about 0.58 MB still free afterwards, no human without a model, no NOFIT) and, with
PINSVC, in M12 (about 0.36 MB free afterwards, largest block 265 KB, no NOFIT; chs_m12s). In M15 nothing is loaded.

## 6. Findings
1. **The M13 duplicate-Fox risk is real and is removed (VERIFIED chs_m13fox).** At the re-join Fox's model was resident
   and Fox absent (m6_fixes.md finding 3); CHOOSE now gives him status 6, the re-joiner became Ajax with his own model.
   Supersedes m6_fixes.md finding 3 ("possible fix") for Mission 13.
2. **Pins are no longer moved away from a Warrior in use (VERIFIED chs_m13fox, chs_reg).** Swan's pin stayed through the
   Fox deletion and the re-join for the rest of the runs (5.4 min); a second Warrior went into slot 1. Supersedes
   m6_fixes.md finding 4.
3. **M12: the first pin of Swan did not become resident while the player's presses kept waiting (FAILED TEST for
   X10 A in M12, chs_m12 and chs_m12b).** 8 and 9 POKE calls over 20 s / 40 s did not make it resident; in both runs the
   GATE timeout released the pin (player 3 -> clone of Cowboy) and the preload's immediate re-pin was resident within
   50-150 polls (player 4 -> Swan). The same kind of pin loaded within one press interval in M13 (chs_m13fox, chs_reg).
   HYPOTHESES (not diagnosed): (a) at every POKE the streamer returned before servicing the pin because M12's own
   dictionary loads were pending (dict+0xC6C, `FUN_00185990`); (b) the first request is lost or blocked and only a new
   pin (which sets dict+0x1B4 again, `FUN_0018AD40`) re-arms it. Static reading of the request functions
   (`FUN_001782E8`, `FUN_0016EA20`, `FUN_0018EB10`: a component is queued only if `FUN_001859A0` finds no pending
   request) shows no duplicate queueing by repeated POKEs. Options for the user: (a) accept (player 3 = clone after 20 s
   in heavy levels like M12, player 4 gets the model); (b) **re-pin on a refused press when the pin is older than about
   8 s** (release and pin again in GATE; about 15 words and 1 config word) - recommended, needs one M12 run to confirm;
   (c) OWN3 = 0 (player 3 always the clone at once, old behaviour). **Superseded (follow-up, section 2.6):** option (b)
   was implemented and FAILED (chs_m12k); the real cause is eviction of the unreferenced loaded parts (VERIFIED chs_m12d);
   the pin service PINSVC fixes it (VERIFIED chs_m12s: players 3 and 4 with own models in M12). Hypotheses (a)/(b)
   above are superseded.
4. **Mission 17 cp1 crashes as soon as a third player joins, whoever he is (VERIFIED chs_m17; also the coordinator's
   smoke_m17 with the old chooser, where player 3 had taken Cochise).** Same TLB-miss signature on both builds and with
   both choosers. Static reading (decompile `all_01.c:33233`, our labels): `FUN_0019B070(obj)` (only caller
   `FUN_0019B4C0`) calls render camera[*(obj+0x28)] (`FUN_0011F9B0`) and then that camera's vtable +0x224 without a NULL
   check; obj+0x28 holds a garbage camera index once the third view appears. HYPOTHESIS: a level55 cp1 object kept per
   camera or view (party / kiss-scene camera) is not prepared for a third camera - the class of `m2_hud_players34.md`
   CAMSAFE. Not a chooser problem; the XC and X2 tables cannot avoid it. Needs a camera fix or blocking drop-in there
   (coordinator informed). **Superseded:** the coordinator found the cause (fog/room-smoke per-camera pitch/yaw arrays
   sized for 2 cameras) and fixed it (F-0184, FXCAM in `mod/m2/fx34.txt`); not re-run here.
5. **M15: with all eight Warriors in the level and Cleon excluded, both players 3-4 are clones of Swan (VERIFIED
   chs_m15b).** By design (X9 A); before this change player 4 would have loaded Cleon.
6. CHOOSE tests residency before presence, so a Warrior present only as a `_gen` variant shows status 3, not 4
   (chs_m15b); ENSURE's PRESENT test then skips him, so nothing wrong is loaded (diagnostic note only).
7. **X7 (b) with HUD-slot reuse (VERIFIED chs_m13fox):** the re-joiner took the freed HUD slot 2, found byte 2 and got
   the level's spray 6 again; the moved player 4 (HUD slot 3) kept byte 1 (no second gift).
8. N_REFUSE counts every poll on which a refused Start is held (4 per scripted press), not presses (diagnostic).
9. **Follow-up: H1 of m2_extra_model.md is confirmed at runtime (chs_m12d):** with a pin waiting, the request priorities
   stayed FLT_MAX and dict+0xBC4 = -1, the pin's instance was never built while the parts came and went; the streamer is
   only reached through our POKE at Start presses. M13 worked before only because its parts were not evicted between
   presses.
10. **Follow-up 2: a second extra model in M12 is borderline (VERIFIED chs_m12s vs chs_pl12).** With the same level and
   checkpoint, Ajax's model fitted in chs_m12s (both players with own models) and did not fit in chs_pl12 (FITCHK ->
   NOFIT -> player 4 = clone of Cowboy). The Sector Pool had about 0.37 MB free after Swan's model with a largest block of
   265 KB; Ajax needs three 128 KB blocks, so it depends on what the fit test can evict at that moment. Behaviour as
   designed (problem 3: "if a second model does not fit, fall back to the clone").
11. **Follow-up 2: F-0195 fixed (VERIFIED chs_pl13, chs_pl12).** Spawned players 3-4 now stand 3.6 units from player 1 on
   different sides (6.9-7.1 units apart in both runs), chosen by the game's own HuTeleportNearHuman; the fallback was not
   needed in either run (N_PLACE_FB 0).

## 7. Not done / open
- **Not run at runtime (static and simulation only):** X3 (`HuChangePlayerGang`) through LVOWE; REL34's marker-7
  branch (a script deleting a W4P-added Warrior -> UNPIN); LV -> UNPIN on a normal leave; FITCHK "does not fit" with two
  slots (no NOFIT in any run); a GATE timeout on slot 1 while slot 0 is in use.
- **Missions:** M1 not run (M12 and M13 used for "both spawned"); M14 cp6-7 cannot be joined after a reload (join off
  at gameplay start, m6_missions.md M14), so Cleon's exclusion there is checked only by simulation (XCHK level 51 cp 1
  and 7); the rows for M2, M3, M6, M7, M9, M10, M11, M16, M17 (cp <= 2), M18 and the hub were not exercised at runtime.
- **4-instance lockstep** with the new code: not run (HYPOTHESIS deterministic, section 2.4).
- **Decisions for the user:** keep or drop the HYPOTHESIS rows for Fox (M16-M18, hub) and the hub rows; X10 (OWN3)
  default. (Ajax rows: done in the follow-up per the user's X9 A; finding 3: fixed by PINSVC.)
- **Follow-up not run:** PINSVC in M14-M18 or with a 4-instance lockstep; KICK with PINSVC together (KICK stays off);
  N_FIX was not read by the probes of chs_m12s (added to `chooser_probe.state` afterwards); the M17 crash fix (F-0184)
  with the chooser was not re-run here.
- **Coordinator:** `mod/w4p_m1.pnach` not regenerated (smoke2 batch); `docs/STATE.md` RAM map and test groups not
  edited (spawn now also 0x000E2300-0x000E243F and the game hook 0x0023D6BC); `m6_fixes.md` findings 3-4 not annotated
  (superseded here).
- **Follow-up 2 not run:** PLACE's fallback (no free spot) at runtime (simulation only); placement in other missions,
  after a checkpoint reload or for a re-join while player 1 runs; 4-instance lockstep. The Select ring of player 3 is only
  described (2.7).

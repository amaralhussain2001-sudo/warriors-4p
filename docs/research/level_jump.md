# Starting a chosen story mission from a test (level jump) — static analysis, 2026-10-11

Build SLUS-21215 v1.03. Function names are OUR labels (stripped ELF). Static analysis only: nothing here was run.
Sources: `local/analysis/all/*.c` (decompile), `local/analysis/lua_bindings.tsv`, pseudo-Lua in
`local/analysis/pseudo/` (WAD entry numbers below), ELF strings read from `local/disc/SLUS_212.15`.

## 1. How the game changes level

### 1.1 The level table (VERIFIED)
- GameMgr+0x14D4: array of 0x84-byte entries, filled from Lua `CfgLevelName(index, ...)` (binding 0x0036B220 →
  FUN_0041D510 → FUN_0041F118). The data is the `levelNames` table in WAD 3773 (`pseudo/03773_e15a707a.lua`
  main_5); the table index is the Lua position − 1.
- GameMgr+0x56D4 = number of entries (loop bound in FUN_0015C7B0). GameMgr+0x56DC (u16) = current level index
  (written only by FUN_0041CE88).
- Entry layout from FUN_0041F118 and its users:
  - +0x00 index;
  - +0x04 level number (read by GetLevelId FUN_0041D6F0);
  - +0x08 number of checkpoints (FUN_0015FE90's checkpoint-cycling debug path compares the checkpoint with it);
  - +0x14 the logical name, max 15 chars, e.g. "level86". This is the string MenuLoadLevel compares;
  - three more strings at +0x24, +0x39 and +0x49 (display/mission names).
  - Correction to F-0009: its "+0x18 name, +0x28 display name" offsets do not match this code. HYPOTHESIS until
    one PINE read of GameMgr+0x14E8+i·0x84.
- Story indexes (VERIFIED by the Lua table and F-0009's runtime dump):

| idx | level | Mission | checkpoints (+0x08) | entry string address if GameMgr = 0x01FD8400 |
|---|---|---|---|---|
| 1 | 99 | 1 New Blood | 3 | 0x01FD996C |
| 2 | 80 | 2 Real Live Bunch | 4 | 0x01FD99F0 |
| 3 | 87 | 3 Payback | 5 | 0x01FD9A74 |
| 4 | 34 | 4 Blackout | 5 | 0x01FD9AF8 |
| 5 | 2 | 5 Real Heavy Rep | 4 | 0x01FD9B7C |
| 6 | 3 | 6 Writer's Block | 5 | 0x01FD9C00 |
| 7 | 5 | 7 Adios Amigo | 4 | 0x01FD9C84 |
| 8 | 81 | 8 Encore | 5 | 0x01FD9D08 |
| 9 | 86 | 9 Payin' The Cost | 4 | 0x01FD9D8C |
| 10 | 93 | 10 Destroyed | 6 | 0x01FD9E10 |
| 11 | 31 | 11 Boys In Blue | 6 | 0x01FD9E94 |
| 12 | 14 | 12 Set Up | 3 | 0x01FD9F18 |
| 13 | 9 | 13 All-City | 3 | 0x01FD9F9C |
| 14 | 51 | 14 Desperate Dudes | 7 | 0x01FDA020 |
| 15 | 52 | 15 No Permits, No Parley | 4 | 0x01FDA0A4 |
| 16 | 54 | 16 Home Run | 5 | 0x01FDA128 |
| 17 | 55 | 17 Friendly Faces | 3 | 0x01FDA1AC |
| 18 | 84 | 18 Come Out To Play | 3 | 0x01FDA230 |
| 19-23 | 82, 92, 83, 20, 11 | flashbacks A-E | 4, 3, 6, 6, 6 | +0x84 each |
| 29 | 95 | hub | 12 | 0x01FDA7DC |

The address column is GameMgr + 0x14E8 + idx·0x84. GameMgr was 0x01FD8400 in every M2 run with the current patch
set (VERIFIED runtime, `local/m2/*/state.txt`). It is a heap address, so recompute it if the heap layout changes.

### 1.2 Requesting a level (VERIFIED, decompile)
- Lua `MenuLoadLevel(name)` (binding 0x0036DF48) → **FUN_00160D78(name)**:
  - sets GameMgr+0x14C = 3 ("leave level");
  - calls FUN_0015C7B0(0x005E5D90, name). That function strcmp's (FUN_00430C4C) every entry+0x14 and stores the
    matching index in 0x005E5D90+0x20, or -1 if none matches.
- Lua `MissionComplete()` (0x0036DF28) → FUN_00160D00:
  - sets GameMgr+0x14C = 2 and next index = current + 1;
  - goes through the mission-complete state 0x005E5DF8 (summary, autosave). Avoid it in tests.
- Lua `Quit()` (0x0036DF78) → FUN_00160D38: sets current index 0, GameMgr+0x14C = 3, checkpoint 1.
- Lua `SetCheckPoint(n)` (0x0037B760) → **FUN_0041ABC0(n)** → FUN_0041CE98(GameMgr, n):
  - sets GameMgr+0x33A = n;
  - clears the GameMgr+0x480 inventory block (FUN_0041E0B8);
  - calls FUN_00422C60(0x006FE490) and FUN_00397E88.
  - FUN_0041CEF0(GameMgr, n) sets only +0x33A, without the clear.

### 1.3 What happens next (VERIFIED code structure / HYPOTHESIS runtime)
- The game runs a stack of states:
  - 0x0050C784 is the top index, 0x005E66A0 the stack, FUN_0015E6B8 the update loop.
  - A state is popped when its update returns 0 (FUN_0015E650 runs exit, then resume of the state below).
- In-game update FUN_00158728: if GameMgr+0x14C is neither 0, 1 nor 2, it returns 0 at once, so with 3 the in-game
  state is popped on the next frame.
- The loading state 0x005E5D90 is below it. Its update FUN_0015C858, when +0x20 >= 0:
  1. loads that level (FUN_0015C5F8);
  2. sets GameMgr+0x56DC = index (FUN_0041CE88);
  3. sets +0x20 = -1;
  4. pushes the in-game state 0x005E56B8 again.
- Level start, the in-game enter (FUN_001582E0):
  - calls FUN_0015FE90 (RunLevel), which starts the script chunk named `sprintf("%s_%d", entry name, checkpoint)`
    (format string 0x00550148), e.g. "level86_1";
  - then calls **FUN_0041A460(GameMgr, -1)** (the drop-in join with "any pad").
- ResetLevel FUN_001607B8 sets join allowed GameMgr+0x56E8 = 1, GameMgr+0x14C = 0 and GameMgr+0x56F0 = 0.
- The game itself uses this exact pattern:
  - The hub (WAD 9401 main_62, main_65; WAD 9512) calls `SetCheckPoint(cp)`, `SSMC_StartSaveSequence()`, then
    `MenuLoadLevel("level"..N)`.
  - The cheat handler (WAD 4106 main_61) calls `SetCheckPoint(1)`, then `MenuLoadLevel("level"..next)`.
  - FUN_0015FE90's debug path calls FUN_00160D78 with a table entry's own string pointer, the same trick proposed
    below.

## 2. Proposal (1): jump to level N with the current two players

**Two test calls, then nothing else.** Both are W4P `CallAt` entries (session polls) through the "warriors-4p test
call" mailbox, called after FrameStats on the game thread:

```
CallAt = P:0041ABC0:1, P+10:00160D78:<GameMgr+0x14E8+idx*0x84>
# Mission 9 (level86, idx 9), checkpoint 1:   P:0041ABC0:1,P+10:00160D78:0x01FD9D8C
# Mission 2 (level80, idx 2), checkpoint 1:   P:0041ABC0:1,P+10:00160D78:0x01FD99F0
```

- **Why the table's own string works:** FUN_0015C7B0 strcmp's the argument against every entry, so it matches its own
  entry. No string has to be written to memory. VERIFIED by code; the game does the same (§1.3).
- **Checkpoint:** 1 is the mission start. Values 2 to entry+0x08 start later sections, for example the "checkpoint A"
  states used in M1. The chunk "levelNN_<cp>" must exist (HYPOTHESIS: 1 always exists).
- **Why it is safe at the FrameStats point:** FUN_00160D78 only writes two variables. GameMgr+0x14C is checked at the
  start of the next in-game update, which is the same timing as a Lua script calling MenuLoadLevel mid-frame.
  HYPOTHESIS until run. Use a poll in normal gameplay, not during a scene or a loading screen, e.g. P ≥ 4300 after
  the boot script (gameplay from about poll 3930).
- **Players kept:** GameMgr+0x56EC is the story "2-player" flag. It is set by FUN_00419AC0 when player 2 joins with a
  real pad in the 2 PLAYER menu, and FUN_00419A80 reads it. Nothing in the level change clears it (VERIFIED for
  FUN_001607B8). The level start's FUN_0041A460(GameMgr, -1) re-adds player 2 when all of these hold (VERIFIED
  code):
  - join allowed;
  - GameMgr+0x158 is 0 or 3;
  - the flag is set;
  - count <= 1;
  - a companion is available.
  This is how Mission 1 gets player 2 after the menu (F-0024/F-0025). Players 3-4 created in the old level are
  destroyed with it; create or join them again after the jump.
- **Cleaner variant (W4P change, optional):** add `GM+0xNNNN` argument syntax to CallAt, so the string address does
  not depend on the heap position.
- **Alternative without a pointer:** `FUN_0015C7A8(0x005E5D90, idx)` then `FUN_00160D38()` (Quit). Quit also sets
  checkpoint 1 and current index 0 before the load. It is less clean; prefer the MenuLoadLevel pair.

**Runtime checks:**
- Before: read32 of the string address equals "leve" (0x6576656C) and the string is "levelNN".
- After the load: GameMgr+0x56DC == idx and GameMgr+0x33A == checkpoint.
- GameMgr+0x224 == 2, and player 2's pad state (0x005DD810 + pad·0x50 + 0x42) == 1 on pad 4.
- Hash streams equal across instances.

## 3. Proposal (2): players 3-4 through the game's own drop-in

The in-game loop (FUN_00158728, the 8-pad loop) calls FUN_0041A460(GameMgr, pad) when a connected pad with no owner
presses Start. With the M2 cap patches, a join succeeds (VERIFIED code) when:
- join is allowed;
- the mode is 0 or 3;
- the count is below 4;
- PickJoinCompanion (FUN_0022A770) finds an AI human (+0x1B0 == -1) in player 1's squad. It prefers the lowest
  non-zero +0x1B1 priority, otherwise takes the first AI member. Outside level 99 in story state 0 it also scans the
  level for Warriors-gang humans with no squad.

Join priorities ≥ 3 in HuCreate (6th argument; scan of the mission chunks in `evidence/missions/mission_scan.json`):

| Mission (level) | priority 1 / 2 / 3+ | named Warriors (MISSIONS.md) |
|---|---|---|
| 6 (3) | Rembrandt/Snow, Ajax/Snow, **Ajax (3)** | Snow, Rembrandt, Ajax, Cowboy |
| 8 (81) | Cleon, Cleon/Swan, **Swan (3)** | Cleon, Swan, Ajax, Snow, Vermin, Rembrandt |
| 12 (14) | Cowboy, -, **WarrBuddy (4)** | Cochise, Cleon, Cowboy, Swan, Ajax, Vermin |
| 13 (9) | Rembrandt, Snow, **Fox (3)** | Fox, Snow, Rembrandt, Cleon |
| 16 (54) | swan, ajax/snow/swan, **cowboy/snow (3)** | Ajax, Cowboy |
| 2 (80) | Cleon, Vermin | 6 named Warriors (priority 0 members may still be picked) |
| 9 (86) | Cleon, Swan | Snow, Cleon, Swan, Vermin, Ash (squad membership unknown) |
| 1 (99), 4 (34), 14 (51), 18 (84) | none ≥ 1 found by the scan | |

- **Recommended first targets:** Mission 13 (level9, idx 13, 3 checkpoints) and Mission 8 (level81, idx 8). Both
  have a third join-priority Warrior; a fourth needs a priority-0 squad member or the fallback scan.
  HYPOTHESIS: squad membership is decided by the scripts at runtime.
- **Runtime check:** after the jump, read player 1's squad with nav_probe's `p1_squad`, then press Start on pads 1
  and 2 (W4P slots 2-3).
- **Missions with none found** (e.g. Mission 9): need added characters (D7 "add" case).

## 4. Proposal (3): risks
- **Pad of player 2 after the jump:** FUN_0041A460(GameMgr, -1) calls MakePlayer with pad -1, which takes a free
  connected pad. With 4-player W4P configs, pads 1 and 2 report connected, so player 2 could be bound to pad 1 instead
  of pad 4. It was observed on pad 4 at Mission 1 start, but that is not proven for a jump. HYPOTHESIS; check the pad
  owners after the jump.
- **Memory card / autosave:** the MenuLoadLevel path never calls `SSMC_StartSaveSequence` or the mission-complete
  state, so there is no autosave prompt (VERIFIED code). The boot script also chose "continue without saving".
- **Story state:** later missions may read unlocks (`UM_IsLevelComplete`), LUASaveData (money, flags) or the
  checkpoint inventory set by earlier missions. Starting at checkpoint 1 from Mission 1's state may differ from a
  real story playthrough, e.g. inventory/money (SetCheckPoint clears GameMgr+0x480). HYPOTHESIS.
- **Lua globals:** they persist across levels (one Lua state), so Mission 1 tutorial globals such as bAshIntro may
  leak into the next level. HYPOTHESIS.
- **Join-allowed flag:** it is 1 at every level start (FUN_001607B8), but missions switch it with
  `CfgMultiplayerJoin` (MISSIONS.md column "Join on/off"). Mission 8 (1/1), 11 (0/1), 12 (0/2) and 18 (1/4) turn it
  off at times, so Start-joins for players 3-4 only work in the open windows.
- **Cutscenes:** every mission starts with intro scenes. Players 3-4 pressing Start during a scene joins
  (FUN_0041A460) only when the pad loop runs; wait for gameplay. The level-99-specific "Ash intro" problem (F-0114)
  does not apply elsewhere, but each mission's join callback is written for player 2 (m2_hud_scripts.md); keep the
  join-event guard (F-0114).
- **Calling during a load or scene:** do not issue the calls while GameMgr+0x14C != 0 or during a loading screen.
- **Checkpoint chunk:** an invalid checkpoint (> entry+0x08) names a chunk that does not exist ("levelNN_9"). The
  behaviour is unknown; keep 1 ≤ cp ≤ entry+0x08.

## Summary
The game changes level when GameMgr+0x14C = 3 and the loading state's target index (0x005E5D90+0x20) is set:
- FUN_00160D78(name) (Lua MenuLoadLevel) does both. It strcmp's the name against each level-table entry+0x14
  ("level86").
- The in-game update then returns 0. The loading state loads that index, starts "levelNN_<checkpoint>"
  (GameMgr+0x33A), and calls FUN_0041A460(GameMgr, -1). That call re-adds player 2, because the story 2-player flag
  GameMgr+0x56EC survives the level change.

For tests, two CallAt entries after gameplay starts:
- `P:0041ABC0:1` (SetCheckPoint 1);
- `P+10:00160D78:<GameMgr+0x14E8+idx·0x84>`, e.g. 0x01FD9D8C for Mission 9 or 0x01FD9F9C for Mission 13 (with
  GameMgr = 0x01FD8400).

This avoids the mission-complete state and its autosave.

Players 3-4 can then join with Start on pads 1-2 through the game's own drop-in, given the cap patches and a free AI
squad member:
- best candidates are Missions 13 (Fox, priority 3), 8 (Swan 3) and 6 (Ajax 3);
- Missions 1, 4, 9, 14 and 18 have no priority ≥ 3 companion.

Risks: player 2 may rebind to pad 1 when pads 1-2 report connected; story state, inventory and Lua globals differ from
a real playthrough; join windows depend on each mission's CfgMultiplayerJoin calls. All runtime effects are
HYPOTHESIS until a run checks the reads listed in §2.

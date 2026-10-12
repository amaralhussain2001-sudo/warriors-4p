# M6 camera parity: cameras that only players 1-2 get, all 18 missions and the hub (static audit, 2026-10-12)

Build: The Warriors SLUS-21215 v1.03 (`local/disc/SLUS_212.15`, opened read-only), current patch set
`mod/w4p_m1.pnach` (5703 patch lines, 2026-10-12 13:48). **Static analysis only: no emulator, no test runner, no build,
no project file changed except this note.** Sources: pseudo-Lua `local/analysis/pseudo/` (cited `WAD:line`, e.g.
`09112:683` = `09112_4f3f3a65.lua` line 683), Lua disassembly `local/analysis/lua/`, decompile `local/analysis/all/all_*.c`,
`local/analysis/lua_bindings.tsv`, the ELF (scratch disassembler with the pnach overlay). Function and structure names
are OUR labels (the ELF is stripped); addresses are static. Labels: VERIFIED (with pointer), HYPOTHESIS. "P1..P4" =
players 1-4 (game player index 0..3 = view index 0..3). Builds on `m2_pads_cameras.md`, `m2_views34.md`,
`m6_missions.md` (file-to-checkpoint map, section 3 headers), `m6_x4_x6.md`, `m6_x6_fixes.md`, `view_merge_rule.md`.

## Plain-English summary
- **What this is.** Every place in the 18 story missions and the hub where the mission script gives a camera (or a
  camera setting) to `player` and `player2` only (view 0 and 1), with what players 3-4 see instead and a proposed fix.
  The user's report (M18 beach fight: "2 good screens, 2 zoomed-in screens") is one of them: players 1-2 get a wide
  80-degree rail camera, players 3-4 keep the normal close follow camera.
- **Counts.** (a) per-player gameplay cameras players 3-4 should also get: **21 spots in 12 missions** (M1, M3, M5,
  M6, M8, M9, M10, M11, M13, M16, M17, M18); 6 of them are worse than "missing": a player 3/4 action there **moves
  another player's camera or leaves his own view stuck** (marked "harm"). Plus 5 per-player button-prompt HUD spots,
  1 non-camera spot (M16 `HuSetNoAutoLock`) and 1 spot in an unused chunk (M17 08407). (b) shared or player-1-only
  cameras that need no per-player fix: 30 rows, 8 of them shared gameplay views where players 3-4 can walk out of the
  shared picture (marked b*; in one, M8 cp5, the shared camera can even frame the wrong people). (c) already covered by
  our X6 rows: 4 (M13 `EnterGraveTrain`, M16 `CamSwitcher`, M16 `GatePicked`, M18 `MoveInFOV/OUTFOV`); 3 of them only
  block the bug, only M16 `GatePicked` gives player 3/4 an equivalent camera. Per-human handlers that already work for
  everybody: 11 rows (ok). Missions with no class (a) camera spot: M2, M4, M7, M12, M14, M15 and the hub.
- **Does view index 2/3 work in the camera functions? Mostly yes (VERIFIED), with one big exception (VERIFIED code):**
  every per-view camera array is already 4 entries long (our `[4p]` relocation), all index-taking camera functions use
  those arrays without a "< 2" limit, and a call without an index loops over all players. **But a rail camera on view
  3 or 4 does not follow anybody**: the rail camera's target picker (`FUN_0013B7B8`) only knows targets for views 1-2,
  the same 2-player limit we already patched for the follow camera (`camtarget.txt`). Expected effect (HYPOTHESIS):
  give player 3 the M18 stage-2 rail with index 2 today and his quarter shows a rail camera that does not track him
  (this matches run x4x6b g5, where player 3's view "showed the empty subway from then on"). So **every rail fix
  below needs one small engine patch first (F4 "RAILTGT", design in 2.4)**.
- **New hazard found (VERIFIED code, effect HYPOTHESIS): the "tracked humans" list.** The cameras of players 1-2 pick
  their target from a 4-slot list (entries 0 and 1 only). When players 3-4 join they are added to this list. Scripts
  that take player 1/2 out of the list and put them back (M1 cp2, M17 cp2 boss, M8 cp5 boss) push players 3-4 into
  slots 0-1. Example (M17 Lizzie boss): list P1,P2,P3,P4 -> script removes P1 and P2 and adds Lizzie -> P3,P4,Lizzie
  -> **player 1's camera now follows player 3 and player 2's follows player 4.** Fix F3 (2.3).
- **What to do (recommended order):** (1) engine patch F4 (rail target for views 3-4); (2) one shared Lua helper F1
  ("mirror": whatever a function does for player 2 / index 1 is repeated for players 3-4 with their own index) plus
  F2 ("own index" for trigger handlers) and F3 (tracked list); (3) LUACH rows per chapter file, most visible first
  (section 4). The current LUACH table has only 5 free rows; the full list needs about 12 more (section 5).
- Everything here is SINGLE-PC static reading; nothing was run. Effects marked HYPOTHESIS need a run each.

## 1. Engine facts that decide each fix (VERIFIED code unless marked)

### 1.1 What the camera bindings do with a view index
| Lua call (binding -> core) | Index argument | With index 2/3 | Without index (default) | Pointer |
|---|---|---|---|---|
| `CamSetupRail(name, h, fov, off, a, far, i)` (0x00366518 -> `FUN_0011CCE8`) | arg 7, default -1 | creates/uses rail[i] via `FUN_0011FBB0(i, 1)` (array relocated to 0x000F0830+4i) | -1 = rail[0] **and** rails 1..count-1 (loop to GameMgr+0x224), created if missing | all_00.c:19209-19296; pnach 0x0011FBD8-0x0011FC6C |
| `CamAddRailPoint(p, i)` (0x003667A0 -> `FUN_0011D098`), `CamModifyRail(k, v, t, i)` (0x003668E8 -> `FUN_0011D228`), `CamLeadRail(a, b, c, i)` (0x003666E8 -> `FUN_0011CF70`), `CamLockRail(b, i)` (0x00366880 -> `FUN_0011D180`) | last arg, default -1 | rail[i] if it exists (`FUN_0011FBB0(i, 0)`) | -1 = rail[0] and rails 1..count-1 | all_00.c:19297-19613 |
| `CameraMakeActive(cam, blend, name, h1, h2)` (0x003656A0 -> `FUN_0011B770` -> `FUN_0011EE08`) | **no index**: view = player index of `h1` (+0x1B0) | h1 = player 3/4 -> view 2/3 (active/render arrays relocated) | no human -> the camera's own player index (0 for locked/fixed/POIZO cameras, i for rail[i]) | all_00.c:18290-18325, 20596-20950 |
| same, camera substitution | - | if `cam` is a follow (type 2), rail (type 9) or type-11 camera of another view, the view's own camera of that type is used **if it exists** (`FUN_0011F9E0/0011FBB0/0011FF50(view, 0)`); otherwise the given camera object is moved to that view (its player index is rewritten, vtable +0x274) | - | all_00.c:20655-20693, 20756 |
| `CamSetFollowPos(v, i)` (0x00365C60 -> `FUN_0011C638`) | arg 2, **default 0** | follow[i] | follow[0] only (player 1) | all_00.c:18952-18989 |
| `CamSetFollowZoom(z, i)` (0x00365BF0 -> `FUN_0011C470`) | arg 2, default -1 | follow[i] if i < player count | all players | all_00.c:18867-18951 |
| `CamSetFollowHeading(x)`, `CamSetFollowAngle(x)` (`FUN_0011C2F0`, `FUN_0011C3B8`) | none | - | **all players** (loop to count) | all_00.c:18793-18866 |
| `CamSetSecondary(h, f, i)` (0x003670C0 -> `FUN_0011DCF0`) | arg 3, **default 0** | follow[i] secondary target (+0x320/+0x3FC) and `FUN_0011FD80(i)` | follow[0] only | all_00.c:19770-19795 |
| `CamEnable(opt, v, i)` (0x003671E0 -> `FUN_0011DE58`) | arg 3, default -1 | opt 0 (stick camera, array relocated to 0x000F08B0, m2_pads_cameras 5), opt 2 (rail), opt 5 (follow): entry i | opt 0: all 4; opt 2/5: all players; **opt 3 = SplitAllowed (global)**; 1, 4, 6-13 global | all_00.c:19845-19957 |
| `CamTarget(mode, cam, h)` (0x00365AD8 -> `FUN_0011C270`) | none; `cam` is **ignored** | - | mode 0 add h to the tracked list, 1 remove, 2 clear | all_00.c:18759-18792 |
| `CamLockLocked(cam, h, on)` (`FUN_0011BDC0` -> `FUN_001358D0`) | none | adds/removes h in the locked camera's own human list (+0x20C) | - | all_00.c:18571-18589, 36515-36541 |
| `CfgFollowCamera(...)` | none | - | global follow-camera config (all) | 04106:1064-1076 |
| `ChangeCam(cam, t)` (Lua helper 04106 main_12) | - | = `CameraMakeActive(cam, t)` + `CameraReset(cam)`; **t is a blend time, not a view index** | view = camera's own index | 04106:1032-1036 |

### 1.2 The rail camera has no target on views 3-4 (blocker for every rail fix)
- Rail camera class: vtable 0x00536DD0, constructor `FUN_0013B118`; per-frame update vtable +0x134 = `FUN_0013D010`,
  which calls the target picker **`FUN_0013B7B8`** (all_00.c:41279-41385, call at 42443; activation +0x144 =
  `FUN_0013B508` calls it too, 41142). VERIFIED (vtable words read from the ELF).
- `FUN_0013B7B8` collects targets from the tracked-humans list 0x005D91A8 **entries 0 and 1 only** (loop bound
  `sltiu v0,s1,2` at 0x0013B8A8) into a 2-slot array cam+0x340/+0x344 (count +0x348). In split mode it keeps slot
  [player index] only if `player index < count` (0x0013B948 `slt v0,v0,v1`); otherwise target 0, count 0
  (0x0013B984). For a rail camera of view 2/3 the test is always false: **no target**. VERIFIED (ELF disassembly with
  the current pnach overlay: no patch word in 0x0013B7B8-0x0013BA60).
- Same limit as the follow camera's picker `FUN_001282A0`, which `camtarget.txt` (`[warriors-4p 4p]`, 0x0012842C ->
  cave 0x000F0B90) fixes by using `HuGetPlayer(p)` for p >= 2. Nothing does this for rails.
- Consistent runtime observation: x4x6b g5 (`m6_x4_x6.md`, negative result 2): the subway rail made active for player
  3 left view 3 "showing the empty subway from then on". Effect for any new rail on view 2/3: HYPOTHESIS until a run.

### 1.3 The tracked-humans list and its order
- 0x005D91A8, 4 slots (handles). Add `FUN_001222B0(h, 1)`: compact, then put h in the **first free slot** (`FUN_004DAEF0`),
  only if fewer than 4 entries (all_00.c:22665-22721). Remove `FUN_00122438(h, 1)`: clear the slot, then compact
  (all_00.c:22724-22740). VERIFIED.
- UpdateJoin `FUN_0041A460` adds every player that is not in the list when someone joins (all_07.c:10735-10745,
  10826-10829), so with X11 the list becomes P1, P2, P3, P4 (full). The generic release `FUN_0022A2A8` does not remove a
  human from the list (it is not among the callers of `FUN_00122438`: `FUN_0011C270`, `FUN_00126558`, `FUN_00126878`,
  `FUN_00233F60`, `FUN_002398B0`, `FUN_00239B80`, `FUN_0041A460`, `FUN_0041A8C0`); the UpdateJoin drop-out loop does
  (all_07.c:10784-10790). VERIFIED code. Whether our session LEAVE cave leaves a stale AI handle in the list: not
  checked (HYPOTHESIS).
- Follow-camera picker (`FUN_001282A0`, all_00.c:27285-27360) and rail picker (1.2): in split mode view p (p = 0, 1)
  follows the p-th valid entry among list entries 0..1. **So the list order decides whom players 1-2's cameras follow.**
  Players 3-4's own follow cameras do not use the list (camtarget patch -> `HuGetPlayer`). VERIFIED code.
- Consequences (HYPOTHESIS until a run): (1) a script that removes `player`/`player2` and adds them (or a boss) back
  moves P3/P4 into entries 0-1 -> players 1-2's cameras follow players 3-4; (2) with the list full, a script's
  `CamTarget(0, cam, boss)` does nothing unless it clears the list first; (3) a shared camera (split off) frames at most
  entries 0-1.

### 1.4 Shared views, view-0-only cameras, box types
- `CamEnable(3, false)` = SplitAllowed 0 -> one view showing camera 0 (`view_merge_rule.md` 2/3.1). W4P shows the whole
  frame on every PC when views < 2 (`CropFor`, emulator/pcsx2/pcsx2/W4P/W4P.cpp:1605-1615) and the sit-out screen lets
  it through when views == 1 with >= 2 players (W4P.cpp:1427-1433). So shared stretches reach all four PCs. VERIFIED code.
- A camera made active without a human goes to view 0 only (1.1). Where split stays on, player 2 is treated exactly like
  players 3-4 there (original 2-player behaviour), so it is not a parity gap between 2 and 3-4 (class b). What the other
  views show at that moment (one view or split) depends on the layout flags: HYPOTHESIS.
- Volume boxes: type 0 notices any human, **type 2 notices only GameMgr+0x228/+0x22C = players 1-2** (loop bound 2 at
  0x004136B0; `m6_x6_fixes.md` 1.1). A per-player camera handler on a type-2 box can never run for players 3-4.
- `HUDTurnOnActionCycleAnim(..., hud)` (0x0036FC80 -> `FUN_001B5A90(...)`): whether HUD 2/3 work with `[4p hud B1]` is
  not checked (HYPOTHESIS).

## 2. Fix patterns (design; nothing applied)

### 2.1 F1 "mirror" (one helper in the "global.lua" row, one line per wrapped function)
`W4P_MIR(f)` returns a wrapper; during the call of `f` the camera bindings are swapped for versions that, after the
original call, **repeat a call made for player 2** (human argument == `player2`, or view index argument == 1) once for
each player 3/4 that exists (`HuGetPlayer(i)`, i = 2, 3, `HuIsAPlayer`), with the human replaced by `HuGetPlayer(i)` and
the index by i. Covered calls: `CamSetupRail` (index arg 7, human arg 2), `CamAddRailPoint`, `CamModifyRail`,
`CamLeadRail`, `CamLockRail`, `CameraMakeActive` (h1/h2 == player2; the name callback is NOT repeated: pass nil),
`CamSetSecondary` (index arg 3; a secondary target equal to `player2` becomes `HuGetPlayer(i)`), `CamLockLocked`
(h == player2), `CamEnable(opt, v, 1)` for opt 0/2/5, `CamSetFollowPos/Zoom(x, 1)`. Rules:
- The original's return value is returned (e.g. `CamStage2 = CamSetupRail(...)` keeps rail[1]'s handle), so script
  globals holding camera handles are unchanged.
- Players 1-2 are untouched: the original call runs first and unchanged (same rule as the existing W4P rows).
- Restore the bindings through `call(f, {...}, "x")` like W4P_GPW (`m6_x6_fixes.md` negative result 6).
- Limitation: a call skipped because `player2` is not human is not mirrored either (a 4-player session always has a
  human player 2 unless he left; then players 3-4 keep follow cameras: acceptable).
Sketch (Lua 4.0, NOT compiled or tested):
```
W4P_CSR = CamSetupRail
function W4P_CSRm(n, h, f, o, a, z, i) local r = W4P_CSR(n, h, f, o, a, z, i)
  if i == 1 then for j = 2, 3 do local p = HuGetPlayer(j)
    if HuIsAPlayer(p) then W4P_CSR(n, p, f, o, a, z, j) end end end return r end
-- likewise W4P_CMAm (CameraMakeActive), W4P_CARPm, W4P_CMRm, W4P_CLRm, W4P_CSSm, W4P_CLLm, ...
function W4P_MIR(f) return function(a, b, c, d) local s = CamSetupRail CamSetupRail = W4P_CSRm
  -- (swap the other bindings the same way)
  local r = call(%f, {a, b, c, d; n = 4}, "x") CamSetupRail = s return r end end
```

### 2.2 F2 "own index" for trigger handlers (extends the existing W4P_GPW)
Handlers on type-0 boxes run with `A1` = the entering human, and most compute the view as "1 if `A1 == player2`, else 0"
(or -1 = everybody). F2 = W4P_GPW extended to the rail functions: while the handler runs for a player 3/4, every index
argument 0/1/-1 becomes his own index and `player`/`player2` human arguments become `A1`. Where the player 3/4 has no
camera of that kind (no rail built for him yet), the wrapper falls back to "make his follow camera active"
(`CameraMakeActive(MainCam, 0, nil, A1)`), never touching another view. Replaces the plain `W4P_G34` guard where a
real equivalent exists.

### 2.3 F3 tracked-list wrapper
`W4P_TRKW(f)`: before `f`, `CamTarget(1, NilHandle, h)` for each player 3/4 (removes them, list compacts); call `f`;
after `f`, `CamTarget(0, NilHandle, h)` for each (appended after whatever the script put first, or dropped if the list
is full, which is harmless for their own follow cameras, 1.3). Players 1-2's list order is then exactly what the
original 2-player script produces. Plus, for boss cameras that also set `CamSetSecondary(player, 0, 0)` /
`(player2, 0, 1)`: mirror with `CamSetSecondary(boss, 0, i)` for players 3/4 (their follow camera targets themselves
through the camtarget patch, so "secondary = boss" gives the same two-subject framing). HYPOTHESIS that the framing
matches. Alternative (engine, global, riskier): keep humans with player index >= 2 out of the list in `FUN_001222B0`;
side effect: fixed cameras on views 3-4 lose their look-at (`FUN_00124000` reads list[player index] in split mode,
all_00.c:24014-24110).

### 2.4 F4 "RAILTGT" engine patch (prerequisite for every rail fix)
Same shape as `camtarget.txt`: at 0x0013B944 (`lw v1,0x348(s0)`, right after the player-index call returns v0) jump to
a cave; if v0 < 2 run the original 0x0013B944-0x0013B950 (`lw v1,0x348(s0)`, `slt v0,v0,v1`,
`beql v0,zero,0x0013B984` with delay `sw zero,0x340(s0)`) and continue at 0x0013B954; if v0 >= 2:
`t = FUN_00390268(GameMgr + 0x228 + 4*v0)`, `sw t,0x340(s0)`, `+0x348 = (t != 0)`, `j 0x0013B988`. About 24 words;
s0 = camera here (s1 in the follow version). Free RAM must be checked first (STATE lists 0x000E5D10-0x000E6FFF,
0x000E9800-0x000EBFFF, 0x000ECA60-0x000EFFFF as free, "check first"). Players 1-2 and shared views unchanged.
VERIFIED: the instruction words above (ELF disassembly); HYPOTHESIS: the effect, until a run.

### 2.5 F5 join hook for players 3-4
Many special cameras are given at a moment (stage start) or in the mission's player-2 join callback (`SetPlayer2Callback`:
M6 `ch4.Multiplayer`, M9 `C4.Player2Start`, M10 `Multiplayer`, M16 `AnotherPlayer`, M17 `C3.Multiplayer`, M18
`C5.SetPlayer2Fight`). Players 3-4 join later through X11 and the join-event guard (0x0041B180 -> 0x000F0ED0) skips
the Lua event for index >= 2, so they never get them. Design: for index >= 2 the guard calls LUARUN
(0x000E79A0, `m6_x4_x6.md` 2.2) with `if W4P_J then W4P_J(<i>) end`; each chapter row defines `W4P_J(i)` (e.g. M18 cp3:
"if stage 2 is running, give player i the stage-2 rail"). HYPOTHESIS feasibility (LUARUN from the join path).

### 2.6 F6 type-2 boxes
Options: (i) mirror on player 2's trigger (F1 on the handler: players 3-4 get the switch when player 2 crosses the box;
fine for chases where everybody runs the same way, wrong for corner cameras); (ii) a Lua poll (`ScheduleFunc` loop,
`IsInsideBox(box, HuGetPlayer(i))`) that calls the handler for players 3-4 with F2 (HYPOTHESIS: `IsInsideBox` works for
any human); (iii) leave as is (players 3-4 keep follow cameras). Widening the type-2 loop in the engine is not a
1-word change (the box keeps a 2-entry inside list at +0xF0, `m6_x6_fixes.md` 1.1).

## 3. Per mission
Columns: P12 = what players 1-2 get; P34 = what players 3-4 get now. Class: (a) per-player gameplay camera missing for
P3/P4, "harm" = a P3/P4 action disturbs another view or leaves his own view broken; (b) shared/cinematic or view-0-only
(player 2 treated like 3-4), b* = shared gameplay view that frames only list entries 0-1; (c) covered by an X6 row;
ok = already per-human or all players. Risk = risk of the proposed fix. Chunk names: from the LUACH log where marked
(log), otherwise the main script's `preLoadFile` name + ".lua" (HYPOTHESIS, same pattern as every logged name).

### M1 - level99 "New Blood" (chunks "level99_lesson1.lua" = 09654 cp2, "level99_lesson2.lua" = 09655 cp3)
| Script file:line | Function | P12 | P34 now | Class | Proposed fix | Risk | Label |
|---|---|---|---|---|---|---|---|
| 09654:53-73 | `P2.SetupLesson1` (continuous path `wheelScene == 1`) | `CamTarget(1/0, MainCam, player/player2)`: removed, `HuChangePlayerGang`, re-added | if P3/P4 (or their left-behind AI humans) are in the list they move to entries 0-1 -> **P1/P2 cameras follow them** | (a) harm | F3 on `P2.SetupLesson1` (save the `HuGetPlayer(2/3)` handles before the gang change and remove those too, in case they stay in the list) | low | VERIFIED script + code (1.3); effect HYPOTHESIS |
| 09655:100-113, 210-229, 356-377, 393-417, 130-147 (`FencePoizoDone` 144/146), 238-244 (`PoizoClimb` 241/243) | `P3.EndChapterScene`, `P3.MoveToClimb`, `P3.Player2Jumps`, `P3.VerminJumped`, clears | follow camera with secondary target Vermin (`CamSetSecondary(Teacher.Vermin, 0, 0/1)`) | plain follow camera | (a) | F1 on the 6 functions (mirrors index 1 -> 2/3; clears with NilHandle too) | low | VERIFIED script/code (`FUN_0011DCF0` follow[i]); framing HYPOTHESIS |
| 09654:78, 09655:514/577; 09655:366/400 | `CamSetFollowZoom(1)`; `CamEnable(0, x)` | all players (default index) | same | ok | - | - | VERIFIED code 1.1 |
| 09654:334-362, 09655:117-137, 486-515 | Vermin/Fence/Dealer POIZOs | split off (`CamEnable(3, false)`), shared locked camera | same picture | b | - | - | VERIFIED script |
| 09654:186-218, 251-290; 09655:245-265, 301-325, 438-461 | car/ped/climb/jump/fence POIZOs | locked camera on view 0 (no human) | as player 2 | b | - | - | VERIFIED script; layout HYPOTHESIS |

### M2 - level80 "Real Live Bunch" (joining off for the intro/tutorial, F-0201)
| Script file:line | Function | P12 | P34 now | Class | Proposed fix | Risk | Label |
|---|---|---|---|---|---|---|---|
| 08774:128-217, 08775:179-214, 08776:276-300/492-529, 08777:144-199/294-295 | tutorial locked cameras, follow resets | locked cameras on view 0 / shared; heading/angle/zoom for all | same | b | - | - | VERIFIED script |

### M3 - level87 "Payback" (chunk "level87_chap5_club.lua" = 09225 cp5; "level87_chap4_street2.lua" = 09224 cp4)
| Script file:line | Function | P12 | P34 now | Class | Proposed fix | Risk | Label |
|---|---|---|---|---|---|---|---|
| 09225:571-586 (+ restores 525-543, 635-645, 651-662) | `ch5.MoveToNextBox` (split back on) | stealth-tutorial locked camera `Tutorial02Cam` on views 0 and 1, `CamLockLocked(cam, player/player2, 1)` | follow camera | (a) | F1 on `MoveToNextBox`, `Stealth3Damaged`, `AfterS03WalksBack`, `Stealth03Damage` (restores) | medium (one locked camera object shared by 4 views, its +0x20C human list grows; framing HYPOTHESIS) | VERIFIED script |
| 09225:604-634 | `ch5.DistractMoveBackTutorial` / `ch5.LockCam` | split off (616), `Dest4Cam` shared, locked to P1/P2 | same shared picture | b* | - | - | VERIFIED script |
| 09224:231-232 (re-enabled 315) | `ch4.StartItUp` | stick camera off (`CamEnable(0, nil, 0/1)`) during the arrival POIZO | stick camera stays on | b (minor) | optional F1 | low | VERIFIED code (opt 0 array 4 entries) |
| 09224:254-268, 312-318, 839-879 | `ch4.RunIntroPoizo`, `HandleCameras`, `The_REAL_End` | POIZO on view 0, then own follow cameras restored | follow camera throughout | b | - | - | VERIFIED script |
| 09171:4283, 4290, 4302 | `ActivateTagCam`, `NixCamera`, `EnemiesInc` | tag camera for the tagging human | same (view from the human; tagging fixed by W4P_TAGW) | ok | - | - | VERIFIED code 1.1 |
| 09171:4021-4023, 09221:140-141, 200-201 | `CameraBlend`, `ch1.CamBack` | `CamSetFollowPos` default index 0 = player 1 only | as player 2 | b | - | - | VERIFIED code |

### M4 - level34 "Blackout"
| Script file:line | Function | P12 | P34 now | Class | Proposed fix | Risk | Label |
|---|---|---|---|---|---|---|---|
| 07968:318-341 | `P1.CarStereoPoizo` / `DoneStereoPoizo` | POIZO for `player` only (view 0) | as player 2 | b | - | - | VERIFIED script |

### M5 - level2 "Real Heavy Rep" (the intro code is in the main chunk "level2.lua" = 07708)
| Script file:line | Function | P12 | P34 now | Class | Proposed fix | Risk | Label |
|---|---|---|---|---|---|---|---|
| 07708:2251-2345 (boxes 07708:1424-1429, 1554 = type 2) | `c1Intro.StartCamOn` / `TrailRail` / `SideRail` | clinic intro: locked camera, then a rail per player (index 0/1) when entering boxes | follow camera (type-2 boxes never notice them) | (a) low | F6 (i) mirror on player 2's trigger + F4, or leave; note `SideRail`'s "else index 0" would hijack rail[0] if ever called for P3/P4 (not reachable by walking) | medium | VERIFIED script/box types |
| 07849:207-216, 258-266 | `P1.EnterStreets`, `EndStreetScene` | follow restored per human / for P1/P2 | follow camera | ok | - | - | VERIFIED |
| 07849:489-533 | `P1.BumsThanks` / `BumOpenGate` | `CamSetSecondary(GateBum)` default index 0 = player 1 | as player 2 | b | - | - | VERIFIED code |

### M6 - level3 "Writer's Block" (chunk "level3_chase.lua" = 08022 cp4 rooftop chase)
| Script file:line | Function | P12 | P34 now | Class | Proposed fix | Risk | Label |
|---|---|---|---|---|---|---|---|
| 08022:293-320 (+ `SetupRailCam` 365-370, `MainRail` 371-390, join callback `ch4.Multiplayer` 325-338) | `ch4.StartRail` (type-2 `vbStartRail`, 07856:1959) | side-scrolling chase rail (`CameraMakeActive(ch4.railCam, 0.5, nil, player/player2)` + `MainRail(player2)`) for the whole rooftop chase | follow camera | **(a) high** | F4 + F1 on `ch4.StartRail` (mirror needs rails 2/3: `SetupRailCam` uses the default index, so rails 2/3 exist only if 3-4 players were in at chapter start -> the wrapper also calls `CamSetupRail("ch4.railCam", HuGetPlayer(i), ch4.NormalFOV, {0,0,2}, 0.05, 150, i)` + the 2 points with index i) + F5 for later joins | medium | VERIFIED script; rail behaviour 1.2 |
| 08022:604-624 (boxes `vTopRail[11..15,19]` = type 0, 07856:1897-1902) | `ch4.EnterTopRail` | own rail switched to "top" framing | **a P3/P4 entering -> index -1 -> every rail (P1/P2's) is changed** | (a) harm | F2 (own index; no rail -> do nothing) | low | VERIFIED script/code (`FUN_0011D228` -1 loop) |
| 08022:538-572 (boxes `vFixCam[*]` = type 0, 07856:1825-1832) | `ch4.ExitFixCam` | rail back after a fixed stunt camera | **P3/P4 leaving any `vFixCam` box -> `CameraMakeActive(ch4.railCam, ..., P3)`: view 3 gets rail[2] (no target, 1.2) or, if rail[2] does not exist, player 1's rail object is moved to view 3 (player 1's view loses its target)** | (a) harm | F2: for P3/P4 make their own rail active if it exists (after F1/F4), else `CameraMakeActive(MainCam, 0, nil, A1)`; keep the pad unlock | low | VERIFIED script/code; effect HYPOTHESIS |
| 08022:472-519 | `ch4.EnterFixCam` (type 0) | fixed stunt camera + pad lock + slow-mo, only when the partner is down | runs for P3/P4 only when player 1 is down; works per human (own view) | ok | (fixed camera look-at for view 3/4 depends on list order, 1.3, HYPOTHESIS) | - | VERIFIED script |
| 08022:450-471, 573-603, 625-677 (types 2) | `EnterBigCam`, `EnterSideRail`, `EnterMainRail` | rail framing changes | nothing (type 2) | (a) low | with F1/F4: F6 (i) | low | VERIFIED |
| 08022:755-774 (`vbJumpWarn` type 2, 07856:1848-) | `ch4.JumpWarnOn` | jump button prompt on HUD 0/1 | none (a P3/P4 call would light HUD 0) | (a) HUD | optional F6 + HUD 2/3 check | low | VERIFIED script; HUD 2/3 HYPOTHESIS |
| 08022:678-698 | `ch4.EnterTopCam` / `ExitTopCam` | (never registered: dead code) | - | - | - | - | VERIFIED (no SetMsgHandler) |
| 08023:625, 672, 1000; 08023:178-180, 08024:64-67 | tag cameras; restores | per human / P1-P2 restore | per human / unchanged | ok | - | - | VERIFIED |
| 08021:217-273, 08023:246-409, 08024:302-304, 08022:227-268 | Ambush fight camera, PoizoPaint, gallery and intro POIZOs | split off / view 0 | same picture | b | - | - | VERIFIED |
| 08021:585, 730; 08026:197-198 | `SetupChatterFight` secondary (index 0); `C0.EnterCompetition` gate cameras | player 1 only | as player 2 | b | - | - | VERIFIED |

### M7 - level5 "Adios Amigo"
| Script file:line | Function | P12 | P34 now | Class | Proposed fix | Risk | Label |
|---|---|---|---|---|---|---|---|
| 08484 (split off at 08484:65, never back on) | Diago boss fight (`DiegoCam` shared rail; `CamTarget` 08484:183-627) | one shared picture framing list entries 0-1 (script puts P1/P2/Diego/Vargas there) | same picture; P3/P4 can be out of shot | b* | (none at script level; framing 4 humans needs a wider picker) | - | VERIFIED script/code |
| 08482:74, 08483:123-292 | `CamSetFollowPos` default 0 | player 1 | as player 2 | b | - | - | VERIFIED |

### M8 - level81 "Encore" (chunks "level81_chase.lua" = 08838 cp3, "level81_chatterbox.lua" = 08839 cp5)
| Script file:line | Function | P12 | P34 now | Class | Proposed fix | Risk | Label |
|---|---|---|---|---|---|---|---|
| 08838:374-405 | `RunStartCam`, `RunCam1` | start locked cameras, then a cart-chase rail per player (loop over {player, player2}, index 0/1) | follow camera (on foot today; **D24 makes them Snow/Ajax in this chase**) | **(a) high with D24** | F4 + F1 on `RunStartCam` (mirror `StartCam2`: a fresh locked camera per extra player) and `RunCam1` (wrapper adds `HuGetPlayer(2/3)` with index 2/3) | medium | VERIFIED script |
| 08838:320-373, 406-491 (boxes `vChaseCam[*]` = type 2, 08780:1237-1242) | `C3.ChaseCam` -> `RunCam2..7` | fixed/locked/rail chase cameras per human; `RunCam3/5/7` use "player2 -> 1 else 0" | nothing (type 2); if ever called for P3/P4, `RunCam3` would change player 1's follow settings and `RunCam5/7` would rebuild player 1's rail | (a) with D24 | F6 (i) mirror on player 2's trigger (the cart riders move together) + F2 inside `RunCam3/5/7` | medium | VERIFIED script/box types |
| 08838:197-199 | `StartChase` | cart tap prompt on HUD 0/1 | none | (a) HUD (D24) | with D24's tapping: HUD 2/3 (check) | low | VERIFIED script |
| 08839:394-412 (split off 08839:121) | `C5.ChatterCam` / `CamBackToWarriors` | shared boss rail: remove P2, P1, add Chatterbox; back: remove boss, add P2, P1 | with P3/P4 in the list the shared camera frames **P3/P4 instead of the boss** (and later instead of P1/P2) | b* harm | F3 on both | low | VERIFIED script/code; effect HYPOTHESIS |
| 08840:56-67 | `Setup` (reload path) | `CamEnable(5/0, 1, idx)` for P1/P2 | already enabled at load (init cave 0x000F0B00 sets [2..3]) | ok | - | - | VERIFIED code |
| 08840:254-274, 08841:127-133 | door/horror-house cameras | view 0 | as player 2 | b | - | - | VERIFIED |

### M9 - level86 "Payin' The Cost" (chunk "level86_chapter4.lua" = 09166 cp4)
| Script file:line | Function | P12 | P34 now | Class | Proposed fix | Risk | Label |
|---|---|---|---|---|---|---|---|
| 09166:249-268, 279-323, 343-372, 397-407, 565-591, 187-200 | `C4.StartFirstRailCam`, `StartRailCam`, `ZoomInRail`, `ZoomOutRail`, `ZoomVan2`, `LockBroken1`, `Player2Start` | cage-fight rails/locked cameras for `player` and `player2`/`hSwan` | follow camera (they are outside the cage by script, `m6_missions.md` M9) | (a) medium | F4 + F1 on these functions (the rails use the default index, so rails 2/3 exist with 4 players) | medium | VERIFIED script |
| 09166:273-278 (`vSecondVanBox` type 0, 09117:1872) | `C4.ZoomRail2` (on leave) | rail back | **P3/P4 leaving the box -> `CameraMakeActive(railCam, 0.8, nil, P3)` -> view 3 gets rail[2] with no target: his view stops following him** | (a) harm | F2 (own rail only after F4; else his follow camera) | low | VERIFIED script/code; effect HYPOTHESIS |

### M10 - level93 "Destroyed" (chunks "level93_chapter5.lua" = 09379, "level93_chapter6.lua" = 09380)
| Script file:line | Function | P12 | P34 now | Class | Proposed fix | Risk | Label |
|---|---|---|---|---|---|---|---|
| 09379:190-266 (`vLCTrigger[1..4]` type 2, 09321:1656-1663) | `C5.LCTrigger1..4Enter/Exit`, `RunSneakCam1..4` | stealth corner cameras per human | follow camera (type 2) | (a) low | F6 (ii) poll (the handlers already work per human) | medium | VERIFIED |
| 09380 (split off 169, 355; no `CamEnable(3, true)`) | Virgil boss stage cameras, `Multiplayer` 588-599 | shared rails/locked cameras | same picture | b* | - | - | VERIFIED |
| 09379:135-163 | `RunLCCam` | view 0 | as player 2 | b | - | - | VERIFIED |

### M11 - level31 "Boys In Blue" (chunk "level31_Birdie.lua" = 07911 cp6)
| Script file:line | Function | P12 | P34 now | Class | Proposed fix | Risk | Label |
|---|---|---|---|---|---|---|---|
| 07911:201-231 | `P6.NewWarrior` | `CamSetSecondary(Birdie, 0, 1)`: player 2's view frames Birdie | plain follow camera (joining is switched off at the first kill, 205) | (a) low | F1 on `P6.NewWarrior` | low | VERIFIED |
| 07911:31-58, 85-146, 236-347 | Birdie fight cameras | split on (54), locked cameras on view 0 | as player 2 | b | - | - | VERIFIED |

### M12 - level14 "Set Up"
| Script file:line | Function | P12 | P34 now | Class | Proposed fix | Risk | Label |
|---|---|---|---|---|---|---|---|
| 07696:328-398 | `C4.DropLoot` / `LootEnd` (action prompt, any human) | loot camera on the planter's view | same for P3/P4 | ok | - | - | VERIFIED |
| 07655:2018-2035 | `TwoDudes` POIZO | shared | same | b | - | - | VERIFIED |

### M13 - level9 "All-City"
| Script file:line | Function | P12 | P34 now | Class | Proposed fix | Risk | Label |
|---|---|---|---|---|---|---|---|
| 09229:2667-2715 (`vbInTrain`, `vbMainCam` type 2, 09229:1502-1526) | `EnterGraveTrain` / `LeaveSub` | subway rail on their own view | follow camera; **X6 row 0 guard = safety net only** | (a) low + (c) | keep the guard; optional F6 (i) + F4; `LeaveSub` must get F2 (its "else index 0" moves player 1's follow camera) if it is ever called for P3/P4 | medium | VERIFIED (x4x6b g5 runtime for the original bug) |
| 09229:3373-3393, 09720:263-280, 09721:142, 217 | tag cameras, scene restores per human | per human | same | ok | - | - | VERIFIED |
| 09720:441-465, 09722:220-224 | radio POIZO, final POIZO | view 0 / shared | same | b | - | - | VERIFIED |

### M14 - level51 "Desperate Dudes" (players 3-4 sit out the cp6-7 chases after a reload, X13)
| Script file:line | Function | P12 | P34 now | Class | Proposed fix | Risk | Label |
|---|---|---|---|---|---|---|---|
| 08186:344-364 (split off 08186:171) | `C7.Rail` | shared bus-chase rail | same picture | b* | - | - | VERIFIED |
| 08186:402-427 (`Trig[*]` type 2, 08031:989-994), 08187:296-298 | `C7.ShowButtonTri/X`, `C9.ReadyRollingStart` | button prompts HUD 0/1 | none | (a) HUD low | with any D24-like rework only | low | VERIFIED |
| 08187:289-293, 330-391 | `C9.Rail1`, `C9.CAMChange` | hood/fixed/locked cameras on view 0 | as player 2 | b | - | - | VERIFIED |
| 08181:111-113, 08183:154-234, 08185:196-199 | follow resets, `CamSetFollowPos` index 0 | all / player 1 | - | b | - | - | VERIFIED |

### M15 - level52 "No Permits, No Parley"
| Script file:line | Function | P12 | P34 now | Class | Proposed fix | Risk | Label |
|---|---|---|---|---|---|---|---|
| 08191:3472-3483, 08255:405-474, 08256:121-127 | gate/park cameras, `CamSetFollowPos` index 0 | view 0 / player 1 | as player 2 | b | - | - | VERIFIED |

### M16 - level54 "Home Run" (chunks "level54_streets.lua" = 08355 cp1, "level54_alley.lua" = 08349 (log), "level54_park.lua" = 08352 cp3, "level54.lua" = 08262 (log))
| Script file:line | Function | P12 | P34 now | Class | Proposed fix | Risk | Label |
|---|---|---|---|---|---|---|---|
| 08355:188-199 (+ `OtherRailStart` 223-229, `TightenSideScroller` 413-421; `chase.CamSwitcher` 08262:2807-3092, `RailDown/Up` 3093-3108, `LeadOut/In` 3150-3167, all on type-2 boxes 08262:1522-1626) | `ch1.StartTheLevel` (loop over the `Warriors` table: index 1 for `player2`, else 0; Lua disassembly 08355 main.7 #98-148) | side-scrolling rail chase, switched box by box | follow camera for the whole cp1 chase | **(a) high** | F4 + F1 on `ch1.StartTheLevel` (rails 2/3 for P3/P4) + F6 (i) mirror on player 2's camswitch (replace the current W4P_G34 guard on `CamSwitcher` by F1 + F2) + F5 | medium-high (big handler, 13 boxes) | VERIFIED script |
| 08355:298-337 | `ch1.ReturnPlayerBrain` (loop over `Warriors`, `HuIsAPlayer`; disassembly main.14 #9-26) | own rail restored | **if P3/P4 control a `Warriors` member: `CameraMakeActive(railCam, 0, nil, P3)`; rail[2] does not exist (explicit indices) -> player 1's (or 2's) rail object is moved to view 3** | (a) harm | F2 on `ReturnPlayerBrain` (P3/P4: own rail if F1 built one, else follow camera) | low | VERIFIED script/code; who P3/P4 control here HYPOTHESIS |
| 08352:119-135 | `ch3.ContinueLevel` | park-chase rail per player (`L1 = {player, player2}`, index 0/1) | follow camera for the cp3 chase | **(a) high** | F4 + F1 (wrapper runs the same 7 calls with `HuGetPlayer(i)`, index i) + F5 | medium | VERIFIED script |
| 08349:152-202 | `ch2.TurnOnMusic` (cp2 reload start) | rail on view 0 (default index: rails for all exist) | as player 2 | b | - | - | VERIFIED |
| 08349:159-160, 08352:87-88, 08355:161-162 | `HuSetNoAutoLock(player/player2)` | no auto lock-on during the chase | auto lock-on | (a) minor (combat, not camera) | optional F1 | low | VERIFIED script |
| 08349:464-480 | `ch2.GatePicked` | own follow camera moved to the gate | **own** follow camera (W4P_GPW) | (c) equivalent | - | - | VERIFIED x6f_m16 |
| 08262:2807-3092 | `chase.CamSwitcher` | rail switches | nothing (type 2); W4P_G34 guard | (c) guard only | see first row | - | VERIFIED x6f_m16c |
| 08349:443-461 | `ch2.LockCamGo` / `LockPickStop` | lock-pick camera per human | same | ok | - | - | VERIFIED |
| 08262:3129-3137 (`vbHint` type 2) | `chase.FenceHint` | fence prompt HUD 0/1 | none | (a) HUD low | F6 + HUD 2/3 check | low | VERIFIED |

### M17 - level55 "Friendly Faces" (chunk "level55_lizziesattack.lua" = 08401 cp2)
| Script file:line | Function | P12 | P34 now | Class | Proposed fix | Risk | Label |
|---|---|---|---|---|---|---|---|
| 08401:195-220, 221-233, 238-245, 286-290 | `C3.ObjShowive`, `C3.Multiplayer`, `PlayerRevived`, `LizzieBossDamage` (split on, 198) | boss camera: player taken out of the tracked list, Lizzie added, `CamSetSecondary(player, 0, 0)` / `(player2, 0, 1)` | **list P1,P2,P3,P4 -> P3,P4,Lizzie: P1's camera follows P3, P2's follows P4**; P3/P4 themselves get a plain follow camera | **(a) harm, high** | F3 on these four + mirror `CamSetSecondary(Lizzie01["101"], 0, i)` for P3/P4 | medium | VERIFIED script/code; effect HYPOTHESIS |
| 08401:314-329, 362-383 (split off) | `C3.DoorDestroyed`, `C3.OutsidePoizo` | shared door/outside cameras, list changes | same picture (list order also affects these) | b* | F3 | low | VERIFIED |
| 08401:330-341 (`vLizCam` type 0) | `C3.LizCamEnter/Exit` | door camera per human | same | ok | - | - | VERIFIED |
| 08404:132-201, 582-589, 656-667 | stall fight (split off 162), `UnderStallRail`, `RailCamIn/Out` | shared / view 0 | same / as player 2 | b* / b | - | - | VERIFIED |
| 08403:444-456, 509-513 | `PARTY.ActionLizzie`, `SceneStopped` | per human / restore | same | ok | - | - | VERIFIED |
| 08407:71-109 | `C6.SetupSubway` | subway rail for P1/P2 | follow camera | (a) | none: chunk not referenced by `Mission[]` (`m6_missions.md` M17), HYPOTHESIS unused | - | VERIFIED script |

### M18 - level84 "Come Out To Play" (chunks "level84_final.lua" = 09112 (log), "level84_chase.lua" = 09110 (log)) - D24 agent working here
| Script file:line | Function | P12 | P34 now | Class | Proposed fix | Risk | Label |
|---|---|---|---|---|---|---|---|
| 09112:417-425, 552-571 (563/565), 605-614 (609/611) -> helper 683-700, 631-661 | `C5.StartStage2`, `C5.SwanGetsTheKnife`, `C5.EndPOIZOLuther` -> `C5.SetRailCam(player/player2)` -> `SetupRail2/3(t, h, 0/1)` | stage-2 beach rails `CamStage2` (fov 80) / `CamStage3` (fov 80 with 2 players, 75 far) | close follow camera (**the user's report**) | **(a) high** | F4 + wrapper on the three callers: after the original, for i = 2, 3 run `SetupRail2(0, HuGetPlayer(i), i, 0)` (or `SetupRail3` when inside `vFOVZoom`), restoring the globals `CamStage2`/`CamStage3` + F5 | medium | VERIFIED script |
| 09112:301-309 | `C5.SetPlayer2Fight` (player-2 join callback) | rail for a newly joined player 2 | joins of 3-4 skip it | (a) | F5 (`W4P_J`) | low | VERIFIED |
| 09112:662-681 (`vFOVZoom` type 0, 09030:1412) | `C5.MoveInFOV` / `MoveOUTFOV` | zoom-zone rail swap for their own view | nothing (W4P_G34 guard) | (c) guard only | after F4/F1: replace the guard by F2 (index 2/3) | low | VERIFIED x6f_m18 |
| 09112:615-630 (split off from `Setup` 87 to `AddStage2Gangs` 336) | `C5.SetupRail1` | stage-1 shared rail; `CamTarget(2)` clears the list, adds P1, P2 | same picture; P3/P4 can be out of shot | b* | - | - | VERIFIED |
| 09110:326-391 (split off 09110:39; `VCarChaseTrig` type 0) | `C1.CAMChange` | shared hood/fixed/locked chase cameras | same picture today (players 3-4 not in cp2); **with D24: a P3/P4 reaching `VCarChaseTrig[5]` takes the "not player" branch = player 2's: `HUDTurnOffActionCycleAnim(1)`, `HuSetTireless(player2, true)`, `HuSetButtonTapControl(player2, 0, ...)` (ends player 2's tapping)** | b (camera) / harm for D24 (not a camera) | D24: guard/own branch for P3/P4 in `C1.CAMChange` | low | VERIFIED script |
| 09110:429-446 | `C1.Random2` | tap prompt HUD 0/1 | none | (a) HUD (D24) | D24 | low | VERIFIED |

### Hub - level95 (09401, 09512, 09513)
| Script file:line | Function | P12 | P34 now | Class | Proposed fix | Risk | Label |
|---|---|---|---|---|---|---|---|
| 09401:2646-2804, 3553-3610, 6261-6275, 6562-6577, 6704-6729, 6838-6965 | marker/menu/new-item cameras, clubhouse setup, door walk | view 0 / shared; `CamSetFollowZoom(0)` and `CamEnable(0, x)` for all | same (players 2-4 sit out the interludes, X12) | b | - | - | VERIFIED script |

## 4. Priority list (most visible to players first; F4 RAILTGT must come before any rail item)
1. **M18 cp3 stage-2 rails** (09112:417-425/552-571/605-614): the reported bug; every 4-player run of the final fight.
   D24 agent.
2. **M16 cp1 side-scroller chase** (08355:188-199 + camswitch boxes) and its hazard `ReturnPlayerBrain` (08355:298-337).
3. **M16 cp3 park chase** (08352:119-135).
4. **M6 cp4 rooftop chase** (08022:293-320) and its two hazards `ExitFixCam` (538-572) and `EnterTopRail` (604-624):
   the hazards are reachable today by walking (type-0 boxes); a quick F2-style guard is worth doing even before F1/F4.
5. **M17 cp2 Lizzie boss** (08401:195-290): players 1-2's cameras may follow players 3-4 (F3).
6. **M8 cp3 cart chase** (08838:374-491): only once D24 puts players 3-4 on Snow/Ajax.
7. **M1 cp2/cp3** (09654:53-73 list reorder; 09655 Vermin secondary): tutorial, first mission everybody plays.
8. **M9 cp4 cage** (09166:249-323) and the `ZoomRail2` hazard (273-278, reachable by walking).
9. **M8 cp5 Chatterbox shared camera** (08839:394-412): shared picture may frame players 3-4 instead of the boss (F3).
10. **M3 cp5 stealth tutorial** (09225:571-586).
11. M10 cp5 sneak cameras (09379:190-266, type 2, needs F6 poll), M13 subway (09229:2667-2715), M5 intro rails
    (07708:2251-2345), M11 Birdie secondary (07911:201-231), HUD prompts (5 spots).
12. Shared-view framing (b*: M7 boss, M8 boss, M10 boss, M14 bus, M17 stall, M18 stage 1 and car chase): players 3-4 can
    leave the shared picture; no script fix (the pickers frame at most 2 humans); bring to the user as a known limit.

## 5. Open points and negative results (read before implementing)
1. **Nothing here was run.** Every effect on screen is HYPOTHESIS; the code paths and script lines are VERIFIED.
2. **Rails without F4 are worse than no fix**: a mirrored rail on view 3/4 would not follow its player (1.2). Do not
   ship F1 for rails before F4 is tested (positive control: M13 `EnterGraveTrain` for player 3 with the guard removed
   should then show player 3 riding the subway instead of an empty car).
3. **The existing X6 camera rows are guards, not parity** (M16 `CamSwitcher`, M18 `MoveInFOV/OUTFOV`, M13
   `EnterGraveTrain`): they stop players 3-4 from breaking other views but give them nothing; only `ch2.GatePicked`
   (W4P_GPW) gives an equivalent camera. M16 `CamSwitcher` and M13 `EnterGraveTrain` cannot even fire for players 3-4
   (type-2 boxes), so those guards are safety nets.
4. **LUACH capacity**: the table at 0x000E7F00 has 5 free rows (0x000E7F58-0x000E7F7F, `m6_x6_fixes.md` section 2);
   the list above needs new rows for about 12 chapter files (level99_lesson1/2, level87_chap5_club, level3_chase,
   level81_chase, level81_chatterbox, level86_chapter4, level93_chapter5, level31_Birdie, level54_streets, level54_park,
   level55_lizziesattack; level84_final, level54 and level9 already have rows that would be extended). The table must move or grow (free RAM check first).
5. **Chunk names** not seen in a LUACH log are HYPOTHESIS ("<preLoadFile name>.lua"); confirm in the first run's log.
6. **Tracked-list order** (1.3) is a new hazard class: besides the script spots above, a player who left may keep his
   AI human in the list (1.3: depends on the release path). Not observed at runtime yet; a PINE read of 0x005D91A8 (4 handles)
   before/after M17 `C3.ObjShowive` with 4 players would settle it.
7. **Locked/fixed cameras on views 3-4**: fixed cameras look at list[player index] in split mode (`FUN_00124000`), locked
   cameras keep their own human list; whether a mirrored locked camera (M3 cp5) frames the right people is HYPOTHESIS.
8. **HUD prompts on HUD 2/3** (`HUDTurnOnActionCycleAnim` -> `FUN_001B5A90`): not checked.
9. Not covered: Rumble/extras scripts, the 08259/08400/08405/08406/08407 chunks (`m6_missions.md`: not referenced by
   `Mission[]`), side missions and post-game hub content.
10. Method: camera calls were listed with a scratch extractor over the pseudo-Lua of every chunk named in `m6_missions.md`
    (1497 calls: 286 `CameraMakeActive`, 242 `CameraCreateLocked`, 137 `CamEnable`, 87 `CamModifyRail`, 82
    `CamAddRailPoint`, 53 `CamTarget`, 30 `CamSetupRail`, 24 `CamSetSecondary`, ...); every call with a human or index
    argument, every `player`/`player2` pair and every handler on a volume box was read in context; box types from the
    `AddVolumeBox` lines; loop tables lost by the pseudo-code were read from the Lua disassembly.

# M6 camera parity, agent camC: tracked-humans list (F3) in M17 cp2 and M8 cp5, M1 cp3 secondary target (F1), two engine rules, audit 5.6 (2026-10-12)

**Status (coordinator, 2026-10-12 21:40):** merged into mod/ (LUACH rows 16-19; BOSSTGT and CFGFOLLOW in camtarget.txt). Placeholders F-CAM-camC-1..11 are summarized in **F-0227**.

## Plain-English summary
- **What this is.** The game keeps a 4-slot list of "tracked humans" (0x005D91A8). The follow cameras of players 1-2
  pick what they look at from slots 1-2 of that list. Some boss scripts take players 1-2 out of the list and put the
  boss in. With 4 players the list also holds players 3-4, so after such a script players 3-4 slide into slots 1-2.
  This note measures that at runtime, fixes it with Lua rows, and gives players 3-4 the same special cameras as
  players 1-2.
- **Mission 17, Lizzie boss (fixed, before/after with the real chapter change).** Example: the party (cp1) ends with 4
  players and the boss fight (cp2) starts. **Before**: player 1's camera followed player 3 and player 2's followed
  player 4 - both top quarters showed close shots of other people (run camc_m17n1, screenshot t0370_p8688).
  **After**: all four quarters show the same boss picture as players 1-2 have in a 2-player game (camc_m17m
  t0319_p8197, t0344_p8906). Players 1-2 are fixed by a Lua row alone; for players 3-4 the row needs two small engine
  rules (BOSSTGT and CFGFOLLOW, section 2.2): without them their quarters showed walls or the crowd.
- **Mission 8, Chatterbox boss (fixed, before/after).** One shared picture for everybody. When Chatterbox is knocked
  down the script points the camera at him. **Before** (4 players): the picture showed players 3-4 instead of Chatterbox
  (camc_m8a t0553_p7298) and kept framing players 3-4 for the rest of the fight. **After**: a close-up of Chatterbox
  (t0699_p8529), then players 1-2 again, as in the 2-player game.
- **Mission 1 cp3 (fixed).** While Vermin runs ahead, the cameras of players 1-2 turn so that Vermin stays in view.
  **Before**: only players 1-2 (camc_m1s t0320_p8252: the bottom quarters look elsewhere). **After**: all four
  (t0345_p8964); a player 3/4 who joins later gets it within 0.5 s (camc_m17n1).
- **Mission 1 cp2 (no change needed, measured).** The squad swap at the start of cp2 drops players 3-4 (the earlier X3
  wrapper) and the game rebuilds the list as P1, P2, exactly as with 2 players (camc_m1c).
- **New engine finding (CFGFOLLOW).** The game's `CfgFollowCamera` (used by 13 script chunks, e.g. the M17 boss
  "close camera") changes the settings of camera 1 and copies them to camera 2 only. Example: in the M17 boss fight
  players 3-4 kept the normal camera distance and their boss camera stood 8 units away from where players 1-2's stood
  (camc_m17h). Fixed in place (13 words); players 1-2 unchanged (camc_reg6).
- **Audit open point 5.6 (answered).** A player who leaves through the session LEAVE does not keep a stale handle in the
  list: player 4's handle was removed (camc_m1c, camc_m17j).
- Everything: SINGLE-PC, one instance at a time (sandboxes 23 and 24), scripted bots, players 3-4 = W4P local bots that
  join through the game's UpdateJoin (x6fix_probe.join34), no impairment, MTVU off, no human play. The machine was
  heavily loaded (6-30 fps), so runs were long.

## Negative results and open points (read these first)
1. **Lua rows alone cannot give players 3-4 the M17 boss camera (FAILED TEST for the Lua-only variants).** Players 1-2's
   boss camera = primary target Lizzie (taken from the list) + secondary target = own player; the follow camera then
   uses a special position (FUN_00127CD8 -> cam+0x2D0, filled in FUN_0012AE58 from the secondary player). Views 3-4 take
   their primary target from `camtarget.txt` (always their own human). Tried: secondary = Lizzie (camc_m17a, m17n2:
   lock-on-like, quarters show walls/crowd, e.g. camc_m17n2 t0733_p9754); secondary = own player (camc_m17b: no visible
   change). Parity needs **BOSSTGT** (VERIFIED: views 3-4 primary Lizzie in camc_m17bt, m17g, m17j, m17m) **and
   CFGFOLLOW** (VERIFIED: without it views 3-4 had eye (375.7, 15.3, 6.3) vs (375.6, 23.1, 6.4) for views 1-2,
   camc_m17h; with it all four (375.5-375.8, 23.1, 6.4), camc_m17m). Both are engine words (group [warriors-4p 4p]),
   outside this agent's "rows only" brief: **the coordinator decides** (lines ready in
   `local/m6/cam/camC/camc_engine_lines.txt`). Without them the M17 row still fixes players 1-2 and is harmless for
   players 3-4 (secondary = own player shows nothing new, camc_m17b 7704-8800).
2. **FAILED TEST, CFGFOLLOW first version (runs camc_m17k, camc_reg5): game frozen, 50 TLB misses at pc 0x0011FA9C**
   (FUN_0011F9E0 read 0x000F0820 + 4 x garbage index). Cause (VERIFIED disassembly): in split mode the code reaches the
   copy through `beq zero,zero,0x0011C20C` at 0x0011C1C8, skipping the counter set-up I had put at 0x0011C208. The final
   version starts at 0x0011C20C, the entry of both paths (camc_m17m, camc_reg6, camc_fin_*: no such TLB).
3. **50 TLB misses in every run that calls `NextMission()` through LUARUN in M17 cp1** (camc_m17n1 without the M17 row;
   camc_m17n2, m17g, m17h, m17m with it): identical signature (pc 0x00323B98 addr 0/8 x17+17, pc 0x003327B4 addr 0 x16 -
   Lua VM reads of an empty reference), only at that call; the game continues normally. Cause HYPOTHESIS: the test
   method (NextMission run inside a DoString from the test mailbox). Not caused by the camC rows (same count without the
   M17 row). Natural cp1 -> cp2 (party end by play) was not reached.
4. **FAILED TEST (method), camc_reg2:** no god mode in a 2-player boss run -> "GAME OVER"; the scripted Cross presses
   chose "Last checkpoint" and the planned level jump then loaded level 99 during that reload -> crash, 22 TLB misses
   (first pc 0x0011E8D0 addr 0: the per-frame camera update FUN_0011E878 found no camera for view 1). Same game over in
   camc_reg3 ("You fell to your death", M8 cp5, before its second jump; no crash). The parts before the game over are
   valid; the rest was redone in camc_reg4 / camc_reg6 (0 TLB).
5. **FAILED TEST (method), camc_m17b:** BOSSTGT written over PINE did not stick: the camtarget words are `patch=2`
   lines, re-applied by PCSX2 every frame (readback at 7301 unchanged). BOSSTGT was then tested from a pnach.
6. **Most before/after evidence for M8 cp5 and M1 cp3, and the M17 door, comes from direct calls** of the original and
   the wrapped function (stubs only for scene preload / speech / goals / tutorial text / the door scene) on a prepared
   list. The M17 hazard and fix are also shown with the real chapter change (camc_m17n1 without the row; camc_m17n2,
   m17g, m17m with it) and the door was destroyed by play in camc_m17bt and camc_m17j (wrapped: Lizzie, P1, P3, P4). The
   M8 Chatterbox knock-down and the M1 cp3 run-ahead stages were not reached by play.
7. **Short window in M8:** `C5.ChatterCam` keeps players 3-4 out of the list until `C5.CamBackToWarriors` (3 s later),
   because the 2-player result has only one entry. A player 3/4 who leaves in those 3 s is not in the list, so the
   session LEAVE skips `FUN_0011ED60(index)` (camera teardown of his view; 0x000E7170-0x000E7188). HYPOTHESIS: harmless
   (the view is dropped anyway; a later join re-uses the camera object). Not tested.
8. **Not changed (not camera, 2-player-only, seen while reading):** M17 `HuSetAutoCombat(player/player2, 1)` in
   C3.SetupBossFight (08401:147-150); M1 cp3 `P3.Player2Jumps` also gives player2 a goal and a look target
   (`GoalAddressPerson`, `HuSetLookTarget`, 09655:363-371).
9. **Dead code in 08401 (no change):** `PlayerDied`, `PlayerRevived`, `LizzieBossDamage`, `C3.OutsidePoizo` have no
   caller: their names occur only at their own definition (Lua disassembly of every chunk in local/analysis/lua/) and
   not as a string in the ELF. VERIFIED static. The audit rows for them need no fix.
10. **CFGFOLLOW affects every mission that calls CfgFollowCamera while players 3-4 are in** (13 chunks incl. global
    04106, M3 09171, M6 08021, M9 09166, M12 07655, M17 08357/08401/08404): their cameras now get the same settings as
    players 1-2 (parity). Only M17 was tested.
11. **Space:** camC region 0x000EB000-0x000EBA00: rows to 0x000EB957, BOSSTGT cave 0x000EB960-0x000EB9B3, free
    0x000EB9B4-0x000EB9FF.

## Per-fix table (placeholder IDs; the coordinator assigns F-numbers)
| # | Mission | Chunk (LUACH log) | Function | Change | Test | Result | Label |
|---|---|---|---|---|---|---|---|
| F-CAM-camC-1 | M17 cp2 | "level55_lizziesattack.lua" (log, all M17 runs) | `C3.ObjShowive` (08401 main_10), `C3.Multiplayer` (main_11) | F3 wrapper `W4PC_TW`: players 3-4 out of the list before, back at the end after | camc_m17a direct calls on list P1..P4; real cp1 -> cp2: camc_m17n1 (no row), camc_m17n2/g/m (row); 2 players camc_reg4/6 | original: list **P3, P4, Lizzie, Lizzie**, view 1 primary P3 (secondary P1), view 2 primary P4 (secondary P2); wrapped: **Lizzie, Lizzie, P3, P4**, views 1-2 primary Lizzie, secondary own player (2-player list: Lizzie, Lizzie) | **VERIFIED** |
| F-CAM-camC-2 | M17 cp2 | same | `C3.DoorDestroyed` (main_25; split off, shared camera) | F3 wrapper | camc_m17a direct calls; door destroyed by play in camc_m17bt/m17j; camc_reg4/6 (2 players) | original from Lizzie, Lizzie, P3, P4: **Lizzie, P3, P4, P1** (shared camera frames Lizzie + P3); wrapped: **Lizzie, P1, P3, P4** (frames Lizzie + P1 = 2-player result Lizzie, P1) | **VERIFIED** |
| F-CAM-camC-3 | M17 cp2 | same | views 3-4 boss camera (`W4PC_L` from the ObjShowive wrapper + 500 ms tick `W4PC_LT`; `Cleanup` clears) | `CamSetSecondary(own player, 0, 2/3)` = the script's pattern for views 1-2; needs F-CAM-camC-7 and -8 | camc_m17m (real chapter change), camc_m17j (late join, LEAVE + re-join) | all four views primary Lizzie / secondary own player / same eye point; screenshot: four alike | **VERIFIED** (with -7 and -8) |
| F-CAM-camC-4 | M8 cp5 | "level81_chatterbox.lua" (log, camc_m8a) | `C5.ChatterCam` (08839 main_20) | F3 wrapper, players 3-4 kept out | camc_m8a, camc_fin_m8 direct calls; camc_reg3 (2 players) | original with P1..P4: **P3, P4, Chatterbox** -> shared rail frames P3 + P4; wrapped: **Chatterbox** -> rail frames Chatterbox only (= 2 players) | **VERIFIED** |
| F-CAM-camC-5 | M8 cp5 | same | `C5.CamBackToWarriors` (main_21) | F3 wrapper, players 3-4 back at the end | camc_m8a, camc_fin_m8, camc_reg3 | original: **P3, P4, P2, P1** (rail keeps framing P3 + P4); wrapped: **P2, P1, P3, P4** (frames P2 + P1 = 2 players) | **VERIFIED** |
| F-CAM-camC-6 | M1 cp3 | "level99_lesson2.lua" (log, camc_m1s) | `P3.EndChapterScene`, `P3.MoveToClimb`, `P3.Player2Jumps` (set Vermin), `P3.FencePoizoDone`, `P3.PoizoClimb`, `P3.VerminJumped` (clear) | F1 mirror `W4PC_SW`: the index-1 secondary target repeated with index 2/3; 500 ms tick `W4PC_ST` for later joins | camc_m1s, camc_fin_m1 direct calls; camc_m17n1 (late join); camc_reg4 (2 players) | original EndChapterScene: Vermin on views 1-2 only; wrapped: Vermin on all four; wrapped VerminJumped clears all four; players 3-4 joining after the set get Vermin | **VERIFIED** (direct calls; stages not reached by play) |
| F-CAM-camC-7 | M17 (engine) | - | **BOSSTGT**: camtarget cave (views 3-4) | a view-3/4 follow camera whose secondary target is its own player takes list entry 0 as primary target when that entry is a non-player human | camc_m17bt, m17g, m17j, m17m; 2 players camc_reg6 | views 3-4 primary Lizzie only while their secondary is their own player (switched back and forth in camc_m17bt); views 1-2 unchanged | **VERIFIED** |
| F-CAM-camC-8 | all (engine) | - | **CFGFOLLOW**: CfgFollowCamera core FUN_0011C0B8 | copy the new settings from follow[0] to follow[1..3], not only follow[1] | camc_m17h (without) vs camc_m17m (with); camc_reg6 (2 players) | without: views 3-4 boss eye (375.7, 15.3, 6.3), views 1-2 (375.6, 23.1, 6.4); with: all four (375.5-375.8, 23.1, 6.4); 2 players: views 1-2 eye (374.9/374.7, 23.5, 6.3) = camc_m17j | **VERIFIED** |
| F-CAM-camC-9 | all | session LEAVE (audit 5.6) | LEAVE cave 0x000E7100 | none | camc_m1c leave4@11000, camc_m17j leave4@7300 | the leaver's handle is removed (0x413DC; 0xA0394), slot empty / refilled by the refresh with a missing player (P1 in M17) | **VERIFIED** |
| F-CAM-camC-10 | M1 cp2 | "level99_lesson1.lua" (log, camc_m1c) | `P2.SetupLesson1` | **none** | camc_m1c: real cp1 -> cp2 (P1.CombatOver) with 4 players | list P1..P4 -> after the squad swap P1, P2 (players 3-4 dropped by X3, removed from the list by LEAVE, list rebuilt by the gang change) -> re-join P1..P4 | **VERIFIED**: no hazard |
| F-CAM-camC-11 | M17 cp2 | - | `PlayerDied`, `PlayerRevived`, `LizzieBossDamage`, `C3.OutsidePoizo` | none | static | no caller (dead code) | **VERIFIED** (static) |

## 1. Static findings (VERIFIED code, static addresses, SLUS-21215 v1.03; function names are OUR labels)
### 1.1 List operations (0x005D91A8, 4 handles, empty = *(0x006EBD30) = 0xFFFFFFFF)
- `CamTarget(mode, cam, h)` binding 0x00365AD8 -> `FUN_0011C270(mode, cam, h)`; **the camera argument is never read**
  (the core ignores param_2). Mode 0 add `FUN_001222B0(h, 1)`, 1 remove `FUN_00122438(h, 1)`, 2 clear (`FUN_004DAD20`).
- Add (0x001222B0-0x00122434): compact (`FUN_004DAD40`), then, if fewer than 4 entries, insert at the first empty slot
  (`FUN_004DAEF0`) **if the human is not a player (+0x1B0 = -1) or not yet in the list**: players are never doubled,
  bosses can be. M17 relies on it: the 2-player boss list is Lizzie, Lizzie (one entry per view; same handle twice,
  0x30087 / 0x9008E at runtime).
- Remove (`FUN_004DAF70`): the **first** occurrence becomes empty, then compact.
- Follow picker `FUN_001282A0` (all_00.c:27285-27360): split mode, view p < 2 follows the p-th valid entry among
  entries 0-1; views 3-4 follow their own human (camtarget.txt, cave 0x000F0B90-0x000F0BEC). Shared view: up to 2
  targets from entries 0-1 (rail picker `FUN_0013B7B8` the same; RAILTGT for views 3-4).
- `CamSetSecondary(h, w, i)` binding 0x003670C0 -> `FUN_0011DCF0`: follow[i]+0x320 = handle, +0x3FC = weight (index
  default 0). Boss mode: `FUN_00127CD8` uses cam+0x2D0 when the secondary is a player, the target count is 1 and the
  primary target is a non-player; `FUN_0012AE58` (all_00.c:30394-30413) fills +0x2D0 from the secondary player.
- Camera eye point = render camera +0x10 (base class vtable +0x21C = 0x004DB1C8 `addiu v0,a0,16`); used by the probe.
### 1.2 Who else changes the list
- UpdateJoin `FUN_0041A460`: a pad join adds the joining human only (all_07.c:10826-10829); the -1 refresh (join flag
  change, after a LEAVE when 2+ players stay, level start) adds every player who is not in the list, in index order.
- Squad swap `FUN_00239B80` (HuChangePlayerGang): removes every released player from the list and adds the new players
  (all_03.c:2852-2950).
- Session LEAVE 0x000E7100 (mod/m2/session.txt): `FUN_00122248(h)` (in list?) -> `FUN_0011ED60(index)` (camera
  teardown of that view) + `FUN_00122438(h, 1)` (0x000E7170-0x000E7194); then UpdateJoin(-1) if 2+ players stay
  (0x000E7290-0x000E7298). -> no stale handle (5.6).
### 1.3 What the scripts do (2 players) and what the original does with 4 (VERIFIED script; 4-player column measured)
| Function | 2-player list before -> after | 4-player list with the original |
|---|---|---|
| M17 `C3.ObjShowive` + `C3.Multiplayer(player2, 1)` | P1, P2 -> Lizzie, Lizzie (+ secondary player / player2) | P1..P4 -> P3, P4, Lizzie, Lizzie |
| M17 `C3.DoorDestroyed` | Lizzie, Lizzie -> Lizzie, P1 (split off) | Lizzie, Lizzie, P3, P4 -> Lizzie, P3, P4, P1 |
| M8 `C5.ChatterCam` | P1, P2 -> Chatterbox (split off since EndIntroScene) | P1..P4 -> P3, P4, Chatterbox |
| M8 `C5.CamBackToWarriors` | Chatterbox -> P2, P1 | P3, P4, Chatterbox -> P3, P4, P2, P1 |
### 1.4 F3 rule
Take players 3-4 out before the original (so it sees the 2-player list); add them back at the end only when the
2-player result has 2+ entries (otherwise an add would put them into entry 1, e.g. M8 ChatterCam -> Chatterbox, P3).
`W4PC_TW(f, k)`: k set = keep them out (M8 ChatterCam; CamBackToWarriors adds them again 3 s later). Only the outermost
wrapped call does it (depth `W4PC_D`), so `C3.Multiplayer` called from inside `C3.ObjShowive` changes nothing extra.
### 1.5 CfgFollowCamera (CFGFOLLOW)
Binding 0x0036AB88 -> core `FUN_0011C0B8` (all_00.c, 440 bytes): sets distance/angle/FOV/offsets on `FUN_0011F9E0(0,0)`
= follow[0] only, then `if (follow[1]) FUN_00124C28(follow[1], follow[0])` (0x0011C208-0x0011C23C). A camera created
later (join, `FUN_0011EAF0`) copies follow[0] as well, so only players 3-4 who are already in the game when a script
calls CfgFollowCamera miss the change. That is exactly the M17 chapter change with 4 players (camc_m17h: views 3-4 boss
eye 7.8 units from views 1-2's). The level-jump runs (players 3-4 joined after the call) did not show it.

## 2. Deliverables
### 2.1 Rows (local/m6/cam/camC/rows/, group [warriors-4p missions], LUACH rows 12-15 in the test build)
Build: `python -I tools/lua_rows.py build --base mod --region 0x000EB000:0x000EB960 --work local/m6/cam/camC --out
local/m6/cam/camC/test.pnach --title "camC camera rows" local/m6/cam/camC/rows/*.lua` -> 4 rows (names
0x000EB000-0x000EB05F, sources 0x000EB060-0x000EB957), **8012 addresses, 6 problems** (the known [4p hud A]/[4p hud B1]
alternatives).
| Row | Chunk | Chars | Content |
|---|---|---|---|
| 12 camCh (a_camc_helpers.lua) | "global.lua" (a second helper row; runs after the coordinator's) | 1076 | `W4PC_P(i)`, `W4PC_O()` / `W4PC_I(t)` (players 3-4 out / in), `W4PC_TW(f, k)` (F3), `W4PC_SW(f)` + `W4PC_A(all)` (F1 secondary mirror) |
| 13 m17t | "level55_lizziesattack.lua" | 751 | originals `W4PC.o[1..4]` (ObjShowive, Multiplayer, DoorDestroyed, Cleanup); the three wrapped; `W4PC_L` gives views 3-4 their own player as secondary; tick `W4PC_LT`; Cleanup clears views 3-4 |
| 14 m1s | "level99_lesson2.lua" | 291 | six P3.* functions wrapped with `W4PC_SW` (originals `W4PC.p3`); tick `W4PC_ST` |
| 15 m8t | "level81_chatterbox.lua" | 149 | originals `W4PC.cc/bw`; ChatterCam `W4PC_TW(f, 1)`, CamBackToWarriors `W4PC_TW(f)` |
All globals start with `W4PC` (no clash with W4P_*, camB's W4B*). Lua 4.0 only (`call(f, {...; n = 4}, "x")`, `%upvalues`).
Players 1-2 are never changed: the original runs unchanged; only players 3-4 (game index 2/3, neither `player` nor
`player2`) are taken out / put back / given index 2/3.

### 2.2 Engine rules (proposal) - `local/m6/cam/camC/camc_engine_lines.txt`, made by `local/m6/cam/camC/camc_engine.py`
After the rows build: `python -I local/m6/cam/camC/camc_engine.py` (patches the work copy of camtarget.txt, writes
`local/m6/cam/camC/test_bt.pnach`, **8046 addresses, 6 problems**; = `final_bt3.pnach`, the tested file).
- **BOSSTGT** (22 + 2 words): camtarget cave 0x000F0B9C `00000000 -> 3C080051` (lui t0,0x51 in the delay slot of
  `bne at,zero,normal`; t0 is dead after the jalr at 0x00128424) and 0x000F0BA0 `3C080051 -> 0803AE58` (j 0x000EB960;
  its delay slot `lw t0,0x489C(t0)` stays). Cave 0x000EB960-0x000EB9B3 (camC region): own handle ==
  follow cam+0x320 and list entry 0 resolves to a non-player -> `j 0x000F0BB8` with v0 = that human (camtarget's own
  tail stores target and count); else `j 0x000F0BB0` (camtarget's own call).
- **CFGFOLLOW** (13 words in place, 0x0011C20C-0x0011C23C; 0x0011C208 keeps `addiu a0,zero,1`): s1 = &follow[3]
  (0x000F082C, relocated array of [warriors-4p 4p]); loop: a0 = *s1; s1 -= 4; if a0: `FUN_00124C28(a0, *(0x000F0820))`;
  repeat while (s1 & 0xF) != 0 (indices 3, 2, 1). s1 is saved by the prologue (0x0011C0C0).
Both belong next to camtarget.txt / RAILTGT in [warriors-4p 4p]; both need the 4p array relocation.

## 3. Tests (SINGLE-PC, 1 instance, bots, MTVU off; local/m6/cam/camC/run.sh = the brief's nav_probe command)
Players 3-4 join with `x6fix_probe:join34`. `god` = HuSetGodMode for all players (test aid in boss fights); `near34` =
HuTeleportNearHuman(P3, player), (P4, player2). Evidence: `local/m2/<tag>/probes.json` + screenshots, consoles and
emulogs `local/m6/cam/camC/<tag>_console.txt`, `<tag>_emulog.txt`; copies of the probes in `evidence/M6/camc_*.json`.
Pnachs (local/m6/cam/camC/): v1 = first rows (M17 views 3-4 secondary = Lizzie; file overwritten since); final_bt =
final rows + BOSSTGT (earlier cave 0x000EB980, hook 0x000F0BB0); final_bt3 = final rows + BOSSTGT (as in 2.2) +
CFGFOLLOW (= test_bt.pnach of 2.2); test_nom17 = v1 without the M17 row.
| Run (inst) | Pnach | Level jump(s) (CallAt) | Players | What | TLB |
|---|---|---|---|---|---|
| camc_m17a (23) | v1 | M17 cp2 `3999:0041ABC0:2,4009:00160D78:0x01FDA1AC` | 4 (5601) | list after join; set4 + original/wrapped ObjShowive; DoorDestroyed original/wrapped | 0 |
| camc_m8a (24) | v1 | M8 cp5 `0x01FD9D08`, cp 5 | 4 (5601) | ChatterCam / CamBackToWarriors original, then wrapped | 0 |
| camc_m1c (24) | v1 | M1 cp1 `0x01FD996C`, `P1.CombatOver` 7400 -> cp2 | 4 (5804/6100), again 9901 | list through the real cp1 -> cp2 swap; LEAVE(3) | 0 |
| camc_m1s (23) | v1 | M1 cp3 | 4 (5802/6102) | VerminJumped / EndChapterScene original vs wrapped | 0 |
| camc_m17n2 (23) | v1 | M17 cp1, `NextMission()` 7500 | 4 (5501) | real cp1 -> cp2 with the row; views 3-4 secondary Lizzie on/off | 50 (neg. 3) |
| camc_m17n1 (23) | test_nom17 (no M17 row) | M17 cp1 -> NextMission; M1 cp3 at 10000 | 4 (5502); 12501/12800 | real cp1 -> cp2 **without** the row; M1 late join | 50 (neg. 3) |
| camc_reg2 (24) | v1 | M17 cp2, M8 cp5 (6400), M1 cp3 (9200) | 2 | 2-player regression | 22 (neg. 4, method) |
| camc_m17b (24) | v1 + PINE pokes | M17 cp2 | 4 (5304) | BOSSTGT by PINE (did not stick) | 0 |
| camc_reg3 (23) | v1 | M8 cp5, M1 cp3 (7300) | 2 | 2-player M8 (M1 part lost: game over) | 0 |
| camc_m17bt (24) | v1 + BOSSTGT test (cave 0x000EFC00) | M17 cp2 | 4 (5303) | views 3-4 secondary own player with BOSSTGT, on/off | 0 |
| camc_m17g (24) | final_bt | M17 cp1 -> NextMission | 4 (5505) | real cp1 -> cp2 | 50 (neg. 3) |
| camc_reg4 (23) | final_bt | M1 cp3, M17 cp2 (7000) | 2 | 2-player regression | 0 |
| camc_m17h (24) | final_bt | M17 cp1 -> NextMission | 4 (5502) | eye points: views 3-4 off (no CFGFOLLOW) | 50 (neg. 3) |
| camc_m17j (23) | final_bt | M17 cp2 | 4 (5303), LEAVE(3) 7302, re-join 7800 | late-join tick, LEAVE + re-join, eye points | 0 |
| camc_m17k (24) / camc_reg5 (23) | final_bt + CFGFOLLOW v1 (`FAILED_cfgfollow_v1.pnach`) | M17 cp1 -> NextMission / M17 cp2 | 4 / 2 | **frozen** (neg. 2) | 50 / 50 (pc 0x0011FA9C) |
| camc_m17m (24) | final_bt3 | M17 cp1 -> NextMission | 4 (5505) | real cp1 -> cp2, final | 50 (neg. 3, NextMission signature) |
| camc_reg6 (23) | final_bt3 | M17 cp2 | 2 | 2-player regression, final | 0 |
| camc_fin_m1 (23) / camc_fin_m8 (24) | final_bt3 | M1 cp3 / M8 cp5 | 4 (5704/6007; 5406) | final check of the M1 and M8 rows | 0 / 0 |

Key readouts (list = 0x005D91A8 as players or `ai<char id>`; ai237 = Lizzie, ai135 = Chatterbox, ai26 = Teacher Vermin):
1. **M17 real chapter change, 4 players:** without the row (camc_m17n1 7807-9509): P3, P4, Lizzie, Lizzie; view 1
   primary P3 / secondary P1, view 2 primary P4 / secondary P2. With the final row + rules (camc_m17m 7803-9200):
   Lizzie, Lizzie, P3, P4; all four views primary Lizzie / secondary own player, eye points (375.8, 23.1, 6.4),
   (375.7, 23.1, 6.4), (375.8, 23.1, 6.4), (375.5-375.7, 23.1, 6.4); render camera handles of views 1-2 unchanged
   through join, chapter change and the rules (0xCAB800 / 0xCDB000 in camc_m17g).
2. **M17 direct calls** (camc_m17a): 2-player start list Lizzie, Lizzie (5001); after joins Lizzie, Lizzie, P3, P4
   (6603); set4 + original ObjShowive -> P3, P4, Lizzie, Lizzie with views 1-2 on P3/P4 (7004); set4 + wrapped ->
   Lizzie, Lizzie, P3, P4 (7504). DoorDestroyed original -> Lizzie, P3, P4, P1, shared camera targets Lizzie + P3
   (8004); wrapped -> Lizzie, P1, P3, P4, targets Lizzie + P1 (8508).
3. **M17 late join / leave** (camc_m17j, final_bt): players 3-4 joined after the boss start (5303) -> tick -> views 3-4
   primary Lizzie / secondary own, eye (374.4-374.9, 23.4-23.5, 6.3) like views 1-2. LEAVE(3): handle 0xA0394 removed;
   the LEAVE refresh put P1 into the free slot (Lizzie, Lizzie, P3, P1: views 1-2 unaffected); re-join 7800 -> the new
   player 4 got the boss camera by the tick (8303).
4. **M8** (camc_m8a): natural P1..P4, shared rail targets P1 + P2 (6800); original ChatterCam -> P3, P4, Chatterbox,
   rail targets **P3 + P4** (7005); original CamBackToWarriors -> P3, P4, P2, P1, rail still P3 + P4 (7503); set4 +
   wrapped ChatterCam -> Chatterbox, rail target Chatterbox (8304); wrapped back -> P2, P1, P3, P4, rail P2 + P1 (8804).
5. **M1 cp3** (camc_m1s): original EndChapterScene -> Vermin on views 1-2, none on 3-4 (7905); wrapped VerminJumped
   clears all (8409); wrapped EndChapterScene -> Vermin on all four (8610). Late join (camc_m17n1): Vermin set with 2
   players (12004), players 3-4 join 12501/12800 -> Vermin on all four by 13100.
6. **M1 cp2** (camc_m1c): cp1 list P1..P4 (7200) -> after P1.CombatOver and P2.SetupLesson1: count 2, list P1, P2
   (7702-9700) -> re-join P1..P4 (10800) -> LEAVE(3): P1, P2, P3, empty; handle 0x413DC no longer in the list.
7. **2 players** (camc_reg3, reg4, reg6): M8 wrapped ChatterCam -> Chatterbox, back -> P2, P1 (= original); M17 natural
   Lizzie, Lizzie with secondaries P1/P2; set4 [P1, P2] + wrapped ObjShowive -> Lizzie, Lizzie; wrapped DoorDestroyed ->
   Lizzie, P1; M1 wrapped EndChapterScene -> Vermin on views 1-2, wrapped VerminJumped clears. With final_bt3 (reg6) the
   eye points of views 1-2 (374.9/374.7, 23.5, 6.3) equal camc_m17j's. Markers: helpers 1 everywhere, M17 row 1 in
   level 55, M8 row 1 in level 81, M1 row 1 in level 99.
8. **Final pnach (final_bt3) checks with 4 players:** camc_fin_m1 (M1 cp3): wrapped EndChapterScene -> Vermin on all four
   views (6907), wrapped VerminJumped clears all four (7406), original EndChapterScene -> views 1-2 only (7903); 0 TLB.
   camc_fin_m8 (M8 cp5): natural P1..P4, rail P1 + P2 (6405); wrapped ChatterCam -> Chatterbox only (6902); wrapped
   CamBackToWarriors -> P2, P1, P3, P4, rail P2 + P1 (7401); 0 TLB. Its last control call (7600) did not run: "GAME OVER -
   You fell to your death" at ~7600 (idle bots in the Chatterbox arena; the same game over happened in the 2-player run
   camc_reg3, so it is not caused by players 3-4 or the rows - HYPOTHESIS: knocked into the pit).

## 4. Screenshots (whole 2x2 window, local/m2/<tag>/)
| What | Before | After |
|---|---|---|
| M17 real chapter change | camc_m17n1 t0370_p8688, t0407_p9497 (top quarters: close shots of other people) | camc_m17m t0319_p8197, t0344_p8906 (all four quarters: the same boss picture) |
| M17 players 3-4 without CFGFOLLOW | camc_m17g t0370_p8219 (top: boss picture; bottom pair: another part of the room) | camc_m17m t0319_p8197 |
| M17 direct call | camc_m17a t0645_p7304 (top-left dark, top-right a close-up of player 4) | camc_m17a t0703_p7791 |
| M17 views 3-4, level jump | camc_m17bt t0340_p6761 (bottom quarters: wall / close-up) | camc_m17bt t0411_p7333, t0511_p7985 (all four alike) |
| M17 door (shared) | camc_m17a t0774_p8314 (Lizzie + P3) | camc_m17a t0827_p8806 (Lizzie + P1) |
| M8 Chatterbox knocked down (shared) | camc_m8a t0553_p7298 (players 3-4 in the foreground, Chatterbox far away) | camc_m8a t0699_p8529 (Chatterbox close-up) |
| M1 cp3 Vermin secondary | camc_m1s t0320_p8252 (bottom quarters look away from the court) | camc_m1s t0345_p8964 (all four toward the basketball court where Vermin is) |

## 5. Files
- New: `local/m6/cam/camC/rows/{a_camc_helpers,m17t,m8t,m1s}.lua`, `tests/m6/cam_camC_probe.py`,
  `local/m6/cam/camC/{run.sh, show.py, eyes.py, camc_engine.py, camc_engine_lines.txt, p1_*.txt}`, test pnachs
  `local/m6/cam/camC/{test,test_bt,final_bt3,test_nom17}.pnach`, `evidence/M6/camc_*.json`, this note.
- Not changed: `mod/` (incl. `mod/w4p_m1.pnach`), shared probe files, emulator.

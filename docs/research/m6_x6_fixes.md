# M6 X6 script fixes for players 3-4: M16/M18 camera handlers, M11 cash, tagging spray (LUACH rows, 2026-10-12)

## Plain-English summary
- **What this is.** The game's mission logic is Lua. Our LUACH hook (m6_x4_x6.md) runs a short piece of our own Lua
  right after a named script file loads. This note adds nine such rows to `mod/m2/missions.txt`: one row of shared
  helpers (after "global.lua", in every level) and one row per fixed file.
- **Mission 16 gate (fixed, tested).** When a player picks the alley gate lock, the script resets "the" camera with
  index 0 (player 1) unless the picker is player 2. Example: player 3 picks the lock -> before, player 1's follow camera
  was moved; now player 3's own camera (index 2) is used and the gate still opens. Runtime: camera calls 0,0,0 before,
  2,2,2 after; only view 3's camera fields changed.
- **Mission 16 camera volumes (guard added, but the problem cannot happen by walking).** The chase camera volumes are a
  kind of box that only ever notices players 1 and 2 (the game loops over 2 players). Tested: player 3 stood inside one
  for about 250 polls and the handler was never called; player 1 walking in was reported at once. The guard stays as
  a safety net (calling the old handler directly for player 3 did rebuild player 1's rail camera on player 3).
- **Mission 13 subway trigger (earlier row).** Same box kind: player 3 cannot set it off by walking either (static
  check). The earlier guard is therefore a safety net too, not a fix for something players would hit.
- **Mission 18 final fight zoom zone (fixed, tested by direct calls).** This box notices every human. Before, a player
  3/4 entering it rebuilt **player 2's** rail camera around himself (direct call: rail index 1 on player 3). Now he is
  ignored; player 1 still gets his zoom. Walk-in: player 3 put into the zone was noticed by the box and the guarded
  handler built nothing; the matching player-1 walk-in check did not work (player 1 was moved away at once).
- **Mission 11 "get $75" (fixed, tested end to end).** The objective only added up players 1-2's money. Example from the
  test: players 1-2 have $0, players 3-4 have $40 each. Before: not enough, nothing happens. After: the $75 is paid
  (player 3 $40 -> $0, player 4 $40 -> $5) and the mission moves on to the gambling club (checkpoint 3).
- **Tagging (fixed in M3, M6, M13; see test table).** When player 3/4 starts a tag, the scripts looked at player 1's
  spray cans (M3, M13) or at nobody's (M6: player number 0, so players 3-4 could never tag there). Now they look at the
  tagging player's own cans (the game's own `HuGetHUD` gives his inventory number). The game's engine already used his
  own cans when spraying.
- **Negative results first:** (1) two of my test methods failed - a teleport into a far camera box dropped player 3
  through the world and stopped the test (run x6f_m16), and creating extra volume boxes from Lua **crashed the game
  (38 TLB misses, run x6f_m16b)** because each level has a fixed number of boxes. Neither is part of the fix; the rows
  never create boxes or teleport. (2) The M16 gate was tested by direct calls only (no real lock pick by player 3); the
  M18 walk-in has no working player-1 control. (3) M18 cp2 `C1.CAMChange` (same "player 2 or else player 1" camera pattern, type-0 boxes) is NOT patched:
  players 3-4 cannot be in cp1-cp2 (joining is off there by the script, X13), so it was not testable.
- Everything: SINGLE-PC, one instance at a time (sandboxes 10 and 11), scripted bots, no impairment, MTVU off, no human
  play. Mission completion with humans is not tested.

Build: The Warriors SLUS-21215 v1.03 (`local/disc/SLUS_212.15`, read-only), fork build w4p-m6-1 (not rebuilt;
`emulator/` untouched). Builds on `m6_x4_x6.md` (LUARUN / LUACH, table 0x000E7F00, the M13 row), `m6_missions.md` (M3,
M6, M11, M13, M16, M18 and 1.3/1.4), `m2_inventory34.md` (player number = slot + 1). Function and structure names are
OUR labels (the ELF is stripped); addresses static unless marked dynamic. Labels: VERIFIED (with pointer), HYPOTHESIS,
BLOCKED, FAILED TEST. `mod/w4p_m1.pnach` was NOT regenerated (a 4-instance batch reads it); every test used
`local/m6/x6/test.pnach` = `python -I mod/make_pnach.py` with the final `mod/m2/missions.txt`.

## Per-fix table
| # | Mission | File (LUACH row name, from the runtime log) | Function | Change | Test | Result | Label |
|---|---|---|---|---|---|---|---|
| 1 | M16 (level54) | "level54.lua" | `chase.CamSwitcher` (08262 main_97) | `W4P_G34` guard: a player 3/4 is ignored | x6f_m16 / x6f_m16c: direct call as player 3 with a CamSetupRail spy; walk-in into camswitch[7] | guarded P3: no rail (100); original P3: rail index 0 = **player 1's** on P3 (213); P1: index 0 on P1 (211). **Walk-in: player 3 inside a camswitch box for ~250 polls is never reported** (100); player 1 at once (111) | **VERIFIED**; reachable only by a direct call, not by walking (type-2 box) |
| 2 | M16 | "level54_alley.lua" | `ch2.GatePicked` (08349 main_27) | not a guard (the gate must still open): during the call by player 3/4, `CameraGetActive` / `CamSetFollowPos` / `CamSetFollowZoom` use **his own view index** (W4P_GPW) | x6f_m16: direct calls with spies; real call with PINE snapshot of the follow cameras | fixed P3: indices 2,2,2 + CameraMakeActive for P3 (333 / 3); original P3: 0,0,0 (111 / 3) = player 1's camera; P1: 0,0,0 (111 / 1). Real call: **only view 3's follow camera** (0x00D1C800 +0x240..+0x248) changed, views 1, 2, 4 unchanged | **VERIFIED** (direct call; a real lock pick by player 3 not exercised) |
| 3 | M18 (level84) | "level84_final.lua" | `C5.MoveInFOV`, `C5.MoveOUTFOV` (09112 main_29/30) | `W4P_G34` guard on both | x6f_m18: direct calls with a CamSetupRail spy; x6f_m13m18: walk-in | guarded In/Out for P3: no rail (100/100); original In for P3: rail index 1 = **player 2's** on P3 (223); P1: index 0 on P1 (211). **Walk-in (x6f_m13m18): player 3 put into vFOVZoom was reported by the type-0 box (MoveInFOV called once for him) and no rail was built (110)**; the player-1 walk-in control was inconclusive (player 1 was moved out of the zone right after the teleport, no call, R 0) | **VERIFIED** (direct calls + player 3 walk-in); walk-in positive control inconclusive |
| 4 | M11 (level31) | "level31_Streets.lua" | `P2.AtGamblingClub`, `P2.GetMoney`, `P2.MoneyCheck`, `P2.GotMoney` (07918 main_21/22/24/27) | during these calls `InvGetMoney(2)` = players 2+3+4 and `TakeMoney(n, 2)` takes from players 2, 3, 4 in turn (W4P_SUMW) | x6f_m11: money P1-P4 = 0/0/40/40, then the original and the fixed `P2.GotMoney(nil, true)` | sum helper 80 (InvGetMoney(2) alone 0); **original: no payment, checkpoint stays 2**; **fixed: paid 75 (P3 40 -> 0, P4 40 -> 5), SetCheckPoint(3), "level31_gclub.lua" loaded** | **VERIFIED** (end to end on the payment path; HUD text not checked) |
| 5 | M3 (level87) | "level87.lua" | `SpotGettingTagged` (09171 main_130) | spray check of a player 3/4 uses his own count: `InvGetSpraycanCharges(HuGetHUD(A1) + 1)` during the call (W4P_TAGW) | x6f_m3m6: stubbed HuTag / no-paint sound spies, both spray combinations; then one real tag | P1 0 / P3 3: fixed -> HuTag for P3, reads P3 (300 / 3); original -> no-paint sound, reads P1 (30 / 11). P1 3 / P3 0: fixed -> no paint (30 / 3); original -> HuTag on P1's paint (300 / 11). P1: unchanged (100 / 11). **Real tag: player 3 tagging (HuIsTagging), his own cans 3 -> 2**, player 1's stay 0 | **VERIFIED** |
| 6 | M6 (level3) | "level3_comp.lua" | `C1.WarrTagStart` (08023 main_32) | same (W4P_TAGW) | x6f_m3m6 (M6 cp2 after a second level jump) | fixed P3 -> HuTag for P3, reads P3 (300 / 3); original asks player number **0** -> no paint (30 / 10) | **VERIFIED** |
| 7 | M6 | "level3_gallery.lua" | `C5.WarrTagStart` (08024 main_10) | same | x6f_m13m6 (M6 cp5) | fixed reads P3 (R2 3), original player number 0 (R2 10). R 0 in both: the original's "no paint" path has no sound call in this handler (08024 disassembly main.10 #58-68), so 0 is expected there; the fixed call stopped between the spray check and HuTag, where the only new read is `Objects[GetIndex(A0, fTagGallery)]` (HYPOTHESIS: not set up at that point of the test; cause not investigated) | **VERIFIED** for the count that is read; the rest of the handler not exercised |
| 8 | M13 (level9) | "level9.lua" (second row) | `WarriorTagging` (09229 main_78) | same | x6f_m13m6 (no tag object), x6f_m13m18 (real tag object) | no object: fixed reads P3 (R2 3), original P1 (11) + no-paint sound. Real tag object (x6f_m13m18, `master[..][..][..].Left`): fixed -> HuTag for P3, reads P3 (300 / 3); original -> no-paint sound, reads P1 (30 / 11) | **VERIFIED** |
| 9 | all | "global.lua" | helpers | `W4P_O` (originals + markers for tests), `W4P_G34`, `W4P_P34`, `W4P_GPW`, `W4P_TAGW`, `W4P_IGM2`, `W4P_TM2`, `W4P_SUMW` | every run: markers read back | helpers present in every level tested (M3, M6 cp2/cp5, M11, M13, M16, M18) | **VERIFIED** |
| - | M18 cp2 | "level84_chase.lua" (not added) | `C1.CAMChange` (09110 main_17) | **NOT APPLIED** | - | same pattern (hood/fixed cameras made active on view 0, "player else player2" branch) on type-0 boxes, but players 3-4 cannot be in cp1-cp2 (joining off by the script, m6_missions.md M18, X13) | HYPOTHESIS (unreachable) |
| - | M13 | "level9.lua" (row 0, earlier) | `EnterGraveTrain` | unchanged | static only | its boxes `vbInTrain` are type 2, so player 3/4 never trigger it by walking (section 1.1); the guard is a safety net | VERIFIED (static) |

Every test run: **0 TLB misses** except x6f_m16b (38, caused by the test itself, negative result 1). Markers read back
(each row stores the original function in `W4P_O` and a marker; "wrapped" = the global is no longer the original):
M16 111, M18 11, M11 11, M3 11, M6 cp2 11, M6 cp5 11, M13 111. LUACH run counter LC_RUNS matches the rows
expected per level (front end + M1 helper rows = 2, then M16 +3, M18 +2, M11 +2, M3 +2, M6 +2, M13 +3 incl. row 0) in
every run, so no row failed to compile (a Lua error in a row would leave its marker unset).

## Negative results and open points (read these first)
1. **FAILED TEST (method), x6f_m16b: creating volume boxes from Lua crashed the game: 38 TLB misses** (first at
   pc 0x004128E8 addr 0x67 [store], then pc 0x004314F8 addr 0x58..; `local/m6/x6/x6f_m16b_emulog.txt`). AddVolumeBox
   takes boxes from per-level pools sized at level load (FUN_0041D628 -> FUN_00413218(count) for type 2, from a
   per-level count table); a full pool returns 0 and FUN_004125B8 then writes the name into object 0. The rows never
   call AddVolumeBox; the probe functions that did were removed from `tests/m2/x6fix_probe.py`.
2. **FAILED TEST (method), x6f_m16: a teleport of player 3 into camswitch[12], far from the players, dropped him through
   the world** (z -234.4 at 11300); GameMgr+0x14C became 1 and the test-call mailbox stopped (PINE probes after poll
   10500 did not run). The later walk-in tests teleport only next to player 1 at his height (camswitch[7]) or along the
   same line in the same arena (vFOVZoom).
3. **M16 camswitch and M13 vbInTrain cannot be triggered by players 3-4 at all** (type-2 boxes, loop bound 2 at
   0x004136B0; runtime: player 3 inside camswitch[7] never reported). So the bug the M13 row and the M16 CamSwitcher row
   guard against is reachable only by a direct call; the rows are safety nets. The same fact means **players 3-4 never
   advance a story step that sits on a type-2 box** (by design of the original: only players 1-2 count there).
4. **M18 walk-in is only half proven:** player 3 inside vFOVZoom reached the guarded handler and built no rail
   (x6f_m13m18 fov3_read1 = 110), but the positive control did not work: after `Teleport(player, ...)` into the zone,
   player 1 stood at (-402.7, -280.1) 9 polls later and back at (-331.8, -222.9) at poll 16261 (moved by something in
   the cp3 script or arena; cause not investigated), so no MoveInFOV call for player 1 was seen (fov3_read2 = 0). The
   direct-call positive control (mi_p1 = 211) stands. Player 4, pulled into the zone by X4 at player 1's teleport,
   built no rail either (rail count stayed 0).
5. **Not exercised:** a real lock pick by player 3 in M16 (whether players 3-4 can use the lock-pick mini-game at all is
   HYPOTHESIS); the M11 objective HUD text ("$x / 75" counts every money change through `CfgMoneyCallback`, which already
   included players 3-4's pick-ups, HYPOTHESIS); checkpoint reloads with these rows (expected to work because the Lua
   state and the rows are rebuilt at every level load, m6_x4_x6.md 2.3); human play; sessions with 4 PCs.
6. **Error path:** the swapping wrappers (W4P_GPW, W4P_TAGW, W4P_SUMW) call the original through Lua's protected
   `call(f, {...; n = N}, "x")` (base library entry `call` 0x00325800, registered in the game's luaL_reg table 0x00574D78),
   so a script error inside the original cannot leave `CameraGetActive`, `InvGetSpraycanCharges`, `InvGetMoney` or
   `TakeMoney` swapped; in that (never observed) case the handler returns nil instead of raising the error.
7. M6 `C5.WarrTagStart` (cp5) and the first M13 test did not reach HuTag (no valid tag object / table in the test):
   they show which count is read, not the full tag start (M3, M6 cp2 and the M13 real-object test show the full path
   for the same wrapper).
8. M11 bum hiring (07917:199-235) still uses players 1-2's money only (LOW, not changed); M4 loot start value
   (07968:273) not changed.

## 1. Static findings that decide each fix (VERIFIED code/script text, static addresses, SLUS-21215 v1.03)

### 1.1 Volume boxes: two kinds, and players 3-4 only trigger one of them
`AddVolumeBox(name, type, corner, size)` (binding 0x0037AC70 -> FUN_004125B8, switch table 0x00588F00) builds:
| Type | Pool / constructor | Vtable | Update (vtable +0x54, run every 5th frame by FUN_00412CA0) | Who triggers enter (msg 3) / leave (msg 4) |
|---|---|---|---|---|
| 0 | 0x0051483C / FUN_004151C0 | 0x00545DF8 | FUN_00415378 | **any human** near the box (FUN_002274A8 list, up to 60), per-human inside list at +0x70 (60 entries) |
| 2 | 0x00514814 / FUN_004133D0 | 0x00545CB8 | FUN_004134F8 | **only GameMgr+0x228 / +0x22C = players 1-2**: loop bound `sltiu v0,s4,2` at 0x004136B0; inside list at +0xF0 has 2 entries |
| 3 | 0x00514834 (vtable call) | - | not read | (turf boxes, not used here) |

So a player 3/4 never fires a type-2 box (none of our patches widens 0x004136B0; grep of the generated pnach).
Boxes in the handlers that matter: M16 `camswitch[1..14]` = type 2 (08262:1522-1540); M13 `vbInTrain[1..3]`
(EnterGraveTrain, `09720` disassembly main.2 #108-115) = type 2 (09229:1522-1526); M18 `vFOVZoom` = **type 0**
(09030:1412; handlers C5.MoveInFOV / C5.MoveOUTFOV 09112:457-458, 698-699); M18 cp2 `VCarChaseTrig[*]` = type 0
(09030:1355-1364, handler C1.CAMChange 09110:216).

### 1.2 Per-view camera index for players 3-4
CamSetupRail core FUN_0011CCE8(..., index) gets the rail camera of a view through FUN_0011FBB0(index, 1);
CamSetFollowPos core FUN_0011C638(vec, index) uses FUN_0011F9E0(index, 0); CameraGetActive core FUN_0011B838 ->
FUN_0011F9B0(index). All three per-view arrays are relocated to 4 entries by `[warriors-4p 4p]`
(m2_pads_cameras.md 2.1: 0x000F0800 + k*0x10), so index 2/3 are valid there. CameraMakeActive core FUN_0011B770 takes
the view from the human (+0x1B0 = player index), which is why the original handlers hit **the entering player's own
view** with a camera built in **player 1's (or 2's) rail slot** (M13 x4x6b g5).

### 1.3 Per-player inventory number of a human
Lua `HuGetHUD(h)` (binding 0x0035D0C8 -> FUN_00239850) returns human+0x380 = the HUD slot (2/3 for players 3-4 with
`[4p hud B1]`), and the inventory bindings take player number = slot + 1 (m2_inventory34.md section 2). So
`HuGetHUD(h) + 1` is a clean per-player number for `InvGetSpraycanCharges`, `InvGetMoney`, `TakeMoney`.
The engine's own tag start (HuTag core FUN_00238DB0, all_03.c ~2283) already checks **the tagger's own** spray
(`InvCount(GameMgr+0x480, human+0x380, 3) > 0`, else "no paint" sound 0x25 and message 14) and consumes from his
own slot (all_02.c:56799); only the scripts ask for player 1's count.

## 2. The rows (`mod/m2/missions.txt`, group [warriors-4p missions])
LUACH table 0x000E7F00 (8 bytes per row {chunk name, Lua source}, source 0 = end): row 0 = the earlier M13 camera
guard (source 0x000E7E00 unchanged; its name "level9.lua" moved from 0x000E7F40 to 0x000EC000 so the table can grow),
rows 1-9 below, row 10 = end at 0x000E7F50; 0x000E7F58-0x000E7F7F free (5 more rows). Names and sources:
**0x000EC000-0x000ECA53** (new; grep of the generated pnach: nothing else in 0x000E8A10-0x000EFFFF; F-0125: zero in
gameplay). All words are `patch=0` (startup only) data. The LUACH code itself is unchanged.

| Row | Name | Source address, length | Source (Lua 4.0, one line in the pnach) |
|---|---|---|---|
| 1 | "global.lua" | 0x000EC090, 1629 | helpers (below) |
| 2 | "level54.lua" | 0x000EC6F0, 90 | `W4P_O.cs = chase.CamSwitcher chase.CamSwitcher = W4P_G34(chase.CamSwitcher) W4P_O.m16a = 1` |
| 3 | "level54_alley.lua" | 0x000EC74C, 81 | `W4P_O.gp = ch2.GatePicked ch2.GatePicked = W4P_GPW(ch2.GatePicked) W4P_O.m16b = 1` |
| 4 | "level84_final.lua" | 0x000EC7A0, 138 | `W4P_O.mi = C5.MoveInFOV W4P_O.mo = C5.MoveOUTFOV C5.MoveInFOV = W4P_G34(C5.MoveInFOV) C5.MoveOUTFOV = W4P_G34(C5.MoveOUTFOV) W4P_O.m18 = 1` |
| 5 | "level31_Streets.lua" | 0x000EC82C, 196 | `W4P_O.gm = P2.GotMoney P2.AtGamblingClub = W4P_SUMW(P2.AtGamblingClub) P2.GetMoney = W4P_SUMW(P2.GetMoney) P2.MoneyCheck = W4P_SUMW(P2.MoneyCheck) P2.GotMoney = W4P_SUMW(P2.GotMoney) W4P_O.m11 = 1` |
| 6 | "level87.lua" | 0x000EC8F4, 89 | `W4P_O.t3 = SpotGettingTagged SpotGettingTagged = W4P_TAGW(SpotGettingTagged) W4P_O.m3 = 1` |
| 7 | "level3_comp.lua" | 0x000EC950, 85 | `W4P_O.t6a = C1.WarrTagStart C1.WarrTagStart = W4P_TAGW(C1.WarrTagStart) W4P_O.m6a = 1` |
| 8 | "level3_gallery.lua" | 0x000EC9A8, 85 | `W4P_O.t6b = C5.WarrTagStart C5.WarrTagStart = W4P_TAGW(C5.WarrTagStart) W4P_O.m6b = 1` |
| 9 | "level9.lua" | 0x000ECA00, 83 | `W4P_O.t13 = WarriorTagging WarriorTagging = W4P_TAGW(WarriorTagging) W4P_O.m13t = 1` |

Helpers (row 1, shown on several lines here):
```
W4P_O = {}
function W4P_G34(f) return function(a0, a1) if HuIsAPlayer(a1) and a1 ~= player and a1 ~= player2 then return end
  return %f(a0, a1) end end
function W4P_P34(h) if HuIsAPlayer(h) and h ~= player and h ~= player2 then for i = 2, 3 do
  if HuGetPlayer(i) == h then return i end end end return nil end
function W4P_GPW(f) return function(a0, a1) local v = W4P_P34(a0) if v == nil then return %f(a0, a1) end
  local g, p, z = CameraGetActive, CamSetFollowPos, CamSetFollowZoom
  CameraGetActive = function(i) return %g(%v) end CamSetFollowPos = function(q, i) return %p(q, %v) end
  CamSetFollowZoom = function(q, i) return %z(q, %v) end local r = call(%f, {a0, a1; n = 2}, "x")
  CameraGetActive, CamSetFollowPos, CamSetFollowZoom = g, p, z return r end end
W4P_IGSC = InvGetSpraycanCharges
function W4P_TAGW(f) return function(a0, a1, a2) if W4P_P34(a1) == nil then return %f(a0, a1, a2) end
  local g = InvGetSpraycanCharges InvGetSpraycanCharges = function(p) return W4P_IGSC(HuGetHUD(%a1) + 1) end
  local r = call(%f, {a0, a1, a2; n = 3}, "x") InvGetSpraycanCharges = g return r end end
W4P_IGM = InvGetMoney W4P_TM = TakeMoney
function W4P_IGM2(p) if p == 2 then return W4P_IGM(2) + W4P_IGM(3) + W4P_IGM(4) end return W4P_IGM(p) end
function W4P_TM2(n, p) if p ~= 2 then return W4P_TM(n, p) end for q = 2, 4 do local m = W4P_IGM(q)
  if m > n then m = n end if m > 0 then W4P_TM(m, q) n = n - m end end end
function W4P_SUMW(f) return function(a, b, c) local g, t = InvGetMoney, TakeMoney
  InvGetMoney, TakeMoney = W4P_IGM2, W4P_TM2 local r = call(%f, {a, b, c; n = 3}, "x")
  InvGetMoney, TakeMoney = g, t return r end end
W4P_O.h = 1
```
Design notes:
- **Players 1-2 are never changed**: every wrapper calls the original unchanged unless the human is a player who is
  neither `player` nor `player2` (W4P_G34 / W4P_P34; the same test as the M13 row).
- **W4P_P34** returns the game player index (HuGetPlayer(i) == h, i = 2/3); the per-view camera arrays and
  CameraMakeActive both use that index (human+0x1B0), runtime-checked: player 3 = index 2 = HUD slot 2 in every run.
- **W4P_TAGW** uses `HuGetHUD(h) + 1` = the inventory player number (HUD slot + 1), the slot the engine itself uses for
  his spray (section 1.3); players 1-2 keep the original "1, or 2 for player2" rule.
- **W4P_SUMW** changes the money functions only during the four P2.* calls (not for the whole level: the later bum hiring
  in "level31_Sewers" still uses players 1-2 as before). Nested wrapped calls are safe (W4P_IGM2/W4P_TM2 use the saved
  originals, not the current globals).
- Rows are keyed by the chunk names seen in the LUACH log (runtime, all runs): "global.lua", "level54.lua",
  "level54_alley.lua", "level84.lua", "level84_final.lua", "level31.lua", "level31_Streets.lua" (capital S kept),
  "level31_gclub.lua", "tag1.lua", "level87.lua", "level87_chap2_street1.lua", "tag7.lua", "level3.lua",
  "level3_comp.lua", "level3_gallery.lua", "tag3.lua", "level9.lua", "level9_chap1_radio.lua". "global.lua" loads
  before the level's own files in every level tested (log order), so the helpers exist when rows 2-9 run.
- Size and checks: `mod/m2/missions.txt` alone 431 -> **1107 addresses, 0 problems** (+676 data words);
  `python -I tools/note_patches.py check local/m6/x6/test.pnach` (the tested pnach) -> **4933 addresses, 6 problems**;
  the current sources at 09:00 (other agents meanwhile added groups) -> **5651 addresses, 6 problems**; the 6 are the
  known `[4p hud A]` vs `[4p hud B1]` alternatives. The `[warriors-4p missions]` group is byte-identical in both. Other
  groups now use 0x000E8A10-0x000E8A2F and 0x000E8B60-0x000E9793; no overlap with 0x000EC000-0x000ECA53.

## 3. Tests (SINGLE-PC, one instance at a time, sandboxes 10/11, scripted bots, no impairment, MTVU off)
Common command (`x6f_run.sh` in the session scratchpad; per run only tag, instance, CallAt and probes differ):
```
python -I tests/m2/nav_probe.py <tag> tests/m2/nav/boot_to_m1_2p.txt --inst <10|11> --players 4
  --script2 tests/m2/nav/p2_join.txt --script3 tests/m2/nav/empty.txt --script4 tests/m2/nav/empty.txt
  --groups "warriors-4p own view;warriors-4p hud;warriors-4p 4p;warriors-4p test call;warriors-4p 4p hud B1;
  warriors-4p 4p hud B2;warriors-4p 4p spawn;warriors-4p 4p spawn leave;warriors-4p 4p inventory;warriors-4p 4p fx;
  warriors-4p 4p markers;warriors-4p session;warriors-4p missions" --ini EmuCore/Speedhacks/vuThread=false
  --callat "4000:0041ABC0:<cp>,4010:00160D78:<entry>[,...]" --patch local/m6/x6/test.pnach
  --probe x6fix_probe:<function>:<poll> ... --seconds 460-680
```
`local/m6/x6/test.pnach` = `python -I mod/make_pnach.py` with the final `mod/m2/missions.txt` (the rows come from the
pnach; no PINE writes to the LUACH table). Players 3-4 join at poll ~8800 through the game's UpdateJoin
(`x6fix_probe.join34`, what W4P X11 does in sessions, F-0183; only in quiet gameplay) - count 2 -> 4 in every run.
Results come back as player 1's money (InvSetMoney channel, restored after each read). Evidence: `local/m2/<tag>/probes.json`
(screenshots alongside), consoles and emulogs `local/m6/x6/<tag>_console.txt`, `<tag>_emulog.txt`.

| Run (sandbox) | Level jump(s) (CallAt) | Players 3-4 | Probes (poll: result) | TLB |
|---|---|---|---|---|
| x6f_m16 (10) | M16 cp2: `4000:0041ABC0:2,4010:00160D78:0x01FDA128` | joined 8807 (2 -> 4) | log 5504: "global.lua", "level54.lua", "level54_alley.lua", LC_RUNS 5; markers 111; cs_p3 100; gp_p3 333/3; gp_p1 111/1; gp_orig_p3 111/3; gp_real_p3: only view 3's follow camera changed; **walk_setup: player 3 teleported into camswitch[12] fell to z -234.4, GameMgr+0x14C = 1, later probes did not run (FAILED TEST, method)** | 0 |
| x6f_m16b (11) | M16 cp2 | joined 8805 | markers 111; cs_p3 100; **box test: AddVolumeBox from Lua crashed the game at poll 10050 (FAILED TEST, method)** | **38** |
| x6f_m16c (10) | M16 cp2 | joined 8804 | markers 111; cs_p3 100; walk7 player 3 inside camswitch[7] (4 units from player 1): **100** (inside, never reported); player 1 inside: **111** (reported, by player 1; player-3 calls 0); cs_orig_p3 **213**; cs_p1 **211** | 0 |
| x6f_m18 (11) | M18 cp3: `4000:0041ABC0:3,4010:00160D78:0x01FDA230` | joined 8803 | log: "level84.lua", "level84_final.lua"; markers 11; mi_p3 **100**; mo_p3 **100**; mi_orig_p3 **223**; mi_p1 **211**; walk-in skipped (box 125 units away, safety limit 30) | 0 |
| x6f_m11 (10) | M11 cp2: `4000:0041ABC0:2,4010:00160D78:0x01FD9E94` | joined 8803 | log: "level31.lua", "level31_Streets.lua", "tag1.lua"; markers 11; sum 80 (InvGetMoney(2) 0); m11_orig: money 0/0/40/40 unchanged, cp 2; m11_fix: **0/0/40/40 -> 0/0/0/5, cp 3, "level31_gclub.lua" logged** | 0 |
| x6f_m3m6 (11) | M3 cp2 `0x01FD9A74`, then 11500 M6 cp2 `0x01FD9C00` | joined 8803 (M3), 14502 (M6) | M3 log: "level87.lua", "tag7.lua", "level87_chap2_street1.lua"; markers 11; m3_tag_p3 **300/3**; m3_orig_p3 **30/11**; m3_tag_p3_empty 30/3; m3_orig_p3_empty 300/11; m3_tag_p1 100/11; m3_real_p3 (spot 1) then **HuIsTagging(player 3) = 1, his cans 3 -> 2** (state 10701); M6 log: "level3.lua", "level3_comp.lua"; markers 11; m6_tag_p3 **300/3**; m6_orig_p3 **30/10** | 0 |
| x6f_m13m6 (10) | M13 cp1 `0x01FD9F9C`, then 11500 M6 cp5 | joined 9210/9600 (M13; X7 gave both 6 cans), 14518 (M6) | M13 log: "level9.lua", "level9_chap1_radio.lua"; markers 111; m13_tag_p3 0/3 (no tag object); m13_orig_p3 30/11; M6 cp5 log: "level3_gallery.lua", "tag3.lua"; markers 11; m6b_tag_p3 0/3; m6b_orig_p3 0/10 | 0 |
| x6f_m13m18 (11) | M13 cp1, then 11500 M18 cp3 | joined 9206/9604 (M13), 15301 (M18; 14502/14900 skipped: cinematic 3) | m13_tag2_p3 **300/3**; m13_orig2_p3 **30/11**; markers_m18 11; fov3: player 3 at (-464.1, -217.9, -0.21) inside vFOVZoom -> **110**; player-1 control 0 (moved away, see negative result 4) | 0 |

Result codes: rail spy R = 100 + calls*100 + (rail index + 1)*10 + target player number (100 = no rail built);
GatePicked R = (index+1) of CameraGetActive / CamSetFollowPos / CamSetFollowZoom, R2 = player number given to
CameraMakeActive; tag R = (player given to HuTag)*100 + (player who got the no-paint sound)*10, R2 = player number whose
count the check read (3 = through the row's own-count path, 10 + n = the original `InvGetSpraycanCharges(n)`).
`errors` in probes.json are PINE "error code 255" reads before the emulator answered (boot) and after the emulator
stopped; no probe result is affected.

## 4. Files changed
- `mod/m2/missions.txt`: header line, "Free RAM used" line, the LUACH table block (row 0 name pointer 0x000E7F40 ->
  0x000EC000; rows 1-9; end row at 0x000E7F50; the 3 old name words at 0x000E7F40-48 removed) and 676 data words at
  0x000EC000-0x000ECA53 (generator: session scratchpad `x6f_rows.py` + `x6f_gen.py`). CRLF kept.
- `tests/m2/x6fix_probe.py` (new): the probes above. Existing test tools untouched.
- `evidence/M6/x6f_*_probes.json` (copies of `local/m2/x6f_*/probes.json`).
- Not changed: `mod/w4p_m1.pnach` (a batch reads it; regenerate with `python -I mod/make_pnach.py > mod/w4p_m1.pnach`
  when the batch is done), emulator, nav_probe, m2_run4, m1 tests, sandbox, pine, mission_smoke.

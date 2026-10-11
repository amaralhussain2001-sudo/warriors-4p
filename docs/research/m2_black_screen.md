# M2 research: full black screen after players 3-4 are created

Static analysis only (decompile `local/analysis/all/*.c`, Lua pseudo-code `local/analysis/pseudo/`, ELF
`local/disc/SLUS_212.15` with the current `mod/w4p_m1.pnach` overlaid). Nothing was run. Function names are our
labels. Build: SLUS-21215 v1.03.

## 1. Observation (from the parent, F-0113)
- Mission 1, all `[warriors-4p 4p]` patches. The picture is normal until players 3-4 are created with
  MakePlayer + `FUN_001222B0(h,1)` + `FUN_0011EAF0(2/3)` + **`FUN_0041B148(GM,h,1)`** + `FUN_00122ED0`
  (polls ~4300-4440).
- From then on the screen is black, while:
  - the game runs at 30 fps with 12-17 % GPU load;
  - views = 1, cameras = 4, players = 4;
  - all four players still move.
- The same happens in four lockstep instances, with equal hashes.
- Screenshot comparison done for this note (`local/m2`):
  - `m2g` called `FUN_0041A460` (join refused, no player created, no script event): normal picture to poll 5216;
  - `m2i`, `m2k`, `m2n` (creation sequence including `FUN_0041B148`): black from the first screenshot after the
    sequence (polls 4485 / 4671 / 4601), and already in `m2i`, before the record and HUD fixes.

## 2. Cause: the test fires Mission 1's player-2 drop-in script, which fades to black (VERIFIED, code)
1. **`FUN_0041B148(GM, human, joined)` is the "multiplayer join/leave" script event.** It calls the Lua function
   registered with `SetMultiplayerCallback` (script system `DAT_00512B04`, vfuncs +0x5C/+0x54/+0x8C with
   (human, joined)). Nothing in it depends on the player index. With `joined != 0` it also calls vfunc 0x13C on render
   camera 1 (player 2's camera).
2. **Lua chain:**
   - `SetupLevelInventory` registers `InventoryPlayer2` for every level below 100 (WAD 4106, main_150).
   - `InventoryPlayer2` (main_152) gives player-2 inventory once, then calls `p2Inventory_Callback(human, joined)`.
   - Mission 1 (WAD 9653, main_7) sets that callback with `SetPlayer2Callback(P1.AddPlayer2)`.
3. **`P1.AddPlayer2` (main_2), on join:**
   - `bAshIntro = true`, `BrSuspend(player2,false)`, `HUDTurnOffRadar(1)`;
   - **`ScreenQueueEffect(1, 0)`**;
   - `SuperRunScene({SceneId = "l99_ash_intro", Humans = {Cleon, Vermin, player, …, player2}, ReturnFunc = P1.Player2Added})`.

   `SuperRunScene` (main_125) does `HideHud()` and another `ScreenQueueEffect(1, 0)`, then
   `ScenePreload(…, "gPlayCutScene")`.

   This is the original drop-in for Ash. Choosing "2 PLAYER" in the menu never triggers it: main_7 only registers the
   callback when player 2 already exists. Our test fires it twice, once per extra player.
4. **`ScreenQueueEffect(1, 0)` means "fade to black, instantly".**
   - The binding `FUN_003682A8` passes a0 = arg1 (effect type) and f12 = arg2 (time).
   - It calls `FUN_0018B168(type, time)`, which applies the effect to ScreenEffects [0] and [1].
   - It then jumps through table 0x00552F70: type 1 → 0x0018D4C8 → `FUN_0018CC60(fx, mode 1, 0, 0, time)`.
   - With time 0, mode 1 sets fx+0x1D8 (fade amount) = 1.0 and fx+0x1DC (rate) = 1.0, and marks the HUD dirty.
   - Type 0 is the fade-in, which scripts pair with type 1: for example `ScreenQueueEffect(1, 2.8)` before `GoToMenu`,
     and `ScreenQueueEffect(0, 1)` afterwards.
5. **The fade is drawn over the whole screen in our state.**
   - `FUN_0018DAC0` (per-view effect render) takes its merged branch when count ≥ 2 and views == 1.
   - That branch ends with `FUN_0018CE58(fx[0])`, which draws the fade while fx+0x1D8 > 0.05.
   - `FUN_0018DA80` copies fx[0]'s fade state into fx[1] every frame.
   - Everything else is still rendered underneath, which explains the GPU load.
6. **Nothing fades back in (HYPOTHESIS).** Only the cut scene path restores the picture, and the scene evidently
   never plays: players keep moving freely and the screen stays black for minutes. Possible reasons:
   - two `ScenePreload`s of the same scene 100 polls apart;
   - the scene's actors are bot-driven players who never reach their marks (`GoalJoinCinematic`);
   - the scene system refuses because player 2 is already a player.

   **Side effects that also stay:** the HUD is hidden, Ash's radar is off, and `bAshIntro = true` makes main_11 and
   later tutorial steps skip their work, so the tutorial will not progress.

This is a test-harness and script problem, not an engine-table problem. Alternatives checked and found unlikely:
- **Render camera choice:** `LayoutViewports` still sets render[0] = active[0] with views = 1.
- **The effect-render function:** `FUN_0018DAC0`'s patched code reads mirror [0]/[1] correctly (disassembly with the
  pnach applied).
- **ScreenEffects objects 2-3:** they existed since level load (`fx_new` showed 4 objects) while the picture was still
  normal.

## 3. Fixes
**A. Test harness (no patch).** Remove the `0041B148` calls from the player 3-4 creation sequences:
- `tests/m2/m2_run4.py` `CALLS`: the entries at polls 4329 and 4429;
- the `--call` strings used with `tests/m2/nav_probe.py`.

The script event only matters for the original player-2 join.

**B. Engine guard (recommended for the real feature): the join event is not sent for players 3-4.**
- `FUN_0041B148` skips the Lua event when `joined != 0` and the joining human's player index (human+0x1B0, a signed
  byte) is ≥ 2.
- It returns through the function's own exit path. Join events for player 2 and all leave events are unchanged.
- No branch lands at 0x0041B184; the two replaced words are moved into the cave.
- Cave 0x000F0ED0-0x000F0EFB is free: the highest used word is 0x000F0EC4.
- `python -I tools/note_patches.py check mod/w4p_m1.pnach <fragment>`: 801 addresses, 0 problems.
- Disassembled back with the pnach applied.

```
patch=2,EE,0041B180,word,0803C3B4 // was 8E030000 lw v1,0(s0) -> j 0x000F0ED0
patch=2,EE,0041B184,word,00000000 // was 84640028 lh a0,40(v1) -> nop (delay slot; moved into the cave)
patch=2,EE,000F0ED0,word,12600005 // beq s3,zero,cont: leave events (joined == 0) pass unchanged
patch=2,EE,000F0ED4,word,00000000 // nop
patch=2,EE,000F0ED8,word,820101B0 // lb at,0x1B0(s0): joining human's player index
patch=2,EE,000F0EDC,word,28210002 // slti at,at,2
patch=2,EE,000F0EE0,word,10200004 // beq at,zero,skip: players 3-4 (index >= 2): no Lua join event
patch=2,EE,000F0EE4,word,00000000 // nop
patch=2,EE,000F0EE8,word,8E030000 // lw v1,0(s0): displaced 0x0041B180
patch=2,EE,000F0EEC,word,08106C62 // j 0x0041B188
patch=2,EE,000F0EF0,word,84640028 // lh a0,40(v1): displaced 0x0041B184 (delay slot)
patch=2,EE,000F0EF4,word,08106C9A // j 0x0041B268: original exit path
patch=2,EE,000F0EF8,word,7BB00050 // lq s0,80(sp): as the original exit's delay slot
```

**Open (not covered by B):** leave events for players 3-4.
- In `FUN_0041A460`'s leave branch, `ReleasePlayer` runs before `FUN_0041B148(GM, h, 0)`, so the player index is gone
  by then.
- Mission 1's leave path (`BrSuspend(player2, true)`, `TeleportToFlag(player2, …)`) would then freeze and teleport
  **Ash**, player 2, when player 3 or 4 leaves.
- The D7 leave work needs a guard on the loop index (player ≥ 2) in that branch, or index-aware Lua callbacks.
- Later missions register their own `SetPlayer2Callback`s (about 20, `m2_hud_scripts.md`), which have the same
  "player-2 only" assumption.

## 4. Runtime checks (PINE, single instance)
| Read | Expected if this note is right |
|---|---|
| fx0 = `read32(0x005FDEB8)` (equal to `read32(0x000F0890)`) | the main view's ScreenEffects object |
| `float(read32(fx0 + 0x1D8))` | 0.0 before the first `0041B148` call; **1.0 (0x3F800000)** from that call on, staying 1.0 during the black screen |
| `read32(fx0 + 0x1D4)` | 1 right after the call, then 2 (set by `FUN_0018CE58`) |
| `float(read32(fx1 + 0x1D8))`, fx1 = `read32(0x005FDEBC)` | 1.0 (copied from fx0 every frame) |
| `read32(0x000F0800)` / `read32(0x000F0810)` | active[0] == render[0] (rules out a wrong render camera) |

**Confirmation tests** (single instance, test only: a PINE write on one instance would break lockstep):
- **Undo the fade:** write `fx0+0x1D8 = 0` and `fx0+0x1D4 = 0` while the screen is black. The picture should return,
  with the HUD still hidden because of `HideHud`.
- **Control without any 4-player patch:** in a normal 2-player Mission 1, call `FUN_0041B148(GM, player-2 human, 1)`
  through the test-call mailbox. The screen should also go black.
- **With guard B:** rerun the creation sequence including the `0041B148` calls. The picture should stay normal and
  `fx0+0x1D8` should stay 0.

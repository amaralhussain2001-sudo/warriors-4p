# M6: why the title screen ignored Start in 60 fps mode, and the fix (2026-10-12)

Build: The Warriors USA v1.03, SLUS_212.15 (static addresses; function names are OUR labels, the ELF is stripped).
Emulator: fork build w4p-m6-1 (`emulator/pcsx2/bin`, rebuilt 03:12). Every runtime test here is **SINGLE-PC**,
sandbox instances 15-16, fresh memory cards, MTVU off, no impairment. Input: scripted W4P bots, or key presses posted to
the game window by the agent (`tools/winkeys.ps1`); no human played. Labels as in CLAUDE.md.
Harness: `tests/m6/sixty_title.py` (new). Evidence: `evidence/M6/sixty_<tag>.json`, screenshots and PINE samples in
`local/m6/sixty/<tag>/` (not committed).

## Summary in plain English

- **Cause (VERIFIED):** the title screen, the main menu, the profile screens and loading screens run the game's clock
  in a "fixed step" mode in which every drawn frame counts as exactly 1/30 s. Our 60 fps patch makes the game think in
  1/60 s steps and run its logic on every step. On those screens the game therefore ran **two logic steps per drawn
  frame**, and each step updates the controllers. The second update in the same frame cannot read the controller
  again (the game skips a real read within 6 ms and copies the previous one), so after the frame the controller looks
  "held", not "just pressed". The title asks "was Start *just pressed*?" once per frame - and the answer was always no.
  Example: you press Start; step 1 records "pressed"; step 2 (same frame) records "pressed" again; the title then sees
  "pressed, pressed" = held, and ignores it. At 30 fps there is only one logic step per frame, so it works.
- **It is not** the EE cycle rate 180 %, not W4P, not the network, not the keyboard or controller type: it fails without
  W4P and at EE 100 %, and it even fails **at 30 fps** with only R60-3 ("logic on every step").
- **Fix (VERIFIED in the tests below):** two more words in the `[warriors-4p 60fps]` group make the fixed-step clock
  count 1/60 s per frame. Then menus run one logic step per frame, as in the original game. With it: the title accepts
  Start (bots, keyboard, with and without W4P), single menu presses act once (same as 30 fps; *held* directions
  auto-repeat at a different rate, section 5), a 2-instance lockstep session reached
  Mission 1 with 2 players, paused, restarted from the last checkpoint, **2806 hash points, 0 mismatches**, and gameplay
  still runs one logic step per frame at about 60 frames/s (F-0161's measurement repeated: median 59.84).
- Side effect (VERIFIED by step counts, not by eye): before the fix the 60 fps menus ran their animations at double
  speed (2 x 1/60 s of game time per 1/60 s frame); with the fix they run at normal speed.
- **E6 (the user's 2-player package):** its `[warriors-4p 60fps]` lines are identical to the ones that fail here and it
  has no fix, so with 60 fps "yes" the title will very probably not accept Start (HYPOTHESIS: that package and its
  build w4p-m3-7 were not run; the cause is in game code and shows without W4P). **For E6, answer 60 fps = no.**

## 1. Results

Title Start "accepted" = the title assigned a controller to player 1 (PINE: HUD manager 0x00600840 -> controller
record, byte +0x19 >= 0, set by `FUN_001AE638` when it sees Start pressed) and/or the screenshots show the main menu.
Steps per frame = SimStep counter 0x005104F4 / FrameStats counter 0x0050C654 over the time in the title mode.
Logic ticks per frame = steps per frame with R60-3, half of it without R60-3.

| Run (tag) | Groups (besides M1 when W4P) | EE | Input | Title Start | Steps/frame in title (logic ticks) | Title frames/s |
|---|---|---|---|---|---|---|
| `a60_w4p` | 60fps | 180 % | W4P 1 instance, Start held 5 polls every 150 polls | **ignored, 83 presses** (polls 1350-13650); still "PRESS THE START BUTTON" at the end (`end_slot0.png`) | 2.0 (2) | 59.81 |
| `h60fix_w4p` | 60fps + fix | 180 % | same | **accepted**: main menu by poll 2087 (`t0045_p2087.png`) | 1.0 (1) | 59.94 |
| `b60_ee0_w4p` | 60fps | **100 %** | same | **ignored, 31 presses** | 2.0 (2) | 59.83 |
| `c30_ee2_w4p` | none (30 fps) | 180 % | same | **accepted** at poll 1356 (first press at the title, 1350) | 2.0 (1) | 25.21 |
| `d60_keys` | 60fps, **no W4P** | 180 % | Return posted every 6 s | **ignored, 9 presses** | 2.0 (2) | 37.33 |
| `d60fix_keys` | 60fps + fix, no W4P | 180 % | same | **accepted**, first press at the title (t 42.6 s -> 43.9 s) | 1.0 (1) | 59.93 |
| `e_r3only_keys` | **R60-3 only** (30 fps) | 100 % | keys | **ignored, 7 presses** | 2.0 (2) | 29.97 |
| `f_r1only_keys` | R60-1 only | 180 % | keys | **accepted** (1st press) | 2.0 (1) | 59.93 |
| `g_r124_keys` | R60-1+2+4 | 180 % | keys | **accepted** (1st press) | 2.0 (1) | 59.82 |
| `i_r13_keys` | R60-1+3 | 180 % | keys | **ignored, 7 presses** | 2.0 (2) | 59.94 |
| `final_w4p` / `final_keys` | `mod/make_pnach.py` output with the fix inside `[warriors-4p 60fps]` (2-player package groups: own view, hud, 60fps, widescreen) | 180 % | W4P bots / keys | **accepted** (first press at the title, both) | 1.0 (1) | 59.93 / 59.95 |
| `menu_hold_fix` / `menu_hold_30` | same `check.pnach`; 60fps (fix) vs no 60fps group | 180 % / 100 % | keys, then agent-driven menu tests (section 5) | **accepted** (both, first press) | 1.0 (1) / 2.0 (1) | 56.07 / 29.97 |

Every run whose logic runs twice per frame in the title fails; every run with one logic tick per frame works. Frame
rates below 59 in some runs are probably CPU sharing (HYPOTHESIS: up to 5 other emulators of other agents ran at the
same time); they are not part of the effect (the same patch gave 37 frames/s in `d60_keys` and 59.8 in `a60_w4p`, and
both failed; the 30 fps run at 25 frames/s worked).

2-instance lockstep session (W4P, loopback, 2 players), `l2p60fix`, groups M1, own view, hud, 60fps + fix,
widescreen, EE 180 %, input = keys posted to each window by the agent (Return = Start, K = Cross, arrows), 1502 s:

| Step | Result | Evidence (`local/m6/sixty/l2p60fix/`) |
|---|---|---|
| Legal/autosave screens, title at poll 2277 | Start accepted at poll 3321 (first press at the title) | `live_s0_04.png`, `live_s0_05_after_title_start.png`, summary `start_accepted` |
| Main menu, "1 PLAYER : 2 PLAYER", profile manager, name entry, difficulty, brightness, subtitles, memory card format | each press moved/acted exactly once (e.g. one letter "A" typed, Down moved one row, Right selected EXTRAS then 2 PLAYER) | `live_s0_06..20*.png` |
| "Player 2 press the START button" | accepted from instance 2's own keyboard (slot 1 -> pad 4) | `live_s1_13_p2start.png` |
| Mission 1 (Coney, "New Blood") with 1P and 2P | reached at poll 11361 (in-game mode 0x005E56B8) | `live_s0_24.png`, `end_slot1.png` |
| Pause menu (mode 0x005E6550) | opens; Right -> Stats, Down -> Restart, Right -> Resume, Cross resumes | `live_s0_26..30*.png` |
| Pause -> Restart -> "Restart Last Check Point" -> Yes | mission reloads, intro, cutscene, gameplay again | `live_s0_31..38*.png` |
| Sync | **2806 common hash points (30-84180), 0 mismatches**; waits slot 0: 2830 (36.6 s total), slot 1: 53235 (141.0 s, max 3.27 s; cause not analysed) | `evidence/M6/sixty_l2p60fix.json` |
| Gameplay rate after the restart (in-game mode, PINE) | **1.001 steps per frame**, 64636 frames in 1118.9 s = 57.77 frames/s; 60-s windows 59.5-59.96 except 6 of 19 at 46-57 (other agents' emulators were running; cause not analysed); W4P windows from poll 19000: median 59.94, p10 53.55, min 29.77 | samples.jsonl; `tests/m2/fps_windows.py` |

Gameplay with four views (F-0161's method: 4-player Mission 13 savestate, random bots on all slots, one instance,
EE 180 %, 60fps group; my harness with `--state`):

| Pair | Launched first | Launched second |
|---|---|---|
| 1 (`local/m2/m6_sx60fix`, `m6_sx60nofix`, via nav_probe) | with fix: median 39.68, min 23.27 | without fix: median 59.54, min 29.16 |
| 2 (`m13_60fix_b`, `m13_60nofix_b`) | with fix: median 56.59, p10 51.66 | without fix: median 59.84, p10 59.34, min 59.14 |
| 3 (`m13_60nofix_c`, `m13_60fix_c`) | **without** fix: median 57.51, p10 46.39 | **with** fix: **median 59.84, p10 59.17, min 59.14**, 1.001 steps/frame |

All six runs: in-game mode only, GameClock fixed-step flag 0 (real-time) the whole time, 1.001-1.002 steps per frame.
The slower run was always the one launched first (its window behind the other), with and without the fix, so the
difference is a measuring artifact of two concurrent instances, not the fix (VERIFIED by the swapped pair 3). With the
fix, pair 3 repeats F-0161 (59.84 / 59.44 / 59.14) within 0.3 frames/s at p10. F-0161 and F-0100's "logic every frame"
remain valid: gameplay never uses the changed code (section 3).

Pause menu at 60 fps over four views (`pause_m13_nofix`, `pause_m13_fix`; Mission 13 savestate, scripted Start / Right
/ Down / Right / Cross): **identical in both**: pause mode 0x005E6550 at session poll 1200, Stats, Restart, Resume
highlighted one by one (`t0045_p11345.png`, `t0050_p11525.png`), Cross resumed (in-game again at guest poll 11831 in
both), second pause at 12307/12310. So the pause menu was never affected (as the code predicts). Observation, not
analysed: the pause menu over four views drew only 32-38 frames/s on this shared PC (GPU 71-81 %).

## 2. Cause: static analysis (VERIFIED, code)

| Claim | Label | Evidence |
|---|---|---|
| Mode object 0x005E65C0 is built in `FUN_0015E530`; vtable 0x00538730: +0x14 type function 0x004DDF58 (returns 18), +0x1C enter `FUN_0015E048`, +0x24 exit `FUN_0015E130`, +0x2C resume `FUN_0015E0F8`, +0x3C **update `FUN_0015E238`** | VERIFIED | ELF words at 0x00538730; decompile |
| It is pushed by `FUN_001552B0`, called from the Lua binding **`ShowProfileManager`** (0x0036EEF8). The title ("PRESS THE START BUTTON"), the main menu (STORY : EXTRAS), 1/2 PLAYER, profile manager, name entry, difficulty, brightness and subtitles are GUI pages of this one mode (the mode stack stays at 0x005E65C0 the whole time in all runs) | VERIFIED | `lua_bindings.tsv`; samples of every run |
| The earlier test criterion "the title mode is left" (m5_package4.md section 4) cannot show acceptance: the main menu is the same mode | VERIFIED | `h60fix_w4p`: main menu on screen, mode unchanged |
| `FUN_0015E238` per frame: `FUN_00145F60(GameClock, 1)` (fixed-step on) -> `FUN_00156220` (GameClock tick, vtable +0x14 = `FUN_00145A10`) -> `FUN_003A3148(sim, 0)` -> SimAdvance `FUN_003A2EA0` -> ... -> `FUN_001AE828(0x00600840)` (HUD manager) -> `FUN_00204BA0` (GUI page) | VERIFIED | decompile `FUN_0015E238` |
| `FUN_001AE828` -> `FUN_001AE638`: if player 1's controller record has no pad (+0x19 < 0), scan the 8 pads with `FUN_00144BF0(pad, 0x800)` (Start pressed) and assign the first one (`FUN_001AE8D8`) | VERIFIED | decompile `FUN_001AE638`; runtime: +0x19 goes -1 -> 0 exactly when Start is accepted (`c30_ee2_w4p` poll 1356) |
| `FUN_00144BF0` (our label PadPressed) = `hist[idx] & mask && !(hist[idx-1] & mask)`; history ring of 8 u16 at pad+0x1C, index pad+0x2C; pads 0x005DD810 + n*0x50 | VERIFIED | decompile; `FUN_00144B88` (held) for comparison |
| `FUN_00144FB0` (one pad update): `idx = idx+1 & 7`; if the timer `*0x0050B8B8` (vtable +0x34, ms) is less than 6 ms after the last real read, `hist[idx] = hist[idx-1]` (copy); else real read `FUN_001498A8` (libpad; our W4P hook is at 0x001498E0) | VERIFIED | decompile `FUN_00144FB0` |
| `PadUpdateAll` `FUN_001454A8` (pads 0 and 4) runs inside the SimStep logic body when `DAT_005E5350 != 0`; that flag is set to 1 at start-up (`FUN_00155A90`) and never cleared | VERIFIED | decompile `FUN_00249108`, `FUN_00155A90` |
| GameClock (`*0x0050B734`) tick `FUN_00145A10`, fixed-step branch (+0x54 == 1, 0x00145A74-0x00145AB4): game time +0x40 += (+0x4C) x (+0x50) x 294,912,000 cycles and unscaled time +0x30 += 0x960000. +0x4C is written only by the clock reset `FUN_00145980` at 0x001459C8-0x001459E4 = **1/30 (0x3D088889)**, +0x50 = 1.0 | VERIFIED | disassembly; no other writer of +0x4C in the decompile, no other `lw/lwc1 76(..)` from the clock pointer in .text |
| SimAdvance (0x003A2F08-0x003A2FA4) reads game time +0x40 (vtable +0x44). Fixed step 0x960000 per frame: original = one pass of 2 steps, SimStep runs logic on the even one = **1 logic tick/frame**; with R60-2 = two passes of 1 step, with R60-3 both run logic = **2 logic ticks/frame** | VERIFIED (code) + runtime (steps/frame 2.0 vs 1.0 in section 1) | disassembly in `sixty_fps.md` section 2 |
| Hence with R60-3 in a fixed-step mode: tick 1 reads the pad (new state), tick 2 copies it (< 6 ms later); after the frame hist = [.., new, new]; `FUN_001AE638` runs after SimAdvance and sees no edge. A press can never be seen, whatever its length | VERIFIED | code above; runtime: pad 0 history sampled one poll after a press began: `a60_w4p` (poll 1801) already holds two "0x800" entries, `h60fix_w4p` (poll 1501) one |
| In gameplay the in-game mode 0x005E56B8 (update `FUN_00158728`) never sets fixed-step; the clock is real-time (1/60 s per frame at 60 fps -> 1 step) | VERIFIED | callers of `FUN_00145F60`; runtime fixed flag 0 and 1.001 steps/frame in all gameplay runs |

### Which screens use the fixed-step clock and full SimAdvance (affected before the fix)

From each mode's update: `FUN_00145F60(clock,1)` = fixed step; `FUN_003A3148(sim,0)` = full SimAdvance,
`(sim,1)` = "paused" step `FUN_003A3000` (own 1/60 s threshold on timer 0x0050B8B8, at most one `PadUpdateAll` per
call; not changed by R60-2/3).

| Mode | Type | Update | Lua / pusher | Fixed | SimAdvance | Affected before the fix |
|---|---|---|---|---|---|---|
| 0x005E65C0 | 18 | `FUN_0015E238` | ShowProfileManager (title, main menu, profiles) | yes | full | **yes (VERIFIED at runtime)** |
| 0x005E5810 | 6 | `FUN_0015BE00` | boot, SSMC save/load/delete sequences (the memory-card format prompt) | yes | full + own PadUpdateAll | HYPOTHESIS yes without the fix (not run); **with the fix the format prompt took Cross once** (`l2p60fix`, mode 0x005E5810 from poll 10794, `live_s0_20_subs.png` -> `live_s0_21_format.png`) |
| 0x005E5D90 | 8 | `FUN_0015C858` | loading | yes | full | no input needed |
| 0x005E5DF8 | 11 | `FUN_0015D160` | HUDLaunchMissionComplete | yes | full | HYPOTHESIS yes (not run) |
| 0x005E5E30 | 16 | `FUN_0015D890` | HUDShowMissionSelect | yes | full | HYPOTHESIS yes (not run) |
| 0x005E66D0 | 17 | `FUN_0015ECA0` | ShowRumbleModeInterface | yes | full | HYPOTHESIS yes (not run) |
| 0x005E56F0 | 19 | `FUN_001596D0` | ShowGameStatsInterface | yes | full | HYPOTHESIS yes (not run) |
| 0x005E6550 | 10 | `FUN_0015DD98` | pause (pushed from the in-game update via `FUN_00154F28`) | no | paused | **no (VERIFIED at runtime, both with and without fix)** |
| 0x005E5DC0, 0x005E53A0 | 12, 13 | `FUN_0015CC78`, `FUN_00155C78` | pushed from the in-game update and GUI code (purpose not identified) | yes | paused | no (code) |
| 0x005E57E0 | 5 | `FUN_00159AE0` | boot logo/legal screens | yes | none, own PadUpdateAll | no (VERIFIED: Start accepted there in every run) |
| 0x005E56B8 | 1 | `FUN_00158728` | in-game | no (real-time) | full | no |

The fix covers every "yes" row at once, because they all use the same fixed-step clock.

## 3. The fix (in `mod/make_pnach.py`, group `[warriors-4p 60fps]`)

```
patch=2,EE,001459C8,word,3C013C88 // R60-FS GameClock fixed step 1/60 s per frame (was 3C013D08 = 1/30): one logic step per frame in menus
patch=2,EE,00145A98,word,3C05004B // R60-FS fixed-step unscaled clock +0x4B0000 cycles per frame (was 3C050096 = 0x960000)
```

- 0x001459C8 is `lui at,0x3D08` in the clock reset; with `ori at,0x8889` it builds 1/30. Changing the upper half to
  0x3C88 gives 0x3C888889 = 1/60 (same exponent trick as R60-4). 0x00145A98 is `lui a1,0x0096` (0x960000 cycles =
  1/30 s) in the fixed-step branch; 0x004B gives 0x4B0000 = 1/60 s.
- Only the fixed-step branch of `FUN_00145A10` uses either value (VERIFIED, section 2), so gameplay (real-time clock)
  runs the same code as before (VERIFIED at runtime: 1.001 steps/frame, F-0161 numbers repeated).
- PCSX2 applies place-2 word patches with a compare-before-write (`IdempotentWrite32`,
  `emulator/pcsx2/pcsx2/Patch.cpp` `Patch::ApplyPatch`), so re-applying them every vsync does not invalidate
  recompiled code (VERIFIED, source).
- Determinism: same words on every player (the group is shared); 0 mismatches over 2806 hash points in `l2p60fix`.
- `python -I tools/note_patches.py check` on the generated pnach: the "was" words match the ELF; only the 6 known
  `[4p hud A]` / `[4p hud B1]` conflicts (`local/m6/sixty/check.pnach`, 3349 addresses).
- Not written: `mod/w4p_m1.pnach` (the coordinator regenerates it), the packages (`package/`, `package4/`, `dist/`).

Options considered: (a) this 2-word change (chosen); (b) a code cave that keeps R60-3 off in fixed-step modes (logic on even steps only) - would
need LogicDt switched back to 1/30 there too, more code; (c) applying the 60fps group only once in gameplay - not
possible with pnach groups, and menus would then run at 30 fps; (d) patching `FUN_001AE638` to look at "held" - would
fix only the title, not the other menus. The chosen 2-word change restores the original "one logic step per frame"
on every fixed-step screen.

## 4. Final check with the generated pnach

`final_w4p` (W4P, bots) and `final_keys` (no W4P, keys): `python -I mod/make_pnach.py > local/m6/sixty/check.pnach`,
groups own view, hud, 60fps, widescreen (the 2-player package's 60 fps set), EE 180 %, fresh cards.
Result: **both accepted Start at the first press on the title**. `final_w4p`: title at poll 1286, Start pressed at 1350,
player 1's pad assigned at poll 1361, 1.0 steps/frame, 59.93 frames/s; `final_keys`: title at 37.8 s, key at 42.4 s,
accepted at 43.7 s, 1.0 steps/frame, 59.95 frames/s (`evidence/M6/sixty_final_w4p.json`, `sixty_final_keys.json`).

## 5. Negative results and caveats (read these)

- Before the fix, **0 of 137 Start presses** at the 60 fps title were accepted in these runs (83 + 31 bot presses held
  5 polls, 9 + 7 + 7 posted key presses), with and without W4P, at EE 100 % and 180 %, and at 30 fps with R60-3 alone.
  The package probes in `m5_package4.md` (`pk4_title60*`, `pk4_m1_2p60*`) and F-0159 are explained by this.
- The m5 conclusion "the title mode was never left" was the wrong signal (section 2); its FAILED TEST stands, the
  reason was right (Start not accepted).
- Two concurrent instances measure differently: the one launched first ran slower in all three gameplay pairs
  (median 39.7 / 56.6 / 57.5 vs 59.5-59.8). Compare 60 fps numbers only from swapped pairs or single runs.
- Mission 1 at 60 fps in the lockstep run had 60-s windows of 46-57 frames/s (other agents' 4-5 emulators ran at the
  same time); not analysed further here (F-0163 already notes Mission 1's start scene is heavy).
- The `c30_ee2_w4p` title ran at 25 frames/s (30 fps mode; cause not analysed); acceptance was not affected.
- One ambiguous menu result in `l2p60fix`: from QUICK RUMBLE, "Up (150 ms), wait 0.7 s, Left (150 ms)" left the cursor
  on QUICK RUMBLE (`live_s0_08_upleft.png`); a single Up afterwards moved it to STORY (`live_s0_09_up.png`). Whether
  Left on STORY wraps to QUICK RUMBLE in the original game was not checked; every other single press in that run moved
  exactly one item. **Resolved:** the same sequence gives the same result at 30 fps without the 60fps group
  (`menu_hold_30/m02_upleft.png` = `menu_hold_fix/m02_upleft.png`), so it is the game's own menu wrap.
- **Held directions differ (open, minor):** side-by-side test `menu_hold_fix` (60fps + fix, `check.pnach`) vs
  `menu_hold_30` (30 fps), same key posts at the same time on both, main menu (cycle STORY -> EXTRAS -> QUICK RUMBLE
  with Right). Short presses (100-150 ms) gave identical results in all 4 compared screenshots (`m02_upleft`, `m05_down100`,
  `m06_right100`, `m07_r2`; others taken but not compared). Holds did not: Right held 600 ms from QUICK RUMBLE -> STORY at 60 fps but QUICK RUMBLE at 30 fps
  (`m03_right600.png`); after Up, Right held 1500 ms -> EXTRAS at 60 fps, STORY at 30 fps (`m04_up_right1500.png`).
  So the menu auto-repeat while a direction is held runs at a different rate at 60 fps (FAILED TEST for "same as
  30 fps"; the exact rates were not measured, the screenshots only give the count modulo 3). HYPOTHESIS: a per-tick
  repeat counter (the pad history helpers `FUN_00144A80` / `FUN_00144AD0` and the bytes pad+0x30..+0x33 compared with
  0x0F) that now counts 60 ticks per second; the same class of problem as R60-6 in `sixty_fps.md`. Not caused by the
  fix (the fix gives the menus the original one tick per frame; without it the menus could not be reached at all).
  Effect for players: holding a direction in a menu scrolls at a different speed; single presses are fine.

## 6. Not tested

- A real game controller (the mechanism does not depend on the device: HYPOTHESIS).
- A memory card that already has a profile; the title still needs Start (same code path: HYPOTHESIS).
- GAME OVER -> "Last checkpoint" after a real defeat (only "Restart Last Check Point" from the pause menu was tested).
- The other fixed-step screens at 60 fps (mission complete, mission select, game stats, rumble, save/load sequences);
  the fix applies to them by the same code (HYPOTHESIS).
- Menu animation speed by eye (only step counts); menu auto-repeat rates (see section 5).
- Gameplay timings that count logic ticks (R60-5/R60-6 audit in `sixty_fps.md`) are unchanged by this work.
- E6 itself (`dist/warriors-4p-test`, build w4p-m3-7) and `package4` with the fix (need rebuilt packages); 4 instances
  through the menus at 60 fps; LAN / internet.

## 7. E6 and what to tell the user

The E6 package has the same 60fps lines without the fix (`dist/warriors-4p-test/game/w4p.pnach` lines 90-103, read
only). Expected effect at 60 fps "yes": the title shows "PRESS THE START BUTTON" and never reacts (HYPOTHESIS for that
package; VERIFIED for the same lines with the current build, with and without W4P). Meanwhile: **answer 60 fps = no
(30 fps) in E6.** A rebuilt package with the regenerated pnach would let 60 fps work from the title (needs the
coordinator; the PatchSet hash changes, so both PCs need the same new package).

## 8. How to reproduce

```
python -I mod/make_pnach.py > local/m6/sixty/base.pnach        # then add the TEST ONLY groups (m6 r60-1..4, m6 fix fixedstep)
python -I tests/m6/sixty_title.py a60_w4p --inst 15 --groups "warriors-4p 60fps" --ee 2 --script tests/m6/nav/start_every150.txt --seconds 240
python -I tests/m6/sixty_title.py d60_keys --keys --inst 15 --groups "warriors-4p 60fps" --ee 2 --key-from 12
python -I tests/m6/sixty_title.py l2p60fix --lockstep --live-input --inst 15 --port-base 46520 --groups "warriors-4p own view;warriors-4p hud;warriors-4p 60fps;m6 fix fixedstep;warriors-4p widescreen" --ee 2 --seconds 1500
   (then drive both windows: python -I tools/drive.py 15 "Return:200,wait:2000" <shot>; instance 16 for player 2)
python -I tests/m6/sixty_title.py m13_60fix_c --inst 16 --pnach local/m6/sixty/prefrag_fix.pnach --groups "<10 M2 groups>;warriors-4p 60fps;m6 fix fixedstep" --ee 2 --state local/m2/states/m13_4p_state.p2s --players 4 --random-bots --seconds 200
python -I tests/m6/sixty_title.py pause_m13_nofix --inst 15 --pnach local/m6/sixty/prefrag_fix.pnach --groups "<10 M2 groups>;warriors-4p 60fps" --ee 2 --state local/m2/states/m13_4p_state.p2s --players 4 --script tests/m6/nav/pause_m13_60.txt --seconds 80 --every 5
python -I tests/m2/fps_windows.py local/m6/sixty/<tag>/w4p_slot0.log [from_poll]
```
`local/m6/sixty/prefrag_fix.pnach` = `local/m2/pnach_prefrag.pnach` + the TEST ONLY group `[m6 fix fixedstep]`.

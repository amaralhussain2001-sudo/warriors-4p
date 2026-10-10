# M1 report — critical proof of concept (2026-10-10)

**Result: all 7 M1 exit criteria met on SINGLE-PC with scripted bots** (`docs/plan/M1.md`). This proves the core
mechanism on one PC only. It does not prove cross-PC sync (E6, needs a second PC), internet play, human play, or
anything about players 3 and 4.

Environment for every test: SINGLE-PC (Ryzen 9 9950X3D, RTX 5090, Windows 11), two instances of our PCSX2 build
(v2.9.115 + W4P patches) on loopback UDP, original game in its own 2-player mode, Mission 9 "Payin' The Cost"
checkpoint A (start state `local/m1_start_m9_2p.p2s`, SHA-256 `262b27c5…4687`), scripted seeded bots on both player
slots (walk, attack, grab, camera turns; never Start/Select), the user's emulation settings (MTVU on), native
resolution. Evidence: `evidence/M1/*.json`; logs, screenshots and RAM dumps in `local/m1/<tag>/` (not committed).

## Completed work
| Item | Where |
|---|---|
| PCSX2 v2.9.115 built from source with the already-installed VS Build Tools (1.5 min clean, 0 errors) | `emulator/build.ps1`, F-0087 |
| W4P module in the fork: delay-based lockstep, frame gate at the game's controller read, UDP transport behind an interface, impairment (latency/jitter/loss), full-RAM hash every 30 frames + comparison, desync log + RAM dump at a common frame, neutral emulated pads during sessions, waiting OSD, presentation crop | `emulator/patches/0001-0003`, fork commits e868c75, 0ef48dc, 97bbb1d |
| Game patch (pnach): controller-read hook with guest poll counter; 2x2 layout when 2+ views | `mod/make_pnach.py`, `mod/w4p_m1.pnach` |
| Test harness | `tests/m1/m1_run.py`, `tools/desync_diff.py` |
| Human trial launcher | `tests/m1/m1_play.py` |

## Test results (exit criteria)
| # | Criterion | Run | Result | Verdict |
|---|---|---|---|---|
| 1 | ≥ 10 min gameplay with combat, hash every 30 frames, zero mismatches | `c1_final` (fork 0ef48dc) | 752 s, 20,254 game frames (11.3 min), 675 hash points compared, **0 mismatches**, no crash. Earlier run `c1_10min` (fork e868c75): 17,588 frames, 586 points, 0 mismatches | **PASS** |
| 2 | 60 ms RTT, 10 ms jitter, 1 % loss, ≥ 5 min | `c2_impair_d2` | 9,538 frames (5.3 min), 317 points, **0 mismatches**; stalls 0.74 s / 0.58 s total, max 33 ms; input delay 2 frames | **PASS** |
| 3 | Different views on the two instances with equal hashes; no-crop control equal | `c1_final` + `c3_nocrop` | instances showed different views with 0 mismatches; the no-crop run's hash stream equals the cropped run's at all 125 common points | **PASS** (crop is presentation-only; E2c) |
| 4 | Own view full screen with own HUD when split; full frame when merged | `c4_views`, `c1_final` screenshots | merged: both windows show the same full frame (shots at 6/18 s); split: each shows its own player's quarter full screen (shots at 31 s), player 2's objective bar only on B | **PASS** |
| 5 | Added delay ≤ 2 frames; ≥ 29 fps in gameplay; stall time reported | `c1_final` | delay 2 frames (66 ms); 29.55 polls/s average in the 63 gameplay windows of 10 s (27.3 including loading/game-over windows, which the game itself runs slower); stalls 0.88 % of session time, max 39 ms | **PASS** |
| 6 | Deliberate corruption detected and logged with frame number | `c6_corrupt` (fork 0ef48dc), `c6_corrupt2` (fork 97bbb1d) | 1-frame Square flip: **not detected** (no state change, like the Stage 1 controls) — FAILED TEST of the test design, kept on record. 30-frame stick corruption on one instance: DESYNC logged at frame 930 (first hash point after the corruption), both instances dumped RAM at frame 12149; `desync_diff.py` shows player 1 (index 0) and a nearby enemy at different positions | **PASS** (after strengthening the test) |
| 7 | Originals unchanged | `evidence/hashes/inputs_2026-10-10_m1.json` | 20 files compared (ISO, all BIOS files, original pcsx2-qt.exe), 0 changed | **PASS** |

Also observed: during the bot runs the bots repeatedly triggered the mission's own failure rule ("GAME OVER — You're
supposed to protect the store, not trash it!") and the bot's Cross presses restarted from the last checkpoint. The
lockstep stayed in sync through game over, checkpoint reload and loading screens.

## New verified findings
F-0080 to F-0090 in `docs/FINDINGS.md`. Most important:
- Emulator-level gating at the game's controller read keeps two instances identical (11.3 min, with and without
  impairment). The game reads the pad once per game frame (≈30 per second in gameplay).
- The crop of the game's split screen is presentation-only (identical hash streams with and without crop).
- The original 2-player camera **does not merge purely by distance**: with both players standing together, a camera
  turn by either player split the screen at once. The real merge rule still has to be traced (M3, policy §4.5).
- In split view the original game draws a "2P" marker over player 2 in player 1's view.

## Hypotheses and open questions
- Cross-PC determinism (E6) — still the main kill risk. Needs a second PC with its own game copy and BIOS.
- The exact merge/split rule of the original co-op camera (affects the "all players close together" rule).
- Human feel at 2 frames of delay (bots cannot judge it).
- Behaviour of the hook when a game copy runs our pnach on stock PCSX2 (would crash: the pnach must only ever be
  applied by our build; packaging must enforce this).

## Changes to the mission status table
Mission 9 "Payin' The Cost" (level86): 2-player lockstep sync **VERIFIED on SINGLE-PC with bots** (not a four-player
status). All missions remain NOT YET TESTED for four players.

## Risks and blockers
- R-01 cross-machine determinism: unchanged, still untested.
- R-05 toolchain: resolved (build works).
- New R-18: the 2x2 layout patch also changes local 2-player play if enabled outside online sessions; it must be
  applied only during W4P sessions (M3).
- New R-19: quarter-screen rendering at native resolution looks soft full screen; needs GS upscaling (M3, measure cost).
- New R-20: controller vibration for the local player is not routed yet (player 2's rumble goes to the emulated port 2).

## Deviations from the plan
- The frame gate sits at the game's controller read (game hook + emulator wait) rather than at vsync: it gives exact
  per-poll alignment and was simpler to make deterministic. Documented in M1.md and the fork code.
- The bot never presses Start/Select; pause, cutscene skip and menus are not covered by M1 (session policies, later).

## Next steps (after the user's go-ahead)
1. **E6 cross-PC test** with a second PC (instructions below) — before investing in M2.
2. M2: four genuine players in one mission (engine extension; Stage 1 E4 showed where it breaks).
3. M3: four views, merge rule, sharpness, vibration routing, conditional layout patch.

## Tests the user can do now (optional, ~5 minutes)
Human trial on this PC (you play player 1, a bot plays player 2):
1. Open a terminal in `C:\Users\PC FORCE\Desktop\New folder\warriors-4p` and run `python -I tests/m1/m1_play.py`.
2. Two windows open. Click the **first** window. Use your usual keys (W/A/S/D move, J/K/L/I buttons, T/F/G/H camera).
   If keys do nothing, switch the Windows keyboard layout to English (Win+Space).
3. Play 2-5 minutes. Tell me: does control feel delayed or fine? Does the screen switch between "together" and
   "own view" as you expect?
4. Close both windows. Send me nothing else; the logs stay on this PC.

## Originals
ISO SHA-256 `e79a4cea…e96e` and all BIOS hashes unchanged (see criterion 7).

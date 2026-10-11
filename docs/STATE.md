# Project state (handoff, updated 2026-10-11 night)

**Stage:** 2 (approved 2026-10-10; decisions D1-D14 in `docs/DECISIONS.md`).
**Milestone:** **M2 complete** - report `docs/reports/M2_report.md`, tag `m2`. All 7 exit criteria have evidence
(caveat: 30 fps mode dips to 27.4-28.7 in one heavy Mission 1 4-view scene, R-31). Findings up to **F-0161**.
The user continues without stopping between milestones (D12). Next: session policies (see Next steps).

## Waiting on the user
- **E6 2-PC test** with `dist/warriors-4p-test.zip` (2-player package, self-test p6: 445 points, 0 mismatches). Ask for:
  the `logs` folder from both PCs, each PC's CPU/GPU, how controls and 60 fps felt. Do NOT rebuild the zip before that
  test unless asked. The zip does not contain this session's fixes (downed-player view, R8, extra model) - on purpose.
- **Q1 (M2 report):** revive blocked by a teammate standing in between (game's own rule, F-0157): (A) keep (recommended)
  / (B) teammates do not block.
- **Q2 (M2 report):** widescreen on by default (D11): (A) yes (recommended) / (B) no.

## What this session did (2026-10-11 evening/night)
- D14 recorded (user: option A, load an extra Warrior model). Implemented and verified: player 4 joins as **SWAN** in
  Mission 13 with own model and HUD name, also in 4-instance lockstep (F-0154, F-0160).
- MTVU desync again with fork 0011/0013 (q13, F-0150): **MTVU stays off; no more MTVU work.**
- Downed player keeps own view: 2 words in `[own view]` (F-0151); GAME OVER text now in all four quarters (F-0152).
- **Level-end crash** (restart / last checkpoint / mission complete) with players 3-4: HUD slot release used the
  2-entry table; fix R8, 18 words in `[4p hud B1]` (F-0153, `docs/research/m2_hud_release.md`).
- Inventory tests: pick-up (F-0156), checkpoint (F-0155), revive (F-0157) pass; money bank inconclusive (F-0158).
- 30-min 4-instance lockstep with the final set: **q15, 2007 s, 1,876 points, 0 mismatches, 0 crashes** (F-0160).
- 60 fps with 4 views: median 59.84, min 59.14 (F-0161). Originals: 20 files unchanged (HASHES.md).
- Step 5 (bottom-row radar sliver with R7): no neighbouring radar in any q14/q15 bottom-row screenshot (F-0160).

## Next steps (in this order)
1. **Session policies** (BRIEF §4.6; risk R-24): pause by any player for everyone with "Paused by Player N", only that
   player or the host unpauses; cutscene skip only when all connected players pressed skip, vote shown on every
   screen ("2/4 want to skip"); disconnect freeze with a 60 s countdown, then host chooses continue-without (D7) or
   restart from checkpoint; host leaving ends the session. Start with research (how the game pauses, cutscene skip
   input, W4P side) - write exit criteria first (new milestone plan).
2. Connection layer (D5: ICE + STUN + join code), then the 4-player package + lobby (players join only in the lobby).
3. M6: all story missions (companions per mission, starting items for players 3-4, extra-model memory per level R-28,
   pocket clearing R-29, money bank via the real mission summary F-0158, GAME OVER menu input question F-0155).
4. Optional: EE 180 % in 30 fps mode for 4-player sessions (R-31); 60 fps tick audit (R-22).

## How to run things (quick reference)
- Build the fork: `powershell -File emulator\build.ps1` (log `local/logs/build_Release.log`). Build tag now
  **w4p-m3-7**; fork commits are exported to `emulator/patches/0001..0013` (author `warriors-4p <w4p@localhost>`).
  Do not build while a test instance runs (the exe is locked).
- Patch file: edit `mod/m2/*.txt` or `mod/make_pnach.py`, then `python -I mod/make_pnach.py > mod/w4p_m1.pnach` and
  `python -I tools/note_patches.py check mod/w4p_m1.pnach` (expected: **2676 addresses, 6 problems** = the known `[4p hud A]` vs
  `[4p hud B1]` alternatives; anything more is new).
- Groups for a full 4-player test: `warriors-4p own view;warriors-4p hud;warriors-4p 4p;warriors-4p 4p hud B1;
  warriors-4p 4p hud B2;warriors-4p 4p spawn;warriors-4p 4p spawn leave;warriors-4p 4p inventory;warriors-4p 4p fx;
  warriors-4p test call` (+ optional `warriors-4p 4p fx fog`, untested). Never combine `4p hud A` with `4p hud B1`.
- One instance, Mission 13, players 3-4 joining (deterministic):
  `python -I tests/m2/nav_probe.py <tag> tests/m2/nav/boot_to_m1_2p.txt --inst 10 --players 4 --script2
  tests/m2/nav/p2_join.txt --script3 tests/m2/nav/cal_p3.txt --script4 tests/m2/nav/cal_p4.txt --groups "<groups>"
  --ini EmuCore/Speedhacks/vuThread=false --callat "4000:0041ABC0:1,4010:00160D78:0x01FD9F9C" --seconds 420`
  - Use `--callat` (exact polls) for the level jump, not `--call` (PINE timing shifts the join windows).
  - Joins: player 3 at about poll 8356 (Start at 8200), player 4 at about 8508 (Start at 8350); repeated Start
    presses every 300 polls are harmless after joining (no pause menu).
  - `--fight 8900` (tests/m2/fightlib.py, report: `python -I tests/m2/fight_report.py <tag>`),
    `--probe module:function:poll` (read-only or test-write helpers in tests/m2: inv_probe, spawn_survey,
    gameover_probe, cam_probe, join_probe, results in `local/m2/<tag>/probes.json`), `--hud-diag <poll>`,
    `--peek addr:words`, `--poke poll:addr:value`.
  - Only one PINE client per instance: add reads as `--probe` functions, not as a second script.
- Four instances in lockstep: `python -I tests/m2/m2_run4.py <tag> --seconds 900 --bots-from 9000 --crop --calls
  "3999:0041ABC0:1,4009:00160D78:0x01FD9F9C" --groups "warriors-4p 4p hud B1;warriors-4p 4p hud B2;warriors-4p 4p
  spawn;warriors-4p 4p spawn leave;warriors-4p 4p inventory;warriors-4p 4p fx" --script3 tests/m2/nav/m13_p3.txt
  --script4 tests/m2/nav/m13_p4.txt --ini EmuCore/Speedhacks/vuThread=false` -> `evidence/M2/<tag>.json`.
  For 30-min runs add `--polls 70000 --script-bots-from 14000 --shot-slots 0,1,2,3` (input files wrap after
  --polls; players 3-4 random + Start every 300 polls after their script; screenshots of all four windows).
  Copy `local/pcsx2/inst6..9/PCSX2/logs/emulog.txt` after the run (crashes show as `TLB Miss` there, not in w4p logs).
- Frame rate from a log: `python -I tests/m2/fps_windows.py local/m2/<tag>/w4p.log <from_poll>`.
- Game buttons (from the game's own texts): grab = Circle, attack = Square/Triangle, **Flash = D-pad Right**, **revive a downed partner = D-pad Left** (within 3 units, clear line, F-0157).
- Useful addresses: GameMgr `*(0x0051489C)` (= 0x01FD8400 in all M2 runs), player handles GameMgr+0x228,
  objects `0x006EBD38 + 8*(h>>16)` (serial check at +4), human stats `*(human+0xD4)` health +0x144 / max +0x146,
  HUD slot human+0x380, inventory GameMgr+0x480 (count of item k, slot s: +0x24+s*0x3F4+k*0x2C; item 1 = Flash),
  views 0x0050B198, merge flags 0x0050B1E8/EC, ScreenEffects mirror 0x000F0890, poll counter 0x000F0500.

- New nav_probe options: `--patch file.pnach` (A/B with an older patch, e.g. `local/m2/pnach_prefrag.pnach` = commit
  64a235c minus the extra-model fragment, i.e. bdb2c52 + view fix, no R8), `--state file.p2s` (start from a savestate),
  `--random-bots` (seeded random input on all slots). Probe modules in tests/m2: `down_probe` (down one player, view
  state), `gameover_probe`, `p4_identity` (char ids, extra-model words, `force_panels` test aid), `extra_survey`
  (model pool), `inv_tests` (+ `inv_t2b`, `inv_t2c`, `revive_probe`), `statesave` (save state to local/m2/states/),
  `sixty_probe`. Only one nav_probe per --inst; the next run deletes that sandbox (copy emulog.txt first).
- 4-player Mission 13 savestate (made with pnach_prefrag + the 10 groups, EE 100 %): `local/m2/states/m13_4p_state.p2s`.
  60 fps measurement: `nav_probe.py sx2_60 tests/m2/nav/empty.txt --inst 10 --players 4 --random-bots --state <state>
  --groups "<10 groups>;warriors-4p 60fps" --patch local/m2/pnach_prefrag.pnach --ee 2 --seconds 200`.
- Scratch disassembler (not in the repo): write one when needed; the ELF is `local/disc/SLUS_212.15`.

## Important settings and rules
- MTVU (`vuThread`) is OFF in the package and in every session (F-0120, F-0150). Never switch it on.
- Never launch the original PCSX2; the user's own PCSX2 may be running. Sandboxes live in `local/pcsx2/instN`.
- Files are CRLF: edit with Python (normalise, edit, write back CRLF). `mod/w4p_m1.pnach` is generated with
  `python -I mod/make_pnach.py > mod/w4p_m1.pnach` from Git Bash, which gives CR CR LF lines - that is how it is stored
  in git, keep it that way (a "fixed" CRLF file shows as a whole-file diff).
- Killing emulator processes from the shell was refused by the permission system this session; let runs end on their own.
- Low RAM map: HUD objects 0x000A0000+; caves/tables 0x000E0000-0x000E0CC7 (B1/B2), 0x000E1000-0x000E15F3 (spawn +
  chooser), 0x000E1600-0x000E1C4B (extra model), 0x000E3000-0x000E3123 (combat C3), 0x000E4000-0x000E501B (inventory),
  0x000E5800-0x000E5C3F (fx), 0x000F0000-0x000F0FFF (M1/hud/4p/test call). Test scratch: 0x000E5D00 (inv_t2b/t2c).
  Free: 0x00096000-0x0009FFFF, 0x000E1C50-0x000E2FFF, 0x000E5020-0x000E57FF, 0x000E5D10-0x000EFFFF (grep the pnach first).
- Sandbox windows may start with the Arabic keyboard layout; `tools/winkeys.ps1` switches the window to en-US.

## Result line for the last run of this session
- q15 (4 instances, Mission 13, final patch set, MTVU off, build w4p-m3-7, 2007 s): **1,876 common hash points,
  0 mismatches, 0 TLB misses, 4 players / 4 views, player 4 = SWAN, survived GAME OVER + level restart** (F-0160).

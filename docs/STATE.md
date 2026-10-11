# Project state (handoff, updated 2026-10-11 late night)

**Stage:** 2 (approved 2026-10-10; decisions D1-D16 in `docs/DECISIONS.md`).
**Milestones:** M2 complete (report `docs/reports/M2_report.md`, tag `m2`). **M5 (session policies + transport) in
progress**: exit criteria `docs/plan/M5.md`. Findings up to **F-0173**. The user continues without stopping between
milestones (D12). Fork build **w4p-m5-1** (fork commit 76f7c1d, patch `emulator/patches/0014`; protocol version 3).

## Waiting on the user
- **E6 2-PC test** with `dist/warriors-4p-test.zip` (2-player package, old build w4p-m3-7). Ask for the `logs` folder
  from both PCs, each PC's CPU/GPU, how controls and 60 fps felt. Do NOT rebuild that zip unless asked.
- **Session-policy details (implemented with the recommended option A, to confirm):** U1 a non-host who paused may only
  resume (Start); U2 Esc in a session = pause request instead of an emulator pause; U3 a completed skip vote skips only
  the current scene (each scene of a chain votes again).
- **Network questions (m5_connection_design.md section 7):** B automatic router port opening (UPnP) - recommended off;
  C public message service ntfy.sh to remove the reply code - recommended no; D when the LAN test (second PC) and the
  internet test with friends can happen (T2-T4). (A: helper process - taken as recommended, within the approved plan.)

## M5 status (all SINGLE-PC, 4 instances on loopback unless noted)
| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | Pause | **met**: any player's Start -> pause on all at the same poll, "Paused by Player N", only pauser/host resumes; Esc request not tested | F-0171 |
| 2 | Cutscene skip | **met**: "k/N want to skip", movie and scene skipped only after the last vote; vote reset per scene fixed after the test (re-test) | F-0171 |
| 3 | Disconnect, back in time | **met** (20 s outage, 0 mismatches); countdown visible on screen | F-0164, F-0167 |
| 4 | Timeout choice | **met** for a dropped player 3/4: continue without (LEAVE, 3 players/3 views) and restart; dropped player 2 variant (2-player flag call) not tested | F-0165, F-0169, F-0170 |
| 5 | Host leaving | **met** ("host left, session over", no hang) | F-0167 |
| 6 | Join only in the lobby | open (launcher/lobby not built) | - |
| 7 | Saving (co-op save separate, identical at start) | open | - |
| 8 | Connection | w4p-net helper built; loopback tests T1a-T1e pass; 4 emulators through the helpers in sync (T1f); LAN/internet need the user | F-0172, F-0173 |
| 9 | Originals unchanged | checked at M2 end (20 files); re-check at M5 end | HASHES.md |

## Next steps (in this order)
1. Re-test the vote reset (two scenes in a chain) and the Esc pause request; dropped player 2 (RestartCalls with
   `0:00419AC0:GM:0,2:00160D78:GM+0x124`, session_policies.md 4.3) and a dropped player whose index shifts (crop check
   with a pad-owner probe).
2. Launcher + lobby (Start-Coop for 2-4 players): host/join with w4p-net codes, slot list, version check, input delay,
   session INI (`SessionPolicies = true`, `LeaveCalls = 0:000E7100:P`, `RestartCalls = 0:00160D78:GM+0x124`, groups incl.
   `[warriors-4p session]` and the call mailbox), join only in the lobby (criterion 6).
3. Saving policy (criterion 7): co-op memory card per group, identical at session start, never the user's own cards.
4. T1g (outage through the helpers), impairment runs through the helpers; then the 4-player test package for the user
   (LAN first, T2), then internet with friends (T3/T4) - needs the user.
5. M6: all story missions (companions, starting items for players 3-4, extra-model memory R-28, pocket clearing R-29,
   money bank F-0158, GAME OVER menu input F-0155). Optional: R-31 / R-22.

## How to run things (quick reference)
- Build the fork: `powershell -File emulator\build.ps1` (log `local/logs/build_Release.log`). Build tag now
  **w4p-m5-1**; fork commits are exported to `emulator/patches/0001..0014` (author `warriors-4p <w4p@localhost>`).
  Do not build while a test instance runs (the exe is locked).
- Patch file: edit `mod/m2/*.txt` or `mod/make_pnach.py`, then `python -I mod/make_pnach.py > mod/w4p_m1.pnach` and
  `python -I tools/note_patches.py check mod/w4p_m1.pnach` (expected: **2810 addresses, 6 problems** = the known `[4p hud A]` vs
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
- M5 tests (4 instances): `m2_run4.py ... --w4p DisconnectTimeoutS=15 --w4p-slot3 TestDrop=9300:0 --w4p-slot0
  TestHostChoice=continue --w4p "LeaveCalls=0:000E7100:P" --leaver 3` (groups + `warriors-4p session`); pause/skip:
  `--script1..4 tests/m2/nav/pol_p1..4.txt --w4p SessionPolicies=true`; through w4p-net: start
  `python -I net/w4p-net/tests/local4.py --emu-ports 41200,41201,41202,41203 --stop-file local/m5/stop_helpers`, wait
  for HELPERS READY, then `m2_run4.py ... --peer-base 46100`, then create the stop file. w4p-net build:
  `powershell -File net\w4p-net\build.ps1` (README in net/w4p-net). `--shot-every 5` for OSD screenshots.
- Rebuilding the fork while other agents run emulators: ask them to pause runs first (the exe is locked).
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
- t1f_helpers (4 instances through 4 w4p-net helpers on loopback, Mission 13, M2 groups, MTVU off, build w4p-m5-1, 605 s):
  **549 common hash points, 0 mismatches, 4 players / 4 views** (F-0173).

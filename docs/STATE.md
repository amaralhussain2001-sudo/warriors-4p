# Project state (handoff, updated 2026-10-11 evening)

**Stage:** 2 (approved 2026-10-10; decisions D1-D13 in `docs/DECISIONS.md`).
**Milestone:** M1 complete (tag `m1`). After M1, at the user's request: view/quality/60 fps work and a 2-PC test
package (`docs/reports/M3_interim_report.md`). Now **M2 (four genuine players)**; the user continues without stopping
between milestones (D12). Criteria table: `docs/reports/M2_progress.md`. Findings up to **F-0148** in `docs/FINDINGS.md`.

## Waiting on the user
- **E6 2-PC test** with `dist/warriors-4p-test.zip` (2-player package, self-test p6: 445 points, 0 mismatches). Ask
  for: the `logs` folder from both PCs (`logs/<date>_playerN/w4p.log`), each PC's CPU/GPU, how controls and 60 fps
  felt. Do NOT rebuild the zip before that test unless asked: nothing done since changes 2-player behaviour (R7 is
  only active with 3+ views; the MTVU changes only act with MTVU on, and the package has MTVU off).
- **Decision needed - player 4's name in Mission 13** (F-0143): no other named Warrior model is loaded there, so the
  spawned player 4 is a Rembrandt copy named REMBRANDT. Options to offer (lettered, with recommendation):
  (A) load one extra Warrior model when a 4th player joins (proper fix: own body + own name; needs research on model
  loading, memory risk) - recommended; (B) keep the Rembrandt body but show another Warrior's name on the HUD;
  (C) use the loaded `warr_cl_gen` model (a second Cleon; a scripted Cleon is already in the level);
  (D) leave as is for now.
- Confirm widescreen as default (D11, taken as recommended).

## M2 status in one list (all SINGLE-PC; "one instance" = one emulator with scripted players)
- Four players join via the game's own Start-join in Mission 13 (companion Fox + spawned Warrior) - lockstep OK.
- Combat for players 3-4 shown (damage, knock-down/recovery, targeted, hits, grabs): F-0139, F-0142, F-0144.
- Own view + radar + own health panel per quarter; duplicate nameless panel FIXED (R5b, F-0137).
- Items for players 3-4: group `[warriors-4p 4p inventory]`; Flash heal works for players 3-4 (F-0141). Pick-ups,
  revive of a partner, checkpoint copy, money banking not runtime-tested yet (tests T2/T4-T7 in
  `docs/research/m2_inventory34.md` section 9). Players 3-4 start levels with no items (script work, open).
- Game-over fade on all four quarters: group `[warriors-4p 4p fx]` (F-0145). Quarter 4 has no GAME OVER text when
  all players are down because the game drops one view (F-0148) - open.
- Lockstep with ALL new groups, MTVU on: q11 10 min and q12 15 min, both 0 mismatches (F-0140, F-0149).
- Frame rate, 4 views, 30 fps mode: Mission 13 29.97; heavy Mission 1 scene ~29.4 median, min ~28.7 - limited by
  the emulated console, not this PC (EE thread ~45 %) (F-0146, F-0147). 60 fps with 4 views not attempted.
- Deterministic MTVU (fork 0011 + 0013): MTVU may be used in sessions; flag events stayed 0 in every run, so the
  original F-0120 desync cause is still unexplained (HYPOTHESIS: safe). Not yet switched on in the package.

## Next steps (in this order)
1. A 30-min 4-instance run with the final group set (criterion 5 with the new groups; q12 did 15 min clean).
2. **Single downed player 1 or 2** (F-0148 risk): down only player 1 (HuKill via `tests/m2/gameover_probe.py`-style
   probe on one handle) in a 4-player AND a 2-player run; check views (0x0050B198) and the merge flags
   0x0050B1E8/EC. If a view drops, the per-player crop shows the wrong view -> fix in the camera/view layer
   (candidates: FUN_0011EE08 switch-offs at 0x0011F644/6CC/7AC/834, FUN_00121888, FUN_00126C40, FUN_00127AC8,
   FUN_0013C710; `docs/research/m2_fx34.md` addendum 1). Then fix the quarter-4 GAME OVER text.
3. Inventory tests T2 (pick-up), T4 (partner revive), T5 (checkpoint), T7 (money bank), T9 (lockstep with items).
4. Player 4 name: act on the user's choice.
5. Bottom-row radar sliver check for R7 with 4 instances (crop on) - `local/m2/q11_m13_all/` frames can be viewed.
6. Then: session policies (pause/skip/disconnect), connection layer (D5), 4-player package + lobby, all missions (M6).
7. M2 report with the ISO/BIOS hash re-check (`python -I tools/hash_inputs.py`, compare `docs/HASHES.md`).

## How to run things (quick reference)
- Build the fork: `powershell -File emulator\build.ps1` (log `local/logs/build_Release.log`). Build tag now
  **w4p-m3-7**; fork commits are exported to `emulator/patches/0001..0013` (author `warriors-4p <w4p@localhost>`).
  Do not build while a test instance runs (the exe is locked).
- Patch file: edit `mod/m2/*.txt` or `mod/make_pnach.py`, then `python -I mod/make_pnach.py > mod/w4p_m1.pnach` and
  `python -I tools/note_patches.py check mod/w4p_m1.pnach` (expected: **6 problems** = the known `[4p hud A]` vs
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
  --script4 tests/m2/nav/m13_p4.txt --ini EmuCore/Speedhacks/vuThread=true` -> `evidence/M2/<tag>.json`.
- Frame rate from a log: `python -I tests/m2/fps_windows.py local/m2/<tag>/w4p.log <from_poll>`.
- Game buttons (from the game's own texts): grab = Circle, attack = Square/Triangle, **Flash = D-pad Right**.
- Useful addresses: GameMgr `*(0x0051489C)` (= 0x01FD8400 in all M2 runs), player handles GameMgr+0x228,
  objects `0x006EBD38 + 8*(h>>16)` (serial check at +4), human stats `*(human+0xD4)` health +0x144 / max +0x146,
  HUD slot human+0x380, inventory GameMgr+0x480 (count of item k, slot s: +0x24+s*0x3F4+k*0x2C; item 1 = Flash),
  views 0x0050B198, merge flags 0x0050B1E8/EC, ScreenEffects mirror 0x000F0890, poll counter 0x000F0500.

## Important settings and rules
- MTVU (`vuThread`) is OFF in the package/profile (F-0120). With fork 0011/0013 it is deterministic by design and
  passed q9/q11 (0 mismatches); switching it on in the package needs the user's OK after more runs.
- Never launch the original PCSX2; the user's own PCSX2 may be running. Sandboxes live in `local/pcsx2/instN`.
- Files are CRLF: edit with Python (normalise, edit, write back CRLF) - Git Bash `sed -i` silently converts to LF.
- Low RAM map: HUD objects 0x000A0000+; caves/tables 0x000E0000-0x000E0CC7 (B1/B2), 0x000E1000-0x000E15F3 (spawn +
  chooser), 0x000E3000-0x000E3123 (combat C3), 0x000E4000-0x000E501B (inventory), 0x000E5800-0x000E5C3F (fx),
  0x000F0000-0x000F0FFF (M1/hud/4p/test call). Free: 0x00096000-0x0009FFFF, 0x000E1600-0x000E2FFF, 0x000E5020-0x000E57FF,
  0x000E5C40-0x000EFFFF (re-check with a grep of the pnach before use).
- Sandbox windows may start with the Arabic keyboard layout; `tools/winkeys.ps1` switches the window to en-US.

## Result line for the last run of this session
- q12 (4 instances, Mission 13, all groups, MTVU on, build w4p-m3-7, 900 s): **841 common hash points, 0 mismatches,
  4 players / 4 views on all instances, 0 TLB misses** (F-0149).

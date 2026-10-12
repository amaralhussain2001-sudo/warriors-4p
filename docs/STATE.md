# Project state (handoff, updated 2026-10-12 ~04:15)

**Stage:** 2 (approved 2026-10-10; decisions D1-D21 in `docs/DECISIONS.md`).
**Milestones:** M2 complete (report `docs/reports/M2_report.md`, tag `m2`). **M5** (session policies + transport):
every SINGLE-PC criterion met, 4-player package built; LAN/INTERNET parts need the user. **M6** (missions) in progress:
exit criteria `docs/plan/M6.md`. Findings up to **F-0185**. The user said "do not stop until you finish everything"
(2026-10-12): keep going without pauses; stop only for things that need the user.
Fork build **w4p-m6-1** (patches `emulator/patches/0001-0018`; protocol version 3).

## Waiting on the user
- **E6 2-PC test** with `dist/warriors-4p-test.zip` (2-player package, old build w4p-m3-7). Do NOT rebuild that zip.
  WARNING (FAILED TEST in the 4-player package, `docs/research/m5_package4.md` section 4): at 60 fps the title screen
  ignored Start in every W4P run; E6 also defaults to 60 fps -> probably affected (HYPOTHESIS). A 60 fps agent is
  investigating (cause found statically: front-end fixed-step clock gives two logic ticks per frame and the second pad
  read loses the Start edge; fix being tested -> `docs/research/m6_sixty_title.md`). Tell the user to answer "no" to
  60 fps until fixed.
- **D (open):** dates for the LAN test (second PC) and the internet test with friends (T2-T4, M6 criterion 4).
- Answered with the recommended default until the user says otherwise: X9 A (no Cleon after his story death),
  X10 A (player 3 also gets his own model), X13 A (players 3-4 wait in 2-player-only stretches), X7 b (starting items
  given again after a script-forced leave).
- Open small decisions (chooser, `docs/research/m6_chooser.md`): Fox-from-M16 and post-game hub rows (HYPOTHESIS),
  Ajax rows after his arrest (agent checking scripts), M12 first-pin stall (agent implementing re-pin after 8 s).

## M5 status (all SINGLE-PC, 4 instances on loopback unless noted)
| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | Pause | **met** (Start); Esc -> pause request (D18) implemented, not tested with a real key | F-0171 |
| 2 | Cutscene skip | **met** | F-0171, F-0177 |
| 3 | Disconnect, back in time | **met** | F-0164, F-0167 |
| 4 | Timeout choice | **met** for players 2, 3, 4 | F-0169, F-0170, F-0176, F-0178 |
| 5 | Host leaving | **met** | F-0167 |
| 6 | Join only in the lobby | **met** in the 4-player package (late joiner refused, running game unaffected) | m5_package4.md |
| 7 | Saving | copy / hash / compare of co-op saves tested; the game never wrote a save in the runs -> partly | m5_package4.md |
| 8 | Connection | loopback + package (codes and Join by IP) pass; LAN/internet need the user | F-0172, F-0173, m5_package4.md |
| 9 | Originals unchanged | **met** 2026-10-12 (20 files, 0 changed) | HASHES.md |

## M6 status (`docs/plan/M6.md`)
| # | Criterion | Status |
|---|---|---|
| 1 | Smoke per mission | first batch (F-0181): 16/17 in sync, M17 crash -> fixed (F-0184); players 3-4 blocked in M2/M5/M16/M18 -> X11 (F-0183) fixes M5/M16; M2/M18 by script design. **Re-test batch smoke2 running** (all 18 missions, policies on, X11, missions group, FXCAM, chooser v2) |
| 2 | Per-mission fixes | X1, X2, X3, X5, X7(b), X8 (F-0180), chooser v2 (F-0182), X11 (F-0183), FXCAM (F-0184), X12 (F-0185). Open: X4 teleport follow, X6 Lua patches, M12 pin |
| 3 | Restart/checkpoint per mission | not yet per mission (M2 tests R8 in M13 only) |
| 4 | Completion with humans | needs the user (D) |
| 5 | Hub interludes | X12 verified with a level jump (F-0185); a real hub after a finished mission untested |
| 6 | Mission status table | not yet written in MISSIONS.md |

## Next steps (in this order)
1. Running: smoke2 batch (`local/m6_smoke2_console.txt`, ~04:03-07:30, instances 6-9); chooser agent (M12 re-pin,
   Ajax rows, instances 10-11); 60 fps agent (title-screen Start, instances 15-19). Integrate their results: regenerate
   `mod/w4p_m1.pnach` only when no 4-instance batch is using it.
2. Record smoke2 (finding + `evidence/M6/smoke2_*`); fix what it finds; write the per-mission status table in
   `docs/MISSIONS.md` (labels NOT YET TESTED / IN PROGRESS until humans finish them).
3. Rebuild the 4-player package after the 60 fps fix: `python -I mod/make_pnach.py > local/m5/pkg4/w4p_pkg.pnach`,
   `python -I tools/make_package4.py --pnach local/m5/pkg4/w4p_pkg.pnach` (no `--reuse-emulator`), run
   `tests/m5/package4_selftest.py` (4 players and a 60 fps title run).
4. Test Esc as pause request (D18) with a real key press (`tools/winkeys.ps1`); T1g (outage through w4p-net);
   restart/checkpoint per mission (M6 criterion 3).
5. Give the user the package + LAN steps (m5_package4.md section "Steps for the user's 2-PC LAN test").
6. M7 robustness (long sessions, regressions 1P / original 2P), M8 packaging, legal review, final report.

## How to run things (quick reference)
- Build the fork: `powershell -File emulator\build.ps1` (log `local/logs/build_Release.log`). Build tag **w4p-m6-1**;
  commit in `emulator/pcsx2` with author/committer `warriors-4p <w4p@localhost>`, export with
  `git format-patch -1 HEAD --start-number N -o ../patches`. Do not build while any instance runs (the exe is locked);
  ask agents to pause runs first.
- Patch file: edit `mod/m2/*.txt` or `mod/make_pnach.py`, then `python -I mod/make_pnach.py > mod/w4p_m1.pnach` and
  `python -I tools/note_patches.py check mod/w4p_m1.pnach` (expected: **3347 addresses, 6 problems** = the known
  `[4p hud A]` vs `[4p hud B1]` alternatives). Never regenerate it while a batch that uses it is starting runs.
- Full 4-player group list: `warriors-4p M1; own view; hud; 4p; 4p hud B1; 4p hud B2; 4p spawn; 4p spawn leave;
  4p inventory; 4p fx; session; missions; session call` (prefix every name with `warriors-4p `; tests add `test call`).
  Never combine `4p hud A` with `4p hud B1`.
- Mission smoke: `python -I tests/m6/mission_smoke.py --missions 1,2,... --seconds 600 --tag <tag> [--policies]
  [--force-join 5500,7000] [--calls-extra ...] [--groups-extra ...]` -> `evidence/M6/<tag>_mNN.json` + summary. With
  `--policies` players 3-4 never press Start (they join only through X11). Level jump: CallAt
  `3999:0041ABC0:1,4009:00160D78:<entry>`, entry = 0x01FD996C + (mission-1)*0x84; hub = 0x01FDA7DC.
- Hub test: `sh tests/m6/hub_test.sh <tag> 600`.
- One instance with probes: `python -I tests/m2/nav_probe.py <tag> tests/m2/nav/boot_to_m1_2p.txt --inst 13
  --players 4 --script2 tests/m2/nav/p2_join.txt --script3 tests/m2/nav/m13_p3.txt --script4 tests/m2/nav/m13_p4.txt
  --groups "<groups without M1>" --ini EmuCore/Speedhacks/vuThread=false --callat "<calls>" --probe module:func:poll
  --seconds 480` (probe modules live in tests/m2; only one PINE client per instance; a probe may block, e.g.
  `fx_crash_probe:after_stall`).
- Four instances: `tests/m2/m2_run4.py` (see its docstring; `--w4p KEY=VALUE`, `--w4p-slotN`, `--leaver`, `--peer-base`,
  `--sample-every`). Copy `local/pcsx2/inst6..9/PCSX2/logs/emulog.txt` after a run (crashes = `TLB Miss` there).
- M5 tests: disconnect `--w4p DisconnectTimeoutS=15 --w4p-slot3 TestDrop=9300:0 --w4p-slot0 TestHostChoice=continue
  --w4p "LeaveCalls=0:000E7100:P" --leaver 3`; policies `--w4p SessionPolicies=true`; through w4p-net:
  `python -I net/w4p-net/tests/local4.py --emu-ports 41200,41201,41202,41203 --stop-file local/m5/stop_helpers`, then
  `m2_run4.py ... --peer-base 46100`. w4p-net build: `powershell -File net\w4p-net\build.ps1`.
- 4-player package: `tools/make_package4.py`, self-test `tests/m5/package4_selftest.py <tag> --preset ... --players N`.
- Frame rate: `python -I tests/m2/fps_windows.py local/m2/<tag>/w4p.log <from_poll>`.
- Scratch disassembler (not in the repo): scratchpad `mydis.py <elf> <start hex> <count> [pnach]`; ELF
  `local/disc/SLUS_212.15`; decompile `local/analysis/all/all_0N.c`.
- Game buttons: grab Circle, attack Square/Triangle, Flash D-pad Right, revive D-pad Left.
- Useful addresses: GameMgr `*(0x0051489C)` (= 0x01FD8400), handles +0x228, count +0x224, join flag +0x56E8,
  cinematic +0x410, level end +0x14C, mode +0x158, checkpoint u16 +0x33A, level index u16 +0x56DC (level number =
  `*(GM+0x14D4+idx*0x84+4)`); pad owner s16 0x005DD810+pad*0x50+0x42; views 0x0050B198; render cameras (relocated)
  0x000F0810+4*i; ScreenEffects mirror 0x000F0890[4]; mode stack top 0x0050C784 / 0x005E66A0; poll counter 0x000F0500.

## Important settings and rules
- MTVU (`vuThread`) is OFF in the package and in every session (F-0120, F-0150). Never switch it on.
- Never launch the original PCSX2. Sandboxes live in `local/pcsx2/instN` (6-9 four-instance runs, 10-14 agents,
  15-19 the 60 fps agent).
- Files are CRLF: edit with Python. `mod/w4p_m1.pnach` is generated from Git Bash with CR CR LF lines - keep it so.
- Killing emulator processes from the shell is refused by the permission system; let runs end on their own.
- The fork's `emulator/pcsx2/AGENTS.md` forbids AI-written contributions to the PCSX2 project: our patches stay in this
  project and are never submitted upstream.
- Low RAM map (grep the pnach before using new space): HUD objects 0x000A0000+; 0x000E0000-0x000E0CC7 (B1/B2);
  0x000E1000-0x000E2173 (spawn + chooser v2 incl. pins 0x000E1C00/0x000E1C50, XC table 0x000E1E10, XCHK 0x000E1FA8);
  0x000E1600-0x000E1C4B (extra model, inside the spawn range); 0x000E3000-0x000E3123 (combat C3);
  0x000E4000-0x000E502B (inventory incl. X8); 0x000E5800-0x000E5C3F (fx); 0x000E7000-0x000E72F7 (session S1-S5,
  LEAVE 0x000E7100); 0x000E7400-0x000E7813 (missions X1/X3/X7, LVOWE 0x000E7790); 0x000F0000-0x000F0FFF
  (M1/hud/4p/test call, mailbox 0x000F0300). Free (check first): 0x00096000-0x0009FFFF, 0x000E2180-0x000E2FFF,
  0x000E5D10-0x000E6FFF, 0x000E7820-0x000EFFFF.

## Result line for the last runs of this session
- hub_cp2 (X12, 4 instances, 607 s): 530 hash points, 0 mismatches, 0 TLB (F-0185). fxfix_m17 (1 instance): M17 with
  4 players to poll 12843, 0 TLB (F-0184). x11_m05 / x11_m16 / x11f_m02: 0 mismatches, 4 players (F-0183).

# Project state

**Stage:** 2 (approved 2026-10-10; decisions D1-D12 in `docs/DECISIONS.md`).
**Milestone:** M1 complete (tag `m1`). After M1, at the user's request: view/quality/60 fps work and a 2-PC test
package (`docs/reports/M3_interim_report.md`). The user continues without stopping between milestones (D12) and will
run the 2-PC test (E6) with the package.

## Done
- Stage 1 (tag `stage1-plan`), M1 (tag `m1`).
- Crop timing fix, aspect fix, always-own-view + view toggle, radar in own view, real 60 fps patch set, widescreen,
  settings profile, online guards, vibration routing, handshake, split hashes (fork patches 0004-0006).
- 2-PC package: `python -I tools/make_package.py` -> `dist/warriors-4p-test(.zip)`; self-test
  `python -I tests/m3/package_selftest.py <tag>`.

## In progress
- M2 (four players): `docs/reports/M2_progress.md`. Four players exist and stay up in Mission 1; players 3-4 do not
  move yet (research `docs/research/m2_player_control.md`).

## Next steps
1. E6 with the user's second PC (package README). Compare logs: both `logs/<date>_playerN/w4p.log` folders.
2. M2: make players 3-4 controllable, 4 views + HUD, 4-instance lockstep (`docs/plan/M2.md`).
3. HUD: health/rage panel size in own view; centred text; 60 fps tick audit; pause policy; connection layer (D5).

## Questions waiting for the user
- E6 results (logs from both PCs, which CPU/GPU each PC has, how the controls felt).
- Confirm widescreen as default (D11, taken as recommended).

## Notes for the next session
- Never launch the original PCSX2; the user's own PCSX2 may be running.
- Our build: `emulator/pcsx2/bin/pcsx2-qtx64.exe` (fork branch w4p, patches in `emulator/patches/`).
- Game patch groups (mod/w4p_m1.pnach): "warriors-4p M1" (hook, 2x2 layout, aspect), "own view", "hud",
  "hud markers" (optional, untested), "60fps", "widescreen". Tests: `tests/m3/fps_probe.py`, `tests/m3/viewcap.py`
  (`--groups "a;b"`).
- Sandbox windows may start with the Arabic keyboard layout; `tools/winkeys.ps1` switches the window to en-US.

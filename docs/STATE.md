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
- M2 (four players): `docs/reports/M2_progress.md` (criteria table). Four players with independent input and four own
  views in 4-instance lockstep (tag `m2-four-views`); 33 min, 0 mismatches with MTVU off. Open: HUD of players 3-4
  (B1/B2 groups; player 3's HUD not drawn in Mission 13), 4th player in missions with too few companions (spawn
  research `m2_spawn_companion.md`), combat checks, 4-view frame rate (~29 fps, host-bound with MTVU off).
- Level jump for tests: `level_jump.md` (MenuLoadLevel with the table entry's name pointer).

## Next steps
1. E6 with the user's second PC (package README). Compare logs: both `logs/<date>_playerN/w4p.log` folders.
2. M2 open items (`docs/reports/M2_progress.md`): controlled combat test for players 3-4 (criterion 3); second nameless
   panel per quarter (R5 failed, F-0133); R7 radar raise (touches the 2-player `[hud]` group); 4-view frame rate
   (~29 fps with MTVU off; deterministic MTVU idea F-0124); name of spawned copies; inventory for players 3-4.
3. Then: session policies (pause/skip/disconnect), connection layer (D5), 4-player package and lobby.
3. HUD: health/rage panel size in own view; centred text; 60 fps tick audit; pause policy; connection layer (D5).

## Questions waiting for the user
- E6 results (logs from both PCs, which CPU/GPU each PC has, how the controls felt).
- Confirm widescreen as default (D11, taken as recommended).

## Important settings
- MTVU (`vuThread`) must be OFF in sessions (F-0120); the package profile does this and the handshake compares it.

## Notes for the next session
- Never launch the original PCSX2; the user's own PCSX2 may be running.
- Our build: `emulator/pcsx2/bin/pcsx2-qtx64.exe` (fork branch w4p, patches in `emulator/patches/`).
- Game patch groups (mod/w4p_m1.pnach): "warriors-4p M1" (hook, 2x2 layout, aspect), "own view", "hud",
  "hud markers" (optional, untested), "60fps", "widescreen". Tests: `tests/m3/fps_probe.py`, `tests/m3/viewcap.py`
  (`--groups "a;b"`).
- Sandbox windows may start with the Arabic keyboard layout; `tools/winkeys.ps1` switches the window to en-US.

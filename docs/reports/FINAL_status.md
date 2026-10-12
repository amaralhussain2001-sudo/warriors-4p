# warriors-4p - status report before your tests (2026-10-12, end of the SINGLE-PC work)

This is the final status of everything that can be done on this one PC. The brief's final mission statuses (BRIEF 8.4)
need tests on separate PCs with people (your LAN test and the internet sessions with friends), so every mission is still
**IN PROGRESS** here; after your tests each mission gets exactly one of the six final statuses. Evidence: findings
F-0001..F-0231 (`docs/FINDINGS.md`), reports in `docs/reports/`, research notes in `docs/research/`.

## Plain-English summary
- **What you get:** a package (`dist/warriors-4p-coop.zip`) that lets 2-4 friends, each on his own PC with his own copy of
  The Warriors and his own PS2 BIOS, play the story together online: each PC shows its own player's view and HUD, and
  the four games stay in step through a lockstep connection (no game data is streamed, every PC runs the real game).
- **Tested on this PC (bots, no humans):** all 18 story missions start and run with 4 players without desync or crash
  (smoke4: 18/18, 0 differences); a 65-minute session; network outages; latency, jitter and packet loss; checkpoint
  restarts; the hideout between missions; the package itself end to end (4 launchers, codes, helpers, 60 fps).
- **Not yet tested, needs you:** real separate PCs, real networks, and real people playing missions to the end.
  Bots cannot finish missions, so "mission completed with 4 players" is still open for every mission.

## Verified (SINGLE-PC unless noted; bots or scripted input)
| Feature | Evidence |
|---|---|
| Four genuine players with independent input, combat, items, revive, down/death | M2 report (F-0108..F-0161) |
| Own view and own HUD per PC (cropped quarter of the 2x2 frame), equal quarter size and zoom | F-0130, F-0137, F-0198 |
| Players 3-4 join through the game's own join (companion or spawned Warrior with own model), auto re-join | F-0154, F-0182, F-0183, F-0209 |
| Lockstep sync, 2-4 instances, desync detection, 0 mismatches in every run | M4/M5 findings, M7 report |
| Session policies: pause, skip votes, sit-out screen, disconnect (back in time / continue / restart), host leaving, join only in the lobby | M5 (F-0164..F-0178, F-0196) |
| Connection helper: join codes, ICE + STUN, forwarding through the host, LAN Join by IP | F-0172, F-0173, m5_package4.md |
| All 18 missions: 4 players (M2 intro 2 by design), 0 desync, 0 crash | smoke4 F-0231 |
| Players 3-4 in the 2-player chases (M18 car escape, M8 cart chase) | D24, F-0211..F-0217 |
| Camera parity for players 3-4 in 12 missions; HUD parity | F-0223..F-0229 |
| Checkpoint restarts with 4 players (6 missions + both chases); real mission end -> hideout | F-0204, F-0212, F-0216, F-0218 |
| 65-minute session, network outages through the helper, impairment series | F-0220, F-0219, F-0206 |
| Regression: single-player, original local 2-player (with the package), optional content | F-0193 |
| Package self-test (4 launchers, 60 fps, co-op save copy-back) | F-0230 |
| Originals unchanged (ISO, BIOS sets, original PCSX2) | `evidence/hashes/inputs_2026-10-12_m7.json`, 20/20 |

## Partial / incomplete
- **Mission completion with 4 people** (every mission) and 2-/3-player sessions through the story: needs you (test D).
- **LAN and internet**: only loopback on this PC so far; the helper's ICE re-dial after a real loss of connectivity is
  untested (T1g covered the game-data side only).
- **Feel of the controls with latency**: needs people.
- **60 fps timers**: no full audit that every game timer behaves at 60 fps (R-22); 60 fps runs are clean in sync.

## Not possible (blocked by the game's design, documented)
- A true single 3D view per PC (each PC rendering only its own player's camera) desyncs within seconds (F-0205, D23);
  every PC computes all four views and shows its own.
- HUD button prompts for players 3-4 (the game has only two prompt objects; F-0228).
- In some places only players 1-2 trigger the game's camera boxes; players 3-4 then follow player 2's camera changes
  (M16) or get them from a position check (M8, M6, M10) - equivalent cameras, but not always at the same moment.

## Failed tests (and what happened)
- **Fixed in this round:** the camera-relocation bug since M2 that lost camera changes for every player (F-0223); the
  4-runner tap rule that made 4-player car escapes fail (F-0213); players 3-4 run over at the start of the M8 chase in
  the first design (F-0216); player 3's Select ring (F-0222, F-0229).
- **Open watch item:** one unexplained 50-TLB-miss burst after a direct test call in the M9 cage (F-0226), not
  reproduced.
- **Kept as documented FAILED TEST:** local 2-player split drawn in the top half if someone switches the mod's patch groups
  on for local play (the package never does this; F-0193).

## Mission status (interim; final statuses after your tests)
All 18 missions: **IN PROGRESS** - every SINGLE-PC test passed (smoke4, F-0231; chapter runs where parity changes were
made); missing for "FOUR-PLAYER ONLINE VERIFIED": play-through from start to completion on 4 separate PCs over the
internet, plus 2- and 3-player sessions. Table with per-mission fixes: `docs/MISSIONS.md`.

## Deliverables (BRIEF 10)
| # | Deliverable | Where |
|---|---|---|
| 1 | Research notes with evidence | `docs/research/`, `docs/FINDINGS.md`, `evidence/` |
| 2 | Approved architecture and plan | `docs/plan/STAGE1_PLAN.md`, `docs/DECISIONS.md` |
| 3 | Reproducible mod source and patch generation from the user's own image, verified by hash | `mod/m2/*.txt`, `mod/make_pnach.py`, `tools/note_patches.py` (checks every patched word against the ELF), `docs/HASHES.md` |
| 4 | Emulator build with source, build instructions, licence compliance | `emulator/patches/0001-0020`, `emulator/build.ps1`, package `source\`, `tools/make_source_zip.py`, `docs/reports/M8_legal_review.md` |
| 5 | Networking components, configuration, protocol specification | `net/w4p-net/`, `docs/PROTOCOL.md`, `docs/research/m5_connection_design.md` |
| 6 | Mission-by-mission test report | `docs/reports/M6_report.md`, `docs/MISSIONS.md` |
| 7 | Windows instructions for non-experts | package `README.txt`, `QUICK-START.txt` |
| 8 | Final status report | this file |
| 9 | Git history, build instructions, checksums | git log, `docs/HASHES.md`, package `MANIFEST.txt`, `evidence/hashes/` |
| 10 | Legally distributable package only | `dist/warriors-4p-coop.zip` (no game/ISO/BIOS/extracted files, F-0230, M8 legal review) |

## Decisions for you
1. **Legal review L1 (GPL source):** A (recommended) give friends `dist/warriors-4p-coop-source.zip` (23 MB, complete
   source) together with the package; B put it inside the package; C keep patches + upstream link only.
2. **Legal review L2 (game fragments in the patch comments):** A (recommended) ship the patch without comments
   (`tools/make_package4.py --strip-comments`, same behaviour); B ship as is.
3. **Who gets the package:** A (recommended) only friends who own the game, by direct transfer; B a public page (needs
   its own review).
4. **Dates** for your LAN test (second PC) and the internet sessions with friends (`docs/reports/USER_TESTS.md`).
5. Still open from before: Q1 (the old 2-player test package E6: recommended skip, use the new package instead), the
   cut-off message "and the person got..." (please resend), exact single-player zoom (54 deg instead of 65, optional).

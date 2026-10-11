# M2 progress note (four genuine players) — 2026-10-11, in progress

Exit criteria: `docs/plan/M2.md`. Status: **not met yet** (criteria 1 partly; 2-6 open). Everything SINGLE-PC, one
instance, scripted input (W4P LocalBot slots), players 3-4 created with the game's own functions on the game thread
(test-only call facility), Mission 1 "New Blood".

## Exit criteria status (docs/plan/M2.md)
| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | Four players exist | **met** (players created with the game's functions; the game's own join needs companions, F-0109) | F-0111 |
| 2 | Independent input | **met** (one instance) | F-0112 |
| 3 | Same systems as players 1-2 (attack, grab, damage, enemies target 3-4) | not tested | - |
| 4 | Four views + own HUD per view | **half met**: four own full-screen views in 4 lockstep instances (F-0121, SplitAllowed forced in the tutorial); no HUD for players 3-4; centred text cut | F-0121 |
| 5 | 4 instances in lockstep >= 30 min, 0 mismatches, no crash | **met** with 1 view (Mission 1 tutorial, MTVU on): 35 min, 2,069 points, 0 mismatches; MTVU later found nondeterministic (F-0120) -> repeat with MTVU off and 4 views | F-0118, F-0120 |
| 6 | >= 29 fps (30 fps mode) | **met with 1 view**: median 29.97, 97 % of 10 s windows >= 29; 4 drawn views not measured; 60 fps mode not measured | `local/m2/q3_long/w4p_slot0.log` |
| 7 | Originals unchanged | to check at the end of M2 | - |

## Done
| Item | Evidence |
|---|---|
| Deterministic boot-to-Mission-1 input script (2 players, fresh memory cards) — no savestates needed (F-0107) | `tests/m2/nav/boot_to_m1_2p*.txt`, `local/m2/n9` |
| Engine patch group `[warriors-4p 4p]`, 697 words, every original checked against the ELF (`tools/note_patches.py`): GameMgr grown and per-player arrays widened (m2_gamemgr.md, m2_gamemgr_records.md), pads 0-7 polled, camera/ScreenEffects/listener/flag tables relocated (m2_pads_cameras.md), interim HUD guards (m2_hud_players34.md (A)) | `mod/m2/*.txt`, `mod/make_pnach.py` |
| 2-player Mission 1 runs unchanged with the 4-player patches (F-0108) | `local/m2/m2a..m2f` |
| Four players exist and the game stays up (count 4, valid handles, 4 cameras, pads 1/2 owned by players 3/4; 2.6 min, no crash) (F-0111) | `local/m2/m2k` |
| Debug tools: W4P `DebugWatch` (logged write watchpoints), `LocalBotN`, test call facility, position/pad tracking | fork patch 0007; `tests/m2/nav_probe.py` |

## Failed / open (kept on record)
- The game's own drop-in cannot add players 3-4 in Mission 1: no companion available (F-0109). Needs per-mission
  companion handling (D7, R-26).
- First 4-player attempt crashed in HUD code and corrupted player 4's handle (F-0110); fixed by the records relocation
  and HUD guards (F-0111).
- Players 3-4 did not move at first (R-27): the test characters were tutorial enemies with switched-off brains.
  Fixed (m2_player_control.md P-1, P-2); **independent input for all four players now VERIFIED** in one instance
  (F-0112). Players 3-4 cover less distance than players 1-2 (cause not checked).
- Views: Mission 1's tutorial keeps one view; four separate views not yet seen.
- No HUD for players 3-4 yet (interim guards).
- A 60 fps version of the boot script does not work yet (menu timing differs at 60 fps; R-22).

## Next
1. Deterministic creation of players 3-4 (W4P CallAt) and a 4-instance lockstep run (criterion 5).
2. A mission with free split views and companions; 4 views and HUD per view.
3. Four instances in lockstep (criterion 5), frame rate (criterion 6).

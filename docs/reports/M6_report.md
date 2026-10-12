# M6 report - mission-by-mission enablement (2026-10-12)

**Result: every SINGLE-PC part of M6 (`docs/plan/M6.md`) has test evidence; M6 is not complete, because criterion 4
(each mission played from start to end by four people) and the final per-mission statuses need you and your friends.**
All tests here: one PC, our PCSX2 build w4p-m6-3, MTVU off, bots or scripted input, no humans, no real network.
Environment per test is in the findings. Evidence: `evidence/M6/*.json`, research notes in `docs/research/`,
screenshots and logs in `local/` (not committed).

## Plain-English summary
- **All 18 story missions start, let four players in and stay in sync** with button-mashing bots (smoke tests with 4
  emulators in lockstep: see the table below). Missions 2 and 18 keep their 2-player openings by design.
- **Players 3-4 now play the two stretches that used to be 2-player only** (decision D24): in the Mission 18 car escape
  they are Cochise and Vermin and tap to run like players 1-2 (one button for everybody, one icon on screen; caught =
  the group retries); in the Mission 8 cart chase they are Snow and Ajax and tap-run in front of the cart. Example: a
  4-PC test run won the car escape with all four tapping; when player 3 stopped tapping he was caught, the game showed
  "You got wrecked", the retry brought all four back and the 7th try was won.
- **Players 3-4 get the same special cameras as players 1-2** in 12 missions (M1, M3, M5, M6, M8, M9, M10, M11, M13, M16,
  M17, M18). Example (Mission 16 park chase): before, players 1-2 had a side-scrolling chase camera and players 3-4 a
  close camera behind their back ("2 good screens and 2 zoomed-in screens"); now all four quarters show the side view,
  each following its own player. Example (Mission 17 boss): before, player 1's camera followed player 3 and player 2's
  followed player 4 once the boss fight began; now every view frames the boss with its own player.
- **A long-standing bug that also hit players 1-2 was found and fixed (LUIFIX, F-0223):** since M2 our 4-player camera
  change missed six instructions, so in some situations a camera change was silently lost (example: in Mission 16 the
  street chase camera never appeared, not even for players 1-2) and a stray value was written into game memory.
- **HUD for players 3-4:** the Select health ring and status panel, the radar timer ring, the radar zoom and the shadow
  spot under each character now work for players 3-4 too (F-0229). Not possible: on-screen button prompts for players
  3-4 (the game has only two prompt objects, F-0228).
- **Hideout:** after a really finished mission the hideout interlude works with 4 players (F-0218).

## Exit criteria
| # | Criterion | Evidence | Verdict |
|---|---|---|---|
| 1 | Smoke test per mission (4 instances, bots, >= 10 min, players 3-4 join, no crash/softlock) | **smoke4** with all fixes: 18/18 missions 0 mismatches, 0 TLB, 4 players in 17 (M2 by design) (F-0231); smoke3 before (F-0201) | **met (SINGLE-PC)** |
| 2 | Per-mission fixes with a finding and a re-test each | X1-X13, PINSVC/PLACE, HUD, FOVFIX, labels (F-0180..F-0209); D24 (F-0211..F-0217); camera parity (F-0223..F-0228); HUD parity (F-0229) | **done for every problem found on SINGLE-PC** |
| 3 | Restart / checkpoint per mission with 4 players | 6 missions (F-0204); M18 escape retry with 4 (F-0212); M8 cp3 reload with 4 (F-0216) | **met (SINGLE-PC)** |
| 4 | Completion from start to end with four people, plus 2- and 3-player checks | needs you: `docs/reports/USER_TESTS.md` test D | **open (needs the user)** |
| 5 | Hub interludes | X12 level jump (F-0185), real mission end -> hideout (F-0218) | **met (SINGLE-PC)** |
| 6 | Mission status table with one final status per mission | `docs/MISSIONS.md`: all IN PROGRESS until the human play-throughs | **open** |

## smoke4 (all fixes; SINGLE-PC, 4 instances in lockstep, loopback, random bots, SessionPolicies on, 900 s per mission)
| M | Name | Hash points | Mismatches | TLB misses | Players seen | First poll with 4 | Note |
|---|---|---|---|---|---|---|---|
| 1 | New Blood | 626 | 0 | 0 | 0, 1, 2, 3, 4 | 10102 |  |
| 2 | Real Live Bunch | 645 | 0 | 0 | 0, 1, 2 | - | joining off in the intro/tutorial by the script (by design, X13); players 3-4 see the waiting screen |
| 3 | Payback | 461 | 0 | 0 | 0, 1, 2, 4 | 7703 | player 3 join not seen in the 30 s samples (count 4 reached) |
| 4 | Blackout | 603 | 0 | 0 | 0, 1, 2, 3, 4 | 7697 |  |
| 5 | Real Heavy Rep | 449 | 0 | 0 | 0, 1, 2, 3, 4 | 7386 |  |
| 6 | Writer's Block | 473 | 0 | 0 | 0, 1, 2, 3, 4 | 6996 |  |
| 7 | Adios Amigo | 497 | 0 | 0 | 0, 1, 2, 3, 4 | 7130 |  |
| 8 | Encore | 422 | 0 | 0 | 0, 1, 2, 3, 4 | 8464 |  |
| 9 | Payin' The Cost | 445 | 0 | 0 | 0, 1, 2, 3, 4 | 6594 |  |
| 10 | Destroyed | 474 | 0 | 0 | 0, 1, 2, 3, 4 | 7668 |  |
| 11 | Boys In Blue | 445 | 0 | 0 | 0, 1, 2, 3, 4 | 9001 |  |
| 12 | Set Up | 510 | 0 | 0 | 0, 1, 2, 4 | 8754 | count 4 reached (3 not sampled) |
| 13 | All-City | 508 | 0 | 0 | 0, 1, 2, 3, 4 | 9545 |  |
| 14 | Desperate Dudes | 501 | 0 | 0 | 0, 1, 2, 3, 4 | 9833 |  |
| 15 | No Permits, No Parley | 510 | 0 | 0 | 0, 1, 2, 3, 4 | 9978 |  |
| 16 | Home Run | 534 | 0 | 0 | 0, 1, 2, 3, 4 | 9936 |  |
| 17 | Friendly Faces | 425 | 0 | 0 | 0, 1, 2, 3, 4 | 8536 |  |
| 18 | Come Out To Play | 674 | 0 | 0 | 0, 1, 2, 4 | 8634 | NEW: 4 players at the car escape (players 3-4 join as Cochise/Vermin, D24); smoke3 stayed at 2 |

**All 18 missions: 0 hash mismatches, 0 TLB misses** (422-674 common hash points each; 3 groups of 4 instances ran at the same time: 6-9, 15-18, 27-30; the PC was GPU-bound, about 13-22 polls/s). Mission completion is not tested (bots cannot do objectives). Evidence: `evidence/M6/smoke4_m01..m18.json`, `evidence/M6/smoke4_summary.json`, `local/m6/smoke4_[abc]_console.txt`. Pnach: mod/w4p_m1.pnach of commit c78aa8e (11733 addresses).

## Chapter runs (F-0232)
All 12 chapters changed by D24 or camera parity, started directly with 4 instances in lockstep (bots mashing buttons): **12/12 with 0 mismatches and 0 TLB misses**; the M8 cart chase and the M18 car escape were won with four tapping players. Camera framing itself was checked in the single-instance runs of the agents (F-0224..F-0228).

## Failed tests and open points (as prominent as the passes)
- **FAILED TEST (fixed): the camera relocation bug F-0223** - affected every player since M2 in situations with camera
  blends or callback names (e.g. Mission 16 street chase camera, blend hand-overs).
- **Unexplained once:** a 50-TLB-miss burst in one single-instance M9 cage test after a direct test call (F-0226); not
  reproduced in the same sequence or in 4-instance runs. Watch item for your play-throughs of Mission 9.
- **Not possible:** HUD button prompts for players 3-4 (F-0228). In M16 players 3-4 switch chase cameras when player 2
  crosses a camera point (the game's camera boxes only notice players 1-2), so a player far behind player 2 sees his
  rail from its start end (F-0225).
- **Not tested on SINGLE-PC:** mission completion (bots cannot do objectives), human play, LAN/internet, 2- and 3-player
  sessions through every mission.

## Tests you must do personally
See `docs/reports/USER_TESTS.md` (test D: one play-through per mission with 4 players, and 2-/3-player sessions).

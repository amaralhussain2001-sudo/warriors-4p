# Decision log

## Made during Stage 1 (technical, within the brief's allowances)

| ID | Date | Context | Options | Choice | Evidence | Approval |
|---|---|---|---|---|---|---|
| S1-01 | 2026-10-10 | Ghidra cannot decode R5900 | stock MIPS / extension / own tooling | Install ghidra-emotionengine-reloaded v2.1.38 in the user profile (allowed by §2.2.3) | F-0040; HASHES.md | allowed by brief |
| S1-02 | 2026-10-10 | Runtime experiments need an emulator | user install / sandbox copy | Sandbox copy in `local/pcsx2/base`, per-instance `-datapath`; `portable.txt` removed from the copy only | F-0041 | allowed by brief |
| S1-03 | 2026-10-10 | E1 needs AI combat reachable without long navigation | story mission / Quick Rumble | Quick Rumble "War Party" for E1-E3; story missions for E4 | E1 RESULTS | technical |
| S1-04 | 2026-10-10 | Frame-aligned comparison without modifying PCSX2 | async PINE reads / in-game barrier | Temporary in-game barrier via experiment pnach (not part of the mod) | E1 README | technical |
| S1-05 | 2026-10-10 | Input injection for experiments | PCSX2 input recording (2 pads, GUI only) / game-side injection | Game-side injection after the libpad read | F-0051, F-0052 | technical |

## Waiting for the user (see docs/plan/STAGE1_PLAN.md §15)
D1 approval of Stage 2; D2 PCSX2 build toolchain; D3 flashback missions A-E scope; D4 hub interludes handling;
D5 transport/hosting; D6 cross-machine and online tests with other people; D7 disconnect "continue" handling.
None is decided yet.

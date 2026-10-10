# Decision log

## Made during Stage 1 (technical, within the brief's allowances)

| ID | Date | Context | Options | Choice | Evidence | Approval |
|---|---|---|---|---|---|---|
| S1-01 | 2026-10-10 | Ghidra cannot decode R5900 | stock MIPS / extension / own tooling | Install ghidra-emotionengine-reloaded v2.1.38 in the user profile (allowed by §2.2.3) | F-0040; HASHES.md | allowed by brief |
| S1-02 | 2026-10-10 | Runtime experiments need an emulator | user install / sandbox copy | Sandbox copy in `local/pcsx2/base`, per-instance `-datapath`; `portable.txt` removed from the copy only | F-0041 | allowed by brief |
| S1-03 | 2026-10-10 | E1 needs AI combat reachable without long navigation | story mission / Quick Rumble | Quick Rumble "War Party" for E1-E3; story missions for E4 | E1 RESULTS | technical |
| S1-04 | 2026-10-10 | Frame-aligned comparison without modifying PCSX2 | async PINE reads / in-game barrier | Temporary in-game barrier via experiment pnach (not part of the mod) | E1 README | technical |
| S1-05 | 2026-10-10 | Input injection for experiments | PCSX2 input recording (2 pads, GUI only) / game-side injection | Game-side injection after the libpad read | F-0051, F-0052 | technical |

## Stage 1 plan approval — 2026-10-10

User's message (verbatim): "each device has different cpu and gpu but that's should not be mattter i guess if u send
the buttons only? all your questions use the recommended"

Reading: the user chose the recommended option for every question in STAGE1_PLAN.md §15. D1's recommended option was
"Yes, approve Stage 2, but stop after the first proof (M1)", so this is explicit approval of the plan with the M1
stop gate. No changes to the plan were requested. The CPU/GPU remark is answered in chat (cross-machine determinism is
still the E6 kill test).

| ID | Decision | Choice (recommended option) | Approval |
|---|---|---|---|
| D1 | Approve Stage 2 | Yes; **stop and report after M1** before M2 | approved 2026-10-10 |
| D2 | PCSX2 build toolchain | A: Visual Studio Build Tools (user accepts Microsoft's terms). Correction: Build Tools 2026 v18.10.1 with MSVC 14.50/14.51, CMake, Ninja and Windows SDK 26100 were already installed (2026-09-19, before this project), so no install is needed for an MSVC build (F-0075) | approved 2026-10-10 |
| D3 | Flashback missions A-E | A: optional; keep original behaviour (no four-player work); must still load and work at original player count with the mod | approved 2026-10-10 |
| D4 | Hub interludes | A first: players 2-4 stay connected and in sync, see a "Host is in the hideout" waiting screen while the host does the required hub steps; B (4-player hub) later | approved 2026-10-10 |
| D5 | Connection method | A: direct with ICE + public STUN + join code; C (overlay VPN) for early tests; B (own relay) only if tests show NAT failures | approved 2026-10-10 |
| D6 | Testers and other PCs | user will arrange a second PC soon for E6 (user notes each device has a different CPU and GPU) | approved 2026-10-10 |
| D7 | "Continue without the player" | replaced companion returns to AI via the game's own release; an added character is removed | approved 2026-10-10 |

## Made during Stage 2

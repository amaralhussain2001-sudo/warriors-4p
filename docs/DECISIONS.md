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

### After M1 (2026-10-11), user decisions in chat

User's messages (verbatim, in order):
1. "okay i have better question can we insted of make if the players are near let's make it always the camera on solo unless the player click something then it will switch to the second mode ( if he wants so not depends on players ) is that possable?"
2. "also the game can you make it 60fps ? or the emulator idk but i don't want to play with 30fps"
3. "also make sure you choose best settings because i put them randomly i'm not sure if it is best settings so you have to make sure you choose the right oncs if i did not do that to make it use my resource to give me a good quality and fps in the game and without issues"
4. "switch only when the player click special button on controll to switch it also start do the plan ( i don't have second pc to test right now so i will test tomorrow when you already finish everything)"
5. "and continue your perivous work i just stopp it by mistake"

| ID | Decision | Choice | Approval |
|---|---|---|---|
| D8 | View policy (changes BRIEF §4.5 "shared only when all players are close") | Every player always sees their own camera, full screen. A special controller button switches **only that player's screen** between "my view" and "all players' views" (grid). Presentation-only, so it cannot cause desync. The game's automatic merge is disabled during online sessions (needs a game patch; HYPOTHESIS until tested) | user, 2026-10-11 (messages 1 and 4; option A of the chat question) |
| D9 | Frame rate | User does not want to play at 30 fps. Pursue a real 60 fps (characters, not only camera/clock). PCSX2's disabled "60 FPS" flag gives 60 rendered frames but characters still update about 30 times per second (`evidence/M3/f4_fps60_ee2_motion.json`) | user, 2026-10-11 (message 2) |
| D10 | Emulator settings | Claude chooses and measures the settings profile for quality and frame rate on the user's PC (RTX 5090, Ryzen 9 9950X3D, 4K 240 Hz). The user's own PCSX2 installation and its settings stay untouched (protected); the profile applies only to the warriors-4p build | user, 2026-10-11 (message 3) |
| D11 | Widescreen 16:9 | Recommended option taken (user has accepted recommendations before; not answered explicitly): add PCSX2's native widescreen patch as a session option and test sync with it | recommended, to confirm in the next report |
| D12 | Milestone stops | User asked to "start do the plan" and to have it finished for a test tomorrow. Work continues past milestone ends without waiting; each milestone still gets its report, tag and hash check. E6 (second PC) will be run by the user tomorrow with a package prepared here | user, 2026-10-11 (message 4) |

User message 2026-10-11 (verbatim): "if you are copy player one to player 3 and 4 ( make sure only the first player control the ganstar not all of them )"

| ID | Decision | Choice | Approval |
|---|---|---|---|
| D13 | Gang commands with 3-4 players | Only player 1 commands the gang. Players 3-4 (companions taken over or spawned copies of player 1's character) never get gang commands. Player 2: keep the original 2-player behaviour unless it already differs; reported to the user (research `m2_gang_command.md`) | user, 2026-10-11 |

User message 2026-10-11 (verbatim, session start): "My decision on player 4's name in Mission 13: option A (load one
extra Warrior model so player 4 has their own body and name)."

| ID | Decision | Choice | Approval |
|---|---|---|---|
| D14 | Player 4's body and name when no other Warrior model is loaded (Mission 13, F-0143) | A: load one extra Warrior model when a fourth player joins, so player 4 gets their own body and HUD name (not a Rembrandt copy). Needs research on the game's model loading and a memory check; if it proves impossible, report back before any fallback (B/C/D) | user, 2026-10-11 |

User message 2026-10-11 (verbatim, answer to the M2 report questions): "Q1 A, Q2 A, continue"

| ID | Decision | Choice | Approval |
|---|---|---|---|
| D15 | Revive blocked by a teammate standing between reviver and downed player (game's own sight sweep FUN_0021C0A8, F-0157, R-30) | A: keep the original rule (no patch); players step aside | user, 2026-10-11 |
| D16 | Widescreen 16:9 default (confirms D11) | A: widescreen on by default in the package/session profile | user, 2026-10-11 |

User message 2026-10-11 (verbatim): "U1 A U2 A U3 A, B A, C A, continue"

| ID | Decision | Choice | Approval |
|---|---|---|---|
| D17 | U1: rights of a non-host player who paused | A: he may only resume (Start); the host controls the pause menu (session_policies.md 1.6) | user, 2026-10-11 |
| D18 | U2: Esc in an online session | A: Esc becomes a pause request for everyone (Start through the lockstep), never an emulator pause (R-24) | user, 2026-10-11 |
| D19 | U3: skipping a chain of cutscenes | A: a completed vote skips only the current scene (injected Cross); every scene of a chain is voted on separately | user, 2026-10-11 |
| D20 | B: automatic router port opening (UPnP/PCP) | A: off; connections use ICE + STUN + join/reply codes only (m5_connection_design.md 7) | user, 2026-10-11 |
| D21 | C: public message service (ntfy.sh) to remove the reply-code step | A: not now; reply codes stay | user, 2026-10-11 |
| D22 | How players 3-4 appear on the radar (the game has only 1P/2P icons; F-0194 recoloured '2P') | Real '3P' and '4P' icons in the game's style, built at runtime from the game's own graphics, and keep the different colours (player 2 yellow, 3 red, 4 green) | user, 2026-10-12 ("can't we make it P3 P4? even if they different colors") |

Open from the same list: D (dates for the LAN test with the second PC and the internet test with friends) - not answered yet.

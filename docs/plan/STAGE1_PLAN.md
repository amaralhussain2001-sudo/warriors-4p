# Stage 1 plan: The Warriors (SLUS-21215) four-player online story co-op

Date: 2026-10-10. Status: **Stage 1 complete, waiting for the user's decision. No Stage 2 work has started.**
Evidence IDs (F-xxxx) refer to `docs/FINDINGS.md`. Experiments are under `tests/experiments/`. Every test so far is
SINGLE-PC, scripted bot input, no network, no impairment. Nothing here claims that online play works.

---

## 1. Feasibility assessment

**Overall: feasible in principle, with high effort and two open kill risks (cross-machine determinism, and the
4-player engine extension). Confidence that a complete 18-mission four-player online result is reachable: low to
medium (roughly 30-50 %, a judgment, not a measurement).** The pieces that would have killed the cheapest
architecture early were tested and passed on one PC.

| Component | Assessment | Confidence | Main evidence |
|---|---|---|---|
| Deterministic lockstep on one PC | Works: identical game state for 60 s of 5v5 AI combat with identical input | High (one PC) | E1, F-0070 |
| Lockstep across different PCs | Unknown; must be tested with a second PC | Medium | E6 not run |
| Waiting for network input | Must stop the whole emulated machine, not the game | High | E3b failed, E3c passed (F-0072) |
| Input injection for 4 players | Works for any pad slot at an exact game frame | High | F-0051, F-0052, E4 |
| Genuine 3rd/4th player in the engine | Engine has hard 2-player storage; naive extension crashed; needs relocation of several subsystems' per-player arrays | Medium-low | F-0060, F-0061, F-0062 |
| Independent full-screen cameras | Feasible only if every PC simulates and renders all players' views identically and the emulator shows only the local one | Medium | E2, E2b, F-0027 |
| Mission scripts for 4 players | Large amount of `player2` logic; Lua source can likely be injected at runtime | Medium | F-0057, MISSIONS.md |
| Session/transport | Standard techniques; no platform account required for the base option | High | transport_options.md |
| Rollback | Not viable with PCSX2 savestates | High | E5 |

What could make it infeasible: (1) E6 shows desync across machines that no settings profile fixes; (2) rendering four
views makes the emulated game too slow and EE overclocking cannot recover it; (3) engine extension to four players
hits a hard memory/pool limit; (4) the user does not approve a PCSX2 build toolchain and the no-fork fallback proves
too fragile.

## 2. Verified findings (summary; full list in FINDINGS.md)
- Image and environment: F-0001 (Redump-matching ISO; no root ISO), F-0041/F-0042 (sandbox, background input, screenshots).
- Game structure: F-0002-F-0008 (disc, ELF, Lua 4.0.1, WAD, RenderWare, dev-only TCP code), F-0013 (964 Lua bindings).
- Story and missions: F-0009, F-0010, F-0063, F-0064, F-0065, F-0066.
- Players/input: F-0020-F-0025, F-0031, F-0051-F-0056, F-0060, F-0062.
- Camera/HUD: F-0026-F-0030, F-0049, F-0074.
- Time and determinism: F-0045-F-0048, F-0058, F-0070-F-0073.
- Experiments: E1 PASS, E2 camera FAILED / renderer PASS, E3 in-game wait FAILED / VM pause PASS, E4 what-breaks recorded, E5 measured.

## 3. Hypotheses and unresolved questions

| Question | Status | How it will be resolved |
|---|---|---|
| Cross-machine determinism (Intel vs AMD, different GPUs) | HYPOTHESIS | E6 with a second PC (needs the user, D6) |
| Original 2P split/merge rule and its distance threshold | HYPOTHESIS (code read; merged view observed) | trace the follow-camera group logic; observe in an open mission (M1) |
| Original 2P separation rules (tether/teleport/streaming) | unknown | trace and observe in M1/M2 before any design (§4.6) |
| Original 2P difficulty scaling, friendly fire, player collision, game-over rule | unknown | static search + runtime tests in M2/M6 |
| RNG seeding | HYPOTHESIS (F-0059) | trace writes to RNG state at boot |
| `dostring` usable from the game's Lua state | HYPOTHESIS (F-0057) | call it via the experiment call facility (M2 first day) |
| Displayed-viewport choice is presentation-only (crop) | HYPOTHESIS | E2c in M1 |
| Human/animation/memory pool limits for extra characters | unknown | measure in M2 |
| Per-mission original 2P support | preliminary (MISSIONS.md) | 2P runs per mission in M6 |
| Hidden time leaks under VM-level gating with real network jitter | HYPOTHESIS that none matter | hash checks in M1/M4 soak tests |

## 4. Main-story mission scope
See `docs/MISSIONS.md`. Summary:
- **MAIN STORY:** 18 missions, levels 99, 80, 87, 34, 2, 3, 5, 81, 86, 93, 31, 14, 9, 51, 52, 54, 55, 84
  ("New Blood" ... "Come Out To Play"), plus the **required hub interludes** in level95 between missions.
- **OPTIONAL (proposed):** flashback missions A-E (82, 92, 83, 20, 11) because no story step requires them; Armies
  of the Night 60-64; level95 free-roam activities; Rumble arenas 101-137.
- **UNRESOLVED:** level7 "Graveyard Shift" (name only, no scripts: probably cut).
- Decisions needed: D3 (flashbacks) and D4 (hub interludes).

## 5. Player and companion strategy
- **Input path for players 3 and 4:** the game polls only pads 0 and 4 (F-0055) but has 8 pad slots and a player-to-pad
  mapping (`MakePlayer` searches 8 slots, F-0056). The mod will poll all slots and feed every player's input into its
  pad slot at the game's own read point (verified mechanism, F-0052). On each PC the local controller is read by the
  emulator as pad 1A; the network layer supplies the other players' inputs.
- **Creating genuine players:** use the game's own `MakePlayer` on a companion, as the original does for player 2
  (F-0024; E4 showed the engine binding a companion to a new pad and driving it). Players 3/4 are then processed by
  the same human/combat/AI systems.
- **Template:** player 2's mechanism and character setup; where a mission needs an added (not replaced) character,
  spawn a Warriors human with player 2's setup and make it a player.
- **Engine limits found (work list, `docs/research/static_analysis.md` §6):** GameMgr player storage (2), camera
  per-viewport arrays (2), viewport/render objects (2), ScreenEffects per-viewport data, HUD slots (2), audio
  listeners (2), pad polling (2), ~17 player-2-specific functions, ~80 count checks, Lua scripts. Plan: allocate
  4-entry replacements in free memory and redirect every accessor (inventory first, then subsystem by subsystem).
- **Preliminary companion analysis:** per-mission named Warriors and P2 branches are in MISSIONS.md; roles (critical
  vs replaceable) are classified in M6 with the method described there. Default: replace non-critical companions;
  preserve-and-add for critical ones. No fallback is proposed for any mission.

## 6. Independent camera and HUD architecture (with E2 results)
- E2: changing one PC's camera changes the simulation (animation update and later everything) → each player's camera
  is part of the simulation and must be identical on every PC. The camera stick input travels with the lockstep input.
- Changing the emulator's renderer did not change the simulation (E2b).
- Rendering different amounts of work on different PCs would change emulated frame time and, because the game clock is
  cycle-based (F-0047), the simulation. Therefore **every PC renders the same views**.
- **Proposed design:** the game runs as 4-player split screen internally on every PC (the engine already has a 2x2
  layout path, F-0027). The emulator shows only the local player's quadrant, cropped and scaled to full screen, with
  PCSX2 GS upscaling for sharpness. Each quadrant contains that player's own HUD (the HUD is drawn per viewport).
  When the engine merges the views into one (all players' cameras coincide), every PC shows the full frame: that is
  the "all players close together" shared camera, using the game's own merge rule extended to all active players.
  When players separate, each returns to their own quadrant. No streamed video; each PC renders its own picture.
- To verify: E2c (crop is presentation-only), the original merge rule and threshold, 4-view performance (R-03).

## 7. Online networking and emulator integration (four layers)
1. **Session:** a small launcher app (ours) runs the lobby: join code, player list, slot choice (1-4, default host =
   P1 then join order), version handshake (protocol version, mod build ID, emulator build ID, ISO SHA-256 computed
   locally, settings-profile hash, BIOS check if E6 shows it matters), mission start, co-op memory card handling.
2. **Transport:** behind an interface. Default: UDP with ICE (libjuice, MPL-2.0) using public STUN, join code carries
   the host's connection info; optional own relay/rendezvous (needs a VPS: D5). LAN and overlay VPNs work through the
   same interface for testing.
3. **Simulation sync:** delay-based deterministic lockstep. Each frame's packet carries every local player's pad state
   (buttons, both sticks) for frame F+D. An instance runs frame F only when all players' inputs for F are present.
   State hashes of game RAM regions (excluding the known timing counters) every N frames; on mismatch: log first
   divergent window and a memory diff, pause, and resync from the host's state (slow, seconds; R-07).
4. **Local presentation:** crop/scale of the local quadrant, OSD messages (pause owner, skip votes, disconnect
   countdown), local audio and vibration.
- **What goes in PCSX2 (fork, GPL-3.0):** frame gate (block at the game's frame boundary until inputs are present),
  local IPC to the launcher (inputs in, hashes out), memory writes of inputs into the pad buffers at the gate,
  state hashing, savestate send/receive for resync, quadrant crop, OSD, settings-profile lock.
- **What goes in the game patch:** pad polling for all slots, 4-player engine extension, Lua script changes (injected as
  source if F-0057 holds), local-view index (presentation only), cutscene/pause hooks for the session policies.
- **Emulator build plan:** fork PCSX2 at tag v2.9.115 (commit cf3c3720), build with clang-cl + Ninja + Qt 6.12 per the
  upstream Windows instructions (needs Visual Studio Build Tools: D2), keep the change set small and rebase-friendly;
  publish source with every build (GPL).
- **No-fork fallback (if D2 is refused):** drive PCSX2's pause/frame-advance hotkeys from the launcher and write inputs
  through PINE while paused. Feasible for a prototype, fragile for release (window messages, vsync granularity).

## 8. Architecture comparison and recommendation

| Approach | Consistency | Independent cameras | Needs (game / emulator) | Latency | Bandwidth | Main failure modes | Effort / risk |
|---|---|---|---|---|---|---|---|
| **Delay-based lockstep + hashing + host resync (recommended)** | Identical simulation on all PCs (E1) | Yes, all views simulated, local crop | 4P patch / frame gate fork | input delay ≈ RTT/2 rounded up to 33 ms frames, plus jitter margin | small (inputs only; estimate tens to ~130 kbit/s per player with redundancy) | cross-machine determinism (E6), stalls on lag spikes | High / medium |
| Rollback | same | same | same + fast state | best feel | small | savestate 220 ms save, 57 ms load → impossible | rejected (E5) |
| Host-authoritative state replication + prediction | host decides; clients replay | yes | deep game rewrite to separate and apply state; PS2 game state is scattered over ~32 MB (E2 showed hundreds of KB change per second) | client lag on remote actions | very high | divergence of client-side simulation, rewrite scale | rejected (scale) |
| Dedicated headless emulator server | as lockstep or replication | yes | same as chosen model + server hosting | adds a hop | small | cost, still needs determinism | not needed now; optional resync source later |
| Lockstep without emulator gate (game waits) | breaks (E3b) | — | patch only | — | — | desync | rejected (E3b) |
| Existing netplay forks / DEV9 / streaming | not applicable | no | — | — | — | — | not usable (existing_online_methods.md) |

## 9. First critical proof of concept (M1)
**Scope:** two PCSX2 instances on this PC, both running the patched game in the original 2-player mode (no 4-player
engine work yet), in one story mission with combat (Mission 1 "New Blood" after the tutorial pen, or Mission 2).
Each instance reads its own local controller (scripted bot first, then a human at each instance), exchanges inputs
over loopback UDP through the transport interface, and runs the frame gate in the PCSX2 fork (or the no-fork
fallback). Instance A displays player 1's view cropped full screen, B displays player 2's view; when the views merge,
both show the merged view.
**Pass criteria:** (a) 10 minutes of play including combat with hash checks every 30 frames and zero mismatches;
(b) E2c: the crop does not change game state (hash equality with an uncropped instance); (c) measured added input
delay on loopback ≤ 2 frames and stable frame pacing; (d) split and merge transitions shown correctly on both screens;
(e) original ISO/BIOS hashes unchanged. **Fail:** any desync, or (b) fails.

## 10. Milestones and dependencies (relative effort, uncertainty)

| M | Content | Depends on | Exit criteria (summary) | Effort (relative) | Uncertainty |
|---|---|---|---|---|---|
| M1 | PoC above | D2 | §9 | M | M |
| M2 | Genuine 4-player local gameplay in one mission (engine extension: GameMgr, camera, viewports, HUD, audio, pads, scripts) on SINGLE-PC | M1 | 4 genuine players with independent input, no crash for 30 min, HUD per player, enemies engage all players | XL | H |
| M3 | 4 independent cameras/HUD with merge rule, all transitions | M2 | each instance full-screen own view; merge only when all close; hashes equal across instances; frame rate acceptable | L | H (R-03) |
| M4 | Sync layer 2-4 instances, loopback + LAN, impairment, desync detection/resync | M1, M3, E6 | 2/3/4-instance sessions without desync over 30 min with simulated 100 ms RTT, 20 ms jitter, 2 % loss; resync works | L | M |
| M5 | Session and transport, handshake, NAT traversal/relay | M4, D5 | LAN then internet join with the user | M | M |
| M6 | Mission-by-mission enablement (18 missions + hub interludes) | M2-M5 | each mission reaches a final §8.4 status with evidence | XL | H |
| M7 | Robustness, regression (1P, local 2P, optional content smoke tests) | M6 | soak tests, disconnect/timeout tests, regressions pass | L | M |
| M8 | Packaging, instructions, legal review, final report | M7 | §10 deliverables | M | L |

Effort letters are relative (M < L < XL); calendar time is not estimated because it depends on testers' availability.

## 11. Testing strategy (§8)
- Tooling already built: sandbox instance manager, PINE client, frame barrier, frame-exact input injection, RAM
  diff/classification, screenshots (`tools/`, `tests/experiments/`).
- To build: N-instance launcher with slot assignment; per-frame hash stream; transport impairment (latency, jitter,
  loss, reorder, disconnect) inside our transport; scripted bots per slot; local savestates per mission for fast tests.
- Labels: every result tagged SINGLE-PC / LAN / INTERNET, bot or human, impairment on/off. Bot tests for sync and
  regression; human tests for control, camera and HUD.
- **Needs other people/computers:** E6 (second PC), LAN tests (2-4 PCs), internet tests (4 PCs on different networks
  for "FOUR-PLAYER ONLINE VERIFIED"), human play for feel. The user personally: approve D2/D5, arrange testers with
  their own game copies and BIOS, run the instructions we provide and send back logs/hashes.

## 12. Fallback conditions (evidence-based)
A mission may fall back (only with the user's acknowledgement) if, after documented attempts: (a) a hard engine limit
(memory/pool) prevents a 3rd/4th player there, measured; or (b) repeated failed tests (≥ 3 documented attempts with
different fixes) show desync/crash we cannot remove. "An NPC can't be replaced" is not a reason. A fallback keeps the
original behaviour (2P online if possible). No fallback is proposed now.

## 13. Session policies (§4.6) — implementation
| Policy | Implementation | Feasible as written? |
|---|---|---|
| Pause: anyone pauses, all pause, "Paused by Player N", only pauser/host unpauses | Start is a lockstep input; the session layer accepts Start from any player to pause (the game's pause menu opens on all PCs deterministically) and shows "Paused by Player N" via OSD; while paused only the pauser's/host's inputs are forwarded | Yes (to verify the pause menu's pad handling) |
| Cutscene skip only when all connected pressed; show "k/N want to skip" | Detect cutscene state from game memory; skip presses become votes in the input stream; when all connected voted, the same frame injects the skip on every PC; OSD shows votes | Yes (cutscene flag to locate) |
| Saving: co-op progress on every PC, separate from single-player saves | Dedicated co-op memory card image per group; host sends it at session start (hash-checked); the game's autosave writes identical data on every PC; single-player cards never mounted in co-op | Yes |
| Joining only in the lobby before a mission | Game's own join disabled during missions; players set up at mission start by the mod | Yes |
| Disconnect: freeze all with 60 s countdown; resume if back; else host chooses continue-without or restart from checkpoint | The frame gate stalls naturally; OSD countdown; on timeout the host's choice is broadcast with a frame number. "Continue without": the dropped player's character returns to AI via the game's own `ReleasePlayer` (F-0056) if it was a replaced companion, or is removed if it was an added character. "Restart": checkpoint restart with the remaining players | Yes (handling proposal for D7) |
| Host leaving ends the session; everyone keeps progress | Session ends; co-op card already saved on every PC | Yes |
| Player separation as original 2P; no new leash | Original rule to be traced first (unknown now); apply the same rule to players 2-4 | Unknown until traced (R-16) |
| Difficulty unchanged | Do not touch; report any original 2P scaling found | Yes |
| Friendly fire/collision as original 2P | Trace and apply to 4 | Unknown until traced |
| Game over: natural extension | Trace the original 2P rule (revive items exist), extend to "all active players down"; ask if unclear | Unknown until traced |
| Slots: lobby choice, default host P1 then join order | Launcher | Yes |

## 14. Project structure, deliverables, licensing and distribution
- Structure as in BRIEF §2.3 (created). Git history with two commits so far; `local/` ignored.
- Patch delivery options: (1) **runtime patches through PCSX2's pnach system plus support code in the fork
  (recommended)**: nothing from the game is distributed; players keep their own ISO; (2) a rebuilt ISO/ELF generated
  on the user's PC from their own image (possible later if pnach limits bite; never distributed); (3) code in unused
  RAM (experiments used 0x00096000-0x000FFFFF; release should prefer memory proven unused or fork-managed);
  (4) emulator hooks (frame gate, crop, OSD).
- Licensing: PCSX2 GPL-3.0 (effective) → publish fork source with builds; libjuice MPL-2.0; our launcher and patch
  under a license of the user's choice; Ghidra extension used only locally (Apache-2.0). The package never contains
  the game, ISO, BIOS, extracted assets, savestates or memory cards. A legal review of package contents happens in M8;
  any uncertainty is raised before distribution (§11).

## 15. Decisions the user needs to make (each with a recommendation)
- **D1. Approve Stage 2?** Recommendation: approve with M1 as the first gate (stop and report after M1).
- **D2. PCSX2 build toolchain** (needed for the frame gate). A: install Visual Studio Build Tools system-wide
  (Microsoft license terms apply; you accept them). B: portable MSVC download script (still Microsoft terms).
  C: no fork, hotkey-driven fallback. Recommendation: A.
- **D3. Flashback missions A-E.** A: optional, keep original behaviour (no 4P). B: include in 4P scope later.
  Recommendation: A for now.
- **D4. Hub interludes between missions.** A: players 2-4 stay connected, their PCs run the hub in sync but show a
  "Host is in the hideout" waiting screen while the host does the short required steps (original hub is 1-player).
  B: make the hub 4-player too. C: auto-complete hub steps (cutscenes still play for all). Recommendation: A first, B later.
- **D5. Connection method for friends.** A: direct with ICE + public STUN + join code (no account, no cost; some NATs
  fail). B: A plus our own small relay server on a VPS (about $4-5/month; account and payment needed).
  C: overlay VPN (Radmin/ZeroTier/Tailscale) as the supported method. Recommendation: A, with C for early tests,
  B only if tests show NAT failures.
- **D6. Testers and other PCs** for E6 and LAN/internet tests (each with their own game copy and BIOS). Recommendation:
  arrange one second PC soon (E6 is a kill test).
- **D7. "Continue without the player" handling** (§13): replaced companion returns to AI; added character removed.
  Recommendation: accept.

## 16. Risk register summary
Top risks (full list `docs/RISKS.md`): R-01 cross-machine determinism (kill), R-02 engine extension size, R-03 4-view
performance, R-04 camera feeds simulation (handled by design, to verify), R-05 toolchain approval, R-08 scripts,
R-16 separation rules unknown, R-17 overall scope.

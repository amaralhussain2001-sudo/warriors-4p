# Risk register (Stage 1, 2026-10-10)

Scale: likelihood / impact = Low, Medium, High. "Kill" = could make a core requirement infeasible.

| ID | Risk | L | I | Evidence | Mitigation / test |
|---|---|---|---|---|---|
| R-01 | **Cross-machine non-determinism** (different CPUs/GPUs/OS) breaks lockstep | M | Kill | E1 passed on one PC only; GS renderer change was harmless (E2b); recompiler code paths may depend on host CPU features | E6 on two different PCs before M4; locked settings profile; per-frame-window state hashing; resync |
| R-02 | Engine extension to 4 players is larger than estimated (2-sized arrays across camera, viewport, HUD, audio, GameMgr; ~200+ code sites; scripts with `player2` everywhere) | H | High | F-0060, F-0061, F-0062 (crash with player 3) | M2 starts with a systematic accessor inventory; relocate arrays to new storage; incremental tests per subsystem |
| R-03 | Rendering 4 viewports exceeds the emulated PS2's frame budget (game slows to <30 fps in emulated time) | M | High | Not measured | Measure in M3; EE cycle-rate overclock (identical on all peers); reduce effects/LOD for extra views |
| R-04 | Camera/presentation feeds simulation (animation LOD, effects RNG) | H (confirmed for camera) | High | E2: camera-only change diverged; shared RNG F-0058 | Simulate all players' cameras identically everywhere; render all views identically; crop only in the emulator (E2c test in M1) |
| R-05 | Emulator-level lockstep needs a PCSX2 modification; toolchain install needs approval | H | High | E3 (in-game waiting not deterministic); no compiler on this PC | User decision D2; fallback: hotkey-driven pause/frame-advance prototype (fragile) |
| R-06 | Input latency too high for combat over the internet (delay-based lockstep, no rollback) | M | Medium | E5: rollback infeasible (save 220 ms) | Measure RTT/jitter per pair; adaptive input delay; 30 fps game gives 33 ms per frame of slack |
| R-07 | Desync recovery is slow (state ~15 MB) | H | Medium | E5 | Prevent desyncs; delta-encode against a shared state; resync at checkpoints |
| R-08 | Mission scripts hard-code two players in ways that need per-mission rewrites | H | High | MISSIONS.md counts | Lua source injection via `dostring` (F-0057, to verify); shared helper overrides; per-mission patches |
| R-09 | Mission-critical companions cannot be replaced; adding characters exceeds human/animation/memory pools | M | Medium | Human pool size not yet known (F-0053) | Measure pools and free RAM in M2; preserve-and-add with player-2 template |
| R-10 | Hub interludes (level95) are single-player in the original; 4-player handling undefined | H | Medium | F-0064, F-0066 | User decision D4 |
| R-11 | NAT traversal fails for some friends without a relay | M | Medium | transport research | Relay option (user decision D5); overlay VPN fallback |
| R-12 | GPL obligations for a modified PCSX2 (GPL-3.0 effectively) | H (obligation exists) | Medium | pcsx2_capabilities.md §8 | Publish fork source with each build; legal review before distribution (§11) |
| R-13 | Memory-card based co-op saves diverge or overwrite single-player saves | L | High | game autosaves after missions (F-0033) | Separate co-op card file per session; identical card at session start; hash check |
| R-14 | Hidden time leaks (audio/stream completion, IOP) differ between peers even with VM-level gating | L | High | E3c passed on one PC | Hash checks from the first M1 runs; long soak tests (M7) |
| R-15 | Experiment code-cave area (0x00096000-0x000FFFFF) is used by the kernel in some situation | L | Medium | F-0050 observation only | Prefer emulator-side or ELF-internal space for the release patch; watchdog checks |
| R-16 | Player separation: original 2P rules (tether, teleport, streaming of distant areas) unknown; 4 widely separated players may break world streaming | M | High | not yet traced | Trace in M2/M3; report before adding any limit (§4.6) |
| R-17 | Scope/effort: the whole project is very large for the available tooling and testers | H | High | this report | Milestone gates with kill tests; honest status per mission |

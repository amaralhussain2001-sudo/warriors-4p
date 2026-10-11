# Risk register (Stage 1, 2026-10-10)

Scale: likelihood / impact = Low, Medium, High. "Kill" = could make a core requirement infeasible.

| ID | Risk | L | I | Evidence | Mitigation / test |
|---|---|---|---|---|---|
| R-01 | **Cross-machine non-determinism** (different CPUs/GPUs/OS) breaks lockstep | M | Kill | E1 passed on one PC only; GS renderer change was harmless (E2b); recompiler code paths may depend on host CPU features | E6 on two different PCs before M4; locked settings profile; per-frame-window state hashing; resync |
| R-02 | Engine extension to 4 players is larger than estimated (2-sized arrays across camera, viewport, HUD, audio, GameMgr; ~200+ code sites; scripts with `player2` everywhere) | H | High | F-0060, F-0061, F-0062 (crash with player 3) | M2 starts with a systematic accessor inventory; relocate arrays to new storage; incremental tests per subsystem |
| R-03 | Rendering 4 viewports exceeds the emulated PS2's frame budget (game slows to <30 fps in emulated time) | M | High | Not measured | Measure in M3; EE cycle-rate overclock (identical on all peers); reduce effects/LOD for extra views |
| R-04 | Camera/presentation feeds simulation (animation LOD, effects RNG) | H (confirmed for camera) | High | E2: camera-only change diverged; shared RNG F-0058 | Simulate all players' cameras identically everywhere; render all views identically; crop only in the emulator (E2c test in M1) |
| R-05 | Emulator-level lockstep needs a PCSX2 modification and a working build (RESOLVED in M1: build works, F-0087) | L | High | E3 (in-game waiting not deterministic); Build Tools 2026 already installed (F-0075; corrects the Stage 1 claim of no compiler); MSVC build of PCSX2 not yet proven | Build unmodified PCSX2 first (M1 step 1); fallback: hotkey-driven pause/frame-advance prototype (fragile) |
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
| R-18 | The 2x2 layout patch also changes local 2-player play if active outside online sessions | H | Medium | M1 layout patch is unconditional in the pnach | Apply only during W4P sessions (fork-controlled) in M3 |
| R-19 | One quarter of the frame shown full screen looks soft at native resolution | H | Low | M1 screenshots (native resolution) | GS upscaling; measure cost in M3 |
| R-20 | Local player's controller vibration not routed (game vibrates the emulated port of that player) | H | Low | M1 design | Route vibration of the local player's port to the local device (M3/M5) |
| R-21 | The M1 pnach crashes stock PCSX2 (unknown SYSCALL) if a user applies it without our build | M | Medium | hook design | Our build applies the patch itself; never ship the pnach separately (M8) |
| R-19 update | Mitigated: 8x upscale measured at about 4 % GPU per instance with High blending (F-0102); user's view sharp in screenshots | - | Low | F-0102 | settings profile 8x on the user's PC |
| R-20 update | Mitigated in code: only the local player's rumble reaches the local controller (fork patch 0006); not yet tested with a real controller | M | Low | patch 0006 | test with the user's controller |
| R-22 | 60 fps patch: code that counts game ticks instead of time may run at double speed; the LogicDt patch is applied every frame and may undo slow-motion moments; the startup-only variant is untested from boot | H | Medium | F-0100; sixty_fps.md R60-5/6 | human feel test; tick audit; boot-based 60 fps test (menu script for 60 fps not yet working) |
| R-23 | HUD in the player's own view: health/rage panel twice too large; players 3-4 have no HUD yet (interim guards) | H | Medium | F-0103, F-0111 | HUD per-view work (m2_hud_scripts.md, m2_hud_players34.md (B)) |
| R-24 | Pause (Esc) on one PC stalls the other PCs ("Waiting for Player N") instead of the agreed pause policy | H | Low | design | session policies milestone |
| R-25 | 2-PC package works only on the same home network (no NAT traversal yet) | H | Medium | D5 | connection layer (M5) |
| R-26 | Players 3-4 need companions to take over; Mission 1's squad has none and the game's own picker finds none (F-0109); per-mission companion handling (D7) required | H | High | F-0109 | M2/M6: spawn or assign companions per mission |
| R-27 | Players 3-4 created in Mission 1 do not move with their (correctly delivered) input (m2m) | H | High | local/m2/m2m/track.csv | m2_player_control.md (in progress) |
| R-28 | Extra Warrior model for an added player does not fit the model pool in some level (Mission 13: 0.97 MB free after loading Swan); then player 4 falls back to a copy of player 1 | M | Low | F-0154, m2_extra_model.md | survey (`tests/m2/extra_survey.py`) per mission in M6; FITCHK fallback |
| R-29 | Players 3-4's inventory slots are not cleared when they are released at a level end; money/items may carry over or be banked twice | M | Medium | F-0158 | check the release path in M6; test the real mission-summary flow |
| R-30 | Revive is refused when a teammate stands between reviver and downed player (game's own sight sweep FUN_0021C0A8); four players block each other more often | H | Low | F-0157 | user question Q1 (M2 report): keep the rule or let teammates not block |
| R-31 | 30 fps mode dips to 27.4-28.7 fps in heavy 4-view scenes (emulated-console bound) | M | Low | F-0146, F-0147, F-0161 | test EE cycle rate 180 % in 30 fps mode for 4-player sessions |

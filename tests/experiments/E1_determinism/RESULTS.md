# E1 / E2 / E3 results — 2026-10-10

Environment for every run: SINGLE-PC (this PC: Ryzen 9 9950X3D, RTX 5090, Windows 11), two sandbox PCSX2 v2.9.115
instances (`inst2`, `inst3`) running at the same time, sandbox "default" profile (the user's emulation settings,
including MTVU = on, EE recompiler, Vulkan renderer, native resolution), same BIOS (SCPH-90001 v2.30), identical
memory-card images, fixed RTC. Input: scripted bot via the experiment patch (no human). No network, no impairment.
Comparison: full 32 MiB EE RAM dumped through PINE while both instances are held at the same game frame by the
experiment barrier. Summaries: `evidence/E1/<tag>.json` (dumps stay in `local/e1/`).

Bytes that differ in every run, including identical-input runs, and are explained by host timing (the instances are
held at the barrier for different wall-clock times while being dumped one after the other):
- 0x005DE418 / 0x005DE498 / 0x005DE918 / 0x005DE998: frame counters inside the two libpad port DMA buffers
  (difference ≈ number of vsyncs elapsed while the other instance was being dumped).
- 0x00519EA0: overflow counter of EE timer 2 used by the libkernel alarm system (decompile 0x00443D98).
- Occasionally a few bytes in 0x00001000–0x0001A800 and 0x00081E40–0x00081FA0 (EE kernel area: thread/context data).
None of these is game state.

## E1 — same-machine determinism
| Tag | Start state | Input | Frames compared | Differing bytes | Verdict |
|---|---|---|---|---|---|
| p0_n300 / n900 / n1800 | Mission 2 start (tutorial prompt, mostly idle scene) | none | +300 / +900 / +1800 | 5 / 11 / 9 | timing counters only, but scene was mostly static: weak test |
| p0v2_n300 / n900 / n1800 | Quick Rumble "War Party" 5v5 | identical scripted brawl input, pad 0 | +300 / +900 / +1800 | 113 / 9 / 5 | **PASS**: only timing counters and kernel-area bytes |
| neg_stick150_n450 (positive control) | same | B's left stick forced right for 60 frames from frame 150 | +450 | 601,672 | divergence detected: the comparison is sensitive |
| neg_perturb100 / neg_stick100 / neg_stick10 | same | 1-frame or 30-frame differences | +600/+300 | 11–77 | no divergence: those inputs fell into frames where the game ignores input (match intro, frame already held); only the injected table bytes differed |

**E1 verdict (SINGLE-PC): PASS.** Two instances with identical settings, start state and frame-exact input stayed
identical in all game state for 60 s of AI-vs-AI combat with MTVU on. Cross-machine determinism (E6) is untested.

## E2 — presentation isolation
| Tag | Difference between A and B | Differing bytes | Verdict |
|---|---|---|---|
| e2_camspin_n600 | B also holds the right stick (camera), script includes walking | 602,804 | confounded (walking is camera-relative) |
| e2_nomove_ctrl_n600 | none (attack buttons only, no walking) | 10 | control: deterministic |
| e2_nomove_camspin_n600 | B rotates the camera; attack buttons only | 568,809 | **FAILED TEST**: the camera feeds the simulation |
| e2_camspin_n60 / n120 | same, early | 426,666 / 419,747 | at +60 frames positions still equal; animation pose data (+0x4E0…+0x584), look-at/target vectors (+0x284…+0x2A0) and distance-like floats (+0x50, +0x334) in most human objects already differ; most bytes are in one ~1 MB heap block (render/animation buffers) |
| e2b_swrender_n600 | B uses PCSX2's software renderer (presented via D3D12), A uses Vulkan hardware rendering | 16 | **PASS**: emulator-side rendering does not feed the simulation |

**E2 verdict:** game-side camera state is NOT presentation-only; changing one instance's camera changes animation
updates and later the whole simulation. Emulator-side rendering (renderer type) is presentation-only.
Consequence: every player's camera must be simulated identically on every instance (camera inputs travel with the
lockstep inputs); an instance may only choose which already-simulated camera view it displays. Whether the choice of
displayed viewport (layout/size) feeds the simulation is still a HYPOTHESIS (test planned: E2c, Stage 2 M1).

## E3 — deterministic input injection
| Tag | What differs | Differing bytes | Verdict |
|---|---|---|---|
| (E1 v2 runs) | game-side injection of pad input at an exact game frame | see E1 | **PASS**: identical frame-exact input in both instances |
| e3b_realtime_n300 | 20 in-game waits; B waits 150 ms longer each time; default real-time game clock | 501,984 | H-E3b-1 confirmed: waiting inside the game breaks determinism |
| e3b_fixed_n300 | same, game clock forced to its fixed-step mode (GameClock+0x54 = 1) | 97,147 (player positions differ) | **FAILED TEST** for H-E3b-2: other emulated-time dependencies remain |
| e3c_vmpause_n300 | B's whole VM paused 12 × 150 ms via PCSX2's pause hotkey | 9 | **PASS**: whole-VM pauses are deterministic |

PINE write round trip on loopback (release writes): median 0.089–0.092 ms, max 0.19–0.23 ms.

**E3 verdict:** inputs can be applied at an exact emulated point for any pad index by a game-side hook. Waiting for
network input must happen with the whole emulated machine stopped, not inside the game. The installed PCSX2 can
only do that through its pause/frame-advance hotkeys (driven by window messages, fragile, vsync granularity); a
small PCSX2 modification that blocks at a frame boundary until inputs are present is the robust route.

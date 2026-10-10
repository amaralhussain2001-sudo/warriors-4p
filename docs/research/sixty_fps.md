# Real 60 fps: static analysis (decision D9), 2026-10-11

Build: The Warriors USA v1.03, SLUS_212.15 (static addresses). Function names are OUR labels (the ELF is stripped).
Method: static analysis only (`local/analysis` decompile, `callers.pkl`, raw ELF words). No runtime tests in this note.
Runtime facts it explains: `evidence/M3/f0..f5*.json` (60 rendered frames per second with PCSX2's flag, but characters
change position about 30 times per second and the pad is read about 30 times per second).

## 1. What 0x00596D70 controls: the display swap interval

| Claim | Label | Evidence |
|---|---|---|
| The game uses `gp = 0x0059E6F0`; 0x00596D70 is accessed as `gp-0x7980` (which is why a grep for `DAT_00596d70` misses the reader) | VERIFIED | `sb a0,-0x7980(gp)` at 0x0048DF9C (setter `FUN_0048df98`) |
| Readers/writers: read only at 0x0048BDE4 in `FUN_0048bdb0`; written at 0x0048DF9C (setter) and 0x0048E204 (reset to 0 in `FUN_0048e1c8`) | VERIFIED | scan of all gp-relative loads/stores |
| `FUN_0048bdb0` (our label `VblankFlipHandler`) is the vblank-interrupt handler that flips the display buffer (writes `GS DISPFB1/DISPLAY1`, kicks GIF DMA). If a flip is pending, it flips only when the vblank counter (byte 0x005970F9) has reached the byte at 0x00596D70; otherwise it increments the counter and returns | VERIFIED | decompile `FUN_0048bdb0` |
| 0x00596D70 = **swap interval** (minimum vblanks between flips). The game sets it once from the static byte **0x0050CDB0 = 2** (`lbu` at 0x00194AEC, then `FUN_0048df98(DAT_0050cdb0)` in `FUN_00194558`) → at most 30 flips per second | VERIFIED | ELF word 0x0050CDB0 = 0x00000002; decompile `FUN_00194558` |
| PCSX2's disabled "60 FPS" entry writes 1 there, so the game may flip every vblank; the render loop then runs at up to 60 per second (matches f1-f3) | VERIFIED (code) + measured | above + `evidence/M3/f3_fps60_ee2.json` |

## 2. Main loop: why characters and the pad stay at 30 Hz

| Claim | Label | Evidence |
|---|---|---|
| The in-game mode update `FUN_00158728` (once per rendered frame) calls `FUN_003a3148(DAT_00512c7c, 0)` → `FUN_003a2ea0` (our label `SimAdvance`), then `FrameStats` and the render/world update `FUN_00156658(frame dt)` | VERIFIED | decompile `FUN_00158728` |
| `SimAdvance` is a **fixed-step accumulator**: elapsed GameClock cycles since the last step (`GameClock` vtable +0x44); step = **0x4B0000 cycles = 1/60 s** (294.912 MHz; the code's 3.390842e-9 = 1/294,912,000); it runs only while elapsed > **0x0095FFFF (two steps)** and then always runs **exactly 2 steps** (`sltiu v0,s2,2`) | VERIFIED | disassembly 0x003A2F08-0x003A2FA4 |
| Each step calls `FUN_003a1580` (set step time), `FUN_00249108` (our label `SimStep`), `FUN_003a3588` (a 256-slot per-step event wheel) and `FUN_00340918` (per-step blend/fade of up to 64 objects) | VERIFIED | same |
| `SimStep` increments the counter 0x005104F4 and runs the **whole game-logic body only when the counter is even** (`andi a0,v1,1; bne a0,zero,exit` at 0x0024912C/0x00249148). So game logic runs once per two 1/60 steps = **30 Hz** | VERIFIED | disassembly 0x00249108-0x0024914C |
| The logic body contains the pad update for all 8 pads (`FUN_001454a8` → `FUN_00144fb0` → `FUN_001498a8` → libpad read 0x00149770, our hook site 0x001498E0), the character/AI loops over 0x3C objects, and at the end `FUN_0011e878(max(LogicDt, 1/30))`, which calls each view camera's update (vtable +0x134) with that dt | VERIFIED | decompile `FUN_00249108`, `FUN_0011e878` |
| Hence at 60 rendered fps: on every other frame `SimAdvance` has ≥ 2 steps of time and runs one logic tick; on the other frames it does nothing → characters, pad reads (30/s) and probably cameras update at 30 Hz, and every second rendered frame repeats the previous state. This is why PCSX2's entry says "doesn't achieve real 60 FPS" | VERIFIED (logic) / HYPOTHESIS (cameras: no runtime check) | above; matches f4 (position changed in 168 of 361 frame pairs at 60 fps vs 153 of 181 at 30 fps) |
| `FUN_00144fb0` also skips the hardware pad read if the previous read was < 6 ms ago (GameClock-timer ms, vtable +0x34 = cycles / 0x48000) and duplicates the previous button state. This guard is not the 30 Hz cause | VERIFIED | decompile `FUN_00144fb0`, `FUN_004dcdd8` |
| Logic time step: **0x005102CC (our label `LogicDt`) = 1/30 s × time scale** (static init 0x3D088889 = 1/30). Writers: `FUN_0023b778` (slow motion: 1/30 or scale×1/30), `FUN_0030c8c8` (1/60), `FUN_0030c8f8` (1/120, back to 1/30), `FUN_0041ab30` (scale×1/30), `FUN_0041ab60` (1/30). About 36 read sites use it (gravity `-dt*15.68`, speeds `dt*24`, etc.); one checks `LogicDt*29.999998 != 1.0` to detect slow motion (decompile all_02.c line 59499) | VERIFIED | decompile; ELF word 0x005102CC |
| 33 functions load 1/30 as an immediate (0x3D088889). Some are per-tick hard-coded dt (e.g., `FUN_00170c88`, called at the start of the logic body, uses 0.033333335 and `FUN_004dac90(1/30, …)`); others convert 30-fps-authored data (frames → seconds, e.g., `FUN_00355ab8`) and must not change | VERIFIED (list) / HYPOTHESIS (classification of the rest) | ELF scan for `lui 0x3D08; ori 0x8889` |
| Per-tick (not time-based) logic exists: Lua config `CfgButtonHeldFrames`, decrement-per-tick counters in the logic body (e.g., `- 10` per tick on a byte at +0x2B); the per-frame mode update `FUN_00158728` counts a byte at +0x28 down once per rendered frame (0xB4 = 6 s at 30 fps), so with the swap-interval flag alone that countdown already runs 2x fast | VERIFIED (code sites) / HYPOTHESIS (visible effect) | `lua_bindings.tsv`; decompile |
| GameClock-based timers (`DAT_0050b734+0x48` ms, Lua `ScheduleFunc`, F-0048) and the per-step event wheel / fades are tick-rate independent | VERIFIED (code) | F-0047, F-0048; `FUN_003a3588`, `FUN_00340918` |

## 3. Candidate patches for a real 60 Hz simulation (none tested)

The engine already steps time in 1/60 s units; only the logic body is gated to every other step and tuned for
dt = 1/30. A real 60 therefore needs: flip every vblank, one step per frame, logic every step, and every 1/30 tick
assumption halved.

| ID | Change | Address: original → new | Confidence |
|---|---|---|---|
| R60-1 | Swap interval 1 | runtime byte 0x00596D70 := 01 every vsync (PCSX2's entry); for boot-time use also static byte 0x0050CDB0: 02 → 01 | HIGH (measured) |
| R60-2 | `SimAdvance` single steps (threshold 1 step, 1 step per iteration) | 0x003A2F08: 3C020095 → 3C02004A; 0x003A2F30: 3C170095 → 3C17004A; 0x003A2F94: 2E420002 → 2E420001 | HIGH that it does this; behaviour at 30 fps unchanged in total steps |
| R60-3 | Logic every step | 0x0024912C: 30640001 (`andi a0,v1,1`) → 30640000 | HIGH that it does this |
| R60-4 | Halve `LogicDt` everywhere (float exponent −1: 0x3D08→0x3C88, 0x3C88→0x3C08, 0x3C08→0x3B88) | static 0x005102CC: 3D088889 → 3C888889; `lui at` at 0x0023B7C8 and 0x0023B7FC (3C013D08 → 3C013C88); 0x0030C8CC (3C013C88 → 3C013C08); 0x0030C924 (3C013C08 → 3C013B88); 0x0030C94C (3C013D08 → 3C013C88); 0x0041AB40 and 0x0041ABA4 (3C013D08 → 3C013C88); camera clamp in `SimStep` 0x00249B44 (3C013D08 → 3C013C88); plus the 29.999998 constant in the slow-motion check inside `FUN_002325e0` (instruction address still to locate) → 59.999996. Alternative with fewer edits: a code cave around `SimStep` that halves `LogicDt` on entry and restores it on exit unless a writer changed it | MEDIUM |
| R60-5 | Hard-coded per-tick dt in logic functions | audit the 33 functions that load 1/30; change only the per-tick ones (e.g., `FUN_00170c88`) | LOW-MEDIUM (audit needed) |
| R60-6 | Tick-count logic | double tick thresholds (e.g., `CfgButtonHeldFrames` via Lua config; per-tick decrements), or run selected subsystems only on even ticks | LOW (unknown size) |
| R60-7 | Emulated CPU headroom | logic cost per second doubles; EE cycle rate 180 % was enough for 60 fps with 30 Hz logic (f3); 60 Hz logic may need 300 % | HYPOTHESIS |

R60-1+2+3 without R60-4..6 would make the game run its logic twice as fast in game terms (wrong speed). R60-1 alone
(PCSX2's entry) keeps game speed correct but gives repeated frames.

Lockstep impact: pad reads become 60 per second (one per logic tick), so the W4P poll rate doubles; input delay
2 polls = 33 ms. Determinism is unaffected as long as every player uses the same patch set (HYPOTHESIS until tested).

## 4. Test plan (for the runtime work, SINGLE-PC, bots)
1. R60-1+2+3+4: character position changes on ~100 % of moving frame pairs; pad hook polls ≈ 60/s.
2. Speed parity against 30 Hz: walking distance per second, a punch/combo animation duration, grab duration, enemy
   attack timing, mission timers (game-time), slow-motion moments; all within a few percent.
3. Camera smoothness (frame captures, `tools/framecap.ps1`), camera speed parity.
4. Hash sync between two instances; EE cycle rate needed for steady 60 with 2 and 4 views.
5. Then R60-5/6 audit guided by the differences found in step 2.

## Summary
The 30 fps cap is the swap interval (0x00596D70, default 2 from 0x0050CDB0). The simulation already steps in
1/60 s units, but `SimAdvance` (0x003A2EA0) runs steps in pairs and `SimStep` (0x00249108) runs the game logic
(pads, characters, AI, cameras) only on even steps, with `LogicDt` (0x005102CC) = 1/30. A real 60 needs
R60-1..4 (concrete words above) plus an audit of hard-coded 1/30 and per-tick counters (R60-5/6). Overall
confidence that a correct-speed real 60 is reachable: MEDIUM; effort dominated by the audit and speed-parity tests.

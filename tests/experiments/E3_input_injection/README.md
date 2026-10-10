# E3 — Deterministic input injection (Stage 1 experiment)

**Question (BRIEF §6.2 E3):** can every instance receive the inputs for all player slots at exactly the same emulated
point, and is the installed PCSX2 enough or does it need modifying?

## E3a — game-side injection at an exact game frame
Patch v2 (`tests/experiments/E1_determinism/e1_v2.pnach`) overrides the per-pad buffer right after the game's libpad
read (call at 0x001498E0), using a table indexed by the game's own frame counter (0x0050C654). This applies the same
input on the same game frame in every instance, independent of host timing. Evidence: E1 v2 runs (identical results
at +300/+900/+1800 frames) and the positive control (a 60-frame input difference diverged).

## E3b — waiting inside the game (lockstep without modifying PCSX2)
A network lockstep needs each instance to wait until every player's input for frame F has arrived. Without changing
PCSX2 the only place to wait is inside the game (the barrier cave spins until released). While the game thread
spins, emulated time continues (vsync interrupts, timers, IOP). The game clock runs in real-time mode during play
(F-0047), so different wait durations change the game's frame time.

**Hypotheses (declared before running):**
- H-E3b-1: with the default real-time clock, two instances that wait different amounts of time at the same frames
  diverge in gameplay state.
- H-E3b-2: forcing the game clock's own fixed-step mode (GameClock+0x54 = 1, 1/30 s per frame; F-0048) removes that
  divergence, unless other time-dependent systems (streaming, audio, timers) leak into gameplay.

**Method:** two instances from the Rumble start state, identical scripted input. A barrier every K = 15 frames for
N frames. Instance A is released immediately; instance B is released after D ms (D = 150). Compare full EE RAM at N.
Run once with the default clock and once with the fixed-step flag written through PINE right after load (the clock
object is on the heap; its pointer is static at 0x0050B734).

**Pass/fail:** H-E3b-1 confirmed if gameplay structures (human objects) differ; H-E3b-2 PASS if only the known
timing counters differ (as in E1), FAIL otherwise.

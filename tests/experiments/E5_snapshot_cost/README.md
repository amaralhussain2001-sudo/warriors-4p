# E5 — State snapshot cost (Stage 1 experiment)

**Hypothesis (declared before running):** a full PCSX2 savestate of The Warriors in gameplay is tens of MB
uncompressed and takes on the order of 100 ms or more to save or load, which would make per-frame rollback
infeasible but leaves an occasional authoritative resync (seconds-scale) viable.

**Method:** sandbox instance `inst1` (PCSX2 v2.9.115, default sandbox profile), level95 hub, gameplay running.
Trigger `SaveState` / `LoadState` through PINE (`tools/pine.py`) N times; measure
(a) wall time from request until the .p2s file stops changing, (b) .p2s size, (c) uncompressed size per zip member,
(d) emulator-reported timings from emulog if present. Transfer time is computed for 1, 10 and 50 Mbit/s uplinks.

**Pass/fail criteria:**
- "Rollback viable" requires save+load < 2 ms each (to fit several per 33 ms frame) — expected FAIL.
- "Resync viable" requires compressed state transfer + load < 10 s at 10 Mbit/s — expected PASS.

Script: `e5_measure.py`. Results: `RESULTS.md`, raw log `evidence/E5/`.

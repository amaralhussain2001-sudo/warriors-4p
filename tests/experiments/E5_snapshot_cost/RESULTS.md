# E5 results — 2026-10-10

Environment: SINGLE-PC, sandbox `inst1`, PCSX2 v2.9.115, sandbox default profile (user's settings incl. MTVU on,
native resolution, Vulkan), level95 hub in gameplay, no human input, no impairment. Raw: `evidence/E5/e5_run1.json`,
emulator log lines quoted below from `local/pcsx2/inst1/PCSX2/logs/emulog.txt`.

| Measure | Result |
|---|---|
| Uncompressed state | 50,649,438 bytes (EE RAM 32 MiB, "Internal Structures" 8.07 MB, GS 4.19 MB, SPU2 2.18 MB, IOP RAM 2 MiB, rest small) |
| Compressed `.p2s` (zstd, default) | 14.33–15.97 MB over 5 runs (includes a 361 KB screenshot) |
| Save (snapshot + compress + write) | emulog "Zipping save state … took 220.54 ms" / "277.47 ms"; wall time until file stable 0.23–0.30 s |
| Load | ≈ 57 ms from load start to "Loaded state" (emulog 1199.0562 → 1199.1135); PINE acknowledges immediately (0.3–0.5 ms) because the request is queued |
| Transfer of 15 MB | 1 Mbit/s ≈ 120 s; 10 Mbit/s ≈ 12 s; 50 Mbit/s ≈ 2.4 s (computed, not measured) |

Emulator warning on every save/load: "MTVU speedhack is enabled, saved states may not be stable".

## Verdict against the pre-declared criteria
- **Rollback viable (save+load < 2 ms): FAILED TEST.** A save takes ~220–280 ms and a load ~57 ms, two orders of
  magnitude too slow for per-frame rollback through PCSX2 savestates.
- **Resync viable (< 10 s at 10 Mbit/s incl. load): FAILED TEST** with stock compressed savestates (~12 s transfer + load).
  HYPOTHESIS: resync passes with a smarter payload: send only EE/IOP RAM and register blocks that differ from a state
  every instance already holds (mission-start state), or a host-generated delta; to be measured in Stage 2 M4.
- Occasional full-state resync at session start/checkpoint over a fast link (≥ 50 Mbit/s ≈ 2.4 s) is practical.

# Project state

**Stage:** 2 (approved 2026-10-10 with all recommended options; `docs/DECISIONS.md`).
**Milestone:** M1 complete — all 7 exit criteria met on SINGLE-PC with bots (`docs/reports/M1_report.md`).
**Stopped after M1 as agreed (decision D1). Waiting for the user before continuing.**

## Done
- Stage 1 (tag `stage1-plan`).
- M1: PCSX2 fork built from source (`emulator/`, patches 0001-0003 on v2.9.115); W4P lockstep module; game patch
  `mod/w4p_m1.pnach`; tests `tests/m1/`; evidence `evidence/M1/`. Tag `m1`.

## Next steps (when the user says to continue)
1. E6 cross-PC determinism with a second PC (kill test; needs the user's help, see M1 report).
2. M2 four genuine players in one mission (exit criteria to be written before starting).
3. M3 views/merge rule/sharpness/vibration/conditional layout patch.

## Questions waiting for the user
- Optional: human trial of M1 on this PC and feedback on control delay (instructions in the M1 report).
- When can a second PC (different CPU/GPU, own game copy + BIOS) be available for E6?

## Notes for the next session
- Never launch the original PCSX2; the user's own PCSX2 may be running (pid 38060 seen all day).
- Our PCSX2 build: `emulator/pcsx2/bin/pcsx2-qtx64.exe`; `tools/sandbox.py` uses it when `W4P_PCSX2_EXE` is set;
  `tests/m1/*.py` use it directly.
- Sandbox windows may start with the Arabic keyboard layout; `tools/winkeys.ps1` switches the sandbox window to en-US.
- Experiment patches in `tests/experiments/*/` are not part of the mod; `mod/` is.

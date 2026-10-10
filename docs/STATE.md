# Project state

**Stage:** 2 — approved by the user on 2026-10-10 (all recommended options; see `docs/DECISIONS.md`).
**Milestone:** M1 (critical proof of concept), exit criteria in `docs/plan/M1.md`. **Stop and report after M1.**

## Done
- Stage 1: investigation, experiments E1-E5, plan (`docs/plan/STAGE1_PLAN.md`), tag `stage1-plan`.
- Approval recorded; toolchain correction recorded (F-0075: Build Tools 2026 already installed).

## In progress (M1)
1. Get PCSX2 v2.9.115 source and dependencies; build unmodified with MSVC; check it runs the game.
2. W4P module in the fork (lockstep, gate, input ring, hashing, crop, OSD).
3. Game patch with ring-indexed input injection.
4. Two-instance tests against the M1 exit criteria.

## Questions waiting for the user
None.

## Notes for the next session
- Never launch the original PCSX2; the user's own PCSX2 may be running.
- Sandbox windows may start with the Arabic keyboard layout; `tools/winkeys.ps1` switches the sandbox window to en-US.
- Experiment patches in `tests/experiments/*/` are not part of the mod.

# Project state

**Stage:** 1 complete — plan delivered (`docs/plan/STAGE1_PLAN.md`). **Waiting for the user's explicit approval.**
Stage 2 must not start until a message explicitly approves the plan (e.g. "Approved, proceed with Stage 2").

## Done (Stage 1)
- Project skeleton, Git, brief copy, CLAUDE.md, hashes of originals (re-verified at the end of Stage 1).
- Disc extraction to `local/disc`; WAD index; Lua 4.0 disassembler and pseudo-Lua renderer; Ghidra project with the
  R5900 extension; full decompile (local only); Lua binding map.
- Runtime tooling: sandbox PCSX2 instances, PINE client, background key input, screenshots, experiment patches
  (frame barrier, frame-exact input injection, call facility), RAM diff tools.
- Experiments: E1 (PASS, SINGLE-PC), E2 (camera feeds sim; renderer does not), E3 (in-game wait fails; VM pause
  passes), E4 (naive 3rd player crashes; what breaks recorded), E5 (savestate cost). E6 designed (needs another PC).
  E7 (optional transport smoke test) not run.
- Research notes: PCSX2 capabilities, existing online methods, transport options, static analysis.
- Mission inventory with classification (MISSIONS.md).

## In progress
Nothing. Sandbox instances are stopped.

## Next steps (only after approval)
M1 proof of concept as defined in the plan §9, after decisions D2 (toolchain) and D6 (testers) are made.

## Questions waiting for the user
D1-D7 in `docs/plan/STAGE1_PLAN.md` §15.

## Notes for the next session
- Never launch the original PCSX2; the user's own PCSX2 was running during Stage 1 and was not touched.
- Sandbox windows may start with the Arabic keyboard layout; `tools/winkeys.ps1` switches the sandbox window to en-US.
- Experiment patches live in `tests/experiments/*/` and are NOT part of the mod.

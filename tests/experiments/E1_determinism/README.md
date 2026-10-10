# E1 — Same-machine determinism (Stage 1 kill test)

**Question:** do two PCSX2 instances on this PC, with identical settings, identical starting state and identical
input, stay identical through gameplay that includes AI combat? If they diverge quickly and no settings profile
fixes it, deterministic lockstep (the cheapest architecture) is dead.

## Hypothesis (declared before running)
H1: With MTVU (multi-threaded VU1) OFF and otherwise identical settings, two instances started from the same
savestate and given identical (here: no) controller input produce identical EE RAM game state at the same game
frame, apart from a small set of addresses tied to host timing (e.g. timers, audio/stream buffers), for at least
1,800 game frames (60 s) of AI-vs-AI combat.
H2: With the user's settings (MTVU ON) the result may differ; this is measured, not assumed.

## Method
- Test bed: Quick Rumble (non-story arena brawl, AI gangs fighting) because it reaches AI combat without
  scripted navigation. Story-mission confirmation is a follow-up (E1b).
- Instances: `tools/sandbox.py make <n>`; both use the sandbox copy of PCSX2 v2.9.115, the same BIOS, the same
  memory-card images (copied), the same fixed RTC (`ManuallySetRealTimeClock`), PINE on distinct slots.
- Frame barrier: a temporary pnach (`e1_barrier.pnach`, place 2) adds a code cave at 0x000F0000 and redirects
  the in-game tick's call to the frame-statistics function (our label `FrameStats` @ 0x001569C0, called at
  0x00158CD0) through the cave. The cave increments nothing itself; after `FrameStats` bumps the game frame
  counter at 0x0050C654 it compares it with a target in a mailbox (0x000F0100). When equal it writes the frame to
  0x000F0104 and spins until 0x000F0108 is set. While spinning, the EE game thread does no game work, so a RAM dump
  taken then is frame-aligned. The cave was placed in RAM observed to be all-zero during gameplay (F-0050).
- Run: boot both instances from the same savestate (`-statefile`), set target = start frame + N via PINE in both,
  wait until both report, dump 32 MiB EE RAM from both via PINE, diff, classify differing ranges.
- Settings profiles: P0 = user's settings (MTVU on); P1 = MTVU off ("det" profile in `tools/sandbox.py`).
- Environment label: SINGLE-PC, scripted bot (no input), no impairment.

## Pass / fail criteria (declared before running)
- PASS: at N = 300, 900 and 1,800 frames, all differing bytes lie in ranges explained as host-timing or
  presentation-only (documented with evidence), and no gameplay structure differs (player/human objects, GameMgr,
  GameClock game time, AI/gang data).
- FAIL: any gameplay structure differs (e.g. human positions/health), or the differing set grows without bound.
- If P0 fails and P1 passes, the deterministic profile becomes a requirement.

Results: `RESULTS.md`; raw dumps under `local/` (copyrighted RAM contents are not committed); diff summaries under
`evidence/E1/`.

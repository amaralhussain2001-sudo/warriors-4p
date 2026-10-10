# E6 — Cross-machine determinism (design; needs the user's help)

**Question:** do two instances on DIFFERENT computers (different CPU vendor and GPU) given the same start state and
the same frame-exact input stay identical, as they did on one PC (E1)?

**Hypothesis (to declare before running):** with the locked settings profile, game state matches at +300, +900 and
+1,800 frames apart from the known timing counters (E1 list). Risk: host-CPU-dependent recompiler code paths.

## What is needed
- A second Windows PC, ideally with a different CPU vendor (Intel) and GPU vendor (AMD or Intel), on the same LAN
  or reachable over the internet.
- On that PC: the person's OWN legally obtained copy of The Warriors (USA) whose ISO SHA-256 matches
  `e79a4cea561c78ee33a3b310421bf3dd2174928ebd278efcf23f7f080b8ae96e`, and their OWN PS2 BIOS dump. Nothing
  copyrighted is sent from this PC.
- A test package built from this repository (scripts, experiment patch, settings profile, the PCSX2 v2.9.115
  build the person downloads from the official PCSX2 site, and the start savestate). Note: a savestate contains
  game RAM; sending it to another person's PC needs the user's approval (it is game-derived data). Alternative
  without a savestate: both PCs boot the game and reach the same point with a scripted input sequence from power-on.

## Steps (to be finalised before running)
1. Both PCs: verify ISO and BIOS hashes; install the sandbox profile; enable PINE.
2. Both PCs: start from the same state (savestate or scripted boot), arm the same input script, barrier at N.
3. Both PCs: dump EE RAM at the barrier, compute per-region SHA-256 and the diff list; exchange only the hash list
   and the list of differing addresses (no RAM contents leave either PC).
4. Repeat for N = 300, 900, 1,800 and for profiles P0 (user settings) and P1 (MTVU off).

**Pass:** only E1-known timing addresses differ. **Fail:** any gameplay structure differs; then bisect settings.

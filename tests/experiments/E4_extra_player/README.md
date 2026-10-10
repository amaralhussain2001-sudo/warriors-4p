# E4 — Extra player feasibility (Stage 1 "what breaks" experiment)

**Question (BRIEF §6.2 E4):** in a representative mission, using temporary experiments only, can the engine run a
third (and fourth) genuine player entity with its own input? Record what breaks.

## Static findings that frame the experiment
- `GameMgr::AddPlayer` (our label, 0x00419B10) refuses when the player count is already 2 (`slti v0,s0,2`).
- GameMgr stores player handles at +0x228/+0x22C; +0x230 is GameMgr's frame tick counter and +0x234…+0x248 a
  sound object, so player 3/4 handles written past the array overwrite live fields.
- Per-player 0x30-byte records at GameMgr+0x5740 (2 slots before other fields at +0x57A0).
- `MakePlayer` (0x00229C40) tries only 2 HUD slots; camera per-viewport arrays have 2 entries (F-0026).
- The pad layer has 8 slots but the update loop polls only pads 0 and 4 (F-0055).

## Hypothesis (declared before running)
With the player limit raised to 4 and all pads polled, calling the engine's own `MakePlayer` on an AI Warriors
companion makes it a third player that moves with pad-1 input, but at least these break: GameMgr tick counter and
sound object corrupted (handle stored at +0x230), no HUD for player 3, camera code indexing a 2-entry array with
index 2. A crash is possible.

## Method
Sandbox `inst4`, patch v3 (both groups), Mission 1 savestate with two players joined (local `e4_start_m1_2p.p2s`).
1. Inject "connected, neutral" on pad 1 so the pad is free and connected.
2. Pick the nearest AI Warriors human (player index −1) from the human pool; resolve its handle via the object table.
3. Call `MakePlayer(human, pad=1, hud=-1, player=2)` through the call facility on the game thread.
4. Read GameMgr/player state, inject 3 s of left-stick input on pad 1, track positions, take screenshots, read the
   emulator log and PINE status for crashes.

Pass/fail is descriptive: record exactly what works and what breaks. Environment: SINGLE-PC, scripted bot input.

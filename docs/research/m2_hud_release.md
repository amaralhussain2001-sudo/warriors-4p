# M2: crash at level end with four players - HUD slot release (R8), 2026-10-11

## 1. Symptom (VERIFIED)
q14 (4 instances, Mission 13, MTVU off, all groups, 2007 s): 0 hash mismatches, but at emulator time 1505.9 s (poll
40656) all four instances logged `TLB Miss, pc=0x1b2300 addr=0x28/0x2c [load]`, then `pc=0x0` misses, and the game
stopped reading the pads (`local/pcsx2/inst6/PCSX2/logs/emulog.txt`; `local/m2/q14_m13_30min_nomtvu/w4p_slot*.log`:
poll counter stuck at 40656; screenshots from t=1533 s show a frozen, dimmed single view and "FPS: N/A").

## 2. Cause (VERIFIED: code + two single-instance reproductions)
`FUN_001B22F0(hud, slot)` (our label: ReleaseHudSlot; callers human cleanup `FUN_0021C7C8` and `FUN_0022A2A8`) reads
`*(hud + 8 + slot*4)` = the 2-entry PlayerHUD table at 0x00600848 and calls that PlayerHUD's vtable +0x28. `[4p hud B1]`
gives players 3-4 HUD slots 2 and 3 (human+0x380) and moved the 4-entry table to T_A = 0x000E0848, but rewrote only
`FUN_001B23D0` / `FUN_001B2400` (show/hide). With slot 2/3 the release reads 0x00600850/54 (other HUD fields, not
PlayerHUD pointers), loads a 0 vtable (`lw v1,0x4120(a1)` -> `lh a0,0x28(v1)` at 0x001B2310 = the TLB miss) and jumps to 0.
`FUN_001B2430` / `FUN_001B2460` (callers `FUN_00221108`) have the same indexing (silent wrong write, no crash).
Reproduced on one instance with the old patch (`local/m2/pnach_prefrag.pnach`):
| Run | Trigger | Result |
|---|---|---|
| invt5 | level reload `MenuLoadLevel(GameMgr+0x124)` = the GAME OVER "Last checkpoint" path, 4 players | TLB miss pc 0x1B2300 at 361.8 s, game stops at poll 9500 (`local/m2/invt5/emulog.txt`) |
| invt7 | mission complete `FUN_0015D420(4)` (Lua HUDLaunchMissionComplete core) | TLB miss pc 0x1B2300 at 348.6 s, game stops at poll 9102 (`local/m2/invt7/emulog_maybe.txt`) |
So with players 3-4 holding HUD slots, every level end (restart, retry, mission complete) crashed.

## 3. Fix R8 (18 words, `[warriors-4p 4p hud B1]`, source `mod/m2/hud_b1.txt`)
The three functions are rewritten in place exactly like B1's `FUN_001B23D0`: `bltz a1` rejects any negative slot (was
`slot == -1`), the table is T_A (`lui a0,0x000E` + `lw ..,0x848(v0)`), everything else unchanged.
| Function | Words | Branch target |
|---|---|---|
| `FUN_001B22F0` | 0x001B22F4-0x001B2308 | 0x001B2320 (epilogue) |
| `FUN_001B2430` | 0x001B2434-0x001B2444, 0x001B2450 | 0x001B2454 |
| `FUN_001B2460` | 0x001B2464-0x001B2474, 0x001B2480 | 0x001B2484 |
Every "was" word matches the ELF and nothing else is touched: `note_patches.py check` -> 2676 addresses, 6 problems
(the known `[4p hud A]`/`[4p hud B1]` alternatives). Disassembled back with a scratch disassembler.

## 4. Test (VERIFIED, SINGLE-PC, one instance, scripted input)
invt5_fix (current pnach incl. R8): the same reload at poll 9500 -> **0 TLB misses**, the level reloads, players 3-4
re-join by Start (player 4 is Swan again, F-0154), 4 views at poll 13704, the game runs on to poll 16617; the
checkpoint inventory of slots 2-3 is restored at level start (F-0157). Mission complete with R8: invt7_fix (see
FINDINGS). Long lockstep with R8: q15.

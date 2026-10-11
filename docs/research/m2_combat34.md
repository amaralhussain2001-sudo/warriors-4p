# M2 research: combat for players 3-4 (criterion 3)

Build: The Warriors SLUS-21215 v1.03 (`local/disc/SLUS_212.15`, read-only). Date: 2026-10-11. Static analysis only
(decompile `local/analysis/all/*.c`, `callers.pkl`, Lua binding table, our disassembly of the ELF); nothing was run.
Function names are OUR labels. Patch originals were checked against the ELF with `tools/note_patches.py`.

Criterion 3 (docs/plan/M2.md): players 3-4 can attack, grab, take damage, be knocked down and recover; enemies target and
hit players 3 and 4.

## Result in one paragraph
Combat itself is player-index-agnostic: health, damage, knock-down, grab and the enemy target search work on any human,
and "is a player" is tested as `human+0x1B0 != -1`. Enemies find targets by scanning **gang member lists**, not the
player list, so players 3-4 are targets as long as they are gang members (joined companions are; the spawned Warrior is
added to player 1's gang by the spawn code). The few places that are still 2-player are one AI target picker (random
of 2), the fall-out-of-world game over, the per-player stats table (writes for HUD slot 2/3 land in the stats
checkpoint copy) and one Lua binding that writes a HUD widget by HUD slot. Four small fixes (21 words) below.
Not part of criterion 3 but important: players 3-4 have **no inventory** (no Flash revive items, no money, no weapons
kept), so a player 3/4 death ends the game sooner than a player 1/2 death.

## 1. Health and state fields (for PINE)
| Field | Where | Type | Evidence | Label |
|---|---|---|---|---|
| Stats block pointer | human+0xD4 | u32 pointer (0 for some objects) | every Hu* core reads `*(human+0xD4)` | VERIFIED |
| Health (current) | stats+0x144 | s16 | HuSetHealth core FUN_00237848, HuGetHealthPercent FUN_00222EF0, damage FUN_00265F70 (`health -= stats+0x118`) | VERIFIED |
| Max health | stats+0x146 | s16 | HuSetMaxHealth core FUN_00237BE0; FUN_00222E60 returns 100 when no stats block | VERIFIED |
| Damage of the current hit | stats+0x118 | s16 | FUN_00265F70 lines `health = health - stats+0x118`, friendly-fire paths zero it | VERIFIED |
| Two more meters | stats+0x148, stats+0x14A | s16 | FUN_00222F48 / FUN_00222FA0 return them as percent of FUN_00223068 / FUN_00223188 | VERIFIED (field) / HYPOTHESIS (meaning) |
| State flags | stats+0x00 | u64 bit set (FUN_002265F0 test, FUN_002265D0 set, FUN_00226620 clear) | below | VERIFIED |
| Rage value | human+0x650 | s32 | HuSetRageFrac core FUN_002369B8 (`+0x650 = frac * max`, +0x648 = time) | VERIFIED |
| Player index / HUD slot | human+0x1B0 (s8, -1 = AI) / human+0x380 (s32) | | F-0023, MakePlayer | VERIFIED |
| Per-human position table | 0x00714B00 + human[+0x92]*0x20 (16 bytes) and +0x10 (second vector) | float | distance helpers (FUN_00419EE0, FUN_0029BF98) | VERIFIED |

State flag bits (stats+0x00):
| Mask | Meaning (binding) | Evidence |
|---|---|---|
| 0x1_0000_0000 | dead (`HuIsDead` -> FUN_00227EB0) | VERIFIED |
| 0xE0000 or 0x2000 | prone / knocked down (`HuIsProne` -> FUN_00223B48, FUN_00223A00) | VERIFIED |
| 0x830 | grabbed (`HuIsGrabbed` -> FUN_002355E0) | VERIFIED |
| 0x20000 | arrested (`HuIsArrested` -> FUN_00223B70) | VERIFIED |
| 0x1_8005_0000 | "not active" set used by `HuIsAlive` (FUN_00227E60) | VERIFIED |
| 0x40000, 0x8000_0000 | further incapacitated states (FUN_00227DD8, FUN_00227E18; game over loop) | VERIFIED (use) / HYPOTHESIS (meaning) |

## 2. How enemies choose targets
- **Perception scan** FUN_0028B358 (brain = 0x006D53F0 + 0x2F0*human[+0x92], brain+0 = its human): loops over all gangs
  (FUN_0016C388(i)), keeps gangs that the brain's gang is hostile to (FUN_00168FE0), then walks each gang's 16 member
  handles (gang+0x48) with distance and validity tests (FUN_0028D358: not dead/arrested/etc.), and stores up to 16
  target handles at **brain+0x164** (16 x u32; searched with FUN_004DE208). No player list, no player index. VERIFIED.
- **Hostility** FUN_00290138 (brain vs brain): gang relation table, plus "both are players" and the cop-style
  "hostile to players" flag (brain+0x2E5) - all tested as `human+0x1B0 != -1`, so any player index works. VERIFIED.
- **Nearest player** FUN_00419EE0 (35 AI callers) loops `i < GameMgr+0x224` over the handle array, which is 4 wide
  with the GameMgr patches. VERIFIED.
- **Player 1 references in AI** (about 30 functions in 0x0028xxxx-0x0032xxxx read GameMgr+0x228 directly): followers,
  look-at, dialogue and scripted behaviours aimed at player 1 (the leader). Player 2 is treated like players 3-4 there in
  the original, so this is parity, not a bug. VERIFIED (sampled 9 functions) / HYPOTHESIS (all 30).
- **2-player-only target picker** FUN_002F0318 (used by the AI task FUN_002F0EC0, a "pick a player to go after"
  behaviour): with 2+ players it picks `random(2)`, so players 3-4 are never chosen; then prefers a nearby one of P1/P2.
  Fix **C1**. VERIFIED.
- Script-directed targeting (`GangEngageEnemy(gang, human)`) is rare (about 15 calls) and names specific characters,
  mostly `player`. Parity. VERIFIED (pseudo-Lua grep).

Consequence: players 3-4 are targeted if they belong to a gang. Fox (joined companion) is in player 1's gang; the
spawned Warrior is added with FUN_00166308(gang, human) (m2_spawn_companion.md). VERIFIED (code) / to confirm at runtime.

## 3. Player-only combat paths
| Path | 2-player limit? | Status for players 3-4 | Label |
|---|---|---|---|
| Damage, friendly fire (FUN_00265F70, FUN_00222A48/A90) | no, `+0x1B0 != -1` tests | works | VERIFIED |
| Combo/hit record (GameMgr 0x5C records, FUN_00264CF8/FUN_00265DD0) | was 2 | relocated to 4 (records.txt) | VERIFIED |
| Per-player block +0x414..+0x42F (command, special state) | was 2 | widened (control.txt) | VERIFIED |
| Rage/slow-motion flags GameMgr+0x220 | was 2 | 4 wide (gamemgr.txt) | VERIFIED |
| Button prompts (grab, finisher, context actions) | per pad bitmask (pad 0-7, FUN_001467A8) | works | VERIFIED |
| **Stats table** 0x006FE490 + HUD slot*0xC0 (FUN_004228A0; called from the damage path via FUN_004ED8C8 when a player hits) | 2 records; records 2-3 at +0x180 are the **checkpoint copy** of 0-1 (FUN_00422C60 copies 0x180 bytes) | slot 2/3 writes corrupt the P1/P2 stats checkpoint copy; slot -1 (HUD group A) writes 0xC0 bytes before the table | VERIFIED; fix **C3** |
| **Lua SpawnCustomCrime** (FUN_0041B7A0) writes HUD widget 0x00618010 + slot*0xAB0 | 2 widgets | slot 2 -> 0x00619570, slot 3 -> inside PlayerHUD 0 (0x0061A020) | VERIFIED; fix **C4** (scripts pass `player` except one generic helper) |
| Fall out of the world -> game over (FUN_0023FEA8, GameMgr+0x150 bit 2) | only P1/P2 compared | a falling player 3/4 does not fail the mission | VERIFIED; fix **C2** (parity) |
| Game over when a player dies (FUN_004197A8) | loops `count` | any player's death ends the game (same rule as P2) | VERIFIED |
| Inventory / items / revives (GameMgr+0x480, 2 x 0x3F4, 17 API functions with `slot < 2`) | 2 | players 3-4 get no items, no Flash revives; reads return 0, writes are ignored (no corruption) | VERIFIED; widening is a separate task |
| Button-tap minigame (FUN_00234318, `count == 2`) | yes | partner prompt not shown with 3-4 players; scripts use player/player2 | VERIFIED (cosmetic) |
| Scripted slow motion reset (FUN_002325E0 clears only P1/P2 +0x3BB) | yes | only `HuSetSlowMo` sets +0x3BB; scripts name player/player2 | VERIFIED / low risk |
| Radar "hostile" icon (FUN_00300678, FUN_00304608 -> FUN_001B32E0, radars 1-2 only) | yes | enemies after players 3-4 are not marked on any radar | VERIFIED (cosmetic) |
| End-of-mission stats sum (FUN_00423098) | P1 + P2 | players 3-4 not counted | VERIFIED (cosmetic) |

## 4. Fixes (21 words; `note_patches.py check` with the current pnach: 1,705 addresses, 0 problems)
```
// C1 FUN_002F0318: random target player over the whole player count (was random of 2)
patch=2,EE,002F034C,word,84850224 // was 84820224 lh v0,0x224(a0) -> lh a1,0x224(a0)
patch=2,EE,002F0350,word,28A20002 // was 28420002 slti v0,v0,2 -> slti v0,a1,2
patch=2,EE,002F036C,word,00000000 // was 24050002 addiu a1,zero,2 -> nop (a1 = player count)
// C2 FUN_0023FEA8: fall-out-of-world game over for any player (was players 1-2 only)
patch=2,EE,002403A0,word,822201B0 // was 8E04489C lw a0,0x489C(s0) -> lb v0,0x1B0(s1)
patch=2,EE,002403A4,word,04420013 // was 0C0E409A jal 0x00390268 -> bltzl v0,0x002403F4 (not a player)
patch=2,EE,002403A8,word,8E230000 // was 2484022C addiu a0,a0,556 -> lw v1,0(s1) (likely-delay, as the original bnel)
patch=2,EE,002403AC,word,00000000 // was 54510011 bnel v0,s1,0x002403F4 -> nop
patch=2,EE,002403B0,word,00000000 // was 8E230000 lw v1,0(s1) -> nop
// C3 FUN_004228A0 stats record by HUD slot: slots outside 0-1 use a scratch record at 0x000E3000 (0xC0 bytes)
patch=2,EE,004228A0,word,08038C40 // was 8CA20380 lw v0,0x380(a1) -> j 0x000E3100
patch=2,EE,004228A4,word,8CA20380 // was 240300C0 addiu v1,zero,0xC0 -> lw v0,0x380(a1) (delay slot)
patch=2,EE,000E3100,word,2C430002 // sltiu v1,v0,2
patch=2,EE,000E3104,word,14600004 // bne v1,zero,0x000E3118
patch=2,EE,000E3108,word,240300C0 // addiu v1,zero,0xC0 (delay slot)
patch=2,EE,000E310C,word,3C04000E // lui a0,0x000E
patch=2,EE,000E3110,word,34843000 // ori a0,a0,0x3000   scratch record
patch=2,EE,000E3114,word,00001021 // addu v0,zero,zero  record 0 of the scratch
patch=2,EE,000E3118,word,00432818 // mult a1,v0,v1
patch=2,EE,000E311C,word,03E00008 // jr ra
patch=2,EE,000E3120,word,00A41021 // addu v0,a1,a0
// C4 FUN_0041B7A0 (Lua SpawnCustomCrime): HUD widget only for HUD slots 0-1 (was: any player)
patch=2,EE,0041B7FC,word,8C620380 // was 806201B0 lb v0,0x1B0(v1) -> lw v0,0x380(v1)
patch=2,EE,0041B800,word,2C420002 // was 00021027 nor v0,zero,v0 -> sltiu v0,v0,2
```
Notes:
- C1: a1 is free there (the function never reads its second argument; every later a1 is set before a call). On the
  `count < 2` path the `beql` delay slot is annulled, as before. The game RNG (0x006EB880) is called once, as before,
  so the number of RNG draws is unchanged. VERIFIED (disassembly 0x002F0318-0x002F0498).
- C2: s1 is the human (the original compares the resolved handles with s1). No branch lands in 0x002403A0-0x002403B0
  (the only nearby branch, at 0x00240398, targets 0x002403B8). VERIFIED. Optional: it changes behaviour only for
  players 3-4 and matches what the original does for player 2.
- C3: free RAM 0x000E3000-0x000E3123 (not used by `mod/w4p_m1.pnach`; F-0125: 0x00096000-0x000EFFFF zero at runtime).
  The scratch record is game RAM above `kGameRamStart`, so it is in the desync hash. Players 3-4 get no stats. AI
  humans (slot -1) also go to the scratch record instead of 0xC0 bytes before the table. VERIFIED (code) / HYPOTHESIS
  (no caller expects the slot-2/3 alias).
- C4: same pattern as the gang-command guard (F-0129). VERIFIED.

## 5. Runtime test plan (bots, SINGLE-PC)
Setup: Mission 13 via `MenuLoadLevel` with players 3-4 joining by Start (m13d setup: groups own view, hud, 4p, 4p hud
B1/B2, 4p spawn, test call, plus the C1-C4 lines), MTVU off.

PINE reads every 0.25 s for each player h (handles GameMgr+0x228..+0x234 -> object table 0x006EBD38) and for the 8
nearest enemies (human pool 0x00640C80 + k*0x6D0, `+0x1B0 == -1`):
- `s = read32(h+0xD4)`; health `s16(read32(s+0x144) & 0xFFFF)`, max `s16(read32(s+0x146)...)`, flags
  `read64(s+0x00)`; position `h+0x10`; rage `read32(h+0x650)`.
- enemy brain `b = 0x006D53F0 + 0x2F0 * s16(read32(e+0x90) >> 16)`; target list `read32(b+0x164+4*i)`, i = 0..15.

Inputs: players 3-4 walk towards the nearest enemy and press Square/X (attack) in bursts, Circle (grab) every few
seconds; players 1-2 stand still away from the fight.

Pass conditions (criterion 3):
1. An enemy's target list contains player 3's or 4's handle (enemies target 3-4).
2. Player 3's and player 4's health go down at least once (enemies hit 3-4).
3. A nearby enemy's health goes down while only players 3-4 attack (3-4 attack).
4. An enemy's flags show 0x830 (grabbed) while player 3 or 4 holds it (grab).
5. Player 3 or 4 shows 0xE0000/0x2000 (prone) and later clears it while health > 0 (knock-down and recovery).
6. No TLB miss; with 4 lockstep instances, hash streams equal.
Optional: with C3, `read32(0x006FE490+0x180..+0x2FF)` stays unchanged while players 3-4 fight (no stats corruption);
with C1, run the AI behaviour that uses FUN_002F0318 and see players 3-4 picked (needs a mission that uses it; not
identified).

## Summary
Combat is index-agnostic: health stats+0x144 (s16, stats = human+0xD4), max +0x146, state flags at stats+0 (dead
bit 32, prone 0xE0000/0x2000, grabbed 0x830, arrested 0x20000), rage human+0x650. Enemies pick targets from gang member
lists (FUN_0028B358 -> brain+0x164, 16 handles) with hostility by gang relation and `human+0x1B0 != -1`, so joined
companions and spawned Warriors (gang members) are targets. Nearest-player helpers loop the player count. Remaining
2-player spots: one AI picker uses random(2) (C1), fall-out-of-world game over only for P1/P2 (C2, parity), the stats
table indexed by HUD slot writes into its own checkpoint copy for slots 2-3 (C3) and SpawnCustomCrime writes a 2-entry
HUD widget (C4); 21 words, checked, 0 problems. Cosmetic/script-only: radar hostile icons, button-tap partner prompt,
scripted slow-mo reset, stats sum. Known gap: no inventory for players 3-4 (no revives), so their death ends the game
sooner; widening the inventory (GameMgr+0x480, 17 API functions) is a separate task. Runtime test plan in section 5.

# M6 mission fixes X1, X2, X3, X5, X7, X8: implementation and single-instance tests (2026-10-12)

Build: The Warriors SLUS-21215 v1.03 (`local/disc/SLUS_212.15`, read-only), fork build w4p-m5-1 (not rebuilt; `emulator/`
untouched). Design: `docs/research/m6_missions.md` section 2 (fix catalogue), section 4 (starting items), 5.3 (mission
end). Builds on `session_policies.md` 3.4 (LEAVE at 0x000E7100, now ending at 0x000E72F4), `m2_spawn_companion.md`,
`m2_extra_model.md` 4.3 (SPAWNPICK/PX/JS/ENSURE/LV), `m2_inventory34.md` (Block B). Function and structure names are
OUR labels (the ELF is stripped); addresses are static unless marked. Labels: VERIFIED (with pointer), HYPOTHESIS,
FAILED TEST. **All tests: SINGLE-PC, one instance, scripted bot input, no impairment**, groups as in STATE.md plus
`warriors-4p session;warriors-4p session call;warriors-4p missions`, MTVU off, patch `local/m6/dev*.pnach` (generated
with `python -I mod/make_pnach.py`; `mod/w4p_m1.pnach` was NOT regenerated because the smoke batch reads it).

## Summary
| Fix | What | Where (source / group) | Result |
|---|---|---|---|
| X1 | delete guard: LEAVE player 3/4 before a script deletes his human | `mod/m2/missions.txt`, new group `[warriors-4p missions]`; hooks 0x00358624 (HuDelete) and 0x0016D0C0 (GangDelete) | **VERIFIED** (m6x1b: Mission 13's own `HuDelete(fox)` with player 3 = Fox; m6x1: gang path with a W4P-added Warrior) |
| X2 | pick filter for players 3-4 (own gang, AI, takeable, not in the do-not-take table, never the fallback scan; else spawn) | `mod/m2/spawn.txt` (`[4p spawn]`): PX's picker call 0x000E1B44 -> X2SEL | **VERIFIED** (A/B m6x2m14a/b: the original gives player 4 the pit-fight Ajax, X2 spawns a Warrior) |
| X3 | HuChangePlayerGang wrapper: LEAVE index 3 then 2 first | `missions.txt`; hook 0x0035D1E8 | **VERIFIED** (A/B m6x3m18b/m6x3m18orig: Mission 18 cp4's own `HuChangePlayerGang(GangRiff01, true)` with 4 players; the original re-seats players 3-4 on the just-released Swan and Snow and leaves the two W4P Warriors behind as AI) |
| X5 | no Lua leave event for index >= 2 on any path | `mod/m2/spawn_leave.txt` (`[4p spawn leave]`): LEAVEHOOK's event call 0x000E1248 -> X5EV | **VERIFIED** (m6x1, instrumented: game leave loop with 4 players -> 1 event (index 1), 1 skipped (index 2)) |
| X7 | starting items for players 3-4 (optional) | `missions.txt`; hooks 0x0041A5C0 (join event call) and 0x00160AE0 (ResetLevel) | **VERIFIED** (m6x7m13: spray 6; m6x7m3: money 15 + spray 1; no second gift on a re-join) |
| X8 | mission end: clear slots 2-3 (live + checkpoint copy) instead of banking them | `mod/m2/inventory.txt` (`[4p inventory]`): Block B cave 0x000E5000 replaced | **VERIFIED** (m6x8: money 10/20/30/40 -> all 0, copy 0, bank 0 -> 0) |
| - | regression: Mission 13, 4 players, random bots | all groups | **VERIFIED** (m6reg: polls 9002-25181, about 9 min of game time, 4 players / 4 views throughout, 0 TLB misses) |

`python -I tools/note_patches.py check local/m6/dev2.pnach`: **3122 addresses, 6 problems** = exactly the 6 known
`[4p hud A]` vs `[4p hud B1]` alternatives (the current `mod/w4p_m1.pnach` gives 2818 addresses, 6 problems; +304 new
addresses). The four changed sources alone: 996 addresses, 0 problems. 295 new code words disassembled and re-assembled
to the same word, comments equal the disassembly (scratch tool, section 3).

New side effects found (details section 6): a forced leave (X1/X3) empties that player's inventory slot and X7 does not
give the items again; after Mission 13's Fox deletion the re-joining player is spawned **as Fox** (CHOOSE), and ENSURE
moves player 4's model pin away from a Warrior still in use; Mission 16 cp1 accepted no drop-in at all in two runs.

## 1. Where the code is
| Address | Source / group | Content |
|---|---|---|
| 0x00358624 | missions | `jal X1D` (was 0C08CFBC `jal 0x00233EF0`, HuDelete binding FUN_00358608) |
| 0x0016D0C0 | missions | `jal X1G` (was 0C0591CE `jal 0x00164738`, GangDelete core FUN_0016D068) |
| 0x0035D1E8 | missions | `jal X3W` (was 0C08E6E0 `jal 0x00239B80`, HuChangePlayerGang binding FUN_0035D1A8) |
| 0x0041A5C0 | missions | `jal X7J` (was 0C106C52 `jal 0x0041B148`, join event call in UpdateJoin FUN_0041A460) |
| 0x00160AE0 | missions | `jal X7R` (was 0C05B0BC `jal 0x0016C2F0`, ResetLevel FUN_001607B8) |
| 0x000E7400-0x000E7473 | missions | REL34(human) (shared by X1D/X1G) |
| 0x000E7480-0x000E74D3 / 0x000E7500-0x000E756F | missions | X1D(handle) / X1G(gang) |
| 0x000E7580-0x000E761F | missions | X3W(gang id, flag) |
| 0x000E7640-0x000E7727 / 0x000E7740-0x000E774B | missions | X7J / X7R |
| 0x000E7760-0x000E7777, 0x000E7780 | missions (patch=0) | X7 table (level, Flash, spray, money) / given flags (byte per HUD slot) |
| 0x000E1B44 | 4p spawn | PX's picker call -> `jal X2SEL` (pnach had 0C08A9DC `jal 0x0022A770`) |
| 0x000E1C60-0x000E1DD7 | 4p spawn | X2SEL / X2 picker |
| 0x000E1E00-0x000E1E0F | 4p spawn (patch=0) | X2 do-not-take table |
| 0x000E1248 | 4p spawn leave | LEAVEHOOK's event call -> `jal X5EV` (pnach had 0C106C52 `jal 0x0041B148`) |
| 0x000E1290-0x000E12BB | 4p spawn leave | X5EV |
| 0x000E5000-0x000E502B | 4p inventory | X8 cave (was Block B, 0x000E5000-0x000E501B); hook 0x0015D3F4 unchanged |

Low RAM now used additionally: 0x000E1C60-0x000E1E0F, 0x000E1290-0x000E12BB, 0x000E501C-0x000E502B,
0x000E7400-0x000E7783 (all grepped free in the pnach, the sources, tests/tools and the fork patches before use; test
scratch 0x000E5D00-0x000E5D7F used only by test probes/variants). Group dependencies: `[warriors-4p missions]` needs
`[warriors-4p session]` (LEAVE), `[4p spawn]` (RELEASE 0x000E1698, PIN_ID 0x000E1C00) and `[4p spawn leave]`; X7 acts
only with HUD slots 2-3 (`[4p hud B1]`) and needs `[4p inventory]` to store slots 2-3. X2, X5, X8 change existing groups
in place (they are active wherever those groups are). `mod/make_pnach.py` registers `missions.txt` as
`[warriors-4p missions]` after `[warriors-4p session]`.

## 2. Design as implemented (and where it differs from m6_missions.md section 2)
### X1 delete guard
- **REL34(human)** (VERIFIED code): if +0x1B0 (player index) >= 2: if +0x1B1 == 7 (Warrior added by W4P), clear the
  marker and, if its char id equals PIN_ID, call RELEASE (exactly what LV would do); then `LEAVE(index)`. Clearing the
  marker matters because LEAVE's index >= 2 path calls LV -> DESPAWN -> HuDelete core for a marked Warrior, and the caller
  would then delete the same human a second time (HuDelete) or clean it up after deletion (gang path).
- **HuDelete path** X1D: resolves the handle as the core does (`FUN_00390268`, `FUN_00229868` = human or 0), REL34, then
  the original core `FUN_00233EF0(handle)`.
- **Gang path, site changed:** the note proposed 0x0016478C (`jal 0x0021C7C8` inside the member loop FUN_00164738).
  FUN_00164738 is also called by `FUN_0016C2F0` (all 32 gangs) from ResetLevel (call 0x00160AE0) - LEAVE there would
  run during the level teardown. GangDelete/RemoveGang reach FUN_00164738 only through `FUN_0016D068` (callers of
  `FUN_0016A1E8`: Lua binding 0x00373200 and the engine's FUN_0016A670, FUN_0016CC60, FUN_0016D170, FUN_001EECC0,
  FUN_001F1FA8, FUN_001FE720; VERIFIED by an ELF jal scan). So X1G replaces `FUN_0016D068`'s call 0x0016D0C0: it walks the
  16 member slots (gang+0x48), REL34 for every player with index >= 2, then tail-jumps to FUN_00164738. ReleasePlayer
  puts the released human back into the same gang (FUN_00166308, first free slot), so FUN_00164738 then cleans him up as
  AI. Also, the LEAVE runs before `FUN_001664D8` removes the member, not in the middle of the loop.
- If LEAVE does not release (v0 != 1, e.g. drop-in pad bit clear), the delete continues as in the original game.
### X2 pick filter (in `[4p spawn]`)
- X2SEL replaces PX's call of PickJoinCompanion. `s2` (UpdateJoin's pad) < 0 or `s3` (count at entry) < 2 -> tail jump
  to the original FUN_0022A770 (player 2, level start, script joins). Otherwise our loop over player 1's gang (a0,
  gang+0x48, 16 slots): AI (+0x1B0 == -1), **not refused by the game's own take-over tests for param 1**
  (`FUN_00227E60`, mask 0x180050000 = dead/beaten/downed/..., which contains FUN_00227DD8's 0x40000; and `FUN_00223B70`,
  0x20000 arrested), not in the do-not-take table; lowest non-zero priority (+0x1B1) else the first such member, exactly
  FUN_0022A770's in-gang rule; **no fallback scan**; nobody -> 0 -> SPAWNPICK spawns (JS).
- Table (patch=0, 4-byte rows: level, last checkpoint, s16 Warrior name index from `FUN_00229570`, -1 = every member; the
  name index matches every variant id of a Warrior): level52 cp <= 255 all; level55 cp <= 1 Cochise (index 1); level9
  cp <= 2 Fox (index 5).
### X3 wrapper
- X3W(gang id, flag): if player 1 is already in the target gang (`brain(P1)+0x20C == FUN_0016C388(id)`), the core does
  nothing (0x00239BF0), so no release. Otherwise, while the count is > 2: `LEAVE(count-1)` (last index first; stop if
  LEAVE does not return 1). Then the original `FUN_00239B80(id, flag)`, return value passed through.
### X5
- LEAVEHOOK (0x000E1240) is called from two places: the game's leave loop (call 0x0041A868, loop index in s3, return
  address 0x0041A870) and the session LEAVE cave (only for index 0-1, s3 = a handle there). X5EV reads LEAVEHOOK's saved
  return address: game loop and s3 >= 2 -> skip the event; every other case -> the event as before.
### X7 starting items (m6_missions.md section 4, option S1)
- X7J replaces UpdateJoin's join-event call (0x0041A5C0; arguments GameMgr, human, 1): runs the event, then for player
  index >= 2 with HUD slot 2-3, checkpoint 0/1 and the slot's "given" byte clear: sets the byte and gives the level's
  `MS` values (WAD 4106 main_149, `04106:4616-4651`; rows 87: spray 1 money 15, 5: spray 2, 9: spray 6, 51: Flash 1
  spray 1, 84: Flash 1) through the cores the Lua functions use with player number = slot + 1: `FUN_0041EDB8`
  InvGiveRevive (adds), `FUN_0041F030` InvSetSpraycanCharges (sets), `FUN_0041EEB8` InvSetMoney (sets). Zero values are
  skipped. X7R clears the bytes at every level (re)load (ResetLevel's call of FUN_0016C2F0). Same rule as player 2's
  `InventoryPlayer2`/`SetPlayer2Inventory = nil` (first join per level load at checkpoint 0/1).
### X8
- At 0x0015D3F4 (s0 = Inv = GameMgr+0x480, after slots 0-1 were banked): `InvReleaseSlot(Inv, 2)`, `InvReleaseSlot(Inv,
  3)` (FUN_0041EC60 -> FUN_0041E218, rewritten by `[4p inventory]` A5 to clear live + copy), then `j 0x00155308`.

## 3. Checks
- Every word was assembled with a scratch assembler, disassembled back with a scratch disassembler and re-assembled; the
  comment of each generated line is the disassembly. Independent pass over the final sources (all patch=2 words in
  0x000E7400-0x000E778F, 0x000E1C60-0x000E1E0F, 0x000E1290-0x000E12BF, 0x000E5000-0x000E502B): **295 code words, 0
  mismatches**. Branch targets and delay slots were reviewed by hand against the listings above.
- The five new hook sites and their delay slots were read from the ELF (`was` words below); none is patched by another
  group (grep of the pnach and sources).
- `python -I tools/note_patches.py check local/m6/dev2.pnach`:
```
CONFLICT 001C0648: dev2.pnach:1829 sets 0803C374, dev2.pnach:2509 sets 0803815C
CONFLICT 001C7890: dev2.pnach:1831 sets 0803C384, dev2.pnach:2511 sets 08038164
CONFLICT 001A6D28: dev2.pnach:1833 sets 0803C394, dev2.pnach:2513 sets 0803816C
CONFLICT 001A6C38: dev2.pnach:1835 sets 0803C3A4, dev2.pnach:2515 sets 08038174
CONFLICT 0041DC44: dev2.pnach:1837 sets 2CA20002, dev2.pnach:2811 sets 2CA20004
CONFLICT 0041DC50: dev2.pnach:1839 sets 3C030060, dev2.pnach:2813 sets 3C03000E
checked 3122 addresses in 1 files: 6 problems
```
  (the 6 known `[4p hud A]`/`[4p hud B1]` alternatives) and
  `python -I tools/note_patches.py check mod/m2/missions.txt mod/m2/spawn.txt mod/m2/spawn_leave.txt mod/m2/inventory.txt`:
  `checked 996 addresses in 4 files: 0 problems`.
- pnach files used: `local/m6/dev.pnach` (X1, X2, X3, X5, X8), `local/m6/dev2.pnach` (= current sources, + X7),
  `local/m6/dev_nox2.pnach` (dev with 0x000E1B44 back to `jal 0x0022A770`, A/B for X2), `local/m6/dev_x5cnt.pnach` (dev
  with TEST-ONLY counters in X5EV: x5_ev -> 0x000E5D40 counts at 0x000E5D38, x5_skip -> 0x000E5D60 counts at
  0x000E5D3C). PCSX2 re-applies patch=2 words every frame (`Patch.cpp` PPT_COMBINED_0_1), so code A/B is done with
  pnach variants, not PINE writes; patch=0 data (the X2 table) can be changed by PINE.

## 4. Patch fragments (as in the sources)
### `mod/m2/missions.txt` (new group `[warriors-4p missions]`, whole file)
```
// [warriors-4p missions] M6 mission fixes X1, X3 and X7 (docs/research/m6_missions.md section 2, docs/research/m6_fixes.md).
// Needs [warriors-4p session] (LEAVE 0x000E7100), [warriors-4p 4p spawn] (RELEASE, PIN_ID) and [warriors-4p 4p spawn leave].
// X1 delete guard: before a script deletes a human held by player 3/4 (HuDelete binding 0x00358608, call 0x00358624;
//    GangDelete FUN_0016D068, call 0x0016D0C0 of the member cleanup FUN_00164738 - not used by the level teardown
//    FUN_0016C2F0), LEAVE(index) releases him; the delete then runs on the AI human. A W4P-added Warrior (+0x1B1 = 7)
//    gets its marker cleared first, so only the caller deletes him (LEAVE's LV would delete him too); its pin is released.
// X3 HuChangePlayerGang wrapper (binding 0x0035D1A8, call 0x0035D1E8): unless player 1 is already in the target gang,
//    LEAVE the last index while more than 2 players are in, then the original FUN_00239B80 (<= 2 players).
//    Players 3-4 re-join with Start (W4P X11 injects it).
// X7 starting items (m6_missions.md section 4, option S1): when player 3/4 joins by Start (UpdateJoin's join-event call
//    0x0041A5C0) at checkpoint 0/1, the first time per level load for that HUD slot, he gets the level's MS values like
//    player 2 (WAD 4106 main_149/153): Flash added, spray and money set (InvGiveRevive/InvSetSpraycanCharges/InvSetMoney
//    cores, player number = HUD slot + 1). Flags cleared at every level load (ResetLevel call 0x00160AE0). Needs [4p hud B1]
//    (HUD slots 2-3) and [4p inventory] (slots 2-3 accepted).
// Free RAM 0x000E7400-0x000E7783.
patch=2,EE,00358624,word,0C039D20 // X1: was 0C08CFBC jal 0x00233EF0 (HuDelete core) -> jal 0x000E7480 X1D; delay slot daddu a0,v0,zero kept
patch=2,EE,0016D0C0,word,0C039D40 // X1: was 0C0591CE jal 0x00164738 (gang member cleanup) in GangDelete FUN_0016D068 -> jal 0x000E7500 X1G; delay slot daddu a0,s1,zero kept
patch=2,EE,0035D1E8,word,0C039D60 // X3: was 0C08E6E0 jal 0x00239B80 (HuChangePlayerGang core) -> jal 0x000E7580 X3W; delay slot sltu a1,zero,v0 kept
patch=2,EE,0041A5C0,word,0C039D90 // X7: was 0C106C52 jal 0x0041B148 (join event) in UpdateJoin -> jal 0x000E7640 X7J; delay slot daddu a0,s1,zero kept
patch=2,EE,00160AE0,word,0C039DD0 // X7: was 0C05B0BC jal 0x0016C2F0 (delete all gangs) in ResetLevel FUN_001607B8 -> jal 0x000E7740 X7R; delay slot nop kept
patch=2,EE,000E7400,word,27BDFFE0 // REL34: addiu sp, sp, -32  ; REL34(human): release player 3/4 (index >= 2) with LEAVE before a script deletes him
patch=2,EE,000E7404,word,FFBF0000 // sd ra, 0x0(sp)
patch=2,EE,000E7408,word,7FB00010 // sq s0, 0x10(sp)
patch=2,EE,000E740C,word,0080802D // daddu s0, a0, zero
patch=2,EE,000E7410,word,820401B0 // lb a0, 0x1B0(s0)  ; player index (-1 = AI)
patch=2,EE,000E7414,word,28880002 // slti t0, a0, 2
patch=2,EE,000E7418,word,15000012 // bne t0, zero, 0x000E7464  ; AI, player 1 or player 2: nothing to do
patch=2,EE,000E741C,word,0000102D // daddu v0, zero, zero
patch=2,EE,000E7420,word,920801B1 // lbu t0, 0x1B1(s0)  ; join priority; 7 = Warrior added by W4P (SPAWN)
patch=2,EE,000E7424,word,24090007 // addiu t1, zero, 7
patch=2,EE,000E7428,word,1509000C // bne t0, t1, 0x000E745C
patch=2,EE,000E742C,word,00000000 // nop
patch=2,EE,000E7430,word,A20001B1 // sb zero, 0x1B1(s0)  ; added Warrior: clear the marker so LEAVE's LV does not delete him too (the caller deletes)
patch=2,EE,000E7434,word,8E0800D0 // lw t0, 0xD0(s0)  ; char id (as LV): his model pin is released like on a leave
patch=2,EE,000E7438,word,3C09000E // lui t1, 0x000E
patch=2,EE,000E743C,word,8D291C00 // lw t1, 0x1C00(t1)  ; PIN_ID
patch=2,EE,000E7440,word,11200006 // beq t1, zero, 0x000E745C
patch=2,EE,000E7444,word,00000000 // nop
patch=2,EE,000E7448,word,15090004 // bne t0, t1, 0x000E745C
patch=2,EE,000E744C,word,00000000 // nop
patch=2,EE,000E7450,word,0C0385A6 // jal 0x000E1698  ; unpin player 4's extra model (data stays cached)
patch=2,EE,000E7454,word,00000000 // nop
patch=2,EE,000E7458,word,820401B0 // lb a0, 0x1B0(s0)  ; index again for LEAVE
patch=2,EE,000E745C,word,0C039C40 // r34_leave: jal 0x000E7100  ; LEAVE(index): release, cameras, pad owners, layout (session group)
patch=2,EE,000E7460,word,00000000 // nop
patch=2,EE,000E7464,word,DFBF0000 // r34_out: ld ra, 0x0(sp)
patch=2,EE,000E7468,word,7BB00010 // lq s0, 0x10(sp)
patch=2,EE,000E746C,word,03E00008 // jr ra
patch=2,EE,000E7470,word,27BD0020 // addiu sp, sp, 32
patch=2,EE,000E7480,word,27BDFFD0 // X1D: addiu sp, sp, -48  ; X1D(handle): replaces the HuDelete binding's call of the core 0x00233EF0
patch=2,EE,000E7484,word,FFBF0000 // sd ra, 0x0(sp)
patch=2,EE,000E7488,word,7FB00010 // sq s0, 0x10(sp)
patch=2,EE,000E748C,word,AFA40020 // sw a0, 0x20(sp)
patch=2,EE,000E7490,word,0080802D // daddu s0, a0, zero  ; handle
patch=2,EE,000E7494,word,0C0E409A // jal 0x00390268  ; object of the handle (0 = none)
patch=2,EE,000E7498,word,27A40020 // addiu a0, sp, 32
patch=2,EE,000E749C,word,10400007 // beq v0, zero, 0x000E74BC
patch=2,EE,000E74A0,word,00000000 // nop
patch=2,EE,000E74A4,word,0C08A61A // jal 0x00229868  ; the core's own test: human or 0
patch=2,EE,000E74A8,word,0040202D // daddu a0, v0, zero
patch=2,EE,000E74AC,word,10400003 // beq v0, zero, 0x000E74BC
patch=2,EE,000E74B0,word,00000000 // nop
patch=2,EE,000E74B4,word,0C039D00 // jal 0x000E7400  ; player 3/4: LEAVE first, he is AI when deleted
patch=2,EE,000E74B8,word,0040202D // daddu a0, v0, zero
patch=2,EE,000E74BC,word,0C08CFBC // x1d_del: jal 0x00233EF0  ; HuDelete core (the replaced call)
patch=2,EE,000E74C0,word,0200202D // daddu a0, s0, zero
patch=2,EE,000E74C4,word,DFBF0000 // ld ra, 0x0(sp)
patch=2,EE,000E74C8,word,7BB00010 // lq s0, 0x10(sp)
patch=2,EE,000E74CC,word,03E00008 // jr ra
patch=2,EE,000E74D0,word,27BD0030 // addiu sp, sp, 48
patch=2,EE,000E7500,word,27BDFFD0 // X1G: addiu sp, sp, -48  ; X1G(gang): replaces GangDelete's (FUN_0016D068) call of the member cleanup 0x00164738
patch=2,EE,000E7504,word,FFBF0000 // sd ra, 0x0(sp)
patch=2,EE,000E7508,word,7FB00010 // sq s0, 0x10(sp)
patch=2,EE,000E750C,word,7FB10020 // sq s1, 0x20(sp)
patch=2,EE,000E7510,word,0080802D // daddu s0, a0, zero  ; gang object
patch=2,EE,000E7514,word,0000882D // daddu s1, zero, zero  ; member slot 0..15
patch=2,EE,000E7518,word,00114080 // x1g_loop: sll t0, s1, 2
patch=2,EE,000E751C,word,02082021 // addu a0, s0, t0
patch=2,EE,000E7520,word,0C0E409A // jal 0x00390268  ; member handle at gang+0x48+4*slot
patch=2,EE,000E7524,word,24840048 // addiu a0, a0, 72
patch=2,EE,000E7528,word,10400007 // beq v0, zero, 0x000E7548
patch=2,EE,000E752C,word,00000000 // nop
patch=2,EE,000E7530,word,804801B0 // lb t0, 0x1B0(v0)  ; player index
patch=2,EE,000E7534,word,29080002 // slti t0, t0, 2
patch=2,EE,000E7538,word,15000003 // bne t0, zero, 0x000E7548
patch=2,EE,000E753C,word,00000000 // nop
patch=2,EE,000E7540,word,0C039D00 // jal 0x000E7400  ; player 3/4: LEAVE; ReleasePlayer keeps him in this gang as AI, cleaned up below
patch=2,EE,000E7544,word,0040202D // daddu a0, v0, zero
patch=2,EE,000E7548,word,26310001 // x1g_next: addiu s1, s1, 1
patch=2,EE,000E754C,word,2A280010 // slti t0, s1, 16
patch=2,EE,000E7550,word,1500FFF1 // bne t0, zero, 0x000E7518
patch=2,EE,000E7554,word,00000000 // nop
patch=2,EE,000E7558,word,0200202D // daddu a0, s0, zero
patch=2,EE,000E755C,word,DFBF0000 // ld ra, 0x0(sp)
patch=2,EE,000E7560,word,7BB00010 // lq s0, 0x10(sp)
patch=2,EE,000E7564,word,7BB10020 // lq s1, 0x20(sp)
patch=2,EE,000E7568,word,080591CE // j 0x00164738  ; the replaced call (tail call, ra = FUN_0016D068)
patch=2,EE,000E756C,word,27BD0030 // addiu sp, sp, 48
patch=2,EE,000E7580,word,27BDFFC0 // X3W: addiu sp, sp, -64  ; X3W(gang id, flag): replaces HuChangePlayerGang's call of 0x00239B80
patch=2,EE,000E7584,word,FFBF0000 // sd ra, 0x0(sp)
patch=2,EE,000E7588,word,7FB00010 // sq s0, 0x10(sp)
patch=2,EE,000E758C,word,7FB10020 // sq s1, 0x20(sp)
patch=2,EE,000E7590,word,0080802D // daddu s0, a0, zero
patch=2,EE,000E7594,word,00A0882D // daddu s1, a1, zero
patch=2,EE,000E7598,word,3C020051 // lui v0, 0x0051
patch=2,EE,000E759C,word,8C44489C // lw a0, 0x489C(v0)  ; GameMgr
patch=2,EE,000E75A0,word,0C0E409A // jal 0x00390268  ; player 1
patch=2,EE,000E75A4,word,24840228 // addiu a0, a0, 552
patch=2,EE,000E75A8,word,10400015 // beq v0, zero, 0x000E7600
patch=2,EE,000E75AC,word,00000000 // nop
patch=2,EE,000E75B0,word,0C087502 // jal 0x0021D408
patch=2,EE,000E75B4,word,0040202D // daddu a0, v0, zero
patch=2,EE,000E75B8,word,8C48020C // lw t0, 0x20C(v0)  ; player 1's gang
patch=2,EE,000E75BC,word,AFA80030 // sw t0, 0x30(sp)
patch=2,EE,000E75C0,word,0C05B0E2 // jal 0x0016C388  ; target gang object (as 0x00239BD4)
patch=2,EE,000E75C4,word,0200202D // daddu a0, s0, zero
patch=2,EE,000E75C8,word,8FA80030 // lw t0, 0x30(sp)
patch=2,EE,000E75CC,word,1048000C // beq v0, t0, 0x000E7600  ; player 1 already in it: the core changes nothing (0x00239BF0)
patch=2,EE,000E75D0,word,00000000 // nop
patch=2,EE,000E75D4,word,3C020051 // x3_loop: lui v0, 0x0051
patch=2,EE,000E75D8,word,8C48489C // lw t0, 0x489C(v0)
patch=2,EE,000E75DC,word,85040224 // lh a0, 0x224(t0)  ; player count
patch=2,EE,000E75E0,word,28890003 // slti t1, a0, 3
patch=2,EE,000E75E4,word,15200006 // bne t1, zero, 0x000E7600  ; <= 2 players: original behaviour
patch=2,EE,000E75E8,word,00000000 // nop
patch=2,EE,000E75EC,word,0C039C40 // jal 0x000E7100  ; LEAVE(count-1): last index first, nobody moves down
patch=2,EE,000E75F0,word,2484FFFF // addiu a0, a0, -1
patch=2,EE,000E75F4,word,24090001 // addiu t1, zero, 1
patch=2,EE,000E75F8,word,1049FFF6 // beq v0, t1, 0x000E75D4  ; released: next
patch=2,EE,000E75FC,word,00000000 // nop
patch=2,EE,000E7600,word,0200202D // x3_call: daddu a0, s0, zero
patch=2,EE,000E7604,word,0C08E6E0 // jal 0x00239B80  ; the replaced call; players 3-4 re-join later (X11)
patch=2,EE,000E7608,word,0220282D // daddu a1, s1, zero
patch=2,EE,000E760C,word,DFBF0000 // ld ra, 0x0(sp)
patch=2,EE,000E7610,word,7BB00010 // lq s0, 0x10(sp)
patch=2,EE,000E7614,word,7BB10020 // lq s1, 0x20(sp)
patch=2,EE,000E7618,word,03E00008 // jr ra
patch=2,EE,000E761C,word,27BD0040 // addiu sp, sp, 64
patch=2,EE,000E7640,word,27BDFFD0 // X7J: addiu sp, sp, -48  ; X7J(GameMgr, human, 1): replaces UpdateJoin's call of the join event FUN_0041B148 (0x0041A5C0)
patch=2,EE,000E7644,word,FFBF0000 // sd ra, 0x0(sp)
patch=2,EE,000E7648,word,7FB00010 // sq s0, 0x10(sp)
patch=2,EE,000E764C,word,7FB10020 // sq s1, 0x20(sp)
patch=2,EE,000E7650,word,0C106C52 // jal 0x0041B148  ; the replaced call (guard 0x0041B180: no Lua event for index >= 2)
patch=2,EE,000E7654,word,00A0802D // daddu s0, a1, zero  ; joining human
patch=2,EE,000E7658,word,820801B0 // lb t0, 0x1B0(s0)  ; player index
patch=2,EE,000E765C,word,29080002 // slti t0, t0, 2
patch=2,EE,000E7660,word,1500002C // bne t0, zero, 0x000E7714  ; players 1-2: Lua SetupLevelInventory / InventoryPlayer2 (WAD 4106 main_150/152)
patch=2,EE,000E7664,word,8E090380 // lw t1, 0x380(s0)  ; HUD slot = inventory slot (2/3 with [4p hud B1])
patch=2,EE,000E7668,word,252AFFFE // addiu t2, t1, -2
patch=2,EE,000E766C,word,2D4A0002 // sltiu t2, t2, 2
patch=2,EE,000E7670,word,11400028 // beq t2, zero, 0x000E7714
patch=2,EE,000E7674,word,3C020051 // lui v0, 0x0051
patch=2,EE,000E7678,word,8C4B489C // lw t3, 0x489C(v0)  ; GameMgr
patch=2,EE,000E767C,word,956C033A // lhu t4, 0x33A(t3)  ; checkpoint
patch=2,EE,000E7680,word,2D8C0002 // sltiu t4, t4, 2
patch=2,EE,000E7684,word,11800023 // beq t4, zero, 0x000E7714  ; like main_150/152: checkpoint 0 or 1 only
patch=2,EE,000E7688,word,3C0D000E // lui t5, 0x000E
patch=2,EE,000E768C,word,01A96821 // addu t5, t5, t1
patch=2,EE,000E7690,word,91AE7780 // lbu t6, 0x7780(t5)  ; this slot already got them in this level load (SetPlayer2Inventory = nil)
patch=2,EE,000E7694,word,15C0001F // bne t6, zero, 0x000E7714
patch=2,EE,000E7698,word,240E0001 // addiu t6, zero, 1
patch=2,EE,000E769C,word,A1AE7780 // sb t6, 0x7780(t5)
patch=2,EE,000E76A0,word,956F56DC // lhu t7, 0x56DC(t3)  ; level index
patch=2,EE,000E76A4,word,000FC1C0 // sll t8, t7, 7
patch=2,EE,000E76A8,word,000FC880 // sll t9, t7, 2
patch=2,EE,000E76AC,word,03197821 // addu t7, t8, t9
patch=2,EE,000E76B0,word,01EB7821 // addu t7, t7, t3
patch=2,EE,000E76B4,word,8DEF14D8 // lw t7, 0x14D8(t7)  ; level number
patch=2,EE,000E76B8,word,3C11000E // lui s1, 0x000E
patch=2,EE,000E76BC,word,26317760 // addiu s1, s1, 30560
patch=2,EE,000E76C0,word,92380000 // x7_tab: lbu t8, 0x0(s1)  ; row: level, Flash, spray, money (0 = end)
patch=2,EE,000E76C4,word,13000013 // beq t8, zero, 0x000E7714
patch=2,EE,000E76C8,word,00000000 // nop
patch=2,EE,000E76CC,word,170FFFFC // bne t8, t7, 0x000E76C0
patch=2,EE,000E76D0,word,26310004 // addiu s1, s1, 4  ; next row (on a match s1 = row + 4)
patch=2,EE,000E76D4,word,25300001 // addiu s0, t1, 1  ; player number = slot + 1 (Lua-style wrappers use p - 1)
patch=2,EE,000E76D8,word,9224FFFD // lbu a0, -0x3(s1)
patch=2,EE,000E76DC,word,10800003 // beq a0, zero, 0x000E76EC
patch=2,EE,000E76E0,word,00000000 // nop
patch=2,EE,000E76E4,word,0C107B6E // jal 0x0041EDB8  ; FUN_0041EDB8 InvGiveRevive(n, p)
patch=2,EE,000E76E8,word,0200282D // daddu a1, s0, zero
patch=2,EE,000E76EC,word,9224FFFE // x7_paint: lbu a0, -0x2(s1)
patch=2,EE,000E76F0,word,10800003 // beq a0, zero, 0x000E7700
patch=2,EE,000E76F4,word,00000000 // nop
patch=2,EE,000E76F8,word,0C107C0C // jal 0x0041F030  ; FUN_0041F030 InvSetSpraycanCharges(n, p)
patch=2,EE,000E76FC,word,0200282D // daddu a1, s0, zero
patch=2,EE,000E7700,word,9224FFFF // x7_money: lbu a0, -0x1(s1)
patch=2,EE,000E7704,word,10800003 // beq a0, zero, 0x000E7714
patch=2,EE,000E7708,word,00000000 // nop
patch=2,EE,000E770C,word,0C107BAE // jal 0x0041EEB8  ; FUN_0041EEB8 InvSetMoney(n, p)
patch=2,EE,000E7710,word,0200282D // daddu a1, s0, zero
patch=2,EE,000E7714,word,DFBF0000 // x7_out: ld ra, 0x0(sp)
patch=2,EE,000E7718,word,7BB00010 // lq s0, 0x10(sp)
patch=2,EE,000E771C,word,7BB10020 // lq s1, 0x20(sp)
patch=2,EE,000E7720,word,03E00008 // jr ra
patch=2,EE,000E7724,word,27BD0030 // addiu sp, sp, 48
patch=2,EE,000E7740,word,3C08000E // X7R: lui t0, 0x000E  ; X7R: replaces ResetLevel's call of FUN_0016C2F0 (0x00160AE0): every level (re)load
patch=2,EE,000E7744,word,0805B0BC // j 0x0016C2F0  ; the replaced call (tail call, ra = ResetLevel)
patch=2,EE,000E7748,word,AD007780 // sw zero, 0x7780(t0)  ; players 3-4 may get the starting items again
patch=0,EE,000E7760,word,0F010057 // X7 row 1: level87 (M3): spray 1, money 15 (bytes level, Flash, spray, money; startup only)
patch=0,EE,000E7764,word,00020005 // X7 row 2: level5 (M7): spray 2 (bytes level, Flash, spray, money; startup only)
patch=0,EE,000E7768,word,00060009 // X7 row 3: level9 (M13): spray 6 (bytes level, Flash, spray, money; startup only)
patch=0,EE,000E776C,word,00010133 // X7 row 4: level51 (M14): Flash 1, spray 1 (bytes level, Flash, spray, money; startup only)
patch=0,EE,000E7770,word,00000154 // X7 row 5: level84 (M18): Flash 1 (bytes level, Flash, spray, money; startup only)
patch=0,EE,000E7774,word,00000000 // X7 table end (startup only)
patch=0,EE,000E7780,word,00000000 // X7 given flags, byte per HUD slot (+2, +3); cleared by X7R at every level load (startup only)
```

### `mod/m2/spawn.txt` (`[warriors-4p 4p spawn]`): changed line and appended X2 block
```
patch=2,EE,000E1B44,word,0C038718 // [warriors-4p 4p spawn] X2: jal 0x000E1C60 X2SEL (pnach had 0C08A9DC jal 0x0022A770 PickJoinCompanion); delay slot nop kept
// X2 (docs/research/m6_missions.md section 2, docs/research/m6_fixes.md): players 3-4 take only a member of player 1's own
// gang that is AI, not dead/downed/arrested (the picker's own tests for param 1: FUN_00227E60, FUN_00223B70) and not in
// the per-level do-not-take table; lowest non-zero priority first, else the first such member; never the fallback scan
// over all type-0 gangs; nobody -> 0, so SPAWNPICK spawns a Warrior (JS). Player 2 (count < 2) and the level-start /
// script path (pad -1) keep the original PickJoinCompanion FUN_0022A770. Table rows: byte level, byte last checkpoint,
// s16 Warrior name index (FUN_00229570; -1 = every member). PX's call 0x000E1B44 above goes here.
patch=2,EE,000E1C60,word,06400003 // X2SEL: bltz s2, 0x000E1C70  ; X2SEL(gang, 0): PX's picker; s2 = UpdateJoin pad (-1 = level start/script)
patch=2,EE,000E1C64,word,2A680002 // slti t0, s3, 2  ; s3 = player count at UpdateJoin entry
patch=2,EE,000E1C68,word,11000003 // beq t0, zero, 0x000E1C78  ; real Start press with >= 2 players: player 3 or 4
patch=2,EE,000E1C6C,word,00000000 // nop
patch=2,EE,000E1C70,word,0808A9DC // x2_orig: j 0x0022A770  ; player 2 and the level-start path: original PickJoinCompanion
patch=2,EE,000E1C74,word,00000000 // nop
patch=2,EE,000E1C78,word,27BDFF80 // x2_mine: addiu sp, sp, -128
patch=2,EE,000E1C7C,word,FFBF0000 // sd ra, 0x0(sp)
patch=2,EE,000E1C80,word,7FB00010 // sq s0, 0x10(sp)
patch=2,EE,000E1C84,word,7FB10020 // sq s1, 0x20(sp)
patch=2,EE,000E1C88,word,7FB40030 // sq s4, 0x30(sp)
patch=2,EE,000E1C8C,word,7FB50040 // sq s5, 0x40(sp)
patch=2,EE,000E1C90,word,7FB60050 // sq s6, 0x50(sp)
patch=2,EE,000E1C94,word,7FB70060 // sq s7, 0x60(sp)
patch=2,EE,000E1C98,word,0080802D // daddu s0, a0, zero  ; player 1's gang
patch=2,EE,000E1C9C,word,0000882D // daddu s1, zero, zero  ; member slot
patch=2,EE,000E1CA0,word,0000A02D // daddu s4, zero, zero  ; first takeable member
patch=2,EE,000E1CA4,word,0000A82D // daddu s5, zero, zero  ; takeable member with the lowest non-zero priority
patch=2,EE,000E1CA8,word,3C020051 // lui v0, 0x0051
patch=2,EE,000E1CAC,word,8C48489C // lw t0, 0x489C(v0)  ; GameMgr
patch=2,EE,000E1CB0,word,950956DC // lhu t1, 0x56DC(t0)  ; level index
patch=2,EE,000E1CB4,word,000951C0 // sll t2, t1, 7
patch=2,EE,000E1CB8,word,00095880 // sll t3, t1, 2
patch=2,EE,000E1CBC,word,014B4821 // addu t1, t2, t3  ; * 0x84
patch=2,EE,000E1CC0,word,01284821 // addu t1, t1, t0
patch=2,EE,000E1CC4,word,8D3614D8 // lw s6, 0x14D8(t1)  ; level number (GameMgr+0x14D4 + index*0x84 + 4, as 0x0022A868)
patch=2,EE,000E1CC8,word,9517033A // lhu s7, 0x33A(t0)  ; checkpoint
patch=2,EE,000E1CCC,word,00114080 // x2_loop: sll t0, s1, 2
patch=2,EE,000E1CD0,word,02082021 // addu a0, s0, t0
patch=2,EE,000E1CD4,word,0C0E409A // jal 0x00390268
patch=2,EE,000E1CD8,word,24840048 // addiu a0, a0, 72  ; member handle at gang+0x48+4*slot
patch=2,EE,000E1CDC,word,1040002D // beq v0, zero, 0x000E1D94
patch=2,EE,000E1CE0,word,0040202D // daddu a0, v0, zero
patch=2,EE,000E1CE4,word,804801B0 // lb t0, 0x1B0(v0)
patch=2,EE,000E1CE8,word,2409FFFF // addiu t1, zero, -1
patch=2,EE,000E1CEC,word,15090029 // bne t0, t1, 0x000E1D94  ; already a player
patch=2,EE,000E1CF0,word,AFA20070 // sw v0, 0x70(sp)
patch=2,EE,000E1CF4,word,0C089F98 // jal 0x00227E60  ; FUN_00227E60: dead/beaten/downed/... (the picker's own test for param 1)
patch=2,EE,000E1CF8,word,00000000 // nop
patch=2,EE,000E1CFC,word,14400025 // bne v0, zero, 0x000E1D94
patch=2,EE,000E1D00,word,8FA40070 // lw a0, 0x70(sp)
patch=2,EE,000E1D04,word,0C088EDC // jal 0x00223B70  ; FUN_00223B70 (same test)
patch=2,EE,000E1D08,word,00000000 // nop
patch=2,EE,000E1D0C,word,14400021 // bne v0, zero, 0x000E1D94
patch=2,EE,000E1D10,word,8FA40070 // lw a0, 0x70(sp)
patch=2,EE,000E1D14,word,0C08A55C // jal 0x00229570  ; FUN_00229570 (leaf): Warrior name index of this human
patch=2,EE,000E1D18,word,00000000 // nop
patch=2,EE,000E1D1C,word,3C0D000E // lui t5, 0x000E
patch=2,EE,000E1D20,word,25AD1E00 // addiu t5, t5, 7680  ; do-not-take table
patch=2,EE,000E1D24,word,91AE0000 // x2_tab: lbu t6, 0x0(t5)  ; level (0 = end)
patch=2,EE,000E1D28,word,11C0000C // beq t6, zero, 0x000E1D5C
patch=2,EE,000E1D2C,word,00000000 // nop
patch=2,EE,000E1D30,word,15D60008 // bne t6, s6, 0x000E1D54
patch=2,EE,000E1D34,word,91AF0001 // lbu t7, 0x1(t5)  ; last checkpoint of the row
patch=2,EE,000E1D38,word,01F7782A // slt t7, t7, s7
patch=2,EE,000E1D3C,word,15E00005 // bne t7, zero, 0x000E1D54
patch=2,EE,000E1D40,word,85AF0002 // lh t7, 0x2(t5)  ; Warrior name index, -1 = every member
patch=2,EE,000E1D44,word,05E00013 // bltz t7, 0x000E1D94
patch=2,EE,000E1D48,word,00000000 // nop
patch=2,EE,000E1D4C,word,11E20011 // beq t7, v0, 0x000E1D94
patch=2,EE,000E1D50,word,00000000 // nop
patch=2,EE,000E1D54,word,1000FFF3 // x2_tnext: beq zero, zero, 0x000E1D24
patch=2,EE,000E1D58,word,25AD0004 // addiu t5, t5, 4
patch=2,EE,000E1D5C,word,8FA80070 // x2_ok: lw t0, 0x70(sp)
patch=2,EE,000E1D60,word,810901B1 // lb t1, 0x1B1(t0)  ; join priority
patch=2,EE,000E1D64,word,16800002 // bne s4, zero, 0x000E1D70
patch=2,EE,000E1D68,word,00000000 // nop
patch=2,EE,000E1D6C,word,0100A02D // daddu s4, t0, zero
patch=2,EE,000E1D70,word,11200008 // x2_hasfirst: beq t1, zero, 0x000E1D94  ; priority 0: only as "first"
patch=2,EE,000E1D74,word,00000000 // nop
patch=2,EE,000E1D78,word,12A00005 // beq s5, zero, 0x000E1D90
patch=2,EE,000E1D7C,word,00000000 // nop
patch=2,EE,000E1D80,word,82AA01B1 // lb t2, 0x1B1(s5)
patch=2,EE,000E1D84,word,012A502A // slt t2, t1, t2
patch=2,EE,000E1D88,word,11400002 // beq t2, zero, 0x000E1D94
patch=2,EE,000E1D8C,word,00000000 // nop
patch=2,EE,000E1D90,word,0100A82D // x2_best: daddu s5, t0, zero
patch=2,EE,000E1D94,word,26310001 // x2_next: addiu s1, s1, 1
patch=2,EE,000E1D98,word,2A280010 // slti t0, s1, 16
patch=2,EE,000E1D9C,word,1500FFCB // bne t0, zero, 0x000E1CCC
patch=2,EE,000E1DA0,word,00000000 // nop
patch=2,EE,000E1DA4,word,02A0102D // daddu v0, s5, zero
patch=2,EE,000E1DA8,word,14400002 // bne v0, zero, 0x000E1DB4
patch=2,EE,000E1DAC,word,00000000 // nop
patch=2,EE,000E1DB0,word,0280102D // daddu v0, s4, zero  ; nobody (0): SPAWNPICK goes on to JS (spawn); never the fallback scan
patch=2,EE,000E1DB4,word,DFBF0000 // x2_out: ld ra, 0x0(sp)
patch=2,EE,000E1DB8,word,7BB00010 // lq s0, 0x10(sp)
patch=2,EE,000E1DBC,word,7BB10020 // lq s1, 0x20(sp)
patch=2,EE,000E1DC0,word,7BB40030 // lq s4, 0x30(sp)
patch=2,EE,000E1DC4,word,7BB50040 // lq s5, 0x40(sp)
patch=2,EE,000E1DC8,word,7BB60050 // lq s6, 0x50(sp)
patch=2,EE,000E1DCC,word,7BB70060 // lq s7, 0x60(sp)
patch=2,EE,000E1DD0,word,03E00008 // jr ra
patch=2,EE,000E1DD4,word,27BD0080 // addiu sp, sp, 128
patch=0,EE,000E1E00,word,FFFFFF34 // X2 do-not-take row 1: level52 (M15): every squad member (C2/C3 scatter them, m6_missions.md M15) (startup only)
patch=0,EE,000E1E04,word,00010137 // X2 do-not-take row 2: level55 (M17) cp <= 1: Cochise (name index 1; kiss-trap bait, 08403:215-218) (startup only)
patch=0,EE,000E1E08,word,00050209 // X2 do-not-take row 3: level9 (M13) cp <= 2: Fox (name index 5; HuDelete(fox) 09720:157, 09721:159) (startup only)
patch=0,EE,000E1E0C,word,00000000 // X2 do-not-take table end (startup only)
```

### `mod/m2/spawn_leave.txt` (`[warriors-4p 4p spawn leave]`): changed line and appended X5 block
```
patch=2,EE,000E1248,word,0C0384A4 // [warriors-4p 4p spawn leave] X5: jal 0x000E1290 X5EV (pnach had 0C106C52 jal 0x0041B148 leave event); delay slot nop kept
// X5 (m6_missions.md section 2): no Lua leave event for player index >= 2 on any path. LEAVEHOOK's event call
// (0x000E1248) goes through X5EV: called from the game's leave loop (return address 0x0041A870, s3 = index of the
// released player) it skips the event for index >= 2; from the session LEAVE cave (index 0-1 only) it runs it.
patch=2,EE,000E1290,word,8FA80000 // X5EV: lw t0, 0x0(sp)  ; X5EV(GameMgr, human, 0): LEAVEHOOK's saved ra = its return address
patch=2,EE,000E1294,word,3C090041 // lui t1, 0x0041
patch=2,EE,000E1298,word,3529A870 // ori t1, t1, 0xA870  ; return address of the game's leave loop call 0x0041A868
patch=2,EE,000E129C,word,15090003 // bne t0, t1, 0x000E12AC  ; other caller (session LEAVE: index 0-1 only): event as before
patch=2,EE,000E12A0,word,2A680002 // slti t0, s3, 2  ; game leave loop: s3 = index of the released player
patch=2,EE,000E12A4,word,11000003 // beq t0, zero, 0x000E12B4  ; index >= 2: no Lua leave event (missions expect player 2)
patch=2,EE,000E12A8,word,00000000 // nop
patch=2,EE,000E12AC,word,08106C52 // x5_ev: j 0x0041B148  ; FUN_0041B148 (the replaced call), returns to LEAVEHOOK
patch=2,EE,000E12B0,word,00000000 // nop
patch=2,EE,000E12B4,word,03E00008 // x5_skip: jr ra
patch=2,EE,000E12B8,word,0000102D // daddu v0, zero, zero
```

### `mod/m2/inventory.txt` (`[warriors-4p 4p inventory]`): Block B replaced by X8
```
// Block B, X8 (m6_missions.md 5.3, F-0158): at mission end clear the money and items of slots 2-3 (players 3-4), live and
// checkpoint copy, instead of banking them - parity with players 1-2, whose money UnlockAndLoad/LiquidizeAssets
// (WAD 4106) sets to 0 before FUN_0015D160 banks slots 0-1. s0 = GameMgr+0x480 at 0x0015D3F4 (set at 0x0015D3DC).
// Replaces the earlier Block B (bank += money of slots 2-3).
patch=2,EE,0015D3F4,word,0C039400 // was 0C0554C2 jal 0x00155308 -> jal 0x000E5000 (cave X8, then j 0x00155308)
patch=2,EE,000E5000,word,27BDFFF0 // X8: addiu sp, sp, -16  ; X8: mission end, after slots 0-1 were banked (0x0015D3B0-0x0015D3F0)
patch=2,EE,000E5004,word,FFBF0000 // sd ra, 0x0(sp)
patch=2,EE,000E5008,word,0200202D // daddu a0, s0, zero  ; s0 = Inv = GameMgr+0x480 (0x0015D3DC)
patch=2,EE,000E500C,word,0C107B18 // jal 0x0041EC60  ; InvReleaseSlot(Inv, 2): slot 2 counts 0, live and checkpoint copy
patch=2,EE,000E5010,word,24050002 // addiu a1, zero, 2
patch=2,EE,000E5014,word,0200202D // daddu a0, s0, zero
patch=2,EE,000E5018,word,0C107B18 // jal 0x0041EC60  ; InvReleaseSlot(Inv, 3)
patch=2,EE,000E501C,word,24050003 // addiu a1, zero, 3
patch=2,EE,000E5020,word,DFBF0000 // ld ra, 0x0(sp)
patch=2,EE,000E5024,word,080554C2 // j 0x00155308  ; the replaced call (save sequence core), returns to 0x0015D3FC
patch=2,EE,000E5028,word,27BD0010 // addiu sp, sp, 16
```

## 5. Tests (SINGLE-PC, one instance each, scripted bots, no impairment)
Common: `python -I tests/m2/nav_probe.py <tag> <p1 script> --inst N --players 4 --script2 tests/m2/nav/p2_join.txt
--script3 local/m6/start_p3.txt --script4 local/m6/start_p4.txt --groups "<groups as above>" --patch <pnach> --ini
EmuCore/Speedhacks/vuThread=false --callat "4000:0041ABC0:<cp>,4010:00160D78:<entry>"` (instances 10-13; `start_p3/p4`
press Start every 300 polls from 7000/7150 = join and re-join, standing in for W4P X11). Probes: `tests/m2/m6fix_probe.py`
(new; `snap`, `brief`, `squad`, `w4p_humans` read-only; test aids through PINE and the test-call mailbox). Results:
`local/m2/<tag>/probes.json`, emulator log copied to `local/m2/<tag>/emulog.txt` (**0 "TLB Miss" lines in every run
below**). Pad owners are listed as pad -> game player index (pad 0 = P1, pad 4 = P2, pads 1/2 = W4P slots 2/3).

| Tag | Setup | What was done | Result | Label |
|---|---|---|---|---|
| m6x1b | M13 cp1 (entry 0x01FD9F9C), dev.pnach, X2's level9 Fox row turned off at poll 6000 (test aid) so P3 = Fox as in the M2 runs | joins 4/4 by 8800 (P3 = Fox index 2 pad 2, P4 = W4P Swan index 3 pad 1); player 1 teleported to vbCutscene2 (9200, no trigger) and to the flag fArrive {64, 314.3, 2.9} (9600) -> trainyard scene (cinematic flag 3 at 9608) -> `ch1.StartTheLevel` -> script `HuDelete(fox)` | 9751: count 4 -> 3, Fox's handle gone, the W4P Swan moved to index 2 with **pad 1 -> 2**, pad 2 -> -1, 3 cameras / 3 views; 9903: player re-joined by Start on pad 2 -> index 3 (pad 2 -> 3), 4 cameras / 4 views; played on to 13604 | **VERIFIED** X1 (HuDelete path) |
| m6x1orig | same, WITHOUT `[warriors-4p missions]` | same script trigger | 9803: count 3 but **pad 1 still -> 3** (its player is index 2 now), the index-3 camera stayed and index 2's camera still follows the deleted Fox: 4 cameras / 4 views for 3 players; after the re-join (9901) **pads 1 and 2 both -> 3**. No crash, no TLB miss | **FAILED TEST (original game)**: the defect X1 removes (same class as run C, session_policies 3.3) |
| m6x1 | M13 cp1, dev_x5cnt.pnach, Fox row off | 12500: new type-0 gang (GangCreate core FUN_0016A1C8), player index 3 (W4P Swan, prio 7, pinned) moved into it (FUN_0016A3F8), GangDelete core FUN_0016A1E8 | count 4 -> 3, index 3 handle invalid, pad 1 -> -1, 3 cameras/views, **PIN_ID 5 -> 0** (released), the human no longer resolves (deleted once, by the gang cleanup); re-join by 12700 (count 4) | **VERIFIED** X1 gang path incl. the prio-7 case |
| m6x1 | same run | 14200: the game's own drop-out (FUN_00419AC0(GM, 0) + UpdateJoin(GM, -1) = leave loop) with 4 players | X5 counters: **event 1, skip 1** (index 1 = Snow: event; then index 2 = the W4P Warrior that had moved down: skipped); count 4 -> 2 (Fox stays, now index 1, because the original loop skips one index after each compaction), views 1, pads 4 -> 1 and 2 -> 2 stale (Fox is index 1 on pad 2). The resulting state is the original leave loop's behaviour with > 2 players; this path is not reachable in sessions (session S3/S4 remove the menu item) | **VERIFIED** X5 decision; original loop defect noted |
| m6x2m14a / m6x2m14b | M14 cp1 (entry 0x01FDA020, level 51), a = dev.pnach (X2), b = dev_nox2.pnach (original picker) | joins by Start | **b:** P3 = spawned Swan clone (at his join the fallback found no candidate), **P4 = Ajax char 12, prio 0, gang id 4, type 0 - the suspended pit-fight Ajax that `StartToRun`/`AddWarrSplit02` creates (08181 main_5; gang name HYPOTHESIS) - taken by the fallback scan**. **a:** P3 and P4 = spawned Warriors (char 5, prio 7, player 1's gang); the pit-fight Ajax stays AI in gang 4 (squad probe: the original picker would return him via the fallback) | **VERIFIED** X2 (hazard reproduced and removed) |
| m6x2 | M6 cp2 (entry 0x01FD9C00, level 3), dev.pnach | joins by 7600 | P3 = Snow (34, prio 0), P4 = Cowboy (19, prio 0) - the same members the original picker takes; squad probe: a 5th join would have reached the fallback and taken the civilian Scopes (char 425, gang 4) | VERIFIED X2 keeps the in-gang choice; **correction:** the M6 cp2 squad has two free companions (Snow 34 and Cowboy 19), not one |
| m6x2m9a / m6x2m9b | M9 cp1 (0x01FD9D8C, level 86), a = X2, b = original | joins at about 7000/7400 | identical: P3 = Vermin (27, prio 0), P4 = spawned Warrior char 11 (Ajax through the pin); no other type-0 AI human existed at that time | VERIFIED (no difference expected; regression of the normal path) |
| m6x2m16a / m6x2m16b | M16 cp1 (0x01FDA128, level 54) | Start presses from 7000 to 12000 | **no drop-in in either run** (count 2, views 1 throughout); squad probe: the original picker would take the AltWar cowboy (char 19, gang 1, god-mode chase NPC) by the fallback | X2 not exercised here; VERIFIED that M16 cp1 refuses drop-in for at least 5000 polls (rail camera, HYPOTHESIS) |
| m6x3m18 | M18 cp4 (0x01FDA230, SetCheckPoint(4)), dev.pnach, 1300 s | idle player 1; P3/P4 Start every 300 polls | 7100/7400: P3/P4 joined during the credits fight (W4P Warriors, char 5 and 11); 8000: after the script's `HuChangePlayerGang(GangRiff01, true)` P1 = RiffBoss (64), P2 = Riff01 (73) and P3 re-joined; 8300: count 4; pads consistent (1 -> 2, 2 -> 3); 17000: mission complete (checkpoint 11, players 0, loading), then the save-sequence mode 0x005E5810 to the end (37406) | VERIFIED: no crash through both script swaps (the second, `FinishMissionNow` `HuChangePlayerGang(GangWarriors)` with 4 players, was not sampled: HYPOTHESIS that X3 released 3 and 2 there) |
| m6x3m18b | same, 480 s, probe `w4p_humans` every 100 polls | first swap | 7300: 4 players (W4P Warriors 0x1bc idx 2, 0x101c1 idx 3); **7800: count 2, pads 1 and 2 -> -1, both W4P Warriors AI (idx -1) and PIN_ID 11 -> 0** (LEAVE -> LV -> DESPAWN/RELEASE); 7900: both gone (deleted), P3 re-joined (spawned clone of the RiffBoss in GangRiff01); 8100: count 4 | **VERIFIED** X3 |
| m6x3m18orig | same, WITHOUT `[warriors-4p missions]` | first swap | 7900: count 4: P1 RiffBoss, P2 Riff01, **P3 = Swan (char 5, the just-released player-1 human), P4 = Snow (char 33)** - picked by FUN_00239B80's PickJoinCompanion fallback scan (GangRiff01 has no AI member); the two W4P Warriors stay as AI humans (prio 7, idx -1) to the end of the run (8600) | **FAILED TEST (original game)**: what X3 prevents (m6_missions.md 1.4 prediction confirmed) |
| m6x8 | M13 cp1, dev.pnach | 9000 `inv_tests.t7_setup` (money 10/20/30/40 in slots 0-3), 9100 FUN_0015D420(4) (Lua HUDLaunchMissionComplete core) | 9300: bank 0 -> **0**, money of slots 0-3 = 0, checkpoint copy of slots 0-3 = 0 (0x000E4020..), checkpoint 10 set (hub); with the old Block B the bank became 70 (F-0158) | **VERIFIED** X8 |
| m6x7m13 | M13 cp1, dev2.pnach (X7) | joins; 9000 gang-delete test on index 3 (forced leave), re-join | 8800: spray of slots 2-3 **0 -> 6** (P1/P2 have 6 from the Lua script); after the forced leave slot 3 = 0 and the re-joined player 4 got **nothing** (first join per level load only) | **VERIFIED** X7 (+ side effect, section 6) |
| m6x7m3 | M3 cp1 (0x01FD9A74, level 87), dev2.pnach | joins | slots 2-3: **money 15, spray 1** at their joins (7000/7600); player 2 money 15, spray 0 (the cp1 script zeroes player 2's spray, `09171:4164`) | **VERIFIED** X7 (InvSetMoney for slots 2-3 with B1's T_A) |
| m6reg | M13 cp1, dev.pnach, `local/m6/rnd_p1..p4.txt` (seeded random walk/attack/grab from poll 9000; slots 3/4 also Start every 300 polls) | 4 players by 9002 (P3 = Rembrandt clone, P4 = Swan; Fox AI by the X2 table) | to poll 25181 (game clock 74.4 s at poll 8800, 449.0 s at poll 20000): count 4, views 4, pads 1 -> 3, 2 -> 2 unchanged in 28 samples; 0 TLB misses | **VERIFIED** regression (no crash, 5+ min) |

Not run: X3 inside a 4-instance lockstep session; X1/X3 with W4P X11 (auto re-join is the coordinator's fork change; the
tests used Start presses in the scripts); X1 in missions other than M13 (M2, M3, M7-M11, M16, M18 deletes); X2's level52
and level55 rows (table logic exercised by the level9 row only: m6x1b turned it off, m6reg/m6x8/m6x7m13 had it on and
player 3 was spawned while Fox stayed AI); X7 rows for levels 5, 51, 84 (Flash) not run; X5EV's other branch (player 2
leaving through the session LEAVE cave, return address 0x000E71CC -> event as before) not re-run after this change
(static only).

## 6. Findings and side effects
1. **Original HuDelete of a player-3 human (m6x1orig, VERIFIED runtime):** no crash; the cleanup's player branch
   (FUN_0021C7C8 -> RemovePlayer) compacts the player array, but pad owners and per-index cameras are not fixed: a
   moved player's pad keeps the old index, the deleted player's camera stays, and after a re-join two pads point at the
   same index. Supersedes the HYPOTHESIS "crash or dead slot" of m6_missions.md 1.4 / 8.1 for the HuDelete path.
   X1 (m6x1b) leaves consistent pad owners, cameras and views.
2. **Forced leave empties the inventory slot (VERIFIED m6x7m13):** LEAVE -> ReleasePlayer(h, 1, 1) -> InvReleaseSlot
   clears the slot (slot 3 spray 6 -> 0), and X7 does not give the starting items again on the re-join (parity rule).
   So a player whom a script deletes (X1) or swaps (X3) loses his items. Options for the user: (a) accept (parity with
   the game's own drop-out); (b) give the X7 items again after a forced leave (clear the slot's X7 byte in REL34/X3W);
   (c) keep the items across the forced leave (needs a "release without inventory" variant of LEAVE). Recommendation (b)
   as the cheap middle ground; nothing implemented.
3. **Duplicate Fox risk (VERIFIED m6x1b):** after `HuDelete(fox)` the re-joining player was spawned as **Fox** (char 21;
   CHOOSE finds Fox's model resident and Fox absent). Mission 13 ch2 re-creates Fox (`AddFoxMid`, `AddFox`,
   09721:40-42/247-270) -> two Foxes (HYPOTHESIS, ch2 not reached). Possible fix: CHOOSE skips Fox in level 9 cp 1-2
   (per-level CHOOSE order, X9).
4. **Pin moved away from a Warrior in use (VERIFIED m6x1b):** at that re-join ENSURE pinned Fox (PIN_ID 5 -> 21) and
   released Swan's pin while the W4P Swan (player 3) was still playing. HYPOTHESIS: Swan's body may be streamed out later
   (R-28). Spawn-group logic (m2_extra_model.md 4.2), not changed here.
5. **Mission 16 cp1 refuses drop-in (VERIFIED m6x2m16a/b, polls 7000-12000):** views 1, count 2, every Start ignored
   (camera type test of FUN_00158728, HYPOTHESIS). Players 3-4 cannot join at the start of M16 at all; the fallback
   hazard there (AltWar cowboy/ajax) is therefore not reachable by Start in that stretch.
6. **Mission 18 cp4:** players 3-4 can join during the credits fight; GangRiff01 has no AI member then, so X2 spawns
   a clone of the RiffBoss (char 64) for player 3 and, for player 4, Ajax (char 11, extra-model pin) inside the Riff
   gang (cosmetic).
7. After mission complete in the sandbox the game stayed in the save-sequence mode 0x005E5810 (m6x8: polls 9300-12500;
   m6x3m18: 17300-37406, player 1 idle); the next level was not loaded within the runs. Not caused by X8 (the X8 cave
   tail-jumps to the same 0x00155308); HYPOTHESIS: the memory-card save prompt waits for input.
8. M6 cp2 squad correction (m6x2) and M9 cp1 join timing (m6x2m9a/b) as in the table.
9. **Original HuChangePlayerGang with 4 players (m6x3m18orig, VERIFIED runtime):** FUN_00239B80 released all four
   players, re-made players 1-2 from the target gang and gave the two remaining seats, through PickJoinCompanion's
   fallback scan, to the just-released Warriors Swan and Snow (players 3-4 become the story's player 1/2 characters
   inside the Riff fight), while the two W4P-added Warriors were left in the level as AI humans (+0x1B1 = 7, still
   there at the end of the run, poll 8600). With X3 the W4P Warriors are deleted by LV and players 3-4 re-join cleanly (m6x3m18b).

## 7. Open points
- X3's second call in M18 (`FinishMissionNow`) not sampled; the scripted swaps in M1, M6, M8, M14, M16, M17 not
  reached; X1 not tested in the other deleting missions.
- 4-instance lockstep test of X1/X2/X3/X7/X8 (all run inside synchronised game code: a script call, the join on a
  synchronised Start, the mission end; HYPOTHESIS: deterministic like the rest of the game thread).
- Decision for the user on finding 2 (items after a forced leave) and on finding 3 (Fox in CHOOSE).
- `docs/STATE.md` RAM map and test groups need `[warriors-4p missions]` and the new ranges (not edited here); the
  coordinator regenerates `mod/w4p_m1.pnach` after the smoke batch.

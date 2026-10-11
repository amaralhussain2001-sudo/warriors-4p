# M2/M6 research: spawning an extra Warrior so players 3-4 can join (D7 "add" case)

Static analysis only (SLUS-21215 v1.03, `local/disc/SLUS_212.15`, decompile `local/analysis/all/*.c`, pseudo-Lua
`local/analysis/pseudo/`). Nothing was run in an emulator; every runtime effect below is HYPOTHESIS until tested.
Function names are OUR labels. Cave words were assembled with a scratch encoder and compared with the game's own
encodings of the same instructions; `tools/note_patches.py check` with the current `mod/w4p_m1.pnach` (both HUD
alternatives, all other groups included) reports **0 problems** (1,007 and 1,574 addresses).

## Summary
- Lua `HuCreate(name, char, {x,y,z}, angle, str, joinprio, gang [, flag])` is binding 0x00358428; its core is
  **`HuCreateCore` FUN_00233D60** with a non-standard argument layout (f12 = angle, a0 = name, a1 = char id,
  a2 = pointer to 3 floats, a3 = ignored, t0 = join priority, t1 = gang id, t2 = flag). It allocates a human, runs the
  full human init (model, brain, **adds it to the gang**), stores the join priority at human+0x1B1 and returns the
  handle. VERIFIED (disassembly 0x00358540-0x0035855C, 0x00233D60-0x00233EE8).
- Player 1's squad **is a gang**: brain(P1)+0x20C = gang object (0x005E6E30 + id*0xB10), gang id = s16 at gang+0x30.
  Spawning with player 1's gang id puts the new human straight into the list PickJoinCompanion walks. VERIFIED.
- Models: the safe choice is to **clone player 1's own character id** (human+0xD0); its model is resident by
  construction. Other char ids only work if their model is loaded in that level (HYPOTHESIS; check per mission).
- Proposal: one pnach group (104 code words + 4 data words, free RAM 0x000E1000-0x000E1213, not used by any group):
  - **Join hook:** the PickJoinCompanion call in the drop-in (0x0041A52C) goes to a cave. When the original picker
    finds nobody, the pad is a real Start press and 2 <= count < 4, the cave spawns a Warrior next to player 1 (clone
    of player 1, priority 7 = "W4P-added" marker) and returns it, so the game's own MakePlayer/camera/layout path makes
    it player 3 or 4. Deterministic in lockstep (it runs inside game code, triggered by a synchronised Start press).
  - **`SPAWN(char, prio)` at 0x000E1080**, also callable with W4P CallAt for tests.
  - **`DESPAWN(handle)` at 0x000E1180**: deletes a W4P-added Warrior (HuDelete core) only when it is AI again.
  - Optional **leave hook** (0x0041A868, 21 words): after the game's own leave path has released a drop-in player,
    a W4P-added Warrior is deleted (D7 "removed again when that player leaves").

## 1. HuCreate (VERIFIED)
Binding FUN_00358428 (Lua name string at 0x00579328) reads arg1 string, arg2 number -> int, arg4 number -> float,
arg5 string, arg6 -> int, arg7 -> int, arg8 boolean, arg3 table of 3 numbers -> floats on its stack, then calls the
core (0x00358540-0x0035855C):

| Register | Value | Use in FUN_00233D60 |
|---|---|---|
| f12 | angle in degrees (arg4) | heading quaternion (`* 0.017453294 * 0.5`, sin/cos) |
| a0 | name string (arg1) | FUN_0021CDA8 copies <= 15 chars to human+0x80 |
| a1 | character id (arg2) | FUN_00218008 (human init) |
| a2 | pointer to x, y, z floats (arg3) | position (only 3 floats read, 0x00233DD0-0x00233DD8) |
| a3 | string (arg5, e.g. "warr_sw") | **never read** (a3 is overwritten at 0x00233E74) |
| t0 | join priority / slot (arg6) | `sb` to human+0x1B1 (0x00233E94); slot 1 -> immediate MakePlayer |
| t1 | gang id (arg7) | FUN_00218008 -> FUN_00166308(gang(id), human) (decompile all_02.c, FUN_00218008 middle) |
| t2 | flag (arg8) | human+0x19D (brain type 2 when set); Warriors scripts pass nil = 0 |

Return: the handle (vtable +0x2C, 0x00233EAC-0x00233EB8), or the invalid handle `*(u32*)0x006EBD30` when no human
could be allocated (FUN_00217F08 returned 0; FUN_00217EC8 debug dump; 0x00233E54-0x00233E64).
Allocation: FUN_00217F08 -> FUN_0038FE88 (object slot); human = 0x00640C80 + slot*0x6D0.

Character ids are per variant (e.g. Fox 21-24, Cleon 1-4, Snow 33/34). FUN_00218008 maps variants to a base id and
keeps the **original id at human+0xD0** (`param_1[0x34] = param_2`) and the base id at human+0xCC. VERIFIED.

Mission 13 (level9, `pseudo/09229_c05eacb5.lua`): `GangWarriors1 = GangCreate(0, "Warriors1", 0, 0)` with Rembrandt
(char 30, priority 1), Snow (33, priority 2) and Fox (22, priority 3); Cleon (char 2) is in a separate gang
(`GangCreate(0, "Cleon", 0, 1)`). VERIFIED (script text). This matches the runtime squad (players 1-2 and Fox) at
0x005E6E30 seen in the parent session.

## 2. Gangs and squads (VERIFIED)
- Gang object = `FUN_0016C388(id)` = 0x005E6E30 + id*0xB10: +0x2C gang type (GangCreate arg 1; Warriors gangs use 0),
  +0x30 s16 id, +0x44 leader handle, +0x48 member handle list (16 slots).
- A human's gang: brain = `FUN_0021D408(human)` = 0x006D53F0 + human[+0x92, s16]*0x2F0; brain+0x20C = gang object.
- `GangAddMember` (binding 0x00373528) -> FUN_0016A3F8(gang id, ?, handle) -> **FUN_00166308(gang, human)**: removes
  the human from its old gang, sets brain+0x20C, appends the handle to gang+0x48 (limit 10; 16 for gang types 1 and
  0x17). An existing Warrior can therefore also be moved into player 1's squad instead of spawning one.
- PickJoinCompanion FUN_0022A770(gang, 0): AI members (+0x1B0 == -1) of that gang, lowest non-zero +0x1B1 first;
  fallback (not level 99, GameMgr+0x158 == 0) scans 60 objects for AI humans in a gang of type 0. In Mission 13 no
  candidate was left after Fox joined (runtime, parent session).
- On humans, +0x1B1 is written only by HuCreateCore, FUN_002398B0 (swaps it between two humans) and FUN_0021C7C8
  (cleared on death/cleanup), and read only by PickJoinCompanion. VERIFIED (exhaustive scan of `lb/lbu/sb` with
  offset 0x1B1; the other hits are HUD objects). A value of 7 is therefore usable as a "W4P-added" marker.

## 3. Models (VERIFIED mechanism, HYPOTHESIS residency)
- `CfgChar(id, ..., model, ...)` (core FUN_00228AF8) fills the character table 0x00684620 + id*0x1AC. The model name
  (arg 10, e.g. "warr_cl") is looked up in the model dictionary `*(0x0050CD4C)` (FUN_001780E8; -1 if the name is
  not in it) and stored as s16 at +0x112; "<name>_a" goes to +0x114.
- FUN_00218008 puts the chosen model index at human+0x37C; draw paths check the model's load state with
  FUN_001774D0(dict, FUN_001780D8(dict, index), 0, 0).
- HYPOTHESIS: the loaded set is per level/checkpoint, so a char id whose model is not loaded may fail or render
  nothing. **Cloning player 1's char id (human+0xD0) takes the same model branch as player 1** (both have a join
  priority >= 1, the `param_5 < 1` test in FUN_00218008), so the model is resident by construction.
- Visual side effect: the added Warrior looks like player 1 (a second Rembrandt in Mission 13). A per-mission table of
  resident named Warriors (e.g. Cleon, char 2, in Mission 13 if his model is loaded at that checkpoint) can replace the
  clone later (M6) through `SPAWN(char, 7)`.

## 4. Removal (VERIFIED code, HYPOTHESIS effects)
- `HuDelete` (binding 0x00358608) -> **FUN_00233EF0(handle)**: resolves the handle, sets flag 0x200000000
  (FUN_002265D0), FUN_002267C8, vtable +0x3C, FUN_003858B8 (destroy). `HuKill` -> FUN_00237E70 -> FUN_002302A8.
- A player-owned human must be released first (ReleasePlayer FUN_0022A2A8, done by the game's leave path in
  FUN_0041A460 or later by the W4P session layer). DESPAWN refuses humans with +0x1B0 >= 0.

## 5. Proposal: `[warriors-4p 4p spawn]` (+ optional `[warriors-4p 4p spawn leave]`)
Free RAM 0x000E1000-0x000E12FF (low RAM 0x96000-0xEFFFF stayed zero at runtime, F-0125; the current pnach uses only
0x000E0010-0x000E0A57 in that area). Data words are written once at startup (place 0).

### 5.1 Join hook (0x0041A52C in GameMgr::UpdateJoin, FUN_0041A460)
Original (VERIFIED): `0x0041A528 lw a0,0x20C(v0)` (player 1's gang), `0x0041A52C jal 0x0022A770`,
`0x0041A530 daddu a1,zero,zero`, `0x0041A534 daddu s0,v0,zero`. Here s2 = pad argument (-1 for the level-start and
script calls) and s3 = player count at entry (VERIFIED at 0x0041A4F8, 0x0041A540, 0x0041A5A4).

`SPAWNPICK` (0x000E1000) calls the original picker. If it returns 0 **and** s2 >= 0 **and** 2 <= s3 < 4, it calls
`SPAWN(-1, 7)` and returns the new human (or 0). Every other case returns the original result, so players 1-2 and the
level-start path are unchanged. The join then continues in the game's own code (MakePlayer with that pad, camera,
layout; the join script event is already skipped for index >= 2 by the existing guard).

### 5.2 `SPAWN(a0 = char id or -1, a1 = join priority)` (0x000E1080)
1. Player 1 = FUN_00390268(GameMgr+0x228), GameMgr = `*(0x0051489C)`; fail if 0.
2. char = a0, or player 1's original char id (human+0xD0) when a0 < 0.
3. position = player 1's +0x10/+0x14/+0x18 with x + 1.5.
4. gang id = s16 at (brain(P1)+0x20C)+0x30.
5. FUN_00233D60(f12 = 0.0, a0 = "W4PAdded" at 0x000E1200, a1 = char, a2 = &pos, a3 = 0, t0 = prio, t1 = gang,
   t2 = 0). The handle is also stored at 0x000E1210.
6. Returns the human pointer, or 0 if the handle equals the invalid handle `*(0x006EBD30)`.

Test use without the join hook (W4P CallAt, needs the "test call" group): `CallAt = <poll>:000E1080:0xFFFFFFFF:7`,
then a Start press on pad 1 or 2 joins it through the normal picker (lowest non-zero priority first, so the mission's
own companions with priority 1-4 are still taken first).

### 5.3 `DESPAWN(a0 = handle, 0 = last spawned)` (0x000E1180)
Resolves the handle and deletes it with FUN_00233EF0 only if +0x1B0 < 0 (AI) and +0x1B1 == 7 (added by W4P).
CallAt use: `CallAt = <poll>:000E1180:0`.

### 5.4 Optional leave hook (0x0041A868)
In the leave loop of FUN_0041A460 (0x0041A7D8-0x0041A890; s0 = the released human), `jal 0x0041B148` (leave script
event) goes to `LEAVEHOOK` (0x000E1240): it calls the event, then, if s0+0x1B1 == 7, gets s0's handle (vtable +0x2C)
and calls DESPAWN. The loop does not use s0 after the event (VERIFIED 0x0041A870-0x0041A890).

## 6. Risks and runtime checks
- HYPOTHESIS: creating a human from inside UpdateJoin (game update, pad loop) is as safe as a Lua HuCreate during the
  update. Check: no TLB miss, count 3/4, a new handle at 0x000E1210.
- Spawn position: player 1 + 1.5 on x may be inside a wall; the game's collision should push the human out
  (HYPOTHESIS). `HuTeleportNearHuman` (binding 0x0035B480 -> FUN_0023B138(h1, h2)) is an alternative placement call.
- Checkpoint reloads and level changes rebuild the level's humans; W4P-added humans are then gone and players 3-4
  must re-join or be re-created (not analysed).
- FUN_002398B0 swaps +0x1B1 between two humans when the game swaps players, so the marker could move (HYPOTHESIS,
  rare).
- Gang capacity is 10 for Warriors gangs; Mission 13's gang holds 3, so two added Warriors fit.
- Duplicate look (clone of player 1) until a per-mission table of resident Warriors exists.
- PINE checks after a Start press on pad 1 with no free companion: `*(0x000E1210)` != 0; the resolved human has
  +0x1B1 == 7, +0x1B0 == 2, brain+0x20C == player 1's gang, +0xD0 == player 1's +0xD0; GameMgr+0x224 == 3; pad 1
  owner (0x005DD810 + 0x50 + 0x42) == 2. After DESPAWN of an AI copy, the handle no longer resolves.

## Appendix A: fragment `[warriors-4p 4p spawn]` (checked: 0 problems with the current pnach)
```
// [warriors-4p 4p spawn] join hook: when PickJoinCompanion finds nobody for player 3-4, spawn a Warrior
patch=2,EE,0041A52C,word,0C038400 // was 0C08A9DC jal 0x0022A770 (PickJoinCompanion) -> jal 0x000E1000 SPAWNPICK; delay slot daddu a1,zero,zero kept
patch=2,EE,000E1000,word,27BDFFF0 // addiu sp,sp,-16
patch=2,EE,000E1004,word,AFBF0000 // sw ra,0(sp)
patch=2,EE,000E1008,word,0C08A9DC // jal 0x0022A770
patch=2,EE,000E100C,word,00000000 // nop
patch=2,EE,000E1010,word,1440000C // bne v0,zero,pick_done
patch=2,EE,000E1014,word,00000000 // nop
patch=2,EE,000E1018,word,0640000A // bltz s2,pick_done
patch=2,EE,000E101C,word,00000000 // nop
patch=2,EE,000E1020,word,2A610002 // slti at,s3,2
patch=2,EE,000E1024,word,14200007 // bne at,zero,pick_done
patch=2,EE,000E1028,word,00000000 // nop
patch=2,EE,000E102C,word,2A610004 // slti at,s3,4
patch=2,EE,000E1030,word,10200004 // beq at,zero,pick_done
patch=2,EE,000E1034,word,00000000 // nop
patch=2,EE,000E1038,word,2404FFFF // addiu a0,zero,-1
patch=2,EE,000E103C,word,0C038420 // jal 0x000E1080
patch=2,EE,000E1040,word,24050007 // addiu a1,zero,7
patch=2,EE,000E1044,word,8FBF0000 // lw ra,0(sp)
patch=2,EE,000E1048,word,03E00008 // jr ra
patch=2,EE,000E104C,word,27BD0010 // addiu sp,sp,16
patch=2,EE,000E1080,word,27BDFFA0 // addiu sp,sp,-96
patch=2,EE,000E1084,word,AFBF0018 // sw ra,24(sp)
patch=2,EE,000E1088,word,7FB00020 // sq s0,32(sp)
patch=2,EE,000E108C,word,7FB10030 // sq s1,48(sp)
patch=2,EE,000E1090,word,7FB20040 // sq s2,64(sp)
patch=2,EE,000E1094,word,0080882D // move s1,a0
patch=2,EE,000E1098,word,00A0902D // move s2,a1
patch=2,EE,000E109C,word,3C020051 // lui v0,0x0051
patch=2,EE,000E10A0,word,8C44489C // lw a0,0x489c(v0)
patch=2,EE,000E10A4,word,0C0E409A // jal 0x00390268
patch=2,EE,000E10A8,word,24840228 // addiu a0,a0,0x228
patch=2,EE,000E10AC,word,10400027 // beq v0,zero,sp_fail
patch=2,EE,000E10B0,word,0040802D // move s0,v0
patch=2,EE,000E10B4,word,06210002 // bgez s1,sp_char
patch=2,EE,000E10B8,word,00000000 // nop
patch=2,EE,000E10BC,word,8E1100D0 // lw s1,0xd0(s0)
patch=2,EE,000E10C0,word,C6000010 // lwc1 f0,0x10(s0)
patch=2,EE,000E10C4,word,C6010014 // lwc1 f1,0x14(s0)
patch=2,EE,000E10C8,word,C6020018 // lwc1 f2,0x18(s0)
patch=2,EE,000E10CC,word,3C013FC0 // lui at,0x3fc0
patch=2,EE,000E10D0,word,44811800 // mtc1 at,f3
patch=2,EE,000E10D4,word,46030000 // add.s f0,f0,f3
patch=2,EE,000E10D8,word,E7A00000 // swc1 f0,0(sp)
patch=2,EE,000E10DC,word,E7A10004 // swc1 f1,4(sp)
patch=2,EE,000E10E0,word,E7A20008 // swc1 f2,8(sp)
patch=2,EE,000E10E4,word,0C087502 // jal 0x0021d408
patch=2,EE,000E10E8,word,0200202D // move a0,s0
patch=2,EE,000E10EC,word,8C43020C // lw v1,0x20c(v0)
patch=2,EE,000E10F0,word,10600016 // beq v1,zero,sp_fail
patch=2,EE,000E10F4,word,00000000 // nop
patch=2,EE,000E10F8,word,84690030 // lh t1,0x30(v1)
patch=2,EE,000E10FC,word,3C04000E // lui a0,0x000E
patch=2,EE,000E1100,word,24841200 // addiu a0,a0,0x1200
patch=2,EE,000E1104,word,0220282D // move a1,s1
patch=2,EE,000E1108,word,03A0302D // move a2,sp
patch=2,EE,000E110C,word,0000382D // move a3,zero
patch=2,EE,000E1110,word,0240402D // move t0,s2
patch=2,EE,000E1114,word,0000502D // move t2,zero
patch=2,EE,000E1118,word,44806000 // mtc1 zero,f12
patch=2,EE,000E111C,word,0C08CF58 // jal 0x00233D60
patch=2,EE,000E1120,word,00000000 // nop
patch=2,EE,000E1124,word,3C03000E // lui v1,0x000E
patch=2,EE,000E1128,word,AC621210 // sw v0,0x1210(v1)
patch=2,EE,000E112C,word,3C01006F // lui at,0x006F
patch=2,EE,000E1130,word,8C21BD30 // lw at,-0x42d0(at)
patch=2,EE,000E1134,word,10410005 // beq v0,at,sp_fail
patch=2,EE,000E1138,word,AFA20010 // sw v0,16(sp)
patch=2,EE,000E113C,word,0C0E409A // jal 0x00390268
patch=2,EE,000E1140,word,27A40010 // addiu a0,sp,16
patch=2,EE,000E1144,word,10000002 // beq zero,zero,sp_out
patch=2,EE,000E1148,word,00000000 // nop
patch=2,EE,000E114C,word,0000102D // move v0,zero
patch=2,EE,000E1150,word,8FBF0018 // lw ra,24(sp)
patch=2,EE,000E1154,word,7BB00020 // lq s0,32(sp)
patch=2,EE,000E1158,word,7BB10030 // lq s1,48(sp)
patch=2,EE,000E115C,word,7BB20040 // lq s2,64(sp)
patch=2,EE,000E1160,word,03E00008 // jr ra
patch=2,EE,000E1164,word,27BD0060 // addiu sp,sp,96
patch=2,EE,000E1180,word,27BDFFE0 // addiu sp,sp,-32
patch=2,EE,000E1184,word,AFBF0010 // sw ra,16(sp)
patch=2,EE,000E1188,word,14800005 // bne a0,zero,ds_have
patch=2,EE,000E118C,word,00000000 // nop
patch=2,EE,000E1190,word,3C03000E // lui v1,0x000E
patch=2,EE,000E1194,word,8C641210 // lw a0,0x1210(v1)
patch=2,EE,000E1198,word,1080000F // beq a0,zero,ds_out
patch=2,EE,000E119C,word,00000000 // nop
patch=2,EE,000E11A0,word,AFA40000 // sw a0,0(sp)
patch=2,EE,000E11A4,word,0C0E409A // jal 0x00390268
patch=2,EE,000E11A8,word,03A0202D // move a0,sp
patch=2,EE,000E11AC,word,1040000A // beq v0,zero,ds_out
patch=2,EE,000E11B0,word,00000000 // nop
patch=2,EE,000E11B4,word,804301B0 // lb v1,0x1b0(v0)
patch=2,EE,000E11B8,word,04610007 // bgez v1,ds_out
patch=2,EE,000E11BC,word,00000000 // nop
patch=2,EE,000E11C0,word,804301B1 // lb v1,0x1b1(v0)
patch=2,EE,000E11C4,word,24010007 // addiu at,zero,7
patch=2,EE,000E11C8,word,14610003 // bne v1,at,ds_out
patch=2,EE,000E11CC,word,00000000 // nop
patch=2,EE,000E11D0,word,0C08CFBC // jal 0x00233EF0
patch=2,EE,000E11D4,word,8FA40000 // lw a0,0(sp)
patch=2,EE,000E11D8,word,8FBF0010 // lw ra,16(sp)
patch=2,EE,000E11DC,word,03E00008 // jr ra
patch=2,EE,000E11E0,word,27BD0020 // addiu sp,sp,32
patch=0,EE,000E1200,word,41503457 // name "W4PAdded" (startup only)
patch=0,EE,000E1204,word,64656464 // name "W4PAdded" (startup only)
patch=0,EE,000E1208,word,00000000 // name "W4PAdded" (startup only)
patch=0,EE,000E1210,word,00000000 // last spawned handle (0 = none; startup only)
```

## Appendix B: fragment `[warriors-4p 4p spawn leave]` (optional; checked: 0 problems)
```
// [warriors-4p 4p spawn leave] optional: delete a W4P-added Warrior after the game's own leave path released it
patch=2,EE,0041A868,word,0C038490 // was 0C106C52 jal 0x0041B148 (leave script event) -> jal 0x000E1240 LEAVEHOOK; delay slot sh v0,1110(s1) kept
patch=2,EE,000E1240,word,27BDFFF0 // addiu sp,sp,-16
patch=2,EE,000E1244,word,AFBF0000 // sw ra,0(sp)
patch=2,EE,000E1248,word,0C106C52 // jal 0x0041B148
patch=2,EE,000E124C,word,00000000 // nop
patch=2,EE,000E1250,word,820301B1 // lb v1,0x1b1(s0)
patch=2,EE,000E1254,word,24010007 // addiu at,zero,7
patch=2,EE,000E1258,word,14610008 // bne v1,at,lh_out
patch=2,EE,000E125C,word,00000000 // nop
patch=2,EE,000E1260,word,8E030000 // lw v1,0(s0)
patch=2,EE,000E1264,word,84640028 // lh a0,0x28(v1)
patch=2,EE,000E1268,word,8C62002C // lw v0,0x2c(v1)
patch=2,EE,000E126C,word,0040F809 // jalr ra,v0
patch=2,EE,000E1270,word,02042021 // addu a0,s0,a0
patch=2,EE,000E1274,word,0C038460 // jal 0x000E1180
patch=2,EE,000E1278,word,0040202D // move a0,v0
patch=2,EE,000E127C,word,8FBF0000 // lw ra,0(sp)
patch=2,EE,000E1280,word,03E00008 // jr ra
patch=2,EE,000E1284,word,27BD0010 // addiu sp,sp,16
```

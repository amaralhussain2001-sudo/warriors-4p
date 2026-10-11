# M2/M6 research: a different named Warrior (and HUD name) for an added player (static analysis, 2026-10-11)

Problem: when player 4 joins in Mission 13 (level9) and no companion is free, `SPAWN` (`[warriors-4p 4p spawn]`,
0x000E1080, `m2_spawn_companion.md` 5.2) clones player 1's character (char 30, Rembrandt). The added player then looks
like Rembrandt and its HUD panel says REMBRANDT (F-0131, screenshot). Goal: a different named Warrior with its own HUD
name, chosen deterministically, only if its model is resident and that Warrior is not already in the level.

Sources and conventions:
- **Static analysis only; nothing was run** (no emulator was started for this note). Build SLUS-21215 v1.03,
  `local/disc/SLUS_212.15` (read-only). Addresses are static (ELF) unless marked. Decompile
  `local/analysis/all/all_*.c`, callers `local/analysis/callers.pkl`, Lua bindings `local/analysis/lua_bindings.tsv`,
  pseudo-Lua `local/analysis/pseudo/`. Disassembly from a scratch R5900 disassembler (checked against the existing
  Ghidra listings, e.g. `listing_addplayer.txt` at 0x00419B10).
- Function names are OUR labels (the ELF is stripped). Labels: VERIFIED / HYPOTHESIS / FAILED TEST.
- The patch fragment (section 5) was assembled with a scratch encoder, every word was disassembled back, and 17
  encodings were compared with words the game itself uses (0 mismatches). `tools/note_patches.py check` results are in
  section 6.

## Summary
1. **The HUD name is a picture chosen from the human's base character id (human+0xCC), once, when the player is
   made.** MakePlayer calls `FUN_00229570(human)` (switch on +0xCC -> "HUD index" 0..11), passes the index to the HUD
   slot claim `FUN_001B2200`, which calls the PlayerHUD's vtable +0x34 = `FUN_0020DC98` ("Bind"). Bind turns the index
   into a sprite asset (0x1F..0x32) and builds 3 sprites (name + 2 shadows). Not human+0xD0, not the CfgChar identity
   (+0x118), not the name string at human+0x80. Not re-chosen per frame. VERIFIED (static); matches F-0131 (Fox shows
   FOX, the Rembrandt clone shows REMBRANDT).
2. **Residency check = exactly the human init's own test:** model index `*(u16*)(0x00684620 + id*0x1AC + 0x112)`
   (+0x114 in levels 60-64), must be below the dictionary count `*(dict+0x84)`, then
   `FUN_001774D0(dict, FUN_001780D8(dict, index), 0, 0) != 0`, dict = `*(0x0050CD4C)`. VERIFIED (0x00218428-0x00218480,
   FUN_00218008 end).
3. **Presence check:** humans live in object-table slots 0..59 (`*(0x006EBD38 + slot*8)`, 0 = free); compare
   `FUN_00229570(h)` with the candidate's HUD index. VERIFIED (allocator, game loops, cleanup).
4. **Chooser `CHOOSE` (88 words at 0x000E1400, table at 0x000E1580):** walks 9 named Warriors in a fixed order and takes
   the first that is configured, resident and not present; else player 1's char id (old behaviour). Only one word of
   `SPAWN` changes (0x000E10BC). Diagnostic words at 0x000E15C0-0x000E15F0 tell exactly why each candidate was
   rejected. Check: 0 problems (section 6).
5. **Open risk (HYPOTHESIS): in Mission 13 there may be no other resident Warrior model** (the level script creates only
   Rembrandt, Snow, Fox and Cleon-as-char-2). Then CHOOSE falls back to the clone and nothing changes. Test T0 (read-only
   PINE survey) answers this before anyone applies the patch; section 4.4 lists what to do if so.

---

## 1. Where the PlayerHUD name comes from (question 1)

### 1.1 Call chain (VERIFIED, disassembly)
| Step | Address | What it does |
|---|---|---|
| MakePlayer `FUN_00229C40` | `0x00229E5C jal 0x00229570` (a0 = human s1) | `s2 = FUN_00229570(human)` = HUD index |
| | `0x00229E90-0x00229EA4` (search) / `0x00229EB0-0x00229EC0` (fixed slot) | `FUN_001B2200(0x00600840, a1 = s2, a2 = slot)`; result stored in human+0x380 |
| HUD slot claim `FUN_001B2200` | `0x001B2288-0x001B229C` | `jalr` vtable +0x34 of the PlayerHUD with a1 = the HUD index (after Init if +0x4100 == 0 and Activate +0x24) |
| Bind `FUN_0020DC98` | `0x0020DCC4` | only if +0x4100 != 0 (initialised); frees the 3 old sprites (`FUN_001A1F10`), then `switch(index)` -> asset |
| | `0x0020DEF0`, `0x0020DF40`, `0x0020DF98` | `FUN_001A1DB8(element, ..., t1 = asset << 16, t2 = -1, ...)` on +0x3DE0 (colour 0x80000000), +0x3EE0 (0x80000000), +0x3CE0 (0xFF808080) |
| Element init `FUN_001A1DB8` | | `FUN_001A2910(element, t1)` stores element+0xC8 = asset<<16; `FUN_001A2918(element, -1)` builds the sprite from dictionary asset `*(u16*)(element+0xCA)` via `FUN_001828C0(*(0x0050CD4C), asset)` (= `*(dict+0x9044) + asset*8`) |

Our 4-player HUD (`[warriors-4p 4p hud B1]`, pnach lines with 0x00229E84 and 0x001B2220-0x001B22D0) lets slots 2-3 use
the same `FUN_001B2200`, so players 3-4 get their name the same way. VERIFIED (pnach text).

**Correction to `m2_hud_full.md` 1.1:** vtable +0x34 is listed there as "Bind(human)". Its argument is the HUD index
from `FUN_00229570`, not a human pointer (`FUN_0020DC98` switches on a1, 0x0020DD50 `sltiu v0,s2,22`). VERIFIED. (Not
edited in that note; flagged here.)

### 1.2 Which field selects it (VERIFIED)
`FUN_00229570` (0x00229570-0x00229618) is a pure leaf: it reads only human+0xCC (s32) and human+0x1B0 (s8) and writes
nothing. Jump table 0x0055BBC0 (index = id-1, 191 entries), decoded from the ELF:

| HUD index | Base ids (human+0xCC) | Bind asset (`lui s2,...`) | Warrior (CfgChar model) |
|---|---|---|---|
| 0 | 5, 7, 8, 9, 10 | 0x31 (switch default) | Swan (`warr_sw`) |
| 1 | 15, 17 | 0x22 | Cochise (`warr_co`) |
| 2 | 18, 20, 188 | 0x23 | Cowboy (`warr_cb`) |
| 3 | 11, 13, 14 | 0x1F | Ajax (`warr_aj`) |
| 4 | 30, 32 | 0x2F | Rembrandt (`warr_re`) |
| 5 | 21, 23, 24, 25 | 0x24 | Fox (`warr_fo`) |
| 6 | 26, 28, 29, 191 | 0x32 | Vermin (`warr_ve`) |
| 7 | 33, 35, 36, 37, 190 | 0x30 | Snow (`warr_sn`) |
| 8 | 1, 3, 4, 189 | 0x21 | Cleon (`warr_cl`) |
| 9 | 38, 39, 40 | 0x20 | `warr_ty` |
| 10 / 11 | 43, 44 / 45-48 | 0x2A-0x2E by GameMgr+0x120 | `warr_ma` / `warr_ly` |
| 12, or 20 + human+0x1B0 | every other id | 12 -> 0x31; 20 -> 0x25-0x29; 21 -> 0x2A-0x2E; 22/23 -> 0x31 | non-Warriors |

- **human+0xCC is the base id**: human init `FUN_00218008` writes the char id to both +0xCC and +0xD0 (0x00218130,
  0x0021813C), maps variants to a base id with the jump table 0x0055A590 (index id-2) and stores the base at +0xCC
  (0x00218484 `sw s2,204(s3)`). Base ids 1, 5, 11, 15, 18, 21, 26, 30, 33 map to themselves with no "variant" flag.
- **human+0xD0** (original id): not read by this chain.
- **CfgChar "identity"** (Lua argument 12 when the id is argument 1, e.g. 7 for `warr_re`): stored as s16 at char
  table +0x118 (`FUN_00228AF8` 0x00228B6C `sh t4,280(s6)`; binding `FUN_00383F38` passes Lua arg 12 in caller 16(sp)).
  The human init copies it to **human+0x3B0** (0x0021849C/0x002184BC), where it selects the voice folder
  `vags/character/voices/%d/l%d_c%d_idle_%2.2d` (0x0055A548). Not used by the HUD. Note the different order:
  identity Cleon 0, Swan 1, Ajax 2, Cochise 3, Cowboy 4, Fox 5, Vermin 6, Rembrandt 7, Snow 8.
- **human+0x80** (16-byte name, "W4PAdded" for our spawn; `FUN_0021CDA8`, Lua `HuSetName`): not read by this chain.
  HYPOTHESIS (not exhaustively checked): no HUD code reads it.
- The same HUD index is also used by `FUN_0019F988` and `FUN_001E5618` (another screen that draws the same assets
  0x1F..0x32 plus a text id 0xEA..0xF2); both call `FUN_00229570` themselves.

### 1.3 Once per claim, not per frame (VERIFIED static)
The sprite asset is written only through `FUN_001A2910` / `FUN_001A1DB8`. Among the normal-class PlayerHUD functions that
address the name elements (immediates 0x3CE0/0x3DE0/0x3EE0: `FUN_0020DBE0`, Bind, `FUN_00211938`, constructor
`FUN_00211CA0`, `FUN_00213290`, Update `FUN_00214138`), only Bind calls them; Update and its helpers (`FUN_00213770`,
`FUN_00213E68`) only position/draw (`FUN_001A2120`, `FUN_001A2648`, ...). The element draw `FUN_001A21E8` may re-create
a missing sprite, but from the stored asset id. So the name is fixed when `FUN_001B2200` runs (each MakePlayer), and a
human whose +0xCC is a different Warrior gets that Warrior's name with no HUD change at all.

Runtime agreement: F-0131 (screenshot) shows player 3 = Fox (char 22, base 21, index 5) as FOX and the clone of char 30
as REMBRANDT. VERIFIED for those two; HYPOTHESIS that assets 0x1F..0x32 show the other names as in the table and are
loaded in every level.

## 2. Is a candidate's model resident? (question 2)

### 2.1 Which model the human init uses (VERIFIED, 0x00218400-0x00218480)
| Join priority (HuCreateCore t0) and variant flag | Level 60-64 | Other levels |
|---|---|---|
| priority < 1, or flagged variant (e.g. 3, 4, 7-10, 13, 14, 20, 25, 32, 35-37) | table[original id]+0x114 | table[original id]+0x112 |
| priority >= 1 and not flagged | table[base id]+0x114 | table[base id]+0x112 |

Level number = `*(G + 0x14D4 + (u16)*(G+0x56DC) * 0x84 + 4)`, G = `*(0x0051489C)` (`FUN_004DAB58` = G+0x14D4,
`FUN_004DAB50` = lhu G+0x56DC). The index is read with `lhu` (u16) and stored at human+0x37C. For our candidates
(base ids, unflagged) both rows give **table[id]+0x112** (+0x114 in levels 60-64), whatever the priority.

### 2.2 Dictionary and load state (VERIFIED)
| Function | Meaning |
|---|---|
| `FUN_001780D0(dict)` | `*(dict+0x84)` = number of entries |
| `FUN_001780D8(dict, i)` | `*(dict+0x88) + i*0x20` = entry (keys at +4, +8, +0xC) |
| `FUN_001780E8(dict, name)` | hash the name, linear search; index or 0xFFFFFFFF (CfgChar stores it with `sh`, so "missing" = 0xFFFF) |
| `FUN_001774D0(dict, entry, a2, a3)` | read-only: lower_bound lookups (`FUN_004DE458/8D0/BE8`) of entry+4 in the tree at dict+0x40, entry+0xC in dict+0x30, entry+8 in dict+0; returns 1 if found (a2 != 0: only the first lookup), 0 otherwise; with a3 != 0 a found node also needs `*(*(node+0x14)+4) != 0`. Writes only its own stack. |

Human init (end of `FUN_00218008`): `e = FUN_001780D8(dict, +0x37C)`; if `FUN_001774D0(dict, e, 0, 0)` -> full model
`FUN_00177B80(dict, e, 0)` + `FUN_00217A98`; else if `FUN_001774D0(dict, e, 1, 0)` -> partial model (mode 1); else **no
model is built at all**. So the safe test for a spawn is the first one: same call, same arguments.

- The index must be range-checked first: 0xFFFF (name not in the dictionary) would make `FUN_001780D8` point far past
  the entry array. `FUN_001780E8` only returns values below the count, so `index < *(dict+0x84)` is the right test.
- Residency is dynamic: Lua `SetCharacterModel(id, 0/1)` (binding 0x0036E6C0 -> `FUN_0018AD40(dict, id, release)`)
  pins/unpins a char's model in a 32-entry list at dict+0xB4 and creates an instance if resident; the streamer
  `FUN_001897A8` requests loads (`FUN_00177B00`). `FUN_00177B80` increments the instance count (+8); HYPOTHESIS: the
  instance keeps the model resident while our human exists.
- The model *names* differ by config script: six scripts run `CfgChar` (`03767`, `03768`, `03769`, `03770`, `03772`,
  `03774`); all define ids 1, 5, 11, 15, 18, 21, 26, 30, 33 with the same ids, but `03768` uses `warr_xx_fury` models
  and `03774` has 600 health instead of 1800. The runtime check adapts to whichever ran. VERIFIED (script text).
- Sanity check used by CHOOSE: char table +0x116 (s16, CfgChar arg 6 = 1800/600; `sh t1,278(s6)` at 0x00228B68) is 0 for
  an id that was never configured.

## 3. Is that Warrior already in the level? (question 3, VERIFIED)
- Humans: `FUN_00217F08` -> `FUN_0038FE88` -> `FUN_0038FE28(0)` (first free object-table slot from 0) and refuses slots
  >= 60 (0x0038FE9C `slti v0,v1,60`); human = 0x00640C80 + slot*0x6D0, i.e. the pool 0x00640C80-0x0065A53F (60 humans;
  the next table at 0x0065A540 is the per-human 0x180 block used by the init). `FUN_0038FFD0` registers it in the object
  table **0x006EBD38 + slot*8** (+0 pointer, +4 s16 serial).
- Other object kinds allocate from slot 60, 108 or 620 (`FUN_0038FED8/EF8/F18`), so slots 0..59 hold only humans.
- The game's own loops do exactly this: PickJoinCompanion's fallback (`FUN_0022A770`, 0x0022A884-0x0022A90C, `uVar8`
  0..0x3B) and `FUN_00217EC8` use `FUN_003900B0(slot)` = `*(0x006EBD38 + slot*8)` (0 = empty).
- `FUN_00390038(handle)` clears the entry; it is called from the human cleanup `FUN_0021C7C8`.
- Presence test: some slot 0..59 with `h != 0` and `FUN_00229570(h) == HUD index of the candidate`. Using the HUD index
  (not raw +0xCC) also catches the alias ids 188-191 and every variant. It costs at most 60 leaf calls per candidate,
  once per join.

## 4. The chooser (question 4)

### 4.1 Candidates (ids VERIFIED against CfgChar, all six config scripts)
| Order | Warrior | Char id | Model (03767) | HUD index | Why this position |
|---|---|---|---|---|---|
| 1 | Swan | 5 | `warr_sw` | 0 | |
| 2 | Ajax | 11 | `warr_aj` | 3 | |
| 3 | Snow | 33 | `warr_sn` | 7 | |
| 4 | Cochise | 15 | `warr_co` | 1 | |
| 5 | Vermin | 26 | `warr_ve` | 6 | |
| 6 | Fox | 21 | `warr_fo` | 5 | |
| 7 | Rembrandt | 30 | `warr_re` | 4 | |
| 8 | Cleon | 1 | `warr_cl` | 8 | late: level9 also creates a separate scripted Cleon (char 2, own gang) |
| 9 | Cowboy | 18 | `warr_cb` | 2 | last: the only one with an attached object (`dyn_warr_cb`, created by `FUN_0024BFC0`, which null-checks it; HYPOTHESIS that a missing hat is harmless) |

The order is data (9 words at 0x000E1580, `(HUD index << 16) | char id`, 0 ends the list) and can be changed without
touching code. Only base ids are used, so the model the init will pick is exactly the one CHOOSE checks.

### 4.2 Algorithm (`CHOOSE`, called from SPAWN only when a0 < 0)
1. s1 = player 1's +0xD0 (fallback, identical to today's behaviour).
2. dict = `*(0x0050CD4C)`; none -> fallback. Model field = +0x114 in levels 60-64, else +0x112.
3. For each candidate c in table order: reject if table[c]+0x116 <= 0 (status 1), if the u16 model index >= count
   (status 2), if `FUN_001774D0(dict, entry, 0, 0) == 0` (status 3), or if a live human has the same HUD index
   (status 4). The first survivor is chosen (status 5).
4. Store the result at 0x000E15F0, reload f0 (see 5.1) and return.

Lockstep (HYPOTHESIS): every input is game RAM (char table, dictionary trees, object table, GameMgr level) and CHOOSE runs
inside the game's own update on a synchronised Start press, so all instances take the same decision as long as their
game state matches. That includes the model streaming state, which the lockstep hash already compares (F-0130 ran with
a spawned Warrior: 0 mismatches). The status words make a disagreement visible (test T1).

### 4.3 Alternative: keep player 1's model, change only the HUD name
Possible: the only HUD input is the index from `FUN_00229570`, so a hook on `0x00229E5C jal 0x00229570` (MakePlayer)
could return another index when the human has +0x1B1 == 7 (our marker). It touches nothing but the PlayerHUD sprite
(the other two `FUN_00229570` callers are unaffected), so it is technically the lower-risk change. But it does not meet
the goal: the body, voice (+0x3B0) and AI identity (+0xCC) stay Rembrandt, and a Rembrandt body labelled e.g. SWAN is
misleading. The +0xCC field itself must not be changed after creation: it drives the model choice, the voice, the HUD,
the radar helper `FUN_0019F988` and many char-table lookups.

| Option | What players see | Risk |
|---|---|---|
| (A) CHOOSE a different resident Warrior, else clone (this note) | different body, voice and HUD name when a model is available; old clone otherwise | model guarded by the engine's own residency test; untested |
| (B) HUD-only rename of the clone | second Rembrandt body with another name | lowest technical risk; confusing |
| (A)+(B) | (A), and in the fallback case the clone gets another name | as (B) for the fallback |

**Recommendation: (A) alone.** It is the only option that gives a different Warrior, its risk is bounded by the same
check the game uses before building a model, and the fallback is exactly today's behaviour. (B) is not recommended.

### 4.4 If Mission 13 has no spare resident Warrior (HYPOTHESIS, decide after T0)
Level9's script creates Rembrandt (30, priority 1 -> `warr_re`), Snow (33 -> `warr_sn`), Fox (22, priority 3 -> base 21
-> `warr_fo`) and a separate Cleon (char 2, priority 0 -> `warr_cl_gen`, not `warr_cl`); the other `"warr_sw"` strings
in that script are the ignored HuCreate argument 5 of cop/Moonrunner chars 215-219/245/246. Unless other Warrior models
stay cached from earlier levels, all candidates may get status 3 or 4 there and CHOOSE returns the clone. Then:
- (C) add "variant" candidates whose resident model the engine would pick, e.g. Cleon char 2 with priority 0
  (`warr_cl_gen`); needs SPAWN to pass priority 0 to `FUN_00233D60` and write the +0x1B1 = 7 marker afterwards, and is
  only useful while the scripted Cleon is not present;
- (D) pin one extra Warrior model early in the level with the game's own `FUN_0018AD40(dict, id, 0)`
  (= `SetCharacterModel(id, 0)`): deterministic, but it costs memory in a level that was not budgeted for it and the
  model streams in asynchronously (needs its own memory/timing test).
Both need user approval as a scope/design change; neither is part of the fragment below.

## 5. Patch fragment (question 5)

### 5.1 What changes in `[warriors-4p 4p spawn]`
- **Replace** the group line `patch=2,EE,000E10BC,word,8E1100D0 // lw s1,0xd0(s0)` (pnach group line in
  `mod/w4p_m1.pnach`; source `mod/m2/spawn.txt` line 38, rebuilt by `mod/make_pnach.py`) with the first line below.
- **Add** the remaining lines (code 0x000E1400-0x000E155F, table 0x000E1580-0x000E15A7, diagnostics
  0x000E15C0-0x000E15F3). All inside the range assigned to this work (0x000E1400-0x000E17FF); no pnach line uses
  0x000E14xx-0x000E17xx (grep), and the range is below the ELF image (0x00100000+) in the low RAM that stayed zero at
  runtime (F-0125).
- Nothing else in SPAWN, SPAWNPICK, DESPAWN or the leave hook changes; the +0x1B1 = 7 marker, gang, position and name
  "W4PAdded" stay as they are.

Why one word is enough: at 0x000E10B4 `bgez s1,0x000E10C0` skips 0x000E10BC for a0 >= 0. For a0 < 0 the new
`jal 0x000E1400` runs with its delay slot `lwc1 f0,0x10(s0)` (0x000E10C0, unchanged, also the bgez target); CHOOSE
reloads f0 from the same address in its own last delay slot, returns s1 = char id to 0x000E10C4 and preserves s0, s2
and the stack. s1 is saved/restored by SPAWN (0x000E108C/0x000E1158).

### 5.2 Source (assembled at 0x000E1400; R5900 loads are interlocked, every delay slot is explicit)
```
CHOOSE: addiu sp,sp,-96              # in: s0 = player 1 human; out: s1 = char id; f0 = *(s0+0x10)
        sd ra,0(sp) / sq s3..s7,16..80(sp)
        lw s1,0xd0(s0)               # fallback: player 1's char id
        lui s3,0x000E / addiu s3,s3,0x1580
        move v0,s3
clr:    lw v1,0(v0) / sw zero,0x40(v0) / bne v1,zero,clr / addiu v0,v0,4
        lui at,0x0051 / lw s4,-0x32B4(at)          # dict = *(0x0050CD4C)
        beq s4,zero,done / lw v0,0x489C(at)        # GameMgr
        lhu v1,0x56DC(v0) / v1*0x84 / lw v0,0x14D8(v0+v1)   # level number
        s5 = 0x112 + 2*((level-60) < 5 unsigned)
cand:   lh a1,0(s3) / beq a1,zero,done
        v0 = 0x00684620 + a1*0x1AC (mult v0,a1,v1)
        lh v1,0x116(v0) / blez v1,reject [t0=1]
        lhu a1,s5(v0) / lw v1,0x84(s4) / sltu / beq v1,zero,reject [t0=2]
        a1 = *(s4+0x88) + a1*32 / a0 = s4 / a2 = a3 = 0 / jal 0x001774D0
        beq v0,zero,reject [t0=3]
        lh s7,2(s3) / s6 = 0
scan:   a0 = *(0x006EBD38 + s6*8) / beq a0,zero,next / jal 0x00229570
        beq v0,s7,reject [t0=4]
next:   s6++ / slti v0,s6,60 / bne v0,zero,scan
        lh s1,0(s3) / status 5 / b done
reject: sw t0,0x40(s3) / b cand / addiu s3,s3,4
done:   sw s1,0x15F0(0x000E0000) / restore ra,s3..s7 / lwc1 f0,0x10(s0) / jr ra / addiu sp,sp,96
```
Registers used: s3 table pointer, s4 dictionary, s5 model-field offset, s6 slot, s7 candidate HUD index (all saved with
`sq`/restored with `lq` like the game), t0 status (set in branch delay slots), a0-a3/v0/v1 scratch. Stack frame 96
bytes, 16-byte aligned (SPAWN's own frame is 96). Callees: `FUN_001774D0` (saves s0-s4/ra itself), `FUN_00229570`
(leaf, a0/a1/v0/v1 only).

### 5.3 Fragment (110 lines; replaces/extends `[warriors-4p 4p spawn]` as in 5.1)
```
// [warriors-4p 4p spawn] named-Warrior chooser (m2_spawn_name.md); replaces the 000E10BC line of the group
patch=2,EE,000E10BC,word,0C038500 // SPAWN char step: jal 0x000E1400 CHOOSE (pnach had 8E1100D0 lw s1,0xd0(s0)); delay slot lwc1 f0,0x10(s0) kept, CHOOSE reloads f0
patch=2,EE,000E1400,word,27BDFFA0 // addiu sp,sp,-96  ; CHOOSE: in s0 = player 1 human; out s1 = char id; reloads f0
patch=2,EE,000E1404,word,FFBF0000 // sd ra,0(sp)
patch=2,EE,000E1408,word,7FB30010 // sq s3,16(sp)
patch=2,EE,000E140C,word,7FB40020 // sq s4,32(sp)
patch=2,EE,000E1410,word,7FB50030 // sq s5,48(sp)
patch=2,EE,000E1414,word,7FB60040 // sq s6,64(sp)
patch=2,EE,000E1418,word,7FB70050 // sq s7,80(sp)
patch=2,EE,000E141C,word,8E1100D0 // lw s1,0xd0(s0)  ; fallback = player 1's original char id (old behaviour)
patch=2,EE,000E1420,word,3C13000E // lui s3,0x000E
patch=2,EE,000E1424,word,26731580 // addiu s3,s3,0x1580  ; s3 = candidate table
patch=2,EE,000E1428,word,0260102D // move v0,s3
patch=2,EE,000E142C,word,8C430000 // lw v1,0(v0)  ; clear the status word of every table entry
patch=2,EE,000E1430,word,AC400040 // sw zero,0x40(v0)
patch=2,EE,000E1434,word,1460FFFD // bne v1,zero,clr
patch=2,EE,000E1438,word,24420004 // addiu v0,v0,4
patch=2,EE,000E143C,word,3C010051 // lui at,0x0051
patch=2,EE,000E1440,word,8C34CD4C // lw s4,-0x32B4(at)  ; s4 = model dictionary *(0x0050CD4C)
patch=2,EE,000E1444,word,1280003B // beq s4,zero,done
patch=2,EE,000E1448,word,8C22489C // lw v0,0x489C(at)  ; GameMgr *(0x0051489C)
patch=2,EE,000E144C,word,944356DC // lhu v1,0x56DC(v0)  ; current level slot (FUN_004DAB50)
patch=2,EE,000E1450,word,000321C0 // sll a0,v1,7
patch=2,EE,000E1454,word,00031880 // sll v1,v1,2
patch=2,EE,000E1458,word,00831821 // addu v1,a0,v1  ; slot * 0x84
patch=2,EE,000E145C,word,00431021 // addu v0,v0,v1
patch=2,EE,000E1460,word,8C4214D8 // lw v0,0x14D8(v0)  ; level number (FUN_004DAB58 table +4)
patch=2,EE,000E1464,word,2442FFC4 // addiu v0,v0,-60
patch=2,EE,000E1468,word,2C420005 // sltiu v0,v0,5  ; levels 60-64: human init reads +0x114
patch=2,EE,000E146C,word,00021040 // sll v0,v0,1
patch=2,EE,000E1470,word,24550112 // addiu s5,v0,0x112  ; s5 = model field offset 0x112 / 0x114
patch=2,EE,000E1474,word,86650000 // lh a1,0(s3)  ; candidate char id (0 = end of table)
patch=2,EE,000E1478,word,10A0002E // beq a1,zero,done
patch=2,EE,000E147C,word,240301AC // addiu v1,zero,0x1AC
patch=2,EE,000E1480,word,00A31018 // mult v0,a1,v1
patch=2,EE,000E1484,word,3C030068 // lui v1,0x0068
patch=2,EE,000E1488,word,24634620 // addiu v1,v1,0x4620
patch=2,EE,000E148C,word,00431021 // addu v0,v0,v1  ; char table entry 0x00684620 + id*0x1AC
patch=2,EE,000E1490,word,84430116 // lh v1,0x116(v0)  ; CfgChar arg 6 (1800/600); 0 = entry never configured
patch=2,EE,000E1494,word,18600024 // blez v1,reject
patch=2,EE,000E1498,word,24080001 // addiu t0,zero,1  ; status 1: char not configured
patch=2,EE,000E149C,word,00551021 // addu v0,v0,s5
patch=2,EE,000E14A0,word,94450000 // lhu a1,0(v0)  ; model index (u16, as FUN_00218008 reads it)
patch=2,EE,000E14A4,word,8E830084 // lw v1,0x84(s4)  ; dictionary entry count (FUN_001780D0)
patch=2,EE,000E14A8,word,00A3182B // sltu v1,a1,v1
patch=2,EE,000E14AC,word,1060001E // beq v1,zero,reject
patch=2,EE,000E14B0,word,24080002 // addiu t0,zero,2  ; status 2: no model index (0xFFFF or out of range)
patch=2,EE,000E14B4,word,8E820088 // lw v0,0x88(s4)
patch=2,EE,000E14B8,word,00052940 // sll a1,a1,5
patch=2,EE,000E14BC,word,00452821 // addu a1,v0,a1  ; entry = FUN_001780D8(dict, index)
patch=2,EE,000E14C0,word,0280202D // move a0,s4
patch=2,EE,000E14C4,word,0000302D // move a2,zero
patch=2,EE,000E14C8,word,0C05DD34 // jal 0x001774D0  ; load state, same call/arguments as FUN_00218008
patch=2,EE,000E14CC,word,0000382D // move a3,zero
patch=2,EE,000E14D0,word,10400015 // beq v0,zero,reject
patch=2,EE,000E14D4,word,24080003 // addiu t0,zero,3  ; status 3: model not resident
patch=2,EE,000E14D8,word,86770002 // lh s7,2(s3)  ; s7 = candidate HUD index
patch=2,EE,000E14DC,word,0000B02D // move s6,zero
patch=2,EE,000E14E0,word,001610C0 // sll v0,s6,3  ; live humans: object table slots 0..59
patch=2,EE,000E14E4,word,3C03006F // lui v1,0x006F
patch=2,EE,000E14E8,word,00431021 // addu v0,v0,v1
patch=2,EE,000E14EC,word,8C44BD38 // lw a0,-0x42C8(v0)  ; *(0x006EBD38 + slot*8)
patch=2,EE,000E14F0,word,10800005 // beq a0,zero,next
patch=2,EE,000E14F4,word,00000000 // nop
patch=2,EE,000E14F8,word,0C08A55C // jal 0x00229570  ; HUD index of that human (pure leaf)
patch=2,EE,000E14FC,word,00000000 // nop
patch=2,EE,000E1500,word,10570009 // beq v0,s7,reject
patch=2,EE,000E1504,word,24080004 // addiu t0,zero,4  ; status 4: this Warrior is already in the level
patch=2,EE,000E1508,word,26D60001 // addiu s6,s6,1
patch=2,EE,000E150C,word,2AC2003C // slti v0,s6,60
patch=2,EE,000E1510,word,1440FFF3 // bne v0,zero,scan
patch=2,EE,000E1514,word,00000000 // nop
patch=2,EE,000E1518,word,86710000 // lh s1,0(s3)  ; chosen
patch=2,EE,000E151C,word,24080005 // addiu t0,zero,5  ; status 5: chosen
patch=2,EE,000E1520,word,10000004 // beq zero,zero,done
patch=2,EE,000E1524,word,AE680040 // sw t0,0x40(s3)
patch=2,EE,000E1528,word,AE680040 // sw t0,0x40(s3)
patch=2,EE,000E152C,word,1000FFD1 // beq zero,zero,cand
patch=2,EE,000E1530,word,26730004 // addiu s3,s3,4
patch=2,EE,000E1534,word,3C01000E // lui at,0x000E
patch=2,EE,000E1538,word,AC3115F0 // sw s1,0x15F0(at)  ; last result (char id) for PINE
patch=2,EE,000E153C,word,DFBF0000 // ld ra,0(sp)
patch=2,EE,000E1540,word,7BB30010 // lq s3,16(sp)
patch=2,EE,000E1544,word,7BB40020 // lq s4,32(sp)
patch=2,EE,000E1548,word,7BB50030 // lq s5,48(sp)
patch=2,EE,000E154C,word,7BB60040 // lq s6,64(sp)
patch=2,EE,000E1550,word,7BB70050 // lq s7,80(sp)
patch=2,EE,000E1554,word,C6000010 // lwc1 f0,0x10(s0)  ; SPAWN's delay slot loaded f0 before the call; reload it
patch=2,EE,000E1558,word,03E00008 // jr ra
patch=2,EE,000E155C,word,27BD0060 // addiu sp,sp,96
patch=2,EE,000E1580,word,00000005 // candidate 1: Swan char 5, HUD index 0
patch=2,EE,000E1584,word,0003000B // candidate 2: Ajax char 11, HUD index 3
patch=2,EE,000E1588,word,00070021 // candidate 3: Snow char 33, HUD index 7
patch=2,EE,000E158C,word,0001000F // candidate 4: Cochise char 15, HUD index 1
patch=2,EE,000E1590,word,0006001A // candidate 5: Vermin char 26, HUD index 6
patch=2,EE,000E1594,word,00050015 // candidate 6: Fox char 21, HUD index 5
patch=2,EE,000E1598,word,0004001E // candidate 7: Rembrandt char 30, HUD index 4
patch=2,EE,000E159C,word,00080001 // candidate 8: Cleon char 1, HUD index 8
patch=2,EE,000E15A0,word,00020012 // candidate 9: Cowboy char 18, HUD index 2
patch=2,EE,000E15A4,word,00000000 // end of candidate table
patch=0,EE,000E15C0,word,00000000 // status of candidate 1 (0 none,1 not configured,2 no model index,3 not resident,4 present,5 chosen; startup only)
patch=0,EE,000E15C4,word,00000000 // status of candidate 2 (0 none,1 not configured,2 no model index,3 not resident,4 present,5 chosen; startup only)
patch=0,EE,000E15C8,word,00000000 // status of candidate 3 (0 none,1 not configured,2 no model index,3 not resident,4 present,5 chosen; startup only)
patch=0,EE,000E15CC,word,00000000 // status of candidate 4 (0 none,1 not configured,2 no model index,3 not resident,4 present,5 chosen; startup only)
patch=0,EE,000E15D0,word,00000000 // status of candidate 5 (0 none,1 not configured,2 no model index,3 not resident,4 present,5 chosen; startup only)
patch=0,EE,000E15D4,word,00000000 // status of candidate 6 (0 none,1 not configured,2 no model index,3 not resident,4 present,5 chosen; startup only)
patch=0,EE,000E15D8,word,00000000 // status of candidate 7 (0 none,1 not configured,2 no model index,3 not resident,4 present,5 chosen; startup only)
patch=0,EE,000E15DC,word,00000000 // status of candidate 8 (0 none,1 not configured,2 no model index,3 not resident,4 present,5 chosen; startup only)
patch=0,EE,000E15E0,word,00000000 // status of candidate 9 (0 none,1 not configured,2 no model index,3 not resident,4 present,5 chosen; startup only)
patch=0,EE,000E15E4,word,00000000 // status word of the end marker (startup only)
patch=0,EE,000E15F0,word,00000000 // last CHOOSE result (char id; startup only)
```

Encoding checks (VERIFIED, scratch encoder/disassembler): every word above disassembles to its comment; `jal 0x001774D0`
= 0C05DD34 and `jal 0x00229570` = 0C08A55C are the game's own words (0x00218E7C, 0x00229E5C); `sq/lq/sd/ld`, the
3-operand `mult` (0x00431018 at 0x00218420), `lhu v0,0x56DC(a0)` (0x004DAB54) and others match game encodings
(17 cases, 0 mismatches). Branch offsets were computed by the assembler and read back as absolute targets.

## 6. `note_patches.py check` output
The current `mod/w4p_m1.pnach` on its own already reports 6 conflicts: `[warriors-4p 4p hud A]` and
`[warriors-4p 4p hud B1]` patch the same 6 addresses (the A group's description says "Use either this or 4p hud B1").
Runs (fragment = section 5.3 saved as a file):

| Files | Result |
|---|---|
| (baseline) `mod/w4p_m1.pnach` | `checked 1853 addresses in 1 files: 6 problems` (the 6 A/B1 conflicts) |
| full pnach + fragment | 7 problems: the same 6, plus `CONFLICT 000E10BC: ... sets 8E1100D0, frag ... sets 0C038500` (the intended replacement) |
| pnach minus the `000E10BC` line + fragment | 6 problems (the same A/B1 conflicts, nothing new) |
| pnach minus the `000E10BC` line and minus the `[4p hud A]` group + fragment | **`checked 1962 addresses in 2 files: 0 problems`** |

The checker's "cave free" test only covers 0x000F0000-0x000F0FFF; 0x000E1400-0x000E17FF was checked separately: no
ELF segment covers it (the image starts at 0x00100000) and no pnach line uses it.

## 7. Risks
| Risk | Label | Mitigation / check |
|---|---|---|
| Mission 13 has no spare resident Warrior model, so CHOOSE always falls back to the clone | HYPOTHESIS | T0 before applying; then option (C) or (D) (4.4) with user approval |
| Name assets 0x1F..0x32 other than FOX/REMBRANDT are missing or not the expected names in some level | HYPOTHESIS | T1 screenshot; the asset comes from the HUD dictionary, not the level's model set |
| A model that is resident now is evicted later (cache, not pinned) | HYPOTHESIS: `FUN_00177B80` takes an instance reference (+8) | T4: watch the added Warrior through area streaming / long play |
| Mission scripts react to the new Warrior's char id (e.g. dialogue or checks for Swan) | HYPOTHESIS | The human is named "W4PAdded", so name lookups do not find it; watch the mission flow in T1/T4 |
| Voice: identity +0x3B0 selects `vags/character/voices/<identity>/l<level>_...`; the file probe only sets +0x196/+0x197 when found | VERIFIED code; effect HYPOTHESIS | Missing files = no idle lines (expected harmless) |
| Cowboy's hat object `dyn_warr_cb` not resident | VERIFIED null check in `FUN_0024BFC0`; HYPOTHESIS for `FUN_003A2E60` | Cowboy is last in the list |
| Lockstep: instances disagree on residency (asset streaming timing) | HYPOTHESIS (same as all game state) | T1 compares 0x000E15C0-0x000E15F0 on every instance; lockstep hash |
| Second added Warrior (players 3 and 4 both added) | VERIFIED logic | The first one is live, so it is excluded for the second; both get different names if two candidates qualify |
| CHOOSE clobbers f0 (SPAWN's delay slot loaded it) | VERIFIED handled | CHOOSE reloads f0 from s0+0x10 in its last delay slot |
| FUN_002398B0 can move the +0x1B1 marker between humans (`m2_spawn_companion.md` 6) | unchanged | not affected by this change |

## 8. Runtime test plan (PINE; addresses static; read on a paused guest)
- **T0, read-only, no patch change:** in the current Mission 13 setup (3 players, before player 4 presses Start), run the
  survey script below against one instance. It prints the level, the model field, live Warriors and, per candidate,
  configured / model index / resident / present, exactly as CHOOSE would decide. Expected: Rembrandt, Snow, Fox "present";
  the question is whether any other candidate is "resident". Repeat on a second instance; results must be identical.
- **T1, patch applied, Mission 13:** player 4 presses Start with no free companion. Read `0x000E15F0` (chosen char id),
  `0x000E15C0..0x000E15E0` (statuses 0-5), `0x000E1210` (spawned handle). Resolve the handle (`FUN_00390180` logic:
  slot = handle >> 16, `*(0x006EBD38 + slot*8)`, serial check at +4) and read human+0xCC (= chosen id), +0xD0 (= chosen
  id), +0x37C (model index = table[id]+0x112), +0x1B1 (= 7), +0x1B0 (= 3), +0x3B0 (identity). Screenshot: P4 quarter shows
  the chosen Warrior's body and name. All four instances: identical words, lockstep hash 0 mismatches.
- **T2, fallback regression:** if T1 shows all statuses 3/4, `0x000E15F0` must equal player 1's +0xD0 and the game must
  behave exactly as before (clone).
- **T3, presence:** a mission where more Warriors are present (e.g. Mission 1): statuses 4 for the present ones.
- **T4, stability:** play/drive the added Warrior across streamed areas for several minutes and through a checkpoint;
  the body stays visible (no missing model), no TLB miss; leave and re-join (DESPAWN and leave hook still work, a new
  CHOOSE excludes nobody stale).
- **T5, direct call (needs `[warriors-4p test call]`):** `CallAt = <poll>:000E1080:0xFFFFFFFF:7` exercises SPAWN and CHOOSE
  without the join.

T0 survey script (save e.g. as `tests/experiments/<id>/survey_t0.py` when the experiment is set up; run from the
project root: `python -I <file> <pine slot>`). Syntax-checked only; not run.
```python
import os, sys
sys.path.insert(0, os.path.join(os.getcwd(), "tools"))
from pine import Pine

p = Pine(int(sys.argv[1])); r32 = p.read32
def r16(a): return (r32(a & ~3) >> (8 * (a & 2))) & 0xFFFF
def s16(x): return x - 0x10000 if x & 0x8000 else x
def found(tree, key):            # FUN_004DE458/8D0/BE8: lower_bound on node+0x10, header = *(tree+4)
    head = r32(tree + 4); node, best = r32(head + 4), head
    while node:
        if r32(node + 0x10) < key: node = r32(node + 0xC)
        else: best, node = node, r32(node + 8)
    return best != head and not key < r32(best + 0x10)
HUD = {}                         # FUN_00229570 jump table (section 1.2)
for idx, ids in {0: [5,7,8,9,10], 1: [15,17], 2: [18,20,188], 3: [11,13,14], 4: [30,32], 5: [21,23,24,25],
                 6: [26,28,29,191], 7: [33,35,36,37,190], 8: [1,3,4,189], 9: [38,39,40], 10: [43,44],
                 11: [45,46,47,48]}.items():
    for i in ids: HUD[i] = idx
G = r32(0x0051489C); level = r32(G + 0x14D8 + r16(G + 0x56DC) * 0x84)
off = 0x114 if 0 <= level - 60 < 5 else 0x112
d = r32(0x0050CD4C); count, entries = r32(d + 0x84), r32(d + 0x88)
live = {s: r32(0x006EBD38 + 8 * s) for s in range(60)}
present = {HUD.get(r32(h + 0xCC), "other") for h in live.values() if h}
print(f"level {level}, field +0x{off:X}, dict 0x{d:08X} ({count} entries), Warrior HUD indices present: {present - {'other'}}")
for cid, name in [(5,"Swan"),(11,"Ajax"),(33,"Snow"),(15,"Cochise"),(26,"Vermin"),(21,"Fox"),(30,"Rembrandt"),(1,"Cleon"),(18,"Cowboy")]:
    e = 0x00684620 + cid * 0x1AC; hp, m = s16(r16(e + 0x116)), r16(e + off)
    if hp <= 0: st = "1 not configured"
    elif m >= count: st = f"2 no model index ({m:#x})"
    else:
        ent = entries + m * 0x20
        ok = found(d + 0x40, r32(ent + 4)) and found(d + 0x30, r32(ent + 0xC)) and found(d, r32(ent + 8))
        st = "3 not resident" if not ok else ("4 present" if HUD[cid] in present else "eligible")
    print(f"{name:10s} char {cid:2d} HUD {HUD[cid]} model {m:#06x} -> {st}")
print("CHOOSE result", hex(r32(0x000E15F0)), "status", [r32(0x000E15C0 + 4 * i) for i in range(9)])
```

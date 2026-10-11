# M2 research: GameMgr per-player 0x5C records (the "+0x234 = 1.0f" overwrite)

Static analysis only (no emulator run). Game: The Warriors SLUS-21215 v1.03. Function names are OUR labels or Ghidra
`FUN_` names (stripped ELF). All "was" words below were read from `local/disc/SLUS_212.15` and checked with
`tools/note_patches.py check` (0 mismatches; one intended conflict, see 3.2). Tools used: the earlier fork's GameMgr
dataflow scan (`gm_all2.json`, scratchpad), an ELF scan for every `addiu/ori/daddiu r,zero,0x5C` and every
`addiu r,r',0x5C` pointer advance, and greps of `local/analysis/all/*.c`.

## Trigger (runtime, already measured)
`local/m2/m2j/w4p.log` (DebugWatch on GameMgr+0x234): after players 3 and 4 were made, `0x00255018 swc1 f0,0x17C(v1)`
in `FUN_00254e78` wrote 1.0f to GameMgr+0x234 (player 4's handle) every frame. The address is
`GameMgr + playerIndex*0x5C + 0x17C` with playerIndex = human+0x1B0 = 2. VERIFIED (log + disassembly
0x00254FF8-0x00255018).

## 1. The record array (VERIFIED)
- **Base GameMgr+0x168, stride 0x5C, 2 entries: +0x168..+0x21F.** It ends exactly where the per-player flags
  (+0x220) start. With 4 players, record 2 covers +0x220..+0x27B (flags, count +0x224, handles +0x228.., +0x238..)
  and record 3 covers +0x27C..+0x2D7 (fields +0x280..+0x2D4). Evidence: constructor `FUN_00418588` builds 2 records
  from `addiu v0,s1,0x168` (0x00418624), pointer advance `addiu s0,v0,0x5C` (0x0041863C), loop counter
  `addiu v1,zero,1` (0x0041861C) counting down to -1; level reset `FUN_00418c68` calls `FUN_00418530(GM+i*0x5C+0x168)`
  for i < 2 (0x00418F30-0x00418F40).
- **Fields** (offsets inside a record; from `FUN_00418588`, `FUN_00418530`, `FUN_004183d8`, `FUN_00418408`,
  `FUN_00418428`):

| Off | Type | Init / meaning |
|---|---|---|
| +0x00, +0x04 | s32[2] | -1 at construction (meaning not traced) |
| +0x08, +0x0C | s32[2] | -1 at construction (meaning not traced) |
| +0x10 | u32 | game time (GameClock+0x48, ms) of the last event (`FUN_00418428`) |
| +0x14 | float | multiplier: 1.0 at init; +0.27 per event of type 2/3, capped at 2.0; set to 1.0 every frame by `FUN_00254e78` in some player states |
| +0x18, +0x19 | u8 | counters for event types 0 and 1, capped at 5 |
| +0x1A | u8 | "capped" flag (set when a counter reaches 5); read by `FUN_00264cf8` |
| +0x1B | u8 | last event type (4 = none); counters restart after 5000 ms or a type change |
| +0x28 | u32 | 0 on reset |
| +0x40..+0x46 | u16 x4 | 0 on reset; +0x46 is read through getter B by HudUpdate (`FUN_001af010`, all_01.c:45969) |
| +0x48, +0x50, +0x54, +0x58 | u32 | 0 on reset |
| +0x4C, +0x4D | u8 | 0 on reset |

  HYPOTHESIS: +0x10..+0x1B is a combo/streak tracker (5 s window, multiplier 1.0-2.0). Not needed for the fix.

## 2. Every access site
### 2.1 Direct (index x 0x5C) sites (VERIFIED, ELF + decompile; these are all 7 `* 0x5c` expressions in the decompile)
| Site | Function | Index source | Access |
|---|---|---|---|
| 0x00222AE8..0x00222B10 | `FUN_00222ad8` (record getter A) | human+0x380 (HUD slot), only if human+0x1B0 != -1; else record 0 | returns GM+0x168+idx*0x5C |
| 0x00222B28..0x00222B50 | `FUN_00222b18` (record getter B) | same | same |
| 0x00254FF8..0x00255018 | `FUN_00254e78` | human+0x1B0 (guarded != -1) | store float +0x14 (GM+0x17C) |
| 0x00264E3C..0x00264E68 | `FUN_00264cf8` | human+0x1B0 (not guarded) | load byte +0x1A (GM+0x182) |
| 0x00264E8C..0x00264E9C | `FUN_00264cf8` | human+0x1B0 | load float +0x14 (GM+0x17C) |
| 0x00265F3C..0x00265F54 | `FUN_00265dd0` | human+0x1B0 (guarded) | &record+0x10 (GM+0x178) passed to `FUN_00418428` |
| 0x00418F30..0x00418F40 | `FUN_00418c68` (level reset) | loop i = 0..1 | `FUN_00418530(record)` |
| 0x0041861C/24/3C | `FUN_00418588` (constructor) | pointer loop, 2 records | -1 fields + `FUN_004183d8(+0x10)` |

### 2.2 Through the getters (relocation-safe)
About 75 call sites of `FUN_00222ad8`/`FUN_00222b18` (all_01: 3, all_02: 42+4, all_03: 30) use only the returned
pointer, so they follow a moved base automatically. This includes `MakePlayer` (0x00229C40), which calls
`FUN_00418530(FUN_00222b18(human))` twice when a player is made. VERIFIED (decompile).

### 2.3 Fixed-index accesses (player 0/1)
None found: the dataflow scan has no load/store/address hit at GM+0x168..+0x21F other than the indexed ones above,
and the decompile has no `DAT_0051489c + 0x1xx` access in that range besides them. HYPOTHESIS for completeness: the
scan is linear per function (no CFG); a record pointer kept in another object would not be seen (none observed).

### 2.4 Two latent bugs for players 3 and 4 (VERIFIED code, HYPOTHESIS runtime)
- **Getters use the HUD slot (+0x380).** `MakePlayer` sets +0x380 from `FUN_001b2200`, which tries HUD slots 0 and 1
  only. Players 3 and 4 then get -1 (as long as the HUD has 2 slots), and the getters return GM+0x168-0x5C =
  **GM+0x10C**. `MakePlayer`'s `FUN_00418530` on that pointer zeroes GM+0x11C..+0x167 (u16 at +0x14C..+0x153 incl.
  +0x150/+0x152, u32 +0x154, bytes +0x158/+0x159 = game mode low byte, +0x15C, +0x160, +0x164). This may be part of
  why joining players 3-4 behaves oddly. The fix below indexes the getters by +0x1B0 like the other four sites.
- `FUN_00264cf8` reads record+0x1A for any human; for AI (+0x1B0 = -1) it reads GM+0x126 today (harmless read; after
  the move it reads GM+0x58BE, also harmless).

## 3. Other per-player arrays in GameMgr (task 2)
Checked: every indexed GameMgr access in the dataflow scan (263 sites, grouped by offset), plus decompile patterns
indexed by human+0x1B0 or human+0x380.
- **Already in `m2_gamemgr.md`:** +0x220/+0x221 flags, +0x222, +0x224, +0x228 handles, +0x230, +0x234, the per-player
  block +0x414..+0x42F (incl. +0x41E x7), options +0x440/+0x448/+0x56DE, records +0x5740 (x0x30).
- **New: only the 0x5C records above** overflow with 4 players.
- **Per-player but bounded (no overflow, players 3-4 simply get nothing):** inventory sub-object at GM+0x480,
  per-HUD-slot stride 0x3F4, item stride 0x2C; `FUN_0041e420` and `FUN_0041e5b0` return early for slot >= 2
  (unsigned test, so -1 is also rejected). VERIFIED. A functional 4-player inventory is separate work.
- **Indexed but not per-player (no change needed):** +0x08 table of 16-byte entries (`FUN_0041d428`, set from Lua;
  indexed by a byte such as human+0x11B) HYPOTHESIS not player-related; +0x294 and +0x32B (15 entries, reset loop to
  0xF); +0x3E8 (4 entries, called with constants 0..3); +0x570C (8 floats, Lua `SetLUASaveDataFloat`/`Get...`);
  +0x572C bitfield; +0x14D4.. level table. VERIFIED.
- Fields +0x25C/+0x260/+0x264 and +0x280/+0x284 are set to -1 in the constructor but are never indexed by a player
  (fixed-offset accessors only). VERIFIED (scan).
- Scan false positives (base register not GameMgr): 0x90/0x94, 0xA0, 0x698 (x0x130, a 4-entry loop in another
  object), 0x828, 0x1540-0x1554, 0x1910.
- Outside GameMgr (for the HUD work): `FUN_004228a0` indexes another manager by HUD slot x0xC0; HUD tables
  0x0060F400 + slot*0x430 and 0x00618010 + slot*0xAB0.

## 3.1 Proposed relocation (4 records at GameMgr+0x5900..+0x5A6F)
- The m2_gamemgr plan uses the tail up to +0x58F7 and states "free from about +0x5900". Four records need 0x170
  bytes, so the allocation must grow from 0x5A00 to at least 0x5A70: use **0x5A80**.
- Record accesses are byte/half/word only (record 1 at +0x1C4 is only 4-byte aligned today), so +0x5900 is safe.
- No code cave is needed (0x000F0B40-0x000F0BFF stays free).
- Records 2 and 3 are reset by `MakePlayer` (through the getter) when players 3 and 4 join. The level-reset loop in
  `FUN_00418c68` resets only records 0-1 because its bound (`slti v0,s3,2` at 0x00418F58) also drives the HUD and
  per-player-block init; when that loop is made 4-wide (m2_gamemgr §1.3 / HUD work), records 2-3 are reset too
  through the patched base. HYPOTHESIS: not resetting them on level reset is harmless (stale combo state until the
  next join).

## 3.2 Patch list (14 words; all "was" words VERIFIED against the ELF)
| Address | Was | New | Note |
|---|---|---|---|
| `00161130` | `240657C0` addiu a2,zero,0x57c0 | `24065A80` addiu a2,zero,0x5a80 | GameMgr allocation 0x57C0 -> 0x5A80. **Supersedes** `24065A00` in `mod/m2/gamemgr.txt` (the checker reports this one intended conflict) |
| `0041861C` | `24030001` addiu v1,zero,0x1 | `24030003` addiu v1,zero,0x3 | constructor: build 4 records (counts down to -1) |
| `00418624` | `26220168` addiu v0,s1,0x168 | `26225900` addiu v0,s1,0x5900 | constructor: record base |
| `00418F38` | `24840168` addiu a0,a0,0x168 | `24845900` addiu a0,a0,0x5900 | level reset: record base |
| `00222AE8` | `8C820380` lw v0,0x380(a0) | `808201B0` lb v0,0x1b0(a0) | getter A: index by player index (same instruction as 0x00222AD8) |
| `00222AFC` | `24420168` addiu v0,v0,0x168 | `24425900` addiu v0,v0,0x5900 | getter A: base |
| `00222B10` | `24420168` addiu v0,v0,0x168 | `24425900` addiu v0,v0,0x5900 | getter A: non-player fallback (record 0) |
| `00222B28` | `8C820380` lw v0,0x380(a0) | `808201B0` lb v0,0x1b0(a0) | getter B: index by player index |
| `00222B3C` | `24420168` addiu v0,v0,0x168 | `24425900` addiu v0,v0,0x5900 | getter B: base |
| `00222B50` | `24420168` addiu v0,v0,0x168 | `24425900` addiu v0,v0,0x5900 | getter B: non-player fallback |
| `00255018` | `E460017C` swc1 f0,0x17c(v1) | `E4605914` swc1 f0,0x5914(v1) | `FUN_00254e78`: record+0x14 (the +0x234 overwrite) |
| `00264E68` | `90620182` lbu v0,0x182(v1) | `9062591A` lbu v0,0x591a(v1) | `FUN_00264cf8`: record+0x1A |
| `00264E9C` | `C441017C` lwc1 f1,0x17c(v0) | `C4415914` lwc1 f1,0x5914(v0) | `FUN_00264cf8`: record+0x14 |
| `00265F54` | `24840178` addiu a0,a0,0x178 | `24845910` addiu a0,a0,0x5910 | `FUN_00265dd0`: &record+0x10 |

```
patch=2,EE,00161130,word,24065A80 // was 240657C0; GameMgr allocation 0x57C0 -> 0x5A80 (supersedes 24065A00)
patch=2,EE,0041861C,word,24030003 // was 24030001; ctor: 4 records
patch=2,EE,00418624,word,26225900 // was 26220168; ctor: record base +0x168 -> +0x5900
patch=2,EE,00418F38,word,24845900 // was 24840168; level reset: record base
patch=2,EE,00222AE8,word,808201B0 // was 8C820380; getter A: index by +0x1B0
patch=2,EE,00222AFC,word,24425900 // was 24420168; getter A: base
patch=2,EE,00222B10,word,24425900 // was 24420168; getter A: fallback base
patch=2,EE,00222B28,word,808201B0 // was 8C820380; getter B: index by +0x1B0
patch=2,EE,00222B3C,word,24425900 // was 24420168; getter B: base
patch=2,EE,00222B50,word,24425900 // was 24420168; getter B: fallback base
patch=2,EE,00255018,word,E4605914 // was E460017C; FUN_00254e78 record+0x14
patch=2,EE,00264E68,word,9062591A // was 90620182; FUN_00264cf8 record+0x1A
patch=2,EE,00264E9C,word,C4415914 // was C441017C; FUN_00264cf8 record+0x14
patch=2,EE,00265F54,word,24845910 // was 24840178; FUN_00265dd0 &record+0x10
```

Risks (HYPOTHESIS):
- Getter index change: for players 1-2, +0x380 (HUD slot) and +0x1B0 (player index) are assumed equal in normal play
  (P1 = slot 0 / index 0, P2 = slot 1 / index 1). Check at runtime by reading both for players 1 and 2.
- Heap: 0x80 more bytes for GameMgr (0x5A00 -> 0x5A80); the allocator's free space is not proven.
- After a player leaves, `RemovePlayer` compacts indices but not records, so a remaining player may inherit another
  player's combo state until the next join (original game had the same behaviour for player 2).

Runtime checks: DebugWatch on GameMgr+0x234 must stay silent after players 3-4 join; DebugWatch on GameMgr+0x5914,
+0x5970, +0x59CC, +0x5A28 (record+0x14 of records 0-3) should show writes from 0x00255018; GameMgr+0x150/+0x152/
+0x158 must keep their values when players 3-4 are made.

## Summary
GameMgr has a per-player array of 0x5C-byte records at **+0x168..+0x21F (2 entries)**, apparently a combo/streak
tracker (time, 1.0-2.0 multiplier, counters; HYPOTHESIS on meaning). With 4 players, record 2 lands on +0x220..+0x27B
(flags, count, handles: the measured 1.0f write to +0x234) and record 3 on +0x27C..+0x2D7.

Access sites (VERIFIED):
- 7 indexed sites: two getters `FUN_00222ad8`/`FUN_00222b18`, `FUN_00254e78`, two in `FUN_00264cf8`, `FUN_00265dd0`,
  and the level reset `FUN_00418c68`;
- the constructor loop in `FUN_00418588`;
- about 75 calls that use the getters' pointer (relocation-safe);
- no fixed player-0/1 accesses.

A second bug: both getters index by the HUD slot (+0x380), which is -1 for players 3-4, so `MakePlayer` zeroes
GameMgr+0x11C..+0x167 (includes +0x150..+0x159).

Fix: move the records to **GameMgr+0x5900** (4 entries) and grow the allocation to **0x5A80**. This takes 14 patch
words, ELF-verified, with no cave needed. The size word supersedes the one in `mod/m2/gamemgr.txt`. The getters are
switched to index by +0x1B0.

Other per-player GameMgr arrays: none new that overflow. Inventory (+0x480, stride 0x3F4) is bounded to 2 slots
(players 3-4 get none). The remaining indexed arrays are not per-player.

Confidence: high for the sites and words; medium for the getter-index change and heap headroom (runtime checks listed).

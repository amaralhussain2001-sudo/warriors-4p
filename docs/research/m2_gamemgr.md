# M2 research: GameMgr player storage and the 2-player limits (static analysis)

Build: The Warriors SLUS-21215 v1.03 (ELF `local/disc/SLUS_212.15`, read-only). Date: 2026-10-11.
Method: decompiled C (`local/analysis/all/*.c`, `funcs.pkl`, `callers.pkl`) plus our own ELF scan: a per-function
register-dataflow pass that follows the GameMgr pointer (`lui 0x0051` + `lw 0x489C`) into registers, constant and
indexed offsets, and GameMgr methods (callees that receive GameMgr in a0; 92 found). 1,798 GameMgr accesses were
found. The scan is heuristic: accesses through a copied GameMgr pointer in another object, or virtual calls, are not
seen. Every patch word below was checked against the ELF word at that address.
Function names are OUR labels (stripped ELF). Nothing was run.

GameMgr: heap object, size **0x57C0** (allocation at 0x00161130 `addiu a2,zero,0x57c0`, the only 0x57C0 immediate
in the code), constructor `GameMgr::ctor` FUN_00418588, reset FUN_00418C68. VERIFIED.

## 1. Inventory of per-player storage

### 1.1 Handle array, count, flags (+0x220..+0x237)
| Field | Meaning | Accesses | Label |
|---|---|---|---|
| +0x224 s16 | player count | 269 loads, 2 stores (AddPlayer 0x00419C38, RemovePlayer 0x00419CF8) in 117 functions | VERIFIED |
| +0x228 u32[2] | player human handles; empty = 0xFFFFFFFF (null handle DAT_006EBD30, set at 0x003902C8); constructor fills 2 | 164 functions touch +0x228/+0x22C; 42 of them with a variable index (loops `i < count`, `HuGetPlayer` core 0x00234FB8, AddPlayer 0x00419B10, RemovePlayer 0x00419C68, swap 0x00419E10) | VERIFIED |
| +0x22C | handle of player 2 used directly | 21 functions: 1236e0 126c40 13c710 1557f8 158728 1b3020 1cef10 1cf468 2325e0 234318 23fea8 249cb0 24b3d8 2f0318 300678 304608 4197a8 419ee0 41a060 41a460 423098 | VERIFIED |
| +0x220 u8[2] | per-player slow-motion/rage flag, indexed by human+0x1B0 (set FUN_0041AB30, clear FUN_0041AB60 which restores LogicDt when no flag is set; RemovePlayer shifts them) | 5 functions | VERIFIED |
| +0x222 s16 | a HUD-slot selector (compared with human+0x380 in the join code); setter FUN_00419A68 accepts only `< 2` | 4 sites | VERIFIED (use) / HYPOTHESIS (meaning) |
| +0x230 u32 | GameMgr frame tick (FUN_0041A370, `% 30`; FUN_004197A8 `% 37`) | 5 sites | VERIFIED |
| +0x234 u32 | music/stream handle (FUN_00419030/00419108/00419150, reached through a pointer only passed to the handle resolver FUN_0010F578); +0x238..+0x24B its fade state, +0x250..+0x258 its parameters | handle: 8 sites; the other fields are reached directly from GameMgr | VERIFIED |

`HuGetPlayer(n)` (0x00234FB8, Lua binding 0x0035B188) has **no bounds check**: in the original game `HuGetPlayer(2)`
reads the tick counter as a handle. VERIFIED.

### 1.2 Per-player records (+0x5740)
0x30-byte records, 2 entries (+0x5740..+0x579F), built by FUN_0018F230 and reset by FUN_0018F268 in the constructor
(two loops counting 1 down to -1); filled by AddPlayer via FUN_0018F7B0(record, human); also used by FUN_00244770
(FUN_0018FEE0), FUN_00419DA0 (loop over `count`, FUN_00190588), camera code FUN_00128678 / FUN_0012AE58 (`lq` at
record+0x10/+0x20). The next field +0x57A0 belongs to something else (6 functions). An exhaustive scan of all code
immediates 0x5740..0x579F found no other record accesses. VERIFIED.

### 1.3 Per-player block +0x414..+0x42F (2 entries each)
| Field | Evidence | Accesses (instr / functions) |
|---|---|---|
| +0x414 u8[2], +0x416 u8[2], +0x418 u8[2] | reset with memset size 2 (FUN_004307E8 in FUN_00418C68) | 5/4, 8/8, 3/3 |
| +0x41A u8[2], +0x41C u8[2], +0x42C u8[2] | FUN_0041C4C8(gm, i, a, b) writes +0x41A+i and +0x42C+i; ctor loop `i < 2` clears +0x41A+i | 14/13, 5/3, 2/2 |
| +0x41E u8[2][7] | `GM + player*7 + slot + 0x41E` (FUN_0041DBE8, FUN_0041DB08 loop `< 2`), player = human+0x1B0 | 19/9 |
| +0x42E u8[2] | `GM + human+0x1B0 + 0x42E` (FUN_0041C4E0) | 11/8 |

Index source VERIFIED for +0x41E and +0x42E; HYPOTHESIS (per player, from the size-2 resets) for the others. These
arrays are packed back to back, so none can grow in place.

### 1.4 Per-player options (+0x440, +0x448, +0x56DE)
+0x440 u32[2] (mirrored to static 0x0050B1F8[2]), +0x448 u32[2] (mirror 0x0050B240[2] bytes), +0x56DE u8[2]
(FUN_0041A3E0/400/410; read by the pad code at 0x00149668). Written by the options menu (0x001D7EF0..0x001D80E0) and
the options save/load (0x00421708 / 0x00421AD0) for players 0 and 1 only. The mirrors are read by camera code with a
camera/view index (FUN_00129050, FUN_00129C78, together with 0x0050B1B0/0x0050B1B8/0x0050B248, all 2 entries).
VERIFIED. These are menu options, not gameplay state.

### 1.5 Not per-player (checked)
+0x3E8 u8[4] (constructor fills 4), +0x456 u16 bitmask of joined pads (bit = pad index, 8 pads fit), +0x570C
(1-based table), +0x572C bitset, +0x14D4 level table. VERIFIED.

## 2. Proposed design: grow GameMgr, extend the handle array in place

The handle array cannot be moved cheaply: 164 functions use it, many as `GM+0x228` plus `i*4`, or as a walking
pointer. But only two fields sit directly behind it (+0x230 tick, +0x234 music handle), and they have 5 and 8
accesses. So:

1. Grow the GameMgr allocation from 0x57C0 to 0x5A00, so every relocated field keeps a one-word `GM+imm` access (no
   base-register change; caves are needed only for the join limit and the constructor init).
2. Move the tick, the music handle and the +0x222 s16 to the new tail. +0x228..+0x237 becomes a contiguous 4-entry
   handle array, and +0x220..+0x223 a 4-entry flag array. Every existing `i < count` loop, `HuGetPlayer`, AddPlayer,
   RemovePlayer and swap then works for 4 players unchanged.
3. Move the records to +0x5800 (4 x 0x30, 16-byte aligned for the `lq` accesses) and construct and reset 4 of them.
4. Raise the AddPlayer and join limits.
5. Initialise the new slots in a small constructor cave: handle[2] = -1, new music handle = -1, tick and s16 = 0.
   The original constructor stores at 0x004186F8 (`sw -1,0x234`) and 0x004186A8 (`sh 0,0x222`) are kept on
   purpose: they now initialise handle[3] and flags[2..3].

New GameMgr layout tail: +0x57C0 tick, +0x57C4 s16 (old +0x222), +0x57C8 music handle, +0x5800..+0x58BF records[4],
+0x58C0..+0x59FF free for section 1.3 (needs about 0x38 bytes for 4-wide copies).

### 2.1 Patch list (GameMgr storage; all original words VERIFIED against the ELF)
| Group | Address | Original | New | Note |
|---|---|---|---|---|
| size | `00161130` | `240657C0` addiu a2,zero,0x57c0 | `24065A00` addiu a2,zero,0x5a00 | GameMgr allocation 0x57C0 -> 0x5A00 |
| tick | `004187BC` | `AE200230` sw zero,0x230(s1) | `AE2057C0` sw zero,0x57c0(s1) | frame tick +0x230 -> +0x57C0 |
| tick | `00419978` | `8E240230` lw a0,0x230(s1) | `8E2457C0` lw a0,0x57c0(s1) | frame tick +0x230 -> +0x57C0 |
| tick | `0041A380` | `8E020230` lw v0,0x230(s0) | `8E0257C0` lw v0,0x57c0(s0) | frame tick +0x230 -> +0x57C0 |
| tick | `0041A38C` | `AE020230` sw v0,0x230(s0) | `AE0257C0` sw v0,0x57c0(s0) | frame tick +0x230 -> +0x57C0 |
| tick | `0041A390` | `8E040230` lw a0,0x230(s0) | `8E0457C0` lw a0,0x57c0(s0) | frame tick +0x230 -> +0x57C0 |
| s16 | `00419A70` | `A4850222` sh a1,0x222(a0) | `A48557C4` sh a1,0x57c4(a0) | s16 +0x222 -> +0x57C4 (ctor 0x004186A8 left as is: now zeroes flags[2..3]) |
| s16 | `0041A644` | `86220222` lh v0,0x222(s1) | `862257C4` lh v0,0x57c4(s1) | s16 +0x222 -> +0x57C4 (ctor 0x004186A8 left as is: now zeroes flags[2..3]) |
| s16 | `0041A688` | `86220222` lh v0,0x222(s1) | `862257C4` lh v0,0x57c4(s1) | s16 +0x222 -> +0x57C4 (ctor 0x004186A8 left as is: now zeroes flags[2..3]) |
| music | `00419040` | `26110234` addiu s1,s0,0x234 | `261157C8` addiu s1,s0,0x57c8 | music handle +0x234 -> +0x57C8 (ctor 0x004186F8 left as is: now handle[3] = -1) |
| music | `00419074` | `AE020234` sw v0,0x234(s0) | `AE0257C8` sw v0,0x57c8(s0) | music handle +0x234 -> +0x57C8 (ctor 0x004186F8 left as is: now handle[3] = -1) |
| music | `0041911C` | `26040234` addiu a0,s0,0x234 | `260457C8` addiu a0,s0,0x57c8 | music handle +0x234 -> +0x57C8 (ctor 0x004186F8 left as is: now handle[3] = -1) |
| music | `00419128` | `8E050234` lw a1,0x234(s0) | `8E0557C8` lw a1,0x57c8(s0) | music handle +0x234 -> +0x57C8 (ctor 0x004186F8 left as is: now handle[3] = -1) |
| music | `00419160` | `26110234` addiu s1,s0,0x234 | `261157C8` addiu s1,s0,0x57c8 | music handle +0x234 -> +0x57C8 (ctor 0x004186F8 left as is: now handle[3] = -1) |
| music | `00419258` | `26040234` addiu a0,s0,0x234 | `260457C8` addiu a0,s0,0x57c8 | music handle +0x234 -> +0x57C8 (ctor 0x004186F8 left as is: now handle[3] = -1) |
| music | `00419384` | `26040234` addiu a0,s0,0x234 | `260457C8` addiu a0,s0,0x57c8 | music handle +0x234 -> +0x57C8 (ctor 0x004186F8 left as is: now handle[3] = -1) |
| records | `004185D8` | `26375740` addiu s7,s1,0x5740 | `26375800` addiu s7,s1,0x5800 | records +0x5740 -> +0x5800 (4 x 0x30) |
| records | `004188C8` | `26325740` addiu s2,s1,0x5740 | `26325800` addiu s2,s1,0x5800 | records +0x5740 -> +0x5800 (4 x 0x30) |
| records | `00244BC4` | `24845740` addiu a0,a0,0x5740 | `24845800` addiu a0,a0,0x5800 | records +0x5740 -> +0x5800 (4 x 0x30) |
| records | `00419BDC` | `24845740` addiu a0,a0,0x5740 | `24845800` addiu a0,a0,0x5800 | records +0x5740 -> +0x5800 (4 x 0x30) |
| records | `00419C24` | `24845740` addiu a0,a0,0x5740 | `24845800` addiu a0,a0,0x5800 | records +0x5740 -> +0x5800 (4 x 0x30) |
| records | `00419DCC` | `24115740` addiu s1,zero,0x5740 | `24115800` addiu s1,zero,0x5800 | records +0x5740 -> +0x5800 (4 x 0x30) |
| records | `001287F8` | `24C65750` addiu a2,a2,0x5750 | `24C65810` addiu a2,a2,0x5810 | records +0x5740 -> +0x5800 (4 x 0x30) |
| records | `0012B77C` | `78625750` lq v0,0x5750(v1) | `78625810` lq v0,0x5810(v1) | records +0x5740 -> +0x5800 (4 x 0x30) |
| records | `00128750` | `78435760` lq v1,0x5760(v0) | `78435820` lq v1,0x5820(v0) | records +0x5740 -> +0x5800 (4 x 0x30) |
| records | `004186EC` | `24120001` addiu s2,zero,0x1 | `24120003` addiu s2,zero,0x3 | ctor: construct 4 records (loop count 1 -> 3, counts down to -1) |
| records | `004188D0` | `24130001` addiu s3,zero,0x1 | `24130003` addiu s3,zero,0x3 | ctor: reset 4 records |
| flags | `0041AB80` | `2CC20002` sltiu v0,a2,0x2 | `2CC20004` sltiu v0,a2,0x4 | slow-motion flags +0x220: scan 4 players |
| flags | `0041AB98` | `2CC20002` sltiu v0,a2,0x2 | `2CC20004` sltiu v0,a2,0x4 | slow-motion flags +0x220: scan 4 players |
| cap | `00419B48` | `2A020002` slti v0,s0,0x2 | `2A020004` slti v0,s0,0x4 | AddPlayer: refuse at 4 instead of 2 |
| cap | `0041A540` | `12750039` beq s3,s5,0x0041a628 | `0803C1C0` j 0x000f0700 | join: beq s3,s5(=2) -> j 0x000F0700 (cave: skip join when count >= 4) |
| init | `0041870C` | `0C1077D0` jal 0x0041df40 | `0C03C1C8` jal 0x000f0720 | ctor: jal 0x0041DF40 -> jal 0x000F0720 (cave inits new fields, then j 0x0041DF40) |

Caves (free RAM 0x000F0700.., F-0050; our existing caves end at 0x000F0670):
```
patch=2,EE,000F0700,word,2A610004 // slti at,s3,0x4
patch=2,EE,000F0704,word,10200003 // beq at,zero,0x000f0714
patch=2,EE,000F0708,word,00000000 // nop
patch=2,EE,000F070C,word,08106952 // j 0x0041a548
patch=2,EE,000F0710,word,00000000 // nop
patch=2,EE,000F0714,word,0810698A // j 0x0041a628
patch=2,EE,000F0718,word,00000000 // nop
patch=2,EE,000F0720,word,AE220230 // sw v0,0x230(s1)
patch=2,EE,000F0724,word,AE2257C8 // sw v0,0x57c8(s1)
patch=2,EE,000F0728,word,081077D0 // j 0x0041df40
patch=2,EE,000F072C,word,FE2057C0 // sd zero,0x57c0(s1)
```
- **Join cap cave:** the original `beq s3,s5` compared the count with s5 = 2. s5 is reused at 0x0041A60C (`bnel v0,s5`,
  viewport mode == 2), so s5 is left as is and the cave tests `count < 4` in `at`. The delay slot 0x0041A544 is
  unchanged.
- **Constructor cave:** it runs in place of `jal 0x0041DF40` at 0x0041870C. There v0 = -1 and s1 = GameMgr (VERIFIED
  0x004186DC..0x00418710). It returns through a tail jump, so ra = 0x00418714 is kept. 0x004187BC is retargeted, so it
  no longer overwrites handle[2].
- **Totals:** 32 patched code words plus 11 cave words. The rest of section 2 (per-player block, options) is not in
  this list.

### 2.2 Per-player block (section 1.3): plan, not yet a patch list
Copy each array to the tail with 4 entries:
- +0x414 -> +0x58C0, +0x416 -> +0x58C4, +0x418 -> +0x58C8, +0x41A -> +0x58CC, +0x41C -> +0x58D0;
- +0x41E (7 bytes per player) -> +0x58D4..+0x58EF;
- +0x42C -> +0x58F0, +0x42E -> +0x58F4.

Then retarget about 67 instructions in about 35 functions, and widen the memsets (FUN_00418C68: size 2 -> 4) and the
constructor loop. The `i*7` index arithmetic stays the same. Each site needs its index source confirmed first (several
are reached through `k + imm` index registers, e.g. 0x00164C20 accesses +0x420).

### 2.3 Options (section 1.4)
Keep 2 entries. Players 3 and 4 have no option slots in the original. Recommended: their readers use player 1's
options, i.e. index `p & 1` -> 0 for p >= 2. This belongs with the camera work, because the readers index by camera
or view (0x0050B1B0/B1B8/B1F8/B240/B248 are 2-entry camera statics). Alternative: give them 4-entry copies in the
tail.

## 3. Count checks: which change for 4
| Kind | Count | Action |
|---|---|---|
| AddPlayer cap `slti v0,s0,2` 0x00419B48 | 1 | raise to 4 (in 2.1) |
| Join cap `count == 2` -> no join (0x0041A540) | 1 | `count >= 4` (cave in 2.1) |
| `count < 2` / `1 < count` "is this multiplayer" tests | 42 sites in 34 functions (e.g. LayoutViewports 0x00122F3C, HUD 0x001C5D90, MakePlayer 0x00229CFC) | keep: the meaning still holds for 3-4 players |
| `count == 2` exact tests | 2: FUN_00234318 (0x0023449C, then uses +0x22C) and FUN_00303260 (0x003032B0) | change to `count >= 2` and make the player-2 body loop over players 2..count (P2-specific code) |
| `x < count` loop bounds | 121 | keep; but the per-player arrays these loops index in other subsystems are 2-wide (cameras 0x005D9148.., HUD 0x00600840/0x00600848[2], viewports) |
| `count > 0` (`blez`) | 72 | keep |
| Literal `i < 2` player loops in functions that also read the handle array | 11 functions: 0012ae58 001557f8 001573e8 00158728 001af010 001b1688 001cf468 001d1aa0 00229c40 004134f8 0041db08 | change to `i < count` together with the 4-wide arrays they index (most are camera/HUD) |
| Player-2-only code (constant +0x22C) | 21 functions (section 1.1) | review one by one: e.g. merge/distance between P1 and P2, P2 HUD, join/drop |
| FUN_00419A68 `+0x222` setter `< 2` | 1 | keep (HUD slots are 0/1 until HUD work) |
| MakePlayer HUD-slot loop `for i < 2` (FUN_001B2200) | 1 | HUD work (P3/P4 get HUD slot -1 today, F-0062) |

Classification by the comparison that follows each count load (ELF scan); VERIFIED for the listed sites, and the
meaning of each "multiplayer" test was read from the decompile.

## 4. How a human becomes a player, and how companions can become players 3 and 4
**MakePlayer(human, pad, hudSlot, playerSlot)** (0x00229C40). VERIFIED:
1. **Pad check.** Pad state for pad p is at 0x005DD810 + p*0x50 (+0x4C connected, +0x42 owning player index, -1 =
   free).
   - If the requested pad is connected and free, the human's controller record (FUN_0021D3E8 -> 0x00660F50 + i*0x2C)
     gets +0x19 = pad.
   - Otherwise: for player slots < 2 it takes the HUD's preferred pad; for other slots it scans pads 0..7 for one that
     is connected and free. If none is found and a player already exists, MakePlayer fails.
2. Earlier players' brains are refreshed. Then `GameMgr::AddPlayer`:
   - inserts the handle;
   - sets human+0x1B0 = player index;
   - fills record[i] with FUN_0018F7B0.
3. **HUD slot.** It tries HUD slots 0..1 and stores the result in human+0x380. The pad's owner (+0x42) becomes the
   player index.
4. **Brain and setup:**
   - switches the brain to player control (FUN_0021D408 -> FUN_0028EF48 / FUN_0028DB20 / FUN_0028D910 /
     FUN_0028CEB8);
   - sets the squad-leader flag human+0x3AC and character stats;
   - calls FUN_0041C4E0(GM, human, ...) to set up the per-player block;
   - camera/squad FUN_00166708.

**Original drop-in (player 2 joins a story mission):** `GameMgr::UpdateJoin` FUN_0041A460(gm, pad). VERIFIED.
- **Conditions:** join allowed (+0x56E8 from Lua `CfgMultiplayerJoin`), game mode +0x158 in {0, 3}, a free pad, and
  count != 2.
- **Choosing the companion:** `FUN_0022A770(player 1's squad (brain+0x20C), 0)` picks it. It walks the squad's 16
  member handles (squad+0x48), keeps humans that are not yet players (+0x1B0 == -1) and prefers the lowest non-zero
  +0x1B1 order. If the squad has none, it scans all Warriors-gang humans in the level.
- **Joining:**
  - MakePlayer(companion, pad, -1, -1);
  - +0x456 |= 1<<pad;
  - creates the player's camera (FUN_001222B0, FUN_0011EAF0(player index));
  - sends a script event (FUN_0041B148 via the script system DAT_00512B04);
  - lays out the viewports again.
- **Leaving:** for players 1..count-1 whose pad bit is set: ReleasePlayer(human, 1, 1) (0x0022A2A8) ->
  RemovePlayer(index) (0x00419C68, compacts arrays).

**For players 3 and 4:** the same path works once the limits in section 2.1 are raised, because FUN_0022A770 returns
the next non-player companion each time. Remaining blockers outside GameMgr:
- **Pads 1..3 / 5..7** are never opened or updated (PadInit 0x00149520, PadUpdateAll 0x001454A8; F-0054/55). Their
  +0x4C connected flag stays 0, so MakePlayer rejects them. They must be opened and polled (as in E4), and W4P's
  default `PadForSlot` mapping {0, 4, 1, 2} already assumes pads 1 and 2.
- **Per-player subsystem arrays of 2:** cameras 0x005D9148.., viewport objects 0x005FDEB8, HUD 0x00600840 slots and
  0x00600848[player] (FUN_0041DB08/DBE8 index it by player, out of bounds for P3/P4), ScreenEffects (the E4 crash,
  F-0062), audio listeners.
- **Lua:** scripts know only `player`/`player2`. Missions where no companion is available need an added character.
  It is a HYPOTHESIS that every story mission has 2 spare Warriors.

Starting from the session savestate: the enlarged GameMgr changes the heap layout from boot onwards. Old savestates
(e.g. `local/m1_start_m9_2p.p2s`) were made with a 0x57C0-byte GameMgr and must not be used with these patches. M2 tests
need new start states created with the patches active from boot.

## Summary
- **Patch sites:** the GameMgr storage part needs 32 code words plus 11 cave words (section 2.1), all checked against
  the ELF.
- **Approach:**
  - grow GameMgr from 0x57C0 to 0x5A00 (one word);
  - move the tick (+0x230) and the music handle (+0x234) to the new tail, so the player-handle array becomes 4 entries
    in place; the 164 functions that use it then need no change;
  - move the +0x222 s16 so the +0x220 slow-motion flags become 4;
  - move the 0x30-byte player records to +0x5800 and build 4 of them;
  - raise the AddPlayer cap (0x00419B48) and the join cap (0x0041A540, cave, because s5 = 2 is reused);
  - initialise handle[2] and the moved fields in a constructor cave.
- **Count checks:**
  - keep the 42 "is multiplayer" tests (`count < 2`), the 121 `i < count` loops and the 72 `count > 0` tests;
  - change the 2 `count == 2` tests (0x0023449C, 0x003032B0), the literal `i < 2` loops in 11 functions and the
    player-2-specific code in 21 functions.
- **Still to do in GameMgr:** the per-player block +0x414..+0x42F (8 small arrays, about 67 instructions in about 35
  functions) needs 4-wide copies in the new tail space. Options (+0x440/+0x448/+0x56DE) stay 2-wide, with players 3
  and 4 mapped to player 1's options.
- **Effort:** storage and limits are small (one session plus a runtime test). The per-player block is medium. The
  real M2 work is outside GameMgr: pads 1/2 polling, cameras, viewports, HUD 0x00600848[2], ScreenEffects and scripts.
- **Risks:**
  - the scan is heuristic, so a missed access to +0x230/+0x234 or to the records would read a player handle;
    mitigated by the exhaustive immediate scans for the records and by checking the decompile;
  - the RAM cave relies on F-0050;
  - old savestates are incompatible.
- **Labels:** VERIFIED for code facts; HYPOTHESIS for runtime behaviour, the meaning of +0x222 and the per-player
  status of +0x414/+0x416/+0x418/+0x41A/+0x41C.

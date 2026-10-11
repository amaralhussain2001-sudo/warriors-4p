# M2 research: inventory for players 3-4 (Flash revives, money, items)

Build: The Warriors SLUS-21215 v1.03 (`local/disc/SLUS_212.15`, opened read-only). Date: 2026-10-11.
Method: static analysis only, nothing was run. Sources: decompile `local/analysis/all/*.c`, `callers.pkl`,
`lua_bindings.tsv`, pseudo-Lua `local/analysis/pseudo/*.lua` (467 scripts), the earlier GameMgr dataflow scan
(`gm_all2.json`, offsets 0..0x5900), and our own disassembly of the ELF. Function and structure names are OUR labels
(the ELF is stripped). Addresses are static (ELF) unless marked. Every "was" word in Appendix A was read from the ELF
and checked with `python -I tools/note_patches.py check` (Appendix B).
Builds on `m2_combat34.md` section 3, `m2_gamemgr.md`, `m2_gamemgr_records.md`, `m2_hud_full.md` (B1) and
`m2_pads_cameras.md` section 3 (ScreenEffects mirror).

## Result in one paragraph
The inventory is one object at **GameMgr+0x480** (our label `Inv`, 0x1054 bytes). It holds a shared "bank" word, then
**one 0x3F4-byte record per slot (23 items x 0x2C bytes)** for slots 0-1, then a **checkpoint copy** of both records,
then four Lua callback names. Four records fit exactly where the two records and the copy are today
(4 x 0x3F4 = 0xFD0 = 2 x 0x7E8), so the fix keeps every `slot*0x3F4` address computation as it is and only:
widens 5 slot checks and 3 slot loops from 2 to 4, and rewrites the three copy/clear routines so the checkpoint copy
lives in free low RAM at **0x000E4000-0x000E4FCF**. Slots 0-1 keep their addresses and contents byte for byte; the
memory card stores only the shared bank word, which is unchanged in 1-2 player games. A Flash makes three code paths
reachable for players 3-4 that read the 2-entry ScreenEffects table 0x005FDEB8 with the player index (index 2/3 reads a
different pointer array), so the fragment also points them at the existing 4-entry mirror 0x000F0890. Block A (core)
is **47 words**; optional Block B (bank the money of players 3-4 at mission end) is 8 words. Check: 0 new problems.
Requires the groups `[warriors-4p 4p]` and `[warriors-4p 4p hud B1]` (B1 gives players 3-4 HUD slots 2/3, the index
most inventory code uses).

## 1. The inventory object `Inv` = GameMgr+0x480 (VERIFIED unless marked)
| Inv+ | GameMgr+ | Size | Content | Evidence |
|---|---|---|---|---|
| +0x000 | +0x480 | u32 | shared value; get/set/add `FUN_0041E3A8`/`FUN_0041E3B0`/`FUN_0041E398`; Lua `AddMoneyToBank`; mission end adds slot 0 and slot 1 money to it (`FUN_0015D160` 0x0015D3B0-0x0015D3F0); the only inventory value the memory-card save reads (`FUN_00421708`). Our label "bank" (meaning HYPOTHESIS) | decompile all_07.c:13783-13807, `FUN_0015D160`, `FUN_00421708` |
| +0x004 | +0x484 | 0x3F4 | record of slot 0 (23 items x 0x2C) | ctor `FUN_0041DF40` (0x0041DF74 `addiu s7,s2,4`, stride `fp = 0x3F4`, loop `sltiu v0,v1,2` at 0x0041DFE4) |
| +0x3F8 | +0x878 | 0x3F4 | record of slot 1 | same |
| +0x7EC | +0xC6C | 0x7E8 | **checkpoint copy** of +0x004..+0x7EB | `FUN_0041E0B8` copies +4 -> +0x7EC (0x0041E0B8-0x0041E160), `FUN_0041E168` copies back, `FUN_0041E218` clears counts in both |
| +0xFD4 | +0x1454 | char[0x20] | Lua function name, `CfgInventoryCallback` (`FUN_0041E460`); called with (item) on a notified change | `FUN_0041E5B0` 0x0041E8C4.. |
| +0xFF4 | +0x1474 | char[0x20] | `CfgHuInventoryCallback` (`FUN_0041E490`); called with (slot, item) | `FUN_0041E5B0` |
| +0x1014 | +0x1494 | char[0x20] | `CfgHuInventoryCallback2` (`FUN_0041E4C0`); called with (item) by `FUN_0041E520` | all_07.c:13905 |
| +0x1034 | +0x14B4 | char[0x20] | `CfgMoneyCallback` (`FUN_0041E4F0`); called with (slot, delta) when item 2 changes | `FUN_0041E5B0` |
| +0x1054 | +0x14D4 | | end of `Inv`; GameMgr+0x14D4 is the level table (`m2_gamemgr.md` 1.5) | |

Item entry (0x2C bytes, at `Inv + 4 + slot*0x3F4 + item*0x2C`):
| Off | Type | Content | Label |
|---|---|---|---|
| +0x00 | char[0x20] | internal name, e.g. "dyn_revival" (empty by default) | VERIFIED (`FUN_0041E250`, `FUN_00431378(.., 0x1F)`) |
| +0x20 | s32 | **count**; address `Inv + 0x24 + slot*0x3F4 + item*0x2C` | VERIFIED (`FUN_0041E420` 0x0041E454 `lw v0,0x24(v1)`) |
| +0x24 | u32 | CRC32 of the icon path (`FUN_00143F68`, table 0x005D91E0) | VERIFIED |
| +0x28 | u32 | 5th argument of `CfgInventoryItem` (10000 by default) | VERIFIED (field) / HYPOTHESIS (meaning: display time) |

Items (names from `CfgInventoryItem` in WAD 3772, `03772_dc3a59ca.lua:694-708`; limits from the ELF table 0x0058B300,
8 bytes per item = min, max; `FUN_0041DED0` adds 1 to the Flash limit when unlock flag (6,7) is set). VERIFIED.
| Item | Name | Max | Item | Name | Max |
|---|---|---|---|---|---|
| 1 | dyn_revival (Flash) | 3 (+1) | 8 | dyn_boltcutter | 1 |
| 2 | "none" (money) | 999 | 9 | dyn_special_key | 1 |
| 3 | dyn_spraycan | 9 | 10 | dyn_store_item | 999 |
| 4 | dyn_swhbld_super | 9 | 11 | dyn_carstereo | 999 |
| 5 | dyn_powercuffs | 9 | 12-15 | ledger, dragon, bagcoins, brownbag | 999 |
| 6 | dyn_key (skeleton key) | 9 | 0, 16-22 | unused | 0 |
| 7 | dyn_pass | 1 | | | |

### What "slot" is (VERIFIED, decompile of all 101 game call sites of the slot-checked functions)
| Index source | Call sites | Functions |
|---|---|---|
| HUD slot human+0x380 (directly or via a local) | 89 | 37, e.g. pickups `FUN_002334D0`, `FUN_0023BF00`, revive `FUN_00274EE0`, Flash use `FUN_002843F8`, HUD `FUN_001AF010` |
| player index human+0x1B0 | 6 | `FUN_00225FF0`, `FUN_00273C60`, `FUN_00285520` (x3), `FUN_002856B8` |
| the PlayerHUD's own slot | 4 | `FUN_001AADF0` (item 6), `FUN_001C68E8` (Flash), `FUN_001C96E0` (spray), `FUN_001BEBE8` (money) |
| constants 0 and 1 | 2 | `FUN_0015D160` (mission-end money to the bank) |
| Lua: player number - 1 | 13 wrappers | section 2 |

For players 1-2, HUD slot and player index are equal in normal play (HYPOTHESIS, same as `m2_gamemgr_records.md`).
For players 3-4 the HUD slot is -1 without the HUD B1 group (every +0x380 site then rejects them) and 2/3 with B1
(MakePlayer slot search 0..3 at 0x00229E84, in `[warriors-4p 4p hud B1]`). VERIFIED (pnach).

## 2. The inventory functions (0x0041DF40-0x0041F06F)
| Address | Our label | What it does | Slot handling (original) | Change |
|---|---|---|---|---|
| `FUN_0041DF40` | InvCtor | bank = 0, names/CRC/+0x28 = 10000 for every item of every slot, clears the 4 callback names, then InvSaveCheckpoint | loop `sltiu v0,v1,2` (0x0041DFE4) | loop 4 (A2) |
| `FUN_0041E040` | InvClear(clear) | clears callback names; if `clear`: counts = 0 in every slot, then InvSaveCheckpoint | loop `slti v0,a2,2` (0x0041E098) | loop 4 (A2) |
| `FUN_0041E0B8` | InvSaveCheckpoint | copy Inv+4..+0x7EB -> Inv+0x7EC | 2 records | rewritten: Inv+4..+0xFD3 -> 0x000E4000 (A3) |
| `FUN_0041E168` | InvRestoreCheckpoint | copy back | 2 records | rewritten: 0x000E4000 -> Inv+4..+0xFD3 (A4) |
| `FUN_0041E218` | InvClearSlot(slot) | counts = 0 in the live record and in the copy | via `FUN_0041EC60` | rewritten for the new copy (A5) |
| `FUN_0041E250` | InvDefineItem (`CfgInventoryItem`) | name, count, CRC, +0x28 of one item in every slot | loop end `addiu s6,s1,0x7E8` (0x0041E290) | end 0xFD0 (A2) |
| `FUN_0041E320`, `E348`, `E370`, `E3C0` | item CRC, +0x28, slot-0 count, slot-0 entry | read slot 0 only | none | none (definitions are the same in every slot) |
| `FUN_0041E3D8` | InvHas(slot, item) | count > 0 | `sltiu v0,a1,2` (0x0041E3D8) | 4 (A1) |
| `FUN_0041E420` | InvCount(slot, item) | count, else 0 | `sltiu v0,a1,2` (0x0041E420) | 4 (A1) |
| `FUN_0041E5B0` | InvAdd(slot, item, delta, notify) | add, clamp to 0x0058B300, spray hint, Lua callbacks | `sltiu v0,s3,2` (0x0041E5E0) | 4 (A1) |
| `FUN_0041E9D8` | InvSet(slot, item, value) | set, clamp | `sltiu v0,s1,2` (0x0041EA00) | 4 (A1) |
| `FUN_0041EC60` | InvReleaseSlot(slot) | InvClearSlot, returns slot or -1 | `sltiu v0,s0,2` (0x0041EC6C) | 4 (A1) |

All checks are unsigned, so slot -1 (AI humans, or a player without a HUD slot) stays rejected with the bound 4.
An exhaustive look at every immediate in 0x0041DF40-0x0041F06F (2, 0x7E4, 0x7E8, 0x7EC, 0xFCC, 0xFD4, -0x7C8, 0x3F4)
found exactly these 11 places that encode "2 slots". VERIFIED.

Lua bindings (all take a 1-based player number, default 1, and pass `p - 1` as the slot; VERIFIED all_06.c:1124-1368,
all_07.c:14183-14330):
| Lua | Binding | Wrapper | Core |
|---|---|---|---|
| InvGetSpraycanCharges(p) | 0x0037B038 | `FUN_0041F000` | InvCount(p-1, 3) |
| InvPlayerHasItem(item, p) | 0x0037B090 | `FUN_0041ED88` | InvHas |
| InvSetSpraycanCharges(n, p) | 0x0037B108 | `FUN_0041F030` | InvSet(p-1, 3, max(n,0)) |
| InvGiveRevive(n, p) / InvNumberRevives(p) | 0x0037B178 / 0x0037B1E8 | `FUN_0041EDB8` / `FUN_0041EDF0` | InvAdd(p-1, 1, n, 1) / InvCount(p-1, 1) |
| InvGiveSkeletonKey / InvNumberSkeletonKeys | 0x0037B268 / 0x0037B2D8 | `FUN_0041EE20` / `FUN_0041EE58` | item 6 |
| InvGetMoney(p) / InvSetMoney(n, p) | 0x0037B358 / 0x0037B3B0 | `FUN_0041EE88` / `FUN_0041EEB8` | item 2; InvSetMoney also writes PlayerHUD[p-1]+0xE20 = 0 with no check (B1 already reads T_A, 0x0041EEC0) |
| GiveMoney / TakeMoney (n, p) | 0x0037B458 / 0x0037B4C8 | `FUN_0041EF00` / `FUN_0041EF60` | InvAdd(p-1, 2, +-n, 1) |
| InvNumberOf(item, p) / InvGiveItem(item, n, p) | 0x0037B538 / 0x0037B5D8 | `FUN_0041EFD0` / `FUN_0041EF98` | InvCount / InvAdd |
| AddMoneyToBank(n) | 0x0037B420 | `FUN_0041EF38` | bank += n |
| CfgInventoryItem, CfgInventoryCallback, CfgHuInventoryCallback(2), CfgMoneyCallback | 0x0036BF58, 0x0036C038, 0x0036C068, 0x0036C098, 0x0036C0C8 | `FUN_0041ECA0`, `FUN_0041ECE8`..`FUN_0041ED60` | InvDefineItem, callback names |
| SetCheckPoint(n) | 0x0037B760 | `FUN_0041ABC0` | `FUN_0041CE98` (section 3) |

**Scripts pass only player numbers 1 and 2.** Every Inv* call in the 467 pseudo-Lua scripts has player argument 1
(105), 2 (94), the default 1 (30), a local set to 1 or 2 (L2, L3, L5, L6: 20), the cheat argument A2 (1 or 2, 7) or 0
(one `GiveMoney(25, 0)`, slot -1, rejected before and after). VERIFIED (grep + reading each local). So no script
reaches slots 2-3, before or after the patch.

## 3. Checkpoints, clears, saves (VERIFIED)
| Event | Path | Inventory effect |
|---|---|---|
| GameMgr constructed | `FUN_00418588` -> InvCtor (through the gamemgr cave 0x000F0720) -> InvClear(1) | all slots defined and zero; copy saved |
| Lua `SetCheckPoint(n)` | `FUN_0041ABC0` -> `FUN_0041CE98`: GameMgr+0x33A = n, InvSaveCheckpoint, stats copy `FUN_00422C60` | live -> copy |
| Level (re)start | `FUN_00418C68`: InvClear(GameMgr+0x33A < 2), InvRestoreCheckpoint, CfgInventoryCallback name cleared | checkpoint 0/1: everything zero; later checkpoint: items back to the checkpoint state |
| Retry path | `FUN_00155408` -> InvRestoreCheckpoint | copy -> live |
| Clear all | `FUN_001BDD38` (menu), `FUN_002A1B50` (a game-mode setup that then gives player 1 one Flash) | InvClear(1) |
| Player leaves | ReleasePlayer `FUN_0022A2A8` -> InvReleaseSlot(human+0x380) | that slot zero, live and copy |
| Memory card save/load | `FUN_00421708` / `FUN_00421AD0` read/write **only the bank word** (`FUN_0041E3A8` / `FUN_0041E3B0`); `FUN_00424D60` sets it to 1,000,000 | no per-player item is on the memory card |
| Lua-side keeping | free roam stores player/player2 items in `roam.playerInventory` around sub-missions (09513_aa7dbfe6.lua:1374-1420); level start items via WAD 4106 (`main_150` player 1; `main_152/153` "InventoryPlayer2": player 2 on the **first** join only, then `SetPlayer2Inventory = nil`) | 2-player, script level |

## 4. Revive (Flash) and pick-ups (VERIFIED code; meaning of each caller HYPOTHESIS where marked)
- **Flash on yourself:** `FUN_002843F8` (player button handler, our label) needs InvCount(slot, 1) != 0, player index
  != -1 and health < max; it starts animation 0x299, and `FUN_00284280` (our label UseFlash) runs at its end
  (`FUN_00245920` case 0xC1) or directly: InvAdd(slot, 1, -1), revive `FUN_0022EB40`, HUD `FUN_001B28A0` (slot-guarded),
  screen effect `FUN_0018B7D0(0x005FDEB8[player index], 0)` (section 6).
- **Flash for rage:** same handler, flag 0x2000000: spends a Flash, fills rage, `FUN_00284340` -> `FUN_00236D28`.
- **Partner revive:** `FUN_00286BA8` allows it if the downed human or the reviver has a Flash -> `FUN_002752A0`;
  the revive `FUN_00274EE0` spends the downed human's Flash first, else the reviver's.
- **AI gang revive:** `FUN_002BD808` (AI) goes to a downed player only if that player has a Flash (InvCount(slot, 1)).
- **Game over** `FUN_004197A8`: any player dead -> game over; all players down -> it checks player 1's Flash and
  state only (parity: player 2 is treated the same way).
- **Before the patch, for players 3-4** (VERIFIED code, HYPOTHESIS runtime): they can be revived with a partner's
  Flash, but never hold one, so they cannot use one, cannot revive others with their own, and the AI gang never comes
  for them. That is why their death ends the game sooner.
- **Pick-ups and spending** (call + arguments VERIFIED, purpose HYPOTHESIS): generic pick-up `FUN_002334D0`
  (InvAdd(slot, item, +1, notify)), typed pick-ups `FUN_0023BF00` (items 1/2/3/5/6/8/10/...), spray `FUN_00245920`,
  `FUN_00274710`, `FUN_00238DB0`, `FUN_00273C60`, money `FUN_00232C60`, `FUN_002E63E0`, `FUN_002E6668`, car stereo
  `FUN_0022E020` (+15 money, +1 item 11), stores `FUN_002C73B8`/`FUN_002C74D8`/`FUN_002C7C20`/`FUN_002AC5E0`, keys
  `FUN_0024D530`/`FUN_002811F0`, robbing a player `FUN_002856B8`/`FUN_00285520` (by player index).

## 5. Where four records can live (task 2)
| Option | Room | Verdict |
|---|---|---|
| After the two records inside `Inv` | none: +0x7EC..+0xFD3 is the checkpoint copy, +0xFD4..+0x1053 the callback names, then the level table | VERIFIED |
| GameMgr tail (grown to 0x5A80) | used: +0x57C0..+0x57CB, +0x5800..+0x58F7, +0x5900..+0x5A6F (`mod/m2/*.txt` grep); free: +0x5A70..+0x5A7F (16 bytes) | too small; growing GameMgr to 0x6A50 needs heap headroom that is unproven |
| **Chosen: 4 records in place, copy moved** | slots 2-3 take Inv+0x7EC..+0xFD3 (exactly the old copy); the 0xFD0-byte copy goes to low RAM 0x000E4000-0x000E4FCF | no index arithmetic changes; 47 words |
| Slots 2-3 elsewhere, layout kept | needs a cave in each of about 13 `slot*0x3F4` computations plus new copy routines anyway | rejected (larger, more risk) |

Free RAM check (VERIFIED, scan 2026-10-11): no line of `mod/w4p_m1.pnach` or `mod/m2/*.txt` writes 0x000E3200-0x000EFFFF,
and no `lui 0x0008..0x000F` + offset in their code builds an address there (pages used: 0x000A0000-0x000B4FFF,
0x000E0000-0x000E1FFF, 0x000E3000, 0x000F0000). No reference in `tests/`, `tools/` or the W4P fork sources. The range is
inside the coordinator's allocation 0x000E4000-0x000EFFFF. F-0050/F-0125: 0x00096000-0x000EFFFF reads zero in gameplay
(VERIFIED observation); that nothing else ever uses it is a HYPOTHESIS. The range is above `kGameRamStart` 0x000A0000,
so the copy is in the desync hash (fine: deterministic).

## 6. Code that a Flash makes reachable for players 3-4 (task 4, VERIFIED code)
Widening the checks changes nothing for a slot that is never 2/3. For players 3-4 it opens every "has item" branch. I
read every caller (section 1 table) and scanned the 95 functions reachable within two calls from the newly opened
branches (Flash use, Flash for rage, partner revive, key, spray, pick-ups) for static tables indexed by
human+0x1B0/+0x380:
- **Three ScreenEffects calls index the 2-entry table 0x005FDEB8 by player index:** `FUN_00284280` (UseFlash,
  0x0028430C/0x00284314), `FUN_00236D28` (rage start, 0x00236E34/0x00236E3C), `FUN_00236FB8` (rage end,
  0x0023700C/0x00237014/0x00237038). For index 2/3 they read 0x005FDEC0/0x005FDEC4, which is a separate array of 25
  pointers to 0x18-byte objects or 0 (filled at all_01.c:24148, cleared at all_01.c:23736). `FUN_0018B7D0` writes
  +0x194/+0x198/+0x19C and `FUN_0018B950` writes +0x198/+0x19C of that "object": a write past a small heap object, or
  into low memory 0x00000194.. when the entry is 0. None of the three is in the ScreenEffects mirror list of `m2_pads_cameras.md`.
  - `FUN_00284280` is reachable for players 3-4 **only** with a Flash: caused by this patch, fixed in A6.
  - `FUN_00236D28`/`FUN_00236FB8` are also reached by a full rage meter, so this is a **pre-existing bug** for players
    3-4 in the current build (rage works for them per `m2_combat34.md`). HYPOTHESIS: it has not shown up in tests
    because players 3-4 rarely fill rage. A6 fixes all three by reading the 4-entry mirror 0x000F0890 (entries 0/1 equal
    0x005FDEB8/0x005FDEBC, `m2_black_screen.md` table "fx0"); behaviour for players 1-2 is unchanged.
- Everything else is index-agnostic or already handled: per-player block writes after the revive check in
  `FUN_00164C20` (relocated to 4 entries by `control.txt`, in `[4p]`); PlayerHUD table reads in `FUN_002843F8`,
  `FUN_0022A2A8`, `FUN_002856B8` and the four +0x411C writers (B1 reads T_A); HUD-level panels `FUN_001B28A0`,
  `FUN_001B3C30`, `FUN_001B3B68/3BA8/3C78`, `FUN_001B28B8/28E8/2918` (own `slot < 2` guards); HudUpdate's inventory
  reads at 0x001B1218/0x001B139C/0x001B13B8 lie in the loop 0x001B11A0-0x001B1464 that `[4p]` clamps to 2 players
  (MIN2, 0x001B1450/0x001B145C); `FUN_0041EEB8` (B1 reads T_A).
- Scan limits: the table scan is a pattern search on the decompile (HYPOTHESIS for completeness); the GameMgr dataflow
  scan is linear per function. Neither found an access to Inv+0x7EC..+0xFD3 other than the three copy/clear routines.

## 7. The patch (Appendix A)
| Block | Part | Words | What |
|---|---|---|---|
| A | A1 | 5 | slot checks 2 -> 4: InvHas, InvCount, InvAdd, InvSet, InvReleaseSlot |
| A | A2 | 3 | slot loops 2 -> 4: InvCtor, InvClear, InvDefineItem (end Inv+0xFD0) |
| A | A3 | 11 | InvSaveCheckpoint rewritten in place: word copy Inv+4..+0xFD3 -> 0x000E4000 (6-instruction loop) |
| A | A4 | 11 | InvRestoreCheckpoint rewritten in place: 0x000E4000 -> Inv+4..+0xFD3 |
| A | A5 | 10 | InvClearSlot rewritten in place: counts of one slot, live (Inv+0x24+..) and copy (0x000E4020+..) |
| A | A6 | 7 | the three ScreenEffects calls read the mirror 0x000F0890 |
| B (optional) | B | 8 | mission end also banks the money of slots 2-3 (cave 0x000E5000, 7 words) |

Checks behind the rewrites (VERIFIED, our disassembly of the patched image):
- No jump, branch or data word outside the three routines points into them (ELF scan), and each is entered only by
  `jal` at its first word, so the dead remainder of the old copy loops is never executed.
- Registers: the new routines use only v0, v1, a0, a1, a2 (the originals already clobber v0, v1, a0-a3, t0).
  `Inv+4` = GameMgr+0x484 is word aligned (the original code reads GameMgr fields such as +0x228 with `lw`, so
  GameMgr is at least word aligned; the original copy loop took its unaligned `ldl/ldr` path only because of the
  8-byte test).
- InvClearSlot keeps the original `mult a1,a1,v0` and uses its result one instruction later, as the compiler does in
  `FUN_0041E3D8` (0x0041E3FC/0x0041E400).
- A6: in `FUN_00284280` and `FUN_00236FB8` the `lui` sits in a branch delay slot; on the taken paths v0 is dead
  (void return) and v1 is used only by the second patched `addiu` (0x00237038).
- Block B: at 0x0015D3F4 s0 = Inv (set at 0x0015D3DC, callee-saved); the cave uses v0/v1 only and tail-jumps to
  0x00155308 with the original return address.

What stays identical for players 1-2 (VERIFIED code / HYPOTHESIS runtime):
- slot 0-1 addresses, contents and every computation on them; the checkpoint copy of slots 0-1 has the same bytes, only
  at 0x000E4000;
- slots 2-3 stay zero in 1-2 player games (cleared at construction and level start; no script and no player reaches
  them), so the bank, and with it the memory card, is unchanged even with Block B;
- `Inv+0x7EC..+0xFD3` now holds slot 2-3 definitions and zero counts instead of the copy; nothing else reads it.
Timing differs slightly (the copy is a word loop of 1012 iterations, run only at checkpoints, level start and retry).

## 8. Risks
| Risk | Effect | Label / mitigation |
|---|---|---|
| Group dependency | A6 needs the mirror 0x000F0890 from `[4p]`; without `[4p]` UseFlash would read a zero pointer. B1 is needed for HUD slots 2/3, else players 3-4 still get nothing from the 89 HUD-slot sites | VERIFIED; ship the fragment inside or next to `[4p]` and only with B1 |
| Savestates made without the fragment | the old GameMgr holds the slot 0-1 copy at Inv+0x7EC (would appear as players 3-4 items) and 0x000E4000 is zero (a retry would wipe items) | VERIFIED code; boot fresh (already required by the GameMgr growth) |
| HUD slot != player index after a leave/rejoin (D7) | most code uses the HUD slot, 6 sites the player index; they can point at different slots for a while | HYPOTHESIS; same class as the records note; test T5 |
| Script callbacks get slot 2/3 | `F1.Health` (5 flashback missions): handler maps 0 -> Swan, 1 -> Ajax, else keeps the old human (nil -> no-op, the Hu* bindings are null-safe), then `F1.NoRevive` strips players 1-2's Flash; hobo hunger (03925) treats 2/3 as player 2; robin hood (09526) keeps the previous warrior; `C3` cash objective (07338) sums only players 1-2 | VERIFIED (scripts) / gameplay only, no crash found |
| Scripts give starting items only to players 1-2 | players 3-4 start each level with nothing (they can pick up and buy) | VERIFIED; open item 1 |
| HUD | players 3-4 see their counts in their PlayerHUD panel children (B1), but HUD-level inventory panels stay 2 entries | VERIFIED (S-guards); HUD work |
| Free RAM | 0x000E4000-0x000E501B relies on F-0050/F-0125 | HYPOTHESIS (always free) |
| Block B changes the bank in 4-player sessions | the money of players 3-4 is added to the shared bank that is saved | gameplay decision for the user; recommended (parity with player 2) |

## 9. Runtime test plan (bots, SINGLE-PC first, then 4-instance lockstep)
Setup as `m2_combat34.md` section 5: fresh boot (no old savestate), `[4p]`, `[4p hud B1]` (+B2), spawn groups, this
fragment, MTVU off. `gm = read32(0x0051489C)`, `Inv = gm + 0x480`.
PINE addresses (count of item k for slot s = `Inv + 0x24 + s*0x3F4 + k*0x2C`; copy = `0x000E4020 + s*0x3F4 + k*0x2C`):
| Item | slot 0 | slot 1 | slot 2 | slot 3 | copy slot 2 / 3 |
|---|---|---|---|---|---|
| Flash (1) | gm+0x4D0 | gm+0x8C4 | gm+0xCB8 | gm+0x10AC | 0x000E4834 / 0x000E4C28 |
| money (2) | gm+0x4FC | gm+0x8F0 | gm+0xCE4 | gm+0x10D8 | 0x000E4860 / 0x000E4C54 |
| spray (3) | gm+0x528 | gm+0x91C | gm+0xD10 | gm+0x1104 | 0x000E488C / 0x000E4C80 |
| key (6) | gm+0x5AC | gm+0x9A0 | gm+0xD94 | gm+0x1188 | 0x000E4910 / 0x000E4D04 |
Also: bank `read32(gm+0x480)`; slot s item 1 name at `gm+0x4B0 + s*0x3F4` ("dyn_revival" for s = 0..3 after the level
script ran); per player human+0x380 and human+0x1B0 (handles at gm+0x228.., object table as in `m2_combat34.md`);
ScreenEffects mirror `read32(0x000F0890 + 4*i)` for i = 0..3.

| Test | Steps | Pass |
|---|---|---|
| T0 layout | after the level script | names at slots 2-3 equal slots 0-1; counts of slots 2-3 = 0; human+0x380 = 2/3 for players 3/4 |
| T1 2-player regression | same 2-player run (same inputs) with and without the fragment; read slot 0-1 counts, the bank and `0x000E4000..+0x7E7` vs the old `Inv+0x7EC..+0xFD3` at each checkpoint | slot 0-1 values equal; copy bytes equal; bank equal; memory-card save file identical |
| T2 pick-up | player 3 (then 4) walks over a Flash / money / spray pick-up | its slot count rises; slots 0-1 unchanged |
| T3 Flash use | player 3 with a Flash (picked up, or PINE write32 on a single instance) gets hurt, presses the Flash button | count -1, health rises; DebugWatch on `read32(0x005FDEC0)+0x194..+0x19F` and 0x00000190-0x0000019F silent; mirror[2]+0x198 changes |
| T4 revive | player 3 knocked down without a Flash, player 4 with one revives him; then the AI gang revive with player 3 holding a Flash | reviver's (or downed player's) count -1, player 3 back up |
| T5 checkpoint | after a scripted checkpoint compare live slots 2-3 with 0x000E4834.. ; change the counts; die and retry | copy equals live at the checkpoint; after retry live equals copy |
| T6 leave | player 3 leaves (D7) | slot 2 counts and copy zero; check human+0x380 vs +0x1B0 of the remaining players |
| T7 bank (Block B) | finish a mission with money on players 3-4 | bank grows by the sum of all four slots (without B: slots 0-1 only) |
| T8 rage | player 3 fills rage and activates it | no write through 0x005FDEC0; mirror[2]+0x198 = 2 during rage |
| T9 lockstep | 4 instances, 20+ min with pick-ups, revives and a checkpoint | 0 hash mismatches, no TLB miss |

## 10. Left open
1. **Starting items for players 3-4.** WAD 4106 `main_150/152/153` give the level's items to player 1 and, on the
   first join, to player 2 only. Options: (a) leave it (players 3-4 start empty, can pick up/buy; recommended for now);
   (b) script work: call the player-2 part for every joining player with that player's number; (c) a C cave on join that
   copies the level-start values (the values live only in the Lua table `MS[Level]`, so this needs (b) anyway).
2. Scripts that know only player/player2 (section 8 row "Script callbacks", roam `playerInventory`, `C3` cash sum).
3. HUD-level inventory panels for players 3-4 (HUD work; the PlayerHUD children already show their counts with B1).
4. Game over with all players down checks only player 1's Flash (parity with the original 2-player rule).

## Summary
- `Inv` = GameMgr+0x480: bank word, 2 x 0x3F4 records (23 items x 0x2C: name, count +0x20, icon CRC, +0x28), a
  0x7E8-byte checkpoint copy, 4 Lua callback names; 0x1054 bytes. The memory card saves only the bank word.
- "Slot" is mostly the HUD slot (89 sites), sometimes the player index (6), Lua uses player number - 1; scripts pass
  only 1 and 2.
- Fix: 4 records in place (Inv+4..+0xFD3), checkpoint copy moved to 0x000E4000-0x000E4FCF; 5 checks and 3 loops
  widened, 3 routines rewritten in place; plus 7 words so the Flash/rage screen effect of players 3-4 reads the
  4-entry ScreenEffects mirror (this also fixes a pre-existing rage bug for players 3-4). Block A 47 words, optional
  Block B 8 words (bank money of players 3-4). `note_patches.py check`: 0 new problems.
- Slots 0-1 and the memory card are unchanged for 1-2 player games (VERIFIED code, HYPOTHESIS until T1).
- Open: starting items for players 3-4 (script work), script callbacks that know only 2 players, HUD-level panels.

## Appendix A: patch fragment
Apply inside or next to `[warriors-4p 4p]`, only together with `[warriors-4p 4p hud B1]`. Block B is optional.
```
// Block A (core): 4 inventory records at GameMgr+0x484..+0xFD3 (slots 2-3 take the place of the old checkpoint copy);
// the checkpoint copy (4 x 0x3F4 = 0xFD0 bytes) moves to free low RAM 0x000E4000..0x000E4FCF.
// A1 slot bounds 2 -> 4 (unsigned compares, so -1 = AI is still rejected)
patch=2,EE,0041E3D8,word,2CA20004 // was 2CA20002 sltiu v0,a1,2 -> sltiu v0,a1,4; FUN_0041e3d8 (has item)
patch=2,EE,0041E420,word,2CA20004 // was 2CA20002 sltiu v0,a1,2 -> sltiu v0,a1,4; FUN_0041e420 (get count)
patch=2,EE,0041E5E0,word,2E620004 // was 2E620002 sltiu v0,s3,2 -> sltiu v0,s3,4; FUN_0041e5b0 (add count)
patch=2,EE,0041EA00,word,2E220004 // was 2E220002 sltiu v0,s1,2 -> sltiu v0,s1,4; FUN_0041e9d8 (set count)
patch=2,EE,0041EC6C,word,2E020004 // was 2E020002 sltiu v0,s0,2 -> sltiu v0,s0,4; FUN_0041ec60 (clear slot, ReleasePlayer)
// A2 loops over slots 2 -> 4
patch=2,EE,0041DFE4,word,2C620004 // was 2C620002 sltiu v0,v1,2 -> sltiu v0,v1,4; FUN_0041df40 ctor: init 4 records
patch=2,EE,0041E098,word,28C20004 // was 28C20002 slti v0,a2,2 -> slti v0,a2,4; FUN_0041e040: clear counts of 4 records
patch=2,EE,0041E290,word,26360FD0 // was 263607E8 addiu s6,s1,0x7e8 -> addiu s6,s1,0xfd0; FUN_0041e250 (CfgInventoryItem): define item in 4 records
// A3 FUN_0041e0b8 SaveCheckpoint (our label): copy I+4..I+0xFD3 -> 0x000E4000 (was I+4..I+0x7EB -> I+0x7EC); a0 = I = GameMgr+0x480
patch=2,EE,0041E0B8,word,3C05000E // was 248507EC addiu a1,a0,0x7ec -> lui a1,0x000e
// 0x0041E0BC stays 24830004 addiu v1,a0,4 (src)
patch=2,EE,0041E0C0,word,34A54000 // was 00651025 or v0,v1,a1 -> ori a1,a1,0x4000 (dst 0x000E4000)
patch=2,EE,0041E0C4,word,24840FD4 // was 30420007 andi v0,v0,7 -> addiu a0,a0,0xfd4 (src end)
patch=2,EE,0041E0C8,word,8C620000 // was 10400016 beq v0,zero,0x0041e124 -> loop: lw v0,0(v1)
patch=2,EE,0041E0CC,word,24630004 // was 248407E4 addiu a0,a0,0x7e4 -> addiu v1,v1,4
patch=2,EE,0041E0D0,word,ACA20000 // was 68620007 ldl v0,7(v1) -> sw v0,0(a1)
patch=2,EE,0041E0D4,word,24A50004 // was 6C620000 ldr v0,0(v1) -> addiu a1,a1,4
patch=2,EE,0041E0D8,word,1464FFFB // was 6866000F ldl a2,15(v1) -> bne v1,a0,0x0041e0c8
patch=2,EE,0041E0DC,word,00000000 // was 6C660008 ldr a2,8(v1) -> nop (delay; loop is 6 instructions, R5900 short-loop rule)
patch=2,EE,0041E0E0,word,03E00008 // was 68670017 ldl a3,23(v1) -> jr ra
patch=2,EE,0041E0E4,word,00000000 // was 6C670010 ldr a3,16(v1) -> nop
// A4 FUN_0041e168 RestoreCheckpoint (our label): copy 0x000E4000 -> I+4..I+0xFD3
// 0x0041E168 stays 24850004 addiu a1,a0,4 (dst)
patch=2,EE,0041E16C,word,3C03000E // was 248307EC addiu v1,a0,0x7ec -> lui v1,0x000e
patch=2,EE,0041E170,word,34634000 // was 00651025 or v0,v1,a1 -> ori v1,v1,0x4000 (src 0x000E4000)
patch=2,EE,0041E174,word,24840FD4 // was 30420007 andi v0,v0,7 -> addiu a0,a0,0xfd4 (dst end)
patch=2,EE,0041E178,word,8C620000 // was 10400016 beq v0,zero,0x0041e1d4 -> loop: lw v0,0(v1)
patch=2,EE,0041E17C,word,24630004 // was 24840FCC addiu a0,a0,0xfcc -> addiu v1,v1,4
patch=2,EE,0041E180,word,ACA20000 // was 68620007 ldl v0,7(v1) -> sw v0,0(a1)
patch=2,EE,0041E184,word,24A50004 // was 6C620000 ldr v0,0(v1) -> addiu a1,a1,4
patch=2,EE,0041E188,word,14A4FFFB // was 6866000F ldl a2,15(v1) -> bne a1,a0,0x0041e178
patch=2,EE,0041E18C,word,00000000 // was 6C660008 ldr a2,8(v1) -> nop (delay)
patch=2,EE,0041E190,word,03E00008 // was 68670017 ldl a3,23(v1) -> jr ra
patch=2,EE,0041E194,word,00000000 // was 6C670010 ldr a3,16(v1) -> nop
// A5 FUN_0041e218 ClearSlot (our label; a0 = I, a1 = slot < 4): zero the 23 counts of the slot, live and checkpoint copy
// 0x0041E218 stays 240203F4 addiu v0,zero,0x3f4; 0x0041E220 stays 00A22818 mult a1,a1,v0 (a1 = slot*0x3F4)
patch=2,EE,0041E21C,word,3C06000E // was 248407EC addiu a0,a0,0x7ec -> lui a2,0x000e
patch=2,EE,0041E224,word,00852021 // was 0000182D move v1,zero -> addu a0,a0,a1 (I + slot*0x3F4)
patch=2,EE,0041E228,word,00C53021 // was 00A42821 addu a1,a1,a0 -> addu a2,a2,a1 (0x000E0000 + slot*0x3F4)
patch=2,EE,0041E22C,word,248303F4 // was 00000000 nop -> addiu v1,a0,0x3f4 (end = 23 items)
patch=2,EE,0041E230,word,AC800024 // was ACA0F838 sw zero,-0x7c8(a1) -> loop: sw zero,0x24(a0) (live count, item+0x20)
patch=2,EE,0041E234,word,ACC04020 // was 24630001 addiu v1,v1,1 -> sw zero,0x4020(a2) (copy count at 0x000E4000+...+0x20)
patch=2,EE,0041E238,word,2484002C // was ACA00020 sw zero,0x20(a1) -> addiu a0,a0,0x2c
patch=2,EE,0041E23C,word,24C6002C // was 2C620017 sltiu v0,v1,23 -> addiu a2,a2,0x2c
patch=2,EE,0041E240,word,1483FFFB // was 1440FFFB bne v0,zero,0x0041e230 -> bne a0,v1,0x0041e230
patch=2,EE,0041E244,word,00000000 // was 24A5002C addiu a1,a1,0x2c -> nop (delay)
// 0x0041E248/0x0041E24C stay jr ra / nop
// A6 ScreenEffects calls indexed by player index (human+0x1B0) read the 2-entry table 0x005FDEB8; index 2/3 reads the
// pointer array at 0x005FDEC0. A Flash makes these paths reachable for players 3-4 (Flash use -> FUN_00284280;
// Flash-for-rage -> FUN_00284340 -> FUN_00236d28; rage end -> FUN_00236fb8). Use the 4-entry mirror 0x000F0890
// of [warriors-4p 4p] (m2_pads_cameras.md section 3; entries 0/1 equal 0x005FDEB8/0x005FDEBC).
patch=2,EE,0028430C,word,3C02000F // was 3C020060 lui v0,0x60 -> lui v0,0xf; FUN_00284280 (Flash use) (delay slot; v0 dead on the taken path)
patch=2,EE,00284314,word,24420890 // was 2442DEB8 addiu v0,v0,-0x2148 -> addiu v0,v0,0x890; FUN_00284280 table 0x000F0890
patch=2,EE,00236E34,word,3C02000F // was 3C020060 lui v0,0x60 -> lui v0,0xf; FUN_00236d28 (rage start effect, mode 2)
patch=2,EE,00236E3C,word,24420890 // was 2442DEB8 addiu v0,v0,-0x2148 -> addiu v0,v0,0x890; FUN_00236d28 table 0x000F0890
patch=2,EE,0023700C,word,3C03000F // was 3C030060 lui v1,0x60 -> lui v1,0xf; FUN_00236fb8 (delay slot shared by both paths)
patch=2,EE,00237014,word,24630890 // was 2463DEB8 addiu v1,v1,-0x2148 -> addiu v1,v1,0x890; FUN_00236fb8 path s1 != 0 (mode 3)
patch=2,EE,00237038,word,24630890 // was 2463DEB8 addiu v1,v1,-0x2148 -> addiu v1,v1,0x890; FUN_00236fb8 path s1 == 0 (mode 2)
// Block B (optional, gameplay decision): bank the money of players 3-4 at mission end like players 1-2 (FUN_0015d160).
// s0 = GameMgr+0x480 at 0x0015D3F4 (set at 0x0015D3DC). Money of slot s = I+0x7C+s*0x3F4.
patch=2,EE,0015D3F4,word,0C039400 // was 0C0554C2 jal 0x00155308 -> jal 0x000E5000 (cave, then j 0x00155308)
patch=2,EE,000E5000,word,8E020000 // lw v0,0(s0)       bank (inventory+0)
patch=2,EE,000E5004,word,8E030864 // lw v1,0x864(s0)   slot 2 money
patch=2,EE,000E5008,word,00431021 // addu v0,v0,v1
patch=2,EE,000E500C,word,8E030C58 // lw v1,0xc58(s0)   slot 3 money
patch=2,EE,000E5010,word,00431021 // addu v0,v0,v1
patch=2,EE,000E5014,word,080554C2 // j 0x00155308 (SSMC_StartSaveSequence core, as the original jal)
patch=2,EE,000E5018,word,AE020000 // sw v0,0(s0) (delay)
```

## Appendix B: check output (2026-10-11)
```
python -I tools/note_patches.py check <fragment>
checked 55 addresses in 1 files: 0 problems
python -I tools/note_patches.py check mod/w4p_m1.pnach
checked 1857 addresses in 1 files: 6 problems      (the 6 known B1-over-A supersessions inside the pnach)
python -I tools/note_patches.py check mod/w4p_m1.pnach <fragment>
checked 1912 addresses in 2 files: 6 problems      (the same 6; 0 new)
```

# M2 research: HUD crash with players 3 and 4, interim guards and full design (static analysis, 2026-10-11)

This note covers:
- why the game crashed about 6 s after players 3 and 4 were created (`local/m2/m2i`);
- a minimal interim patch so that players 3-4 simply have no HUD (no crash, no memory corruption);
- the design for a full 4-player HUD;
- every per-player HUD array that indexes 2-3 out of bounds.

Sources and conventions:
- **Static analysis only; nothing was run.** Build: SLUS-21215 v1.03 (`local/disc/SLUS_212.15`).
- Sources: the Ghidra decompile `local/analysis/all/*.c`, disassembly of the ELF words, and the runtime log
  `local/pcsx2/inst6/PCSX2/logs/emulog.txt` (run m2i).
- Function names are OUR labels. HUD = the static HUD manager object at **0x00600840** (F-0061, `m2_hud_scripts.md`).
- Every "was" word below was read from the ELF.
- The patch block in section 3.3 was checked with `python -I tools/note_patches.py check <block> mod/w4p_m1.pnach`:
  0 problems. There is no address conflict with the current mod, all originals match, and the caves lie outside the
  ELF image.

---

## 1. The crash chain (VERIFIED)

1. `FUN_00158728` (in-game update, main loop) calls **HudUpdate** `FUN_001AF010(0x00600840, ...)` every frame
   (calls at all_00.c:61083 and :61175).
2. HudUpdate has two per-player loops bounded by the GameMgr player count:
   - `lh v0,0x224(v1)` at 0x001B1178 / 0x001B145C;
   - `lh v0,0x224(v1)` at 0x001B1474 / 0x001B15E4.

   With count = 4 they run for index 2 and 3.
3. Loop 2 (0x001B1498-0x001B15F0, index in s3) works on per-player objects at **HUD+0x6B40 + i*0x590**.
   - Only two exist: 0x00607380 and 0x00607910.
   - For i = 2 the address is HUD+0x7660 = 0x00607EA0. That is not such an object; its first word (the "vtable") is 0.
4. When the per-player stack entry is 0, the loop calls `FUN_001B2490(HUD, i)`, which calls
   `FUN_0019F128(HUD + i*0x590 + 0x6B40, 0, 0, 0)`.
5. In `FUN_0019F128`:
   - `lw v1,0(s0)` (0x0019F148) loads vtable 0;
   - `lh a0,0x58(v1)` (0x0019F14C) and `lw ...,0x5C(v1)` read addresses **0x58 and 0x5C**;
   - `jalr` then jumps to 0, so execution continues at pc 0.
6. The emulog shows `TLB Miss, pc=0x19f128 addr=0x58`, then `addr=0x5c`, then `pc=0x0 addr=0x0 ...`. The recompiler
   reports the block start 0x0019F128. This matches step 5 exactly.

The other paths crash too:
- The other branch of the same loop (non-zero stack entry) calls the same vtable directly at 0x001B1574.
- `FUN_0019F1B0` also starts with that vtable call.

So index 2 crashes on either path. Before the crash, the same loop also writes `*(HUD[8 + 4*i]) + 0x411C = 0` when
Select is pressed. For i = 2/3 that pointer is the first word of the embedded object at HUD+0x10 / HUD+0x14, so this is
memory corruption.

**Why 6 s later and not at once:** HYPOTHESIS, not checked. The per-player part of HudUpdate may be skipped while the
tutorial message holds the HUD, and run as soon as the normal HUD comes back.

## 2. Root cause: the HUD exists for exactly two players (VERIFIED)

- **HUD slots.** `MakePlayer` (0x00229C40) asks the HUD for a slot.
  - It loops with `sltiu v0,s0,2` (0x00229E84) around `FUN_001B2200(HUD, human, slot)`.
  - `FUN_001B2200` itself refuses slot >= 2 (`slti v0,s1,2` at 0x001B2220).
  - So players 3-4 get **human+0x380 = -1**. This was also seen at runtime in E4 (F-0062).
- **Player index.** Players 3-4 have human+0x1B0 = 2 / 3, and every loop bounded by the player count reaches i = 2, 3.

HUD code therefore fails in three ways for players 3-4:
1. Count-bounded loops index 2-entry HUD arrays with i = 2, 3.
2. Code that uses the HUD slot (+0x380) without checking for -1 reads `(&DAT_00600848)[-1]` = **HUD+4**, then writes
   through it. HUD+4 is a pointer to a different object; `FUN_001C7488` uses it as `*(HUD+4)+0x19`.
3. Code that uses the player index (+0x1B0) as a HUD index reads HUD+0x10 / HUD+0x14 or other neighbouring fields.
   HUD+0x10 is an embedded object, used as such by `FUN_001B39A0` / `FUN_001B3960`.

Many HUD API functions are already safe, because AI humans always had slot -1:
- they test `slot != -1`: `FUN_001B22F0`, `FUN_001B23D0`, `FUN_001B2400`, `FUN_001B2430`, `FUN_001B2460`;
- or they test `slot < 2` unsigned: `FUN_001B28B8`, `FUN_001B28E8`, `FUN_001B2918`, `FUN_001B2950`, `FUN_001B3B68`,
  `FUN_001B3BA8`, `FUN_001B3C78`, and the inventory functions `FUN_0041E5B0`, `FUN_0041E420`, `FUN_0041EC60`.

The unsafe ones are listed in section 5.

## 3. Option (A), interim: players 3-4 have no HUD (recommended first)

### 3.1 Design
| Guard | Where | What it does | Words |
|---|---|---|---|
| MIN2 cave | 0x000F0C00 (9 words) | returns v0 = min(player count, 2) and v1 = GameMgr | 9 |
| HudUpdate loops | 0x001B1450/0x001B145C, 0x001B15D4/0x001B15E4 | the loop end uses MIN2 instead of the count; the "count > 0" pre-checks stay | 4 |
| HUD tick loop `FUN_001B1688` | 0x001B1B7C/0x001B1B80 | same; this stops `FUN_001CB798` reading the slot table 0x0050EA90 with slot -1 | 2 |
| Main-loop pause/prompt block | 0x00158ECC/0x00158ED4 + cave 0x000F0C40 (11 words) | skips the per-player PlayerHUD block (Start opens pause, prompt dismiss) for player index >= 2, and keeps the original "pause already opened" test | 2 + 11 |
| Overhead markers `FUN_0024A230` | 0x0024A2D4, 0x0024ABD8 | its "is a player" tests (`nor`, meaning "index != -1") become `sltiu ...,2`, so players 3-4 never write the 2-entry marker globals (0x00510530/38/40, 0x006C72C8) | 2 |
| Slot guards S1-S7 | entries of `FUN_001B28A0`, `FUN_001B39E0`, `FUN_001B3B38`, `FUN_001B3C00`, `FUN_001B3C30`, radar `FUN_001B26A8`, `FUN_001B2790`; caves 0x000F0C80-0x000F0DC3 | return at once unless `slot (a1) < 2` unsigned, which rejects -1, 2 and 3 | 7 x (2 + 9) |
| PlayerHUD-pointer guards V1-V4 | entries of `FUN_001C0648` (+0x3480), `FUN_001C7890` (+0x70), `FUN_001A6D28` (+0x1EF0), `FUN_001A6C38` (+0x1EF0); caves 0x000F0DD0-0x000F0EC7 | return at once unless a0 is `PlayerHUD[0]+off` or `PlayerHUD[1]+off`; the pointers are read live from 0x00600848/0x0060084C | 4 x (2 + 14) |

Total: 171 words, of which 28 are changed game words and 143 are cave words in 0x000F0C00-0x000F0ECF.

Checks behind the design (all VERIFIED):
- **No branches into the replaced windows.** No branch in HudUpdate, `FUN_001B1688` or the main loop targets
  0x001B1454-0x001B145C, 0x001B15D8-0x001B15E4, 0x001B1B80 or 0x00158ED0-0x00158ED4.
- **Every guarded function is safe to hook at its entry:**
  - no `j`/`jal` goes to entry+4, and no data (vtable) reference points at the entry;
  - the first two words are plain instructions (no branch, nothing PC-relative);
  - the word before the entry is the previous function's `jr ra` delay slot, so there is no fall-through;
  - the function returns nothing (void in the decompile, and callers ignore v0).
- **Caller counts:** `FUN_001B28A0` 2, `FUN_001B39E0` 1, `FUN_001B3B38` 1, `FUN_001B3C00` 1, `FUN_001B3C30` 1,
  `FUN_001B26A8` 1, `FUN_001B2790` 4, `FUN_001C0648` 4, `FUN_001C7890` 1, `FUN_001A6D28` 1, `FUN_001A6C38` 3. Every
  V-guard caller passes `(&DAT_00600848)[x] + off`.
- **Registers:**
  - MIN2 clobbers v0, v1 and at; afterwards v1 = GameMgr, as in the original.
  - The main-loop cave uses its own 16-byte frame and makes the replaced `jal 0x0021D3E8` call itself. It then sets
    a0 = `iStack_c0 (caller sp+96) | (s3 >= 2)`.
  - s3 is the loop's player index: `daddu s3,zero,zero` at 0x00158D68, `addiu s3,s3,1` at 0x00159058, and
    `sw s3,0x1BC0(v1)` (pause owner) at 0x00158F9C.
  - S-guards use `at`. V-guards use v0/v1 (return registers, dead at entry). t0-t3 are avoided because the EE EABI may
    pass arguments in them.
  - All callers save ra (they contain `jal`).
- **Free RAM:**
  - 0x000F0C00-0x000F0FFF and 0x000F0940-0x000F0A7F are not written by `mod/w4p_m1.pnach`, and no cave in it uses a
    0x000F base offset >= 0x900 (scan, 2026-10-11).
  - F-0050 found 0x00096000-0x000FFFFF reads as zero in gameplay. That it is always free remains a HYPOTHESIS.

### 3.2 What players 3-4 will see and not see (HYPOTHESIS until runtime)
- **No HUD for players 3-4:** no health/rage panel, no radar, no pickup or target indicator, no inventory panel.
- **Game state continues:** the game itself keeps their health, items and rage.
  - The inventory functions already ignore slot -1, so their item pickups are not shown.
  - The pickups are probably not stored either: `FUN_0041E5B0` returns for slot > 1.
- **No pause from players 3-4:** pressing Start does nothing, because the pause menu needs a PlayerHUD. Pause in
  sessions should come from the W4P session policy later (§4.6).
- **Overhead marker:** drawn without the per-player blink/flash state, and it reads "2P" (`FUN_0024B2A8` picks "1P"
  only for index 0).
- **Players 1-2 are unchanged:** every guard passes slots 0/1 and loop indices 0/1 exactly as before.

### 3.3 Patch block (group proposal `[warriors-4p 4p hud-safe]`, apply together with `[warriors-4p 4p]`)
Like the existing caves, these caves are written every frame by place 2; they are code, not live data.
```
patch=2,EE,000F0C00,word,3C030051 // lui v1,0x51
patch=2,EE,000F0C04,word,8C63489C // lw v1,0x489c(v1)  GameMgr
patch=2,EE,000F0C08,word,84620224 // lh v0,0x224(v1)  player count
patch=2,EE,000F0C0C,word,28410003 // slti at,v0,3
patch=2,EE,000F0C10,word,14200002 // bne at,zero,+2 (count < 3: keep)
patch=2,EE,000F0C14,word,00000000 // nop
patch=2,EE,000F0C18,word,24020002 // addiu v0,zero,2  (clamp)
patch=2,EE,000F0C1C,word,03E00008 // jr ra
patch=2,EE,000F0C20,word,00000000 // nop
patch=2,EE,000F0C40,word,27BDFFF0 // addiu sp,sp,-16
patch=2,EE,000F0C44,word,FFBF0000 // sd ra,0(sp)
patch=2,EE,000F0C48,word,0C0874FA // jal 0x0021D3E8  (the call we replaced)
patch=2,EE,000F0C4C,word,00000000 // nop
patch=2,EE,000F0C50,word,DFBF0000 // ld ra,0(sp)
patch=2,EE,000F0C54,word,8FA40070 // lw a0,112(sp)  caller's sp+96 (pause-opened flag)
patch=2,EE,000F0C58,word,2E610002 // sltiu at,s3,2  s3 = player index
patch=2,EE,000F0C5C,word,38210001 // xori at,at,1  at = index >= 2
patch=2,EE,000F0C60,word,00812025 // or a0,a0,at
patch=2,EE,000F0C64,word,03E00008 // jr ra
patch=2,EE,000F0C68,word,27BD0010 // addiu sp,sp,16
patch=2,EE,001B1450,word,0C03C300 // was 8C83489C; HudUpdate loop end: lw v1,0x489c(a0) -> jal MIN2 (delay slot unchanged)
patch=2,EE,001B15D4,word,0C03C300 // was 8C83489C; HudUpdate loop end: lw v1,0x489c(a0) -> jal MIN2 (delay slot unchanged)
patch=2,EE,001B145C,word,00000000 // was 84620224; HudUpdate loop end: lh v0,0x224(v1) -> nop (v0 from MIN2)
patch=2,EE,001B15E4,word,00000000 // was 84620224; HudUpdate loop end: lh v0,0x224(v1) -> nop (v0 from MIN2)
patch=2,EE,001B1B7C,word,0C03C300 // was 8C43489C; FUN_001b1688 loop end: lw v1,0x489c(v0) -> jal MIN2
patch=2,EE,001B1B80,word,00000000 // was 84620224; FUN_001b1688: lh v0,0x224(v1) (was the delay slot) -> nop
patch=2,EE,00158ECC,word,0C03C310 // was 0C0874FA; main loop: jal 0x0021D3E8 -> jal MAIN (same call + skip flag)
patch=2,EE,00158ED4,word,00000000 // was 8FA40060; main loop: lw a0,96(sp) -> nop (a0 set by MAIN)
patch=2,EE,0024A2D4,word,2C620002 // was 00031027; FUN_0024a230: nor v0,zero,v1 -> sltiu v0,v1,2 (skip marker flags for index -1 or >= 2)
patch=2,EE,0024ABD8,word,2C420002 // was 00021027; FUN_0024a230: nor v0,zero,v0 -> sltiu v0,v0,2
patch=2,EE,000F0C80,word,2CA10002 // sltiu at,a1,2  (FUN_001b28a0 HUD+0x225D0+slot byte)
patch=2,EE,000F0C84,word,10200005 // beq at,zero,+5 (reject)
patch=2,EE,000F0C88,word,00000000 // nop
patch=2,EE,000F0C8C,word,3C020002 // original 001B28A0
patch=2,EE,000F0C90,word,344225D0 // original 001B28A4
patch=2,EE,000F0C94,word,0806CA2A // j 001B28A8
patch=2,EE,000F0C98,word,00000000 // nop
patch=2,EE,000F0C9C,word,03E00008 // reject: jr ra
patch=2,EE,000F0CA0,word,00000000 // nop
patch=2,EE,001B28A0,word,0803C320 // was 3C020002; entry -> j guard 000F0C80
patch=2,EE,001B28A4,word,00000000 // was 344225D0; entry+4 -> nop (moved to the guard)
patch=2,EE,000F0CB0,word,2CA10002 // sltiu at,a1,2  (FUN_001b39e0 HUD+0xF420+slot*0x540)
patch=2,EE,000F0CB4,word,10200005 // beq at,zero,+5 (reject)
patch=2,EE,000F0CB8,word,00000000 // nop
patch=2,EE,000F0CBC,word,27BDFF80 // original 001B39E0
patch=2,EE,000F0CC0,word,24020540 // original 001B39E4
patch=2,EE,000F0CC4,word,0806CE7A // j 001B39E8
patch=2,EE,000F0CC8,word,00000000 // nop
patch=2,EE,000F0CCC,word,03E00008 // reject: jr ra
patch=2,EE,000F0CD0,word,00000000 // nop
patch=2,EE,001B39E0,word,0803C32C // was 27BDFF80; entry -> j guard 000F0CB0
patch=2,EE,001B39E4,word,00000000 // was 24020540; entry+4 -> nop (moved to the guard)
patch=2,EE,000F0CE0,word,2CA10002 // sltiu at,a1,2  (FUN_001b3b38 HUD+0xF420+slot*0x540)
patch=2,EE,000F0CE4,word,10200005 // beq at,zero,+5 (reject)
patch=2,EE,000F0CE8,word,00000000 // nop
patch=2,EE,000F0CEC,word,24030540 // original 001B3B38
patch=2,EE,000F0CF0,word,3406F420 // original 001B3B3C
patch=2,EE,000F0CF4,word,0806CED0 // j 001B3B40
patch=2,EE,000F0CF8,word,00000000 // nop
patch=2,EE,000F0CFC,word,03E00008 // reject: jr ra
patch=2,EE,000F0D00,word,00000000 // nop
patch=2,EE,001B3B38,word,0803C338 // was 24030540; entry -> j guard 000F0CE0
patch=2,EE,001B3B3C,word,00000000 // was 3406F420; entry+4 -> nop (moved to the guard)
patch=2,EE,000F0D10,word,2CA10002 // sltiu at,a1,2  (FUN_001b3c00 HUD+0xFEA0+slot*0xB10)
patch=2,EE,000F0D14,word,10200005 // beq at,zero,+5 (reject)
patch=2,EE,000F0D18,word,00000000 // nop
patch=2,EE,000F0D1C,word,24020B10 // original 001B3C00
patch=2,EE,000F0D20,word,3403FEA0 // original 001B3C04
patch=2,EE,000F0D24,word,0806CF02 // j 001B3C08
patch=2,EE,000F0D28,word,00000000 // nop
patch=2,EE,000F0D2C,word,03E00008 // reject: jr ra
patch=2,EE,000F0D30,word,00000000 // nop
patch=2,EE,001B3C00,word,0803C344 // was 24020B10; entry -> j guard 000F0D10
patch=2,EE,001B3C04,word,00000000 // was 3403FEA0; entry+4 -> nop (moved to the guard)
patch=2,EE,000F0D40,word,2CA10002 // sltiu at,a1,2  (FUN_001b3c30 HUD+0xFEA0+slot*0xB10 (virtual call))
patch=2,EE,000F0D44,word,10200005 // beq at,zero,+5 (reject)
patch=2,EE,000F0D48,word,00000000 // nop
patch=2,EE,000F0D4C,word,24020B10 // original 001B3C30
patch=2,EE,000F0D50,word,27BDFFF0 // original 001B3C34
patch=2,EE,000F0D54,word,0806CF0E // j 001B3C38
patch=2,EE,000F0D58,word,00000000 // nop
patch=2,EE,000F0D5C,word,03E00008 // reject: jr ra
patch=2,EE,000F0D60,word,00000000 // nop
patch=2,EE,001B3C30,word,0803C350 // was 24020B10; entry -> j guard 000F0D40
patch=2,EE,001B3C34,word,00000000 // was 27BDFFF0; entry+4 -> nop (moved to the guard)
patch=2,EE,000F0D70,word,2CA10002 // sltiu at,a1,2  (FUN_001b26a8 radar HUD+0x15D0+i*0x2940)
patch=2,EE,000F0D74,word,10200005 // beq at,zero,+5 (reject)
patch=2,EE,000F0D78,word,00000000 // nop
patch=2,EE,000F0D7C,word,27BDFFB0 // original 001B26A8
patch=2,EE,000F0D80,word,3C020001 // original 001B26AC
patch=2,EE,000F0D84,word,0806C9AC // j 001B26B0
patch=2,EE,000F0D88,word,00000000 // nop
patch=2,EE,000F0D8C,word,03E00008 // reject: jr ra
patch=2,EE,000F0D90,word,00000000 // nop
patch=2,EE,001B26A8,word,0803C35C // was 27BDFFB0; entry -> j guard 000F0D70
patch=2,EE,001B26AC,word,00000000 // was 3C020001; entry+4 -> nop (moved to the guard)
patch=2,EE,000F0DA0,word,2CA10002 // sltiu at,a1,2  (FUN_001b2790 radar HUD+0x15D0+i*0x2940)
patch=2,EE,000F0DA4,word,10200005 // beq at,zero,+5 (reject)
patch=2,EE,000F0DA8,word,00000000 // nop
patch=2,EE,000F0DAC,word,27BDFFD0 // original 001B2790
patch=2,EE,000F0DB0,word,3C020051 // original 001B2794
patch=2,EE,000F0DB4,word,0806C9E6 // j 001B2798
patch=2,EE,000F0DB8,word,00000000 // nop
patch=2,EE,000F0DBC,word,03E00008 // reject: jr ra
patch=2,EE,000F0DC0,word,00000000 // nop
patch=2,EE,001B2790,word,0803C368 // was 27BDFFD0; entry -> j guard 000F0DA0
patch=2,EE,001B2794,word,00000000 // was 3C020051; entry+4 -> nop (moved to the guard)
patch=2,EE,000F0DD0,word,3C020060 // lui v0,0x60  (FUN_001c0648 PlayerHUD+0x3480)
patch=2,EE,000F0DD4,word,8C430848 // lw v1,0x848(v0)  PlayerHUD[0]
patch=2,EE,000F0DD8,word,24633480 // addiu v1,v1,0x3480
patch=2,EE,000F0DDC,word,10830006 // beq a0,v1,ok
patch=2,EE,000F0DE0,word,8C43084C // lw v1,0x84c(v0)  PlayerHUD[1] (delay slot)
patch=2,EE,000F0DE4,word,24633480 // addiu v1,v1,0x3480
patch=2,EE,000F0DE8,word,10830003 // beq a0,v1,ok
patch=2,EE,000F0DEC,word,00000000 // nop
patch=2,EE,000F0DF0,word,03E00008 // reject: jr ra
patch=2,EE,000F0DF4,word,00000000 // nop
patch=2,EE,000F0DF8,word,27BDFF30 // ok: original 001C0648
patch=2,EE,000F0DFC,word,0080382D // original 001C064C
patch=2,EE,000F0E00,word,08070194 // j 001C0650
patch=2,EE,000F0E04,word,00000000 // nop
patch=2,EE,001C0648,word,0803C374 // was 27BDFF30; entry -> j guard 000F0DD0
patch=2,EE,001C064C,word,00000000 // was 0080382D; entry+4 -> nop (moved to the guard)
patch=2,EE,000F0E10,word,3C020060 // lui v0,0x60  (FUN_001c7890 PlayerHUD+0x70)
patch=2,EE,000F0E14,word,8C430848 // lw v1,0x848(v0)  PlayerHUD[0]
patch=2,EE,000F0E18,word,24630070 // addiu v1,v1,0x70
patch=2,EE,000F0E1C,word,10830006 // beq a0,v1,ok
patch=2,EE,000F0E20,word,8C43084C // lw v1,0x84c(v0)  PlayerHUD[1] (delay slot)
patch=2,EE,000F0E24,word,24630070 // addiu v1,v1,0x70
patch=2,EE,000F0E28,word,10830003 // beq a0,v1,ok
patch=2,EE,000F0E2C,word,00000000 // nop
patch=2,EE,000F0E30,word,03E00008 // reject: jr ra
patch=2,EE,000F0E34,word,00000000 // nop
patch=2,EE,000F0E38,word,27BDFFC0 // ok: original 001C7890
patch=2,EE,000F0E3C,word,0000282D // original 001C7894
patch=2,EE,000F0E40,word,08071E26 // j 001C7898
patch=2,EE,000F0E44,word,00000000 // nop
patch=2,EE,001C7890,word,0803C384 // was 27BDFFC0; entry -> j guard 000F0E10
patch=2,EE,001C7894,word,00000000 // was 0000282D; entry+4 -> nop (moved to the guard)
patch=2,EE,000F0E50,word,3C020060 // lui v0,0x60  (FUN_001a6d28 PlayerHUD+0x1EF0)
patch=2,EE,000F0E54,word,8C430848 // lw v1,0x848(v0)  PlayerHUD[0]
patch=2,EE,000F0E58,word,24631EF0 // addiu v1,v1,0x1EF0
patch=2,EE,000F0E5C,word,10830006 // beq a0,v1,ok
patch=2,EE,000F0E60,word,8C43084C // lw v1,0x84c(v0)  PlayerHUD[1] (delay slot)
patch=2,EE,000F0E64,word,24631EF0 // addiu v1,v1,0x1EF0
patch=2,EE,000F0E68,word,10830003 // beq a0,v1,ok
patch=2,EE,000F0E6C,word,00000000 // nop
patch=2,EE,000F0E70,word,03E00008 // reject: jr ra
patch=2,EE,000F0E74,word,00000000 // nop
patch=2,EE,000F0E78,word,27BDFF70 // ok: original 001A6D28
patch=2,EE,000F0E7C,word,7FB20060 // original 001A6D2C
patch=2,EE,000F0E80,word,08069B4C // j 001A6D30
patch=2,EE,000F0E84,word,00000000 // nop
patch=2,EE,001A6D28,word,0803C394 // was 27BDFF70; entry -> j guard 000F0E50
patch=2,EE,001A6D2C,word,00000000 // was 7FB20060; entry+4 -> nop (moved to the guard)
patch=2,EE,000F0E90,word,3C020060 // lui v0,0x60  (FUN_001a6c38 PlayerHUD+0x1EF0)
patch=2,EE,000F0E94,word,8C430848 // lw v1,0x848(v0)  PlayerHUD[0]
patch=2,EE,000F0E98,word,24631EF0 // addiu v1,v1,0x1EF0
patch=2,EE,000F0E9C,word,10830006 // beq a0,v1,ok
patch=2,EE,000F0EA0,word,8C43084C // lw v1,0x84c(v0)  PlayerHUD[1] (delay slot)
patch=2,EE,000F0EA4,word,24631EF0 // addiu v1,v1,0x1EF0
patch=2,EE,000F0EA8,word,10830003 // beq a0,v1,ok
patch=2,EE,000F0EAC,word,00000000 // nop
patch=2,EE,000F0EB0,word,03E00008 // reject: jr ra
patch=2,EE,000F0EB4,word,00000000 // nop
patch=2,EE,000F0EB8,word,27BDFFF0 // ok: original 001A6C38
patch=2,EE,000F0EBC,word,FFBF0000 // original 001A6C3C
patch=2,EE,000F0EC0,word,08069B10 // j 001A6C40
patch=2,EE,000F0EC4,word,00000000 // nop
patch=2,EE,001A6C38,word,0803C3A4 // was 27BDFFF0; entry -> j guard 000F0E90
patch=2,EE,001A6C3C,word,00000000 // was FFBF0000; entry+4 -> nop (moved to the guard)
```
To regenerate, run the scratch script `hud34/gen.py` (copy in this session's scratchpad), or rebuild the words from
section 3.1.

### 3.4 Residual risks of (A)
- **A player leaving while 3-4 players are in (D7).** HYPOTHESIS; the D7 leave logic must re-assign HUD slots.
  - `RemovePlayer` compacts the player arrays. If player 2 leaves, player 3 becomes index 1 but keeps HUD slot -1,
    while PlayerHUD 1 is released.
  - HudUpdate (clamped to 2) would then drive PlayerHUD 1 with player 3's data.
  - `FUN_001C7928` (widget-to-human search by slot, all_01.c) can end its search on a slot -1 player and write
    `*(HUD+4)+0x411C`.
- **The GameMgr per-player block (not HUD):**
  - `FUN_0041DBE8` (Lua give-item, index = human+0x1B0) writes GameMgr+0x41E+i*7+n;
  - `FUN_002843F8` reads GameMgr+0x42E+i;
  - for i = 2/3 these hit the neighbouring per-player fields until the block relocation planned in `m2_gamemgr.md`
    §1.3/§2.2 is patched. Their HUD part is covered by V4/V3.
- **Out-of-range reads that remain** (no write, wrong values only):
  - `FUN_002843F8` reads `*((&DAT_00600848)[slot]) + 0x1EFC`. If HUD+4 holds 0, this read lands in kernel RAM at
    0x1EFC (mapped, no fault).
  - `FUN_0024B780` reads `(&DAT_00510530)[i]` and `(&DAT_00622E10)[i]` (= HUD+0x225D0+i) for i = 2/3.
- **Lua bindings** that take a script player number (`FUN_001B4438`, `FUN_001B3F58`, `FUN_001B46A0`, `FUN_001B4948`,
  `FUN_0041EEB8`) are unsafe only if a script passes 2/3 as a player. Current scripts know only `player`/`player2`
  (`m2_hud_scripts.md` §2), and `FUN_001B4438` treats 2 as "both".

## 4. Option (B), full: four PlayerHUDs (design, no words yet)

### 4.1 Per-player HUD storage that must become 4 wide (VERIFIED offsets; sizes from strides)
| Member | Location | Stride | Extra for players 3-4 | Users |
|---|---|---|---|---|
| PlayerHUD pointer array | HUD+0x8 (0x00600848) | 4 | 8 B; **cannot grow in place** (HUD+0x10 is an embedded object) | about 24 functions with `(&DAT_00600848)[i]`, plus HUD-relative `HUD+8+4*i` in `FUN_001B2200` ... `FUN_001B2918`, HudUpdate and the main loop |
| PlayerHUD objects | HUD+0x19130 (embedded; in levels 60-69 they are 0x4620-byte heap objects from `FUN_0020FD80`) | 0x4A50 | 0x94A0 (38,048 B) | built by the `FUN_001AD588` loop `sltiu v0,s3,2` at 0x001AE278 |
| Radar objects | HUD+0x15D0 | 0x2940 | 0x5280 (21,120 B) | `FUN_001B2610/2658/26A8/2790`, HudUpdate; radar patch 2A is 2-player |
| Target/pickup objects | HUD+0x6B40 | 0x590 | 0xB20 (2,848 B) | HudUpdate loops, `FUN_001B2490`; built by the `FUN_001AD588` loop at 0x001ADB78 |
| Inventory panels | HUD+0xEBC0 | 0x430 | 0x860 | `FUN_001B3B68/3BA8/3C78` |
| Weapon/item panels | HUD+0xF420 | 0x540 | 0xA80 | `FUN_001B39E0/3B38`, HudUpdate; built by the loop at 0x001ADD28 |
| Special-move panels | HUD+0xFEA0 | 0xB10 | 0x1620 | `FUN_001B2950/3C00/3C30` |
| HudUpdate fixed-2 blocks | HUD+0x135E0 / +0x137E0 (0x100), +0x9970 (0x3F0), +0x14AE0 (0x560) | | about 0x1910 | HudUpdate `uVar < 2` loops |
| Small arrays | HUD+0x177BC (4), HUD+0x225D0 (1) | | 8 + 2 B | HudUpdate, `FUN_001B3E20`, `FUN_001B28A0`, `FUN_0024B780` |
| Static layout tables | 0x0050FA10 (+0x10), 0x0050FA40 (+0x240), 0x0050FF00 (+0xC0), 0x0050EA90 (+0x30), 0x0050E8C0 (+0x10) | | 4-entry copies | `FUN_00211EF8`, `FUN_00212840`, `FUN_001CB798`, `FUN_001BECB0` |
| Marker globals | 0x00510530 / 38 / 40 (+4), 0x006C72C8 (+4) | | 4-entry copies | `FUN_0024A230`, `FUN_0024B780` |

The extra objects need about 75-80 KB in total.
- **That does not fit the free RAM at 0x000F0000-0x000FFFFF:** it is 64 KB in total, and caves already use about 4 KB.
- So the PlayerHUD and radar objects must come from the game heap, as the levels 60-69 PlayerHUDs already do.
- Whether the heap has room is a HYPOTHESIS; the camera/effects work in `m2_pads_cameras.md` already adds about 12 KB.
- Only the small arrays and tables fit in free RAM: the pointer array, the per-player words and the layout tables,
  about 0x1000 B in total. For example, the 4-entry PlayerHUD pointer table can go at 0x000F0940 (unused, verified
  above).

### 4.2 Limits to raise once storage exists (originals VERIFIED; do not apply before 4.1)
| Address | Was | Becomes | Meaning |
|---|---|---|---|
| 0x00229E84 | 2E020002 `sltiu v0,s0,2` | 2E020004 | MakePlayer HUD slot search |
| 0x001B2220 | 2A220002 `slti v0,s1,2` | 2A220004 | `FUN_001B2200` slot limit |
| 0x001AE278 | 2E620002 `sltiu v0,s3,2` | 2E620004 | `FUN_001AD588` PlayerHUD construction loop |
| 0x001ADB78 | 2E420002 `sltiu v0,s2,2` | 2E420004 | `FUN_001AD588` target-object loop (0x590) |
| 0x001ADD28 | 2E420002 `sltiu v0,s2,2` | 2E420004 | `FUN_001AD588` panel loop (0x540) |
| 0x0021285C | 2EA20002 `sltiu v0,s5,2` | 2EA20004 | `FUN_00212840` panel init |

Each loop above walks a base pointer by its stride. Raising the count without relocating the storage would therefore
build objects over the following HUD fields. Once (B) is in, the S/V guards of (A) become `< 4` and a 4-entry pointer
check.

### 4.3 Approach and alternatives
- **Recommended:**
  1. Relocate the PlayerHUD pointer table to free RAM, about 30 sites: every `0x00600848/0x0060084C` access and every
     `HUD+8+4*i` access.
  2. Allocate PlayerHUD, radar and panel objects 3-4 on the heap in `FUN_001AD588`.
  3. Give each per-player embedded array a 4-entry relocated copy.
  4. Draw each player's HUD in its own view (`m2_hud_scripts.md` §1.3, per-view HUD camera).

  Effort: large, comparable to the camera relocation (about 150-300 words), and needing a lot of runtime testing.
- **Rejected: binding PlayerHUD 0 to the *local* player on each PC.** HUD objects are EE state, and the simulation
  reads them: the main loop calls PlayerHUD vtable +0x8C before it opens the pause menu (0x00158F34). PCs would
  diverge, and the full-RAM hash would report it.
- **Rejected: aliasing players 3-4 to PlayerHUD 0/1 (slot 0/1).** It would show their health, pickups and specials on
  player 1-2's HUD. It would also release player 1's HUD widget when player 3 leaves (`FUN_0022A2A8` calls
  `FUN_001C7890`).

## 5. Every per-player HUD access that goes out of range for players 3-4 (task 3)
| # | Function (our label) | Access | Index source | Effect for players 3-4 | Covered by (A) |
|---|---|---|---|---|---|
| 1 | HudUpdate `FUN_001AF010` loop 1 | HUD+0x6BA8+i*0x590, HUD+0x177BC+4i, `FUN_001B3E20(HUD,i)` | count loop | reads/writes neighbouring HUD fields | MIN2 |
| 2 | HudUpdate loop 2 | HUD+0x6B40+i*0x590 (vtable call), `*(HUD+8+4i)+0x411C = 0` | count loop | **crash** (section 1); write through HUD+0x10/0x14 | MIN2 |
| 3 | `FUN_001B1688` -> `FUN_001CB798(HUD+0x9540, human)` | table 0x0050EA90 + slot*0x30 | count loop, slot -1 | reads table entry -1, draws at a wrong position | MIN2 |
| 4 | main loop `FUN_00158728` | `*(0x00600848+4i)` vtable +0x8C/+0x24/+0x7C | count loop (Start / GameMgr+0x11C) | crash when player 3/4 presses Start | main-loop cave |
| 5 | `FUN_0024A230` markers | 0x00510530/38/40[i], 0x006C72C8[i] | human+0x1B0 | overwrites player 1-2 marker state and the flag 0x006C72D0 | 2 words |
| 6 | `FUN_001B28A0` | HUD+0x225D0+slot (byte) | +0x380 (`FUN_00284280`) or loop index (`FUN_0024B780`) | byte write into a neighbouring field | S1 |
| 7 | `FUN_001B39E0`, `FUN_001B3B38` | HUD+0xF420+slot*0x540 | +0x380 (`FUN_0022D790`, `FUN_0022D908`) | calls on a bogus panel | S2, S3 |
| 8 | `FUN_001B3C00`, `FUN_001B3C30` | HUD+0xFEA0+slot*0xB10 (vtable) | +0x380 (`FUN_0022DD98`, `FUN_0022E020`) | crash | S4, S5 |
| 9 | `FUN_001B26A8`, `FUN_001B2790` | radar HUD+0x15D0+i*0x2940 | player index (`FUN_0023EAB8`) | calls on a bogus radar | S6, S7 |
| 10 | `FUN_002833C0`, `FUN_00283A30`, `FUN_002856B8`, `FUN_00286550` | `FUN_001C0648((&DAT_00600848)[slot]+0x3480, n)` | +0x380 | write through `*(HUD+4)` | V1 |
| 11 | `FUN_0022A2A8` (ReleasePlayer) | `FUN_001C7890((&DAT_00600848)[slot]+0x70)` | +0x380, when +0x1B0 > 0 | write through `*(HUD+4)` when player 3/4 leaves | V2 |
| 12 | `FUN_002843F8` | `FUN_001A6D28(PlayerHUD[slot]+0x1EF0)`, read `+0x1EFC` | +0x380 | call on a bogus object; the read remains | V3 (call) |
| 13 | `FUN_0041DBE8` (Lua), `FUN_001B4948` (Lua); `FUN_0041DB08` loops < 2 and is safe | `FUN_001A6C38(PlayerHUD[i]+0x1EF0)` | human+0x1B0 / script number | write through HUD+0x10/0x14 | V4 |
| 14 | `FUN_001C7928` | `*(PlayerHUD[slot]+0x411C) = 0` | slot of the human found for the widget | safe while players 1-2 stay (section 3.4) | no |
| 15 | `FUN_001B4438`, `FUN_001B3F58`, `FUN_001B46A0`, `FUN_0041EEB8` | PlayerHUD[i] | script player number | safe with current scripts | no |

Already safe (VERIFIED):
- `FUN_001AAE58`, `FUN_001AB038`, `FUN_001C6950`, `FUN_001C9748` and `FUN_001BECB0`: the index is the owning
  PlayerHUD's own slot, and they are called from `FUN_00214138`.
- `FUN_001DCB20` and `FUN_0041DB08`: fixed loops of 2.
- `FUN_00214138`, `FUN_001A6D28` and `FUN_001C7890`: they search players by slot.
- The `FUN_0024B780` stack marker array: 4 entries of 12 bytes (init loop `iVar9 = 3 ... != -1`).
- Every API function listed in section 2.

## Summary
**The crash** is in HudUpdate's second per-player loop.
- The loop is bounded by the player count, which is now 4.
- For player 3 it calls the vtable of a 3rd "target/pickup" object at HUD+0x6B40+2*0x590, which does not exist
  (vtable 0).
- `FUN_001B2490` calls `FUN_0019F128`, which reads 0x58/0x5C and jumps to 0. That is exactly the emulog pattern.

**Root cause:** the HUD is built for two players. Players 3-4 get HUD slot -1 from MakePlayer and player indices 2-3,
and both reach 2-entry HUD arrays.

**Recommendation: apply (A) first.** It is 171 words, checked against the ELF and the current mod. It:
- clamps the three HUD count loops to 2 with one shared cave;
- skips the main-loop PlayerHUD block for players >= 2;
- makes the marker code treat players 2-3 as "not a player";
- puts entry guards on 7 slot-indexed HUD functions and 4 PlayerHUD sub-object functions.

Players 3-4 then have no HUD and cannot open the pause menu. Nothing writes outside the 2-player structures, so the M2
engine tests can run.

Confidence:
- high for the crash chain and the guard code (VERIFIED by disassembly);
- medium that no other HUD path exists (HYPOTHESIS until a 30-minute 4-player run).

**(B)** is a large separate task. It needs:
- about 75-80 KB of extra HUD objects, from the heap rather than the 64 KB of free RAM;
- a relocated PlayerHUD pointer table (about 30 sites);
- 4-entry copies of 5 static tables and of the marker globals;
- then the 6 limit words in section 4.2, plus per-view HUD drawing.

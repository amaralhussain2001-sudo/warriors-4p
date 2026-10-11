# M2: views 3-4 dark, and the TLB misses at 0x0017D880 (static analysis, 2026-10-11)

Static analysis only: decompile `local/analysis/all/*.c` and ELF `local/disc/SLUS_212.15`. Nothing was run.
Function names are our labels. Runtime facts come from the parent's run `local/m2/v4d`:
- views = 4 and cameras = 4;
- the bottom row (views of players 3 and 4) is dark;
- `TLB Miss, pc=0x17d880 addr=0x11` appears 50 times in about 1.6 s.

## 1. The TLB misses: the light manager has per-view data for 2 views only (VERIFIED)

**Light manager.**
- Global pointer `DAT_0050CCE4`.
- Allocated with size 0xC0 in the function at all_01.c:14150 (`alloc(..., 0xc0, 0x10, ...)`).
- Constructor `LightMgr::ctor`, `FUN_0017D338`.

**What the constructor does.** A loop of **2** (0x0017D468-0x0017D490, `sltiu v0,s2,2`) does this for i = 0, 1:
- stores sprite-slot id 7+i at +0x10+2i;
- stores the slot pointer `FUN_00185AB0(spriteMgr 0x0050CD4C, 7+i)` at **+0xB0+4i**.

The slots are sprite/particle batches (`FUN_001828E0` builds them; `FUN_00182DE0` adds a sprite only when slot+0x11 and slot+0x10 are set). +0xB8/+0xBC are the last 8 bytes of the 0xC0 block. Nothing in the constructor writes them.

**Per-view render** (`FUN_00156408` / `FUN_00156540`). For every view v < views (`FUN_0011EAE0` = 0x0050B198):
- `FUN_0017EA60(lm, v)`:
  - time-of-day colours;
  - then `FUN_0017E7E8` = memset(0x00715300, 0, 0x90), which empties the per-view light lists;
  - then `FUN_0017D880(lm, v)`;
- then `FUN_0040D0A8(.., v)`, which applies the light list for that view (`FUN_0017E810` walks the list at 0x00715300, count 0x00715320).

**`FUN_0017D880(lm, v)` (per-view light gathering).**
- 0x0017D898 `sll v0,a1,2`, 0x0017D8A0 `addu v0,s6,v0`.
- 0x0017D8D0 `lw v1,0xb0(v0)`: the slot of view v.
- 0x0017D8D4 `lbu a0,0x11(v1)`.
- 0x0017D8D8 `beq a0,zero,skip-all`.
- For v = 2 and 3 it reads lm+0xB8/+0xBC. In the run that word was 0, so the load hit address 0x11. PCSX2 reports the start of the recompiled block, 0x0017D880, as pc.
- The same array is read again in `FUN_0017CAA8(.., view)` at 0x0017D004 (`lw s0,0xb0(v1)`). That is the per-light halo sprite, called from inside `FUN_0017D880`.

**Scan of the light-manager code (0x0017B000-0x0017F400).** It finds +0xB0 used only at 0x0017D458 (constructor), 0x0017D004 and 0x0017D8D0. The +0xB8/+0xBC hits at 0x0017E50C/10 are a vtable `lh`/`lw` pair on another object, and the `lbu ..,0xb8` hits are fields of light objects.
- VERIFIED that +0xB8/+0xBC of the manager are not used by its own code.
- HYPOTHESIS that they are struct padding.

## 2. Why views 3-4 are dark (HYPOTHESIS, follows from section 1)

For views 2-3 the light list is emptied (`FUN_0017E7E8`) and then never rebuilt, because `FUN_0017D880` faults or skips. So those views are drawn without the dynamic lights (street lamps). Mission 1 is at night, so they look almost black, while the HUD still draws.

I have no static explanation for why the misses stop after about 1.6 s. One possibility is that the word at lm+0xB8 changed from 0 to a pointer whose +0x11 is 0, which means "skip gathering" and gives the same darkness.

**Ruled out or minor (VERIFIED from code):**
- **ScreenEffects for views 2-3.** fx[2] and fx[3] exist (mirror at 0x000F0890). In their constructor (`FUN_0018B1E0`) the fade fields are +0x1D4 = +0x1D8 = 0 and the tint colour +0x1BC/+0x1C4 = `DAT_005FD300`, which has alpha 0 (all_01.c:12624-12640). So `FUN_0018CE58` and `FUN_0018CA50` draw nothing. They do not cause the darkness.
- **Missing patch found while checking.** The ScreenEffects reset loop bound `patch=2,EE,0018C154,word,2EA70004` (m2_pads_cameras.md §3) is **missing from `mod/m2/engine.txt`**. It sits inline in a bullet, so the extractor skipped it; it is the only such miss in all M2 notes. fx[2] and fx[3] are therefore never reset at level load, and +0x1AC/+0x1B0/+0x1C8/+0x1CC stay uninitialised. It is included below.
- **The other per-view calls from the world render** (`FUN_0040E8D8`: `FUN_00174320`, `FUN_0017FD78`, `FUN_00411D10`) show no 2-entry per-view arrays. `FUN_00174320` already limits its per-view slot 9+v to v < 2.
- **Per-view 3D/HUD cameras.** The render manager (`FUN_00194D58`, vtable 0x00538D78) builds 4 of each. `ViewportRect` (`FUN_00195C78`) works per view.

## 3. Fix: give views 2-3 the light slots of views 0-1 (7 words; checker 0 problems)

At the end of the constructor's slot loop, set +0xB8 = +0xB0 and +0xBC = +0xB4.
- Hook the constructor's call to `FUN_0017E7E8` at 0x0017D494. Its delay slot `daddu a0,s3,zero` already gives a0 = manager.
- The cave tail-calls the original function, so `ra` (0x0017D49C) is kept. t0 is caller-saved and free across the call.

Both readers (0x0017D8D0 and 0x0017D004) then work for views 2-3 with no further patches.

```
patch=2,EE,0017D494,word,0C03C3F0 // was 0C05F9FA (jal 0x0017E7E8) -> jal 0x000F0FC0; delay slot daddu a0,s3,zero kept
patch=2,EE,000F0FC0,word,8C8800B0 // lw t0,0xb0(a0)   slot of view 0
patch=2,EE,000F0FC4,word,AC8800B8 // sw t0,0xb8(a0)   view 2 uses it
patch=2,EE,000F0FC8,word,8C8800B4 // lw t0,0xb4(a0)   slot of view 1
patch=2,EE,000F0FCC,word,0805F9FA // j 0x0017E7E8     original call; returns to 0x0017D49C
patch=2,EE,000F0FD0,word,AC8800BC // sw t0,0xbc(a0)   view 3 uses it (delay slot)
patch=2,EE,0018C154,word,2EA70004 // was 2EA70002: ScreenEffects reset loop over 4 entries (missing from engine.txt)
```

**Checks (VERIFIED):**
- The original words 0C05F9FA at 0x0017D494 and 2EA70002 at 0x0018C154 match the ELF.
- The cave 0x000F0FC0-0x000F0FFF is outside the ELF segments and unused by `mod/w4p_m1.pnach`.
- `python -I tools/note_patches.py check mod/w4p_m1.pnach <fragment>`: 854 addresses, 0 problems.
- Re-disassembled with the fragment applied: `jal 0x000f0fc0` with the delay slot intact; the cave reads `lw/sw/lw/j 0x0017e7e8/sw`.
- No branch targets 0x0017D494.

**Placement.**
- The manager is built by game code after boot, so the place-2 code patch is in effect.
- If the manager is rebuilt per level, the hook runs again. HYPOTHESIS: it is rebuilt.

**Side effect (HYPOTHESIS, cosmetic).** Light halos for views 2-3 go into the batches of views 0-1. They may show at the right world position only where views 0-1 look, or not at all in views 2-3.

A separate pair of slots would need slots that already exist, with +0x10/+0x11 set. Slots 9/10 are taken: `FUN_00174320` uses 9+v. A new dynamic slot from `FUN_0018AEC0` starts with +0x11 = 0, which would make `FUN_0017D880` skip the lights again. So sharing the slots of views 0-1 is the smallest working option.

## 4. PINE reads to confirm (single instance, after players 3-4 exist and views = 4)

| Read | Expected before fix | Expected after fix |
|---|---|---|
| `lm = read32(0x0050CCE4)`; `read32(lm+0xB0)`, `read32(lm+0xB4)` | `mgr+7*0x78+0x189C` and `mgr+8*0x78+0x189C` with `mgr = read32(0x0050CD4C)` | same |
| `read32(lm+0xB8)`, `read32(lm+0xBC)` | 0 (the TLB-miss source), or later a pointer whose +0x11 byte is 0 | equal to +0xB0 / +0xB4 |
| `read8(read32(lm+0xB0)+0x11)` | non-zero (views 0-1 gather lights) | non-zero |
| emulog | `TLB Miss, pc=0x17d880 addr=0x11` | none |
| fx[2] = `read32(0x000F0898)`: `+0x1D8`, `+0x1D4`, top byte of `+0x1C4` | 0, 0, 0 (not the cause) | same; after a level reset +0x1C8/+0x1CC = 0 |
| screenshot bottom row | dark | lit like the top row (possibly no light halos) |

**If the bottom row is still dark after the fix,** check the 19 fixed `< 2` ScreenEffects loops (m2_pads_cameras.md §3, cosmetic list). Also check the per-view 3D camera wrappers: render manager `read32(0x0050CDB4)`, cameras at +0x70 + v*0x60, method +0x6C(v), compare the frame/raster pointers of v = 2/3 with v = 0/1.

## Summary
- The TLB misses come from `FUN_0017D880` (per-view light gathering). It reads lightMgr+0xB0+4·view (0x0017D8D0) and then byte +0x11 (0x0017D8D4).
- The light manager (`DAT_0050CCE4`, 0xC0 bytes, ctor `FUN_0017D338`) only fills the per-view slot pointers for views 0-1. Views 2-3 read +0xB8/+0xBC, which were 0, giving the load at 0x11.
- For views 2-3 the light list (0x00715300, emptied per view by `FUN_0017E7E8`) is therefore never rebuilt. Those views render without dynamic lights, which is the most likely cause of the dark bottom row (HYPOTHESIS).
- ScreenEffects fx[2]/fx[3] are ruled out: zero fade, transparent tint.
- Fix (7 words, checker 0 problems):
  - hook at 0x0017D494 to a 5-word cave at 0x000F0FC0 that copies +0xB0/+0xB4 into +0xB8/+0xBC;
  - the missing ScreenEffects reset-loop word 0x0018C154 = 2EA70004, which the note extractor had skipped.
- Expected: no more TLB misses and a lit bottom row. Light halos for views 2-3 may be missing or shared (cosmetic).
- PINE reads in section 4 confirm both.

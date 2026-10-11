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

## Addendum: still dark (2026-10-11, static analysis)

Runtime input from the coordinator (run `local/m2/v4e`, lights fix applied):
- 0 TLB misses; views = 4, cameras = 4;
- the bottom row is still dark (`t0221_p5786.png`), with only small glyphs at the top edge of the bottom quarters.

So the lights were not the cause of the darkness.

### A. What the picture says (HYPOTHESIS)
- **The bottom quarters have one uniform colour,** the same dark olive as the uncovered bottom half in the 2-view runs (`v4b`, `v4d`). The 3D camera of views 2-3 draws nothing visible: no geometry, no player.
- **The small glyphs sit exactly at the top of the bottom quarters.** They are probably HUD sprites drawn through the per-view HUD cameras of views 2-3 (render manager +0x250 + v*0x60, rect set by `FUN_00195C78`).
- **So the per-view loop, the viewport rectangles and the HUD cameras for v = 2/3 work.** The problem is the 3D view itself: its camera position/orientation, or its projection.

### B. Most likely cause: the follow cameras of players 3-4 never get a target (VERIFIED code, HYPOTHESIS effect)
The follow camera (vtable 0x00535D50, 0x480 bytes, one per player at 0x000F0820 + 4p) picks its target human in our label `FollowCam::PickTarget` = `FUN_001282A0`. It runs from the follow-camera update paths: all_00.c:26996, 27038, 29116.

**How it picks targets:**
- **It collects targets from the tracked-humans list (0x005D91A8, capacity 4), entries 0 and 1 only.** The loop runs 0x001282F8-0x00128378, bounded by `sltiu v0,s0,2` at 0x00128374. Targets go into a **2-slot** array at cam+0x314/+0x318 (count u16 at cam+0x444). cam+0x31C is the next field (the target's handle), so the array cannot simply grow.
- **With SplitAllowed (0x0050B1C0 != 0) it compares the camera's player index with the count:**
  - player index from vtable +0x27C, which is byte cam+0x1D8, set by `FUN_0011F9E0` -> +0x274;
  - the compare is 0x0012842C `slt v0,v0,s0`, with s0 = count <= 2;
  - **for p = 2 and p = 3 it is false.**
- **On the false path (0x00128468-0x001284B0),** with the view flag 0x0050B1E8 != 0, it stores 0 to cam+0x314 and 0 to the count.
- **On the fallback path (0x001284E4)** it only uses the previous target handle at cam+0x31C. That handle is null for a new camera (constructor `FUN_00124778`: `piVar6[199] = DAT_006EBD30`).
- **So the cameras of players 3-4 have no target.** They are updated (`FUN_0011E878` calls render[v]+0x134 for every view) but have nothing to follow, so they stay where they were created.
  - Both the 3D world and the players drawn in that view are then out of shot.
  - HYPOTHESIS: they sit at or near the origin, far from the level, so only the camera clear (fog) colour shows.
- **In the tutorial without the test group,** SplitAllowed = 0 takes the shared branch (target = list[0]). That is why this never showed before the "test force split" group.

### C. Fix: players with index >= 2 follow their own human (26 words; checker 0 problems)
- At the compare, a cave handles p >= 2: target = `HuGetPlayer(p)`, i.e. `FUN_00390268(GameMgr + 0x228 + 4p)`, as the game resolves player handles elsewhere. Count = 1, then it continues at the original 0x001284B4, which stores the target's handle at +0x31C.
- p = 0/1 and the shared branch (SplitAllowed = 0) behave exactly as before.

```
patch=2,EE,0012842C,word,0803C2E4 // was 0050102A slt v0,v0,s0 -> j 0x000F0B90 (v0 = player index from the +0x27C call)
patch=2,EE,00128430,word,00000000 // was 1040000D beq v0,zero,0x00128468 -> nop (compare moved into the cave)
patch=2,EE,000F0B90,word,24010002 // addiu at,zero,2
patch=2,EE,000F0B94,word,0041082A // slt at,v0,at            p < 2 ?
patch=2,EE,000F0B98,word,1420000E // bne at,zero,normal (0x000F0BD4)
patch=2,EE,000F0B9C,word,00000000 // nop
patch=2,EE,000F0BA0,word,3C080051 // lui t0,0x51
patch=2,EE,000F0BA4,word,8D08489C // lw t0,0x489c(t0)        GameMgr
patch=2,EE,000F0BA8,word,00024880 // sll t1,v0,2
patch=2,EE,000F0BAC,word,01094021 // addu t0,t0,t1
patch=2,EE,000F0BB0,word,0C0E409A // jal 0x00390268          resolve handle
patch=2,EE,000F0BB4,word,25040228 // addiu a0,t0,0x228        &GameMgr.handle[p] (delay slot)
patch=2,EE,000F0BB8,word,AE220314 // sw v0,0x314(s1)          target
patch=2,EE,000F0BBC,word,10400003 // beq v0,zero,notarget
patch=2,EE,000F0BC0,word,24080001 // addiu t0,zero,1
patch=2,EE,000F0BC4,word,0804A12D // j 0x001284B4
patch=2,EE,000F0BC8,word,A6280444 // sh t0,0x444(s1)          count = 1
patch=2,EE,000F0BCC,word,0804A12D // notarget: j 0x001284B4
patch=2,EE,000F0BD0,word,A6200444 // sh zero,0x444(s1)        count = 0 (original fallback)
patch=2,EE,000F0BD4,word,0050102A // normal: slt v0,v0,s0      (original 0x0012842C)
patch=2,EE,000F0BD8,word,10400003 // beq v0,zero,isfalse
patch=2,EE,000F0BDC,word,00000000 // nop
patch=2,EE,000F0BE0,word,0804A10D // j 0x00128434             (original fall-through incl. its delay slot lui v0,0x51)
patch=2,EE,000F0BE4,word,00000000 // nop
patch=2,EE,000F0BE8,word,0804A11A // isfalse: j 0x00128468
patch=2,EE,000F0BEC,word,3C020051 // lui v0,0x51              (original delay slot, needed at 0x00128468)
```

**Checks (VERIFIED):**
- The original words at 0x0012842C/0x00128430/0x00128434 are 0050102A/1040000D/3C020051 in the ELF.
- No branch or jump in 0x00128000-0x00129000 targets the two patched words.
- The cave 0x000F0B90-0x000F0BEF lies in the free run 0x000F0B84-0x000F0BFF:
  - it is not in `mod/w4p_m1.pnach`;
  - no cave word loads or stores there;
  - `m2_gamemgr_records.md` and `m2_player_control.md` end at or before 0x000F0B80.
- `python -I tools/note_patches.py check mod/w4p_m1.pnach <fragment>`: 880 addresses, 0 problems.
- Disassembled with the fragment applied: the `j 0x000f0b90` / `nop` hook and the cave read back as listed.
- Registers: at/t0/t1/v0/a0 are scratch here, and s0 (count) is used only on the original path. ra was already overwritten by the jalr at 0x00128424, and the function saved it at entry.

### D. PINE reads to tell the causes apart (single instance, after players 3-4 exist, views = 4)
| Read | Healthy (v = 0/1) | Cause B (no target) | Other cause |
|---|---|---|---|
| `cam = read32(0x000F0810 + 4v)` (render camera of view v; `FUN_0011F9B0` reads this array) | non-zero | non-zero | 0, or the same as another view: render list problem |
| `read32(cam)` (vtable) | 0x00535D50 (follow) | 0x00535D50 | another type: check that type's target |
| `read8(cam + 0x1D8)` (player index) | 0 / 1 | 2 / 3 | wrong index: camera creation |
| `read32(cam + 0x314)` (target human), `read16(cam + 0x444)` (count), `read32(cam + 0x31C)` (target handle) | human of player v, count >= 1 | **0, count 0, handle null** | non-zero target but still dark: go on |
| floats `cam + 0x10..0x18` (eye) and `cam + 0x20..0x28` (look-at), from vtable +0xAC (0x004DB3E8) | near player v (e.g. x about -275) | far from the level or 0, eye = look-at, NaN | sane: go on |
| float `cam + 0x44` (FOV), floats `cam + 0x64 / 0x68` (view window, vtable +0x2B4 = 0x004DB200) | e.g. ~0.4-0.6 | can be normal | 0 or NaN: projection problem |
| `mgr = read32(0x0050CDB4)`, `rw = read32(mgr + 0x70 + 0x60v + 4)`: `fb = read32(rw + 0x60)`, width/height `read32(fb + 0x0C/0x10)`, s16 offsets `fb + 0x1C/0x1E`; floats viewWindow `rw + 0x68/0x6C`, near/far `rw + 0x80/0x84` (RW 3.x layout: HYPOTHESIS; +0x60/+0x64 raster/zbuffer VERIFIED by `FUN_00195C78`) | quarter size; offsets (0,0)/(320,0) at native | v = 2/3 offsets (0,224)/(320,224) | zero size, wrong offset, near >= far: raster/clip problem |
| `f = read32(0x000F0898 / 0x000F089C)` (fx[2]/fx[3]): u16 `f + 0x212`, top byte of `f + 0x1C0` and `f + 0x1C4`, float `f + 0x1D8`, `f + 0x1F8` | `+0x212` = 2/3, alpha 0, fade 0, 0 | same | alpha != 0 or fade > 0: overlay effect (section 2) |
| positions of 0x641A20 / 0x6420F0 (`+0x10`) | x about -275, y about 0.25 | same | |

**How to read the table:**
- If cam+0x314 = 0 for views 2/3 -> apply section C.
- If the target is set and the eye is sane but the view is dark -> check the RW camera raster, rect and clip values, then the fx overlay values.

### Summary (addendum)
- The most likely cause: the follow cameras of players 3-4 have no target.
- `FUN_001282A0` (follow-camera target picker) collects targets only from tracked-list entries 0-1 (loop `< 2` at 0x00128374) into a 2-slot array at cam+0x314. In split view it takes slot p only if p < count (0x0012842C), so for players 3-4 it stores target 0 and count 0.
- Those cameras are updated but never move into the level, so views 2-3 show only the clear colour. The per-view HUD glyphs in the right place show that the viewport rects and the loop work.
- Fix, 26 words (checker: 0 problems on 880 addresses):
  - 0x0012842C -> `j 0x000F0B90`, 0x00128430 -> nop;
  - a 24-word cave at **0x000F0B90-0x000F0BEF** (free run 0x000F0B84-0x000F0BFF) sets target = HuGetPlayer(p) for p >= 2;
  - players 1-2 and the shared branch are unchanged.
- Section D gives PINE reads that confirm this (cam+0x314 = 0 and the camera eye far away) or point to the projection/raster or overlay causes instead.

# M2 research: pads, cameras, ScreenEffects, listeners (2-player limits below GameMgr)

Static analysis only, 2026-10-11. Game: The Warriors SLUS-21215 v1.03 (`local/disc/SLUS_212.15`, read-only).
Function names are OUR labels (stripped ELF). Nothing here was run. GameMgr storage and the HUD are handled in
separate notes; this note covers what sits below them.

**Method.** Ghidra decompile (`local/analysis/all/*.c`) plus an instruction scanner over the ELF text that tracks
`lui` values per register (also through `addu` index and `addiu` pointer steps) and reports every load/store/address
computation that lands in a range. The scanner is path-insensitive, so "this `lui` feeds nothing else" is a
HYPOTHESIS per site (two flagged cases were checked by hand and were false positives). Every "was" word below was
read from the ELF. The new words were encoded with `tools/mips_asm.py` or by hand, then disassembled back.
No `.data` word in the ELF points into any of the arrays below (full data scan), so instruction sites cover every
static reference.

## 0. Free RAM plan (proposal, coordinate with the GameMgr and HUD notes)
| Range | Use |
|---|---|
| 0x000F0400-0x000F045F, 0x000F0500 | existing M1 hook cave and poll counter |
| 0x000F0600-0x000F0673 | existing radar cave (`[warriors-4p hud]`) |
| 0x000F0700-0x000F07FF | left free for the GameMgr/HUD work |
| 0x000F0800-0x000F088F | camera arrays, 9 x 4 entries (section 2) |
| 0x000F0890-0x000F089F | ScreenEffects pointers, 4 entries (section 3) |
| 0x000F08A0-0x000F08BF | per-player camera flags, 2 x 4 entries (section 5) |
| 0x000F08C0-0x000F093F | per-player listener buffer, 4 x 0x20 (section 4) |
| 0x000F0A80-0x000F0B3F | code caves of this note |

- The region is all zero in gameplay (F-0050). That it is always free is a HYPOTHESIS.
- All data arrays here are initialised by the game code (sections 2-5) before use, except camera array 6
  (0x000F0860, old 0x005D9178), which the original init loop does not clear either. Zero the data block once
  at load with **place 0** pnach lines (`patch=0,...`, `PPT_ONCE_ON_LOAD`). Never use place 1 or 2 for data:
  place 2 (`PPT_COMBINED_0_1`) rewrites every vsync (`pcsx2/Patch.cpp` lines 1105-1115), which would wipe live
  state.
- **W4P hash split:** `kGameRamStart = 0x00100000` in W4P.cpp puts all of this (and the existing caves) in the
  "kernel" hash. A real desync there would only be reported as a kernel-only difference. Move the split to
  0x000F0000.

## 1. Pads (VERIFIED unless marked)
- **Pad slots.** 8 pad-state structs at 0x005DD810 + pad*0x50: +0x42 s16 owner player index (-1 = free),
  +0x44 s16, +0x4C connected (copied from the port buffer). 8 port buffers at 0x005DE3C0 + pad*0x140: +0x104 port,
  +0x108 slot, +0x10C connected, +0x110.. sticks/buttons. 8 "force" bytes at 0x005DE380.
  Source: `PadInit` 0x00149520, `PadRead` 0x001498A8.
- **Pad index = port*4 + slot.** `PadInit` writes port = i>>2&1 and slot = i&3. This matches W4P's
  `memRead32(+0x104)*4 + memRead32(+0x108)`. Only buffers 0 (port 1A) and 4 (port 2A) are opened
  (`scePadPortOpen`-like 0x0044CFE8).
- **`PadUpdateAll` (0x001454A8) polls only pads 0 and 4.** Loop step at 0x0014562C and pointer step at 0x00145638
  (F-0055). It is called every logic step from `SimStep` 0x00249108 (60/s with the 60 fps patch) and from menus.
  Fix (the E4 words, F-0062 drove a player on pad 1 with them):
  ```
  patch=2,EE,0014562C,word,26940001 // was 26940004: addiu s4,s4,1  (poll pads 0..7)
  patch=2,EE,00145638,word,26B50050 // was 26B50140: addiu s5,s5,0x50
  ```
  Each poll then makes 8 libpad reads, so the W4P hook runs 8 times per poll. The guest counter still increments
  only on pad 0, so `NewPoll` runs once per poll.
- **Pad to player.** `MakePlayer` 0x00229C40 (human, pad, hud, player):
  - With a pad given, it requires pad+0x4C != 0 (connected) and pad+0x42 == -1 (free), then stores the pad in the
    human's controller record (+0x19).
  - Without a pad, it searches 8 pads for a connected free one.
  - The per-pad owner (+0x42) drives the camera-relative stick: `PadUpdateAll` caches the owning player's camera
    vector at 0x005DDC90 + player*0x10. That area is 0x80 bytes up to the next referenced address (0x005DDD10),
    so it has 8 entries and is enough for 4 players (size: HYPOTHESIS).
- **W4P side.** The default `PadForSlot0..3 = 0, 4, 1, 2` keeps players 1 and 2 on the original pads. Players 3 and
  4 use port 1 slots B and C. `WriteInput` already sets +0x10C = 1 and the inputs for every mapped pad on each
  read. Pads with no session player are left with libpad's data. For unopened slots that is presumably
  "not connected" (HYPOTHESIS; E4 only injected pad 1).
- **Join path (risk).** `FUN_00158728` (in-game update) loops over all 8 pads (around 0x001592B0):
  - a connected pad pressing Start (game code 0x800) whose owner is -1 calls `FUN_0041A460(GameMgr, pad)`, the
    drop-in join;
  - so once pads 1 and 2 report connected, players 3 and 4 pressing Start before they are bound reach the game's
    own join code. Today that is limited by the GameMgr count;
  - this is either the natural way to create players 3 and 4 (GameMgr note), or must be gated by the session
    (join only in the lobby).

## 2. Cameras and viewports
### 2.1 The camera block is ten 2-entry arrays, packed (VERIFIED)
| Old address | Role (getter / factory) |
|---|---|
| 0x005D9148 | active camera per player/view (`FUN_0011F9C8`) |
| 0x005D9150 | render list = cameras drawn this frame (`FUN_0011F9B0`) |
| 0x005D9158 | follow camera per player (`FUN_0011F9E0`, alloc 0x480, ctor `FUN_00124778`) |
| 0x005D9160 | `FUN_0011FBB0` (0x3F0, `FUN_0013B118`) |
| 0x005D9168 | `FUN_0011FF50` (0x220, `FUN_00134B90`) |
| 0x005D9170 | `FUN_0011FD80` (0x250, `FUN_00137CD0`) |
| 0x005D9178 | `FUN_0011FE68` (0x260, `FUN_00136068`); not cleared by the init loop |
| 0x005D9180 | `FUN_0011FAC8` (0x240, `FUN_00142F98`) |
| 0x005D9188 | `FUN_0011FC98` (0x340, `FUN_00139D68`) |
| 0x005D9190 | 2-deep camera push/pop stack, depth counter 0x0050B180 (`FUN_00120450`/`FUN_00120488`) - not per player, not moved |
| 0x005D9198 | container (`FUN_004DAE60`) - not moved |
| 0x005D91A8 | tracked-humans list, capacity 4 (F-0029) - fine |

- Index 2 or 3 into any array lands in the next array; F-0026 named only 5 of these arrays.
- 17 functions, 185 instructions access 0x005D9148-0x005D918F:
  - every access is either an immediate in 0x9148-0x918F with `lui 0x5E`, offset 0 on a derived pointer, or a +4
    step within the same array;
  - no access crosses arrays (checked);
  - no `lui` feeding them also feeds another global (53 `lui`s outside the replaced tail, 57 in total).
- **Fix: relocate the 9 per-player arrays to 0x000F0800, 4 entries each** (array k at 0x000F0800 + k*0x10).
  - Mechanical remap: `lui 0x5E` becomes `lui 0x000F`; immediate 0x9148 + k*8 + j*4 becomes 0x0800 + k*0x10 + j*4.
  - Appendix A: **151 words** (98 immediates, 53 `lui`).
  - Plus:
    - **Init loop** `FUN_0011E9C0` (clears 8 of the arrays, 2 iterations):
      `patch=2,EE,0011EA08,word,240A0003 // was 240A0001: addiu t2,zero,3` (4 iterations).
    - **Camera delete** `FUN_0011E440`: its tail clears a deleted camera only from active[0..1] and render[0..1].
      Players 3 and 4 would leave dangling pointers. Replace the tail 0x0011E7EC-0x0011E828 with a loop over 4
      entries of both arrays (all outside branches enter at 0x0011E7EC; 16 of 23 words used):
      ```
      patch=2,EE,0011E7EC,word,3C02000F // lui v0,0xf
      patch=2,EE,0011E7F0,word,24420800 // addiu v0,v0,0x800      active[] (render[] at +0x10)
      patch=2,EE,0011E7F4,word,24030004 // addiu v1,zero,4
      patch=2,EE,0011E7F8,word,8C440000 // lw a0,0x0(v0)
      patch=2,EE,0011E7FC,word,14910002 // bne a0,s1,+2
      patch=2,EE,0011E800,word,00000000 // nop
      patch=2,EE,0011E804,word,AC400000 // sw zero,0x0(v0)
      patch=2,EE,0011E808,word,8C440010 // lw a0,0x10(v0)
      patch=2,EE,0011E80C,word,14910002 // bne a0,s1,+2
      patch=2,EE,0011E810,word,00000000 // nop
      patch=2,EE,0011E814,word,AC400010 // sw zero,0x10(v0)
      patch=2,EE,0011E818,word,2463FFFF // addiu v1,v1,-1
      patch=2,EE,0011E81C,word,1C60FFF6 // bgtz v1,0x0011E7F8
      patch=2,EE,0011E820,word,24420004 // addiu v0,v0,4
      patch=2,EE,0011E824,word,08047A12 // j 0x0011E848            (original continuation)
      patch=2,EE,0011E828,word,00000000 // nop
      ```
      The same function's early "is this an active camera?" guard checks only active[0..1] (when the camera count
      is above 1), so it does not protect players 3 and 4's active cameras from deletion. HYPOTHESIS: harmless,
      because cameras are deleted on level teardown; check at runtime.
- **Creation for players 3 and 4.**
  - `FUN_0011EAF0(player)` creates a player's cameras: the same types player 0 has, then sets active and render.
    It is called from `FUN_0041A460` (GameMgr add/join, GameMgr note).
  - Every getter and every loop over cameras is bounded by the player count (0x224), the view count 0x0050B198 or
    the camera count 0x0050B19C, so with 4-entry arrays it handles 4 players without further change. This
    includes `LayoutViewports` 0x00122ED0, `FUN_0011EE08`, `FUN_0011E878`, the pad code and the HUD.
- **Layout.**
  - `LayoutViewports` already builds N views and forces the 2x2 mode when there are more than 2 views.
  - `FUN_00120A98` (per-camera projection, 0x00120B8C) does the same.
  - With 3-4 views no layout patch is needed. Our 0x00123300/0x00120B8C patches only matter for 2 views.
- **Merge logic is 2-player only:**
  - `FUN_00121888` (merge state 0x0050B1E8/0x0050B1EC) and `FUN_00126C40` use players 0 and 1 explicitly;
  - `FUN_00126C40` runs its merge branch only when the camera count is 2;
  - with D8 (merge option 0x0050B1C4 forced 0) none of this runs in sessions, so no 4-player merge rule is needed.
- **Heap (risk).** About 0xAF0 bytes of camera objects per extra player (follow camera 0x480 + 0x3F0 + 0x220,
  depending on player 0's camera types) come from the game heap (`DAT_005127E4` +0x54). That the heap has room is a
  HYPOTHESIS. If allocation fails, the slot stays 0.

## 3. ScreenEffectsManager (the E4 crash) (VERIFIED)
- **The objects.** 2 per-view objects (0x220 bytes each, plus 0x980 and 0x40 sub-allocations) are created by
  `FUN_0018BA10`: loop `< 2`, constructor `FUN_0018B1E0(obj, view)`, which stores the view at +0x212. The pointers
  live at 0x005FDEB8[2]; 0x005FDEC0 is a different global (only `FUN_0018C058`, `FUN_0018B1E0`, `FUN_0018BE58`
  use it).
- **The E4 crash.**
  - `FUN_003A31A8` loops over the **player count**: `FUN_0018BF68(0x005FDEB8[i])`.
  - With 3 players it passed the word at 0x005FDEC0 as an object.
  - `FUN_0018BF68` reads +0x19C/+0x198 at 0x0018BF90, and `FUN_0018B950` reads at 0x0018B998. These are exactly
    the TLB-miss PCs in F-0062.
- **Users.**
  - 306 instructions in 90 functions use 0x005FDEB8-0x005FDEC3. Most read entry 0 only (the main view's effects).
  - The ones that break with 3-4 players index by player count, by view count, or by a human's player index
    (human+0x1B0):
    - player count: `FUN_0039CBF0`, `FUN_0039D870`, `FUN_0039EC60`, `FUN_0039F450`, `FUN_003A31A8`;
    - view count (`FUN_0011EAE0` = 0x0050B198): `FUN_0018DAC0` (per-view effect render);
    - indexed by player/camera: `FUN_00126A88`, `FUN_0013C5A8` (the follow cameras), `FUN_00156658`,
      `FUN_0018E2F0`, `FUN_0021D928`, `FUN_002371D8`;
    - reset of all objects: `FUN_0018C058`, fixed `< 2`.
- **Fix: a 4-entry "mirror" array at 0x000F0890.**
  - Old entries [0] and [1] stay valid and identical, so the ~80 functions that use fixed [0]/[1] stay untouched.
  - Creation loop (base and bound) plus a tail cave that copies [0],[1] back to 0x005FDEB8:
    ```
    patch=2,EE,0018BA14,word,3C02000F // was 3C020060: lui v0,0xf
    patch=2,EE,0018BA28,word,24510890 // was 2451DEB8: addiu s1,v0,0x890
    patch=2,EE,0018BA94,word,2E020004 // was 2E020002: sltiu v0,s0,4
    patch=2,EE,0018BAA0,word,0803C2A0 // was 3C020051: j 0x000F0A80
    patch=2,EE,0018BAA4,word,00000000 // was 8C45CDB4: nop
    patch=2,EE,000F0A80,word,3C02000F // lui v0,0xf
    patch=2,EE,000F0A84,word,8C430890 // lw v1,0x890(v0)
    patch=2,EE,000F0A88,word,3C040060 // lui a0,0x60
    patch=2,EE,000F0A8C,word,AC83DEB8 // sw v1,-0x2148(a0)     old [0]
    patch=2,EE,000F0A90,word,8C430894 // lw v1,0x894(v0)
    patch=2,EE,000F0A94,word,AC83DEBC // sw v1,-0x2144(a0)     old [1]
    patch=2,EE,000F0A98,word,3C020051 // lui v0,0x51            (original 0x0018BAA0)
    patch=2,EE,000F0A9C,word,08062EAA // j 0x0018BAA8
    patch=2,EE,000F0AA0,word,8C45CDB4 // lw a1,-0x324c(v0)      (original 0x0018BAA4)
    ```
  - Reset loop of all objects: `patch=2,EE,0018C154,word,2EA70004 // was 2EA70002: sltiu a3,s5,4`.
  - Point the 13 functions listed above at the mirror (Appendix B, 51 words). The two "shared `lui`" warnings
    (0x003A32B0, 0x0018DD0C) are a different path and a loop's final +4 step, not real sharing.
- **Not covered by the minimal fix (cosmetic, phase 2).**
  - About 19 functions with fixed `< 2` loops only update views 0-1: `FUN_00126370`, `0012AE58`, `0013B6F8`,
    `00155F78`, `0018B168`, `0018DDA0`, `0018DF00`, `0018E070`, `0018E3C8`, `0018E470`, `0018E530`, `001CF468`,
    `001D1C48`, `001D23D0`, `001DBEE0`, `001DCB20`, `001E0008`, `0042A938`, `003A6EE8`.
  - Those are fades, flashes and blur.
  - Players 3 and 4 would miss these in their quarter. Their objects still exist and are reset, so nothing crashes.
- **Heap.** About 0xBE0 bytes per extra view (HYPOTHESIS: there is room).

## 4. Per-player listener buffer and audio (VERIFIED)
- **Stack overflow.** `FUN_00158728` (in-game update, frame 0x120) builds a 0x20-byte camera/listener entry per
  player into a **stack buffer at sp+0x00 sized for 2**. The loop is 0x00158D98-0x00159070 (`s2` steps 0x20,
  bounded by the player count).
  - Above the buffer: scratch at sp+0x40..0x5F, a flag at sp+0x60, the "entry 1" pointer at sp+0x64 (passed to the
    HUD) and the **saved `ra` at sp+0x70**.
  - Player 3's entry lands on the scratch. Player 4's entry overwrites the flag, the pointer and the saved return
    address: a certain crash with 4 players, independent of the E4 one.
- **Fix: static 4-entry buffer at 0x000F08C0, then copy entries 0-1 back to the stack.** All existing consumers
  (audio `FUN_0010F810`, HUD `FUN_001AF010`, the entry-1 pointer at sp+0x64) stay unchanged. Entries 2-3 are at
  0x000F0900/0x000F0920 for the HUD work.
  ```
  patch=2,EE,00158D88,word,3C12000F // was 03A0902D (daddu s2,sp,zero): lui s2,0xf
  patch=2,EE,00158D94,word,265208C0 // was 00000000 (nop): addiu s2,s2,0x8C0
  patch=2,EE,00159078,word,0803C2B0 // was 3C020051: j 0x000F0AC0  (also the blez target when count <= 0)
  patch=2,EE,000F0AC0,word,3C08000F // lui t0,0xf
  patch=2,EE,000F0AC4,word,790208C0 // lq v0,0x8c0(t0)
  patch=2,EE,000F0AC8,word,790308D0 // lq v1,0x8d0(t0)
  patch=2,EE,000F0ACC,word,7FA20000 // sq v0,0x0(sp)
  patch=2,EE,000F0AD0,word,7FA30010 // sq v1,0x10(sp)
  patch=2,EE,000F0AD4,word,790208E0 // lq v0,0x8e0(t0)
  patch=2,EE,000F0AD8,word,790308F0 // lq v1,0x8f0(t0)
  patch=2,EE,000F0ADC,word,7FA20020 // sq v0,0x20(sp)
  patch=2,EE,000F0AE0,word,7FA30030 // sq v1,0x30(sp)
  patch=2,EE,000F0AE4,word,3C020051 // lui v0,0x51             (original 0x00159078)
  patch=2,EE,000F0AE8,word,08056420 // j 0x00159080
  patch=2,EE,000F0AEC,word,03A0282D // daddu a1,sp,zero        (original 0x0015907C)
  ```
  - Small behaviour change: the "no camera" fallback inside the loop (0x00158DBC/0x00158EB8) copies from sp+0 /
    sp+0x10, which now hold the previous frame's copy of entry 0 instead of the current frame's. It is still
    deterministic.
  - The other path at 0x0015935C (GameMgr+0x410/+0x411 set) writes a fixed 2 entries on the stack and is left as is.
- **Audio listeners: 2.**
  - `FUN_0010F810` passes the buffer to `FUN_00112B10`, which copies exactly 2 listeners (`< 2`) into the sound
    manager (`PTR_DAT_0050AA84`, +0x20..+0x5F).
  - Players 3 and 4 hear positional sound relative to players 1 and 2.
  - Extending the sound object is not possible in place (fields follow).
  - A per-PC listener would make the sound manager's EE state differ between PCs (HYPOTHESIS: voice and culling
    state in EE RAM), so it is not a presentation-only change.
  - Recommendation: keep 2 listeners for M2; revisit later, deterministically on every PC.

## 5. Two more per-player arrays: camera control flags (VERIFIED)
- **The arrays.** 0x0050B1B0[2] (camera input allowed; cleared/set by HUD/map code) and 0x0050B1B8[2] (Lua
  `CamEnable(0, ..)` per player, `FUN_0011DE58`) sit directly before 0x0050B1C0 (split allowed), 0x0050B1C4 (merge
  option) and 0x0050B1C8.
- **Camera input** `FUN_00129050` returns early unless both flags for the camera's player are set:
  - player 3 reads 0x0050B1B8/0x0050B1C0;
  - player 4 reads 0x0050B1BC/**0x0050B1C4**, which D8 forces to 0;
  - so **player 4's camera stick would never work**.
- **Writers with a player index** (`FUN_001A6D28`, `FUN_001A7000`, `FUN_0020E058`) would overwrite players 1 and
  2's flags.
- **Fix: relocate both arrays to 0x000F08A0 / 0x000F08B0, 4 entries each.** 10 `lui`s, none shared:
  ```
  patch=2,EE,0011DEA0,word,3C02000F // was 3C020051
  patch=2,EE,0011DEA4,word,244208B0 // was 2442B1B8
  patch=2,EE,0011DEB4,word,3C02000F // was 3C020051
  patch=2,EE,0011DEB8,word,24030003 // was 24030001: CamEnable(0,-1) loop 4 entries
  patch=2,EE,0011DEBC,word,244208B0 // was 2442B1B8
  patch=2,EE,0011DEC0,word,2442000C // was 24420004: start at entry 3 (loop steps -4)
  patch=2,EE,00122BA8,word,3C04000F // was 3C040051
  patch=2,EE,00122BAC,word,3C02000F // was 3C020051
  patch=2,EE,00122BBC,word,244208B0 // was 2442B1B8
  patch=2,EE,00122BC4,word,248408A0 // was 2484B1B0
  patch=2,EE,001290C8,word,3C03000F // was 3C030051
  patch=2,EE,001290D0,word,246308A0 // was 2463B1B0
  patch=2,EE,001290F8,word,3C03000F // was 3C030051
  patch=2,EE,00129100,word,246308B0 // was 2463B1B8
  patch=2,EE,001A6F24,word,3C03000F // was 3C030051
  patch=2,EE,001A6F28,word,246308A0 // was 2463B1B0
  patch=2,EE,001A7004,word,3C03000F // was 3C030051
  patch=2,EE,001A7008,word,246308A0 // was 2463B1B0
  patch=2,EE,001AF6E8,word,3C02000F // was 3C020051
  patch=2,EE,001AF6F4,word,245208B0 // was 2452B1B8
  patch=2,EE,0020E0C0,word,3C03000F // was 3C030051
  patch=2,EE,0020E0C4,word,246308A0 // was 2463B1B0
  ```
- **Init.** The init loop in `FUN_00122B80` sets [0..1] of both arrays and also the unrelated 2-flag global
  0x0050B1E8 (merge state, fixed indices). So instead of a longer loop, a cave sets entries [2..3] to 1:
  ```
  patch=2,EE,00122BF0,word,0803C2C0 // was 24100001: j 0x000F0B00 (delay slot 0x00122BF4 lui v0,0x51 stays)
  patch=2,EE,000F0B00,word,3C08000F // lui t0,0xf
  patch=2,EE,000F0B04,word,24090001 // addiu t1,zero,1
  patch=2,EE,000F0B08,word,AD0908A8 // sw t1,0x8a8(t0)
  patch=2,EE,000F0B0C,word,AD0908AC // sw t1,0x8ac(t0)
  patch=2,EE,000F0B10,word,AD0908B8 // sw t1,0x8b8(t0)
  patch=2,EE,000F0B14,word,AD0908BC // sw t1,0x8bc(t0)
  patch=2,EE,000F0B18,word,24100001 // addiu s0,zero,1        (original 0x00122BF0)
  patch=2,EE,000F0B1C,word,08048AFE // j 0x00122BF8
  patch=2,EE,000F0B20,word,00000000 // nop
  ```
- **Scripts.** Lua `CamEnable(0, p, ..)` with p = 2 or 3 now works too. With the old layout it would have written
  the split flag.

## 6. Other 2-entry or per-player data checked
- 0x005DDC90 camera vectors: 8 entries (section 1).
- 0x005DE380 force bytes: 8 entries.
- Tracked-humans list: capacity 4.
- 0x00714B00.. (used in many player loops) is a single scratch struct, not an array (HYPOTHESIS).
- 0x0050B1E8/0x0050B1EC: merge state, fixed indices.
- GameMgr per-player records (+0x178 stride 0x5C, +0x228 handles, +0x5740): GameMgr note.
- HUD (0x00600840, 0x0050F7B0 table, radar objects): HUD note.

## 7. Open items
- Runtime checks, all untested:
  - 4 humans bound to pads 0/4/1/2 with independent input;
  - 4 follow cameras and 4 views (2x2);
  - no crash for 30 min;
  - hashes equal across instances;
  - effect objects 2-3 created (heap);
  - player 4's camera stick works.
- The listener fallback change and the phase-2 effect loops.
- Whether the BIOS ever touches 0x000F0000-0x000F0FFF (F-0050 HYPOTHESIS).

## Appendix A: camera block relocation (151 words, generated, "was" from the ELF)
Excludes 0x0011E7EC-0x0011E847, which the tail replacement in section 2 covers.
```
patch=2,EE,0011E5A8,word,3C03000F // was 3C03005E: lui v1,0xf
patch=2,EE,0011E5B4,word,24630870 // was 24639180: addiu v1,v1,2160
patch=2,EE,0011E5D0,word,3C03000F // was 3C03005E: lui v1,0xf
patch=2,EE,0011E5D4,word,8C620810 // was 8C629150: lw v0,0x810(v1)
patch=2,EE,0011E5E0,word,3C02000F // was 3C02005E: lui v0,0xf
patch=2,EE,0011E5E4,word,8C450800 // was 8C459148: lw a1,0x800(v0)
patch=2,EE,0011E66C,word,3C03000F // was 3C03005E: lui v1,0xf
patch=2,EE,0011E678,word,24630830 // was 24639160: addiu v1,v1,2096
patch=2,EE,0011E690,word,3C03000F // was 3C03005E: lui v1,0xf
patch=2,EE,0011E69C,word,24630850 // was 24639170: addiu v1,v1,2128
patch=2,EE,0011E6B4,word,3C03000F // was 3C03005E: lui v1,0xf
patch=2,EE,0011E6C0,word,24630860 // was 24639178: addiu v1,v1,2144
patch=2,EE,0011E6DC,word,3C03000F // was 3C03005E: lui v1,0xf
patch=2,EE,0011E6E0,word,8C620810 // was 8C629150: lw v0,0x810(v1)
patch=2,EE,0011E6EC,word,3C02000F // was 3C02005E: lui v0,0xf
patch=2,EE,0011E6F0,word,8C450800 // was 8C459148: lw a1,0x800(v0)
patch=2,EE,0011E778,word,3C03000F // was 3C03005E: lui v1,0xf
patch=2,EE,0011E784,word,24630820 // was 24639158: addiu v1,v1,2080
patch=2,EE,0011E79C,word,3C03000F // was 3C03005E: lui v1,0xf
patch=2,EE,0011E7A8,word,24630840 // was 24639168: addiu v1,v1,2112
patch=2,EE,0011E7C0,word,3C03000F // was 3C03005E: lui v1,0xf
patch=2,EE,0011E7C8,word,24630880 // was 24639188: addiu v1,v1,2176
patch=2,EE,0011E8AC,word,3C04000F // was 3C04005E: lui a0,0xf
patch=2,EE,0011E8B4,word,8C820810 // was 8C829150: lw v0,0x810(a0)
patch=2,EE,0011E8C0,word,3C03000F // was 3C03005E: lui v1,0xf
patch=2,EE,0011E8C4,word,8C620800 // was 8C629148: lw v0,0x800(v1)
patch=2,EE,0011E8D0,word,3C02000F // was 3C02005E: lui v0,0xf
patch=2,EE,0011E8D4,word,8C420820 // was 8C429158: lw v0,0x820(v0)
patch=2,EE,0011E8E8,word,AC850810 // was AC859150: sw a1,0x810(a0)
patch=2,EE,0011E9C4,word,3C09000F // was 3C09005E: lui t1,0xf
patch=2,EE,0011E9C8,word,3C08000F // was 3C08005E: lui t0,0xf
patch=2,EE,0011E9CC,word,3C07000F // was 3C07005E: lui a3,0xf
patch=2,EE,0011E9D0,word,3C06000F // was 3C06005E: lui a2,0xf
patch=2,EE,0011E9D4,word,3C05000F // was 3C05005E: lui a1,0xf
patch=2,EE,0011E9D8,word,3C04000F // was 3C04005E: lui a0,0xf
patch=2,EE,0011E9DC,word,3C03000F // was 3C03005E: lui v1,0xf
patch=2,EE,0011E9E0,word,3C02000F // was 3C02005E: lui v0,0xf
patch=2,EE,0011E9E8,word,24420880 // was 24429188: addiu v0,v0,2176
patch=2,EE,0011E9EC,word,24630850 // was 24639170: addiu v1,v1,2128
patch=2,EE,0011E9F0,word,24840840 // was 24849168: addiu a0,a0,2112
patch=2,EE,0011E9F4,word,24A50830 // was 24A59160: addiu a1,a1,2096
patch=2,EE,0011E9F8,word,24C60870 // was 24C69180: addiu a2,a2,2160
patch=2,EE,0011E9FC,word,24E70820 // was 24E79158: addiu a3,a3,2080
patch=2,EE,0011EA00,word,25080810 // was 25089150: addiu t0,t0,2064
patch=2,EE,0011EA04,word,25290800 // was 25299148: addiu t1,t1,2048
patch=2,EE,0011EB18,word,3C02000F // was 3C02005E: lui v0,0xf
patch=2,EE,0011EB20,word,8C430820 // was 8C439158: lw v1,0x820(v0)
patch=2,EE,0011EB2C,word,24520820 // was 24529158: addiu s2,v0,2080
patch=2,EE,0011EB54,word,8E850820 // was 8E859158: lw a1,0x820(s4)
patch=2,EE,0011EB58,word,3C02000F // was 3C02005E: lui v0,0xf
patch=2,EE,0011EB5C,word,8C430830 // was 8C439160: lw v1,0x830(v0)
patch=2,EE,0011EB68,word,24520830 // was 24529160: addiu s2,v0,2096
patch=2,EE,0011EB94,word,8EA50830 // was 8EA59160: lw a1,0x830(s5)
patch=2,EE,0011EB98,word,3C02000F // was 3C02005E: lui v0,0xf
patch=2,EE,0011EB9C,word,8C430840 // was 8C439168: lw v1,0x840(v0)
patch=2,EE,0011EBA8,word,24520840 // was 24529168: addiu s2,v0,2112
patch=2,EE,0011EBD4,word,8E650840 // was 8E659168: lw a1,0x840(s3)
patch=2,EE,0011EBDC,word,3C02000F // was 3C02005E: lui v0,0xf
patch=2,EE,0011EBE4,word,8C450800 // was 8C459148: lw a1,0x800(v0)
patch=2,EE,0011EC30,word,26820820 // was 26829158: addiu v0,s4,2080
patch=2,EE,0011EC3C,word,26A20830 // was 26A29160: addiu v0,s5,2096
patch=2,EE,0011EC9C,word,26820820 // was 26829158: addiu v0,s4,2080
patch=2,EE,0011ECA8,word,26A20830 // was 26A29160: addiu v0,s5,2096
patch=2,EE,0011ECB0,word,26620840 // was 26629168: addiu v0,s3,2112
patch=2,EE,0011ECB8,word,26430800 // was 26439148: addiu v1,s2,2048
patch=2,EE,0011ECCC,word,8E820820 // was 8E829158: lw v0,0x820(s4)
patch=2,EE,0011ECD4,word,26830820 // was 26839158: addiu v1,s4,2080
patch=2,EE,0011ECDC,word,26430800 // was 26439148: addiu v1,s2,2048
patch=2,EE,0011ECEC,word,26A20830 // was 26A29160: addiu v0,s5,2096
patch=2,EE,0011ECF0,word,26430800 // was 26439148: addiu v1,s2,2048
patch=2,EE,0011ED04,word,26420800 // was 26429148: addiu v0,s2,2048
patch=2,EE,0011ED14,word,3C02000F // was 3C02005E: lui v0,0xf
patch=2,EE,0011ED18,word,24420810 // was 24429150: addiu v0,v0,2064
patch=2,EE,0011ED70,word,3C02000F // was 3C02005E: lui v0,0xf
patch=2,EE,0011ED78,word,24420820 // was 24429158: addiu v0,v0,2080
patch=2,EE,0011ED94,word,3C02000F // was 3C02005E: lui v0,0xf
patch=2,EE,0011ED98,word,24420830 // was 24429160: addiu v0,v0,2096
patch=2,EE,0011EDB4,word,3C02000F // was 3C02005E: lui v0,0xf
patch=2,EE,0011EDB8,word,24420840 // was 24429168: addiu v0,v0,2112
patch=2,EE,0011EDD4,word,3C02000F // was 3C02005E: lui v0,0xf
patch=2,EE,0011EDD8,word,3C03000F // was 3C03005E: lui v1,0xf
patch=2,EE,0011EDDC,word,24420800 // was 24429148: addiu v0,v0,2048
patch=2,EE,0011EDE0,word,24630810 // was 24639150: addiu v1,v1,2064
patch=2,EE,0011F100,word,3C17000F // was 3C17005E: lui s7,0xf
patch=2,EE,0011F110,word,26E20800 // was 26E29148: addiu v0,s7,2048
patch=2,EE,0011F13C,word,26E20800 // was 26E29148: addiu v0,s7,2048
patch=2,EE,0011F170,word,3C04000F // was 3C04005E: lui a0,0xf
patch=2,EE,0011F174,word,26E20800 // was 26E29148: addiu v0,s7,2048
patch=2,EE,0011F178,word,24830810 // was 24839150: addiu v1,a0,2064
patch=2,EE,0011F25C,word,26E20800 // was 26E29148: addiu v0,s7,2048
patch=2,EE,0011F260,word,3C04000F // was 3C04005E: lui a0,0xf
patch=2,EE,0011F264,word,24830810 // was 24839150: addiu v1,a0,2064
patch=2,EE,0011F470,word,3C02000F // was 3C02005E: lui v0,0xf
patch=2,EE,0011F474,word,24420800 // was 24429148: addiu v0,v0,2048
patch=2,EE,0011F65C,word,3C03000F // was 3C03005E: lui v1,0xf
patch=2,EE,0011F668,word,AC620810 // was AC629150: sw v0,0x810(v1)
patch=2,EE,0011F6E4,word,3C04000F // was 3C04005E: lui a0,0xf
patch=2,EE,0011F6EC,word,AC820810 // was AC829150: sw v0,0x810(a0)
patch=2,EE,0011F9B0,word,3C02000F // was 3C02005E: lui v0,0xf
patch=2,EE,0011F9B8,word,24420810 // was 24429150: addiu v0,v0,2064
patch=2,EE,0011F9C8,word,3C02000F // was 3C02005E: lui v0,0xf
patch=2,EE,0011F9D0,word,24420800 // was 24429148: addiu v0,v0,2048
patch=2,EE,0011FA08,word,3C13000F // was 3C13005E: lui s3,0xf
patch=2,EE,0011FA14,word,26620820 // was 26629158: addiu v0,s3,2080
patch=2,EE,0011FA24,word,26630820 // was 26639158: addiu v1,s3,2080
patch=2,EE,0011FA9C,word,26630820 // was 26639158: addiu v1,s3,2080
patch=2,EE,0011FAF0,word,3C13000F // was 3C13005E: lui s3,0xf
patch=2,EE,0011FAFC,word,26620870 // was 26629180: addiu v0,s3,2160
patch=2,EE,0011FB0C,word,26630870 // was 26639180: addiu v1,s3,2160
patch=2,EE,0011FB84,word,26630870 // was 26639180: addiu v1,s3,2160
patch=2,EE,0011FBD8,word,3C13000F // was 3C13005E: lui s3,0xf
patch=2,EE,0011FBE4,word,26620830 // was 26629160: addiu v0,s3,2096
patch=2,EE,0011FBF4,word,26630830 // was 26639160: addiu v1,s3,2096
patch=2,EE,0011FC6C,word,26630830 // was 26639160: addiu v1,s3,2096
patch=2,EE,0011FCC0,word,3C13000F // was 3C13005E: lui s3,0xf
patch=2,EE,0011FCCC,word,26620880 // was 26629188: addiu v0,s3,2176
patch=2,EE,0011FCDC,word,26630880 // was 26639188: addiu v1,s3,2176
patch=2,EE,0011FD54,word,26630880 // was 26639188: addiu v1,s3,2176
patch=2,EE,0011FDA8,word,3C13000F // was 3C13005E: lui s3,0xf
patch=2,EE,0011FDB4,word,26620850 // was 26629170: addiu v0,s3,2128
patch=2,EE,0011FDC4,word,26630850 // was 26639170: addiu v1,s3,2128
patch=2,EE,0011FE3C,word,26630850 // was 26639170: addiu v1,s3,2128
patch=2,EE,0011FE90,word,3C13000F // was 3C13005E: lui s3,0xf
patch=2,EE,0011FE9C,word,26620860 // was 26629178: addiu v0,s3,2144
patch=2,EE,0011FEAC,word,26630860 // was 26639178: addiu v1,s3,2144
patch=2,EE,0011FF24,word,26630860 // was 26639178: addiu v1,s3,2144
patch=2,EE,0011FF78,word,3C13000F // was 3C13005E: lui s3,0xf
patch=2,EE,0011FF84,word,26620840 // was 26629168: addiu v0,s3,2112
patch=2,EE,0011FF94,word,26630840 // was 26639168: addiu v1,s3,2112
patch=2,EE,0012000C,word,26630840 // was 26639168: addiu v1,s3,2112
patch=2,EE,00121AF8,word,3C02000F // was 3C02005E: lui v0,0xf
patch=2,EE,00121AFC,word,24500800 // was 24509148: addiu s0,v0,2048
patch=2,EE,00121B4C,word,3C10000F // was 3C10005E: lui s0,0xf
patch=2,EE,00121B50,word,8E050800 // was 8E059148: lw a1,0x800(s0)
patch=2,EE,00121B6C,word,8E060800 // was 8E069148: lw a2,0x800(s0)
patch=2,EE,00122ED4,word,3C02000F // was 3C02005E: lui v0,0xf
patch=2,EE,00122EE4,word,8C460800 // was 8C469148: lw a2,0x800(v0)
patch=2,EE,00122EEC,word,3C02000F // was 3C02005E: lui v0,0xf
patch=2,EE,00122F2C,word,AC400810 // was AC409150: sw zero,0x810(v0)
patch=2,EE,00122F68,word,8E650800 // was 8E659148: lw a1,0x800(s3)
patch=2,EE,00122F94,word,8E620800 // was 8E629148: lw v0,0x800(s3)
patch=2,EE,00122FA0,word,AE020810 // was AE029150: sw v0,0x810(s0)
patch=2,EE,00122FB0,word,8E640800 // was 8E649148: lw a0,0x800(s3)
patch=2,EE,00122FBC,word,AE040810 // was AE049150: sw a0,0x810(s0)
patch=2,EE,00123014,word,8E650800 // was 8E659148: lw a1,0x800(s3)
patch=2,EE,0012301C,word,26720800 // was 26729148: addiu s2,s3,2048
patch=2,EE,0012306C,word,8E710800 // was 8E719148: lw s1,0x800(s3)
patch=2,EE,001231A0,word,3C02000F // was 3C02005E: lui v0,0xf
patch=2,EE,001231A4,word,3C03000F // was 3C03005E: lui v1,0xf
patch=2,EE,001231A8,word,24420810 // was 24429150: addiu v0,v0,2064
patch=2,EE,001231AC,word,24630800 // was 24639148: addiu v1,v1,2048
```

## Appendix B: ScreenEffects mirror users (51 words)
Functions `FUN_00126A88`, `0013C5A8`, `00156658`, `0018C058`, `0018DAC0`, `0018E2F0`, `0021D928`, `002371D8`,
`0039CBF0`, `0039D870`, `0039EC60`, `0039F450`, `003A31A8`: old 0x005FDEB8/0x005FDEBC become 0x000F0890/0x000F0894.
```
patch=2,EE,00126B50,word,3C02000F // was 3C020060: lui v0,0xf
patch=2,EE,00126B54,word,24500890 // was 2450DEB8: addiu s0,v0,2192
patch=2,EE,00126BE8,word,26700890 // was 2670DEB8: addiu s0,s3,2192
patch=2,EE,0013C620,word,3C02000F // was 3C020060: lui v0,0xf
patch=2,EE,0013C624,word,24500890 // was 2450DEB8: addiu s0,v0,2192
patch=2,EE,0013C6B8,word,26700890 // was 2670DEB8: addiu s0,s3,2192
patch=2,EE,00156664,word,3C03000F // was 3C030060: lui v1,0xf
patch=2,EE,001566AC,word,8C620890 // was 8C62DEB8: lw v0,0x890(v1)
patch=2,EE,001566C8,word,26840890 // was 2684DEB8: addiu a0,s4,2192
patch=2,EE,001567B0,word,8E840890 // was 8E84DEB8: lw a0,0x890(s4)
patch=2,EE,0018C0B0,word,3C02000F // was 3C020060: lui v0,0xf
patch=2,EE,0018C0BC,word,245E0890 // was 245EDEB8: addiu fp,v0,2192
patch=2,EE,0018DACC,word,3C10000F // was 3C100060: lui s0,0xf
patch=2,EE,0018DADC,word,26110890 // was 2611DEB8: addiu s1,s0,2192
patch=2,EE,0018DAFC,word,8E050890 // was 8E05DEB8: lw a1,0x890(s0)
patch=2,EE,0018DB20,word,8E640890 // was 8E64DEB8: lw a0,0x890(s3)
patch=2,EE,0018DB3C,word,8E640890 // was 8E64DEB8: lw a0,0x890(s3)
patch=2,EE,0018DB60,word,8E640890 // was 8E64DEB8: lw a0,0x890(s3)
patch=2,EE,0018DB6C,word,26700890 // was 2670DEB8: addiu s0,s3,2192
patch=2,EE,0018DB70,word,8E640890 // was 8E64DEB8: lw a0,0x890(s3)
patch=2,EE,0018DBB8,word,8E640890 // was 8E64DEB8: lw a0,0x890(s3)
patch=2,EE,0018DBC0,word,8E640890 // was 8E64DEB8: lw a0,0x890(s3)
patch=2,EE,0018DBFC,word,8E640890 // was 8E64DEB8: lw a0,0x890(s3)
patch=2,EE,0018DC0C,word,8E640890 // was 8E64DEB8: lw a0,0x890(s3)
patch=2,EE,0018DC10,word,8E640890 // was 8E64DEB8: lw a0,0x890(s3)
patch=2,EE,0018DC2C,word,3C02000F // was 3C020060: lui v0,0xf
patch=2,EE,0018DC34,word,24500890 // was 2450DEB8: addiu s0,v0,2192
patch=2,EE,0018E2F4,word,3C02000F // was 3C020060: lui v0,0xf
patch=2,EE,0018E310,word,24530890 // was 2453DEB8: addiu s3,v0,2192
patch=2,EE,0021DBF8,word,3C03000F // was 3C030060: lui v1,0xf
patch=2,EE,0021DBFC,word,24630890 // was 2463DEB8: addiu v1,v1,2192
patch=2,EE,0023721C,word,3C02000F // was 3C020060: lui v0,0xf
patch=2,EE,00237228,word,24420890 // was 2442DEB8: addiu v0,v0,2192
patch=2,EE,00237258,word,3C02000F // was 3C020060: lui v0,0xf
patch=2,EE,00237260,word,24420890 // was 2442DEB8: addiu v0,v0,2192
patch=2,EE,0039CDB4,word,3C02000F // was 3C020060: lui v0,0xf
patch=2,EE,0039CDBC,word,8C440890 // was 8C44DEB8: lw a0,0x890(v0)
patch=2,EE,0039CDF4,word,3C03000F // was 3C030060: lui v1,0xf
patch=2,EE,0039CDFC,word,24750890 // was 2475DEB8: addiu s5,v1,2192
patch=2,EE,0039D8E8,word,3C02000F // was 3C020060: lui v0,0xf
patch=2,EE,0039D8F0,word,24550890 // was 2455DEB8: addiu s5,v0,2192
patch=2,EE,0039EB98,word,3C02000F // was 3C020060: lui v0,0xf
patch=2,EE,0039EB9C,word,24510890 // was 2451DEB8: addiu s1,v0,2192
patch=2,EE,0039F398,word,3C02000F // was 3C020060: lui v0,0xf
patch=2,EE,0039F39C,word,24510890 // was 2451DEB8: addiu s1,v0,2192
patch=2,EE,0039FEC8,word,3C02000F // was 3C020060: lui v0,0xf
patch=2,EE,0039FECC,word,24510890 // was 2451DEB8: addiu s1,v0,2192
patch=2,EE,003A0048,word,3C02000F // was 3C020060: lui v0,0xf
patch=2,EE,003A004C,word,24510890 // was 2451DEB8: addiu s1,v0,2192
patch=2,EE,003A3254,word,3C02000F // was 3C020060: lui v0,0xf
patch=2,EE,003A3258,word,24500890 // was 2450DEB8: addiu s0,v0,2192
```

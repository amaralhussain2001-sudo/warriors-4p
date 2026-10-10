# Co-op camera merge/split rule and an "always split" patch (decision D8)

Static analysis only (2026-10-11). Build: The Warriors SLUS-21215 v1.03, `local/disc/SLUS_212.15` (ELF stripped;
one PT_LOAD segment, file offset 0x1000 = VA 0x00100000). All addresses are static. Function and variable names
are OUR labels. Sources: Ghidra decompile in `local/analysis/all/*.c`, Lua binding table
`local/analysis/lua_bindings.tsv`, Lua pseudo-code `local/analysis/pseudo/*.lua`, raw instruction scan of the ELF
(Python, loads/stores with `lui $x,0x0051` + 16-bit offset within 12 instructions).

## 1. Short answer

The game already has an option for this. **Options -> Camera -> "2P Split Screen Merge"** (string id 0x11E) is
stored in GameMgr+0x450 and mirrored into the global **0x0050B1C4**. Every place where the co-op camera decides to
merge checks `0x0050B1C8 != 0 && 0x0050B1C4 != 0`. With 0x0050B1C4 = 0 the two players keep separate views in
2-player gameplay. Proposed patch (section 4): keep 0x0050B1C4 at 0 during online sessions.

## 2. Variables (our labels)

| Address | Our label | Meaning | Writers | Evidence | Label |
|---|---|---|---|---|---|
| 0x0050B198 | ViewsRendered | number of views drawn this layout | only `LayoutViewports` 0x00122ED0 (store at 0x0012323C) | decompile all_00.c:23357; ELF scan finds one store | VERIFIED |
| 0x0050B19C | ActiveCameras | number of player cameras that exist | only `LayoutViewports` | all_00.c:23358 | VERIFIED |
| 0x0050B1A0 | SplitOrientation | Lua `CamSetSplitMode(n)` (0x00367270 -> 0x0011E0A8, n < 2), then `LayoutViewports` | 0x0011E0CC; reset to 0 in camera init 0x00122B80 | all_00.c:19963, 23122 | VERIFIED |
| 0x0050B1A4 | LayoutMode | = SplitOrientation, forced to 2 when views > 2 (the M1 layout patch at 0x00123300 makes this "views > 1") | `LayoutViewports` | all_00.c:23379-23396 | VERIFIED |
| 0x0050B1A8 / 0x0050B1AA | layout rows / cols | mode 0: (2,1); mode 1: (1,2); mode 2: (2,2); one view: (1,1) | `LayoutViewports` | all_00.c:23377-23396 | VERIFIED (row/col naming from M1 F-0083) |
| 0x0050B1C0 | SplitAllowed | Lua `CamEnable(3, bool)`; 0 = draw only camera 0 (one shared camera even when far apart) | `FUN_0011DE58` case 3 (also calls `LayoutViewports`); camera init sets 1; ELF initial value 1 | all_00.c:19901, 23116 | VERIFIED |
| 0x0050B1C4 | MergeOption | options menu "2P Split Screen Merge"; must be exactly 1 for a merge in `LayoutViewports` | only setter `FUN_00418AC8` (store in delay slot 0x00418AD4); ELF initial value 1; "Restore Default" (0x001D80E0) sets 1 | all_07.c:9532; all_02.c:5594-5604, 5621-5629, 6170-6175; menu text in WARRIORS.WAD (EN "2P Split Screen Merge", DE "2SP-Split-Screen vereinen") | VERIFIED |
| GameMgr+0x450 | saved MergeOption | copy kept in the game settings (GameMgr pointer at 0x0051489C); menu shows On when != 0 | same setter; several settings load/save sites (e.g. 0x001B84C4, 0x001B8500) | ELF scan | VERIFIED (store sites); HYPOTHESIS (which ones are load/save) |
| 0x0050B1C8 | MergeAllowed | Lua `CamEnable(4, bool)`; scripts switch it per section | `FUN_0011DE58` case 4; camera init sets 1; ELF initial value 1 | all_00.c:19905, 23115 | VERIFIED |

`CamEnable(option, bool, player=-1)` is the Lua binding at 0x003671E0 -> `FUN_0011DE58(option, value, player)`
(VERIFIED, lua_bindings.tsv + decompile). Mission and Rumble scripts call `CamEnable(3, false)` 136 times,
`CamEnable(3, true)` 63 times, `CamEnable(4, true)` 54 times and `CamEnable(4, false)` 19 times (pseudo-code grep;
VERIFIED counts). Samples show `CamEnable(3, false)` before win cameras, fixed level cameras and cut-scene cameras.

## 3. How the merge is decided

### 3.1 `LayoutViewports` 0x00122ED0 (our label) — detects a merge, does not cause it
- Camera 0 (pointer 0x005D9148) is drawn if its "active" query (vfunc +0x28C) is true or SplitAllowed is 0.
  With fewer than 2 players it is always drawn (`GameMgr+0x224 < 2`). VERIFIED (all_00.c:23260-23283).
- `merged = 1` only if all of: MergeAllowed (0x0050B1C8) != 0, MergeOption (0x0050B1C4) == 1, camera 0 drawn,
  both camera pointers (0x005D9148, 0x005D914C) set, a mode query (vfunc +0x1EC) returns 1 on both cameras, and
  the two cameras are the same object or have the same two vectors (vfuncs +0x21C and +0x224; squared difference
  <= 1e-10). VERIFIED (all_00.c:23287-23335).
- Every further player camera is drawn if it is active, SplitAllowed != 0 and `merged == 0`. VERIFIED (23339-23353).
- So the views count is 1 when the camera controllers have moved both cameras onto one pose. The decision to do
  that is in the camera update code below.

### 3.2 Follow camera update `FUN_00126C40` (our label: FollowCamUpdate, size 2656)
- Runs the 2-player logic only when ActiveCameras is exactly 2. VERIFIED (all_00.c, function start).
- Reads both player positions (handles at GameMgr+0x228/+0x22C, index at +0x92 into the position table at
  0x00714B00, stride 0x20, height offset from camera field 0x82) and computes a squared distance (two components).
  VERIFIED (code); HYPOTHESIS (that the two components are the ground plane).
- Thresholds: squared distance > 56.25 (7.5 units) clears the "close" flag; the merged state is kept only while the
  squared distance <= 121.0 (11 units). VERIFIED (constants and comparisons).
- Both players must pass an on-screen test (vfunc +0x16C with margin 0.3) and line-of-sight tests (`FUN_00350CD8`,
  probably a ray cast). Neither player may have field +0x1F8 set (objects at 0x005FDEB8 / 0x005FDEBC). The camera
  flag +0x475 must be 0. VERIFIED (code); HYPOTHESIS (meaning of +0x1F8 and +0x475).
- Merging happens only if `0x0050B1C8 != 0 && 0x0050B1C4 != 0`; when views != 1 and the merge flags are off, the
  function clears its merge state (`param_1[0x108] = 0`) and keeps the split. VERIFIED (all_00.c:26509-26520,
  26752-26765).
- Camera type 9 update `FUN_0013C710` has the same pattern: when views == 2, mode 9 and both merge flags set, a
  timer field (`[0xF7]`) accumulates frame time while the squared distance <= 56.25 and the visibility test passes,
  otherwise it resets. VERIFIED (all_00.c around 42080-42100).
- `FUN_001282A0` (camera object list) also branches on the two merge flags. VERIFIED (all_00.c:27314).

Fits the runtime observations (HYPOTHESIS until tested): players idle together -> timer runs -> merge after a few
seconds (v4: merge 5.4 s after recording started); walking about 5 s away -> more than 7.5-11 units -> split
(F-0096); a camera turn alone did not split in Mission 9 (both players still on screen); F-0084's split on a
camera turn with moving bots could be the on-screen test failing.

## 4. Proposed patch: always split in 2-player gameplay

Patch the option, not the counter: all merge decision sites already honour MergeOption, and "Off" is a setting the
original game offers in its own menu.

```
// D8: keep "2P Split Screen Merge" off during online sessions
patch=1,EE,0050B1C4,word,00000000 // was 00000001 (ELF initial value; savestates hold 1): MergeOption = 0 every vsync
patch=2,EE,00418AD4,word,AC40B1C4 // was AC45B1C4: sw a1,-0x4E3C(v0) -> sw zero,-0x4E3C(v0) (setter stores 0)
```

- Setter `FUN_00418AC8` (VERIFIED instruction words): `0x00418AC8 3C020051 lui v0,0x51`,
  `0x00418ACC AC850450 sw a1,0x450(a0)`, `0x00418AD0 03E00008 jr ra`, `0x00418AD4 AC45B1C4 sw a1,-0x4E3C(v0)` (delay slot).
  The second line makes the setter write 0 to the live flag, so the menu, "Restore Default" or loading settings
  cannot switch merging back on between two vsyncs. GameMgr+0x450 is left alone, so the player's saved option
  and the menu text are not changed.
- The first line covers the initial value and savestates. Either line alone is weaker: line 1 alone leaves a
  window of less than one vsync after a setter call; line 2 alone leaves the initial 1 in place until the setter
  runs.
- Effect expected (HYPOTHESIS until a runtime test): in 2-player gameplay ViewsRendered stays 2; each player has
  their own camera at all times.
- Unchanged (HYPOTHESIS, from the code paths above): one player (player count < 2 skips the extra cameras);
  cut-scenes, win cameras and fixed scripted cameras that call `CamEnable(3, false)` still draw one shared camera
  (views = 1) because SplitAllowed is 0 there; menus.
- Applies to two cameras only. The 2-player merge code only runs when ActiveCameras == 2; four players need the M2
  engine extension anyway.

Runtime test to run before relying on it: a 2-player lockstep session with bots idle together for 30 s (views must
stay 2), the "apart" pattern, a cut-scene (views 1 then 2 again), a single-player load, and equal hash streams.

## 5. What else reads the merged/split state (effects on the simulation)

The views count and the merge state are read outside the renderer, so "always split" changes game behaviour
compared with "merged" (identically on every instance, so no desync is expected).
- `FUN_00244770`: a human/player function. When ViewsRendered == ActiveCameras and the player's camera mode is 2,
  it computes a vector between the player and their own camera. HYPOTHESIS: camera-relative movement or aim.
  VERIFIED read (all_03.c, inside FUN_00244770; ELF load at 0x00244A70).
- `FUN_0023DC58`: a player-related check that requires player count == ViewsRendered and camera mode 2.
  VERIFIED read; meaning HYPOTHESIS.
- `FUN_0024B3D8`: uses ViewsRendered + ActiveCameras together with player state at 0x005FDEB8. VERIFIED read.
- `LayoutViewports` sets a camera value (vfunc +0x1B4, at least 40, scaled by 0x0050B200) when the views go from 1
  to more than 1. HYPOTHESIS: field of view.
- Other ViewsRendered readers found by the ELF scan (not analysed): 0x00102DE4/0x00102E3C (FUN_00101DD8),
  0x0011E5C0, 0x0011E6CC, 0x0011E90C, 0x0011EAE8, 0x0011F3A0-0x0011F8C4 (FUN_0011EE08), 0x00121C68, 0x00124050,
  0x0012616C, 0x00126DE4, 0x0012771C, 0x00127B24, 0x001283E4, 0x0012B468, 0x0012DF90, 0x001346DC, 0x001361E4,
  0x00137E64, 0x0013B5E8, 0x0013B90C, 0x0013C890, 0x0013CD24, 0x0013CF60/78, 0x001454FC, 0x001673C0/0x00167844/
  0x00167D3C (FUN_001673B8), 0x0023DDF0, 0x00244A70, 0x0024B3E0.
- E2 (Stage 1) already showed that the game camera feeds the simulation. Not checked: whether AI, spawning or
  streaming use the per-view visibility; whether any Lua binding reads the merge state.

## 6. Limits of this analysis
- The ELF scan only finds accesses built from `lui 0x0051` plus an offset within 12 instructions; gp-relative or
  computed addresses are not covered. Ghidra's decompile shows the same writers.
- Nothing here was run. All behaviour claims about the patch are HYPOTHESIS until the runtime test in section 4.

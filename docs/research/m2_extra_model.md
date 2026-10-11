# M2/M6 research: loading one extra Warrior model for player 4 (static analysis, 2026-10-11)

Problem (F-0143): in Mission 13 (level9) only the Rembrandt, Snow, Fox and `warr_cl_gen` Warrior models are resident,
so when player 4 joins and no companion is free, `SPAWN` + `CHOOSE` fall back to a copy of player 1 (Rembrandt) and the
HUD says REMBRANDT. Decision D14 option A (`docs/DECISIONS.md`): load one extra Warrior model when a fourth player joins.
`CHOOSE` (0x000E1400, `m2_spawn_name.md`) already picks the first configured + resident + absent Warrior; this note
makes one more Warrior model resident with the game's own model-pinning code and gates the 4th join on it.

Sources and conventions:
- **Static analysis only; nothing was run.** No emulator was started, no test runner, no build (a 4-instance lockstep
  run was in progress and was not touched). Build SLUS-21215 v1.03, `local/disc/SLUS_212.15` (read-only); addresses are
  static (ELF) unless marked. Decompile `local/analysis/all/all_*.c`, callers `local/analysis/callers.pkl`, bindings
  `local/analysis/lua_bindings.tsv`, pseudo-Lua `local/analysis/pseudo/`, disc index `local/disc/WARRIORS.DIR/.WAD`
  (read-only). Disassembly with the scratch R5900 disassembler used for `m2_spawn_name.md`.
- Function names are OUR labels (the ELF is stripped). Labels: VERIFIED / HYPOTHESIS / BLOCKED / FAILED TEST.
- "dict" = the model dictionary `*(0x0050CD4C)`; "char table" = 0x00684620 + id*0x1AC; "mi" = model index
  (u16 at char table +0x112).

## Summary
1. **`SetCharacterModel(id, r)`** = binding 0x0036E6C0 -> `FUN_0040CDA8` -> **`FUN_0018AD40(dict, id, r != 0)`** (the only
   call of `FUN_0018AD40` in the ELF, 0x0040CDC0). Pin (r = 0/nil/false): put mi in a 32-entry list at dict+0xB4
   (`{mi, instance}`), set dict+0x1B4 = 1, and if the model is already resident build an instance at once. Release:
   clear the entry and drop its instance. VERIFIED (disassembly 0x0018AD40-0x0018AEBC).
2. **A pin does not load anything by itself.** The streamer `FUN_001897A8` services pins first: fit test
   `FUN_001775D8` (evicts unreferenced cached assets if needed), then `FUN_00177B00` queues three file loads (animation
   set, character model, texture). Residency (`FUN_001774D0(dict, entry, 0, 0)`) becomes true when all three are
   registered; the next streamer call builds the pin's instance. VERIFIED code.
3. **The streamer is called only by the scheduler `FUN_0040F8A0` (0x0040FD7C), and only when some human/object asks for
   a model.** Pins register no request priority, so a pin alone can wait in a quiet scene. HYPOTHESIS H1 (static
   reading of the scheduler). The design therefore calls the streamer itself once after pinning (POKE).
4. **Memory:** streamed models live in the **"Sector Pool"** `*(0x006EB9C8)`, an mmalloc-style pool sized at level
   setup to (free memory - 128 KB). No character budget: it is one LRU cache for character models, textures, animation
   sets, car/object models and particle pages. If a model does not fit, the fit test evicts least-recently-used
   unreferenced assets; if still no room it answers "no" (no assert, no crash) **and the streamer returns early, so a
   pin that can never fit blocks all later model streaming of the level.** A failed pool allocation itself writes to
   address 0 (`FUN_00338BF0`), which the fit test exists to avoid. VERIFIED code.
5. **One Warrior model** = animation set + model + texture: Swan 374,767 bytes (366 KB); the fit test needs free holes
   of 256 + 128 + 128 KB. All nine: 290-399 KB (table 3.1). HYPOTHESIS (values from the dictionary copy in WAD entry
   10671; the survey reads the runtime values).
6. **Game scripts pin and then spawn without waiting** (e.g. `07965:11-20`, `07337:44-51`, `08838:69` pins Cleon long
   before `08838:278 HuCreate("Cleon", 1, ...)`); no script polls, and no Lua binding reports "model loaded". The engine
   test to reuse is `FUN_001774D0` (as `CHOOSE` does). VERIFIED (script text, binding list).
7. **Mission 13 memory is unknown** until the read-only survey X0 (section 3.2, script included) runs.
8. **Recommended design:** start loading player 4's Warrior when the **third** player joins; on the fourth join, if it
   is still loading, refuse that Start press (nothing happens, the next press joins); after 20 s of waiting the next
   press joins as the old Rembrandt copy. Unused pins are released; the pin of player 4's Warrior is released when that
   player leaves; level teardown and a "does not fit" valve clear our state. 380 code words at **0x000E1600-0x000E1BEF**,
   data **0x000E1C00-0x000E1C4B**; replaces 3 words of the W4P spawn caves and hooks 3 game calls.
9. **Check:** `note_patches.py check` gives 0 problems for pnach (without the 3 replaced lines and without `[4p hud A]`)
   + fragment; every word round-trips; 141 of 220 distinct code words occur verbatim in the game ELF (section 5).
10. **Lockstep:** every decision comes from game RAM on the game thread; streaming completion is deterministic as far as
   the existing lockstep runs show (q12: 15 min of streaming, 0 mismatches). HYPOTHESIS for the new load; test X5.

---

## 1. How `SetCharacterModel` works (question 1)

### 1.1 Call chain (VERIFIED, disassembly)
| Step | Address | Detail |
|---|---|---|
| Lua binding | 0x0036E6C0 | arg 1 -> `FUN_004091C8`, `FUN_0042C388` (number -> int); arg 2 -> `FUN_00409318`, then `sltu a1,zero,v0` (0x0036E6FC): release = (arg 2 != 0); nil/false/0 = pin |
| wrapper | `FUN_0040CDA8` | `FUN_0018AD40(*(0x0050CD4C), id, release)` at 0x0040CDC0 - the only `jal 0x0018AD40` in the ELF (full scan) |
| core | `FUN_0018AD40` | 0x0018AD40-0x0018AEBC, below |

### 1.2 `FUN_0018AD40(dict, id, release)` and the pin list (VERIFIED)
- mi = `lhu 0x112(char table entry)` (0x0018AD94). Always +0x112: the level getters `FUN_004DAB58`/`FUN_004DAB50` are
  called (0x0018AD78/0x0018AD80) but their results are unused, so in levels 60-64 (where humans use +0x114,
  `m2_spawn_name.md` 2.1) a pin would load the wrong variant.
- Pin list: dict+0xB4 + 8*i, i = 0..31: `{u32 mi (0xFFFFFFFF = free), u32 CharacterInstance pointer}`; dict+0x1B4 =
  "pins pending" flag.
- **Pin** (release = 0, 0x0018ADFC-0x0018AE94): mi already listed -> return (idempotent). Otherwise the **last** free
  slot (`movz` at 0x0018AE1C); no free slot -> silently nothing. Write mi, instance 0, dict+0x1B4 = 1; if
  `FUN_001774D0(dict, entry, 0, 0)` -> instance = `FUN_00177B80(dict, entry, 0)`.
- **Release** (0x0018ADB0-0x0018ADF0): every entry equal to mi -> 0xFFFFFFFF; an existing instance goes to
  `FUN_00177E00` (instance +8 refcount -1, freed).
- Instances hold references: `FUN_00177B80` fetches each component with `FUN_001783D0` (model), `FUN_0016E8F0`
  (animation), `FUN_0018E9E0` (texture); `FUN_001783D0` increments the component record's refcount (record+4)
  (HYPOTHESIS that the other two do the same; not read). A CharacterInstance is 0x330 bytes ("CharacterInstance",
  0x00551D80) from the current heap (the level pool, 1.4).
- **Clear all pins:** `FUN_0018AB20` (every entry -1, instances released), called only at 0x00188AEC (`FUN_00188AA8`) and
  0x00189734 (`FUN_00189718`), both called only from `FUN_001607B8` (callers.pkl), which unloads the level (decompile:
  `FUN_00178BC8(dict, hash of the level name)` and many cleanups; our reading: level teardown).

### 1.3 When the model is not resident (VERIFIED code unless marked)
Dictionary entry (32 bytes at `*(dict+0x88) + mi*32`): +0 CRC32 of the model name (`FUN_00143F68`, table from
0xEDB88320), +4 animation-set id, +8 character-model id, +0xC texture id, +0x10 animation bytes, +0x14 model file bytes,
+0x18 model memory bytes, +0x1C texture bytes. Each component is a node in its own tree (lower_bound `FUN_004DE458`,
unsigned compare, header `*(tree+4)`, root header+4, left +8, right +0xC, key +0x10, record +0x14): animation dict+0x40
(key +4), model dict+0x00 (key +8), texture dict+0x30 (key +0xC). `FUN_001774D0(dict, e, 0, 0)` = all three present.

Streamer `FUN_001897A8`, pin part 0x00189874-0x00189934:
1. Returns at once while dictionary loads are pending (`FUN_00185990`: dict+0xC6C != 0).
2. If dict+0x1B4: first pinned entry without instance -> `FUN_001775D8(dict, e, 0, 1)` (fit test, 0x001898C8).
   Fails -> return 0 (0x001898D0 -> 0x00189910): later pins and all human/object requests wait for the next call.
3. Not resident -> `FUN_00177B00(dict, e, 0)`: animation (type 5, `FUN_0016EA20`), model (type 3, `FUN_001782E8`),
   texture (type 4, `FUN_0018EB10`) -> `FUN_00187AA8` -> loader `*(0x005E5340)` (`FUN_00154D50`); return 1.
4. Resident -> instance `FUN_00177B80`, stored in the pin entry (0x00189E84 path).
5. When no pin lacks an instance: dict+0x1B4 = 0, then human/object requests by priority.

Completion: the loader calls `FUN_001866E8` -> `FUN_00186710`, which allocates a sub-heap of the request's memory size
in the Sector Pool (`FUN_00338420`), builds the asset there (`FUN_00144180`) and hands it to `FUN_00187098`
(registration; HYPOTHESIS that it inserts the tree node - not decoded).
Residency becomes true when all three components are registered; the pin's own instance appears on the next streamer
call.

Who calls the streamer: only `FUN_0040F8A0` (0x0040FD7C), the streaming scheduler. It has 17 callers, 13 of them
without direct callers at 0x00155C78-0x0015F308 (vtable methods; HYPOTHESIS: game-state updates, once per frame). It
returns early while the loader queue is not empty
(0x0040F96C-0x0040F978, `FUN_00154A68(*(0x005E5340)) != 0`), and calls the streamer only if some request exists (world
sectors, the +0x5C manager, or a dictionary request below FLT_MAX) **and** the lowest priority is not a world
sector's. Dictionary priority = min(dict+0xBCC, +0xBDC, +0xBEC, +0xBFC) (`FUN_00189750`) x `*(float*)0x005147CC`
(0.001 in the ELF; `SetLoadPriority` sets it, e.g. `08031:1276 SetLoadPriority(0.01)`). Humans write +0xBCC
(`FUN_0018A430`); **pins write no priority** -> HYPOTHESIS H1: a pin is serviced only when a human/object model request
makes the scheduler call the streamer (pins go first in that call).

### 1.4 Memory: pool, budget, failure (VERIFIED code; sizes need the survey)
- **Heap:** the dictionary's heap getter `FUN_001879B8` -> `FUN_0040F850` returns `*(0x006EB9C8)` = **"Sector Pool"**,
  a MemoryPoolHeap (vtable 0x00544428) created by `FUN_0040D688` (WorldManagerPS2.cpp) with size = (free size of the
  current heap, memory manager vtable +0x84) - 0x20000; "Sector Pool 2" `*(0x006EB9CC)` gets the rest - 0x20000. The
  fit test and the load callback allocate there. CharacterInstances come from the "Level Dynamic & LUA Pool"
  `*(0x006EB9B8)`, 0x1EF000 bytes (`FUN_0033AFE0`).
- **Allocator:** `FUN_00338A78`/`FUN_0033B9D0`/`FUN_0033B1A0` are an mmalloc-style (GNU malloc) descriptor at
  H = `*(pool+4)`: +0x18 morecore (0x00338948: fails past +0x40), +0x30 heap base, +0x38 heap limit (1 KB blocks),
  +0x3C heapinfo (12-byte entries; free clusters `{size, next, prev}`, list head = entry 0), +0x40 capacity, +0x44
  chunks used, +0x48 bytes used, +0x4C chunks free, +0x50 bytes free, +0xA8 base, +0xB0 break. "Largest free block"
  (vtable +0x84 = `FUN_00338D30`) is found by trial allocations.
- **Budget:** none for characters. One LRU cache over 7 asset trees: character models (dict+0x00), textures (+0x30),
  animation sets (+0x40), and +0x10, +0x20, +0x50, +0x60 for car models, object models, particle pages and a second
  animation kind (which offset is which was not decoded).
- **Size rounding for the fit test:** `FUN_001848D0` = max(32 KB, next power of two) (0x001848D0-0x00184910). Model
  memory = entry+0x18 when non-zero (`FUN_00187960` type 3), animation = +0x10 (type 5), texture = +0x1C + 0x70 (type 4).
- **Does not fit:** `FUN_001775D8(.., 1)` calls `FUN_00187D28(dict, size, 0)`: while the largest free block is too
  small, evict the least-recently-used **unreferenced** asset (record+4 == 0, older than now, not locked, not pending)
  through its unload (`FUN_001784F0` CharacterModel.cpp, `FUN_00173BD0` CarModel.cpp, `FUN_001814F0` ObjectModel.cpp,
  `FUN_0018EC00` Texture.cpp, `FUN_001821D0` ParticlePage.cpp, `FUN_0016EB10`/`FUN_0016F368` Animations.cpp); return 0
  when nothing evictable is left -> fit test 0 -> no load, no assert. `FUN_00187AA8` evicts again when it queues.
- **Hard failure:** the pool allocator `FUN_00338BF0` (vtable +0x54) does `*(u32*)0 = 1` and returns 0 when the
  allocation fails. `FUN_00187AA8` takes a request record from dict+0x9028 without an exhaustion check (HYPOTHESIS:
  null write if too many loads are queued; one model = 3 records).

### 1.5 Humans stream their own model (VERIFIED code, HYPOTHESIS visual effect)
Every human update `FUN_0023D660` calls `FUN_0018A430(distance, dict, human)` (0x0023D6BC): a human without model
instance (human+0xD8 == 0) requests with priority 0; the streamer (0x00189A0C-0x00189B18) loads the animation set first
(partial model), then the full model (`FUN_00177D50`). The farthest full-model human is a downgrade candidate
(dict+0xBC0, `FUN_0018A2B0`). This is why the game's "pin, then spawn" scripts work even before the pin is serviced: the
new humans pull the load. It is not used for player 4 here: spawning before residency would show player 4 without a
body for a while, and a model that never fits would leave him invisible.

## 2. How the level scripts use it (question 2, VERIFIED, pseudo-Lua)
| File:line | What happens |
|---|---|
| `07965_a7d2bd19.lua:11-19`, `:20`, `:41` | pins 9 chars (216, 217, 150, 151, 259, 81, 82, 110, 111), then at once `AddRiotScenePeds()` and spawners |
| `07965_a7d2bd19.lua:97-105` | releases the same 9 at the chapter end, before `RemoveGang` |
| `07337_13c4b542.lua:44-48`, `:51`, `:61` | loop pins a list `{338, 339, ...}`, then `C2.AddRomanGangs2()`; `SetCharacterModel(316, 1)` releases |
| `07655_993b75be.lua:244-252`, `:260` | `SetCharacterModel(253)` (no 2nd argument = pin) x 9 during script load, then `Main()` |
| `08838_0d1362fe.lua:69`, `:278` | pins **Cleon (char 1)** in the setup; much later `HuCreate("Cleon", 1, ...)` in an event (`main_9`) |
| `08838_0d1362fe.lua:155-156` | releases chars 4 and 9 |
| `09317_a02c5c1e.lua:210-218`, `:219`, `:540-548` | pins 197, 199, 180, **2**, **27**, 303 and spawner chars, then `AddSpecialBums()`; releases the same list later |
| `08257_d8b9dc4a.lua:20-27`, `:31`, `:46-53` | pins 174, 175, 164, 165 and `CharGenSpawner8[1]`..., then `SetupParkEvent()`; `true` releases |
| `08184_a4d8f991.lua:57` | pins **Vermin (26)** in a setup |
| `09229_c05eacb5.lua` (Mission 13) | no `SetCharacterModel` call |

- **Before HuCreate, no wait:** every example pins and continues; spawners/HuCreate follow immediately or in later
  events. No script polls or waits for a load.
- **No query binding:** the binding list has no "model loaded" function (only `SceneIsPreloaded` for scenes, and
  `SetLoadPriority`, `preLoadFile`, `PrecacheWorld`, `QueueFileToPrecache`). Reusable engine tests: `FUN_001774D0(dict,
  FUN_001780D8(dict, mi), 0, 0)` (as `CHOOSE`) and "pin serviced" = the pin entry's instance word != 0.
- Level scripts do pin Warrior ids (1, 2, 26, 27): our code must never release a pin it did not create (4.5).

## 3. Memory in Mission 13 (question 3)

### 3.1 Size of one Warrior model (HYPOTHESIS: static values from the disc)
The dictionary records were found in WAD entry 10671 (DIR index; offset 0x58FCE800, 1,041,808 bytes; 32-byte records
at 0xD3630.., located by the CRC32 of each model name). Entry 10672 holds identical values. Cross-check (VERIFIED): the
model file sizes (+0x14) equal the sizes of WAD entries 741, 755, 1825, 1876, 1989, 1995, 2439, 2721, 2834, each of which
contains its Warrior's own name hash.

| Warrior | Model | Animation (+0x10) | Model (+0x18) | Texture (+0x1C + 0x70) | Total | Fit-test holes |
|---|---|---|---|---|---|---|
| Swan | `warr_sw` | 200,896 | 106,767 | 67,104 | 374,767 (366 KB) | 512 KB (256+128+128) |
| Ajax | `warr_aj` | 121,808 | 108,079 | 67,104 | 296,991 (290 KB) | 384 KB (128+128+128) |
| Snow | `warr_sn` | 193,872 | 112,223 | 67,104 | 373,199 (364 KB) | 512 KB |
| Cochise | `warr_co` | 227,040 | 114,127 | 67,104 | 408,271 (399 KB) | 512 KB |
| Vermin | `warr_ve` | 217,296 | 111,023 | 67,104 | 395,423 (386 KB) | 512 KB |
| Fox | `warr_fo` | 204,000 | 110,031 | 67,104 | 381,135 (372 KB) | 512 KB |
| Rembrandt | `warr_re` | 200,640 | 103,647 | 67,104 | 371,391 (363 KB) | 512 KB |
| Cleon | `warr_cl` | 214,608 | 107,247 | 67,104 | 388,959 (380 KB) | 512 KB |
| Cowboy | `warr_cb` | 200,448 | 103,327 | 67,104 | 370,879 (362 KB) | 512 KB |
| (Cleon gen) | `warr_cl_gen` | 2,126,704 | 107,247 | 67,104 | 2,301,055 | (resident in M13) |

- `warr_cl` shares model and texture ids with `warr_cl_gen`, so in Mission 13 Cleon would need only his 214,608-byte
  animation set - but a Cleon is present there (char 2, HUD index 8), so `CHOOSE` rejects him.
- With the current `CHOOSE` table order the Mission 13 target is **Swan** (first configured, absent, not resident;
  F-0143). Ajax is the cheapest (by 78 KB); the order is data (0x000E1580) if the user prefers that.
- The `_a` (levels 60-64) and `_fury` (config `03768`) variants are separate records and may differ.

### 3.2 Test X0: read-only PINE survey
Save the script below as `tests/m2/extra_survey.py` and add `--probe extra_survey:survey_mem:<poll>` to the usual
Mission 13 `nav_probe.py` run (current patch set, fragment NOT applied), e.g. at poll 8300 (2 players), 8450 (3 players)
and 8700 (4 players, clone). It only reads (`read32`, `dump`). It reports:
- Sector Pool, Sector Pool 2, level pool: capacity, bytes used, free in heap, unclaimed tail, number of free clusters,
  largest cluster, largest possible block, total free.
- Dictionary: count, the 32-entry pin list (with model names for Warriors), dict+0x1B4, loads pending, request
  priorities; loader queue length; live humans and how many have no model instance (+0xD8 == 0).
- For each named Warrior: model index, the three components (id, bytes, resident, refcount), missing bytes, fit-test
  holes and an approximate "fits without eviction" (necessary, not sufficient: holes must exist at the same time).
- Unreferenced (refcount 0) nodes and their known bytes in the three character trees (an upper bound of what eviction
  can free there; other trees only counted).
- W4P words: `CHOOSE` result/statuses and the new words of section 4.

Decision help (proposal): go to X1 if the Sector Pool `largest_possible` >= 256 KB, or if unreferenced character bytes
plus `total_free` exceed ~1 MB. Either way the engine's own fit test decides at runtime, and a "does not fit" result
falls back to the clone (4.2). Syntax-checked and run against synthetic memory images (zero memory; a fake pool,
dictionary and trees); never run against the game.

```python
"""Read-only PINE survey for docs/research/m2_extra_model.md (test X0): the Sector Pool that holds streamed models,
the 32-entry model pin list, and what one more Warrior model would need. Reads only (Pine.read32).
Standalone: python -I <this file> <pine slot>     As a probe: survey_mem(p) returns a dict (nav_probe --probe)."""
import json
import os
import struct
import sys
import zlib

WARRIORS = [(5, "Swan", "warr_sw"), (11, "Ajax", "warr_aj"), (33, "Snow", "warr_sn"), (15, "Cochise", "warr_co"),
            (26, "Vermin", "warr_ve"), (21, "Fox", "warr_fo"), (30, "Rembrandt", "warr_re"), (1, "Cleon", "warr_cl"),
            (18, "Cowboy", "warr_cb")]
NAMES = {zlib.crc32(n.encode()) & 0xFFFFFFFF: n for _, _, b in WARRIORS for n in (b, b + "_a", b + "_fury")}
NAMES[zlib.crc32(b"warr_cl_gen") & 0xFFFFFFFF] = "warr_cl_gen"


def survey_mem(p):
    r32 = p.read32

    def r16(a):
        return (r32(a & ~3) >> (8 * (a & 2))) & 0xFFFF

    def block(n):                      # FUN_001848D0: max(32 KB, next power of two)
        b = 1
        while b < n:
            b <<= 1
        return max(b, 0x8000)

    def lookup(tree, key):             # FUN_004DE458/8D0/BE8 lower_bound (unsigned), header *(tree+4), root header+4
        head = r32(tree + 4)
        if not head:
            return 0
        node, best, n = r32(head + 4), head, 0
        while node and n < 64:
            if r32(node + 0x10) < key:
                node = r32(node + 0xC)
            else:
                best, node = node, r32(node + 8)
            n += 1
        return best if best != head and not key < r32(best + 0x10) else 0

    def walk(tree, cap=20000):         # in-order node list (left +8, right +0xC)
        head = r32(tree + 4)
        if not head:
            return []
        out, stack, node, seen = [], [], r32(head + 4), set()
        while (stack or node) and len(out) < cap:
            if node and node != head and node not in seen:
                seen.add(node)
                stack.append(node)
                node = r32(node + 8)
            elif stack:
                node = stack.pop()
                out.append(node)
                node = r32(node + 0xC)
            else:
                break
        return out

    def pool(ptr_addr):                # MemoryPoolHeap (vtable 0x00544428) over an mmalloc-style descriptor
        P = r32(ptr_addr)
        if not P:
            return None
        H = r32(P + 4)
        d = {"obj": hex(P), "vtable": hex(r32(P)), "base": hex(r32(P + 8)), "size": r32(P + 0xC)}
        if not H:
            return d
        cap, used, free_in = r32(H + 0x40), r32(H + 0x48), r32(H + 0x50)
        claimed = (r32(H + 0xB0) - r32(H + 0xA8)) & 0xFFFFFFFF
        info, limit = r32(H + 0x3C), r32(H + 0x38)
        big, adj, n, i, seen = 0, 0, 0, r32(info + 4) if info else 0, set()
        while i and i not in seen and n < 20000:   # free clusters: heapinfo[i] = {size blocks, next, prev}
            seen.add(i)
            size = r32(info + 12 * i)
            big = max(big, size)
            if i + size == limit:
                adj = size
            i, n = r32(info + 12 * i + 4), n + 1
        tail = max(cap - claimed, 0)
        d.update({"capacity": cap, "bytes_used": used, "bytes_free_in_heap": free_in, "chunks_used": r32(H + 0x44),
                  "chunks_free": r32(H + 0x4C), "claimed": claimed, "unclaimed_tail": tail, "free_clusters": n,
                  "largest_cluster": big * 1024, "largest_possible": max(big * 1024, adj * 1024 + tail),
                  "total_free": free_in + tail})
        return d

    out = {"clock_ms": r32(r32(0x0050B734) + 0x38) if r32(0x0050B734) else None,
           "sector_pool": pool(0x006EB9C8), "sector_pool_2": pool(0x006EB9CC), "level_pool": pool(0x006EB9B8)}
    L = r32(0x005E5340)
    if L:                              # FUN_00154A68: queued loader requests (deque of 84-byte items)
        m = lambda x: (x * 0x3CF3CF3D & 0xFFFFFFFF) >> 2  # noqa: E731
        out["loader_queue"] = ((((r32(L + 0x38) - r32(L + 0x28)) & 0xFFFFFFFF) >> 2) - 1) * 6 + \
            m((r32(L + 0x2C) - r32(L + 0x30)) & 0xFFFFFFFF) + m((r32(L + 0x24) - r32(L + 0x1C)) & 0xFFFFFFFF)
    D = r32(0x0050CD4C)
    if not D:
        out["dict"] = None
        return out
    count, ents = r32(D + 0x84), r32(D + 0x88)
    n = min(count, 4096)               # dictionary entries (32 bytes): name hash, anim/model/texture ids, sizes
    if hasattr(p, "dump") and n:
        blob = p.dump(ents, 32 * n)
        raw = [list(struct.unpack_from("<8I", blob, 32 * k)) for k in range(n)]
    else:
        raw = [[r32(ents + 32 * k + 4 * j) for j in range(8)] for k in range(n)]
    size_of = {"anim": {}, "model": {}, "tex": {}}
    for e in raw:
        size_of["anim"][e[1]] = e[4]
        size_of["model"][e[2]] = e[6] or e[5] + 0x2000
        size_of["tex"][e[3]] = e[7] + 0x70
    trees = {"model": D + 0x00, "tex": D + 0x30, "anim": D + 0x40}
    out["dict"] = {"addr": hex(D), "count": count, "pin_flag_1B4": r32(D + 0x1B4), "loads_pending_C6C": r32(D + 0xC6C),
                   "state_BBC": r32(D + 0xBBC), "human_request_BC4": hex(r32(D + 0xBC4)),
                   "request_priorities": [struct.unpack("<f", struct.pack("<I", r32(D + o)))[0]
                                          for o in (0xBCC, 0xBDC, 0xBEC, 0xBFC)],
                   "pins": [(i, r32(D + 0xB4 + 8 * i), hex(r32(D + 0xB8 + 8 * i))) for i in range(32)
                            if r32(D + 0xB4 + 8 * i) != 0xFFFFFFFF]}
    out["dict"]["pins"] = [{"slot": i, "model_index": mi, "instance": inst,
                            "name": NAMES.get(raw[mi][0], hex(raw[mi][0])) if mi < len(raw) else "?"}
                           for i, mi, inst in out["dict"]["pins"]]
    evict = {}
    for k, t in trees.items():         # unreferenced (refcount 0) character components: what eviction could free
        nodes = walk(t)
        zero = [nd for nd in nodes if r32(r32(nd + 0x14) + 4) == 0]
        evict[k] = {"nodes": len(nodes), "unreferenced": len(zero),
                    "unreferenced_bytes_known": sum(size_of[k].get(r32(nd + 0x10), 0) for nd in zero)}
    out["character_trees"] = evict
    out["other_trees_nodes"] = {hex(o): len(walk(D + o)) for o in (0x10, 0x20, 0x50, 0x60)}
    G = r32(0x0051489C)
    level = r32(G + 0x14D8 + r16(G + 0x56DC) * 0x84) if G else -1
    off = 0x114 if 0 <= level - 60 < 5 else 0x112
    out["level"], out["model_field"] = level, hex(off)
    sp = out["sector_pool"] or {}
    cands = {}
    for cid, name, base in WARRIORS:
        mi = r16(0x00684620 + cid * 0x1AC + off)
        if mi >= count:
            cands[name] = {"char": cid, "model_index": hex(mi), "status": "no model index"}
            continue
        e = raw[mi]
        comp = {"anim": (trees["anim"], e[1], e[4]), "model": (trees["model"], e[2], e[6] or e[5] + 0x2000),
                "tex": (trees["tex"], e[3], e[7] + 0x70)}
        need, need_blocks, parts = 0, [], {}
        for k, (t, key, size) in comp.items():
            nd = lookup(t, key)
            parts[k] = {"id": hex(key), "bytes": size, "resident": bool(nd),
                        "refs": r32(r32(nd + 0x14) + 4) if nd else None}
            if not nd:
                need += size
                need_blocks.append(block(size))
        fits = None
        if sp.get("capacity") is not None and need_blocks:
            fits = max(need_blocks) <= sp["largest_possible"] and sum(need_blocks) <= sp["total_free"]
        cands[name] = {"char": cid, "model_index": mi, "name": NAMES.get(e[0], hex(e[0])), "parts": parts,
                       "missing_bytes": need, "fit_test_blocks": sum(need_blocks),
                       "fits_without_eviction": fits}
    out["warriors"] = cands
    live = [h for h in (r32(0x006EBD38 + 8 * s) for s in range(60)) if h]
    out["humans"] = {"live": len(live), "without_model_instance_D8": sum(1 for h in live if not r32(h + 0xD8))}
    out["w4p"] = {"choose_result": r32(0x000E15F0), "choose_status": [r32(0x000E15C0 + 4 * i) for i in range(9)],
                  "pin": [r32(0x000E1C00 + 4 * i) for i in range(15)],
                  "config": [r32(0x000E1C40 + 4 * i) for i in range(3)]}
    return out


if __name__ == "__main__":
    sys.path.insert(0, os.path.join(os.getcwd(), "tools"))
    from pine import Pine
    print(json.dumps(survey_mem(Pine(int(sys.argv[1]))), indent=1, default=str))
```

## 4. Design (question 4)

### 4.1 When to request the load
| Option | What players see | Cost / risk |
|---|---|---|
| **(P3) Pin when the 3rd player joins, gate the 4th join (recommended, `PRELOAD_AT3` = 1)** | In the scripted runs player 4 presses Start ~150 polls (~5 s at ~30 polls/s, F-0146) after player 3 joined, so the model is normally resident and player 4 joins at once as SWAN | ~370 KB of the cache stays pinned for the rest of the level in 3-player sessions |
| (P4) Pin only on the 4th join (`PRELOAD_AT3` = 0) | First Start press: nothing happens (refused); the next press joins as SWAN (nav scripts repeat every 300 polls, ~10 s) | No cost without a 4th player; the first press looks ignored |
| (S) Spawn at once with a non-resident Warrior and let the human stream its model (1.5) | Player 4 joins at once with the right name but without body until the load ends; invisible for the level if it never fits | Not recommended |

Refusing a press is the game's own "nobody to join" path: `SPAWNPICK` returns 0, `UpdateJoin` skips MakePlayer, camera
and join event (0x0041A538 `beq s0,zero,0x0041A628`); VERIFIED static. A human player sees nothing happen and presses
again. **Recommendation: (P3)**, because the target is 4-player sessions and it hides the load time; (P4) is one data
word away.

### 4.2 Flow
- **3rd player joins** (count 2 at `UpdateJoin` entry, real press): after the companion is taken (`PX`) or the Warrior is
  spawned (`JS`), `ENSURE` runs: it pins the Warrior player 4 would get and pokes the streamer.
- **4th player presses Start, nobody to take over** (count 3): `GATE` -> `ENSURE`. A resident absent Warrior -> spawn
  (`CHOOSE` picks it). Still loading -> refuse this press. Waiting longer than `TIMEOUT_MS` (20,000 ms on the game clock)
  -> release the pin and spawn as before (clone). Nothing to load (all present/unconfigured, list full, levels 60-64,
  model does not fit) -> spawn as before.
- After the 4th spawn: if the spawned Warrior is not the pinned one, release the pin.
- **4th player takes a companion** -> release the pin. **The pinned Warrior's player leaves** (`LEAVEHOOK` -> `LV`) ->
  release. **Level teardown** clears every pin -> `CLRPIN` forgets ours. **Streamer finds our pin does not fit** ->
  `FITCHK` unpins it and marks that Warrior "no fit" for this level.

### 4.3 Routines (new code, group `[warriors-4p 4p spawn]`; all VERIFIED as assembled, untested at runtime)
| Routine | Address | Logic |
|---|---|---|
| `CLRPIN` | 0x000E1600 | replaces the teardown's `jal FUN_0018AB20`: PIN_ID = NOFIT = PIN_OWN = 0, then `j 0x0018AB20` (a0, ra unchanged) |
| `INLIST` | 0x000E1614 | leaf: is mi in the pin list of dict (32 x 8 bytes at +0xB4) |
| `PRESENT` | 0x000E1640 | is a live human (slots 0..59) of this HUD index present (`FUN_00229570` is a leaf using a0, a1, v0, v1 only: VERIFIED 0x00229570-0x00229618, so t3/t4 survive) |
| `RELEASE` | 0x000E1698 | if PIN_ID and PIN_OWN: `FUN_0018AD40(dict, PIN_ID, 1)`; PIN_ID = PIN_OWN = 0 |
| `POKE` | 0x000E16F0 | if POKE_EN, loader non-null, `FUN_00154A68(loader) == 0` (the scheduler's own guard) and dict: `FUN_001897A8(dict)` |
| `FITCHK` | 0x000E1758 | replaces the streamer's pin fit test call (0x001898C8): runs `FUN_001775D8`; if it fails and the tested entry is our pin: NOFIT = PIN_ID, `RELEASE`, still return 0 (the streamer returns right after, 0x001898D0, so the list change is safe) |
| `ENSURE` | 0x000E17C8 | below; returns 1 = resident Warrior available, 0 = pinned and loading, 2 = nothing to wait for |
| `GATE` | 0x000E19E8 | `ENSURE`; 1/2 -> go; 0 -> refuse unless clock - PIN_T0 >= TIMEOUT_MS (then `RELEASE`, go) |
| `JS` | 0x000E1A9C | replaces `SPAWNPICK`'s `jal SPAWN` (0x000E103C): count 3 -> `GATE` (refuse returns 0); `SPAWN(-1, 7)`; count 2 -> `ENSURE`; count 3 + spawned + `CHOOSE` result != PIN_ID -> `RELEASE` |
| `PX` | 0x000E1B38 | replaces `SPAWNPICK`'s `jal PickJoinCompanion` (0x000E1008): picker; if it found someone on a real press: count 2 -> `ENSURE`, count 3 -> `RELEASE` |
| `LV` | 0x000E1BAC | replaces `LEAVEHOOK`'s `jal DESPAWN` (0x000E1274): reads the leaving human's +0xD0 first, `DESPAWN`, then `RELEASE` if it equals PIN_ID |

`ENSURE` in detail:
1. Skip (result 2, code 6) without dictionary, in levels 60-64, or without player 1 (`FUN_00390268(GameMgr+0x228)`).
2. If PIN_ID is set but its mi is no longer in the pin list (released or cleared elsewhere): forget it.
3. `CHOOSE` (s0 = player 1). It picked a Warrior -> target = it, result 1 (pinning keeps it resident until the spawn).
   Else target = the first table candidate with `CHOOSE` status 3 (configured, valid mi, not resident) that `PRESENT`
   says is absent; none -> result 2 (code 4).
4. target == NOFIT -> result 1 if resident else 2 (code 7).
5. PIN_ID == target -> code 3. Otherwise `RELEASE` the old pin, note whether mi was already listed (then the level owns
   it: PIN_OWN = 0), `FUN_0018AD40(dict, target, 0)`; not listed afterwards (list full) -> result 1 if resident else 2
   (code 5); else PIN_ID/PIN_OWN/PIN_MI/PIN_T0 (game clock), code 2.
6. Result 0 -> `POKE`; if `FITCHK` unpinned it during the poke -> result 2 (code 7).

Registers: callee-saved registers are saved with `sq`/`lq` and ra with `sd`/`ld` like the game; frames are multiples of 16.
`CHOOSE` is reused unchanged (it needs s0 = player 1, returns s1, reloads f0 from s0+0x10). The game clock is
`*(*(0x0050B734) + 0x38)`: `FUN_00145A10` stores the 64-bit tick count at +0x30 divided by 0x48000 there
(0x00145D84-0x00145D98), i.e. milliseconds; the fixed-step mode adds 0x960000 ticks (33.3 ms) per update. VERIFIED.

### 4.4 Patch points
| Address | Group | Old word | New word | Note |
|---|---|---|---|---|
| 0x000E1008 | `[4p spawn]` | 0C08A9DC `jal 0x0022A770` | 0C0386CE `jal PX` | replaces `mod/m2/spawn.txt` line 5 |
| 0x000E103C | `[4p spawn]` | 0C038420 `jal 0x000E1080` | 0C0386A7 `jal JS` | replaces `mod/m2/spawn.txt` line 18 |
| 0x000E1274 | `[4p spawn leave]` | 0C038460 `jal 0x000E1180` | 0C0386EB `jal LV` | replaces `mod/m2/spawn_leave.txt` line 16 |
| 0x001898C8 | `[4p spawn]` | 0C05DD76 `jal 0x001775D8` (ELF) | 0C0385D6 `jal FITCHK` | streamer pin loop, delay slot `addiu a3,zero,1` kept |
| 0x00188AEC | `[4p spawn]` | 0C062AC8 `jal 0x0018AB20` (ELF) | 0C038580 `jal CLRPIN` | `FUN_00188AA8`, delay slot `move a0,s0` kept |
| 0x00189734 | `[4p spawn]` | 0C062AC8 `jal 0x0018AB20` (ELF) | 0C038580 `jal CLRPIN` | `FUN_00189718`, delay slot `move a0,s0` kept |

`LV` lives in the `[4p spawn]` range, so `[4p spawn leave]` needs `[4p spawn]` (already true today: `LEAVEHOOK` calls
`DESPAWN` at 0x000E1180). All delay slots of the replaced calls are unchanged.

### 4.5 Data words (`patch=0`, written once at startup; PINE can change the config words for tests)
| Address | Name | Meaning |
|---|---|---|
| 0x000E1C00 | PIN_ID | char id we pinned (0 = none) |
| 0x000E1C04 | PIN_OWN | 1 = we created the pin; only then `RELEASE` calls the game (a level script's pin of the same model is never released by us) |
| 0x000E1C08 | PIN_MI | its model index |
| 0x000E1C0C | PIN_T0 | game clock (ms) when pinned |
| 0x000E1C10 | EN_LAST | last `ENSURE` code: 1 resident, 2 new pin, 3 existing pin, 4 none left, 5 list full, 6 skipped, 7 does not fit |
| 0x000E1C14 | GT_LAST | last `GATE` code: 1 go (resident), 2 go (nothing to wait for), 3 refused, 4 go after timeout |
| 0x000E1C18 | GT_T | ms since the pin at the last refused/timed-out press |
| 0x000E1C1C | POKE_RES | last `FUN_001897A8` result |
| 0x000E1C20..30 | N_PIN, N_REFUSE, N_TIMEOUT, N_RELEASE, N_POKE | counters |
| 0x000E1C34 / 38 | NOFIT / N_NOFIT | Warrior whose model did not fit in this level (cleared at teardown) / count |
| 0x000E1C40 | TIMEOUT_MS | config, 20,000 |
| 0x000E1C44 | PRELOAD_AT3 | config, 1 = option (P3), 0 = option (P4) |
| 0x000E1C48 | POKE_EN | config, 1 = call the streamer after pinning, 0 = rely on the scheduler (test of H1) |

### 4.6 Lockstep
Every input is game RAM: char table, dictionary trees and pin list, object table, GameMgr, the loader queue and the
game clock. The code runs inside game code on the game thread: `UpdateJoin` on a synchronised Start press, the streamer,
and the level teardown. So all instances take the same decisions as long as their game state matches. Streaming
completion (when the three files arrive) depends on the emulated disc/IOP timing; HYPOTHESIS: identical on all
instances, consistent with q12 (F-0149: 15 min of Mission 13 with continuous world and character streaming, 841 hash
points, 0 mismatches) and F-0130. `POKE` only moves the request earlier, triggered by the same synchronised press. The
new words 0x000E1C00-0x000E1C4B lie inside the hashed game memory (from 0x000A0000, F-0125), so a disagreement shows as
a mismatch (test X5).

## 5. Checks (question 5)
- **Assembly:** 380 code words (0x000E1600-0x000E1BEF) and 6 hook words assembled with the scratch encoder of
  `m2_spawn_name.md`; every word disassembled back and compared with its source line: 0 mismatches. A mutation test
  (5 corrupted words: a register field, two offsets, a branch offset, a jump target) was flagged 5/5.
- **Game encodings:** 141 of 220 distinct code words occur verbatim in the ELF, e.g. `sq s3,64(sp)` 7FB30040
  (0x00101140), `lq s3,64(sp)` 7BB30040 (0x0010122C), `sd ra,0(sp)` FFBF0000 (0x0010156C), `ld ra,0(sp)` DFBF0000
  (0x00101648), `mult v0,s1,v1` 02231018 (0x0029638C), `lhu a1,274(v0)` 94450112 (0x001305CC), `sltiu v1,v1,5` 2C630005
  (0x002B583C), `sltu v0,v0,v1` 0043102B (0x00101768), `lh a0,2(s1)` 86240002 (0x0021A830), `jal 0x0018AD40` 0C062B50
  (0x0040CDC0), `jal 0x001897A8` 0C0625EA (0x0040FD7C), `jal 0x001775D8` 0C05DD76 (0x001898C8), `jal 0x00154A68`
  0C05529A (0x0040F970). The other 79 contain W4P addresses or labels; their formats match the words above and
  existing pnach words (`j`, `bltz`, `slti`).
- **`python -I tools/note_patches.py check`** (fragment = Appendix A saved as a file; scratch copies of the pnach with
  lines removed; `mod/w4p_m1.pnach` itself was not changed):

| Files | Result |
|---|---|
| (baseline) `mod/w4p_m1.pnach` | `checked 2257 addresses in 1 files: 6 problems` (the known `[4p hud A]` vs `[4p hud B1]` conflicts) |
| pnach + fragment | 9 problems: the same 6 plus `CONFLICT 000E1008`, `000E103C`, `000E1274` (the intended replacements of 4.4) |
| pnach without the 3 replaced lines + fragment | `checked 2658 addresses in 2 files: 6 problems` (the known 6) |
| same, also without `[4p hud A]` | **`checked 2658 addresses in 2 files: 0 problems`** |

The "was" words of the three game hooks matched the ELF (no WAS MISMATCH). The checker's cave test covers only
0x000F0000-0x000F0FFF; 0x000E1600-0x000E1C4B was checked separately: no ELF segment below 0x00100000, no pnach line, no
`mod/m2` source, no test/tool/fork reference (grep). Side observation (VERIFIED, `od -c`): `mod/w4p_m1.pnach` has
CR CR LF line ends, so the checker's line numbers for it are about twice the editor's.

## 6. Runtime test plan (question 6)
All SINGLE-PC, scripted input. Base: the Mission 13 setup of `docs/STATE.md` ("one instance ... players 3-4
joining"), groups including `warriors-4p 4p spawn;warriors-4p 4p spawn leave`.
1. **X0 - survey, fragment not applied:** `--probe extra_survey:survey_mem:8300/8450/8700` on one instance, repeat on a
   second; results identical. Gives pool size/free/largest, pin list, Swan's missing bytes (expect 374,767 if the
   static values hold), unreferenced bytes, humans without model.
2. **X1 - single instance, fragment applied, defaults:** probes at 8300, 8400 (after player 3 at ~8356), 8450, 8500,
   8600; `--peek 0x000E1C00:19`. Expect after player 3: EN_LAST 2, PIN_ID 5, N_PIN 1, N_POKE 1 (0 if the loader queue
   was busy at that moment), Swan's mi in the pin list, then its instance != 0 and Swan resident (note the poll).
   After player 4 (~8508): GT_LAST 1, `0x000E15F0` = 5, Swan's `CHOOSE` status 5, the handle at 0x000E1210 resolves
   to a human with +0xCC = 5, +0xD0 = 5, +0x37C = Swan's mi, +0xD8 != 0, +0x1B1 = 7. Screenshot of quarter 4 after
   ~8520: Swan's body, HUD name SWAN. Quarters 1-3 unchanged.
3. **X2 - option (P4):** as X1 with `--poke <early poll>:0x000E1C44:0`. Expect at the first press GT_LAST 3, N_REFUSE 1,
   no join; at the next press (300 polls later) join as Swan. Record polls and GT_T.
4. **X3 - H1 (scheduler alone):** as X1 with POKE_EN = 0 (`--poke`): time from the pin to resident with and without a
   fight (`--fight`). If it stays unserviced in the calm scene, H1 is confirmed and POKE stays on.
5. **X4 - fallback:** TIMEOUT_MS = 0 with (P4): the first press times out at once: expect GT_LAST 4, N_TIMEOUT 1,
   Swan's mi gone from the pin list, player 4 joins as the Rembrandt copy (old behaviour, F-0131).
6. **X5 - 4 instances in lockstep:** `m2_run4.py` as for q12, all groups, 900 s; expect 0 mismatches, 4 players / 4 views,
   player 4 = Swan on every instance (the data words are hashed).
7. **X6 - leave and re-join:** player 4 leaves (leave path) -> N_RELEASE 1, PIN_ID 0, Swan's mi gone from the list,
   handle no longer resolves. Re-join: Swan still cached -> joins at once (EN_LAST 1); if evicted -> one refusal, then
   Swan. Also: player 3 leaves and re-joins while player 4 stays (pin kept).
8. **X7 - memory over time:** 10+ min with four players moving and fighting; survey every ~1,000 polls: Sector Pool
   total/largest free, unreferenced bytes, N_NOFIT 0, `humans.without_model_instance_D8` not growing, no TLB miss;
   spot-check screenshots that enemies and cars still get their models.
9. **X8 - checkpoint/level change:** after a restart: PIN_ID 0, NOFIT 0, pin list without our entry (CLRPIN or the
   `INLIST` check); players 3-4 re-join normally and player 4 is again Swan.

## 7. Risks and open questions
| Risk | Label | Mitigation / check |
|---|---|---|
| Not enough Sector Pool memory in Mission 13: eviction of cached assets (more streaming, pop-in of enemies/cars) or "no fit" -> clone | HYPOTHESIS (size unknown) | X0 first; FITCHK + NOFIT fall back to the clone; X7 |
| H1: a pin alone is not serviced by the scheduler | HYPOTHESIS | POKE (default on); X3 measures |
| POKE bypasses the scheduler's world-versus-character choice once per join (world sectors may load slightly later) | HYPOTHESIS harmless | X1/X7 |
| A pin that never fits blocks all model streaming of the level (game behaviour) | VERIFIED code (0x001898D0) | FITCHK unpins ours; untested path (needs a full pool) |
| Streaming completion differs between instances | HYPOTHESIS (q12 evidence says no) | X5 |
| 3-player sessions keep ~370 KB pinned all level | VERIFIED by design | option (P4) is one data word |
| A level script pinned the same Warrior first | VERIFIED handled (PIN_OWN = 0, never released by us) | GATE waits on that pin like on ours |
| Levels 60-64: the pin core uses +0x112, humans +0x114 | VERIFIED code | skipped there (old clone behaviour) |
| Player 4 far from the camera: engine LOD may downgrade his model (all players) | HYPOTHESIS | the pin keeps the data cached while he plays; X7 |
| Checkpoint restarts not passing through `FUN_001607B8` | HYPOTHESIS | `ENSURE`'s `INLIST` check drops a vanished pin; X8 |
| Request-record exhaustion in `FUN_00187AA8` | HYPOTHESIS (engine limit) | one model = 3 requests |
| A refused press gives no feedback | VERIFIED (game path) | normally avoided by (P3) |
| WAD entry 10671 may not be the runtime dictionary | HYPOTHESIS | X0 reads the runtime entries |
| `FUN_00187098` tree insert not decoded | HYPOTHESIS | X1 residency timeline |
| 380 new words, nothing run | untested | X1-X8 before any claim |

Applying the fragment means editing `mod/m2/spawn.txt` and `mod/m2/spawn_leave.txt` and rebuilding the pnach with
`mod/make_pnach.py`; not done here.

## Appendix A: fragment (404 patch lines)
The 3 W4P-cave lines replace the lines at the same addresses; everything else is added. Comments give the assembly
source of each word.
```
// [warriors-4p 4p spawn] + [warriors-4p 4p spawn leave]: extra Warrior model for player 4 (m2_extra_model.md)
// hooks in existing W4P caves (replace the pnach line at the same address; old word in the comment)
patch=2,EE,000E1008,word,0C0386CE // [warriors-4p 4p spawn]: jal 0x000E1B38 PX (pnach had 0C08A9DC jal 0x0022A770 PickJoinCompanion); delay slot kept
patch=2,EE,000E103C,word,0C0386A7 // [warriors-4p 4p spawn]: jal 0x000E1A9C JS (pnach had 0C038420 jal 0x000E1080 SPAWN); delay slot kept
patch=2,EE,000E1274,word,0C0386EB // [warriors-4p 4p spawn leave]: jal 0x000E1BAC LV (pnach had 0C038460 jal 0x000E1180 DESPAWN); delay slot kept
// hooks in game code: streamer pin fit test -> FITCHK; level teardown (clear all pins) -> CLRPIN
patch=2,EE,001898C8,word,0C0385D6 // was 0C05DD76 jal 0x001775D8 (pin fit test) in FUN_001897A8 -> jal 0x000E1758 FITCHK; delay slot kept
patch=2,EE,00188AEC,word,0C038580 // was 0C062AC8 jal 0x0018AB20 (clear all pins) in FUN_00188AA8 -> jal 0x000E1600 CLRPIN; delay slot kept
patch=2,EE,00189734,word,0C038580 // was 0C062AC8 jal 0x0018AB20 (clear all pins) in FUN_00189718 -> jal 0x000E1600 CLRPIN; delay slot kept
patch=2,EE,000E1600,word,3C0A000E // CLRPIN: lui t2,0x000E  ; CLRPIN: called instead of FUN_0018AB20 (level teardown clears all pins)
patch=2,EE,000E1604,word,AD401C00 // sw zero,0x1C00(t2)  ; our pin is gone with the others
patch=2,EE,000E1608,word,AD401C34 // sw zero,0x1C34(t2)  ; next level: try again
patch=2,EE,000E160C,word,08062AC8 // j 0x0018AB20  ; tail jump: a0 and ra unchanged
patch=2,EE,000E1610,word,AD401C04 // sw zero,0x1C04(t2)
patch=2,EE,000E1614,word,248200B4 // INLIST: addiu v0,a0,0xB4  ; INLIST(dict, model index): pin list dict+0xB4, stride 8
patch=2,EE,000E1618,word,24080020 // addiu t0,zero,32
patch=2,EE,000E161C,word,8C430000 // lw v1,0(v0)
patch=2,EE,000E1620,word,10650005 // beq v1,a1,il_yes
patch=2,EE,000E1624,word,2508FFFF // addiu t0,t0,-1
patch=2,EE,000E1628,word,1500FFFC // bne t0,zero,il_loop
patch=2,EE,000E162C,word,24420008 // addiu v0,v0,8
patch=2,EE,000E1630,word,03E00008 // jr ra
patch=2,EE,000E1634,word,0000102D // move v0,zero
patch=2,EE,000E1638,word,03E00008 // jr ra
patch=2,EE,000E163C,word,24020001 // addiu v0,zero,1
patch=2,EE,000E1640,word,27BDFFF0 // PRESENT: addiu sp,sp,-16  ; PRESENT(HUD index); t3/t4 survive FUN_00229570 (leaf: a0,a1,v0,v1)
patch=2,EE,000E1644,word,FFBF0000 // sd ra,0(sp)
patch=2,EE,000E1648,word,0080602D // move t4,a0
patch=2,EE,000E164C,word,0000582D // move t3,zero
patch=2,EE,000E1650,word,000B10C0 // sll v0,t3,3
patch=2,EE,000E1654,word,3C03006F // lui v1,0x006F
patch=2,EE,000E1658,word,00431021 // addu v0,v0,v1
patch=2,EE,000E165C,word,8C44BD38 // lw a0,-0x42C8(v0)  ; *(0x006EBD38 + slot*8), 0 = free
patch=2,EE,000E1660,word,10800005 // beq a0,zero,pr_next
patch=2,EE,000E1664,word,00000000 // nop
patch=2,EE,000E1668,word,0C08A55C // jal 0x00229570  ; HUD index of that human
patch=2,EE,000E166C,word,00000000 // nop
patch=2,EE,000E1670,word,104C0006 // beq v0,t4,pr_out
patch=2,EE,000E1674,word,24020001 // addiu v0,zero,1
patch=2,EE,000E1678,word,256B0001 // addiu t3,t3,1
patch=2,EE,000E167C,word,2962003C // slti v0,t3,60
patch=2,EE,000E1680,word,1440FFF3 // bne v0,zero,pr_loop
patch=2,EE,000E1684,word,00000000 // nop
patch=2,EE,000E1688,word,0000102D // move v0,zero
patch=2,EE,000E168C,word,DFBF0000 // ld ra,0(sp)
patch=2,EE,000E1690,word,03E00008 // jr ra
patch=2,EE,000E1694,word,27BD0010 // addiu sp,sp,16
patch=2,EE,000E1698,word,27BDFFF0 // RELEASE: addiu sp,sp,-16  ; RELEASE(): no-op without a pin
patch=2,EE,000E169C,word,FFBF0000 // sd ra,0(sp)
patch=2,EE,000E16A0,word,3C0A000E // lui t2,0x000E
patch=2,EE,000E16A4,word,8D451C00 // lw a1,0x1C00(t2)
patch=2,EE,000E16A8,word,10A0000E // beq a1,zero,rl_out
patch=2,EE,000E16AC,word,8D431C04 // lw v1,0x1C04(t2)
patch=2,EE,000E16B0,word,1060000A // beq v1,zero,rl_clear  ; the level script pinned it first: never release someone else's pin
patch=2,EE,000E16B4,word,3C010051 // lui at,0x0051
patch=2,EE,000E16B8,word,8C24CD4C // lw a0,-0x32B4(at)  ; dict *(0x0050CD4C)
patch=2,EE,000E16BC,word,10800007 // beq a0,zero,rl_clear
patch=2,EE,000E16C0,word,00000000 // nop
patch=2,EE,000E16C4,word,0C062B50 // jal 0x0018AD40  ; SetCharacterModel core, release
patch=2,EE,000E16C8,word,24060001 // addiu a2,zero,1
patch=2,EE,000E16CC,word,3C0A000E // lui t2,0x000E
patch=2,EE,000E16D0,word,8D421C2C // lw v0,0x1C2C(t2)
patch=2,EE,000E16D4,word,24420001 // addiu v0,v0,1
patch=2,EE,000E16D8,word,AD421C2C // sw v0,0x1C2C(t2)
patch=2,EE,000E16DC,word,AD401C00 // sw zero,0x1C00(t2)
patch=2,EE,000E16E0,word,AD401C04 // sw zero,0x1C04(t2)
patch=2,EE,000E16E4,word,DFBF0000 // ld ra,0(sp)
patch=2,EE,000E16E8,word,03E00008 // jr ra
patch=2,EE,000E16EC,word,27BD0010 // addiu sp,sp,16
patch=2,EE,000E16F0,word,27BDFFF0 // POKE: addiu sp,sp,-16  ; POKE(): FUN_001897A8 services pinned models first
patch=2,EE,000E16F4,word,FFBF0000 // sd ra,0(sp)
patch=2,EE,000E16F8,word,3C0A000E // lui t2,0x000E
patch=2,EE,000E16FC,word,8D421C48 // lw v0,0x1C48(t2)
patch=2,EE,000E1700,word,10400012 // beq v0,zero,pk_out
patch=2,EE,000E1704,word,3C01005E // lui at,0x005E
patch=2,EE,000E1708,word,8C245340 // lw a0,0x5340(at)  ; loader *(0x005E5340)
patch=2,EE,000E170C,word,1080000F // beq a0,zero,pk_out
patch=2,EE,000E1710,word,00000000 // nop
patch=2,EE,000E1714,word,0C05529A // jal 0x00154A68  ; queued loader requests (leaf); FUN_0040F8A0 returns early if != 0
patch=2,EE,000E1718,word,00000000 // nop
patch=2,EE,000E171C,word,1440000B // bne v0,zero,pk_out
patch=2,EE,000E1720,word,3C010051 // lui at,0x0051
patch=2,EE,000E1724,word,8C24CD4C // lw a0,-0x32B4(at)  ; dict
patch=2,EE,000E1728,word,10800008 // beq a0,zero,pk_out
patch=2,EE,000E172C,word,00000000 // nop
patch=2,EE,000E1730,word,0C0625EA // jal 0x001897A8  ; model streamer
patch=2,EE,000E1734,word,00000000 // nop
patch=2,EE,000E1738,word,3C0A000E // lui t2,0x000E
patch=2,EE,000E173C,word,AD421C1C // sw v0,0x1C1C(t2)
patch=2,EE,000E1740,word,8D421C30 // lw v0,0x1C30(t2)
patch=2,EE,000E1744,word,24420001 // addiu v0,v0,1
patch=2,EE,000E1748,word,AD421C30 // sw v0,0x1C30(t2)
patch=2,EE,000E174C,word,DFBF0000 // ld ra,0(sp)
patch=2,EE,000E1750,word,03E00008 // jr ra
patch=2,EE,000E1754,word,27BD0010 // addiu sp,sp,16
patch=2,EE,000E1758,word,27BDFFE0 // FITCHK: addiu sp,sp,-32  ; FITCHK(dict, entry, 0, 1)
patch=2,EE,000E175C,word,FFBF0000 // sd ra,0(sp)
patch=2,EE,000E1760,word,7FB00010 // sq s0,16(sp)
patch=2,EE,000E1764,word,00A0802D // move s0,a1  ; entry being tested
patch=2,EE,000E1768,word,0C05DD76 // jal 0x001775D8  ; original fit test (evicts unreferenced assets if needed)
patch=2,EE,000E176C,word,00000000 // nop
patch=2,EE,000E1770,word,14400011 // bne v0,zero,fc_out  ; fits: unchanged
patch=2,EE,000E1774,word,3C0A000E // lui t2,0x000E
patch=2,EE,000E1778,word,8D451C00 // lw a1,0x1C00(t2)
patch=2,EE,000E177C,word,10A0000E // beq a1,zero,fc_out  ; we have no pin: unchanged
patch=2,EE,000E1780,word,8D431C08 // lw v1,0x1C08(t2)
patch=2,EE,000E1784,word,3C010051 // lui at,0x0051
patch=2,EE,000E1788,word,8C24CD4C // lw a0,-0x32B4(at)  ; dict
patch=2,EE,000E178C,word,8C840088 // lw a0,0x88(a0)  ; dictionary entries
patch=2,EE,000E1790,word,00031940 // sll v1,v1,5
patch=2,EE,000E1794,word,00831821 // addu v1,a0,v1  ; our entry (FUN_001780D8)
patch=2,EE,000E1798,word,14700007 // bne v1,s0,fc_out  ; a level pin failed, not ours: unchanged
patch=2,EE,000E179C,word,00000000 // nop
patch=2,EE,000E17A0,word,AD451C34 // sw a1,0x1C34(t2)  ; this Warrior does not fit in this level: do not try again
patch=2,EE,000E17A4,word,8D421C38 // lw v0,0x1C38(t2)
patch=2,EE,000E17A8,word,24420001 // addiu v0,v0,1
patch=2,EE,000E17AC,word,0C0385A6 // jal RELEASE  ; unpin (the streamer returns right after this call, list change is safe)
patch=2,EE,000E17B0,word,AD421C38 // sw v0,0x1C38(t2)
patch=2,EE,000E17B4,word,0000102D // move v0,zero  ; report "does not fit" as the original did
patch=2,EE,000E17B8,word,DFBF0000 // ld ra,0(sp)
patch=2,EE,000E17BC,word,7BB00010 // lq s0,16(sp)
patch=2,EE,000E17C0,word,03E00008 // jr ra
patch=2,EE,000E17C4,word,27BD0020 // addiu sp,sp,32
patch=2,EE,000E17C8,word,27BDFFA0 // ENSURE: addiu sp,sp,-96  ; ENSURE(): frame 96, s0-s3 saved, 80/84/88 locals
patch=2,EE,000E17CC,word,FFBF0000 // sd ra,0(sp)
patch=2,EE,000E17D0,word,7FB00010 // sq s0,16(sp)
patch=2,EE,000E17D4,word,7FB10020 // sq s1,32(sp)
patch=2,EE,000E17D8,word,7FB20030 // sq s2,48(sp)
patch=2,EE,000E17DC,word,7FB30040 // sq s3,64(sp)
patch=2,EE,000E17E0,word,24130002 // addiu s3,zero,2  ; result 2 unless shown otherwise
patch=2,EE,000E17E4,word,24090006 // addiu t1,zero,6  ; code 6: skipped (no dictionary, levels 60-64, no player 1)
patch=2,EE,000E17E8,word,3C010051 // lui at,0x0051
patch=2,EE,000E17EC,word,8C32CD4C // lw s2,-0x32B4(at)  ; s2 = dict *(0x0050CD4C)
patch=2,EE,000E17F0,word,12400073 // beq s2,zero,en_code
patch=2,EE,000E17F4,word,8C22489C // lw v0,0x489C(at)  ; GameMgr *(0x0051489C)
patch=2,EE,000E17F8,word,944356DC // lhu v1,0x56DC(v0)  ; level slot
patch=2,EE,000E17FC,word,000321C0 // sll a0,v1,7
patch=2,EE,000E1800,word,00031880 // sll v1,v1,2
patch=2,EE,000E1804,word,00831821 // addu v1,a0,v1
patch=2,EE,000E1808,word,00431821 // addu v1,v0,v1
patch=2,EE,000E180C,word,8C6314D8 // lw v1,0x14D8(v1)  ; level number
patch=2,EE,000E1810,word,2463FFC4 // addiu v1,v1,-60
patch=2,EE,000E1814,word,2C630005 // sltiu v1,v1,5
patch=2,EE,000E1818,word,14600069 // bne v1,zero,en_code  ; levels 60-64: humans read +0x114, the pin core reads +0x112
patch=2,EE,000E181C,word,00000000 // nop
patch=2,EE,000E1820,word,0C0E409A // jal 0x00390268  ; player 1 human from GameMgr+0x228
patch=2,EE,000E1824,word,24440228 // addiu a0,v0,0x228
patch=2,EE,000E1828,word,0040802D // move s0,v0  ; s0 = player 1 (CHOOSE input)
patch=2,EE,000E182C,word,12000064 // beq s0,zero,en_code
patch=2,EE,000E1830,word,24090006 // addiu t1,zero,6  ; (code 6 again: the call may have changed t1)
patch=2,EE,000E1834,word,3C0A000E // lui t2,0x000E
patch=2,EE,000E1838,word,8D421C00 // lw v0,0x1C00(t2)
patch=2,EE,000E183C,word,10400007 // beq v0,zero,en_choose
patch=2,EE,000E1840,word,0240202D // move a0,s2
patch=2,EE,000E1844,word,0C038585 // jal INLIST  ; is our pin still in the list?
patch=2,EE,000E1848,word,8D451C08 // lw a1,0x1C08(t2)
patch=2,EE,000E184C,word,14400003 // bne v0,zero,en_choose
patch=2,EE,000E1850,word,3C0A000E // lui t2,0x000E
patch=2,EE,000E1854,word,AD401C00 // sw zero,0x1C00(t2)  ; removed behind our back (e.g. a script released it): forget it
patch=2,EE,000E1858,word,AD401C04 // sw zero,0x1C04(t2)
patch=2,EE,000E185C,word,0C038500 // jal 0x000E1400  ; CHOOSE: s1 = chosen char or player 1's; statuses at 0x000E15C0
patch=2,EE,000E1860,word,00000000 // nop
patch=2,EE,000E1864,word,8E0200D0 // lw v0,0xD0(s0)
patch=2,EE,000E1868,word,16220015 // bne s1,v0,en_target  ; a resident, absent Warrior exists
patch=2,EE,000E186C,word,24130001 // addiu s3,zero,1
patch=2,EE,000E1870,word,24130000 // addiu s3,zero,0  ; otherwise: the first not-resident, absent candidate (table order)
patch=2,EE,000E1874,word,3C11000E // lui s1,0x000E
patch=2,EE,000E1878,word,26311580 // addiu s1,s1,0x1580
patch=2,EE,000E187C,word,86220000 // lh v0,0(s1)  ; candidate char id, 0 = end
patch=2,EE,000E1880,word,1040000C // beq v0,zero,en_none
patch=2,EE,000E1884,word,8E230040 // lw v1,0x40(s1)  ; its CHOOSE status
patch=2,EE,000E1888,word,2463FFFD // addiu v1,v1,-3
patch=2,EE,000E188C,word,14600005 // bne v1,zero,en_p2next  ; only status 3: configured, valid model index, not resident
patch=2,EE,000E1890,word,00000000 // nop
patch=2,EE,000E1894,word,0C038590 // jal PRESENT
patch=2,EE,000E1898,word,86240002 // lh a0,2(s1)  ; HUD index
patch=2,EE,000E189C,word,10400003 // beq v0,zero,en_p2hit
patch=2,EE,000E18A0,word,00000000 // nop
patch=2,EE,000E18A4,word,1000FFF5 // beq zero,zero,en_p2
patch=2,EE,000E18A8,word,26310004 // addiu s1,s1,4
patch=2,EE,000E18AC,word,10000004 // beq zero,zero,en_target
patch=2,EE,000E18B0,word,86310000 // lh s1,0(s1)  ; target char id
patch=2,EE,000E18B4,word,24130002 // addiu s3,zero,2
patch=2,EE,000E18B8,word,10000041 // beq zero,zero,en_code
patch=2,EE,000E18BC,word,24090004 // addiu t1,zero,4  ; code 4: no Warrior left to load
patch=2,EE,000E18C0,word,3C0A000E // lui t2,0x000E  ; s1 = target, s3 = 1 (resident) or 0 (needs a load)
patch=2,EE,000E18C4,word,8D421C34 // lw v0,0x1C34(t2)
patch=2,EE,000E18C8,word,14510005 // bne v0,s1,en_fitok
patch=2,EE,000E18CC,word,24090007 // addiu t1,zero,7  ; code 7: this Warrior did not fit in this level
patch=2,EE,000E18D0,word,1660003B // bne s3,zero,en_code  ; resident now anyway: CHOOSE picks it
patch=2,EE,000E18D4,word,00000000 // nop
patch=2,EE,000E18D8,word,10000039 // beq zero,zero,en_code
patch=2,EE,000E18DC,word,24130002 // addiu s3,zero,2
patch=2,EE,000E18E0,word,8D421C00 // lw v0,0x1C00(t2)
patch=2,EE,000E18E4,word,1051002B // beq v0,s1,en_poke  ; already pinned for this target
patch=2,EE,000E18E8,word,24090003 // addiu t1,zero,3  ; code 3: existing pin
patch=2,EE,000E18EC,word,0C0385A6 // jal RELEASE  ; drop a pin for another Warrior (no-op without one)
patch=2,EE,000E18F0,word,00000000 // nop
patch=2,EE,000E18F4,word,240301AC // addiu v1,zero,0x1AC
patch=2,EE,000E18F8,word,02231018 // mult v0,s1,v1
patch=2,EE,000E18FC,word,3C030068 // lui v1,0x0068
patch=2,EE,000E1900,word,24634620 // addiu v1,v1,0x4620
patch=2,EE,000E1904,word,00431021 // addu v0,v0,v1  ; char table entry 0x00684620 + id*0x1AC
patch=2,EE,000E1908,word,94450112 // lhu a1,0x112(v0)  ; model index as FUN_0018AD40 reads it (+0x112)
patch=2,EE,000E190C,word,AFA50050 // sw a1,80(sp)
patch=2,EE,000E1910,word,0C038585 // jal INLIST
patch=2,EE,000E1914,word,0240202D // move a0,s2
patch=2,EE,000E1918,word,AFA20054 // sw v0,84(sp)  ; 1 = pinned before us (by the level)
patch=2,EE,000E191C,word,0240202D // move a0,s2
patch=2,EE,000E1920,word,0220282D // move a1,s1
patch=2,EE,000E1924,word,0C062B50 // jal 0x0018AD40  ; SetCharacterModel(target, 0) core: pin (instance now if resident)
patch=2,EE,000E1928,word,0000302D // move a2,zero
patch=2,EE,000E192C,word,0240202D // move a0,s2
patch=2,EE,000E1930,word,0C038585 // jal INLIST
patch=2,EE,000E1934,word,8FA50050 // lw a1,80(sp)
patch=2,EE,000E1938,word,14400005 // bne v0,zero,en_pinned
patch=2,EE,000E193C,word,24090005 // addiu t1,zero,5  ; code 5: pin list full
patch=2,EE,000E1940,word,1660001F // bne s3,zero,en_code  ; resident anyway: CHOOSE will pick it
patch=2,EE,000E1944,word,00000000 // nop
patch=2,EE,000E1948,word,1000001D // beq zero,zero,en_code
patch=2,EE,000E194C,word,24130002 // addiu s3,zero,2  ; cannot load: let the join fall back
patch=2,EE,000E1950,word,3C0A000E // lui t2,0x000E
patch=2,EE,000E1954,word,AD511C00 // sw s1,0x1C00(t2)
patch=2,EE,000E1958,word,8FA20054 // lw v0,84(sp)
patch=2,EE,000E195C,word,2C420001 // sltiu v0,v0,1
patch=2,EE,000E1960,word,AD421C04 // sw v0,0x1C04(t2)  ; we own it only if it was not pinned before
patch=2,EE,000E1964,word,8FA20050 // lw v0,80(sp)
patch=2,EE,000E1968,word,AD421C08 // sw v0,0x1C08(t2)
patch=2,EE,000E196C,word,3C010051 // lui at,0x0051
patch=2,EE,000E1970,word,8C22B734 // lw v0,-0x48CC(at)  ; timer object *(0x0050B734)
patch=2,EE,000E1974,word,10400002 // beq v0,zero,en_t0
patch=2,EE,000E1978,word,0000182D // move v1,zero
patch=2,EE,000E197C,word,8C430038 // lw v1,0x38(v0)  ; game clock (ms)
patch=2,EE,000E1980,word,AD431C0C // sw v1,0x1C0C(t2)
patch=2,EE,000E1984,word,8D421C20 // lw v0,0x1C20(t2)
patch=2,EE,000E1988,word,24420001 // addiu v0,v0,1
patch=2,EE,000E198C,word,AD421C20 // sw v0,0x1C20(t2)
patch=2,EE,000E1990,word,24090002 // addiu t1,zero,2  ; code 2: new pin
patch=2,EE,000E1994,word,1660000A // bne s3,zero,en_code  ; resident: nothing to stream
patch=2,EE,000E1998,word,00000000 // nop
patch=2,EE,000E199C,word,0C0385BC // jal POKE
patch=2,EE,000E19A0,word,AFA90058 // sw t1,88(sp)
patch=2,EE,000E19A4,word,8FA90058 // lw t1,88(sp)
patch=2,EE,000E19A8,word,3C0A000E // lui t2,0x000E
patch=2,EE,000E19AC,word,8D421C00 // lw v0,0x1C00(t2)
patch=2,EE,000E19B0,word,14400003 // bne v0,zero,en_code  ; still pinned: waiting for the load
patch=2,EE,000E19B4,word,00000000 // nop
patch=2,EE,000E19B8,word,24130002 // addiu s3,zero,2  ; FITCHK unpinned it during the poke: does not fit
patch=2,EE,000E19BC,word,24090007 // addiu t1,zero,7
patch=2,EE,000E19C0,word,3C0A000E // lui t2,0x000E
patch=2,EE,000E19C4,word,AD491C10 // sw t1,0x1C10(t2)
patch=2,EE,000E19C8,word,0260102D // move v0,s3
patch=2,EE,000E19CC,word,DFBF0000 // ld ra,0(sp)
patch=2,EE,000E19D0,word,7BB00010 // lq s0,16(sp)
patch=2,EE,000E19D4,word,7BB10020 // lq s1,32(sp)
patch=2,EE,000E19D8,word,7BB20030 // lq s2,48(sp)
patch=2,EE,000E19DC,word,7BB30040 // lq s3,64(sp)
patch=2,EE,000E19E0,word,03E00008 // jr ra
patch=2,EE,000E19E4,word,27BD0060 // addiu sp,sp,96
patch=2,EE,000E19E8,word,27BDFFF0 // GATE: addiu sp,sp,-16  ; GATE()
patch=2,EE,000E19EC,word,FFBF0000 // sd ra,0(sp)
patch=2,EE,000E19F0,word,0C0385F2 // jal ENSURE
patch=2,EE,000E19F4,word,00000000 // nop
patch=2,EE,000E19F8,word,3C0A000E // lui t2,0x000E
patch=2,EE,000E19FC,word,10400008 // beq v0,zero,gt_wait
patch=2,EE,000E1A00,word,24090001 // addiu t1,zero,1  ; code 1: go, a Warrior is resident
patch=2,EE,000E1A04,word,24030001 // addiu v1,zero,1
patch=2,EE,000E1A08,word,10430002 // beq v0,v1,gt_go
patch=2,EE,000E1A0C,word,00000000 // nop
patch=2,EE,000E1A10,word,24090002 // addiu t1,zero,2  ; code 2: go, nothing to wait for (clone)
patch=2,EE,000E1A14,word,AD491C14 // sw t1,0x1C14(t2)
patch=2,EE,000E1A18,word,1000001D // beq zero,zero,gt_out
patch=2,EE,000E1A1C,word,24020001 // addiu v0,zero,1
patch=2,EE,000E1A20,word,3C010051 // lui at,0x0051
patch=2,EE,000E1A24,word,8C22B734 // lw v0,-0x48CC(at)  ; timer object
patch=2,EE,000E1A28,word,10400009 // beq v0,zero,gt_tmo  ; no clock: do not wait
patch=2,EE,000E1A2C,word,00000000 // nop
patch=2,EE,000E1A30,word,8C420038 // lw v0,0x38(v0)
patch=2,EE,000E1A34,word,8D431C0C // lw v1,0x1C0C(t2)
patch=2,EE,000E1A38,word,00431023 // subu v0,v0,v1  ; ms since the pin
patch=2,EE,000E1A3C,word,AD421C18 // sw v0,0x1C18(t2)
patch=2,EE,000E1A40,word,8D431C40 // lw v1,0x1C40(t2)
patch=2,EE,000E1A44,word,0043102B // sltu v0,v0,v1
patch=2,EE,000E1A48,word,1440000B // bne v0,zero,gt_refuse
patch=2,EE,000E1A4C,word,00000000 // nop
patch=2,EE,000E1A50,word,0C0385A6 // jal RELEASE  ; timed out: stop waiting; CHOOSE falls back to the clone
patch=2,EE,000E1A54,word,00000000 // nop
patch=2,EE,000E1A58,word,3C0A000E // lui t2,0x000E
patch=2,EE,000E1A5C,word,8D421C28 // lw v0,0x1C28(t2)
patch=2,EE,000E1A60,word,24420001 // addiu v0,v0,1
patch=2,EE,000E1A64,word,AD421C28 // sw v0,0x1C28(t2)
patch=2,EE,000E1A68,word,24090004 // addiu t1,zero,4  ; code 4: go after timeout (clone)
patch=2,EE,000E1A6C,word,AD491C14 // sw t1,0x1C14(t2)
patch=2,EE,000E1A70,word,10000007 // beq zero,zero,gt_out
patch=2,EE,000E1A74,word,24020001 // addiu v0,zero,1
patch=2,EE,000E1A78,word,8D421C24 // lw v0,0x1C24(t2)
patch=2,EE,000E1A7C,word,24420001 // addiu v0,v0,1
patch=2,EE,000E1A80,word,AD421C24 // sw v0,0x1C24(t2)
patch=2,EE,000E1A84,word,24090003 // addiu t1,zero,3  ; code 3: refused, model still streaming
patch=2,EE,000E1A88,word,AD491C14 // sw t1,0x1C14(t2)
patch=2,EE,000E1A8C,word,0000102D // move v0,zero
patch=2,EE,000E1A90,word,DFBF0000 // ld ra,0(sp)
patch=2,EE,000E1A94,word,03E00008 // jr ra
patch=2,EE,000E1A98,word,27BD0010 // addiu sp,sp,16
patch=2,EE,000E1A9C,word,27BDFFD0 // JS: addiu sp,sp,-48  ; JS(char, prio)
patch=2,EE,000E1AA0,word,FFBF0000 // sd ra,0(sp)
patch=2,EE,000E1AA4,word,7FB00010 // sq s0,16(sp)
patch=2,EE,000E1AA8,word,AFA40020 // sw a0,32(sp)
patch=2,EE,000E1AAC,word,AFA50024 // sw a1,36(sp)
patch=2,EE,000E1AB0,word,24020003 // addiu v0,zero,3
patch=2,EE,000E1AB4,word,16620005 // bne s3,v0,js_spawn  ; the gate is only for the 4th player
patch=2,EE,000E1AB8,word,00000000 // nop
patch=2,EE,000E1ABC,word,0C03867A // jal GATE
patch=2,EE,000E1AC0,word,00000000 // nop
patch=2,EE,000E1AC4,word,10400017 // beq v0,zero,js_out  ; refuse this press: v0 = 0 = nobody to join
patch=2,EE,000E1AC8,word,0000802D // move s0,zero
patch=2,EE,000E1ACC,word,8FA40020 // lw a0,32(sp)
patch=2,EE,000E1AD0,word,0C038420 // jal 0x000E1080  ; SPAWN(-1, 7) as before (CHOOSE inside)
patch=2,EE,000E1AD4,word,8FA50024 // lw a1,36(sp)
patch=2,EE,000E1AD8,word,0040802D // move s0,v0
patch=2,EE,000E1ADC,word,24020002 // addiu v0,zero,2
patch=2,EE,000E1AE0,word,16620008 // bne s3,v0,js_four
patch=2,EE,000E1AE4,word,3C0A000E // lui t2,0x000E
patch=2,EE,000E1AE8,word,8D421C44 // lw v0,0x1C44(t2)
patch=2,EE,000E1AEC,word,1040000D // beq v0,zero,js_out
patch=2,EE,000E1AF0,word,00000000 // nop
patch=2,EE,000E1AF4,word,0C0385F2 // jal ENSURE  ; 3rd player was spawned: start player 4's Warrior now
patch=2,EE,000E1AF8,word,00000000 // nop
patch=2,EE,000E1AFC,word,10000009 // beq zero,zero,js_out
patch=2,EE,000E1B00,word,00000000 // nop
patch=2,EE,000E1B04,word,12000007 // beq s0,zero,js_out  ; spawn failed: keep the pin for the next press
patch=2,EE,000E1B08,word,00000000 // nop
patch=2,EE,000E1B0C,word,8D4215F0 // lw v0,0x15F0(t2)  ; char id CHOOSE picked for this spawn
patch=2,EE,000E1B10,word,8D431C00 // lw v1,0x1C00(t2)
patch=2,EE,000E1B14,word,10430003 // beq v0,v1,js_out  ; it is the pinned Warrior: keep the pin until that player leaves
patch=2,EE,000E1B18,word,00000000 // nop
patch=2,EE,000E1B1C,word,0C0385A6 // jal RELEASE  ; pin not used (other Warrior or clone)
patch=2,EE,000E1B20,word,00000000 // nop
patch=2,EE,000E1B24,word,0200102D // move v0,s0
patch=2,EE,000E1B28,word,DFBF0000 // ld ra,0(sp)
patch=2,EE,000E1B2C,word,7BB00010 // lq s0,16(sp)
patch=2,EE,000E1B30,word,03E00008 // jr ra
patch=2,EE,000E1B34,word,27BD0030 // addiu sp,sp,48
patch=2,EE,000E1B38,word,27BDFFE0 // PX: addiu sp,sp,-32  ; PX(gang, 0)
patch=2,EE,000E1B3C,word,FFBF0000 // sd ra,0(sp)
patch=2,EE,000E1B40,word,7FB00010 // sq s0,16(sp)
patch=2,EE,000E1B44,word,0C08A9DC // jal 0x0022A770  ; PickJoinCompanion (original call)
patch=2,EE,000E1B48,word,00000000 // nop
patch=2,EE,000E1B4C,word,0040802D // move s0,v0
patch=2,EE,000E1B50,word,12000011 // beq s0,zero,px_out  ; nobody: SPAWNPICK goes on to JS
patch=2,EE,000E1B54,word,00000000 // nop
patch=2,EE,000E1B58,word,0640000F // bltz s2,px_out  ; level start / script join: unchanged
patch=2,EE,000E1B5C,word,24030002 // addiu v1,zero,2
patch=2,EE,000E1B60,word,16630008 // bne s3,v1,px_four
patch=2,EE,000E1B64,word,3C0A000E // lui t2,0x000E
patch=2,EE,000E1B68,word,8D421C44 // lw v0,0x1C44(t2)
patch=2,EE,000E1B6C,word,1040000A // beq v0,zero,px_out
patch=2,EE,000E1B70,word,00000000 // nop
patch=2,EE,000E1B74,word,0C0385F2 // jal ENSURE  ; 3rd player took a companion: start player 4's Warrior now
patch=2,EE,000E1B78,word,00000000 // nop
patch=2,EE,000E1B7C,word,10000006 // beq zero,zero,px_out
patch=2,EE,000E1B80,word,00000000 // nop
patch=2,EE,000E1B84,word,24030003 // addiu v1,zero,3
patch=2,EE,000E1B88,word,16630003 // bne s3,v1,px_out
patch=2,EE,000E1B8C,word,00000000 // nop
patch=2,EE,000E1B90,word,0C0385A6 // jal RELEASE  ; 4th player took a companion: pin not needed
patch=2,EE,000E1B94,word,00000000 // nop
patch=2,EE,000E1B98,word,0200102D // move v0,s0
patch=2,EE,000E1B9C,word,DFBF0000 // ld ra,0(sp)
patch=2,EE,000E1BA0,word,7BB00010 // lq s0,16(sp)
patch=2,EE,000E1BA4,word,03E00008 // jr ra
patch=2,EE,000E1BA8,word,27BD0020 // addiu sp,sp,32
patch=2,EE,000E1BAC,word,27BDFFE0 // LV: addiu sp,sp,-32  ; LV(handle)
patch=2,EE,000E1BB0,word,FFBF0000 // sd ra,0(sp)
patch=2,EE,000E1BB4,word,7FB10010 // sq s1,16(sp)
patch=2,EE,000E1BB8,word,0C038460 // jal 0x000E1180  ; DESPAWN(handle) (original call)
patch=2,EE,000E1BBC,word,8E1100D0 // lw s1,0xD0(s0)  ; char id of the leaving Warrior, read before it is deleted
patch=2,EE,000E1BC0,word,3C0A000E // lui t2,0x000E
patch=2,EE,000E1BC4,word,8D421C00 // lw v0,0x1C00(t2)
patch=2,EE,000E1BC8,word,10400005 // beq v0,zero,lv_out
patch=2,EE,000E1BCC,word,00000000 // nop
patch=2,EE,000E1BD0,word,14510003 // bne v0,s1,lv_out  ; another Warrior left: keep the pin
patch=2,EE,000E1BD4,word,00000000 // nop
patch=2,EE,000E1BD8,word,0C0385A6 // jal RELEASE  ; the pinned Warrior's player left: unpin (data stays cached)
patch=2,EE,000E1BDC,word,00000000 // nop
patch=2,EE,000E1BE0,word,DFBF0000 // ld ra,0(sp)
patch=2,EE,000E1BE4,word,7BB10010 // lq s1,16(sp)
patch=2,EE,000E1BE8,word,03E00008 // jr ra
patch=2,EE,000E1BEC,word,27BD0020 // addiu sp,sp,32
patch=0,EE,000E1C00,word,00000000 // PIN_ID: char id we pinned (0 = none) (startup only)
patch=0,EE,000E1C04,word,00000000 // PIN_OWN: 1 = we created the pin (only then we release it) (startup only)
patch=0,EE,000E1C08,word,00000000 // PIN_MI: model index of the pin (diagnostic) (startup only)
patch=0,EE,000E1C0C,word,00000000 // PIN_T0: game clock (ms) when pinned (startup only)
patch=0,EE,000E1C10,word,00000000 // EN_LAST: last ENSURE code (1 resident,2 new pin,3 existing pin,4 none left,5 list full,6 skipped,7 no fit) (startup only)
patch=0,EE,000E1C14,word,00000000 // GT_LAST: last GATE code (1 go resident,2 go nothing to wait,3 refused,4 go after timeout) (startup only)
patch=0,EE,000E1C18,word,00000000 // GT_T: ms since the pin at the last refused/timed-out GATE (startup only)
patch=0,EE,000E1C1C,word,00000000 // POKE_RES: last FUN_001897A8 result (startup only)
patch=0,EE,000E1C20,word,00000000 // N_PIN: pins made (startup only)
patch=0,EE,000E1C24,word,00000000 // N_REFUSE: join presses refused (startup only)
patch=0,EE,000E1C28,word,00000000 // N_TIMEOUT: timeouts (startup only)
patch=0,EE,000E1C2C,word,00000000 // N_RELEASE: pins released (startup only)
patch=0,EE,000E1C30,word,00000000 // N_POKE: streamer calls (startup only)
patch=0,EE,000E1C34,word,00000000 // NOFIT: char id whose model did not fit in this level (cleared at teardown) (startup only)
patch=0,EE,000E1C38,word,00000000 // N_NOFIT: fit failures of our pin (startup only)
patch=0,EE,000E1C40,word,00004E20 // TIMEOUT_MS: config: give up waiting after this many ms (then clone) (startup only)
patch=0,EE,000E1C44,word,00000001 // PRELOAD_AT3: config: 1 = start loading when the 3rd player joins, 0 = only on the 4th join (startup only)
patch=0,EE,000E1C48,word,00000001 // POKE_EN: config: 1 = call the streamer after pinning, 0 = wait for the game's scheduler (startup only)
```

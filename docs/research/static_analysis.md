# Static and runtime analysis notes: The Warriors SLUS-21215 v1.03

All names are OUR labels (the ELF is stripped). Addresses are EE virtual addresses in this build. Labels refer to
findings in `docs/FINDINGS.md`. Tools: Ghidra 12.1.4 + ghidra-emotionengine-reloaded v2.1.38 (project in
`local/ghidra/`), full decompile in `local/analysis/all/` (not committed), Lua tools in `tools/`.

## 1. Program layout
| Item | Value | Ref |
|---|---|---|
| Load segment | 0x00100000-0x00715B5C (.text 0x100000, .data 0x50A880, .rodata 0x546480, .bss 0x597200) | F-0003 |
| Entry / main | 0x00100008 / 0x001446D0 | F-0045 |
| Build | "Release", Sep 25 2005 20:21:44, CL 104242 | F-0045 |
| Scripting | Lua 4.0.1 (parser present, `dostring`/`dofile` present); 964 C bindings registered at 0x0037D420 | F-0005, F-0013, F-0057 |
| Data | `WARRIORS.DIR`/`.WAD` hashed archive, 10,701 entries, 467 Lua chunks | F-0006 |
| Modules (by assert paths) | Camera 0x11D000-0x13B000; Device/Pad 0x144000-0x14A000; GameModes 0x155000-0x161000; GUI 0x1A1000-0x217000; Human 0x21B000-0x274000; Lua 0x323000-0x386000; World 0x40C000-0x412000; Warriors/GameMgr 0x417000-0x424000 | F-0004 |

## 2. Main loop and time
- Game-mode stack (0x005E66A0, top 0x0050C784); in-game mode 0x005E56B8 update 0x00158728; loading mode 0x005E5D90.
- Frame counter 0x0050C654, bumped by `FrameStats` 0x001569C0 (7 call sites). F-0046.
- GameClock (ptr 0x0050B734): cycle-counter based; real-time mode in gameplay (dt clamped to 40 ms); fixed-step
  mode flag +0x54. Lua scheduler fires on GameClock time. F-0047, F-0048.
- Consequence (E3b): the game must not be made to wait inside itself; emulated time keeps running.

## 3. Players
| Structure | Location | Notes | Ref |
|---|---|---|---|
| GameMgr | ptr 0x0051489C (heap) | +0x224 s16 player count; +0x228 handle[2]; +0x230 frame tick; +0x234.. sound obj; +0x14C level state; +0x14D4 level table (0x84-byte entries); +0x56DC current level index; +0x56E8 join allowed; +0x5740 per-player 0x30 records | F-0020, F-0021, F-0060 |
| Handles | table 0x006EBD38 | (index<<16)\|generation | F-0022 |
| Human | 0x6D0-byte objects, static pool near 0x00640C80 | +0x10 position; +0x92 index; +0x1B0 player index (-1 AI); +0x380 HUD slot | F-0023, F-0053 |
| Controller record | 0x00660F50 + idx x 0x2C | +0x19 pad index | F-0053 |
| Brain/AI record | 0x006D53F0 + idx x 0x2F0 | | F-0053 |
| `MakePlayer` / `ReleasePlayer` | 0x00229C40 / 0x0022A2A8 | pad search over 8 slots; 2 HUD slots | F-0056 |
| `GameMgr::AddPlayer` / remove | 0x00419B10 / 0x00419C68 | limit 2 | F-0060 |
| Join logic | 0x0041A430, 0x0041A460 | creates per-player cameras (0x0011EAF0) when count > 1 | F-0021 |

## 4. Input
| Item | Location | Ref |
|---|---|---|
| Pad state structs (8 x 0x50) | 0x005DD810 | F-0031 |
| Port buffers (8 x 0x140) | 0x005DE3C0 | F-0051 |
| `PadInit` (opens 2 ports) | 0x00149520 | F-0054 |
| `PadUpdateAll` (polls pads 0 and 4) | 0x001454A8 | F-0055 |
| libpad read call (injection point) | 0x001498E0 -> 0x00149770 | F-0051 |
| Button codes | L2 0x1, R2 0x2, L1 0x4, R1 0x8, tri 0x10, circle 0x20, cross 0x40, square 0x80, Select 0x100, Up 0x1000, Right 0x2000, Down 0x4000, Left 0x8000 | F-0031 |

## 5. Camera, viewports, HUD
| Item | Location | Ref |
|---|---|---|
| Per-viewport camera arrays (2 entries each) | 0x005D9148 active, 0x005D9150 render list, 0x005D9158/60/68 per-type | F-0026 |
| `LayoutViewports` (merge/split, 1x2, 2x1, 2x2) | 0x00122ED0; split mode 0x0050B1A0; rendered views 0x0050B198; cameras 0x0050B19C | F-0027 |
| Tracked humans (<= 4) | list 0x005D91A8, count 0x0050B194 | F-0029 |
| Viewport/render objects (2) | 0x005FDEB8 | F-0049 |
| HUD manager | 0x00600840 (164 referencing functions); per-player layout table 0x0050F7B0 (stride 0x48) | F-0030 |
| Audio listener matrices (2) | built in the in-game update (0x0010F810) | F-0049 |

## 6. Known 2-player limits (work list for 4 players)
1. GameMgr handle array and records sized 2; limit check at 0x00419B48 (F-0060).
2. Camera per-viewport arrays sized 2 (F-0026); per-player camera creation 0x0011EAF0 indexes them by player.
3. Viewport/render objects (0x005FDEB8) sized 2; ScreenEffectsManager reads per-viewport data and crashed with
   player index 2 (F-0062).
4. HUD: `MakePlayer` tries 2 slots; layout table indexed by player (F-0030, F-0056).
5. Audio listeners: 2 (F-0049).
6. Pad polling: pads 0 and 4 only (F-0055).
7. Player-2-specific code: 17 functions use GameMgr+0x22C directly; ~39 compare the player count with 1/2 (F-0061).
8. Lua scripts: `player`/`player2` globals throughout; objectives with both-players checks (MISSIONS.md).

## 7. Determinism-relevant
- Shared RNGs between effects and gameplay (F-0058); seeding unknown (F-0059).
- Camera state feeds animation/simulation (E2, F-0071).
- Emulator renderer does not (E2b).
- Timer/IOP counters differ with host timing but are not game state (E1).

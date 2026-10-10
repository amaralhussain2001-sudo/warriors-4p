# Interim report: views, quality, 60 fps and the 2-PC test package (2026-10-11)

Work done after M1 at the user's request (decisions D8-D12 in `docs/DECISIONS.md`). Everything below is **SINGLE-PC**
(two instances on one PC, loopback network) unless stated. Players were scripted bots except where noted.
Nothing here is a four-player result.

## What changed
| Area | Change | Evidence |
|---|---|---|
| View switch "not smooth" (user's trial) | Measured cause: the crop switched about 0.1 s before the picture (F-0093). The crop now travels with the frames through the GS queue, delayed 3 game frames; no wrong frames at either switch direction (F-0106) | `evidence/M3/c3a_split.json`, `c3b_merge.json` |
| Picture stretched | The 2x2 layout drew each quarter stretched about 2x sideways (also in M1 and the user's trial). Fixed with a second layout word at 0x00120B8C (F-0098) | `local/m3/aspect_cmp/sheet.png` |
| Own view always (D8) | The game's own option "2P Split Screen Merge" is forced off in sessions: views stay split even with players together (F-0099). Tab / controller touchpad or share button switches only that player's screen between own view and all views (presentation only) | `evidence/M3/o1_ownview_idle.json`; fork patch 0004 |
| Radar | Each player's radar now sits bottom-right inside their own view at single-player size (F-0103). **Still wrong:** the health/rage panel (name, bar, score, money) is drawn twice as large in the player's view | screenshots `local/m3/v1_hud2`, `v2_hud2_aspect` |
| 60 fps (D9) | PCSX2's built-in "60 FPS" entry only doubled rendered frames (characters still 30 updates/s). New patch set makes the game logic run every 1/60 s with half the time step: 60 fps, characters update every frame, pad read 60/s, walking speed within 1.4 % of 30 fps, in sync (F-0100). Needs the emulated CPU at 180 %. **Not yet checked:** attack/AI/timer speeds in detail; human feel | `evidence/M3/w60_ee2.json`, `x1_mixed_gfx.json` |
| Widescreen (D11) | PCSX2's own 16:9 patch works with the own-view crop; proportions correct, in sync (short run) (F-0104) | `evidence/M3/v4_wide_aspect.json` |
| Quality settings (D10) | 8x resolution with "High" blending: about 4 % GPU per instance on the RTX 5090. "Maximum" blending cost about 6x more GPU with no visible difference in the tested scene (F-0102). Each PC may use different graphics settings: Vulkan 8x vs Direct3D 11 1x stayed in sync for 2 minutes (F-0101) | `evidence/M3/g1..g3`, `x1_mixed_gfx.json` |
| Online safety | Loading/saving savestates, fast-forward, slow motion and frame advance are refused during sessions (they would break sync). Vibration: only the local player's rumble reaches each PC's controller (untested with a real controller) | fork patches 0004, 0006 |
| Handshake | On connect, the two PCs compare emulator build, game version, BIOS version, emulation settings and patch set, and show a message if anything differs. Hashes are now split into BIOS-kernel memory and game memory, so a different BIOS is reported separately from a real desync | fork patches 0005, 0006; `evidence/M3/p2_boot60.json` |
| 2-PC test package | `dist/warriors-4p-test.zip` (56 MB): our PCSX2 build, game patch, settings profile, launcher `Start-Coop.bat`, plain-English README, GPL source pointer and patches. No game, ISO, BIOS, memory card or savestate (the build script refuses them). Self-test on one PC from a fresh boot with fresh memory cards: 325, 147 and 563 hash points, 0 mismatches (F-0105) | `tools/make_package.py`, `evidence/M3/p1..p3_*.json` |

## Human trial (user, 2026-10-11)
About 8 minutes, user on player 1, bot on player 2: 472 hash points, 0 mismatches; the user's instance never waited
(F-0092). The user reported the view switch as not smooth, which led to F-0093 and F-0098.

## Failed or weak tests (kept on record)
- First handshake version reported a false "different emulation settings" (compared during boot; uninitialised bits
  in `Cpu.bitset`). Fixed and re-tested (F-0105).
- The radar patch from `hud_layout.md` placed the radar inside the view but at double size; replaced by the
  size-correct version from `hud_scale.md`.
- Several view-switch recordings had no switch at all because the scripted moves never brought the players together;
  the merge rule turned out to be the game option plus distance and timer conditions (`view_merge_rule.md`).

## Open problems and risks
- **E6 (two different PCs) is still the main unknown.** The package is ready for the user's test.
- Health/rage panel still too large in the player's view; centred messages and subtitles not checked in the crop.
- 60 fps: code that counts game ticks instead of time may run twice as fast (button-hold thresholds, some timers);
  needs an audit and a human feel test. Cutscene/movie timing at 60 fps not checked.
- Pause (Esc) on one PC makes the other PC wait; the agreed pause policy (§4.6) is not built yet.
- The package works on the same home network only; internet play needs the planned connection layer (D5).
- Four players: not started in code (M2).

## Originals
ISO, all BIOS files and the original `pcsx2-qt.exe`: 20 files compared, 0 changed
(`evidence/hashes/inputs_2026-10-11_m3.json`).

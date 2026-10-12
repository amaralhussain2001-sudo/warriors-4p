# M7 regression: single-player, original local 2-player and optional content with the mod installed (2026-10-12)

Build: The Warriors USA v1.03 (SLUS_212.15, static addresses; function names are OUR labels). Emulator: fork build
w4p-m6-1 (`emulator/pcsx2/bin`). Patch file: `local/m7/reg.pnach` = `python -I mod/make_pnach.py` output of the current
mod sources (SHA-256 `a2ae9a97c37e7f09...`, `note_patches check`: 3687 addresses, 6 known problems = the `[4p hud A]` /
`[4p hud B1]` alternatives). **Every run: SINGLE-PC, one emulator (sandbox instance 12), bots/scripted input, no humans,
no network, no impairment.** MTVU off in every run (`EmuCore/Speedhacks/vuThread=false`). M7 exit criteria 5, 6, 7
(`docs/plan/M7.md`). Runner: `tests/m7/reg_run.py` (new). Evidence: `evidence/M7/reg_*.json`, `evidence/M7/opt_*.json`,
6 small screenshots in `local/m7/shots/`; all screenshots and logs in `local/m7/<tag>/` and `local/m2/m7_usercard/`.

## Summary in plain English

- **Single-player still works with the mod's patch file installed (criterion 5, met for what was tested, with one gap).**
  With the same patch groups the 4-player package enables (plus widescreen), a fresh memory card and W4P off or in
  1-player mode, the game boots, the title takes Start, a new 1-player story starts, Mission 1 plays (walking,
  attacks, HUD, pause open/close), the memory card is formatted and saved, the mission ends, and after a reboot
  "Use existing profile" loads the saved progress (Mission 2 "Real Live Bunch"). Every checked screen came at the same
  game poll as in the baseline run; 0 crashes, 0 TLB misses. Example (first 2-second state sample after each change):
  Mission 1 at poll 3924 (mod) vs 3945 (baseline), the pause at 5218 vs 5207, Mission 2 at 6720 vs 6730.
  **Gap:** Mission 1's first checkpoint was NOT reached. The checkpoint comes after the 12-step combat tutorial, which
  scripted presses cannot finish; the mission was ended with the game's own "complete mission" cheat (cheat 12,
  F-0032) instead. So the checkpoint save itself is untested; the end-of-mission autosave and loading it are tested.
- **60 fps:** a short check (W4P off, keyboard) with the 60 fps group: the title accepted the first Start press, the
  menus worked, Mission 1 started and paused/resumed at about 60 frames per second (F-0186's fix holds here).
- **Original local 2-player (criterion 6): the play itself works, but the split screen looks different with the mod's
  groups (FAILED TEST for "matches the original").** Two pads, one emulator, W4P off: player 2 joins with Start, both
  move and fight, player 2 drops out through the pause menu (Quit -> "Player 2 - Continue game in 1 player mode") and
  re-joins with Start - all exactly as in the unmodified game, 0 crashes, 0 TLB misses. But when the two players walk
  apart, the unmodified game shows **two side-by-side halves, each the full screen height** (`shots/reg_2p_orig_split`),
  and joins them back into one picture when they meet again. With the package's groups the two views are drawn **in
  the top half only, and the bottom half of the screen stays empty** (`shots/reg_2p_mod_split`): the M1 group turns
  "2 views" into the 4-player 2x2 layout. In online sessions this is intended (each PC shows only its own quarter);
  for someone playing locally on one screen it is a visible regression. The package never enables these groups for
  local play, so package users are not affected (see "What 'mod installed' means").
- **Unexpected: the 'Player 2 drops out' menu item is still there with the package's groups.** Research note
  `session_policies.md` (S3/S4) and F-0168 say the session group removes it, but `mod/m2/session.txt` contains only S1
  and S5 (no S2/S3/S4 words; the shipped package pnach `f664fdd4...` has none either). Good for local 2-player; for
  online sessions it means the host can still pick it, and in the original code it releases players 2, 3 and 4 at
  once (session_policies.md 1.5) - HYPOTHESIS that this breaks a 3-4 player session; not tested here.
- **Optional content (criterion 7), fresh card:** the menus offer EXTRAS (only "TRAILER") and QUICK RUMBLE (1 ON 1:
  1P / VS; WAR PARTY: 1P / COOP / VS; only the "Fight Pen" arena). Tested with the mod's groups: 1 ON 1 vs CPU
  (1 player), WAR PARTY Co-op (2 players), 1 ON 1 VS (2 players): each ran 2.5-3.5 minutes in the arena (matches
  about 100 s each, VS fought 150 s), 0 crashes, 0 TLB misses, the game's counters kept advancing. The 2-player rumble modes
  show the same top-half layout as above. **Flashback missions and Armies of the Night are BLOCKED on a fresh card**
  (they live in the story's hideout; the arcade needs all five flashbacks, F-0064). As a stand-in they were loaded
  with the test-only level jump: flashback A "Roots" (level 82) and Armies of the Night stage 1 (level 60) each ran
  3-4 minutes with 1 player, 0 TLB misses. With a copy of the user's memory card the story loads into the hideout
  with "Flashback Level - Bonus level unlocked" on screen, and the hideout ran about 2.5 minutes without problems; the
  flashback spot itself was not reached (scripted presses cannot find it).

## What "mod installed" means (decision for these tests)

| Case | What the package does | Consequence |
|---|---|---|
| **The package as shipped** | `package4/Start-Coop.ps1` `Run-Game` copies `game\w4p.pnach` to `<package>\data\PCSX2\patches\SLUS-21215_B99A75DE.pnach` and writes `gamesettings\SLUS-21215_B99A75DE.ini` / `B99A75DE.ini` with `Enable = <group>` for `$BaseGroups` (lines 23-25: M1, own view, hud, 4p, 4p hud B1, 4p hud B2, 4p spawn, 4p spawn leave, 4p inventory, 4p fx, session, missions, session call) + `60fps` / `widescreen` when the host chose them (lines 1000-1007); `EnableCheats = false`, `EnablePatches = true` in `profile_PCSX2.ini`; the same groups go into the W4P `PatchSet` handshake (line 1012). It does this **only when it starts an online session of 2-4 players**; there is no single-player or local 2-player menu entry. Everything lives inside the package folder; the user's own PCSX2 and memory cards are never used (README step 9). The 2-player package (`package/Start-Coop.ps1` line 147) enables only M1, own view, hud (+ 60fps, widescreen). | A user's own single-player and local 2-player games (their own PCSX2) cannot be affected by the package. VERIFIED (launcher code, pointers above); no runtime test needed for that statement. |
| **Tested here: the package's groups active while playing single-player or local 2-player** | Same fork build; current sources' pnach (`local/m7/reg.pnach`); the 13 base groups + `widescreen` (14 enabled, confirmed by the emulator log "Enabled patch: ..." lines in each run's `emulog.txt`); `60fps` added for the 60 fps check with EE cycle rate 180 % as the package uses; game-affecting settings as the package profile (MTVU off, EE 100 % at 30 fps, fast boot, fixed RTC 2005-10-01 12:00, game fixes on). | This is the worst case: it is what a 2-player online session runs (the original 2-player flows), and what someone would get by copying the pnach and groups into a normal PCSX2. |
| Differences from a real package run | PINE on (state reads), native resolution, Vulkan, `Crop = false`, `SessionPolicies` off, no peers; W4P either **off** (no `W4P_CONFIG`; key presses posted to the window with a copy of `tools/winkeys.ps1`) or **on with 1 local player** (input playback from a bot file, `reg_run.py --input w4p`). The shipped package still contains an older pnach (`f664fdd4...`, 3159 patch lines vs 3724 now); results apply to the current sources. | |
| **Baselines** | 1-player: `--groups ""` = only `warriors-4p M1` (its pad-read hook is what W4P input playback and the poll counter need; its two layout words do nothing with one view). W4P-off key runs of the baseline load test also used M1 only. 2-player: **no pnach at all** (unmodified game), W4P off, key presses. | The 1-player baseline is therefore "M1 hook only", not fully unmodified; the 2-player baseline is fully unmodified. |

## Results

Environment for every row: SINGLE-PC, one instance, bots/scripted input (W4P input playback or key presses posted by
the agent), no humans, no network. "Mod" = 14 groups above; "M1" = M1 group only; "none" = no pnach.

| Run (evidence) | Groups / W4P / input | What was checked | Result | Label |
|---|---|---|---|---|
| `reg_1p_mod` | mod / W4P 1 player / script `local/m7/scripts/reg_1p.txt` + seeded random play 5550-6400 | boot, title, STORY, 1 PLAYER, new profile, difficulty, brightness, subtitles, format fresh card, Mission 1 (1 player, poll 3924), walk/attack, pause 5218-5577, cheat 12 -> autosave Yes -> Mission 2 (poll 6720); 419 s | all reached, 0 TLB, polls to 11225 | VERIFIED |
| `reg_1p_base` | M1 / W4P 1 player / same script and seed | same points: Mission 1 at 3945, pause 5207-5565, Mission 2 at 6730 | same screens, 0 TLB, polls to 11213 | VERIFIED (baseline) |
| `reg_1p_load_mod` | mod / **W4P off** / agent key presses; card saved by `reg_1p_mod` | reboot, STORY, 1 PLAYER, USE EXISTING PROFILE, profile "A" -> "2 Coney / Real Live Bunch" (`shots/reg_1p_load_mod_m2`), 1 player, radar HUD, pause menu, squad command "LET'S GO!", walking with the squad | loaded saved progress, 0 TLB | VERIFIED |
| `reg_1p_load_base` | M1 / W4P off / scripted keys (`reg_1p_load_keys.txt`) ; card saved by `reg_1p_base` | same load path -> Mission 2 at poll 2599, pause 4246-4482 | same, 0 TLB | VERIFIED (baseline) |
| `reg_1p_60` | mod + 60fps, EE 180 % / W4P off / agent keys | title Start (first press accepted), menus, Mission 1 (poll 11389), pause/resume; OSD 46-60 fps | works, 0 TLB | VERIFIED (short check) |
| `reg_2p_orig` | **none** / W4P off / agent keys, pad 1 + pad 2 | 2 PLAYER -> "Player 2 press the START button" -> pad 2 Start -> Mission 1 with 2 players; both fight; one merged view in the tutorial pen; pause -> Quit -> Player 2 -> Yes -> 1 player; pad 2 Start -> re-join scene -> 2 players, "2P" marker | original behaviour recorded, 0 TLB | VERIFIED (unmodified baseline) |
| `reg_2p_orig_split` | none / W4P off / agent keys | Mission 2 with 2 players: apart = side-by-side halves, full height, own radar each (`shots/reg_2p_orig_split`); together again = one view | recorded | VERIFIED (unmodified baseline) |
| `reg_2p_mod` | mod / W4P off / agent keys | same 2-player flow, join, both fight, **drop-out offered and works** (`shots/reg_2p_mod_quit_p2`), re-join by Start; Mission 2 apart: views 2 in the **top half only, bottom half empty** (`shots/reg_2p_mod_split`) | play works, 0 TLB; **split-screen layout differs from the original** | VERIFIED (play) / **FAILED TEST** (layout matches original) |
| `opt_rumble_mod` | mod / W4P off / agent keys, fresh cards | EXTRAS = TRAILER only (played, skipped); 1 ON 1 1P vs CPU 174 s in level 102; WAR PARTY Co-op 2 players 156 s; 1 ON 1 VS 2 players 203 s in level 102 (~150 s of fighting); 919 s in total | no crash, 0 TLB, counters advancing; 2-player modes with the top-half layout (`shots/opt_rumble_coop_mod`) | VERIFIED |
| `opt_flashback82_mod` | mod / W4P 1 player / boot + **test-only level jump** to table entry 19 (level 82 "Roots") + random play | loading screen, intro scene, play; 197 s in level 82 (about 90 s of random play) | 0 TLB | VERIFIED (via level jump only) |
| `opt_armies60_mod` | same, table entry 24 (level 60, Armies of the Night stage 1) | stage plays, timer out -> CONTINUE? -> stage restarts and plays again; 236 s in level 60 (`shots/opt_armies60_mod`) | 0 TLB | VERIFIED (via level jump only) |
| `opt_usercard_hub` (nav_probe `--memcards`) | mod / W4P 1 player / script `user_card_menu.txt`; copies of the user's cards | EXTRAS = TRAILER only; STORY -> existing profile "A" -> hideout with "Flashback Level - Bonus level unlocked"; 1 player in the hideout ~2.5 min (polls 3462-8298) | 0 TLB | VERIFIED; flashback spot not reached |
| Flashbacks / Armies from a fresh card | - | menus on a fresh card offer neither | not reachable | **BLOCKED (fresh card)** |
| Mission 1 first checkpoint | - | tutorial not finished by scripted input; cheat 12 used | not reached | **NOT TESTED** |

Notes on the evidence:
- Crash check = `TLB Miss` lines in the run's `emulog.txt` (0 in every run) plus PINE samples every 2 s
  (`samples.jsonl`: poll counter 0x000F0500, frame counter 0x0050C654, level, checkpoint, players, views, pause mode);
  the frame counter advanced in the last 60 s of every run. Runs marked `emulator_exited_early` in the JSON were
  stopped by the agent with `tools/sandbox.py kill` after the test, not by a crash.
- The PCSX2 message "Possible incorrect Q value used in COP2" (an emulator diagnostic) appears in the unmodified runs
  as well as in the mod runs; not related to the mod.
- Key injection detail: a posted Down-arrow key (pad 1 D-pad Down) did not reach the game in menus, in the unmodified
  game too; the later key runs bound pad 1 D-pad Down to ',' (`--ini Pad1/Down=Keyboard/Comma`). Test tooling only.
- The rumble result screens ended at the title screen because the agent's presses picked "Quit" / "To Main Menu";
  this was not compared with the unmodified game.

## Negative results and differences (read these first)

1. **FAILED TEST (criterion 6, "matches the original"): local 2-player split screen layout.** Unmodified: side-by-side
   halves, full height, merging when together (`local/m7/reg_2p_orig_split/k_a6.png`, `k_a7.png`). With the package
   groups: 2x2 layout, the two views in the top half, the bottom half empty (`local/m7/reg_2p_mod/k_d5.png`-`k_d7.png`;
   also every 2-player rumble mode, `local/m7/opt_mod/k_f2_*.png`, `k_f3_*.png`). Cause (VERIFIED patch text):
   `[warriors-4p M1]` words 0x00123300 and 0x00120B8C (`sltiu v0,v0,3` -> `2`) make LayoutViewports use the 2x2 mode
   from 2 views (hud_layout.md); `[warriors-4p own view]` additionally switches the merge off (merging was not
   observed in the mod run). Affects only someone who enables the groups for local play; the package does not.
   Options for the coordinator: (a) document "the warriors-4p groups are for online sessions only" (no change);
   (b) make the layout words session-only (e.g. the fork writes them only while a W4P session with crop runs).
2. **Session group lacks S3/S4 (and S2).** `mod/m2/session.txt` header promises S1-S5, F-0168 says the group has them,
   but only S1 (movie flag) and S5 (LEAVE cave) are in it; `grep 1DEADC|1DF658` finds them only in
   `docs/research/session_policies.md`. Runtime: Quit offered "Player 2 - Continue game in 1 player mode" and it
   worked (`reg_2p_mod`). For online 3-4 player sessions this original path releases all drop-in players at once
   (session_policies.md 1.5) - HYPOTHESIS that it breaks such a session; needs a decision (restore S3/S4, or test).
3. **NOT TESTED: Mission 1 first checkpoint** (scripted input cannot finish the combat tutorial); mission end used
   the original cheat 12. The 1-player test therefore skips most of Mission 1's content.
4. **BLOCKED for fresh cards: flashback missions and Armies of the Night.** Only reached through the test-only level
   jump (not the real entry points) and, for the hideout, through the user's card copy.
5. The 1-player baseline is "M1 hook only", not a fully unmodified game (W4P input playback needs the hook); the 1-player
   comparison therefore cannot see effects of the M1 group itself. The unmodified 2-player runs and the W4P-off mod
   runs show no difference in the 1-view parts of the flow (menus, Mission 1 start, pause, HUD).
6. All input was scripted or posted by the agent; nobody played. Control feel, camera and HUD readability with the mod
   are not judged here.

## Not tested

Mission 1 checkpoint and checkpoint restart in single-player; saving from other points (the game offers saving at the
card format prompt and the end-of-mission autosave; no save item was seen in the pause menu); the 2-player package
(`dist/warriors-4p-test`, groups M1 + own view + hud); local 2-player at 60 fps; W4P input playback with 2 players in
this regression (the 2-player runs used W4P off); WAR PARTY 1P and VS; other rumble arenas (locked); flashbacks B-E,
Armies of the Night stages 2-5, hideout minigames and the arcade machine through their real entry points; a full
mission completed by play; humans.

## How to repeat

```
python -I mod/make_pnach.py > local/m7/reg.pnach
G="warriors-4p own view;warriors-4p hud;warriors-4p 4p;warriors-4p 4p hud B1;warriors-4p 4p hud B2;warriors-4p 4p spawn;warriors-4p 4p spawn leave;warriors-4p 4p inventory;warriors-4p 4p fx;warriors-4p session;warriors-4p missions;warriors-4p session call;warriors-4p widescreen"
python -I tests/m7/reg_run.py reg_1p_mod --inst 12 --players 1 --script local/m7/scripts/reg_1p.txt --rand1 5550-6400 --groups "$G" --ini EmuCore/Speedhacks/vuThread=false --seconds 420 --every 3 --save-cards local/m7/cards_reg_1p_mod
python -I tests/m7/reg_run.py reg_1p_base --inst 12 --players 1 --script local/m7/scripts/reg_1p.txt --rand1 5550-6400 --groups "" --ini EmuCore/Speedhacks/vuThread=false --seconds 420 --every 3 --save-cards local/m7/cards_reg_1p_base
python -I tests/m7/reg_run.py reg_1p_load_base --inst 12 --input keys --groups "" --cards local/m7/cards_reg_1p_base --script local/m7/scripts/reg_1p_load_keys.txt --ini EmuCore/Speedhacks/vuThread=false --seconds 260
# W4P-off key runs driven by the agent (2-player, rumble, 60 fps, mod load): start the runner with --input keys
# (and --no-patch for the unmodified game), then post keys while it runs; the agent's key log is local/m7/<tag>/k_log.txt.
python -I tests/m7/reg_run.py reg_2p_orig --inst 12 --input keys --no-patch --ini EmuCore/Speedhacks/vuThread=false --ini "Pad1/Down=Keyboard/Comma" --seconds 1100
# Level jump for optional levels (test only): --callat "3999:0041ABC0:1,4009:00160D78:<entry>",
# entry = 0x01FD996C + (table index - 1) * 0x84 (19 = level 82 "Roots" -> 0x01FDA2B4; 24 = level 60 -> 0x01FDA548).
```

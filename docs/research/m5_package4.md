# M5: the 2-4 player co-op test package (warriors-4p-coop): build, self-test, LAN test steps

Date: 2026-10-12. Scope: M5 criteria 6 (join only in the lobby), 7 (co-op saving) and the package part of 8
(`docs/plan/M5.md`), on top of the w4p-net helper (`m5_w4pnet_results.md`) and the session policies
(`m5_disconnect.md`). **Every test here is SINGLE-PC, loopback, bots (scripted / seeded random input), no impairment,
no STUN, no firewall involved.** Nothing here shows that the package works between two real PCs or over the internet.
Labels as in CLAUDE.md: VERIFIED (pointer given), HYPOTHESIS, BLOCKED, FAILED TEST.

The 2-player package (`package/`, `tools/make_package.py`, `dist/warriors-4p-test`, `tests/m3/package_selftest.py`) was
not modified or rebuilt (its E6 test with the user is still pending).

## 1. What was built

| Item | Where | What |
|---|---|---|
| Launcher | `package4/Start-Coop.bat`, `package4/Start-Coop.ps1` (CRLF, ASCII, Windows PowerShell 5.1) | First start: game file, BIOS, picture quality, full screen (kept in `my-settings.txt`). Menu: 1 Host a game (2/3/4 players; join code or IP address; co-op save name; 60 fps / widescreen for everybody) - 2 Join a game (join code, read from the clipboard or pasted) - 3 Join by IP address - 4 Settings - 5 Quit |
| Settings profile | `package4/profile_PCSX2.ini` | the 2-player profile's settings line for line (159 setting lines identical, only comments changed): MTVU off, EE cycle rate 180 % with 60 fps (`{EE_CYCLE_RATE}` = 2), 100 % without (0) |
| README | `package4/README.txt` | plain English, steps 1-10: unzip, first start, host, join with codes (reply code if needed), Join by IP, firewall, lobby and start, join only in the lobby, play, co-op saves (the host's save is the reference, how to copy it), what to send back |
| Builder | `tools/make_package4.py` | builds `dist/warriors-4p-coop` + `.zip`; reuses `make_package.py`'s forbidden-file list and VC runtime lookup (that script is imported, not changed); `--reuse-emulator` keeps the emulator copy (the bin folder is copied once; origin in `dist/warriors-4p-coop-emulator-origin.json`); `--pnach FILE` ships another game patch; refuses to run while any program runs from the package folder |
| Self-test | `tests/m5/package4_selftest.py`, test-only nav scripts `tests/m5/nav/*_60x2.txt` | one host + 1-3 joiners on one PC through the package's own launchers and helpers; evidence `evidence/M5/<tag>.json` + small logs in `evidence/M5/pkg4/<tag>/` |

### 1.1 Package contents (`dist/warriors-4p-coop`, 296 files, 153 MB; zip 56 MB)
`Start-Coop.bat/.ps1`, `README.txt`, `VERSION.txt` (package id = hash over every file; the lobby compares it),
`MANIFEST.txt` (SHA-256 of every file), `COPYING.GPLv3`, `THIRD-PARTY-NOTICES.txt`, `licenses/libjuice-LICENSE.txt`,
`emulator/` (our PCSX2 build without .pdb/.ilk/.exp/.lib + msvcp140/vcruntime140/vcruntime140_1), `net/w4p-net.exe`
(+ the same three VC runtime DLLs; it links them dynamically), `game/w4p.pnach` (final package: generated from the
current sources with `python -I mod/make_pnach.py > local/m5/pkg4/w4p_pkg.pnach`, SHA-256 `f664fdd4...`,
`note_patches.py check`: 3122 addresses, 6 problems = the known `[4p hud A]`/`[4p hud B1]` alternatives;
`mod/w4p_m1.pnach` was not overwritten; earlier packages shipped `mod/w4p_m1.pnach`, SHA-256 `04f00b1d...`) and
`game/profile_PCSX2.ini`, `source/` (fork patches 0001-0017, `make_pnach.py`, `SOURCE.txt` with the fork commit, exe
hash and the libjuice v1.7.4 source pointer: archive URL, commit b89c792e..., archive SHA-256 95c08886...;
`source/w4p-net/` = our helper source + CMakeLists + build.ps1 + README). The build refuses .iso/.bin/.chd/.cso/.rom*/
.erom/.nvm/.mec/.ps2/.p2s/.elf/.irx/.mcd and SLUS_/SCUS_ files exactly like `make_package.py`. No game, ISO, BIOS,
memory card, savestate or extracted game file is in the package (VERIFIED: builder check + `find` for .pdb/.p2s/.ps2/.iso
returned nothing).

Emulator in the package: `pcsx2-qtx64.exe` SHA-256 `dc14c3b11cd9565c344773997154e7f64a99e2112b01f3d996677b59c0afa061`,
build tag w4p-m5-1 (protocol 3), built 2026-10-12 00:07:17 from W4P.cpp of 00:06:23; the fork commit when it was copied
was d2325d0 ("RestartCallsP2", 00:18:44), no uncommitted changes then; the exe contains the `RestartCallsP2` key string.
So the binary matches commit d2325d0 (HYPOTHESIS from file times and the key string; the build log was not compared).
w4p-net.exe: SHA-256 `0523eba3...` = the build tested in `m5_w4pnet_results.md` (not rebuilt).

### 1.2 How a session is set up
- **With codes (normal case):** the launcher starts `net\w4p-net.exe host --players N` or `join <code>` (real use:
  all interfaces, STUN `stun.cloudflare.com:3478` = defaults of the helper, D5/D20; no UPnP; no message service, D21),
  shows its codes, and copies the join code to the clipboard (a joiner's reply code is copied after 10 s without a
  connection). The host presses R to pass a reply code from the clipboard to the helper.
- **Lobby messages** (launcher to launcher, text `W4PL1|TYPE|key=value...`) travel through the helper's emulator bridge:
  before the game the launcher itself binds the emulator's port (127.0.0.1:41000) and sends to the helper's slot ports
  (127.0.0.1:41100+p). HELLO every second (package id, pnach SHA-256, game-file check, co-op save hash, the slots it
  hears, its measured pings; the host adds players, save name, 60 fps, widescreen, input delay), PING/PONG for the ping
  per player, START/ACK for the start. W4P ignores these datagrams (wrong magic, `HandlePacket`), so a late one that
  reaches a started emulator is harmless (VERIFIED code; all runs below had no W4P error lines).
- **Join by IP:** the same lobby over direct UDP: the host listens on 0.0.0.0:41000 and gives out slots (JOIN /
  WELCOME / FULL), sends the roster (each joiner's address as the host sees it); the emulators then use
  `BindAddress = 0.0.0.0`, `Peer<p> = <address>:41000` like the 2-player package.
- **Start rules (host):** every player connected (helper `@ready` in code mode), a HELLO from everybody within 4 s, at
  least 3 pings each (the first 2 answers are ignored: PowerShell compiles the handlers on first use and the first ping
  measured 57 ms on loopback), same package id, same pnach, game file OK, same co-op save hash, and every joiner hears
  every other player. Problems are shown per player in plain words. Pressing S locks the lobby (`lock` to the helper /
  no more JOINs) and sends START until every player answers (20 s, then "press S again to start anyway").
- **Input delay:** D = max(2, ceil((largest p90 ping + 15 ms) / (2 x frame time))), at most 12, from the host's and the
  joiners' measured pings (formula of `m5_connection_design.md` 2.4). The pings are measured by the launchers (PowerShell)
  and are a few ms higher than the helper's own pings (loopback: 5-11 ms vs 0.12-0.26 ms).
- **Session INI** (`logs\<stamp>_<mode>\w4p.ini`): `Enabled = true`, `Players = N`, `LocalSlot = k`,
  `PadForSlot0..3 = 0,4,1,2`, `ListenPort`, `BindAddress = 127.0.0.1` + `Peer<p> = 127.0.0.1:<slot port>` (codes) or
  `0.0.0.0` + `<ip>:<port>` (Join by IP), `InputDelay`, `HashInterval = 30`, `LogFile`, `DumpDir`, `Crop = true`,
  `SessionPolicies = true`, `DisconnectTimeoutS = 60`, `LeaveCalls = 0:000E7100:P`, `RestartCalls = 0:00160D78:GM+0x124`,
  `RestartCallsP2 = 0:00419AC0:GM:0,2:00160D78:GM+0x124`, `PatchSet = <pnach SHA-256>|<groups>|<co-op save hash>`.
  Groups: `M1; own view; hud; 4p; 4p hud B1; 4p hud B2; 4p spawn; 4p spawn leave; 4p inventory; 4p fx; session;
  missions; session call` (+ `60fps`, `widescreen` when chosen; both default on). `missions` (M6 fixes X1/X3/X7,
  `mod/m2/missions.txt`) was added at the coordinator's request on 2026-10-12 after the runs marked "without
  missions" below. No `test call` group and no `Test*` key in the
  package; the self-test adds them only through its test answers file (below).
- **Co-op saves (criterion 7):** `coop-saves\<save name>\Mcd001.ps2` (+ `Mcd002.ps2`) in the package folder, never the
  player's own PCSX2 cards. Before the game: the emulator's card folder (`data\PCSX2\memcards`) is emptied (leftovers
  kept in `data\memcard-leftovers`, last 6) and the group's cards are copied in (a new name = no card; PCSX2 creates
  blank 8 MB cards, `MemoryCardFile.cpp` `FileMemoryCard::Open`/`Create`, VERIFIED code). Their hash is in `PatchSet`,
  so the W4P handshake also reports a mismatch. After the game the cards are copied back (previous files kept in
  `backup\<stamp>`, last 5) **only if the game ended normally**: exit code 0, the session started, the W4P log has its
  shutdown line with 0 mismatches, no DESYNC, no "differs", the host did not leave, not force-stopped.
- **Self-test mode** (`-TestFile answers.json`): no questions, no clipboard, own ports/folders, `autoStart`,
  `lobbyTimeoutSec`, `runSeconds` (then the launcher closes its own game window with WM_CLOSE: PCSX2 shuts down
  normally, exit code 0 in every run; a game that does not close within 150 s would be force-stopped - never
  happened), `botFile`, `extraGroups`/`extraW4P` (test only), `baseGroups` (test-only isolation runs),
  `stopBeforeGame` (lobby only). It also writes `lobby-screens.txt`: every different lobby screen a player would see
  (codes masked).

## 2. How to run
- Build: `python -I mod/make_pnach.py > local/m5/pkg4/w4p_pkg.pnach` (from Git Bash, like `mod/w4p_m1.pnach`), then
  `python -I tools/make_package4.py --pnach local/m5/pkg4/w4p_pkg.pnach` (copies `emulator/pcsx2/bin` once; after a new
  emulator build run it without `--reuse-emulator`) or with `--reuse-emulator` (launcher/README changes only).
- Self-tests (each waits until at most 4 `pcsx2-qtx64.exe` run; ports 47000+; the harness never kills a process):
  - `python -I tests/m5/package4_selftest.py <tag> --preset m13 --players 4 --seconds 720 --late-joiner`
  - `python -I tests/m5/package4_selftest.py <tag> --preset m13 --players 3 --seconds 480 --saves-root <dir> --group <name>`
  - `python -I tests/m5/package4_selftest.py <tag> --preset m1_60x2 --players 2 --seconds 420`
  - `python -I tests/m5/package4_selftest.py <tag> --preset m1_30 --players 2 --seconds 240 --lan` (Join by IP)
  - `python -I tests/m5/package4_selftest.py <tag> --mismatch` (lobby only)
  - 60 fps title probes: `--preset title60 --players 2 --seconds 300` (+ `--title-keys`: real key presses with
    `tools/winkeys.ps1` instead of bot input for player 1; + `--groups-2p`: the 2-player package's base groups)
- Players: unzip `dist/warriors-4p-coop.zip`, double-click `Start-Coop.bat`, follow `README.txt`.

## 3. Self-test results

All runs: SINGLE-PC (Ryzen 9 9950X3D, RTX 5090, Windows 11), loopback only, w4p-net with `--no-stun --bind 127.0.0.1`
(the self-test's only change to the helper's real-use command line), fresh memory cards (or the run's own co-op save),
bots, no impairment, native resolution, MTVU off (profile). The coordinator's own tests were running at the same time
(4 other `pcsx2-qtx64.exe` when each run started, 8 later), so CPU load was present and not ours. Hash points = W4P
HASH entries (every 30 polls) present on every instance; mismatches compare all instances. "Waits" = W4P's stall time
per instance (an instance that is ahead waits for the others' input). Test-only additions (never in the package):
`BotInput`, and for the m13 preset the group `warriors-4p test call` + `CallAt = 3999:0041ABC0:1,4009:00160D78:0x01FD9F9C`
(level jump to Mission 13 at fixed polls, as in every M2/M5 4-instance run), given through the test answers file.

| Run (tag) | Package id | Players / mode | What | Hash points (common) | Mismatches (all / game RAM) | Other results | Label |
|---|---|---|---|---|---|---|---|
| `pk4_lobby_mismatch` | 33938fbe8b0c | 2, codes, lobby only (no emulator) | A: joiner's co-op save differs (dummy 4 KB files standing in for cards); host has `autoStart` | - | - | A: host never started (problem "save" for player 2, lobby timeout 45 s); joiner saw "Your co-op save is DIFFERENT ... check code CDDF4B33 / 8DB3E39F" and was not started. B: after copying the host's file to the joiner: START handshake completed on both ("start-ok"), same save hash | VERIFIED (`evidence/M5/pk4_lobby_mismatch.json`, `evidence/M5/pkg4/pk4_lobby_mismatch/*/lobby-screens.txt`) |
| `pk4_m13_4p` | c5eb772416e6 (*) | **4**, codes (helpers), 30 fps, widescreen | boot, Mission 1 (2 players), level jump to Mission 13, players 3-4 join by Start (8200/8350), random bots from poll 9000; **737 s** total, emulators closed after 720 s; late joiner 60 s after the start | **673** (polls 30-20190) | **0 / 0** | lobby ready 9.4 s after the host started (all joiners by direct dial, path b, about 0.5 s each); launcher pings 7.5-10.4 ms, input delay 2; all 12 handshakes "player N matches (build, game, BIOS, settings, patches)"; 0 TLB misses; frame rate from poll 9000 median 29.97, lowest 10-s window 29.87; waits 10.7 / 84.7 / 2.6 / 84.2 s, longest single wait 4.05 s; helper pings p50 0.12-0.26 ms, 0 bad tag/MAC/source, 0 send errors, 0 datagrams without route, 0 emulator datagrams dropped; end screenshots: each window shows its own player's view, player 3's window the FOX panel; all four games closed normally (exit code 0), co-op saves copied back, identical on all four PCs. **Late joiner:** never got a slot; host's connection log "direct dial refused: lobby closed"; the running game was unaffected (0 mismatches) | VERIFIED (`evidence/M5/pk4_m13_4p.json`, `evidence/M5/pkg4/pk4_m13_4p/`, screenshots `local/m5/pkg4/pk4_m13_4p/shot_pc*_t0675.png`) |
| `pk4_m13_3p` | 441a9d76ee72 (*) | **3**, codes, 30 fps | same path, players 1-3; started from the **existing** co-op save of `pk4_m13_4p` (save name `m13group`, hash ac16576d...) on PCs 1-3; 495 s | **436** (30-13080) | **0 / 0** | lobby compared the existing save on all three ("own save same"), started in 8.5 s; frame rate from poll 9000 median 29.97, min 29.97; waits 5.3 / 2.0 / 4.2 s; 0 TLB misses; player 3's own view in Mission 13 at the end; saves copied back, identical | VERIFIED (`evidence/M5/pk4_m13_3p.json`) |
| `pk4_m1_2p60` | 441a9d76ee72 (*) | 2, codes, **60 fps** | repo scripts `boot_to_m1_2p_60*.txt`; late joiner after the start; 433 s | **888** (30-26640) | **0 / 0** | **the game never left the title screen** (section 4): the run covers boot logos, menus and title at 60 fps only; frame rate median 59.94; late joiner refused ("lobby closed") | VERIFIED (sync, title only) / FAILED TEST (gameplay at 60 fps not reached) (`evidence/M5/pk4_m1_2p60.json`) |
| `pk4_m1_2p60b` | 441a9d76ee72 (*) | 2, codes, **60 fps** | test-only script `tests/m5/nav/boot_m1_2p_60x2.txt` (30 fps timings, doubled gaps); 433 s | **876** (30-26280) | **0 / 0** | again stuck at the title: Start (held 5 polls) at poll 8320, 646 polls after the title appeared, was not accepted; median 59.74 fps, lowest window 47.8 (CPU load) | VERIFIED (sync) / FAILED TEST (navigation) (`evidence/M5/pk4_m1_2p60b.json`) |
| `pk4_lan2_m1` | 18d32fe54258 (*) | 2, **Join by IP** (direct UDP), 30 fps | `boot_to_m1_2p.txt` / `p2_join.txt`; 255 s | **209** (30-6270) | **0 / 0** | IP lobby (JOIN/WELCOME) + START in 8 s; reached Mission 1's intro movie with "1/2 want to skip" on screen (player 2's bot never votes); both closed normally, saves identical | VERIFIED (`evidence/M5/pk4_lan2_m1.json`, screenshot `local/m5/pkg4/pk4_lan2_m1/shot_pc1_t0195.png`) |
| `pk4_title60` | 33938fbe8b0c | 2, codes, **60 fps** | title probe: player 1's bot presses Start held 20 polls every 400 polls from poll 7900; player 2 no input; 300 s | 783 | **0 / 0** | the Start at 7900 (screen before the title) was accepted (mode 0x005E57E0 at 7901); title mode 0x005E65C0 from poll 8576; **11 more Start presses (8700-12700) ignored** | FAILED TEST (title at 60 fps) (`evidence/M5/pk4_title60.json`) |
| `pk4_title60_keys` | 33938fbe8b0c | 2, codes, **60 fps** | as above, but player 1 has **no bot input**: the harness posts real key presses (Enter = Start, 200 ms) to his game window with `tools/winkeys.ps1` every ~20 s from 150 s | 873 | **0 / 0** | the first key press (legal/logo screen, poll ~13504) was accepted; title from poll 14179; **5 later key presses at the title ignored** (screenshots `key_pc0_t*.png`) | FAILED TEST (title at 60 fps, keyboard path) (`evidence/M5/pk4_title60_keys.json`, `local/m5/pkg4/pk4_title60_keys/`) |
| `pk4_title60_2pgroups` | aff287cc6ada | 2, codes, **60 fps**, test-only base groups of the **2-player package** (M1, own view, hud + 60fps, widescreen; no 4p/session groups) | same bot presses as `pk4_title60`; 300 s | 787 | **0 / 0** | same result: title from poll 8575, every Start ignored. So the 4-player and session groups are not the cause | FAILED TEST (`evidence/M5/pk4_title60_2pgroups.json`) |
| `pk4_final_4p` | aff287cc6ada (without missions) | **4**, codes, 30 fps | same as `pk4_m13_4p` (new save `final4`), late joiner; 737 s | **677** (30-20310) | **0 / 0** | lobby ready 9.4 s, pings 7.3-10.2 ms, delay 2; all 12 handshakes match; 0 TLB misses; 29.97 fps median, lowest window 29.87; waits only 2.0-4.1 s per instance this time (longest 2.04 s at the start); helper pings p50 0.12-0.23 ms, 0 errors; player 4's own view at the end; all normal ends, saves identical; late joiner refused ("lobby closed"). **Incident:** a package rebuild started by mistake during this run (section 4 item 8) | VERIFIED (`evidence/M5/pk4_final_4p.json`) |
| `pk4_final_lan2` | aff287cc6ada (without missions) | 2, Join by IP, 30 fps | as `pk4_lan2_m1`; 254 s | **209** (30-6270) | **0 / 0** | reached Mission 1's intro; normal ends, saves identical | VERIFIED (`evidence/M5/pk4_final_lan2.json`) |
| `pk4_lobby_mismatch` (rerun) | aff287cc6ada (without missions) | 2, lobby only | as above | - | - | all five checks true | VERIFIED (`evidence/M5/pk4_lobby_mismatch.json`) |
| `pk4_missions_lobby` | **5eab3e866200 (final)** | 2, lobby only | as `pk4_lobby_mismatch` | - | - | all five checks true | VERIFIED (`evidence/M5/pk4_missions_lobby.json`) |
| `pk4_missions_4p` | **5eab3e866200 (final)** | **4**, codes, 30 fps, groups incl. `missions` | as `pk4_m13_4p` (new save `missions4`), no late joiner; **620 s** game, 637 s total | **573** (30-17190) | **0 / 0** | all 12 handshakes match; 0 TLB misses; W4P error lines: none; waits 2.0-4.9 s per instance; helper pings p50 <= 0.22 ms, 0 datagrams dropped or without route; player 3's own view in Mission 13 at the end; all normal ends, saves identical. **Frame rate from poll 9000: median 29.37-29.47, lowest window 29.07-29.27** (earlier runs without `missions`: 29.97 / 29.87); cause not separated (the `missions` patches, or the 4 other emulators of the coordinator running at the same time: HYPOTHESIS) | VERIFIED (`evidence/M5/pk4_missions_4p.json`) |

(*) Package versions (the id changes with every file; emulator, helper and profile are identical in all of them):
5eab3e866200 = **final** (adds the `missions` group and ships the pnach generated from the current sources);
aff287cc6ada = the same launcher without `missions`, with `mod/w4p_m1.pnach`, plus the README 60 fps warning and the
test-only `baseGroups`; 33938fbe8b0c differs from aff287cc6ada only by those two; 441a9d76ee72 additionally only in the
host's "different co-op save" wording; c5eb772416e6 additionally in two displayed texts (the helper's "Player N joined
(...)" message, the "new game" save label); 18d32fe54258 additionally lacks the self-test screen dump
(`lobby-screens.txt`).

## 4. What did not work / negative results
1. **60 fps runs never got past the title screen (FAILED TEST for the test navigation).** With fresh memory cards and
   the package's 60 fps settings, the repo's `boot_to_m1_2p_60.txt` (written for a card with a profile; never used
   before, no evidence found) and my doubled-gap script both stopped at "PRESS THE START BUTTON": game mode 0x005E65C0
   from poll ~7674, no further mode change although Start was pressed (held 5 polls) at poll 8320. At 30 fps the same
   press at the same screen works (`pk4_lan2_m1`, `pk4_m13_*`). Three probes (table rows `pk4_title60*`) show the same thing: at 60 fps the title screen (mode 0x005E65C0) ignored
   every Start - 11 scripted presses held 20 polls, and 5 **real keyboard presses** posted to the window (the screen
   before it accepted both kinds) - also with only the 2-player package's patch groups. So it is tied to 60 fps mode
   (the `[warriors-4p 60fps]` group with EE 180 %, or how W4P input reaches that screen at 60 fps), not to the new
   groups. VERIFIED for this build on SINGLE-PC in W4P sessions; untested: 60 fps without a W4P session, a real game
   controller, a card that already has a profile (the M3 60 fps tests used savestates or never pressed Start there).
   **Consequences:** with the default 60 fps, players may be unable to start a game. The 2-player package (E6, also
   60 fps by default, older build w4p-m3-7) is probably affected the same way (HYPOTHESIS, not run: that package must
   not be touched). The README of this package now tells testers to answer "no" to 60 fps first. **Recommendation for
   the coordinator: investigate before the user's E6 / LAN tests** (e.g. PINE read of the title's pad state at 60 fps;
   compare the 30 fps path), or tell the user to choose 30 fps for E6.
2. **No gameplay at 60 fps was tested in this package** (consequence of 1). 60 fps lockstep with 4 players was measured
   earlier from a savestate (F-0100, F-0161), not through this launcher.
3. **The co-op save content was never really written by the game in these runs:** the cards stayed blank (8,650,752
   bytes of 0xFF, as PCSX2 creates them); no mission was completed and no save prompt answered. The copy-in / hash /
   copy-back / compare path is tested; a real save written in lockstep and then compared is not.
4. **Large stall totals on some instances** (4-player run: 84 s of 720 s on two instances, many short waits of about
   5 ms each; 60 fps runs: 45-50 s). The frame rate stayed at 29.97 / 59.7-59.9 median, so these are the faster
   instances idling for the slower ones under CPU load (4-8 other emulators of the coordinator ran on the same PC). Not
   comparable with T1f (0.7-10.6 s). Real-PC numbers need T2.
5. **Pings measured by the launcher are PowerShell pings:** 5-11 ms on loopback where the helper measures 0.12-0.26 ms
   (the first answers even 57 ms before the warm-up rule was added). The input delay formula therefore over-estimates
   slightly; at 60 fps that can add one frame of delay at about 18-20 ms real RTT (HYPOTHESIS, computed from the formula).
6. **w4p-net cosmetic bug:** its "Player N joined (path b; connected -179417761.6 ms after the agent started)" message
   prints a negative time (it uses `connected_us` before CheckLinks sets it; `helper.cpp`, HELLO branch of HandleCtrl).
   The launcher now shows "Player N joined." instead; the helper itself was not changed or rebuilt.
7. **Bugs found and fixed in the launcher during the self-tests** (for the record): PowerShell variable names are
   case-insensitive (`$P` peer = `$p` index: the first lobby test crashed); a joiner treated "host left" before "start"
   when the host's helper stopped right after START (test-only race, fixed by order); first-ping warm-up (above).
8. **A package rebuild ran during a test (my mistake, `pk4_final_4p`).** The run had just left its "waiting for free
   slots" state; `make_package4.py --reuse-emulator` renamed the package's `emulator` folder (Windows allowed it while
   the four emulators ran from it) and deleted `Start-Coop.bat/.ps1` and `VERSION.txt` before a locked DLL in `net\`
   stopped it. I renamed the folder back and restored the three files from the identical zip (293 other files
   byte-identical); the four emulators showed no error and the run ended normally with 0 mismatches. The builder now
   refuses to run while any program runs from the package folder (checked: it listed the 8 running test processes).
   For the record the run counts, but under a package that was briefly incomplete.
9. **Not exercised by the self-test:** the interactive menus and keys (S/R/Q/C), clipboard copy/paste, the file
   pickers, the Join-by-IP late refusal ("FULL started"), the reply-code path through the launcher (R key; the helper's
   own T1d test covered reply codes), a cancelled start, a session that ends abnormally (crash / forced stop: the
   "do not copy back" path), STUN and real network interfaces, Windows Firewall prompts, the disconnect/host-choice
   policies through the package (tested by the coordinator with m2_run4, F-0164..F-0178). The player-facing lobby
   screens were rendered in test mode (`lobby-screens.txt`) but not seen in a real console window.

## 5. Known limits
- SINGLE-PC only. LAN (T2), internet (T3/T4), real routers/NAT, STUN, IPv6, firewall: all HYPOTHESIS until tested.
- **Players 3-4 can only join where the game lets extra Warriors join.** Verified only in Mission 13 ("All-City"),
  reached here through a test-only level jump that the package does not contain. In Mission 1 they cannot join
  (F-0109); other missions are M6 work. A new story in this package is therefore effectively a 2-player test; README
  step 7 says so.
- Joining only in the lobby (criterion 6) is enforced by the helper (`lock` at start: "direct dial refused: lobby
  closed") and by the launcher (no new slots after START). A late player gets no explicit "game already started"
  message in code mode (the host ignores his dial silently); his window explains it after 30 s. Once the host pressed
  S, nobody can join that lobby any more, even if the start is cancelled (the host must host again).
- The co-op save is compared by hash only; there is no transfer between PCs (players copy the host's files by hand,
  README step 9). Progress is copied back only after a normal end; a crash keeps the previous save (by design).
- Join by IP needs the host's lobby (PowerShell) and PCSX2 to receive on UDP 41000: Windows asks about both programs
  the first time (README). With codes only w4p-net faces the network (the emulator stays on 127.0.0.1).
- Input delay is chosen once at the start (from lobby pings); it does not adapt during the game.
- Esc as a pause request (D18) is still untested (README says so).

## 6. LAN test for the user (needs the second PC; T2 of the design note)
Prerequisite: the E6 test with the 2-player package (`dist/warriors-4p-test.zip`) is separate and still pending;
this is a second, independent test. Both PCs on the same router. About 45 minutes.

1. Copy `dist/warriors-4p-coop.zip` (SHA-256 5c35804863d714f9490dad9f072970e6932cb1239d2adcd0edd9f9bf867d3f8c, package id 5eab3e866200; a rebuild by the coordinator changes both) to both PCs (USB stick or network share) and unzip it on each,
   e.g. to the Desktop (use the unzipped copy, not the project's `dist` folder).
2. On both PCs double-click `Start-Coop.bat`; if Windows says "Windows protected your PC": More info -> Run anyway.
   Pick your game file and your BIOS file; press Enter for the suggested picture quality; full screen: your choice.
3. **Test A - join code (about 15 minutes of play):**
   a. PC 1 (main PC): `1` Host a game -> `2` players -> `1` join code -> save name `lan1` -> 60 fps: see the note below
      -> widescreen `yes`. The window shows a join code (already copied).
   b. Send the code to PC 2 (for example e-mail or a chat app to yourself). On PC 2: copy it, choose `2` Join a game
      (it finds the code in the clipboard: answer `yes`).
   c. If Windows asks about "w4p-net" on either PC: tick "Private networks", click "Allow access". Write down whether
      it asked.
   d. Within about 10 s PC 2 should say "Connected. You are Player 2"; if not, PC 2 shows a reply code: send it to
      PC 1, copy it there and press `R`. Write down whether the reply code was needed.
   e. On PC 1 wait until Player 2 shows "ready" and a ping, then press `S`. Both games start.
   f. Play: PC 1 starts the story with 2 PLAYER, PC 2 presses Start (Enter) to join. Fight, grab, use items, pause
      (Start), skip a cutscene together, lose a fight and continue from the checkpoint. Then close both game windows.
   g. Note what each Start-Coop window says afterwards ("Co-op progress saved ..." or "NOT saved: ...").
4. **Test B - Join by IP (about 10 minutes):** PC 1: `1` Host a game -> `2` players -> `2` by IP address -> save name
   `lan1` -> same answers. PC 2: `3` Join by IP address -> type the address shown on PC 1 (e.g. 192.168.1.23).
   Allow "Windows PowerShell" and "pcsx2-qtx64" if Windows asks. Both windows must show the same save check code
   (if Test A saved progress, the codes now prove the copy-back worked); press `S` on PC 1, play a few minutes, close
   both games.
5. Send back from BOTH PCs the newest folders in `logs\` (one per test, e.g. `20261012_201500_host`, `..._join`,
   `..._lanhost`, `..._lanjoin`), and say: which PC was which, CPU and graphics card of each, whether Windows asked
   about the firewall (for which program), whether the reply code was needed, how controls and frame rate felt,
   anything strange (freezes, "Waiting for Player", "OUT OF SYNC").

Criterion 6 (late join) and 3-4 players cannot be tested with two PCs.

**60 fps note (section 4, item 1):** until the title-screen question is answered, play Test A with 60 fps `no`
(30 fps). Then repeat a short Test A with 60 fps `yes` and report whether Start at the title screen works.

## 7. Proposed findings (IDs to be assigned by the coordinator)
- Final package 5eab3e866200 (with `[warriors-4p missions]`): 4 instances, 620 s, 573 common hash points, 0 mismatches,
  frame rate median 29.37-29.47 (VERIFIED SINGLE-PC, `pk4_missions_4p`).
- The 2-4 player package launcher (codes through w4p-net, lobby over the helper bridge, start handshake, session INI with
  `SessionPolicies`/`DisconnectTimeoutS`/`LeaveCalls`/`RestartCalls`/`RestartCallsP2`/`PatchSet` incl. the co-op save
  hash) ran 4 instances on one PC for 720 s: 673 common hash points, 0 mismatches, 0 TLB misses, all handshakes
  matching; VERIFIED SINGLE-PC (`pk4_m13_4p`). Same for 3 players from an existing co-op save (436 points, 0
  mismatches) and 2 players over Join by IP (209 points, 0 mismatches).
- Joining only in the lobby (M5 criterion 6), transport part: a joiner using the join code after the start got no
  slot; host helper "direct dial refused: lobby closed"; the running game unaffected; VERIFIED SINGLE-PC
  (`pk4_m13_4p`, `pk4_m1_2p60`). The message for a late player is the launcher's text only.
- Co-op save policy (M5 criterion 7), mechanism: different co-op saves block the start on both sides with plain-text
  messages; identical saves start; saves are copied back only after a normal end and were identical on all PCs after
  every run; VERIFIED SINGLE-PC (`pk4_lobby_mismatch`, all runs). Real game-written save data: not tested.
- PCSX2 closes cleanly on WM_CLOSE during a W4P session (exit code 0, W4P shutdown line written) on every instance of
  every run; VERIFIED (launcher logs).
- **FAILED TEST / open:** at 60 fps with fresh memory cards the scripted Start at the title screen was not accepted
  (two scripts; mode 0x005E65C0 from poll ~7674); 30 fps works. Real keyboard presses are ignored there too, and the 2-player package's patch groups give the same result; possibly
  blocks real players at 60 fps (the default); probably affects E6 (HYPOTHESIS).

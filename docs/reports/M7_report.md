# M7 report - robustness (2026-10-12)

**Result: every SINGLE-PC exit criterion of M7 (`docs/plan/M7.md`) now has test evidence, except criterion 4's final
smoke batch, which runs after the D24 and camera-parity changes are merged (section "Still open").** Everything here is
one PC with bots or scripted input, 4 emulators in lockstep on loopback unless noted. It does **not** prove: two or more
real PCs, real routers or the internet, human players, or how the controls feel with latency. Those parts are listed at
the end as tests only you can do.

Environment: Ryzen 9 9950X3D, RTX 5090, 64 GB, Windows 11; our PCSX2 build w4p-m6-3 (v2.9.115 + W4P patches 0001-0020)
unless noted; MTVU off; native resolution in the test sandboxes. Evidence: `evidence/M7/*.json`, `evidence/M2/*.json`,
logs and screenshots in `local/` (not committed). Originals unchanged: 20 files, 0 changed
(`evidence/hashes/inputs_2026-10-12_m7.json`).

## Plain-English summary
- **An hour of play stays in sync.** Four emulators played Mission 13 for 65 minutes with random button-mashing bots,
  including a "Last checkpoint" reload in the middle: 1,545 checkpoints of the game state compared, **0 differences**,
  no crash, no freeze. Each emulator used about a quarter of one CPU core and 1.3 GB of memory; memory grew by about
  40 MB over the hour. (The PC was busy with ~15 other test emulators, so the game ran slower than real time: about 12
  frames of input per second on average instead of 30 - lockstep simply waited, it did not break.)
- **Short network outages heal by themselves; long ones end in the host's choice.** Through the real connection helper
  (the program the package uses), player 4's game traffic was cut three times. Example: a 20-second cut -> the other
  three PCs showed the waiting message for 19 s and then the game simply went on, still in sync; 45 s -> waited 44 s,
  went on; 75 s -> after the 60 s limit the host chose "continue without him" and the other three played on in sync.
  Limit of this test: the helper's own connection check (ICE) kept running, so a real cable-pull that kills the
  connection for more than 30 s (when the helper has to re-dial) still needs your LAN/internet test.
- **Latency, jitter and packet loss do not break the sync** (12 simulated conditions, 0 differences; only 150 ms
  round-trip at the lowest input delay slowed the game by 3 %, and the package's automatic delay rule avoids that).
- **The mod does not change normal play:** single-player, the original local 2-player mode and the optional content
  (Rumble, a flashback mission, Armies of the Night) behave like the unmodified game with the package installed.
- **Bandwidth:** about 1 Mbit/s upload and 1 Mbit/s download per PC with 4 players at 60 fps (half at 30 fps).

## Exit criteria
| # | Criterion | Evidence | Verdict |
|---|---|---|---|
| 1 | >= 60 min, 4 instances, a level change, 0 mismatches / crashes / softlocks | **long1**: 3911 s, 1545 common hash points, 0 mismatches, 0 TLB misses, poll counter advanced in every sample; reload at poll 40000 (players back to 4 after 693 polls); D24 pnach of 16:30 (7214 addresses) - F-0220 | **PASS** (SINGLE-PC, bots) |
| 2 | Outage through the real connection path: short one recovers, long one reaches the host's choice | **t1g**: helpers with the new test switch `mute`; 20 s -> wait 19.0 s, resumed; 45 s -> 44.1 s, resumed; 75 s -> timeout, host "continue", "player 4 leaves the session from poll 10253" on all three, 0 mismatches before and after, 0 TLB - F-0219 | **PASS** for the game-data path; ICE re-dial NOT exercised (needs a real outage) |
| 3 | Impairment RTT 50/100/150, jitter, loss 1 %/5 %, >= 10 min each, 0 unrecovered desyncs, delay/stall/fps reported | 12 runs x 660 s, all 0 mismatches; speed and waiting per condition in F-0206 | **PASS** (simulated, built-in W4P impairment) |
| 4 | Every mission smoke-tested with 4 players after all M6 fixes; restarts in >= 6 missions | smoke3 all 18 missions 0 mismatches / 0 TLB (F-0201, before FOVFIX/X6 rows/labels); checkpoint restarts in 6 missions (F-0204); real mission end -> hideout (hubreal_m4, F-0218) | **partly**: the final smoke after the D24 + camera merge is still to run |
| 5 | Single-player regression | F-0193 (boot, new story, M1, pause, save/load, M2; 60 fps title) | **PASS** |
| 6 | Original local 2-player regression | F-0193: join, fight, drop-out, re-join = original; the 2x2 layout appears only if the mod's groups are switched on for local play, which the package never does | **PASS** with the package; FAILED TEST only in a configuration the package does not produce |
| 7 | Optional content at its original player count | F-0193: Rumble modes, flashback 'Roots', Armies stage 1, user card in the hideout, 0 TLB | **PASS** (flashbacks/Armies via test level jump; not offered on a fresh card) |
| 8 | Measurements | table below | **PASS** (SINGLE-PC numbers) |
| 9 | Originals unchanged | 20 files, 0 changed | **PASS** |

## Measurements (all SINGLE-PC, loopback)
| Quantity | Value | Conditions / source |
|---|---|---|
| Round-trip time between helpers | p50 0.14-0.24 ms, max 0.71 ms | loopback, pk4g_m13_60 helper pings (F-0207) |
| Input delay | 2 frames chosen by the package at 8 ms RTT; rule ceil((p90 RTT + 15) / (2 x frame time)), min 2: 2/2/3 frames at 30 fps and 2/4/5 at 60 fps for RTT 50/100/150 ms | `package4/Start-Coop.ps1` Compute-Delay; F-0206 |
| Jitter / loss tolerance | +-20 ms jitter, 1 % and 5 % loss: 0 mismatches, speed 27.1-27.3 of 30 | F-0206 (simulated) |
| Bandwidth per player | 0.34-0.35 Mbit/s per link and direction at 60 fps; 3 links -> about 1.0 Mbit/s up and down per PC; half at 30 fps | F-0221, pk4g_m13_60 helper byte counters |
| Desync frequency | 0 hash mismatches in every M7 run (long1, t1g, 12 impairment runs, regression, package self-tests) | no resync was ever needed, so resync time could not be measured (the design resyncs by restarting from the checkpoint, M4) |
| Outage recovery | resumes within the poll after packets return (waits 19.0 s for a 20 s cut, 44.1 s for 45 s) | t1g |
| CPU / memory per instance | 0.25-0.26 cores average; working set <= 943 MB; private bytes 1.27 -> 1.32 GB in 65 min | long1, 4 emulators + ~15 others on the same PC |

## New findings
- F-0218 real mission end -> hideout with 4 players (the game's own `UnlockAndLoad()`), interlude screen on the other PCs.
- F-0219 w4p-net test switch `mute` and the T1g result.
- F-0221 bandwidth per player. F-0220 the 65-minute session.

## Still open
- **Criterion 4 final batch:** smoke all 18 missions with 4 players after the D24 (players 3-4 in the 2-player chases)
  and camera-parity rows are merged; result goes into this table and FINDINGS.
- **Needs you (does not block the SINGLE-PC criteria):** a real network outage on LAN/internet (pull a cable or switch
  Wi-Fi off for 20 s, then for 45 s, on one PC), the feel of the controls with latency, and the internet session with
  friends. Exact steps are in the final report's test sheet.

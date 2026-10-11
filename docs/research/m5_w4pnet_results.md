# M5: w4p-net helper, implementation and single-PC test results (T1a-T1e)

Date: 2026-10-11 (tests run 21:12-21:35 local time). Implements option S of `docs/research/m5_connection_design.md`
(helper process; the emulator keeps its loopback UDP transport). Code: `net/w4p-net/` (README there has build/run steps).

**Environment of every test here: SINGLE-PC, loopback only (`--bind 127.0.0.1`), no STUN (`--no-stun`), host
candidates only, no impairment simulated, bots (helper probe traffic or the Python lockstep simulator), no emulator.**
No STUN/TURN server and no other network host was contacted; the only network access was downloading libjuice from
GitHub. During all runs five `pcsx2-qtx64.exe` instances of another test were running on the same PC (CPU load present,
not ours, not touched). Nothing here says anything about LAN or internet behaviour: those stay HYPOTHESIS until T2-T4.

Labels as in CLAUDE.md: VERIFIED (pointer given), HYPOTHESIS, BLOCKED, FAILED TEST.

Build under test: `net/w4p-net/build/w4p-net.exe` SHA-256 `0523eba3e8ef34d88491fd470215380a5a2c7ab12e70f1a97b0e068c47d45af2`
(built 21:18 with `net/w4p-net/build.ps1`, newer than every source file), `w4p-net-codec-test.exe` SHA-256
`3241d8a881f4176109756f241f32dfde21e6eda2c9edc930ac0bdf19a33b1664`; MSVC 19.51.36257, CMake 4.3.1-msvc1, Ninja 1.13.2;
libjuice v1.7.4 (commit `b89c792e3612faf2f12cf35bcc56857313a06be3`, archive SHA-256
`95c088862aa1b88b73d62aa99577135010eb768fcafb252d13aa85a8515ef798`, unmodified, see `net/w4p-net/README.md`).
Evidence: `evidence/M5/w4pnet/<test>/` (summary.json, each helper's connection log and stats JSON; the raw stdout files
with the session codes stay in `net/w4p-net/build/results/`, gitignored).

---

## Results table

| Test | What | Result | Pass criterion (design note section 6) | Label |
|---|---|---|---|---|
| T1a | Code codec: 10,000 random descriptions; every single-character substitution, deletion, adjacent swap | 10,000/10,000 round trips (also inside other text, lower case, line break after a dash). Substitutions 58,981,455 tried: 58,324,228 detected, 657,227 decode to the same description (case, I/L/O aliases), **0 undetected**. Deletions 907,407: all detected. Swaps 877,494: all detected. SipHash-2-4 and CRC-16 test values pass | 100 % round trip, every error detected | **PASS**, VERIFIED (`evidence/M5/w4pnet/t1a/t1a_output.txt`) |
| T1b, 2 helpers | Connect, then 200-byte datagrams at 60/s for 60 s each way | Connected on attempt 1. Host link up 0.4 ms after the host's agent started; joiner ready 0.128 s after its start. 7,200/7,200 probes received, 0 duplicates, **0 loss**; echo RTT p50 0.111 ms, p99 0.186 ms, max 0.412 ms | < 2 s, 0 loss | **PASS**, VERIFIED (`t1b_2p/summary.json`) |
| T1b, 4 helpers | Full mesh (6 pairs), same probe on all 12 directed streams | All 6 pairs on attempt 1 (selected pair host/host loopback). Every helper ready 0.129-1.083 s after its start. 43,200/43,200 received, **0 loss**; echo RTT p50 0.093-0.178 ms, p99 0.196-0.332 ms, max 0.512 ms; 0 rejected datagrams, 0 send errors | < 2 s, 0 loss | **PASS**, VERIFIED (`t1b_4p/summary.json`) |
| T1c | Path (b): joiners use the join code only (no reply code pasted), 2 and 4 players | Every joiner connected by direct dial: 502-510 ms after start (= its first check retransmission at 500 ms; the first check only triggers the host's listener). Host saw each joiner as a peer-reflexive candidate. 4 players: all joiner-joiner links introduced and up; ready 0.67-1.06 s; 10-s probes 7,200/7,200, 0 loss | connects < 3 s | **PASS** on loopback, VERIFIED (`t1c_2p`, `t1c_4p`). Behaviour behind real NATs: HYPOTHESIS (T3) |
| T1d | Reply code pasted 5 s, 45 s, 180 s late, host's direct dial disabled (`--test-no-direct-dial`) | Connected in all three: 26.2 / 23.2 / 21.8 ms after the paste as seen by the harness; the host's agent connected 0.55 / 0.53 / 0.71 ms after it was created. The joiner's agent failed at 39.53-39.58 s after each start (libjuice's 39.5 s timer) and was re-created on the same socket with the same credentials: 0 / 1 / 4 failures before the paste. One ICE socket (`@listen 45401` once) and one reply code for the whole wait | connects in all three; public candidate unchanged | **PASS** (connects), VERIFIED (`t1d_5s`, `t1d_45s`, `t1d_180s`). "Public candidate unchanged": **BLOCKED** on this PC (no STUN allowed); only "same local socket and port" is verified |
| T1e | Joiner pair 1-2 blocked by `--test-block-peer` on both sides; lockstep simulator 60 s (658-byte packets, 60/s) then probes 60 s | Pair 1-2 went through the host the whole time, including across the blocked agents' failures and re-creations at 39.5 / 79.2 / 118.7 s. Simulator: 3,600/3,600 packets each way on every stream, 0 loss, 0 stall, 0 source-check rejections. Probes 1->2 and 2->1: 3,600/3,600 each, all via the host. Added delay: echo RTT p50 0.228 / 0.225 ms through the host vs 0.089-0.120 ms on direct joiner-joiner pairs (**about +0.12 ms RTT**), p99 0.406 vs <= 0.243 ms | uses the host; delay about one extra loopback leg | **PASS**, VERIFIED (`t1e/summary.json`) |
| SIM | Lockstep simulator through 4 helpers vs. the same simulator endpoint-to-endpoint (plain UDP, like today's W4P on one PC), 60 s each | Through helpers: 43,200/43,200 packets, 0 loss, 0 stall, 0 rejected; one-way latency p50 0.171 / p95 0.289 / p99 0.347 / max 0.778 ms. Plain UDP: p50 0.109 / p95 0.230 / p99 0.308 / max 0.918 ms. **The helpers add about 0.06 ms median one-way** on this PC. Helper bridge counters: each helper 10,803 datagrams from and 10,803 to its endpoint, 0 dropped | (no criterion; T1f compares real emulators) | VERIFIED (`sim/summary.json`), SINGLE-PC, Python scheduling included in both runs |
| SEC | Section 5 basics: another session's joiner dials our host; foreign and mistyped reply codes; loopback stranger; mistyped join code | Foreign joiner (other session's secret, aimed at our port) never connected; host rejected its checks 4 times ("joiner of another session rejected"), created no link. Foreign reply code refused ("belongs to another game"); mistyped reply code refused (checksum). 10 datagrams from a loopback stranger to a slot port counted and dropped (0 forwarded). Mistyped join code: helper exits with code 3 and "incomplete or mistyped" | (design 5.1) | VERIFIED (`sec/summary.json`, `sec/h0_connection-log.txt`) |
| local4 | T1f launcher check: `local4.py` (T1f ports) driven by the simulator for 20 s | 14,400/14,400 packets, 0 stall, 0 rejected; stop file stops the helpers cleanly; no `w4p-net.exe` left running | (setup check) | VERIFIED (`local4/local4_summary.json`, `local4/sim_through_local4.json`) |

Sizes measured by T1a (`t1a_output.txt`): join code with 1 LAN + 1 public IPv4 candidate: 29 bytes, **61 characters**
(design estimate 58); reply code 28 bytes, 58 characters; join code + 1 IPv6: 48 bytes, 97 characters (estimate 109).
The extra length byte and the dash grouping are what make deletions always detectable (below).

---

## What was built (VERIFIED by the code in `net/w4p-net/src/`, tested as above)

- **One process per PC**, one UDP socket for all ICE links (libjuice MUX mode, fixed port, default 41500). A
  `juice_mux_listen` listener is registered at start: it keeps the socket open while agents are re-created (libjuice
  releases a MUX registry only when it has no agents and no listener, `conn.c release_registry`,
  `conn_mux.c conn_mux_can_release_registry`) and it receives checks with unknown credentials (path b).
- **Codes:** `src/codec.cpp`. Record = version/kind, length byte, secret (join) or 4-byte session tag + 40-bit nonce
  (reply), candidates (type, family, address, port), CRC-16/CCITT-FALSE. Text = `W4P1-` + Crockford base32 in groups of
  5. The parser finds the code in pasted text, accepts lower case and I/L/O aliases and whitespace around dashes,
  requires full groups of 5 and reads exactly the number of symbols given by the length byte. Why every single error is
  caught: a substitution or a swap of two symbols is an error burst of at most 10 bits, which CRC-16 always detects; a
  deletion either breaks a group of 5, or shortens the code below the length given by the length byte; an error in the
  length byte changes the expected symbol count, which the group structure or the "code must end here" check catches.
  T1a confirms it on 10,000 codes.
- **Credentials:** ufrag/pwd per link derived with SipHash-2-4 as a PRF from the 80-bit secret and the joiner nonce
  (host-joiner) or a pair nonce chosen by the host (joiner-joiner). Joiner ufrag = `J` + nonce (8 symbols); the host
  accepts a direct dial only if the requested host ufrag equals the one derived from its secret and that nonce.
- **Path (b) and path (a) give the same agent:** the listener callback only queues the request; the main thread creates
  the agent (never inside a libjuice callback). If the reply code arrives for an existing direct-dial agent that is not
  connected yet, the agent is restarted with the candidates from the code.
- **Roles:** host controlling for host-joiner links, lower slot controlling for joiner-joiner links (gather before or
  after setting the remote description, `agent.c agent_gather_candidates` / `agent_set_remote_description`).
- **Re-create loop:** a FAILED agent is re-created with the same socket, credentials and remote description while
  within `--connect-minutes` (default 10) of the first start (or of the loss, after a connection was lost).
- **Mesh with forwarding:** the host introduces every pair of welcomed joiners (candidates from their HELLO, pair nonce,
  resent every 250 ms until both acknowledge). A datagram goes direct if the pair link is connected, otherwise to the
  host with the final destination slot; the host verifies it, re-signs it with the destination link's key and sends it
  on (inside libjuice's receive callback: in MUX mode `juice_send` takes only the registry's `send_mutex`, which the
  receive path does not hold, `conn_mux.c conn_mux_send` / `conn_mux_process`).
- **Envelope:** 20 bytes (type, source slot, destination slot, flags, 8-byte session tag, 8-byte SipHash-2-4 MAC with a
  per-link key). Dropped without reply: wrong tag, wrong MAC, source slot not allowed on that link. Bridge: only the
  configured emulator port on 127.0.0.1 may send into the slot ports. A W4P input packet (658 bytes) becomes a 678-byte
  ICE datagram (design estimate: 16-20 bytes of envelope).
- **Emulator side:** helper slot ports `B..B+3` on 127.0.0.1; datagrams from slot p are delivered to the emulator from
  port `B+p`, so W4P's `from == cfg.peers[h.slot]` check (W4P.cpp l.837) identifies forwarded datagrams correctly. The
  simulator applies the same rule and rejected 0 datagrams in every run.
- **Logs:** `connection-log.txt` with candidate classes and ports (IP addresses never written; libjuice log lines are
  masked, including a libjuice WARN line that would print an ICE password), ICE state changes with times, selected pair,
  ping RTT and probe RTT histograms, loss, bytes per link, rejected datagrams. The codes are printed on stdout only.

---

## Negative results, limits and things that did not work

1. **Nothing was tested beyond one PC.** No STUN/srflx candidate, no NAT, no LAN, no internet, no IPv6 address, no
   firewall rule. Whether path (b) works behind home routers (it needs a host reachable without sending first),
   whether hole punching works, and the success rate per pair remain HYPOTHESIS (T2/T3).
2. **T1d "public candidate unchanged across re-creations" could not be tested** (BLOCKED: no STUN allowed in this task).
   What is verified is that the same socket and port are kept for the whole wait (one listen event; libjuice code).
3. **Path (b) costs about 0.5 s:** the joiner's first check only wakes the host's listener (libjuice drops that
   datagram after the callback, `conn_mux.c lookup_agent` returns NULL); the connection comes with the retransmission
   500 ms later. Expected by the design; measured 502-510 ms.
4. **A failed joiner pair is shown as "through the host" only after its first agent fails (about 39.5 s).** Data already
   goes through the host from the first moment (the route falls back to the host whenever the direct link is not
   connected), but the lobby's "ready" waits for the failure, so a real failed pair would delay the lobby by about 40 s.
   With the test switch the pair is marked at once. Possible fix: mark a pair "through the host" after a shorter
   timeout (for example 10 s) while the direct attempt continues.
5. **Not exercised:** the 10-minute give-up path (`gave_up`), reconnection after a lost link (T1g), the `lock` command,
   3-player sessions, packet loss or delay (no impairment was simulated), long runs (longest helper run here: about
   3 minutes, T1d 180 s), helper behaviour when an emulator sends more than 3,980 bytes (dropped by design; W4P's largest packet
   is a relay packet of at most 64 inputs, about 1.3 KB, W4P.cpp l.667).
6. **Windows Firewall:** all sockets were bound to 127.0.0.1 (logs say "bind loopback"), which should not raise a
   firewall prompt; whether a prompt appeared on screen cannot be seen from this session. No firewall setting was
   changed.
7. **Host "ready" lags by up to about 1 s** (joiners report their links every second). Cosmetic for the lobby.
8. **MSVC and libjuice atomics (design note 3.3, HYPOTHESIS there): false.** MSVC 19.51 in C11 mode (`-std:c11`, set by
   libjuice's CMake) defines `__STDC_NO_ATOMICS__`, so libjuice's `src/thread.h` uses its `volatile` fallback, not
   `<stdatomic.h>`. Checked with a probe compile (`/std:c11`: `__STDC_VERSION__=201112`, `__STDC_NO_ATOMICS__`
   defined). libjuice's own comment says only atomic loads/stores are needed; on x64 with MSVC's default `/volatile:ms`
   this is HYPOTHESIS-safe. Option: add `/experimental:c11atomics` for libjuice (build flag only, no source change).
9. **Latency numbers are loopback numbers.** They show the helper's own overhead (about 0.06 ms one-way median, about
   +0.12 ms RTT for forwarding), not network latency. The simulator runs all 4 endpoints in one Python thread, so its
   absolute numbers include Python scheduling (both helper and plain runs).
10. **Problems met while building and fixed** (for the record): `build.ps1` first lost vcvars' PATH (cmd expands
    `%PATH%` before `vcvars64.bat` runs; fixed with full tool paths) and wrote a UTF-16 log (fixed: cmd redirects);
    `SIO_UDP_CONNRESET` was not declared with `WIN32_LEAN_AND_MEAN` (defined locally); the first 4-player harness run
    failed because the `@stats` line was cut at a 2,048-byte print buffer (fixed: dynamic buffers). One cosmetic
    harness error (writing "quit" to an already-exited process) was fixed.
11. **Licence of our code** is marked GPL-3.0-or-later like W4P; the user's choice is still open (STAGE1_PLAN 14).

---

## T1f: what the coordinator must do (real emulators through the helpers)

Goal (design note T1f): 4 instances in lockstep through the helpers (m2_run4 style, 10 min), then with impairment;
compare hash points, mismatches, stall % and maximum stall with a plain-UDP run of the same setup.

**1. Start the helpers first** (they bind only 127.0.0.1; no STUN; 4 helpers on this PC):

```
python -I net/w4p-net/tests/local4.py --stop-file local/m5/stop_helpers
```

(or `--seconds <run length + 120>`). Wait for the line `HELPERS READY`. It checks that helper k got slot k. Ports used:
emulator ListenPort 46000-46003, helper slot ports 46100-46103 / 46110-46113 / 46120-46123 / 46130-46133, ICE ports
46400-46403. If the emulators must keep m2_run4's ListenPorts 41200-41203, start the helpers with
`--emu-ports 41200,41201,41202,41203` instead and keep the ListenPort lines below at 41200+k.

**2. Each emulator's [W4P] lines** (instance k = slot k; with the defaults above; `local4.py` also writes them to
`net/w4p-net/build/results/local4/inst<k>_w4p_lines.txt`):

```
; slot 0 (host)                    ; slot 1                           ; slot 2                           ; slot 3
LocalSlot = 0                      LocalSlot = 1                      LocalSlot = 2                      LocalSlot = 3
BindAddress = 127.0.0.1            BindAddress = 127.0.0.1            BindAddress = 127.0.0.1            BindAddress = 127.0.0.1
ListenPort = 46000                 ListenPort = 46001                 ListenPort = 46002                 ListenPort = 46003
Peer1 = 127.0.0.1:46101            Peer0 = 127.0.0.1:46110            Peer0 = 127.0.0.1:46120            Peer0 = 127.0.0.1:46130
Peer2 = 127.0.0.1:46102            Peer2 = 127.0.0.1:46112            Peer1 = 127.0.0.1:46121            Peer1 = 127.0.0.1:46131
Peer3 = 127.0.0.1:46103            Peer3 = 127.0.0.1:46113            Peer3 = 127.0.0.1:46123            Peer2 = 127.0.0.1:46132
```

Rule: `ListenPort = <emu port of instance k>`, `Peer<p> = 127.0.0.1:<46100 + 10*k + p>` for every other slot p, own
`Peer<k>` empty or absent (W4P skips its own slot and ignores empty peers, W4P.cpp l.1311-1313 and l.420). All other
keys (`Enabled`, `Players = 4`, `PadForSlot*`, `InputDelay`, `HashInterval`, `LogFile`, `BotInput`, `CallAt`, ...)
stay as m2_run4 writes them.

**Important:** `tests/m2/m2_run4.py` writes `ListenPort = 41200+slot` and `Peer<o> = 127.0.0.1:41200+o` itself
(l.36, l.108-112). Appending replacement lines with `--w4p-slot<k> "Peer<o>=..."` does **not** work: the fork's INI
reader is multi-key (`INISettingsInterface.cpp` l.66 `m_ini(true, true)`, lookups through `m_ini.GetValue`, l.214) and SimpleIni
then returns the first value of a key (`3rdparty/simpleini/include/SimpleIni.h` l.920). VERIFIED (code reading). So m2_run4 needs a switch that writes
the helper Peer lines (and, if used, the 46000+k ListenPorts) instead of its own. I did not change m2_run4 (task rule).

**3. Launch order:** helpers (`HELPERS READY`) -> emulators in any order (W4P's hello handles the order; until an
emulator is up, the helper's datagrams to it are dropped by the OS, and W4P ignores the ICMP error, W4PTransport.cpp
`Receive`) -> run -> stop the helpers (`quit` in the local4 window, Enter, Ctrl+C, or create the stop file) -> collect
`net/w4p-net/build/results/local4/` (local4_summary.json: per helper datagrams from/to its emulator, without route,
forwarded through the host; connection logs; stats).

**4. Runs to compare:** (a) plain UDP, as today (m2_run4 unchanged); (b) the same tag settings through the helpers;
(c) `local4.py --block 1,2` (pair 1-2 forwarded by the host, both helpers get the switch); optionally
(d) `local4.py --direct-dial`. With impairment: W4P's own `ImpairLatencyMs/ImpairJitterMs/ImpairLoss` keys still work
(they wrap W4P's transport inside the emulator, before the helper). Expected (HYPOTHESIS from SIM/T1e): stall % within
noise of plain UDP, 0 mismatches, `emu_drop` and `data_no_route` 0 after the start.

---

## Proposed findings (for `docs/FINDINGS.md`; IDs to be assigned by the coordinator)

- w4p-net connects 2 and 4 helpers on one PC (loopback, no STUN), full mesh on attempt 1, 0 loss in 50,400 probe
  datagrams; VERIFIED (T1b).
- Direct dial (path b, join code only) works on loopback through `juice_mux_listen` with on-demand agents, about 0.5 s
  per joiner; VERIFIED SINGLE-PC (T1c); real NAT HYPOTHESIS.
- Re-create loop keeps a joiner dialable for at least 180 s with one socket and one reply code; libjuice's connectivity
  timer measured at 39.53-39.58 s; VERIFIED (T1d).
- Forwarding through the host keeps a blocked joiner pair fully connected, about +0.12 ms RTT on loopback; VERIFIED (T1e).
- Helper overhead about +0.06 ms one-way median on loopback with W4P-sized packets; VERIFIED SINGLE-PC (SIM).
- Codec detects every single-character substitution, deletion and adjacent swap (T1a); VERIFIED.
- MSVC C11 mode makes libjuice use its non-atomic `volatile` fallback; VERIFIED (probe compile); design note 3.3
  hypothesis superseded.
- Appending duplicate W4P ini keys does not override (multi-key INI, first value wins); VERIFIED (code reading).

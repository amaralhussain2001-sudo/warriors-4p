# w4p-net: connection helper for warriors-4p

`w4p-net` is the small helper program from the M5 connection design (`docs/research/m5_connection_design.md`,
option S). It makes the connections between the players' PCs (ICE through libjuice, join codes, mesh with forwarding
through the host) and carries the emulators' datagrams. The emulator keeps its tested loopback UDP transport: W4P sends
to `Peer<p> = 127.0.0.1:<helper port for slot p>` and the helper delivers datagrams from slot p out of that same port,
so W4P's existing source check (`from == Peer<slot>`) still identifies the sender.

**Status (2026-10-11):** tested on one PC only (loopback, no STUN), see `docs/research/m5_w4pnet_results.md`.
Not yet tested with real emulators (T1f), on a LAN (T2) or over the internet (T3/T4). Nothing here shows that it works
between real homes.

## Build

```
powershell -File net\w4p-net\build.ps1
```

- Uses the already-installed Visual Studio Build Tools (found with `vswhere`, set up with `vcvars64.bat`) and the
  CMake and Ninja that come with them. Nothing is installed.
- Output: `net\w4p-net\build\w4p-net.exe` and `net\w4p-net\build\w4p-net-codec-test.exe`; log
  `net\w4p-net\build\build_Release.log`. `build\` is ignored by git (`net/w4p-net/.gitignore`).
- Tested toolchain: MSVC 19.51.36257 (14.51.36231), CMake 4.3.1-msvc1, Ninja 1.13.2 (VS Build Tools 18).
- libjuice is built from `third_party/libjuice` with `NO_TESTS=ON`, `NO_SERVER=ON`, `BUILD_SHARED_LIBS=OFF`
  (set from our CMakeLists; libjuice files are not changed).

## Run

Host (prints a join code):

```
w4p-net host --players 4
```

Friend (prints a reply code; it is only needed if the friend is not connected after about 10 seconds):

```
w4p-net join W4P1-24B78-SJYMR-...
```

The joiner accepts the code inside any pasted text. While running, each helper reads lines from stdin: a reply code
(host: the "Paste a reply" step), `status`, `probe RATE SIZE SECONDS` (test traffic), `lock` (host: no new players),
`quit`. Closing stdin also quits.

Options (all have defaults for a real game; `w4p-net --help` lists them):

| Option | Default | Meaning |
|---|---|---|
| `--players N` | 4 | host: 2..4 players |
| `--ice-port P` | 41500 | UDP port for all connections (one socket, libjuice MUX mode); tries P..P+19 if busy |
| `--bind ADDR` | all interfaces | bind the ICE socket; tests use `127.0.0.1` (no firewall prompt, loopback candidates) |
| `--stun HOST:PORT` | `stun.cloudflare.com:3478` | STUN server to learn the public address |
| `--no-stun` | | contact no STUN server (host candidates only; all single-PC tests use this) |
| `--emu-port P` | 41000 | the emulator's W4P `ListenPort` (on 127.0.0.1) |
| `--slot-ports B` | 41100 | helper loopback ports B..B+3; W4P `Peer<p> = 127.0.0.1:B+p` |
| `--want-slot N` | any | joiner: ask for slot N (1..3) |
| `--log FILE` | `connection-log.txt` | connection log (see below) |
| `--stats FILE` | | final counters as JSON |
| `--connect-minutes M` | 10 | keep re-creating a failed connection attempt this long |
| `--max-seconds S` | | exit after S seconds |
| `--no-stdin`, `--verbose` | | no stdin commands; libjuice debug messages in the log |
| `--test-no-direct-dial` | | TEST: host ignores direct dial-in (forces reply codes) |
| `--test-block-peer N` | | TEST: no direct link to slot N, traffic goes through the host (give it on both sides) |

Machine-readable lines on stdout start with `@` (for the launcher): `@listen <port>`, `@code join|reply <code>`,
`@path a|b <slot>`, `@joined <slot> <path> <ms>`, `@slot <n>`, `@link <peer> connected <ms> <attempt> <path>`,
`@link <peer> failed <attempt>`, `@link <peer> gave_up`, `@ready <ms>`, `@notready`, `@probe_done`, `@left <slot>`,
`@host_left`, `@error ...`, `@stats {json}`, `@bye`.

### Emulator settings (w4p.ini) for one PC per player

```
[W4P]
Enabled = true
Players = 4
LocalSlot = <slot printed by the helper: @slot n; the host is 0>
BindAddress = 127.0.0.1
ListenPort = 41000
Peer0 = 127.0.0.1:41100
Peer1 = 127.0.0.1:41101
Peer2 = 127.0.0.1:41102
Peer3 = 127.0.0.1:41103
```

(The own slot's `Peer` line is ignored by W4P; it may be empty.) Start the helper first, wait until it is ready, then
start the emulator.

## Tests (single PC; no STUN, loopback only)

```
net\w4p-net\build\w4p-net-codec-test.exe 10000              T1a: code codec
python -I net/w4p-net/tests/run_t1.py t1b --players 2        T1b: 2 helpers, 200-byte probes at 60/s for 60 s
python -I net/w4p-net/tests/run_t1.py t1b --players 4        T1b: 4 helpers, full mesh (6 pairs)
python -I net/w4p-net/tests/run_t1.py t1c --players 4        T1c: join code only (direct dial, path b)
python -I net/w4p-net/tests/run_t1.py t1d --delay 45         T1d: reply code pasted 45 s late (also 5, 180)
python -I net/w4p-net/tests/run_t1.py t1e                    T1e: joiner pair 1-2 blocked, forwarded by the host
python -I net/w4p-net/tests/run_t1.py sim                    lockstep simulator through helpers + plain UDP
python -I net/w4p-net/tests/run_t1.py sec                    strangers / other sessions / mistyped codes
python -I net/w4p-net/tests/local4.py                        T1f setup: 4 helpers + the 4 emulators' ini lines
```

Results go to `net/w4p-net/build/results/<test>/` (summary.json, each helper's stdout, connection log and stats).
`tests/lockstep_sim.py` is the 4-endpoint W4P stand-in (658-byte packets at 60/s, 32-input redundancy, resend every
15 ms while stalled, W4P's source-address check); it can also be run alone (`--plain-base` or `--emu-ports` +
`--slot-bases`).

## How it works (short)

- **One UDP socket** per helper (libjuice MUX mode, fixed port). A `juice_mux_listen` listener keeps the socket open
  while agents are re-created and receives connectivity checks for unknown credentials.
- **Join code** (`W4P1-` + Crockford base32, dash every 5 symbols): 80-bit session secret + the host's candidates +
  length byte + CRC-16. **Reply code:** 4-byte session tag + 40-bit joiner nonce + the joiner's candidates. ICE
  ufrag/pwd for each link are derived from the secret and nonces with SipHash-2-4 (so they are not in the codes).
- **Path (b), direct dial:** the joiner starts checks to the host's candidates at once. The host's listener sees the
  check, verifies that the requested host ufrag is the one derived from this session's secret and the nonce in the
  joiner's ufrag, and creates the agent on its main thread. **Path (a):** the host pastes the reply code and creates the
  same agent from it. Whichever comes first wins.
- **Re-create loop:** an agent that fails before connecting (libjuice gives up after 39.5 s) is re-created with the same
  socket, credentials and remote description, for `--connect-minutes` (default 10). A lost connection is re-dialled the
  same way.
- **Mesh:** when two joiners are connected to the host, the host sends both an introduction (the other's candidates and
  a pair nonce); the lower slot is controlling. Datagrams go direct when the pair is connected, else through the host
  (the host checks and re-signs them).
- **Envelope** (20 bytes): type, source slot, destination slot, flags, 8-byte session tag, payload, 8-byte SipHash-2-4
  MAC with a per-link key. Datagrams with a wrong tag, MAC or source slot are dropped without reply. Only the local
  emulator's port may use the loopback bridge. There is no encryption (inputs are not secret).
- **connection-log.txt:** candidate types/families/address classes and ports (never IP addresses: libjuice messages are
  masked too), ICE state changes with times, selected pair, ping RTT and probe RTT histograms, loss, bytes per link,
  rejected datagrams. The codes (which contain the secret and IP addresses) are printed on stdout only, never logged.

Privacy: the join code contains the host's addresses; share it only with the friends who play.

## Third-party: libjuice v1.7.4 (unmodified)

| Item | Source | Version | License | SHA-256 |
|---|---|---|---|---|
| libjuice source archive (`third_party/libjuice/`, extracted unmodified, 81 files incl. `LICENSE`) | https://github.com/paullouisageneau/libjuice/archive/refs/tags/v1.7.4.tar.gz (served from `codeload.github.com`, downloaded 2026-10-11) | tag v1.7.4, commit `b89c792e3612faf2f12cf35bcc56857313a06be3` (from the archive's pax header) | MPL-2.0 (`third_party/libjuice/LICENSE`) | `95c088862aa1b88b73d62aa99577135010eb768fcafb252d13aa85a8515ef798` (archive, 108,422 bytes) |

- The archive was downloaded into an empty directory, its file list was checked (81 files: sources, headers, tests,
  fuzzer, CMake files, LICENSE, README), and the extracted tree was copied without changes; per-file SHA-256 of the copy
  matched the extracted tree. GitHub does not guarantee byte-identical archives over time; the commit hash is the
  stable reference.
- `grep -r "Incompatible With Secondary"` finds only the MPL-2.0 text in `LICENSE` (Exhibit B template); no source file
  carries an Exhibit B notice.
- The sources carry "Copyright (c) 2020-2022 Paul-Louis Ageneau" (e.g. `include/juice/juice.h`) and the MPL-2.0
  Exhibit A notice.
- Build note: with MSVC 19.51 in C11 mode (`-std:c11`, as libjuice's CMake sets it), `__STDC_NO_ATOMICS__` is defined,
  so libjuice's `src/thread.h` uses its `volatile` fallback instead of `<stdatomic.h>` (checked with a probe compile).

## Licence

Our files in `src/` and `tests/` are marked GPL-3.0-or-later like the W4P code; the final choice is the user's
(STAGE1_PLAN section 14). libjuice stays under MPL-2.0; a package must include its licence and say where its source is
(design note section 3.6). The default STUN server is Cloudflare's (`stun.cloudflare.com:3478`); the single-PC tests
never contact it.

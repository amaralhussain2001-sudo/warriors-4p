# M5 connection design: signaling, topology, libjuice, fallbacks, security, tests

Date: 2026-10-11. Status: **research and design only.** Nothing here was built, run or tested. No emulator, test runner
or network service was used; the only network access was reading documentation web pages (all accessed 2026-10-11
unless a source says otherwise). Every claim about what will work on real networks is a HYPOTHESIS until the tests in
section 6 have run. Fits `docs/plan/M5.md` criteria 3 and 8 and decision D5.

Labels (CLAUDE.md): **VERIFIED** (pointer given), **HYPOTHESIS** (how to confirm is given, usually a test in section 6),
**BLOCKED**. Computed numbers (sizes, bit rates, budgets) are arithmetic from the stated inputs; they are labelled
HYPOTHESIS until measured, because real packets and networks may differ. Web sources are `[Cn]` (list at the end).
Code pointers refer to `emulator/pcsx2/pcsx2/W4P/W4P.cpp` as of 2026-10-11 20:13 (build tag `w4p-m5-1`, protocol 3);
that file is being changed by the disconnect-handling work, so line numbers may move.

---

## Recommendation (plain English)

**What we build:** a small helper program, `w4p-net`, that the launcher starts before the game. It makes the internet
connections (ICE through the libjuice library, with Cloudflare's free STUN server to learn each PC's public address)
and carries the button presses between the PCs. The emulator stays as tested: it only talks to the helper on the same
PC. Nobody needs an account, nothing costs money, no server of ours is needed.

**What players do (4 players; 2 or 3 work the same way):**
1. Everyone unzips the same package and double-clicks Start-Coop (the first time: pick your game file and BIOS, as today).
2. The host chooses **Host a game**. The window shows a **join code** such as `W4P1-7KQ2M-9XD4T-...` (about 60-110
   letters and digits, already copied). The host pastes it into the group chat (WhatsApp, Discord, ...).
3. Each friend chooses **Join a game**, copies the join code from the chat and presses Enter (the launcher finds the
   code even if other text was copied with it).
4. Wait about 10 seconds. Often the friend's window already says **"Connected to the host"**: go to step 6.
5. If not, the friend's window shows a **reply code** (already copied). The friend pastes it into the chat; the host
   copies it and chooses **Paste a reply**. Both windows keep trying for 10 minutes, so nobody has to hurry.
6. The host's window lists every player: slot (Player 1-4), connection speed in milliseconds, and any problem
   (different package version, wrong game file). The friends' PCs then connect to each other by themselves; nobody
   types more codes. If two friends cannot reach each other directly, their button presses go through the host
   automatically (a little slower).
7. The host chooses 60 fps and widescreen once for everybody. The launcher chooses the input delay from the measured
   connection speeds and shows it (for example "input delay 2 frames = 33 ms").
8. The host presses **Start**; every PC starts the game.
9. If someone cannot connect at all, their window says in plain words what to try (section 4.3). The backup is a free
   virtual LAN program (Radmin VPN). Our own relay server (about $4-6 per month, needs your approval, D5-B) only if the
   tests with your friends show that it is needed.
- Same house: **Join by IP address** stays, exactly as in today's 2-player test package.

**Why this way:** one code for the whole group; reply codes only when a router needs them; direct links between all
PCs keep the input delay lowest at 60 fps (routing everything through the host would add 1-3 frames, section 2);
no account, server or payment; the tested emulator code does not change.

**Decisions for you** (details at the end): (A) helper program vs. networking inside the emulator (recommend: helper);
(B) automatic router port opening (UPnP) changes the friends' router settings, so it stays off unless you say yes
(recommend: off for now); (C) a free public message service (ntfy.sh) could remove step 5, but every player would be
using a third party's service under its terms (recommend: not now); (D) the internet test with friends needs your
go-ahead and their time.

---

## 1. Signaling without a server

### 1.1 The problem
- ICE needs each side's credentials (ufrag, pwd) and address candidates; RFC 8445 says the exchange "typically" goes
  "through a signaling server" and leaves it outside ICE [C22]. VERIFIED.
- Most home NATs drop a packet from a peer until the PC behind them has sent to that peer first ("Address-Dependent"
  or "Address and Port-Dependent Filtering"; only "Endpoint-Independent Filtering" lets unknown senders in)
  [C19 section 5]. So normally both sides must send to each other, which needs both sides' addresses before the checks.
  VERIFIED (definitions); which filtering the friends' routers use is HYPOTHESIS (test T3).
- Hole punching works only through NATs with Endpoint-Independent Mapping (EIM); RFC 5128 cites a 2005 study in which
  UDP hole punching worked on "more than 80%" of NAT devices and notes that "a substantial fraction" use
  Endpoint-Dependent Mapping [C20]. RFC 4787 makes EIM a MUST (REQ-1) and recommends Endpoint-Independent Filtering
  (REQ-8) [C19]; carrier-grade NATs must follow RFC 4787 (RFC 6888 REQ-1) and should use endpoint-independent filtering
  (REQ-7) [C21]. VERIFIED (texts). Shares on today's networks: no primary measurement found; a 2026 blog cites a 2017
  study with "up to 17.7%" of WebRTC sessions going through a TURN relay [C23]. HYPOTHESIS: roughly 1 in 10 to 1 in 5
  player pairs may fail a direct connection on ordinary home and mobile connections (T3 measures it).

### 1.2 Options compared (2-4 players)

| | How the host gets each joiner's description | Works when | Steps for 4 players | Cost / approval | Label |
|---|---|---|---|---|---|
| **(a) Two-way codes** | Joiner sends a reply code back through any chat | Both NATs keep one public port per local port (EIM), any filtering. Fails if a side has Endpoint-Dependent ("symmetric") mapping, unless the other side's filtering is not port-dependent (peer-reflexive discovery) | Host: 1 copy + up to 3 pastes. Each joiner: 1 paste + 1 copy | None | Mechanism VERIFIED [C19,C20,C22]; the symmetric-NAT exception and the success rate HYPOTHESIS (T3) |
| **(b) Joiner dials the host directly** (one-way code) | From the joiner's first connectivity check (STUN USERNAME + source address) | The host can be reached without sending first: Endpoint-Independent ("full cone") filtering, a public IPv4, a manual port forward, a UPnP/PCP mapping, or IPv6 without an inbound firewall | Host: 1 copy. Each joiner: 1 paste | None (UPnP would change router settings: needs approval) | libjuice API VERIFIED [C1,C10]; this use is not covered by libjuice's own tests [C13]: HYPOTHESIS (T1c) |
| **(c) Free public rendezvous** | Both launchers post to a public message service under a topic derived from the code | Service up and not rate-limited | Host: 1 copy. Each joiner: 1 paste | Third-party terms; every player's PC uses the service | Terms VERIFIED (below); behaviour HYPOTHESIS |
| **(d) Own server (D5-B)** | Our small server maps a short code to a session, passes descriptions, and relays (TURN) when direct fails | Always, if outbound UDP or TCP 443 is allowed (HYPOTHESIS) | Host: 1 copy of a 6-character code. Joiners: 1 paste | VPS from about $4-6/month (quoted 2026-10-10 in `transport_options.md` B3, not re-checked); account, payment, upkeep; **user approval** | Prices VERIFIED 2026-10-10; behaviour HYPOTHESIS |

Details:
- **(a) Timing trap (important).** libjuice arms a connectivity timer of 39.5 s (`ICE_PAC_TIMEOUT 39500`, agent.h [C7])
  once the remote description is set and local gathering is done; on expiry the agent goes to `JUICE_STATE_FAILED` and
  clears the selected pair, so it can no longer send (agent.c [C8]). A FAILED agent still answers incoming binding
  requests (`agent_input` returns early only in DISCONNECTED/GATHERING [C8]). VERIFIED (source). With codes passed
  through a chat, the side that pastes first may wait longer than 39.5 s for the other. **Design:** the helper keeps
  the same local UDP port and the same ICE credentials (`juice_set_local_ice_attributes`: must be called before
  gathering, ufrag >= 4 and pwd >= 22 characters [C8]) and recreates the agent with the same remote description
  whenever it fails before connecting, for up to 10 minutes. HYPOTHESIS: on an EIM NAT the public address stays the same
  across recreations because the local port is the same and the mapping is refreshed within seconds (T1d, T3).
- **(b) libjuice support.** In MUX mode all agents share one UDP socket and one thread; an incoming datagram is routed
  by source address, else (STUN binding request) by the **local ufrag** in USERNAME; if no agent matches and a listener
  is registered, the `juice_mux_listen` callback gets local ufrag, remote ufrag, address and port; non-STUN datagrams
  from unknown sources are dropped (conn_mux.c [C10], juice.h [C1]). VERIFIED. The same "server learns the client from
  the STUN USERNAME" pattern is the libp2p WebRTC-Direct spec, which needs the server to be "publicly reachable" [C15];
  libdatachannel merged the matching hook on 2025-03-26 [C14]. VERIFIED. libjuice's own tests only check that the
  callback fires; none creates an agent on demand [C13]. Creating the host's agent from the callback is therefore
  HYPOTHESIS (prototype T1c; create it outside the callback thread; the joiner retransmits its check after >= 500 ms
  [C7]). Because MUX routes by local ufrag only, every host agent needs its own ufrag: derived per joiner (1.4).
- **(c) Public rendezvous services found:**
  - **ntfy.sh** (HTTP publish/subscribe): terms dated 2026-01-26: "You may use the Service without creating an
    account", free use "is subject to rate limits", service "best effort"; daily message limit on ntfy.sh 250; topic
    names are public, so the payload would have to be encrypted with a key from the code [C26]. VERIFIED (terms and
    limits text). The only service found with written terms that allow no-account use.
  - test.mosquitto.org: "please do not abuse or rely upon it for anything of importance" [C27]. Not suitable. VERIFIED.
  - HiveMQ public broker: "not intended for private or production data" [C28]. Not suitable. VERIFIED.
  - PeerJS Cloud: free, but no terms found; "For production, you can host your own" [C29]. Terms BLOCKED (none found).
  - Verdict: (c) is technically possible (HYPOTHESIS) but makes every player's PC a user of a third-party service; that
    is a terms decision for the user. Not needed if (a)+(b) work; keep it as a later convenience option.
- **(d)** is D5-B: only if T3 shows failures that (a)+(b) plus forwarding through the host cannot fix. libjuice has a
  TURN client (`juice_turn_server_t`) and a small STUN/TURN server (`juice_server_create`) [C1]; coturn is the
  alternative (`transport_options.md` B3). VERIFIED (API).

### 1.3 Recommended: (a) and (b) together, in one flow
1. Host helper: MUX mode on one fixed UDP port (`local_port_range_begin == local_port_range_end` binds exactly that
   port, udp.c [C12]); gathers its candidates once (host + server-reflexive from `stun.cloudflare.com:3478/UDP`, "free
   and unlimited" [C24,C25]); makes a random 80-bit session secret; shows the join code; calls `juice_mux_listen`.
2. Joiner helper: decodes the code, picks a random 40-bit nonce, derives both sides' ICE credentials from
   (secret, nonce), creates its agent, sets the host's description, gathers and starts checks at once (path b). It shows
   its reply code immediately with "if you are not connected in 10 seconds, send this to the host".
3. Host: a binding request with an unknown local ufrag reaches the listener callback; the host checks that this ufrag
   is the one derived from (secret, nonce carried in the joiner's ufrag) and, if a slot is free, creates the agent for
   that joiner (path b). If instead the host pastes the reply code, it creates the same agent from the code (path a).
   Both paths give the same agent and credentials, so it does not matter which one wins.
4. Joiner-to-joiner links: once joiners are connected to the host, the host gives each pair the other's candidates
   and a pair nonce over the existing links and tells both to start at the same moment (no 39.5 s problem). RFC 5128
   describes this: a connected peer "can in turn take over the role of 'introducer'" [C20]. VERIFIED (text).
5. Roles: libjuice takes the controlling role if gathering or the local description comes before the remote
   description, else controlled; conflicts are settled by the tie-breaker [C8]. Design: host controlling for
   host-joiner links, lower slot controlling for joiner-joiner links. VERIFIED (libjuice behaviour); our use HYPOTHESIS.

### 1.4 Code format: short and copy-safe
We do not send libjuice's text description; we send a binary record and rebuild the text on the other side
(`a=ice-ufrag:` / `a=ice-pwd:` / `a=candidate:<foundation> 1 UDP <priority> <ip> <port> typ host|srflx` /
`a=end-of-candidates`, format from ice.c [C5]; libjuice makes a 4-character ufrag and 22-character pwd by default [C5]).

| Field | Join code (host) | Reply code (joiner) |
|---|---|---|
| Format version + kind | 1 byte | 1 byte |
| Session secret / session tag + joiner nonce | 10 bytes (80-bit secret) | 4-byte session tag + 5-byte nonce |
| Candidate count | 1 byte | 1 byte |
| Each candidate | type+family 1 byte, IPv4 4 or IPv6 16 bytes, port 2 bytes | same |
| Checksum | CRC-16, 2 bytes | CRC-16, 2 bytes |

ICE ufrag/pwd are derived from secret and nonce (SipHash-2-4 used as a pseudorandom function [C30]), so they are not in
the code. Priorities are recomputed with libjuice's formula (type preference host 126 / srflx 100, family, index,
component [C5,C6]); HYPOTHESIS that a recomputed priority is good enough, else add 4 bytes per candidate.

Sizes (computed from the field table with a scratch script; HYPOTHESIS until the real codec exists):

| Candidates in the code | libjuice text | text + deflate, base64url | **Binary, base32** | Binary with `W4P1-` prefix and a dash every 5 |
|---|---|---|---|---|
| 1 LAN IPv4 + 1 public IPv4 | 222 B | 222 chars | **45 chars** (28 B) | 58 chars |
| + 1 VPN adapter IPv4 | 285 B | 240 chars | **56 chars** (35 B) | 72 chars |
| + 1 IPv6 | 371 B | 279 chars | **87 chars** (54 B) | 109 chars |

Reply codes are 1 byte shorter. Compressing the binary record does not help (40 random bytes deflate to 45).
- **Alphabet: Crockford base32**: digits and capital letters without I, L, O, U; decoding accepts lower case, reads
  i/l as 1 and o as 0, ignores hyphens [C31]. VERIFIED (spec). Not base64url: it is case-sensitive and uses `_` and `-`,
  and chat apps turn `_text_` into italics (community guide seen in search results only [C33]: HYPOTHESIS).
- **Checksum:** a CRC-16 detects every error burst of up to 16 bits, so every single wrong character (5 bits) is caught
  (standard CRC property; unit test T1a). Message: "This code is incomplete or mistyped. Copy it again."
- **Paste anywhere:** the launcher searches the pasted text for `W4P<digit>-` and reads the code after it, ignoring
  spaces and line breaks. The launcher copies codes to the clipboard itself (`Set-Clipboard` exists in Windows
  PowerShell 5.1 [C32]). VERIFIED (cmdlet).
- **Which candidates go in:** libjuice on Windows lists every adapter address (WSAIoctl `SIO_ADDRESS_LIST_QUERY`; only
  local addresses and duplicates are filtered, udp.c [C12]), so virtual adapters (Hyper-V, WSL, VPNs) appear too.
  VERIFIED. Our code keeps at most 3 IPv4 host candidates (default-route adapter first), 1 IPv6 host candidate and the
  server-reflexive ones. Leaving one out is not fatal: ICE still learns peer-reflexive addresses. HYPOTHESIS.
- **Privacy:** the join code contains the host's public IP address. Share it only with the friends (true of every
  direct-connection method). The code is useless once the host closes the lobby (new secret per session).

---

## 2. Topology

### 2.1 What the lockstep needs
Each instance runs poll t only when every player's input for t is present (`HaveAll`, W4P.cpp). Inputs are sampled
D polls ahead (`InputDelay`, default 2). For two instances with one-way latencies L1, L2 and poll period T, play without
stalls needs **L1 + L2 = RTT <= 2 x D x T**: if B runs s ms after A, A's input for poll k+D must reach B before B runs
k+D (s >= L1 - D x T) and B's must reach A in time (s <= D x T - L2). HYPOTHESIS (derivation; jitter and loss need
margin). Consistent with M1: 60 ms RTT, 10 ms jitter, 1 % loss at 30 polls/s with D = 2 (budget 133 ms) gave 0
mismatches and 0.74 s / 0.58 s of stalls in 5.3 min (`c2_impair_d2`, `docs/reports/M1_report.md`). VERIFIED (that run).

Poll rate: about 30 polls/s in 30 fps mode (M1 report) and 60 in 60 fps mode ("game reads the pad 60 times per
second", F-0100). VERIFIED.

| Polls/s | D = 1 | D = 2 (today) | D = 3 | D = 4 | D = 5 |
|---|---|---|---|---|---|
| 30 (T = 33 ms) | 67 ms | **133 ms** | 200 ms | 267 ms | 333 ms |
| 60 (T = 17 ms) | 33 ms | **67 ms** | 100 ms | 133 ms | 167 ms |

RTT budget 2 x D x T before jitter margin. HYPOTHESIS (computed).

### 2.2 Packet sizes today (from the code)
- `Input` is 20 bytes (`static_assert(sizeof(Input) == 20)`, W4P.cpp l.83); `PktHeader` is 12 bytes and `PktInputs`
  18 bytes (l.85-97); each input packet repeats the last `kResendBurst = 32` local inputs (l.58). In steady play an
  input packet is 18 + 32 x 20 = 658 bytes of UDP payload, 686 bytes with IPv4+UDP headers. It goes once per poll to
  every peer (`SendInputs` -> `SendToPeers`, l.414), every 15 ms while stalled (l.1139) and every 50 ms from vsync when
  no poll happened (l.1524). Hash packets (about 9 entries x 20 bytes every 30 polls) are small. VERIFIED (code).
- The helper adds an envelope (type, session tag, source/destination slot, 8-byte MAC): about 16-20 bytes.

Bit rate per stream (one sender to one receiver), HYPOTHESIS (computed, not measured):

| Input packet | On the wire | 30 polls/s | 60 polls/s |
|---|---|---|---|
| Today (32 inputs) | 686 B | 165 kbit/s | 329 kbit/s |
| Today + envelope | 702 B | 168 kbit/s | 337 kbit/s |
| Only unacknowledged inputs (about 8) + envelope (optional protocol change) | 222 B | 53 kbit/s | 107 kbit/s |

### 2.3 Mesh vs. star vs. mesh with forwarding

| 4 players | ICE pairs | Worst input path | Upload per PC at 60 polls/s with today's packets | Signaling |
|---|---|---|---|---|
| **Full mesh** (today's W4P) | 6 | direct (1 hop) | every PC 3 streams: **about 1.0 Mbit/s** up and down | host, plus joiner-joiner relayed by the host (1.3 step 4) |
| **Star through the host** | 3 | joiner -> host -> joiner (2 hops) | host 3 own + 6 forwarded: **about 3.0 Mbit/s** up; joiner 0.33 up / 1.0 down | host only |
| **Mesh with forwarding fallback (recommended)** | 3-6 | direct, 2 hops only for a pair that cannot connect | as mesh; host adds 2 streams per failed pair | as mesh |

With the optional acknowledged-window change: mesh about 0.32 Mbit/s per PC, star host about 0.96 Mbit/s.
HYPOTHESIS (computed).

Input delay needed, HYPOTHESIS (computed; host forwards on arrival in the helper's network thread - forwarding at its
own poll would add up to one poll period per direction; 15 ms jitter margin; D never below today's 2):

| RTT of every link (host<->joiner = joiner<->joiner) | Mesh, 60 polls/s | Star, 60 polls/s | Mesh, 30 | Star, 30 |
|---|---|---|---|---|
| 20 ms | D = 2 (33 ms) | D = 2 | D = 2 | D = 2 |
| 30 ms | D = 2 | **D = 3 (50 ms)** | D = 2 | D = 2 |
| 50 ms | D = 2 | **D = 4 (67 ms)** | D = 2 | D = 2 |
| 80 ms | D = 3 (50 ms) | **D = 6 (100 ms)** | D = 2 | D = 3 |

At 60 fps a star costs 1-3 extra frames of input delay for everyone at ordinary internet RTTs, and the host's upload
triples. A mesh needs 3 more ICE pairs and more signaling, which the host relays automatically.
**Recommendation: mesh, with automatic forwarding through the host for any pair whose direct link fails.** It keeps
W4P's per-slot packets unchanged (the disconnect handling in `m5_disconnect.md` relies on packets from every slot,
"gone" = nothing received for 2 s) and degrades to "star for that pair only". Note the name clash: W4P's `PktRelay`
(protocol 3) carries a leaving player's inputs; in this note "forwarding" means the host passing datagrams between two
joiners.

### 2.4 Choosing the input delay in the lobby
The helpers measure RTT on every link for about 3 s (ping messages, p95). The host picks
D = max(2, ceil((largest p95 RTT + 15 ms) / (2 x T))) and sends it with the session settings, so every PC writes the
same `InputDelay`; today W4P's hello only warns on screen when `input_delay` differs ("session options", `CompareHello`),
it does not refuse. VERIFIED (code) / HYPOTHESIS (formula, to be tuned with T3/T4 data). The lobby shows why
("Player 2 <-> Player 4: 78 ms, input delay 3 frames").

---

## 3. libjuice integration

### 3.1 Version to pin
- **v1.7.4**, published 2026-09-26 (GitHub releases API [C3]); CMake `project (libjuice VERSION 1.7.4 LANGUAGES C)`
  [C4]. Its notes include "keeping ICE timers running across system suspend" and bounds checking of the poll array
  (summary of [C3]). VERIFIED. When vendoring: record the tag's commit hash and the SHA-256 of the source archive in
  `docs/HASHES.md`; take only bug-fix updates later and re-run T1 after each.
- Facts used below: no required dependencies ("None!"; Nettle optional) [C2]; C11 (`set(CMAKE_C_STANDARD 11)`) [C4];
  Windows links `ws2_32` and `bcrypt` [C4]; options `NO_SERVER`, `NO_TESTS`, `BUILD_SHARED_LIBS`,
  `DISABLE_CONSENT_FRESHNESS`, `ENABLE_LOCALHOST_ADDRESS` [C4]; targets `juice` / `juice-static`, aliases
  `LibJuice::LibJuice` / `LibJuice::LibJuiceStatic`, `JUICE_STATIC` public define for static builds [C4]. VERIFIED.

### 3.2 Where the networking lives: helper process (recommended) or inside the emulator

| | **S: helper process `w4p-net` (recommended)** | F: inside the PCSX2 fork |
|---|---|---|
| Emulator changes | none for the transport: W4P keeps its UDP transport bound to 127.0.0.1 and `Peer{p} = 127.0.0.1:<helper port for slot p>` | new slot-addressed transport, libjuice project in the solution, lobby UI or file hand-shake with the launcher |
| Tested lockstep path | unchanged (same UDP code as M1-M2 runs) | changed (new transport under the lockstep) |
| Lobby (codes, slots, version check, RTT, input delay) | before the emulator boots | needs the emulator running, or a Qt dialog in the fork |
| Exposure | only the helper faces the internet; emulator stays on loopback (default `BindAddress` 127.0.0.1, W4P.cpp l.183) | the emulator socket faces the internet |
| Build | own small CMake project; `add_subdirectory(libjuice)` works as upstream intends | hand-written `libjuice.vcxproj` for the MSBuild solution plus CMake wiring |
| Cost | one more process; two loopback hops per datagram (HYPOTHESIS: tens of microseconds; measure in T1f) | none of these |
| Failure mode | helper crash = "Waiting for Player N" then the disconnect policy | emulator and network fail together |

The plan already puts the lobby in "a small launcher app" and the network behind an interface (STAGE1_PLAN section 7),
so S stays inside the approved architecture. Recommendation: **S**; keep F as the fallback if T1f shows the loopback
hop costs measurable stall time.

### 3.3 Build integration
- **S (recommended):** new folder `net/w4p-net/` (the repo's `net/` folder is empty today). CMakeLists with
  `set(NO_TESTS ON) set(NO_SERVER ON) set(BUILD_SHARED_LIBS OFF)`, `add_subdirectory(third_party/libjuice)`,
  `target_link_libraries(w4p-net PRIVATE LibJuice::LibJuiceStatic)`. Toolchain: CMake, Ninja and MSVC are already
  installed (F-0075, D2 correction in DECISIONS.md), so no new install. HYPOTHESIS that it builds cleanly with MSVC
  14.50 (libjuice lists MSVC as supported [C2]).
- **F (if chosen):** the fork builds with MSBuild from `PCSX2_qt.slnx` (`emulator/build.ps1`), W4P files are listed in
  `pcsx2/pcsx2.vcxproj` (l.373-374, 822-823) and `pcsx2/CMakeLists.txt` (l.100-101); 3rdparty libraries come as
  `3rdparty/<name>/<name>.vcxproj` StaticLibrary projects referenced from `pcsx2.vcxproj` (example `rcheevos`,
  l.1087) and as `add_subdirectory(3rdparty/<name> EXCLUDE_FROM_ALL)` in `cmake/SearchForStuff.cmake` (l.83, 88).
  VERIFIED (repo). Steps: `3rdparty/libjuice/` (unmodified source + LICENSE); `libjuice.vcxproj` with the C files of
  `LIBJUICE_SOURCES` [C4] and defines `JUICE_STATIC; JUICE_EXPORTS; NO_SERVER; USE_NETTLE=0; WIN32_LEAN_AND_MEAN;
  NOMINMAX; _CRT_SECURE_NO_WARNINGS` (+ `RELEASE=1` in Release) and `/utf-8` [C4]; C11 language mode, because
  `thread.h` uses `<stdatomic.h>` only when `__STDC_VERSION__ >= 201112L` and otherwise falls back to plain `volatile`
  [C11] (HYPOTHESIS: MSVC's C11 mode takes the stdatomic path without extra flags; check at the first compile); add
  `bcrypt.lib` (the common link list has `ws2_32.lib` and `iphlpapi.lib` but not bcrypt, `common/vsprops/common.props`
  l.65); solution entry in `PCSX2_qt.slnx`; CMake: `add_subdirectory(3rdparty/libjuice EXCLUDE_FROM_ALL)` and link
  `LibJuice::LibJuiceStatic`.

### 3.4 Threading model
- POLL mode (default): one "juice poll" thread per registry serves all agents; each agent has its own UDP socket;
  `agent_conn_recv` (and therefore `cb_recv`) runs on that thread inside the registry mutex; `juice_send` runs on the
  caller's thread and takes only that connection's send mutex (conn_poll.c [C9]). VERIFIED.
- MUX mode: one UDP socket and one "juice mux" thread per registry; agents asking for the same port share it
  (conn_mux.c [C10]). VERIFIED. The send path in MUX mode was not read: HYPOTHESIS that it is equally cheap.
- THREAD mode: one thread per agent [C1]. Windows mutexes in libjuice are kernel mutexes and recursive (thread.h [C11]).
  VERIFIED.
- Rules for our code: copy data out of `cb_recv` and return quickly; never block, never call `juice_destroy` inside a
  callback (HYPOTHESIS: deadlock risk, untested); create agents for path (b) on our own thread.
- **S:** helper threads = libjuice's MUX thread (receive: check MAC and session tag, then `sendto` the loopback socket
  of the sending slot, or `juice_send` to the destination agent when forwarding as host) + one bridge thread
  (`WSAPoll` on the per-slot loopback sockets, wrap, `juice_send`) + the console/lobby thread. Nothing is shared with
  the emulator process.
- **F:** the CPU thread calls `Send` (direct `juice_send`); `cb_recv` pushes {slot, bytes} into a bounded queue with a
  mutex and condition variable; `Receive(timeout)` waits on it (replacing `WSAPoll` in `UdpTransport::Receive`).

### 3.5 How it maps onto W4PTransport
- Today: `Transport::SendTo(const Endpoint&, ...)` and `Receive(..., Endpoint* from, timeout_ms)` with IPv4 endpoints
  (`W4PTransport.h` l.27-33); W4P accepts a datagram only if `from == cfg.peers[h.slot]` (W4P.cpp l.837). VERIFIED.
- **S:** no interface change. The helper owns one loopback socket per remote slot (for example 127.0.0.1:41101-41104);
  datagrams from slot p reach the emulator from that slot's socket, so the existing source check still identifies the
  slot, including forwarded ones. `w4p.ini` gets `BindAddress = 127.0.0.1`, `Peer<p> = 127.0.0.1:4110<p>`,
  `InputDelay = <lobby choice>`. HYPOTHESIS (design).
- **F:** ICE has no stable "endpoint" to compare, so the interface becomes slot-addressed:
  `bool Send(int slot, const void*, size_t)` and `int Receive(void*, size_t, int* slot, int timeout_ms)`. The UDP
  implementation maps slots to configured endpoints and keeps today's "configured address only" rule; the libjuice
  implementation has one agent per remote slot; `CreateImpairedTransport` wraps either. The check at l.837 becomes
  `from_slot == h.slot` (forwarded datagrams carry the origin slot in the helper envelope).

### 3.6 Licences (MPL-2.0 with GPL-3.0)
- libjuice is MPL-2.0 [C2]; the files read (juice.h, ice.c, ice.h, agent.h) carry the Exhibit A notice ("This Source
  Code Form is subject to the terms of the Mozilla Public License, v. 2.0") and no Exhibit B "Incompatible With
  Secondary Licenses" notice [C1,C5,C6,C7]. VERIFIED for those files; grep all files for "Incompatible With Secondary"
  when vendoring.
- MPL-2.0 section 3.3: a Larger Work may be distributed "under terms of Your choice" if the MPL requirements are met for
  the covered files; when combined with a Secondary License (GPL 2.0+, LGPL 2.1+, AGPL 3.0+, section 1.12) and not
  marked incompatible, the files may "additionally" be distributed under that licence [C16]. The FSF calls this
  "indirect compatibility" with the GNU GPL, with the condition that the MPL files "are still available under the MPL's
  terms as well" [C18]; Mozilla's FAQ says the same, and that changes to an MPL file must stay available under the MPL
  [C17]. VERIFIED (texts). So libjuice inside a GPL-3.0 PCSX2 build (option F) is allowed; with option S the helper is a
  separate program and the question does not arise for PCSX2 (HYPOTHESIS: separate programs talking over sockets are
  an aggregate; confirm in the M8 legal review).
- MPL section 3.2(a): with an executable, the source "must also be made available" and recipients must be told "how
  they can obtain a copy" [C16]. Section 3.4: license and copyright notices may not be removed [C16]. VERIFIED.
- **Package checklist** (`tools/make_package.py` builds `source/`, `COPYING.GPLv3`, `MANIFEST.txt` today, VERIFIED):
  1. `licenses/libjuice-LICENSE.txt` (the MPL-2.0 text from the libjuice repository).
  2. `THIRD-PARTY-NOTICES.txt`: libjuice v1.7.4, "Copyright (c) 2020-2022 Paul-Louis Ageneau" (header of juice.h [C1];
     copy each file's notice as found), MPL-2.0, upstream URL and tag, and where the copy in the package is.
  3. `source/`: the unmodified libjuice v1.7.4 source archive plus our `w4p-net` source and build steps (with F, the
     fork patch that adds `3rdparty/libjuice` already contains it).
  4. Do not modify libjuice files. If ever needed, the changed files stay MPL-2.0 and ship as source.
  5. README "Licence" section: name libjuice, MPL-2.0, where its source is; name Cloudflare STUN as the address-lookup
     service the helper contacts.
  6. Licence of our own `w4p-net` code: the user's choice per STAGE1_PLAN section 14 (GPL-3.0 like W4P is simplest).

---

## 4. Fallbacks and LAN

### 4.1 LAN
- Keep **Join by IP** as it is in the 2-player package (`package/Start-Coop.ps1`: `BindAddress = 0.0.0.0`,
  `Peer<n> = <other IP>:41000`), the path the E6 test uses. VERIFIED (script). On one PC it passed the package self-tests
  (F-0105, F-0122); the 2-PC result is pending (E6).
- ICE also covers a LAN by itself: host candidates on the same network are tried first. HYPOTHESIS (T2). Without
  internet, STUN gathering fails after its retries (`MAX_STUN_SERVER_RETRANSMISSION_COUNT 5`, "total 23500ms" [C7]); the
  helper should not wait for it: it issues the code after about 3 s with whatever candidates it has.

### 4.2 Overlay VPN fallback (D5-C)
- Radmin VPN (free, Windows only, network name + password, relays when direct fails), ZeroTier (free for 10 devices,
  network admin account), Tailscale (free for 6 users, every user logs in with an identity provider):
  `transport_options.md` B5 (accessed 2026-10-10). VERIFIED there; "no registration" for Radmin is HYPOTHESIS there.
- With ICE nothing special is needed: libjuice lists the VPN adapter's address as a host candidate (udp.c [C12]) and our
  code keeps up to 3 IPv4 host candidates, so "install the same VPN, join the same network, then use the codes as
  usual" should connect through the VPN. HYPOTHESIS (T2/T3). Join by IP with the VPN address also works the same way as
  on a LAN (HYPOTHESIS). Installing a VPN is a system-level install that each friend decides for himself.

### 4.3 Detecting failure and telling the user (plain English)
The helper logs ICE states with times and shows one message per situation:

| Situation (how detected) | Message | Suggested action |
|---|---|---|
| Code fails CRC or format | "This code is incomplete or mistyped." | Copy the whole code again (it starts with W4P1-). |
| Code version differs | "Your friend uses a different version of the co-op package." | Both use the same zip. |
| No server-reflexive candidate after about 5 s | "Could not reach the internet address service. Internet games may not work; games in the same house still do." | Check the internet connection; on a work or school network ask the owner; try Join by IP for the same house. |
| Joiner not connected after 10 s (path b failed) | "Send this reply code to the host." | Normal step 5, not an error. |
| Not connected 60 s after the host pasted the reply | "Could not connect directly to the host. This happens with some internet providers and with phone hotspots." | (1) Let another player host. (2) Check that Windows Firewall allows w4p-net. (3) Use the VPN way (README). (4) Send us `connection-log.txt`. |
| A joiner-joiner pair fails | Lobby shows "Player 2 <-> Player 4: through the host" and the chosen input delay | none |
| Windows sees the network as "Public" and has no allow rule for the helper (read-only check, nothing is changed) | "Windows Firewall may block the connection on this network." | Allow w4p-net when Windows asks. (Changing firewall settings for the user is not done automatically.) |
| RTT p95 above about 150 ms on a link | "Slow connection between Player x and Player y (180 ms). Input delay set to n frames." | Optional: let the best-connected player host. |
| Link lost during the game | W4P's own "Waiting for Player N" countdown (`m5_disconnect.md`) | Automatic re-dial (section 5.2). |

HYPOTHESIS: Windows Firewall lets UDP replies in after the program has sent to that address (stateful filtering), so
hole-punched links may work without an allow rule; unsolicited path (b) traffic needs one (T2/T3).

### 4.4 When to ask for D5-B (own relay)
Proposed trigger: after T3, if any friend cannot connect to the host by (a) or (b) on two different days, or more than
1 in 10 player pairs fail both directly and through the host, report to the user with the measured numbers and the
cost (VPS about $4-6 per month, `transport_options.md` B3; or Cloudflare Realtime TURN, which needs a Cloudflare account,
1,000 GB per month free then $0.05/GB, B4). HYPOTHESIS (threshold to agree with the user).

---

## 5. Security and robustness basics

### 5.1 Session, strangers, integrity, versions
- **Session tag:** 8 bytes derived from the session secret, in every helper envelope; datagrams with another tag are
  dropped (stale sessions, other games on the same port). HYPOTHESIS (design).
- **Strangers:** libjuice delivers application data only from addresses of known candidate pairs ("Received a datagram
  from unknown address, ignoring"; MUX: "Got non-STUN message from unknown source address") [C8,C10]. VERIFIED (source).
  Connectivity checks carry message integrity keyed with the ICE pwd (MUX routing looks at requests "with integrity"
  [C10]; the RFC 8445 short-term credential rules were not re-read here: HYPOTHESIS for the details). The host accepts at most
  players - 1 joiners and only while the lobby is open (M5 criterion 6).
- **Integrity:** an 8-byte SipHash-2-4 tag per envelope ("can also be used as a secure message authentication code",
  128-bit key, 64-bit tag; reference code under CC0, MIT or Apache-2.0 [C30]), keys derived per pair from the session
  secret and nonces. Cost: one hash over at most about 700 bytes per datagram (HYPOTHESIS: microseconds). VERIFIED
  (properties, licence). Anyone who has the join code can derive the keys; the code is the shared secret of the group.
- **Encryption:** not planned. Inputs are not secret; the join code (public IP) is the sensitive part and travels in
  the players' own chat. HYPOTHESIS that this is acceptable; revisit in the M8 review.
- **Replays:** harmless for inputs ("first value wins", `Store()`, W4P.cpp l.339) and stopped across sessions by the
  session tag. VERIFIED (code) / HYPOTHESIS (design).
- **No amplification:** the helper never answers an unauthenticated datagram with something larger. HYPOTHESIS (design).
- **Versions:** three layers: the code's format version (`W4P1`); the lobby hello before the emulator starts (package
  build, helper protocol, ISO check result, host's 60 fps / widescreen / input delay choice; a mismatch blocks Start);
  then W4P's existing `PktHello` (build tag, disc CRC, BIOS, settings fingerprint, patch fingerprint, players, delay,
  hash interval; warns on screen) and the protocol-version check that drops other versions (W4P.cpp `CompareHello`,
  `HandlePacket`). VERIFIED (existing code) / HYPOTHESIS (new layers). The lobby
  also removes today's "answer 60 fps and widescreen the same on both PCs" README step, because the host decides.

### 5.2 Timeouts, NAT rebinding, reconnect
- NAT mappings: RFC 4787 says a UDP mapping "MUST NOT expire in less than two minutes" (REQ-5) and outbound packets
  refresh it (REQ-6) [C19]. W4P sends every poll, every 15 ms while stalled and every 50 ms from vsync, and libjuice
  sends consent checks every 4-6 s and keepalives every 15 s [C7], so mappings stay alive during a session. VERIFIED
  (texts, code); real routers HYPOTHESIS.
- Consent freshness: libjuice marks a pair failed when no check succeeds for 30 s (`CONSENT_TIMEOUT 30000`, RFC 7675)
  and the agent goes to FAILED ("Lost connectivity") [C7,C8]. It can be compiled out (`DISABLE_CONSENT_FRESHNESS`
  [C4]); keep it on. VERIFIED (source).
- Interaction with the 60 s policy: W4P calls a player "gone" after 2 s of silence and waits up to 60 s
  (`DisconnectTimeoutS`, `m5_disconnect.md`). An outage shorter than 30 s heals by itself (same ICE pair). After 30 s
  the helper re-dials automatically with the stored descriptions and credentials on the same port; both sides detect
  the loss within seconds of each other, so the 39.5 s timer is no problem. If a side's public address changed (router
  restart, new IP), re-dialing the host works through path (b) only if the host is reachable; otherwise a fresh reply
  code is needed, which will usually not fit in the 60 s window. Joiner-joiner links are re-signaled by the host.
  HYPOTHESIS (T1g).
- Host leaving ends the session (policy); the helper reports it as such, not as a network fault.

---

## 6. Test plan

Environment labels as CLAUDE.md requires. T1 runs on this PC with no internet access needed; T2-T4 need other PCs and
people and therefore the user's approval (T3/T4 also make each friend's PC contact Cloudflare's STUN server, which is
the approved D5 method).

| ID | Environment | What | Measure | Pass |
|---|---|---|---|---|
| T1a | SINGLE-PC, unit | Code codec: 10,000 random descriptions round trip; every single-character substitution, deletion and swap | lengths; detection rate | 100 % round trip; every single-character error detected |
| T1b | SINGLE-PC, loopback, no STUN (host candidates only: the PC's LAN address, or a test build with `ENABLE_LOCALHOST_ADDRESS` [C4]) | 2 helpers, then 4 in mesh (6 pairs), MUX mode | time to connect, selected pair type, RTT (expect < 1 ms), loss | all pairs connected < 2 s, 0 loss |
| T1c | SINGLE-PC | Path (b): joiner connects with the join code only (host agent created from the `juice_mux_listen` callback) | success, time | connects < 3 s; if not, (b) is dropped and (a) alone is used |
| T1d | SINGLE-PC | Delayed paste: host pastes the reply after 5 s, 45 s, 3 min | connected? public candidate unchanged across agent re-creations? | connects in all three |
| T1e | SINGLE-PC | Forwarding: one joiner pair blocked by a helper test switch | pair uses the host; added delay | lockstep continues; added delay about one extra loopback leg |
| T1f | SINGLE-PC, bots | 4 instances in lockstep through the helpers (m2_run4 style, 10 min), then with impairment 100 ms RTT, 20 ms jitter, 2 % loss | hash points and mismatches; stall %; max stall; compare with a plain-UDP run of the same setup | 0 mismatches; stall % within noise of plain UDP |
| T1g | SINGLE-PC, bots | Outage: helper silences one link for 20 s and 45 s | resumes in sync? re-dial time | 0 mismatches after resume (M5 criterion 3 with the real transport) |
| T2 | LAN, user's second PC, humans | Codes over the LAN, then Join by IP; 2 players, 10 min | connect time, selected pair (host-host expected), RTT, stalls, firewall prompts | connects < 15 s, 0 mismatches |
| T3 | INTERNET, friends, no game | `w4p-net probe`: every pair of friends' PCs connects and exchanges 200-byte packets at 60/s for 2 min | per pair: connected yes/no, path (direct host/srflx/peer-reflexive, through host, failed), time to connect, RTT p50/p95/p99, jitter, loss, whether the public address stayed stable; connection type (fibre/cable/DSL/mobile, Wi-Fi or cable) | report the success matrix; triggers 4.4 |
| T4 | INTERNET, friends, humans | Game sessions 2, then 3, then 4 players, 20-30 min each | stall % and max stall, number of waits > 1 s, mismatches, input delay chosen vs. felt, upload per PC (helper counters), reconnects | 0 mismatches; stalls reported as measured |

Logs: the helper writes `connection-log.txt` (candidate types and families, IPs masked except private/public flag, ICE
state changes with times, selected pair, RTT histogram, loss, bytes per link) next to the W4P logs, so friends can send
one folder back.

---

## 7. Open questions for the user
1. **(A)** Networking in a helper program (recommended) or inside the emulator?
2. **(B)** Automatic router port opening (UPnP/PCP) to help path (b): it changes router settings on each player's
   network, so off unless you approve (recommended: off for now, decide after T3).
3. **(C)** Use the free public service ntfy.sh to remove reply codes? Every player's PC would use a third-party service
   under its terms (recommended: not now).
4. **(D)** Approval and timing for T2 (your second PC) and T3/T4 (friends' PCs on their own internet connections).
5. **(E)** The optional protocol change that shrinks input packets (from about 1.0 to about 0.3 Mbit/s upload per PC
   at 60 fps): do it now or only if T3 shows slow uploads (recommended: only if needed).

## 8. Risks
- R-11 (NAT failures) stays open until T3: symmetric NAT, carrier-grade NAT, phone hotspots or blocked UDP can make a
  friend unable to connect without D5-B or a VPN.
- Path (b) depends on libjuice behaviour its own tests do not cover (on-demand agents from `juice_mux_listen`).
- The 39.5 s connectivity timer forces the re-create loop; if public addresses change between re-creations, reply
  codes go stale and must be exchanged again.
- Single STUN provider: if `stun.cloudflare.com` is unreachable, internet codes carry no public address. Google's
  servers have no published terms (`transport_options.md`), so no fallback is built in; a config override can name one.
- Upload: about 1 Mbit/s per PC at 60 polls/s with today's packets; weak uplinks may stall (option E).
- The emulator-side W4P code is changing in parallel (disconnect handling, protocol 3); the helper must not depend on
  W4P packet contents (it only forwards datagrams).
- MSVC C11 atomics in libjuice (option F only) unverified.
- Licence wording for the helper and package is to be confirmed in the M8 legal review.

---

## Sources (accessed 2026-10-11 unless noted)
- C1 https://raw.githubusercontent.com/paullouisageneau/libjuice/master/include/juice/juice.h
- C2 https://github.com/paullouisageneau/libjuice (README)
- C3 https://api.github.com/repos/paullouisageneau/libjuice/releases?per_page=3
- C4 https://raw.githubusercontent.com/paullouisageneau/libjuice/master/CMakeLists.txt
- C5 https://raw.githubusercontent.com/paullouisageneau/libjuice/master/src/ice.c
- C6 https://raw.githubusercontent.com/paullouisageneau/libjuice/master/src/ice.h
- C7 https://raw.githubusercontent.com/paullouisageneau/libjuice/master/src/agent.h
- C8 https://raw.githubusercontent.com/paullouisageneau/libjuice/master/src/agent.c
- C9 https://raw.githubusercontent.com/paullouisageneau/libjuice/master/src/conn_poll.c
- C10 https://raw.githubusercontent.com/paullouisageneau/libjuice/master/src/conn_mux.c
- C11 https://raw.githubusercontent.com/paullouisageneau/libjuice/master/src/thread.h
- C12 https://raw.githubusercontent.com/paullouisageneau/libjuice/master/src/udp.c
- C13 https://api.github.com/repos/paullouisageneau/libjuice/contents/test ;
  https://raw.githubusercontent.com/paullouisageneau/libjuice/master/test/stun-unhandled.c ;
  https://raw.githubusercontent.com/paullouisageneau/libjuice/master/test/stun-unhandled-multiple.c
- C14 https://github.com/paullouisageneau/libdatachannel/pull/1211
- C15 https://raw.githubusercontent.com/libp2p/specs/master/webrtc/webrtc-direct.md
- C16 https://www.mozilla.org/en-US/MPL/2.0/ and https://www.mozilla.org/media/MPL/2.0/index.txt
- C17 https://www.mozilla.org/en-US/MPL/2.0/combining-mpl-and-gpl/
- C18 https://www.gnu.org/licenses/license-list.en.html (entry "Mozilla Public License (MPL) version 2.0")
- C19 https://www.rfc-editor.org/rfc/rfc4787.html
- C20 https://www.rfc-editor.org/rfc/rfc5128.html
- C21 https://www.rfc-editor.org/rfc/rfc6888.html
- C22 https://www.rfc-editor.org/rfc/rfc8445.html
- C23 https://openvidu.io/blog/2026/06/09/turn-key-considerations/
- C24 https://developers.cloudflare.com/realtime/turn/faq/
- C25 https://developers.cloudflare.com/realtime/turn/
- C26 https://docs.ntfy.sh/ ; https://docs.ntfy.sh/terms/ ; https://docs.ntfy.sh/publish/ (Limitations section)
- C27 https://test.mosquitto.org/
- C28 https://www.hivemq.com/mqtt/public-mqtt-broker/
- C29 https://peerjs.com/peerserver
- C30 https://github.com/veorq/SipHash
- C31 https://www.crockford.com/base32.html
- C32 https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.management/set-clipboard?view=powershell-5.1
- C33 search result only, not fetched (HYPOTHESIS): https://streamer.guide/guides/discord-text-formatting
- Project sources: `docs/research/transport_options.md` (accessed 2026-10-10: B3 VPS prices, B4 Cloudflare TURN, B5 VPNs);
  `docs/plan/STAGE1_PLAN.md` section 7; `docs/plan/M5.md`; `docs/research/m5_disconnect.md`; `docs/reports/M1_report.md`;
  F-0075, F-0100, F-0105, F-0122 in `docs/FINDINGS.md`.

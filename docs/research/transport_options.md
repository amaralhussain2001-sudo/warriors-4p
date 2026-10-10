# Session and transport options (Part B)

Stage 1 research note. Read-only web research: no accounts created, nothing installed or downloaded. Every URL was accessed on **2026-10-10**.

**Labels:** **V** = VERIFIED (source ID in brackets, URLs at the end; source IDs start with "B", as in B1). A bare **[B]** means BLOCKED. **H** = HYPOTHESIS (what would confirm it is given). **B** = BLOCKED. **EST** = estimate from first principles, not measured.

**Scope:** Steam, Steamworks, Steam Datagram Relay (SDR), Steam lobbies and Remote Play are **excluded**. Valve's open-source GameNetworkingSockets is evaluated only as a standalone library. Its Steam-only parts are flagged.

No option below is described as low-latency. Nothing was measured; only documented properties are reported.

## Summary table

| Option | Category | Accounts needed | Cost (quoted 2026-10-10) | NAT / firewall | How friends join | Security / reliability features | License | Maintenance |
|---|---|---|---|---|---|---|---|---|
| **libjuice** | ICE/STUN/TURN client, plus a small STUN/TURN server [V:B1] | None (library) | Free | ICE with STUN, TURN relay client [V:B1] | Needs our own signaling (exchange of connection descriptions). Join codes are our design | Raw UDP datagrams. Reliability and encryption are ours to add (H) | MPL-2.0 [V:B1] | v1.7.4, 2026-09-26 [V:B2] |
| **libdatachannel** | WebRTC data channels and WebSocket [V:B3] | None | Free | ICE through libjuice or libnice. TURN [V:B3] | Needs signaling. WebSocket client and server are included [V:B3] | Per-channel ordered/unordered and reliable/unreliable [V:B4]. DTLS (H: WebRTC requires it) | MPL-2.0 [V:B3] | v0.24.6, 2026-09-26 [V:B5] |
| libnice | ICE library | None | Free | ICE | Needs signaling | — | LGPL-2.1-or-later OR MPL-1.1 [V:B6] | GitHub mirror pushed 2026-09-01 [V:B7]. Upstream GitLab fetch blocked [B] |
| pion/webrtc | WebRTC in Go | None | Free | ICE | Needs signaling | Data channels | MIT [V:B8] | Pushed 2026-10-09 [V:B8]. Go, not C++ (poor fit for PCSX2) |
| miniupnpc, libnatpmp | Router port mapping (UPnP IGD, NAT-PMP) | None | Free | Only works if the router allows it (H) | Direct IP:port | — | BSD-3 [V:B9,B10] | miniupnpc 2.3.3, 2025-05-26 [V:B11]. libnatpmp last push 2025-04-03 [V:B10] |
| Cloudflare public STUN | STUN server | None (H) | "free and unlimited" [V:B12] | Discovery only, no relaying | n/a | — | Service | Current docs |
| Google `stun.l.google.com` | STUN server | — | **No official usage terms found** [B] | Discovery only | n/a | — | — | Undocumented for third parties |
| **ENet** | Reliable UDP library [V:B13] | None | Free | **No NAT traversal or relay mentioned** [V:B14] | Direct IP:port (or pair with ICE, H) | Optional reliability, channels, fragmentation, throttling. **No encryption mentioned** [V:B14] | MIT [V:B13] | 1.3.18, 2024-04-14. Last commit 2026-06-23 [V:B15,B16] |
| **GameNetworkingSockets (standalone)** | Message-based UDP transport [V:B17] | None for the standalone build | Free | ICE built in, "no external dependencies". STUN and TURN [V:B18] | "Plug in your own signaling service" [V:B17]. A trivial signaling server example is included [V:B19] | Reliable and unreliable messages, AES-GCM-256, lanes [V:B17] | BSD-3 [V:B17] | v1.6.1, 2026-10-03 [V:B20]. **Steam-only, excluded:** SDR relay, Steam authentication, Steam signaling [V:B17,B18] |
| yojimbo / netcode | Client/server game networking [V:B21,B22] | None | Free | Needs a reachable server. No P2P mentioned [V:B21,B22] | Connect tokens from our backend [V:B22] | Encrypted and signed packets. Reliable-ordered and unreliable messages [V:B21] | BSD-3 [V:B23,B24] | Pushed 2026-09-14 and 2026-09-13 [V:B23,B24] |
| msquic / quiche | QUIC | None | Free | No ICE (H) | Server needed (H) | TLS 1.3, streams (H) | MIT / BSD-2 [V:B25,B26] | Pushed 2026-10-10 and 2026-10-09 [V:B25,B26] |
| **coturn on a VPS** | Self-hosted TURN/STUN [V:B27] | VPS account (operator only) | VPS from about $4–5/month (below) | Relays when direct fails. UDP, TCP, TLS, DTLS [V:B27] | Credentials from our rendezvous service (H) | TURN does not encrypt the payload (H) | BSD-3 [V:B28] | 4.18.0, 2026-09-08 [V:B29] |
| Tiny custom UDP relay or rendezvous on a VPS | Our own server | VPS account (operator only) | Same as above | Always works if outbound UDP is allowed (H) | Join code mapped to session | Ours | Ours | Ours to maintain |
| **Cloudflare Realtime TURN** | Managed TURN | Cloudflare account (H). Self-serve with a card [V:B30] | $0.05/GB egress. "The first 1,000 GB each month is free" (shared with the SFU) [V:B31] | TURN over UDP, TCP and TLS, including port 443 [V:B32] | Our service issues credentials (TTL up to 48 h) [V:B30] | IPv4 relay only. No TCP relaying (RFC 6062) [V:B30] | Service | Current docs |
| Metered TURN | Managed TURN | Account (H) | Free: 500 MB/month. Growth $99/month for 150 GB [V:B33]. Open Relay: 20 GB/month free with signup [V:B34] | Ports 80/443, UDP, TCP, TLS [V:B33] | Credentials through an API | — | Service | Current |
| Epic Online Services P2P | Managed P2P plus relay | Epic developer portal product setup (H). Players' Epic accounts maybe not required (H) | "free" (H: seen only in a search excerpt) | ICE/STUN, secure relay fallback, relay control modes (H) | EOS lobbies or sessions | Encrypted (H) | Proprietary SDK (H) | Docs are JavaScript-rendered and could not be fetched [B] |
| Photon (Realtime) | Managed relay rooms | Account (H) | Free 20 CCU "For Development Only", 60 GB. 100 CCU is $95 one-time for 12 months [V:B35] | Via the cloud (H) | Room names or codes (H) | — | Proprietary | Current |
| PlayFab Party | Managed P2P plus Azure relay [V:B36] | PlayFab title (H) | Metered: connectivity minutes, relay egress [V:B37]. Prices **B** (pricing page returned 403) | "low-latency cloud relay", "Direct peer-to-peer" (vendor wording) [V:B36] | Network descriptor (H) | "Industry-standard encryption" [V:B36] | Proprietary | Docs updated 2026-07-28 [V:B36] |
| Unity Relay | Managed relay | Unity project (H) | 50 average CCU free, then $0.16 per CCU. 3 GiB per CCU free up to 150 GiB, then $0.09/GiB (US/EU) [V:B38] | Via relay | Join codes (H) | — | Proprietary | Unity-centric (H) |
| **Tailscale** | WireGuard overlay VPN | **Each user needs an identity-provider login** [V:B39] | Personal plan free: "Up to 6 users", unlimited user devices, non-commercial [V:B39] | Direct UDP, then peer relay, then DERP [V:B40,B41] | Invite friends to the tailnet. Shared machines are quarantined [V:B42] | WireGuard end to end, including over DERP [V:B40] | Client BSD-3 [V:B43]. The coordination server is proprietary (H) | Pushed 2026-10-10 [V:B43] |
| Headscale | Self-hosted Tailscale control server | None from Tailscale. Operator runs a server | VPS cost | As Tailscale. DERP setup is ours (H) | Our own server | WireGuard | BSD-3 [V:B44] | v0.29.4, 2026-09-23 [V:B45] |
| **ZeroTier** | Layer-2 overlay ("Smart Ethernet Switch") [V:B46] | Network admin account (H). Members join by network ID (H) | Free Personal: "10 devices, one network", non-commercial [V:B47] | Direct, else RELAY through roots ("increased latency and possible packet loss") [V:B48] | Network ID, then admin approval (H) | Encrypted (H) | MPL for the core, plus a source-available "nonfree/" part [V:B49] | Pushed 2026-09-03 [V:B46] |
| **Radmin VPN** | Windows virtual LAN | None (H: a third-party listing, source B50, says "No registration required". Not on the vendor page) | "completely free … without ads or any paid features" [V:B51] | "Relay/TCP connection … when a direct connection cannot be established" [V:B52] | Network name plus password [V:B52] | Claims 256-bit AES [V:B51] | Closed source (H) | Current site (© 2026) [V:B51]. **Windows only** [V:B51] |
| NetBird | WireGuard overlay | Account (H), or self-host | Free: "up to 5 users", "100 machines" [V:B53] | P2P plus relay (H) | Invite or setup key (H) | WireGuard | BSD-3. AGPLv3 for management, signal and relay [V:B54] | Pushed 2026-10-10 [V:B55] |
| NordVPN Meshnet | Overlay | NordVPN account (H) | — | — | — | — | — | Shutdown announced, then **reversed 2025-09-29** per PCWorld [V:B56]. NordVPN page fetch failed [B]. Current status H |

---

## Details

### B1. Direct peer-to-peer (no third-party service)

- **How it works:** each peer learns its public address from a STUN server. The peers exchange candidates through signaling, then try connectivity checks (ICE). If every pair fails, a TURN relay carries the traffic.
  - RFC 8656 says TURN "comes at a high cost to the provider" and is "best" used "only when a direct communication path cannot be found" [V:B57].
  - Tailscale's documentation (general ICE behaviour) says a direct path "can't [be established] if both devices are behind a hard NAT", and that blocked UDP forces a relay [V:B41].
- **libjuice (V) [B1,B58]:**
  - Standards: a "simplified full ICE agent" (RFC 8445), STUN (RFC 8489), TURN (RFC 8656).
  - "Only UDP is supported as transport protocol". No required dependencies.
  - API: `juice_get_local_description`, `juice_set_remote_description`, `juice_send`, and a `juice_turn_server_t` config.
  - It "also implements a lightweight STUN/TURN server" (`juice_server_create`).
  - Fit: a small C library that gives one UDP datagram path per peer pair, with no built-in reliability or encryption. H: that suits an input-only lockstep protocol, where we control redundancy ourselves.
- **libdatachannel (V) [B3,B4]:**
  - WebRTC data channels over SCTP/DTLS, with a choice of ICE back end. It includes a WebSocket client and server, which could be used for signaling.
  - `Reliability{unordered, maxPacketLifeTime, maxRetransmits}` allows unreliable, unordered channels.
  - Heavier: it needs OpenSSL, GnuTLS or Mbed TLS, plus usrsctp.
- **libnice (V) [B6]:** LGPL-2.1-or-later OR MPL-1.1. H: depends on GLib.
- **pion (V) [B8]:** MIT, written in Go. Would need a separate process or cgo to work with C++ PCSX2. Not recommended.
- **Public STUN servers:**
  - Cloudflare: "STUN service at `stun.cloudflare.com` is free and unlimited" [V:B12].
  - Google `stun.l.google.com:19302`: widely used in examples, but **no official Google terms page was found** [B: searched developers.google.com, webrtc.org, firebase.google.com]. Do not depend on it without written terms.
  - GameNetworkingSockets' own P2P test uses public Google STUN servers [V:B18]. That does not grant terms.
- **Port mapping:**
  - miniupnpc is a UPnP IGD client and "also works under MS Windows". For NAT-PMP clients, "use libnatpmp". PCP support is only on the gateway side (MiniUPnPd) [V:B9].
  - H: UPnP is often disabled, and port mapping cannot help behind carrier-grade NAT. Confirm with the friends' actual routers.
  - Manual port forwarding needs router access by the host. That is poor for "easy joining" (H).

### B2. Open-source game networking libraries (no platform account)

- **ENet (V) [B13–B16]:**
  - Sequencing, channels that are "independently sequenced", "optional reliability", fragmentation, aggregation and a dynamic throttle. MIT-style license.
  - The design document does not mention encryption, NAT traversal or relays.
  - Last release 1.3.18 (2024-04-14). Commits continue (2026-06-23).
- **GameNetworkingSockets standalone (V) [B17–B20]:**
  - Features: reliable and unreliable messages; "AES-GCM-256 per packet, Curve25519 for key exchange"; lanes for head-of-line control.
  - P2P: "NAT traversal through google WebRTC's ICE implementation", plus a built-in ICE client "compiled in by default". Signaling must be plugged in by us, and an example `trivial_signaling_server.py` exists [B19].
  - Dependencies: OpenSSL 1.1.1+, libsodium or bcrypt (Windows); protobuf 2.6.1+.
  - **Steam-only (excluded):** "Steam's authentication service", SDR relays ("the SDR support code is not opensource"), and Steamworks signaling and matchmaking.
  - H: without Steam authentication, peer identity must come from our own certificates or trust model. Confirm in `steamnetworkingsockets.h` and the certificate docs.
- **yojimbo and netcode (V) [B21–B24]:**
  - yojimbo is "for client/server games", with "Encrypted and signed packets" and "Cryptographically secure authentication via connect tokens". No P2P is mentioned.
  - Both are BSD-3. Fit: only if we run a dedicated server that every player connects to.
- **QUIC (msquic MIT, quiche BSD-2 in Rust) (V) [B25,B26]:** H: QUIC is client/server with no ICE, and its streams are reliable unless the datagram extension is used. Overkill for a few bytes of input per frame.

### B3. Custom relay or rendezvous on a VPS

- **coturn (V) [B27–B29]:** "free open source implementation of TURN and STUN Server"; UDP, TCP, TLS, and DTLS (`--dtls`); runs on Windows natively (MSVC) and on Linux; BSD-3; release 4.18.0 on 2026-09-08. Alternative: libjuice's built-in server [B1].
- **VPS prices (quoted 2026-10-10):**

| Provider | Plan | Price | Included traffic | Label |
|---|---|---|---|---|
| DigitalOcean | Basic Droplet 1 vCPU / 512 MiB | $4.00/month | 500 GiB; overage $0.01/GiB | V [B59,B60] |
| DigitalOcean | Basic 1 vCPU / 1 GiB | $6.00/month | 1,000 GiB | V [B59] |
| OVHcloud | VPS-1, 2 vCores / 4 GB | "From $4.54 /month" | Unlimited traffic, 500 Mbps | V [B61] |
| Vultr | Regular Performance 1 vCPU / 1 GB | $5.00/month (a $2.50 tier is also listed) | 1 TB; $0.01/GB over | **H**: search excerpt only, pricing page returned 403 |
| Hetzner | Cloud | Prices not rendered on the page. CPX02 "currently unavailable" | EU: "at least 20 TB" | **B** for price. Traffic and availability V [B62] |

- **Bandwidth needed for input-only lockstep (EST, not measured):**
  - Assumptions:
    - Six bytes of DualShock 2 response per pad per poll. A2e uses six bytes (2 digital, 4 analog) [Part A, S18].
    - About 60 polls/s (H: one poll per frame. Confirm in the game).
    - Each packet carries the last 4 frames of input for loss tolerance, plus an 8-byte header.
    - UDP/IPv4 headers add 28 bytes. Optional authenticated encryption adds about 28 bytes.
  - Per direction, per peer link: (8 + 24 + 28) to (8 + 24 + 56) bytes × 60/s gives **about 29–42 kbit/s**.
  - **Full mesh, 4 players:** each PC sends to 3 peers and receives from 3, so **about 90–130 kbit/s up and the same down**.
  - **Star through a host or relay:**
    - Client: about 29–42 kbit/s up. Down, a bundle of 4 players' input (8 + 96 + 28 to 56 bytes) × 60 gives about 65–80 kbit/s.
    - Hub: about 200–250 kbit/s each way.
  - **Relay data volume:** with all 4 players relayed, egress is about 40 kB/s, which is about 140 MB per hour. 100 hours a month is about 14 GB. That is well inside DigitalOcean's 500 GiB and Cloudflare's 1,000 GB free tier. It exceeds Metered's free 500 MB after about 3–4 hours.
  - **One-off bursts (H):**
    - Memory-card sync: a PS2 card is 8 MB.
    - Savestate transfer for resync or late join: H, size not measured.
    - VPN overlays add about 60 bytes per packet for WireGuard (H). This is small at these rates.

### B4. Third-party networking services (Steam excluded)

- **Cloudflare Realtime TURN (V) [B30–B32]:**
  - Pricing: $0.05 per GB from the edge to the client. "The first 1,000 GB each month is free", shared with the SFU.
  - Ports: 3478 UDP/TCP, 5349 TLS, and alternates on 443 and 80.
  - Limits: relay addresses are IPv4 only. TCP relaying (RFC 6062) is not supported. Credentials are valid for up to 48 h. "self-serve (pay with your credit card) plans" exist.
  - TURN "does not discuss encryption beyond wrapper protocols", so the payload must be encrypted by us.
  - H: needs a Cloudflare account and a small credential-issuing endpoint run by us.
- **Metered (V) [B33,B34]:**
  - Free plan: 500 MB/month, "No credit card required". Growth: $99/month for 150 GB, then $0.40/GB.
  - The Open Relay Project gives 20 GB/month free and "you need to sign-up for a free account".
- **Epic Online Services P2P (H, docs blocked):**
  - Search-index excerpts of dev.epicgames.com (overview and P2P guide) describe EOS as "free", using ICE/STUN, with a fallback to "secure relays".
  - The same excerpts describe relay-control modes: allow relays (default), "no relay", "force relay".
  - The pages themselves render with JavaScript and could not be fetched [B].
  - H: needs an Epic developer-portal organization and product, plus acceptance of Epic's terms. Players can log in without Epic accounts through the Connect interface (a forum anecdote only). Confirm in the EOS docs and agreement before any decision. Accepting terms needs user approval.
- **Photon (V) [B35]:**
  - The free 20 CCU plan is "For Development Only" (60 GB). The paid 100 CCU plan is "For Games Only", $95 one-time for 12 months.
  - H: all traffic goes through Photon rooms. Proprietary.
- **PlayFab Party (V) [B36,B37]:**
  - Vendor wording: "automatic low-latency cloud relay … Azure regions" and "Direct peer-to-peer functionality".
  - Billed on Party Connectivity minutes and relay "Network Egress". Prices are B (playfab.com/pricing returned 403).
- **Unity Relay (V) [B38]:** 50 average CCU free, then $0.16 per CCU. Bandwidth free at 3 GiB per CCU up to 150 GiB, then $0.09/GiB (US/EU). H: tied to Unity Gaming Services projects and SDKs, which makes it awkward for a C++ emulator.

### B5. Overlay VPNs

- **Tailscale (V) [B39–B43]:**
  - Free plan and accounts: the Personal plan is free for "Up to 6 users" and "only suitable for non-commercial use". "every user is authenticated using an identity provider".
  - Relaying: DERP is the last resort, after direct and peer relays. "it's impossible for a DERP server to decrypt your traffic". DERP has "limited quality of service" and may cap throughput.
  - Sharing a single machine with another tailnet is quarantined: it "cannot start connections". For a 4-way mesh, friends would join one tailnet as users (H).
  - DEV9 caution: see Part A pull request #11997 (WireGuard adapters with PCAP). This only matters for a DEV9 route, not for our own UDP protocol.
- **Headscale (V) [B44,B45]:** "self-hosted implementation of the Tailscale control server"; "not associated with Tailscale Inc."; single tailnet; BSD-3; v0.29.4 (2026-09-23).
- **ZeroTier (V) [B46–B49]:**
  - Free plan "10 devices, one network", non-commercial. RELAY through root servers when direct fails.
  - License: the core is MPL, with a separate source-available `nonfree/` directory.
- **Radmin VPN (V) [B51,B52]:** free, Windows 11/10/8/7 only, network name plus password, Relay/TCP fallback, made by Famatech. Closed source (H).
- **NetBird (V) [B53–B55]:** free for 5 users and 100 machines. The client is BSD-3; management, signal and relay are AGPLv3, so it can be self-hosted.
- **NordVPN Meshnet:**
  - PCWorld reports that the 2025-12-01 shutdown was reversed on 2025-09-29, and that NordVPN plans to "open-source Meshnet" [V:B56].
  - NordVPN's own blog could not be fetched [B]. Its current status is H.
- **Common trade-off (H):**
  - Pros: a VPN needs zero NAT code in the mod, and our protocol simply uses VPN IPs.
  - Cons: every friend must install a system-level adapter and service, and most products need an account. Relay paths add latency (ZeroTier and Tailscale say so).
  - Good for Stage-2 prototyping and as a fallback. Weak for "easy joining".

### B6. Dedicated servers: when justified

- **Not needed for simulation (H):** with input lockstep, each PC runs its own emulator, so a server never runs game logic.
- **Justified as a small always-on rendezvous service (H).** It would:
  - map a join code to a session;
  - relay ICE candidates (signaling);
  - issue TURN credentials;
  - optionally act as a **star relay** for players whose direct paths fail.
- **Cost:** one small VPS (about $4–6/month quoted above) covers this. A relay of about 14 GB/month (EST) is far under the included traffic.
- **A full star through a server** (every player always relayed) would make the topology identical for everyone and NAT-proof. It costs an extra network hop for all players (H: measure in Stage 2).

### Candidate shortlist (H, for the Stage-2 decision; measured against the brief's priorities)

1. **Own UDP lockstep protocol over libjuice, plus a small self-hosted rendezvous and relay on one VPS.**
   - libjuice: MPL-2.0, no dependencies, active.
   - Rendezvous and relay: coturn or libjuice's TURN server. STUN from Cloudflare (free, documented) and our own.
   - Joining: friends get a join code, and nobody needs an account. A direct path is tried first, with a relay fallback.
   - We must add sequencing, redundancy and encryption ourselves. That is small for input frames.
2. **GameNetworkingSockets standalone,** if built-in encryption and reliable/unreliable lanes are wanted.
   - It adds protobuf and OpenSSL dependencies, and signaling is still ours.
   - SDR and Steam authentication are excluded and unavailable.
3. **Overlay VPN (Tailscale free for ≤6 users, or ZeroTier free for ≤10 devices)** for early LAN-style testing with direct IPs. Needs accounts and installs. Not the final joining experience.
4. **Managed TURN (Cloudflare: 1,000 GB/month free, then $0.05/GB)** instead of self-hosting the relay. Needs a Cloudflare account (user approval).

**Not shortlisted:**
- ENet alone: no NAT traversal or encryption documented.
- yojimbo/netcode: client/server only.
- QUIC: no ICE, and heavier than needed.
- EOS: developer agreement, proprietary SDK, docs unverified.
- Photon free: "Development Only".
- PlayFab and Unity Relay: platform accounts and SDK coupling.
- Radmin: Windows-only and closed, though fine for ad-hoc tests.

## Open gaps

1. **B:** EOS docs (JavaScript-rendered), PlayFab pricing (403), Vultr pricing (403), Hetzner prices (not rendered), the NordVPN Meshnet blog (connection reset), libnice upstream GitLab (bot wall), and the ENet homepage (connection refused).
2. **H:** written usage terms for Google's public STUN servers. None were found.
3. **H:** the real NAT types of the 4 friends' connections (carrier-grade NAT, symmetric NAT, UDP blocked). This decides how often a relay is needed. It needs testing with other people, which needs user approval.
4. **EST to measure:** actual pad poll rate, packet sizes, and memory-card and savestate transfer sizes in Stage 2.
5. **H:** whether GameNetworkingSockets standalone needs a custom certificate authority for authenticated peers without Steam.

## Sources (all accessed 2026-10-10)

- B1 https://github.com/paullouisageneau/libjuice
- B2 https://api.github.com/repos/paullouisageneau/libjuice/releases?per_page=2
- B3 https://github.com/paullouisageneau/libdatachannel
- B4 https://raw.githubusercontent.com/paullouisageneau/libdatachannel/master/include/rtc/reliability.hpp
- B5 https://api.github.com/repos/paullouisageneau/libdatachannel/releases?per_page=2
- B6 https://raw.githubusercontent.com/libnice/libnice/master/COPYING
- B7 https://api.github.com/repos/libnice/libnice
- B8 https://api.github.com/repos/pion/webrtc
- B9 https://github.com/miniupnp/miniupnp
- B10 https://api.github.com/repos/miniupnp/libnatpmp
- B11 https://api.github.com/repos/miniupnp/miniupnp/releases?per_page=3
- B12 https://developers.cloudflare.com/realtime/turn/faq/
- B13 https://github.com/lsalzman/enet
- B14 https://raw.githubusercontent.com/lsalzman/enet/master/docs/design.dox
- B15 https://raw.githubusercontent.com/lsalzman/enet/master/ChangeLog
- B16 https://api.github.com/repos/lsalzman/enet/commits?per_page=1
- B17 https://raw.githubusercontent.com/ValveSoftware/GameNetworkingSockets/master/README.md (and https://github.com/ValveSoftware/GameNetworkingSockets)
- B18 https://raw.githubusercontent.com/ValveSoftware/GameNetworkingSockets/master/README_P2P.md
- B19 https://api.github.com/repos/ValveSoftware/GameNetworkingSockets/contents/examples ; https://raw.githubusercontent.com/ValveSoftware/GameNetworkingSockets/master/BUILDING.md
- B20 https://api.github.com/repos/ValveSoftware/GameNetworkingSockets/releases?per_page=3
- B21 https://github.com/mas-bandwidth/yojimbo
- B22 https://github.com/mas-bandwidth/netcode
- B23 https://api.github.com/repos/mas-bandwidth/yojimbo
- B24 https://api.github.com/repos/mas-bandwidth/netcode
- B25 https://api.github.com/repos/microsoft/msquic
- B26 https://api.github.com/repos/cloudflare/quiche
- B27 https://github.com/coturn/coturn
- B28 https://raw.githubusercontent.com/coturn/coturn/master/LICENSE
- B29 https://api.github.com/repos/coturn/coturn/releases?per_page=2
- B30 https://developers.cloudflare.com/realtime/turn/faq/
- B31 https://developers.cloudflare.com/realtime/pricing/
- B32 https://developers.cloudflare.com/realtime/turn/
- B33 https://www.metered.ca/stun-turn
- B34 https://www.metered.ca/tools/openrelay/
- B35 https://www.photonengine.com/pricing
- B36 https://learn.microsoft.com/en-us/gaming/playfab/features/multiplayer/networking/
- B37 https://learn.microsoft.com/en-us/gaming/playfab/pricing/meters/meters
- B38 https://unity.com/products/gaming-services/pricing
- B39 https://tailscale.com/pricing
- B40 https://tailscale.com/kb/1232/derp-servers
- B41 https://tailscale.com/kb/1257/connection-types
- B42 https://tailscale.com/kb/1084/sharing
- B43 https://api.github.com/repos/tailscale/tailscale
- B44 https://github.com/juanfont/headscale
- B45 https://api.github.com/repos/juanfont/headscale/releases?per_page=2
- B46 https://api.github.com/repos/zerotier/ZeroTierOne
- B47 https://www.zerotier.com/pricing/
- B48 https://docs.zerotier.com/faq/relaying/
- B49 https://raw.githubusercontent.com/zerotier/ZeroTierOne/dev/LICENSE.txt
- B50 https://alternativeto.net/software/radmin-vpn/about (third-party, seen in search results only)
- B51 https://www.radmin-vpn.com/
- B52 https://www.radmin-vpn.com/help/
- B53 https://netbird.io/pricing
- B54 https://raw.githubusercontent.com/netbirdio/netbird/main/LICENSE
- B55 https://api.github.com/repos/netbirdio/netbird
- B56 https://www.pcworld.com/article/2881273/nordvpn-bids-farewell-to-its-meshnet-feature-what-you-need-to-know.html
- B57 https://datatracker.ietf.org/doc/html/rfc8656
- B58 https://raw.githubusercontent.com/paullouisageneau/libjuice/master/include/juice/juice.h
- B59 https://www.digitalocean.com/pricing/droplets
- B60 https://docs.digitalocean.com/platform/billing/bandwidth/
- B61 https://www.ovhcloud.com/en/vps/
- B62 https://www.hetzner.com/cloud/regular-performance (and https://www.hetzner.com/cloud/)
- Search-only (H): EOS excerpts from https://dev.epicgames.com/docs/epic-online-services/eos-overview and https://dev.epicgames.com/docs/epic-online-services/multiplayer/nat-p2p-interface/p2p-overview ; Vultr excerpt from https://www.vultr.com/pricing/

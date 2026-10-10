# Existing ways to play PS2 games online through an emulator (Part A)

Stage 1 research note. Read-only web research. Every URL was accessed on **2026-10-10**.

**Labels:** **V** = VERIFIED (source ID in brackets, URLs listed at the end). **H** = HYPOTHESIS (what would confirm it is given). **B** = BLOCKED (the source could not be read).

**Layers:** L1 Session (finding and joining a game), L2 Transport (moving bytes), L3 Simulation sync (keeping 4 emulators identical), L4 Local presentation (each player's own screen and audio).

Scope note: this note makes no claims about The Warriors itself. The project's own analysis (outside this note) found developer TCP file-server and socket code in the executable, but no evidence of online gameplay.

## Summary table

| # | Method | How it works | Maintained? | PCSX2 version | Players | License | Sync model / known desync | Layers it could help |
|---|---|---|---|---|---|---|---|---|
| A1 | PCSX2 DEV9 network adapter (mainline) | Emulates the PS2 network adapter. The game's own network code runs over PCAP Bridged, PCAP Switched, TAP or Sockets [V:S1,S2] | Yes. It is part of PCSX2 master [V:S1] | Mainline 2.x, including the v2.9.115 nightly (2026-10-09) [V:S3] | Whatever the game's own network code supports | GPL-3.0-or-later [V:S4,S5] | The game's own network code. PCSX2 adds no input sync | L2 only, and only for games that have their own LAN or online code |
| A1b | XLink Kai plus DEV9 (PCAP Switched) | Peer-to-peer LAN tunnelling for system-link games [V:S6] | The PCSX2 setup page was last edited 2022-06-16 [V:S6] | "latest nightly" [V:S6] | Per game. XLink lists 56 PS2 system-link games [V:S6] | Proprietary service. Needs an account and consent to data collection [V:S6] | Game's own | L1 and L2 for LAN-capable games only |
| A1c | Radmin VPN or ZeroTier plus DEV9 (PCAP Bridged) | A virtual LAN adapter is bridged into PCSX2 [V:S7] | Community guide, undated | "latest PCSX2" [V:S7] | Per game | See transport_options.md | Game's own | L1 and L2 for LAN-capable games only |
| A1d | PS2 online revival servers | DNS redirect to fan-run servers. Most titles need a DNAS workaround [V:S8] | Varies per game | Any build with DEV9 | Per game | Varies | Game's own | Only for games that originally shipped online |
| A2a | PCSX2 Online (alexsharoff/pcsx2-online) | Fork with peer-to-peer netplay that syncs controller input, with automatic input-delay detection [V:S9] | **Archived** 2019-11-12. Changelog ends 2012-01-22 [V:S9,S10] | Pre-git PCSX2 (2011–2012 era) [V:S9,S10] | Not stated (host and client roles) [V:S9] | No license field. PCSX2-derived code (H) | Delay-based input sync. "always desync" unless started from a clean emulator start, and changing settings raises desync risk [V:S9] | Reference design for L1–L3 |
| A2b | SmileTheory/pcsx2 | "Fusion of current pcsx2 and pcsx2-online" [V:S11] | Last push 2018-03-08 [V:S12] | PCSX2 master of about 2017–18 (H: check the commit base) | Not stated | GPL-2.0 (GitHub detection) [V:S12] | Presumably the same model as A2a (H) | Reference only |
| A2c | fraserofsmeg/pcsx2-online-Update | Copy of A2a's README and roadmap [V:S13] | All activity on 2016-06-12 [V:S14] | Same as A2a | Not stated | None declared [V:S14] | Same as A2a. Roadmap: "Desync detection/correction" [V:S13] | None |
| A2d | YungMoniCA1/pcsx2-netplay-reborn, TimeFlex1/pcsx2-netplay-reborn-update | Attempts to revive A2a, with no documentation [V:S15,S16] | Last push 2017-11-17 and 2023-12-30 [V:S17] | Unknown | Unknown | Unlicense (GitHub detection) [V:S17] | Unknown | None |
| A2e | q13007868130/git-demo, "PCSX2 Modern Netplay Port" | Ports the classic DualShock 2 poll-response lockstep to current PCSX2 master, over TCP [V:S18,S19] | **Active** personal project. Pushed 2026-09-20, 0 stars [V:S17,S20] | "current PCSX2 master" (Sep 2026) [V:S18] | v0.1: 2. The v0.5 plan targets 1–4 [V:S18,S21] | **None declared** [V:S20] | Delay-based lockstep. v0.4 tests "still show gameplay desynchronization" [V:S21] | Closest public reference for L1–L3 |
| A2f | Arkadyzja beta client | Matchmaking front end. PS2 games use "lockstep delay netplay rather than rollback", P2P with automatic relay fallback [V:S22] | **Active**. News items dated 2026-09-03 and 2026-10-06 [V:S22] | Not stated | "Four-player sessions and even eight-player sessions using two multitaps" [V:S22] | Client repo has no license [V:S23]. The PS2 core's source availability is unknown (H) | Lockstep delay. PS2 support covers "a range of tested fighting, sports and action games" [V:S22] | Could cover L1–L3 if it ran this game. Needs an account [V:S22] |
| A3 | Screen streaming (Parsec and similar) | Streams the host's screen to guests [V:S24] | Yes | Any | Not stated for the free plan | Proprietary. The free plan is for "personal, non-commercial use only" [V:S24] | No emulator sync | **Ruled out by the project** (it shows the host's screen to everyone) |
| A4a | RetroArch plus LRPS2 (libretro PCSX2 core) | Hard fork of PCSX2 for libretro [V:S25] | Yes (H: check commits) | Its own fork | — | GPLv3 [V:S25] | **Netplay: not supported (✕)** [V:S25] | None |
| A4b | RetroArch plus Play! core | Separate PS2 emulator [V:S26] | — | n/a | — | MIT [V:S26] | **Netplay: not supported (✕)** [V:S26] | None |
| A4c | Fightcade | Bundles FBNeo, Snes9x, Flycast-based emulators [V:S27,S28] | Yes | n/a | — | Proprietary | GGPO-style rollback for its own cores | **No PS2.** PS2 is not listed [V:S27,S28] |
| A4d | AnyGameAnywhere (srbengueros) | Claims to "Play ANY game online", PCSX2 included. Ships only a prebuilt `.exe`. The method is not documented [V:S29,S30] | 2 commits. Pushed 2026-07-20 [V:S31] | — | Not stated | Apache-2.0 label [V:S31] | Unknown. **Not run** | Unknown. Treat as untrusted |
| — | "Nyxx" | No PCSX2 netplay project by this name was found [V:S32 search] | — | — | — | — | — | — |

**Bottom line (V and H mixed, as marked):**
- Mainline PCSX2 still has no netplay. The feature request #772, opened in 2015, is open. In 2021 maintainers said they were open to a pull request but "the code needs to be updated", and called the existing forks abandoned [V:S33]. A 2023 request (#8425) was closed as a duplicate of #772 [V:S34].
- DEV9 and the LAN tunnels or VPNs only help games that already have network code.
- Every input-sync netplay effort found uses **delay-based lockstep**, not rollback: A2a, A2e and A2f.
- Only two are active: A2e (2 players working, 4 players planned, desyncs open) and A2f (closed beta, account required).

---

## Details

### A1. PCSX2 DEV9 network adapter emulation

- **Backends (V):** the source in PCSX2 master defines `enum struct NetApi { Unset, PCAP_Bridged, PCAP_Switched, TAP, Sockets }`. Options include `InterceptDHCP`, a manual or auto PS2 IP, mask, gateway and DNS, plus `EthHosts` [S1].
- **Sockets backend (V):** added in pull request #4944, merged 2022-03-27. It "can be used with minimal configuration to join online/resurrected games". It can join LAN games hosted by real hardware or by PCSX2 using TAP or PCAP, but "Hosting a game with Sockets is not expected to work" [S2].
- **PCAP on Windows (V):** needs Npcap (WinPcap also works with XLink Kai) [S6,S7].
- **VPN adapters (V and H):**
  - Pull request #11997 tried to add PCAP support for `NdisMediumIP` VPN adapters such as WARP, ProtonVPN "or any other WireGuard based ones". It was **closed unmerged** on 2025-01-02 [S35].
  - H: WireGuard-based overlays such as Tailscale may therefore not work as a DEV9 PCAP adapter in mainline. Testing PCAP Bridged on a Tailscale adapter would confirm this.
  - Radmin VPN does work in a community guide. That guide's settings: Network & HDD, Ethernet on, PCAP Bridged, Radmin VPN adapter, Intercept DHCP on, PS2 address set to the Radmin IP [S7].
- **XLink Kai (V):**
  - Described as "a multi-platform and peer-to-peer LAN tunneling service".
  - PCSX2 setup uses PCAP Switched and manual IPs from the XLink IP calculator.
  - An XLink Kai account, email verification and consent to the data collection policy are required [S6].
- **Revival servers (V):**
  - The official DNAS service shut down on 2016-04-04.
  - Fan servers exist, and "most" need a workaround to connect. Unofficial servers are reached by changing DNS settings.
  - Wikipedia also names XBSlink, SVDL and XLink Kai as LAN-tunnel options [S8].
- **Relevance:** none of A1 to A1d synchronizes a single-player or split-screen campaign. They carry traffic that the game itself generates. That makes them useful only if a game has its own LAN or online code, which the project's own analysis has not found here. **Layer help:** L2 only, conditionally.

### A2. Input-sync netplay forks of PCSX2

- **A2a, PCSX2 Online (alexsharoff) (V) [S9,S10]:**
  - Features: "peer-to-peer netplay mode", "Automatic input delay detection", input-delay fine-tuning on the host side, and no central servers.
  - Determinism caveats:
    - Netplay resets emulation settings and disables speedhacks.
    - It works only "after a clean emulator start", otherwise it will "always desync".
    - Changing settings other than the controller plugin raises desync risk.
    - Fate/Unlimited Codes and KOF XI desync frequently.
  - "Desync detection/correction" remains on the roadmap.
  - Archived on 2019-11-12. Created 2011-05-04, last push 2019-10-27.
  - Successors named: alexsharoff/pcsx2 (`netplay` branch) and SmileTheory/pcsx2.
- **A2b to A2d (V) [S11–S17]:** all are stale, last activity 2016–2023, and none documents working builds.
  - The 2014 PCSX2 blog calls `DEV9giga-razi` "our netplay plugin" [V:S36]. It was a DEV9 (network adapter) plugin, not input-sync netplay (H: confirm in the 1.2.1 plugin docs).
- **A2e, Modern PCSX2 Netplay Port (q13007868130/git-demo) (V) [S18–S21]:**
  - v0.1, pull request #1, merged 2026-09-16:
    - "two-player delay-based lockstep" over TCP. The host is virtual controller 1 and the joiner is controller 2. Input delay is set by the host.
    - It hooks the DualShock 2 POLL response and exchanges six bytes per pad (2 digital, 4 analog).
    - The author lists what is missing: no "rollback, relay/NAT traversal, room browser, memory-card sync, pressure bytes, or state-hash resync".
  - Issue #2 is open (opened 2026-09-17) and holds the v0.5 plan:
    - A two-phase boot barrier (`PREPARE_BOOT`, then `BOOT_READY`).
    - A host-authoritative shadow memory card, checked by CRC.
    - A compatibility manifest covering build SHA, BIOS fingerprint, game serial/CRC and settings.
    - Per-peer ping and jitter display, and delay changes applied at an agreed future poll.
    - Targets P1–P4, but 4-player transport waits until "v0.5a" is tested.
  - Evidence of open problems in that issue:
    - v0.4 two-PC tests showed desyncs while 514 sampled controller payloads matched.
    - At matching poll indices, the two emulators were +1, 0 and −2 VSync apart.
    - Lockstep waits reached about 9.4 s against a 10 s timeout.
  - The repository declares no license, has 0 stars, and contains no BIOS or game images. The first compatibility target is Tekken 5.
- **A2f, Arkadyzja (V) [S22,S23]:**
  - What it is: a "matchmaking, netplay, replays, spectators" client.
  - PS2 sync and players:
    - PS2 uses "lockstep delay netplay rather than rollback".
    - It claims "reduced default client input delay" compared with the older PCSX2-netplay fork. This is not measured by us.
    - 4 players, or 8 with two multitaps, plus analog controls.
  - Connections: "direct peer-to-peer connections when possible", with automatic fallback to a relay "when UDP hole punching fails". "Two relay servers are currently deployed for testing."
  - Availability: beta for Windows and Linux. An account is required, and the VC++ runtime is needed.
  - GitHub client releases run up to 0.0.45 (2026-05-31). The 0.0.42 notes still said "potentially Saturn and PS2 in the future".
  - The underlying PCSX2 version and the license of the PS2 core are not stated.
  - H: whether this game is in its tested list and stays in sync with 4 players. Confirm by checking its game list, or by a test run once the Stage-2 gate allows it. Creating an account is out of scope for Stage 1.

### A3. Screen streaming

- **Parsec (V) [S24]:**
  - The free plan is "licensed for personal, non-commercial use only".
  - It offers 60 FPS desktop capture and encrypted P2P connections.
  - Guest Access costs $25 per invitation on paid tiers.
- **Fit:** it streams one host's screen, so each player does not run their own PCSX2. **Ruled out** by the project brief. Steam Remote Play is excluded by scope and was not researched.

### A4. Other

- **RetroArch netplay (V) [S37]:**
  - It "continuously synchroniz[es] multiple RetroArch instances running the same emulation core and same content", and needs the same RetroArch version, core version and content.
  - Any core with save states "should work but the performance requirements may be too high". PSX, N64, Dreamcast, GameCube, Wii and 3DS are listed as unsuitable.
  - Connectivity: UPnP IGD port mapping, TCP 55435, with an optional "Relay Server".
  - The PS2 cores LRPS2 and Play! both mark Netplay ✕ [S25,S26]. **Not usable for PS2.**
- **Fightcade (V) [S27,S28]:**
  - Wikipedia lists arcade boards plus Genesis, TurboGrafx-16, SNES and Dreamcast.
  - Flathub names FightcadeFBNeo as the "main emulator".
  - PS2 is not mentioned on either page.

### Layer mapping (H, derived from the above)

- **L1 Session:** Arkadyzja is the only existing matchmaking for PS2 lockstep. A2a has a simple connect dialog.
- **L2 Transport:** A2e uses plain TCP with no NAT traversal. Arkadyzja uses P2P with relay fallback. VPNs and XLink Kai give a virtual LAN.
- **L3 Simulation sync:** the reference designs are A2a and A2e. They agree on these requirements:
  - Same build, settings and BIOS on every PC.
  - A clean boot or a synced start.
  - The same memory card.
  - Speedhacks off.
- **L4 Local presentation:** with input-sync lockstep, every PC renders its own emulator. That means each player sees the full shared screen unless the game is modified. Nothing here provides per-player views.

---

## Open gaps

1. **B:** the PCSX2 forum thread "PCSX2 Netplay" (forums.pcsx2.net/Thread-PCSX2-Netplay--58793) returned HTTP 403. The Emulation General wiki Netplay page also returned 403. The Bountysource page for a libretro PCSX2 rollback bounty did not resolve (DNS).
2. **H:** what Arkadyzja's PS2 core is built on (PCSX2 version, source availability, license), and whether this game is supported. Confirm with its docs or Discord. An account is needed, which is out of scope here.
3. **H:** whether A2e's code is reusable. It has no license, so permission from the author would be needed. Its v0.5 4-player results are still pending; watch issue #2.
4. **H:** whether a WireGuard or Tailscale adapter works with DEV9 PCAP. Pull request #11997 suggests it does not in mainline. Only relevant if a DEV9 route were ever used.
5. **H:** which mechanism AnyGameAnywhere uses. It is binary-only and was deliberately not downloaded or run.
6. The "PCSX2 netplay plugin" of the 1.x era: the only official mention found is `DEV9giga-razi` (2014), which is a network-adapter plugin. No separate 1.x input-netplay plugin was found.

## Sources (all accessed 2026-10-10)

- S1 https://raw.githubusercontent.com/PCSX2/pcsx2/master/pcsx2/Config.h
- S2 https://github.com/PCSX2/pcsx2/pull/4944
- S3 https://api.github.com/repos/PCSX2/pcsx2/releases?per_page=5
- S4 https://en.wikipedia.org/wiki/PCSX2
- S5 https://raw.githubusercontent.com/PCSX2/pcsx2/master/COPYING.GPLv3
- S6 https://www.teamxlink.co.uk/wiki/PCSX2_XLink_Kai_Setup
- S7 https://ravenrepublic.net/wiki/Emulation/PlayStation2
- S8 https://en.wikipedia.org/wiki/PlayStation_2_online_functionality
- S9 https://github.com/alexsharoff/pcsx2-online
- S10 https://api.github.com/repos/alexsharoff/pcsx2-online
- S11 https://github.com/SmileTheory/pcsx2
- S12 https://api.github.com/repos/SmileTheory/pcsx2
- S13 https://github.com/fraserofsmeg/pcsx2-online-Update
- S14 https://api.github.com/repos/fraserofsmeg/pcsx2-online-Update
- S15 https://github.com/YungMoniCA1/pcsx2-netplay-reborn
- S16 https://github.com/TimeFlex1/pcsx2-netplay-reborn-update
- S17 https://api.github.com/search/repositories?q=pcsx2+netplay&sort=updated&per_page=30
- S18 https://github.com/q13007868130/git-demo/pull/1
- S19 https://github.com/q13007868130/git-demo
- S20 https://api.github.com/repos/q13007868130/git-demo
- S21 https://github.com/q13007868130/git-demo/issues/2
- S22 https://arkadyzja.honmaru.pl/
- S23 https://api.github.com/repos/Arkadyzja/ArkadyzjaClient and https://api.github.com/repos/Arkadyzja/ArkadyzjaClient/releases?per_page=5
- S24 https://parsec.app/pricing
- S25 https://docs.libretro.com/library/lrps2/
- S26 https://docs.libretro.com/library/play/
- S27 https://en.wikipedia.org/wiki/Fightcade
- S28 https://flathub.org/apps/com.fightcade.Fightcade
- S29 https://github.com/srbengueros/AnyGameAnywhere
- S30 https://raw.githubusercontent.com/srbengueros/AnyGameAnywhere/main/README.md
- S31 https://api.github.com/search/repositories?q=pcsx2+online+multiplayer&sort=updated&per_page=20
- S32 Web search "\"Nyxx\" PCSX2 netplay" (no matching project)
- S33 https://github.com/PCSX2/pcsx2/issues/772
- S34 https://github.com/PCSX2/pcsx2/issues/8425
- S35 https://github.com/PCSX2/pcsx2/pull/11997
- S36 https://pcsx2.net/blog/2014/config-guide-1-2-1
- S37 https://github.com/libretro/docs/blob/master/docs/guides/netplay-faq.md

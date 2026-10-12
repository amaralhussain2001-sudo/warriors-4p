# warriors-4p network protocol and sync model (W4P protocol version 3, helper w4p-net)

Deliverable 5 of the brief. Describes what is implemented in build w4p-m6-3 (fork `emulator/pcsx2/pcsx2/W4P/W4P.cpp`) and
the connection helper (`net/w4p-net/src/helper.cpp`, `codec.cpp`). Line numbers refer to those files at fork commit
b81b4cc and project commit of 2026-10-12. Design notes: `docs/research/m5_connection_design.md` (signaling, topology,
security), `docs/research/m5_disconnect.md` (disconnect handling), `docs/research/session_policies.md` (pause, skip,
leave, restart).

## 1. Layers
```
 game (PS2 EE, deterministic)  <- pad-read hook: W4P::OnGuestHook (per pad poll)
 W4P lockstep module (inside our PCSX2 build)     UDP, 127.0.0.1:<emu port> <-> helper slot ports
 w4p-net helper (separate process, one per PC)    ICE/UDP through libjuice (host / srflx candidates, STUN at Cloudflare)
 internet / LAN
```
- Each PC runs one emulator and one helper. The emulator talks plain UDP to its local helper; the helper carries the
  emulator's datagrams to the other PCs' helpers over ICE (full mesh; a joiner pair without a direct path is forwarded
  through the host). On a LAN the launcher can also connect emulators directly (Join by IP), without the helper.
- Everything that affects the simulation happens in the emulator; the helper only moves opaque datagrams.

## 2. W4P datagrams (emulator <-> emulator), little-endian, packed
Common header `PktHeader` (12 bytes, W4P.cpp:85): `u32 magic = 0x4E503457 ("W4PN")`, `u16 version = 3`, `u8 type`,
`u8 slot` (sender's player slot 0-3), `u32 c0` (the guest poll counter at which the sender's session started).
Datagrams with another magic are ignored; another version is logged ("rejected datagram with protocol version") and
ignored; a slot outside the session's player count is ignored.

| Type | Name | Body after the header | Sent | Purpose |
|---|---|---|---|---|
| 1 | Inputs | `u32 first_t, u16 count`, then `count` x `Input` (20 bytes: `u16 buttons`, 4 stick bytes, 12 pressure bytes, `u8 valid`, `u8 reserved`) | every new poll and every 50 ms (15 ms while waiting) | the sender's last up-to-32 polls of input (`kResendBurst`, redundancy against loss) |
| 2 | Hashes | `u16 count`, then `count` x `HashEntry` (`u32 t, u64 kernel, u64 game`) | with the inputs | 64-bit hashes of EE RAM below 0x000A0000 (BIOS kernel) and from 0x000A0000 (game + our patch data), every `hash_interval` polls (30) |
| 3 | Hello | `u32 disc_crc, u32 bios_version, u64 settings_fp, u64 patch_fp, u8 players, u8 input_delay, u16 hash_interval, u8 started, 3 pad, char build[16], char bios[48]` | until every peer answered, again after the start | handshake / fingerprint (section 3) |
| 4 | Status | `u32 stall_t, u8 timed_out, 3 pad` | every 250 ms while waiting for a missing player | disconnect handling: where each instance is stalled and whether its timeout passed |
| 5 | Drop | `u8 player, u8 choice (1 continue, 2 restart), u16 pad, u32 from_t` | by the host after the timeout | the host's decision: the player's input is neutral from poll `from_t` |
| 6 | Relay | `u8 player, u8 pad, u16 count, u32 first_t`, then `count` x `Input` | by every remaining instance after a drop | each instance's copy of the leaver's last inputs, so all have them up to `from_t` |

## 3. Versioning and handshake
1. **Protocol version** in every header (`kProtocolVersion = 3`; 2 added Hello and the kernel/game hash split, 3 added
   Status/Drop/Relay). Mismatched versions do not talk at all.
2. **Lobby checks** (launcher, `package4/Start-Coop.ps1` `Problem-Text`): before the host can start, every player's
   package version (the id in `VERSION.txt`), game patch file, game file (The Warriors USA v1.03) and co-op save must
   match the host's; otherwise that player shows a PROBLEM line instead of "ready". All PCs also get the same PCSX2
   settings profile from the package.
3. **Hello / fingerprint** (W4P.cpp:511-588): every instance sends Hello until each peer has answered. After the start
   each pair compares: emulator build tag (`w4p-m6-3`), disc CRC (game version), BIOS version and description,
   a fingerprint of every emulation setting that changes the simulation (recompilers, FPU modes, speed hacks, EE cycle
   rate/skip, game fixes, patches/cheats/widescreen switches, fast boot, RTC), the game patch set fingerprint (60 fps /
   widescreen), players, input delay and hash interval. Any difference is logged and shown ("Player N differs in: ...").
4. **Start state**: the session starts at the first pad poll of the booted game on each PC (`c0`, W4P.cpp:1104); every
   header carries `c0`, and a peer with a different `c0` is reported ("players started from different states").

## 4. Sync model (deterministic lockstep with input delay)
- **Unit of time = one game pad poll** (the game's pad-read routine, hooked at 0x001498E0 by `[warriors-4p M1]`; at 30
  fps one poll per frame, 60 per second at 60 fps).
- **Input delay D** (2 by default; the launcher picks D from the measured round-trip time:
  ceil((p90 RTT + 15 ms) / (2 x frame time)), at least 2): the local input sampled at poll t is used at poll t + D.
  Polls c0 .. c0+D-1 use neutral input on every PC.
- **Frame gate**: at poll t the emulator writes every player's input for t into the game's pad buffers (`WriteInput`);
  if any player's input for t is missing it **holds the EE** (no game time passes) and keeps receiving / resending
  until it arrives (`NewPoll`, W4P.cpp:1466; `WriteInput` 1079). After 500 ms it shows "Waiting for Player N..." and re-presents the last
  frame. Because every PC applies identical inputs at identical polls and the emulation is deterministic (MTVU off,
  same settings, same patches), every PC computes the same game state.
- **Inputs are redundant**: each Inputs packet repeats the last 32 polls, so a lost packet costs nothing unless 32
  packets in a row are lost; late inputs are accepted until the poll is executed.
- **Determinism rules found necessary** (findings): MTVU off (F-0120, F-0150); the game memory hash starts at 0x000A0000
  so BIOS leftovers do not count (F-0125); session-relative test calls only at exact polls (CallAt, mailbox 0x000F0300).

## 5. Desync detection and recovery
- Every `hash_interval` (30) polls each instance hashes EE RAM (kernel part and game part) and sends the hashes; the
  peers compare equal polls (`CompareHashes`, W4P.cpp:1022). A game-hash difference is logged as `DESYNC` and shown as "OUT OF SYNC with
  Player N (poll ...)" for 60 s; a kernel-only difference is logged as a note (different BIOS files).
- **Recovery** is not automatic: the players restart from the last checkpoint (pause menu "Restart" / GAME OVER "Last
  checkpoint"), which reloads the level from the saved checkpoint on every PC; the logs and an optional RAM dump help to
  find the cause. Measured desync frequency in every test so far: 0 (M7 report).

## 6. Disconnect protocol (`docs/research/m5_disconnect.md`)
1. A player is **gone** when nothing at all arrived from him for 2 s; everybody stalls at the first poll his input is
   missing and sends Status packets; the countdown (60 s, `DisconnectTimeoutS`) runs from his last packet.
2. **Back in time**: his packets return, the stalled polls complete, play continues (T1g: 20 s and 45 s outages, F-0219).
3. **Timeout**: each instance stops accepting his inputs; non-hosts wait for the host's choice; the host presses Cross
   (continue) or Circle (restart from the last checkpoint). The host sends **Drop** with `from_t` = the highest poll any
   remaining instance needs; every remaining instance sends **Relay** with its copy of his inputs up to `from_t`, so all
   apply exactly the same inputs before `from_t` and neutral input after it; then the game-side LEAVE (continue) or a
   checkpoint reload (restart) runs at the same poll everywhere (F-0164..F-0170).
4. **Host leaves**: the session ends on every PC ("The host has left").

## 7. Session policies on top of the inputs (W4P.cpp ~1180-1360, `session_policies.md`)
Computed identically on every PC from the synchronized inputs, so they need no extra packets:
- **Pause**: any player's Start (or Esc) opens the pause on every PC ("Paused by Player N"); only that player or the host
  can resume.
- **Cutscene skip votes**: a scene or movie is skipped when every connected player pressed Cross or Start ("2/4 want to
  skip").
- **Sit-out screen**: a player without a character sees a waiting message (cutscenes and shared single views pass
  through, F-0208/F-0210).
- **Hideout interlude**: in level 95 only the host plays; the others see "Host is in the hideout - next: Mission N".
- **Auto re-join (X11)**: in quiet gameplay a player 3/4 without a character is joined through the game's own UpdateJoin
  every 60 polls (F-0183, F-0209).

## 8. Helper datagrams (helper <-> helper, `net/w4p-net/src/helper.cpp`)
`[u8 type, u8 src slot, u8 dst slot, u8 flags]` + 8-byte session tag + payload + 8-byte SipHash-2-4 MAC with the link's
key (`Wrap`, `OnRecv` ~780). Types: `D` game data (the W4P datagram as payload, delivered to the local emulator),
control (`CT_PING`/`CT_PONG` with timestamps for RTT, lobby messages, slot assignment, forwarding), probe (connection
test). Only authenticated datagrams are acted on; strangers get no reply. Forwarded datagrams carry flag `kFlagFwd`.
Join codes (`W4P1-...`) carry the host's ICE description, credentials and session key in a short checksummed text
(codec.cpp; `m5_connection_design.md` 1.4). Test switch (tests only): `mute SECONDS [SLOT]` drops game data (F-0219).

## 9. Bandwidth (measured, F-0221)
About 0.34-0.35 Mbit/s per link and direction at 60 polls/s including the helper's wrapping and pings; a 4-player PC
has 3 links: about 1 Mbit/s up and 1 Mbit/s down at 60 fps, half at 30 fps.

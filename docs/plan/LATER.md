# Features for later (agreed with the user, not started)

Planned features the user asked to keep for later. Nothing here is built yet. Before starting one: re-read it, check
the open questions with the user, then plan, build, test (SINGLE-PC first), package and push like every change.

## 1. Positional voice chat through Mumble (user request 2026-10-13: "we will do it later")
**Goal:** players hear each other from the direction and distance of their characters in the game (louder when close,
from the left when the speaker stands to the left), while playing online.

**Approach (HYPOTHESIS until built):** no new Mumble plugin. Mumble already ships the **Link** plugin: any program can
fill a shared-memory block (`MumbleLink`, struct `LinkedMem`: avatar position/front/top, camera position/front/top,
identity, context) and Mumble places the voices from it. Our emulator fork knows everything needed on every PC (every
PC computes all players), so it only has to write that block about 30 times per second:
- avatar = this PC's own player: position and facing (player handles at GameMgr+0x228 + 4*slot, as used by the
  markers34 / camtarget code; exact position/facing offsets to confirm);
- camera = this PC's own view camera (the per-player follow camera; for players 3-4 the camtarget cameras);
- context = the W4P session id, so only players of the same game are positional to each other;
- identity = player slot (1-4).
**Determinism:** read-only access to EE RAM after the frame, never written: cannot change the game state, so it cannot
desync (still to be confirmed by a 4-instance run with 0 mismatches).

**Work estimate:** about one day.
| Step | Estimate |
|---|---|
| Emulator: write the Link block (Windows shared memory "MumbleLink"), own player + own camera, session context | 3-4 h |
| Units and axes: game units to metres, axis order (Mumble: left-handed, Y up), so voices fade at ~20-30 m | 1-2 h |
| Launcher option "positional voice: on/off", README section (install Mumble, enable Link + positional audio) | 1 h |
| Tests on this PC: the Link values follow the players (4 instances), 0 desync; package + self-test | 1-2 h |

**Open questions for the user (decide before starting):**
1. **Mumble server:** (a) run the free server "Murmur" on one player's PC (friends outside the house may need a router
   port opened: the user's decision, we never change routers or firewalls ourselves), or (b) rent a small Mumble server
   (costs money, needs an account: the user's decision). A recommendation with pros and cons first.
2. Every player installs the Mumble client themselves (free; system-wide install: the user does it).
3. A real voice test needs at least 2 PCs and people (cannot be proven on one PC).
Options already offered: A build the Link part first and test the numbers, then choose the server (recommended);
B decide the server first; C no positional voice (Discord / WhatsApp voice instead).

## 2. Smaller ideas waiting for a decision
- **Controller button for "your view / all views" on every Xbox controller:** today Tab (keyboard), the PlayStation
  touchpad, or the Xbox Series Share button (not tested). Idea: also the Xbox (Guide) button; Windows opens the Game Bar
  on it unless switched off in Windows Settings > Gaming > Xbox Game Bar. Offered as option B (A = keep Tab for now).
- **START-HERE refreshes the game/BIOS paths at every start:** then the co-op folder can be moved anywhere at any time
  (today: after moving it, delete my-settings.txt and start START-HERE.bat again). Offered, not chosen yet.
- **Joining a game that already runs (drop-in):** today players join only in the lobby (the user's own session rule,
  brief 4.6). Would need the running game's state sent to the new PC - a big job and a change of that rule; only if the
  user decides so. (Joining a story in the middle is already possible between games: the host's save is sent in the
  lobby, F-0236.)

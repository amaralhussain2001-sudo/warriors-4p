# Tests only you can do (with your second PC and your friends)

Everything else is tested on this one PC with bots. These tests need real PCs, real networks and real people, so they
decide the final mission statuses (BRIEF 8.4: "FOUR-PLAYER ONLINE VERIFIED" needs 4 separate PCs over the internet).
Use the newest package `dist/warriors-4p-coop.zip` (its id is in `VERSION.txt` and in my last message; every PC must use
the identical zip). Each test says what to send back. Logs: after each game every PC's black window names its folder
`logs\<date>_<time>_...` - zip that folder and send it to me. Logs contain no game files.

## Test A - two PCs in your house (LAN), about 30 minutes
1. Copy the zip to the second PC, unzip both, run `Start-Coop.bat` once on each (choose your .iso and BIOS).
2. PC 1: `1` Host, 2 players, `1` join code, save name `lan1`, 60 fps **no**, widescreen yes. Copy the join code.
3. PC 2: copy the code (e.g. by chat or a text file), `2` Join. If Windows asks about "w4p-net" or "pcsx2-qtx64":
   tick "Private networks", "Allow access".
4. When PC 2 shows "ready", press `S` on PC 1. Start a new story with "2 PLAYER" and play Mission 1 for 15 minutes:
   walk, fight, use Flash, let one player get knocked down and revive him, pause with Start once.
5. **Outage test:** on PC 2 pull the network cable (or switch Wi-Fi off) for about **20 seconds**, then plug it back.
   Expected: both screens freeze with "Waiting for Player 2...", then the game continues. Then do the same for about
   **45 seconds**. Then for about **90 seconds**: after 60 s PC 1 gets "continue without him / restart" - press Cross.
6. Repeat steps 2-4 with "Join by IP address" (`3` on PC 2, type PC 1's address shown by the host window).
7. Send back: both log folders, and a short note: did anything look wrong, how did the controls feel (any delay you
   noticed), did the outage test behave as expected.

## Test B - friends over the internet, connection check only (5 minutes, no game needed)
1. Every friend unzips the same package and runs `Start-Coop.bat` once. The host hosts (4 players, join code), every
   friend joins. When everybody shows "ready", wait 2 minutes **without pressing S** (the helpers measure the
   connections meanwhile), then close the host window.
2. Send back: every PC's log folder. I check that every pair of PCs connected directly and how fast (round-trip times).

## Test C - game sessions with friends over the internet (2, then 3, then 4 players, 20-30 minutes each)
1. Host as in the QUICK-START (save name e.g. `friends`, 60 fps yes if all PCs are fast, otherwise no).
2. Session 1 with 2 players, session 2 with 3, session 3 with 4. Play the story where you are (or start a new one).
3. During the 4-player session please also try: pause (Start), skip a cutscene (everybody presses Cross), Tab / touchpad
   to switch "your view / all views", one player leaving and coming back.
4. Send back: every PC's log folder after each session, and notes: freezes ("Waiting for..."), "OUT OF SYNC", crashes,
   wrong cameras or HUD, anything that differs between players 1-2 and players 3-4.

## Test D - mission play-through (the only way a mission can reach a final status)
Bots cannot finish missions, so each mission needs one real play from start to completion with 4 players (and one
session each with 2 and 3 players over the whole set). Order suggestion: as the story goes. For every mission please
note (one line per mission is enough): finished yes/no; anything wrong (stuck, desync, crash, camera, HUD, a player who
could not join or was left out); which checkpoint restarts happened.
Places that changed recently and need a human look:
- **Mission 8 cart chase** (players 3-4 are Snow and Ajax and tap to run in front of the cart) and **Mission 18 car
  escape** (players 3-4 are Cochise and Vermin and tap like players 1-2; one button icon for everybody).
- **Camera parity** (players 3-4 now get the same special cameras as players 1-2): Mission 16 chases (cp1 side-scroller,
  cp3 park), Mission 6 rooftop chase, Mission 9 cage, Mission 17 Lizzie boss, Mission 8 Chatterbox boss, Mission 1,
  Mission 3 club tutorial, Mission 18 beach. Check that all four players see a similar picture and that nobody's camera
  jumps to another player.
- **HUD** for players 3-4: Select health ring, radar arcs (timer ring) on all four radars.
- Hideout between missions: players 2-4 see "Host is in the hideout - next: Mission N. Please wait." and come back in
  the next mission.
Send back: the log folders and your notes.

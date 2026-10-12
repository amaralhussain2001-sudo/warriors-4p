THE WARRIORS - ONLINE CO-OP FOR 2 TO 4 PLAYERS (warriors-4p, TEST VERSION)
==========================================================================

What this test is for
---------------------
Two, three or four PCs play The Warriors (PS2) together. Each PC runs the game itself; only the button presses travel
between the PCs. This is an experimental TEST. So far it has only been tried on ONE PC (several copies of the game on
the same computer, played by scripted "bots"). Your test shows whether it works between real PCs.

If the PCs ever stop computing the same game, every screen shows "OUT OF SYNC". That is a useful result too - just
tell us (step 10).

What each PC needs
------------------
1. Windows 10 or 11 (64-bit).
2. This whole folder. Everybody must use the SAME zip file (the lobby checks it).
3. Its own copy of The Warriors for PS2, USA version 1.03, as an .iso file. (The launcher checks it the first time;
   that takes about half a minute.)
4. Its own PS2 BIOS file, dumped from a PS2 you own. The same BIOS version on every PC is best.
   This package does NOT contain any game or BIOS files.
5. A keyboard or a game controller.
6. For playing from different homes: an internet connection. In the same house: the same router (Wi-Fi or cable).

Step 1 - Unzip
--------------
Unzip warriors-4p-coop.zip on every PC, for example to the Desktop. Do not run it from inside the zip.

Step 2 - First start (every PC)
-------------------------------
Double-click Start-Coop.bat.
- Windows may say "Windows protected your PC" (the program is not signed): click "More info", then "Run anyway".
- The first time it asks for your game file and your BIOS file (a window opens to pick them), the picture quality
  (just press Enter for the suggested value) and full screen yes/no.
- Your answers are kept in my-settings.txt. Change them later with "4 Settings" in the menu.
Then the menu appears:
    1  Host a game (2, 3 or 4 players)
    2  Join a game (paste the join code from the host)
    3  Join by IP address (same house / same router)
    4  Settings
    5  Quit
One player is the HOST (Player 1). Everybody else joins.

Step 3 - The host creates the game
----------------------------------
The host chooses 1 (Host a game) and answers:
- How many players, including you: 2, 3 or 4.
- How the others connect:
    1 = with a JOIN CODE (works over the internet and in the same house) - recommended.
    2 = by IP ADDRESS (same house only, no codes; see step 5).
- Which co-op save: a name for your group of friends, for example "main". A new name starts the story from the
  beginning. (Step 9 explains co-op saves.)
- 60 fps and widescreen: the host decides for everybody (both "yes" is the default).
  IMPORTANT for this test version: in our own tests the title screen ("PRESS THE START BUTTON") did not react to
  Start in 60 fps mode. Please answer "no" to 60 fps first. If you want to try 60 fps and the title screen ignores
  Start, close the games and host again with 60 fps "no" - and tell us.
With a join code: the window shows a JOIN CODE that starts with W4P1- (for example W4P1-24B78-SJYMR-...) and it is
already copied. Paste it into your group chat (WhatsApp, Discord, e-mail, ...).

Step 4 - The others join with the code
--------------------------------------
Each friend copies the join code from the chat and chooses 2 (Join a game). If the code is in the clipboard, the
launcher finds it by itself; otherwise paste it (right-click or Ctrl+V) and press Enter.
- Wait about 10 seconds. Usually the window says "Connected. You are Player 2" (or 3, 4).
- If it does not: the friend's window shows a REPLY CODE (also starting with W4P1-) and copies it. The friend pastes
  it into the chat. The host copies it and presses R in the host's window. Both keep trying for 10 minutes, so nobody
  has to hurry.
- If someone can still not connect: try another player as the host, or play in the same house with step 5.

Step 5 - Same house without codes: Join by IP address
-----------------------------------------------------
The host chooses 1 (Host a game), then 2 (by IP address). The host's window shows its address, for example
192.168.1.23. Each friend chooses 3 (Join by IP address) and types that address.

Windows Firewall
----------------
The first time, Windows may ask whether a program may use the network: "w4p-net" (with codes), or "Windows
PowerShell" and "pcsx2-qtx64" (Join by IP address). Tick "Private networks" and click "Allow access". Do this on every
PC, otherwise the PCs cannot reach each other. Nothing in this package changes your firewall or router by itself.

Step 6 - The lobby and the start
--------------------------------
The host's window lists every player: "ready", "connecting...", the ping in milliseconds, or a PROBLEM in plain words:
- "different package version" or "different game patch file": everybody must use the same zip file.
- "game file is not The Warriors (USA) v1.03": that PC needs the right game file (Settings).
- "different co-op save": see step 9.
It also shows the input delay it chose from the slowest connection (2 frames is the normal minimum).
When everybody is "ready", the host presses S. Every PC then starts the game by itself.

Joining only in the lobby: someone who arrives after the host pressed S cannot join that game. They wait until the
game is over; then the host chooses "Host a game" again (this makes a new join code) and everybody joins the new lobby.

Step 7 - Play
-------------
- Player 1 (the host) controls the menus. Start the story with "2 PLAYER"; Player 2 presses Start to join, as in the
  original game.
- Players 3 and 4 press Start during a mission to join. IMPORTANT for this test version: this has only been checked in
  mission 13 ("All-City"). In mission 1 (the tutorial) players 3 and 4 cannot join yet; other missions are not tested
  yet. So a test that starts a new story is mainly a test for 2 players.
- Start pauses the game for everybody ("Paused by Player N"). Only that player or the host can resume.
  (Esc is meant to do the same; that has not been tested yet.)
- Cutscenes are skipped only when everybody presses a button ("2/4 want to skip").
- Tab (keyboard) or the touchpad / share button (controller) switches between YOUR view and ALL players' views.
- Savestates and fast-forward are switched off on purpose during online play.
- If a player's connection drops, everybody waits with "Waiting for Player N... 60s". If he does not come back in
  time, the host chooses: Cross = continue without him, Circle = restart from the last checkpoint without him.
  If the host leaves, the game is over for everybody.
Please do a bit of everything: fight, run, grab, use items, stand together, split up, get knocked down, lose a fight
(game over) and continue from the checkpoint, pause, skip a cutscene.

Keyboard controls (a controller also works)
  Move: W A S D        Camera: T F G H        D-pad: arrow keys
  Square J   Cross K   Circle L   Triangle I
  L1 Q   R1 E   L2 1   R2 3   L3 2   R3 4      Start Enter   Select Backspace

Step 8 - Closing
----------------
Close the game window when you are done (all players at about the same time). Keep the Start-Coop window open while
you play; after the game it tells you whether the co-op progress was saved and where the logs are.

Note: this package is only for online co-op. For single-player or for 2 players on one PC, use your own PCSX2 as
before; do not start emulator\pcsx2-qtx64.exe from this folder directly. The co-op patches are switched on only
inside a session started by Start-Coop.bat (they would change the original 2-player split screen).

Step 9 - Co-op saves (your progress together)
---------------------------------------------
- Co-op progress is kept in this package's folder: coop-saves\<save name>\ (files Mcd001.ps2 and Mcd002.ps2).
  It never uses or changes the memory cards of your own PCSX2 or your single-player saves.
- Every PC keeps its own copy. It is updated only when the game ended normally (in sync, closed normally).
- All PCs must start with exactly the same co-op save. The lobby compares them ("check code") and the host cannot
  start while they differ.
- THE HOST'S SAVE IS THE REFERENCE. If a player's save is different: on the host's PC, open the folder
  coop-saves\<save name> (Settings, option 7 opens coop-saves). Copy the files Mcd001.ps2 and Mcd002.ps2 (for example
  with a USB stick, or send them through a chat or a cloud drive). On the other PC, put them into its
  coop-saves\<save name> folder (create the folder if it is missing) and replace the old files. Then join again.
- A new save name starts the story from the beginning on every PC (nobody has files yet, so all match).
- Older copies are kept in coop-saves\<save name>\backup\ (the last 5).

Step 10 - Send the logs back
----------------------------
After the game, every PC's window shows its log folder: logs\<date>_<time>_<host|join|lanhost|lanjoin>.
Please send that whole folder from EVERY PC (zip it, or copy it to the main PC into warriors-4p\incoming\). Also tell us:
- which PC was which player, and each PC's processor and graphics card (if you know them);
- how you connected (join code, reply code needed or not, or IP address) and whether Windows asked about the firewall;
- how the controls and 60 fps felt, and anything strange (freezes, "Waiting for Player", "OUT OF SYNC").
The logs contain no game files. The connection log never contains the codes or IP addresses; the lobby log of
"Join by IP" contains home-network addresses (like 192.168.1.23).

Privacy
-------
A join code contains the host's internet address. Share it only with the friends who play. A code is useless once
the host closes the lobby (every game has a new code).

Licence
-------
The emulator in the "emulator" folder is a modified PCSX2 (GPL-3.0); our changes are in the "source" folder
(SOURCE.txt explains how to rebuild it). The connection helper net\w4p-net.exe is our own program (GPL-3.0-or-later,
source in source\w4p-net) and uses libjuice (MPL-2.0, licenses\libjuice-LICENSE.txt). To learn this PC's internet
address it asks Cloudflare's public STUN server (stun.cloudflare.com). Microsoft's Visual C++ runtime files next to the
programs are included as allowed by Microsoft's redistribution terms. Details: THIRD-PARTY-NOTICES.txt.

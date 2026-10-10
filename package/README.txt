THE WARRIORS - ONLINE CO-OP TEST (warriors-4p, experimental)
=============================================================

What this test is for
---------------------
Two PCs play The Warriors together. Each PC runs the game itself and only the button presses travel over the
network. This test checks the most important question: do two DIFFERENT PCs compute exactly the same game?
If they ever stop matching, both screens show "OUT OF SYNC". That is a useful result too - just tell us.

This build supports 2 players. Players 3 and 4 are still in development.

What each PC needs
------------------
1. Windows 10 or 11 (64-bit).
2. This whole folder (copy it to each PC, e.g. on a USB stick).
3. Its own copy of The Warriors for PS2, USA version 1.03, as an .iso file.
   (The launcher checks this the first time; it takes about half a minute.)
4. Its own PS2 BIOS file, dumped from a PS2 you own. Using the SAME BIOS version on both PCs is best.
   This package does NOT contain any game or BIOS files.
5. A keyboard or a game controller.

Both PCs must be on the same home network (same router, Wi-Fi or cable).
Playing from two different homes needs extra setup that is not part of this test.

Step 1 - find each PC's address
-------------------------------
On each PC: press the Windows key, type cmd, press Enter. Type   ipconfig   and press Enter.
Look for "IPv4 Address", for example 192.168.1.23. Write down both PCs' addresses.

Step 2 - start on BOTH PCs
--------------------------
Double-click Start-Coop.bat. The first time it asks:
- Player 1 or 2: one PC is 1, the other is 2.
- The OTHER PC's address (from step 1).
- Your game file and your BIOS file (a window opens to pick them).
- Picture quality (just press Enter for the suggested value).
- 60 fps mode and widescreen: give the SAME answers on both PCs.
- Full screen: your choice.
Your answers are saved in my-settings.txt (change them there, or start with: Start-Coop.bat -Reset).

Windows may show "Windows protected your PC" because this program is not signed: click "More info", then
"Run anyway". The first time, Windows Firewall asks about PCSX2: tick "Private networks" and click "Allow".
Do this on both PCs, otherwise they cannot see each other.

The game waits with "Waiting for Player ..." until both PCs are running. Then it shows "Connected to Player ...".
If it says a player "uses different ..." something does not match (for example 60 fps on one PC only):
close both games, fix my-settings.txt, start again.

Step 3 - play (about 20-30 minutes)
-----------------------------------
- Player 1 controls the menus. The memory cards start empty every time (that is intended for this test).
- Start the story and choose 2 PLAYER. Player 2 controls the second Warrior.
- Please do a bit of everything: fight, run, grab, use items, stand together, split up, get knocked down,
  lose a fight / game over and continue from the checkpoint.
- Tab (keyboard) or the touchpad / share button (controller) switches between YOUR view and ALL players' views.
- Esc opens the pause menu. While one player is paused, the other player waits. Savestates and fast-forward are
  switched off on purpose.

Keyboard controls (a controller also works)
  Move: W A S D        Camera: T F G H        D-pad: arrow keys
  Square J   Cross K   Circle L   Triangle I
  L1 Q   R1 E   L2 1   R2 3   L3 2   R3 4      Start Enter   Select Backspace

Step 4 - send the logs back
---------------------------
When you close the game, the window shows where the logs are: the folder logs\<date>_player1 (or player2).
Copy that folder from BOTH PCs to the main PC (into warriors-4p\incoming\) and say which PC was which
(processor and graphics card, if you know them). Please also say how the controls felt and anything strange.

Licence
-------
The emulator in the "emulator" folder is a modified PCSX2 (GPL-3.0). The changes are in the "source" folder
(SOURCE.txt explains how to rebuild it). Microsoft's Visual C++ runtime files next to the emulator are included
as allowed by Microsoft's redistribution terms.

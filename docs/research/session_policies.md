# Session policies (BRIEF 4.6): game-side mechanics for pause, cutscene skip, player leave, checkpoint restart

Date 2026-10-11. Build SLUS-21215 v1.03 (ELF `SLUS_212.15`). Sources: decompile `local/analysis/all/*.c`, Ghidra
listings (`tools/ghidra/DumpListing.java`, read-only), pseudo-Lua `local/analysis/pseudo/`, ELF words read directly.
Function and object names are OUR labels (the ELF is stripped). Addresses are EE virtual addresses; "static" = inside
the ELF image (.text/.data/.bss), "dynamic" = heap (GameMgr = 0x01FD8400 in every run here). Runtime results: SINGLE-PC,
one instance, scripted input (bots), no impairment, `tests/m2/nav_probe.py` with the standard Mission 13 setup of
STATE.md (level jump by W4P CallAt at polls 4000/4010, players 3-4 by the game's own Start-join), MTVU off, emulator
build w4p-m3-7 (runs A, B1, B2, C) and w4p-m5-1 (runs D, E, E2, C2, C3, C4; single-instance behaviour of W4P unchanged). Screenshots
are taken with the crop OFF, so one picture shows all four quarters. Probe module: `tests/m2/sp_probe.py`.
Labels: VERIFIED / HYPOTHESIS / BLOCKED / FAILED TEST. Finding IDs are not assigned here (FINDINGS.md is kept by the
coordinator); section 7 lists the results ready to register.

## 0. Answers in short
| Question | Answer | Label |
|---|---|---|
| How does the game pause? | Start (game code 0x0800) on a player's own pad in the in-game update FUN_00158728 pushes the pause game mode 0x005E6550 (mode id 10) on the mode stack; the pause menu (story: object 0x0062E790) is driven only by the pad of the player who paused (menu+0x1BC0 = his player index) | VERIFIED code + run A |
| Players 3-4 and pause | their Start is ignored by our `[4p]` main-loop cave (0x00158ECC, index >= 2 skipped); confirmed at runtime | VERIFIED code + run A |
| What does a pause freeze? | the whole in-game update: game clock (GameMgr's GameClock 0x0050B734 +0x48), FrameStats 0x0050C654, Lua scheduler, Lua pad handlers, AI/physics; pads are still read every frame, so the W4P lockstep keeps running (no stall) | VERIFIED run A (clock and frame counter constant for 400 polls while polls advanced) |
| Clean lockstep pause by any player | yes: a W4P input filter (fork) turns any connected player's Start into a Start on player 1's pad at the same poll, records who asked, and while paused routes only that player's and the host's input to the menu pad; 1 optional game word lets a downed player 1's pad open it; 2 words remove the menu's "Player 2: continue in 1 player mode" drop-out | design VERIFIED by runs A/D; filter not built (HYPOTHESIS until 4-instance test) |
| Cutscene skip | three kinds: Bink movies (any button on any of the 8 pads skips), in-engine scenes (Cross or Start HELD on any current player's pad skips once a 60-frame countdown has run out; Start also sets "skip the following chained scenes"), Lua POIZO camera sequences (Cross/Start on players 1-2 only) | VERIFIED code; movies and scenes also runs B1/B2; POIZO code only |
| Flag W4P can read | scenes: the scene slot table 0x006EBA18 (12 x 0x40, static) -> scene player (+0x24, dynamic): state, skippable +0xE5, countdown +0xE0, skipping +0xE4; GameMgr+0x410 = 3 during a cinematic. Movies: no clean flag exists -> 17-word patch (flag 0x000E70F0 set around the movie loop's pad read) | VERIFIED runs B1/B2/D |
| Original player leave | only through the pause menu (Quit -> "Player 2: Continue game in 1 player mode", FUN_001DF3A8): 2-player flag off, then the leave loop of UpdateJoin FUN_0041A460 releases EVERY drop-in player (ReleasePlayer FUN_0022A2A8, leave script event, camera, layout) | VERIFIED code + strings |
| Leave one player in all PCs at one poll | a 114-word cave LEAVE(player index) = the game's own leave-loop body for one player + fixes for players 3-4 (index shift: cameras, pad owners, UpdateJoin(-1)); called through the W4P call mailbox (`LeaveCalls = 0:000E7100:P`) | VERIFIED runs C/C3 (single instance); first version crashed (C2, FAILED TEST) |
| Restart from checkpoint | MenuLoadLevel core FUN_00160D78(GameMgr+0x124) through the call mailbox (`RestartCalls = 0:00160D78:GM+0x124`) = the GAME OVER menu's "Last checkpoint"; needs R8 (F-0153); players 3-4 re-join with Start, player 2 is re-created automatically while the 2-player flag is set, so for a dropped player 2 clear it first (FUN_00419AC0(GameMgr,0)) | VERIFIED runs C, C3, C4 (+ F-0155, F-0160) |

## 1. Pause

### 1.1 Mode stack and the pause mode (VERIFIED code)
- The game runs a stack of game-mode objects: top index s32 `0x0050C784`, stack of pointers `0x005E66A0` (static).
  Push FUN_0015E5E8, pop FUN_0015E650 (exit of the popped mode, resume of the next), loop FUN_0015E6B8 calls only the
  TOP mode's update (FUN_00156100 -> vtable +0x3C). In a mission the stack is [loading 0x005E5D90, in-game 0x005E56B8].
- Pause mode object `0x005E6550` (static), vtable 0x005386E8 (set by FUN_0015DF68): mode id getter 0x004DDED0
  (`jr ra; li v0,10`), enter FUN_0015DBB8, update FUN_0015DD98, exit FUN_0015DD38.
- **Paused** = `*(0x005E66A0 + 4 * *(0x0050C784)) == 0x005E6550`. Runtime run A: stack ['0x5e5d90','0x5e56b8',
  '0x5e6550'] while the menu was open, ['0x5e5d90','0x5e56b8'] otherwise (`local/m2/sp_pause/probes.json`).
  GameMgr+0x56E0 is NOT a pause flag (it stayed 1 the whole run).
- Toggle FUN_00154F28 (our label PauseToggle): if pause menu+0x20AC (cooldown counter, 0x0063083C for the story menu,
  decremented each frame by HudUpdate FUN_001AF010) is non-zero -> nothing; if the top mode is not 10 -> push the
  pause mode; else pop it and act on the menu's result words (+0x1B74 restart level: FUN_0041CEF0(GameMgr,1) +
  MenuLoadLevel(GameMgr+0x124); +0x1B78 last checkpoint: FUN_0041CEF0(GameMgr, GameMgr+0x33A) + MenuLoadLevel;
  +0x1B70/+0x1B94/+0x1B98/+0x1B9C quit variants: GameMgr+0x14C = 3 and the Lua functions "runNextMission",
  "PauseGoToRMIQuick", "PauseGoToRMIHangout" (strings 0x0054E798/0x0054E7A8/0x0054E7C0) or MenuLoadLevel("menu")).
  The cooldown is set to 1 after a drop-in join (0x0063083C, FUN_00158728), at the end of every scene (FUN_0039EC60,
  FUN_0039F450) and when the in-game mode resumes (FUN_00156F90), so the Start that joined or skipped does not pause.

### 1.2 Who opens it (VERIFIED code; listing 0x00158EC0-0x00158FAC in FUN_00158728)
Per frame, for each player i < GameMgr+0x224 (count), only if GameMgr+0x410 == 0 and GameMgr+0x411 == 0 (no
cinematic, see 2.2), and only for the first player that qualifies:
1. controller record of player i (FUN_0021D3E8(human): 0x00660F50 + human[+0x92]*0x2C) with +0x1B != 0, and a Start
   EDGE on its pad (FUN_00144BF0(pad, 0x800) at 0x00158F10; pad state 0x005DD810 + pad*0x50) - or GameMgr+0x11C != 0
   (forced pause; set only by Lua `ShowOptionMenu` (FUN_0041DD78), which no shipped script calls: VERIFIED by search
   of all 467 decompiled chunks);
2. PlayerHUD[i] sub-object +0x4120, vtable +0x8C == 0 (no on-screen prompt; otherwise Start dismisses the prompt,
   0x00158FB4-0x00159050); 
3. FUN_00227DD8(human) == 0 at 0x00158F50, i.e. the player is NOT downed (stats flag 0x40000) - VERIFIED run A;
4. GameMgr+0x14C == 0 (no GAME OVER / level end) unless the level is 60-69 (FUN_0041D110);
5. then `sw s3,0x1BC0(menu)` at 0x00158F9C (menu+0x1BC0 = player index i = the pause owner) and FUN_00154F28.
Menu object: `*(0x0050EDDC)` = 0x0062E790 in story levels, `*(0x0050EC34)` = 0x006239D0 in levels 60-69.

Drop-in join is the other branch of the same Start press: in the pad loop later in the same block (same no-cinematic
condition, GameMgr+0x14C == 0), a Start held on a CONNECTED pad whose owner (+0x42) is -1 calls UpdateJoin
FUN_0041A460(GameMgr, pad) and sets the cooldown.

### 1.3 Who controls the menu (VERIFIED code + run A)
- On open (vtable +0xAC = FUN_001DBEE0) menu+0x40 = FUN_001AE898(0x00600840, owner) = the HUD's "menu controller"
  record of that player (`*(0x00600840 + 4*owner)`, only 2 exist, allocated by FUN_001AE4D8; +0x19 = pad, set by
  FUN_001AE8D8 which also writes the pad owner). The item list (menu+0x2B00) gets the same record (FUN_001D4200).
- Input (vtable +0x34 = FUN_001DDCF8): Start EDGE on that record's pad -> +0x1B80 = 1 -> fade -> FUN_00154F28 (close).
  Navigation and Cross go through the list widget with the same controller. No other pad is read.
- Run A (`local/m2/sp_pause`, screenshots t0357..t0435, `probes.json`):

| Poll | Input | Result |
|---|---|---|
| 9300 | P1 Start | paused at 9320, owner 0, menu pad 0 |
| 9450 / 9520 | P2 Start / Down | still paused at 9477, 9532, 9651 (P2 has no effect) |
| 9700 | P1 Start | closing at 9721 (+0x1B80 = 1), unpaused at 9810 |
| 10100 | P2 Start | paused at 10135, owner 1, menu pad 4 |
| 10250 | P1 Start | still paused at 10275 and 10433 (P1 cannot close P2's pause) |
| 10400 | P2 Start | closing at 10433, unpaused at 10504 |
| 10700 / 10850 | P3 Start / P4 Start | no pause (10723, 10875, 11002), count stays 4 |
| 11100 | HuKill P1 (test call FUN_00237E70) | P1 health 1, downed at 11326 |
| 11300 | P1 Start (downed) | no pause (11326) |
| 11450 / 11600 | P2 Start / P2 Start | paused (owner 1) at 11475 / closing 11627, unpaused 11705 |

  While paused: game time 90,976 ms and FrameStats 5229 unchanged from poll 9320 to 9721, polls advanced ~30/s.
  The pause menu is drawn in ALL FOUR quarters (screenshot t0357_p9358: "13A Trainyard - All-City; Objectives,
  Stats, Options / Controls, Restart, Resume, Quit"), so every PC's crop shows it.
- 1P / 2P / our 4P:
  - 1 player: pad 0 opens and controls; a second pad's Start is a drop-in join (if joining is allowed), not a pause.
  - 2 players: player 1 (pad 0) or player 2 (pad 4) opens; the opener alone controls and closes (F-0025 + run A).
  - 4P with our patches: players 1-2 as above; players 3-4 cannot open it: the `[4p]` cave at 0x00158ECC/0x00158ED4
    (MAIN 0x000F0C40, `m2_hud_players34.md` 3.1) skips the whole per-player block for index >= 2, because the
    block reads the 2-entry PlayerHUD table 0x00600848 and the menu would read `*(0x00600840 + 4*owner)` for owner
    2/3 = the PlayerHUD pointers (not controller records). Removing the cave alone is therefore not enough.

### 1.4 What a pause does to the game (VERIFIED code, runtime as marked)
- The in-game update FUN_00158728 is not called: no AI, physics, scripts, HUD logic; FrameStats (frame counter) is not
  called (run A: constant). The test-call mailbox (it runs in FrameStats sites) does not run while paused.
- The pause mode uses the UI timer 0x0050B8B8 (FUN_0015DBB8 stores it as its timer), not the GameClock 0x0050B734 of
  the in-game mode, so game time stops (run A: constant) and Lua ScheduleFunc timers (game time, F-0048) stop.
- Lua pad handlers (PadSetHandler) are not dispatched while the top mode is 10 (FUN_00144FB0, `FUN_0015E748() != 10`).
- Pause enter clears the rumble bytes +0x40/+0x41 of every connected pad and calls FUN_003A2C80(...,1) (HYPOTHESIS:
  pauses the world sound); exit restores.
- Pads are still read every frame (FUN_003A3000 -> PadUpdateAll FUN_001454A8), so W4P keeps polling: run A polls
  9320 -> 9721 in 13 s while paused. A game pause therefore never stalls the lockstep (unlike the emulator pause).

### 1.5 Pause menu items and the drop-out risk (VERIFIED code + strings read at runtime, run A `strings@9400`)
Item handler FUN_001DE6C0: 0 Objectives, 1 Stats, 2 Options (string 0x116), 3 Controls (0x173), 4 Restart (choice
"Restart Level - Start level over from the beginning" / "Restart Last Check Point - Go back to last completed check
point"), 5 Resume (+0x1B80 = 1), 6 Quit. With joining allowed and 2+ players, Quit offers "Player 2 - Continue game in
1 player mode" / "All - Exit game and go back to title screen" (strings 0x10A-0x10D; confirm 0x104 "Are you sure you
want to quit 2nd player?"). "Player 2" runs FUN_001DF3A8 (vtable +0xD4): FUN_00419AC0(GameMgr,0) (2-player flag
GameMgr+0x56EC off) + UpdateJoin(GameMgr,-1), whose leave loop releases EVERY drop-in player - in a 4-player session
players 2, 3 and 4 at once. This option must not be reachable in a session (proposal 1.6, words S3/S4).

### 1.6 Proposal: pause (W4P input filter + 3 optional game words)
**W4P (fork), per poll t, after every player's input for t is known (NewPoll, before any pad is written):**
```
raw[s]      = input of slot s for t;  edge(s,b) = raw[s] has b and prev_raw[s] had not
paused      = *(0x005E66A0 + 4 * *(0x0050C784)) == 0x005E6550          # 1.1
cutscene    = section 2.5 (skip vote has priority; Start is a skip vote there, never a pause request)
owned(s)    = *(s16*)(0x005DD810 + pad_for_slot[s]*0x50 + 0x42) != -1   # this slot already controls a character
if not paused and not cutscene:
    for s in slots (ascending):                                           # lowest slot wins on the same poll
        if edge(s, START) and owned(s):                                   # a player asks for the pause
            remove START from eff[s]
            if request < 0: request = s
    if request >= 0 and START not in eff[slot0] of t-1: add START to eff[slot0] (1 poll); pauser = request;
       pending_until = t + 10
    unowned pads: Start passes unchanged (drop-in join while the session still uses the game's join)
elif paused:
    pad 0 (host's pad, menu owner 0) gets merge(raw[slot0], raw[pauser]); every other slot gets neutral input
    OSD on every PC: "Paused by Player <pauser+1>"
if not paused and t > pending_until: pauser = -1 (the game refused: prompt, GAME OVER, cooldown, downed host)
prev_raw = raw
```
All inputs of t and all RAM reads are identical on every PC at poll t, so the filter is deterministic; the OSD is
presentation only. Effect: every pause is opened by player 1's pad (menu owner 0, menu pad 0), the menu is drawn on
every screen, "Paused by Player N" names the real requester, only that player or the host can steer or close it.
Options for the non-host pauser's rights are question U1 (section 8).

**R-24 (Esc):** in a session the TogglePause hotkey must not pause the VM; the fork instead ORs START into the local
player's next sampled input (one poll), so the request travels through the lockstep like a pad press. Esc during a
cutscene then counts as a skip vote, during the pause menu as Start (close, if allowed).

**Game words (group proposal `[warriors-4p session]`, section 6):**
| Id | Address | Change | Why | Status |
|---|---|---|---|---|
| S2 | 0x00158F50 | `jal 0x00227DD8` -> `daddu v0,zero,zero` | a downed player 1 can still open the pause (W4P always opens it on pad 0); without it "any player can pause" fails while player 1 is down | VERIFIED run D: player 1 downed (poll 9207), his Start at 9300 opened the pause (owner 0, pad 0, 9334), his Start at 9500 closed it (9700); without S2 the same press did nothing (run A, 11300) |
| S3 | 0x001DEADC | `bne v0,zero,0x001DEB7C` -> `nop` | Quit offers no "Player 2 - continue in 1 player mode" (would release players 2-4) | VERIFIED run E2: with 4 players and joining allowed, Quit (list index 6) opened the 1-player dialog "To Hangout - Exit game and go back to hangout / Main Menu" (t0377_p9965; menu flag +0x1BB0 = 1, set only by that branch) |
| S4 | 0x001DF658 | `bnel v0,zero,0x001DF674` -> `nop` | same 2-player test in the dialog's back handler FUN_001DF5E8 | VERIFIED run E2: Triangle in the dialog went back to the menu (flags cleared by 10124), a second Triangle resumed |

Without S2, W4P could pick player 2's pad when player 1 is downed, but if both are down nobody can pause.

## 2. Cutscene skip

### 2.1 Three kinds of cutscene (VERIFIED code)
| Kind | Started by | Skippable when | Skip input | Who can skip in our 4P |
|---|---|---|---|---|
| Bink movie (`PSS\*.BIK`: L%d_IN, L%d_OUT, LOGO, PLOGO, TRAILER) | FUN_0042A938(name, skippable) -> movie loop FUN_00429FE8; callers: RunLevel FUN_0015FE90 ("L%d_IN", 1), FUN_00158488 ("L%d_OUT", 1), main FUN_001446D0 (LOGO 0, PLOGO 1, L1_IN 1), Lua `PlayMovie` (extras menu) | flag param a2, kept at sp+0xB0 of the loop (0x00429FF0) | any button (current entry != 0) on ANY of the 8 pads, FUN_0042A820 (it then removes Start from every pad's current entry) | anyone, also a pad that is not a player yet (run B2) |
| In-engine scene / cinematic | Lua `ScenePlayCinematic(id, delay, cb, bars, not NoSkip, looping, freeze, blendcam, final, chain)` (binding 0x00367580 -> FUN_00353C68 -> FUN_00353818), `gPlayCutScene` (WAD 4106 main_126); also ScenePlayFixedScene/ScenePlayAnimation | scene player +0xE5 != 0 and its countdown +0xE0 < 1 (starts at 60, -1 per update, run B2) and the skip-all flag GameMgr+0x56E4 == 0 | Cross (0x40) or Start (0x800) HELD (FUN_00144B88) on the pad of any CURRENT player i < GameMgr+0x224 (FUN_0039CBF0: +0xE5 test 0x0039CD7C, Cross test 0x0039CE64, Start test 0x0039CE8C, +0xE9 0x0039CEFC, +0xE4 0x0039CF08); Start also sets +0xE9 -> GameMgr+0x56E4 = 1 = following scenes of a chain are skipped automatically (reset at the next non-chained scene start) | players 1-4 once they are players; pads of non-players are ignored (run B2) |
| Lua POIZO camera/dialogue sequence (`tblPOIZO.bSkippable`, WAD 7073 main_143..149) | `RegisterPOIZOCallback` (WAD 4106 main_56) | while the callback is registered | Cross or Start, newly pressed, via Lua pad handlers `PadSetHandler(0,64/2048,"DoPOIZOCallback")` and `PadSetHandler(4,...)` = player 1's and player 2's menu-controller pads (FUN_00145698); table 0x005DDA90 + pad*0x40 + bit*4; dispatched in FUN_00144FB0 when the top mode is not 10 | players 1-2 only; mission 09166 also has `C4.SkipPoizoLock3` (Cross, players 1-2) |

During a cinematic GameMgr+0x410 != 0 (FUN_0039D870 sets 1 -> 2 -> 3; FUN_0039EC60 / FUN_0039F450 clear it), and the
in-game per-player block (pause AND drop-in join) is skipped: nobody can pause or join during a cinematic (VERIFIED code;
run B1: players 3-4 pressed Start every 300 polls from 7000 and joined only after the scene ended, 8356+). During a
movie the in-game update does not run at all (the loop is inside the in-game mode's enter), FrameStats is frozen, but
the loop reads the pads once per movie frame, so W4P polls continue (run B1: movie frames 0x0051545C 24 -> 2315 while
polls 4116 -> 6452, FrameStats 2345 constant).

### 2.2 What Mission 13's start contains (VERIFIED run B1, `local/m2/sp_cut1/probes.json`, screenshots)
| Polls | What | Flags |
|---|---|---|
| 4089 | loading screen "13 Trainyard / All-City" | |
| ~4100-6450 | movie L9_IN (about 2,300 frames, 77 s) | 0x0051545C counting, FrameStats frozen, GameMgr+0x410 0 |
| ~6560-8300 | in-engine cinematic (scene slot 0) | state 5, +0xE5 1 (skippable), +0xED 1 (cinematic), +0xE8 0, countdown 39 at 6606 then negative, GameMgr+0x410 3 |
| 8300+ | gameplay; players 3-4 join at their next Start | GameMgr+0x410 0, count 3-4 |

### 2.3 Skip tests (VERIFIED run B2, `local/m2/sp_cut2`)
| Poll | Input | Result |
|---|---|---|
| 4500 | Cross on pad 1 (slot 2, not a player) during L9_IN | movie stopped at frame 403; cinematic starts at 4532 (state 4, countdown 60), state 5 at 4606 |
| 5200 | Cross on pad 1 (not a player) | no skip (state 5 at 5253) |
| 5400 | Start on pad 2 (slot 3, not a player) | no skip (5457, 5553) |
| 5600 | Start on pad 4 (player 2) | skipped by 5626: scene slot empty, GameMgr+0x410 0, skip-all GameMgr+0x56E4 = 1, pause cooldown 0x0063083C = 1 |

### 2.4 Flags W4P can read each poll
- **Scenes (no patch):** for k in 0..11: `slot = 0x006EBA18 + k*0x40` (static); `player = *(slot+0x24)`,
  `data = *(slot+0)` (dynamic heap objects). A skip vote is open while some slot has `*(u16*)(data+0x1C)` in {4, 5},
  `*(u8*)(player+0xE5) == 1` (skippable) and `*(u8*)(player+0xE4) == 0` (not already skipping). The game reads the
  skip input only when also `*(s32*)(player+0xE0) < 1` and `*(u8*)(GameMgr+0x56E4) == 0`. Read by `sp_probe.scan`
  in runs B1/B2/C (VERIFIED values above). GameMgr+0x410 == 3 is a simpler "cinematic playing" test but does not say
  whether it is skippable (non-cinematic scenes keep 0x410 at 0).
- **Movies (patch needed):** nothing static says "a movie is playing": the movie object lives on the movie loop's
  stack; the frame counter 0x0051545C only changes when a frame is decoded, so a poll without a new frame would look
  like "no movie" and unmask a skipping button. Proposal S1: the movie loop's PadUpdateAll call (0x0042A580) goes
  through a 16-word cave 0x000E7000 that writes `2 | skippable` to **0x000E70F0** before the pad read and 0 after it,
  and counts movie pad reads in 0x000E70F4. W4P reads 0x000E70F0 inside its pad hook (which runs inside that pad
  read): non-zero = this poll belongs to a movie, bit 0 = skippable. Result of run D in section 2.6.
- **POIZO (no patch, HYPOTHESIS):** Lua handler for Cross on player 1's pad registered, i.e.
  `*(0x005DDA90 + pad0*0x40 + 6*4) != 0` (pad0 = `*(*(0x00600840)+0x19)`, = 0 in sessions). Menus also register Cross
  handlers (Dlg* scripts), so use it only in the in-game mode (top mode 0x005E56B8). No POIZO occurs in Mission 13's
  start; not observed at runtime.

### 2.5 Proposal: skip vote in W4P (no game change for scenes; S1 for movies)
```
skippable cutscene active at t  = movie flag (bit0) | scene vote open | POIZO handler (in-game mode)
while active:
    for every slot s: a vote is a NEW press (edge) of Cross or Start (movie: any button)  -> votes |= s
    eff[s]: Cross and Start removed for every slot (movie: every button removed)        # nobody skips alone
    OSD on every PC: "k/N want to skip" (N = connected slots, k = votes among them)
    if votes cover all connected slots:
        movie: eff[slot0].buttons = CROSS for 1 poll (FUN_0042A820 sees a button on pad 0)
        scene: eff[slot0].buttons |= CROSS each poll until player+0xE4 == 1 or the scene is gone (max ~10 polls;
               the game reads it only after the countdown, so a vote finished early waits for the window)
        POIZO: CROSS edge on pad 0 for 1 poll
when the cutscene ends (flag / slot / handler gone): votes cleared, OSD removed
```
- Injecting Cross (not Start) skips only the current scene and leaves GameMgr+0x56E4 at 0, so each scene of a chain gets
  its own vote. (Start would skip the rest of the chain: question U3.)
- The next scene start removes Cross/Start from every player's current pad entry (FUN_00148040 in FUN_0039D870), and
  the scene end sets the pause cooldown, so the injected press does not leak into the next scene or open the pause.
- A dropped player is not counted in N; a player who disconnects mid-vote freezes the game anyway (M5 disconnect).
- During a movie the pause cannot open (in-game update not running) and during a cinematic the game itself blocks it;
  so in a cutscene Start is only a vote, never a pause request (1.6).

### 2.6 Movie flag S1 at runtime (VERIFIED run D, `local/m2/sp_down/probes.json`, build w4p-m5-1)
With `local/m2/sp_test.pnach` (S1-S4 as a test group): the movie pad-read count 0x000E70F4 was 126,309 at poll 4100
(boot movies; HYPOTHESIS: the boot movies' loop calls PadUpdateAll more often per poll), 128,614 at 6405 (2,305 more
during L9_IN, about one per poll), 128,758 at 6715 and unchanged at 7500 (no movie). PINE never saw the flag
0x000E70F0 non-zero, as expected: it is non-zero only inside the movie's pad read, which is where W4P's hook runs. The
movie played to its end (frame 2410), gameplay followed, 0 TLB misses. Not yet shown: W4P reading the flag in its
hook (fork change).

## 3. Player leave ("continue without him")

### 3.1 How a player leaves in the original game (VERIFIED code + strings)
- The only way: pause menu -> Quit -> "Player 2 - Continue game in 1 player mode" -> FUN_001DF3A8 (pause menu vtable
  +0xD4): FUN_00419AC0(GameMgr, 0) clears the 2-player flag (GameMgr+0x56EC in story levels), then
  UpdateJoin FUN_0041A460(GameMgr, -1), then menu control goes back to player 1 (FUN_001AE8D8(HUD, 1, -1)).
- UpdateJoin with pad -1, joining allowed (GameMgr+0x56E8, GameMgr+0x158 in {0,3}), 2-player flag off (FUN_00419A80)
  and count >= 2 runs the **leave loop** 0x0041A7D8-0x0041A890, for every player index >= 1:
  1. if tracked by the shared camera list (FUN_00122248): remove that index's cameras FUN_0011ED60(index) and untrack
     FUN_00122438(h, 1);
  2. if the player's pad bit is set in GameMgr+0x456 (drop-in pad mask, set by every drop-in join): FUN_00258A88(h)
     (ends grabs/carries), **ReleasePlayer FUN_0022A2A8(h, 1, 1)**, clear the bit, leave event FUN_0041B148(GameMgr,
     h, 0) (Lua `SetMultiplayerCallback`: WAD 4106 `InventoryPlayer2` -> the mission's `p2Inventory_Callback`;
     Mission 13 (WAD 9229) `TwoPlayerMode` only switches tunnel effects);
  3. tracked count 0x0050B194 = FUN_004DAD40(0x005D91A8) and LayoutViewports FUN_00122ED0.
  The bit is cleared with the pad read AFTER the release (controller +0x19 already -1), so it stays set: a harmless
  quirk of the original (VERIFIED run C: mask 0x16 unchanged after two leaves).
- ReleasePlayer FUN_0022A2A8: pad owner -1, AI brain type restored, inventory slot handling (FUN_0041EC60 on
  GameMgr+0x480), back into its gang (FUN_00166308), health rescaled, HUD slot release (FUN_001B2400 / FUN_001B22F0,
  fixed for slots 2-3 by R8, F-0153), controller +0x19 = -1, and **RemovePlayer FUN_00419C68(GameMgr, index)**, which
  compacts the handle array: every later player moves down one index (+0x1B0 and the +0x220 byte array are updated),
  but the pad owners (pad state +0x42) and the per-index camera arrays (0x000F0800.., m2_pads_cameras.md 2.1) are not.
- So "drop-out" in the original always removes ALL drop-in players together, and since only player 2 (the last
  index) existed, the compaction never moved anybody. Neither is true with four players.

### 3.2 Our 4P hooks (VERIFIED code, `mod/m2/spawn_leave.txt`, `m2_extra_model.md`)
- `[warriors-4p 4p spawn leave]` replaces the leave loop's event call (0x0041A868) with LEAVEHOOK 0x000E1240: the
  event, then, if the human's join priority +0x1B1 == 7 (a Warrior spawned by W4P), LV 0x000E1BAC(handle) =
  DESPAWN 0x000E1180 (HuDelete core FUN_00233EF0, only when the human is AI again) + release of player 4's
  extra-model pin. A taken-over companion (Fox) is simply an AI squad member again after ReleasePlayer.
- The join-event guard (`mod/m2/joinevent.txt`, 0x0041B180) skips the Lua JOIN event for index >= 2 but lets every
  LEAVE event through, so a leaving player 3/4 would run the mission's "player 2 left" Lua code.

### 3.3 Runtime tests (single instance; test-only caves written by PINE, called through the test-call mailbox)
| Run | Action | Result | Label |
|---|---|---|---|
| C (`local/m2/sp_leave`) | cave v1 (`sp_probe.LEAVE_SRC`: the loop body for one index) on index 2 (Fox, slot 3) while index 3 (Swan, W4P-added, slot 2) exists | released (v0 1), count 4 -> 3, Swan moved to index 2 (+0x1B0 2); **but** pad 1 owner stayed 3, the camera of index 2 was removed and Swan's camera stayed at index 3: views 4 -> 2, Swan's quarter showed only a stray radar (t0348_p9117) | VERIFIED (the defect) |
| C | UpdateJoin(GameMgr, -1) through the mailbox (9500) | camera for index 2 re-created, views 3, Swan's quarter back (t0364_p9586); the old index-3 camera stayed in the arrays | VERIFIED |
| C | cave v1 on index 2 again (Swan, last index) | released, DESPAWN path (prio 7), count 2, pad 1 owner -1, views 2 | VERIFIED |
| C | no TLB miss in the whole run (emulog) | | VERIFIED |
| C2 (`local/m2/sp_leave2`) | cave v2, first order (cameras of moved players removed, pad owners fixed, UpdateJoin(-1), layout last) on index 1 (player 2) with players 3-4 present | released and compacted (handles [P1, Fox, Swan], pad owners fixed: pad 2 -> 1, pad 1 -> 2, pad 4 -> -1), then **crash**: TLB miss pc 0x00120270 (FUN_00120230 walks the render list, NULL entries) - the game stopped at poll 9109 | FAILED TEST |
| C3 (`local/m2/sp_leave3`) | cave v2 with the layout redone BEFORE UpdateJoin(-1), index 1 (player 2, Snow, pad 4) with players 3-4 present | released (v0 1), count 3, Fox index 2 -> 1, Swan 3 -> 2, pad owners pad 2 -> 1, pad 1 -> 2, pad 4 -> -1, cameras 3, views 3, each quarter its own player (t0369_p9189) | VERIFIED |
| C3 | slot 2 (pad 1) walks right 9300-9360, slot 3 (pad 2) walks up 9500-9560 | Swan (index 2) moved 4.9 units, Fox stayed; then Fox (index 1) moved 13.1 units, Swan stayed: after the shift each player still controls his own character, and his view moved with him (t0376, t0385) | VERIFIED |
| C3 | cave v2 on index 2 (Swan, W4P-added, last index) | released, count 2, pad 1 owner -1, pad 2 owner 1, views 2 (t0391_p9850) | VERIFIED |
| C3 | whole run (to poll 12800) | 0 TLB misses (`emulog.txt`) | VERIFIED |

### 3.4 Proposal: LEAVE(player index) in the game, triggered by W4P at an agreed poll
- Cave (group `[warriors-4p session]`, 0x000E7100, 114 words, source `sp_probe.LEAVE2_SRC`, words in section 6): for
  player index a0 (>= 1):
  1. same checks and steps as the game's leave loop for that one player (drop-in bit, camera, FUN_00258A88,
     ReleasePlayer);
  2. the Lua leave event only for index 1 (player 2, like the original; mission scripts expect it); for index >= 2
     only LV (DESPAWN of a W4P-added Warrior, extra-model pin release) - mirroring the join-event guard;
  3. remove the cameras of the players that RemovePlayer moved down (old indices index+1 .. count-1);
  4. pad owner (+0x42) = new index for every remaining player (the W4P crop, the pause redirect and the join loop
     read it);
  5. tracked count + LayoutViewports, then, if 2+ players remain, UpdateJoin(GameMgr, -1), which re-creates a camera
     for every player and lays out the views again (with one player left it would re-create a player 2 from a
     companion, so it is skipped).
- W4P: `LeaveCalls = 0:000E7100:P` (P = his game player index = owner of his pad at that poll, read by the fork's
  ScheduleCalls). The mailbox runs at the next FrameStats call, i.e. the same game frame on every PC; it waits while
  the game is paused or a movie plays (FrameStats is not called there) - still the same frame everywhere.
- Production needs the call mailbox (today's `[warriors-4p test call]`, 0x000F0000) in the session patch, with W4P
  writing only the fixed addresses of the session actions (security baseline BRIEF 5.6: no arbitrary calls from the
  network; the drop message carries only player + choice + poll).
- W4P should also report the dropped slot's pad as disconnected (port buffer +0x10C = 0) from T on, so that
  MakePlayer (which searches all 8 pads for a free connected pad) never binds a companion to it later. This matters after
  "continue without player 2": the 2-player flag stays on (it must, 4.3), so a later GAME OVER "Last checkpoint"
  re-creates player 2 from the companion on a free connected pad (run C3 shows it takes his old pad 4).

### 3.5 Risks of a leave
| Who leaves | What happens | Label |
|---|---|---|
| Player 1 (host) | session ends (policy); no game action | - |
| Player 2 (index 1) | the original "1 player mode" path for player 2, except that players 3-4 stay and move down to indices 1-2; mission scripts then see `player2` (the companion human) as AI again (`HuIsAPlayer(player2)` false) - Mission 1 for example suspends/teleports an AI player2 (F-0024); the 2-player flag stays on, so a later level start re-creates player 2 from the companion (4.2, 4.3) | VERIFIED code; C3 runtime for the shift |
| Player 3/4, last index | no shift; like run C's second leave | VERIFIED run C |
| Player 3/4, not last | shift of the other one; cameras and pad owners must be fixed (C, C3) | VERIFIED run C (defect) / C3 |
| any | HUD slot index of the moved player stays (human+0x380), inventory is per HUD slot, so it stays with him; GameMgr per-player records +0x5800 (relocated) are per index and are NOT moved by RemovePlayer (HYPOTHESIS: same class as m2_inventory34.md "HUD slot != player index") | HYPOTHESIS |

## 4. Restart from the last checkpoint without the dropped player

### 4.1 The game's reload path (VERIFIED code)
- MenuLoadLevel core **FUN_00160D78(name)**: GameMgr+0x14C = 3 (leave level; the in-game update returns 0 and its mode
  is popped) and FUN_0015C7B0(0x005E5D90, name) stores the level-table index of `name` in the loading mode, which
  reloads that level at checkpoint GameMgr+0x33A (u16) and pushes the in-game mode again (level_jump.md 1.2-1.3).
- **GameMgr+0x124** is the current level's name string ("level9" in Mission 13; read in every run here,
  `level_name_124`). Callers that use it:
  - GAME OVER menu FUN_00155408: "Last checkpoint" = FUN_00160D78(GameMgr+0x124) (checkpoint unchanged);
    "Restart level" = FUN_0041CEF0(GameMgr, 1) first;
  - pause menu result (FUN_00154F28): +0x1B78 "Restart Last Check Point" = FUN_0041CEF0(GameMgr, GameMgr+0x33A) +
    FUN_00160D78(GameMgr+0x124); +0x1B74 "Restart Level" = FUN_0041CEF0(GameMgr, 1) + the same.
  - FUN_0041CEF0(GameMgr, n) sets GameMgr+0x33A = n and FUN_00397F28 clears a per-checkpoint cache (0x00715780, and
    0x007156F0 when level or checkpoint differ from the cached ones).
- What it needs: (1) a call on the game thread at a frame boundary (the call mailbox runs it after FrameStats; the
  menus call it from their own update); (2) **R8** in `[4p hud B1]` (without it every level end with players 3-4
  crashed, F-0153); (3) `[4p inventory]` restores slots 2-3 at level start (F-0155); (4) afterwards players 3-4 are
  gone (released at level end) and must join again - today by Start, later by the session layer; player 2 is
  re-created automatically from the companion at level start while the 2-player flag GameMgr+0x56EC is set (UpdateJoin
  with pad -1 at the in-game enter, level_jump.md 1.3).

### 4.2 Runtime (VERIFIED run C, `local/m2/sp_leave`, single instance)
After players 3 and 4 had left (cave v1), FUN_00160D78(0x01FD8524 = GameMgr+0x124) at poll 10303 through the mailbox:
the level reloaded at checkpoint 1 (loading screen, L9_IN movie again - skipped by slot 2's Start at 11000, since any
pad skips a movie - then the intro scene), player 2 came back by itself on pad 4, slot 2 re-joined as Fox (index 2,
pad 1) with its next Start, slot 3 pressed nothing and stayed out (3 players, 3 views, pads 0/4/1 owned, from 11400
to the end at 14400). No TLB miss. This is "restart from the last checkpoint without him" for a player 3/4.
Run C3 (`local/m2/sp_leave3`): player 2 left first (cave v2), then player index 2; FUN_00160D78(GameMgr+0x124) at
10202: after the reload **player 2 was re-created automatically from the companion (Snow) on pad 4 - the dropped
player 2's pad** (count 2 at 10404 with the 2-player flag still 1); slot 2 re-joined as Fox at ~11600, slot 3 stayed
out. So "restart without him" works as is for a dropped player 3/4 but NOT for a dropped player 2 (VERIFIED: the
defect); see 4.3.

### 4.3 Proposal
- `RestartCalls = 0:00160D78:GM+0x124` (= the GAME OVER menu's "Last checkpoint"). Works for a dropped player 3/4 as
  long as his slot sends neutral input (no Start) and his pad reads as disconnected (3.4).
- Dropped player 2: clear the 2-player flag first, otherwise the next level start re-creates player 2 from the
  companion on his pad (run C3): `RestartCalls = 0:00419AC0:GM:0,2:00160D78:GM+0x124` (two different polls - the
  mailbox holds one call per frame; FUN_00419AC0(GameMgr, v) sets the flag of the current mode). **VERIFIED run C4**
  (`local/m2/sp_leave4`, the two calls 200 polls apart): player 2 left (cave v2) with 3-4 present, flag cleared at
  10003 (GameMgr+0x56EC 0), reload at 10210 -> only player 1 at level start (pad 4 free); slot 2's and slot 3's next
  Start made them players 2 and 3 (Snow on pad 1, Fox on pad 2; the drop-in join set the flag again: `jal 0x00419AC0`
  at 0x0041A5B0); the dropped slot's pad 4 stayed free to the end (13700); 0 TLB misses.
- Never leave the 2-player flag off while players 2-4 are still in the level: every later UpdateJoin(GameMgr, -1)
  - e.g. a mission script switching joining back on (Lua `CfgMultiplayerJoin` -> FUN_0041A430, which calls
  UpdateJoin(-1) when the flag goes to 1) - would then run the leave loop and release all drop-in players. So clear
  it only immediately before the reload (2 polls in the proposal), never in `LeaveCalls`. VERIFIED code.
- Note the characters change seats after such a restart (slot 2 got Snow, the companion with the lowest join
  priority); the W4P crop follows the pad owner, so each PC still shows its own player.
- The restart while the pause menu is open: the call waits for the menu to close (FrameStats not called while
  paused); W4P should close the menu first or the host chooses in the W4P dialog only while not paused (open question).

## 5. Summary for the W4P side (what the fork reads and writes per poll)
| Item | Address (static unless noted) | Use |
|---|---|---|
| mode stack top / stack | s32 0x0050C784 / u32[] 0x005E66A0 | paused = top == 0x005E6550 |
| pause owner | s32 0x00630350 (menu 0x0062E790 + 0x1BC0) | 0 after every W4P-redirected pause |
| pause menu selected item | s32 0x00631334 (menu + 0x2B00 + 0xA4): 0 Objectives, 1 Stats, 2 Options, 3 Controls, 4 Restart, 5 Resume, 6 Quit (runs E/E2: Down -> 3, Right -> 4, 5, 6) | optional: limit a non-host pauser to Resume (U1) |
| pad owner of a pad | s16 0x005DD810 + pad*0x50 + 0x42 | "is a player"; maps slot -> game player index |
| GameMgr | u32 0x0051489C -> heap (0x01FD8400 in all runs) | +0x224 count, +0x228 handles, +0x410 cinematic, +0x56E4 skip-all, +0x14C level end |
| scene slots | 0x006EBA18 + k*0x40, k < 12; +0x24 scene player (heap): +0xE0 countdown, +0xE4 skipping, +0xE5 skippable, +0xED cinematic; +0 scene data (heap) +0x1C state | skip vote open/closed |
| movie flag (patch S1) | u32 0x000E70F0 (2 = movie pad read, +1 skippable); 0x000E70F4 movie pad-read count | skip vote during movies |
| Lua Cross handler, player 1's pad | u32 0x005DDAA8 (0x005DDA90 + 0*0x40 + 6*4) | POIZO vote (HYPOTHESIS) |
| call mailbox | 0x000F0300.. (test-call group) | LeaveCalls / RestartCalls |
| writes | port buffer of each pad (as today) | Start redirect, menu routing, vote masking and the injected skip |

## 6. Proposed patch group `[warriors-4p session]` (134 words; not yet in `mod/`)
Free RAM 0x000E7000-0x000E72C7 (no pnach line, `mod/m2` source or tool uses 0x000E7xxx; low RAM 0x96000-0xEFFFF stayed
zero at runtime, F-0125). Checked: `python -I tools/note_patches.py check mod/w4p_m1.pnach <this fragment>` ->
**checked 2810 addresses in 2 files: 6 problems** = the 6 known `[4p hud A]`/`[4p hud B1]` alternatives, no new
conflict, every "was" word equals the ELF. S1-S4 were run in `local/m2/sp_test.pnach` (runs D, E, E2); S5 is the cave of
run C3 assembled at 0x000E7100 (branches are PC-relative, so the words equal the tested ones at 0x000E6200).
Needs `[4p spawn]` + `[4p spawn leave]` (S5 calls LEAVEHOOK 0x000E1240 and LV 0x000E1BAC) and a call mailbox.

```
[warriors-4p session]
author=warriors-4p
description=Session policies (session_policies.md): movie flag, pause by a downed player 1, no 'Player 2' drop-out in Quit, LEAVE(index).

patch=2,EE,000E7000,word,27BDFFF0 // S1 FMV flag cave: addiu sp,sp,-16
patch=2,EE,000E7004,word,FFBF0000 // sd ra,0(sp)
patch=2,EE,000E7008,word,8FA800C0 // lw t0,0xc0(sp): the movie loop's sp+0xB0 = skippable flag (stored at 0x00429FF0)
patch=2,EE,000E700C,word,0008402B // sltu t0,zero,t0
patch=2,EE,000E7010,word,35080002 // ori t0,t0,2: 2 = movie pad read, +1 = skippable
patch=2,EE,000E7014,word,3C09000E // lui t1,0x000E
patch=2,EE,000E7018,word,AD2870F0 // sw t0,0x70F0(t1): movie flag
patch=2,EE,000E701C,word,8D2A70F4 // lw t2,0x70F4(t1)
patch=2,EE,000E7020,word,254A0001 // addiu t2,t2,1
patch=2,EE,000E7024,word,0C05152A // jal 0x001454A8 (PadUpdateAll, the replaced call)
patch=2,EE,000E7028,word,AD2A70F4 // sw t2,0x70F4(t1): movie pad-read count
patch=2,EE,000E702C,word,3C09000E // lui t1,0x000E
patch=2,EE,000E7030,word,AD2070F0 // sw zero,0x70F0(t1)
patch=2,EE,000E7034,word,DFBF0000 // ld ra,0(sp)
patch=2,EE,000E7038,word,03E00008 // jr ra
patch=2,EE,000E703C,word,27BD0010 // addiu sp,sp,16
patch=2,EE,0042A580,word,0C039C00 // S1 hook: was 0C05152A jal 0x001454A8 -> jal 0x000E7000; delay slot nop kept
patch=2,EE,00158F50,word,0000102D // S2: was 0C089F76 jal 0x00227DD8 -> daddu v0,zero,zero (a downed player can open the pause)
patch=2,EE,001DEADC,word,00000000 // S3: was 14400027 bne v0,zero,0x001DEB7C -> nop (Quit dialog as in 1-player mode)
patch=2,EE,001DF658,word,00000000 // S4: was 54400006 bnel v0,zero,0x001DF674 -> nop (same test in FUN_001DF5E8)
patch=2,EE,000E7100,word,27BDFFC0 // S5 LEAVE: addiu sp, sp, -64
patch=2,EE,000E7104,word,FFBF0000 // sd ra, 0(sp)
patch=2,EE,000E7108,word,FFB00008 // sd s0, 8(sp)
patch=2,EE,000E710C,word,FFB10010 // sd s1, 16(sp)
patch=2,EE,000E7110,word,FFB20018 // sd s2, 24(sp)
patch=2,EE,000E7114,word,FFB30020 // sd s3, 32(sp)
patch=2,EE,000E7118,word,FFB40028 // sd s4, 40(sp)
patch=2,EE,000E711C,word,FFB50030 // sd s5, 48(sp)
patch=2,EE,000E7120,word,0080A02D // move s4, a0
patch=2,EE,000E7124,word,3C020051 // lui v0, 0x0051
patch=2,EE,000E7128,word,8C51489C // lw s1, 0x489c(v0)
patch=2,EE,000E712C,word,86350224 // lh s5, 0x224(s1)
patch=2,EE,000E7130,word,00044080 // sll t0, a0, 2
patch=2,EE,000E7134,word,01114021 // addu t0, t0, s1
patch=2,EE,000E7138,word,8D130228 // lw s3, 0x228(t0)
patch=2,EE,000E713C,word,0C0E409A // jal 0x00390268
patch=2,EE,000E7140,word,25040228 // addiu a0, t0, 0x228
patch=2,EE,000E7144,word,10400056 // beq v0, zero, out
patch=2,EE,000E7148,word,0000902D // daddu s2, zero, zero
patch=2,EE,000E714C,word,0040802D // move s0, v0
patch=2,EE,000E7150,word,0C0874FA // jal 0x0021d3e8
patch=2,EE,000E7154,word,0200202D // move a0, s0
patch=2,EE,000E7158,word,80490019 // lb t1, 0x19(v0)
patch=2,EE,000E715C,word,962A0456 // lhu t2, 0x456(s1)
patch=2,EE,000E7160,word,012A5006 // srlv t2, t2, t1
patch=2,EE,000E7164,word,314A0001 // andi t2, t2, 1
patch=2,EE,000E7168,word,1140004D // beq t2, zero, out
patch=2,EE,000E716C,word,24120002 // addiu s2, zero, 2
patch=2,EE,000E7170,word,0C048892 // jal 0x00122248
patch=2,EE,000E7174,word,0200202D // move a0, s0
patch=2,EE,000E7178,word,24010001 // addiu at, zero, 1
patch=2,EE,000E717C,word,14410006 // bne v0, at, nocam
patch=2,EE,000E7180,word,00000000 // nop
patch=2,EE,000E7184,word,0C047B58 // jal 0x0011ed60
patch=2,EE,000E7188,word,0280202D // move a0, s4
patch=2,EE,000E718C,word,0200202D // move a0, s0
patch=2,EE,000E7190,word,0C04890E // jal 0x00122438
patch=2,EE,000E7194,word,24050001 // addiu a1, zero, 1
patch=2,EE,000E7198,word,0C0962A2 // nocam: jal 0x00258a88
patch=2,EE,000E719C,word,0200202D // move a0, s0
patch=2,EE,000E71A0,word,0200202D // move a0, s0
patch=2,EE,000E71A4,word,24050001 // addiu a1, zero, 1
patch=2,EE,000E71A8,word,0C08A8AA // jal 0x0022a2a8
patch=2,EE,000E71AC,word,24060001 // addiu a2, zero, 1
patch=2,EE,000E71B0,word,2A810002 // slti at, s4, 2
patch=2,EE,000E71B4,word,10200007 // beq at, zero, noevent
patch=2,EE,000E71B8,word,00000000 // nop
patch=2,EE,000E71BC,word,0220202D // move a0, s1
patch=2,EE,000E71C0,word,0200282D // move a1, s0
patch=2,EE,000E71C4,word,0C038490 // jal 0x000e1240
patch=2,EE,000E71C8,word,0000302D // daddu a2, zero, zero
patch=2,EE,000E71CC,word,10000007 // beq zero, zero, cams
patch=2,EE,000E71D0,word,00000000 // nop
patch=2,EE,000E71D4,word,920801B1 // noevent: lbu t0, 0x1b1(s0)
patch=2,EE,000E71D8,word,24010007 // addiu at, zero, 7
patch=2,EE,000E71DC,word,15010003 // bne t0, at, cams
patch=2,EE,000E71E0,word,00000000 // nop
patch=2,EE,000E71E4,word,0C0386EB // jal 0x000e1bac
patch=2,EE,000E71E8,word,0260202D // move a0, s3
patch=2,EE,000E71EC,word,26920001 // cams: addiu s2, s4, 1
patch=2,EE,000E71F0,word,0255082A // camloop: slt at, s2, s5
patch=2,EE,000E71F4,word,10200005 // beq at, zero, owners
patch=2,EE,000E71F8,word,00000000 // nop
patch=2,EE,000E71FC,word,0C047B58 // jal 0x0011ed60
patch=2,EE,000E7200,word,0240202D // move a0, s2
patch=2,EE,000E7204,word,1000FFFA // beq zero, zero, camloop
patch=2,EE,000E7208,word,26520001 // addiu s2, s2, 1
patch=2,EE,000E720C,word,0000902D // owners: daddu s2, zero, zero
patch=2,EE,000E7210,word,86280224 // ownloop: lh t0, 0x224(s1)
patch=2,EE,000E7214,word,0248082A // slt at, s2, t0
patch=2,EE,000E7218,word,10200012 // beq at, zero, rebuild
patch=2,EE,000E721C,word,00000000 // nop
patch=2,EE,000E7220,word,00124080 // sll t0, s2, 2
patch=2,EE,000E7224,word,01114021 // addu t0, t0, s1
patch=2,EE,000E7228,word,0C0E409A // jal 0x00390268
patch=2,EE,000E722C,word,25040228 // addiu a0, t0, 0x228
patch=2,EE,000E7230,word,0C0874FA // jal 0x0021d3e8
patch=2,EE,000E7234,word,0040202D // move a0, v0
patch=2,EE,000E7238,word,80490019 // lb t1, 0x19(v0)
patch=2,EE,000E723C,word,05200007 // bltz t1, ownnext
patch=2,EE,000E7240,word,00095980 // sll t3, t1, 6
patch=2,EE,000E7244,word,00096100 // sll t4, t1, 4
patch=2,EE,000E7248,word,016C5821 // addu t3, t3, t4
patch=2,EE,000E724C,word,3C0C005E // lui t4, 0x005e
patch=2,EE,000E7250,word,258CD810 // addiu t4, t4, -0x27f0
patch=2,EE,000E7254,word,016C5821 // addu t3, t3, t4
patch=2,EE,000E7258,word,A5720042 // sh s2, 0x42(t3)
patch=2,EE,000E725C,word,1000FFEC // ownnext: beq zero, zero, ownloop
patch=2,EE,000E7260,word,26520001 // addiu s2, s2, 1
patch=2,EE,000E7264,word,3C04005D // rebuild: lui a0, 0x005d
patch=2,EE,000E7268,word,0C136B50 // jal 0x004dad40
patch=2,EE,000E726C,word,348491A8 // ori a0, a0, 0x91a8
patch=2,EE,000E7270,word,3C010051 // lui at, 0x0051
patch=2,EE,000E7274,word,AC22B194 // sw v0, -0x4e6c(at)
patch=2,EE,000E7278,word,0C048BB4 // jal 0x00122ed0
patch=2,EE,000E727C,word,00000000 // nop
patch=2,EE,000E7280,word,86280224 // lh t0, 0x224(s1)
patch=2,EE,000E7284,word,29010002 // slti at, t0, 2
patch=2,EE,000E7288,word,14200004 // bne at, zero, done
patch=2,EE,000E728C,word,00000000 // nop
patch=2,EE,000E7290,word,0220202D // move a0, s1
patch=2,EE,000E7294,word,0C106918 // jal 0x0041a460
patch=2,EE,000E7298,word,2405FFFF // addiu a1, zero, -1
patch=2,EE,000E729C,word,24120001 // done: addiu s2, zero, 1
patch=2,EE,000E72A0,word,0240102D // out: move v0, s2
patch=2,EE,000E72A4,word,DFBF0000 // ld ra, 0(sp)
patch=2,EE,000E72A8,word,DFB00008 // ld s0, 8(sp)
patch=2,EE,000E72AC,word,DFB10010 // ld s1, 16(sp)
patch=2,EE,000E72B0,word,DFB20018 // ld s2, 24(sp)
patch=2,EE,000E72B4,word,DFB30020 // ld s3, 32(sp)
patch=2,EE,000E72B8,word,DFB40028 // ld s4, 40(sp)
patch=2,EE,000E72BC,word,DFB50030 // ld s5, 48(sp)
patch=2,EE,000E72C0,word,03E00008 // jr ra
patch=2,EE,000E72C4,word,27BD0040 // addiu sp, sp, 64
```

## 7. Tests run for this note (all SINGLE-PC, one instance, scripted input, no impairment)
| Tag (local/m2/) | Build | What | Main result | TLB misses |
|---|---|---|---|---|
| sp_pause | w4p-m3-7 | pause by P1, P2, P3, P4, downed P1 | 1.3 table | 0 |
| sp_cut1 | w4p-m3-7 | Mission 13 start, no skip | movie 4100-6450, cinematic 6560-8300 (2.2) | 0 |
| sp_cut2 | w4p-m3-7 | skips by non-players and player 2 | 2.3 table | 0 |
| sp_leave | w4p-m3-7 | cave v1 leaves, UpdateJoin(-1), reload, re-join | 3.3, 4.2 | 0 |
| sp_down | w4p-m5-1 | test group (S1-S4): movie flag, downed P1 pauses | S1 count 2,305 movie pad reads during L9_IN, constant afterwards; S2: downed P1 opened (owner 0, pad 0) and closed the pause | 0 |
| sp_quit | w4p-m5-1 | menu navigation | list index 0x00631334: Down -> 3, Right -> 4, 5 (run ended before Cross: host loaded, polls ~9/s) | 0 |
| sp_quit2 | w4p-m5-1 | Quit dialog with S3/S4 | Down -> 3, Right -> 4, 5, 6; Cross on Quit -> 1-player dialog (To Hangout / Main Menu), no 'Player 2' choice; Triangle back, Triangle resume | 0 |
| sp_leave2 | w4p-m5-1 | cave v2 first order | crash pc 0x00120270 (FAILED TEST) | 22 |
| sp_leave3 | w4p-m5-1 | cave v2 fixed: player 2 leaves with 3-4 present, control check, last-index leave, reload | all VERIFIED (3.3); reload re-created player 2 on the dropped pad 4 (4.2) | 0 |
| sp_leave4 | w4p-m5-1 | player 2 leaves (cave v2), 2-player flag cleared, reload, slots 2-3 re-join | restart without player 2 works (4.3) | 0 |
Commands: `local/m2/sp_*_cmd.txt`; scripts `tests/m2/nav/sp_*.txt`; probes `tests/m2/sp_probe.py`; results
`local/m2/<tag>/probes.json`, `state.txt`, `emulog.txt`, screenshots. Originals were not touched (only sandbox
instances 13/14 were used); hashes not re-checked in this note.

Results ready for FINDINGS.md (proposed wording, labels as above): pause mechanics and owner (1.1-1.3, run A); pause
freezes game clock and FrameStats but not the pad polls (1.4, run A); pause menu drawn in all four quarters (run A);
movie skip by any pad incl. non-players, scene skip only by current players' Cross/Start held after a 60-frame
countdown, Start sets skip-all (2.1-2.3, runs B1/B2); movie flag patch S1 works (run D); downed player 1 can pause with
S2 (run D); single-player leave defects (run C) and the C2 crash (FAILED TEST); single-player leave v2 (run C3), restart without player 3/4 (C) and without player 2 (C4), Quit dialog with S3/S4 (E2).

## 8. Open questions (for the user / coordinator) and risks
- **U1 - what may a non-host pauser do in the menu?** Everything chosen there acts on every PC (Options change shared
  game settings, Restart/Quit end the mission for all). (A) the non-host pauser may only resume: W4P passes his Start,
  his D-pad, and his Cross only while the selected item 0x00631334 is 5 (Resume) - recommended; the host keeps full
  control; (B) the pauser may do everything the host can; (C) everything except Options, Restart and Quit.
- **U2 - Esc:** (A) Esc becomes "pause request" (Start) for the local player, the emulator never pauses in a session -
  recommended; (B) Esc keeps pausing the emulator and the others see "Waiting for Player N" (today, R-24).
- **U3 - skip with Start:** in the original, Start also skips the rest of a scene chain. (A) a completed vote skips
  only the current scene (inject Cross) - recommended, every scene asks again; (B) inject Start when every voter
  pressed Start.
- **Vote timing:** a vote finished in the first 60 frames of a scene waits for the countdown (about 2 s); the OSD
  should show "4/4 - skipping..." meanwhile.
- **POIZO detection** (2.4) is untested; Mission 13's start has none. Needs a mission with a skippable POIZO (WAD
  7338-7340, 7794, 8182, 8481, 9112 set `bSkippable`).
- **Movies outside missions** (boot logos, extras menu `PlayMovie`) are not in a session; the S1 flag covers every
  movie anyway.
- **GAME OVER menu input** (F-0155: Cross on "Last checkpoint" ignored in go5) is the same question for the
  restart policy: which pad controls the GAME OVER menu was not traced here (FUN_00155408, menu `*(0x0050EC8C)`).
- **Risk: per-index GameMgr records** (+0x168 0x5C records, +0x5800 records, +0x414 block) are not moved by
  RemovePlayer, so after a middle leave the moved player uses the leaving player's record (rage multiplier, timers)
  - HYPOTHESIS, small; test with combat after a leave (M6/M7).
- **Risk: Lua leave event for player 2 while 3-4 stay** - mission scripts treat player2 as AI again; per-mission
  check in M6.
- **Risk: W4P filter state** (pauser, votes, previous inputs) must start identical on every PC: derive it only from
  synchronized inputs since session start and RAM at the poll; never from host time or local UI.
- **Not done:** 4-instance lockstep test of the filter (needs the fork change), S5 and the restart calls in 4-instance lockstep (needs the
  M5 disconnect build: `LeaveCalls` / `RestartCalls`).

# Project state (handoff, updated 2026-10-13, second-PC kit)

**Stage:** 2 (approved 2026-10-10; decisions D1-D21 in `docs/DECISIONS.md`).
**Milestones:** M2 complete (report `docs/reports/M2_report.md`, tag `m2`). **M5** (session policies + transport):
every SINGLE-PC criterion met, 4-player package built; LAN/INTERNET parts need the user. **M6** (missions) in progress:
exit criteria `docs/plan/M6.md`. **M7** criteria written (`docs/plan/M7.md`); regression done (F-0193); impairment series done (F-0206). Findings up to **F-0210**. The user said "do not stop until you finish everything"
(2026-10-12): keep going without pauses; stop only for things that need the user.
Fork: **w4p-m6-3** = patches 0001-0020 (fork commit b81b4cc; waiting players see cutscenes and shared single views,
auto re-join every 60 polls). Protocol version 3.
Package: `dist/warriors-4p-coop.zip` id **b94e4b5caed8** (w4p-m6-2, pnach 5666 incl. RARC) passed its self-test
(F-0207) but is NOT yet given to the user: it will be rebuilt with w4p-m6-3.

## READ FIRST: handoff (2026-10-13 ~00:35) - SINGLE-PC work finished, waiting for the user
Everything that one PC with bots can do is done and committed. What remains needs the user (LAN PC, friends, human play)
or his decisions. Read `docs/reports/FINAL_status.md` first, then `docs/reports/USER_TESTS.md`.

### State
- Stage 2; milestones: M2 done (tag m2-mission13), M5 SINGLE-PC done (LAN/internet need the user), M6 SINGLE-PC done
  (criterion 4 = human play-throughs open; all missions IN PROGRESS), **M7 SINGLE-PC done (tag m7-singlepc)**, M8:
  package, instructions, legal review (`docs/reports/M8_legal_review.md`), protocol spec (`docs/PROTOCOL.md`), final
  status report done; final per-mission statuses wait for the user's tests.
- Findings up to **F-0233**. Fork w4p-m6-3 (b81b4cc, patches 0001-0020). mod/w4p_m1.pnach 11733 addresses (6 known
  problems = [4p hud A]/[4p hud B1] alternatives).
- **Package for the user: `dist/warriors-4p-coop.zip` id 26748ee9ec13** (SHA-256 9cc3ac7f...899e85c8c, self-tests F-0230
  60 fps and F-0233 30 fps, 0 mismatches). Complete source zip `dist/warriors-4p-coop-source.zip` (legal L1 option A).
  Superseded, do not send: b94e4b5caed8, e64016ce3a7b, the old 2-player dist/warriors-4p-test.zip (E6).
- This chat's commits: a6a4673 (D24), 5c9d0b5 (M7 tests), c78aa8e (camera/HUD parity + LUIFIX), cb7d54d (smoke4,
  reports), 9af4231 (chapter runs) and docs/tools commits in between.

### Waiting on the user (asked in the final message of 2026-10-13)
1. Legal L1 (give friends the source zip too, recommended A), L2 (ship the patch without comments: `make_package4.py
   --strip-comments`, recommended A, needs a rebuild + short self-test), L8 (private sharing only, recommended A).
2. Dates for the LAN test and the internet sessions; then the play-throughs (USER_TESTS.md tests A-D).
3. Older open items: Q1 (E6 2-player package: recommended skip), the cut-off message "and the person got...", optional
   54 deg single-player zoom.

### Second-PC internet test over a mobile network (prepared 2026-10-13, user asked for it)
The user puts the second PC (nothing installed) on a mobile network to test INTERNET play; home PC = host.
- Kit (user asked for ONE folder on the Desktop): `C:\Users\PC FORCE\Desktop\WARRIORS-SECOND-PC` (4.16 GB, outside the
  repo, never commit/share): package 26748ee9ec13 already unzipped + `MY-GAME-AND-BIOS (never share)/` (own ISO +
  SCPH-90001 set, hashes = originals) + `START-HERE.bat/.ps1` (first time: CHECK-FILES.ps1 over all 307 files, copies
  the BIOS to `bios-in-use\`, writes my-settings.txt: 30 fps, window, save `mobiletest`; stops on USB stick / OneDrive /
  too-long path) + `1-READ-ME-FIRST.txt` (copy to C:\, firewall Private AND Public, 2-minute lobby wait, outage tests
  20/45/90 s). Trial run on a hard-linked copy: 307/307 OK, settings correct. The old `local/SECOND-PC` was removed.
  The user asked me NOT to run anything there: the user runs it on their own to learn it.
- Home PC prepared: `local/HOME-PC/warriors-4p-coop/` (my-settings.txt: original ISO path read-only, own BIOS copy in
  `local/HOME-PC/YOUR-OWN-BIOS (never share)/`, quality 8, 30 fps, window, save `mobiletest`).
- Returned logs go to `local/from-second-pc/`; home logs are in `local/HOME-PC/warriors-4p-coop/logs/`.
- Note: this PC's Ethernet profile is **Public** and it has global IPv6; the README's "Private networks" firewall
  advice is not enough here (kit says tick both). HYPOTHESIS: mobile CGNAT may block direct ICE (no relay, D5 A);
  IPv6 on both sides would likely connect. If it fails: options (overlay VPN / own relay) need the user's approval.
- TODO at the next package rebuild (e.g. with L2): package4 README/QUICK-START firewall text -> tick "Private" AND
  "Public networks" (hotspots and some home networks are Public). Not changed now: the kit must keep the same zip.

### If the user sends logs or reports
Logs land in `logs\<date>_<time>_<role>\` of each PC's package folder: w4p.log (hashes, DESYNC lines, waits),
connection-log.txt / connection-stats.json (helper), lobby log. Compare with PROTOCOL.md sections 5-6.

### (first chat's handoff, kept for reference)
The user cleared the chat. Everything needed to continue is in this file, `docs/FINDINGS.md` (up to F-0210),
`docs/DECISIONS.md` (up to D24) and the research docs named below. The user said "do not stop until you finish
everything": keep working without pauses; stop only for things that need the user. Explain in plain English with
examples; give lettered options with a recommendation.

### Work that was running when the chat was cleared (may have been stopped by the reset - check first)
- **D24 agent** (background agent of the old chat): players 3-4 play the 2-player chases.
  - M18 car escape (09110): players 3-4 join at the escape start **as Cochise and Vermin** and tap like players 1-2.
    User's final choices: **one shared tap button for everybody** (original rule: one random C1.chaser for all,
    changes when any runner enters VCarChaseTrig[10..12]) and **exactly ONE tap icon on screen, identical on every
    PC** (no emulator overlay, no HUD 2/3 icons). Same fail rule as 2-player (caught = group fails); restart path
    must revive/teleport players 3-4 too.
  - M8 cp3 cart chase (08838): players 3-4 join **as Snow and Ajax** (cart is pumped by players 1-2 only).
  - Also asked of it: M18 beach-fight (09112 main_25..31) wide rail cameras for players 3-4 with view index 2/3 (user
    saw "2 good screens and 2 zoomed-in screens"); the **RAILTGT** engine patch (rail target picker FUN_0013B7B8 reads
    list entries 0-1 only, bound 0x0013B8A8, index check 0x0013B948; design in `docs/research/m6_camera_parity.md`
    2.4); C1.CAMChange (09110:346-361: a player 3/4 at VCarChaseTrig[5] stops player 2's tapping); the tap turn-off
    2-player assumption in FUN_00234318 (all_02.c ~60535: `count == 2` -> otherwise command 45 removed for everyone);
    a growable LUACH table (only 5 free rows).
  - Its files (uncommitted, in progress at reset): `docs/research/m6_chase4p.md`, `tests/m6/chase4p_run.py`,
    `tests/m6/chase_probe.py`, changes in `tests/m2/nav_probe.py` and `tests/m2/x6fix_probe.py`, evidence
    `evidence/M2/d24base_m18.json`, `evidence/M6/d24base_m18.json`, runs `local/m2/d24*`. Possibly also
    `mod/m2/*.txt` / `mod/make_pnach.py` later. **Next chat: run `git status`, read m6_chase4p.md, check whether
    pcsx2 processes still run (`tasklist | grep -ci pcsx2`; never kill instances you did not start unless they are
    clearly orphaned from the old chat), then continue D24 from where the files show it stopped.** Its findings were
    to be numbered from **F-0211**.
  - Already known from its baseline run d24base_m18 (4 instances, players 1-2 with scripted tapping, players 3-4
    waiting): the 2-player escape was WON with 4 PCs connected (checkpoint 2 -> 3 at poll 8972, chase about 23 s),
    players 3-4 joined in the beach fight round 2 (4 players / 4 views from poll ~13700). Bot tapping that works: all
    four face buttons every 3 polls (`TRI:2 CIR:2 X:2 SQ:2`) from poll ~4200; tap research summary in the D24 brief
    (speed from press gap: 2-3 ticks = 100 %, stick not read in tap mode).
- After D24: **camera parity** for players 3-4 in the other missions (next steps 2).

### Answers already given to the user in the last chat (do not re-ask)
- All four quarters are the same size and zoom (CropFor in W4P.cpp = exact quarters with the same inset; fov4fix: all
  four cameras FOV 65 / window 0.637 x 0.478). Only the monitor size and the chosen picture quality differ per PC.
- Mission walkthroughs for M16 (shared chase shots, rail cameras for players 1-2 only, Ajax park switch) and M18
  (intro, 2-player car escape, beach rounds, credits as Riffs).
- Why runtime patches instead of an edited disc (plan section 14: legal, sync check, original stays clean, technical
  cost, same behaviour); other games (network/lockstep generic, ~35 Warriors addresses in W4P + the whole pnach are
  game-specific); how professional mods split inside/outside; scope = 18 main-story missions + hideout interludes,
  optional content only at original player count (BRIEF 4.1).
- 2-player-only stretches (players 3-4 wait): every mission start until the first quiet moment, hideout (host only),
  M2 intro/tutorial, M8 cp3 chase, M18 cp1-2 + beach round 1; after a restart also M2 Fox scene, M11 Birdie fight,
  M14 cp6-7 chases. D24 turns the two chases into 4-player parts.
- Join timing before/after the 2-second auto-join (F-0209).

### Still open with the user
- Q1 (E6 2-player package: recommended skip), D (dates for the LAN test and the internet test with friends), the
  cut-off message "and the person got..." (offered: smaller character from FOVFIX / disappears / other), exact
  single-player zoom 54 deg instead of 65 (optional).
- The friend package must be rebuilt after D24 (+ camera fixes if they are quick); `dist/warriors-4p-coop.zip`
  b94e4b5caed8 (F-0207) is superseded - tell the user not to send it.

## Waiting on the user
- **E6 2-PC test** with `dist/warriors-4p-test.zip` (2-player package, old build w4p-m3-7). Do NOT rebuild that zip
  unless asked. Its 60 fps title ignores Start (F-0186, fixed in the sources since): the user was told to choose
  60 fps "no". Question Q1 (keep E6 at 30 fps / rebuild with the fix / skip E6 for the 4-player package) unanswered.
- **D (open):** dates for the LAN test (second PC) and the internet test with friends (T2-T4, M6 criterion 4).
- Answered with the recommended default until the user says otherwise: X9 A (no Cleon after his story death),
  X10 A (player 3 also gets his own model), X13 A (players 3-4 wait in 2-player-only stretches), X7 b (starting items
  given again after a script-forced leave).
- Open small decisions (chooser, `docs/research/m6_chooser.md`): Fox-from-M16 and post-game hub rows (HYPOTHESIS).
- User reports handled 2026-10-12: floating yellow "2P" labels (radar icons, F-0194), radar too big / seen twice
  (F-0191), "map shows every player?" (no in-mission map; radars now show all four, F-0194), zoom (F-0198), orange
  ring (F-0203), true single view (D23 experiment: not feasible, F-0205), equal quarter size (answered: CropFor in
  W4P.cpp + fov4fix cameras), M16/M18 walkthroughs, why runtime patches instead of an edited disc (plan section 14).
- **Asked 2026-10-12, unanswered:** what waiting players 3-4 see in shared-camera stretches (e.g. M18 car escape):
  A (recommended) show the picture when the game itself draws one shared view (views == 1 with >= 2 players in the
  game), B let players 3-4 run as Cochise/Vermin (script change, risky), C keep black (cutscenes visible). Also: the
  cut-off message "and the person got...", exact single-player zoom (54 deg) instead of 65, Q1, D.

## M5 status (all SINGLE-PC, 4 instances on loopback unless noted)
| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | Pause | **met**: Start, and Esc as a pause request with real key presses (F-0196) | F-0171, F-0196 |
| 2 | Cutscene skip | **met** | F-0171, F-0177 |
| 3 | Disconnect, back in time | **met** | F-0164, F-0167 |
| 4 | Timeout choice | **met** for players 2, 3, 4 | F-0169, F-0170, F-0176, F-0178 |
| 5 | Host leaving | **met** | F-0167 |
| 6 | Join only in the lobby | **met** in the 4-player package (late joiner refused, running game unaffected) | m5_package4.md |
| 7 | Saving | copy / hash / compare of co-op saves tested; the game never wrote a save in the runs -> partly | m5_package4.md |
| 8 | Connection | loopback + package (codes and Join by IP) pass; LAN/internet need the user | F-0172, F-0173, m5_package4.md |
| 9 | Originals unchanged | **met** 2026-10-12 (20 files, 0 changed) | HASHES.md |

## M6 status (`docs/plan/M6.md`)
| # | Criterion | Status |
|---|---|---|
| 1 | Smoke per mission | **met (SINGLE-PC)**: smoke3 all 18 missions 0 mismatches / 0 TLB, 4 players in 16 (M2/M18 join off by script) (F-0201) |
| 2 | Per-mission fixes | X1-X8 (F-0180, F-0182), X11 (F-0183), FXCAM (F-0184), X12 (F-0185), PINSVC/PLACE (F-0188, F-0197), X4 (F-0189), X6 rows (F-0190, F-0199), HUD (F-0191, F-0194, F-0200, F-0203), FOVFIX (F-0198). Open: player 3's Select ring, 'player boxes' only for players 1-2 (F-0199) |
| 3 | Restart/checkpoint per mission | **met (SINGLE-PC)**: checkpoint reload with 4 players in M3/M6/M9/M12/M14/M15, players back in 17-43 s, 0 mismatches (F-0204) |
| 4 | Completion with humans | needs the user (D) |
| 5 | Hub interludes | X12 verified with a level jump (F-0185); a real hub after a finished mission untested |
| 6 | Mission status table | interim table in MISSIONS.md (all IN PROGRESS until human completion) |

## Next steps (in this order)
1. Running (agent): **D24** = players 3-4 play the 2-player chases (M18 car escape as Cochise/Vermin with tapping, one
   shared tap button and ONE tap icon for everybody (user's final choice); M8 cp3 cart chase as Snow/Ajax), plus M18
   beach-fight rail cameras for players 3-4, the RAILTGT engine patch (`docs/research/m6_camera_parity.md` 2.4),
   C1.CAMChange (09110:346-361) and a growable LUACH table. Report -> findings from F-0211, research doc
   `docs/research/m6_chase4p.md`. Baseline d24base_m18: the 2-player escape was won with 4 PCs connected (checkpoint
   2 -> 3 at poll 8972; players 3-4 joined in the beach fight round 2) - confirm from the agent's report.
2. After D24: **camera parity** for players 3-4 in the other missions (`docs/research/m6_camera_parity.md`: 21 class-(a)
   spots in 12 missions, 6 harmful; fix patterns F1 mirror / F2 own index / F3 tracked list 0x005D91A8 / F5 join hook;
   priority list section 5): M16 cp1/cp3 chases, M6 cp4 rooftop (2 harmful handlers reachable today), M17 Lizzie boss,
   M8 cp3 cameras, M1, M9 cp4 (harmful), M3, M10, M11, M13, M5. 4-instance tests per mission.
3. Rebuild the package with w4p-m6-3 + the new pnach, self-test (`--preset m13_60 --players 4 --seconds 900`), give the
   user the new id (the zip b94e4b5caed8 is superseded and must not be sent).
4. M7 remaining: 60-minute long session (`sh tests/m7/long_run.sh long1`, script ready, not yet run), T1g outage through
   w4p-net, M7 report (bandwidth from pk4g: about 0.29 Mbit/s per link each way at 60 fps, 3 links per PC).
5. Open M6 items: player 3's Select ring (F-0194), players 3-4 timer arcs (F-0203), 2-player local layout gating
   (F-0193, optional), a real hub after a finished mission; then M8 packaging, legal review, final report.

## How to run things (quick reference)
- Build the fork: `powershell -File emulator\build.ps1` (log `local/logs/build_Release.log`). Build tag **w4p-m6-3**;
  commit in `emulator/pcsx2` with author/committer `warriors-4p <w4p@localhost>`, export with
  `git format-patch -1 HEAD --start-number N -o ../patches`. Do not build while any instance runs (the exe is locked);
  ask agents to pause runs first.
- Patch file: edit `mod/m2/*.txt` or `mod/make_pnach.py`, then `python -I mod/make_pnach.py > mod/w4p_m1.pnach` and
  `python -I tools/note_patches.py check mod/w4p_m1.pnach` (expected: **5666 addresses, 6 problems** = the known
  `[4p hud A]` vs `[4p hud B1]` alternatives). Never regenerate it while a batch that uses it is starting runs.
- Full 4-player group list: `warriors-4p M1; own view; hud; 4p; 4p hud B1; 4p hud B2; 4p spawn; 4p spawn leave;
  4p inventory; 4p fx; 4p markers; session; missions; session call` (prefix every name with `warriors-4p `; tests add
  `test call`). make_pnach stops if a required session hook is missing (F-0192).
  Never combine `4p hud A` with `4p hud B1`.
- Mission smoke: `python -I tests/m6/mission_smoke.py --missions 1,2,... --seconds 600 --tag <tag> [--policies]
  [--force-join 5500,7000] [--calls-extra ...] [--groups-extra ...]` -> `evidence/M6/<tag>_mNN.json` + summary. With
  `--policies` players 3-4 never press Start (they join only through X11). Level jump: CallAt
  `3999:0041ABC0:1,4009:00160D78:<entry>`, entry = 0x01FD996C + (mission-1)*0x84; hub = 0x01FDA7DC.
- Hub test: `sh tests/m6/hub_test.sh <tag> 600`.
- One instance with probes: `python -I tests/m2/nav_probe.py <tag> tests/m2/nav/boot_to_m1_2p.txt --inst 13
  --players 4 --script2 tests/m2/nav/p2_join.txt --script3 tests/m2/nav/m13_p3.txt --script4 tests/m2/nav/m13_p4.txt
  --groups "<groups without M1>" --ini EmuCore/Speedhacks/vuThread=false --callat "<calls>" --probe module:func:poll
  --seconds 480` (probe modules live in tests/m2; only one PINE client per instance; a probe may block, e.g.
  `fx_crash_probe:after_stall`).
- Four instances: `tests/m2/m2_run4.py` (see its docstring; `--w4p KEY=VALUE`, `--w4p-slotN`, `--leaver`, `--peer-base`,
  `--sample-every`). Copy `local/pcsx2/inst6..9/PCSX2/logs/emulog.txt` after a run (crashes = `TLB Miss` there).
- M5 tests: disconnect `--w4p DisconnectTimeoutS=15 --w4p-slot3 TestDrop=9300:0 --w4p-slot0 TestHostChoice=continue
  --w4p "LeaveCalls=0:000E7100:P" --leaver 3`; policies `--w4p SessionPolicies=true`; through w4p-net:
  `python -I net/w4p-net/tests/local4.py --emu-ports 41200,41201,41202,41203 --stop-file local/m5/stop_helpers`, then
  `m2_run4.py ... --peer-base 46100`. w4p-net build: `powershell -File net\w4p-net\build.ps1`.
- 4-player package: `tools/make_package4.py`, self-test `tests/m5/package4_selftest.py <tag> --preset ... --players N`.
- Frame rate: `python -I tests/m2/fps_windows.py local/m2/<tag>/w4p.log <from_poll>`.
- Scratch disassembler (not in the repo): scratchpad `mydis.py <elf> <start hex> <count> [pnach]`; ELF
  `local/disc/SLUS_212.15`; decompile `local/analysis/all/all_0N.c`.
- Game buttons: grab Circle, attack Square/Triangle, Flash D-pad Right, revive D-pad Left.
- Useful addresses: GameMgr `*(0x0051489C)` (= 0x01FD8400), handles +0x228, count +0x224, join flag +0x56E8,
  cinematic +0x410, level end +0x14C, mode +0x158, checkpoint u16 +0x33A, level index u16 +0x56DC (level number =
  `*(GM+0x14D4+idx*0x84+4)`); pad owner s16 0x005DD810+pad*0x50+0x42; views 0x0050B198; render cameras (relocated)
  0x000F0810+4*i; ScreenEffects mirror 0x000F0890[4]; mode stack top 0x0050C784 / 0x005E66A0; poll counter 0x000F0500.

## Important settings and rules
- MTVU (`vuThread`) is OFF in the package and in every session (F-0120, F-0150). Never switch it on.
- Never launch the original PCSX2. Sandboxes live in `local/pcsx2/instN` (6-9 four-instance runs, 10-14 agents,
  15-19 the 60 fps agent).
- Files are CRLF: edit with Python. `mod/w4p_m1.pnach` is generated from Git Bash with CR CR LF lines - keep it so.
- Killing emulator processes from the shell is refused by the permission system; let runs end on their own.
- The fork's `emulator/pcsx2/AGENTS.md` forbids AI-written contributions to the PCSX2 project: our patches stay in this
  project and are never submitted upstream.
- Low RAM map (grep the pnach before using new space): HUD objects 0x000A0000+; 0x000E0000-0x000E0CC7 (B1/B2);
  0x000E1000-0x000E257F (spawn + chooser v2 incl. pins 0x000E1C00/0x000E1C50, XC table 0x000E1E10, XCHK 0x000E1FA8,
  KICK/PINSVC 0x000E219C-0x000E243F, PLACE 0x000E2440-0x000E257F; hook 0x0023D6BC);
  0x000E1600-0x000E1C4B (extra model, inside the spawn range); 0x000E3000-0x000E3123 (combat C3);
  0x000E4000-0x000E502B (inventory incl. X8); 0x000E5800-0x000E5C3F (fx); 0x000E7000-0x000E72F7 (session S1-S5,
  LEAVE 0x000E7100); 0x000E7400-0x000E7BFF + 0x000E7E00-0x000E7F7F (missions X1/X3/X7/X4/X6, LUACH table
  0x000E7F00; 0x000E7C00-0x000E7DFF test buffer); 0x000E8000-0x000E80B3 (RHALF radar); 0x000E8100-0x000E8A07
  (4p markers; 0x000E8180-0x000E82BF free again) + 0x000E8A10-0x000E9793 (3P/4P labels, PICON 0x000E8DE0);
  0x000EC000-0x000ECA53 (X6 LUACH names and Lua sources; LUACH rows 0x000E7F08-0x000E7F50, 5 free rows to 0x000E7F7F);
  0x000F0000-0x000F0FFF (M1/hud/4p/test call, mailbox 0x000F0300). Free (check first): 0x00096000-0x0009FFFF,
  0x000E2580-0x000E2FFF, 0x000E5D10-0x000E6FFF, 0x000E9800-0x000EBFFF, 0x000ECA60-0x000EFFFF.

## Result line for the last runs of this session
- esc2 (M13, 4 instances): Esc -> 3 pause/resume cycles on all PCs, 443 hash points, 0 mismatches (F-0196). smoke2
  missions 1-7: all 0 mismatches / 0 TLB, 4 players except M2 (join off by design); the batch died at mission 8
  (tooling, see Next steps 1). hub_cp2 0/0 (F-0185). fxfix_m17 4 players, 0 TLB (F-0184).

# The Warriors (PS2, SLUS-21215): Four-Player Online Story Co-op
## Investigation and Implementation Brief for Claude Code

## 0. Operating rules (read first)

You are working on my Windows PC as a senior engineer. Your areas are PS2 reverse engineering, game modification, emulator development, and real-time multiplayer networking.

This is a large, high-risk project that may turn out to be partly or wholly infeasible. Your job is to establish the facts with evidence and propose a plan. Only after I approve the plan do you build as much as can be made to work reliably, reporting honestly on every part. No one has verified anything in this brief. Apart from my description of my environment, every statement about the game and the emulator is a requirement or a hypothesis for you to check.

These rules override everything else:
1. **Two stages with a hard gate.** In Stage 1 you investigate, run feasibility experiments, present a plan, and then STOP. In Stage 2 you implement, and only after my explicit approval (§6, §7).
2. **Evidence, not assumption.** Label every technical claim VERIFIED, HYPOTHESIS, BLOCKED, or FAILED TEST (§3). Never invent structures, function names, memory addresses, mission names or classifications, measurements, test results, or claims that online play works.
3. **Protect the originals.** Never modify, overwrite, rename, move, or delete the original ISO, the game image, the PCSX2 installation, the BIOS files, or the Ghidra installation (§2.2).
4. **No success without proof.** Nothing is done just because it compiles, a patch applies, four characters spawn, or a lobby connects (§1.4, §8).
5. **Ask first** before anything outward-facing, costly, legal, or irreversible (§11).
6. **Don't shrink the problem.** Hard parts stay in scope and in the reports until they are solved, proven blocked, or I agree to change the scope.

"Must" means mandatory. "Should" means a strong default, and any deviation needs a documented reason. "May" means optional.

### 0.1 Session continuity
This project will span many sessions and context compactions. Before any other work:
- Create the project directory (§2.3), initialize Git, and save this brief verbatim as `docs/BRIEF.md`. It is the authoritative specification. Re-read the relevant sections before starting each milestone.
- Create `CLAUDE.md` in the project root. It holds a condensed version of §0, §2.2, §3, §11, and §12, plus pointers to the files below.
- Keep these documents up to date throughout the work, not only at the end:
  - `docs/STATE.md`: the current stage and milestone, what is done, what is in progress, next steps, and questions waiting on me.
  - `docs/FINDINGS.md`: the findings register. Each entry has an ID, the claim, its label, an evidence pointer, the build or version, the date, and what superseded it (if anything).
  - `docs/DECISIONS.md`: the decision log. Each entry has the context, the options, the choice, the evidence, and its approval status.
  - `docs/MISSIONS.md`: the main-story mission inventory and status (§4.2, §8.4).
  - `docs/RISKS.md`: the risk register.
  - `docs/HASHES.md`: SHA-256 hashes of original inputs and generated artifacts.
- At the start of every new session, read `CLAUDE.md` and `docs/STATE.md` before doing anything.

## 1. Goal and definition of done

### 1.1 Goal
Modify **The Warriors, PS2, USA version (SLUS-21215)** so that up to four real players can play the normal story campaign together over the internet. Each player runs their own copy of the game in their own PCSX2 instance on their own computer.

The original game supports two-player co-op. That is my statement: verify which missions support it and how it works.

Each player must have:
- their own genuine playable character (§4.3);
- their own controller or mapped input;
- their own independent, full-screen camera view on their own computer (except the shared view when all players are close together, §4.5);
- their own correct HUD;
- their own health, damage, moves, animations, and player-specific gameplay behavior;
- full participation in combat, objectives, pickups, mission progression, cutscenes, deaths, and respawns.

All participants share one gameplay session, and the game state must stay consistent across computers as defined in §5.7.

### 1.2 Session sizes and regression
- "Up to four" means online sessions of **2, 3, and 4 players** must all work.
- With fewer than four players, the mission behaves normally in the unfilled slots: companions that a player would have replaced stay AI-controlled.
- With the mod installed, single-player and original local two-player play must still work.

### 1.3 Done
The project is done when:
- every main-story mission has a final status from §8.4, backed by recorded evidence;
- the deliverables in §10 exist;
- the final report states plainly what works, what is partial, what is blocked, and what failed.

### 1.4 Not done
None of these, by themselves, completes a milestone or the project: code compiles; a patch applies; four characters appear on screen; emulator instances exchange messages; a lobby connects; a mission works once; scripted bots pass a test that requires human play.

## 2. Environment, file protection, project layout

### 2.1 Environment (my description; verify each item and record versions and hashes)
Working root: `C:\Users\PC FORCE\Desktop\New folder`
- `ghidra_12.1.4_PUBLIC`: Ghidra 12.1.4.
- `pcsx2-v2.9.115-windows-x64-Qt`: portable PCSX2 v2.9.115. The PS2 BIOS is configured and the game boots.
- `Warriors The (USA) (EnFrDeEsIt)`: a directory containing a game image.
- `Warriors, The (USA) (En,Fr,De,Es,It).iso`: the original ISO, about 4 GB.
- Java JDK 25, Git, and 7-Zip at `C:\Program Files\7-Zip\7z.exe`.
- Hardware: RTX 5090, 64 GB RAM, AMD Ryzen 9 9950X3D. This machine can run several PCSX2 instances at once.

Also:
- Hash both the root ISO and the image in the game directory, determine whether they are the same dump, and record which one you use.
- List the other tools available: C/C++ compilers and build tools, CMake, Python, PS2/MIPS toolchains, and network tools. Prefer portable tools inside the project. Ask before installing anything system-wide (§11).
- Other players will have different hardware: CPU vendor, GPU, and OS configuration. Treat this as relevant to determinism.

### 2.2 Protected originals
1. Never modify, overwrite, rename, move, or delete the original ISO or the game-image directory. Open them read-only. Extract files only into the project's `local/` area.
2. Never modify the existing PCSX2 installation, its settings, memory cards, caches, or BIOS files. Don't launch the original installation for experiments, because launching it can rewrite its settings and memory cards. Copy it into the project sandbox and run the copies.
3. Don't modify the Ghidra installation directory, and keep Ghidra projects inside the project. If you need a Ghidra extension, install it only in your user profile and record its source, version, license, and hash.
4. Before any write, confirm that the target path is inside the project directory or a temporary directory.
5. At the start, record SHA-256 hashes of the ISO, the game image, the BIOS files, and the PCSX2 executable. Re-verify the ISO and BIOS hashes in every milestone report.

### 2.3 Project directory
Create `C:\Users\PC FORCE\Desktop\New folder\warriors-4p\`. If it already exists, inspect it and ask me before reusing it. Suggested layout, which you may adjust if you document why:

    warriors-4p/
      CLAUDE.md  README.md  .gitignore  .gitattributes
      docs/        brief, state, findings, decisions, risks, missions, hashes,
                   research notes, plan, protocol spec, test reports, milestone reports
      tools/       hashing, extraction, analysis and Ghidra scripts, patch generation, build scripts
      analysis/    your own derived notes: address/structure maps, labels, Ghidra export scripts
      mod/         game patch sources
      emulator/    PCSX2 integration or fork, pinned to an upstream version, with build scripts
      net/         session, transport, and synchronization components
      tests/       harness, experiments, scripted inputs/bots, test plans, impairment profiles
      evidence/    logs, metrics, hash logs (large media gitignored, with a committed manifest)
      local/       GITIGNORED: extracted game files and executable, Ghidra project database,
                   sandbox PCSX2 copies, BIOS copies, memory cards, savestates, screenshots, video
      build/ dist/ GITIGNORED: build outputs and release packages

### 2.4 Git, hashes, licensing, distribution
- Track everything needed to reproduce your work from my original inputs: scripts, patch sources, emulator changes, networking code, configuration, docs, build instructions, and hashes. Commit often with meaningful messages, and tag the end of each milestone.
- Never commit any of the following. Enforce this with `.gitignore` and check `git status` before each commit.
  - the ISO or BIOS;
  - extracted game files or the game executable;
  - Ghidra databases, which contain disassembled copyrighted code;
  - savestates, memory cards, or copyrighted media.
- Record SHA-256 hashes of generated artifacts: patches, builds, and packages.
- The distributable package may contain only:
  - your mod code and patches;
  - tools, configuration, networking components, and documentation;
  - a custom emulator build if one is needed, and only in a form that complies with its license.

  It must never contain the game, the ISO, the BIOS, or extracted copyrighted assets. Players apply the patches to their own legally obtained copies, which are verified by hash.
- Record the license of every third-party component. If you modify and distribute PCSX2, verify its license and meet its source-distribution obligations.

## 3. Evidence standard
Every finding gets exactly one label:
- **VERIFIED**: supported by inspected files, disassembly, reliable documentation, or reproducible testing. Cite the evidence and state which build and version it applies to. Evidence can be any of these:
  - a file and offset;
  - a Ghidra address and function;
  - a runtime address and how it was found;
  - a test ID and log path;
  - a documentation URL and access date.
- **HYPOTHESIS**: plausible but unconfirmed. State what would confirm or refute it.
- **BLOCKED**: investigation cannot proceed because of a documented obstacle. State what would unblock it.
- **FAILED TEST**: an experiment or implementation did not meet its pre-declared criteria. Keep the record.

Rules:
- Names you give to functions, variables, and structures are your own labels unless the binary contains symbols. Say so.
- A memory address is verified only for the build and context in which you observed it. Note whether it is static or dynamically allocated.
- Label the environment of every test:
  - **SINGLE-PC**: several instances on this computer.
  - **LAN**: separate computers on one local network.
  - **INTERNET**: separate computers on different networks, connected over the public internet.

  Also record whether the players were humans or scripted bots, and whether network impairment was simulated.
- Report negative results as prominently as positive ones. Don't upgrade a hypothesis without new evidence. Mark superseded findings instead of deleting them.
- External sources such as wikis, forums, and earlier mods can give you leads. Confirm any claim about this game against the game itself.

## 4. Gameplay requirements

### 4.1 Scope: the main story
- Identify the actual main-story missions from evidence in the game: mission tables, script data, string tables, save-progress data, and observed progression. Don't invent mission names, and don't assume every mode is story content.
- Classify every mission, mode, and activity you find as MAIN STORY, OPTIONAL/NON-STORY, or UNRESOLVED, with evidence. Ask me about anything that stays unresolved.
- Every main-story mission must support four-player online play, including missions that don't originally support two-player co-op.
- Optional side quests, street activities, free-roam activities, and other non-story modes are out of scope, so don't spend effort adding four-player support to them. Engine-level changes must not break them unnecessarily, though. With the mod installed they must still load and work at their original player count (smoke test, §8.2).
- If the story requires moving through hub or free-roam areas between missions, the session must survive those transitions with every player still connected and without desync or crash. Report what you find and propose how to handle it in the plan.

### 4.2 Mission inventory
`docs/MISSIONS.md` records the following for every main-story mission:
- its identifier as it appears in game data, and the evidence for its classification;
- its original player support: single-player or two-player co-op, verified;
- the characters involved and each companion's role;
- any scripting that assumes a particular character or player count;
- the planned strategy for players 3 and 4;
- any fallback and its justification;
- its test status (§8.4).

### 4.3 Four genuine player characters
Players 3 and 4 must be genuine player characters, handled by the game's real player systems. Shadows, puppets, and visual-only copies don't count. Neither does a character that another player controls indirectly.

Over the network, this applies to whichever simulation is authoritative: every instance under lockstep, or the host under host-authoritative replication. In that simulation, players 3 and 4 must be real player entities processed by the same systems as players 1 and 2. Their representation on other machines may come from the synchronization method, as long as their gameplay effects are genuine and consistent everywhere. A character whose gameplay effects are faked or only displayed doesn't count.

Investigate each of these systems instead of assuming how it works:
- player identity, slot and index handling, and the input path: how the game polls controllers, and whether it supports or ignores a multitap;
- character models, rigs, animations, moves, and how each character's resources are loaded;
- health, damage, knockdowns, death, respawn, and revive;
- combat, how enemies choose targets and spread their attention, and NPC interactions;
- physics, collision, and movement;
- pickups, doors, objectives, and interaction prompts;
- the HUD, scoring, meters, and player status;
- sound, gameplay feedback, and controller vibration;
- cutscenes, checkpoints, mission transitions, and game-over logic;
- engine limits:
  - entity and character pools;
  - free memory (PS2 main RAM is 32 MB);
  - animation and streaming budgets;
  - per-player arrays sized for two, and loops or checks hard-coded for one or two players;
  - code overlays or modules loaded per mission.

Don't assume that duplicating a character model or changing a player-count variable is enough. Find everything that is hard-coded for one or two players.

### 4.4 Companions, enemies, and rivals
**Friendly AI companions**
- If a friendly companion has no mission-critical responsibilities and can safely be removed, player 3 or 4 replaces it. Once you have verified how the original game gives player 2 a character, prefer that same mechanism.
- If a companion is needed for anything mission-critical, preserve that NPC and its behavior, and add a separate playable character for player 3 or 4. Mission-critical roles include a story event, unique dialogue, objectives, escort behavior, and scripted actions.
- Use player 2 as the template for added characters wherever possible: the same model, rig, animations, moves, stats, and player behavior. Minor cosmetic differences are acceptable. Where player 2 can't serve as a template in a mission, document why and propose an alternative.
- A companion's special role is never, by itself, a reason to disable players 3 and 4.
- For each mission, record each companion, its role, the evidence for that role, and the decision: replace, or preserve and add.

**Enemy gangs and rival competitors**
- Never replace enemy gangs, rival competitors, or any other opposing AI with players.
- Example: in a story mission with a graffiti competition, the Warriors side has four real players and the opposing gang stays AI-controlled. Keep the rival team's behavior, the competition mechanics, scoring, objectives, timers, and story progression intact.
- Investigate mission scripting that assumes a particular character or player count, and adapt it. Some original two-player conditions will need extending, such as "both players reach the exit". For each one, define the four-player meaning and record the choice.

**Fallback (last resort)**
- Disable players 3 and 4 on a required story mission only when evidence shows that a genuine technical limitation prevents safe, reliable four-player play. Examples are a hard engine limit, or repeated failed tests after documented attempts. "An NPC can't be replaced" is not a valid reason.
- A fallback keeps the original two-player behavior wherever possible. Document the precise reason, the evidence, the attempts, and the tests.
- Report every proposed fallback. It isn't final until I've acknowledged it.

### 4.5 Independent cameras and HUD
- By default, each player sees a full-screen view on their own computer, from their own camera, following their own character, with their own HUD.
  - The final result has no split screen.
  - No player is ever shown streamed video of another player's screen.
  - No player is put on a shared or another player's camera, except under the "all players close together" rule below.
- Each player controls their own camera with whatever camera controls the original game gives a player. Moving it never moves anyone else's camera. When players are far apart in the map (§4.6), each player sees their own surroundings.
- **All players close together.** First verify what the original two-player mode does with the camera when the two players are close to each other. If it switches to one shared camera, such as one view framing both players, reproduce that for four players under these rules:
  - The shared camera is used only when **all** active players in the session are close together: all four in a four-player session, all three in a three-player session, both in a two-player session. Use the original game's own closeness rule, extended so that every active player must meet it, and document exactly how you extended it.
  - While it's active, every player's screen shows the same shared camera, full screen, framing all the active players. Each player still sees their own HUD. Camera controls in this mode follow the original.
  - As soon as any player moves away, everyone returns to their own camera. Transitions in both directions should look like the original's.
  - If only some players are close together (for example, players 1 and 2 together while players 3 and 4 are elsewhere), everyone keeps their own camera.
  - If the original two-player mode doesn't change the camera when the players are close, there is no shared camera at all, and everyone always has their own camera.
- Investigate:
  - camera state and how it is tied to players;
  - how the original co-op handles the camera and screen (a shared view, split screen, or something else), including what changes when the two players are close together or far apart;
  - camera updates and transitions, and who owns the HUD;
  - camera behavior during exploration, combat, death, respawn, cutscenes, and mission transitions;
  - how the original co-op handles players moving apart (any tethering, teleporting to a partner, or shared streaming area), so that four-player play can copy it (§4.6).
- **Critical:** find out which presentation state can differ between instances without changing the gameplay simulation. Camera position often feeds world streaming, visibility or level-of-detail culling, AI or animation update rates, audio, and disc reads, and any of these can make instances diverge. Test this explicitly (experiment E2).
- Cutscenes play for every player and stay in sync with the session.
- Four characters do not automatically mean four cameras.

### 4.6 Session policies (decided by me)
These are my decisions. Implement them as written. If evidence shows that one can't be implemented reliably, report the evidence and propose the closest alternative. Don't change a policy without my approval.

- **Pause.**
  - Any player can pause. The game pauses for all players and shows who paused it (for example "Paused by Player 3").
  - Only the player who paused, or the host, can unpause.
- **Cutscene skipping.**
  - A cutscene is skipped only when every connected player has pressed skip.
  - Show the vote on every screen (for example "2/4 want to skip").
- **Saving.**
  - Every player keeps the shared co-op story progress on their own PC, so any of them can host the next session from where the group stopped.
  - Co-op progress is stored separately from each player's own single-player save and must never overwrite it.
  - You design the mechanism, which must keep all instances consistent. For example, all instances may need identical memory card contents when a session starts.
- **Joining.**
  - Players join only in the lobby before a mission starts. A player who arrives mid-mission waits in the lobby for the next mission.
  - There is no drop-in during a mission.
- **Disconnects.**
  - When a player's connection drops, the game freezes for everyone with a countdown (for example "Waiting for Player 2… 60s"). The timeout is 60 seconds.
  - If the connection returns in time while that player's game is still running at the same point, play continues.
  - If it doesn't, the host chooses between two options. The first is to continue without that player, handling their character in whatever way keeps the mission working. Propose that handling with evidence (for example, a replaced companion returns to AI control, or the character is removed). The second is to restart from the last checkpoint without that player.
  - A player whose emulator crashed or was closed can't rejoin mid-mission (see Joining). They rejoin from the lobby at the next mission start or checkpoint restart.
- **Host leaving.**
  - If the host leaves or crashes, the session ends for everyone.
  - Because of the Saving policy, every player keeps the co-op progress up to the last save.
  - Host migration is out of scope.
- **Player separation.**
  - Players move freely anywhere within the same map and mission, as the original two-player mode allows. One player can be at point A, another at point B, and a third at point C at the same time.
  - First verify exactly how the original two-player mode handles players moving apart, then reproduce that behavior for four players. If the original has its own rule, for example pulling player 2 back when too far away, apply that same rule to players 2, 3, and 4.
  - Don't invent a new leash, distance limit, or teleport-to-group rule.
  - Keep any pull, regroup, or teleport that a mission's own scripting performs (for example, a story moment that gathers the group), and apply it to all players.
  - If evidence shows the engine can't keep the world correct for widely separated players (areas not loaded, AI or objectives breaking), report it with the evidence and propose options. Don't add a limit without my approval.
- **Difficulty.**
  - Keep the original difficulty: the same enemy numbers and strength regardless of player count.
  - Don't scale difficulty in this project. If the original co-op already scales anything with the player count, report it and propose how it extends to three and four players.
- **Friendly fire and player-to-player collision.**
  - Use the same rules as the original two-player mode, applied to all four players.
  - Verify what those rules are.
- **Game over.**
  - Extend the original two-player game-over rule in the most natural way. For example, if the original fails the mission when both players are down, the four-player version fails when all active players are down.
  - Verify the original rule and document the four-player version. If the natural extension is unclear for any mission, ask me.
  - Mission-specific failure conditions stay exactly as in the original, such as a character you must protect dying or a timer running out.
- **Player slots and characters.**
  - Before each mission, players choose their player number (1 to 4) in the lobby. If nobody chooses, the host is Player 1 and the others take slots in the order they joined.
  - Which character each slot controls in a mission follows the companion strategy in §4.4.

## 5. Networking and emulator requirements

### 5.1 Four separate layers
Design and document four layers. Solving one does not solve the others.
1. **Session:** creating and joining sessions with friends, player identity and slot assignment, and version compatibility.
2. **Transport:** moving data between computers, including NAT traversal, relays, reliability, and encryption.
3. **Simulation synchronization:** keeping the game simulation consistent across instances.
4. **Local presentation:** each instance's own camera, HUD, audio, and controller feedback.

Put the transport behind an interface so it can be replaced without rewriting the synchronization or session logic, for example when switching to a different relay service.

### 5.2 Architecture chosen from evidence
- Don't pick a familiar library or approach by default. Don't assume the installed PCSX2 provides any multiplayer synchronization; verify what it has.
- Determine whether the solution needs changes to the game executable, its memory structures, its gameplay systems, PCSX2, or a combination of these.
- Evaluate at least these approaches:
  - deterministic lockstep with synchronized inputs, where every instance runs the full simulation, only inputs are exchanged, and input delay hides latency;
  - rollback or prediction variants, after measuring whether PCSX2 state save and restore are fast enough (don't assume either way);
  - host-authoritative state replication, with client-side prediction for the local player;
  - a dedicated server, such as a headless emulator acting as host (don't assume a server can run the PS2 game logic without an emulator and substantial work);
  - hybrids, such as lockstep with periodic state hashing and an authoritative resync after divergence.
- For each approach, document:
  - how it keeps the simulation consistent;
  - how it allows independent cameras;
  - what it needs from the game patch and from the emulator;
  - its latency behavior, measured where possible;
  - its bandwidth, failure modes, effort, and risk.

### 5.3 Determinism questions to answer with evidence
- On one machine, do two instances given identical inputs stay identical, and for how long?
- Do they stay identical across different machines with different CPU vendors and GPUs? This needs other computers (see §11).
- Examine these candidate sources of divergence:
  - emulator settings: recompiler vs. interpreter, multi-threaded VU, cycle rate and skip, speed hacks, fast boot, disc-read timing, audio sync, frame limiting;
  - renderer readbacks into game memory;
  - values derived from the host clock, such as the PS2 real-time clock;
  - memory card contents and timestamps, BIOS version, and system language;
  - patches and cheats;
  - the game's RNG and how it is seeded;
  - physics, AI, and scripting;
  - streaming triggered by camera position;
  - logic that depends on frame time, and the timing of input polling.
- Input injection: every instance must receive every player's input at the same emulated point. Determine which of these is needed:
  - external tools, for example an IPC interface such as PINE if this build has one (such interfaces may run asynchronously to emulation);
  - changes to PCSX2 itself, for example holding frame advance until every input for a frame has arrived.

### 5.4 PCSX2 integration
- List what this exact build offers, verifying that each feature exists and how it behaves:
  - IPC and remote memory access, the debugger, and the patch and cheat (pnach) system;
  - savestates and input recording;
  - multitap emulation and controller configuration;
  - command-line options, portable mode, and support for multiple instances.
- Work out how to run several isolated instances on one PC, each with its own settings, memory cards, and IPC slots and ports, without touching the original installation.
- If the emulator needs changes, establish these before committing to them: source code matching this version, toolchain availability, build time, license obligations, the cost of maintaining a fork, and how the fork would follow upstream updates.
- Evaluate the ways the patch could be delivered, covering the technical and distribution implications of each:
  - runtime patches through the emulator's patch system;
  - a modified executable rebuilt into an image that each user generates;
  - code injected into unused memory;
  - hooks inside the emulator.

### 5.5 Session and transport options
**Steam is out of scope.** Don't use Steam, the Steamworks SDK, Steam lobbies, Steam networking or relay services, or Steam Remote Play, and don't make the solution depend on Steam in any way. Prefer options that need no third-party platform account. Any service that needs an account still requires my approval (§11).

**Existing ways to play PS2 games online through an emulator: evaluate these first.** I've been told there are existing ways to play PS2 games online with an emulator. Find out what currently exists and verify how each one works. For each, say whether it can help this project and with which of the four layers in §5.1:
- **PCSX2's network adapter emulation (DEV9),** combined with LAN-tunnelling or VPN services. This only helps games that have their own LAN or online multiplayer code. Before relying on it, check whether The Warriors has any such code, for example network modules on the disc or network calls in the executable.
- **Netplay builds, forks, or plugins of PCSX2** that synchronize inputs between players. For each one that exists today, check:
  - whether it's maintained, and which PCSX2 versions it supports;
  - how many players it allows;
  - its license;
  - whether it actually stays in sync.

  A suitable one might be reused or studied for the synchronization and transport layers. It would not provide four players, independent cameras, or per-player HUDs; those still need the game modification.
- **Screen-streaming tools** (Parsec-style remote play): they show everyone the host's screen, which §4.5 rules out. Note that briefly and move on.

Report what you find, labelled per §3. If a method I might have heard about doesn't apply to this game, say so and explain why.

**Other session and transport options.** Evaluate each option against current documentation. Cover requirements, availability, terms, cost, latency, NAT and firewall compatibility, how easily friends can join (join codes, invite links, or a direct address), and maintenance.
- **Direct peer-to-peer:** NAT traversal (STUN/ICE-style libraries), UPnP, and port forwarding.
- **Open-source game networking libraries** that need no platform account, such as ENet or GameNetworkingSockets: verify their features, including reliability channels, encryption, relay support, and NAT traversal.
- **Custom relay services**, such as a self-hosted TURN or relay server: hosting cost and latency.
- **Other third-party networking services:** verify their terms, cost, and whether they need accounts.
- **Overlay VPNs** such as Tailscale, ZeroTier, or Radmin VPN: useful for early internet testing, because they separate NAT problems from synchronization problems. Consider them as a supported fallback too.
- **Dedicated servers**, where justified.

Priorities, in order: responsive combat, easy joining for friends, stable connections, NAT and firewall compatibility, and reasonable maintenance and cost. Never describe anything as "lag-free" or "low-latency" without measurements. Report round-trip time, input delay in frames, jitter, packet loss, and bandwidth.

### 5.6 Compatibility and security
- Run a version handshake before every session starts. It checks:
  - the protocol version, mod build ID, and emulator build ID;
  - that the game image hashes match (each player hashes their own copy locally);
  - the settings profile;
  - BIOS compatibility, if your tests show that the BIOS version matters.
- Security baseline for a friends-only tool:
  - no network message can cause arbitrary memory writes, or run any code the defined protocol doesn't call for;
  - validate message types and sizes;
  - authenticate joins, for example with join codes;
  - open no unnecessary listening ports;
  - document any firewall changes.

### 5.7 Consistency definition (made measurable in the plan)
- Discrete gameplay state must be identical across instances at defined checkpoints. This covers mission and objective flags, health, deaths, knockdowns, pickups, inventory, scores, timers, which enemies are alive or dead, and cutscene and checkpoint state.
- Under lockstep, hashes of the simulation state must match every N frames, excluding memory regions proven to be presentation-only. Any mismatch is a desync.
- Under replication, specify tolerances for continuous values such as positions, and the maximum correction delay.
- Desync detection, logging, and recovery must exist. Logs record the first divergent frame and a memory diff; recovery can be an authoritative resync. Measure how often desyncs occur.

## 6. Stage 1: investigate, experiment, plan, then STOP

**Allowed in Stage 1:**
- read-only inspection of the originals, and extracting files into `local/`;
- static analysis in Ghidra;
- runtime observation and temporary memory experiments in sandbox PCSX2 copies;
- throwaway scripts and minimal prototypes for feasibility experiments, kept under `tests/experiments/` and labeled as experiments;
- reading current documentation, and downloading open-source code to evaluate (record versions and licenses);
- building PCSX2 from source, unmodified or with minimal instrumentation for an experiment.

**Not allowed in Stage 1:**
- implementing the mod: persistent game patches, the networking product, or an emulator fork beyond experiment instrumentation;
- creating accounts, spending money, or publishing anything.

If you're blocked during Stage 1, ask me. Otherwise keep going until the plan is ready.

### 6.1 Workstreams
- **A. Setup:** project skeleton, Git, `CLAUDE.md`, hashes, the tool inventory, sandbox PCSX2 copies, and a list of missing toolchains.
- **B. Static analysis:**
  - Map the disc's file structure. Find the main executable, verify its name, and load it into Ghidra.
  - Check whether this Ghidra version decodes R5900-specific instructions: MMI, COP2/VU0 macro instructions, and 128-bit loads and stores. If it doesn't, evaluate Emotion Engine extensions for compatibility with Ghidra 12.1.4 and for their licenses.
  - Identify the main loop and frame timing, controller input, player structures and player-count assumptions, the camera, the HUD, the mission and script system, entity spawning and pools, the RNG, the memory layout and free memory, and any code overlays or modules loaded at runtime.
- **C. Runtime analysis:** in sandbox PCSX2, use the debugger, memory search, and savestate diffs to confirm the player, camera, input, and mission-state structures. Observe the original two-player co-op closely: how player 2 joins, which character they get, and how the camera, screen, and HUD behave.
- **D. Mission inventory** (§4.1, §4.2), with evidence.
- **E. Emulator and determinism investigation** (§5.3, §5.4).
- **F. Session and transport research** (§5.5): existing emulator online and netplay methods first, then the other options, using current documentation, terms, and prices.
- **G. Patch delivery and distribution analysis** (§2.4, §5.4).

### 6.2 Feasibility experiments, kill tests first
Find the smallest experiments that could prove your preferred architecture unworkable, and run them before any expensive work. Before running an experiment, write down its hypothesis, method, and pass/fail criteria. Afterwards, record the result, its label, and the evidence path. If an experiment rules out the preferred approach, say so plainly and re-plan.

Run at least these:
- **E1 Same-machine determinism.** Give two sandbox instances identical settings and the same starting state. Feed both an identical scripted input sequence long enough to include combat with AI enemies. Compare game-memory hashes at frame-aligned points, find the first divergence if there is one, and look for a settings profile that is deterministic.
- **E2 Presentation isolation.** Repeat E1, but change only the camera and local presentation in one instance. Does the gameplay state diverge? If it does, identify which camera-dependent systems feed the simulation.
- **E3 Deterministic input injection.** Can every instance receive the inputs for all player slots at exactly the same emulated point? Is the installed PCSX2 enough, or does it need modifying?
- **E4 Extra player feasibility.** In a representative mission, using temporary experiments only, can the engine run a third (and a fourth) genuine player entity with its own input? Record what breaks.
- **E5 State snapshot cost.** Measure the full emulator state size, save and load times, and transfer time at realistic bandwidth. This decides whether rollback and resync are viable.
- **E6 Cross-machine determinism.** Run E1 across different computers. This will probably need my help: design the experiment and tell me exactly what you need.
- **E7 Transport smoke test (optional).** Measure round-trip time and NAT behavior of the candidate transports, if you can do so without creating accounts or spending money.

### 6.3 The Stage 1 plan
Write `docs/plan/STAGE1_PLAN.md` and give me a short summary in chat with the file's path. The plan must contain:
1. **Feasibility assessment:** overall and for each component, with honest confidence levels and what could make the project infeasible.
2. **Verified findings** with evidence, referenced by `FINDINGS.md` ID.
3. **Hypotheses and unresolved questions**, each with how it will be resolved.
4. **Main-story mission scope:** the inventory with classification evidence, and anything unresolved that needs my input.
5. **Player and companion strategy:** the input path for players 3 and 4, how genuine player entities are created, the template approach, the engine limits found, and a preliminary companion analysis for each mission.
6. **Independent camera and HUD architecture**, with the E2 results.
7. **Online networking and emulator integration:** the four layers, which changes go in the game and which in PCSX2, and an emulator build plan if one is needed.
8. **Architecture comparison and recommendation:** a comparison table, the recommended architecture, and why you rejected the others.
9. **The first critical proof of concept**, with its exact scope and pass/fail criteria.
10. **Milestones and dependencies** (§7): exit criteria, risks, and rough relative effort with the uncertainty stated.
11. **Testing strategy** (§8), including what needs other computers or people and what I must do personally.
12. **Fallback conditions:** explicit criteria based on evidence.
13. **Session policies** (§4.6): how each decided policy will be implemented, and any that evidence suggests can't be implemented as written, with your proposed alternative.
14. **Project structure, deliverables, and licensing and distribution analysis.**
15. **Decisions I need to make**, each with your recommendation.
16. **Risk register summary.**

**Then STOP.** Don't start any Stage 2 work. Wait for my explicit approval.

Approval means a message from me that explicitly approves the plan, possibly with changes, for example "Approved, proceed with Stage 2". Questions, comments, partial feedback, and silence are not approval. If I approve with changes:
1. update the plan;
2. record the approval in `docs/DECISIONS.md`;
3. confirm the changes back to me before starting.

## 7. Stage 2: implement after approval
Work through the approved milestones, testing the riskiest assumptions first. This is the default sequence; the approved plan may refine it.
- **M1 Critical proof of concept:** eliminate the biggest risk found in Stage 1. For example, show that instances on one PC stay synchronized through a mission segment that includes combat, each with its own independent camera.
- **M2 Genuine four-player local gameplay:** four genuine player characters with independent inputs in one representative main-story mission, on SINGLE-PC.
- **M3 Independent cameras and HUD:** each instance renders full-screen from its local player's camera, with that player's HUD, without the simulation diverging. Instances switch to the shared camera only under the all-players-close-together rule (§4.5). This must hold through exploration, combat, death and respawn, cutscenes, and transitions.
- **M4 Synchronization layer:** the approved sync approach for 2 to 4 instances over loopback and LAN, with desync detection, logging, recovery, and impairment tests.
- **M5 Session and transport:** the join flow, slot assignment, version handshake, and NAT traversal or relay as approved. Test on LAN first, then over the internet with my participation.
- **M6 Mission-by-mission enablement:** companion replacement or preservation, script adaptation, and per-mission testing until each mission reaches a final status. Start with missions that have original co-op and simple companion roles. Then move to the harder ones: missions without co-op, missions with mission-critical companions, and competitions.
- **M7 Robustness:** long sessions, disconnect and reconnect, timeouts, packet loss and jitter, and hunting for crashes and softlocks. Also run regression tests on single-player, original two-player play, and optional content.
- **M8 Packaging and documentation:** the package, instructions, a legal review of the package contents, and the final report.

Write each milestone's exit criteria before work on it starts. A milestone is met only with test evidence, and it ends with a tagged commit and a milestone report (§9).

If evidence invalidates the approved architecture or a milestone's premise, stop, report, propose alternatives, and wait for my approval.

## 8. Testing and acceptance

### 8.1 Test infrastructure
Build tooling that makes tests repeatable:
- launching N isolated sandbox instances with a chosen settings profile and slot assignment;
- scripted input playback and bots for any player slot;
- state hashing, desync checks, and logs;
- network impairment (latency, jitter, loss, reordering, disconnects), preferably built into the transport layer so results are reproducible (external tools may also be used);
- local-only savestates or memory cards for quick per-mission testing.

Bot tests are good for regression and synchronization checks. They don't replace human play where a requirement concerns how the game plays: control, responsiveness, camera, and HUD. Label which kind of test you used.

### 8.2 Per-mission coverage
Test every main-story mission for:
- four real characters with independent inputs, plus 2-player and 3-player sessions;
- health, combat, damage, moves, animations, and targeting (enemies engage all players, not only players 1 and 2);
- the HUD, scoring, meters, pickups, and objectives;
- death, respawn, game over, retry or checkpoint restore, mission completion, and transitions;
- independent cameras and player-specific HUDs on every instance;
- switching between each player's own camera and the shared close-together camera (§4.5), if the original has one: it switches only when all active players are close, and switches back as soon as any player leaves;
- preservation of mission-critical NPCs and their behavior;
- correct enemy and rival AI;
- cutscenes, checkpoints, objectives, competitions, and story progression, including that progress is saved and the next mission unlocks;
- synchronization throughout the run, with desync checks enabled;
- latency, jitter, packet loss, disconnects, timeouts, and desync recovery;
- crashes, softlocks, and audio or graphics corruption;
- at least one complete play-through from mission start to completion in the final configuration.

Also run:
- regression tests of single-player and original local two-player play with the mod installed;
- smoke tests confirming that optional content loads and works at its original player count.

Keep SINGLE-PC, LAN, and INTERNET results separate, and keep local four-player results separate from genuine online results.

### 8.3 Measurements
Report these measurements, each with its test conditions:
- round-trip time and input delay in frames;
- jitter and packet-loss tolerance;
- bandwidth per player;
- desync frequency and resync time;
- CPU and memory cost per instance.

### 8.4 Mission statuses
Every main-story mission ends with exactly one of these statuses, citing test IDs and evidence:
- **FOUR-PLAYER ONLINE VERIFIED:** every required test passed in a four-player session on four separate computers, connected over the public internet with the release's connection method. The mission was played from start to completion with no unresolved desync, crash, or softlock, and the 2-player and 3-player session checks also passed.
- **FOUR-PLAYER LOCAL ONLY:** all four-player tests passed on SINGLE-PC, LAN, or both, but the four-computer internet test is missing or failed. State which setups passed.
- **TWO-PLAYER ONLINE FALLBACK VERIFIED:** players 3 and 4 are disabled for documented technical reasons, I have acknowledged the fallback, and two-player online play is verified over the internet.
- **ORIGINAL TWO-PLAYER FALLBACK VERIFIED:** the mission keeps its original behavior and has been verified to work with the mod installed. State explicitly whether that original behavior is single-player or local two-player.
- **BLOCKED:** implementation or testing cannot proceed because of a documented obstacle.
- **FAILED:** implementation was attempted and doesn't meet its criteria.

A mission is not verified while any required test is incomplete or failed. Interim reports may also use NOT YET TESTED or IN PROGRESS, but the final report uses only the six statuses above.

## 9. Reporting
Report in chat after every major milestone and whenever you're blocked, and save the report under `docs/reports/`. Each report includes:
- completed work, with commits;
- new verified findings;
- hypotheses and open questions;
- test results, with environment labels and measurements;
- changes to the mission status table;
- risks and blockers;
- deviations from the approved plan;
- next steps;
- tests I must perform personally, with exact step-by-step instructions and what to send back to you;
- confirmation that the original ISO and BIOS hashes are unchanged.

## 10. Deliverables
1. Technical research notes with supporting evidence (`docs/`, `analysis/`).
2. The approved architecture and implementation plan.
3. Reproducible mod source and patch-generation tools that work from a user's own game image, verified by hash.
4. Any required emulator integration or compatible custom build, with source, build instructions, and license compliance.
5. Networking components, configuration, and a protocol specification covering message types, versioning, the handshake, and the sync model.
6. A mission-by-mission test report.
7. Windows instructions for installation, controller configuration, and connecting online, written for non-expert players. They include what each player must supply themselves: their own game copy and BIOS.
8. A final status report that separates verified, incomplete, blocked, and failed features.
9. The Git history, reproducible build instructions, and checksums for inputs and outputs.
10. A package of legally distributable mod files and tools only. It contains no commercial game, ISO, BIOS, or extracted assets.

## 11. Stop and ask me before
- starting Stage 2;
- changing the approved architecture or a milestone's premise;
- making any mission fallback final;
- installing system-wide software, drivers, or services, or changing firewall, router, or network settings;
- creating accounts, accepting terms or developer agreements on my behalf, spending money, or using paid services;
- publishing, uploading, or sharing anything outside this computer;
- any action that could touch the protected originals;
- running tests that need other computers or people (tell me exactly what's needed);
- going ahead despite legal or licensing uncertainty about distribution.

Also stop and report as soon as evidence shows that a core requirement can't be met as specified. Whenever you ask, include your recommendation and the trade-offs.

## 12. Never
- Invent structures, function names, memory addresses, mission names or classifications, measurements, test results, or claims that online play works.
- Call anything "lag-free", or say it "works", without the tests and measurements to back it up.
- Commit or distribute the game, the ISO, the BIOS, or extracted copyrighted assets.
- Hide, delete, or soften failed tests.
- Quietly reduce scope, such as shipping fallbacks without approval, skipping hard missions, or substituting shared or streamed views for independent cameras. The only shared view allowed is the all-players-close-together rule in §4.5.
- Use Steam, or make the project depend on it.
- Treat a networking library, a lobby, an existing netplay build, or a screen-streaming tool as the whole solution. None of them provides four genuine players or independent cameras, and a library or lobby does not keep the simulation consistent.

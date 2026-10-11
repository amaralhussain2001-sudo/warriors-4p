# M2 research: HUD, Lua mission scripts and companions for 4 players (static analysis, 2026-10-11)

Scope: what the HUD, the mission scripts and the companion/join logic need so that players 3 and 4 are genuine
players. **Static analysis only; nothing was run.**
- Build: SLUS-21215 v1.03 (`local/disc/SLUS_212.15`).
- Sources: the Ghidra decompile (`local/analysis/all/*.c`), Ghidra listings (DumpListing, read-only project), the
  Lua pseudo-code (`local/analysis/pseudo/*.lua`) and `lua_bindings.tsv`.
- Function names are OUR labels (the ELF is stripped).
- Every quoted instruction word was read from the ELF.
- Script counts are regex counts over all 467 decompiled script chunks (story, Rumble and hub together) unless a
  level is named.

Related notes: `hud_layout.md`, `hud_scale.md`, `view_merge_rule.md`. Findings referenced: F-0020 to F-0062,
F-0095, F-0103.

---

## 1. HUD for 4 players (2x2 layout, own-view crop)

### 1.1 Structure (VERIFIED)
| Item | Where | 2-player limit |
|---|---|---|
| HUD manager | static 0x00600840 (164 code references, F-0061) | |
| Per-player HUD pointers | HUD+8 / HUD+0xC = 0x00600848 / 0x0060084C, indexed `(&DAT_00600848)[i]` in 24 functions | 2 entries; HUD+0x10 is a different field |
| PlayerHUD objects | filled by HUD init `FUN_001AD588` (loop `uVar10 < 2`). Normal levels: embedded at HUD+0x19130 + i·0x4A50 (0x00619970, 0x0061E3C0, ending at 0x00622E10 if HUD = 0x00600840). Levels 60-69 (Armies of the Night): heap objects of 0x4620 bytes (`FUN_0020FD80`) | 2 |
| PlayerHUD fields | +0x40F4 player index, +0x4120 vtable, +0x4144/+0x4148 name colours, +0x4104 forced-show flag, +0x4150 9 sub-widgets of 0x100 bytes (`FUN_00213060`) | |
| Radar objects | HUD+0x15D0 + i·0x2940; on/off `FUN_001B2610(HUD, i)` writes HUD+0x15D4+i·0x2940 with no bound | 2 |
| Rage/health panel layout | `FUN_00211EF8` writes per display mode: base vectors 0x0050FA10 + 16·i (static P1 (0.10, 0.05), P2 (0.785, 0.05); 0x0050FA30 = (0.04, 0.56) is a mode override); per-player element table 0x0050FA40 + 0x240·i; second table 0x0050FF00 + 0xC0·i; globals 0x00510040-0x00510050 | 2; index 2 of each table lands on the next table |
| Camera manager (pointer 0x0050CDB4, vtable 0x00538D78) | constructor `FUN_00194D58` builds 4 entries at +0x70 (stride 0x60) and 4 at +0x250 (stride 0x60), plus singles at +0x10, +0x1F0, +0x3D0 | **already 4.** HYPOTHESIS from order: 4 per-view 3D cameras and 4 per-view HUD cameras. The camera *system* arrays at 0x005D9148 still have 2 entries (F-0026) |

### 1.2 How HUD elements are drawn (VERIFIED, listings + decompile)

**Element object** (2D widget class: init `FUN_001A1DB8`, sprite setup `FUN_001A2918`):
- +0xC4 sprite index, +0xCA texture, +0xE4 sort depth, **+0xF9 view byte**.
- `FUN_001A1DB8` stores its stack argument (caller sp+0x10) into +0xF9: `sb v0,0xf9(s0)` at 0x001A1E10 (A20200F9).
- `FUN_001A2918` passes +0xF9 as the stack argument of `FUN_0018AEC0` (`sw a0,0x0(sp)` at 0x001A2978, AFA40000).
- `FUN_0018AEC0` forwards it to `FUN_001828E0`, which stores it in the sprite item: `sb s5,0x42(s6)` at 0x0018296C
  (A2D50042).

**Sprite flush** `FUN_00185D20` reads the item's view byte v with `lbu s1,0x42(v0)` at 0x00185E44 (90510042):
- if views > 0 and v < views, it uses the per-view HUD camera v (camera-manager vtable +0x7C(v), path at 0x00185E74);
- otherwise it uses the global HUD camera (+0x74, path at 0x00185EE8/0x00185EEC) and draws with
  `FUN_00197168(item, max(views−1, 0))`.

**2D position and size**:
- Camera-manager vtable +0x94 = `FUN_00195238`. It maps normalized screen coordinates to HUD camera space:
  x' = (W/H)·(x − 0.5), **depth = 1.1** (`lui at,0x3F8C` / `ori at,at,0xCCCD` at 0x001952E0/E4), vertical =
  0.5 − y.
- +0x9C = `FUN_00195330` scales a width by W/H.
- `FUN_001A2060` keeps the camera-space result at element+0x80.

**Rage/health panel**: the per-player panel init is `FUN_00212840(PlayerHUD, i)`.
- Its first test is `sltiu v0,s5,0x2` at 0x0021285C (2EA20002): **index ≥ 2 builds nothing**.
- The first element (name text) is created with view byte **0xFF**:
  - `li s6,0xff` at 0x00212980 (241600FF);
  - `sw s6,0x10(sp)` at 0x002129EC (AFB60010) before `jal 0x001A1DB8`.
- s6 = 0xFF is also used as a colour alpha byte (`sb s6,0x3(a2)` at 0x00212AE4), so s6 itself must not be changed.
- The panel has about 10 sub-element constructors whose view arguments are NOT all traced: `FUN_001A1DB8`,
  `FUN_001A0FD0`, `FUN_001C7730`, `FUN_001BEA00`, `FUN_001B6C50` (×3), `FUN_001C6928`, `FUN_001C9720`,
  `FUN_001AAF28`, `FUN_001AB010`.

**Answer to "where is the panel's size control"**:
- There is **no single size control.** Each element's size is a constant in the per-player table (examples:
  name-text size at table+0x30/+0x34 = 0x0050FA70/74 for P1; bar width/height at table+0x90/+0x94 = 0x0050FAD0/D4).
- Sizes are in HUD-camera units at depth 1.1, and the whole panel is drawn by the global HUD camera.
- Two working levers exist:
  - **(a) The view byte.** A view-tagged sprite is drawn by the per-view HUD camera, whose viewport is that view's
    quarter. With `hud_scale.md` patch 2B (undivided per-view window), it appears at half size, at its full-screen
    relative position inside the quarter.
  - **(b) Depth.** The HUD camera is perspective, so doubling the depth halves the size. This was confirmed at
    runtime for the radar (F-0103).

### 1.3 Proposed HUD design for 4 players: "per-view HUD" (HYPOTHESIS until runtime)
Goal: each quarter looks like a single-player screen, so after the 2× crop each player sees a normal full-screen HUD.

1. **Patch 2B** (`hud_scale.md`): 0x00196370 46160502→46000506 and 0x00196398 461703C2→460003C6, sessions only.
2. **Player-owned elements into their owner's view.**
   - Smallest test of the mechanism: 0x002129EC `AFB60010` → `AFB50010` (`sw s5,0x10(sp)`; s5 = player index).
     This tags only each panel's name text. Expected result: the name is drawn half size inside its own quarter.
   - Full version:
     - keep a "current HUD player" word in the free cave area (e.g. 0x000F0700). Set it to the PlayerHUD index on
       entry to `FUN_00212840` (init) and `FUN_00214138` (per-frame update), and back to −1 on exit;
     - replace the store at 0x0018296C with a jump to a cave. The cave does: if s5 == 0xFF and current ≥ 0 and
       layout mode (0x0050B1A4) == 2, then s5 = current; then `sb s5,0x42(s6)`.
   - This catches every sprite the panel code creates, without tracing each constructor.
   - Condition: view index = player index. This holds for 2 players (M1). For 4 it depends on `LayoutViewports`
     ordering (HYPOTHESIS).
   - If views < 2 (cutscenes), the flush falls back to the global camera, which is the original look.
3. **Shared elements in every quarter** (view 0xFF: objectives `HUDSetObjective` → `FUN_001B3940`, message/tutorial
   HUDs, prompts, subtitles; HYPOTHESIS that they all use view 0xFF).
   - Replace the global path of the flush (from 0x00185EE8) by a cave.
   - In layout mode 2 the cave loops v = 0..views−1 through the per-view path: camera +0x7C(v), begin +0x64,
     `FUN_00197168(item, v)`, end +0x6C. Otherwise it keeps the original.
   - Each quarter then shows a half-size copy at the single-player position. This fixes the "centred text sits on
     the corner where four quarters meet" problem.
   - Cost: views × draws for shared items only.
4. **Radar.**
   - P1/P2: patch 2A (in `[warriors-4p hud]`).
   - P3/P4 need two more radar objects in free RAM (2·0x2940 bytes), plus init/update/draw calls next to the P1/P2
     ones (`FUN_001C4388`, `FUN_001C5210`, `FUN_001AA630`).
   - Their position uses the 2A formula with the bottom row z = zs − d·Wz.
5. **PlayerHUD 2 and 3.**
   - Two more PlayerHUD objects: 2·0x4A50 bytes in free RAM (0x00096000-0x000EFFFF observed zero, F-0050).
   - A 4-entry pointer array, which means redirecting the 24 functions that index 0x00600848.
   - Lift the `< 2` limits in `FUN_001AD588`, `FUN_00212840` and `MakePlayer` HUD slots (F-0056).
   - Relocate the layout tables to 4 entries; P3/P4 can copy P1/P2's entries, since each panel lives in its own
     quarter.

Rejected alternatives:
- Halving ~70 table entries in `FUN_00211EF8`: the entries mix positions, sizes and w=1.0 components and are not
  classified.
- Depth trick inside `FUN_00195238` with the current-player word: workable, but it only covers elements that use the
  transform.

### 1.4 "1P/2P" markers and other per-player HUD state
- **Overhead indicator.** `FUN_0024A230` is called per player by `FUN_0024B780`, which loops over the player count.
  - It is called with view = the player's index when views > 1, using sprite slot 9 + view (`FUN_00185AB0(mgr, view+9)`).
    VERIFIED.
  - That it draws the 1P/2P label is a HYPOTHESIS: it uses the player colours, but the texture frame was not traced.
  - Its per-player state arrays have 2 entries: 0x00510530 (bytes), 0x00510538 and 0x00510540 (words; index 2 of
    the first overlaps the second), 0x006C72C8 (words). VERIFIED (decompile).
- **Player ground ring.** `FUN_00249CB0` has 3 hard-coded colours: P1 (0x86,0x1A,0x1A), P2 (0x80,0x64,0x00), and
  "other" (0x23,0x53,0xBC). It reads GameMgr+0x228/+0x22C directly. `FUN_00174320` guards `param_2 < 2` before
  using sprite slot param_2 + 9. VERIFIED.
- **Needed for 4 players:**
  - 4-entry state arrays;
  - P3/P4 colours;
  - sprite slots for views 2/3 (slots 11/12 are probably used by something else; not checked);
  - **3P/4P labels:** no such art is known in the game, so they would be our own textures or colour-only markers
    (HYPOTHESIS).
- **Other 2-entry per-player arrays (VERIFIED):**
  - command-enable bytes GameMgr+0x41E + 7·i (`FUN_0041DB08`, loop `< 2`);
  - inventory GameMgr+0x480 + 0x3F4·i (`FUN_0041E5B0` returns when index > 1).

---

## 2. Lua mission scripts

### 2.1 How scripts refer to players (VERIFIED)
- **Player gang creation.** A mission builds the gang with `PlayerGang[CHAPTER]()` → `AddWarriorsNN()` →
  `GangCreate(...)` plus `HuCreate(name, model, pos, angle, mdl, slot, gang)`. It then sets the globals
  `player = Warriors.X` and `player2 = Warriors.Y`. Example: WAD 7073 main_10/main_102 (Cochise slot 1, Snow).
- **HuCreate's 6th argument ("slot")** goes to human+0x1B1 (`FUN_00233D60`):
  - slot 1 calls `MakePlayer` immediately (player 1);
  - slots 2/3/4 are only a **join priority** (see §3).
  - Tally over all scripts: slot 0 ×2881, 1 ×116, 2 ×108, 3 ×20, 4 ×3.
  - Story levels with a slot-3 candidate: 3 (Ajax), 81 (Swan), 9 (Fox), 54 (cowboy/snow); flashbacks 82 (Vermin)
    and 92 (Cowboy).
  - The regex found no slot data for levels 99, 34, 51 and 84; they spawn the gang in another form (not parsed).
- **`HuGetPlayer(i)`** (core `FUN_00234FB8`) reads GameMgr+0x228+4i with **no range check**. Index 2 would read
  +0x230, the GameMgr tick counter. Scripts never call it (0 uses).
- **`HuIsAPlayer`** has 1,132 uses:
  - player2 277 (+68 `Rumble.player2`);
  - named companions 70 (hCowboy, hVermin, ...);
  - about 760 on callback arguments. These generic checks already work for any player.
- **Other calls made with `player2`:**
  - BrDead 167 (mostly Rumble), HuIsAlive 165, TeleportToFlag 89, CamTarget 85;
  - HuSetPreventRage 38, CreateWinCam 33, CameraMakeActive(…, player2) 20, IsInsideBox 20;
  - InvGiveItem 12, GangAddMember 11, HuRevive 8.
- **Join/leave notification.** The engine calls the Lua function registered with `SetMultiplayerCallback(name)` as
  (human, joined) (`FUN_0041B148`).
  - Shared WAD 4106 registers `InventoryPlayer2`: on join it gives the level's player-2 inventory to **player index
    2** (main_152/main_153, `InvGive*(…, 2)`).
  - Missions register their own callbacks through `SetPlayer2Callback` (~20 distinct; e.g. WAD 8262 `AnotherPlayer`
    stores the joiner as `Warriors["snow"]` and moves it between gang tables).

### 2.2 What would break or ignore players 3 and 4
| Area | Evidence | Effect with 3-4 players |
|---|---|---|
| `WarpPlayers(flagA, flagB)` | shared helper (WAD 7073 main_118 and others): revives the gang, then `TeleportToFlag(player, A0)`, `TeleportToFlag(player2, A1)`; 14 calls (level 5 uses it 3×) | P3/P4 are not teleported (left behind at scene cuts) |
| Both-in-box objectives | `IsInsideBox(box, player2)` 20× next to the player check (per-mission counts in MISSIONS.md) | P3/P4 are ignored; a scripted rule is needed ("all players" or "any player") |
| Join callbacks | 4106 main_152/153; mission callbacks such as 8262 `AnotherPlayer` | a 3rd/4th join re-runs "player-2" logic: duplicate P2 inventory, wrong gang-table keys |
| `HuIsAPlayer(player2)` branches | 277 | only the player2 companion switches between AI and human behaviour. A P3/P4 companion keeps its AI branch (scripts may suspend or teleport it in scenes while a human controls it): each branch needs review |
| Player death checks | `HuIsAlive(player2)` 165 | P3/P4 deaths are ignored by script logic |
| Game over (engine) | `GameOverCheck` (our label, `FUN_004197A8`) loops over all players (count GameMgr+0x224): game over when every player is down; revive and gang-revive checks use player 1 | **extends naturally to 4** once the handle array holds 4 (§4.6 "natural game-over extension") |
| Cameras | scripts create only player 1's follow camera (`AddCameras`: `CameraCreateFollow("follow", player)`); the engine creates a joiner's camera (`FUN_0011EAF0` per player index; camera system arrays sized 2, F-0026) | engine work (M2), not scripts. Scripted shots name player/player2 only |
| Warrior commands | `WCEnableAllCommands` → `FUN_0041DB08` loop `< 2`; `IssueWarriorCommand` uses player 1 | P3/P4 get no command state |

### 2.3 Bindings that take a player index (VERIFIED, decompile)
| Binding | Index meaning | Check | Script use |
|---|---|---|---|
| `HuGetPlayer(i)` | 0-based | none (i = 2 reads GameMgr+0x230) | 0 |
| `InvGiveRevive`, `InvSetSpraycanCharges`, `InvGiveSkeletonKey`, `InvSetMoney`, `InvGiveItem` `(value, p)` | 1-based | `FUN_0041E5B0`: returns when p−1 > 1, so P3/P4 are silently ignored. `InvSetMoney` (`FUN_0041EEB8`) also writes `(&0x00600848)[p−1]+0xE20` with **no check** (p = 3 reads 0x00600850) | with 1 and 2 |
| `ForceShowPlayerHud(i, b)` | 0-based | none (`FUN_001B20E0` writes `*(0x00600848+4i)+0x4104`) | 0 ×48, 1 ×83 |
| `HUDTurnOnRadar(i)` / `HUDTurnOffRadar(i)` | 0/1 = that player; **2 (default) = both** | none | no argument 115×, 0 ×46, 1 ×47 |
| `HUDSetNumIndicator(i, …)` | 0/1 per player; 2 = shared indicator | none | 9 |
| `CamTarget(op, …, human)` | op 0 add, 1 remove, 2 clear (shared-camera list, cap 4, F-0029) | not a player index | 214 |
| `CamSetSplitMode(m)`, `CfgButtonHeldFrames(n)` | not player (split mode < 2; held frames clamped 2..7, tick-based, relevant for 60 fps) | | |
| `HuIsAPlayer`, `HuSwitchPlayer`, `HuLockPad`, `HuSetRageMode` | take a human handle | fine; `HuSetRageMode` indexes +0x228 by the human's player index | |

Rule for 4 players:
- The value 2 means "both" in the radar and indicator bindings. Treat it as **all players**. Scripts only pass
  explicit 0/1, so P3/P4 radars follow the "all" calls.
- Index-checked inventory and the HUD pointer array must grow to 4 before any P3/P4 index can reach them.

### 2.4 Delivering script changes (HYPOTHESIS)
Scripts are compiled Lua 4 chunks in WARRIORS.WAD. Options:
- (a) patch the bytecode chunk in memory after load;
- (b) run Lua source through the linked `dostring` (F-0057, not yet proven callable);
- (c) prefer engine-side generalisation where the engine decides (join, game over, cameras).

Smallest script set to change:
- `WarpPlayers`;
- the shared join callback (index-aware inventory);
- per-mission join callbacks;
- both-in-box checks;
- `HuIsAPlayer(player2)` branches for the companions P3/P4 take over.

The per-mission review belongs to M6.

---

## 3. Companions and taking them over

### 3.1 Original player-2 takeover (VERIFIED, decompile)
`MultiplayerJoin` (our label, `FUN_0041A460(GameMgr, pad)`) is called:
- from the main loop (`FUN_00158728`, loop over 8 pad states at 0x005DD810 + 0x50·i) when a pad has no player
  (s16 at pad state +0x42 = −1) and `count < 2`;
- from Lua `CheckMultiplayer()` (WAD 9401) and four other places, with pad −1.

**Join branch:**
1. Requires GameMgr+0x56E8 (join allowed) and GameMgr+0x158 ∈ {0, 3}; **refuses when count == 2**.
2. `PickJoinCompanion` (our label, `FUN_0022A770(gang of player 1, 0)`) looks at player 1's gang members
   (gang+0x48, 16 slots) that are AI (+0x1B0 == −1). It returns the one with the **lowest non-zero +0x1B1 priority**,
   otherwise the first AI member. Outside level 99 in story state 0 it falls back to scanning 60 objects.
3. `MakePlayer(companion, pad, −1, −1)` (`FUN_00229C40`).
4. It sets the pad bit in GameMgr+0x456, adds the companion to the shared-camera list, creates its camera
   (`FUN_0011EAF0`), runs `LayoutViewports`, and calls Lua (human, true).

**Leave branch:** for each player ≥ 1 whose pad bit is set:
1. `FUN_00258A88(h)`;
2. `ReleasePlayer` (`FUN_0022A2A8(h, 1, 1)`);
3. clear the bit;
4. Lua (human, false).

The companion is AI again. **This is exactly D7's "replaced companion returns to AI via the game's own release".**

### 3.2 Proposal for players 3 and 4 (HYPOTHESIS until M2 runtime tests)
- **Same path, higher limits:**
  - join `count != 2` → `count < 4` in `FUN_0041A460`;
  - main-loop `count < 2` → `< 4` in `FUN_00158728`;
  - `GameMgr::AddPlayer` limit (0x00419B48, F-0060);
  - `MakePlayer` HUD slots (F-0056);
  - pad polling for 4 pads (F-0055);
  - the GameMgr handle array (128 `GameMgr+0x228` and 26 `+0x22C` references; +0x230 onward hold other fields, so
    either relocate the array or move those fields).
- **Selection:** the +0x1B1 priority order gives the script's slot-2, then slot-3/4 candidates, then any AI gang
  member. Where scripts marked a 3rd/4th Warrior (levels 3, 81, 9, 54, 82, 92), that follows the designers' intent.
  Missions with too few AI Warriors need the preserve-and-add rule (§4.4; M6 classification).
- **Leaving:** use the existing leave branch (`ReleasePlayer`) per player. The Lua leave callback must become
  index-aware (§2.2).
- **Online determinism:** the join must happen at the same poll on every PC. Either deliver the joining player's
  Start press through the lockstep input (the original trigger, F-0025/F-0066), or call `MultiplayerJoin` from the
  game hook with the pad index at an agreed poll. Both are deterministic if the session's inputs are.

---

## Summary
- **HUD:**
  - Per-player HUD state is sized 2 everywhere: pointer array 0x00600848, PlayerHUD objects at HUD+0x19130 (stride
    0x4A50), radars at HUD+0x15D0 (stride 0x2940), layout tables at 0x0050FA10/0x0050FA40 (stride 0x240), and the
    overhead state arrays at 0x00510530-0x00510540.
  - The camera manager already holds 4 per-view 3D and 4 per-view HUD cameras.
  - There is **no panel size control**: sizes are per-element table constants drawn by the global HUD camera (view
    byte 0xFF).
  - The clean lever is the **view byte**. The sprite flush (`FUN_00185D20`) draws items with view < views through
    that view's HUD camera.
  - **Proposal:** patch 2B; retag player-owned HUD sprites to their owner's view (cave at 0x0018296C plus a
    current-player word set around `FUN_00212840`/`FUN_00214138`); draw shared view-0xFF items once per view in
    layout mode 2 (cave at 0x00185EE8).
  - Result: every quarter becomes a half-size single-player HUD, which also fixes centred text.
  - One-word test of the mechanism: 0x002129EC AFB60010→AFB50010.
- **Scripts:**
  - `player`/`player2` are named Warriors set per mission. `HuCreate`'s slot argument marks P1 (1) and join
    priorities (2-4).
  - These ignore P3/P4: `WarpPlayers`, both-in-box checks, the player-2 join callbacks (inventory to index 2),
    `HuIsAlive(player2)` and `HuIsAPlayer(player2)` branches.
  - Range checks silently drop P3/P4 in the inventory (`FUN_0041E5B0`). `HuGetPlayer`, `ForceShowPlayerHud` and
    `InvSetMoney`'s HUD write have no check at all.
  - In the radar bindings, 2 means "both".
  - Game over already loops over all players.
- **Companions:** `MultiplayerJoin`/`PickJoinCompanion`/`MakePlayer` join the lowest-priority AI gang member, and
  the leave branch calls `ReleasePlayer`, which is D7's mechanism. Raising the 2-player limits and making the Lua
  callbacks index-aware reuses it for players 3-4.
- **Confidence:** high on the code facts; medium on the per-view HUD result; the 3P/4P marker art is untraced.

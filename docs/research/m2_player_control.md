# M2 research: why players 3-4 did not move, and the GameMgr per-player block (static analysis)

Build: The Warriors SLUS-21215 v1.03 (ELF `local/disc/SLUS_212.15`, read-only). Date: 2026-10-11.
Method:
- decompiled C (`local/analysis/all/*.c`) and Lua pseudo-code (`local/analysis/pseudo/`);
- our own disassembly of the ELF;
- the earlier GameMgr access scan (scratchpad `gm_all2.json`), plus an exhaustive scan of every load, store and addiu
  with an offset of 0x414..0x42F.

Runtime facts come from `local/m2/m2m/track.csv` and `state.txt` (SINGLE-PC, scripted input). Function names are OUR
labels (stripped ELF). Nothing was run for this note.

## 1. Root cause of "player 3 does not move" in the m2m test
**The two humans made into players 3 and 4 were the tutorial's sparring enemies, and the tutorial script had switched
their brains off ("brain dead"). A brain-dead player's controller is detached from its pad. The player index is not
the cause.** VERIFIED (code and script); one runtime read is still to do (section 5).

### Who they are (VERIFIED: script and positions)
- Mission 1's script `09607_8df83362.lua` creates `CombatEnemy.GenWarrior` at (-275.2, 121.5, 0.3) and
  `CombatEnemy2.SecondWave02` at (-274.1, 121.2, 0.3), both in gang type 19.
- In `track.csv`, humans 0x641A20 and 0x6420F0 sit at exactly (-275.2, 121.5, 0.25) and (-274.1, 121.2, 0.25),
  unchanged from mission start.
- Player 1 (0x640C80) and player 2 (0x641350) match `Warriors2.Rembrandt` (-284.4, 120.4) and `Warriors2.Ash`
  (-285.5, 125.1).

### What the script does to them (VERIFIED: `09653_7e3478dd.lua`, lines 105-128)
- It calls `AddCombatEnemy()` then `GangBrDead(GangCombatEnemy, true)`, and `AddCombatEnemy2()` then
  `GangBrDead(GangCombatEnemy2, true)`.
- It also sets no-push, demi-god, no money and look-at-player.
- The same setup brain-deads `GangCombatTeacher` and `GangCombatWarriors`.

### What brain-dead does (VERIFIED: decompile and disassembly)
- Lua `GangBrDead` (0x00373A20) calls FUN_0016AA98 for every member of the gang. That calls FUN_00292330(human), which
  calls FUN_0028CED8(brain, 1). This sets **brain+9 = 1** and then runs the brain recompute FUN_0028C1A8.
- Brain = 0x006D53F0 + (s16 human+0x92)*0x2F0 (FUN_0021D408).
- Controller record = 0x00660F50 + (s16 human+0x92)*0x2C (FUN_0021D3E8). +0x19 is the pad index; +0x1B means
  "driven by a pad".
- FUN_0028C1A8 (0x0028C1A8): if brain+9 == 1, it loads the "dead" behaviour tables. **When brain+4 == 0 (player mode),
  it also stores 0 to controller+0x1B** (`sb zero,27(s1)` at 0x0028C23C). Only the alive branch sets +0x1B = 1.

### MakePlayer does not clear it (VERIFIED)
- MakePlayer (0x00229C40) sets controller+0x19 = pad and the pad owner.
- It then calls FUN_0028EF48, FUN_0028DB20 and FUN_0028D910, and `FUN_0028CEB8(brain, 0)` at 0x00229F30, which sets
  brain+4 = 0 (player mode).
- Nothing writes brain+9. So the recompute takes the dead branch and sets controller+0x1B = 0.

### Effect (VERIFIED: code)
- The per-controller update FUN_00146078 (0x00146078) copies the pad's stick into the controller only when all of
  these hold:
  - controller+0x1B != 0;
  - controller+0x19 != -1;
  - the pad is connected (pad state +0x4C).
- When they hold, it stores the angle and magnitude at +0x08/+0x10 and then runs the button mapping FUN_00147940.
  Otherwise it calls FUN_00146000, which zeroes the move values.
- So the stick on pad 1 never reaches player 3, even though the port buffer shows it (sticks 0x7F7F007F).
- This is consistent with Stage 1 E4: the companion that did move on pad 1 was Ash (Warriors2 gang, never
  brain-dead).

## 2. Every check on the pad -> movement path that depends on player index, HUD slot or pad
| # | Check | Index used | Status for players 3-4 (indices 2-3) | Label |
|---|---|---|---|---|
| 1 | Pad polling: `PadUpdateAll` 0x001454A8 -> `FUN_00144FB0(pad, matrix)` -> `PadRead` 0x001498A8 | pad 0..7 | Pads 1 and 2 are polled (E4 words in `[warriors-4p 4p]`). State dump: connected 1, owners 2 and 3 | VERIFIED (code, runtime dump) |
| 2 | Camera-relative stick: `FUN_0011F9E0(owner,0)` (0x005D9158[]), `FUN_0011F9C8(owner)` (0x005D9148[]), `FUN_0011F9B0(i)` (0x005D9150[]); cache 0x005DDC90 + owner*0x10 | player index | Camera arrays relocated to 4 entries (m2_pads_cameras.md); the cache has room for 8. When views != cameras (Mission 1 tutorial: `CamEnable(4,false)`), cache[2..3] is never refreshed and stays 0, giving an identity rotation (FUN_00336500). Players 3-4 then steer in world axes, not camera axes. A direction problem, not a blocker | VERIFIED (code) / HYPOTHESIS (visible effect) |
| 3 | Pad disconnect handler `FUN_0022A980`. PadInit (0x00149520) installs it via FUN_00145780; the libpad wrapper 0x00149770 calls it when `scePadGetState` returns 0 for an owned pad. It clears the owner (+0x42 = -1) and asks for the "reconnect controller" screen (`DAT_005E5580 = 2`) | pad | Not triggered in m2m: owners 2 and 3 were still set at poll 6193. The game never opens pads 1/2, so this depends on what the emulated libpad reports for unopened slots | VERIFIED (runtime dump) / HYPOTHESIS (why) |
| 4 | Controller update `FUN_00146078`: controller+0x1B, +0x19, pad +0x4C | pad | **Blocked when the human is brain-dead** (section 1) | VERIFIED |
| 5 | Brain recompute `FUN_0028C1A8`: dead flag brain+9; the alive branch calls `FUN_0011F9B0(human+0x1B0)` and FUN_00249BF8 | player index | Camera getter relocated (4 entries) | VERIFIED |
| 6 | MakePlayer HUD-slot loop `i < 2` (FUN_001B2200) sets human+0x380 = -1 | HUD slot | Not on the movement path. HUD users are guarded by m2_hud_players34.md (A) | VERIFIED |
| 7 | 0x5C per-player records (`FUN_00222B18`/`FUN_00222AD8`), used by the death/respawn reset FUN_0022E020 and by FUN_00254E78 | player index (after m2_gamemgr_records.md) | Relocated to 4 entries | VERIFIED (patch list) |
| 8 | GameMgr per-player block +0x414..+0x42F (squad commands, section 3) | player index | Not on the movement path, **but out of bounds for indices 2-3: it corrupts player 1/2 data and +0x430/+0x431** (list below) | VERIFIED (address arithmetic) |

### Out of bounds today, not a blocker
VERIFIED from the address arithmetic; the effect is a HYPOTHESIS.
- `FUN_0041C4C8(gm, p, a, b)` writes +0x41A+p and +0x42C+p.
  - p = 2 hits +0x41C[0] and **+0x42E[0] (player 1's "commands disabled" flag)**.
  - p = 3 hits +0x41D and +0x42F.
- `sb +0x42E+p` in FUN_00164C20, FUN_00303988, FUN_00306190 and FUN_0039F450: p = 2/3 hit **+0x430 / +0x431**. +0x431
  is the "command system on" byte read at 0x00303A04.
- `FUN_0041C4E0` (called at the end of MakePlayer) writes +0x41C+p: p = 2/3 hit +0x41E/+0x41F, which are player 1's
  command slots 0 and 1.
- `FUN_0041DBE8` (Lua `EnableCommand`):
  - writes +0x41E + 7p + slot; for p = 2/3 that is +0x42C..+0x439, including the s16 fields +0x432/+0x434;
  - **reads the PlayerHUD pointer 0x00600848[p] out of bounds** before calling FUN_001A6C38.
- `FUN_0041DCF0` writes +0x418+p: p = 2/3 hit +0x41A[0..1].

## 3. Patches
### 3.1 P-1: MakePlayer clears the brain-dead flag (4 words)
A player must always be pad-driven, so MakePlayer now clears brain+9 before it switches the brain to player mode.
- The call `jal 0x0028CEB8` at 0x00229F30 now goes to a 3-word cave.
- The cave stores 0 to brain+9 (a0 = brain, set in the delay slot 0x00229F34) and tail-jumps to 0x0028CEB8 (a1 = 0,
  from 0x00229F2C).
- The recompute then takes the alive branch and sets controller+0x1B = 1.
```
patch=2,EE,00229F30,word,0C03C2D0 // was 0C0A33AE jal 0x0028CEB8 -> jal 0x000F0B40 (MakePlayer: clear brain-dead first)
patch=2,EE,000F0B40,word,A0800009 // brain cave: sb zero,9(a0)  brain+9 (brain-dead flag) = 0; a0 = brain (delay slot 0x00229F34)
patch=2,EE,000F0B44,word,080A33AE // brain cave: j 0x0028CEB8 (set brain mode a1 = 0 = player; recompute)
patch=2,EE,000F0B48,word,00000000 // brain cave: nop
```
- VERIFIED: disassembly of 0x00229F00-0x00229F40 and 0x0028C1A8; original word checked.
- HYPOTHESIS: no original flow relies on a human staying brain-dead after it becomes a player. Players 1 and 2 are made
  from humans that scripts never brain-dead first.
- A later `GangBrDead(gang, true)` on a gang that contains player 3 or 4 would freeze them again, exactly as it would
  freeze player 1 or 2. Scripts do this to companion gangs during tutorials and scenes, e.g. `GangCombatWarriors` in
  Mission 1. If it turns out to freeze players 3-4 while players 1-2 keep moving, guard FUN_00292330 for humans with
  +0x1B0 >= 2 (not proposed yet).
- On release (D7: player 3/4 leaves, ReleasePlayer 0x0022A2A8) the human stays alive, so a human the script had made
  brain-dead would come back to life as AI. Acceptable for companions; noted.

### 3.2 P-2: GameMgr per-player block +0x414..+0x42F -> +0x58C0..+0x58F7 (4 entries each)
GameMgr is 0x5A80 bytes (records note). The tail +0x58C0..+0x58FF is free, because the records start at +0x5900, and
the block needs only 0x38 bytes. So **the allocation word at 0x00161130 does not change**.

| Old | Meaning (from the squad-command code FUN_0041C4E0) | New (4 entries) |
|---|---|---|
| +0x414 u8[2] | per-player command flag (FUN_0041C338, FUN_004197A8) | +0x58C0 |
| +0x416 u8[2] | per-squad-leader flag, indexed by the leader's +0x1B0 (FUN_00310618 and others) | +0x58C4 |
| +0x418 u8[2] | set by Lua via FUN_0041DCF0 | +0x58C8 |
| +0x41A u8[2] | current squad command per player (FUN_0041C4C8) | +0x58CC |
| +0x41C u8[2] | requested command per player (FUN_0041C4E0; FUN_0041CC10 sets 7) | +0x58D0 |
| +0x41E u8[2][7] | command available, per player and slot (`p*7 + slot`) | +0x58D4 (+0x58D6 = slot 2) |
| +0x42C u8[2] | second value of FUN_0041C4C8 | +0x58F0 |
| +0x42E u8[2] | commands disabled, per player | +0x58F4 |

**Which sites are patched.** Every instruction found by the exhaustive offset scan whose base is GameMgr plus a player
index, each checked in the disassembly. GameMgr counts as the base when the pointer comes from `lw 0x489C` of
0x0051xxxx, or is the GameMgr argument of a GameMgr method.

**What the list contains:**
- 61 immediate changes;
- 3 memset sizes;
- 1 loop count;
- the reset cave (2 + 13 words);
- the EnableCommand guard (7 words).

**Not GameMgr (checked and excluded):**
- the word accesses with these offsets in other classes (0x00124778, 0x00126C40, 0x004C7068, ...);
- the human field +0x418 (0x002AC000/0x002AC458; the base is an object pointer);
- the stack buffer at 0x001B93A8.

**Kept at 2 entries on purpose:**
- **The constructor loop** (0x004187EC, `i < 2`; it also initialises the handles and +0x56DE). The reset cave sets
  entries 2-3, and the reset runs at every level start, before players 3-4 can exist.
- **The reset loop** (0x00418F58, `i < 2`). Its body also resets the PlayerHUD with `FUN_001B3E20(HUD, i)`, and only 2
  PlayerHUDs exist. The cave after the loop initialises entries 2-3 with the same values: 0x41A/0x42C/0x42E = 0, the
  7 slots = 1.
- **FUN_0041DB08** (`i < 2`). It also calls each player's PlayerHUD (0x00600848[i]).
- **The 0x5C record reset for players 2-3** in the reset loop. The records note says it is harmless for now.

```
patch=2,EE,00165008,word,A04058F4 // was A040042E; GM+0x42E -> GM+0x58F4; FUN_00164c20
patch=2,EE,00165018,word,906258CC // was 9062041A; GM+0x41A -> GM+0x58CC; FUN_00164c20
patch=2,EE,0016503C,word,244258D6 // was 24420420; GM+0x420 -> GM+0x58D6; FUN_00164c20
patch=2,EE,00165090,word,A04058F4 // was A040042E; GM+0x42E -> GM+0x58F4; FUN_00164c20
patch=2,EE,001650A0,word,906258CC // was 9062041A; GM+0x41A -> GM+0x58CC; FUN_00164c20
patch=2,EE,001650C4,word,244258D6 // was 24420420; GM+0x420 -> GM+0x58D6; FUN_00164c20
patch=2,EE,0016510C,word,A05058D6 // was A0500420; GM+0x420 -> GM+0x58D6; FUN_00164c20
patch=2,EE,001A6CB0,word,908258D4 // was 9082041E; GM+0x41E -> GM+0x58D4; FUN_001a6c58
patch=2,EE,001A6CF0,word,A06258D0 // was A062041C; GM+0x41C -> GM+0x58D0; FUN_001a6c58
patch=2,EE,001A7FE8,word,904458F4 // was 9044042E; GM+0x42E -> GM+0x58F4; FUN_001a7e48
patch=2,EE,001A8028,word,904458C0 // was 90440414; GM+0x414 -> GM+0x58C0; FUN_001a7e48
patch=2,EE,001A80C0,word,908258D4 // was 9082041E; GM+0x41E -> GM+0x58D4; FUN_001a7e48
patch=2,EE,001A8640,word,908258D4 // was 9082041E; GM+0x41E -> GM+0x58D4; FUN_001a8590
patch=2,EE,001A8694,word,908258D4 // was 9082041E; GM+0x41E -> GM+0x58D4; FUN_001a8590
patch=2,EE,001A8760,word,908258D4 // was 9082041E; GM+0x41E -> GM+0x58D4; FUN_001a8590
patch=2,EE,001A8A38,word,904558D0 // was 9045041C; GM+0x41C -> GM+0x58D0; FUN_001a8988
patch=2,EE,00239A40,word,904658CC // was 9046041A; GM+0x41A -> GM+0x58CC; FUN_002398b0
patch=2,EE,0023E894,word,905058CC // was 9050041A; GM+0x41A -> GM+0x58CC; FUN_0023e7e0
patch=2,EE,0023EA24,word,904358CC // was 9043041A; GM+0x41A -> GM+0x58CC; FUN_0023e7e0
patch=2,EE,00273AC0,word,904358CC // was 9043041A; GM+0x41A -> GM+0x58CC; FUN_00273a68
patch=2,EE,00284530,word,906258F4 // was 9062042E; GM+0x42E -> GM+0x58F4; FUN_002843f8
patch=2,EE,0028459C,word,906258F4 // was 9062042E; GM+0x42E -> GM+0x58F4; FUN_002843f8
patch=2,EE,002B622C,word,906458CC // was 9064041A; GM+0x41A -> GM+0x58CC; FUN_002b60c0
patch=2,EE,002F4558,word,904358CC // was 9043041A; GM+0x41A -> GM+0x58CC; FUN_002f42c0
patch=2,EE,002F5248,word,904358CC // was 9043041A; GM+0x41A -> GM+0x58CC; FUN_002f4e10
patch=2,EE,002FA16C,word,907058CC // was 9070041A; GM+0x41A -> GM+0x58CC; FUN_002fa0e0
patch=2,EE,003039FC,word,A04058F4 // was A040042E; GM+0x42E -> GM+0x58F4; FUN_00303988
patch=2,EE,00303A20,word,905058CC // was 9050041A; GM+0x41A -> GM+0x58CC; FUN_00303988
patch=2,EE,00303CD8,word,906258F0 // was 9062042C; GM+0x42C -> GM+0x58F0; FUN_00303988
patch=2,EE,003061CC,word,904358C8 // was 90430418; GM+0x418 -> GM+0x58C8; FUN_00306190
patch=2,EE,0030629C,word,906458CC // was 9064041A; GM+0x41A -> GM+0x58CC; FUN_00306190
patch=2,EE,003062D8,word,A05158F4 // was A051042E; GM+0x42E -> GM+0x58F4; FUN_00306190
patch=2,EE,0030D30C,word,904458CC // was 9044041A; GM+0x41A -> GM+0x58CC; FUN_0030d208
patch=2,EE,00310668,word,906258C4 // was 90620416; GM+0x416 -> GM+0x58C4; FUN_00310618
patch=2,EE,003111F8,word,906258C4 // was 90620416; GM+0x416 -> GM+0x58C4; FUN_003111a8
patch=2,EE,003139A4,word,906258C4 // was 90620416; GM+0x416 -> GM+0x58C4; FUN_00313958
patch=2,EE,00319F14,word,906258C4 // was 90620416; GM+0x416 -> GM+0x58C4; FUN_00319ec8
patch=2,EE,0032093C,word,906258C4 // was 90620416; GM+0x416 -> GM+0x58C4; FUN_003208e8
patch=2,EE,003211F4,word,906258C4 // was 90620416; GM+0x416 -> GM+0x58C4; FUN_003211a8
patch=2,EE,0039FF58,word,A04058F4 // was A040042E; GM+0x42E -> GM+0x58F4; FUN_0039f450
patch=2,EE,004185BC,word,262358CC // was 2623041A; GM+0x41A -> GM+0x58CC; ctor FUN_00418588 (loop stays 2; [2..3] by reset cave)
patch=2,EE,00418CE8,word,264258C4 // was 26420416; GM+0x416 -> GM+0x58C4; reset FUN_00418c68
patch=2,EE,00418D00,word,264258C8 // was 26420418; GM+0x418 -> GM+0x58C8; reset
patch=2,EE,00418D10,word,265E58C0 // was 265E0414; GM+0x414 -> GM+0x58C0; reset
patch=2,EE,00418D14,word,265658F4 // was 2656042E; GM+0x42E -> GM+0x58F4; reset
patch=2,EE,00418D20,word,265558D4 // was 2655041E; GM+0x41E -> GM+0x58D4; reset
patch=2,EE,0041996C,word,904358C0 // was 90430414; GM+0x414 -> GM+0x58C0; FUN_004197a8
patch=2,EE,0041C3EC,word,263658C0 // was 26360414; GM+0x414 -> GM+0x58C0; FUN_0041c338
patch=2,EE,0041C494,word,A06058C0 // was A0600414; GM+0x414 -> GM+0x58C0; FUN_0041c338
patch=2,EE,0041C4D0,word,A04658CC // was A046041A; GM+0x41A -> GM+0x58CC; FUN_0041c4c8
patch=2,EE,0041C4D8,word,A08758F0 // was A087042C; GM+0x42C -> GM+0x58F0; FUN_0041c4c8
patch=2,EE,0041C580,word,906258F4 // was 9062042E; GM+0x42E -> GM+0x58F4; FUN_0041c4e0
patch=2,EE,0041C59C,word,904358D4 // was 9043041E; GM+0x41E -> GM+0x58D4; FUN_0041c4e0
patch=2,EE,0041C5C4,word,A05E58D0 // was A05E041C; GM+0x41C -> GM+0x58D0; FUN_0041c4e0
patch=2,EE,0041C620,word,904358CC // was 9043041A; GM+0x41A -> GM+0x58CC; FUN_0041c4e0
patch=2,EE,0041CC10,word,248458D3 // was 2484041D; GM+0x41D -> GM+0x58D3; FUN_0041cc10 (start at entry 3)
patch=2,EE,0041CC7C,word,904458CC // was 9044041A; GM+0x41A -> GM+0x58CC; FUN_0041cc40
patch=2,EE,0041CE60,word,A05058C4 // was A0500416; GM+0x416 -> GM+0x58C4; FUN_0041cc40
patch=2,EE,0041DB98,word,A05258D4 // was A052041E; GM+0x41E -> GM+0x58D4; FUN_0041db08 (loop stays 2: HUD table)
patch=2,EE,0041DC40,word,A09058D4 // was A090041E; GM+0x41E -> GM+0x58D4; FUN_0041dbe8
patch=2,EE,0041DD2C,word,A07058C8 // was A0700418; GM+0x418 -> GM+0x58C8; FUN_0041dcf0
patch=2,EE,00418EC0,word,24060004 // was 24060002; reset: memset GM+0x58C0 (old +0x414) size 2 -> 4
patch=2,EE,00418ED0,word,24060004 // was 24060002; reset: memset GM+0x58C4 (old +0x416) size 2 -> 4
patch=2,EE,00418EE0,word,24060004 // was 24060002; reset: memset GM+0x58C8 (old +0x418) size 2 -> 4
patch=2,EE,0041CC18,word,24020003 // was 24020001; FUN_0041cc10: 4 entries (counts 3..0)
patch=2,EE,00418F64,word,0C03C2D4 // was 2403FFFF; reset: after the i<2 loop, jal 0x000F0B50 (init entries 2..3)
patch=2,EE,00418F68,word,00000000 // was 3C020051; reset: nop (the cave re-executes addiu v1,-1 / lui v0,0x51)
patch=2,EE,0041DC44,word,2CA20002 // was 80C201B0; EnableCommand FUN_0041dbe8: sltiu v0,a1,2 (a1 = player index)
patch=2,EE,0041DC48,word,10400007 // was 3C030060; beq v0,zero,0x0041DC68: no PlayerHUD call for players 3-4
patch=2,EE,0041DC4C,word,00051080 // was 24630840; sll v0,a1,2
patch=2,EE,0041DC50,word,3C030060 // was 0200282D; lui v1,0x0060
patch=2,EE,0041DC54,word,00621821 // was 00021080; addu v1,v1,v0
patch=2,EE,0041DC58,word,8C640848 // was 00621821; lw a0,0x848(v1)  (PlayerHUD 0x00600848[p], as before)
patch=2,EE,0041DC5C,word,0200282D // was 8C640008; daddu a1,s0,zero
patch=2,EE,000F0B50,word,A64058CE // reset cave: sh zero,0x58CE(s2)   old +0x41A[2..3] = 0
patch=2,EE,000F0B54,word,A64058F2 // reset cave: sh zero,0x58F2(s2)   old +0x42C[2..3] = 0
patch=2,EE,000F0B58,word,A64058F6 // reset cave: sh zero,0x58F6(s2)   old +0x42E[2..3] = 0
patch=2,EE,000F0B5C,word,24080001 // reset cave: addiu t0,zero,1
patch=2,EE,000F0B60,word,264358E2 // reset cave: addiu v1,s2,0x58E2   old +0x41E[2][0]
patch=2,EE,000F0B64,word,264258F0 // reset cave: addiu v0,s2,0x58F0   end of old +0x41E[3][6]
patch=2,EE,000F0B68,word,A0680000 // reset cave: sb t0,0(v1)          slots of players 3-4 = 1 (as the reset loop)
patch=2,EE,000F0B6C,word,24630001 // reset cave: addiu v1,v1,1
patch=2,EE,000F0B70,word,1462FFFD // reset cave: bne v1,v0,0x000F0B68
patch=2,EE,000F0B74,word,00000000 // reset cave: nop
patch=2,EE,000F0B78,word,2403FFFF // reset cave: addiu v1,zero,-1     (moved from 0x00418F64)
patch=2,EE,000F0B7C,word,03E00008 // reset cave: jr ra                (ra = 0x00418F6C)
patch=2,EE,000F0B80,word,3C020051 // reset cave: lui v0,0x0051        (moved from 0x00418F68)
```
**Checks run on these lines:**
- Every "was" word is VERIFIED against the ELF.
- `python -I tools/note_patches.py check mod/w4p_m1.pnach <these lines>`: 788 addresses, 0 problems. No address is
  patched twice, and the caves at 0x000F0B40-0x000F0B83 are zero in the ELF and unused by the current pnach.
- A branch-target scan finds no branch landing inside the patched windows 0x00418F64-0x00418F68 and
  0x0041DC44-0x0041DC5C.

**Residual risk (HYPOTHESIS):** the scan would miss an access to the block through a different base with an immediate
in 0x414..0x42F, for example `addiu rX, gm, 0x400` followed by `0x14(rX)`. Such an access would read the old bytes,
which are no longer updated: a stale value, but no memory corruption.

## 4. What else players 3-4 need to be driven correctly (not patched here)
- **Choose the right humans.** In the m2m test the creation calls picked brain-dead enemies. Join candidates must come
  from player 1's squad, as in the game's own drop-in (FUN_0022A770). In Mission 1 that squad holds only Rembrandt and
  Ash (F-0109), so players 3-4 there need added Warriors (D7 "added character") or a later mission.
- **Camera-relative stick** (row 2 of the table). When the views are not split, players 3-4 steer in world axes. Fix
  candidate: in PadUpdateAll, use the cache of the camera actually rendered for that player, or refresh cache[owner]
  from camera 0 for owners >= 2. Confirm at runtime first.

## 5. Runtime checks (SINGLE-PC, scripted input)
1. **Brain-dead flag.**
   - Before MakePlayer in Mission 1, read brain+9 of 0x641A20 and 0x6420F0 (brain = 0x006D53F0 +
     (s16 human+0x92)*0x2F0). Expect 1.
   - After MakePlayer without P-1, controller+0x1B (0x00660F50 + (s16 human+0x92)*0x2C + 0x1B) should be 0.
   - With P-1 it should be 1, and the human should move with pad 1/2 input.
2. **No stray writes.** With P-2 and DebugWatch on GameMgr+0x41C..+0x41F and +0x42E..+0x431, expect no writes after
   players 3-4 exist. Writes should appear at +0x58CE/+0x58CF/+0x58F6/+0x58F7 instead.
3. **Squad commands.** Players 1-2's squad commands (the L1 command wheel) still work after players 3-4 join; the
   slots at +0x58D4.. are unchanged.
4. **EnableCommand.** Lua `EnableCommand` on player 3 makes no PlayerHUD call and does not crash.

## Summary
- **Why players 3-4 did not move in the m2m test:**
  - The test turned Mission 1's tutorial sparring enemies (GenWarrior, SecondWave02) into players.
  - The tutorial script had made their gangs brain-dead (`GangBrDead(..., true)` sets brain+9), and MakePlayer does
    not clear that flag.
  - So the brain recompute (FUN_0028C1A8) leaves controller+0x1B = 0, and the controller update (FUN_00146078)
    ignores the pad.
  - Once the camera and record arrays are relocated, nothing on the pad -> movement path is limited by the player
    index. VERIFIED (code, script and matching positions); one runtime read is pending.
- **Fix P-1 (4 words):** MakePlayer clears brain+9 before entering player mode.
- **Separate problem:** the GameMgr per-player block +0x414..+0x42F (squad commands) is written out of bounds for
  indices 2-3, overwriting player 1's command data and +0x430/+0x431.
- **Fix P-2 (87 words):**
  - moves the block to +0x58C0..+0x58F7 with 4 entries;
  - widens the reset memsets and FUN_0041CC10;
  - initialises entries 2-3 after the reset loop;
  - stops Lua `EnableCommand` from reading a PlayerHUD pointer that does not exist.

  GameMgr size is unchanged (0x5A80).
- **Checks:** both lists are checked against the ELF and the current pnach (0 problems).
- **Remaining:**
  - choose join candidates from player 1's squad (Mission 1 has none to spare);
  - players 3-4 steer in world axes when the views are merged.

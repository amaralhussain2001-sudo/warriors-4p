# M2 inventory tests T2, T4, T5, T7 for players 3-4: mechanisms and runnable plan

Build: The Warriors SLUS-21215 v1.03 (`local/disc/SLUS_212.15`, opened read-only), patch `mod/w4p_m1.pnach` as of
2026-10-11. Date: 2026-10-11. Method: **static analysis only, nothing was run** (no emulator, no test runner). Sources:
decompile `local/analysis/all/all_*.c`, `callers.pkl`, `lua_bindings.tsv`, pseudo-Lua `local/analysis/pseudo/`, our own
disassembly of ELF words, and earlier run outputs in `local/m2/*/` (read only). Function and structure names are OUR
labels (the ELF is stripped). Addresses are static unless marked. Test list: `m2_inventory34.md` section 9.
Probe module: `tests/m2/inv_tests.py`. Scripts: `tests/m2/nav/invt_*.txt`.

## Result in one paragraph
All four tests can run in the standard one-instance Mission 13 setup. **T2** uses the game's real pick-up path: the
Flash is put "in the pocket" of player 3 (what the Mission 13 script does to Moonrunners), the game's own knock-out drop
function turns it into a `dyn_revival` pick-up at the player's feet, and the game's touch code gives it to the player
who walks over it. **T4** uses the real button: a downed partner is revived with **D-pad Left** (one press, partner
within 3.0 units, the reviver or the downed player holding a Flash). **T5** calls the game's own checkpoint save (the
`SetCheckPoint` core) and then the exact call of the game's "retry from checkpoint" branch (`MenuLoadLevel(GameMgr+0x124)`),
which reloads the level and restores the copy at 0x000E4000; a direct restore call (T5a) runs first as a quick check.
**T7** checks Block B (it **is** in the `[warriors-4p 4p inventory]` group) by calling the core of
`HUDLaunchMissionComplete(4)`, the call the game's level-skip script makes, which runs the mission-end banking. Setup
values (item counts, money) are PINE writes. Each test has a direct-call fallback that is used only if the real path
did not deliver, and the result says which path did. The "AI gang revive" variant of T4 is BLOCKED in Mission 13 with
four players (no AI Warrior left in the squad).

| Test | Real gameplay path | Direct parts (test only) | Tag / scripts | Pass |
|---|---|---|---|---|
| T2 pick-up | touch pick-up of a `dyn_revival` object (FUN_00395510 / FUN_00219D50 -> FUN_0023BF00) | pocket item + drop call, PINE-free; fallback FUN_0023BF00, then FUN_0041EDB8 | `invt2`, `invt_t2_s2/s3.txt` | slot 2 (then 3) Flash +1, other slots unchanged, `via` = game pick-up |
| T4 revive | D-pad Left press of player 4 -> FUN_00286BA8 -> FUN_002752A0 -> FUN_00274EE0 | Flash counts (PINE), HuKill, teleport if > 2.5 units; fallback FUN_00286BA8 call | `invt4`, `invt_t4_s2/s3.txt` | player 3 up (not down, health > 1), player 4 Flash 1 -> 0 |
| T5 checkpoint | checkpoint save (FUN_0041ABC0 = Lua SetCheckPoint core) + retry branch MenuLoadLevel(GM+0x124) -> level start restore | item counts (PINE); T5a direct InvRestoreCheckpoint | `invt5`, `cal_p3/cal_p4.txt` | copy = live at the checkpoint; after T5a and after the reload slots 2-3 = checkpoint values |
| T7 bank | mission-complete state update FUN_0015D160 banking (incl. Block B) | money (PINE); entry FUN_0015D420(4) instead of the summary screen | `invt7`, `cal_p3/cal_p4.txt` | bank delta = 10+20+30+40 = 100 (30 without Block B) |

## 0. Common setup

**Base command** (docs/STATE.md "One instance, Mission 13, players 3-4 joining"; pick a free `--inst`, the examples use
10):
```
G="warriors-4p own view;warriors-4p hud;warriors-4p 4p;warriors-4p 4p hud B1;warriors-4p 4p hud B2;warriors-4p 4p spawn;warriors-4p 4p spawn leave;warriors-4p 4p inventory;warriors-4p 4p fx;warriors-4p test call"
python -I tests/m2/nav_probe.py <tag> tests/m2/nav/boot_to_m1_2p.txt --inst 10 --players 4 \
  --script2 tests/m2/nav/p2_join.txt --script3 <slot-2 script> --script4 <slot-3 script> --groups "$G" \
  --ini EmuCore/Speedhacks/vuThread=false --callat "4000:0041ABC0:1,4010:00160D78:0x01FD9F9C" --seconds <s> \
  --probe inv_tests:<function>:<poll> ...
```
Results: `local/m2/<tag>/probes.json`, keys `inv_tests.<function>@<poll>`; screenshots `local/m2/<tag>/t*_p<poll>.png`.

**Who is who** (VERIFIED, pad owner u16 at 0x005DD810 + pad*0x50 + 0x42 in `local/m2/{inv2,inv3,go1,go3,fight8}/state.txt`,
all `[(1, 1, 3), (2, 1, 2)]`): game **player 3** (index 2, Fox, HUD slot 2) owns **pad 2 = W4P slot 3 = `--script4`**;
game **player 4** (index 3, spawned Warrior, HUD slot 3) owns **pad 1 = W4P slot 2 = `--script3`**. So the first join
(about poll 8356, player 3) is most likely the `--script4` Start at 8350 (inference from the pad owners). The new scripts are named by W4P slot (`_s2` = `--script3`,
`_s3` = `--script4`); every probe also records the pad owners (`pads`) so a run with a swapped mapping is visible.

**Probe mechanics** (VERIFIED, `tests/m2/nav_probe.py` lines 144-166): a probe runs once when the counter 0x000F0500
reaches its poll; the loop sleeps 0.25 s and takes a screenshot every 4 s, so a probe can start up to about 1 s
(about 30 polls) late. Script inputs are exact. All schedules below keep at least 60-70 polls between a probe and the
input that depends on it. A probe that raises (PINE error) is retried on the next loop; `inv_tests.py` records every
game call it made (`_DONE`) so a retry never repeats a drop, kill, checkpoint or level load.

**Mailbox** (VERIFIED, `[warriors-4p test call]` at 0x000F0000-0x000F0054, hooked into FrameStats at 0x00158CD0 and six
other state updates): same writes as `gameover_probe.py` (a0..a3 0x000F0304..0x000F0310, done 0x000F0318 = 0, function
0x000F0300 last), wait up to 4 s for done = 1, v0 at 0x000F0314. Only addition: if done never comes, 0x000F0300 is
cleared so the request cannot run later. Only four arguments exist; t0 is 0x000F0000 inside the stub, so no 5+-argument
function is called.

**Patch check in every probe** (`code`): reads the active code words 0x0041E3D8 (A1), 0x0041E0B8 (A3), 0x0041E16C (A4),
0x0015D3F4 (Block B) and 0x00158CD0 (test call).

**Reusable read:** `inv_tests:state:<poll>` (groups active, GameMgr fields, pads, players with health/flags/position/
HUD slot/pocket, `inv_probe.inventory`, `dyn_revival` objects).

## 1. T2 pick-up

### 1.1 How a world pick-up reaches the inventory (VERIFIED code unless marked)
| Step | Code | Evidence |
|---|---|---|
| Pick-ups are objects of class `powerup_item`: `CfgObj("dyn_revival", "powerup_item", ..., OBJECT.TYPE_REVIVAL)`, `dyn_money` (TYPE_MONEY), `dyn_key` (TYPE_KEY); TYPE_REVIVAL = 14, TYPE_KEY = 13, TYPE_SPRAYCAN = 16, TYPE_MONEY = 28 | Lua config | `pseudo/03773_e15a707a.lua:953, 771, 707`; `pseudo/03717_c33644d9.lua:33-48` |
| Type definition = `*0x00512C04 + id*0x90`: name +0x28, class +0x43, own id +0x60, kind +0x86; the object's id is the u16 at object+0x112 | FUN_00390F18, FUN_00391778, FUN_003917A0, FUN_00391340, FUN_00391330 | all_06.c:13503-13880 |
| Object side: on its first settled update a `powerup_item` (class string 0x00580EC8) runs FUN_00395510 once: every human overlapping it -> line check FUN_0021C570 -> FUN_0023BF00(human, object); on success FUN_003924D8(object) removes its collision | FUN_00395B70 -> FUN_00395510 | all_06.c:16802-16870, 16487-16545 |
| Human side: a human touching an object (callback FUN_00219D50, class compare with 0x0055A908 "powerup_item") -> FUN_0021C570 -> FUN_0023BF00 -> FUN_003924D8 | FUN_00219D50 | all_02.c:42030-42055 |
| Area scan FUN_00219320(human, 0) does the same for every pick-up near a human; call sites FUN_0021B290 (all_02.c:43198), FUN_00101DD8, FUN_00394050, FUN_003A65A8 (when these run was not traced) | FUN_00219320 | all_02.c:41346-41460 |
| FUN_0023BF00 (our label TypedPickup): picker must be a player (+0x1B0 != -1), brain+4 in {0,2,3,4}, object flag 0x8000 (vtable +0x54); kind 0x0E -> InvAdd(HUD slot, 1, +1) if below the limit; 0x0D key (item 6), 0x10 spray (item 3), 0x1C money (amount object+0x124), 0x0C store items by CRC | FUN_0023BF00 | all_03.c:4605-5020 |
| Full-health rule: if GameMgr+0x56E5 == 0, a player at full health skips Flash pick-ups. Level start sets +0x56E5 = 1 (FUN_00418C68); only Lua `CfgPowerupPickup(false)` (binding 0x0036C208 -> FUN_0041DA70) clears it, in WADs 08488, 08514, 08546, 08570, 08595, **not** in Mission 13 (09229) | three checks | all_02.c:41449, 42041; all_06.c:16545; all_07.c:9736, 13284 |
| A spray can object (`dyn_s_spraycan`, class `simple_object`) is **not** a touch pick-up: it goes through the pick-up animation event (FUN_00245920 default case -> FUN_0023BF00) | FUN_00245920 | all_03.c:11577-11583 |

**Pick-ups in Mission 13 (level9, `pseudo/09229_c05eacb5.lua`)** (VERIFIED script text): the only scripted item object
is `Objects["Spray1"] = ObjSpawn("dyn_s_spraycan", {-80.793, 248.483, 1.014}, ...)` (line 1832), a button pick-up. Flashes
and spray come from Moonrunners: their spawn callbacks call `HuPutItemInPocket(A0, 3)` or, with 50 % chance,
`HuPutItemInPocket(A0, 1)` (lines 2943-3000; the level text says "Some Moonrunners carry spray cans or flash").
**When a human goes down**, FUN_002674C0 (all_03.c:31766-31812) calls **FUN_00232C60(human, 1, 1)** (our label DropLoot):
with a pocket item (+0x250 != 0) it spawns +0x254 objects named `FUN_0041E3C0(Inv, item)` (slot-0 item name, e.g.
"dyn_revival") at the human's position + 0.5 up (VERIFIED disassembly: 0x00232CC8 `lw a1,0x250(s4)`, 0x00232D0C
`jal 0x0041E3C0`, 0x00232D24 `lb v0,0x254(s4)`), with no expiry (FUN_00395D20(obj, 0)). This drop-and-walk-over is the
normal way players get Flashes in this mission. A random 50 % roll and a beaten enemy are not deterministic, so the test
uses the same two game functions on purpose.

**Correction (supersedes a HYPOTHESIS in `m2_inventory34.md` section 4):** FUN_002334D0 is **not** a world pick-up. Its
only caller is FUN_002856B8 (the mugging/robbing minigame, all_03.c:49454-49880): it hands the victim's held/pocket
item (victim+0x250, name at +0x257) to the robber. VERIFIED (`callers.pkl`, decompile).

### 1.2 Design (real path for the pick-up; the drop is a direct call of the game's drop function)
`t2_setup_p3` (player 3; `t2_setup_p4` is the same for player 4):
1. snapshot of all slot counts and existing `dyn_revival` objects; if GameMgr+0x56E5 is 0, lower the player's health
   by 100 (not expected in Mission 13);
2. mailbox **FUN_00238190(player handle, 1, 1)** (HuPutItemInPocket core, binding 0x0035C4D0): pocket = Flash x1;
3. mailbox **FUN_00232C60(player human pointer, 1, 1)**: the game's own drop spawns one `dyn_revival` at the player's feet;
4. mailbox **FUN_00238190(player handle, 0, 0)**: pocket empty again (so a later knock-down drops nothing);
5. records the new object(s): handle, position (object+0x10, HYPOTHESIS), flags +0x54 (0x8000 = may be picked up,
   HYPOTHESIS), +0x117, collision +0x118, distance to the player.
Then the player's script walks out and back over the spot (`LUP:15`, `LDOWN:15`, `LUP:8`, `LDOWN:8`), so the human-side
touch path also gets a chance if the object-side check on the first update did not hand it over.

`t2_fallback_p3` acts **only if the Flash count did not rise**: (b) **FUN_0023BF00(player human pointer, nearest new
dyn_revival object pointer)** (v0 = 1 when given) then FUN_003924D8(object); (c) if still nothing,
**FUN_0041EDB8(1, 3)** (InvGiveRevive core = InvAdd(slot 2, 1, +1, notify)). `t2_read` reports which path gave it
(`via`).

### 1.3 Command (tag `invt2`, about 420 s)
```
python -I tests/m2/nav_probe.py invt2 tests/m2/nav/boot_to_m1_2p.txt --inst 10 --players 4 --script2 tests/m2/nav/p2_join.txt --script3 tests/m2/nav/invt_t2_s2.txt --script4 tests/m2/nav/invt_t2_s3.txt --groups "$G" --ini EmuCore/Speedhacks/vuThread=false --callat "4000:0041ABC0:1,4010:00160D78:0x01FD9F9C" --seconds 420 --probe inv_tests:state:8900 --probe inv_tests:t2_setup_p3:9000 --probe inv_tests:t2_read:9150 --probe inv_tests:t2_read:9400 --probe inv_tests:t2_fallback_p3:9450 --probe inv_tests:t2_setup_p4:9600 --probe inv_tests:t2_read:9750 --probe inv_tests:t2_read:10000 --probe inv_tests:t2_fallback_p4:10050 --probe inv_tests:t2_read:10200
```
Schedule: drop for player 3 at 9000, player 3 walks 9200-9298 (`invt_t2_s3.txt`); drop for player 4 at 9600, player 4
walks 9800-9898 (`invt_t2_s2.txt`). Join Starts in both scripts are identical to `cal_p3.txt`/`cal_p4.txt` up to
8800/8950, so the joins happen as in earlier runs.

### 1.4 What to read, pass
- `t2_setup_p3@9000`: `pocket_after_put` = [1, 1], `pocket_after_clear` = [0, 0], `drop.done` = 1,
  `flash_objects_new` has one object (kind 14, class `powerup_item`) within about 1 unit; `human_before.brain4` and
  `brain26c` are not 5 (else FUN_00232C60 continues into its money code).
- `t2_read@9400`: `result.player3.pass` = true: slot 2 Flash +1, slots 0, 1, 3 unchanged, `via` = "game pick-up (no
  fallback call made)". **This is the real-path pass.** `t2_read@9150` shows whether the object side already handed it
  over before the walk.
- `t2_read@10000`: same for player 4 (slot 3). `t2_read@10200` final.
- If a fallback was needed, T2 is a FAILED TEST for the real path (report `flash_objects` flags/positions), and the
  direct result only shows the inventory side.

## 2. T4 partner revive

### 2.1 Which input, how close, how long (VERIFIED code; runtime cross-check marked)
- **Button: D-pad Left, one press.** The game maps pad buttons to action codes with `AddCommand(action, type, mask,
  param)` (binding 0x00369518 -> FUN_00147430). WAD 4106 `main_3` (unconditional, after the difficulty config):
  `AddCommand(39, 2, 32768, 0)` (`pseudo/04106_7e23a6f2.lua:864`). Type 2 = table 0x005DDDD0, tested by FUN_00144BF0 =
  pressed in this pad sample and not in the previous one (a press edge; holding longer adds nothing). FUN_00147940
  writes the action into input+0x20.
- Mask 32768 = 0x8000 = **D-pad Left**: the game's button word is `~(byte2 << 8 | byte3)` of the libpad buffer
  0x005DE388 (FUN_00149DA0, all_00.c:52398), the same bit order as the W4P bot records (`LEFT` = 0x8000 in
  `tests/m1/m1_run.py`). Cross-check: `AddCommand(40, 2, 8192, 0)` (0x2000 = D-pad Right) is action 0x28, one of the
  actions that call Flash-use FUN_002843F8 in FUN_00254E78 (all_03.c:21893-21896), and D-pad Right used a Flash in
  F-0141 (VERIFIED runtime). F-0141 also saw "D-pad Left did nothing": nobody was down.
- Action 39 = 0x27: the player input handler FUN_0027C120 (all_03.c:43990) runs `FUN_0027BBF8` (action == 0x27) and
  then **FUN_00286BA8(player)**; FUN_0027E040 (all_03.c:44904) also reaches it.
- **FUN_00286BA8 (our label TryPartnerRevive)**, all_03.c:50219: reviver stats+8 == 0 and stats flags & 0x7BF9E9F7FF0 == 0
  (idle); target = FUN_00279078 -> **FUN_0029CC78(3.0, reviver, predicate FUN_00278FA0)** = nearest human within
  **3.0 units** (HYPOTHESIS: the float 0x40400000 is the radius) that is in the same gang (brain+0x20C), has the down flag
  0x40000, not 0x20000, not 0x80000000, not dead (bit 32), and human+0xE0 bit 2 set; the target's stats+8 must be 0;
  FUN_0021C0A8 line check (if it fails: target must be a player and reviver brain+4 == 3); then **InvCount(reviver
  slot, 1) or InvCount(target slot, 1) != 0** -> FUN_002752A0(reviver, target): revive animation 0x15F with end callback
  FUN_00274EE0, which spends the **downed player's Flash first, else the reviver's** (InvAdd(slot, 1, -1, 0)) and calls
  FUN_0022EB40(target, 1).
- **A downed player stays down:** HuKill FUN_00237E70 -> FUN_002302A8 (health 1, knock-down). In `local/m2/go1`
  (kill of player 3 at poll 9301) GameMgr+0x14C was still 0 at poll 10630 (no game over) and the screenshots
  `t0363_p9537.png` and `t0399_p10612.png` show player 3 lying with the red-cross revive marker 1311 polls later.
  VERIFIED (screenshots, state.txt). Game over needs all players down or one dead (FUN_004197A8, all_07.c:10062).
- **Teleport:** HuTeleportNearHuman FUN_0023B138 moves the mover only when the two are **3.6 units or more** apart
  (`12.959999 <= d*d`, all_03.c FUN_0023B138); otherwise it does nothing. The Lua Teleport core FUN_00385BB8(handle,
  float[3]*, -1) moves any object to a position and keeps the heading when the third argument is -1 (all_06.c:4650).

### 2.2 Design (real button path)
1. `t4_setup@9300`: PINE writes Flash(player 4 slot) = 1, Flash(player 3 slot) = 0; mailbox **FUN_00237E70(player 3
   handle)**. Player 3 has no Flash, so nothing else (no AI) will come for him.
2. `t4_move@9400`: distance player 4 - player 3 from the position table 0x00714B00 + human[+0x92]*0x20; if > 2.5:
   **FUN_0023B138(player 4 handle, player 3 handle)**; if still > 2.5: **FUN_00385BB8(player 4 handle,
   0x00714B00 + bidx(player 3)*0x20, 0xFFFFFFFF)** (onto player 3's position). Records all preconditions of 2.1
   (`preconditions.all_ok`).
3. Player 4 (pad 1, `--script3`) presses **D-pad Left** at 9500, 9560, 9620, 9680, 9740 (`invt_t4_s2.txt`). Presses
   while the revive runs or after it are ignored (the reviver is busy, or nobody is down).
4. `t4_read@9900`, `t4_direct@9950` (fallback, only if player 3 is still down: mailbox **FUN_00286BA8(player 4 human
   pointer)**, v0 = 1 = revive started, no button), `t4_read@10200`.

### 2.3 Command (tag `invt4`, about 420 s)
```
python -I tests/m2/nav_probe.py invt4 tests/m2/nav/boot_to_m1_2p.txt --inst 10 --players 4 --script2 tests/m2/nav/p2_join.txt --script3 tests/m2/nav/invt_t4_s2.txt --script4 tests/m2/nav/invt_t4_s3.txt --groups "$G" --ini EmuCore/Speedhacks/vuThread=false --callat "4000:0041ABC0:1,4010:00160D78:0x01FD9F9C" --seconds 420 --probe inv_tests:state:8900 --probe inv_tests:t4_setup:9300 --probe inv_tests:t4_move:9400 --probe inv_tests:t4_read:9900 --probe inv_tests:t4_direct:9950 --probe inv_tests:t4_read:10200
```

### 2.4 What to read, pass
- `t4_setup`: `kill_p3.done` = 1, `pads` = {1: 3, 2: 2}; `t4_move`: final distance <= 3.0, `preconditions.all_ok`.
- **Pass (`t4_read@9900`, `result.pass`):** player 3 not down, health > 1, Flash of player 4 = 0, Flash of player 3 = 0,
  `via` = "D-pad Left press (real path)". If the pass only appears at 10200 after `t4_direct` (`via` = direct
  FUN_00286BA8), the inventory/revive logic works for players 3-4 but the button path FAILED; if `t4_direct` returns
  v0 = 0, read `preconditions` for the condition that blocks it.
- Screenshot after 9800: player 3 standing in quarter 3.

### 2.5 Second scenario, AI gang revive (FUN_002BD808): BLOCKED in Mission 13 with players 3-4
FUN_002BD808 (all_03.c:88000) is an AI tactic step: an AI follower walks to a downed human only if that human, when a
player, has a Flash (InvCount(slot, 1)). It needs an AI Warrior in the squad. In Mission 13 with four players the squad
holds exactly the four players (VERIFIED: `p1_squad` in `local/m2/inv3/state.txt` and `go3/state.txt`: handles 0x162,
0x10165, 0x20168, 0x30234, all with a player index); with three players it holds players 1-3 (Rembrandt, Snow, Fox,
`m2_spawn_companion.md` section 1). So no AI can revive player 3 or 4 there. Needed: a mission whose squad has an extra
AI Warrior (candidate Mission 8, HYPOTHESIS on squad membership) or a 3-player run in such a mission. Not scripted.

## 3. T5 checkpoint copy and retry

### 3.1 Mechanism (VERIFIED code)
- **Checkpoint save:** Lua `SetCheckPoint(n)` (binding 0x0037B760) -> **FUN_0041ABC0(n)** -> FUN_0041CE98(GameMgr, n)
  (all_07.c:12528): GameMgr+0x33A = n, **InvSaveCheckpoint FUN_0041E0B8(GameMgr+0x480)** (with the inventory group:
  Inv+4..+0xFD3 -> 0x000E4000..0x000E4FCF, pnach lines A3), FUN_00422C60 (stats), FUN_00397E88 (objects). Mission 13
  has three checkpoints (`level_jump.md` table); reaching one by play is not deterministic, so the test calls the same
  core the script binding calls.
- **Retry:** FUN_00155408 (all_00.c:58799) is called by the in-game update when GameMgr+0x14C == 1 (game over) and
  FUN_0041D110 returns 0 (all_00.c:60911-60926). It reads choice flags in the object `*0x0050EC8C`; a menu handler,
  FUN_001D2A10, sets +0x7A8 when item 0 is confirmed (that this is the GAME OVER menu on that object is a HYPOTHESIS).
  With +0x7A8 set: if the string at +0x7B0 is empty -> **MenuLoadLevel(GameMgr+0x124)** without
  touching the checkpoint (ELF words at 0x001554E4 `lw v0,0x7A8(a0)`, 0x001554F0 `jal 0x00430EB0` (string length),
  0x001555F4 `lw a0,0x489C(v0)`, 0x001555F8 `jal 0x00160D78`, 0x001555FC `addiu a0,a0,0x124`); if it is not empty ->
  in place: GameMgr+0x14C = 0, FUN_00422D00, **InvRestoreCheckpoint FUN_0041E168(GameMgr+0x480)** (0x001555A8/AC), then
  a vtable call with that string.
- **Level start:** FUN_0015FE90 -> FUN_00418C68 (all_07.c:9616): InvClear(Inv, checkpoint < 2); **if checkpoint >= 2:
  InvRestoreCheckpoint** (copy 0x000E4000 -> live with A4).
- Inventory slots are cleared per player only by InvReleaseSlot FUN_0041EC60, called only from ReleasePlayer
  FUN_0022A2A8 with its second argument != 0; the callers that pass 1 are FUN_00239B80 (a Lua binding core) and the
  drop-out code in FUN_0041A460 (VERIFIED callers). That a level teardown does not release players 3-4 this way is a
  HYPOTHESIS (teardown not traced); T5b shows it.

### 3.2 Design
- `t5_give@9000` (PINE): slot 2 Flash 2, money 40, key 1; slot 3 Flash 1, money 25, spray 3.
- `t5_checkpoint@9100`: mailbox **FUN_0041ABC0(2)**; checks GameMgr+0x33A = 2 and a byte compare of live
  Inv+4..+0xFD3 with 0x000E4000..0x000E4FCF (`live_vs_copy.equal`); stores the checkpoint counts.
- `t5_spend@9200` (PINE): slot 2 Flash 0, money 5, key 0; slot 3 Flash 0, money 0, spray 0; the copy must not change.
- **T5a** `t5_restore_direct@9300`: mailbox **FUN_0041E168(GameMgr+0x480)** (the in-place retry call); live must equal
  the checkpoint counts and the copy byte for byte. Direct call.
- `t5_spend@9400` again; **T5b** `t5_retry@9500`: writes the spend values again, reads the string at GameMgr+0x124
  (expected "level9"; if not, it uses the level-table entry GameMgr+0x14E8+13*0x84, the string the standard CallAt
  uses) and calls **FUN_00160D78(that pointer)** = the retry branch's own call. The level reloads at checkpoint 2
  (chunk "level9_2") and the level start restores the copy. Real game path from the retry branch on (the GAME OVER
  menu itself is skipped).
- `t5_read` at 10500, 11000, 11800 (one of them should land after the load). `cal_p3/cal_p4.txt` keep pressing Start
  every 300 polls, so players 3-4 can join again after the reload; `t5_read` also lists handles and HUD slots.

### 3.3 Command (tag `invt5`, about 480 s)
```
python -I tests/m2/nav_probe.py invt5 tests/m2/nav/boot_to_m1_2p.txt --inst 10 --players 4 --script2 tests/m2/nav/p2_join.txt --script3 tests/m2/nav/cal_p3.txt --script4 tests/m2/nav/cal_p4.txt --groups "$G" --ini EmuCore/Speedhacks/vuThread=false --callat "4000:0041ABC0:1,4010:00160D78:0x01FD9F9C" --seconds 480 --probe inv_tests:state:8900 --probe inv_tests:t5_give:9000 --probe inv_tests:t5_checkpoint:9100 --probe inv_tests:t5_spend:9200 --probe inv_tests:t5_restore_direct:9300 --probe inv_tests:t5_spend:9400 --probe inv_tests:t5_retry:9500 --probe inv_tests:t5_read:10500 --probe inv_tests:t5_read:11000 --probe inv_tests:t5_read:11800 --probe inv_tests:state:11900
```

### 3.4 What to read, pass
- `t5_checkpoint.pass`: checkpoint 2, live = copy (all 0xFD0 bytes), copy counts = checkpoint counts.
- `t5_spend@9200.copy_unchanged` = true.
- **T5a pass:** `t5_restore_direct.pass` (live = checkpoint values, live = copy).
- **T5b pass:** `t5_read@...result.pass` in the first read after the load: checkpoint 2, level index 13, slots 2-3
  live and copy equal the checkpoint values (Flash 2 / money 40 / key 1 and Flash 1 / money 25 / spray 3);
  `slots_0_1_live_vs_checkpoint` is reported only (the level script may set players 1-2's items, e.g.
  `InvSetSpraycanCharges(9)` at 09229:2540).
- Risks: a level restart with four players has never been run (HUD slots 2-3 and the spawned player at level exit,
  `m2_hud_full.md` addendum items); if the instance hangs or crashes after 9500 that is itself a finding, and T5a still
  stands. The poll counter may pause during loading.
- Optional T5c (not scripted): the full menu path = all players down (`gameover_probe.kill_all`), then player 1
  confirms the GAME OVER menu item 0. Which button confirms (the menu handler gets an event code 4) and how long the menu
  needs are not known statically (HYPOTHESIS).

## 4. T7 money bank (Block B)

### 4.1 Mechanism (VERIFIED code / pnach text)
- Block B **is in** group `[warriors-4p 4p inventory]` of `mod/w4p_m1.pnach` (lines 2055-2062: 0x0015D3F4
  `jal 0x000E5000`, cave 0x000E5000-0x000E5018 adding Inv+0x864 and Inv+0xC58 to the bank, then `j 0x00155308`).
- **FUN_0015D160** (all_00.c:63413) is the update of the mission-complete state 0x005E5DF8 (vtable slot 0x00538694).
  When the state's choice word +0x24 (0x005E5E1C) is not 0 it handles the choice (1: checkpoint 1; 2: checkpoint 1 and
  reload this level GameMgr+0x124; 3: checkpoint 1 and next level), pops the state, adds InvCount(0, 2) and
  InvCount(1, 2) to the bank (FUN_0041E398) and calls the save sequence FUN_00155308 (patched by Block B).
- The only writer of the choice word is **FUN_0015D420(choice)** (all_00.c:63488): pushes the state if it is not on top
  and stores the choice. Callers: the in-game update when GameMgr+0x14C == 2 (choice 0, all_00.c:60933; Lua
  `MissionComplete()` = FUN_00160D00 sets 0x14C = 2) and Lua `HUDLaunchMissionComplete(n)` (binding 0x0036F218). The
  scripts call it with no argument or, in the level-skip handler WAD 4106 `main_61`, with **4** after `MenuLoadLevel`
  (`pseudo/04106_7e23a6f2.lua:1775`). How the normal summary screen turns choice 0 into a non-zero choice was not found
  (no other writer of 0x005E5E1C; HYPOTHESIS: through a pointer in HUD code), so the summary-screen path is not scripted.

### 4.2 Design
- `t7_setup@9000` (PINE): money of slots 0-3 = 10, 20, 30, 40; bank before.
- `t7_launch@9100`: mailbox **FUN_0015D420(4)** (HUDLaunchMissionComplete(4) core). On the next frame FUN_0015D160 banks
  the money (and starts the save sequence on the sandbox memory card). Choice 4 changes no level by itself; if the game
  sits in a strange state afterwards, the bank is already read. Alternative if needed: choice 2 (replay this level),
  same banking code.
- `t7_read` at 9300 and 9600.

### 4.3 Command (tag `invt7`, about 400 s)
```
python -I tests/m2/nav_probe.py invt7 tests/m2/nav/boot_to_m1_2p.txt --inst 10 --players 4 --script2 tests/m2/nav/p2_join.txt --script3 tests/m2/nav/cal_p3.txt --script4 tests/m2/nav/cal_p4.txt --groups "$G" --ini EmuCore/Speedhacks/vuThread=false --callat "4000:0041ABC0:1,4010:00160D78:0x01FD9F9C" --seconds 400 --probe inv_tests:state:8900 --probe inv_tests:t7_setup:9000 --probe inv_tests:t7_launch:9100 --probe inv_tests:t7_read:9300 --probe inv_tests:t7_read:9600
```

### 4.4 What to read, pass
- `t7_launch`: `launch.done` = 1, `choice_5e5e1c` = 4.
- **Pass (`t7_read@9300.result.pass`):** bank delta = 100 with Block B active (`block_b_active` true), = 30 without.
  A delta of 30 with Block B active = FAILED TEST for Block B. For a without-Block-B control run use `--patch` with a
  pnach copy that lacks lines 2055-2062 (the coordinator's decision; not created here).

## 5. T9 later (four instances in lockstep)
`inv_tests.py` uses PINE writes and PINE-timed calls: single instance only. For lockstep, replace them with CallAt
entries (exact polls, same on every instance; syntax `poll:function:a0:a1:a2:a3`, `GM` = GameMgr; one entry per poll,
at least 2 polls apart) of the Lua cores, e.g. `9000:0041EDB8:2:3` (InvGiveRevive 2 for player 3), `9010:0041EF00:40:3`
(GiveMoney 40 for player 3), `9020:0041EDB8:1:4`, `9030:0041EF00:25:4`, `9100:0041ABC0:2` (checkpoint 2), and HuKill
`00237E70` with player 3's handle (0x20168 in every Mission 13 run so far; re-check in `state.txt` after any spawn
change). These cores call the Lua inventory callbacks with slots 2/3 (risk row "Script callbacks" in
`m2_inventory34.md` section 8; HYPOTHESIS that they are harmless at runtime), which T9 would then also cover.

## 6. Files
- `tests/m2/inv_tests.py` (new): probe functions `state`, `t2_setup_p3/p4`, `t2_read`, `t2_fallback_p3/p4`,
  `t4_setup`, `t4_move`, `t4_read`, `t4_direct`, `t5_give`, `t5_checkpoint`, `t5_spend`, `t5_restore_direct`,
  `t5_retry`, `t5_read`, `t7_setup`, `t7_launch`, `t7_read`. Syntax-checked with `ast.parse`; not run.
- `tests/m2/nav/invt_t2_s2.txt`, `invt_t2_s3.txt`, `invt_t4_s2.txt`, `invt_t4_s3.txt` (new, CRLF).
- T5 and T7 reuse `tests/m2/nav/cal_p3.txt` and `cal_p4.txt`.

## Summary
- T2: real pick-up path (game drop function + touch pick-up), deterministic setup; fallbacks are direct and labelled.
  FUN_002334D0 is the mugging transfer, not a world pick-up (correction).
- T4: D-pad Left press (action 39), within 3.0 units, one press; downed player stays down (go1). AI gang revive BLOCKED
  in Mission 13 with four players.
- T5: game checkpoint save core + the retry branch's own MenuLoadLevel(GameMgr+0x124) call; T5a direct restore first.
- T7: Block B is in the group; banking runs through FUN_0015D420(4) -> FUN_0015D160; expected bank delta 100.
- Everything above is static; every runtime statement is HYPOTHESIS until these runs are made.

# M2 research: who may give gang (Warrior) commands; keep it to the first player

User requirement (2026-10-11, verbatim): "if you are copy player one to player 3 and 4 ( make sure only the first
player control the ganstar not all of them )".

This note is static analysis only (decompile `local/analysis/all/*.c`, `lua_bindings.tsv`, pseudo-Lua in
`local/analysis/pseudo`, disassembly of `local/disc/SLUS_212.15`). Nothing was run. SLUS-21215 v1.03.
Function names are our labels.

## 1. How the game decides who may command (VERIFIED, code)

**The "war chief" flag is human+0x3AC (byte, written as a word).** A human with +0x3AC == 1 is the leader of its
gang. All gang-command paths check it:

| Path | Code | Check |
|---|---|---|
| Button press opens the command menu | `FUN_002843F8` (player action handler), branch `FUN_0027C058` → 0x002845C0 `jal FUN_001A6D28(PlayerHUD[human+0x380] + 0x1EF0)` | before: human+0x1B0 != -1 (0x00284584-0x0028458C) and per-player lock GM+0x42E == 0; inside `FUN_001A6D28` 0x001A6DE8-0x001A6DEC: `lbu s4,0x3AC(a0)`, menu closes unless == 1 |
| Button release issues the selected command | same handler, branch `FUN_0027C080` → 0x00284564 `jal FUN_001A6C58` → `FUN_0041C4E0(GM, human, cmd, ...)` | human+0x1B0 != -1 (0x00284518-0x00284520), lock byte, and the menu must be open (PlayerHUD+0x1EFC != 0, only set by a successful open) |
| Lua `WCEnableAllCommands` → `FUN_0041DB08` | loops player indices 0..1 | only players with +0x3AC == 1 get their 7 command-enable bytes |
| Leader's automatic orders | `FUN_00303988` | returns at once unless human+0x3AC == 1 |

**Who gets the flag:**
- `MakePlayer` (`FUN_00229C40`, decompile all_02.c around line 54192): sets the new player's +0x3AC = 1, then clears it
  again if any other player is already leader (story mode GameMgr+0x158 == 0: any player; other modes: a player of the
  same gang). So in story mode only the **first** player made is leader; every later player is not.
- `HuSetWarChief` (Lua, `FUN_0035D158` → `FUN_002398B0`): moves the flag. If the new chief is not a player, the
  current leader is released and the new human is made a player **with the leader's pad and HUD slot**; if it is
  already a player, it gets +0x3AC = 1, the old leader 0, and `FUN_00419E10` swaps it into player index 0 (pads stay
  with their humans). Scripts call it 8 times in 4 files, always for `player` (player 1's character), a freshly
  created Warrior, or a transient sequence that ends with `HuSetWarChief(player)` (08916). So the flag stays with
  player 1's pad.
- `GangSetLeader` (Lua, `FUN_0016A538`) sets a gang's AI leader; it does not touch +0x3AC (8 script uses, only one for
  GangWarriors, in a level-64 posing scene).

**Original 2-player story mode (VERIFIED, code):** player 2 joins through `MakePlayer` while player 1 is leader, so
player 2's +0x3AC = 0 and its command menu closes immediately. **Player 2 cannot give gang commands.** Story scripts
enable commands only for `player` (85 `WCEnableCommand(player, ...)`, 37 `WCIssueCommand(player, ...)`; never
`player2`). Rumble scripts enable both `Rumble.player1` and `Rumble.player2`: in Rumble (GameMgr+0x158 != 0) each player
leads their own gang (pseudo-Lua grep, VERIFIED counts).

Naming correction: Lua `EnableCommand` (0x00369638 → `FUN_001467A8`) is the per-pad context-action table, not gang
commands. The function patched at 0x0041DC44 (`FUN_0041DBE8`) is Lua **`WCEnableCommand`**.

## 2. Players 3-4 with our patches

- **Joined companions and spawned clones are not leaders (VERIFIED, code):** they become players through
  `MakePlayer` after player 1, so +0x3AC = 0, and the command menu closes when they press the command button. The
  flag belongs to the human object, not to the character, so a clone of player 1's character (`m2_spawn_companion.md`,
  same character id) does **not** inherit it. No character-id or name check exists on the command path
  (`FUN_002843F8`, `FUN_001A6D28`, `FUN_001A6C58`). HYPOTHESIS for code outside these functions.
- B1 retargets the PlayerHUD table reads in `FUN_002843F8` to T_A (0x00284540, 0x002845AC), so the menu calls for
  slots 2-3 hit real objects; the leader check then rejects them. The B1 change of `WCEnableCommand` (0x0041DC44 limit
  4) only writes enable bytes; it cannot open the menu. `WCEnableAllCommands` still loops 0..1.
- **Remaining ways for players 3-4 to command (HYPOTHESIS, edge cases):** a script `HuSetWarChief` on a human
  controlled by player 3 or 4 (none found in story scripts except the transient 08916 sequence), or a future change of
  the leader rules. Today the game's own rule already gives what the user asked.

## 3. Defensive patch: players with index 2-3 never get the command menu (2 words)

Make both button branches of `FUN_002843F8` accept only player indices 0 and 1. The existing test
`nor v0,zero,a0` / `beq v0,zero,return` (reject index -1) becomes `sltiu v0,a0,2` (reject -1, 2 and 3; `lb`
sign-extends, so -1 is a huge unsigned value):

```
// [warriors-4p 4p gang command] only player indices 0-1 can open/issue the gang command menu
patch=2,EE,0028451C,word,2C820002 // was 00041027 nor v0,zero,a0 -> sltiu v0,a0,2 (issue path: player index 0/1 only)
patch=2,EE,00284588,word,2C820002 // was 00041027 nor v0,zero,a0 -> sltiu v0,a0,2 (open path: player index 0/1 only)
```

- Originals match the ELF (disassembly 0x00284518-0x0028458C). `python -I tools/note_patches.py check
  mod/w4p_m1.pnach <fragment>`: 1,686 addresses, only the 6 known group-A vs B1 alternatives, no new problem. No cave
  needed. Both branches return 0 at 0x00284900, as for a non-player.
- Player 2 is unchanged (index 1 passes; it is still a non-leader in story mode, and keeps leading its own gang in
  Rumble). Player 1 is unchanged.
- Players 3-4 lose only the gang-command menu; their own fighting and actions are other branches of the handler.
- **To also restrict player 2:** use immediate 1 (`2C820001`) at both words. This would break player 2's commands in
  Rumble modes, so it is not proposed.
- **Index vs. person:** after a `HuSetWarChief` swap the leader always sits at player index 0 (`FUN_00419E10`). If a
  script ever made player 3's human the war chief, that human would become index 0 and could command, and player 1's
  human (now index 2) could not. A stricter "only the host's controller" rule would check the human's pad
  (controller record `FUN_0021D3E8(human)+0x19` must be 0 or 4); that needs a small cave and was not written, because
  no story script does this.

## 4. Runtime checks (PINE, one instance)
- human+0x3AC (byte) for players 1-4: expect 1, 0, 0, 0 (players via GameMgr+0x228+4*i, handle table 0x006EBD38).
- With the patch: player 3 pressing the command button leaves T_A[2]+0x1EF0+0xC (menu open flag) at 0; player 1's
  menu still opens (+0xC = 1) and orders still change the gang's behaviour.
- Without the patch: player 3's menu should also stay closed (leader check), which confirms section 2.

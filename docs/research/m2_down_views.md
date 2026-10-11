# M2: a downed player keeps their own view (F-0148 follow-up, 2026-10-11)

Question (STATE.md next step 2): when ONE player is down, does the game drop that player's view, and does that break
the per-player crop? Static analysis below; runtime tests in section 4 (single instance, SINGLE-PC, bots).
Build SLUS-21215 v1.03, addresses static (ELF). Function names are OUR labels. Disassembly from a scratch R5900
disassembler over `local/disc/SLUS_212.15`; decompile `local/analysis/all/all_00.c`.

## 1. The rule that removes a view (VERIFIED, static)
`FUN_00121888` (our label: MergeState, runs every frame) owns the two per-player view flags 0x0050B1E8 / 0x0050B1EC.
LayoutViewports `FUN_00122ED0` lays out one view per camera whose flag is 1 (camera vtable +0x28C = `FUN_00121E30`).
- Early path (0x001218AC-0x001218CC -> 0x00121D98): fewer than 2 players (GameMgr+0x224) or 0x0050B1C0 != 1: both
  flags = 1, no re-layout.
- Normal path: `uVar4 = FUN_00123500(player 1 human)`, `iVar3 = FUN_00123500(player 2 human)`; flags = these values
  with the rule "if both are 0, keep player 1's view" (0x00121AAC-0x00121AF4); when a flag changes, re-layout
  (`FUN_00122ED0`) and merge-camera handling.
- `FUN_00123500(human)` (our label: HasOwnView) returns 0 when `FUN_00227E60` (HuIsAlive core, state mask
  0x1_8005_0000, `m2_combat34.md` 1) says "not active" (down, dead and similar states), or when the human is arrested
  (0x20000, `FUN_00223B70`) and either the 0x006FE998 list check fails or the player's inventory has no item 6 (key).
  Otherwise 1.

So in the original 2-player game a player who is down loses their half of the screen and the partner gets the full
screen until the revive. With our 4p group players 3-4 always count as having a view (`views4`, cave 0x000F0F80), so
only players 1-2 can lose theirs (F-0148: [1,1] -> [0,1] -> [1,0] at GAME OVER).

## 2. Why that breaks online play (VERIFIED, code)
The fork's crop (`CropFor`, `emulator/pcsx2/pcsx2/W4P/W4P.cpp`) shows quarter number = the game player index that owns
the PC's controller. LayoutViewports packs the remaining views, so when player 1's view goes:
| Players | Views after | PC of player 1 shows | PC of player 2 | PC of player 3 | PC of player 4 |
|---|---|---|---|---|---|
| 4 | 3 | player 2's view | player 3's | player 4's | whole screen (index 3 >= 3 views: crop off) |
| 2 | 1 | player 2's view full screen (crop off) | its own view, full screen | - | - |
In 4-player sessions this shows the wrong player's picture on every PC; in 2-player sessions the downed player sees the
partner's view (the original local split-screen behaviour), against D8 ("every player always sees their own camera").

## 3. Fix (2 words, group `[warriors-4p own view]`, source `mod/make_pnach.py`)
Keep both flags at 1 in the normal path; everything else in `FUN_00121888` stays (it still re-lays out when some other
code changed the flags, and still picks the focus human 0x005D91B8 from player 2 when player 1 is down).
| Address | Original (ELF) | New | Meaning |
|---|---|---|---|
| 0x00121AE0 | 8C64B1D8 `lw a0,-0x4e28(v1)` (0x0050B1D8, only used by the next movz) | 24130001 `addiu s3,zero,1` | player 2 flag value s3 = 1 (stored at 0x00121AE8) |
| 0x00121AEC | 00A4880A `movz s1,a1,a0` | 00A0882D `daddu s1,a1,zero` | player 1 flag value s1 = a1 = 1 (stored at 0x00121AF4) |
Encodings checked by hand (I-type op 9 rt 19; SPECIAL fn 0x2D rs 5 rd 17) and the originals read from the ELF.
`python -I tools/note_patches.py check mod/w4p_m1.pnach`: `checked 2257 addresses in 1 files: 6 problems` (the 6 known
`[4p hud A]` / `[4p hud B1]` alternatives, nothing new).

Side effects (HYPOTHESIS until tested): with the flags fixed at 1, the branch at 0x00121AF0 always skips the SetActive
calls that the merge used; the "both players down" case keeps both views (each quarter gets its own GAME OVER text,
which should also fix quarter 4's missing text, F-0145). While players 1 and 2 are both up, the original already computes [1,1], so the fix
changes nothing then (including after other code such as `FUN_0011DAA8` / `FUN_00158728` sets [1,0] for a one-view
camera shot); it only differs while player 1 or 2 is down, out or arrested without a key, or while player 2's handle does not resolve to a human (player count still >= 2) (VERIFIED, static: the two
values only differ from the original when `FUN_00123500` returned 0 for a player).

## 4. Runtime tests (SINGLE-PC, one instance, scripted input, MTVU off, build w4p-m3-7)
Setup: fresh boot, level jump to Mission 13 (W4P CallAt), players 3-4 by the game's own Start-join (4-player runs);
player 1 downed at poll 9000 with HuKill (`tests/m2/down_probe.py` `down_p1`: FUN_00237E70 through the test-call
mailbox); `down_probe.views` reads at polls 8990-10500. "Old patch" = `mod/w4p_m1.pnach` of commit bdb2c52 (`--patch`).
| Run | Players / patch | Before | After the down (polls 9010-10500) | Player 1 state |
|---|---|---|---|---|
| d1_4p_base | 4 / old | 4 views, 2x2, flags [1,1] | **3 views**, flags [0,1]; screenshot `t0362_p9328.png`: three packed views, 4th quarter empty except a stray radar | flags 0x40_0004_0000, health 1, no game over for 50 s |
| d1_4p_fix | 4 / fix | 4 views, [1,1] | **4 views**, [1,1]; `t0357_p9349.png`: player 1's quarter shows player 1 lying down with the revive marker | same |
| d1_2p_base | 2 / old | 2 views, [1,1] | **1 view** (layout 1x1), [0,1]: both PCs would show player 2's view | same |
| d1_2p_fix | 2 / fix | 2 views, [1,1] | **2 views**, [1,1]; `t0358_p9355.png`: player 1's view shows player 1 down with the revive marker, player 2's view unchanged | same |
Crop owner indices per session slot were [0, 1, 3, 2] (pad owners +0x42; join order) in every 4-player run.
VERIFIED (PINE reads, `local/m2/d1_*/probes.json`, screenshots). F-0151.

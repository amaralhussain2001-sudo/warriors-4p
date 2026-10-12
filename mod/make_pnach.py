"""Generate the warriors-4p game patch (pnach) for SLUS-21215 v1.03 (CRC B99A75DE).

M1 content (needs the W4P PCSX2 fork; without it the hook SYSCALL would raise an unhandled exception, so the
patch must only be enabled together with the fork):
  - Controller-read hook: the call to the libpad read at 0x001498E0 goes through a cave at 0x000F0400 that keeps a
    poll counter at 0x000F0500 (incremented on every read of pad 0) and then executes SYSCALL with
    v1 = 0x57345030, a0 = port buffer, a1 = poll counter. The fork blocks there until every player's input for
    the poll is known and writes it into the port buffer (docs/plan/M1.md).
  - Layout: 2x2 grid whenever the game renders 2 or more views (0x00123300: sltiu v0,v0,3 -> 2), so each player's
    view is a 4:3 quarter that the fork can show full screen.
Only our own code and instruction operands are written; no game code is copied.
Usage: python -I mod/make_pnach.py > mod/w4p_m1.pnach
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
from mips_asm import assemble  # noqa: E402

CAVE = 0x000F0400
COUNTER_OFF = 0x500  # counter at 0x000F0500
PADREAD_SITE = 0x001498E0  # jal 0x00149770 (F-0051)
LAYOUT_SITE = (0x00123300, 0x2C420003, 0x2C420002)

HOOK = """
  addiu sp, sp, -32
  sw ra, 0(sp)
  sw a0, 4(sp)
  jal 0x149770
  nop
  lw a0, 4(sp)
  lw t0, 0x104(a0)
  lw t1, 0x108(a0)
  or t2, t0, t1
  bne t2, zero, skip
  nop
  lui t3, 0x000F
  lw t4, 0x500(t3)
  addiu t4, t4, 1
  sw t4, 0x500(t3)
skip:
  lui t3, 0x000F
  lw a1, 0x500(t3)
  lui v1, 0x5734
  ori v1, v1, 0x5030
  syscall
  lw ra, 0(sp)
  jr ra
  addiu sp, sp, 32
"""


def jal(t):
    return 0x0C000000 | (t >> 2)


def main():
    words, _ = assemble(HOOK, CAVE)
    assert CAVE + 4 * len(words) <= 0x000F0000 + COUNTER_OFF, "cave overlaps the poll counter"
    out = ["gametitle=The Warriors (NTSC-U) (SLUS-21215) - warriors-4p", "",
           "[warriors-4p M1]", "author=warriors-4p",
           "description=Online co-op support (requires the warriors-4p PCSX2 build). M1 proof of concept.", ""]
    for k, w in enumerate(words):
        out.append(f"patch=2,EE,{CAVE + 4 * k:08X},word,{w:08X}")
    out.append(f"patch=2,EE,{PADREAD_SITE:08X},word,{jal(CAVE):08X} // was 0C0525DC jal 0x00149770")
    addr, old, new = LAYOUT_SITE
    out.append(f"patch=2,EE,{addr:08X},word,{new:08X} // was {old:08X}: 2x2 layout from 2 views")
    # The 3D cameras get their view windows from a second copy of the same test (FUN_00120A98). Without this the
    # quarters are drawn with side-by-side proportions, i.e. stretched 2x horizontally (local/m3/aspect_cmp, F-0098).
    out.append("patch=2,EE,00120B8C,word,2C420002 // was 2C420003: 2x2 view windows for the 3D cameras")
    # Decision D8: every player always gets their own view. Uses the game's own option "2P Split Screen Merge"
    # (live flag 0x0050B1C4, setter FUN_00418AC8; docs/research/view_merge_rule.md). The saved option is untouched.
    out += ["", "[warriors-4p own view]", "author=warriors-4p",
            "description=Online sessions: never merge the players' views (game option 2P Split Screen Merge off).", "",
            "patch=1,EE,0050B1C4,word,00000000 // live merge option, was 00000001",
            "patch=2,EE,00418AD4,word,AC40B1C4 // was AC45B1C4 (sw a1): the option setter stores 0",
            # A downed player (no item 6) or an 'out' player loses their view in FUN_00121888 (F-0148; FUN_00123500).
            # Our crop picks view = player index, so a dropped view shifts every PC's picture. Keep both flags at 1;
            # the rest of FUN_00121888 is unchanged (it re-lays out when the flags were changed elsewhere).
            "patch=2,EE,00121AE0,word,24130001 // was 8C64B1D8 lw a0,-0x4e28(v1) -> addiu s3,zero,1: player 2 view flag = 1",
            "patch=2,EE,00121AEC,word,00A0882D // was 00A4880A movz s1,a1,a0 -> daddu s1,a1,zero: player 1 view flag = 1 (a1 = 1)",
            # FOVFIX (M6, user report 2026-10-12, F-0198): in the 2x2 layout each quarter has the full screen's shape, but
            # FUN_00120A98 (made for the side-by-side split) halved both view windows in mode 2, so a cropped quarter was
            # about 1.6x zoomed in (window 0.32 vs 0.51 in single player). Without the halving a quarter shows the follow
            # camera's own 65 deg view, the same picture scale as the original 2-player split screen.
            "patch=2,EE,00120C04,word,10000009 // was 3C013F00 lui at,0x3f00 -> beq zero,zero,0x00120C2C (mode 2: windows and +0x48 not halved)"]
    # Each player's radar inside their own quarter, at single-player size after the 2x crop (docs/research/hud_scale.md
    # patch 2A, which replaces hud_layout.md patch A; patch B kept). Only layout mode 2 (our 2x2 patch) changes.
    hud = [(0x001AFF48, 0x0803C180, "was 3C020051 lui v0,0x51 -> j 0x000F0600"),
           (0x001AFF4C, 0x00000000, "was 3C013F80 -> nop (delay slot)"),
           (0x001AFFA4, 0x4600B806, "was C460D42C lwc1 f0,D42C -> mov.s f0,f23 (P2 depth from the cave)"),
           (0x001AA648, 0x00000000, "was E7A00008 swc1 f0,8(sp): widget keeps the caller's height"),
           (0x000F0600, 0x3C020051, "lui v0,0x51"),
           (0x000F0604, 0x3C013F80, "lui at,0x3f80"),
           (0x000F0608, 0x4481B000, "mtc1 at,f22 (1.0, as 0x001AFF50)"),
           (0x000F060C, 0xC440D438, "lwc1 f0,D438(v0): P1 depth (as 0x001AFF54)"),
           (0x000F0610, 0xC457D42C, "lwc1 f23,D42C(v0): P2 depth"),
           (0x000F0614, 0x8C43B1A4, "lw v1,B1A4(v0): layout mode"),
           (0x000F0618, 0x24010002, "addiu at,zero,2"),
           (0x000F061C, 0x14610013, "bne v1,at,0x000F066C: not the 2x2 mode"),
           (0x000F0620, 0x00000000, "nop"),
           (0x000F0624, 0xC443B20C, "lwc1 f3,B20C(v0): HUD scale S"),
           (0x000F0628, 0xC444B208, "lwc1 f4,B208(v0): HUD aspect A"),
           (0x000F062C, 0x3C013F00, "lui at,0x3f00: 0.5"),
           (0x000F0630, 0x44812800, "mtc1 at,f5"),
           (0x000F0634, 0x460518C2, "mul.s f3,f3,f5: Wz = S/2"),
           (0x000F0638, 0x46032102, "mul.s f4,f4,f3: W = A*S/2"),
           (0x000F063C, 0xC446D428, "lwc1 f6,D428(v0): xs (single-player radar x)"),
           (0x000F0640, 0x0803C1A0, "j 0x000F0680 (TOPZ: zs, raised when 3+ views; 0x000F0644 runs in the delay slot)"),
           (0x000F0644, 0x46040202, "mul.s f8,f0,f4"),
           (0x000F0648, 0x46083041, "sub.s f1,f6,f8: P1 x = xs - d1*W"),
           (0x000F064C, 0x46030202, "mul.s f8,f0,f3"),
           (0x000F0650, 0x46083880, "add.s f2,f7,f8: P1 z = zs + d1*Wz"),
           (0x000F0654, 0x46000000, "add.s f0,f0,f0: P1 depth = 2*d1"),
           (0x000F0658, 0x4604BA02, "mul.s f8,f23,f4"),
           (0x000F065C, 0x46083500, "add.s f20,f6,f8: P2 x = xs + d2*W"),
           (0x000F0660, 0x4603BA02, "mul.s f8,f23,f3"),
           (0x000F0664, 0x46083D40, "add.s f21,f7,f8: P2 z = zs + d2*Wz"),
           (0x000F0668, 0x4617BDC0, "add.s f23,f23,f23: P2 depth = 2*d2"),
           (0x000F066C, 0x0806BFD6, "j 0x001AFF58"),
           (0x000F0670, 0x00000000, "nop"),
           # TOPZ (m2_hud_full.md addendum 2, R7; only with 3+ views, so 2-player sessions are unchanged): top-row radars
           # 0.05 higher so the disc's lower edge stays inside the top quarters (no sliver at the top of the bottom row)
           (0x000F0680, 0xC447D430, "lwc1 f7,D430(v0): zs"),
           (0x000F0684, 0x8C41B198, "lw at,B198(v0): view count (0x0050B198)"),
           (0x000F0688, 0x28210003, "slti at,at,3"),
           (0x000F068C, 0x14200005, "bne at,zero,0x000F06A4: fewer than 3 views, zs unchanged"),
           (0x000F0690, 0x00000000, "nop"),
           (0x000F0694, 0x3C013D4C, "lui at,0x3d4c"),
           (0x000F0698, 0x3421CCCD, "ori at,at,0xcccd: 0.05"),
           (0x000F069C, 0x44812800, "mtc1 at,f5"),
           (0x000F06A0, 0x460539C0, "add.s f7,f7,f5: zs + 0.05"),
           (0x000F06A4, 0x0803C192, "j 0x000F0648"),
           (0x000F06A8, 0x00000000, "nop"),
           # RHALF (M6, F-0191): in the 2x2 layout (mode 0x0050B1A4 == 2, >= 2 views) the radar disc size 0x0050E9BC and the
           # blip size 0x0050E9CC are halved, so after the presentation crop (x2) the radar has single-player size and stays
           # inside its own quarter; all other modes (single player, original split screen) load the original values.
           (0x001C598C, 0x0803A000, "was C440E9BC lwc1 f0,-0x1644(v0) -> j 0x000E8000 (radar size, update FUN_001C5210)"),
           (0x001C6304, 0x0803A010, "was C481E9BC lwc1 f1,-0x1644(a0) -> j 0x000E8040 (radar size, draw FUN_001C60B0)"),
           (0x001C5D78, 0x0803A020, "was C46CE9CC lwc1 f12,-0x1634(v1) -> j 0x000E8080 (radar blip size)"),
           (0x000E8000, 0xC440E9BC, "lwc1 f0,-0x1644(v0): radar size 0.9 (original load)"),
           (0x000E8004, 0x8C41B1A4, "lw at,-0x4E5C(base): layout mode 0x0050B1A4"),
           (0x000E8008, 0x2421FFFE, "addiu at,at,-2"),
           (0x000E800C, 0x14200007, "bne at,zero,ret: not the 2x2 layout"),
           (0x000E8010, 0x00000000, "nop"),
           (0x000E8014, 0x8C41B198, "lw at,-0x4E68(base): views 0x0050B198"),
           (0x000E8018, 0x2C210002, "sltiu at,at,2"),
           (0x000E801C, 0x14200003, "bne at,zero,ret: fewer than 2 views"),
           (0x000E8020, 0x3C013EE6, "lui at,0x3ee6"),
           (0x000E8024, 0x34216666, "ori at,at,0x6666: 0.45"),
           (0x000E8028, 0x44810000, "mtc1 at,f0"),
           (0x000E802C, 0x08071665, "j 0x001C5994"),
           (0x000E8030, 0x00000000, "nop"),
           (0x000E8040, 0xC481E9BC, "lwc1 f1,-0x1644(a0): radar size 0.9 (original load)"),
           (0x000E8044, 0x8C81B1A4, "lw at,-0x4E5C(base): layout mode 0x0050B1A4"),
           (0x000E8048, 0x2421FFFE, "addiu at,at,-2"),
           (0x000E804C, 0x14200007, "bne at,zero,ret: not the 2x2 layout"),
           (0x000E8050, 0x00000000, "nop"),
           (0x000E8054, 0x8C81B198, "lw at,-0x4E68(base): views 0x0050B198"),
           (0x000E8058, 0x2C210002, "sltiu at,at,2"),
           (0x000E805C, 0x14200003, "bne at,zero,ret: fewer than 2 views"),
           (0x000E8060, 0x3C013EE6, "lui at,0x3ee6"),
           (0x000E8064, 0x34216666, "ori at,at,0x6666: 0.45"),
           (0x000E8068, 0x44810800, "mtc1 at,f1"),
           (0x000E806C, 0x080718C3, "j 0x001C630C"),
           (0x000E8070, 0x00000000, "nop"),
           (0x000E8080, 0xC46CE9CC, "lwc1 f12,-0x1634(v1): blip size (original load)"),
           (0x000E8084, 0x8C61B1A4, "lw at,-0x4E5C(base): layout mode 0x0050B1A4"),
           (0x000E8088, 0x2421FFFE, "addiu at,at,-2"),
           (0x000E808C, 0x14200007, "bne at,zero,ret: not the 2x2 layout"),
           (0x000E8090, 0x00000000, "nop"),
           (0x000E8094, 0x8C61B198, "lw at,-0x4E68(base): views 0x0050B198"),
           (0x000E8098, 0x2C210002, "sltiu at,at,2"),
           (0x000E809C, 0x14200003, "bne at,zero,ret: fewer than 2 views"),
           (0x000E80A0, 0x3C013C54, "lui at,0x3c54"),
           (0x000E80A4, 0x3421FDF4, "ori at,at,0xfdf4: half of 0x3CD4FDF4"),
           (0x000E80A8, 0x44816000, "mtc1 at,f12"),
           (0x000E80AC, 0x08071760, "j 0x001C5D80"),
           (0x000E80B0, 0x00000000, "nop")]
    out += ["", "[warriors-4p hud]", "author=warriors-4p",
            "description=Online sessions: each player's radar inside their own view at single-player size (2x2 layout).", ""]
    out += [f"patch=2,EE,{a:08X},word,{w:08X} // {c}" for a, w, c in hud]
    # Optional, testing: per-view markers (1P/2P) at half size (hud_scale.md 2B).
    out += ["", "[warriors-4p hud markers]", "author=warriors-4p", "description=Testing: per-view markers at half size.", "",
            "patch=2,EE,00196370,word,46000506 // was 46160502 mul.s f20,f0,f22 -> mov.s f20,f0",
            "patch=2,EE,00196398,word,460003C6 // was 461703C2 mul.s f15,f0,f23 -> mov.s f15,f0"]
    # Decision D9: real 60 fps (docs/research/sixty_fps.md, R60-1..4). Experimental until speed parity is tested.
    out += ["", "[warriors-4p 60fps]", "author=warriors-4p",
            "description=Experimental real 60 fps: flip every vblank, game logic every 1/60 s step, logic time step halved.", "",
            "patch=1,EE,00596D70,byte,01 // R60-1 swap interval 1 (was 2 from 0x0050CDB0)",
            "patch=2,EE,003A2F08,word,3C02004A // R60-2 SimAdvance: one 1/60 s step per pass (was 3C020095)",
            "patch=2,EE,003A2F30,word,3C17004A // R60-2 (was 3C170095)",
            "patch=2,EE,003A2F94,word,2E420001 // R60-2 (was 2E420002)",
            "patch=2,EE,0024912C,word,30640000 // R60-3 SimStep: logic on every step (was 30640001)",
            "patch=2,EE,005102CC,word,3C888889 // R60-4 LogicDt 1/60 (was 3D088889 = 1/30); every frame: tested (w60_ee2); may undo slow-motion scaling (R-22). Startup-only (place 0) is untested from boot.",
            "patch=2,EE,0023B7C8,word,3C013C88 // R60-4 LogicDt writer (was 3C013D08)",
            "patch=2,EE,0023B7FC,word,3C013C88 // R60-4 (was 3C013D08)",
            "patch=2,EE,0030C8CC,word,3C013C08 // R60-4 (was 3C013C88)",
            "patch=2,EE,0030C924,word,3C013B88 // R60-4 (was 3C013C08)",
            "patch=2,EE,0030C94C,word,3C013C88 // R60-4 (was 3C013D08)",
            "patch=2,EE,0041AB40,word,3C013C88 // R60-4 (was 3C013D08)",
            "patch=2,EE,0041ABA4,word,3C013C88 // R60-4 (was 3C013D08)",
            "patch=2,EE,00249B44,word,3C013C88 // R60-4 camera clamp in SimStep (was 3C013D08)",
            # M6 (m6_sixty_title.md): menus/title/loading run the GameClock in fixed-step mode, which advanced 1/30 s per
            # drawn frame -> two logic steps (two pad updates) per frame with R60-2/3, so the title never saw Start pressed.
            "patch=2,EE,001459C8,word,3C013C88 // R60-FS GameClock fixed step 1/60 s per frame (was 3C013D08 = 1/30): one logic step per frame in menus",
            "patch=2,EE,00145A98,word,3C05004B // R60-FS fixed-step unscaled clock +0x4B0000 cycles per frame (was 3C050096 = 0x960000)"]
    # M2 (experimental): four genuine players. GameMgr storage and limits (docs/research/m2_gamemgr.md) and the engine
    # tables below GameMgr: pads, cameras, ScreenEffects, listener buffer, camera flags (m2_pads_cameras.md); the 0x5C
    # per-player records (m2_gamemgr_records.md); interim HUD guards, no HUD for players 3-4 (m2_hud_players34.md (A));
    # MakePlayer clears a dead-brain flag, and the per-player block +0x414..+0x42F widened (m2_player_control.md P-1, P-2);
    # the mission join script event (player-2 scenes) is not sent for players 3-4 (m2_black_screen.md); split-view
    # camera lookups for players without a camera yet fall back safely (m2_hud_players34.md addendum); players 3-4
    # count as having their own view (addendum 2); views 3-4 get light slots and their follow
    # cameras target their own player (m2_views34.md).
    # Lines extracted by tools/note_patches.py and checked against the ELF. New data at 0x000F0800-0x000F093F is
    # zeroed once at startup (place 0; never place 1/2 for live data).
    frag = []
    for name in ("gamemgr.txt", "engine.txt", "records.txt", "hud34.txt", "control.txt", "joinevent.txt", "camsafe.txt", "views4.txt", "lights.txt", "camtarget.txt", "gangcmd.txt", "combat.txt"):
        frag += [l.rstrip() for l in open(os.path.join(HERE, "m2", name), encoding="utf-8") if l.startswith("patch=")]
    out += ["", "[warriors-4p 4p]", "author=warriors-4p",
            "description=Experimental: four players (engine tables for 4; players 3-4 join with Start).", ""]
    out += [f"patch=0,EE,{a:08X},word,00000000 // M2 data block, zero at startup" for a in range(0x000F0800, 0x000F0940, 4)]
    # Lines replaced by the full HUD (m2_hud_full.md section 4) go to their own group "4p hud A" (interim: no HUD for
    # players 3-4); "4p hud B1" (players 3-4 PlayerHUD + radar) and "4p hud B2" (per-view HUD) replace them.
    superseded = ("001C0648", "001C7890", "001A6D28", "001A6C38", "0041DC44", "0041DC50")
    hud_a = [l for l in frag if l.split(",")[2].upper() in superseded]
    frag = [l for l in frag if l.split(",")[2].upper() not in superseded]
    out += frag
    out += ["", "[warriors-4p 4p hud A]", "author=warriors-4p",
            "description=Experimental: interim HUD guards (no HUD for players 3-4). Use either this or 4p hud B1.", ""] + hud_a
    for name, title, desc in (("hud_b1.txt", "4p hud B1", "players 3-4 PlayerHUD and radar (m2_hud_full.md)"),
                              ("hud_b2.txt", "4p hud B2", "per-view HUD at single-player size (m2_hud_full.md)"),
                              ("markers34.txt", "4p markers", "radar icons drawn on their own radar disc (B2 copied them into every quarter as floating 1P/2P/W labels), radars 3-4 get the same icons as radar 2, players 3-4 shown as 3P (red) / 4P (green) labels built at runtime from the game's own 2P art and HUD digits (D22), original label rule otherwise, no stale 2P label on players 3-4 after a merged view, Select health ring of players 3-4 from own per-view sprites; needs hud, 4p, 4p hud B1 and B2 (m6_markers_map.md)"),
                              ("spawn.txt", "4p spawn", "spawn a Warrior when no companion is free for player 3-4 (m2_spawn_companion.md)"),
                              ("spawn_leave.txt", "4p spawn leave", "delete an added Warrior when its player leaves (m2_spawn_companion.md)"),
                              ("inventory.txt", "4p inventory", "items, money and Flash revives for players 3-4; needs 4p and 4p hud B1 (m2_inventory34.md)"),
                              ("fx34.txt", "4p fx", "fades, flashes, blur and game-over black for views 3-4; needs 4p (m2_fx34.md)"),
                              ("fx34_fog.txt", "4p fx fog", "optional: 3D fog on views 3-4 (2 extra fog systems; m2_fx34.md B-opt)"),
                              ("session.txt", "session", "session policies - movie flag, pause by a downed player 1, no Player 2 drop-out in Quit, LEAVE(index); needs 4p spawn and spawn leave (session_policies.md)"),
                              ("missions.txt", "missions", "M6 mission fixes - X1 delete guard (LEAVE player 3/4 before a script deletes his human), X3 HuChangePlayerGang wrapper, X7 starting items for players 3-4 (owed again after a forced leave), X4 teleport follow, X6 Lua fixes after each script file (LUACH; M13 subway camera guard); needs session, 4p spawn and spawn leave (m6_fixes.md, m6_chooser.md, m6_x4_x6.md)")):
        lines = [l.rstrip() for l in open(os.path.join(HERE, "m2", name), encoding="utf-8") if l.startswith("patch=")]
        # Guard (F-0192): required game hooks of a fragment; a rewrite once dropped the session hooks silently.
        required = {"session.txt": ("0042A580", "00158F50", "001DEADC", "001DF658")}.get(name, ())
        missing = [r for r in required if not any(l.split(",")[2].upper() == r for l in lines)]
        if missing:
            sys.exit(f"{name}: required hooks missing: {missing}")
        out += ["", f"[warriors-4p {title}]", "author=warriors-4p", f"description=Experimental: {desc}.", ""] + lines
    # TEST ONLY (M2 engine tests in Mission 1): PickJoinCompanion (FUN_0022A770) skips its gang-wide search in level 99,
    # where player 1's squad holds only players 1 and 2; this lets players 3-4 take over other Warriors there.
    out += ["", "[warriors-4p test level99 join]", "author=warriors-4p", "description=Test only: join search also in level 99.", "",
            "patch=2,EE,0022A85C,word,24047FFF // was 24040063 addiu a0,zero,99 -> 0x7FFF (no such level)"]
    # TEST ONLY: keep SplitAllowed (0x0050B1C0, Lua CamEnable(3, ...)) on, to see every player's view in scripted
    # sections that draw only camera 0 (view_merge_rule.md). Not a session policy (cut-scenes need the shared camera).
    out += ["", "[warriors-4p test force split]", "author=warriors-4p", "description=Test only: views never forced to camera 0.", "",
            "patch=1,EE,0050B1C0,word,00000001 // SplitAllowed"]
    # TEST ONLY (single-instance engine tests): call a game function on the game's main thread right after
    # FrameStats, from a mailbox at 0x000F0300 written over PINE (+0 function, +4..+0x10 a0..a3, +0x14 v0, +0x18 done).
    # As Stage 1 experiment E4 (tests/experiments/E4_extra_player/make_patch_v3.py), without the barrier. Never in
    # online sessions: PINE writes are not part of the lockstep.
    call_cave = """
  addiu sp, sp, -16
  sw ra, 0(sp)
  jal 0x1569c0
  nop
  lui t0, 0x000F
  lw t9, 0x300(t0)
  beq t9, zero, nocall
  nop
  lw a0, 0x304(t0)
  lw a1, 0x308(t0)
  lw a2, 0x30c(t0)
  lw a3, 0x310(t0)
  sw zero, 0x300(t0)
  jalr t9
  nop
  lui t0, 0x000F
  sw v0, 0x314(t0)
  addiu t1, zero, 1
  sw t1, 0x318(t0)
nocall:
  lw ra, 0(sp)
  jr ra
  addiu sp, sp, 16
"""
    cw, _ = assemble(call_cave, 0x000F0000)
    assert 0x000F0000 + 4 * len(cw) <= 0x000F0300
    out += ["", "[warriors-4p test call]", "author=warriors-4p", "description=Test only: call a game function from PINE.", ""]
    out += [f"patch=2,EE,{0x000F0000 + 4 * k:08X},word,{w:08X}" for k, w in enumerate(cw)]
    for site in (0x00158CD0, 0x00159908, 0x0015CA54, 0x0015D270, 0x0015DA8C, 0x0015E44C, 0x0015EFFC):
        out.append(f"patch=2,EE,{site:08X},word,{jal(0x000F0000):08X} // was jal 0x001569C0 (FrameStats)")
    # Online sessions: the same call mailbox for the W4P session layer (LeaveCalls / RestartCalls at an agreed poll;
    # docs/research/m5_disconnect.md). Identical words to the test group, so enabling both is harmless. The fork
    # writes only the configured session calls into it; PINE is not used in sessions.
    out += ["", "[warriors-4p session call]", "author=warriors-4p",
            "description=Online sessions: game calls requested by the W4P session layer (player leave, checkpoint restart).", ""]
    out += [f"patch=2,EE,{0x000F0000 + 4 * k:08X},word,{w:08X}" for k, w in enumerate(cw)]
    for site in (0x00158CD0, 0x00159908, 0x0015CA54, 0x0015D270, 0x0015DA8C, 0x0015E44C, 0x0015EFFC):
        out.append(f"patch=2,EE,{site:08X},word,{jal(0x000F0000):08X} // was jal 0x001569C0 (FrameStats)")
    # PCSX2's own widescreen entry for this game (resources/patches.zip, SLUS-21215_B99A75DE.pnach, by CRASHARKI).
    out += ["", "[warriors-4p widescreen]", "gsaspectratio=16:9", "author=CRASHARKI (PCSX2 patches)",
            "description=Native 16:9 widescreen (copied from PCSX2's patch list).", "",
            "patch=1,EE,007AA05C,byte,01 // was 00"]
    sys.stdout.write("\r\n".join(out) + "\r\n")


if __name__ == "__main__":
    main()

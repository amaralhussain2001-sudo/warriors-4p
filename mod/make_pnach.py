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
    # Decision D8: every player always gets their own view. Uses the game's own option "2P Split Screen Merge"
    # (live flag 0x0050B1C4, setter FUN_00418AC8; docs/research/view_merge_rule.md). The saved option is untouched.
    out += ["", "[warriors-4p own view]", "author=warriors-4p",
            "description=Online sessions: never merge the players' views (game option 2P Split Screen Merge off).", "",
            "patch=1,EE,0050B1C4,word,00000000 // live merge option, was 00000001",
            "patch=2,EE,00418AD4,word,AC40B1C4 // was AC45B1C4 (sw a1): the option setter stores 0"]
    # Each player's radar inside their own quarter of the 2x2 layout (docs/research/hud_layout.md, patches A and B).
    # Only changes layout mode 2, which exists only with the 2x2 layout patch above.
    hud = [(0x001AFF30, 0x0803C180, "was 3C030051 lui v1,0x51 -> j 0x000F0600"),
           (0x001AFF34, 0x00000000, "was C455D430 -> nop (delay slot)"),
           (0x000F0600, 0xC455D430, "lwc1 f21,-0x2bd0(v0): z = default"),
           (0x000F0604, 0x24010002, "addiu at,zero,2"),
           (0x000F0608, 0x14610004, "bne v1,at,+4: not the 2x2 mode"),
           (0x000F060C, 0xC441D434, "lwc1 f1,-0x2bcc(v0): P1 x (delay slot)"),
           (0x000F0610, 0x3C013E19, "lui at,0x3e19"),
           (0x000F0614, 0x3421999A, "ori at,at,0x999a: 0.15"),
           (0x000F0618, 0x4481A800, "mtc1 at,f21: z = 0.15 in the 2x2 mode"),
           (0x000F061C, 0xC454D428, "lwc1 f20,-0x2bd8(v0): P2 x"),
           (0x000F0620, 0x0806BFD2, "j 0x001AFF48"),
           (0x000F0624, 0x4600A886, "mov.s f2,f21 (delay slot)"),
           (0x001AA648, 0x00000000, "was E7A00008 swc1 f0,8(sp): widget keeps the caller's height")]
    out += ["", "[warriors-4p hud]", "author=warriors-4p",
            "description=Online sessions: each player's radar inside their own view (2x2 layout).", ""]
    out += [f"patch=2,EE,{a:08X},word,{w:08X} // {c}" for a, w, c in hud]
    # Decision D9: real 60 fps (docs/research/sixty_fps.md, R60-1..4). Experimental until speed parity is tested.
    out += ["", "[warriors-4p 60fps]", "author=warriors-4p",
            "description=Experimental real 60 fps: flip every vblank, game logic every 1/60 s step, logic time step halved.", "",
            "patch=1,EE,00596D70,byte,01 // R60-1 swap interval 1 (was 2 from 0x0050CDB0)",
            "patch=2,EE,003A2F08,word,3C02004A // R60-2 SimAdvance: one 1/60 s step per pass (was 3C020095)",
            "patch=2,EE,003A2F30,word,3C17004A // R60-2 (was 3C170095)",
            "patch=2,EE,003A2F94,word,2E420001 // R60-2 (was 2E420002)",
            "patch=2,EE,0024912C,word,30640000 // R60-3 SimStep: logic on every step (was 30640001)",
            "patch=2,EE,005102CC,word,3C888889 // R60-4 LogicDt 1/60 (was 3D088889 = 1/30)",
            "patch=2,EE,0023B7C8,word,3C013C88 // R60-4 LogicDt writer (was 3C013D08)",
            "patch=2,EE,0023B7FC,word,3C013C88 // R60-4 (was 3C013D08)",
            "patch=2,EE,0030C8CC,word,3C013C08 // R60-4 (was 3C013C88)",
            "patch=2,EE,0030C924,word,3C013B88 // R60-4 (was 3C013C08)",
            "patch=2,EE,0030C94C,word,3C013C88 // R60-4 (was 3C013D08)",
            "patch=2,EE,0041AB40,word,3C013C88 // R60-4 (was 3C013D08)",
            "patch=2,EE,0041ABA4,word,3C013C88 // R60-4 (was 3C013D08)",
            "patch=2,EE,00249B44,word,3C013C88 // R60-4 camera clamp in SimStep (was 3C013D08)"]
    # PCSX2's own widescreen entry for this game (resources/patches.zip, SLUS-21215_B99A75DE.pnach, by CRASHARKI).
    out += ["", "[warriors-4p widescreen]", "gsaspectratio=16:9", "author=CRASHARKI (PCSX2 patches)",
            "description=Native 16:9 widescreen (copied from PCSX2's patch list).", "",
            "patch=1,EE,007AA05C,byte,01 // was 00"]
    sys.stdout.write("\r\n".join(out) + "\r\n")


if __name__ == "__main__":
    main()

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
    sys.stdout.write("\r\n".join(out) + "\r\n")


if __name__ == "__main__":
    main()

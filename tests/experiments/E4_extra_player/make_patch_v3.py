"""Experiment pnach v3 (Stage 1 only, temporary): v2 + one-shot "call game function" facility, plus a separate
group of E4 limit patches.

Group "warriors4p base v3":
  0x000F0000 barrier cave + call facility (runs right after FrameStats, on the game's main thread, between frames)
     call mailbox 0x000F0300: +0 function address (0 = none), +4..+0x10 a0..a3, +0x14 v0 result, +0x18 done flag
  0x000F0100 barrier mailbox (as v2); 0x000F0200 injection control; 0x000F0400 injection cave; table 0x00098000
Group "warriors4p E4 limits" (what-breaks experiment):
  0x00419B48  slti v0,s0,2 -> slti v0,s0,4     GameMgr::AddPlayer refuses when count >= 2 (F-0060)
  0x0014562C  addiu s4,s4,4 -> 1               controller update loop polls pads 0 and 4 only (F-0055)
  0x00145638  addiu s5,s5,0x140 -> 0x50        (pointer step of the same loop)
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "tools"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "E1_determinism"))
from mips_asm import assemble  # noqa: E402
import make_patch_v2 as v2  # noqa: E402

BARRIER_CALL = """
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
  lui t0, 0x000F
  lw t1, 0x100(t0)
  beq t1, zero, done
  nop
  lui t2, 0x0051
  lw t3, -0x39ac(t2)
  bne t3, t1, done
  nop
  sw t3, 0x104(t0)
spin:
  lw t4, 0x108(t0)
  beq t4, zero, spin
  nop
  sw zero, 0x108(t0)
  sw zero, 0x100(t0)
done:
  lw ra, 0(sp)
  jr ra
  addiu sp, sp, 16
"""

E4_LIMITS = [(0x00419B48, 0x2A020002, 0x2A020004),
             (0x0014562C, 0x26940004, 0x26940001),
             (0x00145638, 0x26B50140, 0x26B50050)]


def main():
    b, _ = assemble(BARRIER_CALL, 0x000F0000)
    assert len(b) * 4 <= 0x100, "barrier cave overlaps the mailbox"
    i, _ = assemble(v2.INJECT, 0x000F0400)
    out = ["gametitle=The Warriors (NTSC-U) (SLUS-21215) - warriors-4p Stage 1 experiments v3", "",
           "[warriors4p base v3]", "author=warriors-4p (Stage 1 experiment, temporary)",
           "description=Barrier, call facility and controller injection. Experiment only.", ""]
    for base, words in ((0x000F0000, b), (0x000F0400, i)):
        for k, w in enumerate(words):
            out.append(f"patch=2,EE,{base + 4 * k:08X},word,{w:08X}")
    for s in v2.FRAMESTATS_SITES:
        out.append(f"patch=2,EE,{s:08X},word,{v2.jal(0x000F0000):08X}")
    out.append(f"patch=2,EE,{v2.PADREAD_SITE:08X},word,{v2.jal(0x000F0400):08X}")
    out += ["", "[warriors4p E4 limits]", "author=warriors-4p (Stage 1 experiment, temporary)",
            "description=Raise GameMgr player limit to 4 and poll all 8 pads (what-breaks test).", ""]
    for addr, old, new in E4_LIMITS:
        out.append(f"patch=2,EE,{addr:08X},word,{new:08X} // was {old:08X}")
    sys.stdout.write("\r\n".join(out) + "\r\n")


if __name__ == "__main__":
    main()

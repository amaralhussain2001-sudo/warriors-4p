"""E1/E3 experiment pnach v2: frame barrier + frame-exact controller injection (Stage 1 only, temporary).

Memory map (RAM observed all-zero during gameplay, F-0050):
  0x000F0000  barrier cave (calls FrameStats 0x001569C0, then waits when frame == target)
  0x000F0100  mailbox: +0 target frame, +4 reached frame, +8 release flag
  0x000F0200  injection control: +0 pad mask (bit = pad index port*4+slot), +4 base frame, +8 frame count
  0x000F0400  injection cave (wraps the libpad read 0x00149770 called at 0x001498E0)
  0x00098000  input table: frame-major, 8 pads x 8 bytes: u16 buttons (game codes), u8 rx, ry, lx, ly, pad[2]
Hooks: 7 FrameStats call sites -> barrier cave; 0x001498E0 (jal 0x00149770) -> injection cave.
The per-pad buffer fields overwritten (offsets from the port buffer at 0x005DE3C0 + idx*0x140):
  +0x10C connected, +0x110 rx, +0x111 ry, +0x112 lx, +0x113 ly, +0x114 buttons  (F-0051)
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "tools"))
from mips_asm import assemble  # noqa: E402

FRAMESTATS_SITES = [0x00158CD0, 0x00159908, 0x0015CA54, 0x0015D270, 0x0015DA8C, 0x0015E44C, 0x0015EFFC]
PADREAD_SITE = 0x001498E0

BARRIER = """
  addiu sp, sp, -16
  sw ra, 0(sp)
  jal 0x1569c0
  nop
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

INJECT = """
  addiu sp, sp, -32
  sw ra, 0(sp)
  sw a0, 4(sp)
  jal 0x149770
  nop
  lw a0, 4(sp)
  lui t0, 0x000F
  lw t1, 0x200(t0)
  beq t1, zero, out
  nop
  lw t2, 0x104(a0)
  lw t3, 0x108(a0)
  sll t2, t2, 2
  addu t3, t2, t3
  srlv t5, t1, t3
  andi t5, t5, 1
  beq t5, zero, out
  nop
  lui t6, 0x0051
  lw t6, -0x39ac(t6)
  lw t7, 0x204(t0)
  subu t6, t6, t7
  bltz t6, out
  nop
  lw t7, 0x208(t0)
  sltu t8, t6, t7
  beq t8, zero, out
  nop
  sll t6, t6, 6
  sll t3, t3, 3
  addu t6, t6, t3
  lui t7, 0x0009
  ori t7, t7, 0x8000
  addu t6, t6, t7
  lhu t8, 0(t6)
  sh t8, 0x114(a0)
  lbu t8, 2(t6)
  sb t8, 0x110(a0)
  lbu t8, 3(t6)
  sb t8, 0x111(a0)
  lbu t8, 4(t6)
  sb t8, 0x112(a0)
  lbu t8, 5(t6)
  sb t8, 0x113(a0)
  addiu t8, zero, 1
  sw t8, 0x10c(a0)
out:
  lw ra, 0(sp)
  jr ra
  addiu sp, sp, 32
"""


def jal(t):
    return 0x0C000000 | (t >> 2)


def main():
    b, _ = assemble(BARRIER, 0x000F0000)
    i, _ = assemble(INJECT, 0x000F0400)
    out = ["gametitle=The Warriors (NTSC-U) (SLUS-21215) - warriors-4p Stage 1 experiments E1/E3", "",
           "[warriors4p E1 barrier+inject]", "author=warriors-4p (Stage 1 experiment, temporary)",
           "description=Frame barrier and frame-exact controller injection. Experiment only, not the mod.", ""]
    for base, words in ((0x000F0000, b), (0x000F0400, i)):
        for k, w in enumerate(words):
            out.append(f"patch=2,EE,{base + 4 * k:08X},word,{w:08X}")
    for s in FRAMESTATS_SITES:
        out.append(f"patch=2,EE,{s:08X},word,{jal(0x000F0000):08X}")
    out.append(f"patch=2,EE,{PADREAD_SITE:08X},word,{jal(0x000F0400):08X}")
    sys.stdout.write("\r\n".join(out) + "\r\n")


if __name__ == "__main__":
    main()

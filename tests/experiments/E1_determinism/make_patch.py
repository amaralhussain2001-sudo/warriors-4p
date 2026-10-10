"""Generate the temporary E1 frame-barrier pnach for SLUS-21215 v1.03 (Stage 1 experiment only).

Cave at 0x000F0000 (RAM observed all-zero during gameplay, F-0050). Mailbox:
  0x000F0100 target frame (0 = disabled)   0x000F0104 reached frame   0x000F0108 release flag
Hooks: all 7 call sites of FrameStats (0x001569C0) call the cave instead; the cave calls FrameStats.
"""
import sys

CAVE = 0x000F0000
# every call site of FrameStats (jal 0x001569C0) in the ELF, verified by byte search
HOOKS = [0x00158CD0, 0x00159908, 0x0015CA54, 0x0015D270, 0x0015DA8C, 0x0015E44C, 0x0015EFFC]
FRAMESTATS = 0x001569C0


def jal(t):
    return 0x0C000000 | (t >> 2)


code = [
    0x27BDFFF0,        # addiu sp, sp, -16
    0xAFBF0000,        # sw    ra, 0(sp)
    jal(FRAMESTATS),   # jal   FrameStats      (original call; bumps frame counter 0x0050C654)
    0x00000000,        # nop
    0x3C08000F,        # lui   t0, 0x000F
    0x8D090100,        # lw    t1, 0x100(t0)   target
    0x1120000B,        # beq   t1, zero, done
    0x00000000,        # nop
    0x3C0A0051,        # lui   t2, 0x0051
    0x8D4BC654,        # lw    t3, -0x39AC(t2) frame counter @ 0x0050C654
    0x15690007,        # bne   t3, t1, done
    0x00000000,        # nop
    0xAD0B0104,        # sw    t3, 0x104(t0)   reached
    0x8D0C0108,        # spin: lw t4, 0x108(t0)
    0x1180FFFE,        # beq   t4, zero, spin
    0x00000000,        # nop
    0xAD000108,        # sw    zero, 0x108(t0)
    0xAD000100,        # sw    zero, 0x100(t0)
    0x8FBF0000,        # done: lw ra, 0(sp)
    0x03E00008,        # jr    ra
    0x27BD0010,        # addiu sp, sp, 16
]


def main():
    out = ["gametitle=The Warriors (NTSC-U) (SLUS-21215) - warriors-4p Stage 1 experiment E1", "",
           "[warriors4p E1 barrier]", "author=warriors-4p (Stage 1 experiment, temporary)",
           "description=Frame barrier code cave for determinism experiment E1. Not part of the mod.", ""]
    for i, w in enumerate(code):
        out.append(f"patch=2,EE,{CAVE + 4 * i:08X},word,{w:08X}")
    for h in HOOKS:
        out.append(f"patch=2,EE,{h:08X},word,{jal(CAVE):08X}")
    sys.stdout.write("\r\n".join(out) + "\r\n")


if __name__ == "__main__":
    main()

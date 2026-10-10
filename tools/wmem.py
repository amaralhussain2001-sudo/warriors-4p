"""Read The Warriors (SLUS-21215 v1.03) runtime structures through PINE.

All offsets are OUR labels from static analysis (docs/FINDINGS.md); the ELF has no symbols.
  0x0051489c  ptr to game manager (label: GameMgr), dynamic heap object
  GameMgr+0x224  s16  player slot count            (F-0020)
  GameMgr+0x228  u32[] player human handles        (F-0020)
  GameMgr+0x56e8 u32  multiplayer-join allowed     (F-0021)
  handle -> object: idx = handle>>16, gen = handle&0xffff,
     ptr = *(0x006ebd38 + idx*8), valid if *(s16*)(0x006ebd3c + idx*8) == gen   (F-0022)
  Human+0x1b0 s8 player index, -1 if AI          (F-0023)

Usage: python -I tools/wmem.py <pine_slot> players
"""
import struct
import sys

sys.path.insert(0, __import__("os").path.dirname(__file__))
from pine import Pine  # noqa: E402


def resolve(p, h):
    if h == 0xFFFFFFFF:
        return 0
    idx, gen = h >> 16, h & 0xFFFF
    if gen == 0:
        return None  # indirect handle, not handled here
    g = p.read32(0x006EBD3C + idx * 8) & 0xFFFF
    return p.read32(0x006EBD38 + idx * 8) if g == gen else 0


def players(p):
    mgr = p.read32(0x0051489C)
    n = struct.unpack("<h", struct.pack("<H", p.read32(mgr + 0x224) & 0xFFFF))[0]
    print(f"GameMgr={mgr:08x} slots={n} joinAllowed={p.read32(mgr + 0x56E8)} state158={p.read32(mgr + 0x158)}")
    for i in range(4):
        h = p.read32(mgr + 0x228 + 4 * i)
        obj = resolve(p, h)
        extra = ""
        if obj:
            b = p.read32(obj + 0x1B0) & 0xFF
            extra = f" obj={obj:08x} playerIdx={b if b < 128 else b - 256} f380={p.read32(obj + 0x380):08x}"
        print(f"  slot{i}: handle={h:08x}{extra}")


if __name__ == "__main__":
    pp = Pine(int(sys.argv[1]))
    if sys.argv[2] == "players":
        players(pp)

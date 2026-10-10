"""Print controller-related state from an E1 RAM dump pair (local/e1/<tag>/inst2.bin, inst3.bin)."""
import os
import struct
import sys

PROJ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
tag = sys.argv[1]
for name in ("inst2", "inst3"):
    m = open(os.path.join(PROJ, "local", "e1", tag, name + ".bin"), "rb").read()
    ctrl = struct.unpack_from("<3I", m, 0xF0200)
    pad = 0x5DD810
    ring = struct.unpack_from("<8H", m, pad + 0x1C)
    idx = struct.unpack_from("<I", m, pad + 0x2C)[0]
    fl = struct.unpack_from("<4f", m, pad + 0x8)
    portbuf = m[0x5DE3C0 + 0x10C: 0x5DE3C0 + 0x118].hex()
    print(name, "ctrl(mask,base,count)", ctrl, "frame", struct.unpack_from("<I", m, 0x50C654)[0],
          "ring", [hex(x) for x in ring], "idx", idx, "stick floats", [round(x, 2) for x in fl],
          "portbuf+10c..117", portbuf, "pad+4c", struct.unpack_from("<I", m, pad + 0x4C)[0],
          "pad+42", struct.unpack_from("<h", m, pad + 0x42)[0], "pad+44", struct.unpack_from("<h", m, pad + 0x44)[0])

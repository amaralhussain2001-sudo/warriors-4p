"""Views/cameras when players go down (m2_fx34.md addendum 1): active camera per player (0x000F0800 + 4*i, our
4-entry table), each camera's +0x1D6 byte, view/camera counts 0x0050B198/0x0050B19C, flags 0x0050B1D8, per-player
flag array 0x0050B1E8. Used by nav_probe.py --probe."""


def cams(p):
    out = {"poll": p.read32(0x000F0500), "views": p.read32(0x0050B198), "cameras": p.read32(0x0050B19C),
           "b1d8": hex(p.read32(0x0050B1D8)), "b1e8": [hex(p.read32(0x0050B1E8)), hex(p.read32(0x0050B1EC))], "cam": []}
    for i in range(4):
        c = p.read32(0x000F0800 + 4 * i)
        if 0x00100000 <= c < 0x02000000:
            w = p.read32(c + 0x1D4)
            out["cam"].append({"ptr": hex(c), "b1d6": (w >> 16) & 0xFF, "vt": hex(p.read32(c))})
        else:
            out["cam"].append({"ptr": hex(c)})
    gm = p.read32(0x0051489C)
    out["players"] = [hex(p.read32(gm + 0x228 + 4 * i)) for i in range(4)]
    return out

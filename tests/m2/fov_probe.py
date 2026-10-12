"""Read-only: field of view and view window of the render cameras (relocated table 0x000F0810 + 4*i, F-0098 /
m2_views34.md: float cam+0x44 = FOV, cam+0x64 / cam+0x68 = view window), views 0x0050B198, layout mode 0x0050B1A4,
the LayoutViewports scale 0x0050B200, and player 1's position. Used to compare a single view with the 2x2 layout
(user report 2026-10-12: "the cut picture feels zoomed in"). nav_probe.py --probe fov_probe:read:<poll>."""
import struct


def _f(p, a):
    return round(struct.unpack("<f", struct.pack("<I", p.read32(a)))[0], 5)


def read(p):
    out = {"poll": p.read32(0x000F0500), "views": p.read32(0x0050B198), "mode": p.read32(0x0050B1A4),
           "scale_b200": _f(p, 0x0050B200), "cams": []}
    for i in range(4):
        c = p.read32(0x000F0810 + 4 * i)
        if 0x00100000 <= c < 0x02000000:
            out["cams"].append({"i": i, "cam": hex(c), "fov44": _f(p, c + 0x44), "win64": _f(p, c + 0x64),
                                "win68": _f(p, c + 0x68), "w40": _f(p, c + 0x40), "w48": _f(p, c + 0x48)})
        else:
            out["cams"].append({"i": i, "cam": hex(c)})
    gm = p.read32(0x0051489C)
    h = p.read32(gm + 0x228) if 0x00100000 <= gm < 0x02000000 else 0
    out["p1_handle"] = hex(h)
    return out

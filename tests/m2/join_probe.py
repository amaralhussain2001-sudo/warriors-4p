"""Player count and handles (GameMgr+0x224/+0x228) for join calibration. Used by nav_probe.py --probe."""


def players(p):
    gm = p.read32(0x0051489C)
    return {"poll": p.read32(0x000F0500), "count": p.read32(gm + 0x224) & 0xFFFF,
            "handles": [hex(p.read32(gm + 0x228 + 4 * i)) for i in range(4)], "join_allowed": p.read32(gm + 0x56E8) & 0xFF}

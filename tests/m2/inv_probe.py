"""Inventory reads for players 3-4 (docs/research/m2_inventory34.md section 9). Used by nav_probe.py --probe.

Inv = GameMgr+0x480; count of item k for slot s = Inv+0x24+s*0x3F4+k*0x2C; name of item k = Inv+0x04+s*0x3F4+k*0x2C;
checkpoint copy (with the fragment) at 0x000E4000+s*0x3F4; bank = Inv+0. Items: 1 Flash, 2 money, 3 spray, 6 key.
"""

ITEMS = {1: "flash", 2: "money", 3: "spray", 6: "key"}


def _name(p, a):
    raw = b"".join(p.read32(a + 4 * i).to_bytes(4, "little") for i in range(4))
    return raw.split(b"\0")[0].decode("latin-1")


def inventory(p):
    gm = p.read32(0x0051489C)
    inv = gm + 0x480
    out = {"poll": p.read32(0x000F0500), "bank": p.read32(inv), "slots": {}, "copy": {}, "players": []}
    for s in range(4):
        base = inv + 0x04 + s * 0x3F4
        out["slots"][s] = {ITEMS[k]: p.read32(inv + 0x24 + s * 0x3F4 + k * 0x2C) for k in ITEMS}
        out["slots"][s]["flash_name"] = _name(p, base + 1 * 0x2C)
        out["copy"][s] = {ITEMS[k]: p.read32(0x000E4020 + s * 0x3F4 + k * 0x2C) for k in ITEMS}
    for i in range(4):
        h = p.read32(gm + 0x228 + 4 * i)
        o = 0
        if h not in (0, 0xFFFFFFFF):
            idx = (h >> 16) & 0xFFFF
            if p.read32(0x006EBD38 + 8 * idx + 4) & 0xFFFF == h & 0xFFFF:
                o = p.read32(0x006EBD38 + 8 * idx)
        if o:
            st = p.read32(o + 0xD4)
            hp = p.read32(st + 0x144) & 0xFFFF if 0x00100000 <= st < 0x02000000 else None
            b = p.read32(o + 0x1B0) & 0xFF
            out["players"].append({"handle": hex(h), "pidx": b - 256 if b & 0x80 else b, "hud_slot": p.read32(o + 0x380), "hp": hp})
        else:
            out["players"].append(None)
    out["fx_mirror"] = [hex(p.read32(0x000F0890 + 4 * i)) for i in range(4)]
    return out

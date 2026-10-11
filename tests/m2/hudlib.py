"""R5 diagnosis for the duplicate nameless panel (m2_hud_full.md addendum 2, C5). Used by nav_probe.py --hud-diag.

Reads the per-view sprite clone table at 0x000E0A60 (entries of 5 words: original item, copies for views 0-3; 0 ends),
the state of every item in it (u8 +0x11 active, u8 +0x42 view, u32 +0x18 capacity, u32 +0x1C quads this frame,
u32 +0x04 packet), CUR (0x000E0010), the number of used sprite slots and the font sprite of PlayerHUD 0's texts.
"""
import struct

SPRITE_MGR_PTR = 0x0050CD4C
ITEM0, ITEM_SIZE, ITEMS = 0x189C, 0x78, 255
TABLE, CUR = 0x000E0A60, 0x000E0010


def diag(pine):
    mgr = pine.read32(SPRITE_MGR_PTR)
    table = [pine.read32(TABLE + 4 * i) for i in range(12)]
    row = {"poll": pine.read32(0x000F0500), "mgr": hex(mgr), "cur": hex(pine.read32(CUR)),
           "table": [hex(v) for v in table], "items": []}
    blob = pine.dump(mgr + ITEM0, ITEMS * ITEM_SIZE) if mgr else b""
    for it in table:
        if not it:
            continue
        h = (it - mgr - ITEM0) // ITEM_SIZE if mgr else -1
        rec = blob[h * ITEM_SIZE:(h + 1) * ITEM_SIZE] if 0 <= h < ITEMS else b""
        if len(rec) == ITEM_SIZE:
            row["items"].append({"item": hex(it), "handle": h, "active_11": rec[0x11], "view_42": rec[0x42],
                                 "cap_18": struct.unpack_from("<I", rec, 0x18)[0], "count_1c": struct.unpack_from("<I", rec, 0x1C)[0],
                                 "pkt_04": hex(struct.unpack_from("<I", rec, 0x04)[0])})
        else:
            row["items"].append({"item": hex(it), "handle": h, "outside_manager": True})
    row["slots_used"] = sum(1 for i in range(ITEMS) if blob and blob[i * ITEM_SIZE + 0x40] != 0)
    row["phud0_text_fonts"] = [pine.read32(0x00619970 + off + 0xA0) for off in (0x2A0, 0xE70, 0x12A0, 0x16D0, 0x1B00)]
    return row

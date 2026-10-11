"""Read-only survey for the spawn chooser (docs/research/m2_spawn_name.md section 8, test T0): which named Warriors
have their model resident in the current level and which are already present. Used by nav_probe.py --probe."""


def survey(p):
    r32 = p.read32

    def r16(a):
        return (r32(a & ~3) >> (8 * (a & 2))) & 0xFFFF

    def s16(x):
        return x - 0x10000 if x & 0x8000 else x

    def found(tree, key):  # FUN_004DE458/8D0/BE8: lower_bound on node+0x10, header = *(tree+4)
        head = r32(tree + 4)
        node, best = r32(head + 4), head
        while node:
            if r32(node + 0x10) < key:
                node = r32(node + 0xC)
            else:
                best, node = node, r32(node + 8)
        return best != head and not key < r32(best + 0x10)

    hud = {}  # FUN_00229570 jump table (m2_spawn_name.md section 1.2)
    for idx, ids in {0: [5, 7, 8, 9, 10], 1: [15, 17], 2: [18, 20, 188], 3: [11, 13, 14], 4: [30, 32], 5: [21, 23, 24, 25],
                     6: [26, 28, 29, 191], 7: [33, 35, 36, 37, 190], 8: [1, 3, 4, 189], 9: [38, 39, 40], 10: [43, 44],
                     11: [45, 46, 47, 48]}.items():
        for i in ids:
            hud[i] = idx
    g = r32(0x0051489C)
    level = r32(g + 0x14D8 + r16(g + 0x56DC) * 0x84)
    off = 0x114 if 0 <= level - 60 < 5 else 0x112
    d = r32(0x0050CD4C)
    count, entries = r32(d + 0x84), r32(d + 0x88)
    live = {s: r32(0x006EBD38 + 8 * s) for s in range(60)}
    present = {hud.get(r32(h + 0xCC), "other") for h in live.values() if h}
    out = {"level": level, "field": hex(off), "dict": hex(d), "dict_count": count,
           "warrior_hud_present": sorted(x for x in present if x != "other"), "candidates": {}}
    for cid, name in [(5, "Swan"), (11, "Ajax"), (33, "Snow"), (15, "Cochise"), (26, "Vermin"), (21, "Fox"),
                      (30, "Rembrandt"), (1, "Cleon"), (18, "Cowboy"), (2, "Cleon gen")]:
        e = 0x00684620 + cid * 0x1AC
        hp, m = s16(r16(e + 0x116)), r16(e + off)
        if hp <= 0:
            st = "1 not configured"
        elif m >= count:
            st = f"2 no model index ({m:#x})"
        else:
            ent = entries + m * 0x20
            ok = found(d + 0x40, r32(ent + 4)) and found(d + 0x30, r32(ent + 0xC)) and found(d, r32(ent + 8))
            st = "3 not resident" if not ok else ("4 present" if hud.get(cid) in present else "eligible")
        out["candidates"][name] = {"char": cid, "hud": hud.get(cid), "model": hex(m), "status": st}
    out["choose_result"] = hex(r32(0x000E15F0))
    return out

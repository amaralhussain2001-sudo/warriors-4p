"""Which character each player is (docs/research/m2_extra_model.md test X1): per player the base char id +0xCC (selects
the HUD name, m2_spawn_name.md 1.2), the original id +0xD0, the model index +0x37C, the model instance +0xD8, the
player index +0x1B0, the W4P marker +0x1B1 (7 = spawned by SPAWN) and the HUD slot +0x380; plus the extra-model words
0x000E1C00-0x000E1C4B and the CHOOSE result/statuses. Read-only; used by nav_probe.py --probe p4_identity:ident:<poll>."""


def _r16(p, a):
    return (p.read32(a & ~3) >> (8 * (a & 2))) & 0xFFFF


def _r8(p, a):
    return (p.read32(a & ~3) >> (8 * (a & 3))) & 0xFF


def ident(p):
    gm = p.read32(0x0051489C)
    out = {"poll": p.read32(0x000F0500), "players": p.read32(gm + 0x224) & 0xFFFF, "player": []}
    for i in range(4):
        h = p.read32(gm + 0x228 + 4 * i)
        row = {"handle": hex(h)}
        if h not in (0, 0xFFFFFFFF):
            e = 0x006EBD38 + 8 * (h >> 16)
            hu = p.read32(e)
            if hu and _r16(p, e + 4) == (h & 0xFFFF):
                row.update({"cc": p.read32(hu + 0xCC), "d0": p.read32(hu + 0xD0), "model_index": _r16(p, hu + 0x37C),
                            "instance_d8": hex(p.read32(hu + 0xD8)), "index": _r8(p, hu + 0x1B0),
                            "marker": _r8(p, hu + 0x1B1), "hud_slot": p.read32(hu + 0x380)})
        out["player"].append(row)
    names = ["PIN_ID", "PIN_OWN", "PIN_MI", "PIN_T0", "EN_LAST", "GT_LAST", "GT_T", "POKE_RES", "N_PIN", "N_REFUSE",
             "N_TIMEOUT", "N_RELEASE", "N_POKE", "NOFIT", "N_NOFIT", "_3C", "TIMEOUT_MS", "PRELOAD_AT3", "POKE_EN"]
    out["extra"] = {n: p.read32(0x000E1C00 + 4 * k) for k, n in enumerate(names)}
    out["choose"] = {"result": p.read32(0x000E15F0), "status": [p.read32(0x000E15C0 + 4 * k) for k in range(9)],
                     "spawned_handle": hex(p.read32(0x000E1210))}
    return out


def force_panels(p):
    """Test aid (m2_hud_full.md addendum: ForceShowPlayerHud): keep all four health/name panels on screen by writing
    1 to +0x4104 of each PlayerHUD from the 4-entry table T_A 0x000E0848 (B1)."""
    out = []
    for slot in range(4):
        hud = p.read32(0x000E0848 + 4 * slot)
        if hud:
            p.write32(hud + 0x4104, 1)
        out.append(hex(hud))
    return {"poll": p.read32(0x000F0500), "huds": out}

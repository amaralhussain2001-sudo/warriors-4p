"""Probes for the added-Warrior chooser (docs/research/m6_chooser.md): XC exclusion table, two model pin slots,
X7 (b) starting items after a forced leave. Used by nav_probe.py --probe chooser_probe:<function>:<poll>
(one instance, SINGLE-PC, scripted input, test only). Read-only except the test aid x2_fox_row_off (m6fix_probe).
Static addresses, SLUS-21215 v1.03; names are OUR labels (stripped ELF).
"""
import inv_tests as T
import m6fix_probe as F

SLOT = (0x000E1C00, 0x000E1C50)       # pin slot k: ID, OWN, MI, T0
DICT_PTR = 0x0050CD4C
CHAR_TABLE = 0x00684620
NAMES = {5: "Swan", 11: "Ajax", 33: "Snow", 15: "Cochise", 26: "Vermin", 21: "Fox", 30: "Rembrandt", 1: "Cleon",
         18: "Cowboy"}
CODES = ["EN_LAST", "GT_LAST", "GT_T", "POKE_RES", "N_PIN", "N_REFUSE", "N_TIMEOUT", "N_RELEASE", "N_POKE", "NOFIT",
         "N_NOFIT", "EN_SLOT", "TIMEOUT_MS", "PRELOAD_AT3", "POKE_EN", "OWN3"]


def _pinlist(p):
    d = p.read32(DICT_PTR)
    if not d:
        return []
    out = []
    for i in range(32):
        mi = p.read32(d + 0xB4 + 8 * i)
        if mi != 0xFFFFFFFF:
            out.append((i, mi, hex(p.read32(d + 0xB8 + 8 * i))))
    return out


def state(p):
    """Players (char ids, model index, model instance +0xD8, marker, HUD slot), pin slots with their game pin-list entry
    and instance, ENSURE/GATE codes and counters, CHOOSE result/statuses, X7 bytes, inventory of slots 0-3."""
    gm = p.read32(F.GM_PTR)
    pins = _pinlist(p)
    players = []
    for i in range(4):
        h, o = T._player(p, i)
        if o:
            players.append({"i": i, "handle": hex(h), "d0": p.read32(o + 0xD0), "cc": p.read32(o + 0xCC),
                            "name": NAMES.get(p.read32(o + 0xCC)), "mi_37c": T._r16(p, o + 0x37C),
                            "inst_d8": hex(p.read32(o + 0xD8)), "marker": T._r8(p, o + 0x1B1),
                            "pidx": F._s8(T._r8(p, o + 0x1B0)), "hud_slot": T._s32(p.read32(o + 0x380))})
        else:
            players.append({"i": i, "handle": hex(h)})
    slots = []
    for k, b in enumerate(SLOT):
        sid, own, mi, t0 = (p.read32(b + 4 * j) for j in range(4))
        ent = [x for x in pins if x[1] == mi] if sid else []
        slots.append({"k": k, "id": sid, "name": NAMES.get(sid), "own": own, "mi": mi, "t0": t0,
                      "in_pin_list": bool(ent), "instance": ent[0][2] if ent else None})
    codes = {n: p.read32(0x000E1C10 + 4 * j) for j, n in enumerate(CODES[:11])}
    codes.update({"EN_SLOT": p.read32(0x000E1C3C), "TIMEOUT_MS": p.read32(0x000E1C40), "PRELOAD_AT3": p.read32(0x000E1C44),
                  "POKE_EN": p.read32(0x000E1C48), "OWN3": p.read32(0x000E1C4C),
                  "KICK_MS": p.read32(0x000E2300), "KICK_T": p.read32(0x000E2304), "N_KICK": p.read32(0x000E2308),
                  "SVC_T": p.read32(0x000E230C), "N_FIX": p.read32(0x000E2310)})
    return {"poll": T._poll(p), "level_cp": F._level(p), "count": F._s16(p.read32(gm + 0x224)), "players": players,
            "slots": slots, "codes": codes, "pin_list": pins,
            "choose": {"result": p.read32(0x000E15F0), "status": [p.read32(0x000E15C0 + 4 * k) for k in range(9)]},
            "x7_bytes": [T._r8(p, 0x000E7780 + k) for k in range(4)], "inv": T._all_counts(p),
            "pads": T._pads(p), "views": p.read32(0x0050B198), "clock_ms": p.read32(p.read32(0x0050B734) + 0x38)}


def brief(p):
    """Compact line: count, (index, char, marker, instance) per player, slot ids/instances, codes, X7 bytes, spray 2-3."""
    s = state(p)
    return {"poll": s["poll"], "lcp": s["level_cp"], "count": s["count"],
            "pl": [[x["i"], x.get("d0"), x.get("marker"), x.get("inst_d8"), x.get("hud_slot")] for x in s["players"]],
            "slots": [[x["id"], x["own"], x["in_pin_list"], x["instance"]] for x in s["slots"]],
            "en_gt": [s["codes"]["EN_LAST"], s["codes"]["GT_LAST"], s["codes"]["N_PIN"], s["codes"]["N_REFUSE"],
                      s["codes"]["N_RELEASE"], s["codes"]["NOFIT"], s["codes"]["N_TIMEOUT"]],
            "choose": [s["choose"]["result"], s["choose"]["status"]], "x7": s["x7_bytes"][2:],
            "spray23": [s["inv"][2]["spray"], s["inv"][3]["spray"]], "pads": s["pads"], "views": s["views"]}


def x2_fox_row_off(p):
    """Test aid (as in m6x1b): X2's level9 Fox row -> level99, so player 3 takes Fox and the script's HuDelete(fox)
    hits a player. The CHOOSE XC table (0x000E1E10) is separate and keeps Fox excluded in level9 cp <= 2."""
    return F.x2_fox_row_off(p)


def tele_cut2(p):
    return F.tele_cut2(p)


def tele_arrive(p):
    return F.tele_arrive(p)

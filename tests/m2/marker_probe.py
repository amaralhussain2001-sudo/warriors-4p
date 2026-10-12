"""Overhead markers / radar / map with 4 players (docs/research/m6_markers_map.md). Read-only PINE probe for
nav_probe.py --probe tests/m2 module: marker_probe:snap:<poll>.

Reads, per player slot 0-3: handle GameMgr+0x228+4*i, human object, position (+0x10/+0x14/+0x18), player index byte
+0x1B0, effect handle +0x360 (the "dyn_p_one/two" label effect of FUN_0024B2A8; 0x006EBD30 = no effect);
views/cameras/layout mode; the marker globals 0x00510530..0x00510560; the HUD 3D sprite table entries 8-14
(*(0x0050CD4C) + 0x189C + i*0x78: +0x0C texture, +0x10/+0x11 flags, +0x1C count, +0x28 flags, +0x40 valid, +0x42 view);
render cameras 0x000F0810+4*i. Our labels; build SLUS-21215 v1.03."""
import struct


def _f(v):
    return round(struct.unpack("<f", struct.pack("<I", v & 0xFFFFFFFF))[0], 3)


def _resolve(p, h):
    if h in (0, 0xFFFFFFFF):
        return 0
    return p.read32(0x006EBD38 + 8 * ((h >> 16) & 0xFFFF))


def snap(p):
    gm = p.read32(0x0051489C)
    out = {"poll": p.read32(0x000F0500), "views": p.read32(0x0050B198), "cameras": p.read32(0x0050B19C),
           "layout": p.read32(0x0050B1A4), "count": p.read32(gm + 0x224) & 0xFFFF,
           "null_handle": hex(p.read32(0x006EBD30)), "players": []}
    for i in range(4):
        h = p.read32(gm + 0x228 + 4 * i)
        o = _resolve(p, h)
        row = {"slot": i, "handle": hex(h), "human": hex(o)}
        if 0x00100000 <= o < 0x02000000:
            b = p.read32(o + 0x1B0)
            row.update(pos=[_f(p.read32(o + 0x10 + 4 * k)) for k in range(3)],
                       pidx=(b & 0xFF) - 256 if b & 0x80 else b & 0xFF, fx360=hex(p.read32(o + 0x360)),
                       f19b=p.read32(o + 0x19B * 4), f36=hex(p.read32(o + 0x36 * 4)))
        out["players"].append(row)
    out["globals"] = {hex(a): hex(p.read32(a)) for a in (0x005104F8, 0x00510500, 0x00510518, 0x00510520, 0x00510530,
                                                          0x00510534, 0x00510538, 0x0051053C, 0x00510540, 0x00510544,
                                                          0x00510548, 0x0051054C, 0x00510558, 0x0051055C, 0x006C72C8,
                                                          0x006C72CC, 0x006C72D0, 0x006C7308, 0x006C7310, 0x00617FE0)}
    base = p.read32(0x0050CD4C)
    out["sprite_table"] = hex(base)
    ents = []
    if 0x00100000 <= base < 0x02000000:
        for i in range(0, 16):
            e = base + 0x189C + i * 0x78
            w = [p.read32(e + 4 * k) for k in range(0x78 // 4)]
            b = lambda off: (w[off // 4] >> (8 * (off % 4))) & 0xFF  # noqa: E731
            ents.append({"i": i, "addr": hex(e), "tex": hex(w[3]), "b10": b(0x10), "b11": b(0x11), "b13": b(0x13),
                         "count1c": w[7], "flags28": hex(w[10]), "valid40": b(0x40), "view42": b(0x42),
                         "w": [hex(x) for x in w]})
    out["entries"] = ents
    out["render_cams"] = [hex(p.read32(0x000F0810 + 4 * i)) for i in range(4)]
    return out


def humans(p):
    """Every human object with a player index or a non-null effect handle +0x360 (label effects left behind)."""
    nullh = p.read32(0x006EBD30)
    rows = []
    for k in range(-40, 160):
        o = 0x00640C80 + k * 0x6D0
        if not (0x00597200 <= o and o + 0x6D0 <= 0x00715B5C):
            continue
        b = p.read32(o + 0x1B0)
        fx = p.read32(o + 0x360)
        pidx = (b & 0xFF) - 256 if b & 0x80 else b & 0xFF
        if pidx != -1 or fx not in (nullh, 0):
            rows.append({"human": hex(o), "pidx": pidx, "fx360": hex(fx),
                         "pos": [_f(p.read32(o + 0x10 + 4 * j)) for j in range(3)]})
    return {"poll": p.read32(0x000F0500), "null_handle": hex(nullh), "rows": rows[:60]}


def both(p):
    out = snap(p)
    out["humans"] = humans(p)
    return out


RADARS = {"r1": 0x00601E10, "r2": 0x00604750, "r3": 0x000A9500, "r4": 0x000ABE40}  # HUD+0x15D0, HUD+0x3F10, B1


def _res(p, h):
    """Handle -> object (FUN_00390180 for non-zero serials): table 0x006EBD38 + 8*(h>>16), serial check +4."""
    if h in (0, 0xFFFFFFFF) or (h & 0xFFFF) == 0:
        return 0
    i = (h >> 16) & 0xFFFF
    if (p.read32(0x006EBD3C + 8 * i) & 0xFFFF) != (h & 0xFFFF):
        return 0
    return p.read32(0x006EBD38 + 8 * i)


def _spr(p, idx):
    base = p.read32(0x0050CD4C)
    return base + 0x189C + (idx & 0xFFFF) * 0x78


def radars(p):
    """Radar blip tables (128 entries at +0x920, stride 0x40; +0x930 handle, +0x934 colour, +0x938 icon, +0x944 dot
    effect handle, +0x948 widget, +0x94C type, +0x951 active) and, per blip, the HUD widget's view tag (+0xF9), sprite
    index (+0xC4), frame (+0xC8), colour (+0xB4) and the sprite item's view byte (+0x42); for dot effects the sprite
    index (+0xB2) and that item's view byte."""
    out = {"poll": p.read32(0x000F0500), "views": p.read32(0x0050B198)}
    for name, r in RADARS.items():
        hdr = [p.read32(r + 4 * k) for k in range(6)]
        rr = {"hdr": [hex(x) for x in hdr], "index": p.read32(r + 0x90), "pos2930": [_f(p.read32(r + 0x2930 + 4 * k)) for k in range(4)],
              "blips": []}
        for k in range(128):
            e = r + 0x920 + k * 0x40
            w = [p.read32(e + 4 * j) for j in range(16)]
            active = (w[12] >> 8) & 0xFF  # +0x951 (word +0x950)
            if not active:
                continue
            typ = w[11] & 0xFFFF  # +0x94C
            b = {"k": k, "type": typ, "handle": hex(w[4]), "col934": hex(w[5]), "icon938": hex(w[6]), "fx944": hex(w[9]),
                 "widget": hex(w[10]), "pos920": [_f(w[j]) for j in range(4)]}
            o = _res(p, w[4])
            if 0x00100000 <= o < 0x02000000:
                pb = p.read32(o + 0x1B0) & 0xFF
                b["pidx"] = pb - 256 if pb & 0x80 else pb
            wid = w[10]
            if 0x00080000 <= wid < 0x02000000:
                f8 = p.read32(wid + 0xF8)
                c4 = p.read32(wid + 0xC4)
                b.update(w_f9=(f8 >> 8) & 0xFF, w_c4=hex(c4), w_c8=hex(p.read32(wid + 0xC8)), w_b4=hex(p.read32(wid + 0xB4)),
                         w_pos30=[_f(p.read32(wid + 0x30 + 4 * j)) for j in range(3)],
                         w_pos80=[_f(p.read32(wid + 0x80 + 4 * j)) for j in range(3)])
                if c4 != 0xFFFFFFFF:
                    s = _spr(p, c4)
                    b["spr_view42"] = (p.read32(s + 0x40) >> 16) & 0xFF
            fo = _res(p, w[9])
            if 0x00080000 <= fo < 0x02000000:
                b0 = p.read32(fo + 0xB0)
                b.update(fx=hex(fo), fx_b0=hex(b0), fx_b4=hex(p.read32(fo + 0xB4)))
                s = _spr(p, b0 >> 16)
                b["fx_spr"] = b0 >> 16
                b["fx_spr_view42"] = (p.read32(s + 0x40) >> 16) & 0xFF
            rr["blips"].append(b)
        out[name] = rr
    return out


def _setbyte(p, addr, val):
    a = addr & ~3
    sh = 8 * (addr & 3)
    w = p.read32(a)
    p.write32(a, (w & ~(0xFF << sh)) | ((val & 0xFF) << sh))


def tag_widgets_fe(p):
    """TEST ONLY (PINE write, single instance): radar-1/2 player blip widgets get view tag 0xFE (global HUD camera path
    of the sprite flush, not B2's per-view SHARED copies)."""
    done = []
    for name in ("r1", "r2"):
        r = RADARS[name]
        for k in range(128):
            e = r + 0x920 + k * 0x40
            if not (p.read32(e + 0x30) >> 8) & 0xFF or (p.read32(e + 0x2C) & 0xFFFF) != 9:
                continue
            wid = p.read32(e + 0x28)
            if not 0x00080000 <= wid < 0x02000000:
                continue
            _setbyte(p, wid + 0xF9, 0xFE)
            c4 = p.read32(wid + 0xC4)
            if c4 != 0xFFFFFFFF:
                _setbyte(p, _spr(p, c4) + 0x42, 0xFE)
            done.append([name, k, hex(wid), hex(c4)])
    return {"poll": p.read32(0x000F0500), "tagged": done}


def tag_dots_fe(p):
    """TEST ONLY: the sprite items used by radar-1/2 dot effects get view byte 0xFE."""
    done = {}
    for name in ("r1", "r2"):
        r = RADARS[name]
        for k in range(128):
            e = r + 0x920 + k * 0x40
            if not (p.read32(e + 0x30) >> 8) & 0xFF:
                continue
            fo = _res(p, p.read32(e + 0x24))
            if 0x00080000 <= fo < 0x02000000:
                idx = p.read32(fo + 0xB0) >> 16
                s = _spr(p, idx)
                done[hex(idx)] = (p.read32(s + 0x40) >> 16) & 0xFF
                _setbyte(p, s + 0x42, 0xFE)
    return {"poll": p.read32(0x000F0500), "sprites_before": done}



def radar_tex(p):
    """Each radar's dot textures +0x48..+0x60 (sprite index << 16) with the sprite item's valid/view bytes, the blip
    sprite index BLIPIDX (0x000E83F8, markers34.txt) and that item's view byte."""
    out = {"poll": p.read32(0x000F0500), "blipidx": hex(p.read32(0x000E83F8))}
    bi = p.read32(0x000E83F8)
    if 0 < bi < 0xFF:
        w = p.read32(_spr(p, bi) + 0x40)
        out["blip_item"] = {"valid": w & 0xFF, "view": (w >> 16) & 0xFF, "count1c": p.read32(_spr(p, bi) + 0x1C)}
    for name, r in RADARS.items():
        rows = []
        for k in range(7):
            t = p.read32(r + 0x48 + 4 * k)
            idx = t >> 16
            row = [hex(t)]
            if 0 < idx < 0xFF:
                w = p.read32(_spr(p, idx) + 0x40)
                row += [w & 0xFF, (w >> 16) & 0xFF]
            rows.append(row)
        out[name] = rows
    return out



def pads(p):
    """Per player: brain (0x006D53F0 + (human+0x90 >> 16) * 0x2F0) bytes +0x19 (pad) / +0x1B (pad control flag) used by the
    Select test of the marker loop FUN_0024B780, and the pad owners (0x005DD810 + pad*0x50 + 0x42)."""
    gm = p.read32(0x0051489C)
    out = {"poll": p.read32(0x000F0500), "players": [], "pad_owner": {}}
    for i in range(4):
        o = _resolve(p, p.read32(gm + 0x228 + 4 * i))
        if not 0x00100000 <= o < 0x02000000:
            continue
        br = 0x006D53F0 + ((p.read32(o + 0x90) >> 16) & 0xFFFF) * 0x2F0
        w = p.read32(br + 0x18)
        out["players"].append({"slot": i, "human": hex(o), "brain": hex(br), "b19_pad": (w >> 8) & 0xFF, "b1b_flag": (w >> 24) & 0xFF})
    for pad in range(8):
        w = p.read32(0x005DD810 + pad * 0x50 + 0x40)
        out["pad_owner"][pad] = ((w >> 16) & 0xFFFF)
    out["b622e10"] = hex(p.read32(0x00622E10))
    return out



def arcs_on(p):
    """TEST ONLY (PINE write, single instance): start the two timer arcs around players 1-2's radars (the orange ring;
    FUN_001AA9B0 reads the squad's end times +0x5E8 / +0x5F0, GameClock ms) for 9.5 s, and report the arc radii of the
    per-player widgets HUD+0x177D0 / HUD+0x18280 (objects +0x0, +0x120, +0x220, +0x340: +0 inner, +4 outer)."""
    gm = p.read32(0x0051489C)
    o = _resolve(p, p.read32(gm + 0x228))
    out = {"poll": p.read32(0x000F0500)}
    if not 0x00100000 <= o < 0x02000000:
        return out
    brain = 0x006D53F0 + ((p.read32(o + 0x90) >> 16) & 0xFFFF) * 0x2F0
    squad = p.read32(brain + 0x20C)
    clock = p.read32(p.read32(0x0050B734) + 0x48)
    if 0x00100000 <= squad < 0x02000000:
        p.write32(squad + 0x5E8, clock + 9500)
        p.write32(squad + 0x5F0, clock + 9500)
    out.update(squad=hex(squad), clock=clock, views=p.read32(0x0050B198), layout=p.read32(0x0050B1A4))
    for name, w in (("w1", 0x00618010), ("w2", 0x00618AC0)):
        out[name] = {"active_a98": p.read32(w + 0xA98), "a94": p.read32(w + 0xA94),
                     "radii": [[_f(p.read32(w + off)), _f(p.read32(w + off + 4))] for off in (0x0, 0x120, 0x220, 0x340)],
                     "pos20": [_f(p.read32(w + 0x20 + 4 * k)) for k in range(3)]}
    return out

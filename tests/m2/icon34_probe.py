"""Radar labels "3P"/"4P" (docs/research/m6_markers_map.md section 9). Read-only PINE probe for
nav_probe.py --probe icon34_probe:<func>:<poll>.

survey: sprite items 0-12 and the radar blip item (BLIPIDX 0x000E83F8; item = *(0x0050CD4C) + 0x189C + i*0x78), each
item's page object (+0x0C), the page's frame table (page+0x0C -> +0x0C, 16 bytes per frame) and texture
(page+0x14 -> texture -> raster); per radar the P3/P4 label data written by markers34.txt (0x000E8A10..).
eedump: the whole 32 MB EE RAM to local/m6/p34/ee_<poll>.bin (game data: stays in local/, never in git).
Our labels; build SLUS-21215 v1.03."""
import os
import struct

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.abspath(os.path.join(HERE, "..", "..", "local", "m6", "p34"))
RADARS = {"r1": 0x00601E10, "r2": 0x00604750, "r3": 0x000A9500, "r4": 0x000ABE40}


def _f(v):
    return round(struct.unpack("<f", struct.pack("<I", v & 0xFFFFFFFF))[0], 5)


def _ok(a):
    return 0x00080000 <= a < 0x02000000


def _words(p, a, n):
    return [p.read32(a + 4 * k) for k in range(n)] if _ok(a) else []


def survey(p):
    mgr = p.read32(0x0050CD4C)
    out = {"poll": p.read32(0x000F0500), "mgr": hex(mgr), "blipidx": hex(p.read32(0x000E83F8)), "items": []}
    idxs = list(range(13)) + [p.read32(0x000E83F8) & 0xFF]
    for i in idxs:
        it = mgr + 0x189C + i * 0x78
        w = _words(p, it, 0x78 // 4)
        row = {"i": i, "item": hex(it), "w": [hex(x) for x in w]}
        page = w[3] if w else 0
        if _ok(page):
            pw = _words(p, page, 8)
            row["page"] = [hex(x) for x in pw]
            res = pw[3]
            if _ok(res):
                rw = _words(p, res, 8)
                row["res"] = [hex(x) for x in rw]
                ft = rw[3]
                row["frames_at"] = hex(ft)
                if _ok(ft):
                    row["f15x_16x"] = {hex(k): [_f(x) for x in _words(p, ft + 16 * k, 4)] for k in range(0x158, 0x170)}
            tex = pw[5]
            if _ok(tex):
                tw = _words(p, tex, 16)
                row["tex"] = [hex(x) for x in tw]
                ras = tw[0]
                if _ok(ras):
                    row["raster"] = [hex(x) for x in _words(p, ras, 64)]
        out["items"].append(row)
    return out


def eedump(p):
    poll = p.read32(0x000F0500)
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, f"ee_{poll}.bin")
    with open(path, "wb") as fh:
        for base in range(0, 0x02000000, 0x40000):
            fh.write(p.dump(base, 0x40000))
    return {"poll": poll, "file": path, "poll_after": p.read32(0x000F0500)}


def both(p):
    out = survey(p)
    out["dump"] = eedump(p)
    return out


def labels(p):
    """Per radar: active player blips (type 9) with widget frame/colour/sprite and the label data of markers34 L1."""
    out = {"poll": p.read32(0x000F0500), "views": p.read32(0x0050B198), "lbl": [hex(x) for x in _words(p, 0x000E8A10, 12)]}
    for name, r in RADARS.items():
        rows = []
        for k in range(128):
            e = r + 0x920 + k * 0x40
            w = _words(p, e, 16)
            if not w or not (w[12] >> 8) & 0xFF or (w[11] & 0xFFFF) != 9:
                continue
            wid = w[10]
            if _ok(wid):
                rows.append({"k": k, "widget": hex(wid), "frame": hex(p.read32(wid + 0xC8)), "spr": hex(p.read32(wid + 0xC4)),
                             "col": hex(p.read32(wid + 0xB4)), "pos80": [_f(x) for x in _words(p, wid + 0x80, 4)],
                             "size90": [_f(x) for x in _words(p, wid + 0x90, 2)], "uv": [_f(x) for x in _words(p, wid + 0xA4, 4)]})
        out[name] = rows
    return out


# ---- texture tests (TEST ONLY, single instance; PINE writes into the part_page0 texture copy in EE RAM) ----
def _gs_tables():
    import re
    src = os.path.abspath(os.path.join(HERE, "..", "..", "emulator", "pcsx2", "pcsx2", "GS", "GSTables.cpp"))
    s = open(src, encoding="utf-8").read()

    def tab(name):
        m = re.search(r"\b" + re.escape(name) + r"\s*\[(\d+)\]\[(\d+)\]\s*=\s*\{(.*?)\};", s, re.S)
        h, w = int(m.group(1)), int(m.group(2))
        nums = [int(x) for x in re.findall(r"\d+", re.sub(r"//[^\n]*", "", m.group(3)))]
        return [nums[r * w:(r + 1) * w] for r in range(h)]
    return tab("_blockTable32"), tab("columnTable32"), tab("_blockTable8"), tab("columnTable8")


def ee_offsets(tw=512, th=256):
    """PSMT8 pixel (x, y) of a tw x th texture uploaded as PSMCT32 (tw/2 x th/2, DBW tw/128) -> byte offset in
    the EE upload buffer (row-major PSMCT32 words)."""
    bt32, ct32, bt8, ct8 = _gs_tables()
    W32, H32, bw32 = tw // 2, th // 2, tw // 128
    inv = {}
    for Y in range(H32):
        for X in range(W32):
            page = (Y // 32) * bw32 + X // 64
            w = (page * 32 + bt32[(Y % 32) // 8][(X % 64) // 8]) * 64 + ct32[Y % 8][X % 8]
            inv[w] = Y * W32 + X
    tbw = tw // 64

    def off(x, y):
        page = (y // 64) * (tbw // 2) + x // 128
        g = (page * 32 + bt8[(y % 64) // 16][(x % 128) // 16]) * 256 + ct8[y % 16][x % 16]
        return inv[g >> 2] * 4 + (g & 3)
    return off


def _p0_raster(p):
    mgr = p.read32(0x0050CD4C)
    page = p.read32(mgr + 0x189C + 2 * 0x78 + 0xC)
    tex = p.read32(page + 0x14)
    ras = p.read32(tex)
    return page, ras


def tex_watch(p):
    """TEX0 (raster ext +0x3C) of part_page0 sampled 40 times: a changing TBP means the texture is re-uploaded."""
    import time
    page, ras = _p0_raster(p)
    rows = []
    for _ in range(40):
        rows.append([p.read32(0x000F0500), hex(p.read32(ras + 0x3C))])
        time.sleep(0.05)
    return {"raster": hex(ras), "pix": hex(p.read32(ras + 4)), "samples": rows}


def tex_test(p):
    """TEST ONLY: copy the '1P' frame (0x168) pixels over the '2P' frame (0x169) in the EE copy of part_page0; the
    rest of the 2P rectangle gets the index of the pixel left of it. Visible on the radars only if the texture is
    re-uploaded from EE RAM."""
    page, ras = _p0_raster(p)
    pix = p.read32(ras + 4)
    w, h = p.read32(ras + 0xC), p.read32(ras + 0x10)
    ft = p.read32(p.read32(page + 0xC) + 0xC)

    def rect(k):
        u0, v0, u1, v1 = [struct.unpack("<f", struct.pack("<I", p.read32(ft + 16 * k + 4 * j)))[0] for j in range(4)]
        return int(u0 * w), int(v0 * h), int(u1 * w + 0.999), int(v1 * h + 0.999)
    off = ee_offsets(w, h)
    sx0, sy0, sx1, sy1 = rect(0x168)
    dx0, dy0, dx1, dy1 = rect(0x169)
    words = {}

    def getb(o):
        a = pix + (o & ~3)
        if a not in words:
            words[a] = p.read32(a)
        return (words[a] >> (8 * (o & 3))) & 0xFF

    def setb(o, v):
        getb(o)
        a = pix + (o & ~3)
        sh = 8 * (o & 3)
        words[a] = (words[a] & ~(0xFF << sh)) | (v << sh)
    bgi = getb(off(dx0 - 1, (dy0 + dy1) // 2))
    src = {(x, y): getb(off(x, y)) for y in range(sy0, sy1) for x in range(sx0, sx1)}
    n = 0
    for y in range(dy0, dy1):
        for x in range(dx0, dx1):
            sx, sy = sx0 + (x - dx0), sy0 + (y - dy0)
            setb(off(x, y), src.get((sx, sy), bgi))
            n += 1
    p.batch_write32(sorted(words.items()))
    return {"poll": p.read32(0x000F0500), "pix": hex(pix), "src": [sx0, sy0, sx1, sy1], "dst": [dx0, dy0, dx1, dy1],
            "pixels": n, "words": len(words), "bg_index": bgi}


def l34(p):
    """markers34.txt L1-L4 state: data at 0x000E8A10 (GENPIX, GENOK, FT, PIX, PAL, BASE, P2X, P2Y, indices F H O B T) and
    the generated texels of "3P" (x 90..110) and "4P" (x 113..133), rows 236..247, read from the EE texture copy."""
    d = [p.read32(0x000E8A10 + 4 * k) for k in range(10)]
    out = {"poll": p.read32(0x000F0500), "data": [hex(x) for x in d]}
    page, ras = _p0_raster(p)
    pix = p.read32(ras + 4)
    out["pix_now"] = hex(pix)
    off = ee_offsets()
    cache = {}

    def tb(x, y):
        o = off(x, y)
        a = pix + (o & ~3)
        if a not in cache:
            cache[a] = p.read32(a)
        return (cache[a] >> (8 * (o & 3))) & 0xFF
    out["3P"] = [" ".join("%02x" % tb(x, y) for x in range(90, 111)) for y in range(236, 248)]
    out["4P"] = [" ".join("%02x" % tb(x, y) for x in range(113, 134)) for y in range(236, 248)]
    out["vtab3"] = [_f(p.read32(0x000E8B60 + 0x30 + 4 * k)) for k in range(8)]
    return out

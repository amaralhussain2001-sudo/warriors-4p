"""Read WARRIORS.DIR / WARRIORS.WAD (extracted copies in local/disc) read-only.

Format as observed (finding F-0006): WARRIORS.DIR = u32 count, then 12-byte
records (u32 wad_offset, u32 size, u32 name_hash). The first record after the
count is all zero. Names are stored only as hashes.

Usage:
    python -I tools/wad_index.py summary            # magic-byte histogram
    python -I tools/wad_index.py list > out.tsv     # index, offset, size, hash, magic
    python -I tools/wad_index.py dump <index> <out> # copy one entry (into local/ only)
"""
import collections
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DISC = os.path.join(HERE, "..", "local", "disc")


def entries():
    d = open(os.path.join(DISC, "WARRIORS.DIR"), "rb").read()
    count = struct.unpack_from("<I", d, 0)[0]
    recs = []
    for i in range((len(d) - 4) // 12):
        off, size, h = struct.unpack_from("<III", d, 4 + i * 12)
        recs.append((i, off, size, h))
    return count, recs


def magic(b):
    if b[:4] == b"\x1bLua":
        return "lua"
    printable = sum(32 <= c < 127 or c in (9, 10, 13) for c in b)
    if printable == len(b):
        return "text:" + b[:8].decode("ascii", "replace").replace("\t", " ").replace("\n", " ").replace("\r", " ")
    return b[:4].hex()


def main():
    count, recs = entries()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "summary"
    wad = open(os.path.join(DISC, "WARRIORS.WAD"), "rb")
    if cmd == "dump":
        idx, out = int(sys.argv[2]), sys.argv[3]
        _, off, size, _ = recs[idx]
        wad.seek(off)
        with open(out, "wb") as f:
            f.write(wad.read(size))
        return
    hist = collections.Counter()
    rows = []
    for i, off, size, h in recs:
        if size == 0:
            continue
        wad.seek(off)
        m = magic(wad.read(16))
        key = m if not m.startswith("text:") else "text"
        hist[key] += 1
        rows.append((i, off, size, h, m))
    if cmd == "list":
        for r in rows:
            print(f"{r[0]}\t{r[1]:#x}\t{r[2]}\t{r[3]:08x}\t{r[4]}")
    else:
        print("count field:", count, "records:", len(recs), "non-empty:", len(rows))
        for k, v in hist.most_common(40):
            print(f"{v:6d}  {k}")


if __name__ == "__main__":
    main()

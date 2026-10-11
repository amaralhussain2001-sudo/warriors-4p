"""Extract pnach lines from a research note into a patch fragment, and check fragments against the game ELF.

Usage:
  python -I tools/note_patches.py extract <note.md> <out.txt>        # "patch=" lines and GameMgr-style tables
  python -I tools/note_patches.py check <fragment.txt> [...]         # checks across all given fragments + mod pnach
Checks: every "was XXXXXXXX" comment equals the ELF word at that address; no address is patched twice with different
values; cave/data addresses (0x000F0000-0x000F0FFF) are zero in the ELF (free). Read-only on the ELF.
"""
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.abspath(os.path.join(HERE, ".."))
ELF = os.path.join(PROJ, "local", "disc", "SLUS_212.15")
LINE = re.compile(r"patch=(\d),EE,([0-9A-Fa-f]{8}),(word|short|byte),([0-9A-Fa-f]+)(.*)$")
TABLE = re.compile(r"^\|[^|]*\|\s*`([0-9A-Fa-f]{8})`\s*\|\s*`([0-9A-Fa-f]{8})`([^|]*)\|\s*`([0-9A-Fa-f]{8})`([^|]*)\|(.*)\|\s*$")


def elf_word(addr, _cache={}):
    if "segs" not in _cache:
        data = open(ELF, "rb").read()
        phoff, = struct.unpack_from("<I", data, 0x1C)
        phnum, = struct.unpack_from("<H", data, 0x2C)
        _cache["data"] = data
        _cache["segs"] = [struct.unpack_from("<6I", data, phoff + 32 * i) for i in range(phnum)]
    for _, off, va, _, fsz, msz in _cache["segs"]:
        if va <= addr < va + fsz:
            return struct.unpack_from("<I", _cache["data"], off + addr - va)[0]
        if va <= addr < va + msz:
            return 0
    return None


def extract(note, out):
    lines = []
    for raw in open(note, encoding="utf-8"):
        s = raw.strip().strip("`").strip()
        m = LINE.search(s)
        if m and s.startswith("patch="):
            lines.append(s)
            continue
        t = TABLE.match(raw.strip())
        if t:
            addr, orig, orig_c, new, new_c, note_c = t.groups()
            lines.append(f"patch=2,EE,{addr.upper()},word,{new.upper()} // was {orig.upper()}{orig_c.strip() and ' ' + orig_c.strip()}; {note_c.strip()}")
    open(out, "w", encoding="utf-8").write(f"// extracted from {os.path.relpath(note, PROJ)}\n" + "\n".join(lines) + "\n")
    print(f"{len(lines)} lines -> {out}")


def parse(path):
    for n, raw in enumerate(open(path, encoding="utf-8"), 1):
        m = LINE.search(raw)
        if m and raw.strip().startswith("patch="):
            place, addr, kind, val, rest = m.groups()
            was = re.search(r"was ([0-9A-Fa-f]{8})", rest)
            yield path, n, int(place), int(addr, 16), kind, int(val, 16), int(was.group(1), 16) if was else None


def check(paths):
    seen = {}
    bad = 0
    for path, n, place, addr, kind, val, was in (e for p in paths for e in parse(p)):
        where = f"{os.path.basename(path)}:{n}"
        if kind == "word" and addr in seen and seen[addr][0] != val:
            print(f"CONFLICT {addr:08X}: {seen[addr][1]} sets {seen[addr][0]:08X}, {where} sets {val:08X}")
            bad += 1
        seen.setdefault(addr, (val, where))
        if was is not None and kind == "word":
            w = elf_word(addr)
            if w != was:
                print(f"WAS MISMATCH {where} {addr:08X}: note says {was:08X}, ELF has {w if w is None else format(w, '08X')}")
                bad += 1
        if 0x000F0000 <= addr < 0x000F1000:
            w = elf_word(addr)
            if w not in (0, None):
                print(f"CAVE NOT FREE {where} {addr:08X}: ELF word {w:08X}")
                bad += 1
    print(f"checked {len(seen)} addresses in {len(paths)} files: {bad} problems")
    return bad


if __name__ == "__main__":
    if sys.argv[1] == "extract":
        extract(sys.argv[2], sys.argv[3])
    else:
        sys.exit(1 if check(sys.argv[2:]) else 0)

"""Add Lua rows to the LUACH table of [warriors-4p missions] (docs/research/m6_x4_x6.md 2.3, m6_x6_fixes.md) on a COPY
of mod/, build a test pnach from it, or apply the result to mod/ itself.

A row file is Lua 4.0 source with a small header:
    -- chunk: level54_park.lua      (the LUACH chunk name from the runtime log; "*" = run after every chunk)
    -- name: m16p                   (short label used in the pnach comments)
    <Lua lines; whole-line "--" comments are dropped, inline "--" comments are not allowed>
The source is joined into one line (like every existing row) and stored as startup-only words (patch=0) in the given
free RAM region together with the chunk name; the rows are inserted before the table's end row.

Usage:
  python -I tools/lua_rows.py build --base mod --region 0x000E9800:0x000EA400 --work local/m6/cam/A \
      --out local/m6/cam/A/test.pnach [--title "..."] rows/a.lua rows/b.lua ...
  (same with --apply: writes mod/m2/missions.txt itself and prints the regenerate command; use only for the final
  integration, never while a 4-instance batch is starting runs)
Checks: the region is not written by any other pnach line, the table stays inside its 64 rows, note_patches check.
"""
import os
import re
import shutil
import subprocess
import sys

PROJ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def opt(name, default=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def read_row(path):
    chunk, name, body = None, None, []
    for ln in open(path, encoding="utf-8").read().splitlines():
        s = ln.strip()
        m = re.match(r"--\s*chunk:\s*(\S+)", s)
        if m:
            chunk = m.group(1)
            continue
        m = re.match(r"--\s*name:\s*(\S+)", s)
        if m:
            name = m.group(1)
            continue
        if not s or s.startswith("--"):
            continue
        body.append(s)
    assert chunk and name, f"{path}: header '-- chunk:' and '-- name:' needed"
    src = " ".join(body)
    assert "--" not in src, f"{path}: inline '--' comment (not allowed: the source becomes one line)"
    assert all(32 <= ord(c) < 127 for c in src), f"{path}: non-ASCII character"
    return chunk, name, src


def words(addr, data, what):
    data = data + b"\0" * (-len(data) % 4)
    out = []
    for i in range(0, len(data), 4):
        chunk = data[i:i + 4]
        shown = "".join(chr(c) if 32 <= c < 127 and chr(c) != '"' else "." for c in chunk)
        out.append(f"patch=0,EE,{addr + i:08X},word,{int.from_bytes(chunk, 'little'):08X} // {what} bytes {i}-{i + 3} "
                   f"\"{shown}\" (startup only)")
    return out, addr + len(data)


def main():
    if len(sys.argv) < 2 or sys.argv[1] != "build":
        print(__doc__)
        sys.exit(2)
    base = os.path.join(PROJ, opt("--base", "mod"))
    a0, a1 = (int(x, 16) for x in opt("--region").split(":"))
    title = opt("--title", "Lua rows added by tools/lua_rows.py")
    flags = {"--base", "--region", "--work", "--out", "--title"}
    files = [a for i, a in enumerate(sys.argv[2:], 2) if not a.startswith("--") and sys.argv[i - 1] not in flags]
    apply = "--apply" in sys.argv
    if apply:
        work = base
    else:
        work = os.path.join(PROJ, opt("--work"), "mod")
        if os.path.exists(work):
            shutil.rmtree(work)
        shutil.copytree(base, work, ignore=shutil.ignore_patterns("*.pnach", "__pycache__"))
        tools = os.path.join(os.path.dirname(work), "tools")
        os.makedirs(tools, exist_ok=True)
        shutil.copyfile(os.path.join(PROJ, "tools", "mips_asm.py"), os.path.join(tools, "mips_asm.py"))
    mp = os.path.join(work, "m2", "missions.txt")
    raw = open(mp, "rb").read()
    assert b"\r\n" in raw
    lines = raw.decode("utf-8").split("\r\n")
    # region must be free in every group file
    for fn in os.listdir(os.path.join(work, "m2")):
        for ln in open(os.path.join(work, "m2", fn), encoding="utf-8", errors="replace"):
            m = re.match(r"patch=\d,EE,([0-9A-Fa-f]{8}),", ln)
            if m and a0 <= int(m.group(1), 16) < a1:
                sys.exit(f"region 0x{a0:08X}-0x{a1:08X} already used: {fn}: {ln.strip()[:100]}")
    end = [i for i, l in enumerate(lines) if re.match(r"patch=0,EE,[0-9A-F]{8},word,00000000 // LC_TAB row \d+: chunk name", l)]
    assert len(end) == 1 and "end of table" in lines[end[0] + 1], "end row of the LUACH table not found"
    i_end = end[0]
    t_addr = int(lines[i_end].split(",")[2], 16)
    row_no = int(re.search(r"LC_TAB row (\d+)", lines[i_end]).group(1))
    t0 = int(next(l for l in lines if " // LC_TAB row 0: chunk name" in l).split(",")[2], 16)
    rows = [read_row(f) for f in files]
    data, table = [], []
    addr = a0
    names = {}
    for chunk, name, src in rows:
        if chunk != "*" and chunk not in names:
            names[chunk] = addr
            w, addr = words(addr, chunk.encode("latin-1") + b"\0", f"row name \"{chunk}\"")
            data += w
    addr = (addr + 15) & ~15
    for chunk, name, src in rows:
        w, nxt = words(addr, src.encode("latin-1") + b"\0", f"row {name} source")
        data += w
        np = names.get(chunk, 0)
        what = f"chunk name \"{chunk}\"" if chunk != "*" else "chunk name pointer 0 = every chunk"
        table.append(f"patch=0,EE,{t_addr:08X},word,{np:08X} // LC_TAB row {row_no}: {what} ({title}) (startup only)")
        table.append(f"patch=0,EE,{t_addr + 4:08X},word,{addr:08X} // LC_TAB row {row_no}: Lua source ({name}, "
                     f"{len(src)} characters) (startup only)")
        print(f"row {row_no}: {chunk} {name} {len(src)} chars at 0x{addr:08X}-0x{nxt - 1:08X}")
        t_addr += 8
        row_no += 1
        addr = (nxt + 15) & ~15
    assert addr <= a1, f"region too small: need up to 0x{addr:08X}"
    assert t_addr + 8 <= t0 + 64 * 8, "LUACH table full (64 rows)"
    table.append(f"patch=0,EE,{t_addr:08X},word,00000000 // LC_TAB row {row_no}: chunk name pointer (0 = every chunk) (startup only)")
    table.append(f"patch=0,EE,{t_addr + 4:08X},word,00000000 // LC_TAB row {row_no}: Lua source pointer 0 = end of table (startup only)")
    lines = lines[:i_end] + table + lines[i_end + 2:]
    while lines and lines[-1] == "":
        lines.pop()
    lines += [f"// {title}: {len(rows)} LUACH rows, names and sources at 0x{a0:08X}-0x{addr - 1:08X} (free low RAM)."] + data + [""]
    open(mp, "wb").write("\r\n".join(lines).encode("utf-8"))
    if apply:
        print("applied to", mp, "- now: python -I mod/make_pnach.py > mod/w4p_m1.pnach")
        return
    out = os.path.join(PROJ, opt("--out"))
    with open(out, "w", encoding="utf-8", newline="") as fh:
        r = subprocess.run([sys.executable, "-I", os.path.join(work, "make_pnach.py")], stdout=fh, cwd=PROJ)
    assert r.returncode == 0
    chk = subprocess.run([sys.executable, "-I", os.path.join(PROJ, "tools", "note_patches.py"), "check", out],
                         capture_output=True, text=True, cwd=PROJ)
    print(chk.stdout.strip().splitlines()[-1] if chk.stdout.strip() else chk.stderr[-300:])


if __name__ == "__main__":
    main()

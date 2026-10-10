"""Parse and disassemble Lua 4.0 bytecode chunks from WARRIORS.WAD.

The chunks carry no debug info (no source names, locals or line numbers), so
the output lists each function's string constants and a readable instruction
listing. Opcode numbering follows stock Lua 4.0.1 lopcodes.h; tools/lua40_dump.py
--selftest checks that assumption against the data (every function must end in
OP_END and every constant index must be in range).

Output stays under local/ because it is derived from copyrighted game data.

Usage:
    python -I tools/lua40_dump.py --selftest
    python -I tools/lua40_dump.py --all <outdir>       # one .txt per WAD entry
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import wad_index  # noqa: E402

OPS = [
    "END", "RETURN", "CALL", "TAILCALL", "PUSHNIL", "POP", "PUSHINT", "PUSHSTRING",
    "PUSHNUM", "PUSHNEGNUM", "PUSHUPVALUE", "GETLOCAL", "GETGLOBAL", "GETTABLE",
    "GETDOTTED", "GETINDEXED", "PUSHSELF", "CREATETABLE", "SETLOCAL", "SETGLOBAL",
    "SETTABLE", "SETLIST", "SETMAP", "ADD", "ADDI", "SUB", "MULT", "DIV", "POW",
    "CONCAT", "MINUS", "NOT", "JMPNE", "JMPEQ", "JMPLT", "JMPLE", "JMPGT", "JMPGE",
    "JMPT", "JMPF", "JMPONT", "JMPONF", "JMP", "PUSHNILJMP", "FORPREP", "FORLOOP",
    "LFORPREP", "LFORLOOP", "CLOSURE",
]
U_STR = {"PUSHSTRING", "GETGLOBAL", "SETGLOBAL", "GETDOTTED", "PUSHSELF"}
U_NUM = {"PUSHNUM", "PUSHNEGNUM"}
S_ARG = {"PUSHINT", "ADDI", "JMPNE", "JMPEQ", "JMPLT", "JMPLE", "JMPGT", "JMPGE", "JMPT",
         "JMPF", "JMPONT", "JMPONF", "JMP", "FORPREP", "FORLOOP", "LFORPREP", "LFORLOOP"}
AB_ARG = {"CALL", "TAILCALL", "SETLIST", "CLOSURE"}
MAXARG_S = ((1 << 26) - 1) >> 1


class Reader:
    def __init__(self, b):
        self.b, self.p = b, 0

    def u8(self):
        v = self.b[self.p]
        self.p += 1
        return v

    def i32(self):
        v = struct.unpack_from("<i", self.b, self.p)[0]
        self.p += 4
        return v

    def string(self):
        n = struct.unpack_from("<I", self.b, self.p)[0]
        self.p += 4
        if n == 0:
            return None
        s = self.b[self.p:self.p + n - 1].decode("latin-1")
        self.p += n
        return s


def load_function(r):
    f = {"source": r.string(), "line": r.i32(), "nparams": r.i32(), "vararg": r.u8(), "maxstack": r.i32()}
    f["locals"] = [(r.string(), r.i32(), r.i32()) for _ in range(r.i32())]
    f["lines"] = [r.i32() for _ in range(r.i32())]
    f["kstr"] = [r.string() for _ in range(r.i32())]
    nk = r.i32()
    f["knum"] = list(struct.unpack_from(f"<{nk}d", r.b, r.p))
    r.p += 8 * nk
    f["protos"] = [load_function(r) for _ in range(r.i32())]
    nc = r.i32()
    f["code"] = list(struct.unpack_from(f"<{nc}I", r.b, r.p))
    r.p += 4 * nc
    return f


def load_chunk(b):
    if b[:5] != b"\x1bLua\x40":
        raise ValueError("not a Lua 4.0 chunk")
    hdr = b[5:13]
    if hdr != bytes([1, 4, 4, 4, 32, 6, 9, 8]):
        raise ValueError(f"unexpected header {hdr.hex()}")
    r = Reader(b)
    r.p = 21  # 13 header bytes + 8-byte test number
    f = load_function(r)
    return f, r.p


def decode(ins):
    op = ins & 0x3F
    u = ins >> 6
    return op, u, (ins >> 6) & 0x1FF, ins >> 15


def check(f, errs, path="main"):
    if not f["code"] or (f["code"][-1] & 0x3F) != 0:
        errs.append(f"{path}: last op is not END")
    for pc, ins in enumerate(f["code"]):
        op, u, b, a = decode(ins)
        if op >= len(OPS):
            errs.append(f"{path}@{pc}: opcode {op} out of range")
            continue
        name = OPS[op]
        if name in U_STR and u >= len(f["kstr"]):
            errs.append(f"{path}@{pc}: {name} kstr {u} out of range")
        if name in U_NUM and u >= len(f["knum"]):
            errs.append(f"{path}@{pc}: {name} knum {u} out of range")
        if name == "CLOSURE" and a >= len(f["protos"]):
            errs.append(f"{path}@{pc}: CLOSURE proto {a} out of range")
    for i, p in enumerate(f["protos"]):
        check(p, errs, f"{path}.{i}")


def disasm(f, out, path="main", depth=0):
    ind = "  " * depth
    out.append(f"{ind}function {path} params={f['nparams']} vararg={f['vararg']} maxstack={f['maxstack']}")
    for pc, ins in enumerate(f["code"]):
        op, u, b, a = decode(ins)
        name = OPS[op] if op < len(OPS) else f"OP{op}"
        if name in U_STR:
            arg = repr(f["kstr"][u])
        elif name in U_NUM:
            arg = repr(f["knum"][u])
        elif name in S_ARG:
            s = u - MAXARG_S
            arg = f"{s}" + (f"  -> {pc + 1 + s}" if name.startswith(("JMP", "FOR", "LFOR")) else "")
        elif name in AB_ARG:
            arg = f"{a} {b}"
        else:
            arg = f"{u}"
        out.append(f"{ind}  {pc:5d} {name:<12s} {arg}")
    for i, p in enumerate(f["protos"]):
        disasm(p, out, f"{path}.{i}", depth + 1)


def wad_luas():
    _, recs = wad_index.entries()
    wad = open(os.path.join(wad_index.DISC, "WARRIORS.WAD"), "rb")
    for i, off, size, h in recs:
        if size == 0:
            continue
        wad.seek(off)
        b = wad.read(size)
        if b[:4] == b"\x1bLua":
            yield i, h, b


def main():
    if "--selftest" in sys.argv:
        total, bad = 0, 0
        for i, h, b in wad_luas():
            total += 1
            try:
                f, end = load_chunk(b)
                errs = []
                check(f, errs)
                if end != len(b):
                    errs.append(f"parsed {end} of {len(b)} bytes")
            except Exception as e:  # noqa: BLE001
                errs = [repr(e)]
            if errs:
                bad += 1
                print(i, f"{h:08x}", errs[:3])
        print(f"{total} chunks, {bad} with problems")
    elif "--all" in sys.argv:
        outdir = sys.argv[sys.argv.index("--all") + 1]
        os.makedirs(outdir, exist_ok=True)
        for i, h, b in wad_luas():
            f, _ = load_chunk(b)
            out = [f"; WAD entry {i} hash {h:08x} size {len(b)}"]
            disasm(f, out)
            with open(os.path.join(outdir, f"{i:05d}_{h:08x}.txt"), "w", encoding="utf-8") as fh:
                fh.write("\n".join(out) + "\n")


if __name__ == "__main__":
    main()

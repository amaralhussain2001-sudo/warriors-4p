"""Turn Lua 4.0 bytecode (from lua40_dump) into readable pseudo-Lua.

This is a reading aid, not a faithful decompiler: control flow is shown as
labels and gotos, locals are named L<slot>, parameters A<slot>, upvalues U<n>.
Expressions are rebuilt by simulating the VM stack symbolically. Whenever the
simulation is unsure it falls back to a comment with the raw instruction.

Usage:
    python -I tools/lua40_pseudo.py --all <outdir>
    python -I tools/lua40_pseudo.py --entry <wad_index>
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lua40_dump as ld  # noqa: E402

BINOPS = {"ADD": "+", "SUB": "-", "MULT": "*", "DIV": "/", "POW": "^"}
CMPS = {"JMPNE": "~=", "JMPEQ": "==", "JMPLT": "<", "JMPLE": "<=", "JMPGT": ">", "JMPGE": ">="}
MULT_RET = 255


def lit_str(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "\\r") + '"'


def num(n):
    return str(int(n)) if n == int(n) and abs(n) < 1e15 else repr(n)


class Expr:
    __slots__ = ("text", "named", "table")

    def __init__(self, text, named=False, table=None):
        self.text, self.named, self.table = text, named, table


def pseudo(f, out, name="main", depth=0):
    ind = "  " * depth
    params = [f"A{i}" for i in range(f["nparams"])]
    if f["vararg"]:
        params.append("...")
    out.append(f"{ind}function {name}({', '.join(params)})")
    code = f["code"]
    targets = set()
    for pc, ins in enumerate(code):
        op, u, b, a = ld.decode(ins)
        nm = ld.OPS[op]
        if nm in ld.S_ARG and nm.startswith(("JMP", "FOR", "LFOR")):
            targets.add(pc + 1 + (u - ld.MAXARG_S))
    stack = [Expr(f"A{i}", True) for i in range(f["nparams"])]
    nlocal = f["nparams"]
    body = ind + "  "
    closures = {}

    def emit(s):
        out.append(body + s)

    def name_of(slot):
        return f"A{slot}" if slot < f["nparams"] else f"L{slot}"

    def materialize(below):
        nonlocal nlocal
        for s in range(min(below, len(stack))):
            e = stack[s]
            if not e.named:
                emit(f"local {name_of(s)} = {e.text}")
                stack[s] = Expr(name_of(s), True)
        nlocal = max(nlocal, min(below, len(stack)))

    def pop(n=1):
        vals = stack[len(stack) - n:] if n else []
        del stack[len(stack) - n:]
        return vals

    for pc, ins in enumerate(code):
        if pc in targets:
            materialize(len(stack))
            out.append(f"{body}::L{pc}::")
        op, u, b, a = ld.decode(ins)
        nm = ld.OPS[op]
        s = u - ld.MAXARG_S
        try:
            if nm == "END":
                emit("-- end")
            elif nm == "RETURN":
                vals = stack[u:]
                materialize(u)
                emit("return " + ", ".join(v.text for v in vals))
                del stack[u:]
            elif nm in ("CALL", "TAILCALL"):
                fn = stack[a]
                args = stack[a + 1:]
                txt = f"{fn.text}({', '.join(x.text for x in args)})"
                del stack[a:]
                if nm == "TAILCALL":
                    materialize(a)
                    emit("return " + txt)
                elif b == 0:
                    materialize(a)
                    emit(txt)
                elif b == 1:
                    stack.append(Expr(txt))
                else:
                    materialize(a)
                    n = b if b != MULT_RET else 1
                    names = [f"L{a + i}" for i in range(n)]
                    emit(f"local {', '.join(names)} = {txt}" + ("  -- multret" if b == MULT_RET else ""))
                    stack.extend(Expr(x, True) for x in names)
            elif nm == "PUSHNIL":
                stack.extend(Expr("nil") for _ in range(u))
            elif nm == "POP":
                vals = pop(u)
                for v in vals:
                    if not v.named and "(" in v.text:
                        emit(v.text + "  -- popped")
            elif nm == "PUSHINT":
                stack.append(Expr(str(s)))
            elif nm == "PUSHSTRING":
                stack.append(Expr(lit_str(f["kstr"][u])))
            elif nm == "PUSHNUM":
                stack.append(Expr(num(f["knum"][u])))
            elif nm == "PUSHNEGNUM":
                stack.append(Expr("-" + num(f["knum"][u])))
            elif nm == "PUSHUPVALUE":
                stack.append(Expr(f"U{u}", True))
            elif nm == "GETLOCAL":
                if u < len(stack) and not stack[u].named:
                    materialize(u + 1)
                stack.append(Expr(name_of(u), True))
            elif nm == "GETGLOBAL":
                stack.append(Expr(f["kstr"][u], True))
            elif nm == "GETTABLE":
                t, k = pop(2)
                stack.append(Expr(f"{t.text}[{k.text}]"))
            elif nm == "GETDOTTED":
                (t,) = pop(1)
                stack.append(Expr(f"{t.text}.{f['kstr'][u]}"))
            elif nm == "GETINDEXED":
                (t,) = pop(1)
                stack.append(Expr(f"{t.text}[{name_of(u)}]"))
            elif nm == "PUSHSELF":
                (t,) = pop(1)
                stack.append(Expr(f"{t.text}:{f['kstr'][u]}"))
                stack.append(Expr("<self>"))
            elif nm == "CREATETABLE":
                stack.append(Expr("{}", table=[]))
            elif nm == "SETLOCAL":
                (v,) = pop(1)
                materialize(len(stack))
                emit(f"{name_of(u)} = {v.text}")
            elif nm == "SETGLOBAL":
                (v,) = pop(1)
                materialize(len(stack))
                emit(f"{f['kstr'][u]} = {v.text}")
            elif nm == "SETTABLE":
                # a = position of table counted from top, b = values to pop
                top = len(stack)
                t, k, v = stack[top - a], stack[top - a + 1], stack[top - 1]
                del stack[top - b:]
                materialize(len(stack))
                emit(f"{t.text}[{k.text}] = {v.text}")
            elif nm == "SETLIST":
                n = b
                vals = pop(n)
                t = stack[-1]
                t.table = (t.table or []) + [v.text for v in vals]
                t.text = "{" + ", ".join(t.table) + "}"
            elif nm == "SETMAP":
                n = u
                vals = pop(2 * n)
                t = stack[-1]
                items = [f"[{vals[i].text}] = {vals[i + 1].text}" for i in range(0, len(vals), 2)]
                t.table = (t.table or []) + items
                t.text = "{" + ", ".join(t.table) + "}"
            elif nm in BINOPS:
                x, y = pop(2)
                stack.append(Expr(f"({x.text} {BINOPS[nm]} {y.text})"))
            elif nm == "ADDI":
                (x,) = pop(1)
                stack.append(Expr(f"({x.text} + {s})"))
            elif nm == "CONCAT":
                vals = pop(u)
                stack.append(Expr("(" + " .. ".join(v.text for v in vals) + ")"))
            elif nm == "MINUS":
                (x,) = pop(1)
                stack.append(Expr(f"-{x.text}"))
            elif nm == "NOT":
                (x,) = pop(1)
                stack.append(Expr(f"not {x.text}"))
            elif nm in CMPS:
                x, y = pop(2)
                materialize(len(stack))
                emit(f"if {x.text} {CMPS[nm]} {y.text} then goto L{pc + 1 + s} end")
            elif nm in ("JMPT", "JMPF"):
                (x,) = pop(1)
                materialize(len(stack))
                emit(f"if {'' if nm == 'JMPT' else 'not '}{x.text} then goto L{pc + 1 + s} end")
            elif nm in ("JMPONT", "JMPONF"):
                x = stack[-1]
                materialize(len(stack) - 1)
                emit(f"-- {x.text} {'or' if nm == 'JMPONT' else 'and'} ... (short-circuit to L{pc + 1 + s})")
                pop(1)
            elif nm == "JMP":
                materialize(len(stack))
                emit(f"goto L{pc + 1 + s}")
            elif nm == "PUSHNILJMP":
                stack.append(Expr("nil"))
                emit("-- pushniljmp")
            elif nm in ("FORPREP", "LFORPREP"):
                materialize(len(stack))
                base = len(stack) - (3 if nm == "FORPREP" else 1)
                if nm == "FORPREP":
                    emit(f"for {name_of(base)} = {name_of(base)}, {name_of(base + 1)}, {name_of(base + 2)} do  -- exit L{pc + 1 + s}")
                else:
                    emit(f"for {name_of(base + 1)}, {name_of(base + 2)} in {name_of(base)} do  -- exit L{pc + 1 + s}")
                    stack.extend([Expr(name_of(base + 1), True), Expr(name_of(base + 2), True)])
            elif nm in ("FORLOOP", "LFORLOOP"):
                materialize(len(stack))
                emit(f"end  -- loop back to L{pc + 1 + s}")
                del stack[len(stack) - (3 if nm == "FORLOOP" else 3):]
            elif nm == "CLOSURE":
                ups = pop(b)
                cname = f"{name}_{a}"
                closures[a] = cname
                stack.append(Expr(f"<closure {cname}" + (f" ups={','.join(x.text for x in ups)}" if ups else "") + ">", True))
            else:
                emit(f"-- {nm} {u}")
        except (IndexError, TypeError) as e:
            emit(f"-- ?? {nm} a={a} b={b} u={u} ({e}); stack={len(stack)}")
            stack[:] = stack[:max(0, nlocal)]
    out.append(f"{ind}end")
    for i, p in enumerate(f["protos"]):
        pseudo(p, out, closures.get(i, f"{name}_{i}"), depth + 1)


def render(b, header=""):
    f, _ = ld.load_chunk(b)
    out = [header] if header else []
    pseudo(f, out)
    return "\n".join(out) + "\n"


def main():
    if "--entry" in sys.argv:
        want = int(sys.argv[sys.argv.index("--entry") + 1])
        for i, h, b in ld.wad_luas():
            if i == want:
                sys.stdout.write(render(b, f"-- WAD entry {i} hash {h:08x}"))
    elif "--all" in sys.argv:
        outdir = sys.argv[sys.argv.index("--all") + 1]
        os.makedirs(outdir, exist_ok=True)
        for i, h, b in ld.wad_luas():
            with open(os.path.join(outdir, f"{i:05d}_{h:08x}.lua"), "w", encoding="utf-8") as fh:
                fh.write(render(b, f"-- WAD entry {i} hash {h:08x} size {len(b)}"))


if __name__ == "__main__":
    main()

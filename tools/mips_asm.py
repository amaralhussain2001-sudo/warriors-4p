"""Tiny MIPS (R5900 subset) assembler for Stage 1 experiment code caves.

Supports: lui ori addiu addu subu sll srl srlv and andi sltu slt lw sw lh lhu sh lb lbu sb
beq bne bltz bgez blez bgtz j jal jr jalr nop move, labels ("name:") and comments (#).
Branch targets are labels; the caller must place delay-slot instructions explicitly.
"""
import re

REGS = {n: i for i, n in enumerate(
    "zero at v0 v1 a0 a1 a2 a3 t0 t1 t2 t3 t4 t5 t6 t7 s0 s1 s2 s3 s4 s5 s6 s7 t8 t9 k0 k1 gp sp fp ra".split())}


def r(x):
    x = x.strip().lstrip("$")
    return REGS[x]


def imm(x):
    x = x.strip()
    return int(x, 0)


def mem(x):
    m = re.match(r"\s*(-?[0-9a-fA-Fx]+)\((\$?\w+)\)\s*", x)
    return imm(m.group(1)), r(m.group(2))


def assemble(src, origin):
    lines = []
    for raw in src.splitlines():
        line = raw.split("#")[0].strip()
        while ":" in line:
            lab, line = line.split(":", 1)
            lines.append(("label", lab.strip()))
            line = line.strip()
        if line:
            lines.append(("ins", line))
    labels, pc = {}, origin
    for kind, v in lines:
        if kind == "label":
            labels[v] = pc
        else:
            pc += 4
    out, pc = [], origin
    for kind, v in lines:
        if kind != "ins":
            continue
        op, _, rest = v.partition(" ")
        a = [s.strip() for s in rest.split(",")] if rest else []

        def br(target):
            off = (labels[target] - (pc + 4)) >> 2
            return off & 0xFFFF
        I = lambda o, rs, rt, im: (o << 26) | (rs << 21) | (rt << 16) | (im & 0xFFFF)  # noqa: E731
        R = lambda rs, rt, rd, sh, fn: (rs << 21) | (rt << 16) | (rd << 11) | (sh << 6) | fn  # noqa: E731
        if op == "nop":
            w = 0
        elif op == "move":
            w = R(r(a[1]), 0, r(a[0]), 0, 0x21)
        elif op == "lui":
            w = I(0x0F, 0, r(a[0]), imm(a[1]))
        elif op in ("ori", "andi", "addiu"):
            w = I({"ori": 0x0D, "andi": 0x0C, "addiu": 0x09}[op], r(a[1]), r(a[0]), imm(a[2]))
        elif op in ("addu", "subu", "and", "sltu", "slt", "or"):
            fn = {"addu": 0x21, "subu": 0x23, "and": 0x24, "or": 0x25, "sltu": 0x2B, "slt": 0x2A}[op]
            w = R(r(a[1]), r(a[2]), r(a[0]), 0, fn)
        elif op in ("sll", "srl"):
            w = R(0, r(a[1]), r(a[0]), imm(a[2]), {"sll": 0, "srl": 2}[op])
        elif op == "srlv":
            w = R(r(a[2]), r(a[1]), r(a[0]), 0, 0x06)
        elif op in ("lw", "sw", "lh", "lhu", "sh", "lb", "lbu", "sb"):
            o = {"lw": 0x23, "sw": 0x2B, "lh": 0x21, "lhu": 0x25, "sh": 0x29, "lb": 0x20, "lbu": 0x24, "sb": 0x28}[op]
            off, base = mem(a[1])
            w = I(o, base, r(a[0]), off)
        elif op in ("beq", "bne"):
            w = I({"beq": 4, "bne": 5}[op], r(a[0]), r(a[1]), br(a[2]))
        elif op in ("blez", "bgtz"):
            w = I({"blez": 6, "bgtz": 7}[op], r(a[0]), 0, br(a[1]))
        elif op in ("bltz", "bgez"):
            w = I(1, r(a[0]), {"bltz": 0, "bgez": 1}[op], br(a[1]))
        elif op in ("j", "jal"):
            t = labels[a[0]] if a[0] in labels else imm(a[0])
            w = ({"j": 2, "jal": 3}[op] << 26) | ((t >> 2) & 0x3FFFFFF)
        elif op == "jr":
            w = R(r(a[0]), 0, 0, 0, 0x08)
        elif op == "jalr":
            w = R(r(a[0]), 0, 31, 0, 0x09)
        else:
            raise ValueError(f"unknown op {op}")
        out.append(w)
        pc += 4
    return out, labels

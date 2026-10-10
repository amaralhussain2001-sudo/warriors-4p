"""Build and arm frame-exact controller input for the Stage 1 experiment patch v2 (e1_v2.pnach).

Table layout (F-0051, F-0052): base 0x00098000, frame-major, 8 pads x 8 bytes:
  u16 buttons (game codes, 1 = pressed), u8 lx, u8 ly, u8 rx, u8 ry, u8 pad[2]; sticks rest at 0x7F, 0x00 = up/left.
Control block 0x000F0200: +0 pad mask, +4 base frame (game frame counter 0x0050C654), +8 frame count.

Scripts are deterministic (seeded) so two instances get byte-identical tables.
Usage (library): build_script(name, frames, seed) -> bytes ; arm(pine, table, base_frame, pad_mask)
"""
import random
import struct

TABLE = 0x00098000
CTRL = 0x000F0200
MAX_FRAMES = (0x000F0000 - TABLE) // 64

BTN = {"L2": 0x1, "R2": 0x2, "L1": 0x4, "R1": 0x8, "TRI": 0x10, "CIR": 0x20, "X": 0x40, "SQ": 0x80,
       "SEL": 0x100, "START": 0x800, "UP": 0x1000, "RIGHT": 0x2000, "DOWN": 0x4000, "LEFT": 0x8000}
NEUTRAL = 0x7F


def entry(buttons=0, lx=NEUTRAL, ly=NEUTRAL, rx=NEUTRAL, ry=NEUTRAL):
    return struct.pack("<HBBBBBB", buttons, lx, ly, rx, ry, 0, 0)


def build_script(name, frames, seed=1, pads=(0,)):
    """'brawl': press X to start, then alternate moving and attacking with a seeded pattern."""
    assert frames <= MAX_FRAMES
    rng = random.Random(seed)
    rows = []
    plan = []
    t = 0
    if name in ("brawl", "brawl_nomove"):
        plan.append((0, 4, {"buttons": BTN["X"]}))
        plan.append((4, 40, {}))
        t = 44
        while t < frames:
            dur = rng.randint(10, 45)
            kind = rng.choice(["walk", "walk", "attack", "attack", "grab", "idle"])
            if kind == "walk" and name == "brawl_nomove":
                spec = {}
            elif kind == "walk":
                spec = {"lx": rng.choice([0x00, 0x7F, 0xFF]), "ly": rng.choice([0x00, 0x00, 0x7F, 0xFF])}
            elif kind == "attack":
                spec = {"buttons_pulse": rng.choice([BTN["SQ"], BTN["X"], BTN["SQ"] | BTN["X"]])}
                if name == "brawl":
                    spec["ly"] = 0x00
            elif kind == "grab":
                spec = {"buttons_pulse": BTN["CIR"]}
            else:
                spec = {}
            plan.append((t, dur, spec))
            t += dur
    else:
        raise ValueError(name)
    for f in range(frames):
        spec = {}
        start = 0
        for s, d, sp in plan:
            if s <= f < s + d:
                spec, start = sp, s
                break
        buttons = spec.get("buttons", 0)
        if "buttons_pulse" in spec and (f - start) % 6 < 2:
            buttons |= spec["buttons_pulse"]
        row = bytearray(64)
        for pidx in range(8):
            if pidx in pads:
                row[pidx * 8:(pidx + 1) * 8] = entry(buttons, spec.get("lx", NEUTRAL), spec.get("ly", NEUTRAL))
            else:
                row[pidx * 8:(pidx + 1) * 8] = entry()
        rows.append(bytes(row))
    return b"".join(rows)


def arm(pine, table, base_frame, pad_mask):
    frames = len(table) // 64
    pine.write32(CTRL, 0)                      # disable while writing
    pine.write_bytes(TABLE, table)
    pine.batch_write32([(CTRL + 4, base_frame), (CTRL + 8, frames), (CTRL, pad_mask)])
    return frames

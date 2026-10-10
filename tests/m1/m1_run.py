"""M1 runner: two W4P fork instances in lockstep over loopback UDP from the same 2-player mission state.

Usage: python -I tests/m1/m1_run.py <tag> <seconds> [--delay 2] [--latency 0] [--jitter 0] [--loss 0]
                                     [--nocrop] [--corrupt N] [--shots 60] [--state m1_start_m9_2p.p2s]
Writes: local/m1/<tag>/ (logs, bot files, screenshots, dumps), evidence/M1/<tag>.json (summary).
Environment label: SINGLE-PC, scripted bots on both slots, impairment as configured.
"""
import json
import os
import random
import re
import shutil
import struct
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(PROJ, "tools"))
import sandbox  # noqa: E402
from pine import Pine  # noqa: E402

INSTS = {0: 2, 1: 3}  # slot -> sandbox instance number
PADS = {0: 0, 1: 4}   # slot -> game pad index (original 2-player mode: port 1 slot A, port 2 slot A)
PORTS = {0: 41000, 1: 41001}
PATCH = os.path.join(PROJ, "mod", "w4p_m1.pnach")

BTN = {"L2": 0x1, "R2": 0x2, "L1": 0x4, "R1": 0x8, "TRI": 0x10, "CIR": 0x20, "X": 0x40, "SQ": 0x80,
       "UP": 0x1000, "RIGHT": 0x2000, "DOWN": 0x4000, "LEFT": 0x8000}
PRESSURE_ORDER = ["RIGHT", "LEFT", "UP", "DOWN", "TRI", "CIR", "X", "SQ", "L1", "R1", "L2", "R2"]


def record(buttons=0, lx=0x7F, ly=0x7F, rx=0x7F, ry=0x7F):
    pressure = bytes(0xFF if buttons & BTN[n] else 0 for n in PRESSURE_ORDER)
    return struct.pack("<HBBBB", buttons, lx, ly, rx, ry) + pressure + bytes([1, 0])


def bot_file(path, seed, polls, idle=0):
    """Seeded bot: walks in random directions, attacks, grabs, sometimes turns the camera. Never presses
    Start/Select (pause menus are a session policy handled later)."""
    rng = random.Random(seed)
    out = bytearray()
    for _ in range(idle):
        out += record()
    t = idle
    while t < polls:
        dur = rng.randint(15, 60)
        kind = rng.choice(["walk", "walk", "walk", "attack", "attack", "grab", "camera", "idle"])
        lx, ly, rx, ry, pulse = 0x7F, 0x7F, 0x7F, 0x7F, 0
        if kind == "walk":
            lx, ly = rng.choice([(0x7F, 0x00), (0x00, 0x7F), (0xFF, 0x7F), (0x7F, 0xFF), (0x20, 0x20), (0xE0, 0x20)])
        elif kind == "attack":
            pulse = rng.choice([BTN["SQ"], BTN["X"], BTN["SQ"] | BTN["X"]])
            lx, ly = rng.choice([(0x7F, 0x7F), (0x7F, 0x00)])
        elif kind == "grab":
            pulse = BTN["CIR"]
        elif kind == "camera":
            rx = rng.choice([0x00, 0xFF])
        for k in range(dur):
            b = pulse if (pulse and k % 8 < 3) else 0
            out += record(b, lx, ly, rx, ry)
        t += dur
    open(path, "wb").write(bytes(out))


def write_ini(path, slot, out_dir, args):
    other = 1 - slot
    lines = ["[W4P]", "Enabled = true", "Players = 2", f"LocalSlot = {slot}",
             f"PadForSlot0 = {PADS[0]}", f"PadForSlot1 = {PADS[1]}",
             f"ListenPort = {PORTS[slot]}", f"Peer{other} = 127.0.0.1:{PORTS[other]}",
             f"InputDelay = {args['delay']}", "HashInterval = 30",
             f"LogFile = {os.path.join(out_dir, f'w4p_slot{slot}.log')}",
             f"DumpDir = {out_dir}", f"BotInput = {os.path.join(out_dir, f'bot_slot{slot}.bin')}",
             f"ImpairLatencyMs = {args['latency'] // 2}", f"ImpairJitterMs = {args['jitter']}",
             f"ImpairLoss = {args['loss']}", f"ImpairSeed = {17 + slot}",
             f"Crop = {'false' if args['nocrop'] else 'true'}"]
    if args["corrupt"] is not None and slot == 1:
        lines.append(f"TestCorruptPoll = {args['corrupt']}")
    open(path, "w", encoding="utf-8").write("\n".join(lines) + "\n")


def opt(name, default, cast=int):
    return cast(sys.argv[sys.argv.index(name) + 1]) if name in sys.argv else default


def main():
    tag, seconds = sys.argv[1], int(sys.argv[2])
    args = {"delay": opt("--delay", 2), "latency": opt("--latency", 0), "jitter": opt("--jitter", 0),
            "loss": opt("--loss", 0.0, float), "nocrop": "--nocrop" in sys.argv, "corrupt": opt("--corrupt", None),
            "shots": opt("--shots", 60), "state": opt("--state", "m1_start_m9_2p.p2s", str)}
    out_dir = os.path.join(PROJ, "local", "m1", tag)
    if os.path.exists(out_dir):
        shutil.rmtree(out_dir)
    os.makedirs(out_dir)
    state = os.path.join(PROJ, "local", args["state"])
    procs = {}
    for slot, n in INSTS.items():
        d = sandbox.inst_dir(n)
        if os.path.exists(d):
            shutil.rmtree(d)
        sandbox.make(n, "default", pad2=True)  # both ports connected on every instance (identical libpad state)
        sandbox.install_patch(n, PATCH, ["warriors-4p M1"])
        for m in ("Mcd001.ps2", "Mcd002.ps2"):
            shutil.copyfile(os.path.join(PROJ, "local", m), os.path.join(sandbox.data_root(n), "memcards", m))
        bot_file(os.path.join(out_dir, f"bot_slot{slot}.bin"), 1000 + slot, 40000, opt("--idle", 0))
        ini = os.path.join(out_dir, f"w4p_slot{slot}.ini")
        write_ini(ini, slot, out_dir, args)
        env = dict(os.environ, W4P_CONFIG=ini)
        cmd = [sandbox.FORK_EXE] + sandbox.cmd(n, ["-statefile", state])[1:]
        procs[slot] = subprocess.Popen(cmd, env=env, creationflags=getattr(subprocess, "DETACHED_PROCESS", 0))
        open(os.path.join(d, "pid.txt"), "w").write(str(procs[slot].pid))
    t_start = time.time()
    shots = []
    alive = {}
    first = opt("--firstshot", 20)
    next_shot = time.time() + first
    while time.time() - t_start < seconds:
        time.sleep(2)
        alive = {s: procs[s].poll() is None for s in procs}
        if not all(alive.values()):
            break
        if time.time() >= next_shot:
            next_shot += args["shots"]
            for slot, n in INSTS.items():
                name = f"m1_{tag}_s{slot}_{int(time.time() - t_start):04d}"
                subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                                os.path.join(PROJ, "tools", "winshot.ps1"), "-ProcessId", str(procs[slot].pid),
                                "-Out", os.path.join(out_dir, name + ".png"), "-Scale", "0.4"], capture_output=True)
                shots.append(name)
    views = {}
    for slot, n in INSTS.items():
        try:
            p = Pine(sandbox.PINE_BASE + n, timeout=3)
            views[slot] = {"views": p.read32(0x0050B198), "cams": p.read32(0x0050B19C), "counter": p.read32(0x000F0500)}
        except Exception as e:  # noqa: BLE001
            views[slot] = repr(e)
    for slot, n in INSTS.items():
        subprocess.run([sys.executable, "-I", os.path.join(PROJ, "tools", "sandbox.py"), "kill", str(n)], capture_output=True)
    for slot in INSTS:
        try:
            procs[slot].wait(15)  # make sure the log files are closed before reading them
        except subprocess.TimeoutExpired:
            pass
    # independent hash comparison from the two logs
    hashes = {}
    stats = {}
    for slot in INSTS:
        txt = open(os.path.join(out_dir, f"w4p_slot{slot}.log"), encoding="utf-8", errors="replace").read()
        hashes[slot] = dict(re.findall(r"^HASH (\d+) ([0-9a-f]+)$", txt, re.M))
        st = re.findall(r"stats: (.*)$", txt, re.M)
        stats[slot] = st[-1] if st else None
        stats[f"{slot}_desync_lines"] = re.findall(r"DESYNC.*$", txt, re.M)[:5]
        stats[f"{slot}_errors"] = re.findall(r"ERROR.*$", txt, re.M)[:5]
    common = sorted(set(hashes[0]) & set(hashes[1]), key=int)
    mism = [t for t in common if hashes[0][t] != hashes[1][t]]
    summary = {"tag": tag, "seconds_run": round(time.time() - t_start), "args": args, "alive_at_end": alive,
               "hash_points_common": len(common), "hash_mismatches": len(mism), "first_mismatch_poll": mism[0] if mism else None,
               "last_common_poll": common[-1] if common else None, "stats": stats, "views_at_end": views,
               "screenshots": shots,
               "environment": "SINGLE-PC, loopback UDP, scripted bots on both slots, "
                              + ("impairment on" if args["latency"] or args["jitter"] or args["loss"] else "no impairment")}
    os.makedirs(os.path.join(PROJ, "evidence", "M1"), exist_ok=True)
    with open(os.path.join(PROJ, "evidence", "M1", f"{tag}.json"), "w") as fh:
        json.dump(summary, fh, indent=1)
    print(json.dumps({k: v for k, v in summary.items() if k != "screenshots"}, indent=1))


if __name__ == "__main__":
    main()

"""60 fps probe: run the two-instance lockstep session (bots) with extra game patch lines and an EE clock setting,
and measure the game's frame rate, game-time speed and sync.

Usage: python -I tests/m3/fps_probe.py <tag> [--seconds 40] [--ee 0] [--fps60] [--wait 12] [--crop]
                                         [--gs key=value,key=value] [--shot-scale 0.5]
  --gs      extra EmuCore/GS settings on both instances (default: the user's settings, upscale 1x)
  --crop    show each player's own view (default: crop off)
  --gs1     EmuCore/GS settings for the second instance only (applied after --gs)
  --walk    player 1 walks straight ahead from the start, player 2 stands still; reports player 1's speed
  --groups  extra pnach groups, separated by ';' (e.g. "warriors-4p 60fps")
  --fps60   add PCSX2's disabled "60 FPS" line (EE byte 0x00596D70 = 1, applied every vsync)
  --ee N    EmuCore/Speedhacks EECycleRate on both instances (0 = 100 %, 1 = 130 %, 2 = 180 %, 3 = 300 %)
Writes local/m3/<tag>/ and evidence/M3/<tag>.json. Environment: SINGLE-PC, bots, no impairment, native resolution.
"""
import configparser
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(PROJ, "tools"))
sys.path.insert(0, os.path.join(PROJ, "tests", "m1"))
import m1_run  # noqa: E402
import sandbox  # noqa: E402
from pine import Pine  # noqa: E402

FRAME_COUNTER = 0x0050C654
VIEWS = 0x0050B198
GAMECLOCK_PTR = 0x0050B734


def opt(name, default, cast=int):
    return cast(sys.argv[sys.argv.index(name) + 1]) if name in sys.argv else default


def set_ini(n, section, key, value):
    path = os.path.join(sandbox.data_root(n), "inis", "PCSX2.ini")
    cp = configparser.ConfigParser(interpolation=None, strict=False)
    cp.optionxform = str
    cp.read(path, encoding="utf-8")
    if not cp.has_section(section):
        cp.add_section(section)
    cp.set(section, key, value)
    with open(path, "w", encoding="utf-8") as fh:
        cp.write(fh, space_around_delimiters=True)


def measure_motion(p, secs):
    """Does the game state advance on every counted frame? Reads player 1's position and the game clock as fast
    as possible and keeps one reading per game frame number."""
    f = lambda v: struct.unpack("<f", struct.pack("<I", v))[0]  # noqa: E731
    # pick the character that moves the most over one second (any human object; players or enemies)
    objs = [0x00640C80 + k * 0x6D0 for k in range(-40, 120)]
    objs = [o for o in objs if o >= 0x00597200 and o + 0x6D0 <= 0x00715B5C]
    pos = lambda o: tuple(f(p.read32(o + 0x10 + 4 * i)) for i in range(3))  # noqa: E731
    before = {o: pos(o) for o in objs}
    time.sleep(1.0)
    best, human = 0.0, None
    for o in objs:
        a, b = before[o], pos(o)
        if all(abs(v) < 1e5 for v in a + b):
            d = sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5
            if d > best:
                best, human = d, o
    if human is None:
        return {"error": "no moving character found"}
    per_frame = {}
    t0 = time.perf_counter()
    while time.perf_counter() - t0 < secs:
        fr = p.read32(FRAME_COUNTER)
        clock = p.read32(GAMECLOCK_PTR)
        pos = tuple(round(f(p.read32(human + 0x10 + 4 * i)), 4) for i in range(3))
        gt = p.read32(clock + 0x48)
        if p.read32(FRAME_COUNTER) == fr and fr not in per_frame:
            per_frame[fr] = (pos, gt)
    frames = sorted(per_frame)
    consecutive = [(a, b) for a, b in zip(frames, frames[1:]) if b == a + 1]
    moved = sum(1 for a, b in consecutive if per_frame[a][0] != per_frame[b][0])
    clock_steps = [(per_frame[b][1] - per_frame[a][1]) & 0xFFFFFFFF for a, b in consecutive]
    return {"object": hex(human), "moved_in_1s": round(best, 2), "frames_seen": len(frames), "consecutive_pairs": len(consecutive),
            "pairs_where_position_changed": moved, "pairs_where_game_clock_advanced": sum(1 for c in clock_steps if c),
            "game_clock_step_ms_values": sorted(set(clock_steps))[:12]}


def player_pos(p, idx):
    """Player idx's position via GameMgr (0x0051489C) +0x228 handle -> object table 0x006EBD38 (F-0020, F-0022)."""
    f = lambda v: struct.unpack("<f", struct.pack("<I", v))[0]  # noqa: E731
    gm = p.read32(0x0051489C)
    h = p.read32(gm + 0x228 + 4 * idx)
    obj = p.read32(0x006EBD38 + 8 * (h >> 16))
    return tuple(f(p.read32(obj + 0x10 + 4 * i)) for i in range(3))


def player_track(p, secs):
    """Player 1's ground speed (units per second of real time and of game time) while walking."""
    t0 = time.perf_counter()
    clock = p.read32(GAMECLOCK_PTR)
    a, g0 = player_pos(p, 0), p.read32(clock + 0x48)
    path, last = 0.0, a
    while time.perf_counter() - t0 < secs:
        time.sleep(0.05)
        b = player_pos(p, 0)
        path += ((b[0] - last[0]) ** 2 + (b[2] - last[2]) ** 2) ** 0.5
        last = b
    dt = time.perf_counter() - t0
    dg = (p.read32(clock + 0x48) - g0) / 1000.0
    return {"path_units": round(path, 3), "real_s": round(dt, 2), "game_s": round(dg, 2),
            "speed_per_real_s": round(path / dt, 3), "speed_per_game_s": round(path / dg, 3) if dg else None}


def main():
    tag = sys.argv[1]
    seconds, wait, ee = opt("--seconds", 40), opt("--wait", 12), opt("--ee", 0)
    fps60 = "--fps60" in sys.argv
    out_dir = os.path.join(PROJ, "local", "m3", tag)
    if os.path.exists(out_dir):
        shutil.rmtree(out_dir)
    os.makedirs(out_dir)
    patch = os.path.join(out_dir, "probe.pnach")
    txt = open(m1_run.PATCH, encoding="utf-8").read().rstrip("\n") + "\n"
    if fps60:
        txt += "patch=1,EE,00596D70,byte,01 // PCSX2 patches.zip, disabled '60 FPS' entry (PeterDelta)\n"
    open(patch, "w", encoding="utf-8").write(txt)
    args = {"delay": 2, "latency": 0, "jitter": 0, "loss": 0.0, "nocrop": "--crop" not in sys.argv, "corrupt": None}
    gs = dict(kv.split("=", 1) for kv in opt("--gs", "", str).split(",") if kv)
    state = os.path.join(PROJ, "local", "m1_start_m9_2p.p2s")
    procs = {}
    for slot, n in m1_run.INSTS.items():
        d = sandbox.inst_dir(n)
        if os.path.exists(d):
            shutil.rmtree(d)
        sandbox.make(n, "default", pad2=True)
        set_ini(n, "EmuCore/Speedhacks", "EECycleRate", str(ee))
        set_ini(n, "EmuCore/GS", "OsdShowVPS", "true")
        for k, v in gs.items():
            set_ini(n, "EmuCore/GS", k, v)
        if slot == 1:  # per-instance graphics differences (graphics must not affect sync)
            for kv in opt("--gs1", "", str).split(","):
                if kv:
                    set_ini(n, "EmuCore/GS", *kv.split("=", 1))
        sandbox.install_patch(n, patch, ["warriors-4p M1"] + [g for g in opt("--groups", "", str).split(";") if g])
        for m in ("Mcd001.ps2", "Mcd002.ps2"):
            shutil.copyfile(os.path.join(PROJ, "local", m), os.path.join(sandbox.data_root(n), "memcards", m))
        if "--walk" in sys.argv:  # player 1 walks straight ahead, player 2 stands still (speed parity)
            open(os.path.join(out_dir, f"bot_slot{slot}.bin"), "wb").write(
                (m1_run.record(ly=0x00) if slot == 0 else m1_run.record()) * 40000)
        else:
            m1_run.bot_file(os.path.join(out_dir, f"bot_slot{slot}.bin"), 1000 + slot, 40000)
        ini = os.path.join(out_dir, f"w4p_slot{slot}.ini")
        m1_run.write_ini(ini, slot, out_dir, args)
        env = dict(os.environ, W4P_CONFIG=ini)
        cmd = [sandbox.FORK_EXE] + sandbox.cmd(n, ["-statefile", state])[1:]
        procs[slot] = subprocess.Popen(cmd, env=env, creationflags=getattr(subprocess, "DETACHED_PROCESS", 0))
        open(os.path.join(d, "pid.txt"), "w").write(str(procs[slot].pid))
    time.sleep(wait)
    p = Pine(sandbox.PINE_BASE + m1_run.INSTS[0])
    walk = player_track(p, 3.0) if "--walk" in sys.argv else None
    smi = subprocess.Popen(["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,power.draw", "--format=csv,noheader,nounits",
                            "-lms", "500"], stdout=subprocess.PIPE, text=True)
    samples = []
    t0 = time.perf_counter()
    while time.perf_counter() - t0 < seconds:
        clock = p.read32(GAMECLOCK_PTR)
        gt = p.read32(clock + 0x48) if 0x100000 <= clock < 0x2000000 else 0
        samples.append((time.perf_counter() - t0, p.read32(FRAME_COUNTER), p.read32(VIEWS), gt))
        time.sleep(0.25)
    smi.terminate()
    gpu = [[float(x) for x in line.split(",")] for line in smi.stdout.read().splitlines() if line.count(",") == 2]
    gpu_stats = {"util_avg": round(sum(g[0] for g in gpu) / len(gpu), 1), "util_max": max(g[0] for g in gpu),
                 "mem_mb_max": max(g[1] for g in gpu), "power_w_avg": round(sum(g[2] for g in gpu) / len(gpu))} if gpu else None
    motion = measure_motion(p, 6.0)
    shot = os.path.join(out_dir, "slot0_end.png")
    subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", os.path.join(PROJ, "tools", "winshot.ps1"),
                    "-ProcessId", str(procs[0].pid), "-Out", shot, "-Scale", str(opt("--shot-scale", 0.5, float))], capture_output=True)
    for slot, n in m1_run.INSTS.items():
        subprocess.run([sys.executable, "-I", os.path.join(PROJ, "tools", "sandbox.py"), "kill", str(n)], capture_output=True)
    for slot in procs:
        try:
            procs[slot].wait(15)
        except subprocess.TimeoutExpired:
            pass
    # per-second windows: game frames per second and game time (two readings: u32 ms and float ms)
    windows = []
    for i in range(len(samples)):
        j = next((k for k in range(i, len(samples)) if samples[k][0] - samples[i][0] >= 4.0), None)
        if j is None:
            break
        dt = samples[j][0] - samples[i][0]
        g_u = (samples[j][3] - samples[i][3]) & 0xFFFFFFFF
        g_f = struct.unpack("<f", struct.pack("<I", samples[j][3]))[0] - struct.unpack("<f", struct.pack("<I", samples[i][3]))[0]
        windows.append({"t": round(samples[i][0], 1), "fps": round((samples[j][1] - samples[i][1]) / dt, 2),
                        "views": samples[i][2], "gametime_u32_per_s": round(g_u / dt, 1), "gametime_f32_per_s": round(g_f / dt, 1)})
    windows = windows[::16]
    hashes = {}
    for slot in procs:
        log = open(os.path.join(out_dir, f"w4p_slot{slot}.log"), encoding="utf-8", errors="replace").read()
        hashes[slot] = dict(re.findall(r"^HASH (\d+) ([0-9a-f]+)$", log, re.M))
    common = sorted(set(hashes[0]) & set(hashes[1]), key=int)
    total_fps = (samples[-1][1] - samples[0][1]) / (samples[-1][0] - samples[0][0])
    summary = {"tag": tag, "fps60_patch": fps60, "ee_cycle_rate": ee, "seconds": seconds, "avg_game_fps": round(total_fps, 2),
               "gs": gs, "crop": "--crop" in sys.argv, "gpu_two_instances": gpu_stats, "windows": windows, "motion": motion, "walk": walk, "hash_points_common": len(common),
               "hash_mismatches": sum(1 for t in common if hashes[0][t] != hashes[1][t]),
               "environment": "SINGLE-PC, bots, no impairment, native resolution, crop off"}
    os.makedirs(os.path.join(PROJ, "evidence", "M3"), exist_ok=True)
    json.dump(summary, open(os.path.join(PROJ, "evidence", "M3", f"{tag}.json"), "w"), indent=1)
    print(f"{tag}: fps60={fps60} ee={ee} avg game fps {total_fps:.2f}; hash points {len(common)}, mismatches {summary['hash_mismatches']}")
    for w in windows:
        print("  ", w)
    print("  motion:", motion)
    print("  walk:", walk)
    print("  gpu (both instances together):", gpu_stats)


if __name__ == "__main__":
    main()

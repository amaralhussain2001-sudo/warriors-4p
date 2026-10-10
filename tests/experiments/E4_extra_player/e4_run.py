"""E4 what-breaks run: make an AI companion player 3 through the engine's own MakePlayer, drive it from pad 1.
Usage: python -I e4_run.py [--pad 1] [--player 2] [--no-limits]
"""
import json
import math
import os
import shutil
import struct
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(PROJ, "tools"))
import inject  # noqa: E402
import sandbox  # noqa: E402
from pine import Pine  # noqa: E402

N = 4
STATE = os.path.join(PROJ, "local", "e4_start_m1_2p.p2s")
if "--state" in sys.argv:
    STATE = os.path.join(PROJ, "local", sys.argv[sys.argv.index("--state") + 1])
PATCH = os.path.join(HERE, "e4_v3.pnach")
MAKEPLAYER = 0x00229C40
CALL = 0x000F0300
OBJTAB = 0x006EBD38
POOL0, STRIDE = 0x00640C80, 0x6D0


def f32(p, a):
    return struct.unpack("<f", struct.pack("<I", p.read32(a)))[0]


def shot(name):
    pid = open(os.path.join(sandbox.inst_dir(N), "pid.txt")).read().strip()
    r = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                        os.path.join(PROJ, "tools", "winshot.ps1"), "-ProcessId", pid, "-Out",
                        os.path.join(PROJ, "local", "shots", name + ".png"), "-Scale", "0.4"], capture_output=True, text=True)
    return r.stdout.strip()


def players(p):
    mgr = p.read32(0x0051489C)
    cnt = struct.unpack("<h", struct.pack("<H", p.read32(mgr + 0x224) & 0xFFFF))[0]
    return mgr, cnt, [p.read32(mgr + 0x228 + 4 * i) for i in range(4)]


def handle_of(p, obj):
    for idx in range(0, 512):
        if p.read32(OBJTAB + idx * 8) == obj:
            return (idx << 16) | (p.read32(OBJTAB + idx * 8 + 4) & 0xFFFF)
    return None


def pad_table(frames, lx=0x7F, ly=0x7F, pads=(1,)):
    rows = []
    for _ in range(frames):
        row = bytearray(64)
        for k in range(8):
            row[k * 8:(k + 1) * 8] = inject.entry(0, lx, ly) if k in pads else inject.entry()
        rows.append(bytes(row))
    return b"".join(rows)


def main():
    pad = int(sys.argv[sys.argv.index("--pad") + 1]) if "--pad" in sys.argv else 1
    pidx = int(sys.argv[sys.argv.index("--player") + 1]) if "--player" in sys.argv else 2
    groups = ["warriors4p base v3"] + ([] if "--no-limits" in sys.argv else ["warriors4p E4 limits"])
    d = sandbox.inst_dir(N)
    if os.path.exists(d):
        shutil.rmtree(d)
    sandbox.make(N, "default", pad2=True)
    sandbox.install_patch(N, PATCH, groups)
    for m in ("Mcd001.ps2", "Mcd002.ps2"):
        shutil.copyfile(os.path.join(sandbox.data_root(1), "memcards", m), os.path.join(sandbox.data_root(N), "memcards", m))
    proc = subprocess.Popen(sandbox.cmd(N, ["-statefile", STATE]), creationflags=getattr(subprocess, "DETACHED_PROCESS", 0))
    open(os.path.join(d, "pid.txt"), "w").write(str(proc.pid))
    log = {"groups": groups, "pad": pad, "player_index": pidx}
    p = None
    for _ in range(120):
        try:
            p = Pine(sandbox.PINE_BASE + N, timeout=5)
            if p.read32(0x0050C654) > 100:
                break
        except (OSError, RuntimeError):
            pass
        time.sleep(0.5)
    time.sleep(2)
    mgr, cnt, hs = players(p)
    log["before"] = {"count": cnt, "handles": [f"{h:08x}" for h in hs], "tick_230": p.read32(mgr + 0x230)}
    p1 = hs[0]
    p1obj = p.read32(OBJTAB + (p1 >> 16) * 8)
    p1pos = [f32(p, p1obj + 0x10 + 4 * k) for k in range(3)]
    extra = int(sys.argv[sys.argv.index("--extra") + 1]) if "--extra" in sys.argv else 1
    pads = tuple(range(pad, pad + extra))
    mask = sum(1 << k for k in pads)
    log["pads"] = list(pads)
    # 1) make the pads connected & neutral for the whole run
    now = p.read32(0x0050C654)
    inject.arm(p, pad_table(1800, pads=pads), now + 5, mask)
    time.sleep(1.0)
    log["pad_connected_flag"] = p.read32(0x005DD810 + pad * 0x50 + 0x4C)
    log["pad_owner_before"] = struct.unpack("<h", struct.pack("<H", p.read32(0x005DD810 + pad * 0x50 + 0x40) >> 16))[0]
    # 2) nearest AI humans
    cands = []
    for k in range(-60, 60):
        o = POOL0 + k * STRIDE
        if o < 0x00597200 or o + STRIDE > 0x00715B5C or o in (p1obj,):
            continue
        pos = [f32(p, o + 0x10 + i * 4) for i in range(3)]
        if not all(abs(v) < 5000 for v in pos) or all(abs(v) < 0.01 for v in pos):
            continue
        if (p.read32(o + 0x1B0) & 0xFF) != 0xFF:
            continue
        dist = math.dist(pos, p1pos)
        h = handle_of(p, o)
        if h is not None:
            cands.append((dist, o, h, pos))
    cands.sort()
    chosen = cands[:extra]
    log["candidates"] = [{"dist": round(c[0], 2), "obj": f"{c[1]:08x}", "handle": f"{c[2]:08x}",
                          "pos": [round(v, 2) for v in c[3]]} for c in chosen]
    log["shot_before"] = shot("e4_before")
    # 3) MakePlayer(human, pad, hud=-1, player=-1 -> append) on the game thread, once per companion
    log["calls"] = []
    for (dist, obj, h, pos), pd in zip(chosen, pads):
        p.batch_write32([(CALL + 4, obj), (CALL + 8, pd), (CALL + 0xC, 0xFFFFFFFF), (CALL + 0x10, 0xFFFF),
                         (CALL + 0x18, 0), (CALL, MAKEPLAYER)])
        for _ in range(100):
            if p.read32(CALL + 0x18) == 1:
                break
            time.sleep(0.05)
        mgr_, cnt_, hs_ = players(p)
        log["calls"].append({"obj": f"{obj:08x}", "pad": pd, "done": p.read32(CALL + 0x18),
                             "result": p.read32(CALL + 0x14), "count_after": cnt_,
                             "handles_after": [f"{x:08x}" for x in hs_],
                             "playerIdx": struct.unpack("<b", bytes([p.read32(obj + 0x1B0) & 0xFF]))[0],
                             "hudslot_380": p.read32(obj + 0x380)})
        time.sleep(0.5)
    obj = chosen[-1][1]
    pad = pads[-1]
    mgr, cnt, hs = players(p)
    ctrl = 0x00660F50 + struct.unpack("<h", struct.pack("<H", p.read32(obj + 0x90) >> 16))[0] * 0x2C
    log["after"] = {"count": cnt, "handles": [f"{h:08x}" for h in hs], "tick_230": p.read32(mgr + 0x230),
                    "human_playerIdx": struct.unpack("<b", bytes([p.read32(obj + 0x1B0) & 0xFF]))[0],
                    "human_hudslot_380": p.read32(obj + 0x380),
                    "controller_pad_19": struct.unpack("<b", bytes([(p.read32(ctrl + 0x18) >> 8) & 0xFF]))[0],
                    "pad_owner_42": struct.unpack("<h", struct.pack("<H", p.read32(0x005DD810 + pad * 0x50 + 0x40) >> 16))[0]}
    log["shot_after_make"] = shot("e4_after_make")
    # 4) drive pad `pad`: 3 s up, then 3 s right; track positions of the new player and player 1
    now = p.read32(0x0050C654)
    secs = int(sys.argv[sys.argv.index("--walk") + 1]) if "--walk" in sys.argv else 3
    tab = pad_table(30 * secs, ly=0x00, pads=pads) + pad_table(30 * secs, lx=0xFF, pads=pads) + pad_table(600, pads=pads)
    inject.arm(p, tab, now + 3, mask)
    others = [c[1] for c in chosen]
    track = []
    for i in range(2 * secs + 1):
        time.sleep(1.0)
        if i % 2 == 1:
            shot(f"e4walk_{i:02d}")
        try:
            track.append({"t": i + 1, "new_players": [[round(f32(p, o + 0x10 + 4 * k), 2) for k in range(2)] for o in others],
                          "p1": [round(f32(p, p1obj + 0x10 + 4 * k), 2) for k in range(3)],
                          "frame": p.read32(0x0050C654), "status": p.status(),
                          "views": p.read32(0x0050B198), "cams": p.read32(0x0050B19C)})
        except Exception as e:  # noqa: BLE001
            track.append({"t": i + 1, "error": repr(e)})
            break
    log["track"] = track
    log["shot_after_drive"] = shot("e4_after_drive")
    try:
        log["final_status"] = p.status()
        log["views_rendered"] = p.read32(0x0050B198)
        log["cameras"] = p.read32(0x0050B19C)
        log["camera_arrays"] = [f"{p.read32(0x005D9148 + 4 * i):08x}" for i in range(10)]
    except Exception as e:  # noqa: BLE001
        log["final_status"] = repr(e)
    tail = open(os.path.join(sandbox.data_root(N), "logs", "emulog.txt"), encoding="utf-8", errors="replace").read().splitlines()[-25:]
    log["emulog_tail_lines"] = len(tail)  # full log stays in local/ (may contain game disassembly)
    os.makedirs(os.path.join(PROJ, "evidence", "E4"), exist_ok=True)
    tag = "e4_" + ("limits" if "--no-limits" not in sys.argv else "nolimits") + f"_extra{extra}"
    with open(os.path.join(PROJ, "evidence", "E4", tag + ".json"), "w") as fh:
        json.dump(log, fh, indent=1)
    print(json.dumps({k: v for k, v in log.items() if k != "emulog_tail"}, indent=1))


if __name__ == "__main__":
    main()

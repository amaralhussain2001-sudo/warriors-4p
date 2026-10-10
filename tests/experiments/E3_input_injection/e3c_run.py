"""E3c: pause the whole emulated machine (PCSX2 TogglePause hotkey) in instance B only, repeatedly.

Hypothesis (declared before running): whole-VM pauses freeze all emulated time (EE, IOP, timers, audio), so B ends
identical to A apart from the known host-timing counters, unlike in-game waiting (E3b).
Usage: python -I e3c_run.py <tag> <N> <pauses> <pause_ms>
"""
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(PROJ, "tools"))
sys.path.insert(0, os.path.join(PROJ, "tests", "experiments", "E1_determinism"))
import e1_run_v2 as e1  # noqa: E402
import inject  # noqa: E402


def hotkey(n, key):
    pid = open(os.path.join(PROJ, "local", "pcsx2", f"inst{n}", "pid.txt")).read().strip()
    subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                    os.path.join(PROJ, "tools", "winkeys.ps1"), "-ProcessId", pid, "-Seq", f"{key}:60"],
                   capture_output=True)


def main():
    tag, N, pauses, pause_ms = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
    e1.setup("default")
    e1.launch()
    pines = {n: e1.connect(n) for n in e1.INSTS}
    c0 = {n: pines[n].read32(e1.FRAME_CTR) for n in e1.INSTS}
    base = max(c0.values()) + 150
    target = base + N
    table = inject.build_script("brawl", N + 30, seed=7)
    for n in e1.INSTS:
        inject.arm(pines[n], table, base, 0x1)
        pines[n].write32(e1.MB_TARGET, target)
    b = e1.INSTS[1]
    while pines[b].read32(e1.FRAME_CTR) < base:
        time.sleep(0.01)
    done = 0
    statuses = []
    interval = (N / 30.0) / (pauses + 1)
    while done < pauses and pines[b].read32(e1.MB_REACHED) != target:
        time.sleep(interval * 0.5)
        hotkey(b, "Space")
        time.sleep(pause_ms / 1000.0)
        statuses.append(pines[b].status())
        hotkey(b, "Space")
        done += 1
    while not all(pines[n].read32(e1.MB_REACHED) == target for n in e1.INSTS):
        if pines[b].status() == "paused":
            hotkey(b, "Space")
        time.sleep(0.2)
    dumps = {n: pines[n].dump(0, 0x02000000) for n in e1.INSTS}
    out_local = os.path.join(PROJ, "local", "e1", tag)
    os.makedirs(out_local, exist_ok=True)
    for n in e1.INSTS:
        open(os.path.join(out_local, f"inst{n}.bin"), "wb").write(dumps[n])
        subprocess.run([sys.executable, "-I", os.path.join(PROJ, "tools", "sandbox.py"), "kill", str(n)], capture_output=True)
    a, bb = dumps[e1.INSTS[0]], dumps[b]
    rs = e1.diff(a, bb)
    summary = {"tag": tag, "N": N, "pauses_done": done, "pause_ms": pause_ms,
               "status_while_paused": statuses,
               "differing_bytes": sum(sum(1 for k in range(s, e) if a[k] != bb[k]) for s, e in rs),
               "range_count": len(rs), "ranges": [{"start": f"{s:08x}", "len": e - s} for s, e in rs[:300]],
               "environment": "SINGLE-PC, scripted bot input pad 0, whole-VM pauses on B via hotkey, PCSX2 v2.9.115 sandbox"}
    with open(os.path.join(PROJ, "evidence", "E1", f"{tag}.json"), "w") as fh:
        json.dump(summary, fh, indent=1)
    print(json.dumps({k: v for k, v in summary.items() if k != "ranges"}, indent=1))
    print("ranges:", summary["ranges"][:12])


if __name__ == "__main__":
    main()

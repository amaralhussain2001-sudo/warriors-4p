"""E1 runner: two sandbox instances, same savestate, frame barrier at start+N, dump and diff EE RAM.

Usage: python -I e1_run.py <profile> <N> <tag> [--input <inputfile>]
  profile: sandbox profile name (default = user's settings incl. MTVU; det = MTVU off etc.)
Writes: local/e1/<tag>/{a,b}.bin (RAM dumps, never committed), evidence/E1/<tag>.json (diff summary).
"""
import json
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(PROJ, "tools"))
import sandbox  # noqa: E402
from pine import Pine  # noqa: E402

STATE = os.path.join(PROJ, "local", "e1_start_m2.p2s")
PATCH = os.path.join(HERE, "e1_barrier.pnach")
FRAME_CTR = 0x0050C654
MB_TARGET, MB_REACHED, MB_RELEASE = 0x000F0100, 0x000F0104, 0x000F0108
INSTS = (2, 3)


def setup(profile):
    for n in INSTS:
        d = sandbox.inst_dir(n)
        if os.path.exists(d):
            shutil.rmtree(d)
        sandbox.make(n, profile)
        sandbox.install_patch(n, PATCH, ["warriors4p E1 barrier"])
        src = os.path.join(sandbox.data_root(1), "memcards")
        for m in ("Mcd001.ps2", "Mcd002.ps2"):
            shutil.copyfile(os.path.join(src, m), os.path.join(sandbox.data_root(n), "memcards", m))


def launch():
    procs = {}
    for n in INSTS:
        procs[n] = subprocess.Popen(sandbox.cmd(n, ["-statefile", STATE]),
                                    creationflags=getattr(subprocess, "DETACHED_PROCESS", 0))
        with open(os.path.join(sandbox.inst_dir(n), "pid.txt"), "w") as fh:
            fh.write(str(procs[n].pid))
    return procs


def connect(n, timeout=90):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            p = Pine(sandbox.PINE_BASE + n, timeout=5)
            if p.read32(FRAME_CTR) > 1000:  # savestate loaded (counter was ~15000 at save)
                return p
        except (OSError, RuntimeError):
            pass
        time.sleep(0.5)
    raise TimeoutError(f"inst{n} not ready")


def diff(a, b):
    """Differing byte ranges (gaps <= 16 bytes merged). Skips equal 4 KiB pages quickly."""
    ranges = []
    for page in range(0, len(a), 4096):
        if a[page:page + 4096] != b[page:page + 4096]:
            ranges.extend(_diff(a, b, page, min(page + 4096, len(a))))
    merged = []
    for s, e in ranges:
        if merged and s - merged[-1][1] <= 16:
            merged[-1] = (merged[-1][0], e)
        else:
            merged.append((s, e))
    return merged


def _diff(a, b, i, n):
    ranges = []
    while i < n:
        if a[i] != b[i]:
            j = i
            last = i
            while j < n and j - last <= 16:
                if a[j] != b[j]:
                    last = j
                j += 1
            ranges.append((i, last + 1))
            i = last + 1
        else:
            i += 1
    return ranges


def main():
    profile, N, tag = sys.argv[1], int(sys.argv[2]), sys.argv[3]
    out_local = os.path.join(PROJ, "local", "e1", tag)
    os.makedirs(out_local, exist_ok=True)
    setup(profile)
    procs = launch()
    pines = {n: connect(n) for n in INSTS}
    c0 = {n: pines[n].read32(FRAME_CTR) for n in INSTS}
    base = max(c0.values())
    target = base + N
    for n in INSTS:
        pines[n].write32(MB_TARGET, target)
    t0 = time.time()
    while True:
        r = {n: pines[n].read32(MB_REACHED) for n in INSTS}
        if all(v == target for v in r.values()):
            break
        if time.time() - t0 > N / 25 + 120:
            raise TimeoutError(f"barrier not reached: {r}")
        time.sleep(0.2)
    t_reach = time.time() - t0
    dumps = {}
    for n in INSTS:
        dumps[n] = pines[n].dump(0x00000000, 0x02000000)
        open(os.path.join(out_local, f"inst{n}.bin"), "wb").write(dumps[n])
    for n in INSTS:
        subprocess.run([sys.executable, "-I", os.path.join(PROJ, "tools", "sandbox.py"), "kill", str(n)],
                       capture_output=True)
    a, b = dumps[INSTS[0]], dumps[INSTS[1]]
    rs = diff(a, b)
    summary = {
        "tag": tag, "profile": profile, "N": N, "counter_at_load": c0, "target": target,
        "seconds_to_reach": round(t_reach, 1), "differing_bytes": sum(sum(1 for k in range(s, e) if a[k] != b[k]) for s, e in rs),
        "ranges": [{"start": f"{s:08x}", "len": e - s} for s, e in rs[:400]], "range_count": len(rs),
        "environment": "SINGLE-PC, scripted (no input), no impairment, PCSX2 v2.9.115 sandbox",
    }
    os.makedirs(os.path.join(PROJ, "evidence", "E1"), exist_ok=True)
    with open(os.path.join(PROJ, "evidence", "E1", f"{tag}.json"), "w") as fh:
        json.dump(summary, fh, indent=1)
    print(json.dumps({k: v for k, v in summary.items() if k != "ranges"}, indent=1))
    print("first ranges:", summary["ranges"][:30])


if __name__ == "__main__":
    main()

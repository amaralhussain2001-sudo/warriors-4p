"""E3b: repeated in-game barriers with different wait times per instance; optional fixed-step clock.

Usage: python -I e3b_run.py <tag> <N> <K> <delay_ms_B> [--fixed]
Reuses the E1 v2 setup (patch v2, Rumble start state, identical scripted input on pad 0).
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

CLOCK_PTR = 0x0050B734


def main():
    tag, N, K, delay = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
    fixed = "--fixed" in sys.argv
    out_local = os.path.join(PROJ, "local", "e1", tag)
    os.makedirs(out_local, exist_ok=True)
    e1.setup("default")
    e1.launch()
    pines = {n: e1.connect(n) for n in e1.INSTS}
    c0 = {n: pines[n].read32(e1.FRAME_CTR) for n in e1.INSTS}
    base = max(c0.values()) + 150
    table = inject.build_script("brawl", N + 30, seed=7)
    clock = {}
    for n in e1.INSTS:
        inject.arm(pines[n], table, base, 0x1)
        clock[n] = pines[n].read32(CLOCK_PTR)
        if fixed:
            pines[n].write32(clock[n] + 0x54, 1)   # GameClock fixed-step flag (F-0048)
    rtt = []
    waits = {n: 0.0 for n in e1.INSTS}
    target = base + K
    while target <= base + N:
        for n in e1.INSTS:
            pines[n].write32(e1.MB_TARGET, target)
        while True:
            r = {n: pines[n].read32(e1.MB_REACHED) for n in e1.INSTS}
            if all(v == target for v in r.values()):
                break
            time.sleep(0.002)
        if target == base + N:
            break
        t0 = time.perf_counter()
        pines[e1.INSTS[0]].write32(e1.MB_RELEASE, 1)
        rtt.append(time.perf_counter() - t0)
        time.sleep(delay / 1000.0)
        pines[e1.INSTS[1]].write32(e1.MB_RELEASE, 1)
        waits[e1.INSTS[1]] += delay / 1000.0
        # wait until both left the barrier (mailbox target cleared by the cave)
        while any(pines[n].read32(e1.MB_TARGET) != 0 for n in e1.INSTS):
            time.sleep(0.001)
        target += K
    fixed_state = {n: pines[n].read32(clock[n] + 0x54) for n in e1.INSTS}
    dumps = {n: pines[n].dump(0, 0x02000000) for n in e1.INSTS}
    for n in e1.INSTS:
        open(os.path.join(out_local, f"inst{n}.bin"), "wb").write(dumps[n])
        subprocess.run([sys.executable, "-I", os.path.join(PROJ, "tools", "sandbox.py"), "kill", str(n)], capture_output=True)
    a, b = dumps[e1.INSTS[0]], dumps[e1.INSTS[1]]
    rs = e1.diff(a, b)
    summary = {"tag": tag, "N": N, "K": K, "delay_ms_B": delay, "fixed_step_forced": fixed,
               "fixed_flag_at_end": fixed_state, "barriers": N // K,
               "pine_release_rtt_ms": {"median": round(sorted(rtt)[len(rtt) // 2] * 1000, 3) if rtt else None,
                                       "max": round(max(rtt) * 1000, 3) if rtt else None},
               "differing_bytes": sum(sum(1 for k in range(s, e) if a[k] != b[k]) for s, e in rs),
               "range_count": len(rs), "ranges": [{"start": f"{s:08x}", "len": e - s} for s, e in rs[:300]],
               "environment": "SINGLE-PC, scripted bot input pad 0, barrier-induced delay on B, PCSX2 v2.9.115 sandbox"}
    with open(os.path.join(PROJ, "evidence", "E1", f"{tag}.json"), "w") as fh:
        json.dump(summary, fh, indent=1)
    print(json.dumps({k: v for k, v in summary.items() if k != "ranges"}, indent=1))


if __name__ == "__main__":
    main()

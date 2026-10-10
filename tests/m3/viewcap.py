"""Record what the player sees when the view switches between merged and split (frame by frame).

Usage: python -I tests/m3/viewcap.py <tag> [--seconds 40] [--nocrop] [--nolayout] [--wait 15] [--slot 0] [--screen]
                                       [--pattern bots|apart|camera] [--walk 60] [--idle 0] [--every 0] [--around 12] [--cropdelay N]
  --pattern   bots: random seeded bots on both slots (as in M1); apart: player 1 walks away and back again while
              player 2 stands still; camera: player 1 turns the camera briefly every few seconds, nobody walks
  --every     also save every N-th capture as PNG
  --nocrop    show the game's own full frame (no presentation crop)
  --nolayout  original 2-player layout (game patch without the 2x2 layout line)
Starts two lockstep instances with bots (like tests/m1/m1_run.py), records one window with tools/framecap.ps1,
then reports every view-count change with the brightness of the lower half of the picture around it.
Writes local/m3/<tag>/ (frames, logs) and evidence/M3/<tag>.json. Environment: SINGLE-PC, bots, no impairment.
"""
import csv
import json
import os
import re
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(PROJ, "tools"))
sys.path.insert(0, os.path.join(PROJ, "tests", "m1"))
import m1_run  # noqa: E402
import sandbox  # noqa: E402


def opt(name, default, cast=int):
    return cast(sys.argv[sys.argv.index(name) + 1]) if name in sys.argv else default


def pattern_file(path, slot, kind, polls=40000):
    """Deterministic test inputs that make the view switch often."""
    out = bytearray()
    for _ in range(opt("--idle", 0) if slot == 0 else 0):
        out += m1_run.record()
    while len(out) < polls * 20:
        if slot == 1 or kind == "bots":
            out += m1_run.record()
        elif kind == "apart":
            walk = opt("--walk", 60)
            for ly in [0x00] * walk + [0x7F] * 90 + [0xFF] * walk + [0x7F] * 150:
                out += m1_run.record(ly=ly)
        elif kind == "camera":
            for rx in [0xFF] * 20 + [0x7F] * 130 + [0x00] * 20 + [0x7F] * 130:
                out += m1_run.record(rx=rx)
    open(path, "wb").write(bytes(out[: polls * 20]))


def main():
    tag = sys.argv[1]
    seconds, wait, cap_slot = opt("--seconds", 40), opt("--wait", 15), opt("--slot", 0)
    args = {"delay": 2, "latency": 0, "jitter": 0, "loss": 0.0, "nocrop": "--nocrop" in sys.argv, "corrupt": None}
    out_dir = os.path.join(PROJ, "local", "m3", tag)
    if os.path.exists(out_dir):
        shutil.rmtree(out_dir)
    os.makedirs(out_dir)
    patch = m1_run.PATCH
    if "--nolayout" in sys.argv:
        patch = os.path.join(out_dir, "w4p_nolayout.pnach")
        lines = open(m1_run.PATCH, encoding="utf-8").read().splitlines()
        open(patch, "w", encoding="utf-8").write("\n".join(l for l in lines if "00123300" not in l) + "\n")
    state = os.path.join(PROJ, "local", "m1_start_m9_2p.p2s")
    procs = {}
    for slot, n in m1_run.INSTS.items():
        d = sandbox.inst_dir(n)
        if os.path.exists(d):
            shutil.rmtree(d)
        sandbox.make(n, "default", pad2=True)
        sandbox.install_patch(n, patch, ["warriors-4p M1"])
        for m in ("Mcd001.ps2", "Mcd002.ps2"):
            shutil.copyfile(os.path.join(PROJ, "local", m), os.path.join(sandbox.data_root(n), "memcards", m))
        kind = opt("--pattern", "bots", str)
        if kind == "bots":
            m1_run.bot_file(os.path.join(out_dir, f"bot_slot{slot}.bin"), 1000 + slot, 40000)
        else:
            pattern_file(os.path.join(out_dir, f"bot_slot{slot}.bin"), slot, kind)
        ini = os.path.join(out_dir, f"w4p_slot{slot}.ini")
        m1_run.write_ini(ini, slot, out_dir, args)
        extra = [f"CropDelayFrames = {opt('--cropdelay', 0)}"] if "--cropdelay" in sys.argv else []
        if extra:
            open(ini, "a", encoding="utf-8").write("".join(line + "\n" for line in extra))
        env = dict(os.environ, W4P_CONFIG=ini)
        cmd = [sandbox.FORK_EXE] + sandbox.cmd(n, ["-statefile", state])[1:]
        procs[slot] = subprocess.Popen(cmd, env=env, creationflags=getattr(subprocess, "DETACHED_PROCESS", 0))
        open(os.path.join(d, "pid.txt"), "w").write(str(procs[slot].pid))
    time.sleep(wait)
    n = m1_run.INSTS[cap_slot]
    frames_dir = os.path.join(out_dir, "frames")
    cap = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", os.path.join(PROJ, "tools", "framecap.ps1"),
           "-ProcessId", str(procs[cap_slot].pid), "-PinePort", str(sandbox.PINE_BASE + n), "-OutDir", frames_dir,
           "-Seconds", str(seconds), "-Every", str(opt("--every", 0)), "-Around", str(opt("--around", 12))]
    if "--screen" in sys.argv:
        cap.append("-Screen")
    r = subprocess.run(cap, capture_output=True, text=True)
    cap_out = (r.stdout + r.stderr).strip()
    for slot, n in m1_run.INSTS.items():
        subprocess.run([sys.executable, "-I", os.path.join(PROJ, "tools", "sandbox.py"), "kill", str(n)], capture_output=True)
    for slot in procs:
        try:
            procs[slot].wait(15)
        except subprocess.TimeoutExpired:
            pass
    rows = list(csv.DictReader(open(os.path.join(frames_dir, "frames.csv"), encoding="utf-8")))
    changes = []
    for i in range(1, len(rows)):
        if rows[i]["views"] != rows[i - 1]["views"]:
            lo, hi = max(0, i - 8), min(len(rows), i + 12)
            changes.append({"capture": i, "t_ms": float(rows[i]["t_ms"]), "views": f"{rows[i-1]['views']}->{rows[i]['views']}",
                            "around": [{"idx": int(rows[k]["idx"]), "dt_ms": round(float(rows[k]["t_ms"]) - float(rows[i]["t_ms"])),
                                        "views": int(rows[k]["views"]), "frame": int(rows[k]["game_frame"]),
                                        "lower_half": round((float(rows[k]["lum_bl"]) + float(rows[k]["lum_br"])) / 2, 1),
                                        "upper_half": round((float(rows[k]["lum_tl"]) + float(rows[k]["lum_tr"])) / 2, 1),
                                        "diff": float(rows[k]["diff_prev"])} for k in range(lo, hi)]})
    hashes = {}
    for slot in procs:
        txt = open(os.path.join(out_dir, f"w4p_slot{slot}.log"), encoding="utf-8", errors="replace").read()
        hashes[slot] = dict(re.findall(r"^HASH (\d+) ([0-9a-f]+)$", txt, re.M))
    common = sorted(set(hashes[0]) & set(hashes[1]), key=int)
    summary = {"tag": tag, "args": args, "nolayout": "--nolayout" in sys.argv, "pattern": opt("--pattern", "bots", str), "captured_slot": cap_slot,
               "capture": cap_out, "view_changes": len(changes), "changes": changes,
               "hash_points_common": len(common), "hash_mismatches": sum(1 for t in common if hashes[0][t] != hashes[1][t]),
               "environment": "SINGLE-PC, bots, no impairment"}
    os.makedirs(os.path.join(PROJ, "evidence", "M3"), exist_ok=True)
    json.dump(summary, open(os.path.join(PROJ, "evidence", "M3", f"{tag}.json"), "w"), indent=1)
    print(cap_out)
    print("view changes:", len(changes), "| hash points", len(common), "mismatches", summary["hash_mismatches"])
    for c in changes:
        print(f"  t={c['t_ms']/1000:.2f}s {c['views']}: " + " ".join(
            f"{a['dt_ms']:+d}:{'v' + str(a['views'])}/{a['lower_half']:.0f}" for a in c["around"]))


if __name__ == "__main__":
    main()

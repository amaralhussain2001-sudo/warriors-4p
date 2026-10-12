"""D24 chase stretches (docs/research/m6_chase4p.md): four instances in lockstep (tests/m2/m2_run4.py), level jump to
Mission 18 or 8 at a checkpoint, scripted tapping (all four face buttons every 3 polls, held 2 polls: full speed whatever
button the chase asks for) for the chosen slots, PINE samples of instance 7 (slot 1; the instances run in lockstep) with
tests/m6/chase_probe.state every few seconds.

Usage: python -I tests/m6/chase4p_run.py <tag> [--mission 18] [--cp 1] [--seconds 900] [--tap-slots 0,1]
       [--tap-from 8000] [--tap-stop "2:12000"]  (slot 2 stops tapping at poll 12000)
       [--tap-gap "2:8300:8800"]  (slot 2 does not tap from poll 8300 to 8799) [--tap-buttons "X"]  (default all four)
       [--policies]  (W4P SessionPolicies = true: X11 auto-join, sit-out, skip votes)
       [--sample-every 3] [--shot-every 20] [--groups-extra "..."]
       [--inst-base 6] [--patch file.pnach]  (passed to m2_run4.py)
Slot 0 boots (tests/m2/nav/boot_to_m1_2p.txt), slot 1 joins at the menu (p2_join.txt); slots 2-3 get only their tap
lines (no Start: with --policies they join only through X11 or the D24 rows). Writes local/m2/<tag>/ (m2_run4.py),
local/m2/<tag>/chase_samples.json and evidence/M6/<tag>.json. Environment: SINGLE-PC, 4 instances, loopback, bots.
"""
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(PROJ, "tools"))
sys.path.insert(0, HERE)
import chase_probe  # noqa: E402
import sandbox  # noqa: E402
from pine import Pine  # noqa: E402

ENTRY0, ENTRY_SIZE = 0x01FD996C, 0x84
GROUPS = ("warriors-4p 4p hud B1;warriors-4p 4p hud B2;warriors-4p 4p spawn;warriors-4p 4p spawn leave;"
          "warriors-4p 4p inventory;warriors-4p 4p fx;warriors-4p 4p markers;warriors-4p session;warriors-4p missions;"
          "warriors-4p session call")
POLLS = 40000


def opt(name, default, cast=str):
    return cast(sys.argv[sys.argv.index(name) + 1]) if name in sys.argv else default


def tap_lines(t0, t1, gaps=(), buttons=("TRI", "CIR", "X", "SQ")):
    keys = " ".join(f"{b}:2" for b in buttons)
    return [f"{t} {keys}" for t in range(t0, t1, 3) if not any(a <= t < b for a, b in gaps)]


def main():
    tag = sys.argv[1]
    mission, cp = opt("--mission", 18, int), opt("--cp", 1, int)
    seconds = opt("--seconds", 900, int)
    tap_slots = [int(x) for x in opt("--tap-slots", "0,1").split(",") if x]
    tap_from = opt("--tap-from", 8000, int)
    stops = dict((int(a), int(b)) for a, b in (x.split(":") for x in opt("--tap-stop", "").split(",") if x))
    gaps = {}
    for x in [x for x in opt("--tap-gap", "").split(",") if x]:
        sl, a, b = (int(v) for v in x.split(":"))
        gaps.setdefault(sl, []).append((a, b))
    buttons = tuple(opt("--tap-buttons", "TRI,CIR,X,SQ").split(","))
    work = os.path.join(PROJ, "local", "m6", "d24", tag)
    os.makedirs(work, exist_ok=True)
    scripts = {}
    for slot in range(4):
        base = {0: "boot_to_m1_2p.txt", 1: "p2_join.txt"}.get(slot)
        lines = open(os.path.join(PROJ, "tests", "m2", "nav", base), encoding="utf-8").read().splitlines() if base else []
        if slot != 0:
            # every player votes to skip the Mission 1 intro movie (SessionPolicies: nobody skips alone), so the level
            # jump's SetCheckPoint at poll 3999 is not overwritten by Mission 1's own start after the movie
            lines += ["3650 X:3", "3700 X:3", "3750 X:3"]
        if slot in tap_slots:
            lines += tap_lines(tap_from, stops.get(slot, POLLS - 10), gaps.get(slot, ()), buttons)
        path = os.path.join(work, f"slot{slot}.txt")
        open(path, "w", encoding="utf-8").write("\n".join(lines) + "\n")
        scripts[slot] = path
    ptr = ENTRY0 + (mission - 1) * ENTRY_SIZE
    cmd = [sys.executable, "-I", os.path.join(PROJ, "tests", "m2", "m2_run4.py"), tag, "--seconds", str(seconds),
           "--polls", str(POLLS), "--shot-slots", "0,1,2,3", "--shot-every", str(opt("--shot-every", 20, int)),
           "--sample-every", "15", "--crop", "--calls", f"3999:0041ABC0:{cp},4009:00160D78:0x{ptr:08X}",
           "--ini", "EmuCore/Speedhacks/vuThread=false",
           "--groups", GROUPS + "".join(";" + g for g in opt("--groups-extra", "").split(";") if g)]
    for slot in range(4):
        cmd += [f"--script{slot + 1}", scripts[slot]]
    if "--policies" in sys.argv:
        cmd += ["--w4p", "SessionPolicies = true"]
    base = opt("--inst-base", 6, int)
    cmd += ["--inst-base", str(base)] + (["--patch", opt("--patch", "")] if "--patch" in sys.argv else [])
    print(" ".join(cmd), flush=True)
    t0 = time.time()
    proc = subprocess.Popen(cmd, cwd=PROJ, stdout=open(os.path.join(work, "run4_console.txt"), "w"),
                            stderr=subprocess.STDOUT)
    every = opt("--sample-every", 3, int)
    samples, out_dir = [], os.path.join(PROJ, "local", "m2", tag)
    time.sleep(25)
    while proc.poll() is None and time.time() - t0 < seconds - 15:
        try:
            pn = Pine(sandbox.PINE_BASE + base + 1, timeout=3)
            s = chase_probe.state(pn)
            s["t"] = round(time.time() - t0)
            samples.append(s)
        except Exception as e:  # noqa: BLE001
            samples.append({"t": round(time.time() - t0), "error": repr(e)})
        if os.path.isdir(out_dir):
            json.dump(samples, open(os.path.join(out_dir, "chase_samples.json"), "w"), indent=1)
        time.sleep(every)
    proc.wait()
    ev = {}
    try:
        ev = json.load(open(os.path.join(PROJ, "evidence", "M2", f"{tag}.json")))
    except (OSError, ValueError):
        pass
    tlb = {}
    for n in range(base, base + 4):
        src = os.path.join(PROJ, "local", "pcsx2", f"inst{n}", "PCSX2", "logs", "emulog.txt")
        try:
            txt = open(src, encoding="utf-8", errors="replace").read()
            open(os.path.join(out_dir, f"emulog_inst{n}.txt"), "w", encoding="utf-8").write(txt)
            tlb[n] = txt.count("TLB Miss")
        except OSError as e:
            tlb[n] = repr(e)
    json.dump(samples, open(os.path.join(out_dir, "chase_samples.json"), "w"), indent=1)
    good = [s for s in samples if "error" not in s]
    cps = []
    for s in good:
        if not cps or cps[-1][1] != s["checkpoint"]:
            cps.append((s["poll"], s["checkpoint"]))
    counts = sorted({s["count"] for s in good})
    max_idx = {}
    for s in good:
        for k, pl in s["players"].items():
            if pl.get("tap"):
                max_idx[k] = max(max_idx.get(k, -1), pl["flag_idx"])
    tapping = {}
    for s in good:
        tapping[len([1 for pl in s["players"].values() if pl.get("tap")])] = s["poll"]
    row = {"tag": tag, "environment": "SINGLE-PC, 4 instances in lockstep, loopback, scripted tapping bots, no impairment",
           "mission": mission, "start_checkpoint": cp, "tap_slots": tap_slots, "tap_from": tap_from, "tap_stop": stops,
           "tap_gaps": gaps, "tap_buttons": buttons,
           "policies": "--policies" in sys.argv, "seconds": ev.get("seconds"), "hash_points": ev.get("hash_points_common"),
           "mismatches": ev.get("hash_mismatches"), "first_mismatch": ev.get("first_mismatch"), "tlb_misses": tlb,
           "checkpoints_seen": cps, "player_counts_seen": counts, "max_tap_flag_index_by_player": max_idx,
           "last_poll_with_n_tapping": tapping, "end_state": ev.get("state"), "samples": len(good)}
    os.makedirs(os.path.join(PROJ, "evidence", "M6"), exist_ok=True)
    json.dump(row, open(os.path.join(PROJ, "evidence", "M6", f"{tag}.json"), "w"), indent=1)
    print(json.dumps({k: row[k] for k in ("hash_points", "mismatches", "tlb_misses", "checkpoints_seen",
                                          "player_counts_seen", "max_tap_flag_index_by_player")}), flush=True)


if __name__ == "__main__":
    main()

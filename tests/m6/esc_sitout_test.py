"""D18 Esc pause request + X13 sit-out screen test (SINGLE-PC, 4 instances in lockstep, loopback, bots, SessionPolicies
on). Level jump to a mission whose script keeps joining off at its start (default Mission 2: players 3-4 must sit out
with a waiting screen instead of the other players' views). The harness posts real Esc key presses (tools/winkeys.ps1)
to player 2's window at the given times; each Esc must become a pause request for everyone ("Paused by Player 2") and
the emulator's own pause menu must not open; the next Esc (player 2's Start) resumes.

Usage: python -I tests/m6/esc_sitout_test.py <tag> [--mission 2] [--seconds 480] [--esc 220,250,280,310,340,370]
Writes local/m2/<tag>/ (via m2_run4.py) and evidence/M6/<tag>.json.
"""
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(PROJ, "tools"))
import sandbox  # noqa: E402

GROUPS = ("warriors-4p 4p hud B1;warriors-4p 4p hud B2;warriors-4p 4p spawn;warriors-4p 4p spawn leave;"
          "warriors-4p 4p inventory;warriors-4p 4p fx;warriors-4p 4p markers;warriors-4p session;warriors-4p missions;warriors-4p session call")


def opt(name, default, cast=str):
    return cast(sys.argv[sys.argv.index(name) + 1]) if name in sys.argv else default


def main():
    tag = sys.argv[1]
    mission = opt("--mission", 2, int)
    seconds = opt("--seconds", 480, int)
    esc_times = [int(x) for x in opt("--esc", "220,250,280,310,340,370").split(",") if x]
    ptr = 0x01FD996C + (mission - 1) * 0x84
    cmd = [sys.executable, "-I", os.path.join(PROJ, "tests", "m2", "m2_run4.py"), tag, "--seconds", str(seconds),
           "--polls", "40000", "--bots-from", "9000", "--shot-slots", "0,1,2,3", "--shot-every", "10",
           "--sample-every", "15", "--crop", "--calls", f"3999:0041ABC0:1,4009:00160D78:0x{ptr:08X}",
           "--ini", "EmuCore/Speedhacks/vuThread=false", "--groups", GROUPS, "--w4p", "SessionPolicies = true"]
    runner = subprocess.Popen(cmd, cwd=PROJ)
    t0 = time.time()
    posted = []
    pid_file = os.path.join(sandbox.inst_dir(7), "pid.txt")  # slot 1 = player 2 runs in instance 7
    for at in esc_times:
        while time.time() - t0 < at and runner.poll() is None:
            time.sleep(0.5)
        if runner.poll() is not None:
            break
        try:
            pid = int(open(pid_file).read().strip())
        except (OSError, ValueError) as e:
            posted.append({"t": round(time.time() - t0), "error": repr(e)})
            continue
        r = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                            os.path.join(PROJ, "tools", "winkeys.ps1"), "-ProcessId", str(pid), "-Seq", "Escape:150"],
                           capture_output=True, text=True)
        posted.append({"t": round(time.time() - t0), "rc": r.returncode, "out": (r.stdout + r.stderr).strip()[-200:]})
    runner.wait()
    out_dir = os.path.join(PROJ, "local", "m2", tag)
    events = {}
    for slot in range(4):
        lines = []
        try:
            for line in open(os.path.join(out_dir, f"w4p_slot{slot}.log"), encoding="utf-8", errors="replace"):
                if any(k in line for k in ("pause requested", "game paused", "game resumed", "sit-out", "auto join", "skip vote")):
                    lines.append(line.strip()[-150:])
        except OSError as e:
            lines.append(repr(e))
        events[slot] = lines[:80]
    ev = {}
    try:
        ev = json.load(open(os.path.join(PROJ, "evidence", "M2", f"{tag}.json")))
    except (OSError, ValueError):
        pass
    tlb = {}
    for n in (6, 7, 8, 9):
        try:
            tlb[n] = open(os.path.join(PROJ, "local", "pcsx2", f"inst{n}", "PCSX2", "logs", "emulog.txt"),
                          encoding="utf-8", errors="replace").read().count("TLB Miss")
        except OSError as e:
            tlb[n] = repr(e)
    res = {"tag": tag, "environment": "SINGLE-PC, 4 instances, loopback, bots, real Esc key presses on player 2's window",
           "mission": mission, "esc_posted": posted, "hash_points": ev.get("hash_points_common"),
           "mismatches": ev.get("hash_mismatches"), "tlb_misses": tlb, "events": events}
    os.makedirs(os.path.join(PROJ, "evidence", "M6"), exist_ok=True)
    json.dump(res, open(os.path.join(PROJ, "evidence", "M6", f"{tag}.json"), "w"), indent=1)
    print(json.dumps({k: res[k] for k in ("hash_points", "mismatches", "tlb_misses")}))


if __name__ == "__main__":
    main()

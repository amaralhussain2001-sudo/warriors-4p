"""Drive a sandbox instance: post key presses, then save a screenshot.

Pad 1 keys (template PCSX2.ini): arrows=D-pad, W/A/S/D=left stick, K=Cross, L=Circle,
J=Square, I=Triangle, Return=Start, Back=Select, Q=L1, E=R1, D1=L2, D3=R2.
Pad 2 keys (sandbox --pad2): Y/B/N/M=left stick, D5-D8=D-pad, X=Cross, C=Circle,
Z=Square, V=Triangle, P=Start, O=Select, U=L1, R=R1, D0=L2, D9=R2.

Usage:
    python -I tools/drive.py <inst> "<seq>" [shot_name] [--scale 0.4]
    seq items: <Key>:<holdMs> | wait:<ms>   (Keys are .NET Keys names)
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.abspath(os.path.join(HERE, ".."))


def pid_of(n):
    return int(open(os.path.join(PROJ, "local", "pcsx2", f"inst{n}", "pid.txt")).read())


def ps(script, *args):
    r = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", os.path.join(HERE, script), *args],
                       capture_output=True, text=True)
    return (r.stdout + r.stderr).strip()


def main():
    n = int(sys.argv[1])
    seq = sys.argv[2]
    pid = pid_of(n)
    if seq:
        out = ps("winkeys.ps1", "-ProcessId", str(pid), "-Seq", seq)
        if out:
            print(out)
    if len(sys.argv) > 3 and not sys.argv[3].startswith("--"):
        scale = sys.argv[sys.argv.index("--scale") + 1] if "--scale" in sys.argv else "0.4"
        shots = os.path.join(PROJ, "local", "shots")
        os.makedirs(shots, exist_ok=True)
        print(ps("winshot.ps1", "-ProcessId", str(pid), "-Out", os.path.join(shots, sys.argv[3] + ".png"), "-Scale", scale))


if __name__ == "__main__":
    main()

"""M1 human trial: you play player 1 in window A (keyboard, same keys as your PCSX2 setup); a bot plays player 2
in window B; both run in lockstep over loopback. Each window shows its own player's view.

Usage: python -I tests/m1/m1_play.py [--delay 2]
Close either window to end. Logs: local/m1/play_<time>/.
Keys (from your PCSX2 settings): arrows = D-pad, W/A/S/D = left stick, T/F/G/H = right stick (camera),
K = Cross, L = Circle, J = Square, I = Triangle, Q = L1, E = R1, 1 = L2, 3 = R2, Enter = Start.
"""
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(PROJ, "tools"))
sys.path.insert(0, HERE)
import m1_run  # noqa: E402
import sandbox  # noqa: E402


def main():
    delay = int(sys.argv[sys.argv.index("--delay") + 1]) if "--delay" in sys.argv else 2
    out_dir = os.path.join(PROJ, "local", "m1", time.strftime("play_%Y%m%d_%H%M%S"))
    os.makedirs(out_dir)
    args = {"delay": delay, "latency": 0, "jitter": 0, "loss": 0.0, "nocrop": False, "corrupt": None}
    state = os.path.join(PROJ, "local", "m1_start_m9_2p.p2s")
    for slot, n in m1_run.INSTS.items():
        d = sandbox.inst_dir(n)
        if os.path.exists(d):
            shutil.rmtree(d)
        sandbox.make(n, "default", pad2=True)
        sandbox.install_patch(n, m1_run.PATCH, ["warriors-4p M1"])
        for m in ("Mcd001.ps2", "Mcd002.ps2"):
            shutil.copyfile(os.path.join(PROJ, "local", m), os.path.join(sandbox.data_root(n), "memcards", m))
        ini = os.path.join(out_dir, f"w4p_slot{slot}.ini")
        if slot == 1:
            m1_run.bot_file(os.path.join(out_dir, "bot_slot1.bin"), 1001, 40000)
        m1_run.write_ini(ini, slot, out_dir, args)
        if slot == 0:  # human on slot 0: no bot file
            txt = open(ini, encoding="utf-8").read().splitlines()
            open(ini, "w", encoding="utf-8").write("\n".join(l for l in txt if not l.startswith("BotInput")) + "\n")
        env = dict(os.environ, W4P_CONFIG=ini)
        cmd = [sandbox.FORK_EXE] + sandbox.cmd(n, ["-statefile", state])[1:]
        p = subprocess.Popen(cmd, env=env, creationflags=getattr(subprocess, "DETACHED_PROCESS", 0))
        open(os.path.join(d, "pid.txt"), "w").write(str(p.pid))
    print("Started. Window A (first) = you, player 1. Window B = bot, player 2. Logs:", out_dir)


if __name__ == "__main__":
    main()

"""Self-test of the 2-PC package on ONE PC: two launchers (player 1 and 2) on loopback, from a fresh boot,
fresh memory cards, scripted bots on both slots. Compares the hash streams afterwards.

Usage: python -I tests/m3/package_selftest.py <tag> [--seconds 180] [--fps60 yes|no] [--wide yes|no] [--quality 2]
Uses dist/warriors-4p-test (build it first with tools/make_package.py), the sandbox BIOS copy and the ISO read-only.
Writes evidence/M3/<tag>.json. Environment: SINGLE-PC, bots, loopback, no impairment.
"""
import glob
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

PKG = os.path.join(PROJ, "dist", "warriors-4p-test")


def opt(name, default, cast=str):
    return cast(sys.argv[sys.argv.index(name) + 1]) if name in sys.argv else default


def main():
    tag = sys.argv[1]
    seconds = opt("--seconds", 180, int)
    work = os.path.join(PROJ, "local", "m3", tag)
    if os.path.exists(work):
        shutil.rmtree(work)
    os.makedirs(work)
    bios = glob.glob(os.path.join(sandbox.BIOS_DIR, "*.ROM0"))[0]
    started = {}
    for player in (1, 2):
        settings = os.path.join(work, f"settings{player}.txt")
        open(settings, "w", encoding="utf-8").write("\n".join([
            f"Player={player}", "OtherIP=127.0.0.1", f"Iso={sandbox.ISO}", f"Bios={bios}",
            f"Quality={opt('--quality', '2')}", f"Fps60={opt('--fps60', 'yes')}", f"Widescreen={opt('--wide', 'no')}",
            "Fullscreen=no", "InputDelay=2", "Renderer=14", "Adapter=NVIDIA GeForce RTX 5090"]) + "\n")
        bot = os.path.join(work, f"bot{player}.bin")
        m1_run.bot_file(bot, 2000 + player, 40000)
        port, other = (41010, 41011) if player == 1 else (41011, 41010)
        cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", os.path.join(PKG, "Start-Coop.ps1"),
               "-SettingsFile", settings, "-DataDir", os.path.join(work, f"data{player}"), "-Port", str(port),
               "-OtherPort", str(other), "-BotFile", bot, "-NoWait"]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        print(r.stdout.strip()[-600:], r.stderr.strip()[-600:])
        started[player] = time.time()
    time.sleep(seconds)
    logs = {}
    for player in (1, 2):
        d = sorted(glob.glob(os.path.join(PKG, "logs", f"*_player{player}")))[-1]
        logs[player] = d
        pid = int(open(os.path.join(d, "pid.txt")).read().strip())
        subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True)
    time.sleep(3)
    res = {}
    hashes, ghashes = {}, {}
    for player, d in logs.items():
        txt = open(os.path.join(d, "w4p.log"), encoding="utf-8", errors="replace").read()
        hashes[player] = dict(re.findall(r"^HASH (\d+) ([0-9a-f]+)$", txt, re.M))
        ghashes[player] = {t: (g, k) for t, g, k in re.findall(r"^GHASH (\d+) ([0-9a-f]+) ([0-9a-f]+)$", txt, re.M)}
        res[f"p{player}_hello"] = re.findall(r"hello from.*$", txt, re.M)[:1]
        res[f"p{player}_errors"] = re.findall(r"(?:ERROR|WARNING|DESYNC|NOTE).*$", txt, re.M)[:5]
        st = re.findall(r"stats: (.*)$", txt, re.M)
        res[f"p{player}_stats"] = st[-1] if st else None
        res[f"p{player}_logdir"] = d
    common = sorted(set(hashes[1]) & set(hashes[2]), key=int)
    res.update({"tag": tag, "environment": "SINGLE-PC, package launcher, fresh boot, fresh memory cards, bots, loopback",
                "args": sys.argv[2:], "hash_points_common": len(common),
                "hash_mismatches": sum(1 for t in common if hashes[1][t] != hashes[2][t]),
                "game_hash_mismatches": sum(1 for t in common if ghashes[1].get(t, ("",))[0] != ghashes[2].get(t, ("",))[0])})
    os.makedirs(os.path.join(PROJ, "evidence", "M3"), exist_ok=True)
    json.dump(res, open(os.path.join(PROJ, "evidence", "M3", f"{tag}.json"), "w"), indent=1)
    print(json.dumps({k: v for k, v in res.items() if not k.endswith("logdir")}, indent=1))


if __name__ == "__main__":
    main()

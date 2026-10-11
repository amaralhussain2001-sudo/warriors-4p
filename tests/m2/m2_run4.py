"""M2: four instances in lockstep (loopback), four players, from a fresh boot.

Usage: python -I tests/m2/m2_run4.py <tag> [--seconds 420] [--bots-from 4700] [--crop] [--force-split]
       [--calls "poll:fn:args,..."] [--groups "extra;groups"] [--script1..4 file] [--ini Section/Key=Value]
       [--polls 40000] [--script-bots-from N] [--shot-slots 0,1,2,3]
--polls: length of every input file (the files wrap around after it, so runs longer than about polls/28 s need more).
--script-bots-from: slots with a --scriptN file play seeded random bot input from poll N on, plus a Start press every
300 polls so that players 3-4 re-join after a mission restart (Start does not pause for them).
Slot 0 runs the boot-to-Mission-1 script, slot 1 joins at the menu; players 3-4 are created at fixed session polls on
every instance with W4P CallAt + the "warriors-4p test call" group (test-only: the game's own join has no companion
in Mission 1, F-0109). From --bots-from on, every slot plays seeded random bot input (m1_run.bot_file).
Writes local/m2/<tag>/ and evidence/M2/<tag>.json. Environment: SINGLE-PC, 4 instances, loopback, bots.
"""
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
sys.path.insert(0, HERE)
import m1_run  # noqa: E402
import nav_probe  # noqa: E402
import sandbox  # noqa: E402
from pine import Pine  # noqa: E402

INSTS = {0: 6, 1: 7, 2: 8, 3: 9}
PORTS = {s: 41200 + s for s in INSTS}
GROUPS = ["warriors-4p M1", "warriors-4p own view", "warriors-4p hud", "warriors-4p 4p", "warriors-4p test call"]
# session-relative polls (session starts at guest poll 1): MakePlayer, camera, layout (no join script event: the
# mission join scripts are written for player 2, m2_black_screen.md)
CALLS = ("4299:00229C40:0x641a20:1:0xffffffff:0xffffffff,4309:001222B0:0x641a20:1,4319:0011EAF0:2,"
         "4339:00122ED0,4399:00229C40:0x6420f0:2:0xffffffff:0xffffffff,"
         "4409:001222B0:0x6420f0:1,4419:0011EAF0:3,4439:00122ED0")


def opt(name, default, cast=int):
    return cast(sys.argv[sys.argv.index(name) + 1]) if name in sys.argv else default


POLLS = opt("--polls", 40000)


def inputs_for(slot, out_dir, bots_from):
    nav = {0: "boot_to_m1_2p.txt", 1: "p2_join.txt"}.get(slot)
    custom = opt(f"--script{slot + 1}", "", str)  # full input script for this slot (replaces nav + random bot)
    if custom:
        path = os.path.join(out_dir, f"bot_slot{slot}.bin")
        data = bytearray(nav_probe.build_inputs(custom, POLLS))
        script_bots = opt("--script-bots-from", 0)
        if script_bots:
            tmp = os.path.join(out_dir, f"rand{slot}.bin")
            m1_run.bot_file(tmp, 3000 + slot, POLLS)
            rnd = bytearray(open(tmp, "rb").read()[: POLLS * 20])
            for t in range(script_bots, POLLS, 300):  # re-join after a restart
                for i in range(t, min(POLLS, t + 4)):
                    rnd[i * 20: i * 20 + 2] = (int.from_bytes(rnd[i * 20: i * 20 + 2], "little") | 0x800).to_bytes(2, "little")
            data[script_bots * 20:] = rnd[script_bots * 20:]
        open(path, "wb").write(bytes(data))
        return path
    base = bytearray(nav_probe.build_inputs(os.path.join(HERE, "nav", nav), POLLS) if nav else m1_run.record() * POLLS)
    tmp = os.path.join(out_dir, f"rand{slot}.bin")
    m1_run.bot_file(tmp, 3000 + slot, POLLS)
    rnd = open(tmp, "rb").read()
    base[bots_from * 20:] = rnd[: (POLLS - bots_from) * 20]
    path = os.path.join(out_dir, f"bot_slot{slot}.bin")
    open(path, "wb").write(bytes(base))
    return path


def main():
    tag = sys.argv[1]
    seconds, bots_from = opt("--seconds", 420), opt("--bots-from", 4700)
    out_dir = os.path.join(PROJ, "local", "m2", tag)
    if os.path.exists(out_dir):
        shutil.rmtree(out_dir)
    os.makedirs(out_dir)
    procs = {}
    for slot, n in INSTS.items():
        d = sandbox.inst_dir(n)
        if os.path.exists(d):
            shutil.rmtree(d)
        sandbox.make(n, "default", pad2=True)
        extra_groups = [g for g in opt("--groups", "", str).split(";") if g]
        sandbox.install_patch(n, m1_run.PATCH, GROUPS + (["warriors-4p test force split"] if "--force-split" in sys.argv else []) + extra_groups)
        for item in [a for i, a in enumerate(sys.argv) if i and sys.argv[i - 1] == "--ini"]:  # Section/Key=Value
            sec_key, val = item.split("=", 1)
            sec, key = sec_key.rsplit("/", 1)
            ini_path = os.path.join(sandbox.data_root(n), "inis", "PCSX2.ini")
            import configparser
            cp = configparser.ConfigParser(interpolation=None, strict=False)
            cp.optionxform = str
            cp.read(ini_path, encoding="utf-8")
            if not cp.has_section(sec):
                cp.add_section(sec)
            cp.set(sec, key, val)
            with open(ini_path, "w", encoding="utf-8") as fh:
                cp.write(fh, space_around_delimiters=True)
        bot = inputs_for(slot, out_dir, bots_from)
        lines = ["[W4P]", "Enabled = true", "Players = 4", f"LocalSlot = {slot}", "PadForSlot0 = 0", "PadForSlot1 = 4",
                 "PadForSlot2 = 1", "PadForSlot3 = 2", f"ListenPort = {PORTS[slot]}", "InputDelay = 2", "HashInterval = 30",
                 f"LogFile = {os.path.join(out_dir, f'w4p_slot{slot}.log')}", f"DumpDir = {out_dir}", f"BotInput = {bot}",
                 f"Crop = {'true' if '--crop' in sys.argv else 'false'}", f"CallAt = {opt('--calls', CALLS, str)}"]
        lines += [f"Peer{o} = 127.0.0.1:{PORTS[o]}" for o in INSTS if o != slot]
        ini = os.path.join(out_dir, f"w4p_slot{slot}.ini")
        open(ini, "w", encoding="utf-8").write("\n".join(lines) + "\n")
        env = dict(os.environ, W4P_CONFIG=ini)
        cmd = [sandbox.FORK_EXE] + sandbox.cmd(n, [])[1:]
        procs[slot] = subprocess.Popen(cmd, env=env, creationflags=getattr(subprocess, "DETACHED_PROCESS", 0))
        open(os.path.join(d, "pid.txt"), "w").write(str(procs[slot].pid))
    t0 = time.time()
    next_shot = t0 + 30
    shot_slots = [int(x) for x in opt("--shot-slots", "0", str).split(",")]  # e.g. 0,1,2,3: one slot per shot, in turn
    shots = 0
    while time.time() - t0 < seconds and all(p.poll() is None for p in procs.values()):
        time.sleep(5)
        if time.time() >= next_shot:  # one picture every 30 s (slot 0 by default)
            next_shot += 30
            ss = shot_slots[shots % len(shot_slots)]
            shots += 1
            subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                            os.path.join(PROJ, "tools", "winshot.ps1"), "-ProcessId", str(procs[ss].pid),
                            "-Out", os.path.join(out_dir, f"s{ss}_t{int(time.time() - t0):04d}.png"), "-Scale", "0.4"],
                           capture_output=True)
    state = {}
    for slot, n in INSTS.items():
        try:
            p = Pine(sandbox.PINE_BASE + n, timeout=3)
            gm = p.read32(0x0051489C)
            state[slot] = {"poll": p.read32(0x000F0500), "players": p.read32(gm + 0x224) & 0xFFFF,
                           "handles": [hex(p.read32(gm + 0x228 + 4 * i)) for i in range(4)],
                           "views": p.read32(0x0050B198), "cameras": p.read32(0x0050B19C)}
        except Exception as e:  # noqa: BLE001
            state[slot] = repr(e)
        subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", os.path.join(PROJ, "tools", "winshot.ps1"),
                        "-ProcessId", str(procs[slot].pid), "-Out", os.path.join(out_dir, f"end_slot{slot}.png"), "-Scale", "0.5"],
                       capture_output=True)
    for slot, n in INSTS.items():
        subprocess.run([sys.executable, "-I", os.path.join(PROJ, "tools", "sandbox.py"), "kill", str(n)], capture_output=True)
    for p in procs.values():
        try:
            p.wait(15)
        except subprocess.TimeoutExpired:
            pass
    hashes, stats = {}, {}
    for slot in INSTS:
        txt = open(os.path.join(out_dir, f"w4p_slot{slot}.log"), encoding="utf-8", errors="replace").read()
        hashes[slot] = dict(re.findall(r"^HASH (\d+) ([0-9a-f]+)$", txt, re.M))
        st = re.findall(r"stats: (.*)$", txt, re.M)
        stats[slot] = {"last": st[-1] if st else None, "desync": re.findall(r"DESYNC.*$", txt, re.M)[:3],
                       "errors": re.findall(r"(?:ERROR|WARNING).*$", txt, re.M)[:3],
                       "calls": len(re.findall(r"test call at poll", txt))}
    common = sorted(set.intersection(*(set(h) for h in hashes.values())), key=int)
    mism = [t for t in common if len({hashes[s][t] for s in INSTS}) > 1]
    summary = {"tag": tag, "environment": "SINGLE-PC, 4 instances, loopback, bots, fresh boot", "seconds": round(time.time() - t0),
               "state": state, "stats": stats, "hash_points_common": len(common), "hash_mismatches": len(mism),
               "first_mismatch": mism[0] if mism else None, "last_common": common[-1] if common else None}
    os.makedirs(os.path.join(PROJ, "evidence", "M2"), exist_ok=True)
    json.dump(summary, open(os.path.join(PROJ, "evidence", "M2", f"{tag}.json"), "w"), indent=1)
    print(json.dumps({k: summary[k] for k in ("hash_points_common", "hash_mismatches", "first_mismatch", "last_common", "state")}, indent=1))
    for slot in INSTS:
        print(slot, stats[slot])


if __name__ == "__main__":
    main()

"""M6: 60 fps front-end probe (docs/research/m6_sixty_title.md): does the title screen accept Start, how many simulation
steps run per rendered frame in each game mode, and (with --lockstep) a 2-player W4P session through the menus.

Usage: python -I tests/m6/sixty_title.py <tag> [--inst 15] [--pnach local/m6/sixty/test.pnach] [--groups "a;b"]
                                            [--ee 0|2] [--seconds 240] [--every 10]
         --keys          no W4P at all (W4P_CONFIG unset, no "warriors-4p M1" group): Return (= Start in the sandbox
                         keyboard profile) is posted to the game window (tools/winkeys.ps1) every --key-every s
                         (default 6) from --key-from s (default 25), until the title mode has been seen and left
                         or Start was accepted there (pad assigned to player 1), then --key-after more presses (default 0); at most
                         --key-max presses (default 14).
         default         W4P with Players = 1 on one instance; input = --script (nav format of tests/m2/nav_probe.py).
         --lockstep      two instances (inst, inst+1) in a 2-player W4P session on loopback (ports --port-base, default
                         46500/46501); slot 0 plays --script, slot 1 --script2; W4P hashes compared at the end.
         --live-input    (W4P modes) no bot input: every slot reads its own window's keyboard, e.g. keys posted with
                         tools/winkeys.ps1 by the tester while the run is going (pids in local/pcsx2/inst<N>/pid.txt).
         --state f.p2s   start from a savestate; --players N (single instance: slots 1..N-1 simulated, LocalBotN);
                         --random-bots: seeded random bot input on every slot (m1_run.bot_file).
         --polls N       length of the input files (default 40000).  --call-at "poll:fn:args,..." W4P CallAt (needs the
                         "warriors-4p test call" group).  --ini Section/Key=Value (repeatable).
Samples of slot 0 (PINE, every 0.25 s): W4P poll counter 0x000F0500, frame counter 0x0050C654 (FrameStats),
SimStep counter 0x005104F4, game-mode stack (top index 0x0050C784, stack 0x005E66A0), GameClock fixed-step flag
(*0x0050B734 + 0x54), pad 0 button history (0x005DD810 + 0x1C, index +0x2C).
Writes local/m6/sixty/<tag>/ (samples.jsonl, summary.json, screenshots) and evidence/M6/sixty_<tag>.json.
Environment: SINGLE-PC, scripted bots or posted key presses, no impairment. MTVU is forced off.
"""
import configparser
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(PROJ, "tools"))
sys.path.insert(0, os.path.join(PROJ, "tests", "m1"))
import m1_run  # noqa: E402
import sandbox  # noqa: E402
from pine import Pine  # noqa: E402

BTN = dict(m1_run.BTN, START=0x0800, SELECT=0x0100)
MODES = {0x005E56B8: "in-game", 0x005E65C0: "title", 0x005E57E0: "m5E57E0", 0x005E5D90: "loading"}
TITLE = 0x005E65C0


def opt(name, default, cast=str):
    return cast(sys.argv[sys.argv.index(name) + 1]) if name in sys.argv else default


def build_inputs(script_path, polls):
    """Nav script ("<poll> <BUTTON>[:hold] ...", '#' comments) -> W4P bot input records (20 bytes per poll)."""
    buttons = [0] * polls
    if script_path:
        for line in open(script_path, encoding="utf-8"):
            line = line.split("#")[0].strip()
            if not line:
                continue
            t, *keys = line.split()
            for k in keys:
                name, _, hold = k.partition(":")
                for i in range(int(t), min(polls, int(t) + int(hold or 3))):
                    buttons[i] |= BTN[name]
    return b"".join(m1_run.record(b) for b in buttons)


def read32s(pn, addrs):
    payload = b"".join(struct.pack("<BI", 2, a) for a in addrs)  # PINE read32 = opcode 2
    r = pn._xfer(payload)
    return [struct.unpack_from("<I", r, 4 * i)[0] for i in range(len(addrs))]


def sample(pn, w4p):
    poll, frame, step, top = read32s(pn, [0x000F0500, 0x0050C654, 0x005104F4, 0x0050C784])
    top = top - (1 << 32) if top & 0x80000000 else top
    mode = read32s(pn, [0x005E66A0 + 4 * top])[0] if 0 <= top < 16 else 0
    clock = read32s(pn, [0x0050B734])[0]
    fixed = read32s(pn, [clock + 0x54])[0] if 0x00100000 <= clock < 0x02000000 else None
    h = read32s(pn, [0x005DD810 + 0x1C, 0x005DD810 + 0x20, 0x005DD810 + 0x24, 0x005DD810 + 0x28, 0x005DD810 + 0x2C])
    hist = [(h[i // 2] >> (16 * (i % 2))) & 0xFFFF for i in range(8)]
    # pad assigned to player 1's HUD controller (HUD manager 0x00600840 -> controller record, +0x19 pad index, -1 = none);
    # the title assigns it when it sees Start pressed (FUN_001AE638 -> FUN_00144BF0(pad, 0x800))
    ctl = read32s(pn, [0x00600840])[0]
    p1pad = None
    if 0x00100000 <= ctl < 0x02000000:
        w = read32s(pn, [(ctl + 0x19) & ~3])[0]
        p1pad = (w >> (8 * ((ctl + 0x19) & 3))) & 0xFF
        p1pad = p1pad - 256 if p1pad & 0x80 else p1pad
    return {"poll": poll if w4p else None, "frame": frame, "step": step, "depth": top, "mode": mode,
            "fixed": fixed, "pad0_idx": h[4], "pad0_hist": hist, "p1pad": p1pad}


def set_ini(n, items):
    ini_path = os.path.join(sandbox.data_root(n), "inis", "PCSX2.ini")
    cp = configparser.ConfigParser(interpolation=None, strict=False)
    cp.optionxform = str
    cp.read(ini_path, encoding="utf-8")
    for sec, key, val in items:
        if not cp.has_section(sec):
            cp.add_section(sec)
        cp.set(sec, key, val)
    with open(ini_path, "w", encoding="utf-8") as fh:
        cp.write(fh, space_around_delimiters=True)


def shot(pid, path):
    subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", os.path.join(PROJ, "tools", "winshot.ps1"),
                    "-ProcessId", str(pid), "-Out", path, "-Scale", "0.4"], capture_output=True)


def summarize_only(tag):
    out = os.path.join(PROJ, "local", "m6", "sixty", tag)
    rows = [json.loads(line) for line in open(os.path.join(out, "samples.jsonl"))]
    old = json.load(open(os.path.join(out, "summary.json")))
    return out, rows, old


def main():
    tag = sys.argv[1]
    if "--summarize-only" in sys.argv:
        out, rows, old = summarize_only(tag)
        finish(tag, out, rows, [], old, None, [0, 1] if os.path.exists(os.path.join(out, "w4p_slot1.log")) else [0],
               os.path.exists(os.path.join(out, "w4p_slot0.log")))
        return
    inst = opt("--inst", 15, int)
    assert 15 <= inst <= 19 and (inst + 1 <= 19 or "--lockstep" not in sys.argv), "this probe uses sandbox instances 15-19"
    keys, lockstep = "--keys" in sys.argv, "--lockstep" in sys.argv
    w4p = not keys
    seconds, polls = opt("--seconds", 240, int), opt("--polls", 40000, int)
    pnach = opt("--pnach", os.path.join(PROJ, "local", "m6", "sixty", "test.pnach"))
    groups = [g for g in opt("--groups", "", str).split(";") if g]
    if w4p:
        groups = ["warriors-4p M1"] + [g for g in groups if g != "warriors-4p M1"]
    else:
        groups = [g for g in groups if g != "warriors-4p M1"]
    out = os.path.join(PROJ, "local", "m6", "sixty", tag)
    if os.path.exists(out):
        shutil.rmtree(out)
    os.makedirs(out)
    slots = [0, 1] if lockstep else [0]
    port_base = opt("--port-base", 46500, int)
    procs = {}
    for slot in slots:
        n = inst + slot
        d = sandbox.inst_dir(n)
        if os.path.exists(d):
            shutil.rmtree(d)
        sandbox.make(n, "default", pad2=True)  # fresh memory cards (created by PCSX2)
        items = [("EmuCore/Speedhacks", "vuThread", "false"), ("EmuCore/Speedhacks", "EECycleRate", opt("--ee", "0"))]
        for item in [a for i, a in enumerate(sys.argv) if i and sys.argv[i - 1] == "--ini"]:
            sec_key, val = item.split("=", 1)
            sec, key = sec_key.rsplit("/", 1)
            items.append((sec, key, val))
        set_ini(n, items)
        sandbox.install_patch(n, pnach, groups)
        env = dict(os.environ)
        env.pop("W4P_CONFIG", None)
        if w4p:
            script = opt("--script" if slot == 0 else "--script2", "", str)
            bot = os.path.join(out, f"bot{slot}.bin")
            rnd = "--random-bots" in sys.argv  # seeded random bots (m1_run.bot_file, never Start) on every slot
            if rnd:
                m1_run.bot_file(bot, 3000 + slot, polls)
            else:
                open(bot, "wb").write(build_inputs(script, polls))
            players = len(slots) if lockstep else opt("--players", 1, int)
            lines = ["[W4P]", "Enabled = true", f"Players = {players}", f"LocalSlot = {slot}", "PadForSlot0 = 0",
                     "PadForSlot1 = 4", "PadForSlot2 = 1", "PadForSlot3 = 2", f"ListenPort = {port_base + slot}",
                     "InputDelay = 2", "HashInterval = 30", f"LogFile = {os.path.join(out, f'w4p_slot{slot}.log')}", "Crop = false"]
            if "--live-input" not in sys.argv:  # --live-input: each instance's own keyboard (keys posted to its window)
                lines.append(f"BotInput = {bot}")
            if not lockstep:  # other players of a single-instance session: simulated in the same instance (LocalBotN)
                for i in range(1, players):
                    lb = os.path.join(out, f"localbot{i}.bin")
                    if rnd:
                        m1_run.bot_file(lb, 3000 + i, polls)
                    else:
                        open(lb, "wb").write(m1_run.record() * polls)
                    lines.append(f"LocalBot{i} = {lb}")
            if lockstep:
                lines.append(f"Peer{1 - slot} = 127.0.0.1:{port_base + 1 - slot}")
            if "--call-at" in sys.argv:
                lines.append(f"CallAt = {opt('--call-at', '', str)}")
            ini = os.path.join(out, f"w4p_slot{slot}.ini")
            open(ini, "w", encoding="utf-8").write("\n".join(lines) + "\n")
            env["W4P_CONFIG"] = ini
        extra = ["-statefile", os.path.abspath(opt("--state", "", str))] if "--state" in sys.argv else []
        cmd = [sandbox.FORK_EXE] + sandbox.cmd(n, extra)[1:]
        procs[slot] = subprocess.Popen(cmd, env=env, creationflags=getattr(subprocess, "DETACHED_PROCESS", 0))
        open(os.path.join(d, "pid.txt"), "w").write(str(procs[slot].pid))
    t0 = time.time()
    pn = None
    rows, presses = [], []
    every = opt("--every", 10, float)
    next_shot = t0 + every
    key_from, key_every, key_max, key_after = opt("--key-from", 25, float), opt("--key-every", 6, float), opt("--key-max", 14, int), opt("--key-after", 0, int)
    next_key = t0 + key_from
    title_seen = title_left = False
    after_left = 0
    fh = open(os.path.join(out, "samples.jsonl"), "w")
    while time.time() - t0 < seconds and all(p.poll() is None for p in procs.values()):
        time.sleep(0.25)
        try:
            pn = pn or Pine(sandbox.PINE_BASE + inst, timeout=3)
            s = sample(pn, w4p)
        except Exception as e:  # noqa: BLE001
            pn = None
            s = {"error": repr(e)}
        s["t"] = round(time.time() - t0, 2)
        rows.append(s)
        fh.write(json.dumps(s) + "\n")
        if "mode" in s:
            if s["mode"] == TITLE:
                title_seen = True
                if s.get("p1pad") is not None and s["p1pad"] >= 0:
                    title_left = True  # Start accepted at the title (the main menu is a page of the same mode)
            elif title_seen:
                title_left = True
        if keys and time.time() >= next_key and len(presses) < key_max and (not title_left or after_left < key_after):
            next_key = time.time() + key_every
            if title_left:
                after_left += 1
            presses.append({"t": round(time.time() - t0, 2), "mode": hex(s.get("mode", 0)), "frame": s.get("frame")})
            subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                            os.path.join(PROJ, "tools", "winkeys.ps1"), "-ProcessId", str(procs[0].pid), "-Seq", "Return:200"],
                           capture_output=True)
            shot(procs[0].pid, os.path.join(out, f"key_t{int(time.time() - t0):04d}.png"))
        if time.time() >= next_shot:
            next_shot += every
            shot(procs[0].pid, os.path.join(out, f"t{int(time.time() - t0):04d}_p{s.get('poll')}.png"))
    fh.close()
    for slot in slots:
        shot(procs[slot].pid, os.path.join(out, f"end_slot{slot}.png"))
    for slot in slots:
        subprocess.run([sys.executable, "-I", os.path.join(PROJ, "tools", "sandbox.py"), "kill", str(inst + slot)], capture_output=True)
    for p in procs.values():  # let the W4P logs be complete before reading them
        try:
            p.wait(20)
        except subprocess.TimeoutExpired:
            pass
    base = {"tag": tag, "environment": "SINGLE-PC, " + ("1 instance, no W4P, key presses posted to the window" if keys else
            f"{len(slots)} instance(s), W4P session, " + ("key presses posted to each window by the tester (--live-input)"
            if "--live-input" in sys.argv else "seeded random bots" if "--random-bots" in sys.argv else "scripted bot input")
            + (f", from savestate {opt('--state', '', str)}" if "--state" in sys.argv else "")), "groups": groups, "pnach": os.path.relpath(pnach, PROJ),
            "ee_cycle_rate": opt("--ee", "0"), "seconds": round(time.time() - t0)}
    finish(tag, out, rows, presses, base, None, slots, w4p)


def finish(tag, out, rows, presses, base, _unused, slots, w4p):
    # mode timeline and simulation steps per rendered frame in each mode
    ok = [r for r in rows if "mode" in r]
    timeline, per_mode = [], {}
    for a, b in zip(ok, ok[1:]):
        if not timeline or timeline[-1]["mode"] != hex(b["mode"]):
            timeline.append({"t": b["t"], "poll": b["poll"], "frame": b["frame"], "mode": hex(b["mode"]),
                             "name": MODES.get(b["mode"], ""), "depth": b["depth"], "fixed": b["fixed"]})
        if a["mode"] == b["mode"] and b["frame"] > a["frame"]:
            m = per_mode.setdefault(hex(b["mode"]), {"frames": 0, "steps": 0, "seconds": 0.0, "polls": 0})
            m["frames"] += b["frame"] - a["frame"]
            m["steps"] += b["step"] - a["step"]
            m["seconds"] += b["t"] - a["t"]
            if w4p:
                m["polls"] += b["poll"] - a["poll"]
    for m in per_mode.values():
        m["steps_per_frame"] = round(m["steps"] / m["frames"], 3) if m["frames"] else None
        m["frames_per_s"] = round(m["frames"] / m["seconds"], 2) if m["seconds"] else None
        m["polls_per_s"] = round(m["polls"] / m["seconds"], 2) if m["seconds"] and w4p else None
        m["seconds"] = round(m["seconds"], 1)
    acc = [r for r in ok if r["mode"] == TITLE and r.get("p1pad") is not None and r["p1pad"] >= 0]
    first_title = next((r for r in ok if r["mode"] == TITLE), None)
    start_accepted = {"t": acc[0]["t"], "poll": acc[0]["poll"], "frame": acc[0]["frame"], "mode": hex(acc[0]["mode"]),
                      "pad": acc[0]["p1pad"]} if acc else None
    for p in presses:  # mode 3 s after each key press
        later = [r for r in ok if r["t"] >= p["t"] + 3.0]
        p["mode_3s_later"] = hex(later[0]["mode"]) if later else None
    title_seen = any(r["mode"] == TITLE for r in ok)
    title_left = bool(acc) or any(r["mode"] != TITLE for r in ok[ok.index(first_title):]) if first_title else False
    summary = {k: base[k] for k in ("tag", "environment", "groups", "pnach", "ee_cycle_rate", "seconds") if k in base}
    if presses or "key_presses" not in base:
        summary["key_presses"] = presses
    else:
        summary["key_presses"] = base["key_presses"]
    summary.update({"title_seen": title_seen, "title_left": title_left,
               "title_first": {"t": first_title["t"], "poll": first_title["poll"], "frame": first_title["frame"]} if first_title else None,
               "start_accepted": start_accepted,
               "timeline": timeline, "per_mode": per_mode})
    if w4p:
        hashes, stats = {}, {}
        for slot in slots:
            try:
                txt = open(os.path.join(out, f"w4p_slot{slot}.log"), encoding="utf-8", errors="replace").read()
            except OSError:
                txt = ""
            hashes[slot] = dict(re.findall(r"^HASH (\d+) ([0-9a-f]+)$", txt, re.M))
            st = re.findall(r"stats: (.*)$", txt, re.M)
            stats[slot] = {"last": st[-1] if st else None, "desync": re.findall(r"DESYNC.*$", txt, re.M)[:3],
                           "errors": re.findall(r"(?:ERROR|WARNING).*$", txt, re.M)[:3]}
        common = sorted(set.intersection(*(set(h) for h in hashes.values())), key=int)
        mism = [t for t in common if len({hashes[s][t] for s in slots}) > 1]
        summary.update({"hash_points_common": len(common), "hash_mismatches": len(mism), "first_mismatch": mism[0] if mism else None,
                        "last_common": common[-1] if common else None, "w4p_stats": stats})
    json.dump(summary, open(os.path.join(out, "summary.json"), "w"), indent=1)
    os.makedirs(os.path.join(PROJ, "evidence", "M6"), exist_ok=True)
    json.dump(summary, open(os.path.join(PROJ, "evidence", "M6", f"sixty_{tag}.json"), "w"), indent=1)
    print(json.dumps({k: summary[k] for k in ("title_seen", "title_left", "title_first", "start_accepted", "per_mode", "key_presses", "hash_points_common",
                                              "hash_mismatches") if k in summary}, indent=1))
    print("timeline:", [(x["t"], x["poll"], x["mode"], x["name"], x["fixed"]) for x in timeline])


if __name__ == "__main__":
    main()

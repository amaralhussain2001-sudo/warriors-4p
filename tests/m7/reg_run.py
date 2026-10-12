"""M7 regression runner (criteria 5-7): ONE sandbox instance, single-player / original local 2-player / optional modes,
with the mod's patch groups installed (or none), scripted input, screenshots and a state sample every few seconds.

Usage: python -I tests/m7/reg_run.py <tag> --inst 12 [--players 1] [--script p1.txt] [--script2 p2.txt]
          [--groups "a;b"]        groups to enable besides "warriors-4p M1" (M1 is always added unless --no-patch)
          [--patch file.pnach]    default local/m7/reg.pnach (generated: python -I mod/make_pnach.py > local/m7/reg.pnach)
          [--no-patch]            no pnach at all (unmodified game; only possible with --input keys)
          [--input w4p|keys]      w4p = W4P input playback (W4P on, 1 or 2 local players, no peers);
                                  keys = W4P OFF, key presses posted to the window (tools/winkeys.ps1, PCSX2 keyboard
                                  bindings: pad 1 template, pad 2 sandbox --pad2)
          [--clock poll|sec]      keys mode: script times are polls (needs M1's counter) or seconds since launch
          [--rand1 "a-b,c-d"] [--rand2 ...]  w4p mode: seeded random bot input in these poll windows (never Start/Select)
          [--cards DIR]           start with DIR/Mcd001.ps2 (+ Mcd002.ps2) instead of fresh cards (copies)
          [--save-cards DIR]      copy the instance's memory cards to DIR at the end
          [--ini Sec/Key=Value]... [--ee N]  PCSX2.ini overrides (always pass EmuCore/Speedhacks/vuThread=false)
          [--callat "poll:fn:a0,..."]       W4P CallAt (needs a call group; test only)
          [--seconds 300] [--every 5] [--sample 2] [--scale 0.5]
Script lines: "<time> <BUTTON>[:<hold polls>] ..." (as tests/m2/nav_probe.py). Buttons: X SQ CIR TRI L1 R1 L2 R2 UP DOWN
LEFT RIGHT START SELECT LUP LDOWN LLEFT LRIGHT.
Writes local/m7/<tag>/: screenshots t<sec>_p<poll>.png, samples.jsonl (poll, frame counter, players, views, paused,
level, checkpoint ...), keys.jsonl (keys mode), emulog.txt, summary.json. Environment: SINGLE-PC, one instance,
bots/scripted input, no humans.
"""
import json
import os
import random
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(PROJ, "tools"))
sys.path.insert(0, os.path.join(PROJ, "tests", "m1"))
sys.path.insert(0, os.path.join(PROJ, "tests", "m2"))
import m1_run  # noqa: E402
import sandbox  # noqa: E402
from pine import Pine  # noqa: E402

BTN = dict(m1_run.BTN, START=0x0800, SELECT=0x0100)
KEYS = [  # PCSX2 keyboard bindings (System.Windows.Forms.Keys names) for pad 1 and pad 2
    {"X": "K", "CIR": "L", "SQ": "J", "TRI": "I", "START": "Return", "SELECT": "Back", "UP": "Up", "DOWN": "Down",
     "LEFT": "Left", "RIGHT": "Right", "LUP": "W", "LDOWN": "S", "LLEFT": "A", "LRIGHT": "D", "L1": "Q", "R1": "E",
     "L2": "D1", "R2": "D3"},
    {"X": "X", "CIR": "C", "SQ": "Z", "TRI": "V", "START": "P", "SELECT": "O", "UP": "D5", "DOWN": "D6", "LEFT": "D7",
     "RIGHT": "D8", "LUP": "Y", "LDOWN": "N", "LLEFT": "B", "LRIGHT": "M", "L1": "U", "R1": "R", "L2": "D0", "R2": "D9"},
]
POLL = 0x000F0500   # M1 hook counter (game pad reads)
FRAMES = 0x0050C654  # game frame counter (FrameStats, F-0046; frozen while paused)


def opt(name, default, cast=str):
    return cast(sys.argv[sys.argv.index(name) + 1]) if name in sys.argv else default


def parse(script_path):
    events = []
    if not script_path:
        return events
    for line in open(script_path, encoding="utf-8"):
        line = line.split("#")[0].strip()
        if not line:
            continue
        t, *keys = line.split()
        for k in keys:
            name, _, hold = k.partition(":")
            events.append((float(t), name, int(hold or 3)))
    return sorted(events)


def windows(spec):
    return [tuple(int(v) for v in w.split("-")) for w in spec.split(",") if w]


def build_records(events, rand, seed, polls=60000):
    """W4P bot file: scripted presses; inside the random windows (where no scripted press is active) seeded random
    play like m1_run.bot_file (walk / attack / grab / camera; never Start or Select)."""
    buttons = [0] * polls
    sticks = [(0x7F, 0x7F, 0x7F, 0x7F)] * polls
    scripted = [False] * polls
    for t, name, hold in events:
        for i in range(int(t), min(polls, int(t) + hold)):
            scripted[i] = True
            if name in ("LUP", "LDOWN", "LLEFT", "LRIGHT"):
                lx, ly, rx, ry = sticks[i]
                lx = {"LLEFT": 0x00, "LRIGHT": 0xFF}.get(name, lx)
                ly = {"LUP": 0x00, "LDOWN": 0xFF}.get(name, ly)
                sticks[i] = (lx, ly, rx, ry)
            else:
                buttons[i] |= BTN[name]
    rng = random.Random(seed)
    for a, b in rand:
        t = a
        while t < min(b, polls):
            dur = rng.randint(15, 60)
            kind = rng.choice(["walk", "walk", "walk", "attack", "attack", "grab", "camera", "idle"])
            lx, ly, rx, ry, pulse = 0x7F, 0x7F, 0x7F, 0x7F, 0
            if kind == "walk":
                lx, ly = rng.choice([(0x7F, 0x00), (0x00, 0x7F), (0xFF, 0x7F), (0x7F, 0xFF), (0x20, 0x20), (0xE0, 0x20)])
            elif kind == "attack":
                pulse = rng.choice([BTN["SQ"], BTN["X"], BTN["SQ"] | BTN["X"], BTN["TRI"]])
                lx, ly = rng.choice([(0x7F, 0x7F), (0x7F, 0x00)])
            elif kind == "grab":
                pulse = BTN["CIR"]
            elif kind == "camera":
                rx = rng.choice([0x00, 0xFF])
            for k in range(dur):
                i = t + k
                if i >= min(b, polls) or scripted[i]:
                    continue
                buttons[i] = pulse if (pulse and k % 8 < 3) else 0
                sticks[i] = (lx, ly, rx, ry)
            t += dur
    return b"".join(m1_run.record(buttons[i], *sticks[i]) for i in range(polls))


def set_ini(ini_path, items):
    import configparser
    cp = configparser.ConfigParser(interpolation=None, strict=False)
    cp.optionxform = str
    cp.read(ini_path, encoding="utf-8")
    for sec, key, val in items:
        if not cp.has_section(sec):
            cp.add_section(sec)
        cp.set(sec, key, val)
    with open(ini_path, "w", encoding="utf-8") as fh:
        cp.write(fh, space_around_delimiters=True)


def sample(pine, has_poll):
    gm = pine.read32(0x0051489C)
    top = pine.read32(0x0050C784)
    s = {"poll": pine.read32(POLL) if has_poll else None, "frames": pine.read32(FRAMES), "gm": hex(gm)}
    if 0x00100000 <= gm < 0x02000000:
        idx = pine.read32(gm + 0x56DC) & 0xFFFF
        s.update({"players": pine.read32(gm + 0x224) & 0xFFFF, "join": pine.read32(gm + 0x56E8) & 0xFF,
                  "cp": pine.read32(gm + 0x338) >> 16, "lvl_idx": idx,
                  "level": pine.read32(gm + 0x14D4 + idx * 0x84 + 4) if idx < 200 else None,
                  "gm14c": pine.read32(gm + 0x14C), "cinematic": pine.read32(gm + 0x410)})
    s.update({"views": pine.read32(0x0050B198), "cameras": pine.read32(0x0050B19C), "mode_top": top,
              "mode": hex(pine.read32(0x005E66A0 + 4 * top)) if 0 <= top < 64 else None})
    s["paused"] = s["mode"] == "0x5e6550"
    s["pad_owner"] = [((pine.read32(0x005DD810 + p * 0x50 + 0x40) >> 16) & 0xFFFF) for p in (0, 4)]
    return s


def main():
    tag = sys.argv[1]
    inst = opt("--inst", 12, int)
    players = opt("--players", 1, int)
    seconds, every, every_sample = opt("--seconds", 300, int), opt("--every", 5.0, float), opt("--sample", 2.0, float)
    mode = opt("--input", "w4p")
    no_patch = "--no-patch" in sys.argv
    assert not (no_patch and mode == "w4p"), "W4P input playback needs the M1 hook group"
    clock = opt("--clock", "poll" if not no_patch else "sec")
    out = os.path.join(PROJ, "local", "m7", tag)
    assert os.path.commonpath([out, PROJ]) == PROJ
    if os.path.exists(out):
        shutil.rmtree(out)
    os.makedirs(out)
    d = sandbox.inst_dir(inst)
    if os.path.exists(d):
        shutil.rmtree(d)
    root = sandbox.make(inst, "default", pad2=True)
    ini_items = []
    for item in [a for i, a in enumerate(sys.argv) if i and sys.argv[i - 1] == "--ini"]:
        sec_key, val = item.split("=", 1)
        sec, key = sec_key.rsplit("/", 1)
        ini_items.append((sec, key, val))
    if "--ee" in sys.argv:
        ini_items.append(("EmuCore/Speedhacks", "EECycleRate", opt("--ee", "0")))
    set_ini(os.path.join(root, "inis", "PCSX2.ini"), ini_items)
    groups = []
    if not no_patch:
        groups = ["warriors-4p M1"] + [g for g in opt("--groups", "").split(";") if g]
        sandbox.install_patch(inst, opt("--patch", os.path.join(PROJ, "local", "m7", "reg.pnach")), groups)
    cards = opt("--cards", "")
    if cards:  # copies only (e.g. a card saved by an earlier run of this script)
        for m in ("Mcd001.ps2", "Mcd002.ps2"):
            if os.path.exists(os.path.join(cards, m)):
                shutil.copyfile(os.path.join(cards, m), os.path.join(root, "memcards", m))
    ev = [parse(opt("--script", "")), parse(opt("--script2", ""))]
    env = dict(os.environ)
    env.pop("W4P_CONFIG", None)
    if mode == "w4p":
        lines = ["[W4P]", "Enabled = true", f"Players = {players}", "LocalSlot = 0", f"ListenPort = {41100 + inst}",
                 "InputDelay = 2", "HashInterval = 30", f"LogFile = {os.path.join(out, 'w4p.log')}", "Crop = false"]
        for p in range(players):
            path = os.path.join(out, f"bot{p}.bin")
            open(path, "wb").write(build_records(ev[p] if p < 2 else [], windows(opt(f"--rand{p + 1}", "")), 3000 + p))
            lines.append(f"BotInput = {path}" if p == 0 else f"LocalBot{p} = {path}")
        lines += [f"PadForSlot{i} = {v}" for i, v in enumerate((0, 4, 1, 2))]
        if "--callat" in sys.argv:
            lines.append(f"CallAt = {opt('--callat', '')}")
        ini = os.path.join(out, "w4p.ini")
        open(ini, "w", encoding="utf-8").write("\n".join(lines) + "\n")
        env["W4P_CONFIG"] = ini
    cmd = [sandbox.FORK_EXE] + sandbox.cmd(inst, [])[1:]
    p = subprocess.Popen(cmd, env=env, creationflags=getattr(subprocess, "DETACHED_PROCESS", 0))
    open(os.path.join(d, "pid.txt"), "w").write(str(p.pid))
    t0 = time.time()
    pine = None
    keyq = sorted([(t, pad, name, hold) for pad in (0, 1) for (t, name, hold) in ev[pad]]) if mode == "keys" else []
    key_proc, key_log = None, []
    next_shot, next_sample = t0 + every, t0 + 1.0
    samples = []
    poll = -1
    has_poll = not no_patch
    while time.time() - t0 < seconds and p.poll() is None:
        time.sleep(0.1)
        now = time.time()
        if keyq and (key_proc is None or key_proc.poll() is not None):
            if clock == "poll":
                try:
                    pine = pine or Pine(sandbox.PINE_BASE + inst, timeout=3)
                    poll = pine.read32(POLL)
                except Exception:  # noqa: BLE001
                    pine, poll = None, -1
                cur = poll
            else:
                cur = now - t0
            if cur >= 0 and cur >= keyq[0][0]:
                batch = [keyq.pop(0)]
                while keyq and keyq[0][0] <= cur:  # presses that are due together are posted one after another
                    batch.append(keyq.pop(0))
                seq = ",".join(f"{KEYS[pad][name]}:{max(120, hold * 40)}" for _, pad, name, hold in batch)
                key_proc = subprocess.Popen(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                                             os.path.join(PROJ, "tools", "winkeys.ps1"), "-ProcessId", str(p.pid),
                                             "-Seq", seq], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                key_log.append({"t": round(now - t0, 1), "at": cur, "seq": seq, "due": [b[0] for b in batch]})
        if now >= next_sample:
            next_sample = now + every_sample
            try:
                pine = pine or Pine(sandbox.PINE_BASE + inst, timeout=3)
                s = sample(pine, has_poll)
                s["t"] = round(now - t0, 1)
                samples.append(s)
                poll = s["poll"] if s["poll"] is not None else -1
            except Exception as e:  # noqa: BLE001
                pine = None
                samples.append({"t": round(now - t0, 1), "error": repr(e)})
        if now >= next_shot:
            next_shot = now + every
            name = os.path.join(out, f"t{int(now - t0):04d}_p{poll}.png")
            subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                            os.path.join(PROJ, "tools", "winshot.ps1"), "-ProcessId", str(p.pid), "-Out", name,
                            "-Scale", str(opt("--scale", 0.5, float))], capture_output=True)
    exited_early = p.poll() is not None
    open(os.path.join(out, "samples.jsonl"), "w").write("".join(json.dumps(s) + "\n" for s in samples))
    if key_log:
        open(os.path.join(out, "keys.jsonl"), "w").write("".join(json.dumps(k) + "\n" for k in key_log))
    subprocess.run([sys.executable, "-I", os.path.join(PROJ, "tools", "sandbox.py"), "kill", str(inst)], capture_output=True)
    time.sleep(2)
    save = opt("--save-cards", "")
    if save:
        os.makedirs(save, exist_ok=True)
        for m in ("Mcd001.ps2", "Mcd002.ps2"):
            src = os.path.join(root, "memcards", m)
            if os.path.exists(src):
                shutil.copyfile(src, os.path.join(save, m))
    log = os.path.join(root, "logs", "emulog.txt")
    tlb = 0
    if os.path.exists(log):
        shutil.copyfile(log, os.path.join(out, "emulog.txt"))
        tlb = sum(1 for line in open(log, encoding="utf-8", errors="replace") if "TLB Miss" in line)
    good = [s for s in samples if "error" not in s]
    polls = [s["poll"] for s in good if s.get("poll") is not None]
    frames = [s["frames"] for s in good]
    summary = {
        "tag": tag, "environment": "SINGLE-PC, one instance, bots/scripted input, no humans, no network",
        "instance": inst, "input": mode, "players": players, "patch": None if no_patch else os.path.relpath(
            opt("--patch", os.path.join(PROJ, "local", "m7", "reg.pnach")), PROJ).replace("\\", "/"),
        "groups": groups, "ini": [f"{a}/{b}={c}" for a, b, c in ini_items], "cards": cards or "fresh",
        "seconds": seconds, "emulator_exited_early": exited_early, "tlb_misses": tlb,
        "last_poll": polls[-1] if polls else None, "last_frames": frames[-1] if frames else None,
        "poll_advancing_last_60s": (len(polls) > 1 and polls[-1] > ([x["poll"] for x in good if x["t"] <= good[-1]["t"] - 60]
                                                                  or [polls[0]])[-1]) if polls else None,
        "first": good[0] if good else None, "last": good[-1] if good else None,
        "keys_posted": len(key_log),
    }
    open(os.path.join(out, "summary.json"), "w").write(json.dumps(summary, indent=1) + "\n")
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()

"""Drive the game's menus from a fresh boot with a scripted input list, taking screenshots, to find a deterministic
"boot to 2-player mission" input script (no savestate needed, so engine patches that change the heap layout work).

Usage: python -I tests/m2/nav_probe.py <tag> <script.txt> [--seconds 120] [--every 4] [--groups "a;b"] [--players 1]
                                        [--script2 p2.txt] [--script3 p3.txt] [--script4 p4.txt] [--pads 0,4,1,2]
                                        [--call "4300:0041A460:GM:1,4400:0041A460:GM:2"] [--track 0x641a20,0x6420f0] [--poke poll:addr:value,...]
  --call  needs the "warriors-4p test call" group: at each poll, call function(a0, a1, ...) on the game thread;
          "GM" = the GameMgr pointer. Results go to calls.txt.
  Other players' scripts are simulated in the same instance (W4P LocalBotN, test only).
Script lines: "<poll> <buttons...>[:<hold polls>]" e.g. "300 START:3", "420 RIGHT:3", "500 X:3"; "#" comments.
Buttons: X SQ CIR TRI L1 R1 L2 R2 UP DOWN LEFT RIGHT START SELECT. Polls are the game's pad reads (W4P hook counter).
One instance, W4P with the given player count (other slots get neutral input from a file of the same length).
Writes local/m2/<tag>/ (screenshots with poll numbers, logs). Environment: SINGLE-PC, scripted input.
"""
import os
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
INST = int(sys.argv[sys.argv.index('--inst') + 1]) if '--inst' in sys.argv else 6
PORT = 41100 + INST


def opt(name, default, cast=str):
    return cast(sys.argv[sys.argv.index(name) + 1]) if name in sys.argv else default


def build_inputs(script_path, polls=40000):
    """Returns a list of 20-byte records, one per poll, relative to the session start poll."""
    events = []
    for line in open(script_path, encoding="utf-8"):
        line = line.split("#")[0].strip()
        if not line:
            continue
        t, *keys = line.split()
        for k in keys:
            name, _, hold = k.partition(":")
            events.append((int(t), name, int(hold or 3)))
    buttons = [0] * polls
    sticks = [(0x7F, 0x7F, 0x7F, 0x7F)] * polls
    for t, name, hold in events:
        for i in range(t, min(polls, t + hold)):
            if name in ("LUP", "LDOWN", "LLEFT", "LRIGHT"):
                lx, ly, rx, ry = sticks[i]
                lx = {"LLEFT": 0x00, "LRIGHT": 0xFF}.get(name, lx)
                ly = {"LUP": 0x00, "LDOWN": 0xFF}.get(name, ly)
                sticks[i] = (lx, ly, rx, ry)
            else:
                buttons[i] |= BTN[name]
    return b"".join(m1_run.record(buttons[i], *sticks[i]) for i in range(polls))


def main():
    tag, script = sys.argv[1], sys.argv[2]
    seconds, every, players = opt("--seconds", 120, int), opt("--every", 4.0, float), opt("--players", 1, int)
    out = os.path.join(PROJ, "local", "m2", tag)
    if os.path.exists(out):
        shutil.rmtree(out)
    os.makedirs(out)
    d = sandbox.inst_dir(INST)
    if os.path.exists(d):
        shutil.rmtree(d)
    sandbox.make(INST, "default", pad2=True)
    for item in [a for i, a in enumerate(sys.argv) if i and sys.argv[i - 1] == "--ini"]:  # Section/Key=Value
        import configparser
        sec_key, val = item.split("=", 1)
        sec, key = sec_key.rsplit("/", 1)
        ini_path = os.path.join(sandbox.data_root(INST), "inis", "PCSX2.ini")
        cp = configparser.ConfigParser(interpolation=None, strict=False)
        cp.optionxform = str
        cp.read(ini_path, encoding="utf-8")
        if not cp.has_section(sec):
            cp.add_section(sec)
        cp.set(sec, key, val)
        with open(ini_path, "w", encoding="utf-8") as fh:
            cp.write(fh, space_around_delimiters=True)
    if "--ee" in sys.argv:  # EmuCore/Speedhacks EECycleRate (2 = 180 %, needed by the 60 fps patch)
        import configparser
        ini_path = os.path.join(sandbox.data_root(INST), "inis", "PCSX2.ini")
        cp = configparser.ConfigParser(interpolation=None, strict=False)
        cp.optionxform = str
        cp.read(ini_path, encoding="utf-8")
        cp.set("EmuCore/Speedhacks", "EECycleRate", opt("--ee", "0", str))
        with open(ini_path, "w", encoding="utf-8") as fh:
            cp.write(fh, space_around_delimiters=True)
    groups = ["warriors-4p M1"] + [g for g in opt("--groups", "", str).split(";") if g]
    sandbox.install_patch(INST, m1_run.PATCH, groups)  # memory cards: fresh (created by PCSX2) unless --memcards
    if "--memcards" in sys.argv:  # the user's memory card copies in local/ (never committed or shared)
        for m in ("Mcd001.ps2", "Mcd002.ps2"):
            shutil.copyfile(os.path.join(PROJ, "local", m), os.path.join(sandbox.data_root(INST), "memcards", m))
    open(os.path.join(out, "bot0.bin"), "wb").write(build_inputs(script))
    lines = ["[W4P]", "Enabled = true", f"Players = {players}", "LocalSlot = 0",
             f"ListenPort = {PORT}", "InputDelay = 2", "HashInterval = 30", f"LogFile = {os.path.join(out, 'w4p.log')}",
             f"BotInput = {os.path.join(out, 'bot0.bin')}", "Crop = false"]
    if "--watch" in sys.argv:  # debug: log writes to these addresses (W4P DebugWatch, slow)
        lines.append(f"DebugWatch = {opt('--watch', '', str)}")
    pads = opt("--pads", "0,4,1,2", str).split(",")
    lines += [f"PadForSlot{i} = {pads[i]}" for i in range(4)]
    for i in range(2, 5):
        sc = opt(f"--script{i}", "", str)
        if i <= players:
            path = os.path.join(out, f"bot{i - 1}.bin")
            open(path, "wb").write(build_inputs(sc) if sc else m1_run.record() * 40000)
            lines.append(f"LocalBot{i - 1} = {path}")
    ini = os.path.join(out, "w4p.ini")
    open(ini, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    env = dict(os.environ, W4P_CONFIG=ini)
    cmd = [sandbox.FORK_EXE] + sandbox.cmd(INST, [])[1:]
    p = subprocess.Popen(cmd, env=env, creationflags=getattr(subprocess, "DETACHED_PROCESS", 0))
    open(os.path.join(d, "pid.txt"), "w").write(str(p.pid))
    t0 = time.time()
    pine = None
    calls = [c.split(":") for c in opt("--call", "", str).split(",") if c]
    call_log = []
    next_shot = time.time() + every
    pokes = sorted([tuple(int(v, 0) for v in item.split(":")) for item in opt("--poke", "", str).split(",") if item])  # poll:addr:value
    track = [int(x, 0) for x in opt("--track", "", str).split(",") if x]  # human objects: log poll + x,y,z
    track_rows = []
    while time.time() - t0 < seconds and p.poll() is None:
        time.sleep(0.25)
        if pokes:  # test only: PINE writes at given polls (not deterministic; single instance)
            try:
                pine = pine or Pine(sandbox.PINE_BASE + INST, timeout=3)
                now_poll = pine.read32(0x000F0500)
                while pokes and now_poll >= pokes[0][0]:
                    _, addr, val = pokes.pop(0)
                    pine.write32(addr, val)
            except Exception:  # noqa: BLE001
                pine = None
        if track:
            try:
                pine = pine or Pine(sandbox.PINE_BASE + INST, timeout=3)
                row = [pine.read32(0x000F0500)]
                for o in track:
                    row += [round(struct.unpack("<f", struct.pack("<I", pine.read32(o + 0x10 + 4 * i)))[0], 2) for i in range(3)]
                for pad in (0, 1, 2, 4):  # what the game sees: port buffer sticks (+0x110) and buttons (+0x114)
                    row += [hex(pine.read32(0x005DE3C0 + pad * 0x140 + 0x110)), hex(pine.read32(0x005DE3C0 + pad * 0x140 + 0x114) & 0xFFFF)]
                track_rows.append(row)
            except Exception:  # noqa: BLE001
                pine = None
        if calls:
            try:
                pine = pine or Pine(sandbox.PINE_BASE + INST, timeout=3)
                poll = pine.read32(0x000F0500)
                if poll >= int(calls[0][0]):
                    t, fn, *args = calls.pop(0)
                    gm = pine.read32(0x0051489C)
                    vals = [gm if a == "GM" else int(a, 0) & 0xFFFFFFFF for a in args] + [0] * (4 - len(args))
                    pine.batch_write32([(0x000F0304, vals[0]), (0x000F0308, vals[1]), (0x000F030C, vals[2]),
                                        (0x000F0310, vals[3]), (0x000F0318, 0), (0x000F0300, int(fn, 16))])
                    for _ in range(80):
                        if pine.read32(0x000F0318) == 1:
                            break
                        time.sleep(0.05)
                    call_log.append({"poll": poll, "fn": fn, "args": [hex(v) for v in vals], "done": pine.read32(0x000F0318),
                                     "v0": hex(pine.read32(0x000F0314)), "players_after": pine.read32(gm + 0x224) & 0xFFFF})
                    open(os.path.join(out, "calls.txt"), "w").write(repr(call_log) + chr(10))
            except Exception as e:  # noqa: BLE001
                pine = None
                call_log.append({"error": repr(e)})
        if time.time() < next_shot:
            continue
        next_shot = time.time() + every
        try:
            pine = pine or Pine(sandbox.PINE_BASE + INST, timeout=3)
            poll = pine.read32(0x000F0500)
        except Exception:  # noqa: BLE001
            pine, poll = None, -1
        name = os.path.join(out, f"t{int(time.time() - t0):04d}_p{poll}.png")
        subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                        os.path.join(PROJ, "tools", "winshot.ps1"), "-ProcessId", str(p.pid), "-Out", name, "-Scale", "0.4"],
                       capture_output=True)
    try:  # game state at the end: GameMgr player count and handles (F-0020), views and cameras
        pine = pine or Pine(sandbox.PINE_BASE + INST, timeout=3)
        gm = pine.read32(0x0051489C)
        st = {"poll": pine.read32(0x000F0500), "gamemgr": hex(gm), "players": pine.read32(gm + 0x224) & 0xFFFF,
              "handles": [hex(pine.read32(gm + 0x228 + 4 * i)) for i in range(4)],
              "views": pine.read32(0x0050B198), "cameras": pine.read32(0x0050B19C),
              "join_allowed": pine.read32(gm + 0x56E8) & 0xFF,
              "gm_158_mode": pine.read32(gm + 0x158), "gm_14c": pine.read32(gm + 0x14C),
              "fx_old": [hex(pine.read32(0x005FDEB8))], "fx_new": [hex(pine.read32(0x000F0890 + 4 * i)) for i in range(4)],
              # pad state 0x005DD810 + pad*0x50: +0x42 owner player (-1 free), +0x4C connected (m2_pads_cameras.md)
              "pads": [(i, pine.read32(0x005DD810 + i * 0x50 + 0x4C), (pine.read32(0x005DD810 + i * 0x50 + 0x40) >> 16) & 0xFFFF)
                       for i in range(8)]}
        # player 1's squad (join candidates): brain = 0x006D53F0 + human[0x92]*0x2F0, squad = brain+0x20C,
        # members squad+0x48 (16 handles); human +0x1B0 player index (-1 AI), +0x1B1 join priority (FUN_0022A770)
        resolve = lambda h: pine.read32(0x006EBD38 + 8 * ((h >> 16) & 0xFFFF)) if h not in (0, 0xFFFFFFFF) else 0  # noqa: E731
        p1 = resolve(pine.read32(gm + 0x228))
        brain = 0x006D53F0 + ((pine.read32(p1 + 0x90) >> 16) & 0xFFFF) * 0x2F0 if p1 else 0
        squad = pine.read32(brain + 0x20C) if brain else 0
        members = []
        for i in range(16):
            h = pine.read32(squad + 0x48 + 4 * i) if squad else 0
            o = resolve(h)
            if o:
                b = pine.read32(o + 0x1B0)
                members.append((hex(h), hex(o), (b & 0xFF) - 256 if b & 0x80 else b & 0xFF, (b >> 8) & 0xFF))
        st["p1_squad"] = {"squad": hex(squad), "members": members}
        humans = []
        for k in range(-40, 120):
            o = 0x00640C80 + k * 0x6D0
            if 0x00597200 <= o and o + 0x6D0 <= 0x00715B5C:
                b = pine.read32(o + 0x1B0)
                if (b & 0xFF) != 0 or ((b >> 8) & 0xFF) != 0:
                    humans.append((hex(o), (b & 0xFF) - 256 if b & 0x80 else b & 0xFF, (b >> 8) & 0xFF))
        st["humans_pidx_prio"] = humans[:40]
        for item in [a for i, a in enumerate(sys.argv) if i and sys.argv[i - 1] == "--peek"]:  # addr:words
            a, _, n = item.partition(":")
            a = int(a, 0)
            st.setdefault("peek", {})[hex(a)] = [hex(pine.read32(a + 4 * k)) for k in range(int(n or "1", 0))]
        hud_ptrs = [pine.read32(0x000E0848 + 4 * k) for k in range(4)]  # m2_hud_full.md T_A (only with "4p hud B1")
        st["hud_TA"] = [hex(v) for v in hud_ptrs]
        st["hud_TA_fields"] = [(hex(pine.read32(v + 0x4120)), pine.read32(v + 0x40F4), pine.read32(v + 0x40F0), pine.read32(v + 0x40F8))
                               if 0x00080000 <= v < 0x02000000 else None for v in hud_ptrs]
        if "--freecheck" in sys.argv:  # is low RAM 0x00080000-0x000EFFFF untouched? (planned HUD objects/caves)
            blob = pine.dump(0x00080000, 0x00070000)
            nz = [i for i in range(0, len(blob), 4) if blob[i:i + 4] != bytes(4)]
            st["lowram_nonzero_words"] = len(nz)
            st["lowram_nonzero_first"] = [hex(0x00080000 + i) for i in nz[:8]]
            pages = {}
            for i in nz:
                pages[(0x00080000 + i) & ~0xFFF] = pages.get((0x00080000 + i) & ~0xFFF, 0) + 1
            st["lowram_nonzero_pages_4k"] = {hex(k): v for k, v in sorted(pages.items())}
    except Exception as e:  # noqa: BLE001
        st = {"error": repr(e)}
    open(os.path.join(out, "state.txt"), "w").write(repr(st) + chr(10))
    if track_rows:
        open(os.path.join(out, "track.csv"), "w").write("".join(",".join(map(str, r)) + chr(10) for r in track_rows))
    print("state:", st)
    subprocess.run([sys.executable, "-I", os.path.join(PROJ, "tools", "sandbox.py"), "kill", str(INST)], capture_output=True)
    print("\n".join(sorted(os.listdir(out))))


if __name__ == "__main__":
    main()

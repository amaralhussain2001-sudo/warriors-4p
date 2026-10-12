"""Self-test of the 2-4 player co-op package (dist/warriors-4p-coop) on ONE PC.

One host and 1-3 joiners, each with its own launcher (the package's Start-Coop.ps1 in test mode: -TestFile with JSON
answers, no questions), its own data folder, co-op save folder and log folder, connected through the package's own
w4p-net helpers on loopback (--no-stun --bind 127.0.0.1), fresh memory cards, scripted bots (W4P BotInput). Afterwards
the hash streams of all instances are compared. Environment label: SINGLE-PC, loopback, no impairment, bots.

Usage:
  python -I tests/m5/package4_selftest.py <tag> --preset m13 --players 4 --seconds 720 [--late-joiner]
  python -I tests/m5/package4_selftest.py <tag> --preset m1_60 --players 2 --seconds 420 [--late-joiner]
  python -I tests/m5/package4_selftest.py <tag> --preset m1_30 --players 2 --seconds 240 --lan    (Join by IP mode)
  python -I tests/m5/package4_selftest.py <tag> --mismatch        (lobby only: different co-op saves, then fixed)
  --title-keys: slot 0 gets NO bot input; the harness posts real key presses (Enter = Start) to player 1's game window
        with tools/winkeys.ps1 at 150-330 s after his emulator started (60 fps title-screen probe).
  --groups-2p: test-only isolation: base patch groups of the 2-player package (M1, own view, hud) instead of the 12.
Options: --group NAME (co-op save name, default = tag), --saves-root DIR (persistent per-PC co-op save folders
<DIR>/pc<k>; default: inside the run folder), --wide yes|no (default yes).

Presets (test-only input, never part of the package):
  m13   30 fps; slots 0-3 play tests/m2/nav/pol_p1..p4.txt up to poll 9000 (boot to Mission 1 in 2-player mode, skip
        votes, players 3-4 press Start at 8200/8350), then seeded random bots (never Start/Select). The level jump to
        Mission 13 uses the test-only group "warriors-4p test call" and CallAt (as in every M2/M5 4-instance run).
  m1_60 60 fps; tests/m2/nav/boot_to_m1_2p_60.txt / boot_to_m1_2p_60_p2.txt, random bots from poll 12000. 2 players.
  m1_30 30 fps; boot_to_m1_2p.txt / p2_join.txt, random bots from poll 4700. 2 players.
  title60 60 fps; slot 0 presses Start (held 20 polls) every 400 polls from poll 7900, slot 1 nothing (title probe).
  m1_60x2 60 fps; tests/m5/nav/boot_m1_2p_60x2.txt / p2_join_60x2.txt (the 30 fps scripts with doubled gaps after the
        first Start; m1_60's scripts stop at the title with fresh memory cards), random bots from poll 13000. 2 players.
Ports (avoid the coordinator's 41200-41203 and 46000-46400): emulator 47000+k, helper slot ports 47100+10k,
ICE 47400+k, Join-by-IP lobby/emulator 47050+k. Never kills a process: every launcher closes its own emulator after
--seconds (window close) and ends by itself. Waits until at most 4 pcsx2-qtx64.exe processes run before starting.
Writes local/m5/pkg4/<tag>/ and evidence/M5/<tag>.json (+ small logs in evidence/M5/pkg4/<tag>/).
"""
import glob
import hashlib
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
sys.path.insert(0, os.path.join(PROJ, "tests", "m2"))
import m1_run  # noqa: E402
import nav_probe  # noqa: E402
import sandbox  # noqa: E402

PKG = os.path.join(PROJ, "dist", "warriors-4p-coop")
NAV = os.path.join(PROJ, "tests", "m2", "nav")
POLLS = 60000
ISO_MD5 = "56a021f03e5718aa3e4760eb0dc179cd"
HELPER_ARGS = ["--no-stun", "--bind", "127.0.0.1"]
TEST_CALLS = "CallAt = 3999:0041ABC0:1,4009:00160D78:0x01FD9F9C"
PRESETS = {
    "m13": {"fps60": False, "scripts": ["pol_p1.txt", "pol_p2.txt", "pol_p3.txt", "pol_p4.txt"], "cut": 9000,
            "rand_from": 9000, "test_call": True},
    "m1_60": {"fps60": True, "scripts": ["boot_to_m1_2p_60.txt", "boot_to_m1_2p_60_p2.txt"], "cut": None,
              "rand_from": 12000, "test_call": False},
    "m1_30": {"fps60": False, "scripts": ["boot_to_m1_2p.txt", "p2_join.txt"], "cut": None, "rand_from": 4700,
              "test_call": False},
    "title60": {"fps60": True, "scripts": ["../../m5/nav/title_probe_60.txt", "../../m5/nav/empty_60.txt"], "cut": None,
                "rand_from": 59000, "test_call": False},
    "m1_60x2": {"fps60": True, "scripts": ["../../m5/nav/boot_m1_2p_60x2.txt", "../../m5/nav/p2_join_60x2.txt"], "cut": None,
                "rand_from": 13000, "test_call": False},
}


def opt(name, default, cast=str):
    return cast(sys.argv[sys.argv.index(name) + 1]) if name in sys.argv else default


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def iso_checked_key():
    """The launcher's 'IsoChecked' value, after verifying the ISO's MD5 once (read-only) and caching the result."""
    st = os.stat(sandbox.ISO)
    cache = os.path.join(PROJ, "local", "m5", "pkg4", "iso_md5.json")
    key = f"{sandbox.ISO}|{st.st_size}|{int(st.st_mtime)}"
    try:
        c = json.load(open(cache))
        if c.get("key") == key and c.get("md5") == ISO_MD5:
            return f"{sandbox.ISO}|{st.st_size}"
    except (OSError, ValueError):
        pass
    h = hashlib.md5()
    with open(sandbox.ISO, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 22), b""):
            h.update(chunk)
    if h.hexdigest() != ISO_MD5:
        sys.exit("ISO MD5 differs from the expected USA v1.03 dump")
    os.makedirs(os.path.dirname(cache), exist_ok=True)
    json.dump({"key": key, "md5": h.hexdigest()}, open(cache, "w"))
    return f"{sandbox.ISO}|{st.st_size}"


def pcsx2_count():
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq pcsx2-qtx64.exe", "/FO", "CSV", "/NH"],
                         capture_output=True, text=True).stdout
    return sum(1 for line in out.splitlines() if line.lower().startswith('"pcsx2-qtx64.exe"'))


def wait_for_slots(limit=4, max_wait=4 * 3600):
    t0 = time.time()
    while True:
        n = pcsx2_count()
        if n <= limit:
            return n
        if time.time() - t0 > max_wait:
            sys.exit(f"{n} pcsx2-qtx64.exe processes still running after {max_wait} s; not starting")
        print(f"waiting: {n} pcsx2-qtx64.exe running (limit {limit})", flush=True)
        time.sleep(30)


def bot_file(path, preset, slot):
    p = PRESETS[preset]
    script = os.path.join(NAV, p["scripts"][slot])
    if p["cut"]:  # drop the later pause requests of the policy test scripts
        cut = os.path.join(os.path.dirname(path), f"script_slot{slot}.txt")
        with open(cut, "w", encoding="utf-8") as f:
            for line in open(script, encoding="utf-8"):
                body = line.split("#")[0].strip()
                if body and int(body.split()[0]) >= p["cut"]:
                    continue
                f.write(line)
        script = cut
    data = bytearray(nav_probe.build_inputs(script, POLLS))
    tmp = path + ".rand"
    m1_run.bot_file(tmp, 5000 + slot, POLLS)
    rnd = open(tmp, "rb").read()[: POLLS * 20]
    data[p["rand_from"] * 20:] = rnd[p["rand_from"] * 20:]
    os.remove(tmp)
    open(path, "wb").write(bytes(data))
    return path


def make_pc(work, k, settings_common, saves_root):
    d = os.path.join(work, f"pc{k}")
    os.makedirs(os.path.join(d, "logs"), exist_ok=True)
    saves = os.path.join(saves_root, f"pc{k}") if saves_root else os.path.join(d, "coop-saves")
    os.makedirs(saves, exist_ok=True)
    with open(os.path.join(d, "settings.txt"), "w", encoding="utf-8", newline="\r\n") as f:
        f.write("\n".join(f"{a}={b}" for a, b in settings_common.items()) + "\n")
    return {"k": k, "dir": d, "saves": saves, "data": os.path.join(d, "data"), "logs": os.path.join(d, "logs"),
            "status": os.path.join(d, "status.json"), "test": os.path.join(d, "test.json"), "proc": None}


def launch(pc, answers):
    answers = dict(answers, savesDir=pc["saves"], logsDir=pc["logs"], statusFile=pc["status"])
    json.dump(answers, open(pc["test"], "w", encoding="utf-8"), indent=1)
    out = open(os.path.join(pc["dir"], "launcher.out"), "w", encoding="utf-8")
    cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", os.path.join(PKG, "Start-Coop.ps1"),
           "-SettingsFile", os.path.join(pc["dir"], "settings.txt"), "-DataDir", pc["data"], "-TestFile", pc["test"]]
    pc["proc"] = subprocess.Popen(cmd, stdout=out, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
    pc["t_launch"] = time.time()


def read_status(pc):
    try:
        return json.load(open(pc["status"], encoding="utf-8-sig"))
    except (OSError, ValueError):
        return None


def shot(pid, out):
    subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", os.path.join(PROJ, "tools", "winshot.ps1"),
                    "-ProcessId", str(pid), "-Out", out, "-Scale", "0.4"], capture_output=True, timeout=60)


def w4p_summary(path):
    txt = open(path, encoding="utf-8", errors="replace").read() if os.path.exists(path) else ""
    st = re.findall(r"stats: (.*)$", txt, re.M)
    sd = re.findall(r"shutdown: (.*)$", txt, re.M)
    return {"hashes": dict(re.findall(r"^HASH (\d+) ([0-9a-f]+)$", txt, re.M)),
            "ghashes": {t: g for t, g, _ in re.findall(r"^GHASH (\d+) ([0-9a-f]+) ([0-9a-f]+)$", txt, re.M)},
            "info": {"session_started": bool(re.search(r"session started at guest poll", txt)),
                     "matches": re.findall(r"player \d matches[^\r\n]*", txt),
                     "errors": re.findall(r"(?:ERROR|WARNING|DESYNC|NOTE)[^\r\n]*", txt)[:6],
                     "test_calls": len(re.findall(r"test call at poll", txt)),
                     "pauses": len(re.findall(r"game paused at poll", txt)),
                     "skip_votes": len(re.findall(r"skip vote by player", txt)),
                     "leaves": re.findall(r"player \d leaves the session[^\r\n]*", txt),
                     "host_gone": "the host did not come back" in txt,
                     "last_stats": st[-1] if st else None, "shutdown": sd[-1] if sd else None}}


def compare(sums):
    hs = [s["hashes"] for s in sums]
    common = sorted(set.intersection(*(set(h) for h in hs)), key=int) if hs else []
    mism = [t for t in common if len({h[t] for h in hs}) > 1]
    gs = [s["ghashes"] for s in sums]
    gm = [t for t in common if len({g.get(t, "") for g in gs}) > 1]
    return {"hash_points_common": len(common), "hash_mismatches": len(mism), "game_hash_mismatches": len(gm),
            "first_mismatch": mism[0] if mism else None, "first_common": common[0] if common else None,
            "last_common": common[-1] if common else None}


def emulog_tlb(path):
    if not os.path.exists(path):
        return None
    return len(re.findall(r"TLB Miss", open(path, encoding="utf-8", errors="replace").read()))


def copy_small(pc, dest):
    os.makedirs(dest, exist_ok=True)
    st = read_status(pc) or {}
    logdir = st.get("logDir")
    if logdir and os.path.isdir(logdir):
        for f in ("lobby-log.txt", "lobby-screens.txt", "launcher-status.json", "connection-log.txt", "connection-stats.json", "w4p.ini"):
            p = os.path.join(logdir, f)
            if os.path.exists(p):
                shutil.copy2(p, os.path.join(dest, f))
    out = os.path.join(pc["dir"], "launcher.out")
    if os.path.exists(out):
        shutil.copy2(out, os.path.join(dest, "launcher.out.txt"))


def run_mismatch(tag, work, settings_common):
    """Lobby only. Phase A: the joiner's co-op save differs -> the host must not start. Phase B: the joiner gets the
    host's file -> the START handshake completes (stopBeforeGame: no emulator)."""
    res = {}
    group = "mm"
    pcs = [make_pc(work, k, settings_common, None) for k in range(2)]
    for k, pc in enumerate(pcs):  # dummy files standing in for memory cards (hash comparison only, never loaded)
        os.makedirs(os.path.join(pc["saves"], group), exist_ok=True)
        open(os.path.join(pc["saves"], group, "Mcd001.ps2"), "wb").write(bytes([0xFF - k]) * 4096)
    for phase in ("A_mismatch", "B_fixed"):
        if phase == "B_fixed":
            shutil.copy2(os.path.join(pcs[0]["saves"], group, "Mcd001.ps2"), os.path.join(pcs[1]["saves"], group, "Mcd001.ps2"))
        code_file = os.path.join(work, f"joincode_{phase}.txt")
        if os.path.exists(code_file):
            os.remove(code_file)
        for pc in pcs:
            if os.path.exists(pc["status"]):
                os.remove(pc["status"])
        base = {"players": 2, "group": group, "fps60": True, "wide": True, "codeFile": code_file, "helperArgs": HELPER_ARGS,
                "lobbyTimeoutSec": 45, "stopBeforeGame": True}
        for k, pc in enumerate(pcs):
            ans = dict(base, mode="host" if k == 0 else "join", autoStart=(k == 0), startAfterSec=3,
                       emuPort=47000 + k, slotPorts=47100 + 10 * k, icePort=47400 + k)
            launch(pc, ans)
            if k == 0:
                t0 = time.time()
                while not os.path.exists(code_file) and time.time() - t0 < 60:
                    time.sleep(0.5)
        for pc in pcs:
            pc["proc"].wait(timeout=180)
        res[phase] = {f"pc{pc['k']}": read_status(pc) for pc in pcs}
        for pc in pcs:
            copy_small(pc, os.path.join(PROJ, "evidence", "M5", "pkg4", tag, phase, f"pc{pc['k']}"))
    a, b = res["A_mismatch"], res["B_fixed"]
    res["verdict"] = {
        "A_host_refused": bool(a["pc0"]) and a["pc0"].get("phase") == "lobby-timeout" and a["pc0"].get("problems", {}).get("2") == "save",
        "A_joiner_not_started": bool(a["pc1"]) and a["pc1"].get("phase") in ("lobby-timeout", "lobby-hostleft"),
        "A_joiner_saw_mismatch": bool(a["pc1"]) and "own-save" in (a["pc1"].get("problems") or {}),
        "B_both_started": bool(b["pc0"]) and bool(b["pc1"]) and b["pc0"].get("phase") == "start-ok" and b["pc1"].get("phase") == "start-ok",
        "B_same_save": bool(b["pc0"]) and bool(b["pc1"]) and b["pc0"].get("saveHash") == b["pc1"].get("saveHash") != "new"}
    return res


def main():
    tag = sys.argv[1]
    if not os.path.exists(os.path.join(PKG, "Start-Coop.ps1")):
        sys.exit("build the package first: python -I tools/make_package4.py")
    work = os.path.join(PROJ, "local", "m5", "pkg4", tag)
    assert os.path.commonpath([work, PROJ]) == PROJ
    if os.path.exists(work):
        shutil.rmtree(work)
    os.makedirs(work)
    bios = glob.glob(os.path.join(sandbox.BIOS_DIR, "*.ROM0"))[0]
    preset = opt("--preset", "m13")
    fps60 = PRESETS.get(preset, PRESETS["m13"])["fps60"]
    settings_common = {"Iso": sandbox.ISO, "Bios": bios, "Quality": "1", "Fullscreen": "no", "Fps60": "yes" if fps60 else "no",
                       "Widescreen": opt("--wide", "yes"), "Renderer": "14", "Adapter": "NVIDIA GeForce RTX 5090",
                       "IsoChecked": iso_checked_key()}
    vf = open(os.path.join(PKG, "VERSION.txt"), encoding="utf-8").read()
    summary = {"tag": tag, "package": re.search(r"id=(\S+)", vf).group(1), "args": sys.argv[2:],
               "environment": "SINGLE-PC, package launcher in test mode, loopback, fresh memory cards, bots, no impairment"}
    if "--mismatch" in sys.argv:
        summary["environment"] = "SINGLE-PC, lobby only (no emulator), loopback helpers, dummy co-op save files"
        summary.update(run_mismatch(tag, work, settings_common))
        os.makedirs(os.path.join(PROJ, "evidence", "M5"), exist_ok=True)
        json.dump(summary, open(os.path.join(PROJ, "evidence", "M5", f"{tag}.json"), "w"), indent=1)
        print(json.dumps(summary["verdict"], indent=1))
        return

    players = opt("--players", 4, int)
    seconds = opt("--seconds", 720, int)
    lan = "--lan" in sys.argv
    group = opt("--group", tag)
    saves_root = opt("--saves-root", "")
    if saves_root:
        saves_root = os.path.abspath(saves_root)
        assert os.path.commonpath([saves_root, PROJ]) == PROJ
    p = PRESETS[preset]
    pcs = [make_pc(work, k, settings_common, saves_root) for k in range(players)]
    code_file = os.path.join(work, "joincode.txt")
    for pc in pcs:
        k = pc["k"]
        ans = {"mode": ("lanhost" if k == 0 else "lanjoin") if lan else ("host" if k == 0 else "join"),
               "players": players, "group": group, "fps60": p["fps60"], "wide": opt("--wide", "yes") == "yes",
               "codeFile": code_file, "helperArgs": HELPER_ARGS, "emuPort": 47000 + k, "slotPorts": 47100 + 10 * k,
               "icePort": 47400 + k, "lanPort": 47050 + k, "lanBind": "127.0.0.1", "hostIp": "127.0.0.1", "hostPort": 47050,
               "autoStart": k == 0, "startAfterSec": 5, "lobbyTimeoutSec": 300, "runSeconds": seconds,
               "botFile": bot_file(os.path.join(pc["dir"], "bot.bin"), preset, k)}
        if "--groups-2p" in sys.argv:  # test-only isolation: the 2-player package's base groups (no 4p/session groups)
            ans["baseGroups"] = ["warriors-4p M1", "warriors-4p own view", "warriors-4p hud"]  # 2-player package set
        if k == 0 and "--title-keys" in sys.argv:
            del ans["botFile"]  # real keyboard input path for player 1
        if p["test_call"]:  # test-only: level jump to Mission 13 at fixed polls (never in the package)
            ans["extraGroups"] = ["warriors-4p test call"]
            ans["extraW4P"] = [TEST_CALLS]
        pc["answers"] = ans
    summary["saves_before"] = {f"pc{pc['k']}": sorted(os.listdir(pc["saves"])) for pc in pcs}
    n = wait_for_slots(4)
    summary["pcsx2_running_before_start"] = n
    t_start = time.time()
    launch(pcs[0], pcs[0]["answers"])
    if not lan:
        while not os.path.exists(code_file) and time.time() - t_start < 90:
            time.sleep(0.5)
        if not os.path.exists(code_file):
            print("host printed no join code; see", os.path.join(pcs[0]["dir"], "launcher.out"))
    else:
        time.sleep(2)
    for pc in pcs[1:]:
        launch(pc, pc["answers"])
        time.sleep(1)
    # watch: emulator pids, screenshots, optional late joiner
    pids, shots, late = {}, [], None
    key_times, keys_sent = list(range(150, 331, 20)), []
    deadline = time.time() + seconds + 900
    late_at = None
    while time.time() < deadline and any(pc["proc"].poll() is None for pc in pcs):
        time.sleep(5)
        for pc in pcs:
            st = read_status(pc)
            if st and st.get("emuPid") and pc["k"] not in pids:
                pids[pc["k"]] = (st["emuPid"], time.time())
        if len(pids) == players and late_at is None:
            late_at = max(t for _, t in pids.values()) + 60
        for k, (pid, t0) in list(pids.items()):
            for mark in (90, seconds - 45):
                name = os.path.join(work, f"shot_pc{k}_t{mark:04d}.png")
                if time.time() - t0 >= mark and name not in shots and time.time() - t0 < seconds - 5:
                    shots.append(name)
                    try:
                        shot(pid, name)
                    except Exception as e:  # noqa: BLE001
                        print("screenshot failed", e)
        if "--title-keys" in sys.argv and 0 in pids and key_times and time.time() - pids[0][1] >= key_times[0]:
            key_times.pop(0)
            r = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                                os.path.join(PROJ, "tools", "winkeys.ps1"), "-ProcessId", str(pids[0][0]), "-Seq", "Return:200"],
                               capture_output=True, text=True, timeout=60)
            keys_sent.append({"t": round(time.time() - pids[0][1]), "rc": r.returncode, "out": (r.stdout + r.stderr).strip()[-200:]})
            try:
                shot(pids[0][0], os.path.join(work, f"key_pc0_t{keys_sent[-1]['t']:04d}.png"))
            except Exception:  # noqa: BLE001
                pass
        if "--late-joiner" in sys.argv and not lan and late is None and late_at and time.time() >= late_at:
            late = make_pc(work, players, settings_common, None)  # a 5th launcher with the same code, after the start
            k = late["k"]
            launch(late, {"mode": "join", "players": players, "group": group, "codeFile": code_file, "helperArgs": HELPER_ARGS,
                          "emuPort": 47000 + k, "slotPorts": 47100 + 10 * k, "icePort": 47400 + k, "lobbyTimeoutSec": 45})
    still = [pc["k"] for pc in pcs if pc["proc"].poll() is None]
    if late is not None:
        try:
            late["proc"].wait(timeout=120)
        except subprocess.TimeoutExpired:
            still.append(late["k"])
    summary["seconds_total"] = round(time.time() - t_start)
    summary["launchers_still_running"] = still
    # results
    sums, per_pc = [], {}
    for pc in pcs:
        st = read_status(pc) or {}
        logdir = st.get("logDir", "")
        s = w4p_summary(os.path.join(logdir, "w4p.log")) if logdir else {"hashes": {}, "ghashes": {}, "info": {}}
        sums.append(s)
        stats = None
        try:
            stats = json.load(open(os.path.join(logdir, "connection-stats.json")))
        except (OSError, ValueError):
            pass
        conn_txt = ""
        try:
            conn_txt = open(os.path.join(logdir, "connection-log.txt"), encoding="utf-8", errors="replace").read()
        except OSError:
            pass
        per_pc[f"pc{pc['k']}"] = {
            "status": {k: st.get(k) for k in ("phase", "mode", "slot", "players", "group", "delay", "fps60", "wide", "sid",
                                              "maxRttMs", "problems", "exitCode", "forcedClose", "normalEnd", "notSavedReason",
                                              "savedBack", "saveHash", "cardHashStart", "saveHashEnd", "helperError")},
            "events": st.get("events"), "w4p": s["info"], "hash_points": len(s["hashes"]),
            "tlb_misses": emulog_tlb(os.path.join(logdir, "emulog.txt")) if logdir else None,
            "helper": None if not stats else {
                "emu_rx": stats.get("emu_rx"), "emu_tx": stats.get("emu_tx"), "emu_drop": stats.get("emu_drop"),
                "loopback_strangers": stats.get("loopback_strangers"),
                "links": [{x: L.get(x) for x in ("peer", "kind", "path", "attempts", "connect_ms", "state", "ping_p50", "ping_p95",
                                                  "ping_max", "fwd_out", "bad_tag", "bad_mac", "bad_src", "send_err")}
                          for L in stats.get("links", [])],
                "no_route": sum(x.get("data_no_route", 0) for x in stats.get("slots", []))},
            "lobby_closed_refusals": len(re.findall(r"direct dial refused: lobby closed", conn_txt)),
            "saves_after": {g: {f: sha256(os.path.join(pc["saves"], g, f)) for f in ("Mcd001.ps2", "Mcd002.ps2")
                                if os.path.exists(os.path.join(pc["saves"], g, f))}
                            for g in os.listdir(pc["saves"]) if os.path.isdir(os.path.join(pc["saves"], g))}}
        copy_small(pc, os.path.join(PROJ, "evidence", "M5", "pkg4", tag, f"pc{pc['k']}"))
    summary["pcs"] = per_pc
    used = set()  # the package id each launcher reported (the package may be rebuilt while a run waits for slots)
    for pc in pcs:
        for f in glob.glob(os.path.join(pc["logs"], "*", "lobby-log.txt")):
            used.update(re.findall(r"package ([0-9a-f]{12})", open(f, encoding="utf-8", errors="replace").read()))
    summary["package_used"] = sorted(used)
    summary.update(compare(sums))
    ends = {per_pc[k]["status"].get("saveHashEnd") for k in per_pc}
    summary["co_op_save"] = {"group": group, "all_saved_back": all(per_pc[k]["status"].get("savedBack") for k in per_pc),
                             "identical_after": len(ends) == 1 and None not in ends and "" not in ends,
                             "hash_after": next(iter(ends)) if len(ends) == 1 else sorted(str(e) for e in ends)}
    if late is not None:
        lst = read_status(late) or {}
        summary["late_joiner"] = {"phase": lst.get("phase"), "slot": lst.get("slot"), "events": lst.get("events"),
                                  "host_refusals_logged": per_pc["pc0"]["lobby_closed_refusals"]}
        copy_small(late, os.path.join(PROJ, "evidence", "M5", "pkg4", tag, "late_joiner"))
    summary["screenshots"] = [os.path.relpath(s, PROJ) for s in shots]
    if "--title-keys" in sys.argv:
        summary["keys_sent"] = keys_sent
    os.makedirs(os.path.join(PROJ, "evidence", "M5"), exist_ok=True)
    json.dump(summary, open(os.path.join(PROJ, "evidence", "M5", f"{tag}.json"), "w"), indent=1)
    print(json.dumps({k: summary[k] for k in ("hash_points_common", "hash_mismatches", "game_hash_mismatches", "first_mismatch",
                                              "last_common", "co_op_save", "launchers_still_running") if k in summary}, indent=1))
    for k, v in per_pc.items():
        print(k, v["status"].get("phase"), "slot", v["status"].get("slot"), "points", v["hash_points"], "normalEnd",
              v["status"].get("normalEnd"), "delay", v["status"].get("delay"), "tlb", v["tlb_misses"], v["w4p"].get("shutdown"))
    if "late_joiner" in summary:
        print("late joiner:", summary["late_joiner"])


if __name__ == "__main__":
    main()

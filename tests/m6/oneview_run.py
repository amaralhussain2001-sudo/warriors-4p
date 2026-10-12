"""D23 experiment (TEST ONLY): N instances in W4P lockstep on loopback; chosen slots also enable a one-view group
("[warriors-4p test oneview pN]", N = that slot's player index), the others run the normal own-view mode.
The W4P full-RAM hash mismatches at once on purpose, so the simulation is compared separately:
  - SNAP records (group "[warriors-4p test simsnap]" on every instance, called with W4P CallAt at the same session
    polls everywhere): players' handles/positions/health, a hash per human (60), brains, GameMgr, rand(), RNG object,
    read through PINE during the run and compared record by record (same poll on every instance);
  - W4P DumpRam: every instance dumps EE RAM at (first mismatching hash point + 8 x HashInterval), i.e. at session poll
    9 x HashInterval (the first hash point already differs because the patch code differs), for tools/desync_diff.py.
Usage: python -I tests/m6/oneview_run.py <tag> [--seconds 900] [--players 2] [--oneview 1] [--hash-interval 1000]
       [--mission 13] [--bots-from 5000] [--snap-from 4500] [--snap-every 300] [--shot-every 60] [--shot-scale 1.0]
       [--groups-b "extra;groups for the one-view slots"] [--groups-all "extra;groups"] [--insts 2,3] [--port 41300]
       [--upscale 2] [--patch local/m6/oneview/test.pnach] [--script3 f] [--script4 f] [--w4p K=V ...]
       [--dense 4700:5400:20] [--read-every 40] [--calls-extra "poll:fn:args,..."]
--oneview: comma list of slots that run one view (empty = control run, every slot normal); --b-template "warriors-4p
test drawonly p{slot}" gives those slots another per-slot test group instead (variant R).
Writes local/m6/oneview/<tag>/ and evidence/M6/oneview_<tag>.json. Environment: SINGLE-PC, loopback, bots, MTVU off.
Instances: 2 and 3 by default (not 6-9, 10-11, 15).
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
sys.path.insert(0, os.path.join(PROJ, "tests", "m2"))
import m1_run  # noqa: E402  (read only: bot_file, record)
import nav_probe  # noqa: E402  (read only: build_inputs)
import sandbox  # noqa: E402
from pine import Pine  # noqa: E402

SNAPBUF, REC, NREC = 0x000E9800, 0x200, 20
ENTRY0, ENTRY_SIZE = 0x01FD996C, 0x84
BASE_GROUPS = ["warriors-4p M1", "warriors-4p own view", "warriors-4p hud", "warriors-4p 4p", "warriors-4p 4p hud B1",
               "warriors-4p 4p hud B2", "warriors-4p 4p spawn", "warriors-4p 4p spawn leave", "warriors-4p 4p inventory",
               "warriors-4p 4p fx", "warriors-4p 4p markers", "warriors-4p session", "warriors-4p missions",
               "warriors-4p session call", "warriors-4p test call", "warriors-4p test simsnap"]
PADS = [0, 4, 1, 2]
WORD_NAMES = (["poll", "gamemgr", "count_word", "checkpoint_word", "level_word", "levelend_word", "rand_state", "rng_obj"]
              + [f"handle{i}" for i in range(4)] + [f"p{i}_{c}" for i in range(4) for c in "xyz"]
              + [f"p{i}_health" for i in range(4)] + ["hash_humans", "hash_health", "hash_brains", "hash_gamemgr"]
              + [f"human{k}" for k in range(60)] + ["hash_humanpool_full", "hash_objtable", "frame_counter", "unused95"]
              + [f"camvec{i // 4}_{i % 4}" for i in range(16)] + [f"hash_cam{i}" for i in range(4)] + ["hash_714b00"]
              + [f"unused{i}" for i in range(117, 127)] + ["marker"])


def opt(name, default, cast=str):
    return cast(sys.argv[sys.argv.index(name) + 1]) if name in sys.argv else default


def set_ini(n, items):
    path = os.path.join(sandbox.data_root(n), "inis", "PCSX2.ini")
    cp = configparser.ConfigParser(interpolation=None, strict=False)
    cp.optionxform = str
    cp.read(path, encoding="utf-8")
    for sec, key, val in items:
        if not cp.has_section(sec):
            cp.add_section(sec)
        cp.set(sec, key, val)
    with open(path, "w", encoding="utf-8") as fh:
        cp.write(fh, space_around_delimiters=True)


def inputs_for(slot, out_dir, polls, bots_from):
    nav = {0: os.path.join(PROJ, "tests", "m2", "nav", "boot_to_m1_2p.txt"),
           1: os.path.join(PROJ, "tests", "m2", "nav", "p2_join.txt")}.get(slot)
    custom = opt(f"--script{slot + 1}", "")
    base = bytearray(nav_probe.build_inputs(custom or nav, polls) if (custom or nav) else m1_run.record() * polls)
    tmp = os.path.join(out_dir, f"rand{slot}.bin")
    m1_run.bot_file(tmp, 3000 + slot, polls)
    rnd = bytearray(open(tmp, "rb").read()[: polls * 20])
    if slot >= 2:  # players 3-4: Start every 300 polls so that they (re-)join (Start does not pause for them)
        for t in range(bots_from, polls, 300):
            for i in range(t, min(polls, t + 4)):
                rnd[i * 20: i * 20 + 2] = (int.from_bytes(rnd[i * 20: i * 20 + 2], "little") | 0x800).to_bytes(2, "little")
    base[bots_from * 20:] = rnd[bots_from * 20: polls * 20]
    path = os.path.join(out_dir, f"bot_slot{slot}.bin")
    open(path, "wb").write(bytes(base))
    return path


def read_ring(pn):
    blob = pn.dump(SNAPBUF, REC * NREC)
    out = []
    for i in range(NREC):
        w = struct.unpack_from("<128I", blob, i * REC)
        if w[127] == 0x534E4150:
            out.append(w)
    return out


def shot(pid, path, scale):
    subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", os.path.join(PROJ, "tools", "winshot.ps1"),
                    "-ProcessId", str(pid), "-Out", path, "-Scale", str(scale)], capture_output=True)


def compare(records):
    """records: slot -> {snap_index: words}. Returns rows for snaps present on every slot."""
    slots = sorted(records)
    common = sorted(set.intersection(*(set(records[s]) for s in slots)))
    rows = []
    for k in common:
        ws = [records[s][k] for s in slots]
        diff = [WORD_NAMES[i] for i in range(127) if len({w[i] for w in ws}) > 1]
        rows.append({"snap": k, "poll": ws[0][0], "polls_equal": len({w[0] for w in ws}) == 1, "differs": diff})
    return rows


def main():
    tag = sys.argv[1]
    seconds = opt("--seconds", 900, int)
    players = opt("--players", 2, int)
    insts = [int(x) for x in opt("--insts", "2,3" if players == 2 else "2,3,4,5").split(",")][:players]
    port0 = opt("--port", 41300, int)
    oneview = [int(x) for x in opt("--oneview", "1").split(",") if x != ""]
    hint = opt("--hash-interval", 1000, int)
    mission = opt("--mission", 13, int)
    bots_from = opt("--bots-from", 5000, int)
    snap_from, snap_every = opt("--snap-from", 4500, int), opt("--snap-every", 300, int)
    polls = opt("--polls", 60000, int)
    patch = os.path.join(PROJ, opt("--patch", os.path.join("local", "m6", "oneview", "test.pnach")))
    out_dir = os.path.join(PROJ, "local", "m6", "oneview", tag)
    if os.path.exists(out_dir):
        shutil.rmtree(out_dir)
    os.makedirs(out_dir)
    ptr = ENTRY0 + (mission - 1) * ENTRY_SIZE
    snaps = list(range(snap_from, polls - 100, snap_every))
    dense = opt("--dense", "")  # e.g. 4700:5400:20 (extra snapshots in a window; use a short --read-every)
    if dense:
        a, b, st = (int(x) for x in dense.split(":"))
        snaps = sorted(set(snaps) | set(range(a, b, st)))
    calls = [f"3999:0041ABC0:1", f"4009:00160D78:0x{ptr:08X}"] + [f"{p}:000E2600:{i % NREC}" for i, p in enumerate(snaps)]
    extra_calls = opt("--calls-extra", "")
    if extra_calls:
        calls += extra_calls.split(",")
    procs, groups_used = {}, {}
    for slot, n in enumerate(insts):
        d = sandbox.inst_dir(n)
        if os.path.exists(d):
            shutil.rmtree(d)
        sandbox.make(n, "default", pad2=True)
        set_ini(n, [("EmuCore/Speedhacks", "vuThread", "false"),
                    ("EmuCore/GS", "upscale_multiplier", opt("--upscale", "2"))])
        groups = BASE_GROUPS + [g for g in opt("--groups-all", "").split(";") if g]
        if slot in oneview:
            groups += [opt("--b-template", "warriors-4p test oneview p{slot}").format(slot=slot)] + [g for g in opt("--groups-b", "").split(";") if g]
        groups_used[slot] = groups
        sandbox.install_patch(n, patch, groups)
        bot = inputs_for(slot, out_dir, polls, bots_from)
        lines = ["[W4P]", "Enabled = true", f"Players = {players}", f"LocalSlot = {slot}"]
        lines += [f"PadForSlot{i} = {PADS[i]}" for i in range(players)]
        lines += [f"ListenPort = {port0 + slot}", "InputDelay = 2", f"HashInterval = {hint}",
                  f"LogFile = {os.path.join(out_dir, f'w4p_slot{slot}.log')}", f"DumpDir = {out_dir}", f"BotInput = {bot}",
                  "Crop = true", f"CallAt = {','.join(calls)}"]
        lines += [f"Peer{o} = 127.0.0.1:{port0 + o}" for o in range(players) if o != slot]
        extra = [a for i, a in enumerate(sys.argv) if i and sys.argv[i - 1] in ("--w4p", f"--w4p-slot{slot}")]
        lines += [f"{k.strip()} = {v.strip()}" for k, v in (e.split("=", 1) for e in extra)]
        ini = os.path.join(out_dir, f"w4p_slot{slot}.ini")
        open(ini, "w", encoding="utf-8").write("\n".join(lines) + "\n")
        env = dict(os.environ, W4P_CONFIG=ini)
        cmd = [sandbox.FORK_EXE] + sandbox.cmd(n, [])[1:]
        procs[slot] = subprocess.Popen(cmd, env=env, creationflags=getattr(subprocess, "DETACHED_PROCESS", 0))
        open(os.path.join(d, "pid.txt"), "w").write(str(procs[slot].pid))
    json.dump({"groups": groups_used, "insts": insts, "calls": calls[:4] + [f"... {len(calls)} entries"]},
              open(os.path.join(out_dir, "setup.json"), "w"), indent=1)
    t0 = time.time()
    records = {s: {} for s in procs}
    live = []
    next_read, next_shot = t0 + 40, t0 + opt("--first-shot", 120, int)
    shot_every, shot_scale = opt("--shot-every", 60, int), opt("--shot-scale", "1.0")
    while time.time() - t0 < seconds and all(p.poll() is None for p in procs.values()):
        time.sleep(2)
        if time.time() >= next_read:
            next_read += opt("--read-every", 40, int)
            row = {"t": round(time.time() - t0)}
            for s, n in enumerate(insts):
                try:
                    pn = Pine(sandbox.PINE_BASE + n, timeout=5)
                    row[f"poll{s}"] = pn.read32(0x000F0500)
                    row[f"views{s}"] = pn.read32(0x0050B198)
                    for w in read_ring(pn):
                        k = (w[0] - snap_from) // snap_every if w[0] >= snap_from else -1
                        records[s][w[0]] = w
                    pn.s.close()
                except Exception as e:  # noqa: BLE001
                    row[f"err{s}"] = repr(e)
            live.append(row)
            json.dump(live, open(os.path.join(out_dir, "live.json"), "w"), indent=1)
            json.dump({s: {str(k): list(v) for k, v in r.items()} for s, r in records.items()},
                      open(os.path.join(out_dir, "snaps.json"), "w"))
        if time.time() >= next_shot:
            next_shot += shot_every
            el = int(time.time() - t0)
            for s in procs:
                shot(procs[s].pid, os.path.join(out_dir, f"s{s}_t{el:04d}.png"), shot_scale)
    state = {}
    for s, n in enumerate(insts):
        try:
            pn = Pine(sandbox.PINE_BASE + n, timeout=5)
            gm = pn.read32(0x0051489C)
            state[s] = {"poll": pn.read32(0x000F0500), "players": pn.read32(gm + 0x224) & 0xFFFF,
                        "handles": [hex(pn.read32(gm + 0x228 + 4 * i)) for i in range(4)],
                        "views": pn.read32(0x0050B198), "cameras": pn.read32(0x0050B19C),
                        "render": [hex(pn.read32(0x000F0810 + 4 * i)) for i in range(4)],
                        "active": [hex(pn.read32(0x000F0800 + 4 * i)) for i in range(4)],
                        "shadow_views": pn.read32(0x000E5F00), "shadow": [hex(pn.read32(0x000E5F10 + 4 * i)) for i in range(4)]}
            for w in read_ring(pn):
                records[s][w[0]] = w
        except Exception as e:  # noqa: BLE001
            state[s] = repr(e)
        shot(procs[s].pid, os.path.join(out_dir, f"end_slot{s}.png"), shot_scale)
    for n in insts:
        subprocess.run([sys.executable, "-I", os.path.join(PROJ, "tools", "sandbox.py"), "kill", str(n)], capture_output=True)
    for p in procs.values():
        try:
            p.wait(15)
        except subprocess.TimeoutExpired:
            pass
    for n in insts:
        src = os.path.join(sandbox.data_root(n), "logs", "emulog.txt")
        try:
            shutil.copyfile(src, os.path.join(out_dir, f"emulog_inst{n}.txt"))
        except OSError:
            pass
    json.dump({s: {str(k): list(v) for k, v in r.items()} for s, r in records.items()},
              open(os.path.join(out_dir, "snaps.json"), "w"))
    stats, tlb = {}, {}
    for s, n in enumerate(insts):
        txt = open(os.path.join(out_dir, f"w4p_slot{s}.log"), encoding="utf-8", errors="replace").read()
        st = re.findall(r"stats: (.*)$", txt, re.M)
        stats[s] = {"last": st[-1] if st else None, "desync_lines": len(re.findall(r"DESYNC", txt)),
                    "first_desync": (re.findall(r"DESYNC.*$", txt, re.M) or [None])[0],
                    "dumps": re.findall(r"dumped RAM to (.*)$", txt, re.M),
                    "calls": len(re.findall(r"test call at poll", txt))}
        try:
            tlb[n] = open(os.path.join(out_dir, f"emulog_inst{n}.txt"), encoding="utf-8", errors="replace").read().count("TLB Miss")
        except OSError:
            tlb[n] = None
    by_poll = {s: {w[0]: w for w in r.values()} for s, r in records.items()}
    rows = compare(by_poll)
    first_div = next((r for r in rows if r["differs"]), None)
    summary = {"tag": tag, "environment": f"SINGLE-PC, {players} instances, loopback, bots, MTVU off",
               "seconds": round(time.time() - t0), "oneview_slots": oneview, "mission": mission, "hash_interval": hint,
               "state": state, "stats": stats, "tlb_misses": tlb, "snapshots_compared": len(rows),
               "snapshots_identical": sum(1 for r in rows if not r["differs"]), "first_divergence": first_div,
               "rows": rows}
    os.makedirs(os.path.join(PROJ, "evidence", "M6"), exist_ok=True)
    json.dump(summary, open(os.path.join(PROJ, "evidence", "M6", f"oneview_{tag}.json"), "w"), indent=1)
    print(json.dumps({k: summary[k] for k in ("seconds", "state", "stats", "tlb_misses", "snapshots_compared",
                                              "snapshots_identical", "first_divergence")}, indent=1))


if __name__ == "__main__":
    main()

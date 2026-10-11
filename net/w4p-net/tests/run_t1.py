# SPDX-License-Identifier: GPL-3.0-or-later
"""Single-PC tests T1b-T1e of docs/research/m5_connection_design.md section 6, plus the lockstep simulator runs.

All helpers run on this PC with --bind 127.0.0.1 --no-stun (host candidates on loopback only; no STUN/TURN or other
network host is contacted). Results: <out>/<test>/summary.json plus each helper's stdout, connection log and stats.

  python -I net/w4p-net/tests/run_t1.py t1b --players 2      2 helpers, probe 200 B at 60/s for 60 s
  python -I net/w4p-net/tests/run_t1.py t1b --players 4      4 helpers, full mesh (6 pairs)
  python -I net/w4p-net/tests/run_t1.py t1c --players 4      join code only (direct dial, no reply code pasted)
  python -I net/w4p-net/tests/run_t1.py t1d --delay 45       reply code pasted 45 s late (direct dial disabled)
  python -I net/w4p-net/tests/run_t1.py t1e                  joiner pair 1-2 blocked: forwarding through the host
  python -I net/w4p-net/tests/run_t1.py sim                  lockstep simulator through 4 helpers + plain-UDP baseline
  python -I net/w4p-net/tests/run_t1.py sec                  strangers: foreign-session joiner, foreign reply code,
                                                             loopback stranger, mistyped code
"""
import argparse
import json
import os
import sys
import time

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # -I does not add the script directory
import lockstep_sim  # noqa: E402
import socket  # noqa: E402

from w4pnet_harness import Helper, helper_args, ports, retarget_join_code  # noqa: E402

OUT_DEFAULT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "build", "results"))


def start_mesh(n, outdir, paste_reply=True, host_extra=(), joiner_extra=None, stagger=0.0):
    host = Helper("h0", ["host"] + helper_args(0, ["--players", str(n)] + list(host_extra)), outdir)
    jc = host.code("join")
    if not jc:
        raise RuntimeError("host printed no join code")
    joiners = []
    for k in range(1, n):
        extra = ["--want-slot", str(k)] + list(joiner_extra(k) if joiner_extra else [])
        j = Helper("j%d" % k, ["join", jc] + helper_args(k, extra), outdir)
        joiners.append(j)
        if paste_reply:
            rc = j.code("reply")
            if rc:
                host.send(rc)  # what the host does when the friend sends the reply code through the chat
        if stagger:
            time.sleep(stagger)
    return host, joiners


def wait_ready(helpers, timeout):
    res = {}
    for h in helpers:
        r = h.wait("ready", timeout)
        res[h.name] = r[0] if r else None
    return res


def link_events(h):
    out = []
    for t, ev in h.find_all("link "):
        f = ev.split()
        out.append({"t": round(t, 3), "peer": int(f[1]), "what": f[2], "args": f[3:]})
    return out


def quit_all(helpers):
    return {h.name: h.quit() for h in helpers}


def probe_tables(stats):
    """Directed probe streams: sender's tx and echo RTT, receiver's unique count."""
    by_slot = {s["slot"]: (name, s) for name, s in stats.items() if s}
    rows = []
    for name, s in stats.items():
        if not s:
            continue
        me = s["slot"]
        for sl in s["slots"]:
            d = sl["slot"]
            if d == me or sl["probe_tx"] == 0:
                continue
            recv = by_slot.get(d)
            rx = recv[1]["slots"][me]["probe_rx"] if recv else None
            dup = recv[1]["slots"][me]["probe_rx_dup"] if recv else None
            rows.append({
                "from": me, "to": d, "sent": sl["probe_tx"], "via_host": sl["probe_tx_via_host"],
                "no_route": sl["probe_no_route"], "received_unique": rx, "dup": dup,
                "loss_pct": round(100.0 * (1 - rx / sl["probe_tx"]), 3) if rx is not None else None,
                "echoes": sl["probe_echo_rx"], "rtt_p50_ms": sl["probe_rtt_p50"], "rtt_p95_ms": sl["probe_rtt_p95"],
                "rtt_p99_ms": sl["probe_rtt_p99"], "rtt_max_ms": sl["probe_rtt_max"],
            })
    return rows


def link_table(stats):
    rows = []
    for name, s in stats.items():
        if not s:
            continue
        for L in s["links"]:
            rows.append({"helper": name, "slot": s["slot"], "peer": L["peer"], "kind": L["kind"], "path": L["path"],
                         "blocked": L["blocked"], "attempts": L["attempts"], "connect_ms": L["connect_ms"],
                         "state": L["state"], "sel_local": L["sel_local"], "sel_remote": L["sel_remote"],
                         "ping_n": L["ping_n"], "ping_p50": L["ping_p50"], "ping_p95": L["ping_p95"],
                         "ping_max": L["ping_max"], "fwd_out": L["fwd_out"], "bad_tag": L["bad_tag"],
                         "bad_mac": L["bad_mac"], "bad_src": L["bad_src"], "send_err": L["send_err"]})
    return rows


def run_probe(helpers, rate, size, seconds):
    t = [h.now() for h in helpers]
    for h in helpers:
        h.send("probe %g %d %g" % (rate, size, seconds))
    done = {}
    for h, t0 in zip(helpers, t):
        r = h.wait("probe_done", seconds + 30, after=t0)
        done[h.name] = r is not None
    return done


def save(outdir, summary):
    with open(os.path.join(outdir, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=1)
    print(json.dumps(summary, indent=1))


def t1b(a, outdir, paste_reply=True, test="T1b"):
    t_begin = time.time()
    host, joiners = start_mesh(a.players, outdir, paste_reply=paste_reply)
    helpers = [host] + joiners
    ready = wait_ready(helpers, a.timeout)
    summary = {"test": test, "players": a.players, "paste_reply": paste_reply, "env": "SINGLE-PC loopback, no STUN",
               "started": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(t_begin)), "ready_s": ready,
               "host_paths": [ev for _, ev in host.find_all("path ")],
               "joined": [ev for _, ev in host.find_all("joined ")],
               "link_events": {h.name: link_events(h) for h in helpers}}
    if all(v is not None for v in ready.values()) and a.probe_seconds > 0:
        summary["probe"] = {"rate": a.rate, "size": a.size, "seconds": a.probe_seconds,
                            "done": run_probe(helpers, a.rate, a.size, a.probe_seconds)}
    stats = quit_all(helpers)
    summary["links"] = link_table(stats)
    summary["probe_streams"] = probe_tables(stats)
    save(outdir, summary)


def t1d(a, outdir):
    host = Helper("h0", ["host"] + helper_args(0, ["--players", "2", "--test-no-direct-dial"]), outdir)
    jc = host.code("join")
    j = Helper("j1", ["join", jc] + helper_args(1, ["--want-slot", "1"]), outdir)
    rc = j.code("reply")
    t_reply = host.now()
    time.sleep(a.delay)
    t_paste = host.now()
    host.send(rc)  # the late paste
    c_host = host.wait("link 1 connected", 60, after=t_paste)
    c_join = j.wait("link 0 connected", 60)
    ready = wait_ready([host, j], 30)
    stats = quit_all([host, j])
    summary = {
        "test": "T1d", "delay_s": a.delay, "env": "SINGLE-PC loopback, no STUN, host --test-no-direct-dial",
        "reply_printed_s": round(t_reply, 3), "pasted_s": round(t_paste, 3),
        "host_connected_s": round(c_host[0], 3) if c_host else None,
        "connected_after_paste_ms": round(1000 * (c_host[0] - t_paste), 1) if c_host else None,
        "joiner_connected_event": c_join[1] if c_join else None,
        "joiner_failed_events": [ev for _, ev in j.find_all("link 0 failed")],
        "joiner_listen_events": [ev for _, ev in j.find_all("listen")],
        "joiner_reply_codes_printed": len(j.find_all("code reply")),
        "ready_s": ready, "links": link_table(stats),
    }
    save(outdir, summary)


def t1e(a, outdir):
    # joiners 1 and 2 must not connect directly: the switch is given to both sides
    block = {1: ["--test-block-peer", "2"], 2: ["--test-block-peer", "1"], 3: []}
    host, joiners = start_mesh(4, outdir, paste_reply=True, joiner_extra=lambda k: block[k])
    helpers = [host] + joiners
    ready = wait_ready(helpers, a.timeout)
    summary = {"test": "T1e", "env": "SINGLE-PC loopback, no STUN, joiner pair 1-2 blocked by --test-block-peer",
               "ready_s": ready}
    if all(v is not None for v in ready.values()):
        eps = lockstep_sim.helper_endpoints(4, [ports(k)["emu"] for k in range(4)], [ports(k)["slots"] for k in range(4)])
        summary["sim"] = lockstep_sim.run(eps, a.sim_seconds, rate=60, size=658, delay=2)
        summary["probe"] = {"rate": a.rate, "size": a.size, "seconds": a.probe_seconds,
                            "done": run_probe(helpers, a.rate, a.size, a.probe_seconds)}
    summary["link_events"] = {h.name: link_events(h) for h in helpers}
    stats = quit_all(helpers)
    summary["links"] = link_table(stats)
    summary["probe_streams"] = probe_tables(stats)
    summary["slots"] = {n: s["slots"] for n, s in stats.items() if s}
    save(outdir, summary)


def sim(a, outdir):
    host, joiners = start_mesh(4, outdir, paste_reply=True)
    helpers = [host] + joiners
    ready = wait_ready(helpers, a.timeout)
    summary = {"test": "SIM", "env": "SINGLE-PC loopback, no STUN; 4 simulated W4P endpoints in one Python process",
               "ready_s": ready}
    if all(v is not None for v in ready.values()):
        eps = lockstep_sim.helper_endpoints(4, [ports(k)["emu"] for k in range(4)], [ports(k)["slots"] for k in range(4)])
        summary["through_helpers"] = lockstep_sim.run(eps, a.sim_seconds, rate=60, size=658, delay=2)
    stats = quit_all(helpers)
    summary["links"] = link_table(stats)
    summary["slots"] = {n: s["slots"] for n, s in stats.items() if s}
    summary["bridge"] = {n: {k: s[k] for k in ("emu_rx", "emu_tx", "emu_drop", "loopback_strangers")}
                         for n, s in stats.items() if s}
    summary["plain_udp"] = lockstep_sim.run(lockstep_sim.plain_endpoints(4, 45900), a.sim_seconds, rate=60, size=658,
                                            delay=2)
    save(outdir, summary)


def sec(a, outdir):
    """Section 5 checks: only holders of this session's join code get in; only the local emulator uses the bridge."""
    host = Helper("h0", ["host"] + helper_args(0, ["--players", "4"]), outdir)
    jc = host.code("join")
    other = Helper("x0", ["host"] + helper_args(5, ["--players", "2"]), outdir)  # another session on this PC
    xjc = other.code("join")
    good = Helper("j1", ["join", jc] + helper_args(1, ["--want-slot", "1"]), outdir)
    good_ok = good.wait("ready", 30) is not None
    # 1. a joiner holding another session's secret, pointed at our host's port (path b dial with wrong credentials)
    foreign_code = retarget_join_code(xjc, ports(0)["ice"])
    stranger = Helper("j9", ["join", foreign_code] + helper_args(9, ["--connect-minutes", "1"]), outdir)
    foreign_reply = stranger.code("reply")
    time.sleep(3)
    # 2. the stranger's reply code pasted into our host (belongs to another session)
    t_paste = host.now()
    host.send(foreign_reply)
    paste_err = host.wait("error paste", 5, after=t_paste)
    # 3. a mistyped reply code
    bad = foreign_reply[:-3] + ("0" if foreign_reply[-3] != "0" else "1") + foreign_reply[-2:]
    t_bad = host.now()
    host.send(bad)
    bad_err = host.wait("error paste", 5, after=t_bad)
    # 4. a loopback stranger sends to the host helper's slot-1 port (only the emulator's port may use the bridge)
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(("127.0.0.1", 0))
    for _ in range(10):
        s.sendto(b"x" * 100, ("127.0.0.1", ports(0)["slots"] + 1))
    s.close()
    time.sleep(1)
    # 5. a mistyped join code given to a joiner: it must refuse to start
    jbad = Helper("jbad", ["join", jc[:20] + jc[21:]] + helper_args(8), outdir)
    jbad.proc.wait(10)
    stranger_connected = stranger.wait("link 0 connected", 0) is not None
    st = quit_all([host, good, stranger, other, jbad])
    with open(os.path.join(outdir, "h0_connection-log.txt"), encoding="utf-8") as f:
        hlog = f.read()
    summary = {
        "test": "SEC", "env": "SINGLE-PC loopback, no STUN",
        "good_joiner_ready": good_ok,
        "foreign_joiner_connected": stranger_connected,
        "host_log_foreign_rejections": hlog.count("joiner of another session rejected"),
        "host_ice_strangers": st["h0"]["ice_strangers"] if st.get("h0") else None,
        "host_links_created": len(st["h0"]["links"]) if st.get("h0") else None,
        "foreign_reply_paste": paste_err[1] if paste_err else None,
        "mistyped_reply_paste": bad_err[1] if bad_err else None,
        "loopback_strangers_counted": st["h0"]["loopback_strangers"] if st.get("h0") else None,
        "host_slot1_data_tx": st["h0"]["slots"][1]["data_tx"] if st.get("h0") else None,
        "mistyped_join_exit_code": jbad.proc.returncode,
        "mistyped_join_events": [ev for _, ev in jbad.find_all("error")],
    }
    save(outdir, summary)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("test", choices=["t1b", "t1c", "t1d", "t1e", "sim", "sec"])
    ap.add_argument("--players", type=int, default=4)
    ap.add_argument("--delay", type=float, default=5)
    ap.add_argument("--rate", type=float, default=60)
    ap.add_argument("--size", type=int, default=200)
    ap.add_argument("--probe-seconds", type=float, default=60)
    ap.add_argument("--sim-seconds", type=float, default=60)
    ap.add_argument("--timeout", type=float, default=90)
    ap.add_argument("--out", default=OUT_DEFAULT)
    ap.add_argument("--tag", default="")
    a = ap.parse_args()
    name = a.tag or {"t1b": "t1b_%dp" % a.players, "t1c": "t1c_%dp" % a.players, "t1d": "t1d_%gs" % a.delay,
                     "t1e": "t1e", "sim": "sim", "sec": "sec"}[a.test]
    outdir = os.path.join(a.out, name)
    os.makedirs(outdir, exist_ok=True)
    if a.test == "t1b":
        t1b(a, outdir)
    elif a.test == "t1c":
        t1b(a, outdir, paste_reply=False, test="T1c")
    elif a.test == "t1d":
        t1d(a, outdir)
    elif a.test == "t1e":
        t1e(a, outdir)
    elif a.test == "sec":
        sec(a, outdir)
    else:
        sim(a, outdir)


if __name__ == "__main__":
    main()

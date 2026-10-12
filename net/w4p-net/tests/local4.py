# SPDX-License-Identifier: GPL-3.0-or-later
"""Starts 2-4 w4p-net helpers on this PC (loopback, no STUN) for test T1f and prints each emulator's w4p.ini lines.

Launch order for T1f: (1) run this script and wait for "HELPERS READY"; (2) start the emulators with the printed
[W4P] lines (any order); (3) when the emulator run is over, type "quit" (or Enter on an empty line, or Ctrl+C), create the --stop-file, or let
--seconds expire (end of stdin alone does not stop it). The script then stops the helpers and prints/saves their counters (datagrams from/to each emulator,
datagrams without route, datagrams forwarded through the host).

  python -I net/w4p-net/tests/local4.py                      4 helpers, ports below, run until "quit"
  python -I net/w4p-net/tests/local4.py --seconds 1500        stop by itself after 25 minutes
  python -I net/w4p-net/tests/local4.py --block 1,2           joiner pair 1-2 forced through the host (T1e setup)
  python -I net/w4p-net/tests/local4.py --direct-dial         joiners connect with the join code only (no reply codes)
  python -I net/w4p-net/tests/local4.py --mute 3:400:20        T1g: 400 s after HELPERS READY, helper 3 drops the game
                                                            data to/from every other slot for 20 s (test switch "mute";
                                                            "K:AT:SECONDS:SLOT" = only the link to SLOT; comma list)

Default ports (instance k = slot k): emulator ListenPort 46000+k, helper slot ports 46100+10k .. 46103+10k,
ICE port 46400+k. They avoid the 41xxx ports used by the m2 runners and the 45xxx ports of run_t1.py.
"""
import argparse
import json
import os
import sys
import threading
import time

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from w4pnet_harness import SAFE_ARGS, Helper  # noqa: E402

OUT_DEFAULT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "build", "results",
                                            "local4"))


def ini_lines(players, slot, emu_port, slot_base):
    lines = ["[W4P]", "Enabled = true", "Players = %d" % players, "LocalSlot = %d" % slot,
             "BindAddress = 127.0.0.1", "ListenPort = %d" % emu_port]
    for p in range(4):
        lines.append("Peer%d = 127.0.0.1:%d" % (p, slot_base + p) if p < players and p != slot else
                     "Peer%d =" % p)
    return lines


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--players", type=int, default=4)
    ap.add_argument("--emu-ports", default="46000,46001,46002,46003")
    ap.add_argument("--slot-bases", default="46100,46110,46120,46130")
    ap.add_argument("--ice-base", type=int, default=46400)
    ap.add_argument("--seconds", type=float, default=0, help="stop after this many seconds (0 = wait for quit)")
    ap.add_argument("--block", default="", help="joiner pair 'a,b' without a direct link (forwarded by the host)")
    ap.add_argument("--direct-dial", action="store_true", help="do not paste reply codes (path b only)")
    ap.add_argument("--stop-file", default="", help="stop the helpers when this file appears (for scripts)")
    ap.add_argument("--mute", default="", help="T1g outages: K:AT:SECONDS[:SLOT],... (helper K, AT s after READY)")
    ap.add_argument("--out", default=OUT_DEFAULT)
    a = ap.parse_args()
    n = a.players
    emu = [int(x) for x in a.emu_ports.split(",")][:n]
    sb = [int(x) for x in a.slot_bases.split(",")][:n]
    block = [int(x) for x in a.block.split(",")] if a.block else []
    os.makedirs(a.out, exist_ok=True)

    def args(k, extra):
        return SAFE_ARGS + ["--ice-port", str(a.ice_base + k), "--emu-port", str(emu[k]), "--slot-ports", str(sb[k]),
                            "--connect-minutes", "60"] + extra

    host = Helper("h0", ["host"] + args(0, ["--players", str(n)]), a.out)
    jc = host.code("join")
    if not jc:
        sys.exit("host printed no join code (see %s)" % host.stdout_path)
    helpers = [host]
    for k in range(1, n):
        extra = ["--want-slot", str(k)]
        if len(block) == 2 and k in block:
            extra += ["--test-block-peer", str(block[1] if k == block[0] else block[0])]
        j = Helper("j%d" % k, ["join", jc] + args(k, extra), a.out)
        helpers.append(j)
        if not a.direct_dial:
            rc = j.code("reply")
            if rc:
                host.send(rc)
    ok = True
    for k, h in enumerate(helpers):
        if h.wait("ready", 90) is None:
            print("helper %s not ready (see %s)" % (h.name, h.stdout_path))
            ok = False
        if k:
            s = h.wait("slot ", 1)
            if not s or int(s[1].split()[1]) != k:
                print("helper %s got slot %s, expected %d" % (h.name, s[1] if s else None, k))
                ok = False
    if not ok:
        for h in helpers:
            h.quit()
        sys.exit(1)

    text = []
    for k in range(n):
        lines = ini_lines(n, k, emu[k], sb[k])
        text.append("; instance %d (slot %d, helper %s)" % (k, k, helpers[k].name))
        text += lines + [""]
        with open(os.path.join(a.out, "inst%d_w4p_lines.txt" % k), "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    print("\n".join(text))
    print("HELPERS READY: start the emulators now. Type quit (or press Enter) to stop the helpers.", flush=True)

    stop = threading.Event()

    def stdin_wait():
        # "quit" or an empty line stops; end of input (no console, stdin redirected) does not
        try:
            while True:
                line = sys.stdin.readline()
                if line == "":
                    return
                if line.strip().lower() in ("", "q", "quit", "exit"):
                    stop.set()
                    return
        except Exception:
            return

    threading.Thread(target=stdin_wait, daemon=True).start()
    t0 = time.time()
    mutes = [[int(f[0]), float(f[1]), float(f[2]), int(f[3]) if len(f) > 3 else None, False]
             for f in (m.split(":") for m in a.mute.split(",") if m)]
    mute_log = []
    try:
        while not stop.is_set():
            for m in mutes:
                if not m[4] and time.time() - t0 >= m[1]:
                    m[4] = True
                    helpers[m[0]].send("mute %g%s" % (m[2], "" if m[3] is None else " %d" % m[3]))
                    mute_log.append({"helper": helpers[m[0]].name, "at_s": round(time.time() - t0, 1), "seconds": m[2],
                                     "slot": m[3], "wall": time.strftime("%H:%M:%S")})
                    print("MUTE sent: %s" % mute_log[-1], flush=True)
            if a.seconds and time.time() - t0 > a.seconds:
                break
            if a.stop_file and os.path.exists(a.stop_file):
                break
            dead = [h.name for h in helpers if h.proc.poll() is not None]
            if dead:
                print("helper(s) exited: %s" % dead)
                break
            stop.wait(1.0)
    except KeyboardInterrupt:
        pass
    stats = {h.name: h.quit() for h in helpers}
    summary = {"players": n, "seconds": round(time.time() - t0, 1), "emu_ports": emu, "slot_bases": sb,
               "block": block, "direct_dial": a.direct_dial, "mutes": mute_log, "helpers": {}}
    for name, s in stats.items():
        if not s:
            continue
        summary["helpers"][name] = {
            "slot": s["slot"], "emu_rx": s["emu_rx"], "emu_tx": s["emu_tx"], "emu_drop": s["emu_drop"],
            "loopback_strangers": s["loopback_strangers"],
            "mute": {k: s.get(k) for k in ("mute_count", "mute_drop_tx", "mute_drop_rx")},
            "per_slot": [{k: x[k] for k in ("slot", "data_tx", "data_tx_via_host", "data_no_route", "data_rx",
                                             "data_rx_via_host")} for x in s["slots"]],
            "links": [{k: L[k] for k in ("peer", "kind", "attempts", "connect_ms", "state", "ping_p50", "ping_p95",
                                         "ping_max", "fwd_out", "bad_tag", "bad_mac", "bad_src", "send_err")}
                      for L in s["links"]],
        }
    with open(os.path.join(a.out, "local4_summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=1)
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()

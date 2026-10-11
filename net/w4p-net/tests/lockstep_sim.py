# SPDX-License-Identifier: GPL-3.0-or-later
"""Loopback lockstep simulator: 4 UDP endpoints that behave like 4 W4P instances on the network.

Each endpoint binds 127.0.0.1:<listen port> (W4P BindAddress/ListenPort) and sends to Peer<p> for every other slot p
(W4P Peer0..3), so it can run either directly endpoint-to-endpoint ("plain UDP", like today's W4P on one PC) or through
the w4p-net helpers (Peer<p> = 127.0.0.1:<helper slot port base + p>). The coordinator later replaces the endpoints by
real emulators (test T1f).

Model (lockstep mode, default): frame period T = 1/rate. At frame f an endpoint sends one packet to every peer with its
inputs for frames f+D-31 .. f+D (like W4P's 32-input resend burst, packet size --size, default 658 bytes = W4P's
steady-state input packet from W4P.cpp, see docs/research/m5_connection_design.md 2.2). It may run frame f only when it
holds every peer's input for f; while waiting it resends its newest packet every 15 ms (W4P resends every 15 ms while
stalled). Waiting beyond the frame's due time is counted as stall time. A datagram is accepted only if it comes from the
configured Peer address of the slot named in its header (the W4P source check, W4P.cpp HandlePacket).

Measured per directed pair: packets sent/received, loss (by sequence number), one-way latency (all endpoints share one
clock: time.perf_counter_ns). Per endpoint: frames run, stall time, longest stall.

Python itself adds scheduling delay (one thread serves all 4 endpoints); compare runs against a plain-UDP run of the
same script instead of reading the absolute numbers as network latency.
"""
import argparse
import ctypes
import json
import select
import socket
import struct
import sys
import time

MAGIC = b"W4PS"
HDR = struct.Struct("<4sBxxxIIQ")  # magic, slot, newest frame, seq, t_send_ns
BURST = 32


def pct(values, q):
    if not values:
        return None
    v = sorted(values)
    k = max(0, min(len(v) - 1, int(-(-q * len(v) // 1)) - 1))
    return v[k]


class Endpoint:
    def __init__(self, slot, listen_port, peers):
        self.slot = slot
        self.peers = peers  # slot -> (host, port)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1 << 20)
        if hasattr(socket, "SIO_UDP_CONNRESET"):
            self.sock.ioctl(socket.SIO_UDP_CONNRESET, False)
        self.sock.bind(("127.0.0.1", listen_port))
        self.sock.setblocking(False)
        self.frame = 0
        self.have = {p: -1 for p in peers}  # highest contiguous frame received from p
        self.seq = 0
        self.last_send_ns = 0
        self.stall_ns = 0
        self.max_stall_ns = 0
        self.stall_start = None
        self.rejected = 0
        self.gaps = 0
        self.sent = {p: 0 for p in peers}
        self.recv = {p: 0 for p in peers}
        self.seen = {p: set() for p in peers}
        self.lat = {p: [] for p in peers}  # one-way latency ms of packets from p
        self.frames_run = 0


def run(endpoints, seconds, rate=60.0, size=658, delay=2, mode="lockstep", warmup=1.0):
    """endpoints: list of (slot, listen_port, {peer_slot: (host, port)}). Returns a result dict."""
    if sys.platform == "win32":
        ctypes.WinDLL("winmm").timeBeginPeriod(1)  # 1 ms timer resolution for this process only
    eps = [Endpoint(s, port, peers) for s, port, peers in endpoints]
    by_sock = {e.sock: e for e in eps}
    addr_to_slot = {e.slot: {v: k for k, v in e.peers.items()} for e in eps}
    period_ns = int(1e9 / rate)
    pad = b"\0" * max(0, size - HDR.size)
    t0 = time.perf_counter_ns()
    start_ns = t0 + int(warmup * 1e9)
    end_ns = start_ns + int(seconds * 1e9)

    def send(e, now):
        newest = e.frame + delay
        for p, addr in e.peers.items():
            ts = time.perf_counter_ns()
            pkt = HDR.pack(MAGIC, e.slot, newest, e.seq, ts) + pad
            try:
                e.sock.sendto(pkt, addr)
                if start_ns <= ts < end_ns:
                    e.sent[p] += 1
            except OSError:
                pass
            e.seq += 1
        e.last_send_ns = now

    # frame f is due at start_ns + f*period (shifted by accumulated stalls, like an emulator that fell behind)
    due = {e.slot: start_ns for e in eps}
    for e in eps:
        send(e, time.perf_counter_ns())
    drain_ns = end_ns + 300_000_000  # stop sending at end_ns, keep receiving packets still in flight
    while True:
        now = time.perf_counter_ns()
        if now >= drain_ns:
            break
        # receive everything pending
        r, _, _ = select.select([e.sock for e in eps], [], [], 0.0005)
        for s in r:
            e = by_sock[s]
            while True:
                try:
                    data, frm = s.recvfrom(4096)
                except BlockingIOError:
                    break
                except ConnectionResetError:
                    continue
                except OSError:
                    break
                tr = time.perf_counter_ns()
                if len(data) < HDR.size or data[:4] != MAGIC:
                    e.rejected += 1
                    continue
                _, src, newest, seq, ts = HDR.unpack_from(data)
                if src not in e.peers or addr_to_slot[e.slot].get(frm) != src:
                    e.rejected += 1  # W4P source check: must come from Peer<src>
                    continue
                if start_ns <= ts < end_ns:
                    e.recv[src] += 1
                    if seq in e.seen[src]:
                        pass
                    else:
                        e.seen[src].add(seq)
                        e.lat[src].append((tr - ts) / 1e6)
                oldest = newest - BURST + 1
                if oldest > e.have[src] + 1:
                    e.gaps += 1  # more than 32 packets lost in a row: lockstep would wait forever here
                    e.have[src] = newest
                elif newest > e.have[src]:
                    e.have[src] = newest
        now = time.perf_counter_ns()
        if now >= end_ns:
            continue  # drain phase
        for e in eps:
            if now < due[e.slot]:
                continue
            ready = mode == "rate" or all(e.have[p] >= e.frame for p in e.peers)
            if ready:
                if e.stall_start is not None:
                    st = now - e.stall_start
                    if e.stall_start >= start_ns:
                        e.stall_ns += st
                        e.max_stall_ns = max(e.max_stall_ns, st)
                    e.stall_start = None
                if due[e.slot] >= start_ns:
                    e.frames_run += 1
                e.frame += 1
                # on time: next frame one period later; after a stall the emulator continues at normal speed
                # from now (it does not run faster to catch up)
                due[e.slot] = due[e.slot] + period_ns if now < due[e.slot] + period_ns else now + period_ns
                send(e, now)
            else:
                if e.stall_start is None:
                    e.stall_start = now
                if now - e.last_send_ns >= 15_000_000:
                    send(e, now)  # resend while stalled
    for e in eps:
        if e.stall_start is not None and e.stall_start >= start_ns:
            st = end_ns - e.stall_start
            e.stall_ns += st
            e.max_stall_ns = max(e.max_stall_ns, st)
    if sys.platform == "win32":
        ctypes.WinDLL("winmm").timeEndPeriod(1)

    pairs = []
    by_slot = {e.slot: e for e in eps}
    all_lat = []
    for e in eps:
        for p in e.peers:
            src = by_slot.get(p)
            if src is None:
                continue
            sent = src.sent[e.slot]
            uniq = len(e.seen[p])
            lat = e.lat[p]
            all_lat += lat
            pairs.append({
                "from": p, "to": e.slot, "sent": sent, "received_unique": uniq,
                "loss_pct": round(100.0 * (1 - uniq / sent), 3) if sent else None,
                "lat_p50_ms": round(pct(lat, 0.5), 3) if lat else None,
                "lat_p95_ms": round(pct(lat, 0.95), 3) if lat else None,
                "lat_p99_ms": round(pct(lat, 0.99), 3) if lat else None,
                "lat_max_ms": round(max(lat), 3) if lat else None,
                "over_33ms": sum(1 for x in lat if x > 1000.0 * delay / rate),
            })
    res = {
        "mode": mode, "seconds": seconds, "rate": rate, "size": size, "delay": delay,
        "endpoints": [{
            "slot": e.slot, "frames_run": e.frames_run, "stall_s": round(e.stall_ns / 1e9, 3),
            "stall_pct": round(100.0 * e.stall_ns / (seconds * 1e9), 3), "max_stall_ms": round(e.max_stall_ns / 1e6, 3),
            "rejected": e.rejected, "gaps_over_32": e.gaps,
        } for e in eps],
        "pairs": pairs,
        "all_lat_p50_ms": round(pct(all_lat, 0.5), 3) if all_lat else None,
        "all_lat_p95_ms": round(pct(all_lat, 0.95), 3) if all_lat else None,
        "all_lat_p99_ms": round(pct(all_lat, 0.99), 3) if all_lat else None,
        "all_lat_max_ms": round(max(all_lat), 3) if all_lat else None,
    }
    for e in eps:
        e.sock.close()
    return res


def plain_endpoints(n, base):
    """Direct endpoint-to-endpoint (no helper): slot k listens on base+k."""
    return [(k, base + k, {p: ("127.0.0.1", base + p) for p in range(n) if p != k}) for k in range(n)]


def helper_endpoints(n, emu_ports, slot_bases, slots=None):
    """Through helpers: endpoint k listens on emu_ports[k]; Peer<p> = 127.0.0.1:slot_bases[k]+p."""
    slots = slots or list(range(n))
    return [(slots[k], emu_ports[k], {p: ("127.0.0.1", slot_bases[k] + p) for p in range(n) if p != slots[k]})
            for k in range(n)]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--players", type=int, default=4)
    ap.add_argument("--seconds", type=float, default=60)
    ap.add_argument("--rate", type=float, default=60)
    ap.add_argument("--size", type=int, default=658)
    ap.add_argument("--delay", type=int, default=2)
    ap.add_argument("--mode", choices=["lockstep", "rate"], default="lockstep")
    ap.add_argument("--plain-base", type=int, help="plain UDP: endpoint k listens on BASE+k")
    ap.add_argument("--emu-ports", help="through helpers: comma list of endpoint listen ports (W4P ListenPort)")
    ap.add_argument("--slot-bases", help="through helpers: comma list of helper slot port bases (Peer<p> = base+p)")
    ap.add_argument("--out", help="write the result JSON here")
    a = ap.parse_args()
    if a.plain_base:
        eps = plain_endpoints(a.players, a.plain_base)
    else:
        eps = helper_endpoints(a.players, [int(x) for x in a.emu_ports.split(",")],
                               [int(x) for x in a.slot_bases.split(",")])
    res = run(eps, a.seconds, a.rate, a.size, a.delay, a.mode)
    txt = json.dumps(res, indent=1)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(txt + "\n")
    print(txt)


if __name__ == "__main__":
    main()

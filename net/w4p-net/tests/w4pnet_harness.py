# SPDX-License-Identifier: GPL-3.0-or-later
"""Starts w4p-net helper processes for single-PC tests and reads their "@" events from stdout.

Every helper is started with --bind 127.0.0.1 --no-stun: host candidates on loopback only, no STUN/TURN server and no
other network host is contacted (binding to loopback also avoids Windows Firewall prompts).
"""
import json
import os
import queue
import subprocess
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_EXE = os.path.normpath(os.path.join(HERE, "..", "build", "w4p-net.exe"))
SAFE_ARGS = ["--bind", "127.0.0.1", "--no-stun"]


class Helper:
    """One w4p-net process. Instance k uses ICE port ice_base+k, emulator port emu_base+10k, slot ports slot_base+10k."""

    def __init__(self, name, args, outdir, exe=DEFAULT_EXE):
        assert "--no-stun" in args and "127.0.0.1" in args, "tests must not contact STUN servers"
        self.name = name
        self.outdir = outdir
        os.makedirs(outdir, exist_ok=True)
        self.cmd = [exe] + args + ["--log", os.path.join(outdir, name + "_connection-log.txt"),
                                   "--stats", os.path.join(outdir, name + "_stats.json")]
        self.t_start = time.perf_counter()
        self.proc = subprocess.Popen(self.cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                     text=True, encoding="utf-8", errors="replace", bufsize=1,
                                     creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        self.events = []  # (t since harness start of this helper, text without '@')
        self.lines = []
        self.cv = threading.Condition()
        self.stdout_path = os.path.join(outdir, name + "_stdout.txt")
        self.reader = threading.Thread(target=self._read, daemon=True)
        self.reader.start()

    def _read(self):
        with open(self.stdout_path, "w", encoding="utf-8") as f:
            for line in self.proc.stdout:
                line = line.rstrip("\r\n")
                t = time.perf_counter() - self.t_start
                f.write("[%9.3f] %s\n" % (t, line))
                f.flush()
                with self.cv:
                    self.lines.append((t, line))
                    if line.startswith("@"):
                        self.events.append((t, line[1:]))
                    self.cv.notify_all()
        with self.cv:
            self.cv.notify_all()

    def send(self, line):
        self.proc.stdin.write(line + "\n")
        self.proc.stdin.flush()

    def wait(self, prefix, timeout, after=0.0):
        """Waits for an event starting with prefix (seen at or after time `after`); returns (t, text) or None."""
        end = time.perf_counter() + timeout
        with self.cv:
            while True:
                for t, ev in self.events:
                    if t >= after and ev.startswith(prefix):
                        return t, ev
                left = end - time.perf_counter()
                if left <= 0 or self.proc.poll() is not None and not self.reader.is_alive():
                    return None
                self.cv.wait(min(left, 0.2))

    def find_all(self, prefix):
        with self.cv:
            return [(t, ev) for t, ev in self.events if ev.startswith(prefix)]

    def code(self, kind, timeout=15):
        r = self.wait("code " + kind, timeout)
        return r[1].split(" ", 2)[2] if r else None

    def quit(self, timeout=20):
        if self.proc.poll() is None:
            try:
                self.send("quit")
                self.proc.stdin.close()
            except OSError:
                pass
        else:
            try:
                self.proc.stdin.close()
            except OSError:
                pass
        try:
            self.proc.wait(timeout)
        except subprocess.TimeoutExpired:
            self.proc.kill()  # our own test process only
            self.proc.wait(5)
        self.reader.join(5)
        st = self.wait("stats ", 0)
        return json.loads(st[1][6:]) if st else None

    def now(self):
        return time.perf_counter() - self.t_start


def ports(k, ice_base=45400, emu_base=45200, slot_base=45300):
    return {"ice": ice_base + k, "emu": emu_base + 10 * k, "slots": slot_base + 10 * k}


def helper_args(k, extra=(), **kw):
    p = ports(k, **kw)
    return SAFE_ARGS + ["--ice-port", str(p["ice"]), "--emu-port", str(p["emu"]), "--slot-ports", str(p["slots"])] + \
        list(extra)


# ---- minimal Python codec (tests only): Crockford base32 + CRC-16/CCITT-FALSE, same format as src/codec.cpp ----
ALPHA = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def crc16(data):
    crc = 0xFFFF
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc


def code_to_bytes(code):
    body = code.split("-", 1)[1].replace("-", "")
    acc, bits, out = 0, 0, bytearray()
    for ch in body:
        acc = (acc << 5) | ALPHA.index(ch)
        bits += 5
        if bits >= 8:
            out.append((acc >> (bits - 8)) & 0xFF)
            bits -= 8
            acc &= (1 << bits) - 1
    return bytes(out)


def bytes_to_code(data):
    data = bytearray(data)
    data[1] = len(data)
    c = crc16(data[:-2])
    data[-2], data[-1] = c >> 8, c & 0xFF
    acc, bits, sym = 0, 0, ""
    for b in data:
        acc = (acc << 8) | b
        bits += 8
        while bits >= 5:
            sym += ALPHA[(acc >> (bits - 5)) & 31]
            bits -= 5
    if bits:
        sym += ALPHA[(acc << (5 - bits)) & 31]
    return "W4P1-" + "-".join(sym[i:i + 5] for i in range(0, len(sym), 5))


def retarget_join_code(code, new_port):
    """Join code with the same secret but every candidate port replaced (to make a foreign joiner dial our host)."""
    b = bytearray(code_to_bytes(code))
    assert b[0] == 0x11, "not a join code"
    p = 2 + 10
    n = b[p]
    p += 1
    for _ in range(n):
        fam = b[p] & 0x0F
        p += 1 + (16 if fam else 4)
        b[p], b[p + 1] = new_port >> 8, new_port & 0xFF
        p += 2
    return bytes_to_code(b)

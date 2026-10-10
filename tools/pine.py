"""Minimal PINE client for sandbox PCSX2 instances (Windows: TCP on 127.0.0.1:<slot>).

Opcodes per PCSX2 pcsx2/PINE.h (see docs/research/pcsx2_capabilities.md for
the verified table). Reads are serviced by the emulator asynchronously to the
emulated frame, so only use them on a paused/spinning guest for exact compares.

Usage:
    python -I tools/pine.py <slot> status|title|id|version|gamever
    python -I tools/pine.py <slot> read32 <hexaddr> [count]
    python -I tools/pine.py <slot> dump <hexaddr> <length> <outfile>
    python -I tools/pine.py <slot> savestate <n> | loadstate <n>
"""
import socket
import struct
import sys

OP = {"read8": 0, "read16": 1, "read32": 2, "read64": 3, "write8": 4, "write16": 5, "write32": 6, "write64": 7,
      "version": 8, "savestate": 9, "loadstate": 10, "title": 11, "id": 12, "uuid": 13, "gamever": 14, "status": 15}


class Pine:
    def __init__(self, slot, host="127.0.0.1", timeout=10.0):
        self.s = socket.create_connection((host, slot), timeout=timeout)

    def _xfer(self, payload):
        self.s.sendall(struct.pack("<I", len(payload) + 4) + payload)
        hdr = self._recv(4)
        size = struct.unpack("<I", hdr)[0]
        body = self._recv(size - 4)
        if body[0] != 0:
            raise RuntimeError(f"PINE error code {body[0]}")
        return body[1:]

    def _recv(self, n):
        buf = b""
        while len(buf) < n:
            chunk = self.s.recv(n - len(buf))
            if not chunk:
                raise ConnectionError("PINE closed")
            buf += chunk
        return buf

    def batch_read64(self, addrs):
        payload = b"".join(struct.pack("<BI", OP["read64"], a) for a in addrs)
        r = self._xfer(payload)
        return [struct.unpack_from("<Q", r, 8 * i)[0] for i in range(len(addrs))]

    def read32(self, a):
        return struct.unpack("<I", self._xfer(struct.pack("<BI", OP["read32"], a)))[0]

    def write32(self, a, v):
        self._xfer(struct.pack("<BII", OP["write32"], a, v))

    def batch_write32(self, pairs, chunk=60000):
        """Write many (addr, u32) pairs; split into requests under the 650,000-byte limit."""
        for i in range(0, len(pairs), chunk):
            part = pairs[i:i + chunk]
            self._xfer(b"".join(struct.pack("<BII", OP["write32"], a, v) for a, v in part))

    def write_bytes(self, addr, data):
        """Write a byte string (length padded to 4) as u32 words."""
        data = data + b"\x00" * (-len(data) % 4)
        self.batch_write32([(addr + i, struct.unpack_from("<I", data, i)[0]) for i in range(0, len(data), 4)])

    def string(self, op):
        r = self._xfer(bytes([OP[op]]))
        n = struct.unpack_from("<I", r)[0]
        return r[4:4 + n].rstrip(b"\0").decode("utf-8", "replace")

    def status(self):
        return {0: "running", 1: "paused", 2: "shutdown"}.get(struct.unpack("<I", self._xfer(bytes([OP["status"]])))[0])

    def state(self, op, n):
        self._xfer(bytes([OP[op], n]))

    def dump(self, addr, length, batch=4096):
        out = bytearray()
        for base in range(addr, addr + length, 8 * batch):
            cnt = min(batch, (addr + length - base + 7) // 8)
            for v in self.batch_read64([base + 8 * i for i in range(cnt)]):
                out += struct.pack("<Q", v)
        return bytes(out[:length])


def main():
    slot, cmd = int(sys.argv[1]), sys.argv[2]
    p = Pine(slot)
    if cmd == "status":
        print(p.status())
    elif cmd in ("title", "id", "version", "gamever", "uuid"):
        print(p.string(cmd))
    elif cmd == "read32":
        a = int(sys.argv[3], 16)
        for i in range(int(sys.argv[4]) if len(sys.argv) > 4 else 1):
            print(f"{a + 4 * i:08x}: {p.read32(a + 4 * i):08x}")
    elif cmd == "dump":
        data = p.dump(int(sys.argv[3], 16), int(sys.argv[4], 0))
        open(sys.argv[5], "wb").write(data)
        print(len(data), "bytes")
    elif cmd in ("savestate", "loadstate"):
        p.state(cmd, int(sys.argv[3]))
        print("ok")


if __name__ == "__main__":
    main()

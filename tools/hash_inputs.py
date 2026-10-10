"""Hash the protected original inputs (brief §2.2.5) without modifying them.

Every file is opened read-only. Output is JSON on stdout so it can be saved
under evidence/ and summarised into docs/HASHES.md.

Usage:
    python -I tools/hash_inputs.py [--quick]   # --quick skips the ISO
"""
import hashlib
import json
import os
import sys
import zlib
from datetime import datetime, timezone

ROOT = r"C:\Users\PC FORCE\Desktop\New folder"
ISO = os.path.join(ROOT, "Warriors The (USA) (EnFrDeEsIt)", "Warriors, The (USA) (En,Fr,De,Es,It).iso")
PCSX2 = os.path.join(ROOT, "pcsx2-v2.9.115-windows-x64-Qt")
BIOS_DIR = os.path.join(PCSX2, "bios")


def digest(path, full=True):
    sha256 = hashlib.sha256()
    md5 = hashlib.md5() if full else None
    sha1 = hashlib.sha1() if full else None
    crc = 0
    with open(path, "rb") as f:
        while True:
            chunk = f.read(16 * 1024 * 1024)
            if not chunk:
                break
            sha256.update(chunk)
            if full:
                md5.update(chunk)
                sha1.update(chunk)
                crc = zlib.crc32(chunk, crc)
    out = {"path": path, "size": os.path.getsize(path), "sha256": sha256.hexdigest()}
    if full:
        out.update(md5=md5.hexdigest(), sha1=sha1.hexdigest(), crc32=f"{crc & 0xFFFFFFFF:08x}")
    return out


def main():
    quick = "--quick" in sys.argv
    result = {"generated_utc": datetime.now(timezone.utc).isoformat(), "files": []}
    if not quick:
        result["files"].append({"role": "game image (ISO)", **digest(ISO)})
    for dirpath, _, names in os.walk(BIOS_DIR):
        for n in sorted(names):
            p = os.path.join(dirpath, n)
            result["files"].append({"role": "BIOS set file", **digest(p, full=False)})
    result["files"].append({"role": "PCSX2 executable", **digest(os.path.join(PCSX2, "pcsx2-qt.exe"), full=False)})
    json.dump(result, sys.stdout, indent=2)


if __name__ == "__main__":
    main()

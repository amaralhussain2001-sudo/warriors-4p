"""E5: measure savestate save/load cost via PINE on a running sandbox instance.
Usage: python -I e5_measure.py <inst> <pine_slot> <runs>
"""
import json, os, sys, time, zipfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "tools"))
from pine import Pine  # noqa: E402

inst, slot, runs = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
proj = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sdir = os.path.join(proj, "local", "pcsx2", f"inst{inst}", "PCSX2", "sstates")
p = Pine(slot)
SLOT = 9
path = os.path.join(sdir, f"SLUS-21215 (B99A75DE).{SLOT:02d}.p2s")
res = {"save": [], "load": []}
for r in range(runs):
    before = os.path.getmtime(path) if os.path.exists(path) else 0
    t0 = time.perf_counter()
    p.state("savestate", SLOT)
    # wait until file mtime changes and size is stable for 200 ms
    while not os.path.exists(path) or os.path.getmtime(path) == before:
        time.sleep(0.005)
    last = -1
    while True:
        s = os.path.getsize(path)
        if s == last:
            break
        last = s
        time.sleep(0.2)
    t_save = time.perf_counter() - t0 - 0.2
    t1 = time.perf_counter()
    p.state("loadstate", SLOT)
    # LoadState is queued; poll status until the emulator responds again
    p.status()
    t_load_ack = time.perf_counter() - t1
    res["save"].append({"wall_s_until_file_stable": round(t_save, 3), "size": last})
    res["load"].append({"pine_ack_s": round(t_load_ack, 4)})
    time.sleep(1.0)
with zipfile.ZipFile(path) as z:
    res["members"] = {i.filename: {"uncompressed": i.file_size, "compressed": i.compress_size} for i in z.infolist()}
res["total_uncompressed"] = sum(m["uncompressed"] for m in res["members"].values())
json.dump(res, sys.stdout, indent=1)

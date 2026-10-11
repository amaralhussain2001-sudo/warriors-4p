"""Save the running instance's state (PINE savestate, slot 1) and copy the .p2s to local/m2/states/<tag>.p2s, e.g. a
4-player Mission 13 state made at normal EE speed for the 60 fps measurement (the scripted boot fails at EE 180 %).
Used by nav_probe.py --probe statesave:save:<poll>; the instance number comes from nav_probe's --inst. Test only."""
import glob
import os
import shutil
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(PROJ, "tools"))
import sandbox  # noqa: E402


def save(p):
    inst = int(sys.argv[sys.argv.index("--inst") + 1]) if "--inst" in sys.argv else 6
    tag = sys.argv[1]
    t0 = time.time()
    poll = p.read32(0x000F0500)
    p.state("savestate", 1)
    found = None
    while time.time() - t0 < 30 and not found:
        time.sleep(1)
        files = [f for f in glob.glob(os.path.join(sandbox.inst_dir(inst), "**", "*.p2s"), recursive=True)
                 if os.path.getmtime(f) >= t0 - 1]
        if files:
            time.sleep(2)  # let the writer finish
            found = max(files, key=os.path.getmtime)
    if not found:
        return {"poll": poll, "error": "no state file"}
    os.makedirs(os.path.join(PROJ, "local", "m2", "states"), exist_ok=True)
    dst = os.path.join(PROJ, "local", "m2", "states", f"{tag}.p2s")
    shutil.copyfile(found, dst)
    return {"poll": poll, "src": found, "dst": dst, "bytes": os.path.getsize(dst)}

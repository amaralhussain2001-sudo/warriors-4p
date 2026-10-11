"""M6 per-mission smoke test (SINGLE-PC, 4 instances in lockstep, bots): jump to a story mission from the scripted
boot (W4P CallAt: SetCheckPoint(1) + MenuLoadLevel(level-table entry name), docs/research/level_jump.md), players 3-4
press Start every 300 polls (drop-in join: companion or spawned Warrior), random bot input, MTVU off, all M2 groups +
session groups. Per mission: hash mismatches, TLB misses, players / views / handles over time (PINE samples of slot 0).

Usage: python -I tests/m6/mission_smoke.py [--missions 1,2,3] [--seconds 600] [--tag smoke]
Writes local/m2/<tag>_m<NN>/ (via m2_run4.py), evidence/M6/<tag>_m<NN>.json and evidence/M6/<tag>_summary.json.
Mission completion is NOT tested here (bots cannot play objectives); see docs/plan/M6.md.
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.abspath(os.path.join(HERE, "..", ".."))
ENTRY0, ENTRY_SIZE = 0x01FD996C, 0x84  # level-table name of story index 1 when GameMgr = 0x01FD8400 (level_jump.md)
MISSIONS = {1: (99, "New Blood"), 2: (80, "Real Live Bunch"), 3: (87, "Payback"), 4: (34, "Blackout"),
            5: (2, "Real Heavy Rep"), 6: (3, "Writer's Block"), 7: (5, "Adios Amigo"), 8: (81, "Encore"),
            9: (86, "Payin' The Cost"), 10: (93, "Destroyed"), 11: (31, "Boys In Blue"), 12: (14, "Set Up"),
            13: (9, "All-City"), 14: (51, "Desperate Dudes"), 15: (52, None), 16: (54, None), 17: (55, None),
            18: (84, None)}
GROUPS = ("warriors-4p 4p hud B1;warriors-4p 4p hud B2;warriors-4p 4p spawn;warriors-4p 4p spawn leave;"
          "warriors-4p 4p inventory;warriors-4p 4p fx;warriors-4p session;warriors-4p session call")


def opt(name, default, cast=str):
    return cast(sys.argv[sys.argv.index(name) + 1]) if name in sys.argv else default


def main():
    tag = opt("--tag", "smoke")
    seconds = opt("--seconds", 600, int)
    wanted = [int(x) for x in opt("--missions", ",".join(str(k) for k in MISSIONS)).split(",")]
    os.makedirs(os.path.join(PROJ, "evidence", "M6"), exist_ok=True)
    summary = []
    for idx in wanted:
        level, name = MISSIONS[idx]
        ptr = ENTRY0 + (idx - 1) * ENTRY_SIZE
        run = f"{tag}_m{idx:02d}"
        cmd = [sys.executable, "-I", os.path.join(PROJ, "tests", "m2", "m2_run4.py"), run, "--seconds", str(seconds),
               "--polls", "40000", "--bots-from", "9000", "--script-bots-from", "14000", "--shot-slots", "0,1,2,3",
               "--shot-every", "20", "--sample-every", "15", "--crop",
               "--calls", f"3999:0041ABC0:1,4009:00160D78:0x{ptr:08X}",
               "--script3", os.path.join(PROJ, "tests", "m2", "nav", "m13_p3.txt"),
               "--script4", os.path.join(PROJ, "tests", "m2", "nav", "m13_p4.txt"),
               "--ini", "EmuCore/Speedhacks/vuThread=false", "--groups", GROUPS]
        print(f"mission {idx} (level {level}) -> {run}", flush=True)
        subprocess.run(cmd, cwd=PROJ, capture_output=True, text=True)
        out_dir = os.path.join(PROJ, "local", "m2", run)
        tlb = {}
        for n in (6, 7, 8, 9):
            src = os.path.join(PROJ, "local", "pcsx2", f"inst{n}", "PCSX2", "logs", "emulog.txt")
            try:
                txt = open(src, encoding="utf-8", errors="replace").read()
                open(os.path.join(out_dir, f"emulog_inst{n}.txt"), "w", encoding="utf-8").write(txt)
                tlb[n] = txt.count("TLB Miss")
            except OSError as e:
                tlb[n] = repr(e)
        ev = json.load(open(os.path.join(PROJ, "evidence", "M2", f"{run}.json")))
        samples = []
        try:
            samples = json.load(open(os.path.join(out_dir, "samples.json")))
        except (OSError, ValueError):
            pass
        players_seen = sorted({s.get("players") for s in samples if "players" in s})
        first4 = next((s.get("poll") for s in samples if s.get("players") == 4), None)
        row = {"mission": idx, "level": level, "name": name, "run": run, "seconds": ev.get("seconds"),
               "hash_points": ev.get("hash_points_common"), "mismatches": ev.get("hash_mismatches"),
               "first_mismatch": ev.get("first_mismatch"), "tlb_misses": tlb,
               "end_state": ev.get("state"), "players_seen": players_seen, "first_poll_with_4": first4,
               "last_sample": samples[-1] if samples else None}
        json.dump(row, open(os.path.join(PROJ, "evidence", "M6", f"{run}.json"), "w"), indent=1)
        summary.append(row)
        json.dump(summary, open(os.path.join(PROJ, "evidence", "M6", f"{tag}_summary.json"), "w"), indent=1)
        print(json.dumps({k: row[k] for k in ("mission", "hash_points", "mismatches", "tlb_misses", "players_seen",
                                              "first_poll_with_4")}), flush=True)


if __name__ == "__main__":
    main()

"""M7 criterion 1 summary of a long session run by tests/m7/long_run.sh (tests/m2/m2_run4.py): hash points and
mismatches (evidence/M2/<tag>.json), TLB misses (emulogs of the run's instances), level changes and the player count over
time (samples.json), softlock check (the poll counter keeps advancing), CPU and memory of the run's four emulators
(local/m7_<tag>_proc.csv rows filtered to the pids in local/pcsx2/inst<N>/pid.txt; the sampler logs every pcsx2 process
on the PC). Writes evidence/M7/<tag>.json.
Usage: python -I tests/m7/long_summary.py <tag> [inst_base]"""
import csv
import json
import os
import sys

PROJ = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))


def main():
    tag = sys.argv[1]
    base = int(sys.argv[2]) if len(sys.argv) > 2 else 6
    insts = list(range(base, base + 4))
    ev = json.load(open(os.path.join(PROJ, "evidence", "M2", f"{tag}.json")))
    out_dir = os.path.join(PROJ, "local", "m2", tag)
    samples = [s for s in json.load(open(os.path.join(out_dir, "samples.json"))) if "poll" in s]
    tlb, pids = {}, {}
    for n in insts:
        txt = open(os.path.join(PROJ, "local", "pcsx2", f"inst{n}", "PCSX2", "logs", "emulog.txt"), encoding="utf-8",
                   errors="replace").read()
        tlb[n] = txt.count("TLB Miss")
        try:
            pids[n] = int(open(os.path.join(PROJ, "local", "pcsx2", f"inst{n}", "pid.txt")).read().strip())
        except (OSError, ValueError):
            pids[n] = None
    # player count changes (level changes show as a drop to 0)
    changes, prev = [], None
    for s in samples:
        k = (s["players"], s["views"])
        if k != prev:
            changes.append({"t": s["t"], "poll": s["poll"], "players": s["players"], "views": s["views"]})
            prev = k
    reloads = [c for c in changes if c["players"] == 0 and c["poll"] > 5000]
    stalls = []
    for a, b in zip(samples, samples[1:]):
        if b["poll"] <= a["poll"]:
            stalls.append({"t": b["t"], "poll": b["poll"]})
    rate = [(b["poll"] - a["poll"]) / max(1, b["t"] - a["t"]) for a, b in zip(samples, samples[1:])]
    proc = {}
    pfile = os.path.join(PROJ, "local", f"m7_{tag}_proc.csv")
    if os.path.exists(pfile):
        want = {p: n for n, p in pids.items() if p}
        for r in csv.DictReader(open(pfile)):
            n = want.get(int(r["pid"]))
            if n is None:
                continue
            d = proc.setdefault(n, {"t": [], "cpu_s": [], "ws": [], "priv": []})
            d["t"].append(float(r["time_s"]))
            d["cpu_s"].append(float(r["cpu_s"]))
            d["ws"].append(float(r["working_set_mb"]))
            d["priv"].append(float(r["private_mb"]))
    cpu = {}
    for n, d in proc.items():
        if len(d["t"]) >= 2 and d["t"][-1] > d["t"][0]:
            cpu[n] = {"cpu_cores_avg": round((d["cpu_s"][-1] - d["cpu_s"][0]) / (d["t"][-1] - d["t"][0]), 2),
                      "working_set_mb_max": max(d["ws"]), "private_mb_max": max(d["priv"]),
                      "private_mb_first_last": [d["priv"][0], d["priv"][-1]], "samples": len(d["t"])}
    stats = ev.get("stats", {})
    row = {"tag": tag, "environment": ev.get("environment"), "seconds": ev.get("seconds"),
           "hash_points_common": ev.get("hash_points_common"), "hash_mismatches": ev.get("hash_mismatches"),
           "first_mismatch": ev.get("first_mismatch"), "tlb_misses": tlb,
           "w4p_stats_last": {k: (v.get("last") if isinstance(v, dict) else v) for k, v in stats.items()},
           "level_reloads": reloads, "player_count_changes": changes, "softlock_candidates": stalls,
           "last_sample": samples[-1] if samples else None,
           "polls_per_s": {"min": round(min(rate), 1) if rate else None, "max": round(max(rate), 1) if rate else None,
                           "mean": round(sum(rate) / len(rate), 1) if rate else None},
           "cpu_mem_per_instance": cpu, "end_state": ev.get("state")}
    os.makedirs(os.path.join(PROJ, "evidence", "M7"), exist_ok=True)
    json.dump(row, open(os.path.join(PROJ, "evidence", "M7", f"{tag}.json"), "w"), indent=1)
    print(json.dumps({k: row[k] for k in ("seconds", "hash_points_common", "hash_mismatches", "tlb_misses", "level_reloads",
                                          "softlock_candidates", "polls_per_s", "cpu_mem_per_instance")}, indent=1))


if __name__ == "__main__":
    main()

"""Summarise a fightlib.py log (local/m2/<tag>/fight.jsonl) against M2 criterion 3 (m2_combat34.md section 5).

Usage: python -I tests/m2/fight_report.py <tag>
Prints, for players 3-4: health drops, knock-down (prone flags 0xE0000/0x2000) and recovery, enemies whose target list
holds their handle, enemy health drops while that player was the nearest player (within 3 units), grabbed enemies (0x830).
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.abspath(os.path.join(HERE, "..", ".."))


def flags(info):
    return int(info.get("flags", "0x0"), 16)


def main():
    tag = sys.argv[1]
    events, rows = [], []
    for line in open(os.path.join(PROJ, "local", "m2", tag, "fight.jsonl")):
        d = json.loads(line)
        (events.append(d["event"]) if "event" in d else rows.append(d))
    out = {"tag": tag, "samples": len(rows), "polls": [rows[0]["poll"], rows[-1]["poll"]] if rows else None}
    out["teleports"] = [{k: e[k] for k in ("poll", "teleport", "enemy", "done", "dist_after")} for e in events if "teleport" in e]
    out["errors"] = [e for e in events if "error" in e][:3]
    g = next((e for e in events if "gangs" in e), None)
    if g:
        out["players_gang"] = g["players_gang"]
        out["hostile_gangs"] = [(x["gang"], x["alive"]) for x in g["gangs"] if x["hostile"]]
    for p in (2, 3):
        name = f"P{p + 1}"
        hs, prone, rec = [], 0, 0
        was_prone = False
        handle = None
        for r in rows:
            pl = r["players"][p]
            if len(pl) < 2 or "hp" not in pl[1]:
                continue
            handle = pl[0]
            hs.append((r["poll"], pl[1]["hp"]))
            pr = bool(flags(pl[1]) & 0xE2000)
            if pr and not was_prone:
                prone += 1
            if was_prone and not pr and pl[1]["hp"] > 0:
                rec += 1
            was_prone = pr
        drops = [(hs[i][0], hs[i - 1][1], hs[i][1]) for i in range(1, len(hs)) if hs[i][1] < hs[i - 1][1]]
        targeted = sorted({(r["poll"], e) for r in rows for e, inf in r["enemies"].items() if handle in inf.get("targets", [])})
        hits, grabs = [], []
        prev = {}
        for r in rows:
            for e, inf in r["enemies"].items():
                near = inf.get("near", {})
                nearest = min(near, key=near.get) if near else None
                if e in prev and "hp" in inf and inf["hp"] < prev[e] and nearest == name and near[name] <= 3.0:
                    others = {k: v for k, v in near.items() if k != name}
                    hits.append((r["poll"], e, prev[e], inf["hp"], round(near[name], 2), round(min(others.values()), 2) if others else None))
                if "hp" in inf:
                    prev[e] = inf["hp"]
                if flags(inf) & 0x830 and near.get(name, 99) <= 2.0:
                    grabs.append((r["poll"], e, inf["flags"]))
        out[name] = {"handle": handle, "hp_first_last": [hs[0][1], hs[-1][1]] if hs else None, "hp_drops": len(drops),
                     "hp_drop_first": drops[:3], "prone_starts": prone, "recoveries": rec,
                     "targeted_samples": len(targeted), "targeted_first": targeted[:2],
                     "enemy_hits_as_nearest": len(hits), "hits_first": hits[:3], "grab_samples": len(grabs), "grab_first": grabs[:2]}
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()

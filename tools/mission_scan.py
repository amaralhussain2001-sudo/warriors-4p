"""Scan the pseudo-Lua dumps (local/analysis/pseudo) per level and summarise co-op relevant facts.

A chunk is assigned to the level whose scene-id prefix ("lNN_") it uses most; chunks without a prefix are
reported as shared. Output: Markdown table + JSON (stdout / --json path). The output contains only counts and
identifier names (our evidence summary), not game script text.
"""
import collections
import glob
import json
import os
import re
import sys

PROJ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PSEUDO = os.path.join(PROJ, "local", "analysis", "pseudo")
STORY = [99, 80, 87, 34, 2, 3, 5, 81, 86, 93, 31, 14, 9, 51, 52, 54, 55, 84]
FLASHBACK = [82, 92, 83, 20, 11]
OTHER = [60, 61, 62, 63, 64, 95, 7]
WARRIORS = ["Cleon", "Swan", "Ajax", "Vermin", "Cochise", "Snow", "Rembrandt", "Cowboy", "Fox", "Ash", "Mercy"]
PATTERNS = {
    "join_on": r"CfgMultiplayerJoin\(true\)",
    "join_off": r"CfgMultiplayerJoin\(false\)",
    "set_p2_callback": r"SetPlayer2Callback\(",
    "set_mp_callback": r"SetMultiplayerCallback\(",
    "player2_refs": r"\bplayer2\b",
    "is_p2_human": r"HuIsAPlayer\(player2\)",
    "both_in_box": r"IsInsideBox\([^)]*player2\)",
    "warp_players": r"WarpPlayers\(",
    "teleport_p2": r"TeleportToFlag\(player2",
    "cam_secondary": r"CamSetSecondary\(",
    "cam_split": r"CamSetSplitMode\(",
    "switch_player": r"HuSwitchPlayer\(|SwapPlayerControl\(",
    "next_mission": r"NextMission\(",
    "mission_failed": r"HUDLaunchMissionFailed\(",
    "timer": r"HUDEnableTextProgress\(|StartTimer|HUDSetTextProgress\(",
}


def level_of(text):
    c = collections.Counter(int(x) for x in re.findall(r'"[lL](\d{1,3})_', text))
    return c.most_common(1)[0][0] if c else None


def main():
    per = collections.defaultdict(lambda: {"chunks": [], "bytes": 0, **{k: 0 for k in PATTERNS},
                                           "warriors": collections.Counter(), "gangs": collections.Counter()})
    for path in sorted(glob.glob(os.path.join(PSEUDO, "*.lua"))):
        t = open(path, encoding="utf-8").read()
        lv = level_of(t)
        key = lv if lv is not None else "shared"
        d = per[key]
        d["chunks"].append(os.path.basename(path)[:5])
        d["bytes"] += len(t)
        for k, pat in PATTERNS.items():
            d[k] += len(re.findall(pat, t))
        for w in WARRIORS:
            d["warriors"][w] += len(re.findall(r"\b%s\b" % w, t))
        for g in re.findall(r"\bGang([A-Z][A-Za-z]+)\b", t):
            if g not in ("Warriors", "Suspend", "BrDead", "BrFlush", "AddMember", "SetSpawnerMustBeOffScreen"):
                d["gangs"][g] += 1
    rows = []
    order = STORY + FLASHBACK + OTHER
    for lv in order + sorted(k for k in per if k not in order and k != "shared") + ["shared"]:
        if lv not in per:
            continue
        d = per[lv]
        rows.append({"level": lv, "chunks": len(d["chunks"]), "chunk_ids": d["chunks"][:12],
                     **{k: d[k] for k in PATTERNS},
                     "warriors": {w: n for w, n in d["warriors"].most_common() if n},
                     "gangs": [g for g, _ in d["gangs"].most_common(6)]})
    if "--json" in sys.argv:
        with open(sys.argv[sys.argv.index("--json") + 1], "w") as fh:
            json.dump(rows, fh, indent=1)
    cols = ["level", "chunks", "join_on", "join_off", "set_p2_callback", "player2_refs", "is_p2_human", "both_in_box",
            "warp_players", "teleport_p2", "cam_secondary", "switch_player"]
    print("| " + " | ".join(cols) + " | companions (name refs) | other gangs |")
    print("|" + "---|" * (len(cols) + 2))
    for r in rows:
        if isinstance(r["level"], int) and r["level"] >= 100:
            continue
        comp = ", ".join(f"{w} {n}" for w, n in list(r["warriors"].items())[:6])
        print("| " + " | ".join(str(r[c]) for c in cols) + f" | {comp} | {', '.join(r['gangs'])} |")


if __name__ == "__main__":
    main()

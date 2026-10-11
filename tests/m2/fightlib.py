"""Controlled combat probe for players 3-4 (M2 criterion 3, m2_combat34.md section 5). Used by nav_probe.py --fight.

From poll `start` on, it finds members of gangs that are hostile to the players' gang (gang table 0x005E6E30 +
i*0xB10: +0x18 active, +0x30 gang bit index, +0x38 hostility mask, +0x48 16 member handles; FUN_00168FE0, FUN_0028B358)
and moves player 3 and player 4 next to one each with the game's own HuTeleportNearHuman core FUN_0023B138(mover,
target) through the test-call mailbox ("warriors-4p test call" group). Players 1-2 stay where they are. Every sample
logs players' and the chosen enemies' health/flags/positions, the enemies' target lists (brain+0x164, 16 handles) and
who is near each enemy. Test only, single instance, PINE timing (not deterministic).
"""
import json
import math
import struct

GM_PTR = 0x0051489C
OBJ_TABLE = 0x006EBD38
GANGS, GANG_SIZE, GANG_COUNT = 0x005E6E30, 0xB10, 0x20
BRAINS, BRAIN_SIZE = 0x006D53F0, 0x2F0
POS_TABLE = 0x00714B00
TELEPORT_NEAR = 0x0023B138


def s16(v):
    v &= 0xFFFF
    return v - 0x10000 if v & 0x8000 else v


def resolve(pine, h):
    """Handle -> object (index h>>16, serial h&0xFFFF must match the table's serial), else 0."""
    if h in (0, 0xFFFFFFFF):
        return 0
    idx = (h >> 16) & 0xFFFF
    if idx >= 0x2000:
        return 0
    ptr, ser = pine.read32(OBJ_TABLE + 8 * idx), pine.read32(OBJ_TABLE + 8 * idx + 4) & 0xFFFF
    return ptr if ser == (h & 0xFFFF) else 0


def human_info(pine, o):
    """Health, max, flags (stats = human+0xD4), position (POS_TABLE + human[0x92]*0x20), brain, player index."""
    st = pine.read32(o + 0xD4)
    pidx = pine.read32(o + 0x1B0) & 0xFF
    bidx = s16(pine.read32(o + 0x90) >> 16)
    pos = [round(struct.unpack("<f", struct.pack("<I", pine.read32(POS_TABLE + bidx * 0x20 + 4 * i)))[0], 2) for i in range(3)]
    info = {"obj": hex(o), "pidx": pidx - 256 if pidx & 0x80 else pidx, "pos": pos, "brain_idx": bidx}
    if 0x00100000 <= st < 0x02000000:
        v = pine.read32(st + 0x144)
        info.update(hp=s16(v), max=s16(v >> 16), flags=hex(pine.batch_read64([st])[0]))
    return info


def dist(a, b):
    return math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(3)))


class Fight:
    def __init__(self, out, start, every_retarget=900):
        self.out, self.start, self.every = out, start, every_retarget
        self.rows, self.events = [], []
        self.targets = {2: None, 3: None}  # player index -> enemy handle
        self.last_move = {2: -10 ** 9, 3: -10 ** 9}
        self.gangs_logged = False

    def call(self, pine, fn, args, wait):
        vals = list(args) + [0] * (4 - len(args))
        pine.batch_write32([(0x000F0304, vals[0]), (0x000F0308, vals[1]), (0x000F030C, vals[2]), (0x000F0310, vals[3]),
                            (0x000F0318, 0), (0x000F0300, fn)])
        for _ in range(80):
            if pine.read32(0x000F0318) == 1:
                return True
            wait(0.05)
        return False

    def players(self, pine):
        gm = pine.read32(GM_PTR)
        return [pine.read32(gm + 0x228 + 4 * i) for i in range(4)]

    def hostile_members(self, pine, player_obj):
        """Alive members of gangs hostile to the given player's gang (either direction of the mask)."""
        brain = BRAINS + s16(pine.read32(player_obj + 0x90) >> 16) * BRAIN_SIZE
        pgang = pine.read32(brain + 0x20C)
        pbit = s16(pine.read32(pgang + 0x30)) & 0x1F
        pmask = pine.read32(pgang + 0x38)
        found, table = [], []
        for i in range(GANG_COUNT):
            g = GANGS + i * GANG_SIZE
            if pine.read32(g + 0x18) == 0:
                continue
            gbit, gmask = s16(pine.read32(g + 0x30)) & 0x1F, pine.read32(g + 0x38)
            members = [pine.read32(g + 0x48 + 4 * k) for k in range(16)]
            alive = []
            for h in members:
                o = resolve(pine, h)
                if o:
                    inf = human_info(pine, o)
                    if inf.get("hp", 0) > 0 and not int(inf.get("flags", "0x0"), 16) & 0x1_0000_0000:
                        alive.append((h, o, inf))
            hostile = bool(gmask >> pbit & 1) or bool(pmask >> gbit & 1)
            table.append({"gang": i, "addr": hex(g), "type": pine.read32(g + 0x2C), "bit": gbit, "mask": hex(gmask),
                          "players_gang": g == pgang, "hostile": hostile, "alive": len(alive)})
            if hostile and g != pgang:
                found += alive
        return found, table, {"brain": hex(brain), "brain_human_ok": pine.read32(brain) == player_obj,
                              "gang": hex(pgang), "bit": pbit, "mask": hex(pmask)}

    def step(self, pine, wait):
        poll = pine.read32(0x000F0500)
        if poll < self.start:
            return
        hs = self.players(pine)
        objs = [resolve(pine, h) for h in hs]
        if not objs[0]:
            return
        need = [p for p in (2, 3) if objs[p] and poll - self.last_move[p] >= 120 and self.needs_target(pine, p, objs)]
        if need:
            members, table, pinfo = self.hostile_members(pine, objs[0])
            if not self.gangs_logged or (members and self.gangs_logged == "empty"):
                self.events.append({"poll": poll, "gangs": table, "players_gang": pinfo, "hostile_alive": len(members)})
                self.gangs_logged = True if members else "empty"
            taken = {self.targets[q] for q in (2, 3) if q not in need}
            p1pos = human_info(pine, objs[0])["pos"]
            # prefer enemies far from player 1 (so players 1-2 and their companions are not in the fight)
            members.sort(key=lambda m: -dist(m[2]["pos"], p1pos))
            for p in need:
                pick = next((m for m in members if m[0] not in taken), None)
                if not pick:
                    break
                taken.add(pick[0])
                ok = self.call(pine, TELEPORT_NEAR, [hs[p], pick[0]], wait)
                self.targets[p], self.last_move[p] = pick[0], poll
                after = human_info(pine, objs[p])
                self.events.append({"poll": poll, "teleport": p + 1, "enemy": hex(pick[0]), "enemy_info": pick[2],
                                    "done": ok, "player_after": after, "dist_after": round(dist(after["pos"], pick[2]["pos"]), 2)})
        row = {"poll": poll, "players": [], "enemies": {}}
        for p in range(4):
            row["players"].append([hex(hs[p])] + ([human_info(pine, objs[p])] if objs[p] else []))
        allpos = [(f"P{p + 1}", human_info(pine, objs[p])["pos"]) for p in range(4) if objs[p]]
        for p in (2, 3):
            h = self.targets[p]
            o = resolve(pine, h) if h else 0
            if not o:
                continue
            inf = human_info(pine, o)
            brain = BRAINS + inf["brain_idx"] * BRAIN_SIZE
            tl = [pine.read32(brain + 0x164 + 4 * i) for i in range(16)]
            inf["targets"] = [hex(t) for t in tl if t not in (0, 0xFFFFFFFF)]
            inf["brain_human_ok"] = pine.read32(brain) == o
            inf["near"] = {name: round(dist(pos, inf["pos"]), 2) for name, pos in allpos}
            row["enemies"][hex(h)] = inf
        self.rows.append(row)

    def needs_target(self, pine, p, objs):
        h = self.targets[p]
        if h is None:
            return True
        o = resolve(pine, h)
        if not o:
            return True
        inf = human_info(pine, o)
        # dead (bit 32), beaten/incapacitated (0x8000_0000, the "not active" set 0x1_8005_0000) or 1 hp left
        if inf.get("hp", 0) <= 1 or int(inf.get("flags", "0x0"), 16) & 0x1_8005_0000 or int(inf.get("flags", "0x0"), 16) & 0x8000_0000:
            return True
        poll = pine.read32(0x000F0500)
        if self.every and poll - self.last_move[p] >= self.every:  # sample another enemy every `every` polls
            return True
        return dist(inf["pos"], human_info(pine, objs[p])["pos"]) > 8.0

    def save(self):
        with open(self.out, "w") as fh:
            for e in self.events:
                fh.write(json.dumps({"event": e}) + "\n")
            for r in self.rows:
                fh.write(json.dumps(r) + "\n")

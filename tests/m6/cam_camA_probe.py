"""camA: M16 "Home Run" chase cameras for players 3-4 (docs/research/m6_cam_camA.md, row local/m6/cam/camA/rows/m16q.lua).

Blocking scenario probes for tests/m2/nav_probe.py (--probe cam_camA_probe:<scenario>:<poll>), SINGLE-PC, one instance,
4 local W4P players (slots 3-4 = bots with empty input), no impairment. Each scenario waits for its chapter, makes players
3-4 join through the game's UpdateJoin (x6fix_probe.join34, what W4P X11 does), drives players 1-4 through the chase
boxes with short script teleports (next to player 1, at his height: the safe method of m6_x6_fixes.md) or direct calls of
the chapter functions, and records at each step the per-view cameras (render / follow / rail arrays of the [4p] group,
0x000F0810 / 0x000F0820 / 0x000F0830 + 4*i), the rail target (+0x340 / count +0x348, RAILTGT), split state and the
players, plus a screenshot local/m2/<tag>/camA_<nn>_<label>_p<poll>.png. Log: local/m2/<tag>/camA_log.jsonl.
Test aids (not part of the fix): HuSetGodMode on players 1-2 so the idle bots are not beaten during the drive.
Function names are OUR labels (the ELF is stripped). Static addresses, SLUS-21215 v1.03.
"""
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(PROJ, "tests", "m2"))
sys.path.insert(0, os.path.join(PROJ, "tools"))
import inv_tests as it  # noqa: E402
import x6fix_probe as xf  # noqa: E402

RENDER, FOLLOW, RAIL = 0x000F0810, 0x000F0820, 0x000F0830
VIEWS, SPLIT = 0x0050B198, 0x0050B1C0       # view count; CamEnable(3) SplitAllowed (FUN_0011DE58 case 3)
STEP = [0]


def _tag():
    return sys.argv[1]


def _inst():
    return int(sys.argv[sys.argv.index("--inst") + 1]) if "--inst" in sys.argv else 6


def _out():
    return os.path.join(PROJ, "local", "m2", _tag())


def _log(entry):
    with open(os.path.join(_out(), "camA_log.jsonl"), "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")


def _shot(p, label):
    try:
        import sandbox
        pid = int(open(os.path.join(sandbox.inst_dir(_inst()), "pid.txt")).read().strip())
        name = os.path.join(_out(), f"camA_{STEP[0]:02d}_{label}_p{it._poll(p)}.png")
        subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                        os.path.join(PROJ, "tools", "winshot.ps1"), "-ProcessId", str(pid), "-Out", name, "-Scale", "0.6"],
                       capture_output=True, timeout=60)
        return os.path.basename(name)
    except Exception as e:  # noqa: BLE001
        return repr(e)


def _wait(p, n):
    """Wait n polls (the game's pad reads; ~16-30 per second depending on the PC load)."""
    t0, start = time.time(), it._poll(p)
    while it._poll(p) < start + n and time.time() - t0 < n / 3 + 30:
        time.sleep(0.2)
    return it._poll(p)


def _lua(p, src, names=("W4P_R",)):
    """Run Lua through LUARUN (xf._run) and read integer globals back through player 1's money (restored)."""
    m0 = xf._money(p, 0)
    r = xf._run(p, "W4P_R = nil W4P_R2 = nil W4P_R3 = nil " + xf.PN + src)
    vals = {}
    for n in names:
        r2 = xf._run(p, f"InvSetMoney({n} or 998, 1)")
        vals[n] = xf._money(p, 0) if r2["v0"] == 0 else ("lua status", r2["v0"])
    xf._run(p, f"InvSetMoney({m0}, 1)")
    return {"status": r["v0"], "done": r["done"], "values": vals}


def _gmf(p):
    gm = it._gm(p)
    return {"count": it._s16(p.read32(gm + 0x224)), "cin": p.read32(gm + 0x410), "end14c": p.read32(gm + 0x14C),
            "cp": it._r16(p, gm + 0x33A), "views": p.read32(VIEWS), "split": p.read32(SPLIT)}


def cams(p):
    """Per view: render/follow/rail camera objects, what the view renders, rail target object and count."""
    pl = {i: it._player(p, i)[1] for i in range(4)}
    out = {}
    for i in range(4):
        r, f, rl = p.read32(RENDER + 4 * i), p.read32(FOLLOW + 4 * i), p.read32(RAIL + 4 * i)
        kind = "rail" if r and r == rl else ("follow" if r and r == f else ("none" if not r else "other"))
        v = {"render": hex(r), "follow": hex(f), "rail": hex(rl), "kind": kind}
        if kind == "other" and 0x00100000 <= r < 0x02000000:   # blend camera of a CameraMakeActive with blend > 0?
            try:
                import struct
                blob = p.dump(r, 0x600)
                ws = struct.unpack("<%dI" % (len(blob) // 4), blob[:len(blob) // 4 * 4])
                v["refs"] = [f"+0x{4 * k:X}={n}" for k, w in enumerate(ws)
                             for n, a in (("rail", rl), ("follow", f)) if a and w == a]
                # blend camera: +0x210 = camera blended from, +0x214 = camera blended to (camA_c2a, camA_dbg2)
                if "+0x214=rail" in v["refs"]:
                    v["kind"] = "rail(blend)"
                elif "+0x214=follow" in v["refs"]:
                    v["kind"] = "follow(blend)"
            except Exception as e:  # noqa: BLE001
                v["refs"] = repr(e)
        if 0x00100000 <= rl < 0x02000000:
            t = p.read32(rl + 0x340)
            v["rail_target"] = hex(t)
            v["rail_target_count"] = p.read32(rl + 0x348)
            v["rail_target_is"] = next((f"P{k + 1}" for k in range(4) if pl[k] and pl[k] == t), None)
            v["rail_params"] = [hex(p.read32(rl + o)) for o in range(0x370, 0x3C8, 4)]
        out[i] = v
    return out


def snap(p, label, shot=True, extra=None):
    STEP[0] += 1
    e = {"step": STEP[0], "label": label, "poll": it._poll(p), "gm": _gmf(p), "cams": cams(p),
         "players": {k: {"handle": v["handle"], "obj": v["obj"], "pos": [round(c, 2) for c in v["pos"]] if v["pos"] else None}
                     for k, v in xf._players(p).items() if k != "count"}}
    # HuSetNoAutoLock(h, v) = bit 39 of the u64 at human+0xE0 (core FUN_002340A8): word +0xE4 bit 7
    e["noautolock"] = {}
    for i in range(4):
        o = it._player(p, i)[1]
        e["noautolock"][i + 1] = (p.read32(o + 0xE4) >> 7) & 1 if o else None
    if extra:
        e.update(extra)
    if shot:
        e["shot"] = _shot(p, label)
    _log(e)
    return e


def _p1pos(p):
    o = it._player(p, 0)[1]
    return it._pos(p, o) if o else None


def tp(p, x, y, n4=True, dz=0.4):
    """Teleport players 1-2 (and players 3-4 when present) to a tight cluster at (x, y), player 1's height + dz
    (offsets <= 1 unit: a wider cluster dropped players 3-4 through the alley walls in runs camA_c1a/c1b). Players 1-4
    get HuSetGodMode again each time (ReturnPlayerBrain clears it for players 1-2; test aid only)."""
    z = _p1pos(p)[2] + dz
    src = (f"Teleport(player, {{{x}, {y}, {z}}}, -1) HuSetGodMode(player, 1) "
           f"if HuIsAPlayer(player2) then Teleport(player2, {{{x + 0.9}, {y + 0.3}, {z}}}, -1) HuSetGodMode(player2, 1) end ")
    if n4:
        src += (f"local h = HuGetPlayer(2) if h and HuIsAPlayer(h) then Teleport(h, {{{x - 0.9}, {y - 0.3}, {z}}}, -1) "
                f"HuSetGodMode(h, 1) end "
                f"h = HuGetPlayer(3) if h and HuIsAPlayer(h) then Teleport(h, {{{x + 1.8}, {y}, {z}}}, -1) HuSetGodMode(h, 1) end ")
    r = xf._run(p, src + "W4P_R = 1")
    return {"tp": [x, y, round(z, 2)], "status": r["v0"]}


def walk(p, pts, step=10.0, wait=35):
    """Hop from player 1's position through the given (x, y) points in steps of at most `step` units."""
    rows = []
    for (x, y) in pts:
        while True:
            x0, y0, _ = _p1pos(p)
            d = ((x - x0) ** 2 + (y - y0) ** 2) ** 0.5
            if d <= step:
                rows.append(tp(p, x, y))
                _wait(p, wait)
                break
            f = step / d
            rows.append(tp(p, round(x0 + (x - x0) * f, 2), round(y0 + (y - y0) * f, 2)))
            _wait(p, wait)
            if len(rows) > 80:
                return rows
    return rows


def inside(p, box):
    """IsInsideBox(box, player) for players 1..3 as digits (1 inside, 0 not, 9 not present; 3 digits: money <= 999)."""
    src = ("W4P_R = 0 for i = 0, 2 do local h = HuGetPlayer(i) local d = 9 "
           f"if h and HuIsAPlayer(h) then d = 0 if IsInsideBox({box}, h) then d = 1 end end W4P_R = W4P_R * 10 + d end")
    return _lua(p, src)["values"]["W4P_R"]


def join(p, tries=12, gap=150):
    res = []
    for _ in range(tries):
        g = _gmf(p)
        if g["count"] >= 4:
            break
        res.append(xf.join34(p))
        _wait(p, gap)
    return {"joins": res, "count": _gmf(p)["count"]}


def ensure_level(p, max_polls=900):
    """The CallAt level jump (3999/4009) did not take in runs camA_bisA/bisB (still M1 at poll 33000, PC under load):
    if the level is not level54 after max_polls, repeat the same two calls through the test-call mailbox."""
    t0 = it._poll(p)
    while it._poll(p) - t0 < max_polls:
        if it._cstr(p, it._gm(p) + 0x124, 16).startswith("level54"):
            return {"ok": True, "poll": it._poll(p)}
        time.sleep(1.0)
    ca = sys.argv[sys.argv.index("--callat") + 1].split(",")
    cp = int(ca[0].split(":")[2], 0)
    entry = int(ca[1].split(":")[2], 0)
    r1 = it._call(p, 0x0041ABC0, cp)
    _wait(p, 10)
    r2 = it._call(p, 0x00160D78, entry)
    _log({"ensure_level": "jump repeated", "r1": r1, "r2": r2})
    return {"ok": False, "repeated": [r1, r2], "poll": it._poll(p)}


def wait_lua(p, cond, max_polls, gap=120):
    if not STEP[1:]:
        STEP.append(ensure_level(p))
    t0 = it._poll(p)
    while it._poll(p) - t0 < max_polls:
        try:
            v = _lua(p, f"W4P_R = ({cond}) and 1 or 0")["values"]["W4P_R"]
            if v == 1:
                return {"ok": True, "poll": it._poll(p)}
        except Exception:  # noqa: BLE001
            pass
        _wait(p, gap)
    return {"ok": False, "poll": it._poll(p)}


def state_lua(p):
    """Row markers and mirror state: W4P_R = helpers*100 + m16q row*10 + (HuGetPlayer(1) == player2);
    W4P_R2 = rail handles known for views 3/4 (r[2]?*10 + r[3]?), W4P_R3 = recorded rail calls (W4Q.n)."""
    return _lua(p, "W4P_R = ((W4P_O and W4P_O.h) and 100 or 0) + ((W4P_O and W4P_O.m16q) and 10 or 0) + "
                   "((HuGetPlayer(1) == player2) and 1 or 0) "
                   "if W4Q then W4P_R2 = (W4Q.r[2] and 10 or 0) + (W4Q.r[3] and 1 or 0) W4P_R3 = W4Q.n end",
                ("W4P_R", "W4P_R2", "W4P_R3"))


def _god(p):
    return xf._run(p, "HuSetGodMode(player, 1) if HuIsAPlayer(player2) then HuSetGodMode(player2, 1) end "
                      "for i = 2, 3 do local h = HuGetPlayer(i) if h and HuIsAPlayer(h) then HuSetGodMode(h, 1) end end "
                      "W4P_R = 1")["v0"]


def _box_point(p, box, corner, size):
    """Point inside box: try the min-corner reading of AddVolumeBox (corner + size/2), else the corner itself."""
    cands = [(round(corner[0] + size[0] / 2, 2), round(corner[1] + size[1] / 2, 2)), (corner[0], corner[1])]
    return cands


def ab_replay(p, label):
    """A/B for players 1-2: run the join replay for player 3 and 4 again (W4Q.R, what a (re)join does) and compare
    players 1-2's render/rail/follow camera objects and rail parameters before and after (expect identical)."""
    before = cams(p)
    r = _lua(p, "W4P_R = 0 if W4Q then for i = 2, 3 do local h = HuGetPlayer(i) "
                "if h and HuIsAPlayer(h) then call(W4Q.R, {i, h; n = 2}, \"x\") W4P_R = W4P_R + 1 end end end")
    _wait(p, 30)
    after = cams(p)
    diff = [f"P{i + 1}.{k}" for i in (0, 1) for k in before[i] if before[i][k] != after[i].get(k)]
    same = not [d for d in diff if not d.endswith("rail_params")]
    e = snap(p, label, extra={"ab_replays": r["values"]["W4P_R"], "p12_unchanged": same, "p12_diff": diff,
                              "p12_before": {i: before[i] for i in (0, 1)}})
    return {"replays": r["values"]["W4P_R"], "p12_unchanged": same, "p12_diff": diff, "step": e["step"]}


# ---------------------------------------------------------------- scenarios
def _c1(p, do_join):
    out = {"start": it._poll(p)}
    out["wait_start"] = wait_lua(p, "ch1 and ch1.StartTheLevel == nil and chase", 14000)
    _wait(p, 60)
    out["god"] = _god(p)
    out["lua0"] = state_lua(p)
    snap(p, "level_started")
    if do_join:
        out["join"] = join(p)
        _wait(p, 60)
        out["lua1"] = state_lua(p)
        snap(p, "joined_startcam")
    # camswitch[1] (08262:1522, type 2): group switch to the street rail (CamSwitcher + ch1.OtherRailStart)
    for (x, y) in [(-82.0, -67.5), (-85.0, -82.5)]:
        tp(p, x, y)
        _wait(p, 25)
        if inside(p, "camswitch[1]") // 100 == 1:
            break
    _wait(p, 90)
    out["lua2"] = state_lua(p)
    snap(p, "after_camswitch1")
    # street to camswitch[2] (shared AlleyTrans view)
    out["walk_street"] = walk(p, [(-150.0, -67.5), (-200.0, -67.0)])
    snap(p, "street_mid")
    out["walk_street2"] = walk(p, [(-255.0, -66.0), (-266.2, -65.7)])
    _wait(p, 60)
    snap(p, "after_camswitch2")
    # camswitch[3] (rail spec S3 built per player) then vbGoGoGo (ch1.ReturnPlayerBrain: split on, rails active)
    out["walk_alley0"] = walk(p, [(-281.9, -38.7)])
    out["in3"] = inside(p, "camswitch[3]")
    _wait(p, 40)
    snap(p, "after_camswitch3")
    out["walk_alley1"] = walk(p, [(-296.0, -38.4), (-305.0, -38.1)])
    out["inGo"] = inside(p, "vbGoGoGo")
    _wait(p, 90)
    out["lua3"] = state_lua(p)
    snap(p, "after_gogogo")
    out["walk_alley2"] = walk(p, [(-335.2, -37.2)])
    _wait(p, 40)
    snap(p, "after_leadout1")
    out["walk_alley3"] = walk(p, [(-351.3, -37.2), (-384.0, -37.2), (-400.1, -37.2), (-414.0, -37.2), (-430.1, -37.2)])
    snap(p, "alley_end")
    out["walk_cs4"] = walk(p, [(-435.6, -36.6)])
    out["in4"] = inside(p, "camswitch[4]")
    _wait(p, 30)
    snap(p, "after_camswitch4")
    out["walk_cs5"] = walk(p, [(-446.3, -36.1)])
    out["in5"] = inside(p, "camswitch[5]")
    _wait(p, 60)
    snap(p, "after_camswitch5")
    out["walk_cs5b"] = walk(p, [(-455.0, -36.1)])
    _wait(p, 60)
    out["lua4"] = state_lua(p)
    snap(p, "past_camswitch5")
    out["ab"] = ab_replay(p, "ab_replay_p34")
    out["end"] = it._poll(p)
    _log({"scenario_result": out})
    return out


def c1_4p(p):
    return _c1(p, True)


def c1_2p(p):
    return _c1(p, False)


def c2_4p(p):
    """cp2 reload: join, then the chase functions called directly in the order the boxes/timers call them in continuous
    play (no teleports: the alley north of the cp2 start rises and teleports dropped everybody, run camA_c2a):
    chase.CamSwitcher(camswitch[7], player) (rails for players 1-2 + split on), ch2.BackToMainCam() (end of that rail),
    chase.CamSwitcher(camswitch[9], player / player2) (rail per player), chase.CamSwitcher(camswitch[14], player)."""
    out = {"start": it._poll(p)}
    out["wait_start"] = wait_lua(p, "ch2 and ch2.Gate and railCam", 14000)
    _wait(p, 60)
    out["god"] = _god(p)
    if C2_JOIN[0]:
        out["join"] = join(p)
        _wait(p, 60)
    out["god2"] = _god(p)
    out["lua0"] = state_lua(p)
    snap(p, "joined_cp2")
    out["cs7"] = _lua(p, "call(chase.CamSwitcher, {camswitch[7], player; n = 2}, \"x\") W4P_R = 1")
    _wait(p, 90)
    out["lua1"] = state_lua(p)
    snap(p, "after_camswitch7_call")
    out["btm"] = _lua(p, "call(ch2.BackToMainCam, {n = 0}, \"x\") W4P_R = 1")
    _wait(p, 60)
    snap(p, "after_backtomaincam_call")
    out["cs9"] = _lua(p, "call(chase.CamSwitcher, {camswitch[9], player; n = 2}, \"x\") "
                         "call(chase.CamSwitcher, {camswitch[9], player2; n = 2}, \"x\") W4P_R = 1")
    _wait(p, 90)
    out["lua2"] = state_lua(p)
    snap(p, "after_camswitch9_calls")
    out["cs14"] = _lua(p, "call(chase.CamSwitcher, {camswitch[14], player; n = 2}, \"x\") W4P_R = 1")
    _wait(p, 60)
    snap(p, "after_camswitch14_p1")
    out["ab"] = ab_replay(p, "ab_replay_p34")
    out["end"] = it._poll(p)
    _log({"scenario_result": out})
    return out


C2_JOIN = [True]


def c2_2p(p):
    """2-player regression for cp2 (players 3-4 never join): same direct calls as c2_4p."""
    C2_JOIN[0] = False
    return c2_4p(p)


def _c3(p, do_join):
    out = {"start": it._poll(p)}
    out["wait_start"] = wait_lua(p, "ch3 and ch3.GoSplit", 14000)
    _wait(p, 60)
    out["god"] = _god(p)
    out["lua0"] = state_lua(p)
    snap(p, "park_started")
    if do_join:
        out["join"] = join(p)
        _wait(p, 60)
        out["lua1"] = state_lua(p)
        snap(p, "joined_park")
    # no teleports in the park: the path slopes down and a teleport at player 1's height dropped everybody through the
    # ground in run camA_c3a (z -235, level end); the bots stand still, the rails frame them where they are
    _god(p)
    _wait(p, 150)
    snap(p, "park_run")
    out["ab"] = ab_replay(p, "ab_replay_p34")
    # end of the park chase: the objective callback (as reaching vbTriggerSplit does), scenes, AjaxScraps
    out["split"] = _lua(p, "call(ch3.StartSplit, {n = 0}, \"x\") W4P_R = 1")
    _wait(p, 60)
    snap(p, "split_called")
    t0 = it._poll(p)
    while it._poll(p) - t0 < 6000:
        g = _gmf(p)
        ok = _lua(p, "W4P_R = (player == ajax and weHateAjax ~= nil) and 1 or 0")["values"]["W4P_R"]
        if g["cin"] == 0 and ok == 1:
            break
        _wait(p, 150)
    _wait(p, 120)
    out["lua2"] = state_lua(p)
    snap(p, "after_ajaxscraps")
    if do_join:
        out["rejoin"] = join(p)
        _wait(p, 90)
        out["lua3"] = state_lua(p)
        snap(p, "rejoined_after_chase")
    out["end"] = it._poll(p)
    _log({"scenario_result": out})
    return out


def c3_4p(p):
    return _c3(p, True)


def c3_2p(p):
    """2-player regression (players 3-4 never join): same steps as c3_4p."""
    return _c3(p, False)


# ---------------------------------------------------------------- investigation (cp1 start: why the street rail never came)
def _flags64(p, o):
    st = p.read32(o + 0xD4)
    return p.batch_read64([st])[0] if 0x00100000 <= st < 0x02000000 else None


def dbg1(p):
    """cp1 start: spy on chase.CamSwitcher calls (count, last box index, last caller), then sample player 1's position,
    status flags (bit 32 = ignored by type-2 boxes, FUN_00227EB0), IsInsideBox(camswitch[1]) and view 0's camera;
    then call chase.CamSwitcher(camswitch[1], player) directly and sample again."""
    out = {"wait": wait_lua(p, "ch1 and chase and camswitch", 14000, gap=40)}
    out["spy"] = _lua(p, "W4P_CN = 0 W4P_CK = 0 W4P_CP = 0 local o = chase.CamSwitcher chase.CamSwitcher = function(a, b) "
                         "W4P_CN = W4P_CN + 1 W4P_CK = GetIndex(a, camswitch) W4P_CP = W4P_PN(b) return %o(a, b) end W4P_R = 1")
    rows = []
    for k in range(40):
        o = it._player(p, 0)[1]
        v = _lua(p, "W4P_R = (W4P_CN or 0) * 100 + (W4P_CK or 0) W4P_R2 = (IsInsideBox(camswitch[1], player) and 1 or 0) * 10 + "
                    "((ch1 and ch1.StartTheLevel == nil) and 1 or 0) W4P_R3 = W4P_CP", ("W4P_R", "W4P_R2", "W4P_R3"))["values"]
        fl = _flags64(p, o) if o else None
        rows.append({"poll": it._poll(p), "pos": [round(c, 2) for c in it._pos(p, o)] if o else None,
                     "flags": hex(fl) if fl is not None else None, "bit32": bool(fl is not None and fl >> 32 & 1),
                     "calls_k": v["W4P_R"], "in1_started": v["W4P_R2"], "caller": v["W4P_R3"],
                     "render0": hex(p.read32(RENDER)), "rail0": hex(p.read32(RAIL)), "views": p.read32(VIEWS),
                     "cin": p.read32(it._gm(p) + 0x410)})
        _log(rows[-1])
        if k in (0, 6, 14):
            snap(p, f"dbg_sample{k}")
        _wait(p, 50)
    out["direct"] = _lua(p, "call(chase.CamSwitcher, {camswitch[1], player; n = 2}, \"x\") W4P_R = (W4P_CN or 0) * 100 + W4P_CK")
    for k in range(8):
        _wait(p, 40)
        rows.append({"poll": it._poll(p), "render0": hex(p.read32(RENDER)), "rail0": hex(p.read32(RAIL)),
                     "views": p.read32(VIEWS)})
        _log(rows[-1])
    snap(p, "dbg_after_direct")
    out["rows"] = rows
    _log({"scenario_result": out})
    return out


def _step_ok(p, body):
    """Run body inside a protected function; W4P_R = 1 when it finished without a Lua error."""
    r = _lua(p, "W4P_R = call(function() " + body + " return 1 end, {n = 0}, \"x\") or 0")
    return r["values"]["W4P_R"]


def dbg2(p):
    """cp1 start, no joins: which part of chase.CamSwitcher's camswitch[1] path does not work. Each piece runs in a
    protected call (1 = no Lua error), view 0's camera is sampled after each."""
    out = {"wait": wait_lua(p, "ch1 and ch1.StartTheLevel == nil and chase", 14000, gap=60)}
    _wait(p, 30)
    def r0():
        return {"render0": hex(p.read32(RENDER)), "rail0": hex(p.read32(RAIL)), "views": p.read32(VIEWS), "poll": it._poll(p)}
    out["s0"] = r0()
    out["railCam_is_rail0"] = _lua(p, "W4P_R = (railCam and 1 or 0) W4P_R2 = (CameraGetActive(0) == railCam) and 1 or 0",
                                   ("W4P_R", "W4P_R2"))["values"]
    tests = [("speak", "HuSpeak(player, SetVag(\"l54_t1_007\"), nil)"),
             ("goals", "for k, v in CUR_GANG_TABLE do BrFlush(v) GoalDevilRun(v, chase.firstPath, GangWarriors, chase.ALTWAR_SPEED, "
                       "chase.ATTACK_AT_DIST, chase.SPEED_UP_RANGE, chase.MAX_FRIENDLY_SPEED, chase.MAX_FRIENDLY_URGENCY, false) "
                       "BrProcessGoal(v) end"),
             ("flagnet", "FlagNetAddLink(fUberHack[1], NilHandle, NilHandle, NilHandle, NilHandle)"),
             ("objective", "HUDSetObjective(0, LEVEL54.MS_C1_1, 0)"),
             ("dialogue", "chase.CheckDialogue()"),
             ("active_b1", "CameraMakeActive(railCam, 1, nil, player)")]
    res = {}
    for name, body in tests:
        res[name] = _step_ok(p, body)
        _wait(p, 40)
        res[name + "_cam"] = r0()
    _wait(p, 60)
    res["after_wait"] = r0()
    res["active_b0"] = _step_ok(p, "CameraMakeActive(railCam, 0, nil, player) CameraReset(railCam)")
    _wait(p, 40)
    res["active_b0_cam"] = r0()
    snap(p, "dbg2_after_b0")
    res["msout"] = _step_ok(p, "MSCamOut()")
    _wait(p, 80)
    res["msout_cam"] = r0()
    res["active_b1_again"] = _step_ok(p, "CameraMakeActive(railCam, 1, nil, player)")
    _wait(p, 60)
    res["active_b1_again_cam"] = r0()
    snap(p, "dbg2_end")
    out["res"] = res
    _log({"scenario_result": out})
    return out


def dbg3(p):
    """cp1 start, no joins: CamSwitcher spy from chapter load; sample the auto-run after StartTheLevel (position, calls,
    view 0 camera, IsInsideBox(camswitch[1])); then teleport players 1-2 into camswitch[1]; then a direct call."""
    out = {"wait": wait_lua(p, "ch1 and chase and camswitch", 14000, gap=40)}
    out["spy"] = _lua(p, "W4P_CN = 0 W4P_CK = 0 W4P_CP = 0 local o = chase.CamSwitcher chase.CamSwitcher = function(a, b) "
                         "W4P_CN = W4P_CN + 1 W4P_CK = GetIndex(a, camswitch) W4P_CP = W4P_PN(b) return %o(a, b) end W4P_R = 1")
    out["started"] = wait_lua(p, "ch1 and ch1.StartTheLevel == nil", 14000, gap=40)

    def sample(tag):
        o = it._player(p, 0)[1]
        v = _lua(p, "W4P_R = (W4P_CN or 0) * 100 + (W4P_CK or 0) W4P_R2 = (IsInsideBox(camswitch[1], player) and 1 or 0) * 10 + "
                    "(IsInsideBox(camswitch[1], player2) and 1 or 0) W4P_R3 = W4P_CP", ("W4P_R", "W4P_R2", "W4P_R3"))["values"]
        c = cams(p)
        row = {"tag": tag, "poll": it._poll(p), "pos": [round(x, 2) for x in it._pos(p, o)] if o else None,
               "calls_k": v["W4P_R"], "in1_p1p2": v["W4P_R2"], "caller": v["W4P_R3"], "v0": c[0]["kind"], "v1": c[1]["kind"],
               "render0": c[0]["render"], "views": p.read32(VIEWS), "gm": _gmf(p)}
        _log(row)
        return row
    rows = []
    for k in range(16):
        rows.append(sample("autorun"))
        _wait(p, 30)
    snap(p, "dbg3_autorun_end")
    out["tp1"] = tp(p, -82.0, -67.5, n4=False)
    for k in range(5):
        _wait(p, 30)
        rows.append(sample("tp_in1"))
    snap(p, "dbg3_after_tp")
    out["direct"] = _lua(p, "call(chase.CamSwitcher, {camswitch[1], player; n = 2}, \"x\") W4P_R = 1")
    for k in range(5):
        _wait(p, 30)
        rows.append(sample("direct"))
    snap(p, "dbg3_after_direct")
    out["rows"] = len(rows)
    _log({"scenario_result": out})
    return out


RAIL_VT = 0x00536DD0   # rail camera class vtable (m6_camera_parity.md 1.2)


def _vt_kind(p, obj):
    """What a render camera object is: a rail (vtable 0x00536DD0), or an object that points to a rail (blend)."""
    if not 0x00100000 <= obj < 0x02000000:
        return "none"
    if p.read32(obj) == RAIL_VT:
        return "rail"
    import struct
    blob = p.dump(obj, 0x400)
    ws = struct.unpack("<%dI" % (len(blob) // 4), blob)
    for k, w in enumerate(ws):
        if 0x00100000 <= w < 0x02000000 and w != obj:
            try:
                if p.read32(w) == RAIL_VT:
                    return f"blend->rail(+0x{4 * k:X})"
            except Exception:  # noqa: BLE001
                pass
    return "other"


def dbg4(p):
    """Minimal mod (groups test call + session + missions, 2 players, no [4p] camera relocation): does camswitch[1]
    put the street rail on views 1-2 there? Original per-view render array 0x005D9150 (camsafe.txt comment)."""
    out = {"wait": wait_lua(p, "ch1 and chase and camswitch", 14000, gap=40)}
    out["spy"] = _lua(p, "W4P_CN = 0 W4P_CK = 0 W4P_CP = 0 local o = chase.CamSwitcher chase.CamSwitcher = function(a, b) "
                         "W4P_CN = W4P_CN + 1 W4P_CK = GetIndex(a, camswitch) W4P_CP = W4P_PN(b) return %o(a, b) end W4P_R = 1")
    out["started"] = wait_lua(p, "ch1 and ch1.StartTheLevel == nil", 14000, gap=40)
    rows = []
    for k in range(20):
        o = it._player(p, 0)[1]
        v = _lua(p, "W4P_R = (W4P_CN or 0) * 100 + (W4P_CK or 0) W4P_R2 = W4P_CP", ("W4P_R", "W4P_R2"))["values"]
        arr = RENDER if p.read32(RENDER) or p.read32(RENDER + 4) else 0x005D9150   # [4p] relocates the array
        r0, r1 = p.read32(arr), p.read32(arr + 4)
        row = {"poll": it._poll(p), "pos": [round(x, 2) for x in it._pos(p, o)] if o else None, "calls_k": v["W4P_R"],
               "caller": v["W4P_R2"], "render0": hex(r0), "k0": _vt_kind(p, r0), "render1": hex(r1), "k1": _vt_kind(p, r1),
               "views": p.read32(VIEWS), "gm": _gmf(p)}
        _log(row)
        rows.append(row)
        if k in (4, 10, 19):
            snap(p, f"dbg4_{k}")
        _wait(p, 40)
    out["rows"] = len(rows)
    _log({"scenario_result": out})
    return out


def _dbg5(p, who):
    """Force who ('player' or 'player2') to be the first in camswitch[1]: teleport him into it right after
    StartTheLevel (the auto-run reaches the box about 150 polls later), then sample the cameras as dbg4."""
    out = {"wait": wait_lua(p, "ch1 and chase and camswitch", 14000, gap=40)}
    out["spy"] = _lua(p, "W4P_CN = 0 W4P_CK = 0 W4P_CP = 0 local o = chase.CamSwitcher chase.CamSwitcher = function(a, b) "
                         "W4P_CN = W4P_CN + 1 W4P_CK = GetIndex(a, camswitch) W4P_CP = W4P_PN(b) return %o(a, b) end W4P_R = 1")
    out["started"] = wait_lua(p, "ch1 and ch1.StartTheLevel == nil", 14000, gap=15)
    o = it._player(p, 0)[1]
    z = it._pos(p, o)[2] + 0.4
    out["tp"] = _lua(p, f"Teleport({who}, {{-82.0, -67.5, {z}}}, -1) W4P_R = 1")
    out["tp_poll"] = it._poll(p)
    for k in range(14):
        _wait(p, 35)
        v = _lua(p, "W4P_R = (W4P_CN or 0) * 100 + (W4P_CK or 0) W4P_R2 = W4P_CP", ("W4P_R", "W4P_R2"))["values"]
        arr = RENDER if p.read32(RENDER) or p.read32(RENDER + 4) else 0x005D9150
        r0, r1 = p.read32(arr), p.read32(arr + 4)
        row = {"poll": it._poll(p), "calls_k": v["W4P_R"], "caller": v["W4P_R2"], "k0": _vt_kind(p, r0),
               "k1": _vt_kind(p, r1), "views": p.read32(VIEWS), "gm": _gmf(p)}
        _log(row)
        if k in (3, 13):
            snap(p, f"dbg5_{k}")
    _log({"scenario_result": out})
    return out


def dbg5_p1(p):
    return _dbg5(p, "player")


def dbg5_p2(p):
    return _dbg5(p, "player2")

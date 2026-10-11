"""Game-over fade test (m2_fx34.md FX tests): kill player 3 with the game's HuKill core FUN_00237E70(handle) through the
test-call mailbox ("warriors-4p test call" group). Any player's death ends the mission (FUN_004197A8), so the
GAME OVER screen follows. Used by nav_probe.py --probe; test only, single instance."""
import time


def kill_p3(p):
    gm = p.read32(0x0051489C)
    h = p.read32(gm + 0x228 + 8)
    if h in (0, 0xFFFFFFFF):
        return {"error": "no player 3"}
    p.batch_write32([(0x000F0304, h), (0x000F0308, 0), (0x000F030C, 0), (0x000F0310, 0), (0x000F0318, 0),
                     (0x000F0300, 0x00237E70)])
    for _ in range(80):
        if p.read32(0x000F0318) == 1:
            break
        time.sleep(0.05)
    return {"handle": hex(h), "done": p.read32(0x000F0318), "poll": p.read32(0x000F0500)}


def fx_state(p):
    """Fade state of the four ScreenEffects objects (mirror 0x000F0890): raw words +0x190..+0x1CC for comparison."""
    out = {"poll": p.read32(0x000F0500)}
    for i in range(4):
        o = p.read32(0x000F0890 + 4 * i)
        out[f"fx{i}"] = [hex(p.read32(o + off)) for off in range(0x190, 0x1D0, 4)] if o else None
    return out


def kill_all(p):
    """All four players down (HuKill each); with nobody standing and no Flash the game ends (FUN_004197A8)."""
    gm = p.read32(0x0051489C)
    out = []
    for i in range(4):
        h = p.read32(gm + 0x228 + 4 * i)
        if h in (0, 0xFFFFFFFF):
            continue
        p.batch_write32([(0x000F0304, h), (0x000F0308, 0), (0x000F030C, 0), (0x000F0310, 0), (0x000F0318, 0),
                         (0x000F0300, 0x00237E70)])
        for _ in range(80):
            if p.read32(0x000F0318) == 1:
                break
            time.sleep(0.05)
        out.append((hex(h), p.read32(0x000F0318)))
    return {"killed": out, "poll": p.read32(0x000F0500)}

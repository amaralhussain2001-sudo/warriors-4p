"""M8 cp3 camera parity for players 3-4 (row m8cam, local/m6/cam/m8): row present, box cameras given (W4P_M8C.n) and the
last box index per player 3/4 (k2/k3) through x6fix_probe._q (player 1's money channel, restored; values < 999).
nav_probe.py --probe m8cam_probe:marks:<poll>; cameras per view: chase_probe:cams."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "m2"))
import inv_tests as it  # noqa: E402
import x6fix_probe as xf  # noqa: E402


def marks(p):
    src = ("W4P_R = (W4P_O and W4P_O.m8cam) and 1 or 0 "
           "W4P_R2 = (W4P_M8C and W4P_M8C.n) or 0 W4P_R3 = (W4P_M8C and W4P_M8C.k2) or 0 "
           "W4P_R4 = (W4P_M8C and W4P_M8C.k3) or 0 W4P_R5 = (W4P_M8C and W4P_M8C.go) or 0")
    return xf._q(p, f"m8cam_{it._poll(p)}", src, names=("W4P_R", "W4P_R2", "W4P_R3", "W4P_R4", "W4P_R5"))

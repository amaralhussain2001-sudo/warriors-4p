#!/bin/sh
# M6 criterion 3 (SINGLE-PC, 4 instances in lockstep, bots, SessionPolicies on): restart the current level from its
# checkpoint at poll 12000 with the call the session's "Last checkpoint" restart uses (MenuLoadLevel FUN_00160D78 with
# GameMgr+0x124 = 0x01FD8524 while GameMgr = 0x01FD8400, as in every run so far). Expect: the level reloads, player 2
# comes back on his pad, players 3-4 rejoin through X11, 0 mismatches, 0 TLB misses.
# Usage: sh tests/m6/restart_test.sh [missions] [tag]
cd "$(dirname "$0")/../.." || exit 1
python -I tests/m6/mission_smoke.py --missions "${1:-3,6,9,12,14,15}" --seconds 600 --tag "${2:-rst}" --policies \
  --calls-extra "12000:00160D78:0x01FD8524"

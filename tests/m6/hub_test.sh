#!/bin/sh
# X12 hub interlude test (SINGLE-PC, 4 instances, bots, SessionPolicies on): level jump from Mission 1 to the hub
# (level95, checkpoint 2 = before Mission 5), host random bot from poll 9000, players 2-4 no input of their own;
# at poll 12000 the test leaves the hub like story.LoadLevel does (SetCheckPoint(1) + MenuLoadLevel("level2")).
# Expect: "hub interlude starts" in the W4P logs, players 2-4 without characters in the hub, waiting text on their
# screens, 0 mismatches; after the load player 2 back on his own pad (4) and players 3-4 joined by X11.
cd "$(dirname "$0")/../.." || exit 1
python -I tests/m2/m2_run4.py "${1:-hub_cp2}" --seconds "${2:-600}" --polls 40000 --bots-from 9000 \
  --shot-slots 0,1,2,3 --shot-every 20 --sample-every 15 --crop \
  --calls "3999:0041ABC0:2,4009:00160D78:0x01FDA7DC,12000:0041ABC0:1,12010:00160D78:0x01FD9B7C" \
  --ini EmuCore/Speedhacks/vuThread=false --w4p "SessionPolicies = true" \
  --groups "warriors-4p 4p hud B1;warriors-4p 4p hud B2;warriors-4p 4p spawn;warriors-4p 4p spawn leave;warriors-4p 4p inventory;warriors-4p 4p fx;warriors-4p 4p markers;warriors-4p session;warriors-4p missions;warriors-4p session call"

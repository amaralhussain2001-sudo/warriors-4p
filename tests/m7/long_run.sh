#!/bin/sh
# M7 criterion 1: long session (SINGLE-PC, 4 instances in lockstep on loopback, bots, SessionPolicies on, Mission 13):
# >= 60 min with two checkpoint restarts = level changes (MenuLoadLevel FUN_00160D78 with GameMgr+0x124 = 0x01FD8524,
# the call the session's "Last checkpoint" restart uses) at polls 40000 and 80000; random bots from poll 9000 (they also
# reach GAME OVER and its menu by themselves). CPU / memory of every emulator sampled every 60 s (proc_sample.ps1).
# Usage: sh tests/m7/long_run.sh <tag> [seconds]
cd "$(dirname "$0")/../.." || exit 1
secs="${2:-3900}"
powershell -NoProfile -ExecutionPolicy Bypass -File tests/m7/proc_sample.ps1 -Out "local/m7_$1_proc.csv" \
  -Seconds "$secs" > /dev/null 2>&1 &
python -I tests/m2/m2_run4.py "$1" --seconds "$secs" --polls 130000 --bots-from 9000 --shot-slots 0,1,2,3 \
  --shot-every 120 --sample-every 30 --crop \
  --calls "3999:0041ABC0:1,4009:00160D78:0x01FD9F9C,40000:00160D78:0x01FD8524,80000:00160D78:0x01FD8524" \
  --ini EmuCore/Speedhacks/vuThread=false --w4p "SessionPolicies = true" \
  --groups "warriors-4p 4p hud B1;warriors-4p 4p hud B2;warriors-4p 4p spawn;warriors-4p 4p spawn leave;warriors-4p 4p inventory;warriors-4p 4p fx;warriors-4p 4p markers;warriors-4p session;warriors-4p missions;warriors-4p session call"
wait

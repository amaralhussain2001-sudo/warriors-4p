#!/bin/sh
# M7 criterion 3 (SINGLE-PC, 4 instances in lockstep on loopback, bots, SessionPolicies on, Mission 13): built-in
# transport impairment (W4P ImpairLatencyMs per packet = half the added round trip, ImpairJitterMs, ImpairLoss).
# Usage: sh tests/m7/impair_run.sh <tag> <latency_ms> <jitter_ms> <loss 0..1> <input_delay> [seconds]
cd "$(dirname "$0")/../.." || exit 1
python -I tests/m2/m2_run4.py "$1" --seconds "${6:-660}" --polls 40000 --bots-from 9000 --shot-slots 0 --shot-every 60 \
  --sample-every 15 --crop --calls "3999:0041ABC0:1,4009:00160D78:0x01FD9F9C" \
  --ini EmuCore/Speedhacks/vuThread=false --w4p "SessionPolicies = true" \
  --w4p "ImpairLatencyMs = $2" --w4p "ImpairJitterMs = $3" --w4p "ImpairLoss = $4" --w4p "InputDelay = $5" \
  --groups "warriors-4p 4p hud B1;warriors-4p 4p hud B2;warriors-4p 4p spawn;warriors-4p 4p spawn leave;warriors-4p 4p inventory;warriors-4p 4p fx;warriors-4p 4p markers;warriors-4p session;warriors-4p missions;warriors-4p session call"

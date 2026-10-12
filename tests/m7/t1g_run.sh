#!/bin/sh
# M7 criterion 2 / test T1g (docs/research/m5_connection_design.md 6): outages through the real connection path.
# SINGLE-PC, loopback, 4 w4p-net helpers (net/w4p-net/tests/local4.py, host candidates only, no STUN) and 4 emulators in
# lockstep whose peers are the helpers' slot ports (m2_run4 --peer-base), Mission 13, random bots, SessionPolicies on,
# W4P DisconnectTimeoutS default (60 s), host's choice "continue". Helper 3 drops the game data to and from every other
# slot (test switch "mute"; ICE, pings and control traffic keep running) for 20 s, later 45 s (both shorter than the
# timeout: expect the session to wait and resume with 0 mismatches), then 75 s (longer: expect the host's choice;
# "continue" drops player 4 and the other three go on in sync). Times are seconds after HELPERS READY.
# Usage: sh tests/m7/t1g_run.sh <tag> [inst_base]   (inst_base 27 -> emulator ports 41284-41287)
cd "$(dirname "$0")/../.." || exit 1
tag="${1:-t1g}"
base="${2:-27}"
p0=$((41200 + 4 * (base - 6)))
out="local/m7/$tag"
mkdir -p "$out"
rm -f "$out/stop_helpers"
python -I net/w4p-net/tests/local4.py --emu-ports "$p0,$((p0 + 1)),$((p0 + 2)),$((p0 + 3))" --seconds 1500 \
  --stop-file "$out/stop_helpers" --out "$out/helpers" --mute "3:420:20,3:620:45,3:840:75" > "$out/local4_console.txt" 2>&1 &
i=0
until grep -q "HELPERS READY" "$out/local4_console.txt" 2>/dev/null; do
  i=$((i + 1)); [ $i -gt 120 ] && { echo "helpers not ready"; exit 1; }; sleep 1
done
python -I tests/m2/m2_run4.py "$tag" --inst-base "$base" --peer-base 46100 --seconds 1260 --polls 40000 --bots-from 9000 \
  --shot-slots 0,1,2,3 --shot-every 30 --sample-every 10 --crop --leaver 3 \
  --calls "3999:0041ABC0:1,4009:00160D78:0x01FD9F9C" --ini EmuCore/Speedhacks/vuThread=false \
  --w4p "SessionPolicies = true" --w4p-slot0 "TestHostChoice = continue" \
  --groups "warriors-4p 4p hud B1;warriors-4p 4p hud B2;warriors-4p 4p spawn;warriors-4p 4p spawn leave;warriors-4p 4p inventory;warriors-4p 4p fx;warriors-4p 4p markers;warriors-4p session;warriors-4p missions;warriors-4p session call" \
  > "$out/run4_console.txt" 2>&1
touch "$out/stop_helpers"
wait
tail -30 "$out/run4_console.txt"

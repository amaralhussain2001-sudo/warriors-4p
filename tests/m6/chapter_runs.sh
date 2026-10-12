#!/bin/sh
# M6 chapter runs (SINGLE-PC, 4 instances in lockstep, loopback, bots, SessionPolicies on): start directly at the
# chapters that got camera-parity rows or chase changes and play them with button-mashing bots (all four slots tap the
# face buttons from poll 6000; players 3-4 join through X11 / the D24 rows). Per run: hash mismatches, TLB misses,
# checkpoints and player counts (tests/m6/chase4p_run.py -> evidence/M6/<tag>.json).
# Usage: sh tests/m6/chapter_runs.sh <tag prefix> <inst base> <mission:cp> [<mission:cp> ...]
cd "$(dirname "$0")/../.." || exit 1
pre="$1"; base="$2"; shift 2
for mc in "$@"; do
  m="${mc%%:*}"; c="${mc##*:}"
  tag="${pre}_m${m}cp${c}"
  python -I tests/m6/chase4p_run.py "$tag" --mission "$m" --cp "$c" --seconds 960 --tap-slots 0,1,2,3 --tap-from 6000 \
    --policies --inst-base "$base" > "local/m6/${tag}_console.txt" 2>&1
  python -I -c "import json; d = json.load(open('evidence/M6/$tag.json')); print('$tag', {k: d.get(k) for k in ('hash_points', 'mismatches', 'tlb_misses', 'checkpoints_seen', 'player_counts_seen')})"
done

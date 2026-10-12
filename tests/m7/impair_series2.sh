#!/bin/sh
# M7 criterion 3, second series: the runs whose input delay differs from 2, repeated after the m2_run4 fix (the first
# series appended InputDelay after the default line and the W4P ini reader kept the default 2; check "delay N" in the
# session-start line of local/m2/<tag>/w4p_slot0.log). Same format as impair_series.sh:
# tag latency_ms(one way) jitter_ms loss input_delay
cd "$(dirname "$0")/../.." || exit 1
while read -r tag lat jit loss delay; do
  [ -z "$tag" ] && continue
  echo "== $tag $(date +%H:%M)"
  sh tests/m7/impair_run.sh "$tag" "$lat" "$jit" "$loss" "$delay" > "local/m7_$tag.txt" 2>&1
  python -I -c "import json;d=json.load(open('evidence/M2/$tag.json'));print('$tag', d.get('hash_points_common'), d.get('hash_mismatches'))"
  grep -m1 "session started" "local/m2/$tag/w4p_slot0.log"
done <<LIST
imp_rtt100d3 50 0 0 3
imp_rtt150d4 75 0 0 4
imp_jit20d3 25 20 0 3
imp_loss5d3 25 0 0.05 3
LIST

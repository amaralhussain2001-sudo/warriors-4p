#!/bin/sh
# M7 criterion 3: impairment series, one 4-instance run after another (each about 11 min).
# tag latency_ms(one way) jitter_ms loss input_delay
cd "$(dirname "$0")/../.." || exit 1
while read -r tag lat jit loss delay; do
  [ -z "$tag" ] && continue
  echo "== $tag $(date +%H:%M)"
  sh tests/m7/impair_run.sh "$tag" "$lat" "$jit" "$loss" "$delay" > "local/m7_$tag.txt" 2>&1
  python -I -c "import json;d=json.load(open('evidence/M2/$tag.json'));print('$tag', d.get('hash_points_common'), d.get('hash_mismatches'))"
done <<LIST
imp_base 0 0 0 2
imp_rtt100 50 0 0 3
imp_rtt150 75 0 0 4
imp_jit20 25 20 0 3
imp_loss1 25 0 0.01 2
imp_loss5 25 0 0.05 3
LIST

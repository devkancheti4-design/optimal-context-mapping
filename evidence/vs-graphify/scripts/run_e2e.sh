#!/bin/zsh
# Part B: Claude + Graphify (3 shards, $12 each) and the final Model D (sequential, it learns; $15), on Django 2022.
source ${0:A:h}/env.sh; cd $TY
zsh scripts/serve.sh $TY/ws/alone 7721 > $H/results/serve_tools.log 2>&1 &
zsh scripts/serve.sh $H/ws/dj_e2e 7722 code > $H/results/serve_final.log 2>&1 &
for p in 7721 7722; do for i in $(seq 1 120); do curl -sf -X POST localhost:$p/stats -d '{}' >/dev/null && break; sleep 5; done; done
for s in 0 1 2; do
  $PY -I $H/scripts/e2e_graphify.py $H/graphs/django-2022/graphify-out/graph.json http://127.0.0.1:7721 \
      $H/results/rows_gf_s$s.jsonl --cap 12 --shard $s/3 --port $((8093 + s)) > $H/results/run_gf_s$s.log 2>&1 &
done
$PY -I scripts/team_year.py md window_2022.json http://127.0.0.1:7722 $H/results/rows_final.jsonl --cap 15 --keep keep.json > $H/results/run_final.log 2>&1
wait %3 %4 %5 2>/dev/null; wait
echo "E2E DONE"

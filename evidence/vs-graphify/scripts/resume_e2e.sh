#!/bin/zsh
# D1: resume Part B. Claude + Graphify unsharded (total cap $36); Model D final sequential (cap $15).
source ${0:A:h}/env.sh; cd $TY
zsh scripts/serve.sh $TY/ws/alone 7721 >> $H/results/serve_tools.log 2>&1 &
zsh scripts/serve.sh $H/ws/dj_e2e 7722 code >> $H/results/serve_final.log 2>&1 &
for p in 7721 7722; do for i in $(seq 1 120); do curl -sf -X POST localhost:$p/stats -d '{}' >/dev/null && break; sleep 5; done; done
$PY -I $H/scripts/e2e_graphify.py $H/graphs/django-2022/graphify-out/graph.json http://127.0.0.1:7721 \
    $H/results/rows_gf.jsonl --cap 36 --port 8093 >> $H/results/run_gf_rest.log 2>&1 &
$PY -I scripts/team_year.py md window_2022.json http://127.0.0.1:7722 $H/results/rows_final.jsonl --cap 15 --keep keep.json >> $H/results/run_final.log 2>&1
wait
pkill -f "serve.sh.*772[12]" ; pkill -f "ocm.server import main; main\(\['.*772[12]" 
echo "E2E DONE"

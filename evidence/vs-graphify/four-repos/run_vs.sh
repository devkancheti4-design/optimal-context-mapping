#!/bin/zsh
# Each snapshot: extract the code, build Model D 0.5.0 and Graphify 0.9.92, read every question with both.
source ~/neos/outreach/vs-graphify/scripts/env.sh
G=$PWD; P=~/neos/outreach/vs-graphify/scripts/point.py; mkdir -p snaps ws gfg vs_results
for qf in questions/*_20??.json; do
  b=${qf:t:r}; n=${b%_*}; sha=$(python3 -c "import json;print(json.load(open('$qf'))['snapshot'])")
  d=$G/snaps/$b
  [ -d $d ] || { mkdir -p $d && git -C hist/$n archive $sha | tar -x -C $d; }
  [ -f ws/$b/workspace.json ] || modeld build $d --out $G/ws/$b > ws_$b.log 2>&1
  [ -f gfg/$b/graph.json ] || GRAPHIFY_OUT=$G/gfg/$b $GF update $d > gfg_$b.log 2>&1
  [ -f vs_results/md_$b.json ] || $PY -I $P md $G/ws/$b $G/questions/$b.list.json $G/vs_results/md_$b.json
  [ -f vs_results/gf_$b.json ] || GF_PORT=8097 $PY -I $P gf $G/gfg/$b/graph.json $G/questions/$b.list.json $G/vs_results/gf_$b.json
  echo "$b done"
done
echo "VS DONE"

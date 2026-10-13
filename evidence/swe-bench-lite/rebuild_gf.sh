#!/bin/zsh
# Rebuild Graphify's graphs with 0.9.87, writing them outside the repos (graphs087/<name>/graphify-out).
L=~/neos/outreach/graphify-seed-study/lite; G=~/neos/outreach/graphify-pr/graphify
for n in flask seaborn xarray requests pylint pytest sphinx astropy matplotlib scikit-learn django sympy; do
  s=$(date +%s); mkdir -p $L/graphs087/$n
  (cd $G && GRAPHIFY_OUT=$L/graphs087/$n/graphify-out uv run --no-sync graphify update $L/repos/$n --no-cluster > $L/graphs087/$n/update.log 2>&1)
  echo "$n graph in $(( $(date +%s) - s ))s: $(ls $L/graphs087/$n/graphify-out/graph.json 2>/dev/null)"
done
echo "GRAPHS DONE"

#!/bin/zsh
# Part A on SWE-bench Lite, one repository at a time: Model D 0.5.0 build, cold readouts, modeld cover, covered
# readouts; Graphify 0.9.92 default build and readouts. Cover spend stops at $12 over all repositories.
source ${0:A:h}/env.sh; mkdir -p $H/ws/lite $H/graphs/lite $H/results
for n in flask requests seaborn xarray pytest pylint sphinx astropy matplotlib scikit-learn django sympy; do
  q=$H/questions/lite_$n.json; w=$H/ws/lite/$n
  [ -f $w/workspace.json ] || { s=$(date +%s); modeld build $LITE/repos/$n --out $w > $H/results/lite_build_$n.log 2>&1; echo "$n built in $(( $(date +%s) - s ))s"; }
  [ -f $H/results/lite_md_cold_$n.json ] || $PY -I $H/scripts/point.py md $w $q $H/results/lite_md_cold_$n.json
  spent=$(cat $H/results/lite_cover_*.log 2>/dev/null | grep -o 'questions written: \$[0-9.]*' | grep -o '[0-9.]*$' | paste -sd+ - | bc)
  left=$(echo "12 - ${spent:-0}" | bc)
  [ -f $H/results/lite_cover_$n.log ] || modeld cover --workspace $w --yes --cap $left > $H/results/lite_cover_$n.log 2>&1
  echo "$n cover: $(tail -2 $H/results/lite_cover_$n.log | tr '\n' ' ')"
  [ -f $H/results/lite_md_cover_$n.json ] || $PY -I $H/scripts/point.py md $w $q $H/results/lite_md_cover_$n.json
  g=$H/graphs/lite/$n/graphify-out
  [ -f $g/graph.json ] || { s=$(date +%s); GRAPHIFY_OUT=$g $GF update $LITE/repos/$n > $H/graphs/lite/$n.update.log 2>&1; rm -f $g/graph.html; echo "$n graph in $(( $(date +%s) - s ))s"; }
  [ -f $H/results/lite_gf_$n.json ] || GF_PORT=8096 $PY -I $H/scripts/point.py gf $g/graph.json $q $H/results/lite_gf_$n.json
done
echo "LITE DONE"

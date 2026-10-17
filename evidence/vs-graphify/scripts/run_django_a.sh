#!/bin/zsh
# Part A on Django 2022: Model D cold, Model D covered (modeld cover, fresh), Graphify; then the end-to-end copy.
source ${0:A:h}/env.sh; mkdir -p $H/ws $H/results
[ -d $H/ws/dj_cold ] || cp -R $TY/ws/base $H/ws/dj_cold
[ -d $H/ws/dj_cover ] || cp -R $TY/ws/base $H/ws/dj_cover
$PY -I $H/scripts/point.py md $H/ws/dj_cold $H/questions/django2022.json $H/results/dj_md_cold.json
modeld cover --workspace $H/ws/dj_cover --yes --cap 2 | tee $H/results/dj_cover.log
$PY -I $H/scripts/point.py md $H/ws/dj_cover $H/questions/django2022.json $H/results/dj_md_cover.json
GF_PORT=8092 $PY -I $H/scripts/point.py gf $H/graphs/django-2022/graphify-out/graph.json $H/questions/django2022.json $H/results/dj_gf.json
[ -d $H/ws/dj_e2e ] || cp -R $H/ws/dj_cover $H/ws/dj_e2e
echo "DJANGO A DONE"

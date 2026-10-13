#!/bin/zsh
# Fetch each SWE-bench Lite repo at its snapshot, then build graphify's AST graph and Model D's index over the full repo.
L=~/neos/outreach/graphify-seed-study/lite
G=~/neos/outreach/graphify-pr/graphify
OCM=~/ocm-eval/venvs/t021/bin/ocm
export OCM_OFFLINE=1 HF_HUB_OFFLINE=1 PYTHONUNBUFFERED=1
python3 -c "
import json; d=json.load(open('$L/swebench_lite_by_repo.json'))
order=sorted(d, key=lambda r: len(d[r]['issues']))
for r in order: print(r, d[r]['snapshot'])" > $L/repos.txt
while read slug sha; do
  name=${slug#*/}; dir=$L/repos/$name
  if [ ! -d $dir/.git ]; then
    mkdir -p $dir && git -C $dir init -q && git -C $dir remote add origin https://github.com/$slug
    git -C $dir fetch -q --depth 1 origin $sha && git -C $dir checkout -q FETCH_HEAD
  fi
  echo "$name at $(git -C $dir rev-parse --short HEAD), $(find $dir -type f -not -path '*/.git/*' | wc -l | tr -d ' ') files"
  if [ ! -f $dir/graphify-out/graph.json ]; then
    (cd $G && uv run --no-sync graphify update $dir --no-cluster > $L/$name.graphify.log 2>&1)
    echo "  graphify graph built"
  fi
  if [ ! -f $L/ws/$name/workspace.json ]; then
    s=$(date +%s); $OCM build $dir --out $L/ws/$name > $L/$name.ocm.log 2>&1
    echo "  model d index built in $(( $(date +%s) - s ))s: $(grep -o 'workspace ready.*' $L/$name.ocm.log)"
  fi
done < $L/repos.txt
echo "LITE PREP DONE"

#!/bin/zsh
# Rebuild Model D's index for each repo, now that Graphify's output lives outside the repo (graphs/<name>).
L=~/neos/outreach/graphify-seed-study/lite; OCM=~/ocm-eval/venvs/t021/bin/ocm
export OCM_OFFLINE=1 HF_HUB_OFFLINE=1
mv $L/ws $L/ws_polluted
for n in flask seaborn xarray requests pylint pytest sphinx astropy matplotlib scikit-learn django sympy; do
  s=$(date +%s)
  r=$($OCM build $L/repos/$n --out $L/ws/$n 2>&1 | grep -o "workspace ready.*")
  echo "$n rebuilt in $(( $(date +%s) - s ))s: $r"
done
echo "REBUILD DONE"

#!/bin/zsh
# PROTOCOL_VALUE E5: clone each repository at its snapshot and build its workspace with the compiled package (no model calls)
set -e
cd ~/cmlm-bench10/value
export OCM_OFFLINE=1 HF_HUB_OFFLINE=1
for spec in "sympy https://github.com/sympy/sympy.git" "scikit-learn https://github.com/scikit-learn/scikit-learn.git" "pytest https://github.com/pytest-dev/pytest.git"; do
  name=${spec%% *}; url=${spec#* }
  snap=$(python3 -c "import json;print(json.load(open('e5_issues.json'))['$name']['snapshot'])")
  if [ ! -d repos/$name/.git ]; then git clone -q --filter=blob:none --no-checkout $url repos/$name; fi
  git -C repos/$name -c advice.detachedHead=false checkout -q $snap
  echo "$name at $(git -C repos/$name rev-parse --short HEAD)"
  rm -rf ws_$name
  ~/ocm-eval/venvs/t312/bin/ocm build repos/$name --out ws_$name --device cpu 2>&1 | tail -1
done
echo E5 PREP DONE

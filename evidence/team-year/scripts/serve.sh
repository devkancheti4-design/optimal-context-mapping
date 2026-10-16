#!/bin/zsh
# scripts/serve.sh <workspace> <port> [scope]: the product's workspace server, current Model D code.
cd ${0:A:h:h}
OCM_OFFLINE=1 HF_HUB_OFFLINE=1 OCM_SCOPE=${3:-all} exec ~/ocm-eval/venvs/t021/bin/python -I -c "
import sys, os; sys.path.insert(0, os.path.expanduser('~/optimal-context-mapping'))
from ocm.server import main; main(['$1', '--port', '$2'])"

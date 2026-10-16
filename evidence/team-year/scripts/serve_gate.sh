#!/bin/zsh
# scripts/serve_gate.sh <workspace> <port>: the workspace server at relation-limit with CERT_MIN_OVER_OWN = 37, code scope.
cd ${0:A:h:h}
OCM_OFFLINE=1 HF_HUB_OFFLINE=1 OCM_SCOPE=code exec ~/ocm-eval/venvs/t021/bin/python -I -c "
import sys, os; sys.path.insert(0, os.path.abspath('ocm-gate'))
import ocm.router.lanes as L; L.CERT_MIN_OVER_OWN = 37
import ocm; assert ocm.__file__.startswith(os.path.abspath('ocm-gate')), ocm.__file__
from ocm.server import main; main(['$1', '--port', '$2'])"

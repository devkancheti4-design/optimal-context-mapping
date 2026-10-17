# Shared settings for the runs. The key is read from team-year/.env into the environment, never printed.
export H=~/neos/outreach/vs-graphify LITE=~/neos/outreach/graphify-seed-study/lite TY=~/neos/outreach/team-year
export PY=~/ocm-eval/venvs/t021/bin/python GF=$H/gfvenv/bin/graphify OCM_OFFLINE=1 HF_HUB_OFFLINE=1 PYTHONUNBUFFERED=1
export ANTHROPIC_API_KEY=$(grep '^ANTHROPIC_API_KEY=' $TY/.env | head -1 | cut -d= -f2-)
modeld() { $PY -I -c "import sys, os; sys.path.insert(0, os.path.expanduser('~/optimal-context-mapping'))
import ocm; assert ocm.__version__ == '0.5.0', ocm.__version__
from ocm.cli import main; main(sys.argv[1:])" "$@"; }

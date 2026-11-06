#!/bin/zsh
# Every positive track of PROTOCOL.md, in order of size: download, the primary run, the OCM_TESTS_TRAIL=off diagnostic, score,
# then delete the track's corpus to make room for the next. Stops rather than fill the disk. Resumes.
W=~/arb-work; PY=~/eval/envs/modeld/bin/python; E=~/optimal-context-mapping/evidence/agent-retrieval-bench
cd $W; rm -f STOP; export PYTHONPATH=$W/agent-retrieval-bench/src
free_mb() { df -m / | tail -1 | awk '{print $4}'; }
( while sleep 30; do [ -f $W/DONE ] && exit 0; if [ $(free_mb) -lt 700 ]; then echo "DISK GUARD: under 700 MB free, stopping"; touch $W/STOP; pkill -f "agent-retrieval-bench/run.py"; exit 0; fi; done ) &
rm -f DONE
for r in v2_trace2code v2_edit2ripple v2_comment2context v2_code2test; do
  [ -f STOP ] && break
  if [ -f results/modeld-0.5.3/${r}_bcy.json ] && [ -f results/modeld-0.5.3-trail-off/${r}_bcy.json ]; then echo "already scored $r"; continue; fi
  if [ ! -d data/corpus/$r ]; then
    $PY -m agent_retrieval_bench.cli download-benchmark --version $r --local-dir data --force 2>&1 | grep -v Malloc | tail -1 | cut -c1-80
    rm -rf data/releases/$r
  fi
  shasum -a 256 data/benchmark/$r/samples.jsonl
  $PY -I $E/run.py $r --label modeld-0.5.3 2>&1 | grep --line-buffered -v -E "MallocStackLogging|Loading|redirects"
  [ -f STOP ] && break
  OCM_TESTS_TRAIL=off $PY -I $E/run.py $r --label modeld-0.5.3-trail-off 2>&1 | grep --line-buffered -v -E "MallocStackLogging|Loading|redirects"
  [ -f STOP ] && break
  python3 $E/score.py $r
  rm -rf data/corpus/$r data/releases/$r data/eval/$r data/reports/$r cache
  echo "TRACK DONE $r, free $(free_mb) MB"
done
touch DONE
echo "ALL TRACKS STOPPED OR DONE"

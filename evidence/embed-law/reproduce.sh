#!/bin/zsh
# E8: every number of THE EMBEDDING LAW from one command, offline (no Claude, no API; embedding only).
#     zsh reproduce.sh       runs in the folder that holds it; log: reproduce.log, errors: stderr.log
#     zsh e8.sh              copies this harness byte for byte into a fresh folder, runs this there and compares every
#                            number with the record, so a regeneration never overwrites it.
# Inputs, not regenerated here: the 0.5.3 control (~/eval/repos/modelD, ec440d7), the branch worktree
# (~/optimal-context-mapping-embed-law), the bge-base ColdSession-Fresh maps (~/coldsession-fresh-work/<repo>/maps/modeld),
# the facts (~/coldsession/fresh/data/<repo>/facts.jsonl), the 20 Newsgroups corpus (~/cmlm-bench4/fts9m.db) and its
# questions (~/neos/sandbox/bench2/questions.json), and the two cached models. MiniLM maps are built when missing.
set -e; setopt pipefail
cd "${0:A:h}"
exec > >(tee reproduce.log) 2>&1
M=sentence-transformers/all-MiniLM-L6-v2; N=all-MiniLM-L6-v2
REPOS=(artemis FrontierAgent DeepInfer sphinx textual celery)
guard() { free=$(df -k ~ | tail -1 | awk '{print $4}'); [ "$free" -lt 1500000 ] && { echo "STOP: free disk ${free} KB"; exit 1; }; true; }
mkdir -p runs laws
echo "reproduce.sh $(date '+%Y-%m-%d %H:%M:%S') in $PWD"; shasum -a 256 PROTOCOL.md

echo "== Stage 1: where 37 and 8 come from (bge-base)"
guard; python3 -I stage1.py 2>>stderr.log | tail -9
python3 -I stage1b.py 2>>stderr.log | tail -1
python3 -I stage1d.py 2>>stderr.log | tail -1

echo "== the integer laws, each by a fresh, strictly alive colony, proven"
python3 -I laws/author_laws.py 2>>stderr.log | tail -8
python3 -I laws/author_whole.py 2>>stderr.log | tail -4

echo "== L1: one reference geometry per model"
guard; python3 -I l1_reference.py BAAI/bge-base-en-v1.5 l1_bge-base.json 2>>stderr.log | tail -1
python3 -I l1_reference.py $M l1_$N.json 2>>stderr.log | tail -1

echo "== bge-base: E2 (control vs branch on 0.5.3 maps), L1, L2"
for r in $REPOS; do
  WS=~/coldsession-fresh-work/$r/maps/modeld; F=~/coldsession/fresh/data/$r/facts.jsonl
  for code in control branch; do python3 -I gates.py --code $code --workspace $WS --facts $F --arm frozen --out runs/E2_${r}_$code.json 2>>stderr.log | tail -1; done
  python3 -I gates.py --code branch --workspace $WS --facts $F --arm L1 --l1 l1_bge-base.json --out runs/bge_${r}_L1.json 2>>stderr.log | tail -1
  python3 -I gates.py --code branch --workspace $WS --facts $F --arm L2 --out runs/bge_${r}_L2.json 2>>stderr.log | tail -1
done

echo "== MiniLM: maps (frozen = 0.5.3's way, read = part A), then the four arms"
for r in $REPOS; do
  guard
  [ -f maps/$N/frozen/$r/workspace.json ] || python3 -I build_maps.py control $M $r maps/$N/frozen/$r 2>>stderr.log | tail -1
  [ -f maps/$N/read/$r/workspace.json ] || python3 -I build_maps.py branch $M $r maps/$N/read/$r 2>>stderr.log | tail -1
done
for r in $REPOS; do
  F=~/coldsession/fresh/data/$r/facts.jsonl
  python3 -I gates.py --code control --workspace maps/$N/frozen/$r --facts $F --arm frozen --out runs/${N}_${r}_frozen.json 2>>stderr.log | tail -1
  python3 -I gates.py --code branch --workspace maps/$N/read/$r --facts $F --arm read --out runs/${N}_${r}_read.json 2>>stderr.log | tail -1
  python3 -I gates.py --code branch --workspace maps/$N/read/$r --facts $F --arm L1 --l1 l1_$N.json --out runs/${N}_${r}_L1.json 2>>stderr.log | tail -1
  python3 -I gates.py --code branch --workspace maps/$N/read/$r --facts $F --arm L2 --out runs/${N}_${r}_L2.json 2>>stderr.log | tail -1
done

echo "== E3 + E4 (CPU, twice), E6 (cost on the largest map), E7 (lessons carried under every model)"
python3 -I e4_e3.py 2>>stderr.log | tail -1 | tee runs/e4_e3.json
python3 -I e6.py 2>>stderr.log | tail -1 | tee runs/e6.json
python3 -I e7.py 2>>stderr.log | tail -4

echo "== TAU, authored after the geometry it is checked on (its rows include every measured lift98 and N)"
python3 -I laws/author_tau.py 2>>stderr.log | tail -8

echo "== Stage 3 and Stage 4"
python3 -I verify_wiring.py 2>>stderr.log
python3 -I analyze.py 2>>stderr.log
du -sh maps/$N; df -h ~ | tail -1 | awk '{print "free:", $4}'
echo "reproduce.sh done $(date '+%Y-%m-%d %H:%M:%S')"

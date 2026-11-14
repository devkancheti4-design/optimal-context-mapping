#!/bin/zsh
cd ~/neos/sandbox/embed_law
M=sentence-transformers/all-MiniLM-L6-v2; N=all-MiniLM-L6-v2
for r in artemis FrontierAgent DeepInfer sphinx textual celery; do
  free=$(df -k ~ | tail -1 | awk '{print $4}'); [ "$free" -lt 1500000 ] && { echo "STOP: free disk ${free} KB"; exit 1; }
  [ -f maps/$N/frozen/$r/workspace.json ] || python3 -I build_maps.py control $M $r maps/$N/frozen/$r 2>/dev/null | tail -1
  [ -f maps/$N/read/$r/workspace.json ] || python3 -I build_maps.py branch $M $r maps/$N/read/$r 2>/dev/null | tail -1
done
[ -f l1_$N.json ] || python3 -I l1_reference.py $M l1_$N.json 2>/dev/null | tail -1
for r in artemis FrontierAgent DeepInfer sphinx textual celery; do
  F=~/coldsession/fresh/data/$r/facts.jsonl
  python3 -I gates.py --code control --workspace maps/$N/frozen/$r --facts $F --arm frozen --out runs/${N}_${r}_frozen.json 2>/dev/null | tail -1
  python3 -I gates.py --code branch --workspace maps/$N/read/$r --facts $F --arm read --out runs/${N}_${r}_read.json 2>/dev/null | tail -1
  python3 -I gates.py --code branch --workspace maps/$N/read/$r --facts $F --arm L1 --l1 l1_$N.json --out runs/${N}_${r}_L1.json 2>/dev/null | tail -1
  python3 -I gates.py --code branch --workspace maps/$N/read/$r --facts $F --arm L2 --out runs/${N}_${r}_L2.json 2>/dev/null | tail -1
done
du -sh maps/$N; df -h ~ | tail -1 | awk '{print "free:", $4}'

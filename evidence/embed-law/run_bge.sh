#!/bin/zsh
cd ~/neos/sandbox/embed_law
for r in artemis FrontierAgent sphinx textual celery DeepInfer; do
  WS=~/coldsession-fresh-work/$r/maps/modeld; F=~/coldsession/fresh/data/$r/facts.jsonl
  [ $r != DeepInfer ] && for code in control branch; do python3 -I gates.py --code $code --workspace $WS --facts $F --arm frozen --out runs/E2_${r}_$code.json 2>/dev/null | tail -1; done
  python3 -I gates.py --code branch --workspace $WS --facts $F --arm L1 --l1 l1_bge-base.json --out runs/bge_${r}_L1.json 2>/dev/null | tail -1
  python3 -I gates.py --code branch --workspace $WS --facts $F --arm L2 --out runs/bge_${r}_L2.json 2>/dev/null | tail -1
done

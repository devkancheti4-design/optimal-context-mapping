"""PROTOCOL_VALUE6b: warm kit + strict Haiku reader.  python run6b.py N"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import harness as Hn
import run as R1
import run7 as R7
import run3 as R3
from harness import V
Hn.CAP = 175.0
n = int(sys.argv[1]); out = f"{V}/warm_strict_r{n}_md.jsonl"
p, url = Hn.serve(f"{V}/ws_warm_base", f"{V}/ws_warm_strict_r{n}", 7940 + n, fresh=not R1.resume(out))
try:
    done = Hn.done_ids(out)
    for it in R1.django_items():
        if it["id"] not in done and not R1.STOP.is_set():
            R3.one(f"warmS{n}", "modeld", it, lambda it: R7.md(it["text"], url, Hn.HAIKU, R7.STRICT), out)
finally:
    p.terminate()
print(f"DONE {n}: spend ${Hn.spent():.2f}", flush=True)

"""PROTOCOL_VALUE4 runner: python run4.py <build | run N>"""
import json, os, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import harness as Hn
import run as R1
import run2  # noqa: F401
import run3 as R3
from harness import V, H

Hn.CAP = 175.0
Q = json.load(open(f"{H}/questions_100.json"))
BASE = f"{V}/ws_v4_base"
_row = R1.item_row


def row_with_first(*a, **k):
    row = _row(*a, **k)
    seen = a[4] or []
    row["first"] = Hn.first_file(seen[0]) if seen else ""
    return row


R1.item_row = row_with_first


def score(it, row):
    f = row.get("first") if row.get("path") == "read" else row.get("at")
    return any(Hn.same_file(f, g) for g in it["golds"])


def build():
    subprocess.run([os.path.join(os.path.dirname(sys.executable), "ocm"), "build", f"{H}/corpus", "--out", BASE], check=True)


def run(n):
    items = [{"id": q["qid"], "text": q["question"], "gold": None, "golds": sorted({e["file"] for e in q["evidence"]}),
              "repeat": bool(q.get("counts_as_repeat"))} for q in Q]
    md_out, al_out = f"{V}/v4_r{n}_md.jsonl", f"{V}/v4_r{n}_alone.jsonl"
    pm, um = Hn.serve(BASE, f"{V}/ws_v4_r{n}", 7890 + n, fresh=not R1.resume(md_out))
    pa, ua = Hn.serve(BASE, f"{V}/ws_v4_r{n}_alone", 7895 + n)

    def md(it):
        res, seen = Hn.modeld(it["text"], um)
        return res, seen

    def al(it):
        a, t = Hn.alone(it["text"], ua)
        return {"path": "alone", "answer": a, "at": t}, []
    try:
        R3.pair(f"v4r{n}", items, md, al, md_out, al_out, score)
    finally:
        pm.terminate(); pa.terminate()


if __name__ == "__main__":
    build() if sys.argv[1] == "build" else run(int(sys.argv[2]))
    print(f"DONE {' '.join(sys.argv[1:])}: spend ${Hn.spent():.2f}", flush=True)

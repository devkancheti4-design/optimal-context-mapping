"""PROTOCOL_VALUE6 runner: python run6.py <warm | run N>"""
import json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import harness as Hn
import run as R1
from harness import V, H

Hn.CAP = 175.0
WARM = f"{V}/ws_warm_base"
STOP = set("the and for with that this from into when are was were not but has have had its use used uses using make made makes "
           "add added adds fix fixed fixes allow allowed allows can could should would will than then also only more less "
           "new old all any each other some such via per your you our them they their there here what which who how why".split())
FILES = json.load(open(f"{H}/swe/files.json"))


def words(s):
    return {w for w in re.findall(r"[a-z][a-z0-9]{2,}", s.lower()) if w not in STOP}


def best_line(subject, gold):
    want = words(subject); best = (-1, 0, 0)
    for fi, g in enumerate(gold):
        try:
            lines = open(FILES["corpus/" + g], encoding="utf-8").read().split("\n")
        except (OSError, UnicodeDecodeError, KeyError):
            continue
        for li, line in enumerate(lines, 1):
            o = len(want & words(line))
            if o > best[0] or (o == best[0] and (fi, li) < (best[1], best[2]) and best[0] > 0):
                best = (o, fi, li)
    return (gold[0], 1) if best[0] <= 0 else (gold[best[1]], best[2])


def warm():
    S = json.load(open(f"{H}/replay/stream.json"))
    hist = [c for c in S if c["date"] < "2019-01-30" and c["gold"] and all(("corpus/" + g) in FILES for g in c["gold"])]
    pairs = []
    for c in hist:
        f, line = best_line(c["raw"], c["gold"])
        pairs.append({"question": c["raw"], "at": f"corpus/{f}:{line}"})
    p, url = Hn.serve(R1.WS_BASE, WARM, 7910, fresh=True)
    try:
        ws = Hn.Workspace(url); total = 0
        for i in range(0, len(pairs), 200):
            r = ws.call("teach", pairs=pairs[i:i + 200]); total += int(re.match(r"taught (\d+)", r).group(1)) if r.startswith("taught") else 0
        print(f"history commits before 2019-01-30: {len(hist)}; taught {total}; last reply: {r[:160]}", flush=True)
        json.dump({"commits": len(hist), "taught": total}, open(f"{V}/warm_teach.json", "w"))
    finally:
        p.terminate()


def run(n):
    out = f"{V}/warm_r{n}_md.jsonl"
    pm, um = Hn.serve(WARM, f"{V}/ws_warm_r{n}", 7911 + n, fresh=not R1.resume(out))
    try:
        R1.md_stream(f"warm{n}", R1.django_items(), um, out)
    finally:
        pm.terminate()


if __name__ == "__main__":
    warm() if sys.argv[1] == "warm" else run(int(sys.argv[2]))
    print(f"DONE {' '.join(sys.argv[1:])}: spend ${Hn.spent():.2f}", flush=True)

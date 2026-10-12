"""PROTOCOL_VALUE2 runner: python run2.py <f1 RUN | f2 | f3q | f3 | f4>  (resumable; reuses run.py and harness.py)"""
import json, os, random, re, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import harness as Hn
import run as R1
from harness import V, H

Hn.CAP = 120.0                                   # PROTOCOL_VALUE2: both batches together
CORPUS = f"{H}/swe/corpus"

_item_row = R1.item_row


def item_row_long(*a, **k):                      # F3 scores file names anywhere in the answer: keep it whole
    row = _item_row(*a, **k)
    res = a[3] or {}
    row["answer"] = (res.get("answer") or "")[:4000]
    return row


R1.item_row = item_row_long


def f1(run):
    md_out, al_out = f"{V}/f1_r{run}_md.jsonl", f"{V}/f1_r{run}_alone.jsonl"
    base = 7831 + 2 * (int(run) - 2)
    pm, um = Hn.serve(R1.WS_BASE, f"{V}/ws_f1_r{run}", base, fresh=not R1.resume(md_out))
    pa, ua = Hn.serve(R1.WS_BASE, f"{V}/ws_f1_r{run}_alone", base + 1)
    try:
        R1.both(f"f1r{run}", R1.django_items(), um, ua, md_out, al_out)
    finally:
        pm.terminate(); pa.terminate()


def f2():
    from mask import mask
    md_out = f"{V}/f2_md.jsonl"
    pm, um = Hn.serve(R1.WS_BASE, f"{V}/ws_f2", 7835, fresh=not R1.resume(md_out))
    pa, ua = Hn.serve(R1.WS_BASE, f"{V}/ws_f2_alone", 7836)
    try:
        R1.both("f2", R1.django_items(lambda i: mask(i["issue"])), um, ua, md_out, f"{V}/f2_alone.jsonl")
    finally:
        pm.terminate(); pa.terminate()


def readers(setting):
    pats = (f"settings.{setting}", f'settings, "{setting}"', f"settings, '{setting}'")
    out = []
    for root, _, fs in os.walk(CORPUS):
        for f in fs:
            if not f.endswith(".py"):
                continue
            p = os.path.join(root, f); rel = os.path.relpath(p, CORPUS)
            if rel.endswith("conf/global_settings.py"):
                continue
            try:
                t = open(p, encoding="utf-8", errors="ignore").read()
            except OSError:
                continue
            if any(x in t for x in pats):
                out.append(rel)
    return sorted(out)


def f3q():
    e6 = {q["setting"] for q in json.load(open(f"{V}/e6_questions.json"))["questions"]}
    txt = open(f"{V}/settings_4a72da7.txt").read(); cands = []
    for m in re.finditer(r"(?m)^\.\. setting:: (\S+)\s*$", txt):
        name = m.group(1); body = txt[m.end(): m.end() + 1500]
        d = re.search(r"(?m)^Default: (.*)$", body); nxt = re.search(r"(?m)^\.\. setting:: ", body)
        if not d or (nxt and nxt.start() < d.start()):
            continue
        spans = re.findall(r"``([^`]+)``", d.group(1))
        if len(spans) == 1 and re.fullmatch(r"-?\d+(\.\d+)?|True|False|None|\[\]|\{\}|\(\)|'[^']*'|\"[^\"]*\"", spans[0].strip()):
            cands.append({"setting": name, "default": spans[0].strip()})
    pool = []
    for c in cands:
        if c["setting"] in e6:
            continue
        rd = readers(c["setting"])
        if rd:
            pool.append({**c, "readers": rd})
    pick = random.Random(20261009).sample(pool, 30)
    json.dump({"candidates": len(cands), "eligible": len(pool), "questions": pick}, open(f"{V}/f3_questions.json", "w"), indent=1)
    print(f"{len(pool)} eligible of {len(cands)}; picked {[p['setting'] for p in pick][:8]}...")


def f3_right(it, row):
    if not R1.e6_right(it, row):
        return False
    a = ((row.get("answer") or "") + " " + (row.get("at") or "")).replace("\\", "/")
    for rel in it["readers"]:
        tail = rel.split("/", 1)[1] if rel.startswith("django/") else rel
        dotted = rel[:-3].replace("/", ".")
        if tail in a or dotted in a or dotted.split(".", 1)[1] in a:
            return True
    return False


def f3():
    Q = json.load(open(f"{V}/f3_questions.json"))["questions"]
    md_out, al_out = f"{V}/f3_md.jsonl", f"{V}/f3_alone.jsonl"
    pm, um = Hn.serve(R1.WS_BASE, f"{V}/ws_f3", 7837, fresh=not R1.resume(md_out))
    pa, ua = Hn.serve(R1.WS_BASE, f"{V}/ws_f3_alone", 7838)
    try:
        for pas, tmpl in ((1, "Where in Django's source code is the {s} setting used, and what is its default value?"),
                          (2, "Which part of Django reads {s}, and what value does it have when a project does not set it?")):
            items = [{"id": f"{q['setting']}#{pas}", "text": tmpl.format(s=q["setting"]), "gold": None, "default": q["default"],
                      "readers": q["readers"]} for q in Q]
            R1.both("f3", items, um, ua, md_out, al_out, web=True, pas=pas, score=f3_right)
    finally:
        pm.terminate(); pa.terminate()


def f4():
    D = json.load(open(f"{V}/f4_issues.json"))
    for k, name in enumerate(["matplotlib", "sphinx", "requests", "flask"]):
        if R1.STOP.is_set():
            break
        items = [{"id": i["id"], "text": i["issue"], "gold": i["file"]} for i in D[name]["issues"]]
        md_out = f"{V}/f4_md.jsonl"
        fresh = not any(json.loads(l)["id"] in {x["id"] for x in items} for l in open(md_out)) if R1.resume(md_out) else True
        pm, um = Hn.serve(f"{V}/ws_{name}", f"{V}/ws_f4_{name}", 7840 + k, fresh=fresh)
        pa, ua = Hn.serve(f"{V}/ws_{name}", f"{V}/ws_f4_{name}_alone", 7850 + k)
        try:
            R1.both("f4", items, um, ua, md_out, f"{V}/f4_alone.jsonl")
        finally:
            pm.terminate(); pa.terminate()


if __name__ == "__main__":
    cmd = sys.argv[1]
    {"f1": lambda: f1(sys.argv[2]), "f2": f2, "f3q": f3q, "f3": f3, "f4": f4}[cmd]()
    print(f"DONE {' '.join(sys.argv[1:])}: spend ${Hn.spent():.2f}", flush=True)

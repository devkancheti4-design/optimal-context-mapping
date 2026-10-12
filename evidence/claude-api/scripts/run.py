"""PROTOCOL_VALUE runner: python run.py <e1 | e2gen | e2 | e3pairs | e3 | e4 | e5 | e6q | e6>  (resumable: done ids are skipped)"""
import json, os, random, re, sys, threading
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import harness as Hn
from harness import V, H

ISS = json.load(open(f"{H}/swe/issues.json"))["issues"]
WS_BASE = f"{H}/swe/ws_base"
STOP = threading.Event()


def item_row(exp, arm, it, res, seen, rec, err, pas=None):
    if not it.get("gold"):
        right = None                                   # E6: scored by its own rule
    elif res and res.get("path") == "read":
        right = Hn.same_file(Hn.first_file(seen[0] if seen else ""), it["gold"])
    else:
        right = Hn.same_file((res or {}).get("at"), it["gold"]) if it.get("gold") else None
    row = {"exp": exp, "arm": arm, "id": it["id"], "pass": pas, "path": (res or {}).get("path"), "right": right,
           "at": (res or {}).get("at"), "answer": ((res or {}).get("answer") or "")[:400], "error": err}
    row.update(Hn.summarise(rec))
    return row


def md_stream(exp, items, url, out, learn=True, web=False, pas=None, score=None):
    done = Hn.done_ids(out)
    for it in items:
        if STOP.is_set() or it["id"] in done:
            continue
        Hn.begin(); res, seen, err = None, [], None
        try:
            res, seen = (Hn.modeld_web if web else Hn.modeld)(it["text"], url, learn)
        except Hn.Capped as e:
            err = str(e); STOP.set()
        except Exception as e:
            err = f"{type(e).__name__}: {e}"[:300]
        row = item_row(exp, "modeld", it, res, seen, Hn.took(), err, pas)
        if score:
            row["right"] = score(it, row)
        Hn.write(out, row)
        print(f"{exp} MD  {it['id']:<28} {str(row['path']):<5} right={row['right']!s:<5} req={row['requests']:>2} ${row['usd']:.4f}  total ${Hn.spent():.2f}" + (f"  ERR {err}" if err else ""), flush=True)


def alone_pool(exp, items, url, out, workers=3, web=False, pas=None, score=None):
    done = Hn.done_ids(out)

    def one(it):
        if STOP.is_set():
            return
        Hn.begin(); ans, at, err = "", None, None
        try:
            ans, at = Hn.alone(it["text"], url, web)
        except Hn.Capped as e:
            err = str(e); STOP.set()
        except Exception as e:
            err = f"{type(e).__name__}: {e}"[:300]
        row = item_row(exp, "alone", it, {"path": "alone", "answer": ans, "at": at}, [], Hn.took(), err, pas)
        if score:
            row["right"] = score(it, row)
        Hn.write(out, row)
        print(f"{exp} AL  {it['id']:<28} right={row['right']!s:<5} req={row['requests']:>2} ${row['usd']:.4f}  total ${Hn.spent():.2f}" + (f"  ERR {err}" if err else ""), flush=True)

    with ThreadPoolExecutor(workers) as ex:
        list(ex.map(one, [it for it in items if it["id"] not in done]))


def both(exp, items, md_url, al_url, md_out, al_out, learn=True, web=False, pas=None, score=None, workers=3):
    t = threading.Thread(target=md_stream, args=(exp, items, md_url, md_out, learn, web, pas, score))
    t.start()
    alone_pool(exp, items, al_url, al_out, workers, web, pas, score)
    t.join()


def django_items(text=lambda i: i["issue"]):
    return [{"id": i["id"], "text": text(i), "gold": i["file"]} for i in ISS]


def resume(path):
    return os.path.exists(path) and os.path.getsize(path) > 0


def e1():
    md_out, al_out = f"{V}/e1_md.jsonl", f"{V}/e1_alone.jsonl"
    pm, um = Hn.serve(WS_BASE, f"{V}/ws_e1", 7801, fresh=not resume(md_out))
    pa, ua = Hn.serve(WS_BASE, f"{V}/ws_e1_alone", 7802)
    try:
        both("e1", django_items(), um, ua, md_out, al_out)
    finally:
        pm.terminate(); pa.terminate()


PARA = ("Rewrite this bug report the way a different engineer on another team might report the same problem. Keep every "
        "technical fact needed to find the bug, but use your own words and sentence structure; do not copy sentences; do "
        "not name any file path that the original does not name. Reply with the rewritten report only.")


def e2gen():
    path = f"{V}/paraphrases.json"
    have = json.load(open(path)) if os.path.exists(path) else {}

    def one(i):
        if i["id"] in have:
            return
        Hn.begin()
        r = Hn.CLIENT.messages.create(model=Hn.HAIKU, max_tokens=4000, system=PARA,
                                      messages=[{"role": "user", "content": i["issue"]}])
        have[i["id"]] = "".join(b.text for b in r.content if b.type == "text").strip()

    with ThreadPoolExecutor(4) as ex:
        list(ex.map(one, ISS))
    json.dump({i["id"]: have[i["id"]] for i in ISS}, open(path, "w"), indent=1)
    print(f"paraphrases: {len(have)}; total ${Hn.spent():.2f}")


def e2():
    P = json.load(open(f"{V}/paraphrases.json"))
    items = django_items(lambda i: P[i["id"]])
    pm, um = Hn.serve(WS_BASE, f"{V}/ws_e1", 7801, fresh=False)           # E1's taught workspace, as it is
    pa, ua = Hn.serve(WS_BASE, f"{V}/ws_e2_alone", 7803)
    try:
        both("e2", items, um, ua, f"{V}/e2_md.jsonl", f"{V}/e2_alone.jsonl")
    finally:
        pm.terminate(); pa.terminate()


def e3pairs():
    import numpy as np, torch
    from transformers import AutoModel, AutoTokenizer
    tok = AutoTokenizer.from_pretrained("BAAI/bge-base-en-v1.5"); m = AutoModel.from_pretrained("BAAI/bge-base-en-v1.5").eval()
    vecs = []
    with torch.no_grad():
        for i in ISS:
            x = tok(i["issue"], truncation=True, max_length=512, return_tensors="pt")
            v = m(**x).last_hidden_state[:, 0]; vecs.append(torch.nn.functional.normalize(v, dim=-1)[0].numpy())
    S = np.stack(vecs) @ np.stack(vecs).T
    taught, asked, pairs = set(), set(), []
    for b in range(len(ISS)):
        if b in taught or b in asked:
            continue
        order = [a for a in np.argsort(-S[b]) if a != b and ISS[a]["file"] != ISS[b]["file"] and a not in asked and a not in taught]
        if not order:
            continue
        a = int(order[0]); taught.add(a); asked.add(b)
        pairs.append({"A": ISS[a]["id"], "B": ISS[b]["id"], "cos": round(float(S[b, a]), 4)})
    json.dump(pairs, open(f"{V}/e3_pairs.json", "w"), indent=1)
    print(f"{len(pairs)} disjoint pairs; mean cosine {np.mean([p['cos'] for p in pairs]):.3f}")


def e3():
    pairs = json.load(open(f"{V}/e3_pairs.json")); by = {i["id"]: i for i in ISS}
    out = f"{V}/e3_md.jsonl"
    pm, um = Hn.serve(WS_BASE, f"{V}/ws_e3", 7808, fresh=not resume(out))
    try:
        if not resume(out):
            r = Hn.Workspace(um).call("teach", pairs=[{"question": by[p["A"]]["issue"], "at": f"corpus/{by[p['A']]['file']}:{by[p['A']]['line']}"} for p in pairs])
            print("taught A:", r[:160], flush=True)
        items = [{"id": p["B"], "text": by[p["B"]]["issue"], "gold": by[p["B"]]["file"]} for p in pairs]
        md_stream("e3", items, um, out, learn=False)
    finally:
        pm.terminate()


def e4():
    from mask import mask
    items = django_items(lambda i: mask(i["issue"]))
    md_out = f"{V}/e4_md.jsonl"
    pm, um = Hn.serve(WS_BASE, f"{V}/ws_e4", 7804, fresh=not resume(md_out))
    pa, ua = Hn.serve(WS_BASE, f"{V}/ws_e4_alone", 7805)
    try:
        both("e4", items, um, ua, md_out, f"{V}/e4_alone.jsonl")
    finally:
        pm.terminate(); pa.terminate()


def e5():
    D = json.load(open(f"{V}/e5_issues.json"))
    for k, name in enumerate(["sympy", "scikit-learn", "pytest"]):
        if Hn_stop():
            break
        items = [{"id": i["id"], "text": i["issue"], "gold": i["file"]} for i in D[name]["issues"]]
        src = f"{V}/ws_{name}"; md_out = f"{V}/e5_md.jsonl"
        fresh = not any(json.loads(l)["id"] in {x["id"] for x in items} for l in open(md_out)) if resume(md_out) else True
        pm, um = Hn.serve(src, f"{V}/ws_e5_{name}", 7810 + k, fresh=fresh)
        pa, ua = Hn.serve(src, f"{V}/ws_e5_{name}_alone", 7820 + k)
        try:
            both("e5", items, um, ua, md_out, f"{V}/e5_alone.jsonl")
        finally:
            pm.terminate(); pa.terminate()


def Hn_stop():
    return STOP.is_set()


def e6q():
    txt = open(f"{V}/settings_4a72da7.txt").read()
    cands = []
    for m in re.finditer(r"(?m)^\.\. setting:: (\S+)\s*$", txt):
        name = m.group(1); body = txt[m.end(): m.end() + 1500]
        d = re.search(r"(?m)^Default: (.*)$", body)
        nxt = re.search(r"(?m)^\.\. setting:: ", body)
        if not d or (nxt and nxt.start() < d.start()):
            continue
        spans = re.findall(r"``([^`]+)``", d.group(1))
        if len(spans) != 1:
            continue
        lit = spans[0].strip()
        if re.fullmatch(r"-?\d+(\.\d+)?|True|False|None|\[\]|\{\}|\(\)|'[^']*'|\"[^\"]*\"", lit):
            cands.append({"setting": name, "default": lit})
    rnd = random.Random(20261008); pick = rnd.sample(cands, 30)
    json.dump({"candidates": len(cands), "questions": pick}, open(f"{V}/e6_questions.json", "w"), indent=1)
    print(f"{len(cands)} candidate settings; 30 picked: {[p['setting'] for p in pick][:8]}...")


def norm(s):
    s = s.lower().replace("’", "'").replace("`", "")
    return re.sub(r"\s+", " ", s)


def e6_right(it, row):
    a, d = norm(row.get("answer") or ""), it["default"]
    words = {"[]": ["[]", "empty list"], "{}": ["{}", "empty dict"], "()": ["()", "empty tuple"], "None": ["none"],
             "True": ["true"], "False": ["false"]}
    if d in words:
        return any(w in a for w in words[d])
    if re.fullmatch(r"-?\d+(\.\d+)?", d):
        return d in re.sub(r"(?<=\d),(?=\d)", "", a)
    lit = d.strip("'\"").lower()
    return lit in a if lit else ("''" in a or '""' in a or "empty string" in a)


def e6():
    Q = json.load(open(f"{V}/e6_questions.json"))["questions"]
    md_out, al_out = f"{V}/e6_md.jsonl", f"{V}/e6_alone.jsonl"
    pm, um = Hn.serve(WS_BASE, f"{V}/ws_e6", 7806, fresh=not resume(md_out))
    pa, ua = Hn.serve(WS_BASE, f"{V}/ws_e6_alone", 7807)
    try:
        for pas, tmpl in ((1, "In Django, what is the default value of the {s} setting?"),
                          (2, "What does Django set {s} to when a project does not configure it?")):
            items = [{"id": f"{q['setting']}#{pas}", "text": tmpl.format(s=q["setting"]), "gold": None, "default": q["default"]} for q in Q]
            both("e6", items, um, ua, md_out, al_out, web=True, pas=pas, score=e6_right)
    finally:
        pm.terminate(); pa.terminate()


if __name__ == "__main__":
    {"e1": e1, "e2gen": e2gen, "e2": e2, "e3pairs": e3pairs, "e3": e3, "e4": e4, "e5": e5, "e6q": e6q, "e6": e6}[sys.argv[1]]()
    print(f"DONE {sys.argv[1]}: program spend ${Hn.spent():.2f}", flush=True)

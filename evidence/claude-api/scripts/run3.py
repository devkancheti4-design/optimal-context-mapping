"""PROTOCOL_VALUE3 runner: python run3.py <g1q | g1 | g2 | g3>"""
import json, os, random, re, sys, threading
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import harness as Hn
import run as R1
import run2  # noqa: F401  (keeps whole answers in rows)
from harness import V, H

Hn.CAP = 175.0
CORPUS = f"{H}/swe/corpus"
STOP = R1.STOP
SPEC = [{"name": t["name"], "description": t["description"], "input_schema": t["parameters"]} for t in Hn.TOOLS]


def loop(system, first, url, web_uses=0, effort=None):
    ws = Hn.Workspace(url)
    spec = SPEC + ([{"type": "web_search_20260209", "name": "web_search", "max_uses": web_uses}] if web_uses else [])
    kw = {"output_config": {"effort": effort}} if effort else {}
    messages = [{"role": "user", "content": first}]
    calls = n = 0
    while n < Hn.MAX_CALLS + 10:
        r = Hn.CLIENT.messages.create(model=Hn.SONNET, max_tokens=16000 if effort else 8000, system=system, tools=spec, messages=messages, **kw)
        n += 1
        if r.stop_reason == "pause_turn":
            messages.append({"role": "assistant", "content": r.content}); continue
        uses = [b for b in r.content if b.type == "tool_use"]
        if not uses:
            return "".join(b.text for b in r.content if b.type == "text").strip(), None
        messages.append({"role": "assistant", "content": r.content})
        results = []
        for u in uses:
            if u.name == "submit":
                return u.input.get("answer", ""), u.input.get("at") or None
            calls += 1
            out = ws.tool(u.name, u.input) if calls <= Hn.MAX_CALLS else "Tool limit reached: call submit now."
            results.append({"type": "tool_result", "tool_use_id": u.id, "content": out})
        messages.append({"role": "user", "content": results})
    return "", None


def md_custom(question, url, web_uses=0, effort=None):
    ws = Hn.WS(url, True)
    code = Hn.readout(ws.call, question)
    if code.startswith(Hn.TAUGHT):
        r = Hn.CLIENT.messages.create(model=Hn.HAIKU, max_tokens=1024, system=Hn.READ,
                                      messages=[{"role": "user", "content": f"Question: {question}\n\nCode:\n{code}"}])
        text = "".join(b.text for b in r.content if b.type == "text")
        if "NEED_SEARCH" not in text:
            return {"path": "read", "answer": text.strip(), "at": None}, ws.seen
    answer, at = loop(Hn.TEACH, f"Question: {question}\n\nThe code the team's workspace ranked for it:\n{code}", url, web_uses, effort)
    if at:
        ws.call("teach", pairs=[{"question": question, "at": at}])
    return {"path": "teach", "answer": answer, "at": at}, ws.seen


def one(exp, arm, it, fn, out, score=None, pas=None):
    Hn.begin(); res, seen, err = None, [], None
    try:
        res, seen = fn(it)
    except Hn.Capped as e:
        err = str(e); STOP.set()
    except Exception as e:
        err = f"{type(e).__name__}: {e}"[:300]
    row = R1.item_row(exp, arm, it, res, seen, Hn.took(), err, pas)
    if score:
        row["right"] = score(it, row)
    Hn.write(out, row)
    print(f"{exp} {arm[:2].upper()}  {it['id']:<30} {str(row['path']):<5} right={row['right']!s:<5} req={row['requests']:>2} ${row['usd']:.4f}  total ${Hn.spent():.2f}" + (f"  ERR {err}" if err else ""), flush=True)


def pair(exp, items, md_fn, al_fn, md_out, al_out, score=None, pas=None, workers=3):
    dm, da = Hn.done_ids(md_out), Hn.done_ids(al_out)
    t = threading.Thread(target=lambda: [one(exp, "modeld", it, md_fn, md_out, score, pas) for it in items if it["id"] not in dm and not STOP.is_set()])
    t.start()
    with ThreadPoolExecutor(workers) as ex:
        list(ex.map(lambda it: None if STOP.is_set() else one(exp, "alone", it, al_fn, al_out, score, pas), [it for it in items if it["id"] not in da]))
    t.join()


def files_named(text, golds):
    a = (text or "").replace("\\", "/")
    for g in golds:
        tail = g.split("/", 1)[1] if g.startswith("django/") else g
        dotted = g[:-3].replace("/", ".")
        if tail in a or dotted in a or dotted.split(".", 1)[1] in a:
            return True
    return False


# ---- G1: deep web research
def g1q():
    S = json.load(open(f"{H}/replay/stream.json")); T = json.load(open(f"{H}/replay/tickets.json"))["tickets"]
    pool = [c for c in S if "2022-01-01" <= c["date"] <= "2023-07-06" and len(T.get(str(c["k"]), [])) == 1
            and 1 <= len(c["gold"]) <= 2 and all(g.startswith("django/") and os.path.exists(f"{CORPUS}/{g}") for g in c["gold"])]
    pick = random.Random(20261010).sample(pool, 30)
    Q = [{"ticket": T[str(c["k"])][0], "subject": c["raw"], "gold": c["gold"], "date": c["date"]} for c in pick]
    json.dump({"eligible": len(pool), "questions": Q}, open(f"{V}/g1_questions.json", "w"), indent=1)
    print(f"{len(pool)} eligible; e.g. #{Q[0]['ticket']} {Q[0]['subject'][:70]} -> {Q[0]['gold']}")


def g1():
    Q = json.load(open(f"{V}/g1_questions.json"))["questions"]
    md_out, al_out = f"{V}/g1_md.jsonl", f"{V}/g1_alone.jsonl"
    pm, um = Hn.serve(R1.WS_BASE, f"{V}/ws_g1", 7860, fresh=not R1.resume(md_out))
    pa, ua = Hn.serve(R1.WS_BASE, f"{V}/ws_g1_alone", 7861)
    score = lambda it, row: files_named((row.get("answer") or "") + " " + (row.get("at") or ""), it["golds"])

    def al(it):
        a, t = loop(Hn.ALONE_SYS, f"Question: {it['text']}", ua, 8)
        return {"path": "alone", "answer": a, "at": t}, []
    try:
        for pas, tmpl in ((1, 'Django ticket #{n}: "{s}". Research it (the ticket, its fix and the code) and tell me which file in '
                              "Django's source the fix changed and, in one sentence, what was wrong."),
                          (2, "Which Django source file was changed to fix ticket #{n} ({s})?")):
            items = [{"id": f"{q['ticket']}#{pas}", "text": tmpl.format(n=q["ticket"], s=q["subject"]), "gold": None, "golds": q["gold"]} for q in Q]
            pair("g1", items, lambda it: md_custom(it["text"], um, web_uses=8), al, md_out, al_out, score, pas)
    finally:
        pm.terminate(); pa.terminate()


# ---- G2: long-running sessions
NOTE = (" You will receive a series of bug reports in this conversation, one at a time. For each one, find the file and "
        "line it concerns and call submit; the next report follows.")


def _cache_last(messages):
    for m in messages:
        if m["role"] == "user" and isinstance(m["content"], list):
            for b in m["content"]:
                if isinstance(b, dict):
                    b.pop("cache_control", None)
    last = messages[-1]
    if isinstance(last["content"], list) and isinstance(last["content"][-1], dict):
        last["content"][-1]["cache_control"] = {"type": "ephemeral"}


def session_turns(system, messages, url):
    ws = Hn.Workspace(url); calls = n = 0
    while n < 25:
        _cache_last(messages)
        r = Hn.CLIENT.messages.create(model=Hn.SONNET, max_tokens=8000, system=system, tools=SPEC, messages=messages)
        n += 1
        messages.append({"role": "assistant", "content": r.content})
        if r.stop_reason == "pause_turn":
            messages.append({"role": "user", "content": [{"type": "text", "text": "Continue."}]}); continue
        uses = [b for b in r.content if b.type == "tool_use"]
        if not uses:
            return "".join(b.text for b in r.content if b.type == "text").strip(), None, []
        results, sub = [], None
        for u in uses:
            if u.name == "submit":
                sub = u; results.append({"type": "tool_result", "tool_use_id": u.id, "content": "Recorded."}); continue
            calls += 1
            out = ws.tool(u.name, u.input) if calls <= Hn.MAX_CALLS else "Tool limit reached: call submit now."
            results.append({"type": "tool_result", "tool_use_id": u.id, "content": out})
        if sub:
            return sub.input.get("answer", ""), sub.input.get("at") or None, results
        messages.append({"role": "user", "content": results})
    return "", None, []


def session(arm, sid, reports, url, out):
    if any(json.loads(l)["session"] == sid and json.loads(l)["arm"] == arm for l in open(out)) if R1.resume(out) else False:
        return
    ws = Hn.WS(url, True)
    system = (Hn.ALONE_SYS if arm == "alone" else Hn.TEACH) + NOTE
    messages, pending = [], []
    for idx, it in enumerate(reports):
        if STOP.is_set():
            return
        text = f"Bug report {idx + 1}:\n{it['text']}"
        if arm == "modeld":
            text = f"The code the team's workspace ranked for this report:\n{Hn.readout(ws.call, it['text'])}\n\n" + text
        messages.append({"role": "user", "content": pending + [{"type": "text", "text": text}]})
        Hn.begin(); err = None; ans, at, pending = "", None, []
        try:
            ans, at, pending = session_turns(system, messages, url)
        except Hn.Capped as e:
            err = str(e); STOP.set()
        except Exception as e:
            err = f"{type(e).__name__}: {e}"[:300]
        if arm == "modeld" and at:
            ws.call("teach", pairs=[{"question": it["text"], "at": at}])
        row = {"exp": "g2", "arm": arm, "session": sid, "index": idx + 1, "id": f"s{sid}:{it['id']}", "right": Hn.same_file(at, it["gold"]),
               "at": at, "answer": (ans or "")[:400], "error": err, "path": None}
        row.update(Hn.summarise(Hn.took()))
        Hn.write(out, row)
        print(f"g2 {arm[:2].upper()} s{sid} #{idx + 1:>2} right={row['right']!s:<5} req={row['requests']:>2} tok={row['tokens']:,} ${row['usd']:.4f} total ${Hn.spent():.2f}" + (f"  ERR {err}" if err else ""), flush=True)
        if err:
            return


def g2():
    items = R1.django_items()[:45]; out = f"{V}/g2.jsonl"
    servers = []
    try:
        pa, ua = Hn.serve(R1.WS_BASE, f"{V}/ws_g2_alone", 7873); servers.append(pa)
        threads = []
        for sid in range(3):
            pm, um = Hn.serve(R1.WS_BASE, f"{V}/ws_g2_s{sid}", 7870 + sid); servers.append(pm)
            rep = items[sid * 15:(sid + 1) * 15]
            for arm, url in (("modeld", um), ("alone", ua)):
                threads.append(threading.Thread(target=session, args=(arm, sid, rep, url, out)))
        for t in threads:
            t.start()
        for t in threads:
            t.join()
    finally:
        for p in servers:
            p.terminate()


# ---- G3: deep thinking
def g3():
    e1 = {json.loads(l)["id"]: json.loads(l) for l in open(f"{V}/e1_alone.jsonl")}
    order = [i["id"] for i in R1.ISS]
    hard = sorted(order, key=lambda i: (-e1[i]["requests"], -e1[i]["tokens"]))[:30]
    items = [it for it in R1.django_items() if it["id"] in set(hard)]
    md_out, al_out = f"{V}/g3_md.jsonl", f"{V}/g3_alone.jsonl"
    pm, um = Hn.serve(R1.WS_BASE, f"{V}/ws_g3", 7880, fresh=not R1.resume(md_out))
    pa, ua = Hn.serve(R1.WS_BASE, f"{V}/ws_g3_alone", 7881)

    def al(it):
        a, t = loop(Hn.ALONE_SYS, f"Question: {it['text']}", ua, 0, "max")
        return {"path": "alone", "answer": a, "at": t}, []
    try:
        pair("g3", items, lambda it: md_custom(it["text"], um, 0, "max"), al, md_out, al_out)
    finally:
        pm.terminate(); pa.terminate()


if __name__ == "__main__":
    {"g1q": g1q, "g1": g1, "g2": g2, "g3": g3}[sys.argv[1]]()
    print(f"DONE {sys.argv[1]}: spend ${Hn.spent():.2f}", flush=True)

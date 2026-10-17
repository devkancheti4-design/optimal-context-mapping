"""modeld cover: teach the workspace the whole codebase once, before anyone asks.

  modeld cover [--workspace DIR] [--cap USD] [--yes] [--threads 8]

Claude Haiku 5.5 writes one question for every piece of non-test code (25 pieces per request, structured output), and
each question is taught onto the code it was written from, as a pointer: its vector becomes a cue on that unit, and the
Life records it by its exact line, so a rebuild carries it. Nothing is stored as an answer: an asked question is pointed
at code, and the agent reads that code. Measured on Django (evidence/team-year/coverage): 23,951 questions for $0.97,
taught in 10 minutes, and the right file came first on 142 of 288 real fix questions against 111 cold (p = 0.0035).

The questions are kept in <workspace>/cover.jsonl, keyed by each unit's text, so a stop resumes and a later cover after
a rebuild writes questions only for code that is new or changed. Keys: ANTHROPIC_API_KEY, or OCM_VERTEX_PROJECT (see
ocm/providers/claude_api.py)."""
import argparse, hashlib, json, os, sys, threading, time

MODEL = "claude-haiku-5-5"
PRICE = (0.10, 0.50)                    # $ per million input / output tokens, list price
PER_UNIT = 0.97 / 23951                 # measured on Django: the estimate shown before any spend
BATCH, CHUNK = 25, 2000
SYS = ("You write questions for a code search benchmark. For each code block, write the one question a developer on this "
       "codebase would ask whose answer is in this block, in the words of a bug report or a how/where/why question, at "
       "most 25 words. Use the names in the code only where a developer would. Return every block's id.")
SCHEMA = {"type": "object", "properties": {"questions": {"type": "array", "items": {"type": "object", "properties": {
    "id": {"type": "integer"}, "question": {"type": "string"}}, "required": ["id", "question"], "additionalProperties": False}}},
    "required": ["questions"], "additionalProperties": False}


def sha(text):
    return hashlib.sha1(text.encode("utf-8", "replace")).hexdigest()


def units(w):
    """The non-test code units, as (unit, path, first line): code scope, not under tests/, not in a file named test*."""
    m, first = w.mem, {}
    for path, spans in w.spans.items():
        for f, _, j in spans:
            first.setdefault(j, (path, f))
    out = []
    for j in range(len(w.code)):
        if not w.code[j] or j not in first:
            continue
        path = first[j][0]
        if "/tests/" in path or path.split("/")[-1].startswith("test"):
            continue
        out.append((j, path, first[j][1]))
    return out


def client():
    import anthropic
    project = os.environ.get("OCM_VERTEX_PROJECT")
    return (anthropic.AnthropicVertex(project_id=project, region=os.environ.get("OCM_VERTEX_REGION", "global"))
            if project else anthropic.Anthropic(max_retries=4))


def write_questions(cl, w, todo, out, cap, threads=8, log=print):
    """Ask Haiku for one question per unit in todo, append them to out, stop at cap dollars. Returns dollars spent."""
    from concurrent.futures import ThreadPoolExecutor
    m, lock, spent = w.mem, threading.Lock(), [0.0]

    def batch(rows):
        if spent[0] >= cap:
            return
        blocks = "\n\n".join(f"<block id=\"{j}\" file=\"{p}\">\n{m.texts[j][:1200]}\n</block>" for j, p, _ in rows)
        r = cl.messages.create(model=MODEL, max_tokens=8000, system=SYS, messages=[{"role": "user", "content": blocks}],
                               output_config={"format": {"type": "json_schema", "schema": SCHEMA}})
        usd = (r.usage.input_tokens * PRICE[0] + r.usage.output_tokens * PRICE[1]) / 1e6
        text = next((b.text for b in r.content if b.type == "text"), "{}")
        try:
            qs = {int(x["id"]): " ".join(str(x["question"]).split()) for x in json.loads(text)["questions"]}
        except (ValueError, KeyError, TypeError):
            qs = {}
        with lock:
            spent[0] += usd
            with open(out, "a") as f:
                for j, p, line in rows:
                    if qs.get(j):
                        f.write(json.dumps({"sha": sha(m.texts[j]), "at": f"{p}:{line}", "question": qs[j]}) + "\n")

    chunks = [todo[i:i + BATCH] for i in range(0, len(todo), BATCH)]
    with ThreadPoolExecutor(threads) as ex:
        for i, _ in enumerate(ex.map(batch, chunks), 1):
            if i % 100 == 0 or i == len(chunks):
                log(f"  {i:,}/{len(chunks):,} requests, ${spent[0]:.3f}")
    return spent[0]


def teach(w, out, log=print):
    """Teach every question in out whose unit is still in the workspace and not yet taught. Returns the count."""
    from .router import lanes as L
    from .router import router as RL
    import numpy as np
    m = w.mem
    by_sha = {}
    for j, p, line in units(w):
        by_sha.setdefault(sha(m.texts[j]), (j, p, line))
    pairs, seen = [], set()
    for row in map(json.loads, open(out)):
        hit = by_sha.get(row["sha"])
        q = " ".join(row["question"].split())
        if hit and q not in m.cue_set and q not in seen:                      # one unit per question: the first written
            seen.add(q); pairs.append((q, hit))
    t0 = time.time()
    for s in range(0, len(pairs), CHUNK):
        part = pairs[s:s + CHUNK]
        m.teach_at([(q, j) for q, (j, _, _) in part])
        for q, (_, p, line) in part:
            w.life.learn(q, json.dumps({"at": f"{p}:{line}", "code": w.line_text(p, line)}, sort_keys=True))
        log(f"  taught {min(s + CHUNK, len(pairs)):,}/{len(pairs):,} ({time.time() - t0:.0f}s)")
    if pairs:
        m.save(); w.life.save()
        w.lanes = L.Lanes(m, np.arange(w.meta["units"]), os.path.join(w.folder, "keyword.db"), RL)
    return len(pairs)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="modeld cover", description=__doc__.split("\n\n")[1])
    ap.add_argument("--workspace"); ap.add_argument("--cap", type=float, default=10.0, help="stop spending at this many dollars")
    ap.add_argument("--yes", action="store_true", help="spend without asking"); ap.add_argument("--threads", type=int, default=8)
    a = ap.parse_args(argv)
    from .cli import find_workspace, OUT
    ws = a.workspace or find_workspace()
    if not ws:
        sys.exit(f"no {OUT} folder here or above: run `modeld build .` first, or pass --workspace")
    os.environ.setdefault("OCM_OFFLINE", "1")
    from .server import Workspace
    w = Workspace(ws)
    out = os.path.join(ws, "cover.jsonl")
    have = {json.loads(l)["sha"] for l in open(out)} if os.path.exists(out) else set()
    todo = [u for u in units(w) if sha(w.mem.texts[u[0]]) not in have]
    todo = list({sha(w.mem.texts[u[0]]): u for u in todo}.values())          # identical code gets one question
    print(f"{len(todo):,} pieces of code to write questions for ({len(have):,} already written)")
    if todo:
        est = len(todo) * PER_UNIT
        print(f"estimated cost: ${est:.2f} of {MODEL} (cap ${a.cap:.2f})")
        if not a.yes:
            if not sys.stdin.isatty():
                sys.exit("pass --yes to spend without a prompt")
            if input("go ahead? [y/N] ").strip().lower() not in ("y", "yes"):
                sys.exit("nothing spent")
        usd = write_questions(client(), w, todo, out, a.cap, a.threads)
        print(f"questions written: ${usd:.3f}")
    n = teach(w, out)
    st = w.mem.law.state()
    print(f"taught {n:,} questions onto code; {len(w.mem.cue_texts):,} taught in all; the learned law "
          f"{'is active' if st.get('active') else 'is not active yet'}")


if __name__ == "__main__":
    main()

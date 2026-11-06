"""Model D on one Agent Retrieval Bench track: see PROTOCOL.md. Resumes. No model calls.

    <modeld 0.5.3 python> -I run.py <release, e.g. v2_trace2code> --label <name> [--work ~/arb-work]

Writes <work>/results/<label>/<release>_details.jsonl in the benchmark's details layout (top_files holds the first 20,
ranked_files the whole list) and prints the means. score.py adds BCY and writes the report here."""
import argparse, json, os, shutil, sys, time

ap = argparse.ArgumentParser()
ap.add_argument("release"); ap.add_argument("--label", default="modeld-0.5.3")
ap.add_argument("--work", default=os.path.expanduser("~/arb-work")); ap.add_argument("--limit", type=int, default=0)
a = ap.parse_args()
os.environ.setdefault("OCM_OFFLINE", "1"); os.environ.setdefault("HF_HUB_OFFLINE", "1")
sys.path.insert(0, os.path.join(a.work, "agent-retrieval-bench", "src"))
import ocm  # noqa: E402
from ocm.build import build  # noqa: E402
from ocm.prove import items_of  # noqa: E402
from ocm.server import Workspace  # noqa: E402
from agent_retrieval_bench import baseline as B  # noqa: E402

assert ocm.__version__ == "0.5.3", ocm.__version__
KEEP = ("Recall@5", "Recall@10", "Recall@20", "MRR", "Precision@5", "F0.5@5")
data = os.path.join(a.work, "data")
samples = [json.loads(l) for l in open(os.path.join(data, "benchmark", a.release, "samples.jsonl"))]
manifest = {(r["repo"], r["base_commit"]): r for r in map(json.loads, open(os.path.join(data, "corpus", a.release, "corpus_manifest.jsonl")))}
out_dir = os.path.join(a.work, "results", a.label); os.makedirs(out_dir, exist_ok=True)
out = os.path.join(out_dir, f"{a.release}_details.jsonl")
done = {json.loads(l)["sample_id"] for l in open(out)} if os.path.exists(out) else set()
tmp = os.path.join(a.work, "tmp"); os.makedirs(os.path.join(a.work, "cache"), exist_ok=True)


def strings(v):
    if isinstance(v, str):
        return [v] if v.strip() else []
    if isinstance(v, dict):
        return [s for x in v.values() for s in strings(x)]
    if isinstance(v, (list, tuple)):
        return [s for x in v for s in strings(x)]
    return []


def render(query):
    """All strings in the query object, shortest first, joined with blank lines."""
    return "\n\n".join(sorted(strings(query), key=len))


def write_snapshot(repo, commit, snap):
    """The kind=file rows of the released corpus at this commit."""
    shutil.rmtree(snap, ignore_errors=True); os.makedirs(snap)
    path = manifest[(repo, commit)]["chunks_path"]
    n = 0
    for row in map(json.loads, open(os.path.join(a.work, path))):
        if row.get("kind") != "file":
            continue
        rel = os.path.normpath(row["path"])
        if rel.startswith("..") or os.path.isabs(rel):              # the corpus is data: nothing is written outside
            continue
        p = os.path.join(snap, rel); os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, "w", encoding="utf-8").write(row["text"]); n += 1
    return n


def ranking(w, q):
    """(files in order, the first readout's spans, the first readout's tokens)."""
    text = w.handle("ask", {"question": q, "scope": "code"})
    first = items_of(w, text)
    files = [f for f, _, _ in first]
    for _ in range(12):
        more = w.handle("next", {"question": q, "scope": "code"})
        if more.startswith("NO MORE READOUTS"):
            break
        files += [f for f, _, _ in items_of(w, more)]
    m = w.mem
    for j in m._rank(q, top=len(m.texts))[0]:
        if m.src[j] >= 0:
            p = m.sources[m.src[j]]["path"]
            files.append(p.split("/", 1)[1] if "/" in p else p)
    return list(dict.fromkeys(files)), first, len(text) // 4


todo = sorted((s for s in samples if s["id"] not in done), key=lambda s: (s["repo"], s["base_commit"]))
todo = todo[:a.limit] if a.limit else todo
print(f"{a.release}: {len(samples)} samples, {len(done)} done, {len(todo)} to run; tests trail {os.environ.get('OCM_TESTS_TRAIL', 'on')}", flush=True)
snap, ws, current, w = os.path.join(tmp, "repo"), os.path.join(tmp, "ws"), None, None
t_all = time.time()
for n, s in enumerate(todo, 1):
    key = (s["repo"], s["base_commit"]); t0 = time.time(); built = 0.0
    if key != current:
        write_snapshot(*key, snap); shutil.rmtree(ws, ignore_errors=True)
        build([snap], ws, log=lambda *x: None, cache=os.path.join(a.work, "cache", s["repo"].replace("/", "__") + ".sqlite"))
        w, current, built = Workspace(ws), key, time.time() - t0
    q = render(s["query"]); t1 = time.time()
    files, first, tokens = ranking(w, q)
    gold = B.target_gold_files(s)
    metrics = B.sample_metrics(gold, [{"path": f, "text": ""} for f in files], hard_negative_files=B.hard_negative_files(s))
    row = {"sample_id": s["id"], "task_type": s["task_type"], "repo": s["repo"], "base_commit": s["base_commit"],
           "candidate_filter": "all_files", "ranker": a.label, "gold_files": gold, "gold_spans": B.gold_spans(s),
           "gold_blocks": B.gold_blocks(s), "hard_negative_files": B.hard_negative_files(s), "query_provenance": B.query_provenance(s),
           "gold_ranks": {g: files.index(g) + 1 if g in files else None for g in gold}, "top_files": files[:20], "ranked_files": files,
           "first_readout": first, "first_readout_tokens": tokens, "gold_in_first_readout": bool(set(gold) & {f for f, _, _ in first}),
           "metrics": {k: metrics[k] for k in KEEP}, "build_s": round(built, 1), "ask_s": round(time.time() - t1, 2)}
    with open(out, "a") as f:
        f.write(json.dumps(row) + "\n")
    print(f"{n:>4}/{len(todo)} {s['repo']:<26} MRR {metrics['MRR']:.3f} R@5 {metrics['Recall@5']:.2f} first readout {tokens:>5} tok  build {built:6.1f}s  total {time.time() - t_all:6.0f}s", flush=True)
shutil.rmtree(ws, ignore_errors=True); shutil.rmtree(snap, ignore_errors=True)
rows = [json.loads(l) for l in open(out)]
mean = lambda k: sum(r["metrics"][k] for r in rows) / len(rows)
print(f"{a.release} n={len(rows)}  MRR {mean('MRR'):.4f}  R@5 {mean('Recall@5'):.4f}  R@10 {mean('Recall@10'):.4f}  R@20 {mean('Recall@20'):.4f}  "
      f"gold in first readout {sum(r['gold_in_first_readout'] for r in rows) / len(rows):.3f}  first readout tokens mean {sum(r['first_readout_tokens'] for r in rows) / len(rows):.0f}")

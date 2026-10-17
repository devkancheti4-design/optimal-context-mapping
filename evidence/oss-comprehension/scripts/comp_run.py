"""PROTOCOL_OSS_COMPREHENSION runner: one arm over atproto's answered discussions, oldest first.

    python comp_run.py md|alone comp_questions.json <server url> <out.jsonl> --cap USD [--shard i/n] [--limit N]

The product loop (ocm.hybrid.run) and the alone loop are team_year.py's, unchanged; only the questions differ."""
import argparse, glob, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import team_year as T  # noqa: E402  (reads ../.env; the key is never printed)

ap = argparse.ArgumentParser(); ap.add_argument("arm", choices=["md", "alone"]); ap.add_argument("questions"); ap.add_argument("url")
ap.add_argument("out"); ap.add_argument("--cap", type=float, required=True); ap.add_argument("--shard"); ap.add_argument("--limit", type=int)
a = ap.parse_args()
items = json.load(open(a.questions))[: a.limit or None]
if a.shard:
    i, n = map(int, a.shard.split("/")); items = [x for x in items if x["k"] % n == i]
prefix = a.out.rsplit("_s", 1)[0] if a.shard else a.out.rsplit(".", 1)[0]
done = {json.loads(l)["k"] for f in glob.glob(prefix + "*.jsonl") for l in open(f)}
spent0 = sum(json.loads(l)["usd"] for f in glob.glob(prefix + "*.jsonl") for l in open(f))
prov = T.Claude(); meter = T.Meter(prov.client)
for x in items:
    if x["k"] in done: continue
    if spent0 + meter.usd >= a.cap:
        print(f"stopped at the cap: ${spent0 + meter.usd:.4f} of ${a.cap:.2f}"); break
    u0, r0 = meter.usd, meter.requests; ws = T.SeenWS(a.url)
    try:
        if a.arm == "md":
            res = T.md_run(x["question"], prov, ws); path, answer, at = res["path"], res["answer"], res["at"]
        else:
            answer, at, _ = T.alone(prov, x["question"], ws); path = "alone"
    except Exception as e:
        print(f"k {x['k']}: {type(e).__name__}: {str(e)[:200]}", flush=True); continue
    row = {"k": x["k"], "date": x["date"], "arm": a.arm, "path": path, "answer": answer, "at": at,
           "requests": meter.requests - r0, "usd": round(meter.usd - u0, 6), "led_by_taught": bool(ws.served and ws.served[0].startswith(T.TAUGHT))}
    with open(a.out, "a") as f: f.write(json.dumps(row) + "\n")
    print(f"k {x['k']} {x['date']} {path:<5} req {row['requests']:>2} ${row['usd']:.4f} total ${spent0 + meter.usd:.3f}", flush=True)

"""A fresh live check of Model D's hybrid on the Claude API, with a spending cap. Run it when you are ready to spend.

    uv tool install "model-d[claude]"           (or: pip install "model-d[claude]")
    export ANTHROPIC_API_KEY=...                 (read from the environment, never printed)
    modeld build <repo> && modeld serve <repo>/modeld-out --port 7700 &
    python scripts/live_api_test.py questions.json --url http://127.0.0.1:7700 --cap 2.00 --out live.jsonl

questions.json is ["question", ...] or [{"question": "...", "again": "the same question in other words"}, ...].
- Pass 1 asks each question. A new question is explored by the teacher (Claude Sonnet 5.5 by default), and the line
  it cites is taught.
- Pass 2 asks each "again" wording. A learned question should come back as one read by the reader (Claude Haiku 5.5).

Every request's tokens come from the API's usage fields, priced with --prices (per million tokens: input, cache write,
cache read, output). The default is the table the value program used; check it against current list prices. The run
stops before a question once the spend reaches --cap."""
import argparse, json, os, sys, time

PRICES = {"sonnet": (2.00, 2.50, 0.20, 10.00), "haiku": (0.10, 0.125, 0.01, 0.50)}


class Meter:
    """Wraps client.messages.create and adds up each request's usage and price."""
    def __init__(self, client, prices):
        self.prices, self.requests, self.usd, self._create = prices, 0, 0.0, client.messages.create
        client.messages.create = self.create

    def create(self, **kw):
        r = self._create(**kw)
        u = r.usage
        p = self.prices["haiku" if "haiku" in kw.get("model", "") else "sonnet"]
        tokens = (u.input_tokens, getattr(u, "cache_creation_input_tokens", 0) or 0,
                  getattr(u, "cache_read_input_tokens", 0) or 0, u.output_tokens)
        self.requests += 1
        self.usd += sum(t * q for t, q in zip(tokens, p)) / 1e6
        return r


def main(argv=None):
    ap = argparse.ArgumentParser(prog="live_api_test")
    ap.add_argument("questions"); ap.add_argument("--url", default=os.environ.get("OCM_URL", "http://127.0.0.1:7700"))
    ap.add_argument("--cap", type=float, default=2.00); ap.add_argument("--out", default="live.jsonl")
    ap.add_argument("--prices", help='JSON, e.g. {"sonnet": [2, 2.5, 0.2, 10], "haiku": [0.1, 0.125, 0.01, 0.5]}')
    a = ap.parse_args(argv)
    if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("OCM_VERTEX_PROJECT")):
        sys.exit("set ANTHROPIC_API_KEY (or OCM_VERTEX_PROJECT) first")
    from ocm.hybrid import run, provider, Workspace
    items = [q if isinstance(q, dict) else {"question": q} for q in json.load(open(a.questions))]
    prov = provider("claude"); meter = Meter(prov.client, json.loads(a.prices) if a.prices else PRICES)
    ws = Workspace(a.url.rstrip("/"))
    passes = [("first", [it["question"] for it in items]), ("again", [it["again"] for it in items if it.get("again")])]
    summary = {}
    with open(a.out, "a") as f:
        for name, qs in passes:
            s = summary.setdefault(name, {"questions": 0, "reads": 0, "requests": 0, "usd": 0.0})
            for q in qs:
                if meter.usd >= a.cap:
                    print(f"stopped: the spend reached the cap (${meter.usd:.4f} of ${a.cap:.2f})"); break
                r0, u0, t0 = meter.requests, meter.usd, time.time()
                out = run(q, prov, ws)
                row = {"pass": name, "question": q, **out, "requests": meter.requests - r0, "usd": round(meter.usd - u0, 6),
                       "seconds": round(time.time() - t0, 1)}
                f.write(json.dumps(row) + "\n"); f.flush()
                s["questions"] += 1; s["reads"] += out["path"] == "read"; s["requests"] += row["requests"]; s["usd"] += row["usd"]
                print(f"[{name}] {out['path']:<5} {row['requests']:>2} req  ${row['usd']:.4f}  {q[:70]}")
    for name, s in summary.items():
        if s["questions"]:
            print(f"{name}: {s['questions']} questions, {s['reads']} answered by one read, {s['requests']} requests, "
                  f"${s['usd']:.4f} (${s['usd'] / s['questions']:.4f} per question)")
    print(f"total spend: ${meter.usd:.4f}; rows in {a.out}")


if __name__ == "__main__":
    main()

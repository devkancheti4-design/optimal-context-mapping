"""PROTOCOL_TEAM_YEAR runner: one arm over Django's 2022 fixes, in commit order.

    python team_year.py md|alone <window_2022.json> <server url> <out.jsonl> --cap USD [--limit N]

md    = the product: ocm.hybrid.run with the Claude provider (Haiku strict read, Sonnet explore and teach), against a
        workspace server that learns from the arm's own explorations, sequentially.
alone = Sonnet with the same tools on a never-taught server; the product's TEACH prompt minus its readout sentence; the
        same loop as the product's teacher, with the question only.
Spend is metered from each response's usage at list price. A stop resumes. The key is read from ../.env and never printed."""
import argparse, json, os, re, sys, threading

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.expanduser("~/optimal-context-mapping"))
for line in open(os.path.join(ROOT, ".env")):
    if line.startswith("ANTHROPIC_API_KEY=") and line.split("=", 1)[1].strip():
        os.environ["ANTHROPIC_API_KEY"] = line.split("=", 1)[1].strip()
from ocm import hybrid  # noqa: E402
from ocm.hybrid import run as md_run, Workspace, TOOLS, TEACH, MAX_CALLS  # noqa: E402
from ocm.loop import TAUGHT  # noqa: E402
from ocm.providers.claude_api import Claude  # noqa: E402

PRICE = {"sonnet": (2.00, 10.00), "haiku": (0.10, 0.50)}
ALONE_SYS = TEACH.replace(" The code the team's workspace ranked for the question comes with it; if it holds the answer, "
                          "submit from it without searching.", "")
assert ALONE_SYS != TEACH, "the TEACH prompt changed; the alone prompt is no longer derived from it"


class Meter:
    def __init__(self, client):
        self.lock, self.usd, self.requests, self.inp, self.out = threading.Lock(), 0.0, 0, 0, 0
        self._create, client.messages.create = client.messages.create, self.create

    def create(self, **kw):
        r = self._create(**kw)
        p = PRICE["haiku" if "haiku" in kw.get("model", "") else "sonnet"]
        with self.lock:
            self.requests += 1; self.inp += r.usage.input_tokens; self.out += r.usage.output_tokens
            self.usd += (r.usage.input_tokens * p[0] + r.usage.output_tokens * p[1]) / 1e6
        return r


class SeenWS(Workspace):
    """The product's HTTP workspace, remembering the readouts it served for this question."""
    def __init__(self, url):
        super().__init__(url); self.served = []

    def call(self, path, **kw):
        out = super().call(path, **kw)
        if path in ("ask", "next"):
            self.served.append(out)
        return out


def first_file(text):
    """The file of the readout's first item: '1. [path:line]'."""
    m = re.search(r"^\s*1\.\s*\[([^\]]+?):\d+\]", text, re.M)
    return m.group(1) if m else None


def right(path, gold):
    if not path:
        return False
    p = path.split(":", 1)[0].strip().lstrip("./")
    p = p.split("/", 1)[1] if p.startswith("django/django/") else p          # the workspace root name comes first
    return any(p == g or p.endswith("/" + g) or g.endswith("/" + p) for g in gold)


def alone(prov, question, ws):
    """The product teacher's loop (ocm/providers/claude_api.py), with the alone prompt and the question only."""
    spec = [{"name": t["name"], "description": t["description"], "input_schema": t["parameters"]} for t in TOOLS]
    messages = [{"role": "user", "content": f"Question: {question}"}]
    calls = n = 0
    while n < MAX_CALLS + 10:
        r = prov.client.messages.create(model=prov.teacher, max_tokens=8000, system=ALONE_SYS, tools=spec, messages=messages)
        n += 1
        if r.stop_reason == "pause_turn":
            messages.append({"role": "assistant", "content": r.content}); continue
        uses = [b for b in r.content if b.type == "tool_use"]
        if not uses:
            return "".join(b.text for b in r.content if b.type == "text").strip(), None, n
        messages.append({"role": "assistant", "content": r.content})
        results = []
        for u in uses:
            if u.name == "submit":
                return u.input.get("answer", ""), u.input.get("at") or None, n
            calls += 1
            out = ws.tool(u.name, u.input) if calls <= MAX_CALLS else "Tool limit reached: call submit now."
            results.append({"type": "tool_result", "tool_use_id": u.id, "content": out})
        messages.append({"role": "user", "content": results})
    return "", None, n


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("arm", choices=["md", "alone"]); ap.add_argument("window")
    ap.add_argument("url"); ap.add_argument("out"); ap.add_argument("--cap", type=float, required=True)
    ap.add_argument("--limit", type=int); ap.add_argument("--keep", required=True, help="kept fix ids (json list)")
    ap.add_argument("--shard", help="i/n: only k with k %% n == i (the alone arm; it never learns)")
    a = ap.parse_args()
    keep = set(json.load(open(a.keep)))
    items = [x for x in json.load(open(a.window)) if x["k"] in keep][: a.limit or None]
    prov = Claude(); meter = Meter(prov.client)
    if a.shard:
        i, n = map(int, a.shard.split("/")); items = [x for x in items if x["k"] % n == i]
    import glob
    prefix = a.out.rsplit("_s", 1)[0] if a.shard else a.out.rsplit(".", 1)[0]
    done = {json.loads(l)["k"] for f in glob.glob(prefix + "*.jsonl") for l in open(f)}
    spent0 = sum(json.loads(l)["usd"] for f in glob.glob(prefix + "*.jsonl") for l in open(f))
    for x in items:
        if x["k"] in done:
            continue
        if spent0 + meter.usd >= a.cap:
            print(f"stopped at the cap: ${spent0 + meter.usd:.4f} of ${a.cap:.2f}"); break
        q = f"Where is the code behind this change: {x['raw']}"
        u0, r0 = meter.usd, meter.requests
        ws = SeenWS(a.url)
        try:
            if a.arm == "md":
                res = md_run(q, prov, ws); path, answer, at = res["path"], res["answer"], res["at"]
                where = at if path == "teach" else first_file(ws.served[0]) if ws.served else None
            else:
                answer, at, _ = alone(prov, q, ws); path, where = "alone", at
        except Exception as e:                                             # an API or server failure: record, go on
            print(f"k {x['k']}: {type(e).__name__}: {str(e)[:200]}", flush=True); continue
        row = {"k": x["k"], "date": x["date"], "arm": a.arm, "path": path, "right": right(where, x["gold"]),
               "where": where, "gold": x["gold"], "answer": answer[:600], "requests": meter.requests - r0,
               "usd": round(meter.usd - u0, 6), "led_by_taught": bool(ws.served and ws.served[0].startswith(TAUGHT))}
        with open(a.out, "a") as f:
            f.write(json.dumps(row) + "\n")
        print(f"k {x['k']} {x['date']} {path:<5} right {row['right']!s:<5} req {row['requests']:>2} ${row['usd']:.4f} "
              f"total ${spent0 + meter.usd:.3f}", flush=True)


if __name__ == "__main__":
    main()

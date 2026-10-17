"""Claude + Graphify, end to end, on the 288 Django 2022 fixes (PROTOCOL_VS_GRAPHIFY, part B).

    python e2e_graphify.py <graph.json> <tools server url> <out.jsonl> --cap USD [--shard i/n] [--limit N]

Sonnet 5.5 with Graphify's own MCP tools (as its server lists them) plus the alone arm's search, read_file, list_files
and submit; the alone arm's system prompt (PROTOCOL_TEAM_YEAR) followed by the CLAUDE.md block Graphify installs,
verbatim, and one sentence naming its commands as these tools. The alone arm's loop, the same tool limit, the same
scoring. Spend is metered at list price; a stop resumes."""
import argparse, glob, json, os, sys
sys.path.insert(0, os.path.expanduser("~/neos/outreach/team-year/scripts"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import team_year as T  # noqa: E402  (reads the key from team-year/.env, never printed)
from gf_mcp import Graphify, GF_PY  # noqa: E402

BLOCK = open(os.path.join(os.path.dirname(os.path.dirname(GF_PY)), "lib/python3.12/site-packages/graphify/always_on/claude-md.md")).read().strip()
MAP = ("Here graphify runs as tools, not a shell: `graphify query` is query_graph, `graphify path` is shortest_path and "
       "`graphify explain` is get_node; graphify-out/ is not readable with read_file.")
SYS = T.ALONE_SYS + "\n\n" + BLOCK + "\n\n" + MAP


def run(prov, question, ws, G, gspec, gnames, stats):
    spec = [{"name": t["name"], "description": t["description"], "input_schema": t["parameters"]} for t in T.TOOLS] + gspec
    messages = [{"role": "user", "content": f"Question: {question}"}]
    calls = n = 0
    while n < T.MAX_CALLS + 10:
        r = prov.client.messages.create(model=prov.teacher, max_tokens=8000, system=SYS, tools=spec, messages=messages)
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
            calls += 1; stats[u.name] = stats.get(u.name, 0) + 1
            if calls > T.MAX_CALLS:
                out = "Tool limit reached: call submit now."
            elif u.name in gnames:
                try:
                    out = G.call(u.name, u.input)
                except Exception as e:
                    out = f"error: {e}"
                stats["graphify_chars"] = stats.get("graphify_chars", 0) + len(out)
            else:
                out = ws.tool(u.name, u.input)
            results.append({"type": "tool_result", "tool_use_id": u.id, "content": out or "(empty)"})
        messages.append({"role": "user", "content": results})
    return "", None


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("graph"); ap.add_argument("url"); ap.add_argument("out")
    ap.add_argument("--cap", type=float, required=True); ap.add_argument("--shard"); ap.add_argument("--limit", type=int)
    ap.add_argument("--port", type=int, default=8093)
    a = ap.parse_args()
    items = json.load(open(os.path.expanduser("~/neos/outreach/vs-graphify/questions/django2022.json")))[: a.limit or None]
    if a.shard:
        i, n = map(int, a.shard.split("/")); items = [x for x in items if x["id"] % n == i]
    prefix = a.out.rsplit("_s", 1)[0] if a.shard else a.out.rsplit(".", 1)[0]
    done = {json.loads(l)["k"] for f in glob.glob(prefix + "*.jsonl") for l in open(f)}
    spent0 = sum(json.loads(l)["usd"] for f in glob.glob(prefix + "*.jsonl") for l in open(f))
    prov = T.Claude(); meter = T.Meter(prov.client)
    G = Graphify(a.graph, a.port, log=a.out + ".serve.log")
    gt = G.tools(); gnames = {t["name"] for t in gt}
    gspec = [{"name": t["name"], "description": t.get("description", ""), "input_schema": t["inputSchema"]} for t in gt]
    try:
        for x in items:
            if x["id"] in done:
                continue
            if spent0 + meter.usd >= a.cap:
                print(f"stopped at the cap: ${spent0 + meter.usd:.4f} of ${a.cap:.2f}"); break
            q = x["queries"]["q"]; u0, r0 = meter.usd, meter.requests; stats = {}
            try:
                answer, at = run(prov, q, T.SeenWS(a.url), G, gspec, gnames, stats)
            except Exception as e:
                print(f"k {x['id']}: {type(e).__name__}: {str(e)[:200]}", flush=True); continue
            row = {"k": x["id"], "date": x["date"], "arm": "graphify", "path": "graphify", "right": T.right(at, x["gold"]),
                   "where": at, "gold": x["gold"], "answer": answer[:600], "requests": meter.requests - r0,
                   "usd": round(meter.usd - u0, 6), "tools": stats}
            with open(a.out, "a") as f:
                f.write(json.dumps(row) + "\n")
            print(f"k {x['id']} {x['date']} right {row['right']!s:<5} req {row['requests']:>2} ${row['usd']:.4f} "
                  f"total ${spent0 + meter.usd:.3f} tools {stats}", flush=True)
    finally:
        G.close()


if __name__ == "__main__":
    main()

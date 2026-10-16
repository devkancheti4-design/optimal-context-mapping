"""Arms C (an exploring reviewer, alone) and D (the same reviewer with Model D's readout), per PROTOCOL_SWR_AGENTIC.md.

    python run_agent_review.py C|D <dataset.jsonl> <pilot_set.json> <contexts.jsonl> <repos dir> <out.jsonl>
                               --cap USD [--limit N]

Tools are Model D's workspace tools, reimplemented line for line from ocm/server.py (search / read / list) over the file
list Model D indexes (ocm.units.files), on the repository checked out at the PR's base_commit. The loop follows the
product's teacher loop (ocm/providers/claude_api.py): up to 15 tool calls, then "Tool limit reached". A stop resumes:
PRs already in the output are skipped. The key is read from ../.env and never printed."""
import argparse, json, os, re, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.expanduser("~/optimal-context-mapping"))
from run_review import TEMPLATE, create_prinfo_prompt, key_from_env_file  # noqa: E402
from ocm.units import files as list_files  # noqa: E402

MODEL, MAX_CALLS = "claude-sonnet-5-5", 15
PRICE = {"in": 2.00, "write": 2.50, "read": 0.20, "out": 10.00}     # $ per million, Sonnet, live_api_test.py

SYSTEM = ("You are a senior engineer reviewing a pull request on this codebase. You can explore the repository as it was "
          "before the pull request: search (a case-insensitive regular expression over every line), read_file (lines of "
          "one file) and list_files reach it. Explore only as much as the review needs. When you are done, call "
          "submit_review with your complete review. At most 15 tool calls.")
SYSTEM_D = SYSTEM + (" The code the team's workspace ranked for this pull request comes with it; if it holds what the "
                     "review needs, review from it without searching.")
TOOLS = [
    {"name": "search", "description": "case-insensitive regular-expression search over every line of every file",
     "input_schema": {"type": "object", "properties": {"pattern": {"type": "string"}}, "required": ["pattern"]}},
    {"name": "read_file", "description": "read lines of one file (at most 200 lines per call)",
     "input_schema": {"type": "object", "properties": {"file": {"type": "string"}, "start_line": {"type": "integer"},
                                                       "num_lines": {"type": "integer"}}, "required": ["file", "start_line"]}},
    {"name": "list_files", "description": "list the files under a folder prefix ('' for all)",
     "input_schema": {"type": "object", "properties": {"prefix": {"type": "string"}}}},
    {"name": "submit_review", "description": "submit the complete review of the pull request",
     "input_schema": {"type": "object", "properties": {"review": {"type": "string"}}, "required": ["review"]}},
]


class Tools:
    """search / read / list exactly as ocm/server.py serves them."""
    def __init__(self, repo):
        name = os.path.basename(os.path.abspath(repo).rstrip("/"))
        self.files = {rel: path for _, rel, path in list_files({name: os.path.abspath(repo)})}

    def search(self, pattern):
        try:
            rx = re.compile(str(pattern), re.I)
        except re.error as e:
            return f"invalid regular expression: {e}"
        hits, n = [], 0
        for rel, p in self.files.items():
            try:
                lines = open(p, encoding="utf-8").read().split("\n")
            except (UnicodeDecodeError, OSError):
                continue
            for i, line in enumerate(lines, 1):
                if rx.search(line):
                    n += 1
                    if len(hits) < 40:
                        hits.append(f"{rel}:{i}: {line.strip()[:200]}")
        return (f"{n} matching lines" + (", first 40:" if n > 40 else ":") + "\n" + "\n".join(hits)) if n else "0 matching lines"

    def read(self, file, start=1, num=80):
        rel = str(file).strip().lstrip("./")
        if rel not in self.files:
            return f"no such file in the workspace: {rel}"
        lines = open(self.files[rel], encoding="utf-8").read().split("\n")
        s = max(1, int(start or 1)); e = min(len(lines), s + max(1, min(200, int(num or 80))) - 1)
        return "\n".join(f"{i}: {lines[i - 1]}" for i in range(s, e + 1)) + f"\n({len(lines)} lines in the file)"

    def list(self, prefix=""):
        p = str(prefix or "").strip().lstrip("./"); fs = [f for f in self.files if f.startswith(p)]
        return f"{len(fs)} files" + (", first 300:" if len(fs) > 300 else ":") + "\n" + "\n".join(fs[:300])

    def run(self, name, args):
        if name == "search": return self.search(args.get("pattern", ""))
        if name == "read_file": return self.read(args.get("file", ""), args.get("start_line", 1), args.get("num_lines", 80))
        if name == "list_files": return self.list(args.get("prefix", ""))
        return f"unknown tool {name}"


def checkout(repo, sha):
    for attempt in range(4):
        if subprocess.run(["git", "-C", repo, "checkout", "-q", "-f", sha], capture_output=True).returncode == 0:
            subprocess.run(["git", "-C", repo, "clean", "-q", "-fdx"], capture_output=True); return
        subprocess.run(["git", "-C", repo, "fetch", "-q", "origin", sha], capture_output=True); time.sleep(10 * (attempt + 1))
    raise SystemExit(f"could not check out {sha} in {repo}")


def cost(u):
    return (u.input_tokens * PRICE["in"] + (u.cache_creation_input_tokens or 0) * PRICE["write"]
            + (u.cache_read_input_tokens or 0) * PRICE["read"] + u.output_tokens * PRICE["out"]) / 1e6


def review(client, arm, item, ctx, tools):
    user = TEMPLATE.format(prinfo=create_prinfo_prompt(item))
    if arm == "D":
        user += f"\nThe code the team's workspace ranked for this pull request:\n{ctx[item['instance_id']]['readout']}\n"
    messages = [{"role": "user", "content": user}]
    st = {"requests": 0, "tool_calls": 0, "input_tokens": 0, "cache_write": 0, "cache_read": 0, "output_tokens": 0, "usd": 0.0}
    calls, text, how = 0, "", "no_submit"
    while st["requests"] < MAX_CALLS + 10:
        r = client.messages.create(model=MODEL, max_tokens=8000, system=SYSTEM_D if arm == "D" else SYSTEM, tools=TOOLS,
                                   messages=messages, cache_control={"type": "ephemeral"})
        st["requests"] += 1; u = r.usage
        st["input_tokens"] += u.input_tokens; st["cache_write"] += u.cache_creation_input_tokens or 0
        st["cache_read"] += u.cache_read_input_tokens or 0; st["output_tokens"] += u.output_tokens; st["usd"] += cost(u)
        if r.stop_reason == "pause_turn":
            messages.append({"role": "assistant", "content": r.content}); continue
        uses = [b for b in r.content if b.type == "tool_use"]
        if not uses:
            text = "".join(b.text for b in r.content if b.type == "text").strip(); how = "text"; break
        messages.append({"role": "assistant", "content": r.content})
        sub = next((b for b in uses if b.name == "submit_review"), None)
        if sub is not None:
            text = str(sub.input.get("review", "")); how = "submit"; break
        results = []
        for b in uses:
            calls += 1
            out = tools.run(b.name, b.input) if calls <= MAX_CALLS else "Tool limit reached: call submit_review now."
            results.append({"type": "tool_result", "tool_use_id": b.id, "content": out})
        messages.append({"role": "user", "content": results})
    st["tool_calls"] = min(calls, MAX_CALLS); st["tool_calls_requested"] = calls
    return text, how, st


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("arm", choices=["C", "D"]); ap.add_argument("dataset"); ap.add_argument("pilot"); ap.add_argument("contexts")
    ap.add_argument("repos"); ap.add_argument("out"); ap.add_argument("--cap", type=float, required=True)
    ap.add_argument("--limit", type=int)
    a = ap.parse_args()
    import anthropic
    rows = {}
    for line in open(a.dataset):
        r = json.loads(line); rows[r["instance_id"]] = r
    ids = [p["instance_id"] for p in json.load(open(a.pilot))["instances"]]
    ctx = {json.loads(l)["instance_id"]: json.loads(l) for l in open(a.contexts)}
    if a.arm == "D":
        ids = [i for i in ids if i in ctx]
    if a.limit:
        ids = ids[:a.limit]
    client = anthropic.Anthropic(api_key=key_from_env_file(), max_retries=4)
    done = {json.loads(l)["instance_id"] for l in open(a.out)} if os.path.exists(a.out) else set()
    spent = sum(json.loads(l)["usd"] for l in open(a.out)) if os.path.exists(a.out) else 0.0
    for i in ids:
        if i in done:
            continue
        if spent >= a.cap:
            print(f"stopped at the cap: ${spent:.4f} of ${a.cap:.2f}"); break
        item = rows[i]; repo = os.path.join(a.repos, item["repo"].split("/")[1])
        checkout(repo, item["base_commit"])
        try:
            text, how, st = review(client, a.arm, item, ctx, Tools(repo))
        except anthropic.APIError as e:
            print(f"{i}: API error {type(e).__name__}: {str(e)[:200]}"); continue
        spent += st["usd"]
        with open(a.out, "a") as f:
            f.write(json.dumps({"instance_id": i, "arm": a.arm, "model": MODEL, "review": text, "response": text,
                                "ended_by": how, **st, "usd": round(st["usd"], 6)}) + "\n")
        print(f"{i:<34} req {st['requests']:>2} tools {st['tool_calls']:>2}  in {st['input_tokens']:>6,} cw {st['cache_write']:>6,} "
              f"cr {st['cache_read']:>7,} out {st['output_tokens']:>5,}  ${st['usd']:.4f}  total ${spent:.4f}  [{how}]", flush=True)


if __name__ == "__main__":
    main()

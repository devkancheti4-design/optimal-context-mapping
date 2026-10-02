"""Measure what agent sessions cost, from Claude Code's own transcripts: the pilot's before-and-after numbers.

    python -m ocm measure <transcripts folder> [--since 2026-10-01] [--until 2026-10-14] [--json]
    python -m ocm measure compare <folder A> <folder B> [--since ...] [--until ...]

Claude Code keeps one transcript per session (JSON lines) under ~/.claude/projects/<project>/ (subagents in a subfolder).
For every session: model requests (distinct assistant messages), input tokens billed (new + cache writes + cache reads),
the same cache-weighted (new 1, cache writes 1.25, cache reads 0.1, as the API prices them), output tokens, tool calls,
and how many of those went to the workspace (tools named workspace_*). compare prints both folders and their ratios.
Nothing is sent anywhere; the transcripts are only read."""
import argparse, glob, json, os
from datetime import datetime, timezone


def session(path, since=None, until=None):
    msgs, tools, ws, first = {}, 0, 0, None
    for line in open(path, encoding="utf-8", errors="replace"):
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            continue
        ts = d.get("timestamp")
        if ts:
            t = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            first = first or t
            if (since and t < since) or (until and t > until):
                continue
        if d.get("type") != "assistant":
            continue
        m = d.get("message") or {}
        if m.get("usage"):
            msgs[m.get("id")] = m["usage"]
        for b in m.get("content") or []:
            if isinstance(b, dict) and b.get("type") == "tool_use":
                tools += 1; ws += "workspace_" in str(b.get("name", ""))
    u = list(msgs.values())
    raw = sum(x.get("input_tokens", 0) + x.get("cache_creation_input_tokens", 0) + x.get("cache_read_input_tokens", 0) for x in u)
    cw = sum(x.get("input_tokens", 0) + 1.25 * x.get("cache_creation_input_tokens", 0) + 0.1 * x.get("cache_read_input_tokens", 0) for x in u)
    return {"requests": len(u), "input billed": raw, "input, cache-weighted": round(cw), "output": sum(x.get("output_tokens", 0) for x in u),
            "tool calls": tools, "workspace calls": ws, "started": first.isoformat() if first else None}


def folder(path, since=None, until=None):
    S = [s for s in (session(p, since, until) for p in sorted(glob.glob(os.path.join(path, "**", "*.jsonl"), recursive=True))) if s["requests"]]
    tot = {k: sum(s[k] for s in S) for k in ("requests", "input billed", "input, cache-weighted", "output", "tool calls", "workspace calls")}
    tot["sessions"] = len(S)
    if S:
        tot["requests per session"] = round(tot["requests"] / len(S), 2)
        tot["cache-weighted input per session"] = round(tot["input, cache-weighted"] / len(S))
    return tot


def day(s):
    return datetime.fromisoformat(s).replace(tzinfo=timezone.utc) if s else None


def main(argv=None):
    argv = list(argv if argv is not None else [])
    cmp = bool(argv) and argv[0] == "compare"
    ap = argparse.ArgumentParser(prog="ocm measure" + (" compare" if cmp else ""))
    ap.add_argument("folders", nargs=2 if cmp else 1); ap.add_argument("--since"); ap.add_argument("--until"); ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv[1:] if cmp else argv)
    R = {f: folder(f, day(a.since), day(a.until)) for f in a.folders}
    if a.json:
        print(json.dumps(R, indent=1)); return
    for f, t in R.items():
        print(f"{f}\n  " + "\n  ".join(f"{k}: {v:,}" if isinstance(v, (int, float)) else f"{k}: {v}" for k, v in t.items()))
    if cmp:
        A, B = R[a.folders[0]], R[a.folders[1]]
        for k in ("requests per session", "cache-weighted input per session"):
            if A.get(k) and B.get(k):
                print(f"A / B {k}: {A[k] / B[k]:.2f}x")

"""PROTOCOL_VALUE5 runner: write the fix, scored by Django's own tests.  python run5.py <run | score>"""
import json, os, re, shutil, subprocess, sys, threading
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import harness as Hn
import run as R1
from harness import V, H
import prep_w as P

Hn.CAP = 175.0
ISS = {i["id"]: i for i in json.load(open(f"{V}/w_issues.json"))}
EVAL = json.load(open(f"{V}/w_eval.json"))["evaluable"]
ORDER = [i["id"] for i in json.load(open(f"{V}/w_issues.json")) if i["id"] in EVAL]
MAXCALLS = 30
TEXT = (".py", ".txt", ".html", ".js", ".css", ".json", ".cfg", ".toml", ".rst", ".xml", ".po", ".sql")

TOOLS = [
    {"name": "search", "description": "case-insensitive regular-expression search over every line of every text file in the repository",
     "input_schema": {"type": "object", "properties": {"pattern": {"type": "string"}}, "required": ["pattern"]}},
    {"name": "read_file", "description": "read lines of one file (at most 200 lines per call)",
     "input_schema": {"type": "object", "properties": {"file": {"type": "string"}, "start_line": {"type": "integer"}, "num_lines": {"type": "integer"}}, "required": ["file", "start_line"]}},
    {"name": "list_files", "description": "list the files under a folder prefix ('' for the top level)",
     "input_schema": {"type": "object", "properties": {"prefix": {"type": "string"}}}},
    {"name": "edit_file", "description": "replace old_string with new_string in one file; old_string must match the file exactly and occur once",
     "input_schema": {"type": "object", "properties": {"file": {"type": "string"}, "old_string": {"type": "string"}, "new_string": {"type": "string"}}, "required": ["file", "old_string", "new_string"]}},
    {"name": "finish", "description": "call when the fix is complete",
     "input_schema": {"type": "object", "properties": {"summary": {"type": "string"}}, "required": ["summary"]}},
]
SYS = ("You are an engineer fixing an issue in this repository (Django). Find the cause with search, read_file and "
       "list_files, then fix it with edit_file (exact string replacement: old_string must match the file exactly and occur "
       "once). Change only the source code needed to resolve the issue; do not edit or add tests. When the fix is complete, "
       "call finish with a one-line summary. At most 30 tool calls.")
SYS_D = SYS.replace(" Find the cause", " The code the team's workspace ranked for the issue comes with it; start from it when it is "
                    "relevant. Find the cause")


class Repo:
    def __init__(self, root):
        self.root = root; self.edits = []
        self.files = sorted(os.path.relpath(os.path.join(d, f), root) for d, _, fs in os.walk(root) if "/.git" not in d + "/"
                            for f in fs if f.endswith(TEXT))

    def tool(self, name, a):
        try:
            if name == "search":
                rx = re.compile(a.get("pattern", ""), re.I); hits = []
                for rel in self.files:
                    for k, line in enumerate(open(os.path.join(self.root, rel), errors="ignore"), 1):
                        if rx.search(line):
                            hits.append(f"{rel}:{k}: {line.strip()[:200]}")
                return (f"{len(hits)} matching lines" + (", first 40:" if len(hits) > 40 else ":") + "\n" + "\n".join(hits[:40])) if hits else "0 matching lines"
            if name == "read_file":
                p = os.path.join(self.root, a.get("file", "")); lines = open(p, errors="ignore").read().split("\n")
                s = max(1, int(a.get("start_line") or 1)); e = min(len(lines), s + min(200, int(a.get("num_lines") or 80)) - 1)
                return "\n".join(f"{i}: {lines[i - 1]}" for i in range(s, e + 1)) + f"\n({len(lines)} lines in the file)"
            if name == "list_files":
                pre = (a.get("prefix") or "").strip("/")
                fs = sorted({f[len(pre):].lstrip("/").split("/")[0] for f in self.files if f.startswith(pre)})
                return "\n".join(fs[:300]) or "no files"
            if name == "edit_file":
                p = os.path.join(self.root, a["file"]); t = open(p).read(); n = t.count(a["old_string"])
                if n != 1:
                    return f"edit refused: old_string occurs {n} times"
                open(p, "w").write(t.replace(a["old_string"], a["new_string"]))
                line = t[: t.index(a["old_string"])].count("\n") + 1
                self.edits.append(f"{a['file']}:{line}")
                return f"edited {a['file']} at line {line}"
        except re.error as e:
            return f"invalid regular expression: {e}"
        except (OSError, ValueError, KeyError) as e:
            return f"error: {e}"
        return f"unknown tool {name}"


def agent(system, first, repo):
    messages = [{"role": "user", "content": first}]; calls = n = 0
    while n < MAXCALLS + 15:
        r = Hn.CLIENT.messages.create(model=Hn.SONNET, max_tokens=16000, system=system, tools=TOOLS, messages=messages)
        n += 1
        if r.stop_reason == "pause_turn":
            messages.append({"role": "assistant", "content": r.content}); continue
        uses = [b for b in r.content if b.type == "tool_use"]
        if not uses:
            return "".join(b.text for b in r.content if b.type == "text").strip()
        messages.append({"role": "assistant", "content": r.content}); results = []; done = None
        for u in uses:
            if u.name == "finish":
                done = u.input.get("summary", ""); results.append({"type": "tool_result", "tool_use_id": u.id, "content": "ok"}); continue
            calls += 1
            out = repo.tool(u.name, u.input) if calls <= MAXCALLS else "Tool limit reached: call finish now."
            results.append({"type": "tool_result", "tool_use_id": u.id, "content": out})
        if done is not None:
            return done
        messages.append({"role": "user", "content": results})
    return ""


def workdir(iid, arm):
    wd = f"{V}/wt/{iid}/{arm}"
    shutil.rmtree(wd, ignore_errors=True)
    subprocess.run(["cp", "-cR", f"{V}/wt/{iid}/base", wd], check=True)
    return wd


def one(arm, iid, url, out):
    it = ISS[iid]; repo = Repo(workdir(iid, arm)); Hn.begin(); err = summary = None
    try:
        if arm == "modeld":
            ws = Hn.WS(url, True); code = Hn.readout(ws.call, it["issue"])
            summary = agent(SYS_D, f"Issue:\n{it['issue']}\n\nThe code the team's workspace ranked for it:\n{code}", repo)
            if repo.edits:
                ws.call("teach", pairs=[{"question": it["issue"], "at": f"corpus/{repo.edits[0]}"}])
        else:
            summary = agent(SYS, f"Issue:\n{it['issue']}", repo)
    except Hn.Capped as e:
        err = str(e); R1.STOP.set()
    except Exception as e:
        err = f"{type(e).__name__}: {e}"[:300]
    diff = subprocess.run(["git", "diff"], cwd=repo.root, capture_output=True, text=True).stdout
    row = {"exp": "w", "arm": arm, "id": iid, "edits": repo.edits, "patch": diff, "summary": (summary or "")[:300], "error": err}
    row.update(Hn.summarise(Hn.took()))
    Hn.write(out, row)
    print(f"w {arm[:2].upper()} {iid:<24} edits={len(repo.edits)} req={row['requests']:>2} ${row['usd']:.4f} total ${Hn.spent():.2f}" + (f" ERR {err}" if err else ""), flush=True)


def run():
    md_out, al_out = f"{V}/w_md.jsonl", f"{V}/w_alone.jsonl"
    pm, um = Hn.serve(R1.WS_BASE, f"{V}/ws_w", 7900, fresh=not R1.resume(md_out))
    try:
        dm, da = Hn.done_ids(md_out), Hn.done_ids(al_out)
        t = threading.Thread(target=lambda: [one("modeld", i, um, md_out) for i in ORDER if i not in dm and not R1.STOP.is_set()])
        t.start()
        with ThreadPoolExecutor(3) as ex:
            list(ex.map(lambda i: None if R1.STOP.is_set() else one("alone", i, None, al_out), [i for i in ORDER if i not in da]))
        t.join()
    finally:
        pm.terminate()


def score():
    for arm in ("alone", "modeld"):
        out = f"{V}/w_{arm if arm == 'alone' else 'md'}.jsonl"; scored = f"{V}/w_scored_{arm}.jsonl"
        done = Hn.done_ids(scored)
        for r in [json.loads(l) for l in open(out)]:
            if r["id"] in done:
                continue
            it = ISS[r["id"]]; tmp = f"{V}/wt/{r['id']}/score_{arm}"
            shutil.rmtree(tmp, ignore_errors=True); subprocess.run(["cp", "-cR", f"{V}/wt/{r['id']}/base", tmp], check=True)
            ok_model = (not r["patch"]) or P.apply(tmp, r["patch"])[0]
            tests = re.findall(r"^diff --git a/(\S+) b/", it["test_patch"], re.M)
            subprocess.run(["git", "checkout", "--", *[t for t in tests if os.path.exists(os.path.join(tmp, t))]], cwd=tmp, capture_output=True)
            ok_test = P.apply(tmp, it["test_patch"])[0]
            st, _ = P.run_tests(tmp, P.modules(it["test_patch"])) if (ok_model and ok_test and r["patch"]) else ({}, 1)
            resolved = bool(r["patch"]) and ok_model and ok_test and P.judge(st, it)
            shutil.rmtree(tmp, ignore_errors=True)
            Hn.write(scored, {"id": r["id"], "arm": arm, "resolved": resolved, "patch applied": ok_model, "tests applied": ok_test,
                              "f2p ok": sum(st.get(t) == "ok" for t in it["FAIL_TO_PASS"]), "f2p": len(it["FAIL_TO_PASS"])})
            print(f"score {arm:<6} {r['id']:<24} resolved={resolved}", flush=True)


if __name__ == "__main__":
    {"run": run, "score": score}[sys.argv[1]]()
    print(f"DONE {sys.argv[1]}: spend ${Hn.spent():.2f}", flush=True)

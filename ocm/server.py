"""The team's workspace server: one per team, shared by every person's and agent's sessions.

    python -m ocm serve <workspace folder> [--port 7700] [--host 127.0.0.1]

The workspace is a CMLM: vectors and laws, not stored text. Code and docs are units with 1,024-bit vectors; the vector
law ranks them for a question; the router law picks which readout to send and, when one does not answer, the next;
the learned law reorders the nearest by meaning once it beats the vector order. Teaching stores no answer: a question
someone asked becomes a cue vector on the unit that holds its answer line, so a later question near it in meaning is
drawn to that code (vector generalisation), and it is an example for the learned law. All of it runs locally, at no
model tokens.

POST JSON to these paths (the hooks in ocm.loop and the MCP plugin call them):
  /ask      {"question"}            the router law's first readout: the code a taught question's vector points to, or
                                    10 code blocks and doc sentences (by meaning, by keyword, or both)
  /next     {"question"}            the router law's next readout for the same question (ADVANCE), until there are none
  /recall   {"query", "k"}          the k units nearest in meaning (k up to 10)
  /teach    {"pairs": [{"question", "at"}, ...]}
                                    "at" names the line the answer is on, as path:line (the first path:line in it is
                                    used); the question's vector becomes a cue on the unit holding that line
  /search   {"pattern"}  /read {"file", "start", "num"}  /list {"prefix"}
                                    plain regex search, file reading and listing over the workspace's folders
  /stats    {}                      units, question vectors taught, the learned law, calls served
Every call is appended to <workspace>/calls.jsonl (time, path, sizes), so a pilot can count what the workspace did."""
import argparse, glob, hashlib, json, os, re, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import numpy as np

from .cmlm_vector import Memory
from .router import router as RL
from .router import lanes as L
from .units import files as list_files

NAMES = {0: "the code a taught question's vector points to (ranked by meaning, not verified: use it only if it answers the question)",
         1: "meaning", 2: "keyword matches", 3: "meaning and keyword matches", 4: "meaning, wider"}


class Workspace:
    def __init__(self, folder):
        self.folder = folder
        self.meta = json.load(open(os.path.join(folder, "workspace.json")))
        self.mem = Memory(os.path.join(folder, "memory"))
        RL.observe.THETA = self.meta.get("theta", 9.349)
        L.N9 = max(1, self.meta["units"])                                          # the IDF base: the units at build
        self.lanes = L.Lanes(self.mem, np.arange(self.meta["units"]), os.path.join(folder, "keyword.db"), RL)
        self.files = {rel: path for _, rel, path in list_files(self.meta["roots"])}
        self.state, self.lock, self.log = {}, threading.Lock(), os.path.join(folder, "calls.jsonl")
        self.spans = {}                                                            # path -> [(first line, last line, unit)]
        m, sp = self.mem, os.path.join(folder, "spans.json")
        lines = json.load(open(sp)) if os.path.exists(sp) else None
        for j in range(min(self.meta["units"], len(m.texts))):
            if m.src[j] < 0:
                continue
            if lines is not None:
                first, last = lines[j]
            else:                                                                  # a workspace built before spans.json
                t = m.texts[j]; first = m.pos[j]; last = first + (t.count("\n") - 1 if t.startswith("# ") else 0)
            if first:
                self.spans.setdefault(m.sources[m.src[j]]["path"], []).append((first, last, j))

    CITE = re.compile(r"([A-Za-z0-9_./-]*[A-Za-z0-9_-]):(\d+)")

    def unit_at(self, ref):
        """The unit holding the line named by the first path:line in ref (a path may be given relative or by its
        tail), or None when the workspace holds no such line."""
        for path, line in self.CITE.findall(str(ref)):
            path = path.strip("./"); line = int(line)
            hits = [p for p in self.spans if p == path or p.endswith("/" + path)]
            if len(hits) != 1:
                continue                                                           # unknown or ambiguous: try the next
            held = [j for first, last, j in self.spans[hits[0]] if first <= line <= last]
            if held:
                return held[0]
        return None

    def fmt(self, j, i):
        m = self.mem
        if m.src[j] < 0:
            return f"{i}. [text taught to a workspace from before vectors-only teaching]\n{m.texts[j]}"
        path = m.sources[m.src[j]]["path"]; t = m.texts[j]
        body = t.split("\n", 1)[1] if t.startswith("# ") and "\n" in t else t
        return f"{i}. [{path}" + (f":{m.pos[j]}" if m.pos[j] else "") + f"]\n{body}"

    def routed(self, question, first):
        key = hashlib.sha1(" ".join(question.split()).lower().encode()).hexdigest()
        st = self.state.get(key)
        if first or st is None or st["slot"] is None:
            st = self.state[key] = {"live": 63, "slot": None, "tried": False}
        else:
            st["live"] = RL.advance(st["live"], st["slot"]); st["tried"] = True
        rows, obs = self.lanes.measure(question)
        slot, lane = RL.emit(self.lanes.byte(obs, st["tried"]), st["live"]); st["slot"] = slot
        if lane == 5:
            return "NO MORE READOUTS for this question: ask in other words with recall, or search the code."
        m = self.mem
        if m.law.active and lane in (1, 3, 4):                                # the learned law orders the top 8 by meaning
            cand, strong, weak = m._rank(question)
            law = m.law.order(cand[:m.law.n], m._lane_words(question, cand, strong, weak)) + cand[m.law.n:]
            if lane == 3:
                rows[3] = list(dict.fromkeys(law[:5] + [j for j in rows[3] if j not in set(cand[:5])]))
            else:
                rows[lane] = law[:len(rows[lane])]
        rows = [j for j in rows[lane] if j < len(self.mem.texts)]
        return f"(readout: {NAMES[lane]})\n\n" + "\n\n".join(self.fmt(j, i) for i, j in enumerate(rows, 1))

    def handle(self, path, req):
        m = self.mem
        if path == "ask":
            return self.routed(str(req.get("question", "")), True)
        if path == "next":
            return self.routed(str(req.get("question", "")), False)
        if path == "recall":
            r = m.recall(str(req.get("query", "")), k=max(1, min(10, int(req.get("k") or 5))), context=0)
            return "\n\n".join(self.fmt(m.by_text[x["fact"]], i) for i, x in enumerate(r["rows"], 1))
        if path == "teach":
            items = req.get("pairs") or [{"question": n.get("question", ""), "at": n.get("note", "")} for n in req.get("notes", [])]
            placed, missed = [], 0
            for it in items:
                q, j = str(it.get("question", "")), self.unit_at(it.get("at", ""))
                if q.strip() and j is not None:
                    placed.append((q, j))
                else:
                    missed += 1
            r = m.teach_at(placed) if placed else {"cues": 0}; m.save()
            self.lanes = L.Lanes(m, np.arange(self.meta["units"]), os.path.join(self.folder, "keyword.db"), RL)
            st = m.law.state()
            return (f"taught {r['cues']} question vectors onto code; {missed} not placed (no path:line the workspace holds); "
                    f"learned law: {st['law']}, {'active' if st['active'] else 'not yet active'} ({st['examples']} examples)")
        if path == "search":
            try:
                rx = re.compile(str(req.get("pattern", "")), re.I)
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
        if path == "read":
            rel = str(req.get("file", "")).strip().lstrip("./")
            if rel not in self.files:
                return f"no such file in the workspace: {rel}"
            lines = open(self.files[rel], encoding="utf-8").read().split("\n")
            s = max(1, int(req.get("start", 1) or 1)); e = min(len(lines), s + max(1, min(200, int(req.get("num", 80) or 80))) - 1)
            return "\n".join(f"{i}: {lines[i - 1]}" for i in range(s, e + 1)) + f"\n({len(lines)} lines in the file)"
        if path == "list":
            p = str(req.get("prefix", "")).strip().lstrip("./"); fs = [f for f in self.files if f.startswith(p)]
            return f"{len(fs)} files" + (", first 300:" if len(fs) > 300 else ":") + "\n" + "\n".join(fs[:300])
        if path == "stats":
            return json.dumps({"units": len(m.texts), "question vectors taught": len(m.cue_texts),
                               "files": len(self.files), "learned law": m.law.state()})
        return f"unknown path: /{path}"


def serve(folder, port=7700, host="127.0.0.1"):
    ws = Workspace(folder)

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_POST(self):
            path = self.path.strip("/")
            try:
                req = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
                with ws.lock:
                    out = ws.handle(path, req)
                    with open(ws.log, "a") as f:
                        f.write(json.dumps({"t": time.time(), "path": path, "in": len(json.dumps(req)), "out": len(out),
                                            "taught": len(req.get("pairs") or req.get("notes") or []) if path == "teach" else None}) + "\n")
                body, code = out.encode(), 200
            except Exception as e:                                       # noqa: BLE001 -- reported to the caller
                body, code = f"error: {type(e).__name__}: {e}".encode(), 500
            self.send_response(code); self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)

    print(f"workspace {folder}: {ws.meta['units']:,} units from {ws.meta['files']:,} files; serving on http://{host}:{port}", flush=True)
    ThreadingHTTPServer((host, port), H).serve_forever()


def main(argv=None):
    ap = argparse.ArgumentParser(prog="ocm serve"); ap.add_argument("workspace"); ap.add_argument("--port", type=int, default=7700)
    ap.add_argument("--host", default="127.0.0.1")
    a = ap.parse_args(argv); serve(a.workspace, a.port, a.host)

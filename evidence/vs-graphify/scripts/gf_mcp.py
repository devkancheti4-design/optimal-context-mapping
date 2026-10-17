"""Graphify 0.9.92 as it ships: its own MCP server (python -m graphify.serve, Streamable HTTP, JSON responses,
stateless), started over one graph.json and spoken to with plain JSON-RPC."""
import json, os, subprocess, time, urllib.request

GF_PY = os.path.expanduser("~/neos/outreach/vs-graphify/gfvenv/bin/python")


class Graphify:
    def __init__(self, graph, port, log=None):
        self.url = f"http://127.0.0.1:{port}/mcp"
        self.p = subprocess.Popen([GF_PY, "-m", "graphify.serve", graph, "--transport", "http", "--json-response",
                                   "--stateless", "--port", str(port)], stdout=open(log or os.devnull, "a"),
                                  stderr=subprocess.STDOUT)
        for _ in range(600):
            try:
                self.tools(); return
            except Exception:
                if self.p.poll() is not None:
                    raise RuntimeError(f"graphify serve exited with {self.p.returncode}")
                time.sleep(1)
        raise RuntimeError("graphify serve did not answer in 600 s")

    def rpc(self, method, params=None):
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, **({"params": params} if params else {})}).encode()
        req = urllib.request.Request(self.url, data=body, headers={"Content-Type": "application/json",
                                                                   "Accept": "application/json, text/event-stream"})
        d = json.loads(urllib.request.urlopen(req, timeout=600).read().decode())
        if "error" in d:
            raise RuntimeError(str(d["error"])[:300])
        return d["result"]

    def tools(self):
        return self.rpc("tools/list")["tools"]

    def call(self, name, args):
        r = self.rpc("tools/call", {"name": name, "arguments": args})
        return "".join(c.get("text", "") for c in r.get("content", []))

    def close(self):
        self.p.terminate()
        try:
            self.p.wait(30)
        except subprocess.TimeoutExpired:
            self.p.kill()

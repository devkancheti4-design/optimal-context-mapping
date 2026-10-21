"""Memory test setup on fastify at HEAD.
Taught set: fixes 0-19. Each is taught where its fix landed (the first line the fix wrote in its main file, found again
in HEAD's copy of that file), then asked again in other words. Untaught set: fixes 20-39, asked as-is, before and
after teaching, to see whether the memory hurts new questions."""
import json, re, subprocess

REPO = "~/eval/targets/fastify"
PARA = [
    "How is the serializer schema chosen for a reply based on its media type?",
    "Reading the hostname and protocol from X-Forwarded headers crashes when there is no socket. Where is that?",
    "Where do async error handlers report to diagnostics_channel?",
    "Where are trailer completion callbacks handled so that a second completion is dropped?",
    "How does fastify split a big Buffer payload when replying over http2?",
    "Which error is thrown when a plugin's dependency has not been registered?",
    "Where is per-socket metadata cleaned up after a response, so keep-alive sockets don't leak memory?",
    "Why do nested plugin prefixes end up with '//' in the route path?",
    "Where does the check for whether a request or reply decorator exists look at properties set in the constructor?",
    "When a route has an onTimeout hook and the reply is hijacked, where is the socket metadata released?",
    "How does reply.send decide that a payload is JSON and which charset to use?",
    "How is the port of an incoming request computed?",
    "Does findRoute handle lowercase HTTP methods?",
    "Why are falsy values returned by a custom validator ignored when updating the request body?",
    "Errors thrown in writeHead can't be caught when an async hook is used. Where does that happen?",
    "Where are Content-Type parameters with quoted values parsed?",
    "Where is the warning for overriding a request's HTTP method declared?",
    "On close, why are in-flight connections forcibly closed when forceCloseConnections is 'idle'?",
    "Removing every trailer leaves stale trailer state behind. Where?",
    "What argument is passed to the requestCompleted log callback when a request succeeds?",
]


def git(*a):
    return subprocess.run(["git", "-C", REPO, *a], capture_output=True, text=True, check=True).stdout


Q = json.load(open("~/eval/bench/q_fastify.json"))
taught = []
for q, para in zip(Q[:20], PARA):
    best, line_text = None, None
    for f in q["gold"]:
        d = git("diff", "-U0", "--no-renames", q["parent"], q["hash"], "--", f)
        added = [l[1:] for l in d.split("\n") if l.startswith("+") and not l.startswith("+++") and l[1:].strip()]
        if added and (best is None or len(added) > best[1]):
            best, line_text = (f, len(added)), added[0]
    f = best[0] if best else q["gold"][0]
    head = git("show", f"HEAD:{f}").split("\n")
    ln = next((i for i, l in enumerate(head, 1) if line_text and l.strip() == line_text.strip()), 1)
    taught.append({"question": q["question"], "paraphrase": para, "gold": q["gold"], "file": f, "line": ln,
                   "found_at_head": ln != 1})
json.dump({"taught": taught, "untaught": [{"question": q["question"], "gold": q["gold"]} for q in Q[20:]]},
          open("~/eval/bench/mem_set.json", "w"), indent=1)
print(sum(t["found_at_head"] for t in taught), "of 20 landing lines found again at HEAD")

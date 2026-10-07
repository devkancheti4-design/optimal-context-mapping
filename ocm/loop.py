"""The workspace inside the model's loop: nothing for the model to call, no extra round trip.

    python -m ocm hook prompt     # before each request: prints the workspace's readout for the prompt (Claude Code
                                  # UserPromptSubmit hook; what it prints goes in with the request)
    python -m ocm hook stop       # after each reply: teaches the reply's TEACH: lines (Claude Code Stop hook)

Before every request the workspace's laws pick what matters for it: the router law's first readout (the code a taught
question's vector points to, or the nearest code and doc sentences by meaning and keyword). When the first readout is
the taught one, the router law's own next readout goes with it, which is the law's ADVANCE, run one step ahead so a
near miss costs no search. The model answers from the readout when it answers the question, searches only when it does
not, and ends its reply with one TEACH: line per question naming the line its answer is on. The stop hook teaches those
lines locally, at no model tokens: each question's vector becomes a cue on the unit holding that line. `prefetch` and
`teach_from_reply` are the same two steps for any other agent loop. Both talk to the team's workspace server at $OCM_URL
(default http://127.0.0.1:7700)."""
import json
import os
import sys
import urllib.request

URL = os.environ.get("OCM_URL", "http://127.0.0.1:7700").rstrip("/")
HEADER = ("Team workspace: the code and docs its laws ranked for this request before it was sent (there is nothing to "
          "call; they are ranked, not verified). If they answer it, answer from them without searching; if not, search.")
RULE = ("End your reply with one line per question you answered, so the team's workspace learns it:\n"
        "TEACH: <the question> | <path>:<line> (the one line your answer is on)")


def _call(path, url=None, **kw):
    req = urllib.request.Request((url or URL) + "/" + path, data=json.dumps(kw).encode())
    return urllib.request.urlopen(req, timeout=120).read().decode()


COMPACT = os.environ.get("OCM_COMPACT") == "1"
SHORT_HEADER = "Team workspace, nearest matches (ranked, not verified; use them only if they answer it):"
SHORT_RULE = "End with: TEACH: <the question> | <path>:<line your answer is on>"


def compact_readout(readout, k=3):
    """A small injection: each readout in it cut to its top k items. In a session that keeps its transcript every
    injected token is re-read by every later request, so less is kept."""
    import re
    out = []
    for part in re.split(r"(?m)^(?=\(readout: )", readout):
        if not part.strip() or part.startswith("NO MORE"):
            continue
        head, _, body = part.partition("\n\n")
        items = re.split(r"(?m)^(?=\d+\. \[)", body)
        out.append(head + "\n\n" + "".join(x for x in items[:k + 1] if x).rstrip())
    return "\n\n".join(out)


TAUGHT = "(readout: the code a taught question"


def readout(call, question):
    """The router law's readout for a request: its first, and when the first is the taught one, its next (ADVANCE)
    too. call(path, **kw) -> text reaches the workspace (over HTTP, or in process)."""
    first = call("ask", question=question)
    if first.startswith(TAUGHT):
        nxt = call("next", question=question)
        if nxt.startswith("(readout:"):
            return first + "\n\n" + nxt
    return first


def prefetch(question, url=None, compact=None):
    """The context that goes in with a request: the workspace's first readout for it, and the teach rule.
    compact (default $OCM_COMPACT=1): each readout cut to its top 3 items, with a short header."""
    out = readout(lambda path, **kw: _call(path, url, **kw), question)
    if COMPACT if compact is None else compact:
        return f"{SHORT_HEADER}\n{compact_readout(out)}\n{SHORT_RULE}"
    return f"{HEADER}\n\n{out}\n\n{RULE}"


def teach_lines(text):
    """[(question, where the answer is)] from the TEACH: lines of a reply."""
    out = []
    for line in str(text).splitlines():
        s = line.strip().lstrip("*-> ").strip()
        if s.upper().startswith("TEACH:") and "|" in s:
            q, n = s[len("TEACH:"):].split("|", 1)
            if q.strip() and n.strip():
                out.append((q.strip(), " ".join(n.split())))
    return out


def teach_from_reply(text, url=None):
    """Teach every TEACH: line of a reply in one call; returns how many lines were sent."""
    pairs = teach_lines(text)
    if pairs:
        _call("teach", url, pairs=[{"question": q, "at": at} for q, at in pairs])
    return len(pairs)


def _last_reply(transcript_path):
    text = ""
    for line in open(transcript_path, encoding="utf-8", errors="replace"):
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            continue
        if d.get("type") == "assistant":
            parts = [b.get("text", "") for b in (d.get("message") or {}).get("content") or [] if isinstance(b, dict) and b.get("type") == "text"]
            if parts:
                text = "\n".join(parts)
    return text


def main(argv=None):
    argv = list(argv or [])
    if argv[:1] == ["prompt"]:
        data = json.load(sys.stdin)
        q = str(data.get("prompt", "")).strip()
        if q:
            try:
                print(prefetch(q))
            except OSError as e:                                  # the workspace is down: the request goes on without it
                print(f"(team workspace unavailable: {e})")
    elif argv[:1] == ["stop"]:
        data = json.load(sys.stdin)
        if data.get("stop_hook_active") or not data.get("transcript_path"):
            return
        try:
            teach_from_reply(_last_reply(data["transcript_path"]))
        except OSError:
            pass
    else:
        print(__doc__); sys.exit(2)

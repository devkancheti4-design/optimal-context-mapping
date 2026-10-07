"""The workspace inside the model's loop: nothing for the model to call, no extra round trip.

    python -m ocm hook prompt     # before each request: prints the workspace's facts for the prompt (Claude Code
                                  # UserPromptSubmit hook; what it prints goes in with the request)
    python -m ocm hook stop       # after each reply: teaches the reply's TEACH: lines (Claude Code Stop hook)

Before every request the workspace recalls what matters for it: the router law's first readout, which is the nearest
teammate's note when one is close (ranked by meaning, not verified), or else the nearest code blocks, doc sentences and notes. That
readout goes in with the request, so the model needs no `ask` call and no transcript of earlier work. The model answers
from the facts when they answer it, searches only when they do not, and ends its reply with one TEACH: line per
question. The stop hook teaches those lines to the workspace locally, at no model tokens, so the next request, by this
person or a teammate, starts from them. `prefetch` and `teach_from_reply` are the same two steps for any other agent
loop. Both talk to the team's workspace server at $OCM_URL (default http://127.0.0.1:7700)."""
import json
import os
import sys
import urllib.request

URL = os.environ.get("OCM_URL", "http://127.0.0.1:7700").rstrip("/")
HEADER = ("Team workspace: the nearest code, docs and teammates' notes for this request, ranked by meaning before it "
          "was sent (there is nothing to call; they are ranked, not verified). If they answer it, answer from them without "
          "searching; if not, search.")
RULE = ("End your reply with one line per question you answered, so the team's workspace learns it:\n"
        "TEACH: <the question> | <the answer in one to three sentences, with the files and lines it comes from>")


def _call(path, url=None, **kw):
    req = urllib.request.Request((url or URL) + "/" + path, data=json.dumps(kw).encode())
    return urllib.request.urlopen(req, timeout=120).read().decode()


COMPACT = os.environ.get("OCM_COMPACT") == "1"
SHORT_HEADER = "Team workspace, nearest matches (ranked, not verified; use them only if they answer it):"
SHORT_RULE = "End with: TEACH: <the question> | <the answer, with files and lines>"


def compact_readout(readout, k=3):
    """A small injection: a teammate's note alone stays as it is; otherwise only the top k items. In a session that
    keeps its transcript every injected token is re-read by every later request, so less is kept."""
    import re
    if readout.startswith("(readout: a teammate's note") or readout.startswith("NO MORE"):
        return readout
    head, _, body = readout.partition("\n\n")
    items = re.split(r"(?m)^(?=\d+\. \[)", body)
    return head + "\n\n" + "".join(x for x in items[:k + 1] if x).rstrip()


def prefetch(question, url=None, compact=None):
    """The context that goes in with a request: the workspace's first readout for it, and the teach rule.
    compact (default $OCM_COMPACT=1): only a teammate's note alone, or the top 3 items, with a short header."""
    out = _call('ask', url, question=question)
    if COMPACT if compact is None else compact:
        return f"{SHORT_HEADER}\n{compact_readout(out)}\n{SHORT_RULE}"
    return f"{HEADER}\n\n{out}\n\n{RULE}"


def teach_lines(text):
    """[(question, note)] from the TEACH: lines of a reply."""
    out = []
    for line in str(text).splitlines():
        s = line.strip().lstrip("*-> ").strip()
        if s.upper().startswith("TEACH:") and "|" in s:
            q, n = s[len("TEACH:"):].split("|", 1)
            if q.strip() and n.strip():
                out.append((q.strip(), " ".join(n.split())))
    return out


def teach_from_reply(text, url=None):
    """Teach every TEACH: line of a reply in one call; returns how many notes were taught."""
    notes = teach_lines(text)
    if notes:
        _call("teach", url, notes=[{"question": q, "note": n} for q, n in notes])
    return len(notes)


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

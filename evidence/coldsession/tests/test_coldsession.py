"""The harness end to end on a tiny repository with a scripted stand-in for the model. No model calls. The map, lessons and rebuilds are Model D's real code.

    HF_HUB_OFFLINE=1 <modeld python> -m pytest -q tests"""
import json, os, re, sys

import pytest

H = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, H)
HOME = None
T0 = {
    "pkg/__init__.py": "",
    "pkg/transport.py": 'def open_connection(host, retries=5):\n    """Open a connection to a host."""\n    return (host, retries)\n\n\nLIMIT_BYTES = 4096\n',
    "pkg/replies.py": 'def wait_for_reply(channel, timeout=30):\n    """Block until the other side answers."""\n    return channel.get(timeout)\n',
    "pkg/widgets.py": 'class Widget(object):\n    """A thing on the screen."""\n    def draw(self, depth=16):\n        return depth\n',
}
T2 = {
    "pkg/__init__.py": "",
    "pkg/transport.py": '# moved lines down\n\n\ndef open_connection(host, retries=7):\n    """Open a connection to a host."""\n    return (host, retries)\n\n\nLIMIT_BYTES = 4096\n',
    "pkg/replies.py": '# moved lines down\n\n\ndef wait_for_reply(channel, timeout=30):\n    """Block until the other side answers."""\n    return channel.get(timeout)\n',
    "pkg/ui/__init__.py": "",
    "pkg/ui/widgets.py": 'class Widget(object):\n    """A thing on the screen."""\n    def draw(self, depth=16):\n        return depth\n',
}
NEEDS = [  # the scripted model knows one regex per need; the wordings are close enough for a real lesson to land
    ("retries", r"retries=(\d+)", "How many times does opening a connection try again by default"),
    ("timeout", r"timeout=(\d+)", "How long does waiting for an answer block by default"),
    ("depth", r"depth=(\d+)", "What colour depth does drawing use by default"),
]


def write(root, files):
    for rel, text in files.items():
        p = os.path.join(root, rel); os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, "w").write(text)


class Scripted:
    """Stands in for the model: reads the code it is given, searches when it has to, submits what it finds. Reports token counts the size of what it was sent."""
    def __init__(self):
        self.calls = 0

    @staticmethod
    def need(text):
        for name, rx, phrase in NEEDS:
            if phrase in text.split("\n")[0]:
                return rx, phrase
        raise AssertionError(text[:200])

    def __call__(self, model, body):
        self.calls += 1
        sent = json.dumps(body)
        usage = {"usageMetadata": {"promptTokenCount": len(sent) // 4, "candidatesTokenCount": 10}}
        contents = body["contents"]
        first = contents[0]["parts"][0]["text"]
        rx, phrase = self.need(first)
        if "tools" not in body:                                # a read
            found = re.search(rx, first)
            return {"candidates": [{"content": {"parts": [{"text": f"It is {found.group(1)}." if found else "NEED_SEARCH"}]}}], **usage}
        if "Notes from earlier sessions" in first:             # trusts its notes
            note = re.search(re.escape(phrase) + r"[^\n]*-> ([^\n]*)", first)
            if note:
                return {"candidates": [{"content": {"parts": [{"functionCall": {"name": "submit", "args": {"answer": note.group(1), "at": ""}}}]}}], **usage}
        replies = [p for c in contents for p in c["parts"] if "functionResponse" in p]
        if not replies:
            return {"candidates": [{"content": {"parts": [{"functionCall": {"name": "search", "args": {"pattern": rx}}}]}}], **usage}
        out = replies[-1]["functionResponse"]["response"]["content"]
        found = re.search(r"([\w./-]+:\d+):.*?" + rx, out)
        answer = int(found.group(2)) if "depth" in rx else f"It is {found.group(2)}."      # a real model sometimes submits a bare number
        return {"candidates": [{"content": {"parts": [{"functionCall": {"name": "submit", "args": {"answer": answer, "at": found.group(1)}}}]}}], **usage}


@pytest.fixture(scope="module")
def world(tmp_path_factory):
    global HOME
    HOME = str(tmp_path_factory.mktemp("home"))
    work = str(tmp_path_factory.mktemp("work"))
    os.environ["COLDSESSION_HOME"], os.environ["COLDSESSION_WORK"], os.environ["COLDSESSION_CAP"] = HOME, work, "1000"
    for m in ("common", "arms", "session", "grade", "score", "wordings", "facts", "landing"):
        sys.modules.pop(m, None)
    import common as C
    import facts as F
    for t, files in (("T0", T0), ("T1", T2), ("T2", T2), ("mate", T0)):
        write(C.work("toy", "snap", t, "repo"), files)
    old, new = F.snapshot_facts(C.work("toy", "snap", "T0", "repo")), F.snapshot_facts(C.work("toy", "snap", "T2", "repo"))
    by = {(r["subject"], r["param"]): r for r in F.compare(old, new)}
    os.makedirs(C.data("toy"), exist_ok=True)
    chosen = []
    for name, rx, phrase in NEEDS:
        f = by[({"depth": "Widget.draw", "retries": "open_connection", "timeout": "wait_for_reply"}[name], name)]
        chosen.append({**f, "id": name, "role": "taught", "wordings": {w: f"{phrase}{suffix}?" for w, suffix in zip("abcd", ("", " in the code", " in this project", " right now"))}})
    with open(C.data("toy", "facts.jsonl"), "w") as o:
        for f in chosen:
            o.write(json.dumps(f) + "\n")
    json.dump({"repo": "acme/toy"}, open(C.data("toy", "pins.json"), "w"))
    json.dump(F.rates(F.compare(old, new)), open(C.data("toy", "rates.json"), "w"))
    with open(C.data("toy", "pool.jsonl"), "w") as o:             # a lesson outside the questions, for session 5
        for r in F.compare(old, new):
            if r["kind"] == "where" and r["subject"] == "wait_for_reply":
                o.write(json.dumps({**r, "id": "extra"}) + "\n")
    import session as S
    import arms as A
    for arm in ("modeld", "alone", "map", "notes"):                # the order run.py uses
        for s in C.SESSIONS[arm]:
            S.main("toy", arm, s, model=A.Model(send=Scripted()))
    import score
    return {r["arm"] + str(r["session"]) + r["id"]: r for r in score.load("toy")}


def test_facts_compare_says_what_happened(world):
    assert world["alone2retries"]["status"] == "changed" and world["alone2timeout"]["status"] == "same" and world["alone2depth"]["status"] == "moved"


def test_the_agent_alone_explores_every_session_and_stays_right(world):
    for s in (2, 4):
        for fact in ("retries", "timeout", "depth"):
            assert world[f"alone{s}{fact}"]["grade"] == "right" and world[f"alone{s}{fact}"]["requests"] >= 2


def test_memory_off_never_learns(world):
    assert all(world[f"map{s}timeout"]["path"] != "read" for s in (2, 4))


def test_lessons_reach_new_sessions_a_teammate_and_a_year_later(world):
    assert world["modeld1timeout"]["path"] == "teach"
    for s in (2, 3, 4):
        assert world[f"modeld{s}timeout"]["path"] == "read" and world[f"modeld{s}timeout"]["requests"] == 1 and world[f"modeld{s}timeout"]["grade"] == "right"


def test_a_moved_line_keeps_its_lesson(world):
    assert world["modeld4depth"]["path"] == "read" and world["modeld4depth"]["grade"] == "right"


def test_more_lessons_on_disk_still_land_and_notes_get_longer(world):
    assert world["modeld5timeout"]["path"] == "read" and world["modeld5timeout"]["grade"] == "right"
    assert world["notes5timeout"]["notes_chars"] > world["notes1depth"]["notes_chars"] and world["notes5timeout"]["requests"] == 1


def test_a_changed_fact_is_never_read_stale_by_model_d(world):
    assert world["modeld4retries"]["grade"] == "right"


def test_a_notes_file_goes_stale_when_the_code_changes(world):
    assert world["notes2retries"]["requests"] == 1 and world["notes2retries"]["grade"] == "right"
    assert world["notes4retries"]["grade"] == "stale" and world["notes4timeout"]["grade"] == "right"


def test_grading_rules():
    import grade as G
    assert G.grade("default", 30, "It defaults to 30 seconds.") == "right"
    assert G.grade("default", 30, "It is 300.") == "miss" and G.grade("default", 30, "It is 30.5.") == "miss"
    assert G.grade("default", 7, "The default is 5.", old=5) == "stale"
    assert G.grade("default", 7, "It was 5, now 7.", old=5) == "hedged"
    assert G.grade("default", "utf-8", "It uses 'utf-8' by default.") == "right"
    assert G.grade("where", "pkg/ui/widgets.py", "In repo/pkg/ui/widgets.py:3.", old="pkg/widgets.py") == "right"
    assert G.grade("where", "pkg/ui/widgets.py", "In `pkg/widgets.py`.", old="pkg/widgets.py") == "stale"
    assert G.grade("base", ["abc.ABC"], "It inherits from ABC.") == "right"
    assert G.grade("base", ["Mixin", "Base"], "Mixin, Base", old=["Base"]) == "right" and G.grade("base", ["Mixin", "Base"], "Base", old=["Base"]) == "stale"
    assert G.grade("default", 1000, "It is 1,000.") == "right"
    assert G.grade("default", None, "it defaults to none") == "right"


def test_wordings_reject_the_codes_names_and_the_answer():
    import wordings as W
    f = {"kind": "default", "subject": "Client.send", "param": "max_tries", "value": 30, "path": "a/b.py"}
    assert W.leaks(f, "How long does Client.send wait?") and W.leaks(f, "What does max_tries default to?") and W.leaks(f, "Is the default wait 30?")
    assert not W.leaks(f, "How many times does a request get tried by default?")

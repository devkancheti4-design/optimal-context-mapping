"""Smoke tests: build a workspace over the fixture repo, ask, teach in one batch, ask again in other words, and speak
MCP. Needs the embedding model (downloaded once). Run: python -m pytest -q tests"""
import json, os, shutil, tempfile

from ocm.build import build
from ocm.mcp import handle
from ocm.server import Workspace

HERE = os.path.dirname(os.path.abspath(__file__))


def test_workspace_end_to_end():
    out = os.path.join(tempfile.mkdtemp(), "ws")
    build([os.path.join(HERE, "fixture_repo")], out, log=lambda *a: None)
    ws = Workspace(out)
    assert all(".env" not in p for p in ws.files) and not any("should-never" in t for t in ws.mem.texts)
    assert any(p.endswith("/Dockerfile") for p in ws.files)                    # build files with no extension are code
    assert ws.unit_at("docs/README.md:4") is not None                           # doc sentences keep their lines
    first = ws.handle("ask", {"question": "How many times do we retry a failed card charge?"})
    assert "MAX_CHARGE_RETRIES = 3" in first
    units = len(ws.mem.texts)
    taught = ws.handle("teach", {"pairs": [{"question": "How many times do we retry a failed card charge?", "at": "src/config.py:4"},
                                           {"question": "Who owns refunds?", "at": "nowhere.py:3"}]})
    assert taught.startswith("taught 1 question vectors onto code; 1 not placed") and "(1 examples)" in taught, taught
    assert len(ws.mem.texts) == units                                           # teaching stores vectors, never text
    again = ws.handle("ask", {"question": "what is the retry limit when a payment to a card fails?"})
    assert again.startswith("(readout: the code a taught question") and "MAX_CHARGE_RETRIES = 3" in again, again
    assert "src/config.py:3" in again                                           # the code block itself, with its place
    assert "ChargeDeclined" in ws.handle("search", {"pattern": "class ChargeDeclined"})
    scoped = ws.handle("ask", {"question": "Who owns refunds?", "scope": "code"})   # code scope: no documentation
    assert "docs/README.md" not in scoped and "[" in scoped, scoped
    assert "docs/README.md" in ws.handle("ask", {"question": "Who owns refunds?", "scope": "all"})
    st = json.loads(ws.handle("stats", {}))
    assert st["question vectors taught"] == 1 and st["learned law"]["examples"] == 1
    again2 = Workspace(out)                                                     # taught vectors persist on disk
    assert json.loads(again2.handle("stats", {}))["question vectors taught"] == 1


def test_mcp_protocol():
    init = handle({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}})
    assert init["protocolVersion"] == "2025-06-18" and "tools" in init["capabilities"]
    names = [t["name"] for t in handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})["tools"]]
    assert names == ["workspace_ask", "workspace_next", "workspace_recall", "workspace_teach"]


def test_loop_teach_lines():
    from ocm.loop import teach_lines
    reply = """The token lasts 8 days.
ANSWER: 8 days | SOURCE: backend/app/core/config.py
TEACH: How long does a login token stay valid? | backend/app/core/config.py:36
- TEACH: Where do emails go locally? | compose.override.yml:84
TEACH: no separator here
"""
    got = teach_lines(reply)
    assert got == [("How long does a login token stay valid?", "backend/app/core/config.py:36"),
                   ("Where do emails go locally?", "compose.override.yml:84")], got


def test_loop_compact_readout():
    from ocm.loop import compact_readout
    many = "(readout: meaning)\n\n" + "\n\n".join(f"{i}. [corpus/a.py:{i}]\nline {i}" for i in range(1, 11))
    small = compact_readout(many)
    assert "3. [corpus/a.py:3]" in small and "4. [corpus/a.py:4]" not in small, small


def test_loop_readout_advances_after_the_taught_lane():
    from ocm.loop import readout
    calls = []
    def taught(path, **kw):
        calls.append(path)
        return "(readout: the code a taught question's vector points to)\n\n1. [a.py:3]\nX = 3" if path == "ask" else "(readout: meaning)\n\n1. [b.py:9]\nY = 4"
    out = readout(taught, "q")
    assert calls == ["ask", "next"] and "X = 3" in out and "Y = 4" in out
    calls.clear()
    plain = readout(lambda path, **kw: calls.append(path) or "(readout: meaning)\n\n1. [b.py:9]\nY = 4", "q")
    assert calls == ["ask"] and "Y = 4" in plain


def test_life_carries_taught_vectors_across_a_rebuild():
    """The Life remembers what was taught, exactly; a rebuild over moved code carries it to the new line, and an entry
    whose line is gone abstains."""
    root = tempfile.mkdtemp(); repo = os.path.join(root, "repo")
    shutil.copytree(os.path.join(HERE, "fixture_repo"), repo)
    old = os.path.join(root, "ws_old")
    build([repo], old, log=lambda *a: None)
    ws = Workspace(old)
    ws.handle("teach", {"pairs": [{"question": "How many times do we retry a failed card charge?", "at": "src/config.py:4"},
                                  {"question": "What currency do charges default to?", "at": "src/config.py:9"}]})
    st = json.loads(ws.handle("stats", {}))
    assert st["life"]["entries"] == 2 and st["question vectors taught"] == 2
    entry = json.loads(ws.life.recall("How many times do we retry a failed card charge?"))
    assert entry == {"at": "repo/src/config.py:4", "code": "MAX_CHARGE_RETRIES = 3"}, entry
    # the code moves: two lines inserted above the retry limit, and the currency line deleted
    p = os.path.join(repo, "src", "config.py"); lines = open(p).read().split("\n")
    lines = [l for l in lines if not l.startswith("DEFAULT_CURRENCY")]
    lines[1:1] = ["# Payments settings, reviewed every quarter.", ""]
    open(p, "w").write("\n".join(lines))
    new = os.path.join(root, "ws_new")
    build([repo], new, log=lambda *a: None, carry=old)
    nw = Workspace(new)
    moved = json.loads(nw.life.recall("How many times do we retry a failed card charge?"))
    assert moved["at"] == "repo/src/config.py:6", moved                            # found by its exact line
    assert len(nw.life.history("How many times do we retry a failed card charge?")) == 2   # old and new both kept
    assert json.loads(nw.handle("stats", {}))["question vectors taught"] == 1         # the gone line abstained
    again = nw.handle("ask", {"question": "what is the retry limit when a payment to a card fails?"})
    assert again.startswith("(readout: the code a taught question") and "MAX_CHARGE_RETRIES = 3" in again, again
    assert Workspace(new).life.sha() == nw.life.sha()                                  # byte-exact identity on disk


def test_carry_survives_reformatting_and_prunes_lines_gone_for_good():
    """A reformat (re-indented, spaced out) keeps a lesson: its line is found with whitespace ignored. A lesson whose
    line is gone counts its misses, and prune_after removes it once it has missed that many carries in a row."""
    root = tempfile.mkdtemp(); repo = os.path.join(root, "repo")
    shutil.copytree(os.path.join(HERE, "fixture_repo"), repo)
    ws0 = os.path.join(root, "ws0"); build([repo], ws0, log=lambda *a: None)
    Workspace(ws0).handle("teach", {"pairs": [{"question": "How many times do we retry a failed card charge?", "at": "src/config.py:4"},
                                              {"question": "What currency do charges default to?", "at": "src/config.py:9"}]})
    p = os.path.join(repo, "src", "config.py")
    lines = [l for l in open(p).read().split("\n") if not l.startswith("DEFAULT_CURRENCY")]
    lines = ["    MAX_CHARGE_RETRIES  =  3" if l == "MAX_CHARGE_RETRIES = 3" else l for l in lines]
    open(p, "w").write("\n".join(lines))
    ws1 = os.path.join(root, "ws1"); build([repo], ws1, log=lambda *a: None, carry=ws0)
    e = json.loads(Workspace(ws1).life.recall("How many times do we retry a failed card charge?"))
    assert e == {"at": "repo/src/config.py:4", "code": "    MAX_CHARGE_RETRIES  =  3"}, e     # found despite the reformat
    assert json.load(open(os.path.join(ws1, "carry_misses.json"))) == {"What currency do charges default to?": 1}
    ws2 = os.path.join(root, "ws2"); build([repo], ws2, log=lambda *a: None, carry=ws1, prune_after=2)
    w2 = Workspace(ws2)
    assert w2.life.recall("What currency do charges default to?") is None                         # pruned: 2 misses in a row
    assert w2.life.recall("How many times do we retry a failed card charge?") is not None
    assert json.load(open(os.path.join(ws2, "carry_misses.json"))) == {}


def test_a_cached_rebuild_is_bit_identical_and_reuses_every_embedding():
    import numpy as np, shutil
    from ocm.cmlm_vector.memory import Memory
    tmp = tempfile.mkdtemp(); repo = os.path.join(tmp, "app")
    shutil.copytree(os.path.join(HERE, "fixture_repo"), repo)
    cache = os.path.join(tmp, "embed.sqlite")
    build([repo], os.path.join(tmp, "cold"), log=lambda *_: None)
    build([repo], os.path.join(tmp, "warm1"), log=lambda *_: None, cache=cache)              # fills the cache
    with open(os.path.join(repo, "src", "config.py"), "a") as f:                             # the code changes a little
        f.write("\nNEW_SETTING = 7  # added after the first build\n")
    build([repo], os.path.join(tmp, "cold2"), log=lambda *_: None)
    out = []
    build([repo], os.path.join(tmp, "warm2"), log=out.append, cache=cache)
    def bits(ws):
        m = Memory(os.path.join(tmp, ws, "memory"))
        return list(m.texts), np.concatenate([np.asarray(s) for s in m.fshards])
    for cold, warm in (("cold", "warm1"), ("cold2", "warm2")):
        (ta, fa), (tb, fb) = bits(cold), bits(warm)
        assert ta == tb and np.array_equal(fa, fb)                                           # bit for bit
    assert "newly embedded, the rest from the cache" in out[-1]


def test_cover_teaches_every_piece_of_code_once_as_pointers_and_resumes():
    from types import SimpleNamespace as NS
    from ocm import cover
    out = os.path.join(tempfile.mkdtemp(), "ws")
    build([os.path.join(HERE, "fixture_repo")], out, log=lambda *a: None)
    ws = Workspace(out)
    todo = cover.units(ws)
    assert todo and all(ws.code[j] for j, _, _ in todo)
    asked = []

    class Fake:                                                                 # stands in for Claude Haiku
        def create(self, **kw):
            assert kw["model"] == cover.MODEL and kw["output_config"]["format"]["type"] == "json_schema"
            ids = [int(x.split('"')[0]) for x in kw["messages"][0]["content"].split('<block id="')[1:]]
            asked.extend(ids)
            qs = [{"id": j, "question": "How many times do we retry a failed card charge?" if "MAX_CHARGE_RETRIES" in ws.mem.texts[j]
                   else f"What does the code at unit {j} do?"} for j in ids]
            return NS(usage=NS(input_tokens=1000, output_tokens=100), content=[NS(type="text", text=json.dumps({"questions": qs}))])

    qfile = os.path.join(out, "cover.jsonl")
    usd = cover.write_questions(NS(messages=Fake()), ws, todo, qfile, cap=1.0, threads=2, log=lambda *a: None)
    assert sorted(asked) == sorted(j for j, _, _ in todo) and usd > 0
    units = len(ws.mem.texts)
    taught = cover.teach(ws, qfile, log=lambda *a: None)
    assert taught == len({q for q in map(lambda l: json.loads(l)["question"], open(qfile))})   # one pointer per distinct question
    assert len(ws.mem.texts) == units                                           # pointers only: no text is stored
    again = ws.handle("ask", {"question": "what is the retry limit when a payment to a card fails?", "scope": "code"})
    assert again.startswith("(readout: the code a taught question") and "MAX_CHARGE_RETRIES = 3" in again, again
    assert len(ws.life.store) == taught                                         # each recorded by its exact line, for a rebuild
    assert cover.teach(Workspace(out), qfile, log=lambda *a: None) == 0         # a second run teaches nothing twice

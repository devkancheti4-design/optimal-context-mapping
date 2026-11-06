"""The questions, written once and shipped with the data, so everyone answers the same ones. Picks each repository's facts from its pool (data/<repo>/pool.jsonl), in the
pool's fixed order, and gives each four wordings.

    taught     20: up to 8 changed, up to 4 moved, the rest the same; asked in sessions 1-4, in plain words that avoid the code's names
    sibling    up to 3: another parameter of a function a taught fact is about, never asked before session 2
    unrelated  the rest of 6: never asked before session 2
    named      4: asked in sessions 1 and 2 by the code's exact name, as a control: when a question names the code, a plain search is already cheap

Plain wordings come from one fixed prompt that sees the code at T0 and nothing about the benchmark's arms. A wording that uses the code's names or states the answer is rejected.

    <modeld python> -I wordings.py <repo> [--templates]    (--templates: no model calls, every wording from the named templates, for dry runs only)"""
import json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402
import grade as G  # noqa: E402
from arms import Model  # noqa: E402

TAUGHT, CHANGED, MOVED, NEW, SIBLINGS, NAMED = 20, 8, 4, 6, 3, 4
TEMPLATES = {
    "default": ("What is the default value of the `{p}` parameter of `{s}`?", "If I call `{s}` without passing `{p}`, what value does it use?",
                "`{s}` takes a `{p}` argument. What does it default to?", "What does `{p}` default to in `{s}`?"),
    "const": ("What is the value of `{s}`?", "What is `{s}` set to?", "In the code, which value is assigned to `{s}`?", "Which value does `{s}` have?"),
    "base": ("Which classes does `{s}` inherit from?", "What is the parent class of `{s}`?", "`{s}` is a subclass of what?", "What does the class `{s}` extend?"),
    "where": ("In which file is `{s}` defined?", "Where does `{s}` live in the repository? Give the file.", "Which file holds the definition of `{s}`?", "What is the path of the file that defines `{s}`?"),
}
FACT = {
    "default": "the parameter `{p}` of `{s}` defaults to {v}",
    "const": "`{s}` is set to {v}",
    "base": "the class `{s}` inherits from {v}",
    "where": "`{s}` is defined in the file {v}",
}
PROMPT = """Here is a piece of a code repository and one fact about it.

File: {path}
```python
{context}
```

Fact: {fact}

Write four different questions that a developer who has never seen this code might ask to find out this fact. Each question must ask for this one fact and must be answerable from the code with a short value. Describe the thing by what it does, in everyday words, not by its name. Vary the wording and the sentence structure from question to question.

Never use these words: {names}.
Never state the answer: {answer}.

Reply with only a JSON list of four strings."""


def shown(f):
    v = f["value"]
    return ", ".join(v) if isinstance(v, list) else v if f["kind"] == "where" else repr(v)


def names(f):
    out = f["subject"].split(".")
    if f["param"] and ("_" in f["param"] or f["param"] != f["param"].lower()):
        out.append(f["param"])
    return out


def leaks(f, q):
    if any(re.search(r"(?<!\w)" + re.escape(n) + r"(?!\w)", q, 0 if n.islower() else re.I) for n in names(f)):
        return True
    return f["kind"] != "where" and G.states(f["kind"], f["value"], q) or f["kind"] == "where" and f["value"].rsplit("/", 1)[-1] in q


def templated(f):
    return dict(zip("abcd", (t.format(p=f["param"], s=f["subject"]) for t in TEMPLATES[f["kind"]])))


def plain(model, f):
    """Four wordings, or None if two tries can't produce four clean ones."""
    prompt = PROMPT.format(path=f["path"], context=f["context"], fact=FACT[f["kind"]].format(p=f["param"], s=f["subject"], v=shown(f)), names=", ".join(names(f)), answer=shown(f))
    for _ in range(2):
        r = model._post(model.reader, {"contents": [{"role": "user", "parts": [{"text": prompt}]}]})
        text = " ".join(p.get("text", "") for p in ((r.get("candidates") or [{}])[0].get("content") or {}).get("parts") or [])
        try:
            qs = json.loads(text[text.index("["):text.rindex("]") + 1])
        except ValueError:
            continue
        if isinstance(qs, list) and len(qs) == 4 and all(isinstance(q, str) and q.strip() for q in qs) and len(set(qs)) == 4 and not any(leaks(f, q) for q in qs):
            return dict(zip("abcd", (" ".join(q.split()) for q in qs)))
    return None


def choose(pool, word):
    """Facts with their role and wordings, in the pool's order. word(fact) returns wordings or None."""
    out, used, subjects = [], set(), set()

    def take(f, role, wordings):
        out.append({**f, "role": role, "wordings": wordings}); used.add(f["id"]); subjects.add(f["subject"])

    def pick(want, role, test, wording=word):
        n = 0
        for f in pool:
            if n >= want:
                break
            if f["id"] not in used and test(f):
                w = wording(f)
                if w:
                    take(f, role, w); n += 1
        return n

    changed = pick(CHANGED, "taught", lambda f: f["status"] == "changed")
    moved = pick(MOVED, "taught", lambda f: f["status"] == "moved")
    pick(TAUGHT - changed - moved, "taught", lambda f: f["status"] == "same" and f["t1_status"] == "same")
    taught_subjects = {f["subject"] for f in out if f["kind"] == "default"}
    sib = pick(SIBLINGS, "sibling", lambda f: f["kind"] == "default" and f["status"] == "same" and f["subject"] in taught_subjects)
    pick(NEW - sib, "unrelated", lambda f: f["status"] == "same" and f["subject"] not in subjects)
    pick(NAMED, "named", lambda f: f["status"] == "same" and f["subject"] not in subjects, templated)
    return out


def main(repo, templates=False):
    pool = C.rows(C.data(repo, "pool.jsonl"))
    model = None if templates else Model()
    chosen = choose(pool, templated if templates else lambda f: plain(model, f))
    with open(C.data(repo, "facts.jsonl"), "w") as o:
        for f in chosen:
            o.write(json.dumps(f) + "\n")
    count = {}
    for f in chosen:
        count[(f["role"], f["status"])] = count.get((f["role"], f["status"]), 0) + 1
    print(repo, len(chosen), "facts", {f"{a}/{b}": n for (a, b), n in sorted(count.items())}, f"spent ${C.spent():.3f}", flush=True)


if __name__ == "__main__":
    main(sys.argv[1], "--templates" in sys.argv)

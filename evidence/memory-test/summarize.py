"""Recompute every number in RESULTS.md from the files memtest.py wrote (data/memtest) and its question plan.

    python evidence/memory-test/summarize.py

Standard library only. A lesson "opens" when the readout is the code a taught question's vector points to (the
CERTIFIED lane); "answer line" means the line that answers the question appears in the readout."""
import hashlib, json, os, re

H = os.path.dirname(os.path.abspath(__file__)); D = f"{H}/data/memtest"
PLAN = json.load(open(f"{H}/memtest_questions.json"))
REPOS = list(PLAN["repos"])
load = lambda name: json.load(open(f"{D}/{name}.json"))


def pairs(repo, phase, qs):
    """(question, same-words row, other-words row) for every question asked in that phase."""
    rows = load(f"{repo}.{phase}"); assert len(rows) == 2 * len(qs)
    for i, q in enumerate(qs):
        s, o = rows[2 * i], rows[2 * i + 1]; assert s["q"] == q["q"] and o["q"] == q["other"]
        yield q, s, o


def main():
    sha = hashlib.sha256(open(f"{H}/memtest_questions.json", "rb").read()).hexdigest()
    print(f"question plan sha256 {sha[:16]}..., recorded at the run: {open(f'{D}/questions.sha256').read().strip() == sha}")
    total = {}
    add = lambda k, v: total.__setitem__(k, total.get(k, 0) + v)
    for repo in REPOS:
        spec = PLAN["repos"][repo]; qs = spec["questions"]; b = load(f"{repo}.build")
        teach = load(f"{repo}.teach"); taught = [not t["reply"].startswith("taught 0") for t in teach]
        print(f"\n{repo}: {spec['url']}, {spec['t0']} -> {spec['t2']}: {b['commits_between']} commits, {b['diff']}")
        units = [re.search(r"\(([\d,]+) units from (\d+) files", l).groups() for x in b["builds"] for l in x["lines"] if "units from" in l]
        print(f"  maps: {units[0][0]} units from {units[0][1]} files then, {units[2][0]} from {units[2][1]} now")
        print(f"  {len(qs)} questions; the answer changed by now for {sum(q['t0'] != q['t2'] for q in qs)}")
        print(f"  teach placed {sum(taught)} of {len(qs)}; refused: {', '.join(q['at'] for q, t in zip(qs, taught) if not t)}")
        add("questions", len(qs)); add("placed", sum(taught))
        for phase in ("cold", "next", "mate", "copy", "later", "fresh"):
            key = "t2" if phase in ("later", "fresh") else "t0"
            P = list(pairs(repo, phase, qs))
            line_s = sum(s["line_in_readout"] for _, s, _ in P); line_o = sum(o["line_in_readout"] for _, _, o in P)
            open_s = sum(s["opens"] and t for (_, s, _), t in zip(P, taught)); open_o = sum(o["opens"] and t for (_, _, o), t in zip(P, taught))
            wrong = sum((r["opens"] and not r["line_in_readout"]) for _, s, o in P for r in (s, o))
            old = sum(r["old_answer_shown"] for _, s, o in P for r in (s, o))
            tok = round(sum(s["tokens"] for _, s, _ in P) / len(P))
            print(f"  {phase:6} answer line: same words {line_s:2}/{len(qs)}, other words {line_o:2}/{len(qs)};"
                  f" lessons opened: same {open_s:2}/{sum(taught)}, other {open_o:2}/{sum(taught)}; opened on a wrong line {wrong};"
                  f" old answer shown {old}; {tok} tokens (same words)")
            for k, v in (("line_s", line_s), ("line_o", line_o), ("open_s", open_s), ("open_o", open_o), ("wrong", wrong), ("old", old)):
                add(f"{phase}.{k}", v)
            if phase == "later":
                for (q, s, _), t in zip(P, taught):
                    if t and not s["opens"]:
                        print(f"    stepped aside: {q['kind']} at {q['at']}; answer changed: {q['t0'] != q['t2']}")
                        add("aside", 1); add("aside_changed", q["t0"] != q["t2"])
        carry = [l for x in b["builds"] for l in x["lines"] if l.startswith("carried")]
        print(f"  carried, teammate's build: {carry[0].split(': ')[1].split(';')[0]}")
        print(f"  carried, a year later:     {carry[1].split(': ')[1].split(';')[0]}")
        print(f"  a lesson with no line in the repository: {load(f'{repo}.notes')['reply'][:52]}")
        rec = load(f"{repo}.recite")
        print(f"  refused lessons cited again with the folder name in front: placed {sum(not r['reply'].startswith('taught 0') for r in rec)} of {len(rec)}")
        add("recited", len(rec)); add("recited_placed", sum(not r["reply"].startswith("taught 0") for r in rec))
    t = total; n, p = t["questions"], t["placed"]
    print("\nBoth repositories")
    print(f"  teach placed {p} of {n}; {t['recited_placed']} of the {t['recited']} refused were placed when cited with the folder name")
    for phase in ("cold", "next", "mate", "copy", "later", "fresh"):
        print(f"  {phase:6} answer line {t[phase + '.line_s']}/{n} same words, {t[phase + '.line_o']}/{n} other words;"
              f" lessons opened {t[phase + '.open_s']}/{p} same, {t[phase + '.open_o']}/{p} other; wrong line {t[phase + '.wrong']}; old answer {t[phase + '.old']}")
    print(f"  a year later: {p - t['aside']} of {p} lessons kept; {t['aside']} stepped aside, {t['aside_changed']} of them because the answer changed")
    c = json.load(open(f"{D}/cli.json"))
    print(f"\nThe real command line ({c['repo']}), each call its own process:")
    for x in c["calls"]:
        print(f"  modeld {x['args'][0]:<5} -> {x['out'].splitlines()[0][:120]}")


if __name__ == "__main__":
    main()

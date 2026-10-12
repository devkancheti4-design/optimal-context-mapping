"""PROTOCOL_MODEL_D.md: the brain's readouts (replayed), the eyes' one-call answers on the taught lane, the eyes' picks among
neo4d's verified candidates, and the brain-only fixes, checked by the tests.

    ~/.venvs/cmlm-live/bin/python brain_eyes.py      -> eyes.json"""
import json, os, re, shutil, subprocess, sys, tempfile, threading, warnings
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
warnings.filterwarnings("ignore")
os.environ.setdefault("OCM_OFFLINE", "1"); os.environ.setdefault("HF_HUB_OFFLINE", "1"); os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
H = Path(os.path.dirname(os.path.abspath(__file__))); B = H.parent
sys.path.insert(0, os.path.expanduser("~/optimal-context-mapping")); sys.path.insert(0, str(B / "api")); sys.path.insert(0, str(B / "reports"))
sys.argv = sys.argv[:1]
import api_bench as AB
from common import usd
from ocm.server import Workspace
from ocm.loop import readout, teach_lines

URL = AB.url_for(1)
QS = json.load(open(os.path.expanduser("~/cmlm-bench5/questions.json"))); FACT = {q["qid"]: q for q in QS}
STREAM = [(q["qid"], q["question"]) for q in QS] + [(q["qid"] + "b", q["question2"]) for q in QS]
TAUGHT = "(readout: the code a taught question"
EYES_Q = ("You answer questions about the Hugging Face transformers codebase. Answer the question from the code below only, "
          "in one short sentence. If the code below does not contain the answer, reply exactly NEED_SEARCH.")
EYES_FIX = ("A Python program has exactly one bug. A fix engine has found candidate one-line fixes, each of which makes the "
            "program's tests pass. Pick the one that matches the program's intended behaviour. Reply with the candidate's number only.")


def replay():
    teach = {}
    for t in range(1, 7):
        for line in open(B / f"large/agents/cmlm_t{t:02d}/answers.jsonl"):
            d = json.loads(line); teach[d["qid"]] = d.get("teach") or ""
    tmp = tempfile.mkdtemp(); d = os.path.join(tmp, "ws"); shutil.copytree(B / "large/ws_L_base", d); w = Workspace(d)
    out = []
    for qid, q in STREAM:
        text = readout(lambda path, **kw: w.handle(path, kw), q)
        out.append({"qid": qid, "question": q, "readout": text, "taught lane": text.startswith(TAUGHT)})
        pairs = teach_lines(teach.get(qid, ""))
        if pairs:
            w.handle("teach", {"pairs": [{"question": a, "at": b} for a, b in pairs]})
    shutil.rmtree(tmp)
    return out


def eyes_question(item, run):
    body = {"systemInstruction": {"parts": [{"text": EYES_Q}]},
            "contents": [{"role": "user", "parts": [{"text": f"Question: {item['question']}\n\nCode:\n{item['readout']}"}]}]}
    r, dt, tries = AB.call(body, URL)
    u = r.get("usageMetadata", {}); parts = ((r.get("candidates") or [{}])[0].get("content") or {}).get("parts") or []
    text = " ".join(p.get("text", "") for p in parts).strip()
    rec = {"qid": item["qid"], "run": run, "answer": text, "need_search": "NEED_SEARCH" in text, "seconds": round(dt, 2),
           "prompt": u.get("promptTokenCount", 0), "cached": u.get("cachedContentTokenCount", 0), "output": u.get("candidatesTokenCount", 0), "thoughts": u.get("thoughtsTokenCount", 0)}
    rec["usd"] = usd(rec)
    return rec


FIX = json.load(open(B / "fix/neo4d_fixes.json")); N4 = Path(os.path.expanduser("~/neeeos/neo4d"))
PY = N4 / "bench" / "tvenv" / "bin" / "python"


def tests(work, name, program):
    p = work / "python_programs" / f"{name}.py"; orig = p.read_text()
    try:
        p.write_text(program)
        r = subprocess.run([str(PY), "-m", "pytest", f"python_testcases/test_{name}.py", "-q", "-x", "-p", "no:cacheprovider", "--timeout=3"],
                           cwd=work, capture_output=True, timeout=120)
        return r.returncode == 0
    except subprocess.TimeoutExpired:
        return False
    finally:
        p.write_text(orig)


def apply(prog, line_no, after):
    lines = prog.split("\n"); indent = lines[line_no - 1][:len(lines[line_no - 1]) - len(lines[line_no - 1].lstrip())]
    lines[line_no - 1] = indent + after
    return "\n".join(lines)


def fixes(work):
    out = {"brain only (repaired)": [], "eyes pick (ambiguous)": []}
    for r in FIX["rows"]:
        name = r["program"]; prog = (work / "python_programs" / f"{name}.py").read_text()
        if r.get("outcome") == "repaired":
            g = r["greens"][0]
            out["brain only (repaired)"].append({"program": name, "requests": 0, "fixed": tests(work, name, apply(prog, g["line"], g["after"]))})
        elif r.get("outcome") == "ambiguous":
            cands = sorted({(g["line"], g["before"], g["after"]) for g in r["greens"]})
            listing = "\n".join(f"{i + 1}. line {l}: `{b}` -> `{a}`" for i, (l, b, a) in enumerate(cands))
            for run in (1, 2, 3):
                body = {"systemInstruction": {"parts": [{"text": EYES_FIX}]},
                        "contents": [{"role": "user", "parts": [{"text": f"Program python_programs/{name}.py:\n```python\n{prog}\n```\n\nCandidates:\n{listing}"}]}]}
                resp, dt, tries = AB.call(body, URL)
                u = resp.get("usageMetadata", {}); parts = ((resp.get("candidates") or [{}])[0].get("content") or {}).get("parts") or []
                text = " ".join(p.get("text", "") for p in parts).strip(); m = re.search(r"\d+", text)
                k = int(m.group()) - 1 if m else -1
                ok = 0 <= k < len(cands) and tests(work, name, apply(prog, cands[k][0], cands[k][2]))
                rec = {"program": name, "run": run, "picked": k + 1, "of": len(cands), "fixed": ok, "requests": 1,
                       "prompt": u.get("promptTokenCount", 0), "cached": u.get("cachedContentTokenCount", 0), "output": u.get("candidatesTokenCount", 0), "thoughts": u.get("thoughtsTokenCount", 0)}
                rec["usd"] = usd(rec); out["eyes pick (ambiguous)"].append(rec)
    return out


def main():
    items = replay()
    print("replayed", len(items), "taught lane", sum(i["taught lane"] for i in items), flush=True)
    lane = [i for i in items if i["taught lane"]]
    with ThreadPoolExecutor(6) as ex:
        eyes = list(ex.map(lambda a: eyes_question(*a), [(i, run) for run in (1, 2, 3) for i in lane]))
    print("eyes calls", len(eyes), "need_search", sum(e["need_search"] for e in eyes), flush=True)
    work = H / "qb"
    if work.exists(): shutil.rmtree(work)
    shutil.copytree(N4 / "bench" / "QuixBugs", work, ignore=shutil.ignore_patterns(".git", "java_*", "correct_java_programs", "*.class"))
    fx = fixes(work); shutil.rmtree(work)
    out = {"protocol sha256": json.load(open(B / "prereg_hashes.json"))["PROTOCOL_MODEL_D.md"]["sha256"],
           "readouts": items, "eyes questions": eyes, "fixes": fx}
    json.dump(out, open(H / "eyes.json", "w"), indent=1)
    print("brain-only fixes", [(x["program"], x["fixed"]) for x in fx["brain only (repaired)"]])
    print("eyes picks", [(x["program"], x["run"], x["picked"], x["fixed"]) for x in fx["eyes pick (ambiguous)"]])


if __name__ == "__main__":
    main()

"""Session B prompts: a reworded question in a fresh session (run with the modeld venv).
base: the task alone. mdcold: Model D's hook readout from a workspace nobody has taught.
mdmem: Model D's hook readout from the shared workspace after session A's TEACH lines were taught, as its Stop hook
does (ocm.loop.teach_lines on each line, then the workspace's teach)."""
import json, os, shutil, sys, uuid
sys.path.insert(0, os.path.dirname(__file__))
from ocm.server import Workspace
from ocm import loop

B = "~/eval/bench"
A = "~/eval/agentsnaps"
TASK = ("Locate the code responsible for this behaviour in the repository at {root} (the text comes from a teammate's "
        "question): \"{q}\"\n\nWork only inside {root}; read-only, do not edit or create files there. Reply with the "
        "first line exactly `ANSWER: <path relative to {root}>:<line> <function or symbol>`, naming the single most likely "
        "place, then at most three sentences of explanation.")
sets = json.load(open(f"{B}/agent_set.json"))
reworded = dict(l.rstrip("\n").split("\t", 1) for l in open(f"{B}/reworded.tsv") if l.strip())
teach = {int(i): (q, at) for i, q, at in (l.rstrip("\n").split("\t") for l in open(f"{B}/teach_lines.tsv") if l.strip())}

cold, mem = {}, {}
for r in ("aiohttp", "fastify", "zod"):
    src = f"{B}/work/agent_ws_{r}"
    for name, d in (("cold", cold), ("mem", mem)):
        dst = f"{B}/work/agent_ws_{r}_{name}"
        shutil.rmtree(dst, ignore_errors=True); shutil.copytree(src, dst)
        d[r] = Workspace(dst)
replies = {}
for i, (q, at) in teach.items():
    r = sets[i]["repo"]
    pairs = loop.teach_lines(f"TEACH: {q} | {at}")            # the exact parse the Stop hook applies to a reply
    replies[i] = mem[r].handle("teach", {"pairs": [{"question": a, "at": b} for a, b in pairs]})[:90]

out, paths = [], {}
for i, s in enumerate(sets):
    r, q = s["repo"], reworded[str(i)]
    user = f"Locate the code responsible for this behaviour: \"{q}\""
    prompts = {"base": TASK.format(root=f"{A}/{r}_base", q=q)}
    for name, w in (("mdcold", cold[r]), ("mdmem", mem[r])):
        ro = loop.readout(lambda path, **kw: w.handle(path, {**kw, "scope": "code"}), user)
        prompts[name] = (f"{TASK.format(root=f'{A}/{r}_md', q=q)}\n\n<user-prompt-submit-hook>\n{loop.HEADER}\n\n{ro}\n\n"
                         f"{loop.RULE}\n</user-prompt-submit-hook>")
    led = prompts["mdmem"].split("(readout: ", 1)[1][:40]
    out.append({**s, "reworded": q, "mem_readout_starts": led, "taught": replies.get(i)})
    for c, p in prompts.items():
        d = f"~/eval/agentprompts/{uuid.uuid4().hex[:12]}"
        os.makedirs(d); open(f"{d}/task.txt", "w").write(p); paths[f"{i}_{c}"] = f"{d}/task.txt"
json.dump(out, open(f"{B}/agent_set_b.json", "w"), indent=1)
json.dump(paths, open(f"{B}/agent_prompt_paths_b.json", "w"), indent=1)
for o in out:
    print(o["i"], o["repo"], "| mem readout:", o["mem_readout_starts"].split(")")[0], "|", o["reworded"][:70])
print("teach replies:", sorted({v[:40] for v in replies.values()}))

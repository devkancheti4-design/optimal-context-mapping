"""Build the three prompts per question for the agent test (run with the modeld venv).
base: the task alone. md: the task plus exactly what Model D's UserPromptSubmit hook adds (ocm.loop.prefetch, scope code).
gf: the task plus the CLAUDE.md block `graphify claude install` writes, with graphify on the path."""
import json, os, shutil, sys
sys.path.insert(0, os.path.dirname(__file__))
from ocm.build import build
from ocm.server import Workspace
from ocm import loop

A = "~/eval/agentsnaps"
GF = "~/eval/envs/graphify/bin/graphify"
GF_MD = open("~/eval/repos/graphify/graphify/always_on/claude-md.md").read()
TASK = ("Locate the code responsible for this behaviour in the repository at {root} (the text comes from one of its past "
        "bug fixes): \"{q}\"\n\nWork only inside {root}; read-only, do not edit or create files there. Reply with the "
        "first line exactly `ANSWER: <path relative to {root}>:<line> <function or symbol>`, naming the single most likely "
        "place, then at most three sentences of explanation.")
sets = json.load(open("~/eval/bench/agent_set.json"))
ws = {}
out = []
for s in sets:
    r = s["repo"]
    if r not in ws:
        d = f"~/eval/bench/work/agent_ws_{r}"
        shutil.rmtree(d, ignore_errors=True)
        build([f"{A}/{r}_md"], d, log=lambda *a: None, cache=f"~/eval/bench/work/m_{r}/embed.sqlite")
        ws[r] = Workspace(d)
    w = ws[r]
    base = TASK.format(root=f"{A}/{r}_base", q=s["question"])
    md_task = TASK.format(root=f"{A}/{r}_md", q=s["question"])
    call = lambda path, **kw: w.handle(path, {**kw, "scope": "code"})
    # The hook sees the user's message; the answer-format boilerplate stands in for project instructions, not the prompt.
    readout = loop.readout(call, f"Locate the code responsible for this behaviour: \"{s['question']}\"")
    md = f"{md_task}\n\n<user-prompt-submit-hook>\n{loop.HEADER}\n\n{readout}\n\n{loop.RULE}\n</user-prompt-submit-hook>"
    gf_root = f"{A}/{r}_gf"
    gf = (f"{TASK.format(root=gf_root, q=s['question'])}\n\nProject instructions ({gf_root}/CLAUDE.md):\n\n{GF_MD}\n"
          f"The graphify command is {GF}; run it from {gf_root}.")
    out.append({**s, "prompts": {"base": base, "md": md, "gf": gf}, "md_readout_tokens": len(readout) // 4})
json.dump(out, open("~/eval/bench/agent_prompts.json", "w"), indent=1)
print("prompts ready", [o["md_readout_tokens"] for o in out])

"""PROTOCOL_COVERAGE generation: one question per non-test code unit of ws/base, by Claude Haiku 5.5, 25 units per call.

    python coverage_gen.py ws/base coverage_questions.jsonl --cap 6

Writes {"unit": j, "path": ..., "question": ...} lines; a stop resumes. The key is read from ../.env and never printed."""
import json, os, sys, threading
from concurrent.futures import ThreadPoolExecutor
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.expanduser("~/optimal-context-mapping"))
for line in open(os.path.join(ROOT, ".env")):
    if line.startswith("ANTHROPIC_API_KEY=") and line.split("=", 1)[1].strip():
        os.environ["ANTHROPIC_API_KEY"] = line.split("=", 1)[1].strip()
import anthropic  # noqa: E402
from ocm.server import Workspace  # noqa: E402

ws_dir, out, cap = sys.argv[1], sys.argv[2], float(sys.argv[4])
w = Workspace(ws_dir); m = w.mem
path = lambda j: m.sources[m.src[j]]["path"] if m.src[j] >= 0 else ""
units = [j for j in range(min(len(w.code), len(m.texts))) if w.code[j] and "/tests/" not in path(j) and not path(j).split("/")[-1].startswith("test")]
done = {json.loads(l)["unit"] for l in open(out)} if os.path.exists(out) else set()
todo = [j for j in units if j not in done]
print(f"{len(units)} non-test code units; {len(todo)} to write", flush=True)
SYS = ("You write questions for a code search benchmark. For each code block, write the one question a developer on this "
       "codebase would ask whose answer is in this block, in the words of a bug report or a how/where/why question, at "
       "most 25 words. Use the names in the code only where a developer would. Return every block's id.")
SCHEMA = {"type": "object", "properties": {"questions": {"type": "array", "items": {"type": "object", "properties": {
    "id": {"type": "integer"}, "question": {"type": "string"}}, "required": ["id", "question"], "additionalProperties": False}}},
    "required": ["questions"], "additionalProperties": False}
client = anthropic.Anthropic(max_retries=4); lock = threading.Lock(); spent = [0.0]


def batch(js):
    if spent[0] >= cap:
        return
    blocks = "\n\n".join(f"<block id=\"{j}\" file=\"{path(j)}\">\n{m.texts[j][:1200]}\n</block>" for j in js)
    r = client.messages.create(model="claude-haiku-5-5", max_tokens=8000, system=SYS,
                               messages=[{"role": "user", "content": blocks}],
                               output_config={"format": {"type": "json_schema", "schema": SCHEMA}})
    usd = (r.usage.input_tokens * 0.10 + r.usage.output_tokens * 0.50) / 1e6
    text = next((b.text for b in r.content if b.type == "text"), "{}")
    try:
        qs = {int(x["id"]): x["question"] for x in json.loads(text)["questions"]}
    except (ValueError, KeyError):
        qs = {}
    with lock:
        spent[0] += usd
        with open(out, "a") as f:
            for j in js:
                if j in qs and qs[j].strip():
                    f.write(json.dumps({"unit": j, "path": path(j), "question": " ".join(qs[j].split())}) + "\n")


chunks = [todo[i:i + 25] for i in range(0, len(todo), 25)]
with ThreadPoolExecutor(8) as ex:
    for i, _ in enumerate(ex.map(batch, chunks)):
        if i % 100 == 0:
            print(f"  {i}/{len(chunks)} batches, ${spent[0]:.3f}", flush=True)
print(f"done: ${spent[0]:.3f}", flush=True)

"""The official SWR-Bench judge (evaluation_struct.evaluate, its prompts, schemas and parsing unchanged) with its one
model call sent to Claude Haiku 5.5 through the Anthropic SDK instead of an OpenAI-compatible endpoint (deviation D3).

    python judge_claude.py <reviews.jsonl> <judged.jsonl> [--threads N] [--cap USD]

The judge's own JSON schema (OpenAI response_format) becomes Claude's output_config json_schema. No temperature is sent
(Haiku 5.5 rejects non-default sampling parameters). Usage and spend are written to <judged>.usage.json; the run stops
taking new calls at the cap. The key is read from ../.env (ANTHROPIC_API_KEY) and never printed."""
import argparse, json, os, sys, threading, time

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
os.environ.setdefault("OPENAI_API_BASE", "unused-by-the-claude-judge"); os.environ.setdefault("OPENAI_API_KEY", "unused")
sys.path.insert(0, os.path.join(ROOT, "vendor", "SWRench", "swrbench"))
import evaluation_struct as E  # noqa: E402
import anthropic  # noqa: E402

JUDGE = "claude-haiku-5-5"
PRICE_IN, PRICE_OUT = 0.10, 0.50                     # $ per million tokens (prompts under 100K tokens)
lock, usage = threading.Lock(), {"requests": 0, "input_tokens": 0, "output_tokens": 0, "usd": 0.0, "errors": 0}


def key():
    for line in open(os.path.join(ROOT, ".env")):
        if line.startswith("ANTHROPIC_API_KEY=") and line.split("=", 1)[1].strip():
            return line.split("=", 1)[1].strip()
    raise SystemExit("ANTHROPIC_API_KEY is empty in swr-pilot/.env")


def make_run_chat(client, cap, usage_file):
    def run_chat(model, messages, temperature=None, max_tokens=None, response_format=None, max_retries=5):
        if usage["usd"] >= cap:
            return None
        system = "\n".join(m["content"] for m in messages if m["role"] == "system") or None
        kw = {"model": JUDGE, "max_tokens": max(16000, max_tokens or 0),
              "messages": [{"role": m["role"], "content": m["content"]} for m in messages if m["role"] != "system"]}
        if system:
            kw["system"] = system
        if response_format and response_format.get("type") == "json_schema":
            kw["output_config"] = {"format": {"type": "json_schema", "schema": response_format["json_schema"]["schema"]}}
        for attempt in range(max_retries):
            try:
                with client.messages.stream(**kw) as s:
                    m = s.get_final_message()
                with lock:
                    usage["requests"] += 1; usage["input_tokens"] += m.usage.input_tokens
                    usage["output_tokens"] += m.usage.output_tokens
                    usage["usd"] += m.usage.input_tokens * PRICE_IN / 1e6 + m.usage.output_tokens * PRICE_OUT / 1e6
                    json.dump(usage, open(usage_file, "w"), indent=1)
                if m.stop_reason in ("refusal", "max_tokens"):
                    return None
                return next((b.text for b in m.content if b.type == "text"), None)
            except anthropic.APIError as e:
                with lock:
                    usage["errors"] += 1
                if isinstance(e, anthropic.BadRequestError):
                    print(f"judge: bad request: {str(e)[:300]}", flush=True); return None
                time.sleep(2 * 2 ** attempt)
        return None
    return run_chat


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("pred"); ap.add_argument("out")
    ap.add_argument("--threads", type=int, default=4); ap.add_argument("--cap", type=float, default=2.0)
    ap.add_argument("--ids", nargs="+")
    a = ap.parse_args()
    client = anthropic.Anthropic(api_key=key(), max_retries=4)
    E.run_chat = make_run_chat(client, a.cap, os.path.abspath(a.out) + ".usage.json")
    args = argparse.Namespace(dataset_file=os.path.join(ROOT, "vendor", "SWRench", "data", "swr_datasets_d5c5.jsonl"),
                              pred_file=os.path.abspath(a.pred), output_file=os.path.abspath(a.out), model=JUDGE,
                              instance_ids=a.ids, ignore_ids=None, num_threads=a.threads, temperature=0.0,
                              max_tokens=16000, overwrite=False)
    E.evaluate(args)
    print(json.dumps(usage), flush=True)


if __name__ == "__main__":
    main()

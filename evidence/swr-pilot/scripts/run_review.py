"""Reviews for arm A (the paper's base prompt) or arm B (A plus Model D's readout), per PROTOCOL_SWR_PILOT.md.

    python run_review.py A|B <dataset.jsonl> <pilot_set.json> <contexts.jsonl> <out.jsonl> --cap USD [--dry-run]

The prompt is SWR-Bench's generate_task_base prompt, built by its own create_prinfo_prompt; arm B adds one block after
the code changes. The key is read from ../.env (ANTHROPIC_API_KEY) and never printed. A stop resumes: PRs already in the
output are skipped. --dry-run sends nothing and prints the prompt sizes and the estimated cost."""
import argparse, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
os.environ.setdefault("OPENAI_API_BASE", "unused-by-the-reviewer"); os.environ.setdefault("OPENAI_API_KEY", "unused")
sys.path.insert(0, os.path.join(ROOT, "vendor", "SWRench", "swrbench"))   # it imports its helpers as top-level modules
from generation import create_prinfo_prompt  # noqa: E402

MODEL = "claude-sonnet-5-5"
PRICE_IN, PRICE_OUT = 2.00, 10.00            # $ per million tokens, optimal-context-mapping/scripts/live_api_test.py

TEMPLATE = (
    "You are a senior project manager at a leading tech company, entrusted with maintaining the high standards of the codebase. A developer has submitted a pull request, and it’s your responsibility to review it thoroughly to ensure it meets the company’s quality and functionality requirements.\n"
    "Your task is to review the provided pull request, which includes the title, description, and code changes. You need to assess whether the pull request meets the standards for a good pull request or if there are any issues that need to be addressed.\n"
    "**Response Format**: In your response, please provide a brief summary of your assessment. Ensure your feedback is constructive and actionable. If you find no issues, please explicitly state that the pull request looks good and meets the standards.\n"
    "**Note**: The goal of this review is to maintain code quality and support the developer. Please provide respectful, specific, and helpful feedback to foster a collaborative environment. \n"
    "<Start of Pull Request Details>\n"
    "{prinfo}\n"
    "<End of Pull Request Details>\n"
)


def prompt_for(arm, item, ctx):
    prinfo = create_prinfo_prompt(item)
    if arm == "B":
        prinfo += f"- **Related Code in the Repository** (selected by a context tool): \n{ctx[item['instance_id']]['readout']} \n"
    return TEMPLATE.format(prinfo=prinfo)


def key_from_env_file():
    for line in open(os.path.join(ROOT, ".env")):
        if line.startswith("ANTHROPIC_API_KEY="):
            k = line.split("=", 1)[1].strip()
            if k:
                return k
    raise SystemExit("ANTHROPIC_API_KEY is empty in swr-pilot/.env")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("arm", choices=["A", "B"]); ap.add_argument("dataset"); ap.add_argument("pilot"); ap.add_argument("contexts")
    ap.add_argument("out"); ap.add_argument("--cap", type=float, required=True); ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--ready-only", action="store_true", help="arm B: review only PRs whose context exists; rerun later for the rest")
    a = ap.parse_args()
    rows = {}
    for line in open(a.dataset):
        r = json.loads(line); rows[r["instance_id"]] = r
    ids = [p["instance_id"] for p in json.load(open(a.pilot))["instances"]]
    ctx = {json.loads(l)["instance_id"]: json.loads(l) for l in open(a.contexts)} if os.path.exists(a.contexts) else {}
    if a.arm == "B":
        missing = [i for i in ids if i not in ctx]
        if missing and not a.ready_only:
            raise SystemExit(f"{len(missing)} PRs have no Model D context yet")
        ids = [i for i in ids if i in ctx]
    if a.dry_run:
        n = [len(prompt_for(a.arm, rows[i], ctx)) // 4 for i in ids]
        est = sum(n) * PRICE_IN / 1e6 + len(ids) * 1500 * PRICE_OUT / 1e6
        print(f"arm {a.arm}: {len(ids)} prompts, ~{sum(n) / len(n):,.0f} input tokens each (max {max(n):,}); "
              f"estimated ${est:.2f} at ~1,500 output tokens per review")
        return
    import anthropic
    client = anthropic.Anthropic(api_key=key_from_env_file())
    done = {json.loads(l)["instance_id"] for l in open(a.out)} if os.path.exists(a.out) else set()
    spent = sum(json.loads(l).get("usd", 0) for l in open(a.out)) if os.path.exists(a.out) else 0.0
    for i in ids:
        if i in done:
            continue
        if spent >= a.cap:
            print(f"stopped at the cap: ${spent:.4f} of ${a.cap:.2f}"); break
        p = prompt_for(a.arm, rows[i], ctx)
        try:
            with client.messages.stream(model=MODEL, max_tokens=8192, messages=[{"role": "user", "content": p}]) as s:
                m = s.get_final_message()
        except anthropic.APIError as e:
            print(f"{i}: API error {type(e).__name__}: {str(e)[:200]}"); continue
        text = "".join(b.text for b in m.content if b.type == "text")
        usd = m.usage.input_tokens * PRICE_IN / 1e6 + m.usage.output_tokens * PRICE_OUT / 1e6
        spent += usd
        with open(a.out, "a") as f:
            f.write(json.dumps({"instance_id": i, "arm": a.arm, "model": MODEL, "prompt": p, "response": text, "review": text,
                                "stop_reason": m.stop_reason, "input_tokens": m.usage.input_tokens,
                                "output_tokens": m.usage.output_tokens, "usd": round(usd, 6)}) + "\n")
        print(f"{i:<34} in {m.usage.input_tokens:>6,}  out {m.usage.output_tokens:>5,}  ${usd:.4f}  total ${spent:.4f}", flush=True)


if __name__ == "__main__":
    main()

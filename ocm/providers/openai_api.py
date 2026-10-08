"""OpenAI models for the hybrid, through the official OpenAI SDK (pip install openai) and its Chat Completions tool
calling. Key: OPENAI_API_KEY. Model names are set with --reader / --teacher (or OCM_OPENAI_READER / OCM_OPENAI_TEACHER)."""
import json, os


class OpenAIProvider:
    def __init__(self, reader=None, teacher=None):
        from openai import OpenAI
        self.client = OpenAI()
        self.reader = reader or os.environ.get("OCM_OPENAI_READER", "gpt-5.6-terra")
        self.teacher = teacher or os.environ.get("OCM_OPENAI_TEACHER", "gpt-5.6-terra")

    def read(self, system, question, code):
        r = self.client.chat.completions.create(model=self.reader, messages=[
            {"role": "system", "content": system}, {"role": "user", "content": f"Question: {question}\n\nCode:\n{code}"}])
        return r.choices[0].message.content or ""

    def teach(self, system, question, code, tools, run_tool, max_calls):
        spec = [{"type": "function", "function": {"name": t["name"], "description": t["description"], "parameters": t["parameters"]}} for t in tools]
        messages = [{"role": "system", "content": system},
                    {"role": "user", "content": f"Question: {question}\n\nThe code the team's workspace ranked for it:\n{code}"}]
        calls = n = 0
        while n < max_calls + 10:
            r = self.client.chat.completions.create(model=self.teacher, messages=messages, tools=spec)
            n += 1
            m = r.choices[0].message
            if not m.tool_calls:
                return (m.content or "").strip(), None, n
            messages.append({"role": "assistant", "content": m.content, "tool_calls": [tc.model_dump() for tc in m.tool_calls]})
            for tc in m.tool_calls:
                args = json.loads(tc.function.arguments or "{}")
                if tc.function.name == "submit":
                    return args.get("answer", ""), args.get("at") or None, n
                calls += 1
                out = run_tool(tc.function.name, args) if calls <= max_calls else "Tool limit reached: call submit now."
                messages.append({"role": "tool", "tool_call_id": tc.id, "content": out})
        return "", None, n

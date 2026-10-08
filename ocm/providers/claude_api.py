"""Claude for the hybrid, through the official Anthropic SDK (pip install anthropic).

Reading runs on Claude Haiku 5.5 and teaching on Claude Sonnet 5.5 by default. Keys: ANTHROPIC_API_KEY, or set
OCM_VERTEX_PROJECT (and optionally OCM_VERTEX_REGION, default global) to use Claude on Google Cloud Vertex AI
(pip install "anthropic[vertex]")."""
import os


class Claude:
    def __init__(self, reader="claude-haiku-5-5", teacher="claude-sonnet-5-5"):
        import anthropic
        project = os.environ.get("OCM_VERTEX_PROJECT")
        self.client = (anthropic.AnthropicVertex(project_id=project, region=os.environ.get("OCM_VERTEX_REGION", "global"))
                       if project else anthropic.Anthropic())
        self.reader, self.teacher = reader, teacher

    def read(self, system, question, code):
        r = self.client.messages.create(model=self.reader, max_tokens=1024, system=system,
                                        messages=[{"role": "user", "content": f"Question: {question}\n\nCode:\n{code}"}])
        return "".join(b.text for b in r.content if b.type == "text")

    def teach(self, system, question, code, tools, run_tool, max_calls):
        spec = [{"name": t["name"], "description": t["description"], "input_schema": t["parameters"]} for t in tools]
        messages = [{"role": "user", "content": f"Question: {question}\n\nThe code the team's workspace ranked for it:\n{code}"}]
        calls = n = 0
        while n < max_calls + 10:
            r = self.client.messages.create(model=self.teacher, max_tokens=8000, system=system, tools=spec, messages=messages)
            n += 1
            if r.stop_reason == "pause_turn":
                messages.append({"role": "assistant", "content": r.content}); continue
            uses = [b for b in r.content if b.type == "tool_use"]
            if not uses:                                              # answered in text without submit: no line to teach
                return "".join(b.text for b in r.content if b.type == "text").strip(), None, n
            messages.append({"role": "assistant", "content": r.content})
            results = []
            for u in uses:
                if u.name == "submit":
                    return u.input.get("answer", ""), u.input.get("at") or None, n
                calls += 1
                out = run_tool(u.name, u.input) if calls <= max_calls else "Tool limit reached: call submit now."
                results.append({"type": "tool_result", "tool_use_id": u.id, "content": out})
            messages.append({"role": "user", "content": results})
        return "", None, n

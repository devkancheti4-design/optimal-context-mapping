"""The arms. Every arm that searches uses the same tools over the same code, through Model D's own server code, so the only differences are the ones being tested.

    alone    a new agent for every question, nothing carried over
    notes    the same agent, plus a notes file on disk: every answer is written down and read back in later sessions
    map      Model D as released with its memory off: its map chooses the code that goes in with the question, nothing is taught
    modeld   Model D as released, end to end (ocm.hybrid.run): a question near a lesson costs one read, anything new is explored and taught
    guess    no tools and no code: what the model already knows about the project"""
import os, threading, urllib.error

from ocm import hybrid as H
from ocm.providers.gemini_api import Gemini
from ocm.server import Workspace

import common as C

SOLO = H.TEACH.replace(" The code the team's workspace ranked for the question comes with it; if it holds the answer, submit from it without searching.", "")
assert SOLO != H.TEACH
NOTED = SOLO + " Notes from earlier sessions come with the question. They may be out of date; if they answer it, you can submit from them without searching."
GUESS = "Answer the question about this open-source project from what you know, in one short sentence."


class Kit:
    """Model D's server code in this process, with the surface of ocm.hybrid.Workspace."""
    tool = H.Workspace.tool

    def __init__(self, folder, memory=True):
        self.w, self.memory, self.lock = Workspace(folder), memory, threading.Lock()

    def call(self, path, **kw):
        if path == "teach" and not self.memory:
            return "memory off"
        with self.lock:
            return self.w.handle(path, kw)


class Model(Gemini):
    """Model D's own Gemini provider, on the benchmark's model, billed. teach and read are the provider's, unchanged."""
    def __init__(self, send=None):
        super().__init__(reader=C.MODEL, teacher=C.MODEL)
        self.bill = C.Bill(send or self.paid)

    def paid(self, model, body):
        try:
            return super()._post(model, body)
        except urllib.error.HTTPError as e:
            if e.code == 402:
                raise C.OverCap("the account's credits are used up")
            raise

    def _post(self, model, body):
        return self.bill.post(model, body)

    def solo(self, system, opening, tools, run_tool, max_calls):
        """The provider's teach loop for an agent with no workspace: only the opening message differs."""
        spec = [{"functionDeclarations": [{"name": t["name"], "description": t["description"], "parameters": t["parameters"]} for t in tools]}]
        contents = [{"role": "user", "parts": [{"text": opening}]}]
        calls = n = 0
        while n < max_calls + 10:
            force = calls >= max_calls
            r = self._post(self.teacher, {"systemInstruction": {"parts": [{"text": system}]}, "contents": contents, "tools": spec,
                                          "toolConfig": {"functionCallingConfig": {"mode": "ANY", "allowedFunctionNames": ["submit"]} if force else {"mode": "AUTO"}}})
            n += 1
            parts = ((r.get("candidates") or [{}])[0].get("content") or {}).get("parts") or []
            contents.append({"role": "model", "parts": parts or [{"text": ""}]})
            fcs = [p["functionCall"] for p in parts if "functionCall" in p]
            if not fcs:
                return " ".join(p.get("text", "") for p in parts).strip(), None, n
            responses = []
            for fc in fcs:
                name, args = fc.get("name"), fc.get("args") or {}
                if name == "submit":
                    return str(args.get("answer", "")), args.get("at") or None, n
                calls += 1
                responses.append({"functionResponse": {"name": name, "response": {"content": run_tool(name, args)}}})
            contents.append({"role": "user", "parts": responses})
        return "", None, n

    def guess(self, slug, question):
        r = self._post(self.reader, {"systemInstruction": {"parts": [{"text": GUESS}]}, "contents": [{"role": "user", "parts": [{"text": f"Project: {slug}\n\nQuestion: {question}"}]}]})
        parts = ((r.get("candidates") or [{}])[0].get("content") or {}).get("parts") or []
        return " ".join(p.get("text", "") for p in parts).strip()


def alone(model, kit, question):
    answer, at, n = model.solo(SOLO, f"Question: {question}", H.TOOLS, kit.tool, H.MAX_CALLS)
    return {"path": "explore", "answer": answer, "at": at, "requests": n}


class Notes:
    """A plain file on disk, the way a team keeps a CLAUDE.md: one line per answer."""
    def __init__(self, path):
        self.path = path

    def read(self):
        return open(self.path).read() if os.path.exists(self.path) else ""

    def add(self, question, answer, at):
        if answer.strip():
            with open(self.path, "a") as f:
                f.write(f"- {' '.join(question.split())} -> {' '.join(answer.split())}" + (f" ({at})" if at else "") + "\n")


def noted(model, kit, notes, question):
    text = notes.read()
    answer, at, n = model.solo(NOTED if text else SOLO, f"Question: {question}" + (f"\n\nNotes from earlier sessions:\n{text}" if text else ""), H.TOOLS, kit.tool, H.MAX_CALLS)
    notes.add(question, answer, at)
    return {"path": "explore", "answer": answer, "at": at, "requests": n, "notes_chars": len(text)}


def modeld(model, kit, question):
    return H.run(question, model, kit)

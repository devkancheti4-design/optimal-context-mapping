"""Gemini for the hybrid, over Google's REST generateContent (no extra dependency). Key: GEMINI_API_KEY (Google AI
Studio), or set OCM_VERTEX_PROJECT (and OCM_VERTEX_REGION, default us-east4) to use Vertex AI with `gcloud auth
print-access-token`. Model names: --reader / --teacher (default gemini-2.5-flash)."""
import json, os, subprocess, time, urllib.error, urllib.request

REGIONS = ["us-east4", "us-east1", "us-west1", "europe-west1", "asia-northeast1", "us-south1", "northamerica-northeast1"]


class Gemini:
    def __init__(self, reader="gemini-2.5-flash", teacher="gemini-2.5-flash"):
        self.reader, self.teacher = reader, teacher
        self.project = os.environ.get("OCM_VERTEX_PROJECT")
        self.regions = [os.environ.get("OCM_VERTEX_REGION", "us-east4")] + [r for r in REGIONS if r != os.environ.get("OCM_VERTEX_REGION", "us-east4")]
        self.key = os.environ.get("GEMINI_API_KEY")
        self._tok = (None, 0)

    def _post(self, model, body):
        """On 429 or 5xx, back off and, on Vertex, move to the next region (the same model); an expired token is refreshed."""
        for attempt in range(40):
            if self.project:
                if time.time() - self._tok[1] > 300:
                    self._tok = (subprocess.run(["gcloud", "auth", "print-access-token"], capture_output=True, text=True).stdout.strip(), time.time())
                region = self.regions[attempt % len(self.regions)]
                url = (f"https://{region}-aiplatform.googleapis.com/v1/projects/{self.project}/locations/{region}"
                       f"/publishers/google/models/{model}:generateContent")
                headers = {"Authorization": "Bearer " + self._tok[0]}
            else:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
                headers = {"x-goog-api-key": self.key or ""}
            headers["Content-Type"] = "application/json"
            try:
                with urllib.request.urlopen(urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers), timeout=180) as r:
                    return json.loads(r.read())
            except urllib.error.HTTPError as e:
                if e.code == 401: self._tok = (None, 0); continue
                if e.code not in (429, 500, 502, 503, 504): raise
            except (TimeoutError, urllib.error.URLError, ConnectionError):
                pass
            time.sleep(min(20, 1 + attempt))
        raise RuntimeError("Gemini did not answer after 40 attempts")

    def read(self, system, question, code):
        r = self._post(self.reader, {"systemInstruction": {"parts": [{"text": system}]},
                                     "contents": [{"role": "user", "parts": [{"text": f"Question: {question}\n\nCode:\n{code}"}]}]})
        parts = ((r.get("candidates") or [{}])[0].get("content") or {}).get("parts") or []
        return " ".join(p.get("text", "") for p in parts)

    def teach(self, system, question, code, tools, run_tool, max_calls):
        spec = [{"functionDeclarations": [{"name": t["name"], "description": t["description"], "parameters": t["parameters"]} for t in tools]}]
        contents = [{"role": "user", "parts": [{"text": f"Question: {question}\n\nThe code the team's workspace ranked for it:\n{code}"}]}]
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
                    return args.get("answer", ""), args.get("at") or None, n
                calls += 1
                responses.append({"functionResponse": {"name": name, "response": {"content": run_tool(name, args)}}})
            contents.append({"role": "user", "parts": responses})
        return "", None, n

"""Sentence embeddings from a small local model, at no token cost: nothing leaves the machine.

BAAI/bge-base-en-v1.5 by default (768 dimensions, CLS pooled, normalized), read from the local Hugging Face cache.
Batched in order of length so padding stays small, on Apple's GPU or CUDA when present. The device is recorded in
the memory's manifest: CPU and GPU arithmetic differ in the last bits, so an exact replication uses the same device
(or --device cpu everywhere)."""
import os

DEFAULT_MODEL = os.environ.get("CMLM_EMBED_MODEL", "BAAI/bge-base-en-v1.5")
# The instruction a model's card says to put before a search query matched against passages (not before passages,
# and not before a query matched against other questions). 0.5.3's table: maps without an "embed" record keep it.
QUERY_PREFIX = {"BAAI/bge-small-en-v1.5": "Represent this sentence for searching relevant passages: ",
                "BAAI/bge-base-en-v1.5": "Represent this sentence for searching relevant passages: ",
                "BAAI/bge-large-en-v1.5": "Represent this sentence for searching relevant passages: "}

# THE EMBEDDING LAW, part A: how to embed is read from the model's own files, never from our results.
# Prompts come from the "prompts" field of config_sentence_transformers.json when the model has one; a model without one
# takes them from this single declared table, written before any measurement, each entry quoting its model card.
_BGE_CARD = ('"For s2p(short query to long passage) retrieval task, suggest to use encode_queries() which will automatically '
             'add the instruction to each query" ... instruction: "Represent this sentence for searching relevant passages: "')
PROMPT_TABLE = {
    "BAAI/bge-small-en-v1.5": {"query": QUERY_PREFIX["BAAI/bge-small-en-v1.5"], "document": "", "card": _BGE_CARD},
    "BAAI/bge-base-en-v1.5": {"query": QUERY_PREFIX["BAAI/bge-base-en-v1.5"], "document": "", "card": _BGE_CARD},
    "BAAI/bge-large-en-v1.5": {"query": QUERY_PREFIX["BAAI/bge-large-en-v1.5"], "document": "", "card": _BGE_CARD},
    "intfloat/e5-base-v2": {"query": "query: ", "document": "passage: ",
                            "card": '"Each input text should start with "query: " or "passage: ". For tasks other than retrieval, you can simply use the "query: " prefix."'},
    "sentence-transformers/all-MiniLM-L6-v2": {"query": "", "document": "",
                                               "card": 'usage: "embeddings = model.encode(sentences)", with no instruction or prefix'},
}
MAX_LENGTH = 128                     # pieces are at most 400 characters; a model whose own limit is smaller keeps its own


class Refused(ValueError):
    """A model whose files do not say how to embed with it: refused, never guessed."""


def read_spec(name):
    """Pooling, normalisation, prompts and length, read from the model's own files (modules.json, its Pooling module's
    config.json, config_sentence_transformers.json, sentence_bert_config.json, config.json). Refuses a model with no
    pooling config, or one that needs trust_remote_code. Never branches on a model's name: only its files and the table."""
    import json
    local = os.environ.get("OCM_OFFLINE") == "1"           # offline: the local cache only; the Hub is never asked
    if local:                                              # before huggingface_hub is imported, so its later model
        os.environ.setdefault("HF_HUB_OFFLINE", "1"); os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")   # load is too
    from huggingface_hub import hf_hub_download

    def read(fname):
        try:
            return json.load(open(hf_hub_download(name, fname, local_files_only=local)))
        except Exception:
            return None
    cfg = read("config.json") or {}
    if cfg.get("auto_map"):
        raise Refused(f"refused: {name} needs trust_remote_code (config.json has auto_map); only models whose code ships with transformers are run")
    mods = read("modules.json")
    pool_mod = next((m for m in (mods or []) if m.get("type", "").endswith("models.Pooling")), None)
    pool = read(f"{pool_mod['path']}/config.json") if pool_mod and pool_mod.get("path") else None
    if not pool:
        raise Refused(f"refused: {name} has no pooling config (modules.json and its Pooling module's config.json); pooling is not guessed")
    modes = [m for m, key in (("cls", "pooling_mode_cls_token"), ("mean", "pooling_mode_mean_tokens"), ("max", "pooling_mode_max_tokens"),
                              ("mean_sqrt_len", "pooling_mode_mean_sqrt_len_tokens"), ("lasttoken", "pooling_mode_lasttoken")) if pool.get(key)]
    if len(modes) != 1:
        raise Refused(f"refused: {name} declares {modes or 'no'} pooling modes; exactly one is needed")
    normalize = any(m.get("type", "").endswith("models.Normalize") for m in mods)
    st = read("config_sentence_transformers.json") or {}
    if isinstance(st.get("prompts"), dict) and st["prompts"]:
        p = st["prompts"]; prompts = {"query": p.get("query", ""), "document": p.get("document", p.get("passage", ""))}
        psrc = "config_sentence_transformers.json prompts"
    elif name in PROMPT_TABLE:
        prompts = {k: PROMPT_TABLE[name][k] for k in ("query", "document")}; psrc = "declared table: " + PROMPT_TABLE[name]["card"]
    else:
        prompts = {"query": "", "document": ""}; psrc = "none: no prompts field and not in the declared table"
    own = (read("sentence_bert_config.json") or {}).get("max_seq_length") or cfg.get("max_position_embeddings") or MAX_LENGTH
    return {"pooling": modes[0], "normalize": bool(normalize), "query_prompt": prompts["query"], "document_prompt": prompts["document"],
            "max_length": int(min(MAX_LENGTH, own)), "model_max_length": int(own),
            "sources": {"pooling": f"{pool_mod['path']}/config.json", "normalize": "modules.json", "prompts": psrc,
                        "max_length": "min(128, sentence_bert_config.json max_seq_length)"}}


def pick_device(device=None):
    import torch
    if device:
        return device
    if torch.cuda.is_available():
        return "cuda"
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


class Embedder:
    def __init__(self, name=DEFAULT_MODEL, device=None, offline=None, max_length=128, spec=None):
        # spec (part A, read_spec): pooling and normalisation from the model's files. None: 0.5.3's way for every model
        # (first token, normalised, 128 tokens), which is exactly what bge's files say.
        self.pooling = spec["pooling"] if spec else "cls"
        self.normalize = spec["normalize"] if spec else True
        max_length = spec["max_length"] if spec else max_length
        # The first run downloads the embedding model (about 440 MB) from Hugging Face; set OCM_OFFLINE=1 afterwards to
        # guarantee nothing is fetched. Your code and questions are never sent anywhere: embedding runs on this machine.
        offline = os.environ.get("OCM_OFFLINE") == "1" if offline is None else offline
        if offline:
            os.environ.setdefault("HF_HUB_OFFLINE", "1"); os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
        import torch
        from transformers import AutoModel, AutoTokenizer
        self.torch, self.name, self.max_length = torch, name, max_length
        self.device = pick_device(device)
        self.tok = AutoTokenizer.from_pretrained(name)
        self.model = AutoModel.from_pretrained(name).train(False).to(self.device)   # inference only: nothing learns
        self.dim = self.model.config.hidden_size

    def __call__(self, texts, batch=256):
        import numpy as np
        texts = list(texts)
        out = np.zeros((len(texts), self.dim), dtype=np.float32)
        order = sorted(range(len(texts)), key=lambda i: len(texts[i]))
        with self.torch.no_grad():
            for s in range(0, len(order), batch):
                idx = order[s:s + batch]
                b = self.tok([texts[i] for i in idx], padding=True, truncation=True, max_length=self.max_length, return_tensors="pt")
                b = {k: v.to(self.device) for k, v in b.items()}
                h = self.model(**b).last_hidden_state
                if self.pooling == "cls":
                    v = h[:, 0]
                else:
                    m = b["attention_mask"].unsqueeze(-1).to(h.dtype)
                    if self.pooling == "mean":
                        v = (h * m).sum(1) / m.sum(1).clamp(min=1e-9)
                    elif self.pooling == "mean_sqrt_len":
                        v = (h * m).sum(1) / m.sum(1).clamp(min=1e-9).sqrt()
                    elif self.pooling == "max":
                        v = h.masked_fill(m == 0, -1e9).max(1).values
                    else:                                                        # lasttoken: each text's last real token
                        last = b["attention_mask"].sum(1) - 1
                        v = h[self.torch.arange(h.shape[0], device=h.device), last]
                v = self.torch.nn.functional.normalize(v.float(), dim=-1) if self.normalize else v.float()
                out[idx] = v.cpu().numpy()
        return out


_SHARED = {}


def shared(name=DEFAULT_MODEL, device=None, spec=None):
    key = (name, device, None if spec is None else (spec["pooling"], spec["normalize"], spec["max_length"]))
    if key not in _SHARED:
        _SHARED[key] = Embedder(name, device, spec=spec)
    return _SHARED[key]

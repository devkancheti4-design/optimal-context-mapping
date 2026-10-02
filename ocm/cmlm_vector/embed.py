"""Sentence embeddings from a small local model, at no token cost: nothing leaves the machine.

BAAI/bge-base-en-v1.5 by default (768 dimensions, CLS pooled, normalized), read from the local Hugging Face cache.
Batched in order of length so padding stays small, on Apple's GPU or CUDA when present. The device is recorded in
the memory's manifest: CPU and GPU arithmetic differ in the last bits, so an exact replication uses the same device
(or --device cpu everywhere)."""
import os

DEFAULT_MODEL = os.environ.get("CMLM_EMBED_MODEL", "BAAI/bge-base-en-v1.5")
# The instruction a model's card says to put before a search query matched against passages (not before passages,
# and not before a query matched against other questions).
QUERY_PREFIX = {"BAAI/bge-small-en-v1.5": "Represent this sentence for searching relevant passages: ",
                "BAAI/bge-base-en-v1.5": "Represent this sentence for searching relevant passages: ",
                "BAAI/bge-large-en-v1.5": "Represent this sentence for searching relevant passages: "}


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
    def __init__(self, name=DEFAULT_MODEL, device=None, offline=None, max_length=128):
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
                v = self.model(**b).last_hidden_state[:, 0]
                v = self.torch.nn.functional.normalize(v.float(), dim=-1).cpu().numpy()
                out[idx] = v
        return out


_SHARED = {}


def shared(name=DEFAULT_MODEL, device=None):
    key = (name, device)
    if key not in _SHARED:
        _SHARED[key] = Embedder(name, device)
    return _SHARED[key]

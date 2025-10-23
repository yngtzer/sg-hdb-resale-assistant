import json, pathlib
import numpy as np
from sentence_transformers import SentenceTransformer

IDX_DIR = pathlib.Path("rag/index_rules")
EMB_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

class RuleRetriever:
    def __init__(self, top_k=6):
        self.model = SentenceTransformer(EMB_MODEL)
        self.emb = np.load((IDX_DIR / "rules.npy").as_posix()).astype("float32")  # [N, D], normalized
        self.chunks = json.loads((IDX_DIR / "rules.json").read_text(encoding="utf-8"))
        self.top_k = top_k

    def search(self, query: str):
        q = self.model.encode([query], normalize_embeddings=True).astype("float32")  # [1, D]
        # cosine since both normalized -> dot product
        scores = (q @ self.emb.T)[0]  # [N]
        idxs = np.argpartition(scores, -self.top_k)[-self.top_k:]
        # sort top-k by score desc
        idxs = idxs[np.argsort(scores[idxs])[::-1]]
        out = []
        for i in idxs:
            c = self.chunks[int(i)].copy()
            c["score"] = float(scores[i])
            out.append(c)
        return out

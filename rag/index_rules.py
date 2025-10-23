import os, re, json, hashlib, pathlib, yaml
from datetime import datetime
from urllib.parse import urlparse
import trafilatura
from bs4 import BeautifulSoup
from sentence_transformers import SentenceTransformer
import numpy as np
import requests, requests_cache
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from readability import Document


BASE = pathlib.Path(".")
DATA_DIR = BASE / "data"
RAG_DIR  = BASE / "rag"
IDX_DIR  = RAG_DIR / "index_rules"
IDX_DIR.mkdir(parents=True, exist_ok=True)

SOURCES_YAML = RAG_DIR / "sources.yaml"
EMB_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

requests_cache.install_cache("data/http_cache", expire_after=60*60*6)  # 6h cache
SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
})

class FetchError(Exception): pass

@retry(
    reraise=True,
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.7, min=1, max=6),
    retry=retry_if_exception_type(FetchError),
)
def _get_html(url: str) -> str:
    try:
        resp = SESSION.get(url, timeout=20, allow_redirects=True)
    except requests.RequestException as e:
        raise FetchError(str(e))
    if resp.status_code >= 400 or not resp.text.strip():
        raise FetchError(f"HTTP {resp.status_code}")
    return resp.text

def fetch_clean(url: str) -> str:
    """
    Resilient fetch: requests → trafilatura.extract → readability fallback.
    Returns cleaned text; may be empty string if everything fails.
    """
    # 1) Try trafilatura.fetch_url first (works on many sites)
    try:
        raw = trafilatura.fetch_url(url)
        if raw:
            txt = trafilatura.extract(
                raw, include_comments=False, include_tables=True, favor_recall=True, url=url
            )
            if txt and txt.strip():
                return txt
    except Exception:
        pass

    # 2) Robust GET with browser-like headers
    try:
        html = _get_html(url)
    except FetchError:
        return ""

    # 3) Try trafilatura on downloaded HTML
    try:
        txt = trafilatura.extract(
            html, include_comments=False, include_tables=True, favor_recall=True, url=url
        )
        if txt and txt.strip():
            return txt
    except Exception:
        pass

    # 4) Final fallback: readability -> cleaned HTML -> plain text via BS4
    try:
        doc = Document(html)
        summary_html = doc.summary(html_partial=True)
        soup = BeautifulSoup(summary_html, "html5lib")
        # Keep headings, paragraphs, list items, and table text
        parts = []
        for el in soup.find_all(["h1","h2","h3","h4","p","li","th","td","caption"]):
            text = el.get_text(" ", strip=True)
            if text:
                parts.append(text)
        return "\n".join(parts)
    except Exception:
        return ""


def split_into_chunks(text: str, title: str, url: str, max_tokens=800, overlap=80):
    # crude split by headings / paragraphs
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    chunks = []
    buf = []
    tokens = 0
    def tok_count(s): return max(1, len(s.split()))
    for line in lines:
        if re.match(r"^[A-Z].{0,80}$", line) and len(line.split()) <= 12:
            # heading — flush current buffer
            if buf:
                chunks.append("\n".join(buf))
                buf = []
                tokens = 0
        if tokens + tok_count(line) > max_tokens and buf:
            chunks.append("\n".join(buf))
            # overlap: keep last ~overlap tokens
            keep = " ".join(" ".join(buf).split()[-overlap:])
            buf = [keep, line]
            tokens = tok_count(keep) + tok_count(line)
        else:
            buf.append(line)
            tokens += tok_count(line)
    if buf:
        chunks.append("\n".join(buf))
    # attach metadata
    out = []
    for i, c in enumerate(chunks):
        out.append({
            "doc_id": hashlib.md5((url+str(i)).encode()).hexdigest(),
            "title": title,
            "url": url,
            "retrieved_at": datetime.utcnow().strftime("%Y-%m-%d"),
            "text": c
        })
    return out

def main():
    sources = yaml.safe_load(SOURCES_YAML.read_text(encoding="utf-8"))
    all_chunks = []
    for s in sources:
        t, u = s["title"], s["url"]
        txt = fetch_clean(u)
        if not txt:
            print(f"[WARN] Could not fetch {u}")
            continue
        chunks = split_into_chunks(txt, t, u)
        all_chunks.extend(chunks)
        print(f"[OK] {t} -> {len(chunks)} chunks")

    # embed
    model = SentenceTransformer(EMB_MODEL)
    embeddings = model.encode([c["text"] for c in all_chunks], show_progress_bar=True, normalize_embeddings=True)
    embeddings = embeddings.astype("float32")
    # Save artifacts
    np.save((IDX_DIR / "rules.npy").as_posix(), embeddings)
    (IDX_DIR / "rules.json").write_text(
        json.dumps(all_chunks, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"[DONE] {len(all_chunks)} chunks indexed (NumPy).")

if __name__ == "__main__":
    main()

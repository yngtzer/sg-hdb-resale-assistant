import streamlit as st

st.set_page_config(page_title="Methodology • SG HDB Resale Assistant", layout="wide")
st.title("🧩 Methodology")
st.caption("How the data flows, how RAG works, and how each use case is implemented")

st.markdown("""
## Architecture Overview
This app uses three cooperating layers:

1. **Analytics Store (DuckDB)**
   - Loads the public **Resale Flat Prices** CSV.
   - Computes medians/IQR/PSF for **town/block** and returns recent transactions & monthly series.
   - Powers the **Price Fairness** and **Discovery** tabs.

2. **RAG for Rules/Guides (Mini Index)**
   - Crawler fetches public pages (HDB/CPF/MAS/CEA), chunks by sections, embeds with **MiniLM**.
   - Embeddings stored in a `.npy` matrix + JSON metadata (no heavy vector DB).
   - At runtime, queries → cosine top-k → (optional) LLM synthesis with **citations**.
   - Powers **Readiness/Grants/Eligibility** explanatory text.

3. **Deterministic Calculators**
   - **Affordability (MSR)**: annuity maths + YAML policy knobs.
   - **Timeline**: pure date arithmetic (OTP, next working day, 21-day target, ~8-week anchor).

All features strictly use **public info** and clearly point back to official pages.
""")

st.markdown("---")

st.markdown("## Data Flow Details")

st.markdown("""
### 1) Transactions & Comps (DuckDB)
- **Ingestion**: `db/init_duckdb.py` loads `data/resale-flat-prices.csv` into `db/resale.duckdb`.
- **Schema**: one table `resale_txn(month, town, block, street_name, flat_type, storey_range, floor_area_sqm, lease_commence_year, remaining_lease, resale_price)`.
- **Queries**:
  - **Summary** (median, p25, p75, **median PSF**) for any `town/block + flat_type + window`.
  - **Series**: monthly medians for charts.
  - **Recent**: last N transactions.
- **Discovery**:
  - Aggregates **block-level** stats in a lookback window.
  - Approximates remaining lease: `(lease_commence_year + 99) - current_year`.
  - Filters: budget, min-lease, min-deals, towns.

### 2) RAG for Rules & Explainability
- **Crawler**: robust `requests` → `trafilatura` extraction → `readability` fallback, browser-like headers, retry/cache.
- **Chunking**: header-aware, 600–900 tokens, overlap ~80; tables kept intact per chunk.
- **Embeddings**: `all-MiniLM-L6-v2`; stored as `rules.npy` with metadata in `rules.json`.
- **Retrieval**: cosine top-k via NumPy; no external vector DB.
- **Answering**:
  - If `OPENAI_API_KEY` present → concise synthesis with numbered **[citations]**.
  - Else → extractive fallback: top snippets + source links.

### 3) Calculators & Timeline
- **MSR Calculator**: computes monthly headroom (MSR × income − other debt), derives max loan principal from annuity inverse.
- **Stamp Duty**: tiered calculation from YAML (kept as an estimate).
- **Timeline**: OTP date → next working day for **Request for Value** → resale application target (OTP + 21 days) → completion anchor (~8 weeks after acceptance).
""")

st.markdown("---")

st.markdown("## Implementation Notes")
st.markdown("""
- **Caching**: RAG retriever and towns list use `@st.cache_resource` to avoid cold reloads.
- **Config-driven**: policy assumptions (MSR cap, stamp duty tiers, placeholders) live in `config/policy.yaml`.
- **Guardrails**: every guidance panel nudges users to verify on official sites; no paywalled scraping; no storage of personal data.
- **Extensibility**: add URLs to `rag/sources.yaml`, run indexer; drop new CSV for resale data, re-init DB.
""")

st.markdown("---")
st.header("Flowcharts by Use Case")

st.subheader("A) Chat with Information (RAG Q&A)")
st.caption("User asks a question → retrieve official guidance → synthesize a concise, cited answer.")
st.graphviz_chart("""
digraph RAG_QA {
  graph [rankdir=LR, fontsize=10];
  node [shape=box, style="rounded,filled", fillcolor="#eef6ff"];

  User[label="User question\n(e.g., 'When to submit Request for Value?')", fillcolor="#e8fff2"];
  Router[label="RAG Router\n(builds focused query)"];
  Retriever[label="Retriever\n(NumPy cosine top-k over MiniLM embeddings)"];
  Chunks[label="Top Chunks\n(HDB/CPF/MAS/CEA sections)"];
  Synth[label="Answer Synthesizer\n(OpenAI if key, else extractive)"];
  Answer[label="Cited Answer\n(markdown + [1][2] links)", fillcolor="#e8fff2"];

  User -> Router -> Retriever -> Chunks -> Synth -> Answer;
}
""")

st.subheader("B) Intelligent Search (Discovery & Comps)")
st.caption("User specifies filters → block/town summaries → candidates with medians, PSF, deals, last txn.")
st.graphviz_chart("""
digraph Discovery {
  graph [rankdir=LR, fontsize=10];
  node [shape=box, style="rounded,filled", fillcolor="#fff7e6"];

  Inputs[label="Filters\n(towns, flat type, budget, min lease, lookback, min deals)", fillcolor="#e8fff2"];
  DuckDB[label="DuckDB\n(resale_txn)"];
  Agg[label="Aggregate per block\n(median, p25–p75, PSF,\nlast txn, deals)"];
  Lease[label="Approx remaining lease\n(lease_commence_year)"];
  Filter[label="Apply filters\n(budget, min lease, min deals)"];
  Results[label="Candidate blocks\n(table + links)", fillcolor="#e8fff2"];

  Inputs -> DuckDB -> Agg -> Lease -> Filter -> Results;
}
""")

st.subheader("C) Price Fairness (Town/Block Comps)")
st.caption("For selected town/block + flat type + lookback, compute medians, IQR, PSF + chart.")
st.graphviz_chart("""
digraph Comps {
  graph [rankdir=LR, fontsize=10];
  node [shape=box, style="rounded,filled", fillcolor="#f0fff4"];

  Sel[label="Selection\n(town/block, flat type, lookback)", fillcolor="#e8fff2"];
  DB[label="DuckDB query\n(windowed)"];
  Stats[label="Summary\n(median price, p25–p75, median PSF,\ndeals, avg sqm)"];
  Series[label="Monthly medians\n(price & PSF)"];
  UI[label="UI Cards & Chart", fillcolor="#e8fff2"];

  Sel -> DB -> Stats -> UI;
  DB -> Series -> UI;
}
""")

st.markdown("---")
st.header("Operational Flow (End-to-End)")
st.graphviz_chart("""
digraph EndToEnd {
  graph [rankdir=TB, fontsize=10];
  node [shape=box, style="rounded,filled", fillcolor="#f5f5ff"];

  subgraph cluster_ingest {
    label="Ingestion & Indexing";
    style="rounded";
    CSV[label="data.gov.sg CSV\n(Resale Flat Prices)", fillcolor="#fff"];
    INIT[label="db/init_duckdb.py\n(load -> resale_txn)"];
    SRC[label="rag/sources.yaml", fillcolor="#fff"];
    CRAWL[label="Crawler + Chunker\n(robust fetch → clean text)"];
    EMB[label="MiniLM Embeddings\n(rules.npy + rules.json)"];
    CSV -> INIT;
    SRC -> CRAWL -> EMB;
  }

  subgraph cluster_runtime {
    label="Runtime";
    style="rounded";
    UI[label="Streamlit UI\n(sidebar + tabs)", fillcolor="#e8fff2"];
    COMPS[label="Comps/Discovery\n(DuckDB queries)"];
    RAG[label="RAG retrieval\n(NumPy cosine top-k)"];
    LLM[label="Synthesis (optional)\n(OpenAI if key)"];
    UI -> COMPS;
    UI -> RAG -> LLM;
  }

  INIT -> COMPS;
  EMB -> RAG;
}
""")

st.markdown("""
---

## Repro & Refresh
- **Update data**: replace CSV → `python db/init_duckdb.py`
- **Update rules**: edit `rag/sources.yaml` → `python rag/index_rules.py`
- **Auto-refresh**: optional guard `ensure_rules_index(max_age_hours=7*24)` in app startup

## Validation
- Unit test math paths (annuity, MSR headroom).
- Smoke test RAG with a golden set (e.g., RfV timing, MSR vs TDSR).
- Visual check for outliers in monthly series (consider IQR bands if needed).

## Security & Privacy
- No credentials or personal data stored.
- Only public pages are fetched and chunked.
- Links drive users to official sites for final checks.
""")

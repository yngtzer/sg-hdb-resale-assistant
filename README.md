# SG HDB Resale Assistant (Streamlit + RAG)

Public-info assistant for Singapore HDB resale decisions.  
Uses: **data.gov.sg** resale transactions (DuckDB) + **RAG** over official HDB/CPF/MAS/CEA pages.

## Quick start
```bash
git clone <this-repo>
cd sg-hdb-resale-assistant
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# (Optional) add your OpenAI key for nicer answers
cp .env.example .env && edit .env

# Load dataset (put CSV at data/resale-flat-prices.csv first)
python db/init_duckdb.py

# Build rule index (once, or when sources change)
python rag/index_rules.py

# Run
streamlit run app/streamlit_app.py


---

## 4) First deploy options

### Option A — Streamlit Community Cloud (fastest)
1. Push repo to GitHub.
2. Go to share.streamlit.io → “New app” → select repo/branch → **Main file:** `app/streamlit_app.py`.
3. In “Advanced settings”:
   - Add `OPENAI_API_KEY` as a secret (optional).
   - Add `PYTHON_VERSION` to **3.11** if asked.
4. Click **Deploy**.
5. **Post-deploy task (manual):**
   - Upload `data/resale-flat-prices.csv` to the app (you can add a simple uploader in a future step), or commit it if license allows.
   - Open the app shell (if available) or trigger:
     - `python db/init_duckdb.py`
     - `python rag/index_rules.py`
   - If you can’t run those post-deploy commands in Streamlit Cloud, pre-build artifacts locally and **commit**:
     - `db/resale.duckdb` (allowed if size < 100MB; otherwise use Git LFS)
     - `rag/index_rules/rules.json` and `rules.npy`

> Tip: A tiny “Ensure index” guard you added earlier can auto-rebuild on boot. If Streamlit Cloud blocks shell calls, pre-commit artifacts.

### Option B — Docker (portable)
Create `Dockerfile`:
```dockerfile
FROM python:3.11-slim

WORKDIR /app
ENV PIP_NO_CACHE_DIR=1

# System deps for lxml/html5lib if needed
RUN apt-get update && apt-get install -y build-essential libxml2-dev libxslt1-dev && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Pre-build indices at image build time (optional)
# RUN python db/init_duckdb.py && python rag/index_rules.py

EXPOSE 8501
CMD ["streamlit", "run", "app/streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]

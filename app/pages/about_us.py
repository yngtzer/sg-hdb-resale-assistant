import streamlit as st

st.set_page_config(page_title="About • SG HDB Resale Assistant", layout="wide")

st.title("📄 About This Project")
st.caption("Version 1.0 — public-data powered guidance for Singapore HDB resale buyers")

st.markdown("""
## Project Scope
This app helps buyers evaluate **resale HDB flats** using **only public information**. It focuses on:
- Understanding the **official process** (HFE → OTP → Request for Value → resale application → completion)
- Checking **price fairness** via recent transactions (town/block, flat type)
- Running a transparent **affordability (MSR)** check with clear assumptions
- Explaining **eligibility** topics (EIP/SPR, lease-to-95 CPF rules) with cited guidance
- Shortlisting **candidate blocks** that fit budget and lease filters
- Providing a dated **timeline** with planning anchors

---

## Objectives
1. **Accuracy over opinion** → always show **links to official sources**.
2. **Transparency** → calculators are deterministic and **config-driven** (YAML).
3. **Speed** → analytics are local (DuckDB), RAG is light (NumPy + MiniLM).
4. **Privacy** → the app does not store personal data; all inputs are session-local.

---

## Data Sources (Public)
- **HDB**: resale process, HFE, Request for Value, EIP/SPR overview, “Check Resale Prices”.
- **data.gov.sg**: **Resale Flat Prices** dataset (transactions), **Resale Price Index** (macro trend).
- **CPF**: lease-to-age-95 CPF usage guidance & calculators (linked).
- **MAS/MND/CEA**: MSR/TDSR explainers, buyer guides (selected sections).

> Pages are periodically re-indexed by the lightweight crawler and chunker. When a policy page changes, the app rebuilds its mini index to stay fresh.

---

## Features at a Glance
- **Readiness meter**: HFE / EIP-SPR / Grants / MSR-CPF checklist with quick links
- **Grants explainer**: RAG-backed, cited breakdown (CPF Housing, EHG, PHG)
- **Price fairness**: town/block comps with **median, IQR, PSF** + monthly medians chart
- **Affordability**: MSR-based max loan & monthly; transparent assumptions & placeholders
- **Eligibility (EIP/SPR)**: concise explainer with sources + **copyable block checklist**
- **Timeline**: OTP date → RfV next working day → application target (21 days) → completion anchor (~8 weeks)

---

## What This App Is Not
- It’s **not** financial or legal advice.
- It does **not** replace official checks (EIP/SPR, HFE, CPF calculators).
- It does **not** scrape behind logins or paywalled data.

---

## Contact & Contributions
- Ideas/PRs welcome (code comments reference module names for easy navigation).
- For issues or suggestions, open a ticket or drop a note in the repo discussions.

""")

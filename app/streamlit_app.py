import pandas as pd
from tools.comps import sql_comps
from tools.calc_afford import AffordInputs, calc_afford
import streamlit as st
from rag.retrieve import RuleRetriever
from rag.answer import synthesize_answer
from tools.readiness import ReadinessInputs, readiness_score
from tools.timeline import TimelineInputs, build_timeline
from datetime import date
from tools.formatting import fmt_money, fmt_psf
from tools.grants_prompt import build_grants_prompt
from tools.eip_spr_prompt import build_eip_spr_prompt
from tools.block_checklist import build_block_checklist
import os, pathlib, time

st.set_page_config(page_title="SG HDB Resale Assistant", layout="wide")
st.title("🇸🇬 SG HDB Resale Assistant")

# Data freshness (DuckDB)
db_path = pathlib.Path("db/resale.duckdb")
if db_path.exists():
    age_hours = (time.time() - db_path.stat().st_mtime)/3600
    st.caption(f"Data: Resale transactions loaded • updated ~{age_hours:.1f}h ago")
else:
    st.caption("Data: (no DB yet) — run `python db/init_duckdb.py`")

@st.cache_resource
def get_retriever():
    return RuleRetriever(top_k=6)

retriever = get_retriever()


with st.sidebar:
    st.header("Buyer Profile")
    income = st.number_input("Household income (SGD)", min_value=0, step=100)
    ages = st.text_input("Buyer ages (comma)", "35,33")
    citizenship = st.selectbox("Citizenship", ["SC","SC+SPR","SPR"])
    scheme = st.selectbox("Scheme", ["Family","Singles"])
    parents_postal = st.text_input("Parents' postal (optional)")
    loan_type = st.selectbox("Loan type", ["HDB","Bank"])
    interest = st.number_input("Est. interest % p.a.", min_value=0.1, max_value=10.0, value=3.0, step=0.1)
    tenure = st.slider("Tenure (years)", 5, 30, 25)
    monthly_debt = st.number_input("Other monthly debt (SGD)", min_value=0, step=50)
    remaining_lease = st.number_input("Remaining lease (years, optional)", min_value=0, step=1, value=0)
    remaining_lease = remaining_lease if remaining_lease > 0 else None


    st.divider()
    st.header("Target Flat")
    town = st.text_input("Town", "Tampines")
    block = st.text_input("Block (optional)")
    flat_type = st.selectbox("Flat type", ["3 ROOM","4 ROOM","5 ROOM","EXECUTIVE"])
    budget = st.number_input("Budget (SGD)", min_value=0, step=1000)

    st.divider()
    st.header("Readiness")
    has_hfe = st.checkbox("I have an HFE letter (or started application).", value=False)
    understands_eip_spr = st.checkbox("I understand EIP/SPR quota may apply to my profile.", value=False)
    knows_grants = st.checkbox("I reviewed which grants I might get (EHG/CPF Housing/PHG).", value=False)
    ran_afford_calc = st.checkbox("I ran the affordability calculator (MSR/CPF).", value=False)


tabs = st.tabs([
    "Readiness", "Grants", "Price Fairness",
    "Affordability", "Eligibility / EIP-SPR",
    "Timeline", "Discovery"
])

with tabs[0]:
    st.subheader("Readiness")
    inp = ReadinessInputs(
        has_hfe=has_hfe,
        understands_eip_spr=understands_eip_spr,
        knows_grants=knows_grants,
        ran_afford_calc=ran_afford_calc,
    )
    r = readiness_score(inp)
    st.metric("Readiness", f"{r['percent']}%", help=r["status"])

    # Show check statuses
    for label, ok in r["checks"].items():
        st.write(("✅ " if ok else "⬜️ ") + label)

    st.divider()
    st.caption("Helpful official links")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.link_button("HFE Letter (HDB)", "https://www.hdb.gov.sg/residential/buying-a-flat/hfe-letter")
    with col2:
        st.link_button("EIP/SPR Overview", "https://www.hdb.gov.sg/residential/living-in-an-hdb-flat/ethnic-integration-policy-and-spr-quota")
    with col3:
        st.link_button("Check Resale Prices", "https://www.hdb.gov.sg/residential/buying-a-flat/resale/price-check")

    col4, col5 = st.columns(2)
    with col4:
        st.link_button("CPF usage (lease to 95)", "https://www.cpf.gov.sg/member/faq/housing-schemes/using-cpf-to-buy-a-property/how-much-cpf-savings-can-i-use-to-buy-a-property")
    with col5:
        st.link_button("HDB Resale Process", "https://www.hdb.gov.sg/residential/buying-a-flat/resale")



with tabs[1]:
    st.subheader("Grants")

    col1, col2 = st.columns(2)
    with col1:
        is_first_timer = st.checkbox("First-timer household?", value=True)
        within_4km = st.selectbox(
            "Within 4km of parents/children (for PHG)?",
            ["Unknown", "Yes", "No"]
        )
        within_4km_bool = None if within_4km == "Unknown" else (within_4km == "Yes")
    with col2:
        st.caption("Using sidebar values for scheme/citizenship/income/flat type.")
        st.write(f"- Scheme: **{scheme}**")
        st.write(f"- Citizenship: **{citizenship}**")
        st.write(f"- Household income: **${income:,.0f}**")
        st.write(f"- Flat type: **{flat_type}**")

    if st.button("Explain my grant options"):
        # Compose the RAG question and ask the retriever/LLM
        q = build_grants_prompt(
            is_first_timer=is_first_timer,
            scheme=scheme,
            citizenship=citizenship,
            household_income=int(income or 0),
            flat_type=flat_type,
            within_4km_of_parents=within_4km_bool
        )
        hits = retriever.search(q)
        ans = synthesize_answer(q, hits)

        # Render answer + sources
        st.markdown(ans["answer_markdown"])
        if ans.get("citations"):
            st.caption("Sources:")
            for i, c in enumerate(ans["citations"], 1):
                st.markdown(f"- [{i}] {c['title']} — {c['url']}")

    st.info(
        "Grant amounts and eligibility change over time. Use this as guidance and confirm on the official HDB/CPF pages "
        "before committing to a purchase or OTP."
    )

with tabs[2]:
    st.subheader("Price Fairness (Comps)")

    # Mode switcher
    comp_mode = st.radio(
        "Compare by",
        options=["Town", "Block"],
        horizontal=True,
        help="Use Town for broader view. Use Block for specific address if you filled Block above."
    )
    mode = "block" if (comp_mode == "Block" and block.strip()) else "town"
    lookback = st.slider("Lookback (months)", 3, 24, 12, help="Window of past transactions to summarise.")

    st.caption(f"Mode: **{mode.upper()}**, Flat type: **{flat_type}**, Lookback: **{lookback} months**")

    if st.button("Run Comps"):
        out = sql_comps(mode=mode, town=town, block=block, flat_type=flat_type, lookback_months=lookback)
        s = out.get("summary", {}) or {}
        if not s or s.get("deals", 0) == 0:
            st.warning("No transactions found for the chosen filters.")
        else:
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.metric("Deals", int(s["deals"]))
            with c2:
                st.metric("Median Price", fmt_money(s["median_price"]))
                st.caption(f"P25–P75: {fmt_money(s['p25_price'])} – {fmt_money(s['p75_price'])}")
            with c3:
                st.metric("Median PSF", fmt_psf(s["median_psf"]))
                st.caption(f"P25–P75: {fmt_psf(s['p25_psf'])} – {fmt_psf(s['p75_psf'])}")
            with c4:
                st.metric("Avg Size (sqm)", f"{s['avg_sqm']:.1f}")

            st.divider()
            st.write("**Recent transactions**")
            import pandas as pd
            df = pd.DataFrame(out["recent"])
            if not df.empty:
                df = df.rename(columns={"psf": "psf_est"})
                st.dataframe(df, use_container_width=True)

            st.write("**Monthly medians**")
            series_df = pd.DataFrame(out["series"])
            if not series_df.empty:
                series_df = series_df.set_index("month")[["median_price","median_psf"]]
                st.line_chart(series_df)

with tabs[3]:
    st.subheader("Affordability (MSR-based)")
    st.caption("Uses a configurable MSR cap and your inputs. Verify details on official pages.")

    colA, colB = st.columns(2)
    with colA:
        use_budget = st.checkbox("Use budget as 'loan amount' for monthly estimate", value=True)
    with colB:
        show_inputs = st.checkbox("Show raw inputs", value=False)

    if st.button("Compute Affordability"):
        ages_list = [int(a.strip()) for a in ages.split(",") if a.strip().isdigit()]
        inp = AffordInputs(
            gross_income_sgd=income,
            monthly_debt_sgd=monthly_debt,
            loan_type=loan_type,
            interest_pa=interest,
            tenure_years=tenure,
            est_price_sgd=budget if use_budget and budget > 0 else None,
            buyer_ages=ages_list if ages_list else None,
            remaining_lease_years=remaining_lease
        )
        out = calc_afford(inp)

        if show_inputs:
            st.write("**Inputs**")
            st.json(inp.__dict__)

        st.write("**Results**")
        st.json(out["results"])

        st.write("**Cashflow (placeholders)**")
        st.json(out["cashflow_placeholders"])

        st.write("**CPF / Lease note**")
        st.info(out["cpf_lease"]["note"])


with tabs[4]:
    st.subheader("Eligibility / EIP-SPR")

    # Inputs (reuse sidebar values for citizenship + flat_type + town/block)
    ethnicity = st.selectbox("Your ethnicity (for EIP)", ["Chinese", "Malay", "Indian/Others"])
    profile = citizenship  # reuse sidebar: "SC", "SC+SPR", "SPR"

    # Gentle hint if user selects Block mode elsewhere but left Block empty
    if (block.strip() == ""):
        st.info("Tip: Enter a Block in the sidebar if you want block-specific notes; otherwise we’ll explain EIP/SPR at the town level.")

    # 1) RAG explainer (concise, cited)
    if st.button("Explain how EIP/SPR affects me"):
        q = build_eip_spr_prompt(ethnicity=ethnicity, profile=profile, town=town, block=block if block.strip() else None)
        hits = retriever.search(q)
        ans = synthesize_answer(q, hits)
        st.markdown(ans["answer_markdown"])
        if ans.get("citations"):
            st.caption("Sources:")
            for i, c in enumerate(ans["citations"], 1):
                st.markdown(f"- [{i}] {c['title']} — {c['url']}")
    st.warning(
    "Key timing risk: you submit Request for Value **after** OTP. If the HDB valuation is below your agreed price, "
    "the difference (COV) must be paid in **cash**. Consider block-level comps before offering."
    )
    st.divider()

    # 2) Quick official actions
    st.caption("Go check on official sites (opens in new tab)")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.link_button("EIP/SPR Overview", "https://www.hdb.gov.sg/residential/living-in-an-hdb-flat/ethnic-integration-policy-and-spr-quota")
    with c2:
        # Public ‘checker’ is typically via Flat Portal; keep high-level link to avoid breakage.
        st.link_button("Check EIP/SPR (Flat Portal)", "https://www.hdb.gov.sg/residential/buying-a-flat/resale")
    with c3:
        st.link_button("Check Resale Flat Prices", "https://www.hdb.gov.sg/residential/buying-a-flat/resale/price-check")

    st.divider()

    # 3) Copyable checklist for this town/block
    st.write("**Block checklist** (copy & paste)")
    checklist = build_block_checklist(town=town, block=block if block.strip() else None, flat_type=flat_type, today=date.today())
    # st.code provides a copy-to-clipboard button automatically
    st.code(checklist)

with tabs[5]:
    st.subheader("Timeline")
    st.caption("Dates are indicative. Always verify exact deadlines on the official pages.")

    otp_date = st.date_input("OTP signed on", value=date.today())
    completion_weeks = st.slider("Completion planning (weeks after acceptance)", 6, 12, 8)
    if st.button("Generate Timeline"):
        t_items = build_timeline(TimelineInputs(otp_signed_on=otp_date, completion_weeks=completion_weeks))
        for label, d in t_items:
            st.write(f"- **{label}**: {d.strftime('%Y-%m-%d')}")

        st.divider()
        st.caption("Quick actions")
        c1, c2 = st.columns(2)
        with c1:
            st.link_button("Submit Request for Value (login via Flat Portal)", "https://www.hdb.gov.sg/residential/buying-a-flat/resale/request-for-value")
        with c2:
            st.link_button("Start/Check Resale Application", "https://www.hdb.gov.sg/residential/buying-a-flat/resale/apply-for-resale")


with tabs[6]:
    st.subheader("Discovery")
    st.write("Filters to find candidate blocks by budget/lease/flat type.")

st.divider()
question = st.text_input("Ask a question about HDB resale")
if question:
    hits = retriever.search(question)
    ans = synthesize_answer(question, hits)
    st.markdown(ans["answer_markdown"])
    if ans.get("citations"):
        st.caption("Sources:")
        for i, c in enumerate(ans["citations"], 1):
            st.markdown(f"- [{i}] {c['title']} — {c['url']}")


st.write("")
st.caption("This app uses only public information (HDB/CPF/MAS/CEA/data.gov.sg). Always verify on the official pages before acting.")

import pandas as pd
from tools.comps import sql_comps
from tools.calc_afford import AffordInputs, calc_afford
import streamlit as st
from rag.retrieve import RuleRetriever
from rag.answer import synthesize_answer
from tools.readiness import ReadinessInputs, readiness_score
from tools.timeline import TimelineInputs, build_timeline
from datetime import date


st.set_page_config(page_title="SG HDB Resale Assistant", layout="wide")

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
    st.write("Grant breakdown UI goes here.")

with tabs[2]:
    st.subheader("Price Fairness (Comps)")
    mode = "block" if block.strip() else "town"
    st.caption(f"Mode: {mode.upper()} (lookback: 12 months)")
    if st.button("Run Comps"):
        out = sql_comps(mode=mode, town=town, block=block, flat_type=flat_type, lookback_months=12)
        if not out or out["summary"]["deals"] == 0:
            st.warning("No transactions found for the chosen filters.")
        else:
            s = out["summary"]
            st.metric("Deals (12m)", s["deals"])
            st.metric("Median Price", f"${s['median_price']:,.0f}")
            st.metric("IQR (P25–P75)", f"${s['p25_price']:,.0f} – ${s['p75_price']:,.0f}")

            st.write("Recent transactions")
            st.dataframe(pd.DataFrame(out["recent"]))

            st.write("Monthly median series")
            series_df = pd.DataFrame(out["series"])
            if not series_df.empty:
                series_df = series_df.set_index("month")[["median_price"]]
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
    st.write("Live links to official checkers + explainer.")

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


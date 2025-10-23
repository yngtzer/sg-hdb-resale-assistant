from tools.calc_afford import AffordInputs, calc_afford

def test_basic_afford():
    inp = AffordInputs(
        gross_income_sgd=8000,
        monthly_debt_sgd=0,
        loan_type="HDB",
        interest_pa=3.0,
        tenure_years=25,
        est_price_sgd=600000,
        buyer_ages=[35,33],
        remaining_lease_years=70
    )
    out = calc_afford(inp)
    assert out["results"]["max_loan_by_msr_sgd"] > 0
    assert out["cpf_lease"]["status"] in ("ok","limited","unknown")

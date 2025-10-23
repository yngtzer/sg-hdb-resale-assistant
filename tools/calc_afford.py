from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import math
import yaml
from pathlib import Path

POLICY_PATH = Path("config/policy.yaml")

def load_policy() -> dict:
    if POLICY_PATH.exists():
        return yaml.safe_load(POLICY_PATH.read_text(encoding="utf-8")) or {}
    return {}

def annuity_payment(principal: float, monthly_rate: float, months: int) -> float:
    """Monthly payment for loan 'principal' at 'monthly_rate' over 'months'."""
    if monthly_rate == 0:
        return principal / months
    f = (1 + monthly_rate) ** months
    return principal * monthly_rate * f / (f - 1)

def principal_from_payment(target_monthly: float, monthly_rate: float, months: int) -> float:
    """Solve principal P from given monthly payment."""
    if monthly_rate == 0:
        return target_monthly * months
    f = (1 + monthly_rate) ** months
    return target_monthly * (f - 1) / (monthly_rate * f)

def compute_bsd(price: float, tiers: List[Dict[str, float]]) -> float:
    """Tiered Buyer’s Stamp Duty."""
    remaining = price
    last_cap = 0.0
    tax = 0.0
    for t in tiers:
        cap = t["up_to"]
        rate = float(t["rate"])
        if cap is None:  # top tier
            tax += remaining * rate
            break
        band = max(0.0, min(price, cap) - last_cap)
        tax += band * rate
        remaining -= band
        last_cap = cap
        if remaining <= 0:
            break
    return tax

@dataclass
class AffordInputs:
    gross_income_sgd: float
    monthly_debt_sgd: float
    loan_type: str            # "HDB" | "Bank" (for display only; logic uses MSR cap)
    interest_pa: float
    tenure_years: int
    est_price_sgd: Optional[float] = None
    buyer_ages: Optional[List[int]] = None
    remaining_lease_years: Optional[float] = None

def cpf_lease_flag(ages: Optional[List[int]], remaining_lease_years: Optional[float]) -> Dict[str, Any]:
    """Return notes about CPF usage based on remaining lease vs youngest age to 95 rule."""
    if ages is None or not ages or remaining_lease_years is None:
        return {"status": "unknown", "note": "Add youngest buyer age and remaining lease to check CPF rule."}
    youngest = min(ages)
    to_95 = 95 - youngest
    total = remaining_lease_years
    if total >= to_95:
        return {"status": "ok", "note": "Remaining lease appears to cover youngest buyer to age 95 (full CPF usage generally allowed)."}
    else:
        return {"status": "limited", "note": "Remaining lease may not cover youngest buyer to age 95 — CPF usage could be prorated/limited. Verify on official calculator."}

def calc_afford(inputs: AffordInputs) -> Dict[str, Any]:
    policy = load_policy()
    msr_cap = float(policy.get("msr_cap", 0.30))
    placeholders = policy.get("placeholders", {})
    bsd_tiers = policy.get("bsd_tiers", [])

    # 1) MSR headroom
    # MSR applies to (housing instalment) <= msr_cap * gross_income - other monthly debt
    msr_limit = max(0.0, msr_cap * inputs.gross_income_sgd - inputs.monthly_debt_sgd)

    months = int(inputs.tenure_years * 12)
    monthly_rate = float(inputs.interest_pa) / 100.0 / 12.0

    # 2) Max principal by MSR headroom
    max_loan = principal_from_payment(msr_limit, monthly_rate, months) if msr_limit > 0 else 0.0
    est_monthly_for_budget = None
    if inputs.est_price_sgd:
        # If user has a target price, compute monthly needed assuming loan covers that price less downpayment.
        # We don't model exact LTV; keep this neutral and show monthly for a hypothetical full-loan amount.
        est_monthly_for_budget = annuity_payment(inputs.est_price_sgd, monthly_rate, months)

    # 3) BSD on estimated price (if given)
    bsd = compute_bsd(inputs.est_price_sgd, bsd_tiers) if (inputs.est_price_sgd and bsd_tiers) else None

    # 4) Lease/CPF note
    lease_flag = cpf_lease_flag(inputs.buyer_ages, inputs.remaining_lease_years)

    # 5) Cashflow placeholders
    cash_items = {
        "option_fee_sgd": placeholders.get("option_fee_sgd", 1000),
        "exercise_fee_sgd": placeholders.get("exercise_fee_sgd", 4000),
        "legal_misc_sgd": placeholders.get("legal_misc_sgd", 3000),
        "stamp_duty_est_sgd": bsd
    }

    out = {
        "assumptions": {
            "msr_cap": msr_cap,
            "interest_pa": inputs.interest_pa,
            "tenure_years": inputs.tenure_years,
            "note": "This is a deterministic calculator using configurable assumptions. Verify MSR/CPF/fees on official sites."
        },
        "results": {
            "max_loan_by_msr_sgd": round(max_loan, 2),
            "msr_monthly_headroom_sgd": round(msr_limit, 2),
            "est_monthly_for_budget_fullloan_sgd": round(est_monthly_for_budget, 2) if est_monthly_for_budget else None
        },
        "cashflow_placeholders": cash_items,
        "cpf_lease": lease_flag
    }
    return out

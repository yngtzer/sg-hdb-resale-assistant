from datetime import date

def build_block_checklist(town: str, block: str | None, flat_type: str, today: date) -> str:
    headline = f"HDB Resale Block Checklist — {town}{' Blk ' + block if block else ''} ({flat_type}) — {today.isoformat()}"
    lines = [
        headline,
        "",
        "1) EIP / SPR quota:",
        "   - Check official EIP/SPR status for this block before offering.",
        "   - If reached for my profile, shortlist nearby blocks where quota is open.",
        "",
        "2) Recent transactions (fair price checks):",
        f"   - Review HDB 'Check Resale Flat Prices' for {town}{' Blk ' + block if block else ''}.",
        "   - Compare last 6–12 months median, IQR, and any outliers.",
        "",
        "3) Request for Value (valuation timing):",
        "   - After OTP, submit Request for Value by next working day.",
        "   - COV risk: if seller price > valuation, difference is CASH only.",
        "",
        "4) Lease & CPF usage:",
        "   - Confirm remaining lease and whether it covers youngest buyer to age 95.",
        "   - If not, CPF usage may be limited (use official calculator).",
        "",
        "5) Grants:",
        "   - Check eligibility for CPF Housing Grant, Enhanced CPF Housing Grant, PHG (if within 4km).",
        "",
        "6) Timeline:",
        "   - OTP validity ~21 days; resale application before expiry.",
        "   - Completion typically ~8 weeks after HDB accepts the application.",
        "",
        "7) Quick links:",
        "   - HFE letter (Flat Portal).",
        "   - EIP/SPR overview & checker.",
        "   - Check Resale Flat Prices.",
        "   - CPF usage (lease to 95 rule).",
    ]
    return "\n".join(lines)

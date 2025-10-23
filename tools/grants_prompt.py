from typing import Optional, Dict, Any

def build_grants_prompt(
    is_first_timer: bool,
    scheme: str,                 # "Family" | "Singles"
    citizenship: str,            # "SC" | "SC+SPR" | "SPR"
    household_income: int,
    flat_type: str,              # "3 ROOM" | "4 ROOM" | ...
    within_4km_of_parents: Optional[bool],  # PHG hint
) -> str:
    """Compose a concise, retrieval-friendly question for the RAG."""
    ftimer = "first-timer" if is_first_timer else "not first-timer"
    near_parents = (
        "within 4km of parents (potential PHG)" if within_4km_of_parents
        else "not within 4km of parents (PHG likely not applicable)"
        if within_4km_of_parents is not None else "unknown proximity to parents"
    )
    # Keep the ask specific, but neutral; let the official pages drive amounts/eligibility.
    question = (
        f"For a {ftimer} buyer under the {scheme} scheme with citizenship '{citizenship}', "
        f"household income ${household_income:,} and flat type '{flat_type}', "
        f"{near_parents}. What resale grants might apply in Singapore (CPF Housing Grant, Enhanced CPF Housing Grant (EHG), "
        f"Proximity Housing Grant (PHG)) and their latest eligibility rules and amounts? "
        f"Please itemize each grant, explain the conditions, give amount ranges/tiers if applicable, and show total potential grant. "
        f"Include short citations to the official HDB/CPF pages."
    )
    return question

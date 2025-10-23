def build_eip_spr_prompt(
    ethnicity: str,            # e.g., "Chinese", "Malay", "Indian/Others"
    profile: str,              # e.g., "SC", "SC+SPR", "SPR"
    town: str,
    block: str | None
) -> str:
    """
    Compose a concise retrieval-friendly question about EIP/SPR rules for a specific buyer profile.
    We don't guess live quota; we explain rules and link to the official checker.
    """
    blk_txt = f"block '{block}' in {town}" if block else f"the town '{town}'"
    return (
        f"Explain how HDB's Ethnic Integration Policy (EIP) and SPR Quota work for resale buyers in Singapore. "
        f"Buyer profile: ethnicity '{ethnicity}', household citizenship '{profile}'. "
        f"Context location: {blk_txt}. "
        f"Cover: (1) what EIP/SPR quota means at block/neighbourhood level, "
        f"(2) what happens if the quota is reached, (3) when/how to check officially, and "
        f"(4) any timing or application tips related to the resale process. "
        f"Keep it concise and include short citations to official HDB pages."
    )

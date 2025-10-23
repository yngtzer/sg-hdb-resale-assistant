from dataclasses import dataclass
from typing import Optional, Dict, Any

@dataclass
class ReadinessInputs:
    has_hfe: bool
    understands_eip_spr: bool
    knows_grants: bool
    ran_afford_calc: bool

def readiness_score(inp: ReadinessInputs) -> Dict[str, Any]:
    checks = {
        "HFE letter ready": inp.has_hfe,
        "Understands EIP/SPR basics": inp.understands_eip_spr,
        "Reviewed grant options": inp.knows_grants,
        "Checked affordability (MSR/CPF)": inp.ran_afford_calc,
    }
    total = len(checks)
    done = sum(1 for v in checks.values() if v)
    pct = round((done / total) * 100) if total else 0
    status = ("On track" if pct >= 75 else "Getting there" if pct >= 50 else "Start here")
    return {"percent": pct, "status": status, "checks": checks}

from dataclasses import dataclass
from datetime import date, timedelta

# Basic working-day helper (Sat/Sun off; SG PH not modelled)
def next_working_day(d: date) -> date:
    nd = d + timedelta(days=1)
    while nd.weekday() >= 5:  # 5=Sat,6=Sun
        nd += timedelta(days=1)
    return nd

@dataclass
class TimelineInputs:
    otp_signed_on: date
    completion_weeks: int = 8  # typical from HDB acceptance to completion
    rfv_due_next_workday: bool = True

def build_timeline(inp: TimelineInputs):
    items = []
    # 1) OTP signed
    items.append(("Option to Purchase (OTP) signed", inp.otp_signed_on))

    # 2) Request for Value (next working day after OTP)
    if inp.rfv_due_next_workday:
        rfv_date = next_working_day(inp.otp_signed_on)
        items.append(("Submit Request for Value (HDB)", rfv_date))

    # 3) Resale application submission (buyer/seller)
    # We don’t pin an exact date; show a target window: within ~21 days (OTP validity).
    app_deadline = inp.otp_signed_on + timedelta(days=21)
    items.append(("Submit resale application (target, within 21 days of OTP)", app_deadline))

    # 4) Completion ~8 weeks after HDB accepts the application
    # We don’t know the acceptance date; show a planning anchor = app_deadline + 56 days
    completion_est = app_deadline + timedelta(weeks=inp.completion_weeks)
    items.append((f"Estimated completion (~{inp.completion_weeks} weeks after acceptance, planning anchor)", completion_est))

    return items

def fmt_money(x):
    try:
        return f"${x:,.0f}"
    except Exception:
        return "-"

def fmt_psf(x):
    try:
        return f"${x:,.0f} psf"
    except Exception:
        return "-"

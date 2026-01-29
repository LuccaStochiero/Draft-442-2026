import pandas as pd

def robust_to_float(x):
    """
    Robustly converts input to float, handling commas and dots.
    Returns 0.0 on failure.
    """
    if x is None: return 0.0
    try:
        if isinstance(x, str):
            x = x.replace(',', '.')
        return float(x)
    except:
        return 0.0

def format_br_decimal(x):
    """
    Returns float to let Google Sheets handle formatting.
    Sending strings caused interpretation errors (e.g. 1,50 -> 150).
    """
    try:
        if isinstance(x, str):
            x = x.replace(',', '.')
        return float(x)
    except:
        return 0.0

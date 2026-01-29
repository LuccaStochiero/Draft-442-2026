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
    Formats a float to a string with 4 decimal places and comma separator.
    """
    try:
        val = float(x)
        return f"{val:.4f}".replace('.', ',')
    except:
        return "0,0000"

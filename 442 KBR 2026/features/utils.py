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
    Returns STRING with comma decimal for PT-BR Sheets.
    e.g. 10.5 -> '10,50'
    """
    try:
        if isinstance(x, str):
            x = x.replace(',', '.')
        val = float(x)
        return "{:.2f}".format(val).replace('.', ',')
    except:
        return "0,00"

POS_MAPPING = {
    'Goalkeeper': 'GK',
    'Defender': 'DEF',
    'Midfielder': 'MEI',
    'Forward': 'ATA'
}

def clean_pos(p):
    return POS_MAPPING.get(p, p)

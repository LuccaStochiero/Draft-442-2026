from features.auth import get_client
import pandas as pd

def debug_reading():
    client, sh = get_client()
    ws = sh.worksheet("H2H - TEAM_POINTS")
    
    # Check what get_all_records returns
    print("--- RAW get_all_records ---")
    data = ws.get_all_records()
    if not data:
        print("Empty")
        return

    # Check first 5 rows
    for i, row in enumerate(data[:5]):
        val = row.get('pontuacao')
        print(f"Row {i} pontuacao: {repr(val)} (Type: {type(val)})")
        
    # Check for any value that looks like our problem
    print("\n--- Searching for '85' or '8,5' ---")
    for row in data:
        val = row.get('pontuacao')
        if str(val).replace('.', '').replace(',', '') in ['85', '850', '425']:
             print(f"Found suspect value: {repr(val)}") 
             # Just print first few matches
             break

if __name__ == "__main__":
    debug_reading()

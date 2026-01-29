"""Debug script to inspect raw values from PLAYER_POINTS and H2H - TEAM_POINTS"""
from features.auth import get_client
import pandas as pd

def debug_sheets():
    client, sh = get_client()
    
    # 1. Check PLAYER_POINTS using get_values (raw strings)
    print("=== PLAYER_POINTS (using get_values) ===")
    ws_pts = sh.worksheet("PLAYER_POINTS")
    raw_values = ws_pts.get_values()
    if raw_values and len(raw_values) > 1:
        headers = raw_values[0]
        print(f"Columns: {headers}")
        print(f"First 5 rows:")
        for i, row in enumerate(raw_values[1:6]):
            # Find pontuacao column
            if 'pontuacao' in headers:
                idx = headers.index('pontuacao')
                pont_val = row[idx] if len(row) > idx else 'N/A'
                print(f"  Row {i}: pontuacao = {repr(pont_val)}")
    else:
        print("Empty or no data")
    
    # 2. Check H2H - TEAM_POINTS
    print("\n=== H2H - TEAM_POINTS ===")
    ws_h2h = sh.worksheet("H2H - TEAM_POINTS")
    data_h2h = ws_h2h.get_all_records()
    if data_h2h:
        df_h2h = pd.DataFrame(data_h2h)
        print(f"Columns: {df_h2h.columns.tolist()}")
        print(f"First 5 rows pontuacao:")
        for i, row in enumerate(data_h2h[:5]):
            val = row.get('pontuacao')
            print(f"  Row {i}: {repr(val)} (type: {type(val).__name__})")
    else:
        print("Empty")

if __name__ == "__main__":
    debug_sheets()

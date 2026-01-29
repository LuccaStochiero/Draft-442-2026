from features.auth import get_client
import pandas as pd

def debug_values_v2():
    client, sh = get_client()
    ws = sh.worksheet("H2H - TEAM_POINTS")
    data = ws.get_all_records()
    
    if not data: 
        print("Empty.")
        return
        
    print("Keys:", list(data[0].keys()))
    
    for i, row in enumerate(data[:5]):
        print(f"Row {i}: {row}")

if __name__ == "__main__":
    debug_values_v2()

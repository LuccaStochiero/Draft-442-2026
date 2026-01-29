from features.auth import get_client
import pandas as pd

def inspect():
    client, sh = get_client()
    
    print("--- TEAM_LINEUP ---")
    try:
        ws = sh.worksheet('TEAM_LINEUP')
        print(ws.row_values(1))
        # Determine how starters/subs are marked. Maybe looking at some rows?
        print(ws.row_values(2)) 
        print(ws.row_values(3)) 
    except Exception as e:
        print(e)
        
    print("\n--- GAMEWEEK ---")
    try:
        ws = sh.worksheet('GAMEWEEK')
        print(ws.row_values(1))
        print(ws.row_values(2))
    except Exception as e:
        print(e)

if __name__ == "__main__":
    inspect()

import pandas as pd
from features.auth import get_client

def debug_table():
    print("--- DEBUGGING H2H - TABLE ---")
    try:
        client, sh = get_client()
        ws = sh.worksheet("H2H - TABLE")
        data = ws.get_all_records()
        df = pd.DataFrame(data)
        
        print(f"Worksheet Found: {ws.title}")
        print(f"Record Count: {len(data)}")
        
        if not df.empty:
            print("Columns:", df.columns.tolist())
            print("First 5 rows:")
            print(df.head())
        else:
            print("WARNING: Dataframe is empty.")
            
            # Check raw values including header
            raw = ws.get_values()
            print("Raw Values (first 3 rows):")
            for r in raw[:3]:
                print(r)
                
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    debug_table()

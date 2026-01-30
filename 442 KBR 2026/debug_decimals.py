import streamlit as st
import pandas as pd
from features.auth import get_client

def debug_sheet_values():
    client, sh = get_client()
    ws = sh.worksheet("H2H - TABLE")
    
    # Get raw values (list of lists) to avoid pandas inference for a moment
    raw_values = ws.get_all_values()
    
    print("--- RAW VALUES (First 3 rows) ---")
    for row in raw_values[:3]:
        print(row)
        
    # Get all records (dict)
    records = ws.get_all_records()
    df = pd.DataFrame(records)
    
    print("\n--- DATAFRAME HEAD (PF/PS Columns) ---")
    if 'PF' in df.columns and 'PS' in df.columns:
        print(df[['team_id', 'PF', 'PS']].head())
        print("\n--- DTYPES ---")
        print(df.dtypes)
        
        # Check specific values
        print("\n--- SAMPLE VALUES ---")
        for val in df['PF'].head(3):
            print(f"PF Value: {repr(val)} Type: {type(val)}")

if __name__ == "__main__":
    debug_sheet_values()

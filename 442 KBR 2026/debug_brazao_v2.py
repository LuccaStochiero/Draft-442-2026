import pandas as pd
import streamlit as st
from features.auth import get_client
from features.live_stats import calculate_points, STATS_SHEET, POINTS_SHEET

def debug_brazao_v2(target_pid="905448"):
    print(f"--- Debugging Player ID: {target_pid} (V2) ---")
    
    client, sh = get_client()
    
    # 1. Fetch Raw Stats from Sheet
    print("Fetching PLAYERS_STATS...")
    ws_stats = sh.worksheet(STATS_SHEET)
    data_stats = ws_stats.get_all_records()
    df_stats = pd.DataFrame(data_stats)
    
    # Find Brazao
    def match(val): return target_pid in str(val)
    player_rows = df_stats[df_stats['player_id'].apply(match)]
    
    if player_rows.empty:
        print("❌ Player not found in stats sheet.")
        return
        
    print(f"✅ Found {len(player_rows)} raw entries.")
    
    for i, row in player_rows.iterrows():
        print(f"\n--- Entry {i} ---")
        fouls = row.get('fouls')
        pen_conceded = row.get('penaltyConceded')
        print(f"Fouls (Sheet): {fouls}")
        print(f"Pen Conceded (Sheet): {pen_conceded}")
        
        # Create single-row DF for calculation
        # We need to ensure columns match what calculate_points expects
        # calculate_points expects a DF where columns are numeric.
        # But 'row' from get_all_records might be int or str.
        # The function `calculate_points` does `pd.to_numeric` conversion internally.
        
        calc_df = pd.DataFrame([row])
        
        # Run Calculation
        print("Running calculate_points on this raw data...")
        res_df = calculate_points(calc_df)
        
        if not res_df.empty:
            new_score = res_df.iloc[0]['PONTUACAO_LUCCA_MATCH']
            print(f"🧮 Calculated Score (Local Logic): {new_score}")
        else:
            print("⚠️ Calculation returned empty.")

    # 2. Check Stored Points
    print("\nFetching PLAYER_POINTS...")
    ws_points = sh.worksheet(POINTS_SHEET)
    data_points = ws_points.get_all_records()
    df_points = pd.DataFrame(data_points)
    
    stored_rows = df_points[df_points['player_id'].apply(match)]
    if not stored_rows.empty:
        stored_score = stored_rows.iloc[0].get('pontuacao')
        print(f"💾 Stored Score (Sheet): {stored_score}")
    else:
        print("❌ Player not found in points sheet.")

if __name__ == "__main__":
    debug_brazao_v2()

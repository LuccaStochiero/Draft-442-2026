import pandas as pd
import streamlit as st
from features.auth import get_client
from features.live_stats import calculate_points, STATS_SHEET, POINTS_SHEET, save_points_to_sheet

def recalculate_all():
    print("--- Recalculating Points for ALL Games ---")
    
    client, sh = get_client()
    
    # 1. Fetch ALL Raw Stats
    print("Fetching ALL PLAYERS_STATS...")
    ws_stats = sh.worksheet(STATS_SHEET)
    data_stats = ws_stats.get_all_records()
    df_stats = pd.DataFrame(data_stats)
    
    if df_stats.empty:
        print("No stats found.")
        return

    print(f"Loaded {len(df_stats)} rows.")
    
    # 2. Recalculate
    print("Recalculating points...")
    points_df = calculate_points(df_stats)
    
    # 3. Save (Overwrite mode usually needed for full update)
    # save_points_to_sheet logic usually merges active games. 
    # But since we are passing EVERYTHING, we can just dump it?
    # save_points_to_sheet has logic:
    #   if existing:
    #       mask = ~existing['game_id'].isin(updated_game_ids)
    #       final = concat(existing[mask], new)
    # If we pass ALL game_ids, 'mask' will be empty (all overridden), which is exactly what we want.
    
    if points_df.empty:
        print("Calculation resulted in empty DataFrame.")
        return
        
    print(f"Saving {len(points_df)} points rows...")
    save_points_to_sheet(points_df)
    
    print("✅ Full Recalculation Complete.")

if __name__ == "__main__":
    recalculate_all()

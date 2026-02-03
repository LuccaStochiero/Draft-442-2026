import pandas as pd
import streamlit as st
from features.auth import get_client

def debug():
    print("--- START DEBUG ---")
    client, sh = get_client()
    
    # 1. Load GAMEWEEK
    ws_gw = sh.worksheet("GAMEWEEK")
    df_gw = pd.DataFrame(ws_gw.get_all_records())
    print(f"\n[GAMEWEEK] Total Rows: {len(df_gw)}")
    print(df_gw.columns)
    
    # Round 1 Games
    r1_games = df_gw[df_gw['rodada'] == 1]['id_jogo'].unique()
    print(f"\n[R1 Games] Count: {len(r1_games)}")
    print(r1_games[:3])
    
    # Round 2 Games
    r2_games = df_gw[df_gw['rodada'] == 2]['id_jogo'].unique()
    print(f"\n[R2 Games] Count: {len(r2_games)}")
    print(r2_games[:3])
    
    # Intersection?
    inter = set(r1_games) & set(r2_games)
    print(f"\n[INTERSECTION R1/R2] {inter}")
    
    # 2. Load PLAYER_POINTS
    ws_pts = sh.worksheet("PLAYER_POINTS")
    # Using get_values to see raw strings
    raw_pts = ws_pts.get_values()
    df_pts = pd.DataFrame(raw_pts[1:], columns=raw_pts[0])
    print(f"\n[PLAYER_POINTS] Total Rows: {len(df_pts)}")
    
    # Check Game IDs in Points
    pts_gids = df_pts['game_id'].unique()
    print(f"\n[Unique Game IDs in POINTS] Count: {len(pts_gids)}")
    print(pts_gids[:10])
    
    # Do any points have Round 2 IDs?
    r2_game_ids_str = set([str(x) for x in r2_games])
    
    # Helper to strip URL
    def clean_id(x):
        s = str(x)
        if "id:" in s: return s.split("id:")[-1]
        if "/" in s: return s.split("/")[-1]
        return s
    
    r2_clean = {clean_id(x) for x in r2_games}
    print(f"\n[R2 IDs Clean] {r2_clean}")
    
    # Filter Points matching R2
    # We want to see if there are points associated with R2 games
    # OR if the points associated with R1 games are somehow being picked up by R2 logic
    
    # Check what IDs in POINTS match R2 Clean
    matching_pts = df_pts[df_pts['game_id'].apply(clean_id).isin(r2_clean)]
    print(f"\n[POINTS matching R2 IDs] Count: {len(matching_pts)}")
    if not matching_pts.empty:
        print(matching_pts.head())
    
    print("--- END DEBUG ---")

if __name__ == "__main__":
    debug()

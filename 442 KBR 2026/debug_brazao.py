import pandas as pd
from features.auth import get_client
from features.live_stats import STATS_SHEET, POINTS_SHEET

def debug_brazao(target_pid="905448"):
    print(f"--- Debugging Player ID: {target_pid} ---")
    
    client, sh = get_client()
    
    # 1. Fetch Raw Stats
    ws_stats = sh.worksheet(STATS_SHEET)
    data_stats = ws_stats.get_all_records()
    df_stats = pd.DataFrame(data_stats)
    
    print("Searching in PLAYERS_STATS...")
    
    def match(val):
        return target_pid in str(val)
        
    player_stats = df_stats[df_stats['player_id'].apply(match)]
    
    if player_stats.empty:
        print("❌ Player NOT found in PLAYERS_STATS.")
    else:
        print(f"✅ Found {len(player_stats)} records in PLAYERS_STATS.")
        for _, row in player_stats.iterrows():
            print("\n[RAW STATS]")
            for k, v in row.items():
                if v != 0 and v != '' and v != '0':
                    print(f"  {k}: {v}")
            
            # Print specific fields needed for calculation verification
            fields = ['Posição', 'gols_sofridos_partida', 'rating', 'minutesPlayed', 'saves', 'savedShotsFromInsideTheBox', 'goalsPrevented', 'accurateKeeperSweeper', 'goalLineClearance']
            print("\n[KEY FIELDS]")
            for f in fields:
                print(f"  {f}: {row.get(f)}")

    # 2. Fetch Points Sheet
    print("\n\nSearching in PLAYER_POINTS...")
    ws_points = sh.worksheet(POINTS_SHEET)
    data_points = ws_points.get_all_records()
    df_points = pd.DataFrame(data_points)
    
    player_points = df_points[df_points['player_id'].apply(match)]
    if player_points.empty:
         print("❌ Player NOT found in PLAYER_POINTS.")
    else:
        print(f"✅ Found {len(player_points)} records in PLAYER_POINTS.")
        for _, row in player_points.iterrows():
             print(f"  Game: {row.get('game_id')} -> Points: {row.get('pontuacao')}")

if __name__ == "__main__":
    debug_brazao()

"""Script to recalculate ALL points from stats and COMPLETELY OVERWRITE the PLAYER_POINTS sheet."""
import pandas as pd
from features.auth import get_client
from features.live_stats import calculate_points, STATS_SHEET, POINTS_SHEET
from features.utils import robust_to_float, format_br_decimal

def recalculate_all():
    print("--- Recalculating Points for ALL Games (FULL OVERWRITE) ---")
    
    client, sh = get_client()
    
    # 1. Fetch ALL Raw Stats
    print("Fetching ALL PLAYERS_STATS...")
    ws_stats = sh.worksheet(STATS_SHEET)
    data_stats = ws_stats.get_all_records()
    df_stats = pd.DataFrame(data_stats)
    
    if df_stats.empty:
        print("No stats found.")
        return

    print(f"Loaded {len(df_stats)} rows from PLAYERS_STATS.")
    
    # 2. Recalculate Points
    print("Recalculating points...")
    points_df = calculate_points(df_stats)
    
    if points_df.empty:
        print("Calculation resulted in empty DataFrame.")
        return
    
    # Rename column for sheet
    points_df = points_df.rename(columns={'PONTUACAO_LUCCA_MATCH': 'pontuacao'})
    
    # 3. Format pontuacao for BR locale (comma as decimal separator)
    print("Formatting pontuacao for BR locale...")
    points_df['pontuacao'] = points_df['pontuacao'].apply(robust_to_float)
    points_df['pontuacao'] = points_df['pontuacao'].apply(format_br_decimal)
    
    # 4. COMPLETE OVERWRITE - do NOT merge with existing data
    print(f"Saving {len(points_df)} points rows (FULL OVERWRITE)...")
    
    try:
        ws = sh.worksheet(POINTS_SHEET)
    except:
        ws = sh.add_worksheet(POINTS_SHEET, 1000, 3)
    
    # Prepare data
    header = ['game_id', 'player_id', 'pontuacao']
    final_df = points_df[header]
    final_values = [header] + final_df.values.tolist()
    
    # Clear and write (fixed argument order for gspread >= 5.0)
    ws.clear()
    ws.update(values=final_values, range_name='A1', value_input_option='USER_ENTERED')
    
    print("✅ Full Recalculation Complete (PLAYER_POINTS overwritten).")

if __name__ == "__main__":
    recalculate_all()

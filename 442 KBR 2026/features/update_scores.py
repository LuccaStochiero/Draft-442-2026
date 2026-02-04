import pandas as pd
import time
import datetime
import argparse
from features.data_cache import load_gameweek_data
from features.live_stats import (
    fetch_event_details,
    fetch_sofascore_lineups,
    fetch_game_comments,
    get_player_pos_map,
    extract_stats,
    calculate_points,
    STATS_SHEET,
    POINTS_SHEET
)
from features.auth import get_client
from features.utils import robust_to_float, format_br_decimal
from features.team_points import calculate_team_points

def save_custom_stats(all_stats_rows, numeric_ids_to_purge):
    if not all_stats_rows: return
    
    try:
        client, sh = get_client()
        ws = sh.worksheet(STATS_SHEET)
        
        # 1. Get all existing records
        existing_data = ws.get_all_records()
        existing_df = pd.DataFrame(existing_data)
        
        # 2. Prepare New Data
        new_df = pd.DataFrame(all_stats_rows)
        
        # Standard cols from live_stats matching Sheets structure
        STATS_COLUMNS = [
            'game_id', 'player_id', 'Posição', 'gols_sofridos_partida', 'rating', 'ownGoals', 'yellowCards', 'redCards', 
            'totalOffside', 'dispossessed', 'minutesPlayed', 'penaltySave', 'penaltyWon', 
            'penaltyConceded', 'penaltyMiss', 'totalPass', 'accuratePass', 
            'totalLongBalls', 'accurateLongBalls', 'duelWon', 'duelLost', 
            'wonContest', 'totalContest', 'keyPass', 'wasFouled', 'fouls',
            'totalClearance', 'outfielderBlock', 'interceptionWon', 'wonTackle', 
            'savedShotsFromInsideTheBox', 'saves', 'punches', 'goodHighClaim', 
            'accurateKeeperSweeper', 'goals', 'goalAssist', 'goalLineClearance', 
            'shotOffTarget', 'onTargetScoringAttempt', 'hitWoodwork', 'goalsPrevented',
            'updated_at' 
        ]
        
        for c in STATS_COLUMNS:
            if c not in new_df.columns: new_df[c] = ''
        new_df = new_df[STATS_COLUMNS]
        
        # 3. Filter Existing
        if not existing_df.empty:
            existing_df['game_id'] = existing_df['game_id'].astype(str)
            
            updated_ids = new_df['game_id'].unique().astype(str).tolist()
            purge_ids = [str(x) for x in numeric_ids_to_purge]
            
            # Mask: Keep if NOT in updated_ids AND NOT in purge_ids
            mask = (~existing_df['game_id'].isin(updated_ids)) & (~existing_df['game_id'].isin(purge_ids))
            
            final_df = pd.concat([existing_df[mask], new_df], ignore_index=True)
        else:
            final_df = new_df
            
        # 4. Write
        final_values = [STATS_COLUMNS] + final_df.astype(str).values.tolist()
        ws.clear()
        ws.update('A1', final_values)
        print(f"Stats Saved. Purged numeric IDs: {numeric_ids_to_purge}")
        
    except Exception as e:
        print(f"Error saving stats: {e}")

def save_custom_points(points_df, numeric_ids_to_purge):
    if points_df.empty: return
    try:
        client, sh = get_client()
        ws = sh.worksheet(POINTS_SHEET)
        
        existing_data = ws.get_all_records()
        existing_df = pd.DataFrame(existing_data)
        
        updated_ids = points_df['game_id'].unique().astype(str).tolist()
        purge_ids = [str(x) for x in numeric_ids_to_purge]
        
        # Prepare New
        points_df_renamed = points_df.rename(columns={'PONTUACAO_LUCCA_MATCH': 'pontuacao'})
        
        if not existing_df.empty:
            existing_df['game_id'] = existing_df['game_id'].astype(str)
            mask = (~existing_df['game_id'].isin(updated_ids)) & (~existing_df['game_id'].isin(purge_ids))
            final_df = pd.concat([existing_df[mask], points_df_renamed], ignore_index=True)
        else:
            final_df = points_df_renamed
            
        # Format
        header = ['game_id', 'player_id', 'pontuacao']
        if 'pontuacao' in final_df.columns:
             final_df['pontuacao'] = final_df['pontuacao'].apply(robust_to_float).apply(format_br_decimal)
             
        final_df = final_df[header]
        final_values = [header] + final_df.values.tolist()
        ws.clear()
        ws.update('A1', final_values, value_input_option='USER_ENTERED')
        print(f"Points Saved. Purged numeric IDs: {numeric_ids_to_purge}")
        
    except Exception as e:
        print(f"Error saving points: {e}")

def run_update(target_round=None):
    if target_round is None:
        print("Please specify a target round.")
        return

    print(f"--- Starting Unified Score Update for Round {target_round} ---")
    
    # --- PHASE 1: STATS & POINTS ---
    df_gw = load_gameweek_data()
    
    if 'rodada' in df_gw.columns:
        df_gw['rodada'] = pd.to_numeric(df_gw['rodada'], errors='coerce')
        round_games = df_gw[df_gw['rodada'] == target_round]
    else:
        round_games = pd.DataFrame()

    if round_games.empty:
        print(f"No games found for Round {target_round} in GAMEWEEK sheet.")
    else:
        print(f"Found {len(round_games)} games for Round {target_round}.")
        
        all_stats_rows = []
        numeric_ids_processed = []
        pos_map = get_player_pos_map()

        for index, row in round_games.iterrows():
            raw_id_jogo = str(row.get('id_jogo', '')).strip()
            
            # Extract Numeric ID
            if 'id:' in raw_id_jogo:
                numeric_id = raw_id_jogo.split('id:')[-1]
            elif '/' in raw_id_jogo:
                 numeric_id = raw_id_jogo.split('/')[-1]
            else:
                numeric_id = raw_id_jogo
            numeric_id = ''.join(filter(str.isdigit, numeric_id))
            
            if not numeric_id: continue
            
            # Use full URL from sheet as ID for saving
            saving_game_id = raw_id_jogo

            home_team = row.get('home_team', 'Home')
            away_team = row.get('away_team', 'Away')
            
            print(f"Processing {home_team} vs {away_team} (API: {numeric_id}) -> Saving ID: {saving_game_id}...")
            
            details = fetch_event_details(numeric_id)
            if not details: 
                print("  - Failed details.")
                continue
                
            event = details.get('event', {})
            home_score = event.get('homeScore', {}).get('current', 0)
            away_score = event.get('awayScore', {}).get('current', 0)
            status_code = event.get('status', {}).get('code', 0)
            
            # 0=Not Started, 60=Postponed, 70=Canceled, 100=Ended, 6/7=HT/2nd
            # We assume we only process if it has started? Or strictly started.
            if status_code == 0:
                print("  - Not started.")
                continue

            lineups_data = fetch_sofascore_lineups(numeric_id)
            if not lineups_data: continue
                
            comments_data = fetch_game_comments(numeric_id)
            card_map = {}
            if comments_data:
                from features.live_stats import parse_cards_from_comments
                card_map = parse_cards_from_comments(comments_data)

            teams = [('home', lineups_data.get('home', {})), ('away', lineups_data.get('away', {}))]
            
            for side, team_data in teams:
                players = team_data.get('players', [])
                for p_data in players:
                    stats_row = extract_stats(
                        player_data=p_data,
                        game_id=saving_game_id,
                        team_side=side,
                        home_score=home_score,
                        away_score=away_score,
                        pos_map=pos_map,
                        card_map=card_map
                    )
                    if stats_row:
                        all_stats_rows.append(stats_row)
            
            numeric_ids_processed.append(numeric_id)
            time.sleep(1)

        # Save Phase 1
        if all_stats_rows:
            print(f"Calculating points for {len(all_stats_rows)} records...")
            df_stats = pd.DataFrame(all_stats_rows)
            df_points = calculate_points(df_stats)
            
            print("Saving Stats & Points...")
            save_custom_stats(all_stats_rows, numeric_ids_processed)
            save_custom_points(df_points, numeric_ids_processed)
        else:
            print("No new stats extracted for this round.")

    # --- PHASE 2: TEAM POINTS ---
    print(f"--- Updating H2H Team Points for Round {target_round} ---")
    calculate_team_points(target_round=target_round)
    print("--- Unified Update Complete ---")

if __name__ == "__main__":
    import sys
    # Simple arg parse
    try:
        r_arg = int(sys.argv[1])
    except:
        r_arg = 2 # Default to 2 if not provided
        
    run_update(r_arg)

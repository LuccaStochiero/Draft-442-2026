import pandas as pd
import datetime
from features.auth import get_client
from features.live_stats import (
    fetch_sofascore_lineups,
    fetch_event_details,
    fetch_game_comments,
    parse_cards_from_comments,
    get_player_pos_map,
    extract_stats,
    save_stats_to_sheet,
    calculate_points,
    save_points_to_sheet,
    GAMEWEEK_SHEET
)
from features.team_points import calculate_team_points
from features.league_table import update_league_table

# Configuration
TARGET_DATES = ["28/01/2026", "29/01/2026"]

def manual_update_scores():
    print(f"--- Manual Score Update for {TARGET_DATES} ---")

    # 1. Get Games for Target Date
    client, sh = get_client()
    ws_gw = sh.worksheet(GAMEWEEK_SHEET)
    gw_data = ws_gw.get_all_records()
    df_gw = pd.DataFrame(gw_data)
    
    # Filter by date
    target_games = []
    
    print(f"Scanning {len(df_gw)} games in GAMEWEEK...")
    
    for _, row in df_gw.iterrows():
        dt_str = str(row.get('data_hora', ''))
        if any(d in dt_str for d in TARGET_DATES):
            target_games.append(row)
            
    if not target_games:
        print(f"No games found for dates {TARGET_DATES}.")
        return

    print(f"Found {len(target_games)} games for {TARGET_DATES}.")
    
    # 2. Extract Stats
    all_game_stats = []
    enriched_data_for_calc = []
    
    pos_map = get_player_pos_map()
    
    for game in target_games:
        raw_id = str(game.get('id_jogo', ''))
        
        # Extract API ID
        if 'id:' in raw_id: 
            api_id = raw_id.split('id:')[-1]
        elif '/' in raw_id: 
            api_id = raw_id.split('/')[-1]
        else: 
            api_id = raw_id
            
        print(f"Processing Game: {game.get('home_team')} vs {game.get('away_team')} (ID: {api_id})")
        
        # A. Fetch Score
        event_details = fetch_event_details(api_id)
        home_score = 0
        away_score = 0
        if event_details:
             event = event_details.get('event', {})
             home_score = event.get('homeScore', {}).get('current', 0)
             away_score = event.get('awayScore', {}).get('current', 0)
        
        # B. Fetch Lineups
        data = fetch_sofascore_lineups(api_id)
        if not data: 
            print(f"  -> Failed to fetch lineups for {api_id}")
            continue
            
        # C. Fetch Comments (Cards Override)
        comments_data = fetch_game_comments(api_id)
        card_map = parse_cards_from_comments(comments_data)
        
        # Process Home
        home_players = data.get('home', {}).get('players', [])
        for p in home_players:
            row = extract_stats(p, raw_id, 'home', home_score, away_score, pos_map, card_map)
            all_game_stats.append(row)
            enriched_data_for_calc.append(row)
            
        # Process Away
        away_players = data.get('away', {}).get('players', [])
        for p in away_players:
            row = extract_stats(p, raw_id, 'away', home_score, away_score, pos_map, card_map)
            all_game_stats.append(row)
            enriched_data_for_calc.append(row)
            
    # 3. Save Raw Stats
    if all_game_stats:
        print(f"Saving {len(all_game_stats)} stats rows...")
        save_stats_to_sheet(all_game_stats)
        
        # 4. Calculate and Save Points
        print("Calculating points...")
        df_calc = pd.DataFrame(enriched_data_for_calc)
        points_df = calculate_points(df_calc)
        
        print(f"Saving {len(points_df)} points rows...")
        save_points_to_sheet(points_df)
        
        print("✅ Stats and Player Points Updated.")
        
        # 5. Update Team Points (H2H)
        print("Updating H2H - TEAM_POINTS...")
        calculate_team_points()
        
        # 6. Update League Table
        update_league_table()
        
    else:
        print("No stats extracted.")

if __name__ == "__main__":
    manual_update_scores()

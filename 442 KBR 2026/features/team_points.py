import pandas as pd
import datetime
import re
from features.auth import get_client
from features.live_stats import STATS_SHEET, POINTS_SHEET
from features.utils import robust_to_float, format_br_decimal

TEAM_POINTS_SHEET = "H2H - TEAM_POINTS"

def parse_time(t_str):
    if not t_str: return None
    try:
        return pd.to_datetime(t_str, dayfirst=True)
    except:
        return None

def calculate_team_points(target_round=None):
    client, sh = get_client()
    
    # 1. Load Data
    try:
        ws_lineup = sh.worksheet("TEAM_LINEUP")
        df_lineup = pd.DataFrame(ws_lineup.get_all_records())
        
        ws_gw = sh.worksheet("GAMEWEEK")
        df_gw = pd.DataFrame(ws_gw.get_all_records())
        
        # Use get_values for POINTS_SHEET to preserve comma-decimal strings
        ws_pts = sh.worksheet(POINTS_SHEET)
        pts_values = ws_pts.get_values()
        if pts_values and len(pts_values) > 1:
            df_pts = pd.DataFrame(pts_values[1:], columns=pts_values[0])
        else:
            df_pts = pd.DataFrame(columns=['game_id', 'player_id', 'pontuacao'])
        
        ws_stats = sh.worksheet(STATS_SHEET)
        df_stats = pd.DataFrame(ws_stats.get_all_records())
        
        # NEW: Load Players to link ID -> Club -> Game (for DNP check)
        try:
             ws_all = sh.worksheet("ALL_PLAYERS")
             df_players = pd.DataFrame(ws_all.get_all_records())
        except:
             df_players = pd.DataFrame()
        
    except Exception as e:
        print(f"Error loading sheets: {e}")
        return

    # Normalize Columns
    df_lineup.columns = [c.lower() for c in df_lineup.columns] 
    df_gw.columns = [c.lower() for c in df_gw.columns] 
    df_pts.columns = [c.lower() for c in df_pts.columns] 
    df_stats.columns = [c.lower() for c in df_stats.columns] 
    df_players.columns = [c.lower() for c in df_players.columns]
    
    # Robust numeric conversion for points
    if 'pontuacao' in df_pts.columns:
        df_pts['pontuacao'] = df_pts['pontuacao'].apply(robust_to_float)

    
    # Ensure IDs are strings
    df_lineup['player_id'] = df_lineup['player_id'].astype(str)
    df_lineup['team_id'] = df_lineup['team_id'].astype(str)
    df_pts['player_id'] = df_pts['player_id'].astype(str)
    df_stats['player_id'] = df_stats['player_id'].astype(str)
    df_players['player_id'] = df_players['player_id'].astype(str)

    # Map Player -> Club
    # normalization: verify 'club' or 'clube' or 'time' column in players
    club_col = next((c for c in df_players.columns if c in ['club', 'clube', 'team', 'time']), None)
    pid_to_club = {}
    if club_col:
        pid_to_club = pd.Series(df_players[club_col].values, index=df_players['player_id']).to_dict()

    # 2. Filter Round
    if target_round is None:
        rounds = df_lineup['rodada'].unique()
    else:
        rounds = [target_round]
        
    final_rows = []
    
    now = datetime.datetime.now()
    
    def clean_id(x): return str(x).split("id:")[-1]
    
    df_gw['simple_id'] = df_gw['id_jogo'].apply(clean_id)
    df_stats['simple_id'] = df_stats['game_id'].apply(clean_id)
    
    # Merge Stats + GW
    df_merged_full = df_stats.merge(df_gw[['simple_id', 'data_hora', 'rodada', 'home_team', 'away_team']], on='simple_id', how='left')
    
    player_game_map = {} # (pid, round) -> {minutes, is_finished}
    
    # Also build Club -> GameInfo map per round to catch DNP
    # (Club, Round) -> {is_finished, start_time}
    club_round_status = {}

    for _, row in df_merged_full.iterrows():
        pid = str(row['player_id'])
        rod = row.get('rodada')
        if pd.isna(rod) or str(rod) == '': continue
        
        mins = row.get('minutesplayed', 0)
        start_str = row.get('data_hora')
        
        is_finished = False
        if start_str:
            dt = parse_time(start_str)
            if dt:
                if (dt + datetime.timedelta(hours=3)) < now:
                    is_finished = True
        
        # Store Player Status
        player_game_map[(pid, int(rod))] = {'min': mins, 'finished': is_finished}
        
        # Store Club Status (Iteratively update)
        # We know this player's club played this game
        p_club = pid_to_club.get(pid)
        
        # FIX: Ensure this game actually involves the player's club
        # This prevents players with wrong game_ids (or transferred players) 
        # from marking their (new) club as 'finished' based on a game they didn't play as a team.
        game_home = row.get('home_team')
        game_away = row.get('away_team')
        
        if p_club and (p_club == game_home or p_club == game_away):
             club_round_status[(p_club, int(rod))] = {'finished': is_finished}

    # ... get_score helper ...
    def get_score(pid, rod):
        gids_in_round = df_gw[df_gw['rodada'] == rod]['simple_id'].tolist()
        df_pts['simple_id'] = df_pts['game_id'].apply(clean_id)
        subset = df_pts[ (df_pts['player_id'] == pid) & (df_pts['simple_id'].isin(gids_in_round)) ]
        if subset.empty: return 0.0
        return float(subset['pontuacao'].max())

    # 3. Process Per Team / Per Round
    for r in rounds:
        r = int(r)
        
        # Get lineups for this round
        round_lineup = df_lineup[df_lineup['rodada'] == r]
        teams = round_lineup['team_id'].unique()
        
        for tid in teams:
            team_players = round_lineup[round_lineup['team_id'] == tid]
            
            # Separate Starters and Subs
            # Identify Starters (Case-insensitive)
            starters = team_players[team_players['lineup'].astype(str).str.upper() == 'TITULAR'].copy()
            active_pids = starters['player_id'].astype(str).tolist()
            subs = team_players[team_players['lineup'].str.startswith('PRI', na=False)].copy()
            
            def get_pri(x):
                try: 
                    return int(str(x).split()[-1])
                except: 
                    return 99
            
            subs['priority'] = subs['lineup'].apply(get_pri)
            subs = subs.sort_values('priority')
            
            # Check Substitutions
            for _, starter in starters.iterrows():
                sid = starter['player_id']
                spos = starter['posicao']
                
                # DETERMINE STATUS
                is_finished = False
                mins = 0
                
                # 1. Direct Stats Lookup
                if (sid, r) in player_game_map:
                    s_data = player_game_map[(sid, r)]
                    is_finished = s_data['finished']
                    mins = s_data['min']
                else:
                    # 2. Fallback: Check Club Status
                    s_club = pid_to_club.get(sid)
                    
                    if s_club and (s_club, r) in club_round_status:
                        # Club played?
                        c_status = club_round_status[(s_club, r)]
                        if c_status['finished']:
                            is_finished = True
                            mins = 0 # DNP
                    # If Club not known or game not mapped, assume not finished -> No Sub
                
                if is_finished and mins == 0:
                     # MATCHES DNP CRITERIA
                    # CANDIDATE FOR SUB
                    # Find replacement
                    # Same Position, Highest Priority, (Played > 0 min? User implied valid score?)
                    # "entrada... de mesma pontuação" (Assumed Position)
                    
                    replacement = None
                    for _, sub in subs.iterrows():
                        sub_id = sub['player_id']
                        if sub_id in active_pids: continue 
                        
                        if sub['posicao'] == spos:
                            # Candidate found. Check if they PLAYED.
                            sub_mins = 0
                            if (sub_id, r) in player_game_map:
                                sub_mins = player_game_map[(sub_id, r)]['min']
                            
                            # Only accept if they played
                            if sub_mins > 0:
                                replacement = sub_id
                                break
                    
                    if replacement:
                         # PERFORM SUB
                         print(f"  [SUB] Player {pid_to_club.get(sid)} ID:{sid} (Mins: {mins}, Finished: {is_finished}) OUT.")
                         print(f"  [SUB] Replacement ID:{replacement} IN.")
                         
                         active_pids.remove(sid)
                         active_pids.append(replacement)
                         # Remove from potential subs pool (though loop handles it via active_pids check)
                         # But strictly speaking, a player can't be subbed IN twice anyway. 
                    else:
                        print(f"  [SUB FAIL] Player {pid_to_club.get(sid)} ID:{sid} DNP, but no valid sub found.")
                        print(f"   - Checked {len(subs)} bench players. (Pos: {spos})")
                        
            # Final Generation
            for _, p in team_players.iterrows():
                pid = str(p['player_id'])
                score = get_score(pid, r)
                
                in_active = (pid in active_pids)
                
                # Check if player is captain (cap column = 'CAPITAO')
                is_captain = str(p.get('cap', '')).upper() == 'CAPITAO'
                if is_captain and in_active:
                    score = score * 1.5  # Captain bonus
                
                # User wants: ["team_id", "player_id", "rodada", "pontuacao", "escalado", "cap"]
                final_rows.append({
                    "team_id": tid,
                    "player_id": pid,
                    "rodada": r,
                    "pontuacao": score,
                    "escalado": in_active, # "se ele entrou na escalacao titular" -> The final active lineup
                    "cap": 'CAPITAO' if is_captain else ''
                })

    # 4. Save
    df_out = pd.DataFrame(final_rows)
    
    # Format pontuacao as string with comma for PT-BR locale sheets
    if 'pontuacao' in df_out.columns:
        df_out['pontuacao'] = df_out['pontuacao'].apply(robust_to_float)
        # Removed format_br_decimal to pass raw float

    # Write to H2H - TEAM_POINTS
    try:
        try:
            ws_out = sh.worksheet(TEAM_POINTS_SHEET)
            # Load existing if we are doing a partial update
            if target_round is not None:
                # Use get_values to preserve formatting (UNFORMATTED to get floats)
                existing_values = ws_out.get_values(value_render_option='UNFORMATTED_VALUE')
                if existing_values and len(existing_values) > 1:
                    df_existing = pd.DataFrame(existing_values[1:], columns=existing_values[0])
                    # Generic cleanup of columns
                    df_existing.columns = [c.lower() for c in df_existing.columns]
                    
                    if 'pontuacao' in df_existing.columns:
                         df_existing['pontuacao'] = df_existing['pontuacao'].apply(robust_to_float)

                    # Filter out the round we are updating
                    if 'rodada' in df_existing.columns:
                        df_existing['rodada'] = pd.to_numeric(df_existing['rodada'], errors='coerce')
                        # Keep rows NOT in target_round
                        df_existing = df_existing[df_existing['rodada'] != int(target_round)]
                        
                        # Concatenate
                        df_out = pd.concat([df_existing, df_out], ignore_index=True)
                        
                        # Sort by rodada, team_id for cleanliness
                        df_out = df_out.sort_values(by=['rodada', 'team_id'])

        except:
            ws_out = sh.add_worksheet(TEAM_POINTS_SHEET, 1000, 5)
            
        ws_out.clear()
        # Use USER_ENTERED to respect sheet locale for decimal interpretation
        ws_out.update([df_out.columns.values.tolist()] + df_out.values.tolist(), value_input_option='USER_ENTERED')
        print("Updated H2H - TEAM_POINTS")
    except Exception as e:
        print(f"Error saving: {e}")

if __name__ == "__main__":
    calculate_team_points()

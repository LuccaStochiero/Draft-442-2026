import pandas as pd
import datetime
import re
from features.auth import get_client
from features.live_stats import STATS_SHEET, POINTS_SHEET

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
    except Exception as e:
        print(f"Error loading sheets: {e}")
        return

    # Normalize Columns
    df_lineup.columns = [c.lower() for c in df_lineup.columns] # team_id, player_id, rodada, lineup...
    df_gw.columns = [c.lower() for c in df_gw.columns] # id_jogo, ... data_hora
    df_pts.columns = [c.lower() for c in df_pts.columns] # game_id, player_id, pontuacao
    df_stats.columns = [c.lower() for c in df_stats.columns] # game_id, player_id, minutesplayed...
    
    # Robust numeric conversion for points
    if 'pontuacao' in df_pts.columns:
        def to_float(x):
            try:
                if isinstance(x, str): x = x.replace(',', '.')
                return float(x)
            except:
                return 0.0
        df_pts['pontuacao'] = df_pts['pontuacao'].apply(to_float)

    
    # Ensure IDs are strings
    df_lineup['player_id'] = df_lineup['player_id'].astype(str)
    df_lineup['team_id'] = df_lineup['team_id'].astype(str)
    df_pts['player_id'] = df_pts['player_id'].astype(str)
    df_stats['player_id'] = df_stats['player_id'].astype(str)

    # 2. Filter Round
    if target_round is None:
        # If not specified, do all? Or just current? User said "agora", maybe all known line ups?
        # Let's process ALL rounds found in Lineup.
        rounds = df_lineup['rodada'].unique()
    else:
        rounds = [target_round]
        
    final_rows = []
    
    now = datetime.datetime.now()
    
    # Helper for Game Status
    # We need to link player -> game -> time
    # PLAYER_STATS has game_id. GAMEWEEK has game_id + time.
    # We can map player_id -> game_id (via stats) -> start_time
    
    # Create Player -> Game Info Map (Last known game for the round?)
    # A player might play only one game per round.
    # Merge Stats with Gw
    
    # Needs to handle "id:" prefix logic
    def clean_id(x): return str(x).split("id:")[-1]
    
    df_gw['simple_id'] = df_gw['id_jogo'].apply(clean_id)
    df_stats['simple_id'] = df_stats['game_id'].apply(clean_id)
    
    # Merge Stats + GW
    # We need: Player ID -> {Minutes, StartTime, FinishedBoolean}
    # Caution: df_stats has raw data.
    
    df_merged = df_stats.merge(df_gw[['simple_id', 'data_hora']], on='simple_id', how='left')
    # If merged fails, we might miss time (e.g. game not in gameweek). 
    
    player_game_map = {} # (pid, round) -> {minutes, is_finished}
    
    # Iterate merged to build map
    for _, row in df_merged.iterrows():
        # recover round from GW? We merged on ID, but we need round.
        # df_gw has rodada.
        pass
        
    # Better: Join Stats with GW on simple_id AND retrieve rodada
    df_merged_full = df_stats.merge(df_gw[['simple_id', 'data_hora', 'rodada']], on='simple_id', how='left')
    
    # Build Lookup
    # Key: (player_id, rodada)
    # Val: {minutes, is_finished}
    
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
                # Finished if Start + 2h < Now
                if (dt + datetime.timedelta(hours=2)) < now:
                    is_finished = True
        
        # Store
        player_game_map[(pid, int(rod))] = {'min': mins, 'finished': is_finished}
        
    # Helper to get score
    def get_score(pid, rod):
        # We need to find the game for this player in this round
        # df_pts doesn't have rodada directly usually? 
        # Actually df_pts linked to game_id.
        # We can try to sum points for that player in that round
        # But wait, df_pts is raw points.
        # Let's filter df_pts by game_ids that belong to the round?
        
        # Get GameIDs for the round
        gids_in_round = df_gw[df_gw['rodada'] == rod]['simple_id'].tolist()
        
        # Filter PTS
        # We need simple_id on pts
        df_pts['simple_id'] = df_pts['game_id'].apply(clean_id)
        
        subset = df_pts[ (df_pts['player_id'] == pid) & (df_pts['simple_id'].isin(gids_in_round)) ]
        if subset.empty: return 0.0
        return float(subset['pontuacao'].sum())

    # 3. Process Per Team / Per Round
    for r in rounds:
        r = int(r)
        
        # Get lineups for this round
        round_lineup = df_lineup[df_lineup['rodada'] == r]
        teams = round_lineup['team_id'].unique()
        
        for tid in teams:
            team_players = round_lineup[round_lineup['team_id'] == tid]
            
            # Separate Starters and Subs
            starters = team_players[team_players['lineup'] == 'TITULAR'].copy()
            subs = team_players[team_players['lineup'].str.startswith('PRI', na=False)].copy()
            
            # Sort Subs by Priority
            def get_pri(x):
                try: return int(str(x).split()[-1])
                except: return 99
            subs['pri_num'] = subs['lineup'].apply(get_pri)
            subs = subs.sort_values('pri_num')
            
            # We track who is "Final Active"
            # Initially all starters are active
            active_pids = starters['player_id'].tolist()
            
            # Check Substitutions
            for _, starter in starters.iterrows():
                sid = starter['player_id']
                spos = starter['posicao']
                
                # Check performance
                info = player_game_map.get((sid, r), {'min': 0, 'finished': True}) # Default to 0 min, finished if no data? Or finished=False?
                # If no data (game didn't happen or id mismatch), usually 0 pts.
                # If game hasn't happened yet, is_finished=False.
                # If game happened and he wasn't in stats (DNP), min=0, finished=True (if simple_id matches gw).
                # Warning: if player not in Stats at all, he played 0 mins.
                # But is his game finished? Use team's game status? 
                # Complex. Assume if not in Stats, he DNP. Check if ANY game in round finished?
                # Simplified: Use map. If not in map, assume 0 min.
                # But is_finished? If we don't know the game, we can't substitute him yet?
                # Actually, user said "se o jogo já terminou".
                # If we can't find the game, we assume it hasn't started or we assume nothing.
                # If we assume nothing, we don't sub.
                
                # We need to know if his specific match finished.
                # If not in map, check if his TEAM (real life) played?
                # This requires Player->Team mapping.
                # For now, rely on map. If not in map, we can't confirm game finished, so NO SUB.
                
                if (sid, r) not in player_game_map:
                     # Check if we can find game via other players in same game? No too hard.
                     # Skip sub if unknown.
                     continue
                     
                s_data = player_game_map[(sid, r)]
                
                if s_data['finished'] and s_data['min'] == 0:
                    # CANDIDATE FOR SUB
                    # Find replacement
                    # Same Position, Highest Priority, (Played > 0 min? User implied valid score?)
                    # "entrada... de mesma pontuação" (Assumed Position)
                    
                    replacement = None
                    for _, sub in subs.iterrows():
                        sub_id = sub['player_id']
                        if sub_id in active_pids: continue # Already used? (Sub can only enter once? Usually yes)
                        # Wait, subs list is static. "active_pids" tracks the finals.
                        # We shouldn't reuse a sub.
                        
                        if sub['posicao'] == spos:
                            # Candidate found. Check if already used?
                            # Need to track used subs.
                            replacement = sub_id
                            break
                    
                    if replacement:
                        # PERFORM SUB
                        active_pids.remove(sid)
                        active_pids.append(replacement)
                        # Mark sub as used so he can't sub for another?
                        # Remove from 'subs' df or keep tracked set.
                        subs = subs[subs['player_id'] != replacement] 
                        
            # Final Generation
            for _, p in team_players.iterrows():
                pid = str(p['player_id'])
                score = get_score(pid, r)
                
                in_active = (pid in active_pids)
                
                # Check if player is captain (cap column = 'CAPITAO')
                is_captain = str(p.get('cap', '')).upper() == 'CAPITAO'
                if is_captain and in_active:
                    score = score * 1.5  # Captain bonus
                
                # User wants: ["team_id", "player_id", "rodada", "pontuacao", "entrou_titular"]
                final_rows.append({
                    "team_id": tid,
                    "player_id": pid,
                    "rodada": r,
                    "pontuacao": score,
                    "escalado": in_active # "se ele entrou na escalacao titular" -> The final active lineup
                })

    # 4. Save
    df_out = pd.DataFrame(final_rows)
    
    # Format pontuacao as string with comma for PT-BR locale sheets
    if 'pontuacao' in df_out.columns:
        df_out['pontuacao'] = pd.to_numeric(df_out['pontuacao'], errors='coerce').fillna(0.0)
        # Convert to string with comma as decimal separator for BR locale sheets
        df_out['pontuacao'] = df_out['pontuacao'].apply(lambda x: f"{x:.4f}".replace('.', ','))

    # Write to H2H - TEAM_POINTS
    try:
        try:
            ws_out = sh.worksheet(TEAM_POINTS_SHEET)
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

import pandas as pd
from features.auth import get_client

def debug_specific_players():
    target_names = ["Brenner", "Nuno Moreira"]
    
    client, sh = get_client()
    
    # 1. Load Players
    ws_all = sh.worksheet("ALL_PLAYERS")
    df_players = pd.DataFrame(ws_all.get_all_records())
    df_players.columns = [c.lower() for c in df_players.columns]
    
    print(f"Loaded {len(df_players)} players.")
    
    found_players = []
    
    for name in target_names:
        # Match 'nome'
        match = df_players[df_players['nome'].str.contains(name, case=False, na=False)]
        
        if not match.empty:
            print(f"\n--- Found {name} ---")
            print(match[['player_id', 'nome', 'team', 'posição']].to_string(index=False))
            found_players.extend(match.to_dict('records'))
        else:
            print(f"Could not find {name} in ALL_PLAYERS")
            
    if not found_players: return

    # 2. Check Lineup for Round 2
    ws_lineup = sh.worksheet("TEAM_LINEUP")
    df_lineup = pd.DataFrame(ws_lineup.get_all_records())
    df_lineup.columns = [c.lower() for c in df_lineup.columns]
    
    r2_lineup = df_lineup[df_lineup['rodada'] == 2]
    
    for p in found_players:
        pid = str(p['player_id'])
        p_team_id = None
        
        # Find player in lineup
        p_lineup = r2_lineup[r2_lineup['player_id'].astype(str) == pid]
        
        if not p_lineup.empty:
            print(f"\nLineup Info for {p['nome']} (ID: {pid}):")
            print(p_lineup[['team_id', 'player_id', 'posicao', 'lineup']].to_string(index=False))
            p_team_id = p_lineup.iloc[0]['team_id']
            p_pos = p_lineup.iloc[0]['posicao']
        else:
            print(f"Player {p['nome']} not found in Round 2 Lineup.")
            continue
            
        if p_team_id:
            # Find STARTERS in same position for that Fantasy Team
            starters = r2_lineup[
                (r2_lineup['team_id'] == p_team_id) & 
                (r2_lineup['posicao'] == p_pos) &
                (r2_lineup['lineup'] == 'TITULAR')
            ]
            
            print(f"\nStarters for Fantasy Team {p_team_id} at {p_pos}:")
            if not starters.empty:
                print(starters[['player_id', 'posicao', 'lineup']].to_string(index=False))
                
                # Check IDs of starters to see their Real Club
                for _, s in starters.iterrows():
                    sid = str(s['player_id'])
                    s_info = df_players[df_players['player_id'].astype(str) == sid]
                    if not s_info.empty:
                        s_club = s_info.iloc[0]['team']
                        s_name = s_info.iloc[0]['nome']
                        print(f"  -> Starter {s_name} ({sid}) plays for: {s_club}")
                    else:
                        print(f"  -> Starter {sid} club unknown.")

if __name__ == "__main__":
    debug_specific_players()

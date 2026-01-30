import pandas as pd
import datetime
from features.auth import get_client

# Constants
H2H_TABLE_SHEET = "H2H - TABLE"
TEAM_POINTS_SHEET = "H2H - TEAM_POINTS"
ROUNDS_SHEET = "H2H - ROUNDS"
GAMEWEEK_SHEET = "GAMEWEEK"
SQUAD_SHEET = "SQUAD"

def parse_date(date_str):
    """Robust date parser for DD/MM/YYYY HH:MM"""
    try:
        return pd.to_datetime(date_str, dayfirst=True)
    except:
        return None

def is_round_finished(rodada, df_gw):
    """
    Checks if a round is finished.
    Rule: ALL games in the round must have (Start Time + 2.5 hours) < Now.
    """
    if df_gw.empty or 'rodada' not in df_gw.columns:
        return False
        
    # Filter games for this round
    round_games = df_gw[df_gw['rodada'] == rodada]
    
    if round_games.empty:
        # If no games defined for this round in GW logic, we can't say it's finished?
        # Or implies it doesn't exist. safest is False to avoid calc.
        return False
        
    now = datetime.datetime.now()
    
    for _, row in round_games.iterrows():
        dt_str = str(row.get('data_hora', ''))
        dt = parse_date(dt_str)
        if not dt:
             # invalid date, assume not finished/scheduled? 
             # Safety: return False
             return False
             
        # Check if finished (Start + 2.5h)
        # Using 2.5h to be safe for injury time
        if (dt + datetime.timedelta(hours=2.5)) > now:
            return False # Found a game not finished
            
    return True

def robust_float(x):
    try:
        if isinstance(x, str):
            x = x.replace(',', '.')
        return float(x)
    except:
        return 0.0

def update_league_table():
    print("--- Updating H2H League Table ---")
    client, sh = get_client()
    
    try:
        # 1. Load Data
        ws_rounds = sh.worksheet(ROUNDS_SHEET)
        df_rounds = pd.DataFrame(ws_rounds.get_all_records())
        
        ws_tp = sh.worksheet(TEAM_POINTS_SHEET)
        # Use get_values for precision if needed, but get_all_records is usually ok if formatted
        # actually for robust_float we prefer raw strings if decimal is comma
        vals_tp = ws_tp.get_values()
        if vals_tp and len(vals_tp) > 1:
            df_tp = pd.DataFrame(vals_tp[1:], columns=vals_tp[0])
        else:
            df_tp = pd.DataFrame()
            
        ws_gw = sh.worksheet(GAMEWEEK_SHEET)
        df_gw = pd.DataFrame(ws_gw.get_all_records())
        
        ws_squad = sh.worksheet(SQUAD_SHEET)
        df_squad = pd.DataFrame(ws_squad.get_all_records())
        
    except Exception as e:
        print(f"Error loading sheets for Table: {e}")
        return

    # Normalize Columns
    df_rounds.columns = [c.lower() for c in df_rounds.columns]
    df_tp.columns = [c.lower() for c in df_tp.columns]
    df_gw.columns = [c.lower() for c in df_gw.columns]
    df_squad.columns = [c.lower() for c in df_squad.columns]
    
    # Types
    if 'rodada' in df_rounds.columns: df_rounds['rodada'] = pd.to_numeric(df_rounds['rodada'], errors='coerce')
    if 'rodada' in df_tp.columns: df_tp['rodada'] = pd.to_numeric(df_tp['rodada'], errors='coerce')
    if 'rodada' in df_gw.columns: df_gw['rodada'] = pd.to_numeric(df_gw['rodada'], errors='coerce')
    
    df_tp['pontuacao'] = df_tp['pontuacao'].apply(robust_float)
    df_tp['team_id'] = df_tp['team_id'].astype(str)
    
    # Pre-calc Team Points per Round
    # FILTER: Only 'escalado' == True
    # 'escalado' column might be boolean or string 'TRUE'/'FALSE' or '1'/'0'
    # We should normalize/check
    if 'escalado' in df_tp.columns:
         # Convert to string and upper case for safety
         df_tp['escalado_str'] = df_tp['escalado'].astype(str).str.upper()
         # Filter
         df_active = df_tp[df_tp['escalado_str'].isin(['TRUE', '1'])]
    else:
         # If column missing, assume all? OR none? Safest is warn and empty?
         # But manual update script creates it.
         print("Warning: 'escalado' column missing in TEAM_POINTS. Using all.")
         df_active = df_tp

    # Group by Team, Round -> Sum Points
    round_scores = df_active.groupby(['team_id', 'rodada'])['pontuacao'].sum().to_dict() # Key: (tid, rod)
    
    # Init Table Data
    # Key: TeamID
    stats = {} 
    
    # Identify unique teams from Squad or Rounds
    all_teams = set()
    if 'home_team_id' in df_rounds.columns:
        all_teams.update(df_rounds['home_team_id'].astype(str).unique())
        all_teams.update(df_rounds['away_team_id'].astype(str).unique())
        
    for tid in all_teams:
        stats[tid] = {
            'team_id': tid,
            'P': 0, # Pontos
            'J': 0, # Jogos
            'PF': 0.0, # Pontos Feitos
            'PS': 0.0, # Pontos Sofridos
            'V': 0, 'E': 0, 'D': 0 # Optional details
        }
        
    # ITERATE ROUNDS
    # We iterate unique rounds found in matchups
    rounds_list = sorted(df_rounds['rodada'].unique())
    
    for r in rounds_list:
        if pd.isna(r): continue
        r = int(r)
        
        # CHECK IF FINISHED
        if not is_round_finished(r, df_gw):
            print(f"  -> Round {r} NOT finished. Skipping.")
            continue
            
        print(f"  -> Processing Round {r} (Finished)...")
        
        # Get matchups for this round
        matches = df_rounds[df_rounds['rodada'] == r]
        
        for _, m in matches.iterrows():
            tid_h = str(m['home_team_id'])
            tid_a = str(m['away_team_id'])
            
            # Get Scores
            # If entry missing, 0.0
            score_h = round_scores.get((tid_h, r), 0.0)
            score_a = round_scores.get((tid_a, r), 0.0)
            
            # Update Games
            if tid_h in stats: stats[tid_h]['J'] += 1
            if tid_a in stats: stats[tid_a]['J'] += 1
            
            # Update PF/PS
            if tid_h in stats:
                stats[tid_h]['PF'] += score_h
                stats[tid_h]['PS'] += score_a
            if tid_a in stats:
                stats[tid_a]['PF'] += score_a
                stats[tid_a]['PS'] += score_h
                
            # Result Logic
            if score_h > score_a:
                # Home Win
                if tid_h in stats: 
                    stats[tid_h]['P'] += 3
                    stats[tid_h]['V'] += 1
                if tid_a in stats: 
                    stats[tid_a]['D'] += 1
            elif score_a > score_h:
                # Away Win
                if tid_h in stats: 
                    stats[tid_h]['D'] += 1
                if tid_a in stats: 
                    stats[tid_a]['P'] += 3
                    stats[tid_a]['V'] += 1
            else:
                # Draw
                if tid_h in stats: 
                    stats[tid_h]['P'] += 1
                    stats[tid_h]['E'] += 1
                if tid_a in stats: 
                    stats[tid_a]['P'] += 1
                    stats[tid_a]['E'] += 1
                    
    # BUILD DATAFRAME
    table_rows = []
    for tid, data in stats.items():
        # Calculate Efficiency (Aproveitamento)
        # P / (J * 3)
        aprov = 0.0
        if data['J'] > 0:
            aprov = (data['P'] / (data['J'] * 3)) * 100
            
        data['Aproveitamento'] = aprov
        table_rows.append(data)
        
    df_table = pd.DataFrame(table_rows)
    
    if df_table.empty:
        print("Table empty.")
        return
        
    # JOIN TEAM NAMES
    # df_squad has team_id_norm usually or need to find id column
    if not df_squad.empty:
         # Find ID column in squad
         id_col = next((c for c in df_squad.columns if c in ['team_id', 'id', 'id_time']), None)
         name_col = next((c for c in df_squad.columns if c in ['team_name', 'name', 'nome', 'time']), None)
         
         if id_col and name_col:
             df_squad[id_col] = df_squad[id_col].astype(str)
             # Create map
             name_map = pd.Series(df_squad[name_col].values, index=df_squad[id_col]).to_dict()
             
             df_table['Team'] = df_table['team_id'].map(name_map).fillna(df_table['team_id'])
         else:
             df_table['Team'] = df_table['team_id']
    else:
        df_table['Team'] = df_table['team_id']
        
    # SORTING
    # 1. Aproveitamento DESC
    # 2. PF DESC
    df_table = df_table.sort_values(by=['Aproveitamento', 'PF'], ascending=[False, False])
    
    # FORMAT FOR DISPLAY/SAVING
    # Reorder columns
    cols_order = ['team_id', 'Team', 'P', 'J', 'V', 'E', 'D', 'Aproveitamento', 'PF', 'PS']
    df_final = df_table[cols_order].copy()
    
    # Format decimals
    df_final['Aproveitamento'] = df_final['Aproveitamento'].apply(lambda x: f"{x:.1f}%")
    df_final['PF'] = df_final['PF'].apply(lambda x: f"{x:.2f}".replace('.', ','))
    df_final['PS'] = df_final['PS'].apply(lambda x: f"{x:.2f}".replace('.', ','))
    
    # SAVE
    try:
        try:
            ws_table = sh.worksheet(H2H_TABLE_SHEET)
        except:
            ws_table = sh.add_worksheet(H2H_TABLE_SHEET, 100, 10)
            
        ws_table.clear()
        ws_table.update([df_final.columns.values.tolist()] + df_final.values.tolist(), value_input_option='USER_ENTERED')
        print("✅ H2H Table Updated successfully.")
    except Exception as e:
        print(f"Error saving table: {e}")

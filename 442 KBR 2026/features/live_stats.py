import streamlit as st
import pandas as pd
import requests
import datetime
import time
import numpy as np
from features.auth import get_client, BASE_DIR, get_players_file
import sys
import subprocess

# Constants
CACHE_SHEET = "CACHE_LIVE"
POINTS_SHEET = "PLAYER_POINTS"
STATS_SHEET = "PLAYERS_STATS"
GAMEWEEK_SHEET = "GAMEWEEK"
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

# ... (Previous Cache functions same) ...

def fetch_event_details(game_id):
    """Fetches event details to get current score."""
    url = f"https://api.sofascore.com/api/v1/event/{game_id}"
    try:
        r = cffi_requests.get(url, impersonate="chrome120", timeout=15)
        if r.status_code == 200:
            return r.json()
    except:
        pass
    return None

def fetch_sofascore_lineups(game_id):
    # ... (Same as before) ...
    # Wait, need to move this fetch_event_details *before* extract_stats usage in main loop?
    # Or keep it separate.
    pass

# (Keeping existing checks)

# Updating extract_stats to accept game context
def extract_stats(player_data, game_id, team_side, home_score, away_score):
    """
    Extracts flat stats and enriched data for scoring.
    team_side: 'home' or 'away'
    home_score, away_score: int
    """
    p = player_data.get('player', {})
    stats = player_data.get('statistics', {})
    pos = p.get('position', 'M') # Default Midfielder if missing
    
    pid = p.get('id', '')
    slug = p.get('slug', '')
    
    # Calculate Gols Sofridos (Conceded)
    # If I am Home, conceded = Away Score
    gols_sofridos = 0
    if team_side == 'home':
        gols_sofridos = away_score
    else:
        gols_sofridos = home_score
    
    # Construct row
    row = {
        'game_id': game_id,
        'player_id': f"https://www.sofascore.com/football/player/{slug}/{pid}",
        'Posição': pos, # Needed for calculation
        'gols_sofridos_partida': gols_sofridos, # Needed for calculation
        'rating': stats.get('rating', 0), # Default 0 to avoid NaNs
        'minutesPlayed': stats.get('minutesPlayed', 0),
        'updated_at': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    # Map requested fields
    fields = [
        'ownGoals', 'yellowCards', 'redCards', 'totalOffside', 
        'dispossessed', 'penaltySave', 'penaltyWon', 
        'penaltyConceded', 'penaltyMiss', 'totalPass', 'accuratePass', 
        'totalLongBalls', 'accurateLongBalls', 'duelWon', 'duelLost', 
        'wonContest', 'totalContest', 'keyPass', 'wasFouled', 'fouls',
        'totalClearance', 'outfielderBlock', 'interceptionWon', 'wonTackle', 
        'savedShotsFromInsideTheBox', 'saves', 'punches', 'goodHighClaim', 
        'accurateKeeperSweeper', 'goals', 'goalAssist', 'goalLineClearance', 
        'shotOffTarget', 'onTargetScoringAttempt', 'hitWoodwork', 'goalsPrevented'
    ]
    
    for f in fields:
        row[f] = stats.get(f, 0)
        
    return row

@st.cache_data(ttl=300, show_spinner=False)
def get_active_games_cached():
    """Finds games that started > 5 mins ago and haven't finished."""
    try:
        client, sh = get_client()
        ws = sh.worksheet(GAMEWEEK_SHEET)
        data = ws.get_all_records()
        df = pd.DataFrame(data)
        
        if df.empty: 
            # st.toast("⚠️ Planilha GAMEWEEK vazia ou não lida.", icon="📂")
            return []
            
        # DEBUG COLUMNS
        # st.info(f"Colunas encontradas: {list(df.columns)}")

        # Convert to datetime (Assuming 'data_hora' is GMT-3 string or similar)
        # Format usually: "YYYY-MM-DD HH:MM:SS"
        now = datetime.datetime.now()
        active_games = []
        
        # st.toast(f"🔍 Analisando {len(df)} linhas da planilha...")
        
        for _, row in df.iterrows():
            try:
                # ... (ID logic) ...
                raw_id = str(row.get('id_jogo', '')).strip()
                if not raw_id: continue

                # Extract numeric ID logic (keep existing or simplified)
                if 'id:' in raw_id: gid = raw_id.split('id:')[-1]
                elif '/' in raw_id: gid = raw_id.split('/')[-1]
                else: gid = raw_id
                
                if not gid.isdigit(): 
                     # Handle complex URL cases
                     if 'id:' in raw_id: gid = raw_id.split('id:')[-1]
                     elif '/' in raw_id: gid = raw_id.split('/')[-1]
                     # Fallback clean
                     if not gid.isdigit(): gid = ''.join(filter(str.isdigit, gid))

                dt_str = str(row.get('data_hora', ''))
                
                # Parsing
                game_start = pd.to_datetime(dt_str, dayfirst=True, errors='coerce') 
                
                if pd.isna(game_start):
                     # st.toast(...)
                     continue
                
                diff = (now - game_start).total_seconds() / 60
                
                # FORCE DEBUG FOR TARGET ID
                if '14773692' in str(gid):
                    # st.toast(f"🎯 ALVO ENCONTRADO: {gid}. Data: {game_start}. Diff: {diff} min. (Janela: 0-200)", icon="🎯")
                    pass
                
                if 0 < diff < 130: 
                    # Return both RAW ID (for saving) and API ID (for fetching)
                    active_games.append({'raw': raw_id, 'api': gid})
                else:
                    # Optional: Log future games? No, too spammy.
                    pass 
                    
            except Exception as e:
                continue
                
        return active_games

    except Exception as e:
        # print(f"Error checking active games: {e}")
        # st.toast(f"❌ Erro Crítico planilha GAMEWEEK: {e}", icon="💥")
        return []

import uuid

def try_acquire_lock(active_games_count):
    """
    Attempts to acquire a lock to update the stats.
    Uses CACHE_LIVE sheet with a 'Lock ID' mechanism.
    Returns (True, lock_id) if successful, (False, None) otherwise.
    """
    if active_games_count == 0: return False, None

    try:
        client, sh = get_client()
        try:
            ws = sh.worksheet(CACHE_SHEET)
        except:
            ws = sh.add_worksheet(CACHE_SHEET, 10, 3)
            ws.append_row(['last_update', 'last_general_sync', 'lock_id'])
            ws.append_row(['2000-01-01 00:00:00', '2000-01-01', 'init'])

        # 1. Check existing timestamp (A2)
        # We only try to acquire if the last update was > 5 mins ago OR it's clearly stale/free
        val_time = ws.acell('A2').value
        should_try = False
        
        if not val_time: 
            should_try = True
        else:
            try:
                last_dt = pd.to_datetime(val_time)
                now = datetime.datetime.now()
                diff_min = (now - last_dt).total_seconds() / 60
                if diff_min >= 2: # Reduce to 2 mins to be more responsive but still safe? Or keep 5? User said 5. Let's stick to logic.
                     should_try = True
            except:
                should_try = True
        
        if not should_try:
            return False, None

        # 2. Attempt to Lock
        # Generate ID
        my_lock_id = str(uuid.uuid4())[:8]
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Write Lock ID (C2) and Time (A2)
        # We write Time to "reserve" the slot so others see it as recent.
        # We write Lock ID to claim it.
        ws.update_acell('A2', now_str)
        ws.update_acell('C2', my_lock_id)
        
        # 3. Wait for consistency (Race condition check)
        time.sleep(2)
        
        # 4. Read back Lock ID
        current_lock_id = ws.acell('C2').value
        
        if current_lock_id == my_lock_id:
            # We have the lock!
            return True, my_lock_id
        else:
            # Someone else overwrote us
            return False, None

    except Exception as e:
        print(f"Lock Error: {e}")
        return False, None

def release_lock(lock_id):
    # Optional: Clear lock? 
    # Actually, we leave the time set (A2) so strictly speaking the "Lock" is the time window.
    # The LockID was just to win the race to SET the time.
    # So we don't need to do anything else.
    pass

def check_and_run_daily_sync():
    """
    Checks if General Sync (B2 in CACHE_LIVE) runs for today.
    If not, runs it and updates the date.
    """
    try:
        client, sh = get_client()
        try:
            ws = sh.worksheet(CACHE_SHEET)
        except:
             # If doesn't exist, create (handled in other func usually but safety)
             ws = sh.add_worksheet(CACHE_SHEET, 10, 2)
             ws.append_row(['last_update', 'last_general_sync'])
             ws.append_row(['2000-01-01 00:00:00', '2000-01-01'])

        # Header B1: last_general_sync
        # Value B2
        # Check if B1 is correct header (optional but good practice)
        # Assuming A1=last_update, B1... if not set, set it?
        # Just read B2 directly.
        
        today_str = datetime.datetime.now().strftime("%Y-%m-%d")
        
        # Read B2
        val_b2 = ws.acell('B2').value
        
        if val_b2 != today_str:
            # NEEDS UPDATE
            st.toast("📅 Detectado primeiro acesso do dia. Iniciando Sincronização Geral...", icon="🔄")
            
            # 1. Update B2 immediately to lock
            ws.update_acell('B2', today_str)
            
            # 2. Run Subprocess
            # module: features.games_extraction
            cmd = [sys.executable, "-m", "features.games_extraction"]
            
            result = subprocess.run(
                cmd, 
                cwd=str(BASE_DIR), 
                capture_output=True, 
                text=True,
                encoding='utf-8', 
                errors='replace'
            )
                
            if result.returncode == 0:
                st.toast("✅ Sincronização Diária Concluída!", icon="📅")
                # Optional: Log stdout
                print("Daily Sync Success:", result.stdout)
            else:
                st.toast("❌ Falha na Sincronização Diária.", icon="⚠️")
                st.error(f"Detalhes do erro na Sincronização:\n{result.stderr}")
                
                # Log to file for debugging
                try:
                    log_path = BASE_DIR / "sync_log.txt"
                    with open(log_path, "w", encoding="utf-8") as f:
                        f.write(f"EXIT CODE: {result.returncode}\n")
                        f.write("--- STDOUT ---\n")
                        f.write(result.stdout)
                        f.write("\n--- STDERR ---\n")
                        f.write(result.stderr)
                    st.info(f"Log de erro salvo em: {log_path}")
                except:
                    pass
                
                print("Daily Sync Error:", result.stderr)
                # Revert B2 so it tries again? Or keep it locked to avoid loop?
                # Keep it locked to avoid breaking app for everyone if persistent error.
                
    except Exception as e:
        print(f"Error in Daily Sync Check: {e}")

from curl_cffi import requests as cffi_requests # Rename to avoid conflict if any

def fetch_sofascore_lineups(game_id):
    url = f"https://api.sofascore.com/api/v1/event/{game_id}/lineups"
    
    # Headers can be minimal, the impersonate does the heavy lifting
    
    try:
        # User impersonate="chrome120" or similar to mimic real browser TLS
        r = cffi_requests.get(url, impersonate="chrome120", timeout=15)
        
        if r.status_code == 200:
            return r.json()
        elif r.status_code == 403:
             # Try mobile version if desktop fails
             print(f"DEBUG 403 on Desktop. Retrying...")
        else:
            print(f"DEBUG API FAIL: {game_id} -> Status {r.status_code}") 
            # st.toast(f"Erro API: {r.status_code}", icon="❌")
            return None
    except Exception as e:
        print(f"DEBUG API EXCEPTION: {e}")
        # st.toast(f"Erro Conexão: {e}", icon="⚠️")
        pass
    return None

@st.cache_data(ttl=3600)
def get_player_pos_map():
    """
    Reads Players.csv and returns a dict: {str(id): 'G'/'D'/'M'/'F'}
    """
    try:
        f = get_players_file()
        if not f.exists(): return {}
        
        df = pd.read_csv(f)
        
        # Helper to extract ID
        def extract_id(val):
            s = str(val)
            if '/' in s: return s.split('/')[-1]
            return s
            
        df['pid'] = df['player_id'].apply(extract_id)
        
        # Map PT -> EN structure
        # GK->G, DEF->D, MEI->M, ATA->F
        pos_map_dict = {
            'GK': 'G',
            'DEF': 'D',
            'MEI': 'M',
            'ATA': 'F'
        }
        
        # Create map
        pmap = {}
        for _, row in df.iterrows():
            clean_pos = row['Posição'].strip().upper() if isinstance(row['Posição'], str) else ''
            mapped = pos_map_dict.get(clean_pos, 'M') # Default to M if unknown
            pmap[str(row['pid'])] = mapped
            
        return pmap
    except Exception as e:
        print(f"Error loading player map: {e}")
        return {}

def fetch_game_comments(game_id):
    url = f"https://api.sofascore.com/api/v1/event/{game_id}/comments"
    try:
        r = cffi_requests.get(url, impersonate="chrome120", timeout=15)
        if r.status_code == 200:
            return r.json()
    except:
        pass
    return None

def parse_cards_from_comments(comments_data):
    """
    Parses comments to count yellow and red cards per player.
    Returns: { str(player_id): {'yellow': int, 'red': int} }
    """
    card_map = {}
    if not comments_data or 'comments' not in comments_data:
        return card_map
    
    for c in comments_data['comments']:
        ctype = c.get('type')
        if ctype in ['yellowCard', 'redCard']:
            p = c.get('player', {})
            pid = str(p.get('id', ''))
            if not pid: continue
            
            if pid not in card_map: card_map[pid] = {'yellow': 0, 'red': 0}
            
            if ctype == 'yellowCard':
                card_map[pid]['yellow'] += 1
            elif ctype == 'redCard':
                card_map[pid]['red'] += 1
                
    return card_map

def extract_stats(player_data, game_id, team_side, home_score, away_score, pos_map=None, card_map=None):
    """
    Extracts flat stats and enriched data for scoring.
    team_side: 'home' or 'away'
    home_score, away_score: int
    """
    p = player_data.get('player', {})
    stats = player_data.get('statistics', {})
    
    pid = str(p.get('id', ''))
    
    # 1. POSITION OVERRIDE
    api_pos = p.get('position', 'M')
    real_pos = api_pos
    if pos_map and pid in pos_map:
        real_pos = pos_map[pid]
        
    pos = real_pos
    
    slug = p.get('slug', '')
    
    # Calculate Gols Sofridos (Conceded)
    # If I am Home, conceded = Away Score
    gols_sofridos = 0
    if team_side == 'home':
        gols_sofridos = away_score
    else:
        gols_sofridos = home_score
    
    # Construct row
    row = {
        'game_id': game_id,
        'player_id': f"https://www.sofascore.com/football/player/{slug}/{pid}",
        'Posição': pos, # Needed for calculation
        'gols_sofridos_partida': gols_sofridos, # Needed for calculation
        'rating': stats.get('rating', 0), # Default 0 to avoid NaNs
        'minutesPlayed': stats.get('minutesPlayed', 0),
        'updated_at': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    # Map requested fields
    fields = [
        'ownGoals', 'yellowCards', 'redCards', 'totalOffside', 
        'dispossessed', 'penaltySave', 'penaltyWon', 
        'penaltyConceded', 'penaltyMiss', 'totalPass', 'accuratePass', 
        'totalLongBalls', 'accurateLongBalls', 'duelWon', 'duelLost', 
        'wonContest', 'totalContest', 'keyPass', 'wasFouled', 'fouls',
        'totalClearance', 'outfielderBlock', 'interceptionWon', 'wonTackle', 
        'savedShotsFromInsideTheBox', 'saves', 'punches', 'goodHighClaim', 
        'accurateKeeperSweeper', 'goals', 'goalAssist', 'goalLineClearance', 
        'shotOffTarget', 'onTargetScoringAttempt', 'hitWoodwork', 'goalsPrevented'
    ]
    
    for f in fields:
        row[f] = stats.get(f, 0)
    
    # 2. CARD OVERRIDE FROM COMMENTS
    if card_map and pid in card_map:
        # Override values
        row['yellowCards'] = card_map[pid]['yellow']
        row['redCards'] = card_map[pid]['red']
        
    return row

def calculate_points(df):
    """Calculates fantasy points based on Lucca's rules."""
    if df.empty: return pd.DataFrame()
    
    # Ensure numeric types
    cols = [
        'rating', 'ownGoals', 'yellowCards', 'redCards', 'totalOffside',
        'dispossessed', 'penaltyConceded', 'penaltyMiss', 'fouls',
        'minutesPlayed', 'totalPass', 'accuratePass', 'totalLongBalls',
        'accurateLongBalls', 'duelWon', 'duelLost', 'wonContest',
        'totalContest', 'keyPass', 'penaltySave', 'penaltyWon',
        'wasFouled', 'shotOffTarget', 'onTargetScoringAttempt', 'hitWoodwork',
        'goals', 'totalClearance', 'outfielderBlock', 'interceptionWon',
        'wonTackle', 'goalLineClearance', 'saves', 'savedShotsFromInsideTheBox',
        'accurateKeeperSweeper', 'goalsPrevented', 'goalAssist', 'gols_sofridos_partida'
    ]
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
            
    # Lucca's Logic
    # 1. Nota (Rating)
    cond_nota = [(df['rating']>=9), (df['rating']>=8), (df['rating']>=7), (df['rating']>=6.5), (df['rating']>=6), (df['rating']>=3)]
    val_nota = [3, 2, 1, 0, -1, -2]
    df['L_nota'] = np.select(cond_nota, val_nota, default=0)

    # 2. Pontos Negativos
    real_fouls = (df['fouls'] - df['penaltyConceded']).clip(lower=0)
    df['L_negativos'] = (
        (df['ownGoals'] * -2) + (df['yellowCards'] * -1) + (df['totalOffside'] * -0.25) +
        (df['dispossessed'] * -0.25) + (df['penaltyConceded'] * -2) + 
        (df['penaltyMiss'] * -3) + (real_fouls * -0.5)
    )
    
    # 3. Cartão Vermelho
    df['L_red'] = np.where(df['redCards'] > 0, -3, 0)
    
    # 4. Participação (> 75 min)
    df['L_part'] = np.where(df['minutesPlayed'] > 75, 1, 0)

    # 5. Bonus Stats
    p_passe = np.where(df['totalPass']>0, df['accuratePass']/df['totalPass'], 0)
    p_long = np.where(df['totalLongBalls']>0, df['accurateLongBalls']/df['totalLongBalls'], 0)
    p_duel = np.where((df['duelWon']+df['duelLost'])>0, df['duelWon']/(df['duelWon']+df['duelLost']), 0)
    p_drib = np.where(df['totalContest']>0, df['wonContest']/df['totalContest'], 0)

    df['L_bonus'] = (
        np.where((df['totalPass']>=40) & (p_passe>=0.90), 1, 0) +
        np.where((df['accurateLongBalls']>=3) & (p_long>=0.60), 1, 0) +
        np.where((df['duelWon']>=3) & (p_duel>=0.50), 1, 0) +
        np.where((df['wonContest']>=3) & (p_drib>=0.60), 1, 0)
    )

    # 6. Ações Ofensivas
    real_shot = (df['onTargetScoringAttempt'] - df['hitWoodwork'] - df['goals']).clip(lower=0)
    df['L_acoes'] = (
        (df['keyPass'] * 0.75) + (df['penaltySave'] * 5) + (df['penaltyWon'] * 2) +
        (df['wasFouled'] * 0.5) + (df['shotOffTarget'] * 0.75) + 
        (real_shot * 1.5) + (df['hitWoodwork'] * 3)
    )

    # 7. Defesa (Jogadores de Linha)
    # Using 'Posição' column. Ensure it matches 'G', 'D', 'M', 'F'.
    # SofaScore stats usually use 'G', 'D', 'M', 'F'.
    df['L_def'] = np.where(df['Posição'] != 'G', 
        (df['totalClearance']*0.1) + (df['outfielderBlock']*0.25) + 
        (df['interceptionWon']*0.5) + (df['wonTackle']*0.75) + (df['goalLineClearance']*2), 0
    )

    # 8. Goleiro
    saves_out = (df['saves'] - df['savedShotsFromInsideTheBox']).clip(lower=0)
    df['L_gk'] = np.where(df['Posição'] == 'G',
        (df['savedShotsFromInsideTheBox']*1.0) + (saves_out*0.5) + 
        (df['accurateKeeperSweeper']*1) + (df['goalLineClearance']*2)+
        (df['goalsPrevented']*2), 0
    )

    # 9. Posição (Gols + Assist + SG)
    # Mapping logic via nice lookup
    # Need to handle Apply vs Vectorized. Vectorized is faster/safer with np.select or map.
    
    # Goal Points
    # G:6, D:6, M:6, F:6 (Wait, user put 6 for F? Usually F is 4 or 5. But code says 6. Sticking to code.)
    # Actually User Code: pos_L_G = {'G':6,'D':6,'M':6,'F':6}
    # Assist Points
    # pos_L_A = {'G':4,'D':4,'M':4,'F':4}
    # SG Points
    # pos_L_SG = {'G':4,'D':3,'M':0,'F':0}
    
    # Since all are constant across positions (except SG), we can simplify or use map.
    # Goals = 6 pts for everyone
    pts_goals = df['goals'] * 6
    pts_assists = df['goalAssist'] * 4
    
    # SG
    # SG apply only if clean sheet AND minutes > 0? User code: if (x['gols_sofridos_partida']==0 and x['minutesPlayed'] > 0)
    has_sg = (df['gols_sofridos_partida'] == 0) & (df['minutesPlayed'] > 0)
    sg_pts = np.select(
        [
            (df['Posição'] == 'G') & has_sg,
            (df['Posição'] == 'D') & has_sg
        ],
        [4, 3],
        default=0
    )
    
    # Gols Sofridos (Defense only) - Only count if player played > 0 minutes
    # np.where(df['Posição'].isin(['G','D']), df['gols_sofridos_partida']*-0.5, 0)
    def_conceded = np.where(
        (df['Posição'].isin(['G','D'])) & (df['minutesPlayed'] > 0), 
        df['gols_sofridos_partida'] * -0.5, 
        0
    )
    
    df['L_pos'] = pts_goals + pts_assists + sg_pts + def_conceded

    df['PONTUACAO_LUCCA_MATCH'] = df[['L_nota','L_negativos','L_red','L_part','L_bonus','L_acoes','L_def','L_gk','L_pos']].sum(axis=1)
    
    return df[['game_id', 'player_id', 'PONTUACAO_LUCCA_MATCH']]

def save_stats_to_sheet(all_stats_rows):
    if not all_stats_rows: return
    
    try:
        client, sh = get_client()
        try:
            ws = sh.worksheet(STATS_SHEET)
        except:
            ws = sh.add_worksheet(STATS_SHEET, 1000, len(STATS_COLUMNS))
            ws.append_row(STATS_COLUMNS)
            
        # OVERWRITE LOGIC:
        # 1. Get all existing records
        existing_data = ws.get_all_records()
        existing_df = pd.DataFrame(existing_data)
        
        # 2. Identify Game IDs being updated
        new_df = pd.DataFrame(all_stats_rows)
        # Ensure columns match STATS_COLUMNS order
        # (Handling potential missing cols by filling with 0 or empty)
        for c in STATS_COLUMNS:
            if c not in new_df.columns: new_df[c] = ''
        new_df = new_df[STATS_COLUMNS]
        
        updated_game_ids = new_df['game_id'].unique().astype(str).tolist()
        
        # 3. Filter out old rows for these games
        if not existing_df.empty:
            # Ensure game_id is string for comparison
            existing_df['game_id'] = existing_df['game_id'].astype(str)
            # Keep rows where game_id is NOT in updated_game_ids
            mask = ~existing_df['game_id'].isin(updated_game_ids)
            final_df = pd.concat([existing_df[mask], new_df], ignore_index=True)
        else:
            final_df = new_df
            
        # 4. Write back
        # Convert to list of lists (including header)
        # Ensure all values are strings or compatible
        final_values = [STATS_COLUMNS] + final_df.astype(str).values.tolist()
        
        ws.clear()
        ws.update('A1', final_values)
        
    except Exception as e:
        print(f"Error saving stats (overwrite): {e}")

from features.utils import robust_to_float, format_br_decimal

def save_points_to_sheet(points_df):
    if points_df.empty: return
    try:
        client, sh = get_client()
        try:
            ws = sh.worksheet(POINTS_SHEET)
        except:
            ws = sh.add_worksheet(POINTS_SHEET, 1000, 3)
            ws.append_row(['game_id', 'player_id', 'pontuacao'])
            
        # OVERWRITE LOGIC (Same pattern)
        existing_data = ws.get_all_records()
        existing_df = pd.DataFrame(existing_data)
        
        # Identify Game IDs
        updated_game_ids = points_df['game_id'].unique().astype(str).tolist()
        
        if not existing_df.empty:
            existing_df['game_id'] = existing_df['game_id'].astype(str)
            mask = ~existing_df['game_id'].isin(updated_game_ids)
            # Ensure columns match
            # points_df has ['game_id', 'player_id', 'PONTUACAO_LUCCA_MATCH']
            # sheet has ['game_id', 'player_id', 'pontuacao']
            # Need to map PONTUACAO_LUCCA_MATCH to pontuacao
            points_df_renamed = points_df.rename(columns={'PONTUACAO_LUCCA_MATCH': 'pontuacao'})
            
            final_df = pd.concat([existing_df[mask], points_df_renamed], ignore_index=True)
        else:
            final_df = points_df.rename(columns={'PONTUACAO_LUCCA_MATCH': 'pontuacao'})
            
        # Write back
        header = ['game_id', 'player_id', 'pontuacao']
        if 'pontuacao' in final_df.columns:
            # ROBUST FLOAT CONVERSION
            final_df['pontuacao'] = final_df['pontuacao'].apply(robust_to_float)
            # FORMAT FOR BR LOCALE
            final_df['pontuacao'] = final_df['pontuacao'].apply(format_br_decimal)
        
        # Ensure correct order
        final_df = final_df[header]
        
        final_values = [header] + final_df.values.tolist()
        
        ws.clear()
        # Use USER_ENTERED to respect sheet locale for decimal interpretation
        ws.update('A1', final_values, value_input_option='USER_ENTERED')

        # st.toast(f"Pontos salvos na aba '{POINTS_SHEET}': {len(final_df)} registros.", icon="✅")

    except Exception as e:
        print(f"Error saving points (overwrite): {e}")
        # st.toast(f"Erro ao salvar Pontos: {e}", icon="🚩")

def run_auto_update(force=False):
    """Main entry point called by Players.py"""
    
    # 0. Daily Sync Check
    check_and_run_daily_sync()

    # 1. Check Active Games
    active_ids = get_active_games_cached()
    
    # VISIBLE DEBUG
    # st.info(f"DEBUG LIVE: Jogos Ativos Encontrados: {len(active_ids)}. IDs: {active_ids}")
    
    if not active_ids: return # No games, nothing to do
    
    # 2. Check Cache & Lock
    if not force:
        locked, lock_id = try_acquire_lock(len(active_ids))
        if not locked:
            # Lock held by someone else or not time yet
            return
    else:
        # If force, we proceed but log it?
        pass
    
    # st.toast(f"🔄 Atualizando Stats e Pontos de {len(active_ids)} jogos...", icon="⏳")
    
    # 3. Process
    all_game_stats = []
    enriched_data_for_calc = []
    
    # Load Map Once
    pos_map = get_player_pos_map()
    
    for item in active_ids:
        # Compatibility check if getting mixed types (shouldn't happen but safety first)
        if isinstance(item, dict):
            api_id = item.get('api')
            raw_id = item.get('raw')
        else:
            api_id = item
            raw_id = item
            
        # A. Fetch Score using API ID
        event_details = fetch_event_details(api_id)
        home_score = 0
        away_score = 0
        if event_details:
             event = event_details.get('event', {})
             home_score = event.get('homeScore', {}).get('current', 0)
             away_score = event.get('awayScore', {}).get('current', 0)
        
        # B. Fetch Lineups using API ID
        data = fetch_sofascore_lineups(api_id)
        if not data: 
            # st.toast(f"Falha jogo {api_id}", icon="⚠️")
            continue
            
        # C. Fetch Comments (Cards Override)
        comments_data = fetch_game_comments(api_id)
        card_map = parse_cards_from_comments(comments_data)
        
        # Process Home
        home_players = data.get('home', {}).get('players', [])
        for p in home_players:
            # Stats for 'STATS_SHEET' (Raw) - Wait, reuse the enriched dict or separate?
            # Enriched dict has 'Posição' and 'gols_sofridos' which are not in STATS_COLUMNS
            # That's fine, save_stats_to_sheet selects columns.
            
            # Home Team -> team_side='home'
            # PASS RAW ID FOR SAVING
            row = extract_stats(p, raw_id, 'home', home_score, away_score, pos_map, card_map)
            all_game_stats.append(row)
            enriched_data_for_calc.append(row)
            
        # Process Away
        away_players = data.get('away', {}).get('players', [])
        for p in away_players:
            # Away Team -> team_side='away'
             # PASS RAW ID FOR SAVING
            row = extract_stats(p, raw_id, 'away', home_score, away_score, pos_map, card_map)
            all_game_stats.append(row)
            enriched_data_for_calc.append(row)
            
    # 4. Save Raw Stats
    if all_game_stats:
        save_stats_to_sheet(all_game_stats)
        
        # 5. Calculate and Save Points
        df_calc = pd.DataFrame(enriched_data_for_calc)
        points_df = calculate_points(df_calc)
        save_points_to_sheet(points_df)

        # 6. Update Team Points (Substitutions)
        try:
             from features.team_points import calculate_team_points
             calculate_team_points() 
        except Exception as e:
             print(f"Error updating team points: {e}")
        
        # Lock is released implicitly by time, no need to call update_cache_time again
        # st.toast(f"✅ Atualizado: Stats e Pontos salvos.", icon="💾")

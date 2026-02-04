import streamlit as st
import pandas as pd
from features.auth import get_client
from features.utils import clean_pos

@st.cache_data(ttl=300)
def load_all_players_data():
    """
    Loads ALL_PLAYERS from Google Sheets with 5 minute cache.
    Returns dataframe with processed columns.
    """
    try:
        client, sh = get_client()
        ws_all = sh.worksheet("ALL_PLAYERS")
        data_all = ws_all.get_all_records()
        df_players = pd.DataFrame(data_all)
        
        if not df_players.empty:
            df_players['player_id'] = df_players['player_id'].astype(str)
            
            # Ensure Posição exists
            if 'Posição' not in df_players.columns:
                df_players['Posição'] = 'Unknown'

            # Apply clean_pos
            df_players['Posição Simplificada'] = df_players['Posição'].apply(clean_pos)
                
            return df_players
            
        # Return empty with schema
        return pd.DataFrame(columns=['player_id', 'Posição', 'Nome', 'Team', 'Status', 'Lesão', 'Valor de Mercado', 'Posição Simplificada'])

    except Exception as e:
        # Fallback or error reporting?
        # User requested everything on sheets, so error is appropriate if fails.
        print(f"Error loading ALL_PLAYERS: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=300)
def load_free_players_ids():
    """
    Loads PLAYERS_FREE from Google Sheets with 5 minute cache.
    Returns set of free player IDs.
    """
    try:
        client, sh = get_client()
        ws_free = sh.worksheet("PLAYERS_FREE")
        data_free = ws_free.get_all_records()
        df_free = pd.DataFrame(data_free)
        
        if not df_free.empty:
            df_free.columns = df_free.columns.str.lower()
            return set(df_free['player_id'].astype(str).unique())
            
        return set()

    except Exception as e:
        print(f"Error loading PLAYERS_FREE: {e}")
        return set()

@st.cache_data(ttl=300)
def load_team_data():
    """Returns TEAM sheet data (Ownership map)"""
    try:
        client, sh = get_client()
        ws = sh.worksheet("TEAM")
        df = pd.DataFrame(ws.get_all_records())
        if not df.empty:
            df.columns = df.columns.str.lower()
            df['player_id'] = df['player_id'].astype(str)
            df['team_id'] = df['team_id'].astype(str)
        return df
    except Exception as e:
        print(f"Error loading TEAM: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=300)
def load_squad_data():
    """Returns SQUAD sheet data (Teams metadata)"""
    try:
        client, sh = get_client()
        ws = sh.worksheet("SQUAD")
        df = pd.DataFrame(ws.get_all_records())
        if not df.empty:
            df.columns = df.columns.str.lower()
            # Normalize ID column
            id_col = next((c for c in df.columns if c in ['team_id', 'id']), 'team_id')
            df['team_id_norm'] = df[id_col].astype(str)
        return df
    except Exception as e:
        print(f"Error loading SQUAD: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=300)
def load_gameweek_data():
    """Returns GAMEWEEK sheet data"""
    try:
        client, sh = get_client()
        ws = sh.worksheet("GAMEWEEK")
        df = pd.DataFrame(ws.get_all_records())
        if not df.empty:
            df.columns = df.columns.str.lower()
        return df
    except Exception as e:
        print(f"Error loading GAMEWEEK: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=300)
def load_player_stats_data():
    """Returns PLAYERS_STATS sheet data"""
    try:
        client, sh = get_client()
        ws = sh.worksheet("PLAYERS_STATS")
        df = pd.DataFrame(ws.get_all_records())
        if not df.empty:
            df.columns = df.columns.str.lower()
            df['player_id'] = df['player_id'].astype(str)
            df['game_id'] = df['game_id'].astype(str)
            # Ensure numeric cols
            for col in df.columns:
                if col not in ['player_id', 'game_id', 'fixture_id']:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        return df
    except Exception as e:
        print(f"Error loading PLAYERS_STATS: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=300)
def load_player_points_data():
    """Returns PLAYER_POINTS sheet data"""
    try:
        client, sh = get_client()
        ws = sh.worksheet("PLAYER_POINTS")
        vals = ws.get_values()
        if vals and len(vals) > 1:
            df = pd.DataFrame(vals[1:], columns=vals[0])
            df.columns = df.columns.str.lower()
            df['player_id'] = df['player_id'].astype(str)
            df['game_id'] = df['game_id'].astype(str)
            
            def safe_float(x):
                try: return float(str(x).replace(',', '.'))
                except: return 0.0
                
            if 'pontuacao' in df.columns:
                df['pontuacao'] = df['pontuacao'].apply(safe_float)
            return df
        return pd.DataFrame()

    except Exception as e:
        print(f"Error loading PLAYER_POINTS: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=300)
def load_h2h_rounds_data():
    """Returns H2H - ROUNDS data"""
    try:
        client, sh = get_client()
        ws = sh.worksheet("H2H - ROUNDS")
        df = pd.DataFrame(ws.get_all_records())
        if not df.empty:
            df.columns = df.columns.str.lower()
            if 'rodada' in df.columns:
                df['rodada'] = pd.to_numeric(df['rodada'], errors='coerce')
        return df
    except Exception as e:
        print(f"Error loading H2H - ROUNDS: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=300)
def load_team_lineup_data():
    """Returns TEAM_LINEUP data"""
    try:
        client, sh = get_client()
        ws = sh.worksheet("TEAM_LINEUP")
        df = pd.DataFrame(ws.get_all_records())
        if not df.empty:
            df.columns = df.columns.str.lower()
            df['player_id'] = df['player_id'].astype(str)
            df['team_id'] = df['team_id'].astype(str)
            if 'rodada' in df.columns:
                df['rodada'] = pd.to_numeric(df['rodada'], errors='coerce')
        return df
    except Exception as e:
        print(f"Error loading TEAM_LINEUP: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=300)
def load_h2h_table_data():
    """Returns H2H - TABLE data"""
    try:
        client, sh = get_client()
        ws = sh.worksheet("H2H - TABLE")
        raw_data = ws.get_all_values()
        
        if raw_data and len(raw_data) > 1:
            df = pd.DataFrame(raw_data[1:], columns=raw_data[0])
            df.columns = df.columns.str.lower()
            
            # Clean Numerics
            for col in ['pf', 'ps']:
                if col in df.columns:
                    df[col] = df[col].astype(str).str.replace(',', '.')
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
            
            for col in ['p', 'j', 'v', 'e', 'd']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
            return df
        return pd.DataFrame()
    except Exception as e:
        print(f"Error loading H2H - TABLE: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=300)
def load_h2h_team_points_data():
    """Returns H2H - TEAM_POINTS data"""
    try:
        client, sh = get_client()
        ws = sh.worksheet("H2H - TEAM_POINTS")
        vals = ws.get_values()
        if vals and len(vals) > 1:
            df = pd.DataFrame(vals[1:], columns=vals[0])
            df.columns = df.columns.str.lower()
            df['player_id'] = df['player_id'].astype(str)
            df['team_id'] = df['team_id'].astype(str)
            
            def safe_float(x):
                try: return float(str(x).replace(',', '.'))
                except: return 0.0
                
            if 'pontuacao' in df.columns:
                df['pontuacao'] = df['pontuacao'].apply(safe_float)
                
            if 'rodada' in df.columns:
                df['rodada'] = pd.to_numeric(df['rodada'], errors='coerce')
                
            return df
        return pd.DataFrame()
    except Exception as e:
        print(f"Error loading H2H - TEAM_POINTS: {e}")
        return pd.DataFrame()

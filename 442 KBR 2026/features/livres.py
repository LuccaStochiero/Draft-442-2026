import streamlit as st
import pandas as pd
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- CONFIG ---
SERVICE_ACCOUNT_FILE = "service_account.json"
SHEET_ID = "1mG0XiZwzTyDncD592_XcpFwKeUwR97Gi8-tEh_XPW50"
PLAYERS_LOCAL_FILE = os.path.join("Dados", "Players.csv")

POS_MAPPING = {
    'Goalkeeper': 'GK',
    'Defender': 'DEF',
    'Midfielder': 'MEI',
    'Forward': 'ATA'
}

def clean_pos(p):
    return POS_MAPPING.get(p, p)

@st.cache_data(ttl=60)
def load_data():
    # 1. Load Local Players Data (Detailed info)
    if os.path.exists(PLAYERS_LOCAL_FILE):
        df_players = pd.read_csv(PLAYERS_LOCAL_FILE)
        df_players['player_id'] = df_players['player_id'].astype(str)
        # Pre-calc
        df_players['Posição Simplificada'] = df_players['Posição'].apply(clean_pos)
        
        from datetime import datetime
        def calculate_age(dob_str):
            if pd.isna(dob_str) or not isinstance(dob_str, str): return 0
            try:
                dob = datetime.strptime(dob_str, "%d/%m/%Y")
                today = datetime.today()
                return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            except: return 0
            
        if 'Nascimento' in df_players.columns:
            df_players['Idade'] = df_players['Nascimento'].apply(calculate_age)
        else:
            df_players['Idade'] = 0
    else:
        st.error("Arquivo `Dados/Players.csv` não encontrado.")
        return pd.DataFrame(), pd.DataFrame()

    # 2. Load PLAYERS_FREE from Sheets (Availability)
    if not os.path.exists(SERVICE_ACCOUNT_FILE):
        st.error("Credenciais não encontradas.")
        return df_players, pd.DataFrame()

    try:
        scope = ["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/spreadsheets',
                 "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name(SERVICE_ACCOUNT_FILE, scope)
        client = gspread.authorize(creds)
        sh = client.open_by_key(SHEET_ID)
        
        ws_free = sh.worksheet("PLAYERS_FREE")
        data_free = ws_free.get_all_records()
        df_free_ids = pd.DataFrame(data_free)
        if not df_free_ids.empty:
            df_free_ids.columns = df_free_ids.columns.str.lower()
            df_free_ids['player_id'] = df_free_ids['player_id'].astype(str)
    except Exception as e:
        st.error(f"Erro ao ler Google Sheet: {e}")
        return df_players, pd.DataFrame()
        
    return df_players, df_free_ids

def app():
    st.title("🆓 Jogadores Livres")
    
    df_players, df_free_ids = load_data()
    
    if df_players.empty or df_free_ids.empty:
        st.warning("Dados indisponíveis ou nenhum jogador livre no momento.")
        return

    # Filter: Only keep players who are in the free list
    free_ids = set(df_free_ids['player_id'].unique())
    df_free_detailed = df_players[df_players['player_id'].isin(free_ids)].copy()
    
    st.markdown(f"**Disponíveis:** {len(df_free_detailed)}")
    
    # --- Status Info Construction ---
    def make_status(row):
        s = str(row.get('Status', ''))
        l = str(row.get('Lesão', ''))
        
        if s.lower() == 'nan': s = ''
        if l.lower() == 'nan': l = ''

        if s.lower() == 'active' and not l:
            return "✅"
        
        # Replace dayToDay with warning emoji
        if 'daytoday' in s.lower().replace(" ",""):
             s = "⚠️"
             
        if l:
            return f"{s} ({l})"
        return s

    df_free_detailed['Status Info'] = df_free_detailed.apply(make_status, axis=1)

    # --- Filters ---
    c1, c2, c3 = st.columns(3)
    with c1:
        search_name = st.text_input("Buscar por Nome")
    with c2:
        # Fix sort error: ensure strings and dropna or fillna
        unique_pos = df_free_detailed['Posição Simplificada'].dropna().astype(str).unique()
        all_pos = sorted(unique_pos)
        sel_pos = st.multiselect("Posição", all_pos)
    with c3:
        all_clubs = sorted(df_free_detailed['Team'].fillna('-').astype(str).unique())
        sel_clubs = st.multiselect("Clube Real", all_clubs)
        
    filtered = df_free_detailed.copy()
    if search_name:
        filtered = filtered[filtered['Nome'].str.contains(search_name, case=False, na=False)]
    if sel_pos:
        filtered = filtered[filtered['Posição Simplificada'].isin(sel_pos)]
    if sel_clubs:
        filtered = filtered[filtered['Team'].astype(str).isin(sel_clubs)]
        
    # --- Compact Display ---
    # Just essential cols
    display_df = filtered[['Nome', 'Posição Simplificada', 'Team', 'Idade', 'Altura', 'Status Info', 'Valor de Mercado']].copy()
    
    st.dataframe(
        display_df.sort_values(by='Valor de Mercado', ascending=False),
        use_container_width=True,
        height=600,
        hide_index=True
    )

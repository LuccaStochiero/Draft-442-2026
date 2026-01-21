import streamlit as st
import pandas as pd
from features.auth import get_client

@st.cache_data(ttl=300)
def load_data():
    try:
        client, sh = get_client()
        
        # 1. H2H - ROUNDS (Fantasy Matchups)
        ws_h2h = sh.worksheet("H2H - ROUNDS")
        df_h2h = pd.DataFrame(ws_h2h.get_all_records())
        # Normalize columns
        df_h2h.columns = df_h2h.columns.str.lower().str.strip()
        
        # 2. GAMEWEEK (Real Matches)
        ws_gw = sh.worksheet("GAMEWEEK")
        df_gw = pd.DataFrame(ws_gw.get_all_records())
        
        # 3. TEAM/SQUAD for Name Mapping (if needed)
        ws_squad = sh.worksheet("SQUAD")
        df_squad = pd.DataFrame(ws_squad.get_all_records())
        df_squad.columns = df_squad.columns.str.lower()
        
        return df_h2h, df_gw, df_squad
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

def app():
    st.title("⚔️ Confrontos da Rodada")
    
    with st.spinner("Carregando tabelas..."):
        df_h2h, df_gw, df_squad = load_data()
        
    if df_h2h.empty and df_gw.empty:
        st.warning("Sem dados de confrontos.")
        return

    # Determine Round
    min_r, max_r = 1, 38
    if not df_gw.empty and 'rodada' in df_gw.columns:
        df_gw['rodada'] = pd.to_numeric(df_gw['rodada'], errors='coerce').fillna(1).astype(int)
        max_r = int(df_gw['rodada'].max())
        
    # Standardize H2H Round col
    # Look for 'round', 'rodada', 'gw'
    r_col = next((c for c in df_h2h.columns if c in ['round', 'rodada', 'gw', 'gameweek']), None)
    
    if r_col:
        df_h2h[r_col] = pd.to_numeric(df_h2h[r_col], errors='coerce').fillna(0).astype(int)
        if not df_h2h.empty:
            max_r = max(max_r, int(df_h2h[r_col].max()))
    
    # Selection
    sel_round = st.number_input("Selecione a Rodada", min_value=1, max_value=38, value=1, step=1)
    
    st.divider()
    
    # Custom CSS for styling
    st.markdown("""
    <style>
    .match-card {
        background-color: rgba(255, 255, 255, 0.05);
        border-radius: 12px;
        padding: 10px;
        margin-bottom: 8px;
        text-align: center;
        font-size: 14px;
        color: #e0e0e0;
    }
    .vertical-line {
        border-left: 1px solid rgba(255, 255, 255, 0.2);
        height: 100%;
        margin: auto;
    }
    </style>
    """, unsafe_allow_html=True)
    
    col_fantasy, col_sep, col_real = st.columns([1, 0.1, 1])
    
    # --- LEFT: FANTASY ---
    with col_fantasy:
        st.subheader("🏆 Fantasy 4-4-2")
        if not df_h2h.empty and r_col:
            round_h2h = df_h2h[df_h2h[r_col] == sel_round].copy()
            
            if not round_h2h.empty:
                # Identify Home/Away columns (Explicit ID support)
                home_col = next((c for c in round_h2h.columns if c in ['home_team_id', 'home', 'mandante', 'casa']), None)
                away_col = next((c for c in round_h2h.columns if c in ['away_team_id', 'away', 'visitante', 'fora']), None)
                
                if home_col and away_col:
                    # Resolve Names if they look like IDs and we have SQUAD
                    if not df_squad.empty:
                         id_col = next((c for c in df_squad.columns if c in ['team_id', 'id']), 'team_id')
                         name_col = next((c for c in df_squad.columns if c in ['team_name', 'name', 'nome', 'team', 'time']), None)
                         
                         if id_col and name_col:
                             df_squad['team_id_norm'] = df_squad[id_col].astype(str).str.strip()
                             team_map = pd.Series(df_squad[name_col].values, index=df_squad['team_id_norm']).to_dict()
                             
                             # Apply Map
                             round_h2h[home_col] = round_h2h[home_col].astype(str).str.strip().map(team_map).fillna(round_h2h[home_col])
                             round_h2h[away_col] = round_h2h[away_col].astype(str).str.strip().map(team_map).fillna(round_h2h[away_col])

                    # Display as CSS Cards
                    for _, row in round_h2h.iterrows():
                        home = str(row[home_col]).strip()
                        away = str(row[away_col]).strip()
                        st.markdown(f"""
                        <div class="match-card">
                            <b>{home}</b> ⚔️ <b>{away}</b>
                        </div>
                        """, unsafe_allow_html=True)

                else:
                    st.warning("Colunas de Mandante/Visitante não identificadas no H2H.")
            else:
                st.info(f"Sem jogos fantasy para Rodada {sel_round}.")
        else:
            st.warning("Aba H2H vazia.")

    # --- MIDDLE: SEPARATOR ---
    with col_sep:
        st.markdown('<div class="vertical-line"></div>', unsafe_allow_html=True)

    # --- RIGHT: REAL ---
    with col_real:
        st.subheader("📅 Jogos Reais (SofaScore)")
        if not df_gw.empty:
            round_gw = df_gw[df_gw['rodada'] == sel_round].copy()
            
            if not round_gw.empty:
                # Format Columns: home_team, away_team, data_hora
                if 'data_hora' in round_gw.columns:
                     for _, row in round_gw.iterrows():
                         home = row['home_team']
                         away = row['away_team']
                         dt = row['data_hora']
                         
                         st.markdown(f"""
                        <div class="match-card">
                            {home} ⚔️ {away} <br>
                            <span style="font-size: 12px; color: #888;">({dt})</span>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.dataframe(round_gw)
            else:
                st.info(f"Sem jogos reais importados para Rodada {sel_round}.")
        else:
            st.warning("Aba GAMEWEEK vazia.")

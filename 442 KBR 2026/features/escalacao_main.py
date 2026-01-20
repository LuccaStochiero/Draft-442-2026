import streamlit as st
import pandas as pd
from features.auth import get_client, get_players_file

FORMATIONS = {
    '5-4-1': {'DEF': 5, 'MEI': 4, 'ATA': 1},
    '5-3-2': {'DEF': 5, 'MEI': 3, 'ATA': 2},
    '4-5-1': {'DEF': 4, 'MEI': 5, 'ATA': 1},
    '4-4-2': {'DEF': 4, 'MEI': 4, 'ATA': 2},
    '4-3-3': {'DEF': 4, 'MEI': 3, 'ATA': 3},
    '3-5-2': {'DEF': 3, 'MEI': 5, 'ATA': 2},
    '3-4-3': {'DEF': 3, 'MEI': 4, 'ATA': 3}
}

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
    players_file = get_players_file()
    if players_file.exists():
        df_players = pd.read_csv(players_file)
        df_players['player_id'] = df_players['player_id'].astype(str)
        df_players['SimplePos'] = df_players['Posição'].apply(clean_pos)
    else:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    try:
        client, sh = get_client()
        
        # Load TEAM
        ws_team = sh.worksheet("TEAM")
        df_team = pd.DataFrame(ws_team.get_all_records())
        if not df_team.empty:
            df_team.columns = df_team.columns.str.lower()
            df_team['player_id'] = df_team['player_id'].astype(str)
            df_team['team_id'] = df_team['team_id'].astype(str)

        # Load SQUAD
        ws_squad = sh.worksheet("SQUAD")
        df_squad = pd.DataFrame(ws_squad.get_all_records())
        if not df_squad.empty:
            df_squad.columns = df_squad.columns.str.lower()
            id_col = next((c for c in df_squad.columns if c in ['team_id', 'id']), 'team_id')
            df_squad['team_id_norm'] = df_squad[id_col].astype(str)

    except Exception as e:
        st.error(f"Erro sheets: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
        
    return df_players, df_team, df_squad

def save_lineup(team_id, rodada, formation, lineup_data):
    try:
        client, sh = get_client()

        try:
            ws = sh.worksheet("TEAM_LINEUP")
        except:
            ws = sh.add_worksheet("TEAM_LINEUP", 1000, 10)
            ws.append_row(['team_id', 'player_id', 'rodada', 'formacao', 'lineup', 'posicao', 'cap'])

        # Read existing to remove old lineup for this team/round
        existing = ws.get_all_records()
        df_ex = pd.DataFrame(existing)
        
        new_rows = []
        for p in lineup_data:
            new_rows.append([str(team_id), str(p['player_id']), int(rodada), formation, p['status'], p.get('posicao', ''), p.get('cap', '')])

        if not df_ex.empty:
            df_ex['team_id'] = df_ex['team_id'].astype(str)
            df_ex['rodada'] = pd.to_numeric(df_ex['rodada'], errors='coerce').fillna(0).astype(int)
            mask_del = (df_ex['team_id'] == str(team_id)) & (df_ex['rodada'] == int(rodada))
            df_keep = df_ex[~mask_del]
            # Handle existing data with or without posicao/cap columns
            keep_cols = ['team_id', 'player_id', 'rodada', 'formacao', 'lineup']
            if 'posicao' in df_keep.columns:
                keep_cols.append('posicao')
            else:
                df_keep['posicao'] = ''
                keep_cols.append('posicao')
            if 'cap' in df_keep.columns:
                keep_cols.append('cap')
            else:
                df_keep['cap'] = ''
                keep_cols.append('cap')
            final_data = df_keep[keep_cols].values.tolist()
        else:
            final_data = []

        # Write
        ws.clear()
        ws.append_row(['team_id', 'player_id', 'rodada', 'formacao', 'lineup', 'posicao', 'cap'])
        ws.append_rows(final_data + new_rows)
        return True
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")
        return False

def app():
    st.title("⚽ Escalar Time")
    
    df_players, df_team, df_squad = load_data()
    
    if df_team.empty or df_squad.empty:
        st.warning("Sem dados.")
        return

    # 1. Select Team & Settings
    c1, c2, c3 = st.columns(3)
    with c1:
        name_col = next((c for c in df_squad.columns if c in ['name', 'nome', 'team', 'time', 'team_name']), None)
        team_map = pd.Series(df_squad[name_col].values, index=df_squad['team_id_norm']).to_dict()
        selected_name = st.selectbox("Clube", sorted(team_map.values()))
        team_id = next((k for k,v in team_map.items() if v == selected_name), None)

    with c2:
        rodada = st.number_input("Rodada", min_value=1, max_value=38, value=1)
    
    with c3:
        formacao = st.selectbox("Formação", list(FORMATIONS.keys()), index=3)
    
    # 2. Filter Roster
    roster_ids = df_team[df_team['team_id'] == team_id]['player_id'].tolist()
    roster = df_players[df_players['player_id'].isin(roster_ids)].copy()
    
    st.divider()
    
    # 3. Select Starters
    fmt = FORMATIONS[formacao]
    selected = [] # List of dicts {player_id, status}
    used_ids = set()

    st.subheader("Titulares")
    c_gk, c_def, c_mei, c_ata = st.columns(4)
    
    def select_players(label, pos, count, container):
        avail = roster[(roster['SimplePos'] == pos) & (~roster['player_id'].isin(used_ids))]
        chosen = container.multiselect(f"{label} ({count})", avail['Nome'].unique(), max_selections=count, key=f"start_{pos}")
        
        # Lookup IDs
        for name in chosen:
            row = avail[avail['Nome'] == name].iloc[0]
            pid = row['player_id']
            pos = row['SimplePos']
            used_ids.add(pid)
            selected.append({'player_id': pid, 'status': 'TITULAR', 'posicao': pos})

    with c_gk: select_players("Goleiro", 'GK', 1, st)
    with c_def: select_players("Defensores", 'DEF', fmt['DEF'], st)
    with c_mei: select_players("Meias", 'MEI', fmt['MEI'], st)
    with c_ata: select_players("Atacantes", 'ATA', fmt['ATA'], st)

    # 3.5 Select Captain (from starters only)
    starters = [p for p in selected if p['status'] == 'TITULAR']
    if starters:
        starter_pids = [p['player_id'] for p in starters]
        starter_names = roster[roster['player_id'].isin(starter_pids)]['Nome'].tolist()
        
        st.markdown("#### 🏅 Capitão")
        captain_name = st.selectbox("Escolha o Capitão", starter_names, key="captain_select")
        captain_pid = roster[roster['Nome'] == captain_name]['player_id'].iloc[0] if captain_name else None

    # 4. Select Reserves
    st.divider()
    st.subheader("Reservas (1 por posição)")
    r_gk, r_def, r_mei, r_ata = st.columns(4)

    def select_reserve(label, pos, container):
        avail = roster[(roster['SimplePos'] == pos) & (~roster['player_id'].isin(used_ids))]
        
        if avail.empty:
            container.warning(f"{label}: Sem opções")
            return

        options = list(avail['Nome'].unique())
        # Default to no selection effectively requires handle, but Streamlit selectbox default is index 0.
        # User implies they want to choose from available.
        # We can use index=None (placeholder) if newer streamlit, but let's stick to standard behavior 
        # or use a placeholder if desired. User said "no None option", meaning they MUST pick or it just shows options.
        
        # If we remove None, they must pick one of the available.
        chosen = container.selectbox(f"Reserva {label}", options, key=f"res_{pos}")
        
        if chosen:
            row = avail[avail['Nome'] == chosen].iloc[0]
            pid = row['player_id']
            pos = row['SimplePos']
            used_ids.add(pid)
            selected.append({'player_id': pid, 'status': 'RESERVA', 'posicao': pos})

    with r_gk: select_reserve("GK", 'GK', st)
    with r_def: select_reserve("DEF", 'DEF', st)
    with r_mei: select_reserve("MEI", 'MEI', st)
    with r_ata: select_reserve("ATA", 'ATA', st)

    # 5. Mark Rest as FORA
    remaining = roster[~roster['player_id'].isin(used_ids)]
    for _, row in remaining.iterrows():
        selected.append({'player_id': row['player_id'], 'status': 'FORA', 'posicao': row['SimplePos']})

    # 6. Save
    st.markdown("---")
    if st.button("💾 Salvar Escalação", type="primary"):
        # Apply Captain Status
        if starters and captain_pid:
            for p in selected:
                if p['player_id'] == captain_pid:
                    p['cap'] = 'CAPITAO'
                else:
                    p['cap'] = ''
        
        with st.spinner("Salvando..."):
            if save_lineup(team_id, rodada, formacao, selected):
                st.success("Escalação salva com sucesso!")

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
    captain_pid = None
    starters = [p for p in selected if p['status'] == 'TITULAR']
    if starters:
        starter_pids = [p['player_id'] for p in starters]
        starter_names = roster[roster['player_id'].isin(starter_pids)]['Nome'].tolist()
        
        st.markdown("#### 🏅 Capitão")
        captain_name = st.selectbox("Escolha o Capitão", starter_names, key="captain_select")
        captain_pid = roster[roster['Nome'] == captain_name]['player_id'].iloc[0] if captain_name else None

    # 4. Priority Bench (Reservas)
    st.divider()
    st.subheader("Banco de Reservas (Prioridade)")
    st.info("Selecione os reservas na ordem de prioridade (1º selecionado = 1ª opção, etc). Jogadores não selecionados entrarão na lista com prioridade inferior automaticamente.")

    rb_col1, rb_col2 = st.columns(2)
    
    # Helper for Priority Selection
    def select_priority_reserves(label, pos, container):
        # 1. Get available
        avail = roster[(roster['SimplePos'] == pos) & (~roster['player_id'].isin(used_ids))]
        
        if avail.empty:
            container.caption(f"{label}: Sem jogadores disponíveis.")
            return

        # 2. Ordered Multiselect
        options = avail['Nome'].tolist()
        # Sort options alphabetically for easier finding, but selection order matters for priority
        options.sort() 
        
        chosen_names = container.multiselect(
            f"{label} (Defina a Ordem)", 
            options, 
            key=f"bench_pri_{pos}",
            help="O primeiro nome escolhido será a Pri 1, o segundo a Pri 2, e assim por diante."
        )
        
        # 3. Assign Priority to Selected
        priority_counter = 1
        for name in chosen_names:
            row = avail[avail['Nome'] == name].iloc[0]
            pid = row['player_id']
            p_pos = row['SimplePos']
            
            selected.append({
                'player_id': pid, 
                'status': f'PRI {priority_counter}', 
                'posicao': p_pos
            })
            used_ids.add(pid)
            priority_counter += 1
            
        # 4. Assign Priority to Unselected (Remaining)
        remaining = avail[~avail['Nome'].isin(chosen_names)]
        # Sort remaining by something standard (e.g. Value or Name)
        remaining = remaining.sort_values(by='Valor de Mercado', ascending=False)
        
        for _, row in remaining.iterrows():
            selected.append({
                'player_id': row['player_id'],
                'status': f'PRI {priority_counter}',
                'posicao': row['SimplePos']
            })
            used_ids.add(row['player_id'])
            priority_counter += 1

    with rb_col1:
        select_priority_reserves("Goleiros", 'GK', st)
        select_priority_reserves("Defensores", 'DEF', st)
        
    with rb_col2:
        select_priority_reserves("Meias", 'MEI', st)
        select_priority_reserves("Atacantes", 'ATA', st)

    # 5. Remaining (should be empty if logic works, but check just in case of other positions?)
    # The clean_pos ensures we only have 4 positions. 
    # Any player not caught above?
    remaining_all = roster[~roster['player_id'].isin(used_ids)]
    for _, row in remaining_all.iterrows():
         # Fallback
         selected.append({'player_id': row['player_id'], 'status': 'PRI 99', 'posicao': row['SimplePos']})

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
    
    st.caption("v1.3 - Com Capitão e Posição")

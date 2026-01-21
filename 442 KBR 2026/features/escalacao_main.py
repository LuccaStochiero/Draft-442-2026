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

def get_saved_lineup_data(team_id, rodada):
    try:
        client, sh = get_client()
        try:
             ws = sh.worksheet("TEAM_LINEUP")
        except:
             return pd.DataFrame()
             
        # Optimization: Get all and filter in DF (easier than cell matching)
        records = ws.get_all_records()
        df = pd.DataFrame(records)
        
        if df.empty: return df
        
        df.columns = df.columns.str.lower()
        if 'rodada' not in df.columns or 'team_id' not in df.columns: return pd.DataFrame()
        
        df['rodada'] = pd.to_numeric(df['rodada'], errors='coerce').fillna(0).astype(int)
        df['team_id'] = df['team_id'].astype(str)
        
        mask = (df['team_id'] == str(team_id)) & (df['rodada'] == int(rodada))
        return df[mask].copy()
        
    except Exception as e:
        # st.error(f"Erro ao ler escalação: {e}") # Silently fail or log?
        return pd.DataFrame()

def render_card_header(label, bg_color, text_color):
    st.markdown(
        f"""
        <div style="
            background-color: {bg_color};
            padding: 10px;
            border-radius: 5px;
            margin-bottom: 10px;
            text-align: center;
        ">
            <h5 style="margin: 0; color: {text_color};">{label}</h5>
        </div>
        """,
        unsafe_allow_html=True
    )

def render_saved_player(name, pos, cap, status, bg_color):
    cap_icon = "©️" if (cap and str(cap).lower() == 'capitao') else ""
    st.markdown(
        f"""
        <div style="
            background-color: {bg_color};
            padding: 8px 12px;
            border-radius: 4px;
            margin-bottom: 5px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border: 1px solid #ddd;
        ">
            <div>
                <span style="font-weight: bold; margin-right: 8px; color: #333;">{pos}</span>
                <span style="color: #000;">{name}</span>
                <span style="margin-left: 5px;">{cap_icon}</span>
            </div>
            <div style="font-size: 0.8em; color: #555;">
                {status}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

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

    # --- TOP SECTION: DEADLINE & SAVE ---
    import features.calendar_utils as calendar_utils
    state = calendar_utils.get_game_state()
    is_locked = state['status'] == 'LOCKED' or state['status'] == 'Season Finished'
    
    # Check Saved Lineup
    saved_df = get_saved_lineup_data(team_id, rodada)
    has_lineup = not saved_df.empty

    # Logic to build lineup from session state (for Callback)
    def save_adapter(tid, rod, fmt, rst):
        # Security Check
        curr = calendar_utils.get_game_state()
        if curr['status'] in ['LOCKED', 'Season Finished']:
            st.toast(f"🚫 Fechado: {curr.get('msg')}", icon="🔒")
            return

        # Reconstruct 'selected' from session_state
        sel = []
        u_ids = set()
        
        # 1. Starters
        f_map = FORMATIONS[fmt]
        
        def process_start(pos):
             keys = [k for k in st.session_state.keys() if k == f"start_{pos}"]
             if keys:
                 names = st.session_state[keys[0]]
                 for name in names:
                     row = rst[rst['Nome'] == name]
                     if not row.empty:
                         pid = row.iloc[0]['player_id']
                         ppos = row.iloc[0]['SimplePos']
                         u_ids.add(pid)
                         sel.append({'player_id': pid, 'status': 'TITULAR', 'posicao': ppos})

        process_start('GK')
        process_start('DEF')
        process_start('MEI')
        process_start('ATA')

        # 2. Captain
        cap_val = st.session_state.get("captain_select")
        cap_pid = None
        if cap_val:
            c_row = rst[rst['Nome'] == cap_val]
            if not c_row.empty:
               cap_pid = c_row.iloc[0]['player_id']
        
        # Apply Captain
        if cap_pid:
            for p in sel:
                if p['player_id'] == cap_pid: p['cap'] = 'CAPITAO'
                else: p['cap'] = ''
        
        # 3. Reserves
        def process_bench(pos, counter_start):
             key = f"bench_pri_{pos}"
             chosen = st.session_state.get(key, [])
             
             # Available for this pos (excluding starters)
             avail = rst[(rst['SimplePos'] == pos) & (~rst['player_id'].isin(u_ids))].copy()
             
             # Priority from Selection
             for name in chosen:
                 row = avail[avail['Nome'] == name]
                 if not row.empty:
                     pid = row.iloc[0]['player_id']
                     p_pos = row.iloc[0]['SimplePos']
                     sel.append({'player_id': pid, 'status': f'PRI {counter_start}', 'posicao': p_pos})
                     u_ids.add(pid)
                     counter_start += 1
            
             # Remaining
             rem = avail[~avail['Nome'].isin(chosen)]
             rem = rem.sort_values(by='Valor de Mercado', ascending=False)
             for _, r in rem.iterrows():
                 sel.append({'player_id': r['player_id'], 'status': f'PRI {counter_start}', 'posicao': r['SimplePos']})
                 u_ids.add(r['player_id'])
                 counter_start += 1
             return counter_start

        # Need a global counter? actually the PRI is per position? 
        # "O primeiro nome escolhido será a Pri 1..." usually implies Global or Per Pos?
        # Based on previous code: "priority_counter = 1" was reset? 
        # checking previous code... 
        # "priority_counter = 1" was defined INSIDE select_priority_reserves loop.
        # So it is 1,2,3 PER position group call. 
        # Wait, select_priority_reserves was called 4 times.
        # Inside the function: priority_counter = 1.
        # So GK PRI 1, GK PRI 2... DEF PRI 1, DEF PRI 2...
        # Yes.
        
        process_bench('GK', 1)
        process_bench('DEF', 1)
        process_bench('MEI', 1)
        process_bench('ATA', 1)
        
        # 4. Fallback for anyone missing?
        rem_all = rst[~rst['player_id'].isin(u_ids)]
        for _, r in rem_all.iterrows():
            sel.append({'player_id': r['player_id'], 'status': 'PRI 99', 'posicao': r['SimplePos']})

        # SAVE
        if save_lineup(tid, rod, fmt, sel):
            st.toast("Escalação Salva!", icon="💾")

    # Layout Top
    if is_locked:
        st.error(f"🚫 Escalação Fechada: {state.get('msg', 'Mercado Fechado')}")
        if state.get('deadline_msg'): st.caption(state['deadline_msg'])
    else:
        deadline_txt = state.get('lineup_msg') or state.get('deadline_msg')
        if deadline_txt:
            st.info(f"⏳ Prazo Final: {deadline_txt} (2h antes do jogo)")
    
    c_btn, c_stat = st.columns([1, 2])
    
    with c_btn:
        if st.button("💾 Salvar Escalação", type="primary", disabled=is_locked, 
                     on_click=save_adapter, args=(team_id, rodada, formacao, roster)):
            pass # Callback handles it
            
    with c_stat:
        if has_lineup:
            st.success("✅ Escalação Salva")
        else:
            st.warning("🔴 Precisa Escalar")
            
    if has_lineup:
        with st.expander("Ver Escalação Salva", expanded=False):
            # Show Formation
            saved_form = saved_df['formacao'].iloc[0]
            st.caption(f"Formação Salva: {saved_form}")

            # Merge with Player Details (Name)
            # saved_df has 'player_id', 'lineup' (status), 'posicao', 'cap'
            # roster has 'player_id', 'Nome'
            
            # Ensure types match
            saved_df['player_id'] = saved_df['player_id'].astype(str)
            full_saved = saved_df.merge(roster[['player_id', 'Nome']], on='player_id', how='left')
            full_saved['Nome'] = full_saved['Nome'].fillna("Desconhecido")
            
            # 1. Starters
            starters = full_saved[full_saved['lineup'] == 'TITULAR'].copy()
            # Sort Order: GK, DEF, MEI, ATA
            pos_map_order = {'GK': 0, 'DEF': 1, 'MEI': 2, 'ATA': 3}
            starters['pos_idx'] = starters['posicao'].map(pos_map_order).fillna(99)
            starters = starters.sort_values('pos_idx')
            
            # Colors
            pos_colors = {'GK': '#E3F2FD', 'DEF': '#E8F5E9', 'MEI': '#FFF9C4', 'ATA': '#FFEBEE'}
            
            st.markdown("###### Titulares")
            for _, r in starters.iterrows():
                bg = pos_colors.get(r['posicao'], '#f9f9f9')
                render_saved_player(r['Nome'], r['posicao'], r['cap'], r['lineup'], bg)
                
            # 2. Reserves
            # Typically 'lineup' is 'PRI 1', 'PRI 2', etc.
            # We want to sort by that string text naturally works 1 < 2? 
            # 'PRI 1' < 'PRI 10' -> Yes. But 'PRI 2' > 'PRI 10' strings.. Wait
            # PRI 1 vs PRI 10. '1' < '10' in ASCII. ' ' is same. 
            # '1' vs '1'. ' ' vs '0'. ' ' is 32, '0' is 48. So PRI 1 < PRI 10.
            # PRI 9 vs PRI 10. '9' > '1'. It will sort wrong if just string sort PRI 10 comes before PRI 2.
            # Let's extract number.
            
            reserves = full_saved[full_saved['lineup'].str.startswith("PRI")].copy()
            
            def extract_pri(s):
                try: 
                    return int(s.replace("PRI", "").strip())
                except:
                    return 999
            
            reserves['pri_idx'] = reserves['lineup'].apply(extract_pri)
            reserves = reserves.sort_values('pri_idx')
            
            st.markdown("###### Banco de Reservas (Prioridade)")
            for _, r in reserves.iterrows():
                bg = pos_colors.get(r['posicao'], '#f9f9f9')
                render_saved_player(r['Nome'], r['posicao'], r['cap'], r['lineup'], bg)

    st.divider()

    # --- MAIN LAYOUT ---
    col_titulares, col_reservas = st.columns(2)
    
    # --- COLUNA 1: TITULARES + CAPITÃO ---
    with col_titulares:
        with st.container(border=True):
            render_card_header("TITULARES E CAPITÃO", "#e6fffa", "#00664d")
            
            fmt = FORMATIONS[formacao]
            selected = [] # List of dicts {player_id, status}
            used_ids = set()

            # Starters Layout: Stacked Vertically
            
            def select_players(label, pos, count, container):
                avail = roster[(roster['SimplePos'] == pos) & (~roster['player_id'].isin(used_ids))]
                chosen = container.multiselect(f"{label} ({count})", avail['Nome'].unique(), max_selections=count, key=f"start_{pos}")
                
                # Lookup IDs
                for name in chosen:
                    row = avail[avail['Nome'] == name]
                    if not row.empty:
                        pid = row.iloc[0]['player_id']
                        p_pos = row.iloc[0]['SimplePos']
                        used_ids.add(pid)
                        selected.append({'player_id': pid, 'status': 'TITULAR', 'posicao': p_pos})

            select_players("Goleiro", 'GK', 1, st)
            select_players("Defensores", 'DEF', fmt['DEF'], st)
            select_players("Meias", 'MEI', fmt['MEI'], st)
            select_players("Atacantes", 'ATA', fmt['ATA'], st)

            st.divider()
            
            # Captain
            possible_starters = roster[roster['player_id'].isin(used_ids)]
            starter_names = possible_starters['Nome'].tolist()
            st.markdown("#### 🏅 Capitão")
            st.selectbox("Escolha o Capitão", starter_names, key="captain_select")


    # --- COLUNA 2: RESERVAS ---
    with col_reservas:
        with st.container(border=True):
            render_card_header("PRIORIDADE DOS RESERVAS", "#fffbe6", "#997a00")
            st.info("Selecione os reservas na ordem de prioridade. (1º = Pri 1, etc).")
            
            # Helper for Priority Selection
            def select_priority_reserves(label, pos, container):
                # 1. Get available
                avail = roster[(roster['SimplePos'] == pos) & (~roster['player_id'].isin(used_ids))]
                
                if avail.empty:
                    container.caption(f"{label}: Sem opções.")
                    return

                # 2. Ordered Multiselect
                options = avail['Nome'].tolist()
                options.sort() 
                
                chosen_names = container.multiselect(
                    f"{label}", 
                    options, 
                    key=f"bench_pri_{pos}",
                    help="Ordem define a prioridade."
                )
                
                # Update used_ids for next calls (though usually distinct pos)
                for name in chosen_names:
                    row = avail[avail['Nome'] == name]
                    if not row.empty:
                        used_ids.add(row.iloc[0]['player_id'])

            # Stacked Vertically
            select_priority_reserves("Goleiros", 'GK', st)
            select_priority_reserves("Defensores", 'DEF', st)
            select_priority_reserves("Meias", 'MEI', st)
            select_priority_reserves("Atacantes", 'ATA', st)
    
    st.caption("v1.5 - Filters Stacked, Top Save")

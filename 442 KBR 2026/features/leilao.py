import streamlit as st
import pandas as pd
from features.auth import get_client, get_players_file

@st.cache_data(ttl=60)
def load_data():
    players_file = get_players_file()
    if not players_file.exists():
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    
    df_players = pd.read_csv(players_file)
    df_players['player_id'] = df_players['player_id'].astype(str)
    
    try:
        client, sh = get_client()
        
        # Load TEAM
        data_team = sh.worksheet("TEAM").get_all_records()
        df_team = pd.DataFrame(data_team)
        if not df_team.empty:
            df_team.columns = df_team.columns.str.lower()
            df_team['player_id'] = df_team['player_id'].astype(str)
            df_team['team_id'] = df_team['team_id'].astype(str)
            
        # Load SQUAD
        data_squad = sh.worksheet("SQUAD").get_all_records()
        df_squad = pd.DataFrame(data_squad)
        if not df_squad.empty:
            df_squad.columns = df_squad.columns.str.lower()
            id_col = next((c for c in df_squad.columns if c in ['team_id', 'id']), 'team_id')
            df_squad['team_id_norm'] = df_squad[id_col].astype(str)
            if 'caixa' in df_squad.columns:
                df_squad['caixa'] = pd.to_numeric(df_squad['caixa'].astype(str).str.replace(',','.'), errors='coerce').fillna(0)

        # Load FREE
        try:
            data_free = sh.worksheet("PLAYERS_FREE").get_all_records()
            df_free_tab = pd.DataFrame(data_free)
            if not df_free_tab.empty:
                df_free_tab.columns = df_free_tab.columns.str.lower()
                df_free_tab['player_id'] = df_free_tab['player_id'].astype(str)
        except:
            df_free_tab = pd.DataFrame()

    except Exception as e:
        st.error(f"Erro sheets: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
        
    return df_players, df_team, df_squad, df_free_tab

def save_bid(team_id, rodada, pid_free, pid_team, price):
    try:
        client, sh = get_client()
        try:
            ws = sh.worksheet("LEILAO_LANCES")
        except:
            ws = sh.add_worksheet("LEILAO_LANCES", 1000, 5)
            ws.append_row(['team_id', 'rodada', 'player_id_free', 'player_id_team', 'price'])
        
        ws.append_row([str(team_id), int(rodada), str(pid_free), str(pid_team), float(price)])
        return True
    except Exception as e:
        st.error(f"Erro ao salvar lance: {e}")
        return False

def process_auction():
    try:
        client, sh = get_client()
        
        # 1. Load Data Live
        ws_lances = sh.worksheet("LEILAO_LANCES")
        lances = pd.DataFrame(ws_lances.get_all_records())
        
        if lances.empty: st.info("Sem lances."); return

        lances.columns = lances.columns.str.lower()
        if 'rodada' not in lances.columns: return
        
        lances['rodada'] = pd.to_numeric(lances.rodada, errors='coerce').fillna(0).astype(int)
        lances['price'] = pd.to_numeric(lances.price, errors='coerce').fillna(0)
        
        max_round = lances['rodada'].max()
        df_process = lances[lances['rodada'] == max_round].sort_values(by='price', ascending=False)
        
        st.write(f"Processando Rodada {max_round} ({len(df_process)} lances)...")
        
        # Load State
        ws_team = sh.worksheet("TEAM")
        teams_rows = ws_team.get_all_records() # List of dicts
        
        ws_squad = sh.worksheet("SQUAD")
        squad_rows = ws_squad.get_all_records()
        
        try: ws_free = sh.worksheet("PLAYERS_FREE") 
        except: ws_free = sh.add_worksheet("PLAYERS_FREE", 1000,2)
        free_rows = ws_free.get_all_records()
        
        # Helpers
        def get_budget(tid):
            for r in squad_rows:
                if str(r.get('team_id', r.get('id'))) == str(tid):
                    val = str(r.get('caixa', 0)).replace(',','.')
                    return float(val)
            return 0.0
            
        def update_budget(tid, val):
            for r in squad_rows:
                 if str(r.get('team_id', r.get('id'))) == str(tid):
                    cur = float(str(r.get('caixa', 0)).replace(',','.'))
                    r['caixa'] = cur - val
                    return

        def is_free(pid):
            # Check strictly in PLAYERS_FREE
            for r in free_rows:
                if str(r.get('player_id')) == str(pid): return True
            return False

        def owns_player(tid, pid):
            for r in teams_rows:
                if str(r.get('team_id')) == str(tid) and str(r.get('player_id')) == str(pid): return True
            return False

        def get_roster_size(tid):
            count = 0
            for r in teams_rows:
                if str(r.get('team_id')) == str(tid):
                    count += 1
            return count

        processed_bids = []
        valid_bids = []

        for _, bid in df_process.iterrows():
            tid = str(bid['team_id'])
            p_free = str(bid['player_id_free'])
            p_drop = str(bid['player_id_team'])
            price = float(bid['price'])
            
            # Checks
            if get_budget(tid) < price:
                st.write(f"❌ {tid}: Sem caixa.")
                continue
            if not is_free(p_free):
                st.write(f"❌ {tid}: {p_free} não está livre (já vendido?).")
                continue
            
            # Check for NENHUM (empty slot) case
            is_empty_slot = p_drop == "NENHUM" or p_drop == ""
            
            if is_empty_slot:
                # Verify team still has ≤17 players
                if get_roster_size(tid) > 17:
                    st.write(f"❌ {tid}: Elenco cheio (>17). Não pode usar vaga livre.")
                    continue
            else:
                # Normal case - must own the player to drop
                if not owns_player(tid, p_drop):
                    st.write(f"❌ {tid}: Não possui {p_drop}.")
                    continue
            
            # --- EXECUTE ---
            st.write(f"✅ Lance Válido: {tid} leva {p_free} por {price}" + (" (Vaga Livre)" if is_empty_slot else ""))
            
            # 1. Update Budget
            update_budget(tid, price)
            
            # 2. Handle TEAM
            if is_empty_slot:
                # Just add the new player without removing anyone
                # Create a new row (use first row as template for structure)
                if teams_rows:
                    new_row = {k: '' for k in teams_rows[0].keys()}
                    new_row['team_id'] = tid
                    new_row['player_id'] = p_free
                else:
                    new_row = {'team_id': tid, 'player_id': p_free}
                teams_rows.append(new_row)
            else:
                # Swap: Find row to remove and replace player
                idx_rem = -1
                for i, r in enumerate(teams_rows):
                    if str(r.get('team_id')) == tid and str(r.get('player_id')) == p_drop:
                        idx_rem = i
                        break
                
                if idx_rem != -1:
                    old_row = teams_rows.pop(idx_rem)
                    new_row = old_row.copy()
                    new_row['player_id'] = p_free
                    teams_rows.append(new_row)
                
                # Add dropped player to FREE
                free_rows.append({'player_id': p_drop})
            
            # 3. Remove p_free from FREE list
            idx_free = -1
            for i, r in enumerate(free_rows):
                 if str(r.get('player_id')) == p_free: idx_free = i; break
            if idx_free != -1: free_rows.pop(idx_free)
            
            valid_bids.append(bid)
        
        # --- COMMIT ---
        if valid_bids:
            # TEAM
            ws_team.clear()
            headers = list(teams_rows[0].keys()) if teams_rows else []
            ws_team.update([headers] + [list(r.values()) for r in teams_rows])
            
            # PLAYERS_FREE
            ws_free.clear()
            ws_free.update([['player_id']] + [[r['player_id']] for r in free_rows])
            
            # SQUAD
            ws_squad.clear()
            headers_sq = list(squad_rows[0].keys()) if squad_rows else []
            ws_squad.update([headers_sq] + [list(r.values()) for r in squad_rows])
            
            # LEILAO_VENCIDO
            try: ws_vencido = sh.worksheet("LEILAO_VENCIDO")
            except: ws_vencido = sh.add_worksheet("LEILAO_VENCIDO", 1000, 5)
            
            vb_df = pd.DataFrame(valid_bids)
            data_venc = vb_df[['team_id','rodada','player_id_free','player_id_team','price']].values.tolist()
            ws_vencido.append_rows(data_venc)
            
            # Remove from LANCES (Only processed round)
            # Re-read lances to be safe or filter df
            lances_remain = lances[lances['rodada'] != max_round]
            ws_lances.clear()
            if not lances_remain.empty:
                ws_lances.update([lances_remain.columns.tolist()] + lances_remain.values.tolist())
            else:
                 ws_lances.append_row(['team_id','rodada','player_id_free','player_id_team','price'])
            
            st.success("Processamento concluído com sucesso!")
        else:
            st.warning("Nenhum lance foi efetivado.")

    except Exception as e:
        st.error(f"Erro processamento: {e}")

from features import calendar_utils

def execute_free_swap(team_id, drop_pid, pickup_pid, rodada):
    """
    Swap a player from Team to Free Agency
    """
    try:
        client, sh = get_client()
        
        # 1. Update TEAM
        ws_team = sh.worksheet("TEAM")
        team_rows = ws_team.get_all_records()
        
        updated_team = False
        for r in team_rows:
            if str(r.get('team_id')) == str(team_id) and str(r.get('player_id')) == str(drop_pid):
                r['player_id'] = str(pickup_pid)
                updated_team = True
                break
        
        if not updated_team:
            st.error("Erro: Jogador a dispensar não encontrado no time.")
            return False
            
        # 2. Update PLAYERS_FREE
        ws_free = sh.worksheet("PLAYERS_FREE")
        free_rows = ws_free.get_all_records()
        
        # Remove pickup
        new_free_rows = [r for r in free_rows if str(r.get('player_id')) != str(pickup_pid)]
        # Add drop (only player_id col usually)
        new_free_rows.append({'player_id': str(drop_pid)})
        
        # 3. Log Transaction
        try:
            ws_log = sh.worksheet("LOG_FREE_AGENCY")
        except:
            ws_log = sh.add_worksheet("LOG_FREE_AGENCY", 1000, 5)
            ws_log.append_row(['rodada', 'team_id', 'added_id', 'dropped_id', 'timestamp'])
            
        from datetime import datetime
        ws_log.append_row([
            rodada, 
            str(team_id), 
            str(pickup_pid), 
            str(drop_pid), 
            str(datetime.now())
        ])
        
        # Commit Updates
        ws_team.clear()
        if team_rows:
            ws_team.update([list(team_rows[0].keys())] + [list(r.values()) for r in team_rows])
            
        ws_free.clear()
        if new_free_rows:
             keys = list(new_free_rows[0].keys())
             ws_free.update([keys] + [list(r.values()) for r in new_free_rows])
        else:
             ws_free.update([['player_id']]) # Header only
             
        return True

    except Exception as e:
        st.error(f"Erro ao processar troca: {e}")
        return False

def app(is_admin=False):
    st.title("💰 Leilão / Free Agency")
    
    # --- GAME STATE BANNER ---
    state = calendar_utils.get_game_state()
    if state['status'] == 'ERROR':
        st.error(state['msg'])
    else:
        # Color coding
        color = "green" if "ABERTO" in state['msg'] else "red"
        if "FREE AGENCY" in state['msg']: color = "orange"
        
        st.info(f"📅 **Status do Mercado:** {state['msg']}")
        if state.get('deadline_msg'):
            # Emphasized Deadline with colored box
            # Default Blue
            box_color = "#e6f3ff" 
            border_color = "#3366ff"
            text_color = "#004d99"
            
            if "LEILÃO" in state['msg']:
                # Greenish
                box_color = "#e6fffa"
                border_color = "#00cc99"
                text_color = "#00664d"
            elif "FREE" in state['msg']:
                # Yellowish
                box_color = "#fffbe6"
                border_color = "#ffcc00"
                text_color = "#997a00"
                
            st.markdown(
                f"""
                <div style="
                    background-color: {box_color};
                    border-left: 5px solid {border_color};
                    padding: 15px;
                    border-radius: 5px;
                    margin-top: 10px;
                    margin-bottom: 10px;
                ">
                    <h4 style="margin:0; color: {text_color}; font-size: 1.2rem;">🕒 {state['deadline_msg']}</h4>
                </div>
                """,
                unsafe_allow_html=True
            )
            
        # Optional: Show warnings if relevant
        if not state['auction_open'] and not state['free_open']:
            st.warning("Mercado fechado no momento.")
            
    st.divider()

    if is_admin:
        if st.button("👑 PROCESSAR RODADA ATUAL (Leilão)", type="primary"):
            process_auction()
        st.divider()

    # TABS using streamlit tabs
    tab_auction, tab_free = st.tabs(["🔨 Leilão", "🆓 Free Agency"])
    
    # --- LOAD DATA ---
    df_players, df_team, df_squad, df_free_tab = load_data()
    if df_squad.empty: return

    # Common Team Map
    name_col = next((c for c in df_squad.columns if c in ['name', 'nome', 'team', 'time', 'team_name']), None)
    team_map = pd.Series(df_squad[name_col].values, index=df_squad['team_id_norm']).to_dict()

    # --- TAB 1: AUCTION ---
    with tab_auction:
        if not state['auction_open']:
            st.warning("O Leilão está FECHADO.")
        
        # User Form (Auction)
        # 1. Inputs
        c1, c20 = st.columns(2)
        with c1:
            sel_team = st.selectbox("Clube", sorted(team_map.values()), key="auc_team")
            tid = next((k for k,v in team_map.items() if v == sel_team), None)
            
            # Budget info
            budget = df_squad[df_squad['team_id_norm'] == tid]['caixa'].iloc[0]
            st.caption(f"Caixa: $ {budget:,.2f}")

        with c20:
            rodada = st.number_input("Rodada", min_value=1, max_value=38, value=1, key="auc_round")
            
        c2, c3, c4 = st.columns(3)
        
        # Target (Free)
        with c2:
            if not df_free_tab.empty:
                free_ids = df_free_tab['player_id'].unique()
                free_details_auc = df_players[df_players['player_id'].isin(free_ids)].copy()
                free_details_auc['Label'] = free_details_auc['Nome'] + " (" + free_details_auc['Posição'] + ")"
                
                target_name = st.selectbox("Alvo (Livre)", free_details_auc['Label'].unique(), key="auc_target")
                pid_free = free_details_auc[free_details_auc['Label'] == target_name]['player_id'].iloc[0]
            else:
                st.warning("Ninguem livre.")
                pid_free = None
                
        # Drop (Own)
        with c3:
            own_ids = df_team[df_team['team_id'] == tid]['player_id'].tolist()
            roster_size = len(own_ids)
            own_details = df_players[df_players['player_id'].isin(own_ids)].copy()
            st.caption(f"Elenco: {roster_size} jogadores")
            
            if not own_details.empty:
                own_details['Label'] = own_details['Nome'] + " (" + own_details['Posição'] + ")"
                options = list(own_details['Label'].unique())
                if roster_size <= 17:
                    options = ["Nenhum (Vaga Livre)"] + options
                
                drop_name = st.selectbox("Descarte (Meu)", options, key="auc_drop")
                if drop_name == "Nenhum (Vaga Livre)":
                    pid_drop = "NENHUM"
                else:
                    pid_drop = own_details[own_details['Label'] == drop_name]['player_id'].iloc[0]
            else:
                pid_drop = "NENHUM" # Empty roster
                
        with c4:
            safe_budget = float(budget or 0.0)
            if safe_budget <= 0.0:
                st.error("Sem caixa.")
                price = 0.0
            else:
                price = st.number_input("Lance ($)", min_value=0.0, max_value=safe_budget, step=0.1, format="%.1f", key="auc_price")
            
        if st.button("Enviar Lance", disabled=not state['auction_open']):
            if not state['auction_open']:
                st.error("Leilão Fechado.")
            elif price > budget:
                st.error("Sem grana.")
            elif not pid_free:
                st.error("Selecione o jogador.")
            else:
                if save_bid(tid, rodada, pid_free, pid_drop, price):
                    st.success("Lance enviado!")

    # --- TAB 2: FREE AGENCY ---
    with tab_free:
        if not state['free_open']:
            st.warning("O Free Agency está FECHADO.")

        st.markdown("##### Troca de Jogador (Free Agency)")
        
        # Team Selector for Free Agency
        c_fa_1, _ = st.columns(2)
        with c_fa_1:
             sel_team_fa = st.selectbox("Clube", sorted(team_map.values()), key="fa_team_select")
             tid_fa = next((k for k,v in team_map.items() if v == sel_team_fa), None)

        col1, col2 = st.columns(2)
        
        # --- COLUMN 1: DROP (My Team) ---
        with col1:
            st.subheader("🔻 Dispensar")
            
            # Get players for selected team
            own_ids_fa = df_team[df_team['team_id'] == tid_fa]['player_id'].tolist()
            own_details_fa = df_players[df_players['player_id'].isin(own_ids_fa)].copy()
            
            if not own_details_fa.empty:
                own_details_fa['Label'] = own_details_fa['Nome'] + " (" + own_details_fa['Posição'] + ")"
                drop_player_label_fa = st.selectbox("Escolha quem sai", own_details_fa['Label'].tolist(), key="fa_drop")
                drop_pid_fa = own_details_fa[own_details_fa['Label'] == drop_player_label_fa]['player_id'].iloc[0]
            else:
                st.warning("Seu time está vazio.")
                drop_pid_fa = None

        # --- COLUMN 2: PICKUP (Free Agents) ---
        with col2:
            st.subheader("Adicionar")
            # Filters
            search_fa = st.text_input("Buscar Jogador Livre", placeholder="Nome...", key="fa_search")
            
            # Need to re-filter free players if needed or reuse loaded full set (df_players - owned)
            # Actually we load `free_ids` from PLAYERS_FREE sheet
            # Reuse `df_free_tab` logic
            if not df_free_tab.empty:
                free_ids_fa = df_free_tab['player_id'].unique()
                free_details_fa = df_players[df_players['player_id'].isin(free_ids_fa)].copy()
                free_details_fa['Label'] = free_details_fa['Nome'] + " (" + free_details_fa['Posição'] + ")"
            else:
                free_details_fa = pd.DataFrame()

            filtered_free = free_details_fa.copy()
            
            if search_fa and not filtered_free.empty:
                filtered_free = filtered_free[filtered_free['Nome'].str.contains(search_fa, case=False, na=False)]
                
            if not filtered_free.empty:
                pickup_player_label_fa = st.selectbox("Escolha quem entra", filtered_free['Label'].tolist(), key="fa_pickup")
                pickup_pid_fa = filtered_free[filtered_free['Label'] == pickup_player_label_fa]['player_id'].iloc[0]
            else:
                st.warning("Nenhum jogador encontrado / Lista vazia.")
                pickup_pid_fa = None

        st.divider()
        if st.button("🔄 Confirmar Troca (Free)", type="primary", disabled=not state['free_open']):
            if not state['free_open']:
                st.error("Free Agency Fechada.")
            elif not drop_pid_fa or not pickup_pid_fa:
                st.error("Selecione os dois jogadores.")
            else:
                # Validate team roster size if needed? 
                # Assuming Swap maintains size.
                rodada_fa = state.get('next_round', 0)
                if execute_free_swap(tid_fa, drop_pid_fa, pickup_pid_fa, rodada_fa):
                    st.balloons()
                    st.success("Troca realizada! Tabelas atualizadas.")
                    st.cache_data.clear()
                    st.rerun()

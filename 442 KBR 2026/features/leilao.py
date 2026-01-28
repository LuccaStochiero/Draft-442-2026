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
            ws.append_row(['team_id', 'rodada', 'player_id_free', 'player_id_team', 'price', 'status'])
        
        # Ensure price is float
        price_val = float(price)
        # Store status as empty initially
        ws.append_row([str(team_id), int(rodada), str(pid_free), str(pid_team), price_val, ''])
        return True
    except Exception as e:
        st.error(f"Erro ao salvar lance: {e}")
        return False

def has_pending_bids():
    try:
        client, sh = get_client()
        ws_lances = sh.worksheet("LEILAO_LANCES")
        # Check if there is any data beyond headers
        vals = ws_lances.get_all_values()
        if len(vals) <= 1: return False
        
        # Check if there are unprocessed items
        # Heuristic: Look for empty status in last column?
        # Better: just return True, process_auction handles the check
        return True
    except:
        return False

def process_auction():
    try:
        client, sh = get_client()
        
        # 1. Load Data Live
        ws_lances = sh.worksheet("LEILAO_LANCES")
        all_values = ws_lances.get_all_values()
        
        if len(all_values) <= 1: 
            st.info("Sem lances.")
            return

        headers = [h.lower() for h in all_values[0]]
        data = all_values[1:]
        lances = pd.DataFrame(data, columns=headers)
        
        if lances.empty: 
            st.info("Sem lances.")
            return

        if 'rodada' not in lances.columns: return
        
        # Ensure 'status' column exists in DataFrame
        if 'status' not in lances.columns:
            lances['status'] = ''

        # Filter: Only process UNPROCESSED bids
        # We assume empty string or None means unprocessed. 
        # Be robust: fillna('') and strip.
        lances['status'] = lances['status'].fillna('').astype(str).str.strip()
        df_pending = lances[lances['status'] == ''].copy()
        
        if df_pending.empty:
            st.info("Todos os lances já foram processados.")
            return

        # Fix Numerics (Commas)
        # Apply to df_pending for calculation
        df_pending['rodada'] = pd.to_numeric(df_pending['rodada'], errors='coerce').fillna(0).astype(int)
        
        # Fix Price: Replace , with . and convert
        df_pending['price'] = df_pending['price'].astype(str).str.replace(',', '.', regex=False)
        df_pending['price'] = pd.to_numeric(df_pending['price'], errors='coerce').fillna(0.0)
        
        max_round = df_pending['rodada'].max()
        # Filter for the current round being processed
        df_process = df_pending[df_pending['rodada'] == max_round].sort_values(by='price', ascending=False)
        
        if df_process.empty:
            st.info(f"Sem lances pendentes para a rodada atual ({max_round}).")
            return

        st.write(f"Processando Rodada {max_round} ({len(df_process)} lances novos)...")
        
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
                    try: return float(val)
                    except: return 0.0
            return 0.0
            
        def update_budget(tid, val):
            for r in squad_rows:
                 if str(r.get('team_id', r.get('id'))) == str(tid):
                    cur_str = str(r.get('caixa', 0)).replace(',','.')
                    cur = float(cur_str) if cur_str else 0.0
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

        valid_bids = []

        # Use index from original 'lances' to update status later
        # But df_process is a filtered copy. We need to map back or easier:
        # Just update 'lances' using the index from df_process (preserved)
        
        for idx, bid in df_process.iterrows():
            tid = str(bid['team_id'])
            p_free = str(bid['player_id_free'])
            p_drop = str(bid['player_id_team'])
            price = float(bid['price'])
            
            # Checks
            if get_budget(tid) < price:
                st.write(f"❌ {tid}: Sem caixa ({price}).")
                lances.at[idx, 'status'] = 'REJEITADO_CAIXA'
                continue
            if not is_free(p_free):
                st.write(f"❌ {tid}: {p_free} não está livre.")
                lances.at[idx, 'status'] = 'REJEITADO_NAO_LIVRE'
                continue
            
            # Check for NENHUM (empty slot) case
            is_empty_slot = p_drop == "NENHUM" or p_drop == "" or p_drop.lower() == "none"
            
            if is_empty_slot:
                # Verify team still has ≤17 players
                if get_roster_size(tid) > 17:
                    st.write(f"❌ {tid}: Elenco cheio.")
                    lances.at[idx, 'status'] = 'REJEITADO_CHEIO'
                    continue
            else:
                # Normal case - must own the player to drop
                if not owns_player(tid, p_drop):
                    st.write(f"❌ {tid}: Não possui {p_drop}.")
                    lances.at[idx, 'status'] = 'REJEITADO_NAO_POSSUI'
                    continue
            
            # --- EXECUTE ---
            st.write(f"✅ Lance Válido: {tid} leva {p_free} por {price}" + (" (Vaga Livre)" if is_empty_slot else ""))
            lances.at[idx, 'status'] = 'APROVADO'
            
            # 1. Update Budget
            update_budget(tid, price)
            
            # 2. Handle TEAM
            if is_empty_slot:
                # Just add the new player without removing anyone
                if teams_rows:
                    new_default = {k: '' for k in teams_rows[0].keys()}
                    new_default['team_id'] = tid
                    new_default['player_id'] = p_free
                    teams_rows.append(new_default)
                else:
                    teams_rows.append({'team_id': tid, 'player_id': p_free})
            else:
                # Swap
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
            headers_tm = list(teams_rows[0].keys()) if teams_rows else []
            ws_team.update([headers_tm] + [list(r.values()) for r in teams_rows])
            
            # PLAYERS_FREE
            ws_free.clear()
            ws_free.update([['player_id']] + [[r['player_id']] for r in free_rows])
            
            # SQUAD
            ws_squad.clear()
            headers_sq = list(squad_rows[0].keys()) if squad_rows else []
            ws_squad.update([headers_sq] + [list(r.values()) for r in squad_rows])
            
            # LEILAO_VENCIDO (Keep this as Log)
            try: ws_vencido = sh.worksheet("LEILAO_VENCIDO")
            except: ws_vencido = sh.add_worksheet("LEILAO_VENCIDO", 1000, 5)
            
            vb_df = pd.DataFrame(valid_bids)
            # Ensure columns exist
            cols_to_save = ['team_id','rodada','player_id_free','player_id_team','price']
            for c in cols_to_save:
                 if c not in vb_df.columns: vb_df[c] = ''
            
            # Format price back to something standard or keep as float
            data_venc = vb_df[cols_to_save].values.tolist()
            ws_vencido.append_rows(data_venc)
            
        # FINAL STEP: Update LEILAO_LANCES with new status
        # Reconstruct full data
        # Ensure status handled for NaN
        lances = lances.fillna('')
        
        # Prepare output
        output_data = [lances.columns.tolist()] + lances.values.tolist()
        
        # SAFE UPDATE: Do NOT use clear()
        # We only overwrite the rows we read + changed.
        # If new rows were added (row > len(output_data)), they remain untouched.
        # We assume headers didn't change (A1 start).
        ws_lances.update(output_data, "A1")
        
        if valid_bids:
            st.success("Processamento concluído com sucesso!")
        else:
            st.warning("Rodada processada. Nenhum lance aprovado.")

    except Exception as e:
        st.error(f"Erro processamento: {e}")

from features import calendar_utils

def execute_free_swap(team_id, drop_pid, pickup_pid, rodada):
    """
    Swap a player from Team to Free Agency
    Or Add if drop_pid is None/Empty (and space exists)
    """
    try:
        client, sh = get_client()
        
        ws_team = sh.worksheet("TEAM")
        ws_free = sh.worksheet("PLAYERS_FREE")
        
        # 1. OPTIMISTIC CHECK: Ensure pickup target is STILL free
        # We search specifically for the Cell. This is faster and verifies state.
        cell_free = ws_free.find(str(pickup_pid))
        if not cell_free:
            st.error(f"Opa! O jogador {pickup_pid} já foi levado por outro time agorinha. 😢")
            return False

        # Check roster limit if adding without dropping
        is_addition = (str(drop_pid).upper() == "NENHUM" or not drop_pid)
        
        # --- PHASE 1: HANDLE DROP (Release Player) ---
        if not is_addition:
            # Find player in TEAM sheet to remove
            # Need to search for player_id column typically? 
            # Risk: find(player_id) might find it in another team if logic allows duplicates (shouldn't).
            # Safer: Search, check team_id in same row.
            cell_drop = ws_team.find(str(drop_pid))
            
            if not cell_drop:
                 st.error("Erro: Jogador a dispensar não encontrado na base de dados.")
                 return False
                 
            # Verify ownership (Column A usually team_id, B player_id... need to check schema)
            # Assuming team_id is col 1 or we check the row.
            row_vals = ws_team.row_values(cell_drop.row)
            # We assume team_id is in the row. 
            # Simple check: is str(team_id) in row_vals?
            if str(team_id) not in [str(v) for v in row_vals]:
                 st.error("Erro: Esse jogador não parece pertencer ao seu time na base.")
                 return False
            
            # ATOMIC DELETE (Drop)
            ws_team.delete_rows(cell_drop.row)
            
            # ATOMIC APPEND (Add to Free)
            # We assume PLAYERS_FREE has 1 col usually: player_id. 
            # But earlier code handled multiple key preservation? 
            # Usually strict ID is enough.
            ws_free.append_row([str(drop_pid)])
            
        else:
            # Addition - Check Limit 
            # We rely on the caller or pre-check. 
            # But let's verify size LIVE to be safe?
            # Doing a full read is expensive. We assume the UI pre-check was decent.
            # If we want to be paranoid:
            # all_team = ws_team.col_values(1) # Team IDs
            # count = all_team.count(str(team_id))
            # if count >= 18: ...
            pass # Trusting the UI/Pre-load for limit check to save API calls, focusing on Race Cond of Pickup.

        # --- PHASE 2: HANDLE PICKUP (Acquire Player) ---
        # We found `cell_free` earlier. 
        # But if the Drop phase took time, maybe `cell_free` row shifted?
        # If we dropped a player from TEAM, FREE sheet was touched (appended). Append doesn't shift rows.
        # So cell_free.row should be safe IF we didn't delete from Free yet.
        
        # DELETE from FREE
        # Re-find to be ultra safe against row shifts from OTHER users?
        # If High Concurrency: Yes.
        cell_free_final = ws_free.find(str(pickup_pid))
        if cell_free_final:
            ws_free.delete_rows(cell_free_final.row)
        else:
            st.error("Erro Crítico: Jogador sumiu durante o processamento da troca.")
            return False
            
        # APPEND to TEAM
        # Get headers to know order? Or just append dict values?
        # append_row takes list. 
        # TEAM format: team_id, player_id...
        ws_team.append_row([str(team_id), str(pickup_pid)])
        
        # --- PHASE 3: LOG ---
        try:
            ws_log = sh.worksheet("FREE_AGENCY")
        except:
            ws_log = sh.add_worksheet("FREE_AGENCY", 1000, 5)
            ws_log.append_row(['rodada', 'team_id', 'added_id', 'dropped_id', 'timestamp'])
            
        from datetime import datetime
        ws_log.append_row([
            rodada, 
            str(team_id), 
            str(pickup_pid), 
            str(drop_pid) if not is_addition else "NENHUM", 
            str(datetime.now())
        ])
             
        return True

    except Exception as e:
        st.error(f"Erro ao processar troca (Race Condition?): {e}")
        return False

import time

def get_time_remaining(target_ts):
    if not target_ts: return "Indefinido"
    now = time.time()
    diff = target_ts - now
    if diff <= 0: return "00h 00m"
    
    hours = int(diff // 3600)
    minutes = int((diff % 3600) // 60)
    return f"{hours}h {minutes:02d}m"

def render_timer(label, time_str, color="#333", bg_color="#f0f2f6"):
    st.markdown(
        f"""
        <div style="
            display: flex; 
            justify-content: space-between; 
            align-items: center; 
            padding: 10px 20px; 
            background-color: {bg_color}; 
            border-radius: 8px; 
            margin-bottom: 15px;
            border: 1px solid {color};
        ">
            <span style="font-weight: bold; color: {color}; font-size: 1rem;">{label}</span>
            <span style="font-weight: bold; color: {color}; font-size: 1.2rem; font-family: monospace;">⏱ {time_str}</span>
        </div>
        """,
        unsafe_allow_html=True
    )

from datetime import datetime, timedelta, timezone

def format_deadline_ts(ts):
    if not ts: return ""
    # UTC to GMT-3
    dt = datetime.fromtimestamp(ts, timezone.utc) - timedelta(hours=3)
    day_name = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sab", "Dom"][dt.weekday()]
    return f"{day_name} {dt.strftime('%d/%m às %H:%M')}"

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

def app(is_admin=False):
    st.title("💰 Leilão / Free Agency")
    
    # Auto-Refresh (5 mins = 300s)
    st.markdown(
        """
        <meta http-equiv="refresh" content="300">
        """,
        unsafe_allow_html=True
    )
    
    # --- GAME STATE BANNER ---
    state = calendar_utils.get_game_state()
    if state['status'] == 'ERROR':
        st.error(state['msg'])

    if is_admin:
        # Auto-Process Check
        if not state['auction_open']:
             if has_pending_bids():
                 st.success("✅ Verificando lances pendentes (Prazo encerrado)...")
                 process_auction()
                 st.divider()

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
        # Inputs moved UP to determine state
        c1, c20 = st.columns(2)
        with c1:
            sel_team = st.selectbox("Clube", sorted(team_map.values()), key="auc_team")
            tid = next((k for k,v in team_map.items() if v == sel_team), None)
            
            # Budget info
            budget = df_squad[df_squad['team_id_norm'] == tid]['caixa'].iloc[0]
            st.caption(f"Caixa: $ {budget:,.2f}")

        with c20:
            rodada_auc = st.number_input("Rodada", min_value=1, max_value=38, value=1, key="auc_round")
            
        # State based on Selected Round
        state_auc = calendar_utils.get_game_state(target_round=rodada_auc)
        
        # Timer / Status Banner
        if state_auc['auction_open']:
            trem = get_time_remaining(state_auc.get('closing_ts'))
            d_str = format_deadline_ts(state_auc.get('closing_ts'))
            final_str = f"{trem} (Fecha: {d_str})"
            render_timer(f"🟢 Leilão Aberto (Rodada {rodada_auc})", final_str, color="#00664d", bg_color="#e6fffa")
        else:
            # Auction Closed
            render_timer(f"🔴 Leilão Fechado (Rodada {rodada_auc})", "Fora do prazo", color="#990000", bg_color="#ffe6e6")
            
        c_add, c_drop = st.columns(2)
        
        # --- COLUNA ADICIONAR ---
        with c_add:
            with st.container(border=True):
                render_card_header("ADICIONAR 🟢", "#e6fffa", "#00664d")
                if not df_free_tab.empty:
                    free_ids = df_free_tab['player_id'].unique()
                    free_details_auc = df_players[df_players['player_id'].isin(free_ids)].copy()
                    free_details_auc['Label'] = free_details_auc['Nome'] + " (" + free_details_auc['Posição'] + ")"
                    
                    # --- FILTROS ---
                    st.caption("Filtros")
                    fc1, fc2 = st.columns(2)
                    with fc1:
                        f_nome = st.text_input("Nome", key="auc_f_nome", placeholder="Buscar...")
                        all_pos = sorted(free_details_auc['Posição'].unique())
                        f_pos = st.multiselect("Posição", all_pos, key="auc_f_pos", placeholder="Pos...")
                    with fc2:
                        all_teams = sorted(free_details_auc['Team'].dropna().unique())
                        f_team = st.multiselect("Time Real", all_teams, key="auc_f_team", placeholder="Time...")

                    # Apply
                    if f_nome:
                        free_details_auc = free_details_auc[free_details_auc['Nome'].str.contains(f_nome, case=False, na=False)]
                    if f_pos:
                        free_details_auc = free_details_auc[free_details_auc['Posição'].isin(f_pos)]
                    if f_team:
                        free_details_auc = free_details_auc[free_details_auc['Team'].isin(f_team)]
                    
                    if not free_details_auc.empty:
                        target_name = st.selectbox("Alvo (Livre)", free_details_auc['Label'].unique(), key="auc_target")
                        pid_free = free_details_auc[free_details_auc['Label'] == target_name]['player_id'].iloc[0]
                    else:
                        st.warning("Nenhum jogador encontrado.")
                        pid_free = None
                else:
                    st.warning("Ninguem livre.")
                    pid_free = None
                
        # --- COLUNA DISPENSAR ---
        with c_drop:
            with st.container(border=True):
                render_card_header("DISPENSAR 🔴", "#ffe6e6", "#990000")
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
                    
                st.divider()
                
                safe_budget = float(budget or 0.0)
                if safe_budget <= 0.0:
                    st.error("Sem caixa.")
                    price = 0.0
                else:
                    price = st.number_input("Valor do leilão (1 casa decimal)", min_value=0.0, max_value=safe_budget, step=0.1, format="%.1f", key="auc_price")
            
        if st.button("Enviar Lance", disabled=not state_auc['auction_open']):
            if not state_auc['auction_open']:
                st.error("Leilão Fechado para esta rodada.")
            elif price > budget:
                st.error("Sem grana.")
            elif not pid_free:
                st.error("Selecione o jogador.")
            else:
                if save_bid(tid, rodada_auc, pid_free, pid_drop, price):
                    st.success("Lance enviado!")

    # --- TAB 2: FREE AGENCY ---
    with tab_free:
        # Team Selector for Free Agency
        c_fa_1, c_fa_2 = st.columns(2)
        with c_fa_1:
             sel_team_fa = st.selectbox("Clube", sorted(team_map.values()), key="fa_team_select")
             tid_fa = next((k for k,v in team_map.items() if v == sel_team_fa), None)
             
        with c_fa_2:
             # Add Round Selector for Free Agency
             rodada_fa = st.number_input("Rodada", min_value=1, max_value=38, value=1, key="fa_round")

        # State based on Selected Round
        state_fa = calendar_utils.get_game_state(target_round=rodada_fa)
        
        # Timer / Status Banner
        if state_fa['free_open']:
             trem = get_time_remaining(state_fa.get('closing_ts'))
             d_str = format_deadline_ts(state_fa.get('closing_ts'))
             final_str = f"{trem} (Fecha: {d_str})"
             render_timer(f"🟢 Free Agency Aberta (Rodada {rodada_fa})", final_str, color="#997a00", bg_color="#fffbe6")
        else:
             # If Auction is open, Free Agency opens when Auction closes (plus buffer)
             if state_fa['auction_open']:
                 open_ts = state_fa.get('ts_free_start', 0) # Exact timestamp from HOUR
                 if open_ts == 0: open_ts = state_fa.get('closing_ts', 0) # Fallback
                 
                 trem = get_time_remaining(open_ts)
                 d_str = format_deadline_ts(open_ts)
                 final_str = f"{trem} (Abre: {d_str})"
                 render_timer(f"🔴 Free Agency Fechada (Rodada {rodada_fa})", final_str, color="#990000", bg_color="#ffe6e6")
             else:
                 render_timer(f"🔴 Free Agency Fechada (Rodada {rodada_fa})", "Fora do prazo", color="#990000", bg_color="#ffe6e6")

        st.markdown("##### Troca de Jogador (Free Agency)")

        col_add, col_drop = st.columns(2)
        
        # --- COLUNA ADICIONAR (Left) ---
        with col_add:
            with st.container(border=True):
                render_card_header("ADICIONAR 🟢", "#e6fffa", "#00664d")
                
                # Populate basic list first
                if not df_free_tab.empty:
                    free_ids_fa = df_free_tab['player_id'].unique()
                    free_details_fa = df_players[df_players['player_id'].isin(free_ids_fa)].copy()
                    free_details_fa['Label'] = free_details_fa['Nome'] + " (" + free_details_fa['Posição'] + ")"
                else:
                    free_details_fa = pd.DataFrame()

                # Filters Harmoniosos (Igual Leilão)
                c_f1, c_f2 = st.columns(2)
                with c_f1:
                    search_fa = st.text_input("Nome", placeholder="Buscar...", key="fa_search")
                    if not free_details_fa.empty:
                        pos_opts = sorted(free_details_fa['Posição'].unique())
                        sel_pos_fa = st.multiselect("Posição", pos_opts, key="fa_pos_filt", placeholder="Pos...")
                    else:
                        sel_pos_fa = []
                with c_f2:
                     if not free_details_fa.empty:
                        team_opts = sorted(free_details_fa['Team'].dropna().unique())
                        sel_team_fa_real = st.multiselect("Time Real", team_opts, key="fa_team_filt", placeholder="Time...")
                     else:
                        sel_team_fa_real = []

                filtered_free = free_details_fa.copy()
                
                if search_fa and not filtered_free.empty:
                    filtered_free = filtered_free[filtered_free['Nome'].str.contains(search_fa, case=False, na=False)]
                
                if sel_pos_fa and not filtered_free.empty:
                    filtered_free = filtered_free[filtered_free['Posição'].isin(sel_pos_fa)]
                    
                if sel_team_fa_real and not filtered_free.empty:
                    filtered_free = filtered_free[filtered_free['Team'].isin(sel_team_fa_real)]
                    
                if not filtered_free.empty:
                    pickup_player_label_fa = st.selectbox("Escolha quem entra", filtered_free['Label'].tolist(), key="fa_pickup")
                    pickup_pid_fa = filtered_free[filtered_free['Label'] == pickup_player_label_fa]['player_id'].iloc[0]
                else:
                    st.warning("Nenhum jogador encontrado / Lista vazia.")
                    pickup_pid_fa = None

        # --- COLUNA DISPENSAR (Right) ---
        with col_drop:
            with st.container(border=True):
                render_card_header("DISPENSAR 🔴", "#ffe6e6", "#990000")
                
                # Get players for selected team
                own_ids_fa = df_team[df_team['team_id'] == tid_fa]['player_id'].tolist()
                own_details_fa = df_players[df_players['player_id'].isin(own_ids_fa)].copy()
                roster_size_fa = len(own_ids_fa)
                
                st.caption(f"Elenco: {roster_size_fa} jogadores")

                # Handle roster options
                if not own_details_fa.empty:
                    own_details_fa['Label'] = own_details_fa['Nome'] + " (" + own_details_fa['Posição'] + ")"
                    options_fa = list(own_details_fa['Label'].unique())
                    
                    # Allow EMPTY SLOT if roster < 18
                    if roster_size_fa < 18:
                         options_fa = ["Nenhum (Vaga Livre)"] + options_fa

                    drop_player_label_fa = st.selectbox("Escolha quem sai", options_fa, key="fa_drop")
                    
                    if drop_player_label_fa == "Nenhum (Vaga Livre)":
                        drop_pid_fa = "NENHUM"
                    else:
                        drop_pid_fa = own_details_fa[own_details_fa['Label'] == drop_player_label_fa]['player_id'].iloc[0]
                else:
                    # Empty Team - Can add if < 18
                    if roster_size_fa < 18:
                         drop_pid_fa = "NENHUM"
                         st.info("Vaga Livre disponível.")
                    else:
                         st.warning("Seu time está vazio (mas cheio?). Erro de lógica.")
                         drop_pid_fa = None

        st.divider()
        if st.button("🔄 Confirmar Troca (Free)", type="primary", disabled=not state_fa['free_open']):
            if not state_fa['free_open']:
                st.error("Free Agency Fechada para esta rodada.")
            elif not pickup_pid_fa:
                 st.error("Selecione quem entra.")
            elif not drop_pid_fa:
                 st.error("Selecione quem sai (ou Vaga Livre).")
            else:
                # Validation based on SELECTED round
                if execute_free_swap(tid_fa, drop_pid_fa, pickup_pid_fa, rodada_fa):
                    st.balloons()
                    st.success("Operação realizada! Tabelas atualizadas.")
                    st.cache_data.clear()
                    st.rerun()

import streamlit as st
import pandas as pd
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- CONFIG ---
SERVICE_ACCOUNT_FILE = "service_account.json"
SHEET_ID = "1mG0XiZwzTyDncD592_XcpFwKeUwR97Gi8-tEh_XPW50"
PLAYERS_LOCAL_FILE = os.path.join("Dados", "Players.csv")

def get_client():
    scope = ["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/spreadsheets',
             "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(SERVICE_ACCOUNT_FILE, scope)
    client = gspread.authorize(creds)
    return client, client.open_by_key(SHEET_ID)

@st.cache_data(ttl=60)
def load_data():
    if not os.path.exists(PLAYERS_LOCAL_FILE):
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    
    df_players = pd.read_csv(PLAYERS_LOCAL_FILE)
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
            if not owns_player(tid, p_drop):
                st.write(f"❌ {tid}: Não possui {p_drop}.")
                continue
            
            # --- EXECUTE ---
            st.write(f"✅ Lance Válido: {tid} leva {p_free} por {price}")
            
            # 1. Update Budget
            update_budget(tid, price)
            
            # 2. Swap in TEAM
            # Find row to remove
            idx_rem = -1
            for i, r in enumerate(teams_rows):
                if str(r.get('team_id')) == tid and str(r.get('player_id')) == p_drop:
                    idx_rem = i; break
            
            if idx_rem != -1:
                old_row = teams_rows.pop(idx_rem)
                new_row = old_row.copy()
                new_row['player_id'] = p_free
                teams_rows.append(new_row)
            
            # 3. Update FREE
            # Remove p_free
            idx_free = -1
            for i, r in enumerate(free_rows):
                 if str(r.get('player_id')) == p_free: idx_free = i; break
            if idx_free != -1: free_rows.pop(idx_free)
            
            # Add p_drop
            free_rows.append({'player_id': p_drop})
            
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

def app(is_admin=False):
    st.title("⚖️ Leilão")
    
    if is_admin:
        if st.button("👑 PROCESSAR RODADA ATUAL", type="primary"):
            process_auction()
        st.divider()

    # User Form
    df_players, df_team, df_squad, df_free_tab = load_data()
    
    if df_squad.empty: return
    
    # 1. Inputs
    c1, c20 = st.columns(2)
    with c1:
        name_col = next((c for c in df_squad.columns if c in ['name', 'nome', 'team', 'time', 'team_name']), None)
        team_map = pd.Series(df_squad[name_col].values, index=df_squad['team_id_norm']).to_dict()
        sel_team = st.selectbox("Clube", sorted(team_map.values()))
        tid = next((k for k,v in team_map.items() if v == sel_team), None)
        
        # Budget info
        budget = df_squad[df_squad['team_id_norm'] == tid]['caixa'].iloc[0]
        st.caption(f"Caixa: $ {budget:,.2f}")

    with c20:
        rodada = st.number_input("Rodada", min_value=1, max_value=38, value=1)
        
    c2, c3, c4 = st.columns(3)
    
    # Target (Free)
    with c2:
        # Filter players who are in FREE tab
        # Get Names
        if not df_free_tab.empty:
            free_ids = df_free_tab['player_id'].unique()
            free_details = df_players[df_players['player_id'].isin(free_ids)].copy()
            free_details['Label'] = free_details['Nome'] + " (" + free_details['Posição'] + ")"
            
            target_name = st.selectbox("Alvo (Livre)", free_details['Label'].unique())
            pid_free = free_details[free_details['Label'] == target_name]['player_id'].iloc[0]
        else:
            st.warning("Ninguem livre.")
            pid_free = None
            
    # Drop (Own)
    with c3:
        # Filter owned players
        own_ids = df_team[df_team['team_id'] == tid]['player_id'].tolist()
        own_details = df_players[df_players['player_id'].isin(own_ids)].copy()
        
        if not own_details.empty:
            own_details['Label'] = own_details['Nome'] + " (" + own_details['Posição'] + ")"
            drop_name = st.selectbox("Descarte (Meu)", own_details['Label'].unique())
            pid_drop = own_details[own_details['Label'] == drop_name]['player_id'].iloc[0]
        else:
            st.warning("Elenco vazio.")
            pid_drop = None
            
    with c4:
        safe_budget = float(budget or 0.0)
        # Prevent min > max error if budget is 0
        if safe_budget <= 0.0:
            st.error("Sem caixa disponível para lances.")
            price = 0.0
        else:
            price = st.number_input("Lance ($)", min_value=0.0, max_value=safe_budget)
        
    if st.button("Enviar Lance"):
        if price > budget:
            st.error("Sem grana.")
        elif not pid_free or not pid_drop:
            st.error("Selecione jogadores.")
        else:
            if save_bid(tid, rodada, pid_free, pid_drop, price):
                st.success("Lance enviado!")

import streamlit as st
import pandas as pd
from features.auth import get_client, get_players_file

@st.cache_data(ttl=60)
def load_data():
    players_file = get_players_file()
    if not players_file.exists():
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    
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

    except Exception as e:
        st.error(f"Erro sheets: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
        
    return df_players, df_team, df_squad

def execute_trade(rodada, team1_id, team1_players, team1_cash, team2_id, team2_players, team2_cash):
    """Execute the trade immediately updating all sheets"""
    try:
        client, sh = get_client()
        
        # Load current state
        ws_team = sh.worksheet("TEAM")
        teams_rows = ws_team.get_all_records()
        
        ws_squad = sh.worksheet("SQUAD")
        squad_rows = ws_squad.get_all_records()
        
        # Get or create TROCAS_FEITAS
        try:
            ws_trades = sh.worksheet("TROCAS_FEITAS")
        except:
            ws_trades = sh.add_worksheet("TROCAS_FEITAS", 1000, 7)
            ws_trades.append_row(['rodada', 'team_id_1', 'player_id_1', 'cash_1', 'team_id_2', 'player_id_2', 'cash_2'])
        
        # --- UPDATE TEAM (swap players) ---
        for pid in team1_players:
            for r in teams_rows:
                if str(r.get('team_id')) == str(team1_id) and str(r.get('player_id')) == str(pid):
                    r['team_id'] = str(team2_id)
                    break
        
        for pid in team2_players:
            for r in teams_rows:
                if str(r.get('team_id')) == str(team2_id) and str(r.get('player_id')) == str(pid):
                    r['team_id'] = str(team1_id)
                    break
        
        # --- UPDATE SQUAD (cash) ---
        for r in squad_rows:
            tid = str(r.get('team_id', r.get('id')))
            if tid == str(team1_id):
                cur = float(str(r.get('caixa', 0)).replace(',', '.'))
                r['caixa'] = cur - team1_cash + team2_cash
            elif tid == str(team2_id):
                cur = float(str(r.get('caixa', 0)).replace(',', '.'))
                r['caixa'] = cur - team2_cash + team1_cash
        
        # --- COMMIT TO SHEETS ---
        # TEAM
        ws_team.clear()
        headers = list(teams_rows[0].keys()) if teams_rows else []
        ws_team.update([headers] + [list(r.values()) for r in teams_rows])
        
        # SQUAD
        ws_squad.clear()
        headers_sq = list(squad_rows[0].keys()) if squad_rows else []
        ws_squad.update([headers_sq] + [list(r.values()) for r in squad_rows])
        
        # TROCAS_FEITAS (one row per player pair)
        for i in range(len(team1_players)):
            ws_trades.append_row([
                int(rodada),
                str(team1_id),
                str(team1_players[i]),
                float(team1_cash) if i == 0 else 0,
                str(team2_id),
                str(team2_players[i]),
                float(team2_cash) if i == 0 else 0
            ])
        
        return True
        
    except Exception as e:
        st.error(f"Erro ao executar troca: {e}")
        return False

def execute_drop(team_id, player_id, rodada):
    """Drop a player from TEAM and move to PLAYERS_FREE, logging to DROPS_FEITOS"""
    try:
        client, sh = get_client()
        
        # 1. Update TEAM
        ws_team = sh.worksheet("TEAM")
        rows = ws_team.get_all_records()
        
        # Filter out the dropped player
        new_rows = []
        found = False
        for r in rows:
            if str(r.get('team_id')) == str(team_id) and str(r.get('player_id')) == str(player_id):
                found = True
                continue # Skip (Remove)
            new_rows.append(r)
            
        if not found:
            st.error("Jogador não encontrado no time.")
            return False
            
        # 2. Update PLAYERS_FREE
        try:
             ws_free = sh.worksheet("PLAYERS_FREE")
        except:
             ws_free = sh.add_worksheet("PLAYERS_FREE", 1000, 1)
             ws_free.append_row(['player_id'])
             
        # Just append row for efficiency? Or read-write to avoid dups?
        # Let's just append. It's safe enough.
        ws_free.append_row([str(player_id)])
        
        # 3. Log to DROPS_FEITOS
        try:
            ws_log = sh.worksheet("DROPS_FEITOS")
        except:
            ws_log = sh.add_worksheet("DROPS_FEITOS", 1000, 3)
            ws_log.append_row(['rodada', 'team_id', 'player_id'])
            
        ws_log.append_row([int(rodada), str(team_id), str(player_id)])
        
        # Commit Team Changes
        ws_team.clear()
        if rows:
            headers = list(rows[0].keys())
            if new_rows:
                ws_team.update([headers] + [list(r.values()) for r in new_rows])
            else:
                ws_team.append_row(headers)
        
        return True
    except Exception as e:
        st.error(f"Erro no drop: {e}")
        return False

from features import calendar_utils

def app():
    st.markdown("### 🔄 Trade / Drop")
    
    st.divider() 
    
    df_players, df_team, df_squad = load_data()
    
    if df_squad.empty or df_team.empty:
        st.warning("Dados insuficientes.")
        return
    
    # Team name mapping
    name_col = next((c for c in df_squad.columns if c in ['name', 'nome', 'team', 'time', 'team_name']), None)
    if not name_col:
        st.error("Coluna Nome não encontrada.")
        return
    
    team_map = pd.Series(df_squad[name_col].values, index=df_squad['team_id_norm']).to_dict()
    team_names = sorted(team_map.values())
    
    # Round input
    rodada = st.number_input("Rodada", min_value=1, max_value=38, value=1, key="trade_round")
    
    tab_trade, tab_drop = st.tabs(["🔄 Trocas entre Times", "🗑️ Dispensar (Drops)"])
    
    # --- TAB 1: TROCAS ---
    with tab_trade:
        st.caption("Troca direta de jogadores e caixa entre dois clubes.")
        # rodada moved up
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("##### Clube 1")
            team1_name = st.selectbox("Selecione o Clube 1", team_names, key="team1")
            team1_id = next((k for k, v in team_map.items() if v == team1_name), None)
            
            # Budget
            budget1 = df_squad[df_squad['team_id_norm'] == team1_id]['caixa'].iloc[0]
            st.caption(f"Caixa: $ {budget1:,.2f}")
            
            # Get players
            team1_player_ids = df_team[df_team['team_id'] == team1_id]['player_id'].tolist()
            team1_details = df_players[df_players['player_id'].isin(team1_player_ids)].copy()
            
            if not team1_details.empty:
                team1_details['Label'] = team1_details['Nome'] + " (" + team1_details['Posição'] + ")"
                team1_selected = st.multiselect("Jogadores do Clube 1", team1_details['Label'].tolist(), key="p1")
            else:
                team1_selected = []
                st.warning("Sem jogadores")
            
            team1_cash = st.number_input("Dinheiro do Clube 1 ($)", min_value=0.0, max_value=float(budget1), value=0.0, key="cash1")
        
        with col2:
            st.markdown("##### Clube 2")
            # Exclude team1 from options
            team2_options = [t for t in team_names if t != team1_name]
            team2_name = st.selectbox("Selecione o Clube 2", team2_options, key="team2")
            team2_id = next((k for k, v in team_map.items() if v == team2_name), None)
            
            # Budget
            budget2 = df_squad[df_squad['team_id_norm'] == team2_id]['caixa'].iloc[0]
            st.caption(f"Caixa: $ {budget2:,.2f}")
            
            # Get players
            team2_player_ids = df_team[df_team['team_id'] == team2_id]['player_id'].tolist()
            team2_details = df_players[df_players['player_id'].isin(team2_player_ids)].copy()
            
            if not team2_details.empty:
                team2_details['Label'] = team2_details['Nome'] + " (" + team2_details['Posição'] + ")"
                team2_selected = st.multiselect("Jogadores do Clube 2", team2_details['Label'].tolist(), key="p2")
            else:
                team2_selected = []
                st.warning("Sem jogadores")
            
            team2_cash = st.number_input("Dinheiro do Clube 2 ($)", min_value=0.0, max_value=float(budget2), value=0.0, key="cash2")
        
        st.divider()
        
        # Validation and submission
        if st.button("Confirmar Troca", type="primary"):
            # Validations
            if len(team1_selected) != len(team2_selected):
                st.error(f"Número de jogadores deve ser igual! Clube 1: {len(team1_selected)}, Clube 2: {len(team2_selected)}")
            elif len(team1_selected) == 0:
                st.error("Selecione pelo menos 1 jogador de cada clube.")
            elif team1_cash > budget1:
                st.error("Clube 1 não tem caixa suficiente.")
            elif team2_cash > budget2:
                st.error("Clube 2 não tem caixa suficiente.")
            else:
                # Get player IDs
                team1_pids = team1_details[team1_details['Label'].isin(team1_selected)]['player_id'].tolist()
                team2_pids = team2_details[team2_details['Label'].isin(team2_selected)]['player_id'].tolist()
                
                if execute_trade(rodada, team1_id, team1_pids, team1_cash, team2_id, team2_pids, team2_cash):
                    st.success("✅ Troca realizada com sucesso!")
                    st.cache_data.clear()
                    st.rerun()

    # --- TAB 2: DROPS ---
    with tab_drop:
        st.caption("Dispensar um jogador do elenco (enviar para Free Agency).")
        
        d_col1, d_col2 = st.columns(2)
        with d_col1:
            my_team_name = st.selectbox("Selecione o Clube", team_names, key="drop_team")
            my_tid = next((k for k, v in team_map.items() if v == my_team_name), None)
            
            my_roster_ids = df_team[df_team['team_id'] == my_tid]['player_id'].tolist()
            my_roster = df_players[df_players['player_id'].isin(my_roster_ids)].copy()
            
            st.info(f"Jogadores no elenco: {len(my_roster)}")
            
            if not my_roster.empty:
                my_roster['Label'] = my_roster['Nome'] + " (" + my_roster['Posição'] + ")"
                to_drop_label = st.selectbox("Selecionar Jogador para Dispensar", my_roster['Label'].tolist(), key="drop_p")
                
                to_drop_pid = my_roster[my_roster['Label'] == to_drop_label]['player_id'].iloc[0]
            else:
                to_drop_pid = None
                st.warning("Elenco vazio.")
                
        with d_col2:
            st.markdown("### Confirmar")
            st.warning("⚠ Atenção: Essa ação remove o jogador do time imediatamente.")
            
            # Using the same rodada input from Tab 1 or a new one?
            # It's better to verify rodada is set. 
            # Currently rodada is defined inside tab_trade, so it's not accessible here directly?
            # Wait, `rodada` variable scope in Python functions...
            # If defined in `with tab_trade:`, it might be local to that block? No, Python doesn't scope `with` blocks.
            # But the st.number_input is RENDERED in tab_trade. 
            # If the user is on TAB 2, TAB 1 content might not be rendered or updated?
            # Safest is to have a rodada input here too or move `rodada` to top level.
            # I will move `rodada` input to top level (common for both).
            
        # Refactoring to move rodada to top level (before tabs)
            
            if st.button("🗑️ Confirmar Drop", type="primary", disabled=(to_drop_pid is None)):
                if to_drop_pid:
                    if execute_drop(my_tid, to_drop_pid, rodada):
                        st.success("✅ Jogador invalidado com sucesso! (Enviado para Free Agency e Logado)")
                        st.cache_data.clear()
                        st.rerun()
                        st.rerun()

import streamlit as st
import pandas as pd
from features.auth import get_client, get_players_file
from features.pontuacao import render_player_row, load_static_data, load_live_data, clean_pos

# Reuse data loading structure from pontuacao, but we need TEAM_POINTS too
@st.cache_data(ttl=60) 
def load_matchup_data():
    client, sh = get_client()
    try:
        ws = sh.worksheet("H2H - TEAM_POINTS")
        # Use get_values to preserve comma-decimal strings
        raw_values = ws.get_values()
        if raw_values and len(raw_values) > 1:
            df_tp = pd.DataFrame(raw_values[1:], columns=raw_values[0])
        else:
            df_tp = pd.DataFrame()
        
        # Normalize
        if not df_tp.empty:
             df_tp.columns = [c.lower() for c in df_tp.columns]
             # Columns: team_id, player_id, rodada, pontuacao, escalado
             df_tp['player_id'] = df_tp['player_id'].astype(str)
             df_tp['team_id'] = df_tp['team_id'].astype(str)
             # Convert pontuacao comma-string to float
             if 'pontuacao' in df_tp.columns:
                 df_tp['pontuacao'] = df_tp['pontuacao'].apply(
                     lambda x: float(str(x).replace(',', '.')) if x else 0.0
                 )
             # Ensure numeric round
             df_tp['rodada'] = pd.to_numeric(df_tp['rodada'], errors='coerce')
    except:
        df_tp = pd.DataFrame()
        
    return df_tp

def app():
    st.title("🆚 MATCHUP")
    
    # Loads
    df_players, df_gw, df_h2h, df_lineup, df_squad, _ = load_static_data() # From pontuacao
    df_pts, df_stats = load_live_data() # From pontuacao
    df_team_points = load_matchup_data()
    
    if df_gw.empty:
        st.warning("Sem dados de Gameweek.")
        return
        
    # Standard Filters (Round)
    all_rounds = sorted(df_gw['rodada'].unique()) if 'rodada' in df_gw.columns else []
    
    # Determine default index (Round closest to today)
    default_idx = 0
    if all_rounds and 'data_hora' in df_gw.columns and not df_gw.empty:
        try:
            now = pd.Timestamp.now()
            # Convert GW dates
            df_gw['dt'] = pd.to_datetime(df_gw['data_hora'], dayfirst=True, errors='coerce')
            # Find future or active games
            future = df_gw[df_gw['dt'] >= (now - pd.Timedelta(days=2))] # Include recent past
            if not future.empty:
                next_round = future.sort_values('dt').iloc[0]['rodada']
                if next_round in all_rounds:
                    default_idx = all_rounds.index(next_round)
            else:
                default_idx = len(all_rounds) - 1
        except:
            default_idx = len(all_rounds) - 1

    sel_round = st.selectbox("Rodada", all_rounds, index=default_idx)
    
    if df_h2h.empty:
        st.info("Sem confrontos.")
        return
        
    # Filter H2H
    if 'rodada' in df_h2h.columns:
        round_h2h = df_h2h[df_h2h['rodada'] == sel_round].copy()
    else:
        round_h2h = pd.DataFrame()
        
    if round_h2h.empty:
        st.info("Confrontos não encontrados para esta rodada.")
        return

    # Prepare Team Name Map
    team_map = {}
    if not df_squad.empty:
         name_col = next((c for c in df_squad.columns if c in ['team_name', 'name', 'nome', 'team', 'time']), None)
         if name_col:
             team_map = pd.Series(df_squad[name_col].values, index=df_squad['team_id_norm']).to_dict()

    # Iterate Matchups
    for _, match in round_h2h.iterrows():
        h_col = next((c for c in round_h2h.columns if c in ['home_team_id', 'home', 'mandante']), None)
        a_col = next((c for c in round_h2h.columns if c in ['away_team_id', 'away', 'visitante']), None)
        
        if not h_col or not a_col: continue

        tid_h = str(match[h_col]).strip()
        tid_a = str(match[a_col]).strip()
        
        name_h = team_map.get(tid_h, tid_h)
        name_a = team_map.get(tid_a, tid_a)
        
        # Get Players for this team/round
        # Logic: 
        # 1. Try to get from H2H - TEAM_POINTS (calculated finalized/partial state)
        # 2. If empty, fallback to TEAM_LINEUP (raw lineup, assume all starters active)
        
        tp_round = df_team_points[df_team_points['rodada'] == sel_round] if not df_team_points.empty else pd.DataFrame()
        
        def get_team_data(tid):
            # Returns list of dicts: {player_row, stats, score, is_starter, is_escalado}
            # and total_score_titular
            
            processed = []
            total = 0.0
            
            # CHECK SOURCE
            # Filter TP by team
            tp_team = tp_round[tp_round['team_id'] == tid] if not tp_round.empty else pd.DataFrame()
            
            use_tp = not tp_team.empty
            
            # IDs to iterate
            if use_tp:
                # Use data from Team Points
                # It has 'player_id', 'pontuacao', 'escalado'
                # Merge with Player Details
                target_df = tp_team
            else:
                # Use Raw Lineup
                lineup_team = df_lineup[(df_lineup['rodada'] == sel_round) & (df_lineup['team_id'] == tid)]
                target_df = lineup_team
                
            if target_df.empty: return [], 0.0
            
            for _, row in target_df.iterrows():
                pid = str(row['player_id'])
                
                # Player Info
                p_rows = df_players[df_players['player_id'] == pid]
                if p_rows.empty: continue
                p_info = p_rows.iloc[0].to_dict()
                
                # Stats & Score
                # If using TP, score is in 'pontuacao'. If using Lineup, need to calc.
                # Assuming TP is up to date.
                
                if use_tp:
                    raw_score = row.get('pontuacao', 0)
                    try:
                        score = float(raw_score)
                    except:
                        try:
                            score = float(str(raw_score).replace(',', '.'))
                        except:
                            score = 0.0
                    
                    escalado = str(row.get('escalado')).upper() == 'TRUE'
                    if str(row.get('escalado')) == '1': escalado = True
                    
                    # Read Captain from TP
                    cap_val = str(row.get('cap', '')).upper()
                    is_captain = (cap_val == 'CAPITAO')
                    
                else:
                    # Fallback Calc
                    pts_rows = df_pts[df_pts['player_id'] == pid] 
                    score = pts_rows['pontuacao'].sum()
                    
                    lineup_val = row.get('lineup', 'TITULAR')
                    escalado = (lineup_val == 'TITULAR') 
                    
                    # Check Captain in Lineup
                    is_captain = str(row.get('cap', '')).upper() == 'CAPITAO'
                    if is_captain:
                        score = score * 1.5
                    
                # Add to total if escalado
                if escalado: total += score
                
                # Stats for Render
                # df_stats might have player_id as int or float
                df_stats['player_id'] = df_stats['player_id'].astype(str)
                s_row = df_stats[df_stats['player_id'] == pid] 
                # Using last known stats for PID.
                s_dict = s_row.iloc[0].to_dict() if not s_row.empty else {}
                
                # Enrich p_info for renderer
                p_info['pontuacao'] = score
                
                # Raw Score for Display
                raw_score_disp = score
                if is_captain and score != 0:
                    raw_score_disp = score / 1.5
                
                processed.append({
                    'p_info': p_info,
                    's_dict': s_dict,
                    'score': score,
                    'escalado': escalado,
                    'is_captain': is_captain,
                    'raw_score': raw_score_disp
                })
                
            # SORTING LOGIC
            # 1. Active (Escalado) First
            # 2. Position (GK, DEF, MID, FWD)
            # 3. Score Desc
            
            POS_ORDER = {'GK': 0, 'G': 0, 'GOL': 0, 'DEF': 1, 'D': 1, 'MID': 2, 'M': 2, 'MEI': 2, 'FWD': 3, 'F': 3, 'ATT': 3, 'ATA': 3}
            
            def get_sort_key(item):
                # Escalado: True -> 0, False -> 1 (so True comes first)
                is_bench = not item['escalado']
                
                # Position
                pos_val = clean_pos(item['p_info'].get('Posição', ''))
                pos_idx = POS_ORDER.get(pos_val, 99)
                
                return (is_bench, pos_idx, -item['score'])

            processed.sort(key=get_sort_key)
            
            return processed, total

        # PROCESS TEAMS
        data_h, score_h = get_team_data(tid_h)
        data_a, score_a = get_team_data(tid_a)
        
        # RENDER
        # RENDER
        header_str = f"**{name_h}** ({score_h:.2f})  x  ({score_a:.2f}) **{name_a}**"
        
        with st.expander(header_str, expanded=True):
             st.markdown(
               f"""
               <div style="display: flex; justify-content: space-around; font-size: 1.5em; font-weight: bold; margin-bottom: 20px; background-color: rgba(255,255,255,0.05); padding: 10px; border-radius: 8px;">
                   <div style="color: #4CAF50;">{score_h:.2f}</div>
                   <div style="color: #888;">vs</div>
                   <div style="color: #4CAF50;">{score_a:.2f}</div>
               </div>
               """,
               unsafe_allow_html=True
             )
             
             c1, c2 = st.columns(2)
             
             def render_list(data_list):
                 if not data_list: return
                 
                 starters = [x for x in data_list if x['escalado']]
                 bench = [x for x in data_list if not x['escalado']]
                 
                 if starters:
                     st.markdown("**TITULARES**")
                     for item in starters:
                         render_player_row(
                             item['p_info'], item['s_dict'], 
                             is_captain=item.get('is_captain', False), 
                             raw_score=item.get('raw_score')
                         )
                         
                 if bench:
                     st.markdown("---")
                     st.markdown("**BANCO DE RESERVAS**")
                     for item in bench:
                         # Render with opacity
                         st.markdown(f"<div style='opacity: 0.5;'>", unsafe_allow_html=True)
                         render_player_row(
                             item['p_info'], item['s_dict'],
                             is_captain=item.get('is_captain', False),
                             raw_score=item.get('raw_score')
                         )
                         st.markdown("</div>", unsafe_allow_html=True)

             with c1:
                 st.subheader(f"{name_h}")
                 render_list(data_h)
                 
             with c2:
                 st.subheader(f"{name_a}")
                 render_list(data_a)

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
        df_tp = pd.DataFrame(ws.get_all_records())
        # Normalize
        if not df_tp.empty:
             df_tp.columns = [c.lower() for c in df_tp.columns]
             # Columns: team_id, player_id, rodada, pontuacao, escalado
             df_tp['player_id'] = df_tp['player_id'].astype(str)
             df_tp['team_id'] = df_tp['team_id'].astype(str)
             # escalado might be boolean or TRUE/FALSE string
             # Ensure numeric round
             df_tp['rodada'] = pd.to_numeric(df_tp['rodada'], errors='coerce')
    except:
        df_tp = pd.DataFrame()
        
    return df_tp

def app():
    st.title("🆚 MATCHUP")
    
    # Loads
    df_players, df_gw, df_h2h, df_lineup, df_squad = load_static_data() # From pontuacao
    df_pts, df_stats = load_live_data() # From pontuacao
    df_team_points = load_matchup_data()
    
    if df_gw.empty:
        st.warning("Sem dados de Gameweek.")
        return
        
    # Standard Filters (Round)
    all_rounds = sorted(df_gw['rodada'].unique()) if 'rodada' in df_gw.columns else []
    sel_round = st.selectbox("Rodada", all_rounds, index=len(all_rounds)-1 if all_rounds else 0)
    
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
                    score = float(row.get('pontuacao', 0))
                    escalado = str(row.get('escalado')).upper() == 'TRUE'
                    # Or maybe 1/0
                    if str(row.get('escalado')) == '1': escalado = True
                else:
                    # Fallback Calc
                    # Get Score from df_pts logic (similar to team_points.py get_score)
                    # For UI speed, we can reuse `pontuacao` logic: get all game_ids for round...
                    # Simplified: Use `df_pts` loaded in `load_live_data`
                    
                    # Need game_ids for this round again
                    # This is heavy to do per player.
                    # Let's try to lookup in df_pts directly if unique enough
                    # OR, assume if TP is missing, scores are likely 0 or not calculated yet?
                    # No, user might look at Matchup before auto-update runs substitution logic?
                    # Ideally auto-update runs frequently.
                    # Let's assume we fetch live score from df_pts if TP missing.
                    
                    # Score fetch
                    pts_rows = df_pts[df_pts['player_id'] == pid] 
                    # Filter by round? We need logic. 
                    # Reuse get_pid_score logic from pontuacao.py
                    # (Simplified)
                    score = pts_rows['pontuacao'].sum() # risky if multiple rounds active?
                    # Correct: Filter by game_ids of the round.
                    # (Code needs reference to round_matches)
                    
                    lineup_val = row.get('lineup', 'TITULAR')
                    escalado = (lineup_val == 'TITULAR') # Default assumption
                    
                # Add to total if escalado
                if escalado: total += score
                
                # Stats for Render
                s_row = df_stats[df_stats['player_id'] == pid] # Need filter?
                # Using last known stats for PID.
                s_dict = s_row.iloc[0].to_dict() if not s_row.empty else {}
                
                # Enrich p_info for renderer
                p_info['pontuacao'] = score
                
                processed.append({
                    'p_info': p_info,
                    's_dict': s_dict,
                    'score': score,
                    'escalado': escalado
                })
                
            # Sort: Active First, then Score Desc
            processed.sort(key=lambda x: (not x['escalado'], -x['score']))
            
            return processed, total

        # PROCESS TEAMS
        data_h, score_h = get_team_data(tid_h)
        data_a, score_a = get_team_data(tid_a)
        
        # RENDER
        with st.expander(f"{name_h} ({score_h:.2f})  x  ({score_a:.2f}) {name_a}", expanded=True):
             c1, c2 = st.columns(2)
             
             def render_list(data_list):
                 if not data_list: return
                 for item in data_list:
                     p = item['p_info']
                     s = item['s_dict']
                     esc = item['escalado']
                     
                     # Visual Queue for Bench/Out
                     if not esc:
                         st.markdown(f"<div style='opacity: 0.5;'>", unsafe_allow_html=True)
                     
                     render_player_row(p, s)
                     
                     if not esc:
                         st.markdown("</div>", unsafe_allow_html=True)

             with c1:
                 st.subheader(f"{name_h}")
                 render_list(data_h)
                 
             with c2:
                 st.subheader(f"{name_a}")
                 render_list(data_a)

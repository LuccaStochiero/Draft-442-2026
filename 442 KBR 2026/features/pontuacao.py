import streamlit as st
import pandas as pd
from features.auth import get_client
from features.utils import robust_to_float

from features.data_cache import (
    load_all_players_data,
    load_gameweek_data,
    load_h2h_rounds_data,
    load_team_lineup_data,
    load_squad_data,
    load_h2h_table_data,
    load_player_points_data,
    load_player_stats_data
)

def load_data_v2():
    """
    Legacy wrapper for Matchup compatibility.
    Loads: players, gw, h2h_rounds, lineup, squad, table
    """
    df_players = load_all_players_data()
    df_gw = load_gameweek_data()
    df_h2h = load_h2h_rounds_data()
    df_lineup = load_team_lineup_data()
    df_squad = load_squad_data()
    df_table = load_h2h_table_data()
    
    return df_players, df_gw, df_h2h, df_lineup, df_squad, df_table

def load_live_data(_client=None, _sh=None):
    """
    Legacy wrapper for Matchup compatibility.
    Loads: points, stats
    """
    df_pts = load_player_points_data()
    df_stats = load_player_stats_data()
    
    # Ensure columns exist if empty (Validation from old code)
    if df_pts.empty:
        df_pts = pd.DataFrame(columns=['game_id', 'player_id', 'pontuacao'])
    if df_stats.empty:
        df_stats = pd.DataFrame(columns=['game_id', 'player_id'])
    
    # Ensure basic validation
    for df, req_cols in [(df_pts, ['game_id', 'player_id', 'pontuacao']), (df_stats, ['game_id', 'player_id'])]:
        for c in req_cols:
             if c not in df.columns:
                 df[c] = pd.Series(dtype='str' if c != 'pontuacao' else 'float')

    return df_pts, df_stats

def clean_pos(p):
    mapping = {'Goalkeeper': 'GK', 'Defender': 'DEF', 'Midfielder': 'MEI', 'Forward': 'ATA'}
    return mapping.get(p, p)

def get_pos_color(pos):
    colors = {'GK': '#E3F2FD', 'DEF': '#E8F5E9', 'MEI': '#FFF9C4', 'ATA': '#FFEBEE'}
    return colors.get(pos, '#f0f0f0')


def render_player_row(row, stats_row, is_captain=False, raw_score=None):
    # Normalize keys to lower case for easier access
    s = {k.lower(): v for k, v in stats_row.items()}
    
    details = []
    
    # --- HELPER TO GET VAL ---
    def g(key):
        return s.get(key.lower(), 0)

    # 1. BASIC Stats
    rating = g('rating')
    if rating: details.append(f"Nota {rating}")
    
    goals = g('goals')
    if goals: details.append(f"{goals}G")
    
    assists = g('goalassist') or g('goalAssist')
    if assists: details.append(f"{assists}A")
    
    # 2. CARDS
    yc = g('yellowcards') or g('yellowCards')
    rc = g('redcards') or g('redCards')
    if yc: details.append(f"{yc}CA")
    if rc: details.append(f"{rc}CV")

    # 3. GOALKEEPER / DEFENSE
    pos = clean_pos(row.get('Posição', ''))
    
    saves = g('saves') + g('savedshotsfrominsidethebox') # Total Saves often split
    # If using just 'saves' from raw dict check corresponding logic
    # In live_stats: saves = df['saves']
    saves_raw = g('saves')
    if saves_raw: details.append(f"{saves_raw}DD")
    
    # SG (Clean Sheet)
    conceded = g('gols_sofridos_partida')
    mins = g('minutesplayed') or g('minutesPlayed')
    
    if pos in ['GK', 'DEF'] and mins > 0:
        if conceded == 0:
            details.append("SG")
        elif conceded > 0:
            details.append(f"-{int(conceded)}GS")
            
    # 4. BONUSES (Calculated on the fly for display)
    # Rules matched from live_stats.calculate_points
    
    # Bonus Passe: >= 40 passes AND >= 90% accuracy
    tot_pass = g('totalPass')
    acc_pass = g('accuratePass')
    if tot_pass >= 40 and (acc_pass/tot_pass >= 0.90):
        details.append("B_PAS")
        
    # Bonus Longa: >= 3 long balls AND >= 60% accuracy
    tot_long = g('totalLongBalls')
    acc_long = g('accurateLongBalls')
    if tot_long > 0 and tot_long >= 3 and (acc_long/tot_long >= 0.60):
        details.append("B_LON")

    # Bonus Duelo: >= 3 won AND >= 50% win rate
    won_duel = g('duelWon')
    lost_duel = g('duelLost')
    tot_duel = won_duel + lost_duel
    if tot_duel > 0 and won_duel >= 3 and (won_duel/tot_duel >= 0.50):
        details.append("B_DUE")
        
    # Bonus Drible (Contest): >= 3 won AND >= 60% win rate
    won_con = g('wonContest')
    tot_con = g('totalContest')
    if tot_con > 0 and won_con >= 3 and (won_con/tot_con >= 0.60):
        details.append("B_DRI")

    # 5. OFFENSIVE ACTIONS
    # 5. OFFENSIVE ACTIONS
    shots_ontarget = g('ontargetscoringattempt')
    hit_wood = g('hitwoodwork') # standardized lowercase key
    goals = g('goals')
    
    # Calculate "Real" Shots on Target for Display (F.DEF)
    f_def_display = max(0, shots_ontarget - hit_wood - goals)
    
    if f_def_display > 0: details.append(f"{int(f_def_display)}F.DEF") # Finalização Defendida
    
    shots_offtarget = g('shotOffTarget')
    if shots_offtarget: details.append(f"{shots_offtarget}F.FOR") # Finalização Fora
    
    hit_wood = g('hitWoodwork')
    if hit_wood: details.append(f"{hit_wood}F.TRA") # Trave
    
    key_pass = g('keyPass')
    if key_pass: details.append(f"{key_pass}KEY") # Passe Decisivo
    
    fouled = g('wasFouled')
    if fouled: details.append(f"{fouled}FS") # Falta Sofrida
    
    pen_won = g('penaltyWon')
    if pen_won: details.append(f"{pen_won}PS") # Pênalti Sofrido
    
    # 6. DEFENSIVE ACTIONS (Outfield)
    if pos != 'GK':
        tackles = g('wonTackle')
        if tackles: details.append(f"{tackles}DES") # Desarme
        
        interceptions = g('interceptionWon')
        if interceptions: details.append(f"{interceptions}INT")
        
        clearances = g('totalClearance')
        if clearances: details.append(f"{clearances}COR") # Corte
        
        blocks = g('outfielderBlock')
        if blocks: details.append(f"{blocks}BLC") # Bloqueio
        
        goal_line = g('goalLineClearance')
        if goal_line: details.append(f"{goal_line}LINHA") # Salvo Linha
    else:
        # GK Specific Extras
        keeper_sweeper = g('accurateKeeperSweeper')
        if keeper_sweeper: details.append(f"{keeper_sweeper}G.LIB") # Goleiro Líbero
        
        goals_prevented = g('goalsPrevented')
        if goals_prevented: details.append(f"{goals_prevented:.1f}xGK") # Gols Evitados
    
    pen_saved = g('penaltySave')
    if pen_saved: details.append(f"{pen_saved}DP") # Defesa Pênalti

    # 7. NEGATIVE
    offsides = g('totalOffside')
    if offsides: details.append(f"{offsides}IMP")
    
    fouls_commited = g('fouls')
    pen_conceded = g('penaltyconceded') or g('penaltyConceded')
    
    # Adjust for display so we don't double count penalty in fouls count visual
    real_fouls_disp = max(0, fouls_commited - pen_conceded)
    
    if real_fouls_disp: details.append(f"{real_fouls_disp}FC")
    
    pen_conceded = g('penaltyConceded')
    if pen_conceded: details.append(f"{pen_conceded}PC")
    
    pen_miss = g('penaltyMiss')
    if pen_miss: details.append(f"{pen_miss}PP")
    
    own_goals = g('ownGoals')
    if own_goals: details.append(f"{own_goals}GC")
    
    dispossessed = g('dispossessed')
    if dispossessed: details.append(f"{dispossessed}DIS") # Perda Posse

    if mins: details.append(f"{mins}'")

    detail_str = " | ".join(details) if details else "-"

    pos = clean_pos(row.get('Posição', ''))
    bg_color = get_pos_color(pos)
    
    pts = row.get('pontuacao', 0)
    # Style logic based on points
    pts_color = "#333"
    if pts > 8: pts_color = "#006600" # High score
    elif pts < 0: pts_color = "#cc0000" # Negative
    
    # Captain Logic
    name_display = row.get('Nome', 'Desconhecido')
    points_display_str = f"{pts:.2f}"
    
    if is_captain:
        name_display += " ©"
        if raw_score is not None:
             points_display_str = f"{pts:.2f} ({raw_score:.2f})"
        else:
             points_display_str = f"{pts:.2f}"
    
    st.markdown(
        f"""
        <div style="
            display: flex; 
            align-items: center; 
            background-color: transparent; 
            border: 1px solid #ffffff; 
            border-radius: 8px;
            margin-bottom: 8px;
            padding: 8px 12px;
        ">
            <div style="
                background-color: {bg_color}; 
                width: 35px; 
                text-align: center; 
                border-radius: 4px; 
                font-weight: bold; 
                font-size: 0.8em; 
                margin-right: 12px;
                color: #444;
            ">
                {pos}
            </div>
            <div style="flex-grow: 1;">
                <div style="font-weight: 600; color: #ffffff;">{name_display}</div>
                <div style="font-size: 0.75em; color: #eeeeee;">{detail_str}</div>
            </div>
            <div style="
                font-size: 1.1em; 
                font-weight: bold; 
                color: #ffffff;
                min-width: 40px;
                text-align: right;
            ">
                {points_display_str}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

def app():
    st.title("📊 Pontuações da Rodada")
    
    # Load Data (Split for Optimization)
    df_players, df_gw, df_h2h, df_lineup, df_squad, df_table = load_data_v2()
    df_pts, df_stats = load_live_data()
    
    if df_gw.empty:
        st.warning("Sem jogos carregados (GAMEWEEK vazia).")
        return

    # --- FILTERS ---
    c1, c2, c3 = st.columns([1, 2, 2])
    
    import datetime
    
    with c1:
        # Standardize Rodada to Int
        all_rounds = sorted(df_gw['rodada'].unique()) if 'rodada' in df_gw.columns else []
        
        # Determine Default Round (Latest started round)
        default_idx = 0
        if all_rounds and 'data_hora' in df_gw.columns:
            try:
                # Convert to datetime for comparison
                df_gw['dt_obj'] = pd.to_datetime(df_gw['data_hora'], dayfirst=True, errors='coerce')
                now = datetime.datetime.now()
                # Find max round where at least one game has started
                started_rounds = df_gw[df_gw['dt_obj'] <= now]['rodada'].unique()
                if len(started_rounds) > 0:
                    last_started = max(started_rounds)
                    if last_started in all_rounds:
                         default_idx = all_rounds.index(last_started)
            except Exception as e:
                pass

        sel_round = st.selectbox("Rodada", all_rounds, index=default_idx)
        
    with c2:
        # Filter Matches by Team (Home or Away)
        # Get teams present in this round
        round_matches = df_gw[df_gw['rodada'] == sel_round].copy()
        teams = set(round_matches['home_team'].unique()) | set(round_matches['away_team'].unique())
        sel_team = st.selectbox("Filtrar por Clube", ["Todos"] + sorted(list(teams)))

    with c3:
        # Filter by Position
        valid_pos = ["GK", "DEF", "MEI", "ATA"]
        sel_pos = st.multiselect("Filtrar por Posição", valid_pos, default=valid_pos)

    # Apply Filters
    if sel_team != "Todos":
        mask_team = (round_matches['home_team'] == sel_team) | (round_matches['away_team'] == sel_team)
        matches_to_show = round_matches[mask_team]
    else:
        matches_to_show = round_matches
        
    # Create Tabs
    tab_confrontos, tab_jogos, tab_lista = st.tabs(["⚔️ Confrontos", "Jogos", "Lista"])

    # --- TAB 0: CONFRONTOS (New) ---
    with tab_confrontos:
        if df_h2h.empty:
            st.info("Sem dados de confrontos.")
        else:
            # 1. Prepare Team Map
            team_map = {}
            if not df_squad.empty:
                 name_col = next((c for c in df_squad.columns if c in ['team_name', 'name', 'nome', 'team', 'time']), None)
                 if name_col:
                     team_map = pd.Series(df_squad[name_col].values, index=df_squad['team_id_norm']).to_dict()

            # 2. Filter H2H for Selected Round
            if 'rodada' in df_h2h.columns:
                round_h2h = df_h2h[df_h2h['rodada'] == sel_round].copy()
            else:
                round_h2h = pd.DataFrame()

            if round_h2h.empty:
                st.info(f"Sem confrontos para Rodada {sel_round}.")
            else:
                # 3. Filter Lineups for this round
                round_lineups = df_lineup[df_lineup['rodada'] == sel_round].copy() if not df_lineup.empty else pd.DataFrame()
                
                # Prepare Round Stats for full details
                r_games = df_gw[df_gw['rodada'] == sel_round]
                gids_full = r_games['id_jogo'].astype(str).tolist()
                gids_simple = []
                for x in gids_full:
                    if "id:" in x: gids_simple.append(x.split("id:")[-1])
                
                valid_gids = set(gids_full) | set(gids_simple)
                # Remove empty/invalid
                valid_gids = {x for x in valid_gids if x and str(x).lower() != 'nan' and str(x).strip() != ''}

                # Filter Points to only this round
                # Ensure we are not matching on empty IDs
                if not valid_gids:
                     round_pts_all = pd.DataFrame(columns=df_pts.columns)
                else:
                    round_pts_all = df_pts[
                        (df_pts['game_id'].astype(str).isin(valid_gids))
                    ].copy()
                
                # Helper to get score for a pid
                def get_pid_score(pid):
                    # Sum in case of duplicates (weird edge case), usually one entry
                    row = round_pts_all[round_pts_all['player_id'] == str(pid)]
                    return row['pontuacao'].sum() if not row.empty else 0.0

                mask_stats = (df_stats['game_id'].astype(str).isin(valid_gids))
                round_stats = df_stats[mask_stats].copy()

                # Iterate Matchups
                for _, match in round_h2h.iterrows():
                    # Identify Columns
                    h_col = next((c for c in round_h2h.columns if c in ['home_team_id', 'home', 'mandante']), None)
                    a_col = next((c for c in round_h2h.columns if c in ['away_team_id', 'away', 'visitante']), None)
                    
                    if not h_col or not a_col: continue
                    
                    tid_h = str(match[h_col]).strip()
                    tid_a = str(match[a_col]).strip()
                    
                    name_h = team_map.get(tid_h, tid_h)
                    name_a = team_map.get(tid_a, tid_a)
                    
                    # Get Lineups
                    lineup_h = round_lineups[round_lineups['team_id'] == tid_h]
                    lineup_a = round_lineups[round_lineups['team_id'] == tid_a]
                    
                    # Store processed players to render later
                    # List of (player_row, stats_dict, score)
                    proc_h = []
                    proc_a = []
                    
                    total_h = 0.0
                    total_a = 0.0
                    
                    any_pts_h = False
                    any_pts_a = False

                    # Process Home
                    if not lineup_h.empty:
                        for _, p in lineup_h.iterrows():
                            pid = str(p['player_id'])
                            p_rows = df_players[df_players['player_id'] == pid]
                            if p_rows.empty: continue
                            p_row = p_rows.iloc[0].to_dict()
                            
                            # Score & Stats
                            score = get_pid_score(pid)
                            total_h += score
                            if score != 0: any_pts_h = True
                            
                            s_row = round_stats[round_stats['player_id'] == pid]
                            s_dict = s_row.iloc[0].to_dict() if not s_row.empty else {}
                            
                            # Inject score into p_row for render color logic if needed or just display
                            p_row['pontuacao'] = score
                            proc_h.append((p_row, s_dict, score))
                            
                        # Sort by Score Desc
                        proc_h.sort(key=lambda x: x[2], reverse=True)

                    # Process Away
                    if not lineup_a.empty:
                        for _, p in lineup_a.iterrows():
                            pid = str(p['player_id'])
                            p_rows = df_players[df_players['player_id'] == pid]
                            if p_rows.empty: continue
                            p_row = p_rows.iloc[0].to_dict()
                            
                            score = get_pid_score(pid)
                            total_a += score
                            if score != 0: any_pts_a = True
                            
                            s_row = round_stats[round_stats['player_id'] == pid]
                            s_dict = s_row.iloc[0].to_dict() if not s_row.empty else {}
                            
                            p_row['pontuacao'] = score
                            proc_a.append((p_row, s_dict, score))
                            
                        proc_a.sort(key=lambda x: x[2], reverse=True)

                    # RENDER EXPANDER
                    # "enquanto nao tiver pontuação... nao é pra mostrar nenhuma escalação"
                    show_details = any_pts_h or any_pts_a
                    
                    header_str = f"{name_h} x {name_a}"
                    
                    with st.expander(header_str, expanded=False):
                        if show_details:
                           c_h, c_a = st.columns(2)
                           with c_h:
                               st.markdown(f"**{name_h}**")
                               if not proc_h: st.caption("Não escalou.")
                               for pr, sr, _ in proc_h:
                                   render_player_row(pr, sr)
                                   
                           with c_a:
                               st.markdown(f"**{name_a}**")
                               if not proc_a: st.caption("Não escalou.")
                               for pr, sr, _ in proc_a:
                                   render_player_row(pr, sr)
                        else:
                            st.info("Aguardando pontuações...")
    # --- TAB 1: JOGOS ---
    with tab_jogos:
        if matches_to_show.empty:
            st.info("Nenhum jogo encontrado.")
        else:
            # Normalize Columns for Stats
            if not df_stats.empty:
                df_stats.columns = df_stats.columns.str.lower()
                
            # --- RENDER MATCHES ---
            for _, match in matches_to_show.sort_values(by='data_hora').iterrows():
                # Match Header
                home = match['home_team']
                away = match['away_team']
                time_str = match.get('data_hora', '')
                game_id_full = str(match.get('id_jogo', '')) # URL
                
                # Filter: Only show if game_id exists
                if not game_id_full or game_id_full == 'nan':
                    continue

                # Extract ID from URL for matching stats
                try:
                     game_id_simple = game_id_full.split("id:")[-1]
                except:
                     game_id_simple = "0"
                     
                # Match Container
                with st.expander(f"{home} x {away}  |  {time_str}", expanded=False):
                    
                    # Match Logic:
                    match_pts = df_pts[df_pts['game_id'].astype(str) == game_id_full]
                    match_stats = df_stats[df_stats['game_id'].astype(str) == game_id_full]
                    
                    if match_pts.empty and match_stats.empty:
                         match_pts = df_pts[df_pts['game_id'].astype(str) == game_id_simple]
                         match_stats = df_stats[df_stats['game_id'].astype(str) == game_id_simple]
                    
                    if match_pts.empty and match_stats.empty:
                        st.caption(f"Ainda sem pontuações para este jogo. (ID: {game_id_simple})")
                        continue
                        
                    # Merge with Player Details
                    pids_pts = match_pts['player_id'].unique()
                    pids_stats = match_stats['player_id'].unique()
                    all_pids = set(pids_pts) | set(pids_stats)
                    
                    details = df_players[df_players['player_id'].isin(all_pids)].copy()
                    
                    if details.empty:
                        st.warning("IDs de jogadores não encontrados no banco de dados.")
                        continue
                    
                    # Apply Position Clean
                    details['CleanPos'] = details['Posição'].apply(clean_pos)
                    
                    # Filter by Position (UI Filter)
                    if sel_pos:
                        details = details[details['CleanPos'].isin(sel_pos)]


    # --- TAB 2: LISTA (GENERAL SCALE) ---
    with tab_lista:
        st.subheader(f"Classificação Geral - Rodada {sel_round}")

        # 1. Get all game IDs for this round to filter points
        # Use round_matches which already respects the Team Filter (if any)
        # Wait, if user selects "Santos", round_matches only has Santos games.
        # General list will show only players from those games.
        # IF user wants GLOBAL list, they should set Club Filter to "Todos".
        # This behavior is consistent.
        
        round_game_ids_full = round_matches['id_jogo'].astype(str).tolist()
        round_game_ids_simple = []
        for raw in round_game_ids_full:
            try:
                 if "id:" in raw: 
                     val = raw.split("id:")[-1]
                     if val and val.strip(): round_game_ids_simple.append(val)
                 elif raw and raw.strip() and raw.lower() != 'nan': 
                     round_game_ids_simple.append(raw)
            except: pass
        
        # Remove potential empty/nans from full list too just in case
        round_game_ids_full = [x for x in round_game_ids_full if x and str(x).lower() != 'nan' and str(x).strip() != '']

        # 2. Filter df_pts
        mask_pts = (df_pts['game_id'].astype(str).isin(round_game_ids_full)) | \
                   (df_pts['game_id'].astype(str).isin(round_game_ids_simple))
        
        round_pts = df_pts[mask_pts].copy()
        
        # --- FIX: Deduplicate by Best Score ---
        if not round_pts.empty:
             round_pts = round_pts.sort_values(by='pontuacao', ascending=False).drop_duplicates(subset=['player_id'], keep='first')


        if not round_pts.empty:
            # 3. Merge with Player Details
            round_pts['player_id'] = round_pts['player_id'].astype(str)
            merged = round_pts.merge(df_players[['player_id', 'Nome', 'Team', 'Posição']], on='player_id', how='left')
            
            # Apply Position Filter
            merged['CleanPos'] = merged['Posição'].apply(clean_pos)
            if sel_pos:
                merged = merged[merged['CleanPos'].isin(sel_pos)]

            # 4. Prepare Stats for this Round
            mask_stats = (df_stats['game_id'].astype(str).isin(round_game_ids_full)) | \
                         (df_stats['game_id'].astype(str).isin(round_game_ids_simple))
            round_stats = df_stats[mask_stats].copy()

            # 5. Sort by Points
            merged = merged.sort_values(by='pontuacao', ascending=False)
            
            # 6. Render List
            for _, p in merged.iterrows():
                # Modify Name to include Club
                p_dict = p.to_dict()
                team_name = p_dict.get('Team', '?')
                if pd.isna(team_name): team_name = '?'
                p_dict['Nome'] = f"{p_dict.get('Nome', '')} ({team_name})"
                
                # Get Stats
                # Need to match player_id AND game_id (Best Score Game)
                gid = str(p.get('game_id', ''))
                s_row = round_stats[
                    (round_stats['player_id'] == p['player_id']) & 
                    (round_stats['game_id'].astype(str) == gid)
                ]
                
                # Fallback
                if s_row.empty:
                    s_row = round_stats[round_stats['player_id'] == p['player_id']]
                
                # Using the first found stats (closest match)
                s_dict = s_row.iloc[0].to_dict() if not s_row.empty else {}
                
                render_player_row(p_dict, s_dict)
        else:
            st.info("Nenhuma pontuação registrada para esta rodada (com os filtros atuais).")

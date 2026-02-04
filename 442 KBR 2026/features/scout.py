import streamlit as st
import pandas as pd
# from features.auth import get_client, get_players_file
from features.utils import clean_pos

# --- CONSTANTS & MAPPING ---
POS_ORDER = ['GK', 'DEF', 'MEI', 'ATA']

# --- DISPLAY NAMES MAPPING ---
DISPLAY_NAMES = {
    "rating": "Nota",
    "goals": "Gols",
    "goalassist": "Assist.",
    "ontargetscoringattempt": "Fin. Defendida",
    "shotofftarget": "Fin. Fora",
    "hitwoodwork": "Trave",
    "keypass": "Passe Decisivo",
    "wasfouled": "Falta Sofrida",
    "penaltywon": "Pên. Sofrido",
    "wontackle": "Desarme",
    "interceptionwon": "Interceptação",
    "totalclearance": "Corte",
    "outfielderblock": "Bloqueio",
    "goallineclearance": "Salvo Linha",
    "saves": "Defesas",
    "goalsprevented": "Gols Evitados",
    "penaltysave": "Pên. Defendido",
    "accuratekeepersweeper": "Gol. Líbero",
    "savedshotsfrominsidethebox": "Def. Área",
    "totaloffside": "Impedimento",
    "fouls": "Faltas",
    "penaltyconceded": "Pên. Cometido",
    "penaltymiss": "Pên. Perdido",
    "owngoals": "Gol Contra",
    "dispossessed": "Perda Posse",
    "redcards": "Vermelho",
    "yellowcards": "Amarelo",
    "minutesplayed": "Minutos",
    "bonus_passe": "B. Passe",
    "bonus_longa": "B. Bola Longa",
    "bonus_duelo": "B. Duelo",
    "minutesplayed": "Minutos",
    "bonus_passe": "B. Passe",
    "bonus_longa": "B. Bola Longa",
    "bonus_duelo": "B. Duelo",
    "bonus_drible": "B. Drible",
    "pontuacao": "Pontuação"
}

def get_mapping_options():
    """
    Returns the dictionary of Analysis Categories -> Variables.
    Keys are what the user sees/selects.
    Values are lists of columns/keys in the stats dataframe or computed fields.
    """
    return {
        "Nota": ["rating"],
        "Part.Gol": ["goals", "goalassist"],
        "Ações": [
            "ontargetscoringattempt", "shotofftarget", "hitwoodwork", 
            "keypass", "wasfouled", "penaltywon"
        ],
        "Def": [
            "wontackle", "interceptionwon", "totalclearance", 
            "outfielderblock", "goallineclearance"
        ],
        "GK": [
            "saves", "goalsprevented", "penaltysave", "accuratekeepersweeper",
            "savedshotsfrominsidethebox"
        ],
        "Negativos": [
            "totaloffside", "fouls", "penaltyconceded", 
            "penaltymiss", "owngoals", "dispossessed"
        ],
        "Red": ["redcards", "yellowcards"],
        "Part": ["minutesplayed"], # We will also calculate 'Matches' count dynamically
        "Bonus": [
            "bonus_passe", "bonus_longa", "bonus_duelo", "bonus_drible" # Computed on the fly
        ],
        "Pontuação": ["pontuacao"]
    }

from features.data_cache import (
    load_all_players_data, 
    load_player_stats_data, 
    load_player_points_data,
    load_team_data,
    load_squad_data,
    load_gameweek_data
)

@st.cache_data(ttl=300)
def load_scout_data():
    """
    Loads all necessary data for the Scout tab using centralized cache.
    """
    # 1. Players
    df_players = load_all_players_data()
    if not df_players.empty:
         # Ensure Pos is cleaned (already done in data_cache but let's be safe if key is Pos vs Posição)
         # data_cache adds 'Posição Simplificada'. Scout uses 'Pos'
         if 'Posição Simplificada' in df_players.columns:
             df_players['Pos'] = df_players['Posição Simplificada']
         elif 'Posição' in df_players.columns:
             df_players['Pos'] = df_players['Posição'].apply(clean_pos)


    # 2. Stats
    df_stats = load_player_stats_data()

    # 2a. Points
    df_pts = load_player_points_data()
    
    # Merge Points into Stats
    if not df_stats.empty:
        if not df_pts.empty:
            if 'pontuacao' not in df_stats.columns:
                df_stats = df_stats.merge(df_pts[['player_id', 'game_id', 'pontuacao']], on=['player_id', 'game_id'], how='left')
                df_stats['pontuacao'] = df_stats['pontuacao'].fillna(0)
        else:
            if 'pontuacao' not in df_stats.columns:
                df_stats['pontuacao'] = 0.0
    
    # 3. Teams
    df_team = load_team_data()
    df_squad = load_squad_data()
    
    # 4. Gameweek
    df_gw = load_gameweek_data()

    return df_players, df_stats, df_team, df_squad, df_gw

def calculate_bonuses(row):
    """
    Returns a dict with 1 if bonus achieved, 0 otherwise.
    Based on features/pontuacao.py logic.
    """
    bonuses = {
        "bonus_passe": 0,
        "bonus_longa": 0,
        "bonus_duelo": 0,
        "bonus_drible": 0
    }
    
    # Bonus Passe: >= 40 passes AND >= 90% accuracy
    tot_pass = row.get('totalpass', 0)
    acc_pass = row.get('accuratepass', 0)
    if tot_pass >= 40 and (acc_pass/tot_pass >= 0.90):
        bonuses['bonus_passe'] = 1
        
    # Bonus Longa: >= 3 long balls AND >= 60% accuracy
    tot_long = row.get('totallongballs', 0)
    acc_long = row.get('accuratelongballs', 0)
    if tot_long >= 3 and (acc_long/tot_long >= 0.60):
        bonuses['bonus_longa'] = 1
        
    # Bonus Duelo: >= 3 won AND >= 50% win rate
    won_duel = row.get('duelwon', 0)
    lost_duel = row.get('duellost', 0)
    tot_duel = won_duel + lost_duel
    # Check if total > 0 to avoid div by zero
    if tot_duel > 0 and won_duel >= 3 and (won_duel/tot_duel >= 0.50):
        bonuses['bonus_duelo'] = 1
    
    # Bonus Drible (Contest): >= 3 won AND >= 60% win rate
    won_con = row.get('woncontest', 0)
    tot_con = row.get('totalcontest', 0)
    if tot_con > 0 and won_con >= 3 and (won_con/tot_con >= 0.60):
        bonuses['bonus_drible'] = 1
        
    return pd.Series(bonuses)

def app():
    st.markdown("## 🕵️ Scout Center")
    st.caption("Central de Análise e Scouting de Jogadores")

    # Load Data
    with st.spinner("Carregando base de dados..."):
        df_players, df_stats, df_team, df_squad, df_gw = load_scout_data()

    if df_stats.empty:
        st.warning("Sem dados estatísticos disponíveis.")
        return

    # --- PRE-PROCESSING ---
    
    # 1. Map Game IDs to Rounds
    # Create a map: game_id -> round
    game_round_map = {}
    if not df_gw.empty and 'rodada' in df_gw.columns:
        for _, row in df_gw.iterrows():
            gid_full = str(row.get('id_jogo', ''))
            gw = row.get('rodada')
            if gid_full:
                game_round_map[gid_full] = gw
                if 'id:' in gid_full:
                    game_round_map[gid_full.split('id:')[-1]] = gw
    
    df_stats['rodada'] = df_stats['game_id'].apply(lambda x: game_round_map.get(str(x), 0))
    # Filter out stats with no valid round (maybe friendly or bug)
    df_stats = df_stats[df_stats['rodada'] != 0]

    # 2. Enrich df_stats with Player Metadata (Name, Pos, Team)
    # Merge stats with players
    # First, let's map player ownership (Fictional Team)
    # Map player_id -> Team Name
    player_team_map = {}
    if not df_team.empty and not df_squad.empty:
         # Create team id -> name map
        name_col = next((c for c in df_squad.columns if c in ['name', 'nome', 'team', 'team_name']), 'name')
        tid_name_map = pd.Series(df_squad[name_col].values, index=df_squad['team_id_norm']).to_dict()
        
        # Map player -> tid -> Team Name
        for _, row in df_team.iterrows():
            pid = str(row['player_id'])
            tid = str(row['team_id'])
            tname = tid_name_map.get(tid, f"Time {tid}")
            player_team_map[pid] = tname
            
    # Add 'FictionalTeam' to df_players temporarily for display/filtering
    df_players['FictionalTeam'] = df_players['player_id'].apply(lambda x: player_team_map.get(x, 'Sem Time'))
    
    # --- FILTERS (EXPANDER) ---
    with st.expander("🔍 Filtros de Pesquisa", expanded=True):
        c1, c2, c3 = st.columns(3)
        
        with c1:
            # Name Search
            search_name = st.text_input("Nome do Jogador")
            
            # Position
            all_pos = POS_ORDER
            sel_pos = st.multiselect("Posição", all_pos, default=all_pos)
            
        with c2:
            # Fictional Teams
            all_teams = sorted(list(set(player_team_map.values())))
            all_teams.insert(0, "Sem Time")
            # Default: All? Or None?
            # Let's add a "Todos" option logic or just empty = all
            sel_teams = st.multiselect("Time", options=all_teams, placeholder="Selecione times specificos...")
            
        with c3:
            # Rounds
            # Get available rounds from stats
            avail_rounds = sorted(df_stats['rodada'].unique())
            # Slider or MultiSelect? MultiSelect gives more control (e.g. "Last 5")
            # But Slider is user requested "Acumulada" (Assuming range)
            # Let's do a multiselect for flexibility, but pre-select all or range
            sel_rounds = st.multiselect("Rodadas Consideradas", avail_rounds, default=avail_rounds)

        st.divider()
        
        # Analysis Settings
        c4, c5 = st.columns([1, 2])
        with c4:
            mapping_opts = get_mapping_options()
            cats = list(mapping_opts.keys())
            sel_cat = st.radio("Categoria de Análise", cats, horizontal=True)
            
        with c5:
            # Specific Variables (Sub-selection or All in Cat)
            vars_in_cat = mapping_opts[sel_cat]
            
            # Use Display Names for Dropdown
            # Create list of (Friendly, Internal)
            opts_list = [(DISPLAY_NAMES.get(v, v), v) for v in vars_in_cat]
            friendly_opts = [x[0] for x in opts_list]
            
            sel_vars_display = st.multiselect("Variáveis", friendly_opts, default=friendly_opts)
            
            # Map back to internal keys
            # Create reverse map based on current scope to handle any potential collisions or simple lookup
            rev_map_local = {k: v for k, v in opts_list}
            sel_vars = [rev_map_local[v] for v in sel_vars_display]

    # --- FILTER DATA ---
    
    # 1. Filter Players Metadata first
    df_p_filtered = df_players.copy()
    
    if search_name:
        df_p_filtered = df_p_filtered[df_p_filtered['Nome'].str.contains(search_name, case=False, na=False)]
        
    if sel_pos:
        df_p_filtered = df_p_filtered[df_p_filtered['Pos'].isin(sel_pos)]
        
    if sel_teams:
        df_p_filtered = df_p_filtered[df_p_filtered['FictionalTeam'].isin(sel_teams)]
        
    target_pids = df_p_filtered['player_id'].unique()
    
    if len(target_pids) == 0:
        st.info("Nenhum jogador encontrado com os filtros selecionados.")
        return

    # 2. Filter Stats
    stats_filtered = df_stats[
        (df_stats['player_id'].isin(target_pids)) & 
        (df_stats['rodada'].isin(sel_rounds))
    ].copy()
    
    if stats_filtered.empty:
        st.info("Nenhuma estatística encontrada para os jogadores/rodadas selecionados.")
        return

    # --- AGGREGATION ---
    
    # Pre-calculate Bonuses if needed
    if "bonus_passe" in sel_vars or "bonus_longa" in sel_vars or "bonus_duelo" in sel_vars or "bonus_drible" in sel_vars:
        # We need to apply this row by row
        bonus_df = stats_filtered.apply(calculate_bonuses, axis=1)
        stats_filtered = pd.concat([stats_filtered, bonus_df], axis=1)

    # Define aggregation dict
    # Most cols sum, Rating averages
    agg_dict = {}
    for col in sel_vars:
        if col.lower() == 'rating':
            agg_dict[col] = 'mean'
        else:
            agg_dict[col] = 'sum'
            
    # Always include 'rodada' count to know matches played
    agg_dict['rodada'] = 'count' # This gives number of matches
    
    # Group By Player
    grouped = stats_filtered.groupby('player_id').agg(agg_dict).reset_index()
    
    # Rename 'rodada' to 'Jogos'
    grouped = grouped.rename(columns={'rodada': 'Jogos'})
    
    # Round Rating
    for col in sel_vars:
        if col.lower() == 'rating' and col in grouped.columns:
            grouped[col] = grouped[col].round(2)

    # --- FINAL MERGE ---
    final_df = grouped.merge(df_p_filtered[['player_id', 'Nome', 'Pos', 'FictionalTeam', 'Team']], on='player_id', how='left')
    
    # Organize Columns
    cols_order = ['Nome', 'Pos', 'FictionalTeam', 'Team', 'Jogos'] + sel_vars
    final_display = final_df[cols_order].sort_values(by=sel_vars[0] if sel_vars else 'Jogos', ascending=False)
    


    # Rename Columns for Display to match user request
    # FictionalTeam -> Time
    # Team -> Time Real
    final_display = final_display.rename(columns={'FictionalTeam': 'Time', 'Team': 'Time Real'})
    
    # Apply Portuguese Translations
    final_display.columns = [DISPLAY_NAMES.get(c, c).title() if c in DISPLAY_NAMES else c for c in final_display.columns]
    
    # Capitalize others if needed (cleaning up remaining internal names if any missed)
    final_display.columns = [c.title() if c not in ['Nome', 'Pos', 'Time', 'Time Real'] and c not in DISPLAY_NAMES.items() else c for c in final_display.columns]
    
    # --- DISPLAY ---
    st.dataframe(
        final_display,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Nome": st.column_config.TextColumn("Jogador", width="medium"),
            "Pos": st.column_config.TextColumn("Pos", width="small"),
            "Time": st.column_config.TextColumn("Time", width="medium"),
            "Time Real": st.column_config.TextColumn("Time Real", width="small"),
            "Jogos": st.column_config.NumberColumn("# J", help="Jogos analisados no período"),
        }
    )

if __name__ == "__main__":
    app()

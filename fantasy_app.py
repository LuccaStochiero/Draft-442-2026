import streamlit as st
import pandas as pd
import random

# --- CONFIG ---
st.set_page_config(page_title="Fantasy Draft", layout="wide")

DATA_FILE = "Players.csv"

# --- STATE MANAGEMENT ---
def init_state():
    if 'setup_complete' not in st.session_state:
        st.session_state.setup_complete = False
    if 'teams' not in st.session_state:
        st.session_state.teams = []
    if 'draft_order' not in st.session_state:
        st.session_state.draft_order = []
    if 'current_pick_idx' not in st.session_state:
        st.session_state.current_pick_idx = 0
    if 'picks_history' not in st.session_state:
        st.session_state.picks_history = []  # List of dicts: {round, pick, team_idx, player_data}
    if 'league_name' not in st.session_state:
        st.session_state.league_name = "Minha Liga"
    if 'n_rounds' not in st.session_state:
        st.session_state.n_rounds = 10
    if 'available_players' not in st.session_state:
        try:
            df = pd.read_csv(DATA_FILE)
            st.session_state.available_players = df
        except FileNotFoundError:
            st.error(f"Arquivo {DATA_FILE} não encontrado!")
            st.session_state.available_players = pd.DataFrame()

# --- HELPER FUNCTIONS ---
def generate_snake_order(num_teams, num_rounds, random_order=False):
    order = []
    team_indices = list(range(num_teams))
    if random_order:
        random.shuffle(team_indices)
    
    st.session_state.base_team_order = team_indices.copy()

    for r in range(num_rounds):
        round_teams = team_indices.copy()
        if r % 2 == 1: # Odd index (Round 2, 4...) -> Reverse
            round_teams.reverse()
        for t_idx in round_teams:
            order.append({'team_idx': t_idx, 'round': r+1})
    return order

def get_position_color_style(pos):
    # Colors for positions (Darker, High Contrast, Colorblind friendly variants)
    # Text is white for better contrast on dark backgrounds.
    
    # Forward: Dark Green
    # Midfielder: Dark Gold/Ochre (Yellow that is visible)
    # Defender: Vermilion/Dark Orange
    # Goalkeeper: Strong Blue
    
    map_style = {
        "Forward": "background-color: #006400; color: white",      # Dark Green
        "Midfielder": "background-color: #B8860B; color: white",   # Dark Goldenrod
        "Defender": "background-color: #D35400; color: white",     # Pumpkin
        "Goalkeeper": "background-color: #191970; color: white"    # Midnight Blue
    }
    return map_style.get(pos, "background-color: #262730; color: white") # Default Dark

# --- STYLING ---
def load_css():
    st.markdown("""
        <style>
        /* General Theme */
        .stApp {
            background-color: #121212;
            color: #e0e0e0;
        }
        
        /* Headers */
        h1, h2, h3, h4, h5, h6 {
            font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            color: #ffffff;
            font-weight: 600;
        }
        
        /* Custom Card Containers */
        .custom-card {
            background-color: #1e1e1e;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
            margin-bottom: 20px;
            border: 1px solid #333;
        }
        
        /* Draft Header / Status Bar */
        .draft-header {
            background-color: #000000;
            padding: 15px 25px;
            border-bottom: 2px solid #333;
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 20px;
        }
        .draft-status-active {
            color: #00ff00; /* Neon Green */
            font-weight: bold;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .draft-info {
            color: #888;
            font-size: 0.9em;
        }
        
        /* Active Team Banner */
        .active-team-banner {
            background: linear-gradient(90deg, #1e1e1e 0%, #2a2a2a 100%);
            border-left: 5px solid #00ff00;
            padding: 20px;
            border-radius: 5px;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 20px;
        }
        
        /* Tabs Styling */
        .stTabs [data-baseweb="tab-list"] {
            gap: 10px;
            background-color: transparent;
        }
        .stTabs [data-baseweb="tab"] {
            background-color: #262626;
            border-radius: 5px;
            color: #888;
            padding: 10px 20px;
            border: none;
        }
        .stTabs [data-baseweb="tab"][aria-selected="true"] {
            background-color: #333;
            color: #fff;
            font-weight: bold;
            border-bottom: 2px solid #a020f0; /* Purple Accent */
        }
        
        /* Dataframes */
        [data-testid="stDataFrame"] {
            background-color: #1e1e1e;
        }
        
        /* Inputs */
        .stTextInput input, .stSelectbox div[data-baseweb="select"] {
            background-color: #262626 !important;
            color: white !important;
            border: 1px solid #444 !important;
        }
        
        /* Buttons */
        .stButton button {
            background-color: #a020f0;
            color: white;
            border: none;
            border-radius: 5px;
            font-weight: bold;
            transition: all 0.2s;
        }
        .stButton button:hover {
            background-color: #b040ff;
            transform: translateY(-2px);
        }
        
        /* Utility */
        .highlight-text {
            color: #a020f0;
            font-weight: bold;
        }
        </style>
    """, unsafe_allow_html=True)

# --- VIEWS ---

def render_setup():
    load_css()
    
    st.markdown('<div class="custom-card">', unsafe_allow_html=True)
    st.title("🏆 Configuração do Draft")
    st.markdown("</div>", unsafe_allow_html=True)
    
    with st.container():
        st.markdown('<div class="custom-card">', unsafe_allow_html=True)
        st.subheader("Configurações Gerais")
        st.session_state.league_name = st.text_input("Nome da Liga", value="Brasileirão Fantasy")
        
        col1, col2 = st.columns(2)
        with col1:
            n_teams = st.number_input("Quantidade de Times", min_value=2, max_value=20, value=4, step=1)
        with col2:
            st.session_state.n_rounds = st.number_input("Quantidade de Rodadas", min_value=1, max_value=30, value=11, step=1)
        
        random_order = st.checkbox("Ordem Aleatória?", value=True)
        st.markdown("</div>", unsafe_allow_html=True)
    
    with st.container():
        st.markdown('<div class="custom-card">', unsafe_allow_html=True)
        with st.form("teams_form"):
            st.markdown("### Times")
            teams_data = [] 
            cols = st.columns(2)
            for i in range(n_teams):
                with cols[i % 2]:
                    # Using container for better grouping if needed, mostly logic here
                    st.markdown(f"**Time {i+1}**")
                    name = st.text_input(f"Nome", value=f"Time {i+1}", key=f"team_name_{i}")
                    logo = st.file_uploader(f"Escudo", type=['png', 'jpg', 'jpeg'], key=f"team_logo_{i}")
                    teams_data.append({'name': name, 'logo': logo, 'id': i, 'players': []})
            
            st.markdown("---")
            submitted = st.form_submit_button("Iniciar Draft 🚀", use_container_width=True)
            
            if submitted:
                st.session_state.teams = teams_data
                st.session_state.draft_order = generate_snake_order(n_teams, st.session_state.n_rounds, random_order)
                st.session_state.setup_complete = True
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

def render_draft():
    load_css()
    
    # --- HEADER SECTION ---
    # Custom HTML Header
    league_name = st.session_state.league_name
    pick_idx = st.session_state.current_pick_idx
    total_picks = len(st.session_state.draft_order)
    
    if pick_idx >= total_picks:
        st.success("🎉 Draft Finalizado!")
        st.balloons()
        render_overall_board()
        return

    pick_info = st.session_state.draft_order[pick_idx]
    current_team_idx = pick_info['team_idx']
    current_team = st.session_state.teams[current_team_idx]
    current_round = pick_info['round']
    
    st.markdown(f"""
    <div class="draft-header">
        <div>
            <h2 style="margin:0; padding:0;">{league_name}</h2>
        </div>
        <div>
            <div class="draft-status-active">
                <span>● Draft Ao Vivo</span>
            </div>
            <div class="draft-info">Rodada {current_round} • Pick #{pick_idx + 1}</div>
        </div>
        <div>
           <!-- Placeholder for tools/admin -->
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # --- ACTIVE TURN BANNER ---
    col_banner_logo, col_banner_text = st.columns([1, 10])
    
    with st.container():
        # We simulate the banner visually using markdown and columns
        st.markdown(f"""
        <div class="active-team-banner">
            <div style="font-size: 2em; margin-right: 15px;">
                {'🛡️' if not current_team['logo'] else ''}
            </div>
            <div>
                <div style="color: #888; font-size: 14px; text-transform: uppercase;">Sua vez de escolher</div>
                <div style="font-size: 24px; font-weight: bold; color: white;">{current_team['name']}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        # Note: file_uploader images are harder to embed in raw HTML instantly without base64 processing. 
        # For simplicity, we keep the logic simple or add the image via standard st.image above/below if needed, 
        # but the request emphasizes visuals. 

    # --- MAIN CONTENT GRID ---
    
    # Layout: Left (Draft Board/Roster) - Right (Available Players)
    col_left, col_right = st.columns([2, 1], gap="large")
    
    with col_left:
        st.markdown('<div class="custom-card">', unsafe_allow_html=True)
        tab_roster, tab_board = st.tabs(["📋 Meu Elenco", "📊 Tabela Geral"])
        
        with tab_roster:
             st.markdown(f"#### Elenco: <span class='highlight-text'>{current_team['name']}</span>", unsafe_allow_html=True)
             render_team_roster(current_team)
             
        with tab_board:
             render_overall_board()
        st.markdown('</div>', unsafe_allow_html=True)

    with col_right:
        st.markdown('<div class="custom-card">', unsafe_allow_html=True)
        st.markdown("### Jogadores Disponíveis")
        render_available_players(current_team_idx, current_round)
        st.markdown('</div>', unsafe_allow_html=True)


def render_overall_board():
    n_rounds = st.session_state.n_rounds
    teams = st.session_state.teams
    
    # Prepare Data
    board_data = {}
    
    # Helper to find player details quickly
    history_map = {}
    for pick in st.session_state.picks_history:
        t_name = teams[pick['team_idx']]['name']
        r = pick['round']
        history_map[(t_name, r)] = pick['player_data']

    # For display
    board_data = {}
    for t in teams:
        col_data = []
        for r in range(1, n_rounds + 1):
            details = history_map.get((t['name'], r))
            if details:
                col_data.append(f"{details['Nome']}")
            else:
                col_data.append("-")
        board_data[t['name']] = col_data
        
    df_board = pd.DataFrame(board_data)
    df_board.index = [f"R{i+1}" for i in range(n_rounds)]
    
    # Styling Logic (Restored)
    def style_board(df_main):
        df_styler = pd.DataFrame('', index=df_main.index, columns=df_main.columns)
        for t in teams:
            for r in range(1, n_rounds + 1):
                details = history_map.get((t['name'], r))
                if details:
                    # Reuse the global helper function
                    css = get_position_color_style(details['Posição'])
                    # Add border for current pick? Optional.
                    df_styler.at[f"R{r}", t['name']] = css
        return df_styler

    # Apply Styler
    st.markdown("##### 🔢 Board Geral")
    st.dataframe(
        df_board.style.apply(style_board, axis=None),
        use_container_width=True,
        height=500
    )


def render_team_roster(team):
    players = team['players']
    
    # Summary Metrics
    total_players = len(players)
    total_value = sum([p.get('Valor de Mercado', 0) for p in players])
    
    c1, c2 = st.columns(2)
    c1.metric("Jogadores", f"{total_players}/{st.session_state.n_rounds}")
    c2.metric("Valor Total", f"€ {total_value:.1f}M")
    
    if not players:
        st.info("Ainda sem jogadores.")
        return
        
    df = pd.DataFrame(players)
    # Reorder cols
    cols_show = ['Posição', 'Nome', 'Team', 'Valor de Mercado']
    # Check if cols exist
    existing_cols = [c for c in cols_show if c in df.columns]
    
    st.dataframe(
        df[existing_cols],
        use_container_width=True,
        hide_index=True,
        column_config={
            "Valor de Mercado": st.column_config.NumberColumn(format="€ %.1fM"),
        }
    )

def render_available_players(current_team_idx, current_round):
    df = st.session_state.available_players
    
    # --- SEARCH & FILTER ---
    search = st.text_input("🔍 Buscar", placeholder="Nome do jogador...")
    
    f1, f2 = st.columns(2)
    with f1:
        # Club Filter
        all_teams = ["Todos"] + sorted(df['Team'].unique().tolist())
        team_filter = st.selectbox("Clube", all_teams, label_visibility="collapsed")
    with f2:
        # Pos Filter
        pos_filter = st.selectbox("Posição", ["Todas"] + list(df['Posição'].unique()), label_visibility="collapsed")
    
    # Apply filters
    filtered_df = df.copy()
    if search:
        filtered_df = filtered_df[filtered_df['Nome'].str.contains(search, case=False, na=False)]
    if team_filter != "Todos":
        filtered_df = filtered_df[filtered_df['Team'] == team_filter]
    if pos_filter != "Todas":
        filtered_df = filtered_df[filtered_df['Posição'] == pos_filter]
        
    filtered_df = filtered_df.sort_values(by="Valor de Mercado", ascending=False)
    
    st.caption(f"{len(filtered_df)} jogadores encontrados")
    
    # --- PLAYER LIST ---
    # We want a selectable list. 
    # Use dataframe with selection_mode if streamlit version supports it (recent versions do).
    # Assuming standard environment, we use column config.
    
    st.dataframe(
        filtered_df[['Posição', 'Nome', 'Team', 'Valor de Mercado']].head(100),
        use_container_width=True,
        hide_index=True,
        height=300,
        column_config={
            "Valor de Mercado": st.column_config.NumberColumn(format="€ %.1fM"),
        }
    )
    
    st.markdown("### Selecionar")
    # Selection Widget (Compact)
    with st.form("pick_form", border=False):
        selection_pool = filtered_df.head(50)
        
        # Create a display label for the selectbox
        selection_pool['display_label'] = selection_pool.apply(
            lambda x: f"{x['Nome']} | {x['Team']} | {x['Posição']}", axis=1
        )
        
        selected_label = st.selectbox(
            "Escolha o jogador:", 
            options=selection_pool['display_label'],
            label_visibility="collapsed"
        )
        
        confirm = st.form_submit_button("✅ CONFIRMAR ESCOLHA", type="primary", use_container_width=True)
            
        if confirm and selected_label:
             # Find the row
             # We rely on the index or exact match. 
             # To be safe, we verify strict match on display_label 
             # (assuming no duplicates in top 50 identical name+team+pos)
             selected_row = selection_pool[selection_pool['display_label'] == selected_label].iloc[0]
             perform_pick(selected_row, current_team_idx, current_round)

def perform_pick(player_row, team_idx, round_num):
    # Standard logic
    player_data = player_row.to_dict()
    # Remove helper col
    if 'display_label' in player_data:
        del player_data['display_label']
        
    st.session_state.teams[team_idx]['players'].append(player_data)
    
    st.session_state.picks_history.append({
        'round': round_num,
        'pick': st.session_state.current_pick_idx + 1,
        'team_idx': team_idx,
        'player_data': player_data
    })
    
    # Remove from available
    # We need the original index from the main df to drop it correctly
    # player_row.name contains the index if we selected from a sliced df preserving index
    st.session_state.available_players = st.session_state.available_players.drop(player_row.name)
    
    st.session_state.current_pick_idx += 1
    st.rerun()

# --- MAIN LOOP ---
init_state()

if not st.session_state.setup_complete:
    render_setup()
else:
    render_draft()

import streamlit as st
import pandas as pd
import os
from features.auth import get_client

# --- CONFIG ---
PLAYERS_LOCAL_FILE = os.path.join("Dados", "Players.csv")

POS_ORDER = ['GK', 'DEF', 'MEI', 'ATA']
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
    if os.path.exists(PLAYERS_LOCAL_FILE):
        df_players = pd.read_csv(PLAYERS_LOCAL_FILE)
        df_players['player_id'] = df_players['player_id'].astype(str)
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
            # Normalize ID col
            id_col = next((c for c in df_squad.columns if c in ['team_id', 'id']), 'team_id')
            df_squad['team_id_norm'] = df_squad[id_col].astype(str)

    except Exception as e:
        st.error(f"Erro sheets: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
        
    return df_players, df_team, df_squad

def app():
    st.markdown("### Visualização de Elenco")
    
    df_players, df_team, df_squad = load_data()
    
    if df_team.empty or df_squad.empty:
        st.warning("Dados insuficientes.")
        return

    # Name col
    name_col = next((c for c in df_squad.columns if c in ['name', 'nome', 'team', 'time', 'team_name']), None)
    if not name_col: 
        st.error("Coluna Nome não achada no SQUAD.")
        return
    
    # Position colors with dark text
    def style_row(row):
        colors = {'GK': '#E3F2FD', 'DEF': '#E8F5E9', 'MEI': '#FFF9C4', 'ATA': '#FFEBEE'}
        bg = colors.get(row['Pos'], '#FFF')
        return [f'background-color: {bg}; color: #1a1a1a;'] * len(row)
    
    # Status Info - only emoji
    def make_status(row):
        s = str(row.get('Status', ''))
        l = str(row.get('Lesão', ''))
        if s.lower() == 'nan': s = ''
        if l.lower() == 'nan': l = ''
        if s.lower() == 'active' and not l: return "✅"
        if 'daytoday' in s.lower().replace(" ",""): return "⚠️"
        if l: return "🚑"
        return ""
    
    # Prepare all players data
    all_players = df_players.copy()
    all_players['Pos'] = all_players['Posição'].apply(clean_pos)
    all_players['Status'] = all_players.apply(make_status, axis=1)
    
    # Get team map
    team_map = pd.Series(df_squad[name_col].values, index=df_squad['team_id_norm']).to_dict()
    sorted_teams = sorted(team_map.items(), key=lambda x: x[1])
    
    # CSS for horizontal scroll with wider tables
    st.markdown("""
        <style>
        [data-testid="stHorizontalBlock"] {
            overflow-x: auto;
            flex-wrap: nowrap !important;
        }
        [data-testid="stHorizontalBlock"] > div {
            min-width: 350px !important;
            flex-shrink: 0 !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Display teams in columns
    cols = st.columns(len(sorted_teams))
    
    for i, (team_id, team_name) in enumerate(sorted_teams):
        with cols[i]:
            st.markdown(f"###### {team_name}")
            
            # Get players for this team
            team_roster_ids = df_team[df_team['team_id'] == team_id]['player_id'].tolist()
            team_players = all_players[all_players['player_id'].isin(team_roster_ids)].copy()
            
            if team_players.empty:
                st.caption("Nenhum jogador")
            else:
                # Sort by position
                team_players['PosOrder'] = team_players['Pos'].map({p: i for i, p in enumerate(POS_ORDER)})
                team_players = team_players.sort_values(['PosOrder', 'Nome'])
                
                # Display table
                display_df = team_players[['Nome', 'Pos', 'Team', 'Status']].rename(columns={'Team': 'Clube'})
                
                st.dataframe(
                    display_df.style.apply(style_row, axis=1),
                    hide_index=True,
                    use_container_width=True,
                    height=(len(display_df) + 1) * 35 + 10
                )


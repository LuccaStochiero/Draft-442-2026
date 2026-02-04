import streamlit as st
import pandas as pd
# from features.auth import get_client, get_players_file # Not needed anymore
from features.data_cache import load_all_players_data, load_team_data, load_squad_data
from features.utils import clean_pos

# Constants
POS_ORDER = ['GK', 'DEF', 'MEI', 'ATA']

def load_data():
    df_players = load_all_players_data()
    df_team = load_team_data()
    df_squad = load_squad_data()
    
    # API success is effectively implicit if data frames are not empty
    # If they are empty, it means fetch failed (or sheets empty)
    is_api_fresh = not (df_players.empty or df_team.empty or df_squad.empty)
            
    return df_players, df_team, df_squad, is_api_fresh

def app():
    st.markdown("### Visualização de Elenco")
    
    df_players, df_team, df_squad, is_api_fresh = load_data()
    
    if not is_api_fresh:
        st.toast("⚠️ API indisponível (Quota). Exibindo dados em cache local.", icon="📂")
    
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
    all_players['Pos'] = all_players.get('Posição Simplificada', all_players.get('Posição', 'Unknown'))
    # Ensure clean_pos is applied if we fell back to 'Posição' (though data_cache should have handled it)
    if 'Posição Simplificada' not in all_players.columns and 'Posição' in all_players.columns:
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
            overflow-y: hidden;
            flex-wrap: nowrap !important;
            padding-bottom: 15px;
        }
        [data-testid="stHorizontalBlock"] > div {
            min-width: 350px !important;
            flex-shrink: 0 !important;
        }
        </style>
    """, unsafe_allow_html=True)

    # --- Player Search ---
    with st.expander("🔍 Pesquisar Jogador (Onde ele está?)"):
        search_term = st.text_input("Nome do jogador (min 3 letras):", key="search_elenco")
        if search_term and len(search_term) >= 3:
            mask = df_players['Nome'].str.contains(search_term, case=False, na=False)
            results = df_players[mask].head(10)
            
            if results.empty:
                st.info("Nenhum jogador encontrado.")
            else:
                for _, p_row in results.iterrows():
                    pid = str(p_row['player_id'])
                    pname = p_row['Nome']
                    ppos = p_row.get('Posição', 'N/A')
                    preal = p_row.get('Club', '') 
                    
                    # Find owner
                    owner_row = df_team[df_team['player_id'] == pid]
                    
                    status_txt = "LIVRE"
                    status_color = "green"
                    
                    if not owner_row.empty:
                        tid = str(owner_row.iloc[0]['team_id'])
                        # Team Name from already loaded df_squad
                        squad_row = df_squad[df_squad['team_id_norm'] == tid]
                        if not squad_row.empty:
                             if name_col:
                                 tname = squad_row.iloc[0][name_col]
                                 status_txt = f"Em: {tname}"
                                 status_color = "orange"
                             else:
                                 status_txt = f"Em: Time {tid}"
                                 status_color = "orange"
                        else:
                             status_txt = f"Em: Time {tid}"
                             status_color = "orange"
                    
                    st.markdown(f"**{pname}** ({ppos}) - {preal} -> <span style='color:{status_color}; font-weight:bold'>{status_txt}</span>", unsafe_allow_html=True)
    
    st.divider()
    
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
                
                # Checkbox for view mode (optional? No, user asked for card style)
                # Just render cards.
                
                display_df = team_players[['Nome', 'Pos', 'Team', 'Status']].rename(columns={'Team': 'Clube'})
                
                POS_COLORS = {'GK': '#E3F2FD', 'DEF': '#E8F5E9', 'MEI': '#FFF9C4', 'ATA': '#FFEBEE'}
                
                for _, row in display_df.iterrows():
                    pos = row['Pos']
                    name = row['Nome']
                    team = row['Clube']
                    status = row['Status']
                    bg = POS_COLORS.get(pos, '#FFF')
                    
                    st.markdown(
                        f"""
                        <div style="
                            background-color: {bg};
                            padding: 6px 8px;
                            border-radius: 5px;
                            margin-bottom: 5px;
                            display: flex;
                            align-items: center;
                            gap: 6px;
                            border: 1px solid #eee;
                            font-size: 0.85em;
                        ">
                             <span style="
                                font-weight: bold; 
                                color: #444; 
                                background-color: rgba(255,255,255,0.6); 
                                padding: 1px 4px; 
                                border-radius: 3px;
                                font-size: 0.75em;
                                min-width: 25px;
                                text-align: center;
                            ">{pos}</span>
                             <span style="font-weight: 600; color: #111;">{name} ({team})</span>
                             <span style="margin-left: auto;">{status}</span>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )




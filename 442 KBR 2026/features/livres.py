import streamlit as st
import pandas as pd
from features.auth import get_client

from features.data_cache import load_all_players_data, load_free_players_ids

def load_data():
    df_players = load_all_players_data()
    free_ids = load_free_players_ids()
    
    # Convert set back to DataFrame for compatibility with existing code structure if needed
    # Or actually, the existing code expects df_free_ids as a dataframe in column 'player_id'
    # But wait, looking at my previous edit to livres.py, I made it return df_players and df_free_ids.
    
    # Let's reconstruct df_free_ids from the set to minimize code changes in app()
    if free_ids:
        df_free_ids = pd.DataFrame({'player_id': list(free_ids)})
    else:
        df_free_ids = pd.DataFrame(columns=['player_id'])
        
    return df_players, df_free_ids

def app():
    st.title("🆓 Jogadores Livres (Lista)")
    
    df_players, df_free_ids = load_data()

    # --- Debug Utils ---
    if st.sidebar.checkbox("🛠️ Debug Info", value=False):
        st.sidebar.markdown("### 📊 Data Stats")
        st.sidebar.info(f"Local Players (CSV): **{len(df_players)}**")
        st.sidebar.info(f"Free Sheet (Rows): **{len(df_free_ids)}**")
        
        # Check intersection
        if not df_players.empty and not df_free_ids.empty:
            comm = df_players[df_players['player_id'].isin(set(df_free_ids['player_id'].unique()))]
            st.sidebar.code(f"Intersection: {len(comm)}")
            
        if st.sidebar.button("🧹 Limpar Cache"):
            st.cache_data.clear()
            st.cache_resource.clear()
            st.rerun()
    
    if df_players.empty or df_free_ids.empty:
        st.warning("Dados indisponíveis ou nenhum jogador livre no momento.")
        return

    # Filter: Only keep players who are in the free list
    free_ids = set(df_free_ids['player_id'].unique())
    df_free_detailed = df_players[df_players['player_id'].isin(free_ids)].copy()
    
    st.markdown(f"**Total Disponíveis:** {len(df_free_detailed)}")
    
    # --- Status Info Construction ---
    def make_status(row):
        s = str(row.get('Status', ''))
        l = str(row.get('Lesão', ''))
        
        if s.lower() == 'nan': s = ''
        if l.lower() == 'nan': l = ''

        if s.lower() == 'active' and not l:
            return "✅"
        
        # Replace dayToDay with warning emoji
        if 'daytoday' in s.lower().replace(" ",""):
             s = "⚠️"
             
        if l:
            return f"{s} ({l})"
        return s

    df_free_detailed['Status Info'] = df_free_detailed.apply(make_status, axis=1)

    # --- Filters ---
    c1, c2, c3 = st.columns(3)
    with c1:
        search_name = st.text_input("Buscar por Nome")
    with c2:
        unique_pos = sorted(df_free_detailed['Posição Simplificada'].dropna().astype(str).unique())
        sel_pos = st.multiselect("Posição", unique_pos)
    with c3:
        all_clubs = sorted(df_free_detailed['Team'].fillna('-').astype(str).unique())
        sel_clubs = st.multiselect("Clube Real", all_clubs)
        
    filtered = df_free_detailed.copy()
    if search_name:
        filtered = filtered[filtered['Nome'].str.contains(search_name, case=False, na=False)]
    if sel_pos:
        filtered = filtered[filtered['Posição Simplificada'].isin(sel_pos)]
    if sel_clubs:
        filtered = filtered[filtered['Team'].astype(str).isin(sel_clubs)]
        
    # --- Compact Display (Cards) ---
    st.divider()
    
    POS_COLORS = {'GK': '#E3F2FD', 'DEF': '#E8F5E9', 'MEI': '#FFF9C4', 'ATA': '#FFEBEE'}
    
    def render_player_card(pos, name, team, status, valor, bg_color):
        st.markdown(
            f"""
            <div style="
                background-color: {bg_color};
                padding: 10px 14px;
                border-radius: 6px;
                margin-bottom: 8px;
                display: flex;
                justify-content: space-between;
                align-items: center;
                border: 1px solid #e0e0e0;
                box-shadow: 0 1px 2px rgba(0,0,0,0.05);
            ">
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span style="
                        font-weight: bold; 
                        color: #444; 
                        background-color: rgba(255,255,255,0.6); 
                        padding: 2px 6px; 
                        border-radius: 4px;
                        font-size: 0.85em;
                        min-width: 35px;
                        text-align: center;
                    ">{pos}</span>
                    <span style="font-weight: 600; color: #111; font-size: 1.05em;">{name} ({team})</span>
                    <span style="margin-left: 5px;">{status}</span>
                </div>
                <div style="font-weight: bold; color: #00664d;">
                    $ {valor}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    # Sort by Value Descending
    filtered = filtered.sort_values(by='Valor de Mercado', ascending=False)
    
    # Check for empty after filters
    if filtered.empty:
        st.info("Nenhum jogador encontrado com os filtros selecionados.")
        return

    # Pagination handling to avoid rendering too many at once (optional but good practice)
    # For now, let's just show top 100 if no search is active to be safe, or just all.
    # User didn't ask for pagination, but performance is a concern.
    # I'll just render all but add a warning if > 200.
    
    if len(filtered) > 200:
        st.warning(f"Exibindo os primeiros 200 de {len(filtered)} jogadores. Use filtros para refinar.")
        filtered = filtered.head(200)

    for _, row in filtered.iterrows():
        pos = row['Posição Simplificada']
        name = row['Nome']
        team = row['Team']
        status = row['Status Info']
        val = row['Valor de Mercado']
        
        bg = POS_COLORS.get(pos, '#f9f9f9')
        
        # Format Value if numeric
        try:
            val_fmt = f"{float(val):,.1f} M" if pd.notnull(val) else "-"
        except:
             val_fmt = str(val)
             
        render_player_card(pos, name, team, status, val_fmt, bg)

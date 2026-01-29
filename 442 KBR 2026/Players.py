import streamlit as st

# Must be the first streamlit command
st.set_page_config(page_title="4-4-2 Manager (Players)", layout="wide")

from features import escalacao_main, elenco, leilao, livres, trade, live_stats, pontuacao, matchup

import time

def main():
    # Background Service: Check Live Stats (Safe Concurrency)
    # Throttling: Only run every 60 seconds per session to avoid UI stutter on page changes
    if 'last_sync_ts' not in st.session_state:
        st.session_state['last_sync_ts'] = 0
        
    now = time.time()
    if now - st.session_state['last_sync_ts'] > 60:
        try:
            # Using a status container is less intrusive than a full spinner for background checks
            with st.status("🔄 Verificando dados...", expanded=False) as status:
                live_stats.run_auto_update()
                status.update(label="✅ Dados verificados.", state="complete", expanded=False)
            st.session_state['last_sync_ts'] = now
        except Exception as e:
            st.error(f"Erro na atualização automática: {e}")
    
    st.sidebar.title("⚽ Players Area")
    
    # Navigation
    options = {
        "Visualização Elenco": elenco.app,
        "Jogadores Livres": livres.app,
        "Jogadores Livres": livres.app,
        "Pontuações": pontuacao.app,
        "MATCHUP": matchup.app,
        "Escalação": escalacao_main.app,
        "Leilão / Free Agency": lambda: leilao.app(is_admin=False),
        "Trade / Drop": trade.app
    }
    
    selection = st.sidebar.radio("Navegação", list(options.keys()))
    
    st.sidebar.divider()
    
    # Run selected app
    options[selection]()

if __name__ == "__main__":
    main()

import streamlit as st

# Must be the first streamlit command
st.set_page_config(page_title="4-4-2 Manager (Players)", layout="wide")

from features import escalacao_main, elenco, leilao, livres, trade, live_stats, pontuacao

def main():
    # Background Service: Check Live Stats (Safe Concurrency)
    live_stats.run_auto_update()
    
    st.sidebar.title("⚽ Players Area")
    
    # Navigation
    options = {
        "Visualização Elenco": elenco.app,
        "Jogadores Livres": livres.app,
        "Jogadores Livres": livres.app,
        "Pontuações": pontuacao.app,
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

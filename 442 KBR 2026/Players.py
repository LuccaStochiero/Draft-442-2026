import streamlit as st

# Must be the first streamlit command
st.set_page_config(page_title="4-4-2 Manager (Players)", layout="wide")

from features import escalacao_main, elenco, leilao, livres, trade

def main():
    st.sidebar.title("⚽ Players Area")
    
    # Navigation
    options = {
        "Visualização Elenco": elenco.app,
        "Jogadores Livres": livres.app,
        "Escalação": escalacao_main.app,
        "Leilão": lambda: leilao.app(is_admin=False),
        "Trocas": trade.app
    }
    
    selection = st.sidebar.radio("Navegação", list(options.keys()))
    
    st.sidebar.divider()
    
    # Run selected app
    options[selection]()

if __name__ == "__main__":
    main()

import streamlit as st

# Must be the first streamlit command
st.set_page_config(page_title="4-4-2 Manager (ADMIN)", layout="wide")

from features import escalacao_main, dados, elenco, leilao, livres, trade, confrontos

def main():
    st.sidebar.title("👮‍♂️ Admin Panel")
    
    # Navigation
    options = {
        "Dados & Sync": dados.app,
        "Visualização Elenco": elenco.app,
        "Jogadores Livres": livres.app,
        "Confrontos": confrontos.app,
        "Escalação": escalacao_main.app,
        "Leilão / Free Agency": lambda: leilao.app(is_admin=True),
        "Trade / Drop": trade.app
    }
    
    selection = st.sidebar.radio("Navegação", list(options.keys()))
    
    st.sidebar.divider()
    
    # Run selected app
    options[selection]()

if __name__ == "__main__":
    main()

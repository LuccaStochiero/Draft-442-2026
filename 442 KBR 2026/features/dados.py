import streamlit as st
import subprocess
import pandas as pd
import sys
from pathlib import Path
from features.auth import get_client, BASE_DIR

def app():
    st.title("🎲 Dados & Sincronização")
    
    st.info("O novo sistema unificado atualiza Jogos, Rodadas, ALL_PLAYERS e PLAYERS_FREE em uma única operação.")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### Atualização Geral")
        if st.button("🔄 Atualizar Banco de Dados (Jogos, Rodadas e Jogadores)", type="primary"):
            status_text = st.empty()
            status_text.info("Iniciando extração completa (SofaScore)... Por favor aguarde.")
            
            try:
                # Use subprocess to avoid asyncio loop conflicts with Streamlit/Windows
                # module: features.games_extraction
                cmd = [sys.executable, "-m", "features.games_extraction"]
                
                # Check execution
                result = subprocess.run(
                    cmd, 
                    cwd=str(BASE_DIR), 
                    capture_output=True, 
                    text=True,
                    encoding='utf-8', 
                    errors='replace'
                )
                
                if result.returncode == 0:
                    st.balloons()
                    status_text.success("✅ Atualização Completa com Sucesso!")
                    with st.expander("Ver Logs"):
                        st.code(result.stdout)
                else:
                    status_text.error("❌ Erro na Atualização")
                    st.error("Detalhes do erro:")
                    st.code(result.stderr)
                    with st.expander("Logs (stdout)"):
                        st.code(result.stdout)
                        
            except Exception as e:
                st.error(f"Erro ao executar subprocesso: {e}")

    with col2:
        st.markdown("### Status")
        st.write("A operação atualiza diretamente o Google Sheets.")
        
        # Link to sheets potentially?
        # Or just empty for now.

if __name__ == "__main__":
    app()

import streamlit as st
import subprocess
import pandas as pd
import sys
from pathlib import Path
from features.auth import get_client, get_players_file, BASE_DIR

# --- CONSTANTS ---
DATA_DIR = BASE_DIR / "Dados"
SCRAPER_SCRIPT = "scrape_sofascore.py"
PROCESS_SCRIPT = "process_data.py"

TAB_NAME = "ALL_PLAYERS"

def upload_to_drive():
    players_csv = get_players_file()
    if not players_csv.exists():
        st.error(f"Erro: `Players.csv` não encontrado em {players_csv}.")
        return False
    
    try:
        client, sh = get_client()
        
        st.info("Autenticando no Google Sheets...")
        
        # Check if tab exists, if not create
        try:
            worksheet = sh.worksheet(TAB_NAME)
            worksheet.clear()
        except:
            worksheet = sh.add_worksheet(title=TAB_NAME, rows=1000, cols=20)
        
        # Read CSV
        df = pd.read_csv(players_csv)
        df = df.fillna('') 
        df['player_id'] = df['player_id'].astype(str)
        
        st.info(f"Enviando {len(df)} linhas para a nuvem ({TAB_NAME})...")
        worksheet.update([df.columns.values.tolist()] + df.values.tolist())
        
        # --- SYNC PLAYERS_FREE ---
        st.info("Sincronizando PLAYERS_FREE...")
        try:
            # 1. Get Taken Players from TEAM tab
            try:
                ws_team = sh.worksheet("TEAM")
                team_data = ws_team.get_all_records()
                df_team = pd.DataFrame(team_data)
                
                if not df_team.empty:
                    df_team.columns = df_team.columns.str.lower()
                    taken_ids = set(df_team['player_id'].astype(str).unique())
                    st.info(f"Carregando jogadores de times (Total: {len(taken_ids)}) da aba TEAM.")
                else:
                    taken_ids = set()

            except:
                taken_ids = set()
                
            # 2. Filter Free Players
            df_free = df[~df['player_id'].isin(taken_ids)].copy()
            
            # 3. Format strictly as requested: player_id
            df_free_export = df_free[['player_id']].copy()
            
            # 4. Update PLAYERS_FREE tab
            FREE_TAB_NAME = "PLAYERS_FREE"
            try:
                ws_free = sh.worksheet(FREE_TAB_NAME)
                ws_free.clear()
            except:
                ws_free = sh.add_worksheet(title=FREE_TAB_NAME, rows=1000, cols=1)
                
            ws_free.update([df_free_export.columns.values.tolist()] + df_free_export.values.tolist())
            st.info(f"PLAYERS_FREE atualizado com {len(df_free_export)} registros (apenas player_id).")
            
        except Exception as e_free:
            st.warning(f"Erro ao atualizar PLAYERS_FREE: {e_free}")

        return True
        
    except Exception as e:
        st.error(f"Erro ao enviar para Google Sheets: {e}")
        return False

def app():
    st.title("🎲 Dados & Sincronização")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown("### Atualização")
        st.markdown("Clique abaixo para buscar novos dados do SofaScore e atualizar a base de jogadores.")
        
        if st.button("🔄 Atualizar e Sincronizar Tudo", type="primary"):
            status_placeholder = st.empty()
            
            # Step 1: Scrape
            status_placeholder.info("⏳ Iniciando o Scraper (sofascore)... Isso pode levar alguns minutos.")
            try:
                result_scrape = subprocess.run(
                    [sys.executable, SCRAPER_SCRIPT], 
                    cwd=DATA_DIR, 
                    capture_output=True, 
                    text=True
                )
                
                if result_scrape.returncode == 0:
                    st.success("✅ Scraper finalizado!")
                else:
                    st.error("❌ Erro no Scraper")
                    st.code(result_scrape.stderr)
                    st.stop()
                    
                # Step 2: Process
                status_placeholder.info("⏳ Processando dados...")
                result_process = subprocess.run(
                    [sys.executable, PROCESS_SCRIPT], 
                    cwd=DATA_DIR, 
                    capture_output=True, 
                    text=True
                )
                
                if result_process.returncode == 0:
                    st.success("✅ Processamento finalizado!")
                else:
                    st.error("❌ Erro no Processamento")
                    st.code(result_process.stderr)
                    st.stop()
    
                # Step 3: Upload
                status_placeholder.info("⏳ Enviando para Google Sheets...")
                if upload_to_drive():
                    st.balloons()
                    status_placeholder.success("🎉 TUDO PRONTO! Base Local e Google Sheets Atualizados!")
                
            except Exception as e:
                st.error(f"Ocorreu um erro inesperado: {e}")
    
    with col2:
        st.markdown("### Visualização (ALL_PLAYERS)")
        players_csv = get_players_file()
        
        if players_csv.exists():
            df = pd.read_csv(players_csv)
            st.write(f"**Total de Jogadores:** {len(df)}")
            st.write(f"**Última modificação:** {pd.to_datetime(players_csv.stat().st_mtime, unit='s').strftime('%d/%m/%Y %H:%M:%S')}")
            st.dataframe(df, use_container_width=True, height=500)
        else:
            st.warning(f"Arquivo Players.csv não encontrado em: {players_csv}")
    
    # --- MANUAL UPLOAD OPTION ---
    st.markdown("---")
    if st.checkbox("Mostrar opção de Envio Manual"):
        if st.button("☁️ Apenas Enviar para Google Sheets"):
            if upload_to_drive():
                st.success("Enviado com sucesso!")
    
    if __name__ == "__main__":
        app()


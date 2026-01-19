import streamlit as st
import subprocess
import os
import pandas as pd
import sys


# --- CONSTANTS ---
DATA_DIR = os.path.join(os.getcwd(), "Dados")
SERVICE_ACCOUNT_FILE = "service_account.json"
SHEET_ID = "1mG0XiZwzTyDncD592_XcpFwKeUwR97Gi8-tEh_XPW50"
SCRAPER_SCRIPT = "scrape_sofascore.py"
PROCESS_SCRIPT = "process_data.py"

TAB_NAME = "ALL_PLAYERS"

def upload_to_drive():
    players_csv = os.path.join(DATA_DIR, "Players.csv")
    if not os.path.exists(players_csv):
        st.error("Erro: `Players.csv` não encontrado. Execute a atualização local primeiro.")
        return False
    elif not os.path.exists(SERVICE_ACCOUNT_FILE):
        st.error(f"Erro: Arquivo de credenciais `{SERVICE_ACCOUNT_FILE}` não encontrado.")
        return False
    else:
        try:
            import gspread
            from oauth2client.service_account import ServiceAccountCredentials
            
            # Use st.status or placeholder if inside another flow, but simple st.info works
            st.info("Autenticando no Google Sheets...")
            scope = ["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/spreadsheets',
                     "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]
            
            creds = ServiceAccountCredentials.from_json_keyfile_name(SERVICE_ACCOUNT_FILE, scope)
            client = gspread.authorize(creds)
            
            sh = client.open_by_key(SHEET_ID)
            
            # Check if tab exists, if not create
            try:
                worksheet = sh.worksheet(TAB_NAME)
                worksheet.clear()
            except gspread.WorksheetNotFound:
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
                # 1. Get Taken Players from TEAM tab (Current Roster)
                # TEAM tab now represents the SINGLE source of truth for current ownership.
                # No round filtering needed.
                current_round = 1 # Default for export if needed
                
                try:
                    ws_team = sh.worksheet("TEAM")
                    team_data = ws_team.get_all_records()
                    df_team = pd.DataFrame(team_data)
                    
                    if not df_team.empty:
                        # Clean column names
                        df_team.columns = df_team.columns.str.lower()
                        # Get all player_ids currently in TEAM
                        taken_ids = set(df_team['player_id'].astype(str).unique())
                        st.info(f"Carregando jogadores de times (Total: {len(taken_ids)}) da aba TEAM.")
                    else:
                        taken_ids = set()

                except (gspread.WorksheetNotFound, KeyError):
                    taken_ids = set() # No team tab or empty
                    
                # 2. Filter Free Players
                # Only keep players NOT in taken_ids
                df_free = df[~df['player_id'].isin(taken_ids)].copy()
                
                # 3. Format strictly as requested: player_id
                # User requested "apenas com o player_id"
                df_free_export = df_free[['player_id']].copy()
                
                # 4. Update PLAYERS_FREE tab
                FREE_TAB_NAME = "PLAYERS_FREE"
                try:
                    ws_free = sh.worksheet(FREE_TAB_NAME)
                    ws_free.clear()
                except gspread.WorksheetNotFound:
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
        players_csv = os.path.join(DATA_DIR, "Players.csv")
        
        if os.path.exists(players_csv):
            df = pd.read_csv(players_csv)
            st.write(f"**Total de Jogadores:** {len(df)}")
            st.write(f"**Última modificação:** {pd.to_datetime(os.path.getmtime(players_csv), unit='s').strftime('%d/%m/%Y %H:%M:%S')}")
            st.dataframe(df, use_container_width=True, height=500)
        else:
            st.warning("Arquivo `Players.csv` não encontrado.")
    
    # --- MANUAL UPLOAD OPTION ---
    st.markdown("---")
    if st.checkbox("Mostrar opção de Envio Manual"):
        if st.button("☁️ Apenas Enviar para Google Sheets"):
            if upload_to_drive():
                st.success("Enviado com sucesso!")
    
    if __name__ == "__main__":
        app()


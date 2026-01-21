import streamlit as st
import gspread
import os
from pathlib import Path
from oauth2client.service_account import ServiceAccountCredentials

# Get the base directory (where features folder is)
BASE_DIR = Path(__file__).parent.parent
SERVICE_ACCOUNT_FILE = BASE_DIR / "service_account.json"
SHEET_ID = "1mG0XiZwzTyDncD592_XcpFwKeUwR97Gi8-tEh_XPW50"
PLAYERS_LOCAL_FILE = BASE_DIR / "Dados" / "Players.csv"

def get_credentials():
    """Get credentials from Streamlit secrets or local file"""
    scope = ["https://spreadsheets.google.com/feeds", 
             'https://www.googleapis.com/auth/spreadsheets',
             "https://www.googleapis.com/auth/drive.file", 
             "https://www.googleapis.com/auth/drive"]
    
    # Try Streamlit secrets first (for cloud deployment)
    try:
        if "gcp_service_account" in st.secrets:
            creds = ServiceAccountCredentials.from_json_keyfile_dict(
                dict(st.secrets["gcp_service_account"]), scope
            )
            return creds
    except Exception as e:
        # Local run without secrets.toml is expected; fail silently and try local file
        pass # print(f"Debug: Secrets not found ({e}), trying local file...")
    
    # Fall back to local file
    if SERVICE_ACCOUNT_FILE.exists():
        creds = ServiceAccountCredentials.from_json_keyfile_name(str(SERVICE_ACCOUNT_FILE), scope)
        return creds
    
    st.error(f"No credentials found. Checked: {SERVICE_ACCOUNT_FILE}")
    return None

def get_client():
    """Get authenticated gspread client and spreadsheet"""
    creds = get_credentials()
    if creds is None:
        raise Exception("No credentials found")
    
    client = gspread.authorize(creds)
    return client, client.open_by_key(SHEET_ID)

def get_players_file():
    """Get the path to Players.csv"""
    return PLAYERS_LOCAL_FILE

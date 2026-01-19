import streamlit as st
import gspread
import os
from oauth2client.service_account import ServiceAccountCredentials

SERVICE_ACCOUNT_FILE = "service_account.json"
SHEET_ID = "1mG0XiZwzTyDncD592_XcpFwKeUwR97Gi8-tEh_XPW50"

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
    except:
        pass
    
    # Fall back to local file
    if os.path.exists(SERVICE_ACCOUNT_FILE):
        creds = ServiceAccountCredentials.from_json_keyfile_name(SERVICE_ACCOUNT_FILE, scope)
        return creds
    
    return None

def get_client():
    """Get authenticated gspread client and spreadsheet"""
    creds = get_credentials()
    if creds is None:
        raise Exception("No credentials found")
    
    client = gspread.authorize(creds)
    return client, client.open_by_key(SHEET_ID)

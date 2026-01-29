"""Debug script to check raw cell values vs get_all_records"""
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from pathlib import Path

BASE_DIR = Path(__file__).parent
SERVICE_ACCOUNT_FILE = BASE_DIR / "service_account.json"
SHEET_ID = "1mG0XiZwzTyDncD592_XcpFwKeUwR97Gi8-tEh_XPW50"

def get_fresh_client():
    scope = ["https://spreadsheets.google.com/feeds", 
             'https://www.googleapis.com/auth/spreadsheets',
             "https://www.googleapis.com/auth/drive.file", 
             "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(str(SERVICE_ACCOUNT_FILE), scope)
    client = gspread.authorize(creds)
    return client, client.open_by_key(SHEET_ID)

def debug_raw_cells():
    print("Getting FRESH client...")
    client, sh = get_fresh_client()
    
    print("\n=== Checking TEST_DECIMALS raw cells ===")
    try:
        ws = sh.worksheet("TEST_DECIMALS")
    except:
        print("TEST_DECIMALS sheet not found")
        return
    
    # Get raw cell values (not interpreted)
    print("Getting raw values via get_values()...")
    raw_values = ws.get_values()
    for i, row in enumerate(raw_values[:5]):
        print(f"Raw Row {i}: {row}")
    
    # Get formatted values
    print("\nGetting get_all_records()...")
    records = ws.get_all_records()
    for i, row in enumerate(list(records)[:5]):
        print(f"Record {i}: {row}")
    
    # Check specific cell
    print("\nChecking cell B2 specifically...")
    cell = ws.acell('B2')
    print(f"Cell B2 value: {repr(cell.value)}")
    print(f"Cell B2 numeric_value: {repr(cell.numeric_value) if hasattr(cell, 'numeric_value') else 'N/A'}")

if __name__ == "__main__":
    debug_raw_cells()

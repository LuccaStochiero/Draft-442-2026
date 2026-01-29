"""Test script to write directly WITHOUT cached client"""
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from pathlib import Path

BASE_DIR = Path(__file__).parent
SERVICE_ACCOUNT_FILE = BASE_DIR / "service_account.json"
SHEET_ID = "1mG0XiZwzTyDncD592_XcpFwKeUwR97Gi8-tEh_XPW50"

def get_fresh_client():
    """Get a FRESH gspread client (no caching)"""
    scope = ["https://spreadsheets.google.com/feeds", 
             'https://www.googleapis.com/auth/spreadsheets',
             "https://www.googleapis.com/auth/drive.file", 
             "https://www.googleapis.com/auth/drive"]
    
    creds = ServiceAccountCredentials.from_json_keyfile_name(str(SERVICE_ACCOUNT_FILE), scope)
    client = gspread.authorize(creds)
    return client, client.open_by_key(SHEET_ID)

def test_fresh_write():
    print("Getting FRESH client (no cache)...")
    client, sh = get_fresh_client()
    
    # Test on a specific sheet
    print("Clearing and writing to TEST_DECIMALS...")
    try:
        ws = sh.worksheet("TEST_DECIMALS")
    except:
        ws = sh.add_worksheet("TEST_DECIMALS", 10, 3)
    
    ws.clear()
    
    # Test data with commas
    test_data = [
        ['id', 'pontuacao'],
        [1, '17,4082'],  # String with comma
        [2, '8,5000'],
        [3, '3,2500'],
    ]
    
    print("Writing test data...")
    ws.update(values=test_data, range_name='A1', value_input_option='USER_ENTERED')
    print("Write complete.")
    
    # Read back immediately
    print("\nReading back...")
    records = ws.get_all_records()
    for i, row in enumerate(records):
        val = row.get('pontuacao')
        print(f"Row {i}: pontuacao = {repr(val)} (type: {type(val).__name__})")

if __name__ == "__main__":
    test_fresh_write()

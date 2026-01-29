"""Test script to verify gspread write behavior"""
from features.auth import get_client
import gspread

def test_write():
    client, sh = get_client()
    
    # Create or get a test sheet
    try:
        ws = sh.worksheet("TEST_DECIMALS")
        ws.clear()
    except:
        ws = sh.add_worksheet("TEST_DECIMALS", 10, 3)
    
    # Write test values with USER_ENTERED
    test_data = [
        ['id', 'value_float', 'value_str'],
        [1, 17.4082, '17.4082'],
        [2, 8.5, '8.5'],
        [3, 3.25, '3.25'],
    ]
    
    print("Writing test data with USER_ENTERED...")
    ws.update('A1', test_data, value_input_option='USER_ENTERED')
    print("Done writing.")
    
    # Read back
    print("\nReading back...")
    records = ws.get_all_records()
    for i, row in enumerate(records):
        print(f"Row {i}: value_float={repr(row.get('value_float'))} (type: {type(row.get('value_float')).__name__}), value_str={repr(row.get('value_str'))}")

if __name__ == "__main__":
    test_write()

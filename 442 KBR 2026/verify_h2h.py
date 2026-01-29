"""Verify H2H - TEAM_POINTS has correct decimal values using get_values"""
from features.auth import get_client

def verify():
    client, sh = get_client()
    
    print("=== H2H - TEAM_POINTS (using get_values) ===")
    ws = sh.worksheet("H2H - TEAM_POINTS")
    raw_values = ws.get_values()
    
    if raw_values and len(raw_values) > 1:
        headers = raw_values[0]
        print(f"Columns: {headers}")
        print(f"First 10 rows:")
        for i, row in enumerate(raw_values[1:11]):
            if 'pontuacao' in headers:
                idx = headers.index('pontuacao')
                pont_val = row[idx] if len(row) > idx else 'N/A'
                player = row[1][:50] if len(row) > 1 else 'N/A'
                print(f"  Row {i}: pontuacao = {repr(pont_val)}, player = {player}")
    else:
        print("Empty or no data")

if __name__ == "__main__":
    verify()

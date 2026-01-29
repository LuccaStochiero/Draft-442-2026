from features.auth import get_client
import pandas as pd

def inspect_reserves():
    client, sh = get_client()
    ws = sh.worksheet('TEAM_LINEUP')
    df = pd.DataFrame(ws.get_all_records())
    
    print("Distinct Lineup Values:", df['lineup'].unique())
    print("Sample Reserves:")
    print(df[df['lineup'].str.contains('RESERVA', case=False, na=False)].head())

if __name__ == "__main__":
    inspect_reserves()

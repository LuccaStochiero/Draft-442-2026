from features.auth import get_client
import pandas as pd

def check_h2h_rounds():
    client, sh = get_client()
    try:
        ws = sh.worksheet("H2H - ROUNDS")
        vals = ws.get_all_records()
        if vals:
             df = pd.DataFrame(vals)
             print("Columns:", df.columns.tolist())
             print("First 3 rows:")
             print(df.head(3))
        else:
            print("Sheet is empty")
    except Exception as e:
        print(e)

check_h2h_rounds()

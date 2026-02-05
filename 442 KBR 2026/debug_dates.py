import pandas as pd
import datetime
from features.auth import get_client

def debug_dates():
    client, sh = get_client()
    ws = sh.worksheet("GAMEWEEK")
    df = pd.DataFrame(ws.get_all_records())
    
    # Normalize
    df.columns = [c.lower() for c in df.columns]
    
    # Filter Round 2
    if 'rodada' in df.columns:
        df['rodada'] = pd.to_numeric(df['rodada'], errors='coerce')
        r2 = df[df['rodada'] == 2]
    else:
        print("No rodada column")
        return

    now = datetime.datetime.now()
    print(f"Current Time: {now}")
    print(f"Checking {len(r2)} games for Round 2...\n")
    
    for i, row in r2.iterrows():
        t1 = row.get('home_team')
        t2 = row.get('away_team')
        dt_str = row.get('data_hora')
        
        is_finished = False
        parsed_dt = None
        
        if dt_str:
            try:
                parsed_dt = pd.to_datetime(dt_str, dayfirst=True)
                # Check +3h rule
                if (parsed_dt + datetime.timedelta(hours=3)) < now:
                    is_finished = True
            except Exception as e:
                print(f"Error parsing date {dt_str}: {e}")
        
        status_str = "FINISHED" if is_finished else "FUTURE/ACTIVE"
        print(f"{t1} vs {t2} | Date: {dt_str} | Parsed: {parsed_dt} | Status: {status_str}")

if __name__ == "__main__":
    debug_dates()

import pandas as pd
from datetime import datetime

INPUT_FILE = "sofascore_players.csv"
OUTPUT_FILE = "Players.csv"

def clean_name(name):
    if not isinstance(name, str):
        return name
    return name.strip()

def clean_timestamp(ts):
    # Convert SofaScore timestamp (seconds/ms) to dd/mm/yyyy
    # Usually it's unix timestamp (seconds).
    if pd.isna(ts) or ts == '':
        return ''
    try:
        # Check if ms (13 digits) or s (10 digits)
        ts = int(ts)
        # If huge, likely ms
        if ts > 100000000000:
             ts = ts / 1000
        
        dt = datetime.fromtimestamp(ts)
        return dt.strftime("%d/%m/%Y")
    except:
        return ''

def clean_team_slug(t):
    if not isinstance(t, str): return t
    return t.replace('-', ' ').title()

def process_data():
    try:
        df = pd.read_csv(INPUT_FILE)
    except FileNotFoundError:
        print(f"File {INPUT_FILE} not found.")
        return

    # Helper: Rename columns from Scraper (keys in dict) to Final Target
    # Scraper Keys: 'posicao', 'numero', 'nome', 'nacionalidade', 'altura', 'nascimento', 'team', 'status', 'lesao', 'valor_mercado', 'player_id'
    
    # Target Columns:
    # Posição, Número, Nome, Nacionalidade, Altura, Nascimento, Team, Status, Lesão, Valor de Mercado, player_id
    
    rename_map = {
        'posicao': 'Posição',
        'numero': 'Número',
        'nome': 'Nome',
        'nacionalidade': 'Nacionalidade',
        'altura': 'Altura',
        'nascimento': 'Nascimento_Raw', # Process first
        'team': 'Team',
        'status': 'Status',
        'lesao': 'Lesão',
        'valor_mercado': 'Valor de Mercado',
    }
    
    # Rename known
    df = df.rename(columns=rename_map)
    
    # Process
    if 'Nascimento_Raw' in df.columns:
        df['Nascimento'] = df['Nascimento_Raw'].apply(clean_timestamp)
    else:
        df['Nascimento'] = ''
        
    if 'Team' in df.columns:
        df['Team'] = df['Team'].apply(clean_team_slug)
        
    # Translate Positions? (Optional, user didn't explicitly ask but existing code did)
    # Keeping raw English from API usually safer unless asked. API returns "F" "M" "D" "G" or "Forward" etc.
    # We will keep raw for now as user just said "retire as informações... Posição..."
    # API gives clean names usually, unlike scraping text content that mixes injury status.
    # We can perform minimal cleanup.
    
    # --- NEW CLEANING LOGIC ---
    def clean_pos(p):
        mapping = {
            'G': 'Goalkeeper',
            'D': 'Defender',
            'M': 'Midfielder',
            'F': 'Forward'
        }
        return mapping.get(p, p)

    def clean_injury(val):
        if not isinstance(val, str): return ""
        # Remove parenthesized status e.g. "Muscle (doubtful)" or "ACL (dayToDay)" -> "Muscle", "ACL"
        if "(" in val:
            return val.split("(")[0].strip()
        return val

    def clean_mv(val):
        try:
            return float(val) / 1000.0
        except:
            return 0.0

    if 'Posição' in df.columns:
        df['Posição'] = df['Posição'].apply(clean_pos)
        
    if 'Lesão' in df.columns:
        df['Lesão'] = df['Lesão'].apply(clean_injury)
        
    if 'Valor de Mercado' in df.columns:
        df['Valor de Mercado'] = df['Valor de Mercado'].apply(clean_mv)
    
    # Final Selection
    wanted_cols = ['Posição', 'Número', 'Nome', 'Nacionalidade', 'Altura', 'Nascimento', 'Team', 'Status', 'Lesão', 'Valor de Mercado', 'player_id']
    
    # Ensure cols exist
    for c in wanted_cols:
        if c not in df.columns:
            df[c] = ''
            
    df_final = df[wanted_cols].copy()
    
    df_final.to_csv(OUTPUT_FILE, index=False)
    print(f"Processed {len(df_final)} rows to {OUTPUT_FILE}")
    print(df_final.head())

if __name__ == "__main__":
    process_data()

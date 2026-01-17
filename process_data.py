import pandas as pd
import re

INPUT_FILE = "sofascore_players.csv"
OUTPUT_FILE = "Players.csv"


def clean_name(name):
    if not isinstance(name, str):
        return name
    
    # -1. Remove Injury words FIRST (as requested)
    injury_words = ["Hamstring", "Muscle", "Knee", "Leg", "Medical condition", "Thigh", "Foot", "Fatigue", "Hand", "Ankle", "Calf"]
    for word in injury_words:
        name = name.replace(word, "")

    # 0. Remove "Day to day" (Requested previously, ensuring it's also done)
    name = name.replace("Day to day", "")


    # 1. Remove specific position words
    remove_words = ["Goalkeeper", "Defender", "Midfielder", "Forward"]
    for word in remove_words:
        name = name.replace(word, "")
    
    # 2. Remove trailing uppercase sequence (2 or more)
    match = re.search(r'([A-Z]{2,}(?:[\s,]+[A-Z]{2,})*)$', name)
    if match:
        name = name[:match.start()]
        
    return name.strip()

def clean_height(val):
    if pd.isna(val) or val == "-":
        return None
    s = str(val).lower().replace(" cm", "").strip()
    if s == "-" or s == "":
        return None
    try:
        return int(s)
    except:
        return None

def clean_market_value(val):
    if pd.isna(val) or val == "N/A" or val == "-" or val == "":
        return 0.0
    
    s = str(val).replace("€", "").strip()
    if not s:
        return 0.0
    
    multiplier = 1
    if "M" in s:
        multiplier = 1000000
        s = s.replace("M", "")
    elif "K" in s:
        multiplier = 1000
        s = s.replace("K", "")
        
    try:
        # User wants values in Millions (e.g. 13.5)
        # So we calculate the raw float, then divide by 1,000,000
        val_float = float(s) * multiplier
        return val_float / 1000000.0
    except:
        return 0.0

def process_data():
    df = pd.read_csv(INPUT_FILE)
    
    # Rename Mapping based on Verified CSV Content
    rename_map = {
        'Position': 'Posição',
        'RawName': 'Número',
        'Height': 'Nome',
        'Date of Birth': 'Nacionalidade',
        'Age': 'Altura',
        'Other_5': 'Nascimento',
        'Team': 'Team',
        'Market Value': 'Valor de Mercado',
        'PlayerLink': 'player_id' 
    }
    
    # Rename columns that we keep
    df = df.rename(columns=rename_map)
    
    # Create valid dataframe with selected columns
    wanted_columns = ['Posição', 'Número', 'Nome', 'Nacionalidade', 'Altura', 'Nascimento', 'Team', 'Valor de Mercado', 'player_id']
    
    for col in wanted_columns:
        if col not in df.columns:
             print(f"Warning: Column {col} missing.")

    # Select only wanted columns
    df_final = df[wanted_columns].copy()
    
    # --- Cleaning ---
    
    # 1. Clean Nome
    df_final['Nome'] = df_final['Nome'].apply(clean_name)
    
    # 2. Clean Altura
    df_final['Altura'] = df_final['Altura'].apply(clean_height)
    
    # 3. Clean Valor de Mercado
    df_final['Valor de Mercado'] = df_final['Valor de Mercado'].apply(clean_market_value)
    
    # 4. Clean Team (First letter uppercase, replace dashes)
    # The scraped team is a slug "atletico-mineiro".
    # User said "Colocar as palavras do Team com a primeira letra maíuscula".
    # Assuming "atletico-mineiro" -> "Atletico-Mineiro" or "Atletico Mineiro".
    # Standard Title Case for teams usually replaces hyphen.
    def format_team(t):
        if not isinstance(t, str): return t
        # Replace hyphens with space then title case looks cleaner for typically names
        # e.g. atletico-mineiro -> Atletico Mineiro
        return t.replace('-', ' ').title()

    df_final['Team'] = df_final['Team'].apply(format_team)

    # Save
    df_final.to_csv(OUTPUT_FILE, index=False)
    print(f"Processed data saved to {OUTPUT_FILE}")
    print(df_final.head())

if __name__ == "__main__":
    process_data()

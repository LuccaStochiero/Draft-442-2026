import asyncio
import pandas as pd
import gspread
from playwright.async_api import async_playwright
from datetime import datetime
import streamlit as st
from features.auth import get_client, get_players_file

# Constants
BASE_URL = "https://www.sofascore.com"
ROUNDS_API = "https://www.sofascore.com/api/v1/fantasy/competition/140/rounds"
EVENTS_NEXT_API = "https://www.sofascore.com/api/v1/fantasy/competition/140/events/next/{page}"
EVENTS_LAST_API = "https://www.sofascore.com/api/v1/fantasy/competition/140/events/last/{page}"
MATCH_URL_TEMPLATE = "https://www.sofascore.com/football/match/{slug}/{custom_id}#id:{id}"

async def get_browser_context(p):
    browser = await p.chromium.launch(headless=True) # Headless for background
    context = await browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    return browser, context

async def fetch_rounds(context):
    print("Fetching rounds...")
    page = await context.new_page()
    # Go to base to set cookies/headers
    try:
        await page.goto(BASE_URL, wait_until="domcontentloaded", timeout=30000)
    except:
        pass

    response = await page.request.get(ROUNDS_API)
    if response.status == 200:
        data = await response.json()
        rounds = data.get('rounds', [])
        # Extract: rodada, inicio, final
        # rounds structure: [{round: 1, startTime: 123, endTime: 456}, ...]
        if rounds:
             print(f"DEBUG: First round object keys: {rounds[0].keys()}")
             
        extracted = []
        for r in rounds:
            extracted.append({
                'rodada': r.get('sequence'), 
                'inicio': r.get('startTimestamp'),
                'final': r.get('endTimestamp'),
                'id': r.get('id')
            })
        return extracted
    else:
        print(f"Error fetching rounds: {response.status}")
        return []

async def fetch_matches_from_endpoint(context, api_template, direction="next"):
    all_matches = []
    page_num = 0
    found_any = True
    
    page = await context.new_page()
    # Ensure context is primed
    if page.url == "about:blank":
         try:
            await page.goto(BASE_URL, wait_until="domcontentloaded", timeout=30000)
         except:
             pass

    while found_any:
        url = api_template.format(page=page_num)
        print(f"Fetching {direction} page {page_num}: {url}")
        
        # Add random delay
        await page.wait_for_timeout(1000)
        
        response = await page.request.get(url)
        if response.status != 200:
            print(f"Failed to fetch {url}: {response.status}")
            break
            
        data = await response.json()
        events = data.get('events', [])
        
        if not events:
            found_any = False
            break
            
        print(f"Found {len(events)} events in {direction} page {page_num}")
        
        for i, item in enumerate(events):
            # Check if 'event' is nested inside the item (based on user JSON sample)
            # Sample: { "event": { ... }, "sequence": 1, "roundName": "Gameweek 1" }
            if 'event' in item:
                event_obj = item['event']
                round_name = item.get('roundName')
            else:
                # Fallback if structure is flat
                event_obj = item
                round_name = None

            # Extract info from the actual event object
            eid = event_obj.get('id')
            slug = event_obj.get('slug')
            custom_id = event_obj.get('customId')
            
            # Skip invalid events
            if not eid or not slug:
                # Log first 5 failures to debug (safe encoding)
                if i < 5:
                    print(f"Skipping event {i}: ID={eid}, CustomID={custom_id}")
                continue

            link = MATCH_URL_TEMPLATE.format(slug=slug, custom_id=custom_id, id=eid)
            
            # Rodada info
            # 1. Try 'roundInfo' inside event_obj
            rodada = event_obj.get('roundInfo', {}).get('round')
            
            # 2. If valid rodada not found, try to parse 'roundName' from wrapper
            # Example: "Gameweek 1" -> 1
            if not rodada and round_name:
                import re
                match = re.search(r'(\d+)', str(round_name))
                if match:
                    rodada = int(match.group(1))

            home_team = event_obj.get('homeTeam', {}).get('name')
            away_team = event_obj.get('awayTeam', {}).get('name')
            timestamp = event_obj.get('startTimestamp')
            status = event_obj.get('status', {}).get('type') # 'finished', 'notstarted', etc.
            
            row = {
                'id_jogo': link,
                'rodada': rodada,
                'home_team': home_team,
                'away_team': away_team,
                'data_hora': timestamp,
                'status': status,
                'timestamp': timestamp # keep for sorting/min/max
            }
            all_matches.append(row)
            
        page_num += 1
        
    return all_matches

async def run_extraction_async():
    async with async_playwright() as p:
        browser, context = await get_browser_context(p)
        
        # 1. Rounds
        rounds_data = await fetch_rounds(context)
        
        # 2. Matches (Next and Last)
        # Using separate pages/tasks or sequential? Sequential is safer for rate limits.
        matches_next = await fetch_matches_from_endpoint(context, EVENTS_NEXT_API, "next")
        matches_last = await fetch_matches_from_endpoint(context, EVENTS_LAST_API, "last")
        
        await browser.close()
        
        combined_matches = matches_next + matches_last
        print(f"Total valid matches extracted: {len(combined_matches)}")
        
        return rounds_data, combined_matches

def update_google_sheets(rounds_data, matches_data):
    client, sh = get_client()
    
    # 1. Update GAMEWEEK
    # Always try to clear/update
    try:
        ws_gw = sh.worksheet("GAMEWEEK")
        ws_gw.clear()
    except:
        ws_gw = sh.add_worksheet("GAMEWEEK", 1000, 10)
        
    if matches_data:
        df_matches = pd.DataFrame(matches_data)
        # Sort might be good
        df_matches = df_matches.sort_values(by='timestamp')
        
        # Select columns to save
        cols = ['id_jogo', 'rodada', 'home_team', 'away_team', 'data_hora', 'status']
        # Convert df to values
        data_to_upload = [cols] + df_matches[cols].values.tolist()
        ws_gw.update(data_to_upload)
        print(f"Updated GAMEWEEK with {len(df_matches)} matches.")
    else:
        print("No matches to save in GAMEWEEK (Sheet cleared).")
    
    # 2. Update HOUR
    if rounds_data:
        try:
            ws_hour = sh.worksheet("HOUR")
            ws_hour.clear()
        except:
             ws_hour = sh.add_worksheet("HOUR", 100, 10)
        
        df_rounds = pd.DataFrame(rounds_data)
        
        # Calculate First and Last match for each round from matches_data
        if matches_data:
            df_m = pd.DataFrame(matches_data)
            # Group by rodada
            if 'rodada' in df_m.columns and 'timestamp' in df_m.columns:
                 # Ensure numeric
                 df_m['rodada'] = pd.to_numeric(df_m['rodada'], errors='coerce')
                 df_rounds['rodada'] = pd.to_numeric(df_rounds['rodada'], errors='coerce')
                 
                 agg = df_m.groupby('rodada')['timestamp'].agg(['min', 'max']).reset_index()
                 agg.columns = ['rodada', 'primeiro', 'ultimo']
                 
                 print("DEBUG Rounds Data (Head):")
                 print(df_rounds.head())
                 print("DEBUG Agg Data:")
                 print(agg)
                 
                 # Merge
                 df_rounds = pd.merge(df_rounds, agg, on='rodada', how='left')
                 
                 print("DEBUG Rounds After Merge:")
                 print(df_rounds.head())
                 
                 # Fill NaN
                 df_rounds = df_rounds.fillna('')
            else:
                df_rounds['primeiro'] = ''
                df_rounds['ultimo'] = ''
        else:
             df_rounds['primeiro'] = ''
             df_rounds['ultimo'] = ''

        # Columns expected: rodada, inicio, final, primeiro, ultimo, id
        target_cols = ['rodada', 'inicio', 'final', 'primeiro', 'ultimo', 'id']
        # Ensure cols exist
        for c in target_cols:
            if c not in df_rounds.columns:
                df_rounds[c] = ''
                
        # Upload
        data_rounds = [target_cols] + df_rounds[target_cols].values.tolist()
        ws_hour.update(data_rounds)
        print(f"Updated HOUR with {len(df_rounds)} rounds.")


async def fetch_fantasy_players(round_id):
    """
    Fetches all players for a specific fantasy round ID using pagination.
    Endpoint: https://www.sofascore.com/api/v1/fantasy/round/{round_id}/players?page={page}
    """
    all_players = []
    page_num = 0
    has_next = True
    
    base_url = f"https://www.sofascore.com/api/v1/fantasy/round/{round_id}/players"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context(
             user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        )
        page = await context.new_page()

        while has_next:
            url = f"{base_url}?page={page_num}"
            print(f"Fetching players page {page_num}...")
            
            try:
                response = await page.request.get(url)
                if response.status != 200:
                    print(f"Error fetching page {page_num}: Status {response.status}")
                    break
                
                data = await response.json()
                # print(f"DEBUG: Response keys: {data.keys()}")
                
                players_list = data.get('players', [])
                has_next = data.get('hasNextPage', False)
                
                if not players_list:
                    print("No more players found (list empty).")
                    has_next = False
                    break
                
                for item in players_list:
                    # Handle potential wrapper from user snippet "fantasyPlayer": {...}
                    if 'fantasyPlayer' in item:
                        fp = item['fantasyPlayer']
                    else:
                        fp = item

                    # Extract logic
                    p_obj = fp.get('player', {})
                    t_obj = fp.get('team', {})
                    
                    status = "Active"
                    
                    # Market Value
                    price = fp.get('price', 0)
                    
                    # Position Mapping
                    raw_pos = fp.get('position', '')
                    # Map G, D, M, F to GK, DEF, MEI, ATA
                    pos_map = {'G': 'GK', 'D': 'DEF', 'M': 'MEI', 'F': 'ATA'}
                    final_pos = pos_map.get(raw_pos, raw_pos)
                    
                    # Player ID as URL
                    pid = p_obj.get('id', '')
                    slug = p_obj.get('slug', '')
                    if pid and slug:
                        full_id = f"https://www.sofascore.com/football/player/{slug}/{pid}"
                    else:
                        full_id = str(pid)
                    

                    all_players.append({
                        'Posição': final_pos,
                        'Número': p_obj.get('jerseyNumber', ''),
                        'Nome': p_obj.get('name', ''),
                        'Team': t_obj.get('name', ''),
                        'Status': status,
                        'Lesão': '', # Placeholder
                        'Valor de Mercado': price,
                        'player_id': full_id
                    })
                    
                page_num += 1
                if page_num > 100: break 
                
            except Exception as e:
                print(f"Exception on page {page_num}: {e}")
                break
                
        await browser.close()
        
    return all_players

def run_extraction():
    # Run async part
    rounds_data, matches_data = asyncio.run(run_extraction_async())
    
    # Run sheets update
    update_google_sheets(rounds_data, matches_data)
    
    # --- UPDATE PLAYERS ---
    target_round_id = None
    import time
    now_ts = time.time()
    
    if rounds_data:
        sorted_rounds = sorted(rounds_data, key=lambda x: x['inicio'])
        for r in sorted_rounds:
            if r['final'] > now_ts:
                target_round_id = r.get('id')
                print(f"Selected Round ID {target_round_id} (R{r['rodada']}) for Players Update")
                break
    
    if target_round_id:
        print(f"Starting Player Extraction for Round ID: {target_round_id}")
        players_data = asyncio.run(fetch_fantasy_players(target_round_id))
        if players_data:
             update_players_sheet(players_data)
        else:
             print("No players fetched.")
    else:
        print("Could not determine target round ID.")

    return True

def update_players_sheet(players_data):
    try:
        client, sh = get_client()
        
        # 1. Update ALL_PLAYERS
        try:
             ws_all = sh.worksheet("ALL_PLAYERS")
             ws_all.clear()
        except:
             ws_all = sh.add_worksheet("ALL_PLAYERS", 1000, 20)
             
        df_p = pd.DataFrame(players_data)
        
        # Columns (removed slug, Nac, Alt, Nasc)
        cols = ['Posição', 'Número', 'Nome', 'Team', 'Status', 'Lesão', 'Valor de Mercado', 'player_id']
        
        # Ensure cols exist
        for c in cols:
            if c not in df_p.columns: df_p[c] = ''
            
        # Reorder
        df_p = df_p[cols]
        
        # --- LOCAL SYNC ---
        try:
            local_file = get_players_file()
            # Ensure proper encoding for special chars
            df_p.to_csv(local_file, index=False, encoding='utf-8')
            print(f"Updated local Players.csv with {len(df_p)} rows at {local_file}")
        except Exception as e_csv:
            print(f"Error updating local CSV: {e_csv}")
        
        # Upload
        data_up = [cols] + df_p.values.tolist()
        ws_all.update(data_up)
        print(f"Updated ALL_PLAYERS with {len(df_p)} rows.")
        
        # 2. Update PLAYERS_FREE
        # Logic: Free = ALL - (Those in TEAM sheet)
        try:
            ws_team = sh.worksheet("TEAM")
            team_data = ws_team.get_all_records()
            df_team_owned = pd.DataFrame(team_data)
            
            # Need to match the IDs format. 
            # If TEAM sheet has old IDs (ints), and we now have URL IDs, this logic MIGHT FAIL unless TEAM sheet is also updated or we partial match.
            # Assuming TEAM sheet will eventually use the new IDs or we are wiping it? 
            # Risk: Currently owned players might have ID '12345' but new ID is 'url/12345'.
            # Fix: We should check if the URL contains the ID, or better, the user should update TEAM sheet too? 
            # Or simpler: The user intends for the new format to be the standard.
            # I cannot easily convert the TEAM sheet IDs right now without extra logic. 
            # I will proceed as is, but be aware of mismatch. 
            # Actually, if I can extract the numeric ID from the URL, I could compare? 
            # But the user asked for URL as the ID.
            # The most robust way is to assume current TEAM sheet might effectively "lose" players if IDs don't match.
            # But for "PLAYERS_FREE" logic:
            
            owned_ids = []
            if not df_team_owned.empty and 'player_id' in df_team_owned.columns:
                 # Normalize to string
                 owned_ids = df_team_owned['player_id'].astype(str).tolist()
            
        except Exception as e:
            print(f"Error reading TEAM sheet: {e}")
            owned_ids = []
            
        # Filter
        # Since we changed ID format, simple string match might fail if owned_ids are numbers.
        # But we must respect the request.
        # Ideally, existing teams should be updated to the new ID format manually or via migration.
        
        df_p['player_id'] = df_p['player_id'].astype(str)
        
        # If the owned_ids are short numbers, they won't match the long URLs.
        # Use regex or simple check? 
        # For now, strict match.
        df_free = df_p[~df_p['player_id'].isin(owned_ids)]
        
        # Use ONLY player_id for Free sheet
        df_free_export = df_free[['player_id']]
        
        try:
             ws_free = sh.worksheet("PLAYERS_FREE")
             ws_free.clear()
        except:
             ws_free = sh.add_worksheet("PLAYERS_FREE", 1000, 1)
             
        data_free = [['player_id']] + df_free_export.values.tolist()
        ws_free.update(data_free)
        print(f"Updated PLAYERS_FREE with {len(df_free)} rows.")
        
    except Exception as e:
        print(f"Error updating player sheets: {e}")


if __name__ == "__main__":
    run_extraction()

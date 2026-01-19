import asyncio
from playwright.async_api import async_playwright
import pandas as pd
import random
import time
import json
from datetime import datetime

# Constants
TOURNAMENT_URL = "https://www.sofascore.com/tournament/football/brazil/brasileirao-serie-a/325#id:87678"
BASE_URL = "https://www.sofascore.com"
OUTPUT_FILE = "sofascore_players.csv"
API_PLAYER_URL_TEMPLATE = "https://api.sofascore.com/api/v1/team/{}/players"

async def scrape_sofascore_api():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        print(f"Navigating to: {TOURNAMENT_URL}")
        try:
            await page.goto(TOURNAMENT_URL, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(3000)
        except Exception as e:
            print(f"Error navigating: {e}")
            await browser.close()
            return

        # 1. Get Team IDs from standings table
        print("locating teams...")
        try:
            await page.wait_for_selector('a[href*="/football/team"]', timeout=20000)
        except:
            print("Timeout waiting for team links.")
        
        # Extract unique team IDs from hrefs like "/team/football/team-slug/1977"
        hrefs = await page.locator('a[href*="/football/team"]').evaluate_all("els => els.map(e => e.getAttribute('href'))")
        
        teams = {} # {id: name}
        
        for h in hrefs:
            if h:
                # Format: /team/football/palmeiras/1963
                parts = h.split('/')
                if len(parts) >= 2:
                    tid = parts[-1] 
                    tname = parts[-2]
                    # Simple validation that ID is digit
                    if tid.isdigit():
                        teams[tid] = tname

        print(f"Found {len(teams)} unique teams: {list(teams.keys())}")
        
        all_players = []

        # 2. Iterate Teams and Fetch API
        for i, (tid, tslug) in enumerate(teams.items()):
            print(f"[{i+1}/{len(teams)}] Fetching players for {tslug} (ID: {tid})...")
            
            api_url = API_PLAYER_URL_TEMPLATE.format(tid)
            
            # We use page.request to fetch JSON in context (handles cookies/headers automatically)
            try:
                # Adding a small random delay to be polite
                await page.wait_for_timeout(random.randint(1000, 3000))

                response = await page.request.get(api_url)
                if response.status == 200:
                    data = await response.json()
                    players = data.get('players', [])
                    print(f"   -> Found {len(players)} players.")
                    
                    for p in players:
                        player = p.get('player', {})
                        
                        # Extract requested fields
                        pid = player.get('id', '')
                        slug = player.get('slug', '')
                        
                        # Construct full URL as player_id
                        # https://www.sofascore.com/football/player/{slug}/{id}
                        full_kink = f"https://www.sofascore.com/football/player/{slug}/{pid}"

                        # Market Value
                        mv = player.get('proposedMarketValue', 0)
                        
                        # Injury
                        # "injury": { "reason": "ACL Knee Injury", "status": "dayToDay" } -> usually under 'player' or just 'injury' key at root of item?
                        # Based on user snippet: "alem disso os jogadores machucados possuem a parte injury... que deve estar tambem dentro do ALL_PLAYERS"
                        # In the /team/players endpoint, structure is often { player: {...}, injury: {...} } OR player has injury field.
                        # We will check both 'p' (the item) and 'player' (the nested object).
                        
                        injury_obj = p.get('injury') # Check parent 'p' first based on common schema
                        if not injury_obj: injury_obj = player.get('injury')
                        
                        lesao_str = ""
                        status_str = "Active"
                        
                        if injury_obj:
                            reason = injury_obj.get('reason', '')
                            i_status = injury_obj.get('status', '')
                            if reason:
                                lesao_str = f"{reason} ({i_status})" if i_status else reason
                            status_str = i_status if i_status else "Injured"

                        row = {
                            'posicao': player.get('position', ''),
                            'numero': player.get('shirtNumber', '') or player.get('jerseyNumber', ''),
                            'nome': player.get('name', ''),
                            'nacionalidade': player.get('country', {}).get('name', '') if player.get('country') else '',
                            'altura': player.get('height', ''),
                            'nascimento': player.get('dateOfBirthTimestamp', ''),
                            'team': tslug, 
                            'status': status_str,
                            'lesao': lesao_str,
                            'valor_mercado': mv,
                            'player_id': full_kink
                        }

                        all_players.append(row)
                else:
                    print(f"   -> Failed {response.status}: {response.status_text}")
                    
            except Exception as e:
                print(f"   -> Error fetching API: {e}")

        await browser.close()
        
        # Save
        if all_players:
            df = pd.DataFrame(all_players)
            df.to_csv(OUTPUT_FILE, index=False)
            print(f"Saved {len(df)} players to {OUTPUT_FILE}")
        else:
            print("No players extracted.")

if __name__ == "__main__":
    asyncio.run(scrape_sofascore_api())

import asyncio
from playwright.async_api import async_playwright
import pandas as pd
from io import StringIO
import time
import random

# Constants
TOURNAMENT_URL = "https://www.sofascore.com/tournament/football/brazil/brasileirao-serie-a/325#id:87678"
BASE_URL = "https://www.sofascore.com"
OUTPUT_FILE = "sofascore_players.csv"

async def scrape_sofascore():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False) # Headless=False to see what's happening and avoid some bot detection
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        )
        page = await context.new_page()

        print(f"Navigating to tournament page: {TOURNAMENT_URL}")
        try:
            await page.goto(TOURNAMENT_URL, wait_until="domcontentloaded", timeout=60000)
        except Exception as e:
            print(f"Navigation warning: {e}")

        
        # Extract team links
        print("Extracting team links...")
        # Waiting for the links to be present
        try:
            await page.wait_for_selector('a[href*="/football/team"]', timeout=10000)
        except:
             print("Timeout waiting for team links selector.")
        
        # Get all hrefs
        links = await page.locator('a[href*="/football/team"]').evaluate_all("els => els.map(e => e.getAttribute('href'))")
        
        # Deduplicate and clean links
        unique_links = list(set(links))
        team_links = [l for l in unique_links if l]
        
        print(f"Found {len(team_links)} team links.")
        
        all_players_data = []

        for link in team_links:
            full_url = BASE_URL + link
            print(f"Processing team: {full_url}")
            
            try:
                await page.goto(full_url, wait_until="domcontentloaded")
                
                # Navigate to Players tab
                # The selector found in investigation was a[href="#tab:players"]
                players_tab_selector = 'a[href*="tab:players"]'
                
                # Navigate to Players tab
                players_tab_selector = 'a[href*="tab:players"]'
                
                try:
                    await page.wait_for_selector(players_tab_selector, timeout=5000)
                    await page.click(players_tab_selector)
                    
                    # Wait for table
                    await page.wait_for_selector('table.bd-sp_0', timeout=5000)
                    
                    # --- Step 1: Extract Main Player Data with Positions ---
                    # We get the HTML and parse manually to track the "Position" headers
                    table_outer_html = await page.locator('table.bd-sp_0').evaluate("el => el.outerHTML")
                    
                    # Use lxml for parsing
                    from lxml import html
                    tree = html.fromstring(table_outer_html)
                    rows = tree.xpath('.//tr')
                    
                    current_position = "Unknown"
                    team_players = []
                    
                    # Extract team info from URL
                    parts = link.split('/')
                    if len(parts) >= 4:
                        team_name = parts[-2]
                        team_id = parts[-1]
                    else:
                        team_name = "unknown"
                        team_id = "unknown"

                    for row in rows:
                        # Check if it's a position header (usually has 'colspan' text or specific class)
                        # Based on investigation: span with class textStyle_display... inside a TH/TD
                        # Simplest check: if the row has a colspan and meaningful text
                        header_text_el = row.xpath('.//th//span | .//td//span')
                        if header_text_el:
                            text = header_text_el[0].text_content().strip()
                            if text in ['Forward', 'Midfielder', 'Defender', 'Goalkeeper']:
                                current_position = text
                                continue

                        # Parse Player Row
                        # Typically player rows have specific cells. We can try to extract basic info.
                        # Using pandas for the row parsing is easier if we can map it back, but let's do manual to be safe with alignment.
                        # Alternatively, we iterate rows and if it's not a header, it's a player.
                        # We need Name, Nationality, Height, DOB, Age.
                        # Let's see the columns from the previous CSV: Name column often has "NameSymbol" concatenated.
                        
                        cols = row.xpath('.//td')
                        if len(cols) > 2: # Player row should have multiple columns
                            # This depends on exact column order. 
                            # Main table usually: [Name/Info, Nationality, Height, DOB, Age]
                            # But scanning the CSV shows: Name mixed with position symbol etc.
                            
                            # Let's retrieve texts
                            row_texts = [c.text_content().strip() for c in cols]
                            
                            # We can just store raw data and clean later, or try to be precise.
                            # Previous pandas read_html did a decent job. 
                            # Let's match the pandas output logic but add Position.
                            # Actually, we can just attach the "current_position" to a list and create a DF.
                            
                            # Extract Player Link
                            player_href = ""
                            # Look for any link in the row, usually in the name column
                            hrefs = row.xpath('.//a/@href')
                            for h in hrefs:
                                if "/player/" in h:
                                    player_href = BASE_URL + h
                                    break
                            
                            player_data = {
                                'Position': current_position,
                                'RawName': row_texts[0] if len(row_texts) > 0 else "",
                                'Nationality': row_texts[1] if len(row_texts) > 1 else "",
                                'Height': row_texts[2] if len(row_texts) > 2 else "",
                                'Date of Birth': row_texts[3] if len(row_texts) > 3 else "",
                                'Age': row_texts[4] if len(row_texts) > 4 else "",
                                'Other_5': row_texts[5] if len(row_texts) > 5 else "",
                                'Other_6': row_texts[6] if len(row_texts) > 6 else "",
                                'Team': team_name,
                                'TeamID': team_id,
                                'Team Link': full_url,
                                'PlayerLink': player_href 
                            }
                            team_players.append(player_data)


                    # --- Step 2: Extract Market Values ---
                    # Click "Market value" button
                    market_val_btn = 'button:has-text("Market value")'
                    if await page.query_selector(market_val_btn):
                        await page.click(market_val_btn)
                        # Wait for update. The table class is same, but content changes.
                        # We can wait for a currency symbol or just a small sleep + check.
                        await asyncio.sleep(1) 
                        
                        mv_table_html = await page.locator('table.bd-sp_0').evaluate("el => el.outerHTML")
                        mv_tree = html.fromstring(mv_table_html)
                        mv_rows = mv_tree.xpath('.//tr')
                        
                        # We assume the order of players remains the same (minus headers) 
                        # OR we match by name. Matching by name is safer.
                        mv_map = {} # Name -> Value
                        
                        for row in mv_rows:
                            cols = row.xpath('.//td')
                            if len(cols) > 1:
                                # Market value table usually has: Name, ?, Market Value (last col?)
                                # We need to check the exact columns visually or guess.
                                # Usually market value is the last column.
                                name_text = cols[0].text_content().strip()
                                val_text = cols[-1].text_content().strip()
                                mv_map[name_text] = val_text
                        
                        # Merge Market Value
                        for p in team_players:
                            # The name in main table might differ slightly (e.g. extra whitespace or symbols)
                            # We try exact match or lookup.
                            # 'RawName' from main table: "NeymarAM, LW, ST" (based on csv) - actually pandas read_html concatenated lines?
                            # lxml text_content() joins text. 
                            # Let's store the raw name for matching.
                            
                            p_name = p['RawName']
                            # Simple lookup
                            if p_name in mv_map:
                                p['Market Value'] = mv_map[p_name]
                            else:
                                p['Market Value'] = "N/A"
                                
                    df = pd.DataFrame(team_players)
                    all_players_data.append(df)
                    print(f"  -> Extracted {len(df)} players with positions.")
                    
                except Exception as inner_e:
                     print(f"  -> Players tab/table issue for {link}: {inner_e}")

            except Exception as e:
                print(f"  -> Error processing {link}: {e}")
            
            # Politeness delay
            await asyncio.sleep(random.uniform(1, 3))

        await browser.close()
        
        # Combine and Save
        if all_players_data:
            final_df = pd.concat(all_players_data, ignore_index=True)
            final_df.to_csv(OUTPUT_FILE, index=False)
            print(f"Valid data saved to {OUTPUT_FILE}")
        else:
            print("No data extracted.")

if __name__ == "__main__":
    asyncio.run(scrape_sofascore())

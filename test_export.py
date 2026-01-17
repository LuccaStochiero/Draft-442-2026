import requests
import json
import time

API_URL = "http://localhost:8000/api"

def test_export():
    # 1. Setup Draft
    setup_data = {
        "league_name": "Test League",
        "teams": [
            {"name": "Team A", "logo": ""},
            {"name": "Team B", "logo": ""}
        ],
        "n_rounds": 2,
        "random_order": False
    }
    try:
        requests.post(f"{API_URL}/setup", json=setup_data)
        
        # 2. Get Players
        res = requests.get(f"{API_URL}/players")
        players = res.json()
        if not players:
            print("No players found")
            return

        # 3. Make Picks
        # Team A picks
        p1 = players[0]['Nome']
        requests.post(f"{API_URL}/pick", json={"team_idx": 0, "player_name": p1})
        
        # Team B picks
        p2 = players[1]['Nome']
        requests.post(f"{API_URL}/pick", json={"team_idx": 1, "player_name": p2})
        
        # 4. Export
        res = requests.get(f"{API_URL}/export")
        print("--- CSV CONTENT PREVIEW ---")
        print(res.text)
        print("---------------------------")
        
    except Exception as e:
        print(f"Test failed: {e}")

if __name__ == "__main__":
    time.sleep(5) # Wait for server
    test_export()

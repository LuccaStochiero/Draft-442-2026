import pandas as pd
import random
import os

class DraftEngine:
    def __init__(self, data_path):
        self.data_path = data_path
        self.players_df = self._load_data()
        
        # State
        self.teams = [] # List of dicts
        self.draft_order = [] # List of {team_idx, round}
        self.picks_history = []
        self.current_pick_idx = 0
        self.league_name = "Nova Liga"
        self.n_rounds = 10
        self.is_setup = False
        
    def reset_league(self):
        self.teams = []
        self.draft_order = []
        self.picks_history = []
        self.current_pick_idx = 0
        self.is_setup = False
        self.players_df = self._load_data()
        return {"message": "Reset successful"}
        
    def _load_data(self):
        if os.path.exists(self.data_path):
            df = pd.read_csv(self.data_path)
            return df.fillna("")
        return pd.DataFrame()

    def setup_league(self, league_name, teams_data, n_rounds, random_order=False):
        """
        teams_data: List of dicts [{'name': '...', 'logo': '...'}]
        random_order: If True, shuffle. User requested strict order (False by default).
        """
        self.league_name = league_name
        self.n_rounds = n_rounds
        
        # Initialize teams with logo support
        self.teams = []
        for i, t_data in enumerate(teams_data):
            self.teams.append({
                'id': i, 
                'name': t_data['name'], 
                'logo': t_data.get('logo', ''), # Base64 string
                'players': []
            })

        self.current_pick_idx = 0
        self.picks_history = []
        
        # Reload players
        self.players_df = self._load_data()
        
        # Generate Snake Order (Strict)
        team_indices = list(range(len(self.teams)))
        
        # Only shuffle if explicitly requested (User asked for input order)
        if random_order:
            random.shuffle(team_indices)
            
        self.draft_order = []
        for r in range(n_rounds):
            round_teams = team_indices.copy()
            # 0-indexed rounds. Round 0 (1st) = Normal. Round 1 (2nd) = Reverse.
            if r % 2 == 1: 
                round_teams.reverse()
                
            for t_idx in round_teams:
                self.draft_order.append({'team_idx': t_idx, 'round': r+1})
        
        self.is_setup = True
        return self.get_state()

    def make_pick(self, team_idx, player_name):
        if not self.is_setup:
            raise Exception("Draft not setup")
            
        pick_info = self.draft_order[self.current_pick_idx]
        if pick_info['team_idx'] != team_idx:
            raise Exception("Not this team's turn")

        # Find player
        player_row = self.players_df[self.players_df['Nome'] == player_name]
        if player_row.empty:
            raise Exception("Player not found")
            
        player_data = player_row.iloc[0].to_dict()
        
        # Add to team
        self.teams[team_idx]['players'].append(player_data)
        
        # Add to history
        self.picks_history.append({
            'round': pick_info['round'],
            'pick_overall': self.current_pick_idx + 1,
            'team_idx': team_idx,
            'player': player_data
        })
        
        # Remove from pool
        self.players_df = self.players_df[self.players_df['Nome'] != player_name]
        
        self.current_pick_idx += 1
        return self.get_state()

    def undo_last_pick(self):
        if not self.is_setup:
            raise Exception("Draft not setup")
        if not self.picks_history:
            raise Exception("No picks to undo")

        # Get last pick
        last_pick = self.picks_history.pop()
        team_idx = last_pick['team_idx']
        player_data = last_pick['player']
        
        # Remove from team
        team = self.teams[team_idx]
        # Assuming player names are unique or matching the exact dict
        team['players'] = [p for p in team['players'] if p['Nome'] != player_data['Nome']]
        
        # Add back to available players (DataFrame)
        # We need to construct a DataFrame for the single row and concat it
        # Note: This is less efficient but safe. 
        # Ideally we should keep 'id' but we used 'Nome' for matching.
        player_df_row = pd.DataFrame([player_data])
        self.players_df = pd.concat([self.players_df, player_df_row], ignore_index=True)
        
        # Decrement pick index
        self.current_pick_idx -= 1
        
        return self.get_state()

    def get_state(self):
        return {
            "league_name": self.league_name,
            "teams": self.teams,
            "current_pick_idx": self.current_pick_idx,
            "total_picks": len(self.draft_order),
            "draft_order": self.draft_order,
            "history": self.picks_history,
            "is_finished": self.current_pick_idx >= len(self.draft_order)
        }

    def get_available_players(self):
        return self.players_df.to_dict(orient="records")

    def export_results_csv(self):
        import io
        import csv
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow(['player_id', 'Time Escolhido', 'Nome', 'Posição', 'Valor'])
        
        # Rows
        for pick in self.picks_history:
            team_idx = pick['team_idx']
            team_name = self.teams[team_idx]['name']
            p = pick['player']
            
            # Use player_id if available, else fallback to Nome
            p_id = p.get('player_id', '')
            if not p_id:
                p_id = p.get('PlayerLink', '') # Fallback
                
            writer.writerow([
                p_id,
                team_name,
                p.get('Nome', ''),
                p.get('Posição', ''),
                p.get('Valor de Mercado', '')
            ])
            
        return output.getvalue()

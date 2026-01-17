export interface Player {
    Nome: string;
    Posição: string;
    Team: string;
    "Valor de Mercado": number;
    [key: string]: any;
}

export interface Team {
    id: number;
    name: string;
    logo?: string;
    players: Player[];
}

export interface PickHistory {
    round: number;
    pick_overall: number;
    team_idx: number;
    player: Player;
}

export interface DraftState {
    league_name: string;
    teams: Team[];
    current_pick_idx: number;
    total_picks: number;
    draft_order: Array<{ team_idx: number; round: number }>;
    history: PickHistory[];
    is_finished: boolean;
}

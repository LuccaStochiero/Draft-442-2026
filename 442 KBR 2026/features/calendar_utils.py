import pandas as pd
import streamlit as st
from datetime import datetime
import time
from features.auth import get_client

def get_game_state():
    """
    Determines the current game state:
    - Auction Open/Closed
    - Free Agency Open/Closed
    - Deadlines
    """
    try:
        client, sh = get_client()
        ws = sh.worksheet("HOUR")
        data = ws.get_all_records()
        df = pd.DataFrame(data)
        
        # Ensure numeric
        cols = ['rodada', 'inicio', 'final', 'primeiro', 'ultimo']
        for c in cols:
            df[c] = pd.to_numeric(df[c], errors='coerce')
        
        df = df.sort_values(by='rodada')
        
        # Current Timestamp
        now_ts = time.time()
        # Debug: allow overriding with a query param or manually if needed? No, strict for now.
        
        # Find Next Round (first round where 'primeiro' > now)
        # We need the 'primeiro' (first match) to identify the "Next Round Start"
        future_rounds = df[df['primeiro'] > now_ts]
        
        if future_rounds.empty:
            return {
                'status': 'Season Finished',
                'auction_open': False,
                'free_open': True, # Always allow free after season? Or False? Assuming False for safety.
                'msg': 'Temporada encerrada ou sem próximas rodadas.',
                'next_round': None
            }
        
        next_round_row = future_rounds.iloc[0]
        next_round_idx = next_round_row['rodada']
        next_start = next_round_row['primeiro']
        
        # Find Previous Round (to calc gap)
        # It's simply the round before Next Round
        prev_round_row = df[df['rodada'] == next_round_idx - 1]
        
        if prev_round_row.empty:
            # If next is round 1, gap is infinite -> Auction ON
            gap_hours = 999.0
        else:
            prev_end = prev_round_row.iloc[0]['ultimo']
            gap_seconds = next_start - prev_end
            gap_hours = gap_seconds / 3600.0
            
        # Deadlines based on Next Start
        hours_to_next = (next_start - now_ts) / 3600.0
        
        # Format Deadline helper
        def fmt_deadline(ts):
            dt = datetime.fromtimestamp(ts)
            day_name = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sab", "Dom"][dt.weekday()]
            return f"{day_name} {dt.strftime('%d/%m às %H:%M')}"
            
        # Logic
        # > 48h Gap
        
        if gap_hours > 48:
            # Auction ends 24h before
            # Free starts 24h before
            
            if hours_to_next > 24:
                # Phase 1: Auction
                deadline = fmt_deadline(next_start - 24*3600)
                return {
                    'status': 'AUCTION_OPEN',
                    'auction_open': True,
                    'free_open': False, 
                    'msg': "🟢 LEILÃO ABERTO",
                    'deadline_msg': f"Fim do Leilão: {deadline}",
                    'next_round': next_round_idx,
                    'next_start': next_start
                }
            elif hours_to_next > 2:
                # Phase 2: Free open
                deadline = fmt_deadline(next_start - 2*3600)
                return {
                    'status': 'FREE_OPEN',
                    'auction_open': False,
                    'free_open': True,
                    'msg': "🟡 FREE AGENCY ABERTA (Pós-Leilão)",
                    'deadline_msg': f"Fecha em: {deadline}",
                    'next_round': next_round_idx,
                    'next_start': next_start
                }
            else:
                # Locked (Pre-match)
                return {
                    'status': 'LOCKED',
                    'auction_open': False,
                    'free_open': False,
                    'msg': "🔴 MERCADO FECHADO (Pré-Jogo)",
                    'deadline_msg': f"Rodada começa em {hours_to_next*60:.0f} min",
                    'next_round': next_round_idx,
                    'next_start': next_start
                }
        else:
            # Gap <= 48h: No Auction, Free Only.
            if hours_to_next > 2:
                deadline = fmt_deadline(next_start - 2*3600)
                return {
                    'status': 'FREE_OPEN_ONLY',
                    'auction_open': False,
                    'free_open': True,
                    'msg': "🔵 FREE AGENCY ABERTA",
                    'deadline_msg': f"Fecha em: {deadline}",
                    'next_round': next_round_idx,
                    'next_start': next_start
                }
            else:
                 return {
                    'status': 'LOCKED',
                    'auction_open': False,
                    'free_open': False,
                    'msg': "🔴 MERCADO FECHADO (Pré-Jogo)",
                    'deadline_msg': f"Rodada começa em {hours_to_next*60:.0f} min",
                    'next_round': next_round_idx,
                    'next_start': next_start
                }

    except Exception as e:
        return {
            'status': 'ERROR',
            'auction_open': False,
            'free_open': False,
            'msg': f"Erro ao calcular status: {e}",
            'next_round': None
        }

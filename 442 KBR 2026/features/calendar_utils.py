import pandas as pd
import streamlit as st
from datetime import datetime, timedelta, timezone
import time
from features.auth import get_client

@st.cache_data(ttl=60, show_spinner=False)
def get_game_state(target_round=None):
    """
    Determines the current game state:
    - Auction Open/Closed
    - Free Agency Open/Closed
    - Deadlines
    If target_round is provided, checks status for that specific round.
    """
    try:
        client, sh = get_client()
        ws = sh.worksheet("HOUR")
        data = ws.get_all_records()
        df = pd.DataFrame(data)
        
        # Ensure numeric for rodada
        df['rodada'] = pd.to_numeric(df['rodada'], errors='coerce')
        df = df.sort_values(by='rodada')

        # Helper to parse GMT-3 String ("dd/mm/yyyy HH:MM") back to UTC Timestamp - KEEPING FOR SAFETY
        def parse_gmt3_to_utc_ts(date_str):
            if not date_str or str(date_str).lower() == 'nan': return 0
            try:
                dt_naive = datetime.strptime(str(date_str), "%d/%m/%Y %H:%M")
                tz_gmt3 = timezone(timedelta(hours=-3))
                dt_aware = dt_naive.replace(tzinfo=tz_gmt3)
                return dt_aware.timestamp()
            except:
                return 0

        # Current Timestamp (UTC)
        now_ts = time.time()
        
        next_round_row = None
        
        if target_round:
            # Find specific round
            rows = df[df['rodada'] == int(target_round)]
            if not rows.empty:
                next_round_row = rows.iloc[0]
            else:
                 return {
                     'status': 'ERROR',
                     'msg': f'Rodada {target_round} não encontrada.',
                     'next_round': target_round
                 }
        else:
            # Logic: Find the first round where 'fim_escalacao' (Lineup Deadline) is in the future.
            # If all passed, season finished.
            for idx, row in df.iterrows():
                # Use 'fim_escalacao' (timestamp) directly if available
                lineup_end = float(row.get('fim_escalacao', 0))
                
                # If 0, maybe try parsing? (Should be populated by extraction)
                if lineup_end == 0:
                     lineup_end = parse_gmt3_to_utc_ts(row.get('fim_escalacao_fmt'))
                
                if lineup_end > now_ts:
                    next_round_row = row
                    break
                
        if next_round_row is None:
             return {
                 'status': 'Season Finished',
                 'auction_open': False,
                 'free_open': False,
                 'msg': 'Temporada encerrada / Rodada Passada.',
                 'next_round': None
             }
        
        # Target Round Data
        r_idx = next_round_row.get('rodada')
        
        # Timestamps for Logic
        ts_auc_start = float(next_round_row.get('inicio_leilao', 0))
        ts_auc_end = float(next_round_row.get('fim_leilao', 0))
        ts_free_start = float(next_round_row.get('inicio_free', 0))
        ts_free_end = float(next_round_row.get('fim_free', 0))
        # Lineup End is usually Free End
        
        # Strings for Display
        str_auc_end = next_round_row.get('fim_leilao_fmt', '')
        str_free_end = next_round_row.get('fim_free_fmt', '')
        
        common_data = {
            'next_round': r_idx,
            'next_start': float(next_round_row.get('primeiro', 0)), # First Game match start
            'lineup_msg': f"Fecha: {str_free_end}",
            # Raw Timestamps from HOUR sheet
            'ts_auc_start': ts_auc_start,
            'ts_auc_end': ts_auc_end,
            'ts_free_start': ts_free_start,
            'ts_free_end': ts_free_end,
            'ts_lineup_start': float(next_round_row.get('inicio_escalacao', 0)),
            'ts_lineup_end': float(next_round_row.get('fim_escalacao', 0))
        }

        # DETERMINE STATUS
        
        # 1. Auction Open?
        if ts_auc_start > 0 and ts_auc_end > 0 and now_ts >= ts_auc_start and now_ts < ts_auc_end:
            return {
                'status': 'AUCTION_OPEN',
                'auction_open': True,
                'free_open': False,
                'msg': "🟢 LEILÃO ABERTO",
                'deadline_msg': f"Fim do Leilão: {str_auc_end}",
                'closing_ts': ts_auc_end,
                **common_data
            }
            
        # 2. Free Agency Open?
        if ts_free_start > 0 and ts_free_end > 0 and now_ts >= ts_free_start and now_ts < ts_free_end:
             return {
                'status': 'FREE_OPEN', # Unified status, app can distinguish if it was post-auction or direct
                'auction_open': False, # Explicitly closed
                'free_open': True,
                'msg': "🟡 FREE AGENCY ABERTA",
                'deadline_msg': f"Fecha em: {str_free_end}",
                'closing_ts': ts_free_end,
                **common_data
            }
            
        # 3. If neither -> Locked (Pre-Match or Post-Deadline)
        # Calculate time to start match
        first_game = float(next_round_row.get('primeiro', 0))
        hours_to_game = (first_game - now_ts) / 3600.0 if first_game else 0
        
        return {
            'status': 'LOCKED',
            'auction_open': False,
            'free_open': False,
            'msg': "🔴 MERCADO FECHADO (Aguardando Rodada)",
            'deadline_msg': f"Rodada começa em {hours_to_game:.1f}h",
            'closing_ts': first_game,
            **common_data
        }

    except Exception as e:
        return {
            'status': 'ERROR',
            'auction_open': False,
            'free_open': False,
            'msg': f"Erro ao calcular status: {e}",
            'next_round': None
        }

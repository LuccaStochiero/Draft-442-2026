import pandas as pd
import streamlit as st
from datetime import datetime, timedelta, timezone
import time
from features.auth import get_client

@st.cache_data(ttl=60, show_spinner=False)
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
        
        # Ensure numeric for rodada
        df['rodada'] = pd.to_numeric(df['rodada'], errors='coerce')
        df = df.sort_values(by='rodada')

        # Helper to parse GMT-3 String ("dd/mm/yyyy HH:MM") back to UTC Timestamp
        def parse_gmt3_to_utc_ts(date_str):
            if not date_str or str(date_str).lower() == 'nan': return None
            try:
                # Parse naive string
                dt_naive = datetime.strptime(str(date_str), "%d/%m/%Y %H:%M")
                # Assume this is GMT-3. To get UTC, we subtract (-3) => Add 3 hours
                # Or simplistic: timestamp() assumes Local (System).
                # We want explicitly: Input is GMT-3. Output is UTC timestamp.
                
                # Method: Create timezone-aware DT in GMT-3
                tz_gmt3 = timezone(timedelta(hours=-3))
                dt_aware = dt_naive.replace(tzinfo=tz_gmt3)
                return dt_aware.timestamp()
            except:
                return None

        # Calculate Logic Timestamps from Formatted columns
        # Priority: use `_fmt` columns if available (Source of Truth for User Edits)
        # Fallback: use raw columns if available
        
        if 'primeiro_fmt' in df.columns:
            df['start_ts'] = df['primeiro_fmt'].apply(parse_gmt3_to_utc_ts)
        elif 'primeiro' in df.columns:
            df['start_ts'] = pd.to_numeric(df['primeiro'], errors='coerce')
        else:
             df['start_ts'] = 0
             
        if 'ultimo_fmt' in df.columns:
            df['end_ts'] = df['ultimo_fmt'].apply(parse_gmt3_to_utc_ts)
        elif 'ultimo' in df.columns:
            df['end_ts'] = pd.to_numeric(df['ultimo'], errors='coerce')
        else:
            df['end_ts'] = 0

        # Current Timestamp (UTC)
        now_ts = time.time()
        
        # Find Next Round (first round where 'start_ts' > now)
        future_rounds = df[(df['start_ts'] > now_ts) & (df['start_ts'].notna()) & (df['start_ts'] > 0)]
        
        if future_rounds.empty:
            return {
                'status': 'Season Finished',
                'auction_open': False,
                'free_open': True,
                'msg': 'Temporada encerrada ou sem próximas rodadas.',
                'next_round': None
            }
        
        next_round_row = future_rounds.iloc[0]
        next_round_idx = next_round_row['rodada']
        next_start = next_round_row['start_ts']
        
        # Find Previous Round (to calc gap)
        prev_round_row = df[df['rodada'] == next_round_idx - 1]
        
        if prev_round_row.empty:
            # If next is round 1, gap is infinite -> Auction ON
            gap_hours = 999.0
        else:
            prev_end = prev_round_row.iloc[0]['end_ts']
            if not prev_end or pd.isna(prev_end) or prev_end == 0:
                # Fallback if previous round has no end data
                 gap_hours = 999.0
            else:
                gap_seconds = next_start - prev_end
                gap_hours = gap_seconds / 3600.0
            
        # Deadlines based on Next Start
        hours_to_next = (next_start - now_ts) / 3600.0
        
        # Format Deadline helper (Input TS is UTC, we want to Display GMT-3)
        def fmt_deadline(ts):
            # Convert UTC TS to GMT-3 DT
            dt = datetime.fromtimestamp(ts, timezone.utc) - timedelta(hours=3)
            day_name = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sab", "Dom"][dt.weekday()]
            return f"{day_name} {dt.strftime('%d/%m às %H:%M')}"
            
        # Hard Deadline (2h before game) - Always calculated
        deadline_2h_ts = next_start - 2 * 3600
        str_deadline_2h = fmt_deadline(deadline_2h_ts)

        common_data = {
            'next_round': next_round_idx,
            'next_start': next_start,
            'lineup_msg': str_deadline_2h
        }

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
                    **common_data
                }
            elif hours_to_next > 2:
                # Phase 2: Free open
                # deadline = fmt_deadline(next_start - 2*3600)
                return {
                    'status': 'FREE_OPEN',
                    'auction_open': False,
                    'free_open': True,
                    'msg': "🟡 FREE AGENCY ABERTA (Pós-Leilão)",
                    'deadline_msg': f"Fecha em: {str_deadline_2h}",
                    **common_data
                }
            else:
                # Locked (Pre-match)
                return {
                    'status': 'LOCKED',
                    'auction_open': False,
                    'free_open': False,
                    'msg': "🔴 MERCADO FECHADO (Pré-Jogo)",
                    'deadline_msg': f"Rodada começa em {hours_to_next*60:.0f} min",
                    **common_data
                }
        else:
            # Gap <= 48h: No Auction, Free Only.
            if hours_to_next > 2:
                # deadline = fmt_deadline(next_start - 2*3600)
                return {
                    'status': 'FREE_OPEN_ONLY',
                    'auction_open': False,
                    'free_open': True,
                    'msg': "🔵 FREE AGENCY ABERTA",
                    'deadline_msg': f"Fecha em: {str_deadline_2h}",
                    **common_data
                }
            else:
                 return {
                    'status': 'LOCKED',
                    'auction_open': False,
                    'free_open': False,
                    'msg': "🔴 MERCADO FECHADO (Pré-Jogo)",
                    'deadline_msg': f"Rodada começa em {hours_to_next*60:.0f} min",
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

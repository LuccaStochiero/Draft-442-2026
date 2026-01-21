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
        
        # Determine Current/Next Round based on User Rule:
        # "SE o tempo atual esta antes da (inicio da ultima partida da rodada + 4, está nessa rodada."
        # If after, check next.
        
        next_round_row = None
        
        # Iterate sorted rounds to find the first one that fits the criteria or is future
        for idx, row in df.iterrows():
            # Must have valid start/end
            if pd.isna(row.get('start_ts')) or pd.isna(row.get('end_ts')) or row['start_ts'] == 0:
                continue
                
            # Logic: Round is "Active/Current" if Now < (LastGameStart + 4h)
            # Use 'end_ts' which comes from 'ultimo_fmt' (Last Game Start)
            # Wait, 'ultimo' usually means Last Game Time.
            # User said "inicio da ultima partida". 
            # Code line 54 maps 'ultimo_fmt' to 'end_ts'. Assuming 'ultimo_fmt' IS the start time of the last match.
            
            threshold = row['end_ts'] + (4 * 3600)
            
            if now_ts < threshold:
                next_round_row = row
                break
        
        if next_round_row is None:
             # No future rounds found
             return {
                 'status': 'Season Finished',
                 'auction_open': False,
                 'free_open': True,
                 'msg': 'Temporada encerrada.',
                 'next_round': None
             }
        
        # Now 'next_round_row' is the target round.
        # It could be the CURRENTLY RUNNING round (if Now > Start but < End+4h)
        # Or it could be a FUTURE round.
        
        next_round_idx = next_round_row['rodada']
        next_start = next_round_row['start_ts']
        
        # Recalculate 'future_rounds' just for reference? No, we have the row.
        # But we need 'prev_round_row' logic below.
        
        
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
                deadline_ts = next_start - 24*3600
                deadline = fmt_deadline(deadline_ts)
                return {
                    'status': 'AUCTION_OPEN',
                    'auction_open': True,
                    'free_open': False, 
                    'msg': "🟢 LEILÃO ABERTO",
                    'deadline_msg': f"Fim do Leilão: {deadline}",
                    'closing_ts': deadline_ts,
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
                    'closing_ts': deadline_2h_ts,
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
                    'closing_ts': next_start, # Opens after game? No, closes at start.
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
                    'closing_ts': deadline_2h_ts,
                    **common_data
                }
            else:
                 return {
                    'status': 'LOCKED',
                    'auction_open': False,
                    'free_open': False,
                    'msg': "🔴 MERCADO FECHADO (Pré-Jogo)",
                    'deadline_msg': f"Rodada começa em {hours_to_next*60:.0f} min",
                    'closing_ts': next_start,
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

import pandas as pd
import streamlit as st
from features.auth import get_client
from features.live_stats import calculate_points, STATS_SHEET, POINTS_SHEET

def debug_player(target_pid="1150391"):
    print(f"--- Debugging Player ID: {target_pid} ---")
    
    client, sh = get_client()
    
    # 1. Fetch Raw Stats
    ws_stats = sh.worksheet(STATS_SHEET)
    data_stats = ws_stats.get_all_records()
    df_stats = pd.DataFrame(data_stats)
    
    # Filter (The player_id in sheet might be a URL or just ID)
    # Check both
    print("Searching in PLAYERS_STATS...")
    
    # helper to check
    def match(val):
        return target_pid in str(val)
        
    player_stats = df_stats[df_stats['player_id'].apply(match)]
    
    if player_stats.empty:
        print("❌ Player NOT found in PLAYERS_STATS.")
    else:
        print(f"✅ Found {len(player_stats)} records in PLAYERS_STATS.")
        for _, row in player_stats.iterrows():
            print("\n[RAW STATS]")
            for k, v in row.items():
                if v != 0 and v != '' and v != '0':
                    print(f"  {k}: {v}")
            
            # Recalculate to see breakdown
            # We need to pass a DataFrame to calculate_points
            single_df = pd.DataFrame([row])
            
            # We want the breakdown columns (L_nota, etc), but calculate_points returns only final.
            # So I will replicate the logic here or modify the function? 
            # Replicating logic for display is safer to assume what 'live_stats' is doing.
            # Actually, let's just use the function and verify the final match first.
            
            res = calculate_points(single_df)
            print("\n[CALCULATED SCORE by System]")
            print(res)
            
            # Let's manually print the logic breakdown based on the row:
            print("\n[LOGIC BREAKDOWN ESTIMATE]")
            rating = float(row.get('rating', 0))
            minutes = int(row.get('minutesPlayed', 0))
            
            # 1. Nota
            l_nota = 0
            if rating >= 9: l_nota = 3
            elif rating >= 8: l_nota = 2
            elif rating >= 7: l_nota = 1
            elif rating >= 6.5: l_nota = 0
            elif rating >= 6: l_nota = -1
            elif rating >= 3: l_nota = -2
            print(f"  Rating {rating} -> L_nota: {l_nota}")
            
            # 2. Negativos
            # (df['ownGoals'] * -2) + (df['yellowCards'] * -1) + (df['totalOffside'] * -0.25) +
            # (df['dispossessed'] * -0.25) + (df['penaltyConceded'] * -2) + 
            # (df['penaltyMiss'] * -3) + (df['fouls'] * -0.5)
            n_og = float(row.get('ownGoals', 0)) * -2
            n_yc = float(row.get('yellowCards', 0)) * -1
            n_off = float(row.get('totalOffside', 0)) * -0.25
            n_disp = float(row.get('dispossessed', 0)) * -0.25
            n_pc = float(row.get('penaltyConceded', 0)) * -2
            n_pm = float(row.get('penaltyMiss', 0)) * -3
            n_fls = float(row.get('fouls', 0)) * -0.5
            l_neg = n_og + n_yc + n_off + n_disp + n_pc + n_pm + n_fls
            print(f"  Negativos -> {l_neg} (Fouls: {row.get('fouls')}, Yellow: {row.get('yellowCards')}, Off: {row.get('totalOffside')}, Disp: {row.get('dispossessed')})")

            # 3. Red
            l_red = -3 if float(row.get('redCards', 0)) > 0 else 0
            print(f"  Red -> {l_red}")
            
            # 4. Part
            l_part = 1 if minutes > 75 else 0
            print(f"  Participation (>75min) -> {l_part} ({minutes} min)")
            
            # 5. Bonus
            # p_passe = np.where(df['totalPass']>0, df['accuratePass']/df['totalPass'], 0)
            t_pass = float(row.get('totalPass', 0))
            a_pass = float(row.get('accuratePass', 0))
            p_pass_ratio = a_pass/t_pass if t_pass > 0 else 0
            
            t_long = float(row.get('totalLongBalls', 0))
            a_long = float(row.get('accurateLongBalls', 0))
            p_long_ratio = a_long/t_long if t_long > 0 else 0
            
            duel_w = float(row.get('duelWon', 0))
            duel_l = float(row.get('duelLost', 0))
            duel_t = duel_w + duel_l
            p_duel_ratio = duel_w/duel_t if duel_t > 0 else 0
            
            won_cont = float(row.get('wonContest', 0)) # Dribles certos? check extraction
            # Code: p_drib = np.where(df['totalContest']>0, df['wonContest']/df['totalContest'], 0)
            tot_cont = float(row.get('totalContest', 0))
            p_drib_ratio = won_cont/tot_cont if tot_cont > 0 else 0
            
            l_bonus = 0
            if t_pass >= 40 and p_pass_ratio >= 0.90: l_bonus += 1
            if a_long >= 3 and p_long_ratio >= 0.60: l_bonus += 1
            if duel_w >= 3 and p_duel_ratio >= 0.50: l_bonus += 1 # WARNING: Code says duelWon >= 3
            if won_cont >= 3 and p_drib_ratio >= 0.60: l_bonus += 1
            
            print(f"  Bonus -> {l_bonus}")
            print(f"    Pass: {t_pass} ({p_pass_ratio:.2f})")
            print(f"    Long: {a_long}/{t_long} ({p_long_ratio:.2f})")
            print(f"    Duel: {duel_w}/{duel_t} ({p_duel_ratio:.2f})")
            print(f"    Drib: {won_cont}/{tot_cont} ({p_drib_ratio:.2f})")

            # 6. Acoes
            # (df['keyPass'] * 0.75) + (df['penaltySave'] * 5) + (df['penaltyWon'] * 2) +
            # (df['wasFouled'] * 0.5) + (df['shotOffTarget'] * 0.75) + 
            # (real_shot * 1.5) + (df['hitWoodwork'] * 3)
            # real_shot = (df['onTargetScoringAttempt'] - df['hitWoodwork'] - df['goals']).clip(lower=0)
            otp = float(row.get('onTargetScoringAttempt', 0))
            wood = float(row.get('hitWoodwork', 0))
            goals = float(row.get('goals', 0))
            real_shot = max(0, otp - wood - goals)
            
            l_acoes = (
                (float(row.get('keyPass', 0)) * 0.75) +
                (float(row.get('penaltySave', 0)) * 5) +
                (float(row.get('penaltyWon', 0)) * 2) +
                (float(row.get('wasFouled', 0)) * 0.5) +
                (float(row.get('shotOffTarget', 0)) * 0.75) +
                (real_shot * 1.5) +
                (wood * 3)
            )
            print(f"  Acoes -> {l_acoes}")
            print(f"    KeyPass: {row.get('keyPass')}, Fouled: {row.get('wasFouled')}, ShotOff: {row.get('shotOffTarget')}")
            print(f"    OnTarget: {otp}, Goals: {goals}, Wood: {wood} -> RealShot: {real_shot}")

            # 7. Defesa / 8. GK
            pos = str(row.get('Posição', 'M'))
            l_def = 0
            l_gk = 0
            if pos == 'G':
                 # (df['savedShotsFromInsideTheBox']*1.0) + (saves_out*0.5) + 
                 # (df['accurateKeeperSweeper']*1) + (df['goalLineClearance']*2)+
                 # (df['goalsPrevented']*2), 0
                 # saves_out = (df['saves'] - df['savedShotsFromInsideTheBox']).clip(lower=0)
                 saves = float(row.get('saves', 0))
                 saved_in = float(row.get('savedShotsFromInsideTheBox', 0))
                 saves_out = max(0, saves - saved_in)
                 
                 l_gk = (
                     (saved_in * 1.0) + (saves_out * 0.5) +
                     (float(row.get('accurateKeeperSweeper', 0)) * 1) +
                     (float(row.get('goalLineClearance', 0)) * 2) + 
                     (float(row.get('goalsPrevented', 0)) * 2)
                 )
                 print(f"  GK Points -> {l_gk} (Saves: {saves})")
            else:
                # (df['totalClearance']*0.1) + (df['outfielderBlock']*0.25) + 
                # (df['interceptionWon']*0.5) + (df['wonTackle']*0.75) + (df['goalLineClearance']*2)
                l_def = (
                    (float(row.get('totalClearance', 0)) * 0.1) +
                    (float(row.get('outfielderBlock', 0)) * 0.25) +
                    (float(row.get('interceptionWon', 0)) * 0.5) +
                    (float(row.get('wonTackle', 0)) * 0.75) +
                    (float(row.get('goalLineClearance', 0)) * 2)
                )
                print(f"  Def Points -> {l_def}")
                print(f"    Clear: {row.get('totalClearance')}, Block: {row.get('outfielderBlock')}, Int: {row.get('interceptionWon')}, Tackle: {row.get('wonTackle')}")

            # 9. Scout / Pos
            # Goals 6, Assist 4
            pts_g = goals * 6
            pts_a = float(row.get('goalAssist', 0)) * 4
            
            # SG
            # has_sg = (df['gols_sofridos_partida'] == 0) & (df['minutesPlayed'] > 0)
            # G: 4, D: 3
            gs = float(row.get('gols_sofridos_partida', 10))
            sg_pts = 0
            if gs == 0 and minutes > 0:
                if pos == 'G': sg_pts = 4
                elif pos == 'D': sg_pts = 3
                
            # Def Conceded
            # np.where(df['Posição'].isin(['G','D']), df['gols_sofridos_partida']*-0.5, 0)
            def_conc = 0
            if pos in ['G', 'D']:
                def_conc = gs * -0.5
            
            l_pos = pts_g + pts_a + sg_pts + def_conc
            print(f"  Pos/Scout -> {l_pos}")
            print(f"    Gols: {goals}, Assist: {row.get('goalAssist')}, GS: {gs}, Pos: {pos}")
            
            total = l_nota + l_neg + l_red + l_part + l_bonus + l_acoes + l_def + l_gk + l_pos
            print(f"TOTAL ESTIMATED: {total}")

    # 2. Fetch Points Sheet
    print("\n\nSearching in PLAYER_POINTS...")
    ws_points = sh.worksheet(POINTS_SHEET)
    data_points = ws_points.get_all_records()
    df_points = pd.DataFrame(data_points)
    
    player_points = df_points[df_points['player_id'].apply(match)]
    if player_points.empty:
         print("❌ Player NOT found in PLAYER_POINTS.")
    else:
        print(f"✅ Found {len(player_points)} records in PLAYER_POINTS.")
        for _, row in player_points.iterrows():
             print(f"  Game: {row.get('game_id')} -> Points: {row.get('pontuacao')}")

if __name__ == "__main__":
    debug_player()

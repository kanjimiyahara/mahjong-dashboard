# pyrefly: ignore [missing-import]
import streamlit as st
import pandas as pd
import glob
import os
import plotly.express as px
import plotly.graph_objects as go
import calendar
from datetime import date

st.set_page_config(page_title="Mahjong Score Analysis", layout="wide")

def infer_game_rates(players_data):
    """
    Dynamically infers the point rate and chip rate for a game.
    players_data: list of dicts with 'スコア', 'チップ_num', '収支'
    Returns: (point_rate, chip_rate)
    """
    approx_rates = []
    for d in players_data:
        s = d['スコア']
        b = d['収支']
        # Use players with significant scores to avoid chip values dominating the ratio
        if abs(s) >= 5:
            approx_rates.append(b / s)
            
    if not approx_rates:
        for d in players_data:
            if d['スコア'] != 0:
                approx_rates.append(d['収支'] / d['スコア'])
                
    if not approx_rates:
        return 0, 0  # Unknown
        
    avg_approx = sum(approx_rates) / len(approx_rates)
    
    # The true p_rate is likely the closest to avg_approx
    possible_p_rates = [0.1, 0.2, 0.3, 0.4, 0.5, 1.0, 2.0, 5.0, 10.0]
    p_rate = min(possible_p_rates, key=lambda x: abs(x - avg_approx))
    
    # Now deduce c_rate using the inferred p_rate
    c_rates = []
    for d in players_data:
        s = d['スコア']
        c = d['チップ_num']
        b = d['収支']
        if c != 0:
            c_rates.append((b - s * p_rate) / c)
            
    if c_rates:
        c_rate = max(0.0, sum(c_rates) / len(c_rates))
        c_rate = round(c_rate, 2)
    else:
        c_rate = 0.0
        
    return p_rate, c_rate

def render_calendar(df_target, title, key_prefix, show_mode_selector=False):
    st.header(title)
        
    dates = pd.to_datetime(df_target['日付']).dt.date
    df_for_cal = df_target.copy()
    df_for_cal['date_only'] = dates
    
    daily_stats = {}
    for d, group in df_for_cal.groupby('date_only'):
        group_played = group[group['参加フラグ']] if '参加フラグ' in group else group
        
        g_count = group_played['ゲームID'].nunique()
        if g_count == 0:
            continue
            
        bal_sum = group_played['収支'].sum()
        
        r_counts = group_played['順位'].value_counts()
        r1 = r_counts.get(1, 0)
        r2 = r_counts.get(2, 0)
        r3 = r_counts.get(3, 0)
        r4 = r_counts.get(4, 0)
        
        members_list = group_played['プレイヤー'].unique().tolist()
        
        daily_stats[d] = {
            'games': g_count,
            'balance': bal_sum,
            'ranks': f"{r1}/{r2}/{r3}/{r4}",
            'members': ", ".join(members_list)
        }
    
    if not daily_stats:
        st.info("No data available.")
        return
        
    all_dates = list(daily_stats.keys())
    min_date = min(all_dates)
    max_date = max(all_dates)
    
    month_options = []
    curr = date(min_date.year, min_date.month, 1)
    while curr <= date(max_date.year, max_date.month, 1):
        month_options.append(f"{curr.year}-{curr.month:02d}")
        if curr.month == 12:
            curr = date(curr.year + 1, 1, 1)
        else:
            curr = date(curr.year, curr.month + 1, 1)
    
    month_options.reverse()
    
    session_key = f"cal_{key_prefix}"
    if session_key not in st.session_state:
        st.session_state[session_key] = month_options[0] if month_options else ""

    def go_prev():
        if month_options and st.session_state[session_key] in month_options:
            idx = month_options.index(st.session_state[session_key])
            if idx < len(month_options) - 1:
                st.session_state[session_key] = month_options[idx + 1]
    
    def go_next():
        if month_options and st.session_state[session_key] in month_options:
            idx = month_options.index(st.session_state[session_key])
            if idx > 0:
                st.session_state[session_key] = month_options[idx - 1]

    col_nav1, col_nav2, col_nav3, col_nav4 = st.columns([1, 1, 3, 3])
    with col_nav1:
        st.markdown("<div style='padding-top:28px'></div>", unsafe_allow_html=True)
        st.button("◀ Prev", on_click=go_prev, key=f"prev_{key_prefix}", use_container_width=True)
    with col_nav2:
        st.markdown("<div style='padding-top:28px'></div>", unsafe_allow_html=True)
        st.button("Next ▶", on_click=go_next, key=f"next_{key_prefix}", use_container_width=True)
    with col_nav3:
        selected_month_str = st.selectbox("Select Calendar Month", month_options, key=session_key)
    with col_nav4:
        if show_mode_selector:
            cal_mode = st.radio("Display Mode", ["Games", "Balance"], horizontal=True, key=f"cal_mode_{key_prefix}")
        else:
            cal_mode = "Games"
            
    sel_year = int(selected_month_str[:4])
    sel_month = int(selected_month_str[5:7])
    
    m_games = 0
    m_bal = 0.0
    for d_dt, s in daily_stats.items():
        if d_dt.year == sel_year and d_dt.month == sel_month:
            m_games += s['games']
            m_bal += s['balance']
            
    m_color = "#2ca02c" if m_bal > 0 else "#d62728" if m_bal < 0 else "#888"
    html_summary = f'''
    <div class="anim-pop" style="margin-bottom: 20px; padding: 12px 20px; border-radius: 8px; background-color: rgba(128,128,128,0.05); border-left: 5px solid {m_color}; display: flex; align-items: center; justify-content: space-between;">
        <div style="font-size: 16px; color: #888; font-weight: bold;">{sel_year}-{sel_month:02d} Monthly Summary</div>
        <div>
            <span style="font-size: 14px; color: #888; margin-right: 5px;">Games:</span>
            <strong style="font-size: 20px; color: #1f77b4; margin-right: 20px;">{m_games} <span style="font-size:14px;">hanchan</span></strong>
            <span style="font-size: 14px; color: #888; margin-right: 5px;">Balance:</span>
            <strong style="font-size: 22px; color: {m_color};">{m_bal:+.1f}</strong>
        </div>
    </div>
    '''
    st.markdown(html_summary, unsafe_allow_html=True)
    
    cal = calendar.Calendar(firstweekday=6)
    month_days = cal.monthdatescalendar(sel_year, sel_month)
    
    html = '<table style="width:100%; border-collapse: collapse; text-align:center; font-family: sans-serif; margin-bottom: 20px;">'
    html += '<tr style="background-color: rgba(128,128,128,0.1);"><th>Sun</th><th>Mon</th><th>Tue</th><th>Wed</th><th>Thu</th><th>Fri</th><th>Sat</th></tr>'
    
    max_games = max([s['games'] for s in daily_stats.values()]) if daily_stats else 1
    max_bal = max([abs(s['balance']) for s in daily_stats.values()]) if daily_stats else 1
    if max_bal == 0: max_bal = 1
    
    today_date = date.today()
    
    for week in month_days:
        html += '<tr>'
        for day in week:
            is_current_month = day.month == sel_month
            is_today = (day == today_date)
            
            if is_current_month:
                color_style = "color: inherit;"
            else:
                color_style = "color: rgba(128, 128, 128, 0.5);"
                
            if is_today:
                bg_color = "rgba(44,160,44,0.15)"
                border_color = "#2ca02c"
                today_badge = '<div style="background-color:#2ca02c; color:white; border-radius:3px; font-size:10px; padding:2px 4px; display:inline-block; margin-left: 5px;">Today</div>'
            else:
                bg_color = "rgba(128,128,128,0.05)" if is_current_month else "rgba(128,128,128,0.01)"
                border_color = "rgba(128,128,128,0.3)" if is_current_month else "rgba(128,128,128,0.1)"
                today_badge = ''
            
            cell_content = f'<div style="{color_style} padding: 5px; font-size: 14px; text-align: left; font-weight: {"bold" if is_today else "normal"};">{day.day}{today_badge}</div>'
            stats = daily_stats.get(day, None)
            
            if stats:
                games = stats['games']
                bal = stats['balance']
                rank_str = stats['ranks']
                members_str = stats['members']
                
                if show_mode_selector:
                    hover_text = f"[Activity: {games} hanchan]&#10;Players: {members_str}&#10;Placement: {rank_str}&#10;Balance: {bal:+.1f}"
                else:
                    hover_text = f"[Activity: {games} hanchan]&#10;Players: {members_str}"
                    
                if cal_mode == "Games":
                    size = 28 + min((games / max_games) * 32, 32)
                    alpha = 0.5 + (games / max_games) * 0.5
                    color_rgba = f"rgba(65, 170, 210, {alpha})"
                    text_disp = str(games)
                    font_size = size * 0.45
                else:
                    abs_bal = abs(bal)
                    size = 24 + min((abs_bal / max_bal) * 36, 36)
                    alpha = 0.4 + (abs_bal / max_bal) * 0.6
                    
                    if bal > 0:
                        color_rgba = f"rgba(30, 144, 255, {alpha})"
                    elif bal < 0:
                        color_rgba = f"rgba(255, 69, 0, {alpha})"
                    else:
                        color_rgba = f"rgba(150, 150, 150, {alpha})"
                        
                    text_disp = f"{int(bal):+d}"
                    font_size = size * 0.32
                
                shadow_rgba = color_rgba.replace(str(alpha)+")", str(alpha*0.6)+")") if str(alpha)+")" in color_rgba else "rgba(0,0,0,0.3)"
                
                circle_html = f'<div title="{hover_text}" style="width: {size}px; height: {size}px; border-radius: 50%; background-color: {color_rgba}; margin: auto; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; font-size: {font_size}px; box-shadow: 0 0 10px {shadow_rgba}; cursor: help;">{text_disp}</div>'
                cell_content += circle_html
            else:
                cell_content += '<div style="height: 60px;"></div>'
                
            html += f'<td style="border: 1px solid {border_color}; background-color: {bg_color}; vertical-align: top; width: 14%; height: 90px;">{cell_content}</td>'
        html += '</tr>'
    html += '</table>'
    
    st.markdown(html, unsafe_allow_html=True)

def load_data(folder_paths=["scores"], uploaded_files=None):
    # Collect (source, filename) tuples from folder
    all_sources = []
    for fp in folder_paths:
        if os.path.exists(fp):
            for root, _, files in os.walk(fp):
                for file in files:
                    if file.endswith(".csv"):
                        path = os.path.join(root, file)
                        all_sources.append((path, os.path.basename(path)))
    
    # Sort folder files descending
    all_sources.sort(key=lambda x: x[1], reverse=True)
    
    # Add uploaded files (pandas accepts file-like objects directly)
    if uploaded_files:
        for uf in uploaded_files:
            all_sources.append((uf, uf.name))
    
    if not all_sources:
        return pd.DataFrame()
    
    game_records = []
    seen_signatures = set()
    seen_score_signatures = set()  # For detecting duplicates caused by player name changes
    
    for source, fname in all_sources:
        try:
            df = pd.read_csv(source)
            # Remove leading/trailing spaces in columns
            df.columns = [str(c).strip() for c in df.columns]

            # Dynamically identify players
            players = set()
            for col in df.columns:
                if col.endswith('点数'):
                    players.add(col.replace('点数', '').strip())

            for index, row in df.iterrows():
                original_date = str(row.get('日付', '')).strip()
                date = original_date
                game_num = row.get('回戦数', 0)
                

                game_participants = []
                for p in players:
                    score = row.get(f'{p} 点数')
                    points = row.get(f'{p} スコア')
                    chips = row.get(f'{p} チップ')
                    balance = row.get(f'{p} 収支')

                    pts = float(score) if pd.notna(score) and str(score).strip() != '-' else 0.0
                    sc = float(points) if pd.notna(points) and str(points).strip() != '-' else 0.0
                    cp_str = str(chips).strip() if pd.notna(chips) and str(chips).strip() != 'nan' else '-'
                    cp_num = float(cp_str) if cp_str not in ['-', '', 'nan'] else 0.0
                    
                    bal_str = str(balance).strip()
                    is_no_rate = False
                    
                    # If balance is not entered but score exists, treat as no-rate
                    if pd.isna(balance) or bal_str in ['-', '']:
                        if sc != 0.0 or pts != 0.0:
                            bal = 0.0
                            is_no_rate = True
                        else:
                            continue
                    else:
                        bal = float(balance) / 100.0 if bal_str != '-' else 0.0
                    
                    # Skip players sitting out
                    if pts == 0.0 and sc == 0.0 and cp_num == 0.0 and bal == 0.0:
                        continue
                        
                    is_playing = (pts != 0.0) or (sc != 0.0)
                    
                    p_name = p
                        
                    game_participants.append({
                        'プレイヤー': p_name,
                        '元プレイヤー名': p,
                        '点数': pts,
                        'スコア': sc,
                        'チップ': cp_str,
                        'チップ_num': cp_num,
                        '収支': bal,
                        '参加フラグ': is_playing,
                        'ノーレート': is_no_rate,
                        '元データ行番号': index
                    })

                # Calculate ranking among actual players
                playing_pts = [(d['プレイヤー'], d['点数']) for d in game_participants if d['参加フラグ']]
                playing_pts.sort(key=lambda x: x[1], reverse=True)
                ranks = {p: rank+1 for rank, (p, _) in enumerate(playing_pts)}
                
                for d in game_participants:
                    d['順位'] = ranks.get(d['プレイヤー'], None)
                
                # Deduplication by game signature
                sig_participants = sorted(game_participants, key=lambda x: x['元プレイヤー名'])
                sig_elements = [str(date), str(game_num)]
                for d in sig_participants:
                    sig_elements.append(f"{d['元プレイヤー名']}:{d['点数']}:{d['チップ_num']}")
                game_sig = "||".join(sig_elements)
                
                if game_sig in seen_signatures:
                    continue
                seen_signatures.add(game_sig)
                
                # Score-based deduplication (catches player name changes)
                active_participants = [d for d in game_participants if d['参加フラグ']]
                score_vals = sorted([d['点数'] for d in active_participants])
                score_pts = sorted([d['スコア'] for d in active_participants])
                score_chips = sorted([d['チップ_num'] for d in active_participants])
                score_sig = f"{date}||{game_num}||{'|'.join(str(s) for s in score_vals)}||{'|'.join(str(s) for s in score_pts)}||{'|'.join(str(s) for s in score_chips)}"
                
                if score_sig in seen_score_signatures:
                    continue
                seen_score_signatures.add(score_sig)
                
                # Infer rate
                p_rate, c_rate = infer_game_rates(game_participants)
                if p_rate == 0:     rate_name = "Unknown Rate"
                elif p_rate == 0.1: rate_name = "Tenichi ($0.1/pt)"
                elif p_rate == 0.2: rate_name = "Tenryan ($0.2/pt)"
                elif p_rate == 0.3: rate_name = "Tensan ($0.3/pt)"
                elif p_rate == 0.4: rate_name = "Tenyon ($0.4/pt)"
                elif p_rate == 0.5: rate_name = "Tengo ($0.5/pt)"
                elif p_rate == 1.0: rate_name = "Tenpin ($1.0/pt)"
                else: rate_name = f"${p_rate}/pt"
                
                is_game_no_rate = any(d['ノーレート'] for d in game_participants)
                if is_game_no_rate:
                    rate_name = "No Rate"
                
                for p_data in game_participants:
                    game_records.append({
                        'ファイル': fname,
                        '日付': date,
                        '回戦数': game_num,
                        'プレイヤー': p_data['プレイヤー'],
                        '点数': p_data['点数'],
                        'スコア': p_data['スコア'],
                        'チップ': p_data['チップ'],
                        'チップ_num': p_data['チップ_num'],
                        '収支': p_data['収支'],
                        '順位': p_data['順位'],
                        '参加フラグ': p_data['参加フラグ'],
                        '点数レート': p_rate,
                        'チップレート': c_rate,
                        'レート名': rate_name,
                        'ノーレートフラグ': is_game_no_rate,
                        '元データ行番号': p_data['元データ行番号']
                    })
        except Exception as e:
            st.error(f"Error reading file {fname}: {e}")

    if not game_records:
        return pd.DataFrame()

    res_df = pd.DataFrame(game_records)
    res_df = res_df.sort_values(['日付', 'ファイル', '元データ行番号']).reset_index(drop=True)
    res_df['ゲームID'] = res_df['ファイル'].astype(str) + '_' + res_df['元データ行番号'].astype(str)
    
    return res_df

st.title("🀄 Mahjong Score Analysis Dashboard")

st.markdown("""
<style>
@keyframes popIn {
    0% { opacity: 0; transform: scale(0.95) translateY(15px); }
    100% { opacity: 1; transform: scale(1) translateY(0); }
}
div[data-testid="stPlotlyChart"], div[data-testid="stMetric"], div[data-testid="stDataFrame"], .anim-pop {
    animation: popIn 0.6s cubic-bezier(0.16, 1, 0.3, 1) forwards !important;
}
</style>
""", unsafe_allow_html=True)

# ========================================
# Player Icon Utilities
# ========================================
import base64
from pathlib import Path

ICON_DIR = Path("icons")

@st.cache_data
def _load_icon_base64(player_name):
    """Load player icon as base64. Cached."""
    for ext in ['png', 'jpg', 'jpeg', 'webp']:
        path = ICON_DIR / f"{player_name}.{ext}"
        if path.exists():
            data = base64.b64encode(path.read_bytes()).decode()
            mime = 'jpeg' if ext == 'jpg' else ext
            return f"data:image/{mime};base64,{data}"
    return None

def get_player_icon(player_name, size=40):
    """Return player icon HTML. Falls back to initial circle if no image."""
    src = _load_icon_base64(player_name)
    if src:
        return f'<img src="{src}" style="width:{size}px;height:{size}px;border-radius:50%;object-fit:cover;vertical-align:middle;border:2px solid rgba(255,255,255,0.3);">'
    initial = player_name[0] if player_name else "?"
    colors = ['#1f77b4','#ff7f0e','#2ca02c','#d62728','#9467bd','#8c564b','#e377c2','#17becf']
    color = colors[hash(player_name) % len(colors)]
    return f'<div style="display:inline-flex;align-items:center;justify-content:center;width:{size}px;height:{size}px;border-radius:50%;background:{color};color:white;font-weight:bold;font-size:{size//2}px;vertical-align:middle;">{initial}</div>'

@st.cache_data
def get_player_icon_circle(player_name):
    """Return circular cropped icon as data URI for Plotly. Returns None if no image."""
    from PIL import Image, ImageDraw
    import io
    for ext in ['png', 'jpg', 'jpeg', 'webp']:
        path = ICON_DIR / f"{player_name}.{ext}"
        if path.exists():
            img = Image.open(path).convert("RGBA")
            s = min(img.width, img.height)
            left = (img.width - s) // 2
            top = (img.height - s) // 2
            img = img.crop((left, top, left + s, top + s))
            img = img.resize((200, 200), Image.LANCZOS)
            mask = Image.new('L', (200, 200), 0)
            draw = ImageDraw.Draw(mask)
            draw.ellipse((0, 0, 200, 200), fill=255)
            result = Image.new('RGBA', (200, 200), (0, 0, 0, 0))
            border_draw = ImageDraw.Draw(result)
            border_draw.ellipse((0, 0, 199, 199), fill=(255, 255, 255, 80))
            border_draw.ellipse((4, 4, 195, 195), fill=(0, 0, 0, 0))
            icon_layer = Image.new('RGBA', (200, 200), (0, 0, 0, 0))
            icon_layer.paste(img, (0, 0), mask)
            result = Image.alpha_composite(result, icon_layer)
            buf = io.BytesIO()
            result.save(buf, format='PNG')
            data = base64.b64encode(buf.getvalue()).decode()
            return f"data:image/png;base64,{data}"
    return None

# ----------------------------------------
# Sidebar: File Upload
# ----------------------------------------
st.sidebar.header("📂 Upload Score Files")
uploaded_files = st.sidebar.file_uploader(
    "Upload your CSV score files",
    type=["csv"],
    accept_multiple_files=True,
    help="Drag & drop one or more CSV files. Combined with the sample data already in the app."
)

if uploaded_files:
    st.sidebar.success(f"✅ {len(uploaded_files)} file(s) loaded")
else:
    st.sidebar.info("No files uploaded — showing sample data.")

df = load_data(
    folder_paths=[] if uploaded_files else ["scores"],
    uploaded_files=uploaded_files
)

if not df.empty:
    df['事前レーティング'] = 1500.0
    df['事後レーティング'] = 1500.0
    
    # Calculate score-based ratings for 4-player games
    playing_counts_elo = df[df['参加フラグ']].groupby('ゲームID')['プレイヤー'].count()
    yonma_games_elo = playing_counts_elo[playing_counts_elo == 4].index
    df_yonma_for_elo = df[df['ゲームID'].isin(yonma_games_elo) & df['参加フラグ']].copy()
    
    ratings_dict = {}
    W_SCORE = 0.10
    W_ELO = 0.01
    
    def get_r(p):
        return ratings_dict.get(p, 1500.0)
    
    for gid, group in df_yonma_for_elo.groupby('ゲームID', sort=False):
        players = group['プレイヤー'].tolist()
        scores = group['スコア'].tolist()
        indices = group.index.tolist()
        
        changes = {}
        
        table_avg_rating = sum(get_r(p) for p in players) / len(players)
        score_offset = sum(scores) / len(players)
        normalized_scores = [s - score_offset for s in scores]
        
        for p, s in zip(players, normalized_scores):
            r = get_r(p)
            change = (s * W_SCORE) + (table_avg_rating - r) * W_ELO
            changes[p] = change
        
        for p, idx in zip(players, indices):
            old_r = get_r(p)
            new_r = old_r + changes[p]
            df.at[idx, '事前レーティング'] = old_r
            df.at[idx, '事後レーティング'] = new_r
            ratings_dict[p] = new_r

if df.empty:
    st.info("No data found. Please save CSV score data in the `scores` folder.")
else:
    st.sidebar.header("📋 View Mode")
    if 'view_mode' not in st.session_state:
        st.session_state.view_mode = "Overview"
    view_mode = st.sidebar.radio("Select Mode", ["Overview", "Individual Stats", "Player Comparison", "Rankings (All)", "Fun Stats", "📈 Cumulative Summary"], key="view_mode")

    st.sidebar.header("📅 Data Period")
    date_mode = st.sidebar.radio(
        "Select Period",
        ["All Time", "Custom Period"],
        index=0
    )
    
    if date_mode == "Custom Period":
        min_dt = pd.to_datetime(df['日付']).min().date()
        max_dt = pd.to_datetime(df['日付']).max().date()
        date_sel = st.sidebar.date_input("Select Date Range", [min_dt, max_dt])
        if len(date_sel) == 2:
            start_d, end_d = date_sel
            df = df[(pd.to_datetime(df['日付']).dt.date >= start_d) & (pd.to_datetime(df['日付']).dt.date <= end_d)]
    
    st.sidebar.header("🔍 Filter Settings")
    include_norate = st.sidebar.checkbox("Include no-rate games", value=True)
    if not include_norate:
        df = df[~df['ノーレートフラグ']]
        
    rates = ["All"] + list(df['レート名'].dropna().unique())
    selected_rate = st.sidebar.selectbox("Filter by Rate", rates)
    
    if selected_rate != "All":
        df = df[df['レート名'] == selected_rate]
        
    # Separate sanma (3-player) data
    playing_counts = df[df['参加フラグ']].groupby('ゲームID')['プレイヤー'].count()
    sanma_games = playing_counts[playing_counts == 3].index
    yonma_games = playing_counts[playing_counts == 4].index

    df_sanma = df[df['ゲームID'].isin(sanma_games)].copy()
    df = df[df['ゲームID'].isin(yonma_games)].copy()
    
    if df.empty:
        st.warning("No 4-player (yonma) data matches the selected criteria.")
        st.stop()

    # Currency: USD fixed
    currency_symbol = '$'

    # Adding cumulative calculations
    df['累積収支'] = df.groupby('プレイヤー')['収支'].cumsum()
    df['累積スコア'] = df.groupby('プレイヤー')['スコア'].cumsum()
    
    # ---------------------------
    # Global Stats Calculation
    # ---------------------------
    all_players_global = df['プレイヤー'].dropna().unique()
    global_stats = []
    
    for p in all_players_global:
        p_df_all = df[df['プレイヤー'] == p]
        p_df_played = p_df_all[p_df_all['参加フラグ']]
        
        t_games = len(p_df_played)
        if t_games == 0:
            continue
            
        t_balance = p_df_all['収支'].sum()
        t_points = p_df_all['スコア'].sum()
        
        a_rank = p_df_played['順位'].mean()
        r_counts = p_df_played['順位'].value_counts()
        f_place = r_counts.get(1, 0)
        s_place = r_counts.get(2, 0)
        lst_place = r_counts.get(4, 0)
        
        t_rate = (f_place / t_games * 100) if t_games > 0 else 0.0
        rentai_rate = ((f_place + s_place) / t_games * 100) if t_games > 0 else 0.0
        l_avoid_rate = ((t_games - lst_place) / t_games * 100) if t_games > 0 else 0.0
        max_s = p_df_played['スコア'].max() if t_games > 0 else 0.0
        avg_score = p_df_played['スコア'].mean() if t_games > 0 else 0.0
        tobi_count = len(p_df_played[p_df_played['点数'] < 0])
        tobi_rate = (tobi_count / t_games * 100) if t_games > 0 else 0.0
        
        curr_rating = p_df_played['事後レーティング'].iloc[-1] if t_games > 0 else 1500.0
        max_rating = p_df_played['事後レーティング'].max() if t_games > 0 else 1500.0
        
        global_stats.append({
            'Player': p,
            'Games': t_games,
            'Current Rating': float(curr_rating),
            'Peak Rating': float(max_rating),
            'Total Balance': t_balance,
            'Total Score': t_points,
            'Avg Placement': float(a_rank) if pd.notna(a_rank) else None,
            '1st Rate (%)': float(t_rate),
            'Top-2 Rate (%)': float(rentai_rate),
            'Last Avoid (%)': float(l_avoid_rate),
            'Bust Rate (%)': float(tobi_rate),
            'Best Score': float(max_s),
            'Avg Score': float(avg_score)
        })
        
    summary_df = pd.DataFrame(global_stats)
    
    # Rankings for players with minimum qualifying games
    st.sidebar.markdown("---")
    st.sidebar.header("🏆 Ranking Settings")
    min_rank_options = [5, 10, 15, 20, 30, 50, 100]
    MIN_GAMES_FOR_RANKING = st.sidebar.selectbox("Min. Qualifying Games", min_rank_options, index=1)
    
    ranked_df = summary_df[summary_df['Games'] >= MIN_GAMES_FOR_RANKING].copy()
    total_ranked_players = len(ranked_df)
    
    if total_ranked_players > 0:
        ranked_df['Rating Rank'] = ranked_df['Current Rating'].rank(ascending=False, method='min')
        ranked_df['Balance Rank'] = ranked_df['Total Balance'].rank(ascending=False, method='min')
        ranked_df['Avg Placement Rank'] = ranked_df['Avg Placement'].rank(ascending=True, method='min')
        ranked_df['1st Rate Rank'] = ranked_df['1st Rate (%)'].rank(ascending=False, method='min')
        ranked_df['Top-2 Rate Rank'] = ranked_df['Top-2 Rate (%)'].rank(ascending=False, method='min')
        ranked_df['Last Avoid Rank'] = ranked_df['Last Avoid (%)'].rank(ascending=False, method='min')
        ranked_df['Best Score Rank'] = ranked_df['Best Score'].rank(ascending=False, method='min')
        ranked_df['Avg Score Rank'] = ranked_df['Avg Score'].rank(ascending=False, method='min')
        ranked_df['Bust Rate Rank'] = ranked_df['Bust Rate (%)'].rank(ascending=True, method='min')
        
    def get_rank_str(player_name, col_rank):
        if total_ranked_players == 0:
            return None
        row = ranked_df[ranked_df['Player'] == player_name]
        if row.empty:
            return f"N/A (< {MIN_GAMES_FOR_RANKING} games)"
        r = int(row.iloc[0][col_rank])
        return f"#{r} / {total_ranked_players}"
    
    if view_mode == "Overview":
        min_date = pd.to_datetime(df['日付']).min().strftime('%Y/%m/%d')
        max_date = pd.to_datetime(df['日付']).max().strftime('%Y/%m/%d')
        total_games = df['ゲームID'].nunique()
        total_days = pd.to_datetime(df['日付']).dt.date.nunique()
        total_players = df['プレイヤー'].dropna().nunique()
        
        html_kpi = f'''
        <div class="anim-pop" style="display: flex; gap: 20px; justify-content: space-between; margin-bottom: 30px;">
            <div style="flex: 1; background-color: rgba(128,128,128,0.05); padding: 20px; border-radius: 12px; border-top: 5px solid #1f77b4; box-shadow: 0 4px 6px rgba(0,0,0,0.1); text-align: center;">
                <div style="font-size: 16px; color: #888; margin-bottom: 10px;">📅 Data Collection Period</div>
                <div style="font-size: 20px; font-weight: bold; color: #1f77b4; line-height: 1.4;">{min_date}<br><span style="font-size:16px; color:#888;">to</span><br>{max_date}</div>
            </div>
            <div style="flex: 1; background-color: rgba(128,128,128,0.05); padding: 20px; border-radius: 12px; border-top: 5px solid #ff7f0e; box-shadow: 0 4px 6px rgba(0,0,0,0.1); text-align: center; display: flex; flex-direction: column; justify-content: center;">
                <div style="font-size: 16px; color: #888; margin-bottom: 10px;">🀄 Total Hanchan Played</div>
                <div style="font-size: 40px; font-weight: bold; color: #ff7f0e;">{total_games} <span style="font-size: 20px;">games</span></div>
            </div>
            <div style="flex: 1; background-color: rgba(128,128,128,0.05); padding: 20px; border-radius: 12px; border-top: 5px solid #2ca02c; box-shadow: 0 4px 6px rgba(0,0,0,0.1); text-align: center; display: flex; flex-direction: column; justify-content: center;">
                <div style="font-size: 16px; color: #888; margin-bottom: 10px;">🗓️ Days Played</div>
                <div style="font-size: 40px; font-weight: bold; color: #2ca02c;">{total_days} <span style="font-size: 20px;">days</span></div>
            </div>
            <div style="flex: 1; background-color: rgba(128,128,128,0.05); padding: 20px; border-radius: 12px; border-top: 5px solid #d62728; box-shadow: 0 4px 6px rgba(0,0,0,0.1); text-align: center; display: flex; flex-direction: column; justify-content: center;">
                <div style="font-size: 16px; color: #888; margin-bottom: 10px;">👥 Total Players</div>
                <div style="font-size: 40px; font-weight: bold; color: #d62728;">{total_players} <span style="font-size: 20px;">players</span></div>
            </div>
        </div>
        '''
        st.markdown(html_kpi, unsafe_allow_html=True)
        
        st.header("📊 Player Performance Summary")
        # Display sorted by number of games (descending)
        st.dataframe(summary_df.sort_values('Games', ascending=False).reset_index(drop=True), use_container_width=True)

        # --- Calendar ---
        render_calendar(df, "📅 Mahjong Calendar (All Activity)", "global")

        # --- Visualizations ---
        st.header("📈 Performance Trends")
        st.markdown("Cumulative balance and score trends by player.")
        
        # Filter UI
        ctrl_col1, ctrl_col2 = st.columns(2)
        
        with ctrl_col1:
            try:
                df['年月'] = pd.to_datetime(df['日付']).dt.strftime('%Y-%m')
            except:
                df['年月'] = df['日付'].astype(str).str[:7]
                
            month_options = ["All Time", "Last 30 Games"] + sorted(df['年月'].unique().tolist(), reverse=True)
            selected_month = st.selectbox("Select Period", month_options)
            
        with ctrl_col2:
            min_game_options = {"10+ games": 10, "20+ games (Default)": 20, "50+ games": 50, "All Players": 0}
            selected_min = st.selectbox("Min. games to appear on chart", list(min_game_options.keys()), index=1)
            min_games = min_game_options[selected_min]
            
        if selected_month == "Last 30 Games":
            last_30_game_ids = pd.Series(df['ゲームID'].unique()).tail(30)
            df_period = df[df['ゲームID'].isin(last_30_game_ids)].copy()
            period_label = "(Last 30 Games)"
        elif selected_month != "All Time":
            df_period = df[df['年月'] == selected_month].copy()
            period_label = f"({selected_month})"
        else:
            df_period = df.copy()
            period_label = "(All Time)"
        
        # Filter to players with enough games (based on total count across all time)
        player_counts = df[df['参加フラグ']]['プレイヤー'].value_counts()
        eligible_players = player_counts[player_counts >= min_games].index.tolist()
        
        df_chart = df_period[df_period['プレイヤー'].isin(eligible_players)].copy()
        
        if df_chart.empty:
            st.warning("No players meet this criteria in the selected period.")
        else:
            st.markdown(f"**{period_label}**")
            tab1, tab2, tab3 = st.tabs(["Cumulative Balance", "Cumulative Score", "Rating Trend"])
            
            # Recalculate cumulative within the selected period (starts from 0)
            df_chart['期間内_累積収支'] = df_chart.groupby('プレイヤー')['収支'].cumsum()
            df_chart['期間内_累積スコア'] = df_chart.groupby('プレイヤー')['スコア'].cumsum()
            
            # X-axis: sequential game count within the period
            unique_games = df_chart['ゲームID'].unique()
            game_to_seq = {g: i+1 for i, g in enumerate(unique_games)}
            df_chart['通算ゲーム数'] = df_chart['ゲームID'].map(game_to_seq)
            
            with tab1:
                pivot_balance = df_chart.pivot(index='通算ゲーム数', columns='プレイヤー', values='期間内_累積収支')
                pivot_balance = pivot_balance.reindex(range(1, len(unique_games) + 1)).ffill().fillna(0)
                st.line_chart(pivot_balance)
                
            with tab2:
                pivot_points = df_chart.pivot(index='通算ゲーム数', columns='プレイヤー', values='期間内_累積スコア')
                pivot_points = pivot_points.reindex(range(1, len(unique_games) + 1)).ffill().fillna(0)
                st.line_chart(pivot_points)

            with tab3:
                pivot_rating = df_chart.pivot(index='通算ゲーム数', columns='プレイヤー', values='事後レーティング')
                pivot_rating = pivot_rating.reindex(range(1, len(unique_games) + 1)).ffill()
                pivot_rating = pivot_rating.fillna(1500.0)
                valid_cols = list(pivot_rating.columns)
                if valid_cols:
                    st.line_chart(pivot_rating[valid_cols])
                else:
                    st.info("No players available for rating trend display.")

        # --- Game Log & Validation ---
        st.header("🗂️ Hanchan Log (Game-by-Game Records)")
        
        # Aggregate data by game
        game_log_data = []
        for game_id, group in df.groupby('ゲームID'):
            date = group['日付'].iloc[0]
            game_num = group['回戦数'].iloc[0]
            rate = group['レート名'].iloc[0]
            
            played_group = group[group['参加フラグ']].sort_values('順位')
            
            participants_info = []
            for _, row in played_group.iterrows():
                p = row['プレイヤー']
                s = row['スコア']
                participants_info.append(f"{p}({s})")
                
            game_log_data.append({
                'Date': date,
                'Game #': game_num,
                'Rate': rate,
                'Players': len(played_group),
                'Members': ", ".join(played_group['プレイヤー'].tolist()),
                'Results (Player(Score))': " / ".join(participants_info)
            })

        game_log_df = pd.DataFrame(game_log_data).sort_values(['Date', 'Game #', 'Rate']).reset_index(drop=True)
        game_log_df.index = game_log_df.index + 1
        
        st.dataframe(game_log_df, use_container_width=True)

        # --- Data Validation ---
        st.header("✅ Data Integrity Check")
        total_games = len(game_log_df)
        total_player_games = df['参加フラグ'].sum()
        
        col1, col2 = st.columns(2)
        col1.metric("Total Hanchan", f"{total_games} games")
        col2.metric("Total Player-Games", f"{total_player_games} entries")
        
        if total_games * 4 == total_player_games:
            st.success("✔ Data integrity verified — all games have exactly 4 players.")
        else:
            st.warning(f"⚠ Integrity Error: Hanchan×4 ({total_games * 4}) doesn't match actual player-games ({total_player_games}). Possible data gaps.")
            
            invalid_games = game_log_df[game_log_df['Players'] != 4]
            if not invalid_games.empty:
                st.write("▼ Games without exactly 4 players")
                st.dataframe(invalid_games, use_container_width=True)

        st.markdown("---")
        st.header("🤝 Table Chemistry Heatmap")
        st.markdown("Visualizes **average placement when sitting at the same table as each player**. Blue = better (closer to 1st), Red = worse (closer to 4th).")
        
        # Collect player-opponent placement pairs across all games
        compat_records = []
        for game_id, group in df[df['参加フラグ']].groupby('ゲームID'):
            players_in_game = group[['プレイヤー', '順位']].values.tolist()
            for p, rank in players_in_game:
                for co_p, _ in players_in_game:
                    if p != co_p:
                        compat_records.append({'プレイヤー': p, '同卓者': co_p, '順位': rank})
        
        if compat_records:
            compat_df = pd.DataFrame(compat_records)
            # Show only pairs with 5+ shared games
            counts = compat_df.groupby(['プレイヤー', '同卓者']).size().reset_index(name='Shared Games')
            compat_agg = compat_df.groupby(['プレイヤー', '同卓者'])['順位'].mean().reset_index()
            compat_agg = compat_agg.merge(counts, on=['プレイヤー', '同卓者'])
            MIN_GAMES_COMPAT = st.slider("Min. shared games filter", 1, 30, 5, key="compat_min")
            compat_agg = compat_agg[compat_agg['Shared Games'] >= MIN_GAMES_COMPAT]
            
            if not compat_agg.empty:
                # Create pivot table
                pivot = compat_agg.pivot(index='プレイヤー', columns='同卓者', values='順位')
                pivot_count = compat_agg.pivot(index='プレイヤー', columns='同卓者', values='Shared Games').fillna(0).astype(int)
                
                # Hover text (avg placement + shared games)
                hover_text = []
                for row_p in pivot.index:
                    row_hover = []
                    for col_p in pivot.columns:
                        val = pivot.loc[row_p, col_p] if col_p in pivot.columns else None
                        cnt = pivot_count.loc[row_p, col_p] if col_p in pivot_count.columns else 0
                        if pd.notna(val):
                            row_hover.append(f"{row_p} × {col_p}<br>Avg Placement: {val:.2f}<br>Shared Games: {int(cnt)}")
                        else:
                            row_hover.append("")
                    hover_text.append(row_hover)
                
                fig_heat = go.Figure(data=go.Heatmap(
                    z=pivot.values,
                    x=list(pivot.columns),
                    y=list(pivot.index),
                    text=hover_text,
                    hovertemplate="%{text}<extra></extra>",
                    colorscale=[
                        [0.0, '#1f77b4'],   # 1st: Blue
                        [0.33, '#59c96b'],  # 2nd: Green
                        [0.66, '#ffaa33'],  # 3rd: Orange
                        [1.0, '#d62728']    # 4th: Red
                    ],
                    zmin=1, zmax=4,
                    colorbar=dict(
                        title="Avg Placement",
                        tickvals=[1, 2, 3, 4],
                        ticktext=["1st (Best)", "2nd", "3rd", "4th (Worst)"]
                    ),
                    xgap=3, ygap=3,
                ))
                
                # Display values in cells
                annotations = []
                for i, row_p in enumerate(pivot.index):
                    for j, col_p in enumerate(pivot.columns):
                        val = pivot.iloc[i, j]
                        if pd.notna(val):
                            annotations.append(dict(
                                x=col_p, y=row_p,
                                text=f"{val:.2f}",
                                showarrow=False,
                                font=dict(color='white', size=12, weight='bold')
                            ))
                
                n_players = len(pivot.index)
                fig_heat.update_layout(
                    annotations=annotations,
                    height=max(300, n_players * 55 + 100),
                    xaxis=dict(title="Opponent (columns)", side='top'),
                    yaxis=dict(title="Player (rows)", autorange='reversed'),
                    margin=dict(l=20, r=20, t=80, b=20),
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                )
                st.plotly_chart(fig_heat, use_container_width=True)
                st.caption("Shows the row player's average placement when sitting at the same table as the column player.")
            else:
                st.info(f"No pairs found with {MIN_GAMES_COMPAT}+ shared games. Try lowering the filter.")
        
        st.markdown("---")
        st.header("📑 Detailed Performance Data Table")
        filtered_cols = ['ファイル', '日付', '回戦数', 'プレイヤー', '点数', 'スコア', 'チップ', '収支', '順位', 'レート名', '参加フラグ', '累積収支']
        st.dataframe(df[filtered_cols], use_container_width=True)
        
        if not df_sanma.empty:
            st.header("🀄 Sanma Log (Excluded Data)")
            st.info("The following data was identified as 3-player games (sanma) and excluded from the main statistics.")
            sanma_log_data = []
            for game_id, group in df_sanma.groupby('ゲームID'):
                played_group = group[group['参加フラグ']].sort_values('順位')
                sanma_log_data.append({
                    'File': group['ファイル'].iloc[0],
                    'Date': group['日付'].iloc[0],
                    'Game #': group['回戦数'].iloc[0],
                    'Members': ", ".join(played_group['プレイヤー'].tolist()),
                })
            st.dataframe(pd.DataFrame(sanma_log_data), use_container_width=True)
    elif view_mode == "Individual Stats":
        # ==========================================
        # Individual Performance Page
        # ==========================================
        st.header("👤 Individual Performance")
        
        # Sort players by game count (descending)
        player_game_counts = df[df['参加フラグ']]['プレイヤー'].value_counts()
        all_players = df['プレイヤー'].dropna().unique()
        players_sorted = sorted(all_players, key=lambda p: player_game_counts.get(p, 0), reverse=True)
        
        selected_player = st.selectbox("Select a player to analyze", players_sorted)
        
        # Selected player's data
        p_df = df[df['プレイヤー'] == selected_player].copy()
        p_df_played = p_df[p_df['参加フラグ']].copy()
        
        if p_df_played.empty:
            st.warning("No yonma data available for this player.")
        else:
            total_games = len(p_df_played)
            total_balance = p_df['収支'].sum()
            total_points = p_df['スコア'].sum()
            avg_rank = p_df_played['順位'].mean()
            avg_score = p_df_played['スコア'].mean()
            curr_rate = p_df_played['事後レーティング'].iloc[-1]
            
            # 1. Basic Stats KPI
            st.markdown(f"### {selected_player}'s Performance")
            bal_rank = get_rank_str(selected_player, 'Balance Rank')
            ar_rank = get_rank_str(selected_player, 'Avg Placement Rank')
            avg_score_rank = get_rank_str(selected_player, 'Avg Score Rank')
            rate_rank = get_rank_str(selected_player, 'Rating Rank')
            
            col1, col2, col3, col4, col5, col6 = st.columns(6)
            col1.metric("Current Rating", f"{curr_rate:.1f}", delta=rate_rank, delta_color="off")
            col2.metric(f"Total Balance ({currency_symbol})", f"{currency_symbol}{total_balance:.1f}", delta=bal_rank, delta_color="off")
            col3.metric("Avg Score", f"{avg_score:.1f} pt", delta=avg_score_rank, delta_color="off")
            col4.metric("Total Score", f"{total_points:.1f}")
            col5.metric("Games Played", f"{total_games} hanchan")
            col6.metric("Avg Placement", f"{avg_rank:.2f}", delta=ar_rank, delta_color="off")
            
            st.markdown("---")
            
            # 2. Charts (Side-by-side)
            chart_col1, chart_col2 = st.columns([3, 2])
            
            # Prepare data for tooltips and logs
            p_chart_df = p_df_played[['ゲームID', '日付', '回戦数', '順位', 'スコア', '収支', '事後レーティング']].copy()
            p_chart_df = p_chart_df.sort_values(['日付', '回戦数'])
            p_chart_df['通算ゲーム数'] = range(1, len(p_chart_df) + 1)
            
            game_details = []
            for g_id in p_chart_df['ゲームID']:
                group = df[df['ゲームID'] == g_id]
                played_group = group[group['参加フラグ']].sort_values('順位')
                info_str = " / ".join([f"{r['プレイヤー']}({r['スコア']})" for _, r in played_group.iterrows()])
                game_details.append(info_str)
            
            p_chart_df['対局結果'] = game_details
            
            with chart_col1:
                st.subheader("Trend Charts")
                
                chart_type = st.radio("Select chart", ["Rating Trend", "Placement Trend"], horizontal=True, label_visibility="collapsed")
                
                ctrl_r1, ctrl_r2 = st.columns(2)
                with ctrl_r1:
                    display_options = {"Last 30": 30, "Last 50": 50, "All": None}
                    selected_range = st.radio("Display Range", list(display_options.keys()), index=0, horizontal=True, label_visibility="collapsed")
                with ctrl_r2:
                    ma_options = {"MA: Off": 0, "10 games": 10, "20 games": 20, "30 games": 30, "50 games": 50, "100 games": 100}
                    ma_label = st.radio("Moving Avg", list(ma_options.keys()), index=2, horizontal=True, label_visibility="collapsed")
                    ma_window = ma_options[ma_label]
                
                plot_df = p_chart_df.tail(display_options[selected_range]) if display_options[selected_range] else p_chart_df
                plot_df = plot_df.copy()
                
                # Performance check: disable markers for large datasets
                HEAVY_THRESHOLD = 150
                is_heavy = len(plot_df) > HEAVY_THRESHOLD
                if is_heavy:
                    st.caption(f"⚡ Large dataset ({len(plot_df)} games) — individual markers hidden for performance. Moving average uses all data.")
                
                # Subsample scatter points for heavy datasets
                if is_heavy:
                    scatter_df = plot_df.iloc[::5].copy()
                else:
                    scatter_df = plot_df
                
                y_col = '事後レーティング' if chart_type == "Rating Trend" else '順位'
                
                fig_line = px.line(
                    scatter_df, 
                    x='通算ゲーム数', 
                    y=y_col, 
                    markers=not is_heavy,
                    custom_data=['日付', '収支', '対局結果'] if not is_heavy else ['日付']
                )
                
                if chart_type == "Placement Trend":
                    fig_line.update_yaxes(autorange="reversed", range=[4.5, 0.5], dtick=1)
                
                fig_line.update_layout(xaxis_title="Game # (hover for date)")
                
                # Hover template
                if not is_heavy:
                    fig_line.update_traces(
                        hovertemplate=(
                            "<b>Game: %{x}</b><br>"
                            "Date: %{customdata[0]}<br>"
                            + ( "Rating: %{y:.1f}<br>" if chart_type == "Rating Trend" else "Placement: %{y}<br>" ) +
                            "Balance: %{customdata[1]}<br>"
                            "Results:<br>%{customdata[2]}"
                            "<extra></extra>"
                        ),
                        line=dict(width=2, color='rgba(78,121,167,0.4)'),
                        marker=dict(size=7, color='#e15759')
                    )
                else:
                    fig_line.update_traces(
                        hovertemplate=(
                            "<b>Game: %{x}</b><br>"
                            "Date: %{customdata[0]}<br>"
                            "Placement: %{y}"
                            "<extra></extra>"
                        ),
                        line=dict(width=1, color='rgba(78,121,167,0.25)'),
                    )
                
                # Moving average overlay
                if ma_window > 0 and len(plot_df) >= ma_window:
                    plot_df['移動平均'] = plot_df[y_col].rolling(window=ma_window, min_periods=max(1, ma_window//2)).mean()
                    fig_line.add_trace(go.Scatter(
                        x=plot_df['通算ゲーム数'],
                        y=plot_df['移動平均'],
                        mode='lines',
                        name=f'Moving Avg (last {ma_window})',
                        line=dict(width=3, color='#2ca02c', dash='solid'),
                        hovertemplate="Moving Avg: %{y:.2f}" + ("<extra></extra>")
                    ))
                    # Trend annotation
                    last_ma = plot_df['移動平均'].dropna()
                    if len(last_ma) >= 5:
                        trend = last_ma.iloc[-1] - last_ma.iloc[-5]
                        if chart_type == "Placement Trend":
                            trend_str = f"{'↑ Improving' if trend < -0.1 else ('↓ Declining' if trend > 0.1 else '→ Stable')} (Δ{trend:+.2f})"
                        else:
                            trend_str = f"{'↑ Rising' if trend > 5 else ('↓ Falling' if trend < -5 else '→ Stable')} (Δ{trend:+.1f})"
                            
                        fig_line.add_annotation(
                            x=plot_df['通算ゲーム数'].iloc[-1],
                            y=last_ma.iloc[-1],
                            text=trend_str,
                            showarrow=True,
                            arrowhead=2,
                            ax=50, ay=-30,
                            font=dict(color='#2ca02c', size=12),
                            bgcolor='rgba(44,160,44,0.1)'
                        )
                
                # Styling
                fig_line.update_layout(
                    hovermode="x unified",
                    height=450,
                    margin=dict(l=20, r=20, t=30, b=20),
                    legend=dict(orientation='h', y=1.08)
                )
                st.plotly_chart(fig_line, use_container_width=True)
                
            with chart_col2:
                st.subheader("Placement Distribution")
                rank_counts = p_df_played['順位'].value_counts().reset_index()
                rank_counts.columns = ['順位', '回数']
                rank_counts['Placement'] = rank_counts['順位'].astype(int).astype(str) + "st/nd/rd/th"
                # Fix ordinal suffixes
                ordinal_map = {1: "1st", 2: "2nd", 3: "3rd", 4: "4th"}
                rank_counts['Placement'] = rank_counts['順位'].map(ordinal_map)
                rank_counts = rank_counts.sort_values('順位')
                
                color_map = {
                    "1st": "#1f77b4",
                    "2nd": "#2ca02c",
                    "3rd": "#ff7f0e",
                    "4th": "#d62728"
                }
                
                fig_pie = px.pie(
                    rank_counts, 
                    names='Placement', 
                    values='回数',
                    color='Placement',
                    color_discrete_map=color_map,
                    hole=0.4
                )
                fig_pie.update_traces(
                    textposition='inside', 
                    textinfo='percent+label',
                    insidetextorientation='horizontal'
                )
                fig_pie.update_layout(
                    height=450,
                    margin=dict(l=20, r=20, t=30, b=20),
                    showlegend=False
                )
                st.plotly_chart(fig_pie, use_container_width=True)

            # 3. Detailed Stats Grid
            st.markdown("---")
            st.subheader("Detailed Statistics")
            
            first_rate = p_df_played[p_df_played['順位'] == 1].shape[0] / total_games * 100
            second_rate = p_df_played[p_df_played['順位'] == 2].shape[0] / total_games * 100
            third_rate = p_df_played[p_df_played['順位'] == 3].shape[0] / total_games * 100
            fourth_rate = p_df_played[p_df_played['順位'] == 4].shape[0] / total_games * 100
            rentai_rate = first_rate + second_rate
            top_score = p_df_played['スコア'].max()
            worst_score = p_df_played['スコア'].min()
            
            s_col1, s_col2, s_col3, s_col4 = st.columns(4)
            s_col1.metric("Top-2 Rate (1st+2nd)", f"{rentai_rate:.1f}%", delta=get_rank_str(selected_player, 'Top-2 Rate Rank'), delta_color="off")
            s_col2.metric("1st Place Rate", f"{first_rate:.1f}%", delta=get_rank_str(selected_player, '1st Rate Rank'), delta_color="off")
            s_col3.metric("Last Place Rate (4th)", f"{fourth_rate:.1f}%")
            
            last_avoid_rate = 100 - fourth_rate
            s_col4.metric("Last Avoid Rate (1st-3rd)", f"{last_avoid_rate:.1f}%", delta=get_rank_str(selected_player, 'Last Avoid Rank'), delta_color="off")
            
            st.metric("Personal Best Score", f"{top_score:.1f}", delta=get_rank_str(selected_player, 'Best Score Rank'), delta_color="off")
            
            st.markdown(" ")
            def jump_to_ranking():
                st.session_state.view_mode = "Rankings (All)"
                
            st.button("👑 View Full Rankings", on_click=jump_to_ranking)
            
            st.markdown("---")
            render_calendar(p_df_played, f"📅 {selected_player}'s Activity Calendar", "personal", show_mode_selector=True)
            
            # 4. Personal Game Log
            st.markdown("---")
            st.subheader("Game Log")
            log_disp = p_df_played[['日付', '回戦数', 'レート名', '順位', '事後レーティング', '点数', 'スコア', 'チップ', '収支']].copy()
            log_disp['同卓者結果'] = p_chart_df['対局結果'].values
            
            # Re-index (newest first)
            log_disp = log_disp.sort_values(['日付', '回戦数'], ascending=[False, False]).reset_index(drop=True)
            log_disp.index = log_disp.index + 1
            
            # Rename columns for English display
            log_disp.columns = ['Date', 'Game #', 'Rate', 'Placement', 'Rating', 'Points', 'Score', 'Chips', 'Balance', 'Table Results']
            
            # format rating
            log_disp['Rating'] = log_disp['Rating'].map('{:.1f}'.format)
            
            st.dataframe(log_disp, use_container_width=True)

    elif view_mode == "Rankings (All)":
        st.header(f"👑 Rankings (Min. {MIN_GAMES_FOR_RANKING} games)")
        
        if total_ranked_players == 0:
            st.warning(f"No player has reached the qualifying threshold ({MIN_GAMES_FOR_RANKING} games). Try lowering the threshold in the sidebar.")
        else:
            st.markdown(f"Rankings for players with {MIN_GAMES_FOR_RANKING}+ games played.")
            
            rank_limit_options = {"TOP 3": 3, "TOP 5 (Default)": 5, "TOP 10": 10, "Show All": None}
            selected_limit_label = st.radio("Display Count", list(rank_limit_options.keys()), index=1, horizontal=True)
            limit_val = rank_limit_options[selected_limit_label]
            
            def create_ranking_chart(df, metric, base_title, ascending_rank=False, color='#1f77b4', is_percent=False):
                plot_df = df.sort_values(metric, ascending=ascending_rank)
                if limit_val is not None:
                    plot_df = plot_df.head(limit_val)
                    
                plot_df = plot_df.iloc[::-1] # Reverse for Plotly (bottom = top)
                
                if metric == "Avg Placement":
                    text_vals = plot_df[metric].apply(lambda x: f"{x:.2f}")
                elif is_percent:
                    text_vals = plot_df[metric].apply(lambda x: f"{x:.1f}%")
                else:
                    text_vals = plot_df[metric].apply(lambda x: f"{x:.1f}")
                
                title_suffix = f"TOP {limit_val}" if limit_val else "All"
                
                fig = px.bar(
                    plot_df, 
                    x=metric, 
                    y='Player', 
                    orientation='h',
                    title=f"<b>{base_title} ({title_suffix})</b>"
                )
                
                fig.update_traces(
                    marker_color=color,
                    text=text_vals,
                    textposition='outside',
                    cliponaxis=False,
                    width=0.6,
                    marker=dict(line=dict(color='rgba(0,0,0,0)', width=0), opacity=0.9)
                )
                
                chart_height = max(200, len(plot_df) * 40 + 80)
                
                fig.update_layout(
                    xaxis=dict(showgrid=False, showticklabels=False, title=""),
                    yaxis=dict(title="", tickfont=dict(size=14, weight='bold')),
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    height=chart_height,
                    margin=dict(l=10, r=40, t=50, b=10)
                )
                return fig

            st.plotly_chart(create_ranking_chart(ranked_df, 'Current Rating', '🏆 Current Rating', ascending_rank=False, color='#e024b5'), use_container_width=True)
            st.plotly_chart(create_ranking_chart(ranked_df, 'Total Balance', '💰 Total Balance', ascending_rank=False, color='#2ca02c'), use_container_width=True)
            
            rank_col1, rank_col2 = st.columns(2)
            with rank_col1:
                st.plotly_chart(create_ranking_chart(ranked_df, 'Avg Score', '💫 Avg Score (per hanchan)', ascending_rank=False, color='#8c564b'), use_container_width=True)
                st.plotly_chart(create_ranking_chart(ranked_df, '1st Rate (%)', '🥇 1st Place Rate', ascending_rank=False, color='#ff7f0e', is_percent=True), use_container_width=True)
                st.plotly_chart(create_ranking_chart(ranked_df, 'Top-2 Rate (%)', '🥈 Top-2 Rate', ascending_rank=False, color='#17becf', is_percent=True), use_container_width=True)
                st.plotly_chart(create_ranking_chart(ranked_df, 'Best Score', '🔥 Best Single-Game Score', ascending_rank=False, color='#d62728'), use_container_width=True)
                
            with rank_col2:
                st.plotly_chart(create_ranking_chart(ranked_df, 'Avg Placement', '🎯 Avg Placement', ascending_rank=True, color='#1f77b4'), use_container_width=True)
                st.plotly_chart(create_ranking_chart(ranked_df, 'Last Avoid (%)', '🛡️ Last Place Avoidance', ascending_rank=False, color='#9467bd', is_percent=True), use_container_width=True)
                st.plotly_chart(create_ranking_chart(ranked_df, 'Bust Rate (%)', '💥 Bust Rate (lower = better)', ascending_rank=True, color='#d62728', is_percent=True), use_container_width=True)
                st.plotly_chart(create_ranking_chart(ranked_df, 'Games', '🀄 Most Games Played', ascending_rank=False, color='#e377c2'), use_container_width=True)

    elif view_mode == "Fun Stats":
        st.header("🎭 Fun Stats (Records & Milestones)")
        st.markdown("A collection of remarkable records, achievements, and misadventures!")
        
        df_chrono = df[df['参加フラグ']].sort_values(['日付', '回戦数', 'ゲームID']).copy()
        
        def get_best_streak(condition_func):
            best_streak = 0
            best_records = []
            
            for p in df_chrono['プレイヤー'].unique():
                p_df = df_chrono[df_chrono['プレイヤー'] == p]
                curr_streak = 0
                curr_start = None
                for _, row in p_df.iterrows():
                    if condition_func(row):
                        if curr_streak == 0:
                            curr_start = row['日付']
                        curr_streak += 1
                        if curr_streak > best_streak:
                            best_streak = curr_streak
                            best_records = [{'player': p, 'start': curr_start, 'end': row['日付']}]
                        elif curr_streak == best_streak and curr_streak > 0:
                            existing = [r for r in best_records if r['player'] == p]
                            if existing:
                                existing[0]['start'] = curr_start
                                existing[0]['end'] = row['日付']
                            else:
                                best_records.append({'player': p, 'start': curr_start, 'end': row['日付']})
                    else:
                        curr_streak = 0
                        
            if best_streak == 0:
                return "-", 0, "-"
                
            if len(best_records) == 1:
                p_str = best_records[0]['player']
                d_str = f"Period: {best_records[0]['start']} — {best_records[0]['end']}"
            else:
                p_str = ", ".join([r['player'] for r in best_records])
                d_str = f"Period: Achieved at different times (latest: {best_records[-1]['start']} — {best_records[-1]['end']})"
                
            return p_str, best_streak, d_str
            
        top_p, top_streak, top_date_str = get_best_streak(lambda x: x['順位'] == 1)
        rentai_p, rentai_streak, rentai_date_str = get_best_streak(lambda x: x['順位'] <= 2)
        last_p, last_streak, last_date_str = get_best_streak(lambda x: x['順位'] == 4)
        
        max_score_idx = df_chrono['スコア'].idxmax()
        min_score_idx = df_chrono['スコア'].idxmin()
        max_chip_idx = df_chrono['チップ'].idxmax()
        
        max_score_row = df_chrono.loc[max_score_idx] if not pd.isna(max_score_idx) else None
        min_score_row = df_chrono.loc[min_score_idx] if not pd.isna(min_score_idx) else None
        max_chip_row = df_chrono.loc[max_chip_idx] if not pd.isna(max_chip_idx) else None
        
        df_chrono['date_only'] = pd.to_datetime(df_chrono['日付']).dt.date
        daily_counts = df_chrono.groupby(['date_only', 'プレイヤー'])['ゲームID'].nunique().reset_index(name='count')
        if not daily_counts.empty:
            max_day_val = daily_counts['count'].max()
            max_day_rows = daily_counts[daily_counts['count'] == max_day_val]
            latest_record_date = max_day_rows['date_only'].max()
            record_players = max_day_rows[max_day_rows['date_only'] == latest_record_date]['プレイヤー'].tolist()
            max_day_player_str = ", ".join(record_players)
            max_day_count = int(max_day_val)
            max_day_date_str = str(latest_record_date)
            max_day_found = True
        else:
            max_day_found = False
        
        def render_fun_stat(icon, title, value, player, subtext, color="#1f77b4"):
            html = f'''
            <div class="anim-pop" style="background-color: rgba(255,255,255,0.05); padding: 15px; border-radius: 10px; margin-bottom: 20px; border-left: 5px solid {color}; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                <div style="font-size: 16px; margin-bottom: 5px; color: #ddd;">{icon} {title}</div>
                <div style="margin-bottom: 5px; display: flex; align-items: baseline; gap: 15px;">
                    <span style="font-size: 26px; font-weight: bold; color: {color};">{player}</span>
                    <span style="font-size: 20px; font-weight: bold;">{value}</span>
                </div>
                <div style="color: #999; font-size: 13px;">{subtext}</div>
            </div>
            '''
            return st.markdown(html, unsafe_allow_html=True)
            
        # Longest consecutive active days calculation
        from datetime import timedelta
        consec_best = 0
        consec_best_records = []
        
        for p in df_chrono['プレイヤー'].unique():
            p_dates = sorted(df_chrono[df_chrono['プレイヤー'] == p]['date_only'].unique())
            if len(p_dates) == 0:
                continue
            curr_streak_d = 1
            curr_start_d = p_dates[0]
            for i in range(1, len(p_dates)):
                if p_dates[i] - p_dates[i-1] == timedelta(days=1):
                    curr_streak_d += 1
                else:
                    if curr_streak_d > consec_best:
                        consec_best = curr_streak_d
                        consec_best_records = [{'player': p, 'start': curr_start_d, 'end': p_dates[i-1]}]
                    elif curr_streak_d == consec_best and curr_streak_d > 0:
                        consec_best_records.append({'player': p, 'start': curr_start_d, 'end': p_dates[i-1]})
                    curr_streak_d = 1
                    curr_start_d = p_dates[i]
            # check last streak
            if curr_streak_d > consec_best:
                consec_best = curr_streak_d
                consec_best_records = [{'player': p, 'start': curr_start_d, 'end': p_dates[-1]}]
            elif curr_streak_d == consec_best and curr_streak_d > 0:
                consec_best_records.append({'player': p, 'start': curr_start_d, 'end': p_dates[-1]})
        
        if consec_best > 0 and consec_best_records:
            consec_player_str = ", ".join(list(dict.fromkeys([r['player'] for r in consec_best_records])))
            consec_date_str = f"Period: {consec_best_records[0]['start']} — {consec_best_records[0]['end']}"
        else:
            consec_player_str = "-"
            consec_date_str = "-"
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🏃‍♂️ Streak Records")
            render_fun_stat("👑", "Longest 1st Place Streak", f"{top_streak} in a row", top_p, f"{top_date_str}", "#ff7f0e")
            render_fun_stat("🥈", "Longest Top-2 Streak (1st+2nd)", f"{rentai_streak} in a row", rentai_p, f"{rentai_date_str}", "#17becf")
            render_fun_stat("💀", "Longest Last Place Streak", f"{last_streak} in a row", last_p, f"{last_date_str} / Iron will", "#9467bd")
            render_fun_stat("📅", "Most Consecutive Active Days", f"{consec_best} days straight", consec_player_str, f"{consec_date_str} / The iron player who never missed a day", "#1f77b4")
            
        with col2:
            st.subheader("💥 Single-Game Records")
            if max_score_row is not None:
                render_fun_stat("🚀", "All-Time Highest Score", f"{max_score_row['スコア']:.1f} pt", max_score_row['プレイヤー'], f"Date: {max_score_row['日付']} / Legendary top finish", "#d62728")
            if min_score_row is not None:
                render_fun_stat("📉", "All-Time Lowest Score", f"{min_score_row['スコア']:.1f} pt", min_score_row['プレイヤー'], f"Date: {min_score_row['日付']} / Historic bustout", "#7f7f7f")
            if max_day_found:
                render_fun_stat("🔥", "Most Games in a Single Day", f"{max_day_count} hanchan", max_day_player_str, f"Date: {max_day_date_str} / A day devoted to mahjong", "#e377c2")
            
            # Daily balance & score records
            daily_balance = df_chrono.groupby(['date_only', 'プレイヤー'])['収支'].sum().reset_index()
            if not daily_balance.empty:
                best_win_idx = daily_balance['収支'].idxmax()
                best_win = daily_balance.loc[best_win_idx]
                worst_loss_idx = daily_balance['収支'].idxmin()
                worst_loss = daily_balance.loc[worst_loss_idx]
                render_fun_stat("💰", "Best Single-Day Winnings", f"{currency_symbol}{best_win['収支']:+.1f}", best_win['プレイヤー'], f"Date: {best_win['date_only']} / A golden day", "#2ca02c")
                render_fun_stat("🕳️", "Worst Single-Day Losses", f"{currency_symbol}{worst_loss['収支']:+.1f}", worst_loss['プレイヤー'], f"Date: {worst_loss['date_only']} / A day to forget", "#d62728")

            daily_score = df_chrono.groupby(['date_only', 'プレイヤー'])['スコア'].sum().reset_index()
            if not daily_score.empty:
                best_score_idx = daily_score['スコア'].idxmax()
                best_score_day = daily_score.loc[best_score_idx]
                worst_score_idx = daily_score['スコア'].idxmin()
                worst_score_day = daily_score.loc[worst_score_idx]
                render_fun_stat("⭐", "Best Single-Day Score Total", f"{best_score_day['スコア']:+.1f} pt", best_score_day['プレイヤー'], f"Date: {best_score_day['date_only']} / Points all day long", "#ff7f0e")
                render_fun_stat("🌧️", "Worst Single-Day Score Total", f"{worst_score_day['スコア']:+.1f} pt", worst_score_day['プレイヤー'], f"Date: {worst_score_day['date_only']} / Nothing went right", "#7f7f7f")

        # ============================
        # Detailed Records TOP10
        # ============================
        st.markdown("---")
        st.subheader("📋 Detailed Records TOP10")
        st.caption("Click each category to expand the TOP10 records.")

        def get_all_streaks(condition_func):
            results = []
            for p in df_chrono['プレイヤー'].unique():
                p_df = df_chrono[df_chrono['プレイヤー'] == p]
                best = 0
                best_start = best_end = None
                curr = 0
                c_start = None
                for _, row in p_df.iterrows():
                    if condition_func(row):
                        if curr == 0: c_start = row['日付']
                        curr += 1
                        if curr > best:
                            best = curr
                            best_start, best_end = c_start, row['日付']
                    else:
                        curr = 0
                if best > 0:
                    results.append({'Player': p, 'Streak': best, 'From': best_start, 'To': best_end})
            return pd.DataFrame(results).sort_values('Streak', ascending=False).head(10).reset_index(drop=True) if results else pd.DataFrame()

        with st.expander("👑 Longest 1st Place Streak TOP10"):
            streak_df = get_all_streaks(lambda x: x['順位'] == 1)
            if not streak_df.empty:
                streak_df.index = streak_df.index + 1
                st.dataframe(streak_df, use_container_width=True)

        with st.expander("🥈 Longest Top-2 Streak TOP10"):
            streak_df = get_all_streaks(lambda x: x['順位'] <= 2)
            if not streak_df.empty:
                streak_df.index = streak_df.index + 1
                st.dataframe(streak_df, use_container_width=True)

        with st.expander("💀 Longest Last Place Streak TOP10"):
            streak_df = get_all_streaks(lambda x: x['順位'] == 4)
            if not streak_df.empty:
                streak_df.index = streak_df.index + 1
                st.dataframe(streak_df, use_container_width=True)

        with st.expander("📅 Most Consecutive Active Days TOP10"):
            from datetime import timedelta as td
            consec_all = []
            for p in df_chrono['プレイヤー'].unique():
                p_dates = sorted(df_chrono[df_chrono['プレイヤー'] == p]['date_only'].unique())
                if not p_dates: continue
                best_d, best_s, best_e = 1, p_dates[0], p_dates[0]
                cs, c_start = 1, p_dates[0]
                for i in range(1, len(p_dates)):
                    if p_dates[i] - p_dates[i-1] == td(days=1):
                        cs += 1
                    else:
                        if cs > best_d: best_d, best_s, best_e = cs, c_start, p_dates[i-1]
                        cs, c_start = 1, p_dates[i]
                if cs > best_d: best_d, best_s, best_e = cs, c_start, p_dates[-1]
                consec_all.append({'Player': p, 'Days': best_d, 'From': best_s, 'To': best_e})
            if consec_all:
                cdf = pd.DataFrame(consec_all).sort_values('Days', ascending=False).head(10).reset_index(drop=True)
                cdf.index = cdf.index + 1
                st.dataframe(cdf, use_container_width=True)

        with st.expander("🚀 All-Time Highest Single-Game Score TOP10"):
            top_scores = df_chrono.nlargest(10, 'スコア')[['日付', 'プレイヤー', 'スコア', '点数', '順位']].reset_index(drop=True)
            top_scores.columns = ['Date', 'Player', 'Score', 'Points', 'Placement']
            top_scores.index = top_scores.index + 1
            st.dataframe(top_scores, use_container_width=True)

        with st.expander("📉 All-Time Lowest Single-Game Score WORST10"):
            worst_scores = df_chrono.nsmallest(10, 'スコア')[['日付', 'プレイヤー', 'スコア', '点数', '順位']].reset_index(drop=True)
            worst_scores.columns = ['Date', 'Player', 'Score', 'Points', 'Placement']
            worst_scores.index = worst_scores.index + 1
            st.dataframe(worst_scores, use_container_width=True)

        with st.expander("🔥 Most Games in a Single Day TOP10"):
            dc_top = daily_counts.sort_values('count', ascending=False).head(10).reset_index(drop=True)
            dc_top.columns = ['Date', 'Player', 'Games']
            dc_top.index = dc_top.index + 1
            st.dataframe(dc_top, use_container_width=True)

        if not daily_balance.empty:
            with st.expander("💰 Best Single-Day Winnings TOP10"):
                db_top = daily_balance.nlargest(10, '収支').reset_index(drop=True)
                db_top.columns = ['Date', 'Player', 'Balance']
                db_top['Balance'] = db_top['Balance'].map(lambda x: f"{currency_symbol}{x:+.1f}")
                db_top.index = db_top.index + 1
                st.dataframe(db_top, use_container_width=True)

            with st.expander("🕳️ Worst Single-Day Losses WORST10"):
                db_worst = daily_balance.nsmallest(10, '収支').reset_index(drop=True)
                db_worst.columns = ['Date', 'Player', 'Balance']
                db_worst['Balance'] = db_worst['Balance'].map(lambda x: f"{currency_symbol}{x:+.1f}")
                db_worst.index = db_worst.index + 1
                st.dataframe(db_worst, use_container_width=True)


    elif view_mode == "Player Comparison":
        st.header("⚔️ Player Comparison (Head-to-Head)")
        st.markdown("Compare two players' play styles and stats side by side!")
        
        players_list = list(summary_df.sort_values('Games', ascending=False)['Player'])
        
        if len(players_list) < 2:
            st.warning("Need at least 2 players for comparison.")
        else:
            sel_col1, sel_col2, sel_col3 = st.columns([2, 1, 2])
            with sel_col1:
                p1 = st.selectbox("Player 1", players_list, index=0, key="cmp_p1")
            with sel_col3:
                p2 = st.selectbox("Player 2", players_list, index=1, key="cmp_p2")
                
            if p1 == p2:
                st.warning("Please select different players.")
            else:
                # Same-table filter
                coplay_only = st.checkbox("🤝 Compare using shared games only", value=False, key="cmp_coplay")
                
                if coplay_only:
                    games_p1 = set(df[(df['プレイヤー'] == p1) & df['参加フラグ']]['ゲームID'])
                    games_p2 = set(df[(df['プレイヤー'] == p2) & df['参加フラグ']]['ゲームID'])
                    coplay_games = games_p1 & games_p2
                    
                    if not coplay_games:
                        st.warning(f"⚠️ No shared games found between {p1} and {p2}.")
                        st.stop()
                    
                    df_cmp = df[df['ゲームID'].isin(coplay_games)].copy()
                    st.info(f"🤝 Shared games: **{len(coplay_games)}** hanchan")
                else:
                    df_cmp = df.copy()
                
                def calc_p_stats(p_name, source_df=None):
                    if source_df is None:
                        source_df = df
                    p_df = source_df[(source_df['プレイヤー'] == p_name) & source_df['参加フラグ']]
                    t_games = len(p_df)
                    if t_games == 0: return None
                    ranks = p_df['順位'].value_counts()
                    r1 = ranks.get(1, 0)
                    r2 = ranks.get(2, 0)
                    r4 = ranks.get(4, 0)
                    top_games_df = p_df[p_df['順位'] == 1]
                    avg_top_score_val = top_games_df['スコア'].mean() if len(top_games_df) > 0 else 0
                    
                    tobi_games = len(p_df[p_df['点数'] < 0])
                    tobi_avoid_rate = 100 - (tobi_games / t_games * 100) if t_games > 0 else 100
                    avg_score_val = p_df['スコア'].mean() if t_games > 0 else 0.0
                    
                    return {
                        "Games": t_games,
                        "Total Balance": p_df['収支'].sum(),
                        "Avg Score": avg_score_val,
                        "Avg Placement": p_df['順位'].mean(),
                        "1st Rate": (r1 / t_games) * 100,
                        "Top-2 Rate": ((r1 + r2) / t_games) * 100,
                        "Last Avoid": (1 - r4 / t_games) * 100,
                        "Bust Avoid": tobi_avoid_rate,
                        "Avg Score When 1st": avg_top_score_val,
                        "Current Rating": p_df['事後レーティング'].iloc[-1] if t_games > 0 else 1500.0,
                    }
                    
                s1 = calc_p_stats(p1, df_cmp)
                s2 = calc_p_stats(p2, df_cmp)
                
                if not s1 or not s2:
                    st.error("Insufficient game data.")
                else:
                    st.subheader("🕸️ Play Style Comparison (Radar Chart)")
                    str_bounds = {
                        '1st Rate': (0, 50, False), 
                        'Top-2 Rate': (0, 75, False),
                        'Last Avoid': (25, 100, False),
                        'Bust Avoid': (75, 100, False),
                        'Avg Placement': (1.5, 3.5, True), 
                        'Avg Score When 1st': (40, 80, False)
                    }
                    thetas = ['1st Place Power', 'Top-2 Power', 'Last Avoidance', 'Bust Avoidance', 'Avg Placement', 'Big Win Power']
                    keys = ['1st Rate', 'Top-2 Rate', 'Last Avoid', 'Bust Avoid', 'Avg Placement', 'Avg Score When 1st']
                    
                    def get_radar(stats):
                        r = []
                        for k in keys:
                            b_min, b_max, rev = str_bounds[k]
                            v = stats[k]
                            v = max(b_min, min(b_max, v))
                            norm = ((v - b_min) / (b_max - b_min)) * 100
                            if rev: norm = 100 - norm
                            r.append(norm)
                        return r
                        
                    fig_radar = go.Figure()
                    r1_vals = get_radar(s1)
                    r2_vals = get_radar(s2)
                    
                    fig_radar.add_trace(go.Scatterpolar(r=r1_vals + [r1_vals[0]], theta=thetas + [thetas[0]], fill='toself', name=p1, line_color='#1f77b4'))
                    fig_radar.add_trace(go.Scatterpolar(r=r2_vals + [r2_vals[0]], theta=thetas + [thetas[0]], fill='toself', name=p2, line_color='#ff7f0e'))
                    
                    fig_radar.update_layout(
                        polar=dict(
                            radialaxis=dict(visible=True, range=[0, 100], showticklabels=False)
                        ),
                        showlegend=True,
                        height=450,
                        margin=dict(t=50, b=50, l=50, r=50),
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                    )
                    st.plotly_chart(fig_radar, use_container_width=True)
                    
                    st.markdown("---")
                    st.subheader("📊 Direct Stats Comparison")
                    
                    def render_cmp_row(label, v1, v2, fmt="{:.1f}", invert_good=False):
                        if invert_good:
                            c1 = "#2ca02c" if v1 < v2 else ("#d62728" if v1 > v2 else "#888")
                            c2 = "#2ca02c" if v2 < v1 else ("#d62728" if v2 > v1 else "#888")
                        else:
                            c1 = "#2ca02c" if v1 > v2 else ("#d62728" if v1 < v2 else "#888")
                            c2 = "#2ca02c" if v2 > v1 else ("#d62728" if v2 < v1 else "#888")
                            
                        b1 = "bold" if c1 == "#2ca02c" else "normal"
                        b2 = "bold" if c2 == "#2ca02c" else "normal"
                        
                        v1_str = fmt.format(v1)
                        v2_str = fmt.format(v2)
                        
                        html = f'''
                        <div class="anim-pop" style="display: flex; justify-content: space-between; align-items: center; padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.1);">
                            <div style="flex: 1; text-align: right; font-size: 24px; font-weight: {b1}; color: {c1};">{v1_str}</div>
                            <div style="flex: 1; text-align: center; font-size: 16px; font-weight: bold; color: #ddd;">{label}</div>
                            <div style="flex: 1; text-align: left; font-size: 24px; font-weight: {b2}; color: {c2};">{v2_str}</div>
                        </div>
                        '''
                        st.markdown(html, unsafe_allow_html=True)
                        
                    render_cmp_row("Current Rating", s1["Current Rating"], s2["Current Rating"], "{:.1f}")
                    render_cmp_row("Games", s1["Games"], s2["Games"], "{:.0f}")
                    render_cmp_row("Total Balance", s1["Total Balance"], s2["Total Balance"], "{:+.1f}")
                    render_cmp_row("Avg Score", s1["Avg Score"], s2["Avg Score"], "{:+.1f}")
                    render_cmp_row("Avg Placement", s1["Avg Placement"], s2["Avg Placement"], "{:.2f}", invert_good=True)
                    render_cmp_row("1st Place Rate", s1["1st Rate"], s2["1st Rate"], "{:.1f}%")
                    render_cmp_row("Top-2 Rate", s1["Top-2 Rate"], s2["Top-2 Rate"], "{:.1f}%")
                    render_cmp_row("Last Avoid Rate", s1["Last Avoid"], s2["Last Avoid"], "{:.1f}%")
                    render_cmp_row("Bust Avoid Rate", s1["Bust Avoid"], s2["Bust Avoid"], "{:.1f}%")
                    render_cmp_row("Avg Score When 1st<br><span style='font-size:12px;color:rgba(255,255,255,0.4);'>(Big Win Power)</span>", s1["Avg Score When 1st"], s2["Avg Score When 1st"], "{:.1f}")
                    
                    st.markdown("<br>", unsafe_allow_html=True)

    elif view_mode == "📈 Cumulative Summary":
        st.header("📈 Cumulative Summary")
        st.markdown("A bird's-eye view of all game data — **stacked visualizations dashboard**.")
    
        df_played = df[df['参加フラグ']].copy()
        total_games_all = df['ゲームID'].nunique()
        total_player_games = len(df_played)
    
        # =========================================
        # ① Big Number KPIs
        # =========================================
        st.markdown("---")
        st.subheader("💰 Cumulative Financial Summary")
    
        total_positive = df_played[df_played['収支'] > 0]['収支'].sum()
    
        kpi1, kpi2 = st.columns(2)
        kpi1.metric("Total Hanchan", f"{total_games_all:,} games")
        kpi2.metric(f"Total Money Moved ({currency_symbol})", f"{currency_symbol}{total_positive:.1f}")
    
        # =========================================
        # ② Rate Breakdown Donut Chart
        # =========================================
        st.markdown("---")
        st.subheader("🎰 Games by Rate Level")
        rate_counts = df_played.groupby('レート名')['ゲームID'].nunique().reset_index()
        rate_counts.columns = ['Rate', 'Games']
        rate_counts = rate_counts.sort_values('Games', ascending=False)
    
        fig_rate = px.pie(
            rate_counts,
            names='Rate',
            values='Games',
            hole=0.55,
            color_discrete_sequence=px.colors.qualitative.Plotly
        )
        fig_rate.update_traces(
            textposition='outside',
            textinfo='label+percent',
            hovertemplate='%{label}<br>%{value} games (%{percent})<extra></extra>'
        )
        fig_rate.update_layout(
            height=380,
            showlegend=True,
            legend=dict(orientation='h', y=-0.1),
            margin=dict(l=10, r=10, t=30, b=60),
            paper_bgcolor='rgba(0,0,0,0)',
            annotations=[dict(text=f"{total_games_all}<br>games", x=0.5, y=0.5, font_size=18, showarrow=False)]
        )
        st.plotly_chart(fig_rate, use_container_width=True)
    
        # =========================================
        # ④ Point Distribution Histogram (500-point bins)
        # =========================================
        st.markdown("---")
        st.subheader("🎯 Final Point Distribution (All Players)")
        st.caption("All games, all players — final point counts in 500-point bins. Notice the clusters around 25,000 (start) and 30,000.")
    
        all_points = df_played['点数'].dropna()
        
        bin_min = int((all_points.min() // 500) * 500)
        bin_max = int((all_points.max() // 500 + 1) * 500)
        bins_500 = list(range(bin_min, bin_max + 500, 500))
        
        counts_pt, bins_pt = pd.cut(all_points, bins=bins_500, retbins=True, right=False)
        freq_pt = counts_pt.value_counts().sort_index().values
        centers_pt = 0.5 * (bins_pt[:-1] + bins_pt[1:])
        
        fig_pts = go.Figure()
        fig_pts.add_trace(go.Bar(
            x=centers_pt,
            y=freq_pt,
            width=500,
            marker=dict(
                color=freq_pt,
                colorscale=[[0.0, '#1f77b4'], [0.45, '#59c96b'], [0.8, '#ffaa33'], [1.0, '#d62728']],
                cmin=0,
                cmax=freq_pt.max(),
                line=dict(color='rgba(0,0,0,0.2)', width=0.5)
            ),
            hovertemplate='Points: %{x} range<br>Count: %{y}<extra></extra>',
            name='Points'
        ))
        
        # 25000-point line (starting points)
        fig_pts.add_vline(x=25000, line_dash='dash', line_color='rgba(255,255,255,0.5)',
                          annotation_text='Start (25,000)', annotation_position='top right',
                          annotation_font_color='rgba(255,255,255,0.7)')
        
        fig_pts.update_layout(
            xaxis_title='Points',
            yaxis_title='Count',
            height=420,
            margin=dict(l=20, r=20, t=30, b=40),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            showlegend=False,
            bargap=0.05
        )
        fig_pts.update_xaxes(
            tickmode='linear', tick0=bin_min, dtick=5000,
            showgrid=True, gridcolor='rgba(255,255,255,0.08)',
            tickformat=',d'
        )
        fig_pts.update_yaxes(showgrid=True, gridcolor='rgba(255,255,255,0.08)')
        st.plotly_chart(fig_pts, use_container_width=True)

        # =========================================
        # ⑤ Score Distribution Histogram
        # =========================================
        st.markdown("---")
        st.subheader("📊 Score Distribution (All Players)")
        st.caption("Combined distribution of single-game scores across all players. Note the ±0 line.")
    
        all_scores = df_played['スコア'].dropna()
        
        min_sc = int(all_scores.min() - 1)
        max_sc = int(all_scores.max() + 1)
        bins_sc = list(range(min_sc, max_sc + 2, 1))
        
        counts_sc, bins_sc_out = pd.cut(all_scores, bins=bins_sc, retbins=True)
        freq_sc = counts_sc.value_counts().sort_index().values
        centers_sc = 0.5 * (bins_sc_out[:-1] + bins_sc_out[1:])
        
        fig_hist = go.Figure()
        fig_hist.add_trace(go.Bar(
            x=centers_sc,
            y=freq_sc,
            width=(bins_sc[1] - bins_sc[0]),
            marker=dict(
                color=freq_sc,
                colorscale=[[0.0, '#1f77b4'], [0.45, '#59c96b'], [0.8, '#ffaa33'], [1.0, '#d62728']],
                cmin=0,
                cmax=freq_sc.max(),
                line=dict(color='rgba(0,0,0,0.2)', width=0.3)
            ),
            hovertemplate='Score: %{x:.1f} pt<br>Count: %{y}<extra></extra>',
            name='Score Distribution'
        ))
        fig_hist.add_vline(x=0, line_dash='dash', line_color='rgba(255,255,255,0.5)',
                           annotation_text='±0', annotation_position='top right',
                           annotation_font_color='rgba(255,255,255,0.7)')
    
        fig_hist.update_layout(
            xaxis_title='Score (pt)',
            yaxis_title='Count',
            height=400,
            margin=dict(l=20, r=20, t=30, b=40),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            showlegend=False,
            bargap=0.03
        )
        fig_hist.update_xaxes(showgrid=True, gridcolor='rgba(255,255,255,0.1)', zeroline=True, zerolinecolor='rgba(255,255,255,0.3)')
        fig_hist.update_yaxes(showgrid=True, gridcolor='rgba(255,255,255,0.1)')
        st.plotly_chart(fig_hist, use_container_width=True)
    
        # =========================================
        # ⑤ Monthly Avg Score Trend
        # =========================================
        st.markdown("---")
        st.subheader("📅 Monthly Avg Score Trend")
    
        df_played['月'] = pd.to_datetime(df_played['日付']).dt.to_period('M').astype(str)
        monthly_avg = df_played.groupby(['月', 'プレイヤー'])['スコア'].mean().reset_index()
        monthly_avg.columns = ['Month', 'Player', 'Avg Score']
    
        # Top players by game count only
        monthly_players = df_played.groupby('プレイヤー').size().sort_values(ascending=False).head(6).index.tolist()
        monthly_avg = monthly_avg[monthly_avg['Player'].isin(monthly_players)]
    
        fig_month = px.bar(
            monthly_avg,
            x='Month',
            y='Avg Score',
            color='Player',
            barmode='group',
            color_discrete_sequence=px.colors.qualitative.Plotly
        )
        fig_month.add_hline(y=0, line_dash='dash', line_color='rgba(255,255,255,0.4)', annotation_text='±0')
            
        fig_month.update_layout(
            height=420,
            xaxis_title='',
            yaxis_title='Avg Score (pt)',
            margin=dict(l=20, r=20, t=30, b=60),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            legend=dict(orientation='h', y=1.08),
            xaxis=dict(
                tickangle=-45,
                type='category',
                showgrid=True,
                gridcolor='rgba(255,255,255,0.4)',
                griddash='dot',
                tickson='boundaries'
            )
        )
        fig_month.update_yaxes(showgrid=True, gridcolor='rgba(255,255,255,0.08)')
        st.plotly_chart(fig_month, use_container_width=True)

        # =========================================
        # ⑥ Monthly Total Balance Trend
        # =========================================
        st.markdown("---")
        st.subheader("📅 Monthly Total Balance Trend")
    
        monthly_bal = df_played.groupby(['月', 'プレイヤー'])['収支'].sum().reset_index()
        monthly_bal.columns = ['Month', 'Player', 'Balance']
        monthly_bal = monthly_bal[monthly_bal['Player'].isin(monthly_players)]
    
        fig_month_bal = px.bar(
            monthly_bal,
            x='Month',
            y='Balance',
            color='Player',
            barmode='group',
            color_discrete_sequence=px.colors.qualitative.Plotly
        )
        fig_month_bal.add_hline(y=0, line_dash='dash', line_color='rgba(255,255,255,0.4)', annotation_text='±0')
            
        fig_month_bal.update_layout(
            height=420,
            xaxis_title='',
            yaxis_title=f'Total Balance ({currency_symbol})',
            margin=dict(l=20, r=20, t=30, b=60),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            legend=dict(orientation='h', y=1.08),
            xaxis=dict(
                tickangle=-45,
                type='category',
                showgrid=True,
                gridcolor='rgba(255,255,255,0.4)',
                griddash='dot',
                tickson='boundaries'
            )
        )
        fig_month_bal.update_yaxes(showgrid=True, gridcolor='rgba(255,255,255,0.08)')
        st.plotly_chart(fig_month_bal, use_container_width=True)

        # Monthly game count
        st.markdown('---')
        st.subheader('📅 Monthly Hanchan Count')
        st.caption('Number of hanchan played per month — easily spot your active and quiet periods.')

        # Assign consistent colors to all players
        all_players_by_games = df_played['プレイヤー'].value_counts().index.tolist()
        palette = px.colors.qualitative.Plotly + px.colors.qualitative.Pastel + px.colors.qualitative.D3
        color_map = {p: palette[i % len(palette)] for i, p in enumerate(all_players_by_games)}
        color_map['Others'] = '#666666'
        
        monthly_records = []
        for m, group in df_played.groupby('月'):
            player_counts = group.groupby('プレイヤー')['ゲームID'].nunique().sort_values(ascending=False)
            top5 = player_counts.head(5)
            others_count = player_counts.iloc[5:].sum() if len(player_counts) > 5 else 0
            
            for p, cnt in top5.items():
                monthly_records.append({'Month': m, 'Player': p, 'Games': cnt, 'Share': cnt / 4})
            if others_count > 0:
                monthly_records.append({'Month': m, 'Player': 'Others', 'Games': others_count, 'Share': others_count / 4})

        df_monthly_cnt = pd.DataFrame(monthly_records)

        fig_cnt = px.bar(
            df_monthly_cnt,
            x='Month',
            y='Share',
            color='Player',
            color_discrete_map=color_map,
            custom_data=['Games']
        )
        fig_cnt.update_traces(
            hovertemplate='%{fullData.name}<br>Played: %{customdata[0]} hanchan<extra></extra>',
            marker_line_width=0
        )
        total_monthly = df_monthly_cnt.groupby('Month')['Share'].sum()
        avg_cnt = total_monthly.mean() if not total_monthly.empty else 0
        fig_cnt.add_hline(y=avg_cnt, line_dash='dot', line_color='rgba(255,200,0,0.6)',
                          annotation_text=f'Monthly Avg: {avg_cnt:.1f} hanchan', annotation_position='top right',
                          annotation_font_color='rgba(255,200,0,0.9)')
        
        fig_cnt.update_layout(
            barmode='stack',
            xaxis_title='',
            yaxis_title='Hanchan Count',
            height=400,
            showlegend=False,
            margin=dict(l=20, r=20, t=50, b=60),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(tickangle=-45),
            bargap=0.15
        )
        fig_cnt.update_yaxes(showgrid=True, gridcolor='rgba(255,255,255,0.08)')
        st.plotly_chart(fig_cnt, use_container_width=True)

        # =========================================
        # Battle Network Graph
        # =========================================
        st.markdown('---')
        st.header('🌐 Battle Network Graph')
        st.caption('Nodes = players, edge thickness = number of shared games. Thicker lines = more time at the same table.')

        import networkx as nx
        from itertools import combinations

        coplay_counts = {}
        player_game_totals = {}

        for gid, group in df[df['参加フラグ']].groupby('ゲームID'):
            players_in_game = group['プレイヤー'].tolist()
            for p in players_in_game:
                player_game_totals[p] = player_game_totals.get(p, 0) + 1
            for p1, p2 in combinations(sorted(players_in_game), 2):
                pair = (p1, p2)
                coplay_counts[pair] = coplay_counts.get(pair, 0) + 1

        data_collector = max(player_game_totals, key=player_game_totals.get) if player_game_totals else ""

        net_ctrl1, net_ctrl2, net_ctrl3 = st.columns(3)
        with net_ctrl1:
            m_val = max(max(coplay_counts.values()), 5) if coplay_counts else 5
            net_min = st.slider('Min. shared games (your group)', min_value=1, max_value=m_val, value=min(5, m_val), key='net_min_coplay')
        with net_ctrl2:
            net_mode = st.radio('Edge weight', ['Raw count', 'Normalized rate'], index=1, key='net_mode')
        with net_ctrl3:
            net_layout = st.selectbox('Layout', ['Circle (no overlap)', 'Spring (force-directed)'], index=0, key='net_layout')

        m_val_others = max(max(coplay_counts.values()), 3) if coplay_counts else 3
        net_min_others = st.slider(f'Min. shared games (without {data_collector})', min_value=1, max_value=m_val_others, value=min(3, m_val_others), key='net_min_others_coplay')

        def should_include_pair(pair, count):
            if data_collector in pair:
                return count >= net_min
            else:
                return count >= net_min_others

        filtered_pairs = {k: v for k, v in coplay_counts.items() if should_include_pair(k, v)}

        if filtered_pairs:
            G = nx.Graph()
            for (p1, p2), count in filtered_pairs.items():
                if net_mode == 'Normalized rate':
                    min_games = min(player_game_totals.get(p1, 1), player_game_totals.get(p2, 1))
                    weight = count / max(min_games, 1) * 100
                else:
                    weight = count
                G.add_edge(p1, p2, weight=weight, raw=count)

            if net_layout == 'Circle (no overlap)':
                pos = nx.circular_layout(G)
            else:
                pos = nx.spring_layout(G, seed=42, k=6.0, iterations=100)

            edge_traces = []
            max_weight = max(d['weight'] for _, _, d in G.edges(data=True))
            min_weight = min(d['weight'] for _, _, d in G.edges(data=True))

            for edge in G.edges(data=True):
                x0, y0 = pos[edge[0]]
                x1, y1 = pos[edge[1]]
                w = edge[2]['weight']
                width = 1 + (w - min_weight) / (max_weight - min_weight) * 9 if max_weight > min_weight else 3
                opacity = 0.3 + 0.7 * (w - min_weight) / (max_weight - min_weight) if max_weight > min_weight else 0.6
                edge_traces.append(go.Scatter(
                    x=[x0, x1, None], y=[y0, y1, None],
                    mode='lines',
                    line=dict(width=width, color=f'rgba(150,150,200,{opacity:.2f})'),
                    hoverinfo='text',
                    text=f"{edge[0]} ↔ {edge[1]}: {edge[2].get('raw', int(w))} games" + (f" ({w:.1f}%)" if net_mode == 'Normalized rate' else ""),
                    showlegend=False
                ))

            node_x, node_y, node_text, node_size, node_color = [], [], [], [], []
            for node in G.nodes():
                x, y = pos[node]
                node_x.append(x)
                node_y.append(y)
                total = player_game_totals.get(node, 0)
                node_text.append(f"{node}<br>Total games: {total}")
                node_size.append(min(70, 35 + total * 0.1))
                node_color.append(total)

            node_trace = go.Scatter(
                x=node_x, y=node_y,
                mode='markers+text',
                text=[n for n in G.nodes()],
                textposition='top center',
                textfont=dict(size=11, color='white'),
                marker=dict(size=node_size, color=node_color, colorscale='Viridis',
                            colorbar=dict(title='Games', thickness=15),
                            line=dict(width=2, color='white')),
                hovertext=node_text,
                hoverinfo='text',
                showlegend=False
            )

            fig_net = go.Figure(data=edge_traces + [node_trace])
            fig_net.update_layout(
                height=600,
                xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, title=''),
                yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, title='', scaleanchor='x'),
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                margin=dict(l=10, r=10, t=10, b=10),
                hovermode='closest'
            )
            st.plotly_chart(fig_net, use_container_width=True)
        else:
            st.info(f'No pairs with {net_min}+ shared games. Lower the slider.')

        # =========================================
        # Money Flow Sankey Diagram
        # =========================================
        st.markdown('---')
        st.subheader('🌊 Money Flow (Sankey Diagram)')
        st.markdown("Visualizes how money flowed between players overall. Left side = net losers (sources), right side = net winners (sinks).")

        # Calculate net flows between pairs
        flows = {}
        for game_id, group in df.groupby('ゲームID'):
            group = group[group['参加フラグ']]
            if group.empty: continue
            winners = group[group['収支'] > 0]
            losers = group[group['収支'] < 0]
            total_win = winners['収支'].sum()
            if total_win <= 0: continue
            for _, loser in losers.iterrows():
                payer = loser['プレイヤー']
                lost_amount = abs(loser['収支'])
                for _, winner in winners.iterrows():
                    payee = winner['プレイヤー']
                    win_amount = winner['収支']
                    if payer == payee: continue
                    flow_amount = lost_amount * (win_amount / total_win)
                    p1, p2 = min(payer, payee), max(payer, payee)
                    pair = (p1, p2)
                    if payer == p1:
                        flows[pair] = flows.get(pair, 0) + flow_amount
                    else:
                        flows[pair] = flows.get(pair, 0) - flow_amount

        directed_flows = []
        for (p1, p2), net in flows.items():
            if abs(net) < 1.0: continue
            if net > 0:
                directed_flows.append({'source': p1, 'target': p2, 'weight': net})
            else:
                directed_flows.append({'source': p2, 'target': p1, 'weight': abs(net)})

        if not directed_flows:
            st.info('No money flow data available.')
        else:
            sankey_max_flow = max(d['weight'] for d in directed_flows)
            sankey_min_flow = st.slider(
                'Min. flow amount to display',
                min_value=1, max_value=int(sankey_max_flow) + 1,
                value=int(sankey_max_flow * 0.1) if sankey_max_flow >= 10 else 1,
                help='Filter out small flows to focus on major transfers.'
            )
            sankey_flows = [d for d in directed_flows if d['weight'] >= sankey_min_flow]

            if not sankey_flows:
                st.info('No flows meet the threshold. Lower the slider.')
            else:
                all_sankey_nodes = list(set([d['source'] for d in sankey_flows] + [d['target'] for d in sankey_flows]))
                node_indices = {name: i for i, name in enumerate(all_sankey_nodes)}
                source_idx = [node_indices[d['source']] for d in sankey_flows]
                target_idx = [node_indices[d['target']] for d in sankey_flows]
                values = [d['weight'] for d in sankey_flows]

                sankey_node_colors = []
                for node in all_sankey_nodes:
                    in_val = sum(d['weight'] for d in sankey_flows if d['target'] == node)
                    out_val = sum(d['weight'] for d in sankey_flows if d['source'] == node)
                    if in_val > out_val:
                        sankey_node_colors.append('rgba(46, 204, 64, 0.8)')
                    else:
                        sankey_node_colors.append('rgba(255, 65, 54, 0.8)')

                fig_sankey = go.Figure(data=[go.Sankey(
                    valueformat='.1f',
                    valuesuffix=f' {currency_symbol}',
                    node=dict(
                        pad=20, thickness=30,
                        line=dict(color='white', width=1.0),
                        label=all_sankey_nodes,
                        color=sankey_node_colors
                    ),
                    link=dict(
                        source=source_idx, target=target_idx, value=values,
                        color=['rgba(150,150,150,0.3)' for _ in sankey_flows]
                    )
                )])
                fig_sankey.update_layout(
                    font_size=12, height=500,
                    margin=dict(l=10, r=10, t=20, b=10),
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)'
                )
                st.plotly_chart(fig_sankey, use_container_width=True)

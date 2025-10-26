# dashboard_pro.py  -- Pro Dashboard 2.0
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import mplfinance as mpf
import yfinance as yf
from datetime import datetime
from ta.trend import MACD
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands, AverageTrueRange
import plotly.graph_objects as go
import plotly.express as px
import time

# ====== Twoje sektory ======
from stock_market_agent_new import STOCK_SECTORS

# ====== Page config ======
st.set_page_config(page_title="StockMatrix742 — Pro", layout="wide", initial_sidebar_state="collapsed")

# ====== Top CSS small tweaks ======
st.markdown("""
    <style>
      .live-indicator { position: fixed; top: 20px; right: 25px; background-color: #ff4d4d; color: white; font-weight: bold; border-radius: 50px; padding: 6px 12px; animation: pulse 1s infinite; z-index: 9999; }
      @keyframes pulse { 0% {opacity:1;} 50% {opacity:0.5;} 100% {opacity:1;} }
      .card { padding: 8px 12px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); background-color: white; }
      .small-muted { color: #6c757d; font-size:12px; }
    </style>
""", unsafe_allow_html=True)

# ====== Sidebar settings ======
st.sidebar.title("⚙️ Settings — Pro")
selected_sector = st.sidebar.selectbox("Select Sector", list(STOCK_SECTORS.keys()))
custom_symbol = st.sidebar.text_input("🔍 Symbol (e.g. AAPL)").upper()
period_option = st.sidebar.select_slider("Select Time Range",
                                        options=["7d", "30d", "3mo", "6mo", "1y", "2y", "5y"], value="3mo")
chart_backend = st.sidebar.radio("Chart Backend", ["Plotly (interactive)", "mplfinance (classic)"])
compare_peer = st.sidebar.text_input("Compare with (peer ticker, optional)").upper()
compact_mode = st.sidebar.checkbox("Compact view", value=False)
auto_refresh = st.sidebar.checkbox("Enable Auto-Refresh (cache bust)", value=False)
refresh_interval = st.sidebar.slider("Refresh Interval (minutes)", 1, 15, 5)

live_mode = st.sidebar.checkbox("Live Mode (every 30s)", value=False)

# helpers for period -> yfinance timeframe
_period_map = {
    "7d": "7d", "30d": "30d", "3mo": "3mo", "6mo": "6mo", "1y": "1y", "2y": "2y", "5y": "5y"
}
yf_period = _period_map.get(period_option, "3mo")

# ====== caching & utilities ======
@st.cache_data(ttl=60)
def fetch_ticker_hist(symbol: str, period: str = "3mo", interval: str = "1d"):
    try:
        t = yf.Ticker(symbol)
        info = t.info
        hist = t.history(period=period, interval=interval)
        if hist is None or len(hist) == 0:
            return pd.DataFrame(), info
        hist = hist.dropna(how='all').fillna(method='ffill').fillna(method='bfill')
        return hist, info
    except Exception:
        return pd.DataFrame(), {}

def compute_indicators(df: pd.DataFrame):
    out = df.copy()
    if 'Close' in out:
        # RSI
        try:
            rsi = RSIIndicator(out['Close'], window=14)
            out['RSI'] = rsi.rsi()
        except Exception:
            out['RSI'] = np.nan
        # MACD
        try:
            macd = MACD(out['Close'])
            out['MACD'] = macd.macd()
            out['MACD_Signal'] = macd.macd_signal()
        except Exception:
            out['MACD'] = out['MACD_Signal'] = np.nan
        # Bollinger
        try:
            bb = BollingerBands(out['Close'])
            out['BB_Upper'] = bb.bollinger_hband()
            out['BB_Lower'] = bb.bollinger_lband()
        except Exception:
            out['BB_Upper'] = out['BB_Lower'] = np.nan
        # SMA/EMA
        out['SMA_20'] = out['Close'].rolling(window=20).mean()
        out['EMA_20'] = out['Close'].ewm(span=20, adjust=False).mean()
        # OBV
        out['OBV'] = (np.sign(out['Close'].diff().fillna(0)) * out['Volume']).cumsum()
        # ATR
        try:
            atr = AverageTrueRange(high=out['High'], low=out['Low'], close=out['Close'], window=14)
            out['ATR'] = atr.average_true_range()
        except Exception:
            out['ATR'] = np.nan
    return out

def compute_return_pct(df: pd.DataFrame):
    if len(df) < 2:
        return 0.0
    return (df['Close'].iloc[-1] / df['Close'].iloc[0] - 1) * 100

def signal_from_indicators(latest):
    # heuristic signal
    rsi = latest.get('RSI', np.nan)
    macd = latest.get('MACD', np.nan)
    macd_s = latest.get('MACD_Signal', np.nan)
    obv = latest.get('OBV', np.nan)
    atr = latest.get('ATR', np.nan)
    score = 0
    reason = []
    if not np.isnan(rsi):
        if rsi < 30:
            score += 2; reason.append("RSI low")
        elif rsi > 70:
            score -= 2; reason.append("RSI high")
    if not np.isnan(macd) and not np.isnan(macd_s):
        if macd > macd_s:
            score += 1; reason.append("MACD bullish")
        elif macd < macd_s:
            score -= 1; reason.append("MACD bearish")
    if not np.isnan(obv) and obv > 0:
        score += 0.5; reason.append("OBV positive")
    if not np.isnan(atr) and atr > 0:
        # higher ATR -> more volatile
        reason.append("ATR present")
    if score >= 2.5:
        return "Strong Buy", " / ".join(reason)
    elif score >= 1:
        return "Buy", " / ".join(reason)
    elif score <= -2:
        return "Strong Sell", " / ".join(reason)
    elif score <= -1:
        return "Sell", " / ".join(reason)
    return "Neutral", " / ".join(reason)

# ====== Live refresh handling ======
if live_mode:
    st.markdown("<div class='live-indicator'>LIVE 🔴</div>", unsafe_allow_html=True)
    last_live = st.session_state.get("last_live", time.time())
    elapsed = time.time() - last_live
    st.sidebar.write(f"Next update in {30 - int(elapsed % 30)}s")
    if elapsed >= 30:
        st.session_state["last_live"] = time.time()
        st.experimental_rerun()
else:
    st.session_state.pop("last_live", None)

if auto_refresh:
    last_update_time = st.session_state.get("last_update_time", time.time())
    if time.time() - last_update_time > refresh_interval * 60:
        st.session_state["last_update_time"] = time.time()
        st.experimental_rerun()

# ====== Page header ======
title_col1, title_col2 = st.columns([8,2])
with title_col1:
    st.title("📈 StockMatrix742 — Pro Dashboard")
    st.markdown(f"#### {selected_sector} analysis — {period_option} — backend: {chart_backend}")
with title_col2:
    st.caption(f"Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if compact_mode:
        st.caption("Compact view: ON")

# ====== Select stock ======
sector_stocks = STOCK_SECTORS[selected_sector]
selected_stock = custom_symbol if custom_symbol else st.selectbox("Select Stock", sector_stocks)

# fetch data for main ticker and optional peer
hist_data, info = fetch_ticker_hist(selected_stock, period=yf_period)
if compare_peer:
    hist_peer, info_peer = fetch_ticker_hist(compare_peer, period=yf_period)
else:
    hist_peer, info_peer = pd.DataFrame(), {}

# compute indicators safely
if not hist_data.empty:
    hist_data = compute_indicators(hist_data)
if not hist_peer.empty:
    hist_peer = compute_indicators(hist_peer)

# ========== Tabs: Chart / Analysis / Sector ==========
tab_chart, tab_analysis, tab_sector = st.tabs(["📊 Chart", "🧠 Analysis", "🏭 Sector Overview"])

# ---------- Chart tab ----------
with tab_chart:
    col_left, col_right = st.columns([3,1]) if not compact_mode else st.columns([4,1])
    with col_left:
        if hist_data.empty:
            st.warning(f"No data for {selected_stock}. Try another ticker or longer period.")
        else:
            # interactive Plotly chart (candlestick + indicators)
            if chart_backend.startswith("Plotly"):
                fig = go.Figure()
                fig.add_trace(go.Candlestick(x=hist_data.index, open=hist_data['Open'], high=hist_data['High'],
                                             low=hist_data['Low'], close=hist_data['Close'], name=selected_stock))
                # overlays if present
                if 'SMA_20' in hist_data and hist_data['SMA_20'].notna().any():
                    fig.add_trace(go.Scatter(x=hist_data.index, y=hist_data['SMA_20'], name='SMA20', mode='lines'))
                if 'EMA_20' in hist_data and hist_data['EMA_20'].notna().any():
                    fig.add_trace(go.Scatter(x=hist_data.index, y=hist_data['EMA_20'], name='EMA20', mode='lines'))
                if 'BB_Upper' in hist_data and hist_data['BB_Upper'].notna().any():
                    fig.add_trace(go.Scatter(x=hist_data.index, y=hist_data['BB_Upper'], name='BB Upper', line={'dash':'dash'}))
                if 'BB_Lower' in hist_data and hist_data['BB_Lower'].notna().any():
                    fig.add_trace(go.Scatter(x=hist_data.index, y=hist_data['BB_Lower'], name='BB Lower', line={'dash':'dash'}))

                # If comparing with peer -> show normalized percent-change overlay
                if not hist_peer.empty:
                    # align indices by reindexing to intersection
                    common = hist_data.index.intersection(hist_peer.index)
                    if len(common) > 1:
                        base_main = hist_data.loc[common, 'Close']
                        base_peer = hist_peer.loc[common, 'Close']
                        norm_main = (base_main / base_main.iloc[0] - 1) * 100
                        norm_peer = (base_peer / base_peer.iloc[0] - 1) * 100
                        fig2 = go.Figure()
                        fig2.add_trace(go.Scatter(x=common, y=norm_main, name=selected_stock + " %"))
                        fig2.add_trace(go.Scatter(x=common, y=norm_peer, name=compare_peer + " %"))
                        fig2.update_layout(title=f"Comparison (% change since start of period)", yaxis_title="% change")
                        st.plotly_chart(fig2, use_container_width=True)

                fig.update_layout(margin=dict(l=10, r=10, t=30, b=10), height=550, xaxis_rangeslider_visible=False)
                st.plotly_chart(fig, use_container_width=True)
            else:
                # fallback mplfinance
                df_mpf = hist_data[['Open','High','Low','Close','Volume']].copy()
                addplots = []
                if 'BB_Upper' in hist_data and hist_data['BB_Upper'].notna().any():
                    addplots.append(mpf.make_addplot(hist_data['BB_Upper'], color='gray', linestyle='--'))
                if 'BB_Lower' in hist_data and hist_data['BB_Lower'].notna().any():
                    addplots.append(mpf.make_addplot(hist_data['BB_Lower'], color='gray', linestyle='--'))
                if 'SMA_20' in hist_data and hist_data['SMA_20'].notna().any():
                    addplots.append(mpf.make_addplot(hist_data['SMA_20'], color='orange'))
                fig, axlist = mpf.plot(df_mpf, type='candle', addplot=addplots if addplots else None, volume=True,
                                       returnfig=True, figsize=(12,6))
                st.pyplot(fig)

    with col_right:
        # Key metrics + fundamental data
        st.subheader("Quick Snapshot")
        if not hist_data.empty:
            last_close = hist_data['Close'].iloc[-1]
            prev_close = hist_data['Close'].iloc[-2] if len(hist_data) > 1 else last_close
            pct_change = (last_close / prev_close - 1) * 100 if prev_close != 0 else 0.0
            # colored metric box
            color = "green" if pct_change >= 0 else "red"
            st.markdown(f"<div class='card'><h3 style='margin:0'>${last_close:.2f}</h3><div class='small-muted'>Change: <span style='color:{color}; font-weight:700'>{pct_change:+.2f}%</span></div></div>", unsafe_allow_html=True)

            # fundamentals (if available)
            if info:
                marketcap = info.get('marketCap', None)
                pe = info.get('trailingPE', None)
                eps = info.get('trailingEps', None)
                col_f1, col_f2 = st.columns(2)
                with col_f1:
                    st.metric("Market Cap", f"${marketcap/1e9:.2f}B" if marketcap else "N/A")
                    st.metric("P/E", f"{pe:.2f}" if pe else "N/A")
                with col_f2:
                    st.metric("EPS", f"{eps:.2f}" if eps else "N/A")
                    st.metric("Period return", f"{compute_return_pct(hist_data):+.2f}%")
            # download & CSV
            csv = hist_data.to_csv().encode('utf-8')
            st.download_button("💾 Download CSV", data=csv, file_name=f"{selected_stock}_data.csv")
        else:
            st.info("No data to show snapshot.")

# ---------- Analysis tab ----------
with tab_analysis:
    left, right = st.columns([2,1])
    with left:
        st.subheader("Technical Analysis & Signals")
        if hist_data.empty:
            st.warning("No data.")
        else:
            latest = hist_data.iloc[-1].to_dict()
            signal, reason = signal_from_indicators(latest)
            # fancy box
            color_box = {"Strong Buy":"#0f9d58","Buy":"#2e7d32","Neutral":"#6c757d","Sell":"#d32f2f","Strong Sell":"#b71c1c"}
            st.markdown(f"<div class='card'><h3 style='color:{color_box.get(signal,'black')}; margin:0'>{signal}</h3><p class='small-muted' style='margin:6px 0 0 0'>Reasons: {reason or '—'}</p></div>", unsafe_allow_html=True)

            # Show indicators
            st.write("Latest indicators:")
            ind_cols = st.columns(4)
            def show_ind(col, label, val, fmt="{:.2f}"):
                col.markdown(f"**{label}**")
                col.markdown(f"<div style='font-size:20px'>{fmt.format(val) if val is not None and not (isinstance(val,float) and np.isnan(val)) else 'N/A'}</div>", unsafe_allow_html=True)

            show_ind(ind_cols[0], "RSI (14)", latest.get('RSI', np.nan))
            show_ind(ind_cols[1], "MACD", latest.get('MACD', np.nan))
            show_ind(ind_cols[2], "OBV", latest.get('OBV', np.nan), "{:.0f}")
            show_ind(ind_cols[3], "ATR", latest.get('ATR', np.nan))

            st.markdown("**AI-like comment:**")
            # short generated commentary
            def commentary(df):
                latest = df.iloc[-1]
                trend = "uptrend" if df['Close'].iloc[-1] > df['Close'].iloc[0] else "downtrend"
                rsi = latest.get('RSI', np.nan)
                macd = latest.get('MACD', np.nan)
                macd_s = latest.get('MACD_Signal', np.nan)
                lines = []
                lines.append(f"{selected_stock} shows a {trend} over selected period.")
                if not np.isnan(rsi):
                    if rsi < 35: lines.append("RSI indicates oversold conditions.")
                    elif rsi > 65: lines.append("RSI indicates overbought conditions.")
                if not np.isnan(macd) and not np.isnan(macd_s):
                    if macd > macd_s: lines.append("Recent MACD crossover is bullish.")
                    else: lines.append("MACD indicates bearish momentum.")
                if df['Volume'].iloc[-1] > df['Volume'].rolling(20).mean().iloc[-1]:
                    lines.append("Volume spike in latest session.")
                return " ".join(lines)
            st.info(commentary(hist_data))

            # Simple alert widgets
            st.markdown("**Alerts (simple rules)**")
            if latest.get('RSI', np.nan) < 30:
                st.success("💚 RSI < 30 — Potential BUY (oversold)")
            if latest.get('RSI', np.nan) > 70:
                st.error("🔴 RSI > 70 — Potential SELL (overbought)")
            if latest.get('MACD', np.nan) > latest.get('MACD_Signal', np.nan):
                st.success("MACD > MACD_Signal — bullish crossover")
            if latest.get('MACD', np.nan) < latest.get('MACD_Signal', np.nan):
                st.warning("MACD < MACD_Signal — bearish crossover")

            # Historical indicator plots quick (plotly)
            st.markdown("**Indicator charts**")
            ind_fig = go.Figure()
            if 'RSI' in hist_data and hist_data['RSI'].notna().any():
                ind_fig.add_trace(go.Scatter(x=hist_data.index, y=hist_data['RSI'], name='RSI'))
                ind_fig.add_hline(y=70, line_dash="dash", line_color="red")
                ind_fig.add_hline(y=30, line_dash="dash", line_color="green")
            if 'MACD' in hist_data and hist_data['MACD'].notna().any():
                ind_fig.add_trace(go.Scatter(x=hist_data.index, y=hist_data['MACD'], name='MACD'))
                ind_fig.add_trace(go.Scatter(x=hist_data.index, y=hist_data['MACD_Signal'], name='MACD Signal'))
            ind_fig.update_layout(height=350, showlegend=True, margin=dict(l=10,r=10,t=20,b=10))
            st.plotly_chart(ind_fig, use_container_width=True)

    with right:
        st.subheader("Compare & Filters")
        st.markdown("Pick a second ticker to compare (in sidebar).")
        st.markdown("---")
        st.write("Resampling (for large periods):")
        rs = st.selectbox("Resample to", options=["None","1D","1W","1M"], index=0)
        if rs != "None" and not hist_data.empty:
            rule = rs
            hist_data_res = hist_data.resample(rule).agg({'Open':'first','High':'max','Low':'min','Close':'last','Volume':'sum'}).dropna()
            st.markdown(f"Resampled to {rs}, rows: {len(hist_data_res)}")
        else:
            hist_data_res = hist_data

# ---------- Sector tab ----------
with tab_sector:
    st.subheader(f"Sector Overview — {selected_sector}")
    # build sector heatmap/treemap
    symbols = sector_stocks[:30]
    sector_rows = []
    for s in symbols:
        h, _ = fetch_ticker_hist(s, period="5d")
        if h is None or h.empty:
            sector_rows.append({"symbol": s, "change": np.nan})
        else:
            ch = (h['Close'].iloc[-1] / h['Close'].iloc[0] - 1) * 100 if len(h) > 1 else 0.0
            sector_rows.append({"symbol": s, "change": ch})
    df_sector = pd.DataFrame(sector_rows).dropna()
    if not df_sector.empty:
        fig = px.treemap(df_sector, path=['symbol'], values='change', color='change', color_continuous_scale='RdYlGn', title='Sector performance (last 5d)')
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No sector data available.")

    # quick table
    if not df_sector.empty:
        st.dataframe(df_sector.sort_values('change', ascending=False).reset_index(drop=True).style.format({'change':'{:+.2f}%'}), height=300)

# ====== Footer ======
st.markdown("---")
st.caption("Pro Dashboard enhancements: interactive plotly charts, comparison overlay, OBV/ATR, alerts, fundamentals & sector treemap.")

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import mplfinance as mpf
import yfinance as yf
from datetime import datetime
from ta.trend import MACD
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands
import time

# ====== Twoje sektory ======
from stock_market_agent_new import STOCK_SECTORS

# ====== Konfiguracja strony ======
st.set_page_config(
    page_title="StockMatrix Pro 3.0",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ====== Styl i CSS ======
st.markdown("""
<style>
body { background-color: #0e1117; color: #e8e6e3; }
.metric-card { padding: 10px; border-radius: 8px; background-color: #1c1f26; margin-bottom: 10px; }
.signal-box { border-radius: 8px; padding: 10px; font-weight: bold; text-align: center; }
.live-indicator {
    position: fixed; top: 20px; right: 25px;
    background-color: #ff0000; color: white;
    font-weight: bold; border-radius: 50px;
    padding: 6px 12px; animation: pulse 1s infinite;
    z-index: 9999;
}
.ticker-bar {
    background-color: #1c1f26; padding: 5px 10px; color: #ffffff; font-weight: bold; border-radius: 5px; margin-bottom: 10px;
}
@keyframes pulse { 0% {opacity:1;} 50%{opacity:0.5;} 100%{opacity:1;} }
</style>
""", unsafe_allow_html=True)

# ====== Sidebar ======
st.sidebar.title("⚙️ Settings")

selected_sector = st.sidebar.selectbox("Select Sector", list(STOCK_SECTORS.keys()))
custom_symbol = st.sidebar.text_input("🔍 Custom symbol (e.g. TSLA)").upper()

period_option = st.sidebar.select_slider(
    "Select Time Range",
    options=["7d", "30d", "3mo", "6mo", "1y", "2y", "5y"],
    value="30d"
)

chart_type = st.sidebar.radio("Chart Type", ["Candle", "Line", "Bar"])
chart_map = {"Candle": "candle", "Line": "line", "Bar": "ohlc"}

theme = st.sidebar.radio("Theme", ["Light", "Dark"])
style = "yahoo" if theme == "Light" else "nightclouds"

refresh_interval = st.sidebar.slider("Refresh Interval (minutes)", 1, 10, 3)
auto_refresh = st.sidebar.toggle("Enable Auto-Refresh", True)
live_mode = st.sidebar.toggle("🚀 Enable Live Mode (every 30s)", False)
compact_view = st.sidebar.toggle("🧩 Compact View", False)

# ====== Live Ticker Bar ======
indices = {"S&P500": "^GSPC", "NASDAQ": "^IXIC", "DOW": "^DJI", "BTC": "BTC-USD"}
ticker_data = {}
for name, symbol in indices.items():
    try:
        hist = yf.Ticker(symbol).history(period="1d")
        last_price = hist['Close'].iloc[-1] if not hist.empty else 0
        change = (hist['Close'].iloc[-1]/hist['Close'].iloc[0]-1)*100 if len(hist) > 1 else 0
        ticker_data[name] = (last_price, change)
    except:
        ticker_data[name] = (0,0)

ticker_html = " | ".join([f"{name}: ${price:.2f} ({change:+.2f}%)" for name,(price,change) in ticker_data.items()])
st.markdown(f"<div class='ticker-bar'>{ticker_html}</div>", unsafe_allow_html=True)

# ====== Cache danych ======
@st.cache_data(ttl=60)
def get_stock_data(symbol, period='30d'):
    try:
        stock = yf.Ticker(symbol)
        info = stock.info
        if 'regularMarketPrice' not in info or info['regularMarketPrice'] is None:
            return pd.DataFrame()
        hist = stock.history(period=period)
        if len(hist) == 0:
            return pd.DataFrame()
        hist = hist.fillna(method='ffill').fillna(method='bfill')

        rsi = RSIIndicator(close=hist['Close'], window=14)
        macd = MACD(close=hist['Close'])
        bb = BollingerBands(close=hist['Close'])

        hist['RSI'] = rsi.rsi()
        hist['MACD'] = macd.macd()
        hist['MACD_Signal'] = macd.macd_signal()
        hist['BB_Upper'] = bb.bollinger_hband()
        hist['BB_Lower'] = bb.bollinger_lband()
        hist['SMA_20'] = hist['Close'].rolling(window=20).mean()
        hist['EMA_20'] = hist['Close'].ewm(span=20, adjust=False).mean()
        return hist
    except Exception:
        return pd.DataFrame()

def get_signal(rsi, macd, macd_signal):
    if rsi < 30 and macd > macd_signal:
        return "Buy"
    elif rsi > 70 and macd < macd_signal:
        return "Sell"
    return "Neutral"

def get_signal_strength(rsi, macd, macd_signal, volatility):
    strength = 5
    if rsi < 20 or rsi > 80:
        strength += 2
    elif rsi < 30 or rsi > 70:
        strength += 1
    macd_diff = abs(macd - macd_signal)
    if macd_diff > 0.5:
        strength += 2
    elif macd_diff > 0.2:
        strength += 1
    if volatility > 3:
        strength += 1
    return min(10, strength)

def interpret_signal(signal, rsi, volatility):
    if signal == "Buy" and rsi < 40:
        return "📈 The stock appears undervalued and gaining momentum."
    elif signal == "Sell" and rsi > 60:
        return "📉 Possible overbought conditions detected."
    elif volatility and volatility > 4:
        return "⚠️ High volatility – price swings expected."
    return "⚖️ Neutral market conditions."

# ====== Live Mode / Auto-refresh ======
if live_mode:
    st.markdown("<div class='live-indicator'>LIVE 🔴</div>", unsafe_allow_html=True)
    st.session_state["last_live_refresh"] = st.session_state.get("last_live_refresh", time.time())
    elapsed = time.time() - st.session_state["last_live_refresh"]
    if elapsed >= 30:
        st.session_state["last_live_refresh"] = time.time()
        st.rerun()

if auto_refresh and not live_mode:
    last_update_time = st.session_state.get("last_update_time", time.time())
    if time.time() - last_update_time > refresh_interval * 60:
        st.session_state["last_update_time"] = time.time()
        st.rerun()

# ====== Layout ======
st.title("📊 StockMatrix Pro 3.0 Dashboard")
st.markdown(f"#### {selected_sector} Sector Analysis")

sector_stocks = STOCK_SECTORS[selected_sector]
selected_stock = custom_symbol if custom_symbol else st.selectbox("Select Stock for Detailed Analysis", sector_stocks)

# ====== Porównywarka spółek ======
compare_symbols = st.multiselect("Compare with...", sector_stocks, default=[])
if selected_stock not in compare_symbols and selected_stock:
    compare_symbols.insert(0, selected_stock)

# ====== Główne kolumny ======
col1, col2, col3 = st.columns([2, 1, 1])

# ====== COL1 - wykres ======
with col1:
    if compare_symbols:
        plt.close('all')
        fig, axlist = plt.subplots(figsize=(12,6))
        for sym in compare_symbols:
            hist = get_stock_data(sym, period=period_option)
            if not hist.empty:
                trend = (hist['Close']/hist['Close'].iloc[0]-1)*100
                axlist.plot(trend, label=sym)
        axlist.set_title("Stock Comparison (% change)")
        axlist.set_ylabel("% Change")
        axlist.legend()
        st.pyplot(fig)

# ====== COL2 - analiza techniczna + fundamentals ======
with col2:
    st.subheader("🧠 Technical & Fundamentals")
    if selected_stock:
        hist_data = get_stock_data(selected_stock, period=period_option)
        if not hist_data.empty:
            current_price = hist_data['Close'].iloc[-1]
            daily_change = ((hist_data['Close'].iloc[-1]/hist_data['Close'].iloc[-2]-1)*100) if len(hist_data)>1 else 0
            current_rsi = hist_data['RSI'].iloc[-1]
            current_macd = hist_data['MACD'].iloc[-1]
            current_macd_signal = hist_data['MACD_Signal'].iloc[-1]
            volatility = hist_data['Close'].pct_change().std()*100

            signal = get_signal(current_rsi, current_macd, current_macd_signal)
            signal_strength = get_signal_strength(current_rsi, current_macd, current_macd_signal, volatility)

            # Technical metrics
            st.metric("Price (USD)", f"${current_price:.2f}")
            st.metric("Daily Change", f"{daily_change:+.2f}%")
            st.metric("RSI (14)", f"{current_rsi:.1f}")
            st.metric("Volatility", f"{volatility:.1f}%")

            color_map = {"Buy": "green", "Sell": "red", "Neutral": "gray"}
            st.markdown(f"<div class='signal-box' style='border:2px solid {color_map[signal]};color:{color_map[signal]};'>Signal: {signal}</div>", unsafe_allow_html=True)
            st.progress(signal_strength/10)
            st.caption(f"Signal Strength: {signal_strength}/10")
            st.info(interpret_signal(signal, current_rsi, volatility))

            # Fundamentals
            try:
                info = yf.Ticker(selected_stock).info
                st.metric("Market Cap", f"${info.get('marketCap',0)/1e9:.1f}B")
                st.metric("P/E Ratio", f"{info.get('trailingPE','–')}")
                st.metric("EPS", f"{info.get('trailingEps','–')}")
                st.metric("Beta", f"{info.get('beta','–')}")
            except:
                st.warning("Fundamental data not available.")

# ====== COL3 - sektor ======
with col3:
    st.subheader("🏭 Sector Overview")
    sector_data = []
    for symbol in sector_stocks[:10]:
        hist = get_stock_data(symbol, period='5d')
        if not hist.empty and len(hist)>=2:
            daily_return = (hist['Close'].iloc[-1]/hist['Close'].iloc[-2]-1)*100
            rsi_value = hist['RSI'].iloc[-1]
            current_price = hist['Close'].iloc[-1]
            sector_data.append({'Symbol': symbol, 'Price': current_price, 'Change': daily_return, 'RSI': rsi_value})

    if sector_data:
        sector_df = pd.DataFrame(sector_data).sort_values('Change', ascending=False)
        st.dataframe(sector_df.style.format({'Price':'${:.2f}','Change':'{:+.2f}%','RSI':'{:.1f}'}), height=380)

        # Mini sparkline / heatmap
        fig, ax = plt.subplots(figsize=(3.5,3))
        cmap = plt.cm.RdYlGn
        changes = sector_df['Change'].values
        norm = plt.Normalize(vmin=-max(abs(changes)), vmax=max(abs(changes)))
        colors = cmap(norm(changes))
        ax.barh(sector_df['Symbol'], sector_df['Change'], color=colors)
        ax.set_xlabel('% Change (5d)')
        ax.set_ylabel('Symbol')
        st.pyplot(fig)

# ====== Stopka ======
st.markdown("---")
st.caption(f"Data source: Yahoo Finance | Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

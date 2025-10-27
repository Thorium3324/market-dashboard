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
st.set_page_config(page_title="StockMatrix Pro 3.0", layout="wide", initial_sidebar_state="collapsed")

# ====== Styl ======
st.markdown("""
<style>
body { background-color: #0e1117; color: #e8e6e3; }
.metric-card { padding: 10px; border-radius: 8px; background-color: #1c1f26; margin-bottom: 10px; }
.signal-box { border-radius: 8px; padding: 10px; font-weight: bold; text-align: center; }
.live-indicator { position: fixed; top: 20px; right: 25px; background-color: #ff0000; color: white; font-weight: bold; border-radius: 50px; padding: 6px 12px; animation: pulse 1s infinite; z-index: 9999; }
.ticker-bar { background-color: #1c1f26; padding: 5px 10px; color: #ffffff; font-weight: bold; border-radius: 5px; margin-bottom: 10px; }
@keyframes pulse { 0% {opacity:1;} 50%{opacity:0.5;} 100%{opacity:1;} }
</style>
""", unsafe_allow_html=True)

# ====== Sidebar ======
st.sidebar.title("⚙️ Settings")
selected_sector = st.sidebar.selectbox("Select Sector", list(STOCK_SECTORS.keys()))
custom_symbol = st.sidebar.text_input("🔍 Custom symbol (e.g. TSLA)").upper()
period_option = st.sidebar.select_slider("Select Time Range", options=["7d","30d","3mo","6mo","1y","2y","5y"], value="30d")
chart_type = st.sidebar.radio("Chart Type", ["Candle", "Line", "Bar"])
chart_map = {"Candle": "candle", "Line": "line", "Bar": "ohlc"}
theme = st.sidebar.radio("Theme", ["Light", "Dark"])
style = "yahoo" if theme == "Light" else "nightclouds"

# ====== Rozszerzony suwak refresh ======
refresh_unit = st.sidebar.selectbox("Refresh unit", ["Minutes","Hours","Days"])
if refresh_unit=="Minutes":
    refresh_value = st.sidebar.slider("Refresh Interval", 1, 60, 5)
    refresh_seconds = refresh_value * 60
elif refresh_unit=="Hours":
    refresh_value = st.sidebar.slider("Refresh Interval", 1, 24, 1)
    refresh_seconds = refresh_value * 3600
else:
    refresh_value = st.sidebar.slider("Refresh Interval", 1, 7, 1)
    refresh_seconds = refresh_value * 86400  # dni w sekundach
auto_refresh = st.sidebar.toggle("Enable Auto-Refresh", True)
live_mode = st.sidebar.toggle("🚀 Enable Live Mode (every 30s)", False)

# ====== Live Ticker Bar ======
indices = {"S&P500":"^GSPC","NASDAQ":"^IXIC","DOW":"^DJI","BTC":"BTC-USD"}
ticker_data = {}
for name,symbol in indices.items():
    try:
        hist = yf.Ticker(symbol).history(period="1d")
        last_price = hist['Close'].iloc[-1] if not hist.empty else 0
        change = (hist['Close'].iloc[-1]/hist['Close'].iloc[0]-1)*100 if len(hist)>1 else 0
        ticker_data[name] = (last_price,change)
    except:
        ticker_data[name]=(0,0)
ticker_html = " | ".join([f"{name}: ${price:.2f} ({change:+.2f}%)" for name,(price,change) in ticker_data.items()])
st.markdown(f"<div class='ticker-bar'>{ticker_html}</div>", unsafe_allow_html=True)

# ====== Cache danych ======
@st.cache_data(ttl=60)
def get_stock_data(symbol, period='30d'):
    try:
        stock = yf.Ticker(symbol)
        hist = stock.history(period=period)
        if hist.empty: return pd.DataFrame()
        hist = hist.fillna(method='ffill').fillna(method='bfill')
        hist['RSI'] = RSIIndicator(hist['Close']).rsi()
        macd = MACD(hist['Close'])
        hist['MACD'] = macd.macd()
        hist['MACD_Signal'] = macd.macd_signal()
        bb = BollingerBands(hist['Close'])
        hist['BB_Upper'] = bb.bollinger_hband()
        hist['BB_Lower'] = bb.bollinger_lband()
        hist['SMA_20'] = hist['Close'].rolling(20).mean()
        hist['EMA_20'] = hist['Close'].ewm(span=20, adjust=False).mean()
        return hist
    except:
        return pd.DataFrame()

# ====== Wskaźniki i sygnały ======
def get_signal(rsi, macd, macd_signal):
    if rsi<30 and macd>macd_signal: return "Buy"
    elif rsi>70 and macd<macd_signal: return "Sell"
    return "Neutral"

def get_signal_strength(rsi, macd, macd_signal, volatility):
    strength=5
    if rsi<20 or rsi>80: strength+=2
    elif rsi<30 or rsi>70: strength+=1
    macd_diff=abs(macd-macd_signal)
    if macd_diff>0.5: strength+=2
    elif macd_diff>0.2: strength+=1
    if volatility>3: strength+=1
    return min(10,strength)

def interpret_signal(signal,rsi,volatility):
    if signal=="Buy" and rsi<40: return "📈 Undervalued and gaining momentum."
    elif signal=="Sell" and rsi>60: return "📉 Possible overbought."
    elif volatility>4: return "⚠️ High volatility – expect swings."
    return "⚖️ Neutral market."

# ====== Live Mode / Auto-refresh ======
if live_mode:
    st.markdown("<div class='live-indicator'>LIVE 🔴</div>", unsafe_allow_html=True)
    st.session_state["last_live_refresh"] = st.session_state.get("last_live_refresh", time.time())
    if time.time()-st.session_state["last_live_refresh"]>=30:
        st.session_state["last_live_refresh"]=time.time()
        st.rerun()
if auto_refresh:
    last_update_time = st.session_state.get("last_update_time",time.time())
    if time.time()-last_update_time>refresh_seconds:
        st.session_state["last_update_time"]=time.time()
        st.rerun()

# ====== Tabs ======
tab1,tab2,tab3,tab4 = st.tabs(["📈 Stocks","💰 Crypto","🪙 Metals","📊 Indices"])

# -------- Tab 1: Stocks --------
with tab1:
    st.header("Stock Dashboard")
    sector_stocks = STOCK_SECTORS[selected_sector]
    selected_stock = custom_symbol if custom_symbol else st.selectbox("Select Stock", sector_stocks)
    compare_symbols = st.multiselect("Compare with...", sector_stocks, default=[selected_stock] if selected_stock else [])

    col1,col2,col3 = st.columns([2,1,1])
    with col1:
        for sym in compare_symbols:
            hist_data = get_stock_data(sym, period=period_option)
            if hist_data.empty or hist_data.shape[0]<2:
                st.warning(f"Not enough data to plot {sym}.")
                continue
            df_mpf = hist_data[['Open','High','Low','Close','Volume']].copy()
            addplots=[]
            if 'SMA_20' in hist_data and hist_data['SMA_20'].notna().any():
                addplots.append(mpf.make_addplot(hist_data['SMA_20'], color='orange'))
            if 'EMA_20' in hist_data and hist_data['EMA_20'].notna().any():
                addplots.append(mpf.make_addplot(hist_data['EMA_20'], color='cyan'))
            if 'RSI' in hist_data and hist_data['RSI'].notna().any():
                addplots.append(mpf.make_addplot(hist_data['RSI'], panel=1, color='purple', ylabel='RSI'))
            if 'MACD' in hist_data and hist_data['MACD'].notna().any():
                addplots.append(mpf.make_addplot(hist_data['MACD'], panel=2, color='blue', ylabel='MACD'))
            if 'MACD_Signal' in hist_data and hist_data['MACD_Signal'].notna().any():
                addplots.append(mpf.make_addplot(hist_data['MACD_Signal'], panel=2, color='orange'))
            fig, axlist = mpf.plot(
                df_mpf,
                type=chart_map[chart_type],
                style=style,
                addplot=addplots if addplots else None,
                volume=True,
                returnfig=True,
                figsize=(12,8)
            )
            st.pyplot(fig)

# -------- Tab 2: Crypto --------
with tab2:
    st.header("Cryptocurrency Dashboard")
    crypto_symbols = ["BTC-USD","ETH-USD","BNB-USD","XRP-USD"]
    crypto_choice = st.selectbox("Select crypto", crypto_symbols)
    hist = get_stock_data(crypto_choice, period=period_option)
    if not hist.empty:
        plt.close('all')
        fig,ax=plt.subplots(figsize=(12,6))
        ax.plot(hist['Close'], label=crypto_choice)
        ax.set_title(f"{crypto_choice} Price")
        ax.legend()
        st.pyplot(fig)

# -------- Tab 3: Metals --------
with tab3:
    st.header("Metals Dashboard")
    metal_symbols = {"Gold":"GC=F","Silver":"SI=F","Platinum":"PL=F"}
    metal_choice = st.selectbox("Select metal", list(metal_symbols.keys()))
    hist = get_stock_data(metal_symbols[metal_choice], period="1y")
    if not hist.empty:
        plt.close('all')
        fig,ax=plt.subplots(figsize=(12,6))
        ax.plot(hist['Close'], label=metal_choice)
        ax.set_title(f"{metal_choice} Price")
        ax.legend()
        st.pyplot(fig)

# -------- Tab 4: Indices --------
with tab4:
    st.header("Market Indices")
    index_symbols = {"S&P500":"^GSPC","NASDAQ":"^IXIC","DOW":"^DJI"}
    index_choice = st.selectbox("Select index", list(index_symbols.keys()))
    hist = get_stock_data(index_symbols[index_choice], period="1y")
    if not hist.empty:
        plt.close('all')
        fig,ax=plt.subplots(figsize=(12,6))
        ax.plot(hist['Close'], label=index_choice)
        ax.set_title(f"{index_choice} Index")
        ax.legend()
        st.pyplot(fig)

# ====== Stopka ======
st.markdown("---")
st.caption(f"Data source: Yahoo Finance | Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

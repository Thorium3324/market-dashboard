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
st.set_page_config(page_title="StockMatrix Pro 4.0", layout="wide", initial_sidebar_state="collapsed")

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

# ====== Ticker bar ======
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

# ====== Sygnały i analiza ======
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

# ====== Auto-refresh / Live ======
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

# ====== Tab 1: Stocks ======
with tab1:
    st.header("Stock Dashboard")
    sector_stocks = STOCK_SECTORS[selected_sector]
    selected_stock = custom_symbol if custom_symbol else st.selectbox("Select Stock", sector_stocks)

    hist_data = get_stock_data(selected_stock, period=period_option)
    if hist_data.empty or hist_data.shape[0]<2:
        st.warning(f"Not enough data for {selected_stock}.")
    else:
        # ====== Wykres ======
        df_mpf = hist_data[['Open','High','Low','Close','Volume']].copy()
        addplots=[]
        for col,color,panel,ylabel in [('SMA_20','orange',0,''),('EMA_20','cyan',0,''),('RSI','purple',1,'RSI'),('MACD','blue',2,'MACD'),('MACD_Signal','orange',2,'')]:
            if col in hist_data and hist_data[col].notna().any():
                addplots.append(mpf.make_addplot(hist_data[col], panel=panel, color=color, ylabel=ylabel))
        fig,axlist=mpf.plot(df_mpf,type=chart_map[chart_type],style=style,addplot=addplots if addplots else None,volume=True,returnfig=True,figsize=(12,8))
        if len(axlist)>1:
            axlist[1].axhline(70,color='r',linestyle='--',alpha=0.5)
            axlist[1].axhline(30,color='g',linestyle='--',alpha=0.5)
        st.pyplot(fig)

        # ====== Analiza techniczna ======
        col1,col2=st.columns([1,1])
        with col1:
            current_price = hist_data['Close'].iloc[-1]
            daily_change = ((hist_data['Close'].iloc[-1]/hist_data['Close'].iloc[-2]-1)*100) if len(hist_data)>1 else 0
            st.metric("Price (USD)", f"${current_price:.2f}")
            st.metric("24h Change", f"{daily_change:+.2f}%")
        with col2:
            current_rsi = hist_data['RSI'].iloc[-1]
            current_macd = hist_data['MACD'].iloc[-1]
            current_macd_signal = hist_data['MACD_Signal'].iloc[-1]
            volatility = hist_data['Close'].pct_change().std()*100
            signal = get_signal(current_rsi,current_macd,current_macd_signal)
            signal_strength = get_signal_strength(current_rsi,current_macd,current_macd_signal,volatility)
            signal_color = {'Buy':'green','Sell':'red','Neutral':'gray'}
           

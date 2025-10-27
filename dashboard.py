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
.metric-card { padding: 15px; border-radius: 10px; background-color: #1c1f26; margin-bottom: 15px; }
.signal-box { border-radius: 8px; padding: 10px; font-weight: bold; text-align: center; margin-top:5px; }
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

# ====== Refresh ======
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

# ====== Sygnały ======
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
        st.experimental_rerun()
if auto_refresh:
    last_update_time = st.session_state.get("last_update_time",time.time())
    if time.time()-last_update_time>refresh_seconds:
        st.session_state["last_update_time"]=time.time()
        st.experimental_rerun()

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
        for col,color,panel,ylabel in [
            ('SMA_20','orange',0,''), 
            ('EMA_20','cyan',0,''), 
            ('RSI','purple',1,'RSI'), 
            ('MACD','blue',2,'MACD'), 
            ('MACD_Signal','orange',2,'')
        ]:
            if col in hist_data and hist_data[col].notna().any():
                addplots.append(mpf.make_addplot(hist_data[col], panel=panel, color=color, ylabel=ylabel))
        fig, axlist = mpf.plot(
            df_mpf,
            type=chart_map[chart_type],
            style=style,
            addplot=addplots if addplots else None,
            volume=True,
            returnfig=True,
            figsize=(12,8)
        )
        # ====== Linie poziome RSI tylko jeśli panel istnieje ======
        if 'RSI' in hist_data.columns and len(axlist)>1:
            try:
                axlist[1].axhline(70,color='r',linestyle='--',alpha=0.5)
                axlist[1].axhline(30,color='g',linestyle='--',alpha=0.5)
            except Exception:
                pass
        st.pyplot(fig)

        # ====== Analiza techniczna ======
        st.subheader("Technical Analysis")
        current_price = hist_data['Close'].iloc[-1]
        prev_price = hist_data['Close'].iloc[-2]
        daily_change = ((current_price/prev_price)-1)*100 if prev_price else 0
        current_rsi = hist_data['RSI'].iloc[-1]
        current_macd = hist_data['MACD'].iloc[-1]
        current_macd_signal = hist_data['MACD_Signal'].iloc[-1]
        volatility = hist_data['Close'].pct_change().std()*100

        signal = get_signal(current_rsi,current_macd,current_macd_signal)
        signal_strength = get_signal_strength(current_rsi,current_macd,current_macd_signal,volatility)
        signal_color = {'Buy':'green','Sell':'red','Neutral':'gray'}

        st.markdown(f"""
        <div class='metric-card'>
            <h4>Price: ${current_price:.2f}</h4>
            <h4>24h Change: {daily_change:+.2f}%</h4>
            <h4>RSI (14): {current_rsi:.1f}</h4>
            <h4>MACD: {current_macd:.3f}</h4>
            <h4>MACD Signal: {current_macd_signal:.3f}</h4>
            <h4>Volatility (30d): {volatility:.2f}%</h4>
            <div class='signal-box' style='border:2px solid {signal_color[signal]}; color:{signal_color[signal]}'>
                Signal: {signal} | Strength: {signal_strength}/10
            </div>
            <p>{interpret_signal(signal,current_rsi,volatility)}</p>
        </div>
        """, unsafe_allow_html=True)

        # ====== Pobranie CSV ======
        csv = hist_data.to_csv().encode('utf-8')
        st.download_button("💾 Download Data as CSV", data=csv, file_name=f"{selected_stock}_data.csv")

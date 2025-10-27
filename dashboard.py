import streamlit as st
import pandas as pd
import yfinance as yf
import mplfinance as mpf
from ta.trend import MACD
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands
import time
import numpy as np

from stock_market_agent_new import STOCK_SECTORS

st.set_page_config(page_title="StockMatrix Pro 4.0", layout="wide")

# ====== Styl ======
st.markdown("""
<style>
body { background-color: #0e1117; color: #e8e6e3; font-family: 'Verdana', sans-serif; }
.metric-card { padding: 12px; border-radius: 10px; margin-bottom: 12px; background-color: #1c1f26; font-size: 14px; }
.signal-box { padding: 10px; border-radius: 8px; text-align: center; margin-top:5px; font-size: 16px; color:white; font-weight:bold; }
</style>
""", unsafe_allow_html=True)

# ====== Lewy panel: wybór rynku i symbolu ======
st.sidebar.title("⚙️ Markets & Symbols")

market_option = st.sidebar.selectbox("Select Market", ["Stocks","Crypto","Metals","Bonds","ETFs"])

# W zależności od rynku wybór symboli
if market_option=="Stocks":
    selected_sector = st.sidebar.selectbox("Select Sector", list(STOCK_SECTORS.keys()))
    symbol_list = STOCK_SECTORS[selected_sector]
elif market_option=="Crypto":
    symbol_list = ["BTC-USD","ETH-USD","BNB-USD","SOL-USD","ADA-USD"]
elif market_option=="Metals":
    symbol_list = ["GC=F","SI=F","PL=F","HG=F"]  # Gold, Silver, Platinum, Copper futures
elif market_option=="Bonds":
    symbol_list = ["^TNX","^IRX"]  # 10Y, 3M Treasury yields
elif market_option=="ETFs":
    symbol_list = ["SPY","QQQ","IWM","DIA","GLD","SLV"]

custom_symbol = st.sidebar.text_input("Custom symbol (optional)").upper()
selected_symbol = custom_symbol if custom_symbol else st.sidebar.selectbox("Select Symbol", symbol_list)

# Zakres czasu i chart type
period_option = st.sidebar.selectbox("Select Time Range", ["7d","30d","3mo","6mo","1y","2y","5y"], index=1)
chart_type_option = st.sidebar.radio("Chart Type", ["Candle", "Line", "Bar"])
theme = st.sidebar.radio("Theme", ["Light", "Dark"])
style = "yahoo" if theme=="Light" else "nightclouds"
chart_type_map = {"Candle":"candle", "Line":"line", "Bar":"ohlc"}

# Live mode
live_mode = st.sidebar.checkbox("Live Mode (refresh every 30s)")
refresh_interval = 30  # seconds

# ====== Fetch data ======
@st.cache_data(ttl=60)
def get_data(symbol, period='30d'):
    try:
        stock = yf.Ticker(symbol)
        hist = stock.history(period=period)
        if hist.empty or len(hist)<2: return pd.DataFrame()
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

# ====== Main layout ======
st.title("📊 StockMatrix Pro 4.0")

# Dynamic refresh
if live_mode:
    if 'last_refresh' not in st.session_state:
        st.session_state['last_refresh'] = time.time()
    if time.time() - st.session_state['last_refresh'] >= refresh_interval:
        st.session_state['last_refresh'] = time.time()
        st.experimental_rerun()

hist_data = get_data(selected_symbol, period=period_option)

col1, col2 = st.columns([2,1])

# ----- Wykres -----
with col1:
    if hist_data.empty:
        st.warning(f"No data for {selected_symbol}")
    else:
        df_mpf = hist_data[['Open','High','Low','Close','Volume']]
        addplots=[]
        for col,color,panel,ylabel in [('SMA_20','orange',0,''), ('EMA_20','cyan',0,''), ('RSI','purple',1,'RSI'), ('MACD','blue',2,'MACD'), ('MACD_Signal','orange',2,'')]:
            if col in hist_data.columns and hist_data[col].notna().any():
                addplots.append(mpf.make_addplot(hist_data[col], panel=panel, color=color, ylabel=ylabel))

        try:
            fig, axlist = mpf.plot(df_mpf, type=chart_type_map[chart_type_option], style=style,
                                   addplot=addplots if addplots else None, volume=True, returnfig=True, figsize=(8,5))
            st.pyplot(fig)
        except Exception as e:
            st.error(f"Error rendering chart: {e}")

# ----- Prawy panel: wskaźniki -----
with col2:
    if not hist_data.empty:
        current_price = hist_data['Close'].iloc[-1]
        prev_price = hist_data['Close'].iloc[-2]
        daily_change = ((current_price/prev_price)-1)*100
        current_rsi = hist_data['RSI'].iloc[-1]
        current_macd = hist_data['MACD'].iloc[-1]
        current_macd_signal = hist_data['MACD_Signal'].iloc[-1]
        volatility = hist_data['Close'].pct_change().std()*100
        sma_20 = hist_data['SMA_20'].iloc[-1]
        ema_20 = hist_data['EMA_20'].iloc[-1]
        bb_upper = hist_data['BB_Upper'].iloc[-1]
        bb_lower = hist_data['BB_Lower'].iloc[-1]

        if current_rsi<30 and current_macd>current_macd_signal:
            signal_text = "BUY"
            signal_color = "green"
        elif current_rsi>70 and current_macd<current_macd_signal:
            signal_text = "SELL"
            signal_color = "red"
        else:
            signal_text = "HOLD"
            signal_color = "gray"

        change_color = "green" if daily_change>0 else "red" if daily_change<0 else "white"

        st.markdown(f"""
        <div class='metric-card'><b>Price:</b> <span style='color:{change_color}'>${current_price:.2f} ({daily_change:+.2f}%)</span></div>
        <div class='metric-card'><b>Signal:</b> <span class='signal-box' style='background-color:{signal_color};'>{signal_text}</span></div>
        <div class='metric-card'><b>RSI (14):</b> <span style='color:{"green" if current_rsi<30 else "red" if current_rsi>70 else "white"}'>{current_rsi:.1f}</span></div>
        <div class='metric-card'><b>MACD:</b> <span style='color:{"green" if current_macd>current_macd_signal else "red"}'>{current_macd:.3f}</span> | <b>Signal:</b> <span style='color:{"green" if current_macd>current_macd_signal else "red"}'>{current_macd_signal:.3f}</span></div>
        <div class='metric-card'><b>SMA 20:</b> {sma_20:.2f} | <b>EMA 20:</b> {ema_20:.2f}</div>
        <div class='metric-card'><b>Bollinger Bands:</b> {bb_lower:.2f} - {bb_upper:.2f}</div>
        <div class='metric-card'><b>Volatility (30d):</b> {volatility:.2f}%</div>
        """, unsafe_allow_html=True)

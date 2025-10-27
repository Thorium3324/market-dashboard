import streamlit as st
import pandas as pd
import yfinance as yf
import mplfinance as mpf
from ta.trend import MACD, ADXIndicator
from ta.momentum import RSIIndicator, StochasticOscillator, ROCIndicator
from ta.volatility import BollingerBands, AverageTrueRange
from ta.volume import OnBalanceVolumeIndicator
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

# ====== Lewy panel ======
st.sidebar.title("⚙️ Markets & Symbols")
market_option = st.sidebar.selectbox("Select Market", ["Stocks","Crypto","Metals","Bonds","ETFs"])
if market_option=="Stocks":
    selected_sector = st.sidebar.selectbox("Select Sector", list(STOCK_SECTORS.keys()))
    symbol_list = STOCK_SECTORS[selected_sector]
elif market_option=="Crypto":
    symbol_list = ["BTC-USD","ETH-USD","BNB-USD","SOL-USD","ADA-USD"]
elif market_option=="Metals":
    symbol_list = ["GC=F","SI=F","PL=F","HG=F"]
elif market_option=="Bonds":
    symbol_list = ["^TNX","^IRX"]
elif market_option=="ETFs":
    symbol_list = ["SPY","QQQ","IWM","DIA","GLD","SLV"]

custom_symbol = st.sidebar.text_input("Custom symbol (optional)").upper()
selected_symbol = custom_symbol if custom_symbol else st.sidebar.selectbox("Select Symbol", symbol_list)

period_option = st.sidebar.selectbox("Select Time Range", ["7d","30d","3mo","6mo","1y","2y","5y"], index=1)
chart_type_option = st.sidebar.radio("Chart Type", ["Candle", "Line", "Bar"])
theme = st.sidebar.radio("Theme", ["Light", "Dark"])
style = "yahoo" if theme=="Light" else "nightclouds"
chart_type_map = {"Candle":"candle", "Line":"line", "Bar":"ohlc"}

live_mode = st.sidebar.checkbox("Live Mode (refresh every 30s)")
refresh_interval = 30

# ====== Fetch data ======
@st.cache_data(ttl=60)
def get_data(symbol, period='30d'):
    try:
        stock = yf.Ticker(symbol)
        hist = stock.history(period=period)
        if hist.empty or len(hist)<2: return pd.DataFrame()
        hist = hist.fillna(method='ffill').fillna(method='bfill')
        # Trend indicators
        hist['SMA_20'] = hist['Close'].rolling(20).mean()
        hist['EMA_20'] = hist['Close'].ewm(span=20, adjust=False).mean()
        hist['ATR'] = AverageTrueRange(hist['High'], hist['Low'], hist['Close'], window=14).average_true_range()
        hist['ADX'] = ADXIndicator(hist['High'], hist['Low'], hist['Close'], window=14).adx()
        # Momentum
        hist['RSI'] = RSIIndicator(hist['Close']).rsi()
        hist['MACD'] = MACD(hist['Close']).macd()
        hist['MACD_Signal'] = MACD(hist['Close']).macd_signal()
        hist['Stoch'] = StochasticOscillator(hist['High'], hist['Low'], hist['Close']).stoch()
        hist['ROC'] = ROCIndicator(hist['Close']).roc()
        # Volatility
        bb = BollingerBands(hist['Close'])
        hist['BB_Upper'] = bb.bollinger_hband()
        hist['BB_Lower'] = bb.bollinger_lband()
        hist['BB_Width'] = hist['BB_Upper'] - hist['BB_Lower']
        # Volume
        hist['OBV'] = OnBalanceVolumeIndicator(hist['Close'], hist['Volume']).on_balance_volume()
        hist['Vol_MA20'] = hist['Volume'].rolling(20).mean()
        return hist
    except:
        return pd.DataFrame()

# ====== Main layout ======
st.title("📊 StockMatrix Pro 4.0")

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

        # Sygnał
        if hist_data['RSI'].iloc[-1]<30 and hist_data['MACD'].iloc[-1]>hist_data['MACD_Signal'].iloc[-1]:
            signal_text = "BUY"
            signal_color = "green"
        elif hist_data['RSI'].iloc[-1]>70 and hist_data['MACD'].iloc[-1]<hist_data['MACD_Signal'].iloc[-1]:
            signal_text = "SELL"
            signal_color = "red"
        else:
            signal_text = "HOLD"
            signal_color = "gray"
        change_color = "green" if daily_change>0 else "red" if daily_change<0 else "white"

        # Wyświetlanie wskaźników
        st.markdown(f"""
        <div class='metric-card'><b>Price:</b> <span style='color:{change_color}'>${current_price:.2f} ({daily_change:+.2f}%)</span></div>
        <div class='metric-card'><b>Signal:</b> <span class='signal-box' style='background-color:{signal_color};'>{signal_text}</span></div>
        <div class='metric-card'><b>RSI (14):</b> {hist_data['RSI'].iloc[-1]:.1f}</div>
        <div class='metric-card'><b>MACD:</b> {hist_data['MACD'].iloc[-1]:.3f} | Signal: {hist_data['MACD_Signal'].iloc[-1]:.3f}</div>
        <div class='metric-card'><b>SMA 20:</b> {hist_data['SMA_20'].iloc[-1]:.2f} | EMA 20: {hist_data['EMA_20'].iloc[-1]:.2f}</div>
        <div class='metric-card'><b>Bollinger Bands:</b> {hist_data['BB_Lower'].iloc[-1]:.2f} - {hist_data['BB_Upper'].iloc[-1]:.2f} | Width: {hist_data['BB_Width'].iloc[-1]:.2f}</div>
        <div class='metric-card'><b>ATR:</b> {hist_data['ATR'].iloc[-1]:.2f} | ADX: {hist_data['ADX'].iloc[-1]:.2f}</div>
        <div class='metric-card'><b>Stochastic:</b> {hist_data['Stoch'].iloc[-1]:.2f} | ROC: {hist_data['ROC'].iloc[-1]:.2f}</div>
        <div class='metric-card'><b>OBV:</b> {hist_data['OBV'].iloc[-1]:.0f} | Vol MA20: {hist_data['Vol_MA20'].iloc[-1]:.0f}</div>
        <div class='metric-card'><b>52-Week High/Low:</b> {hist_data['Close'].max():.2f} / {hist_data['Close'].min():.2f}</div>
        """, unsafe_allow_html=True)

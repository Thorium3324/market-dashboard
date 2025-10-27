import streamlit as st
import pandas as pd
import yfinance as yf
import mplfinance as mpf
from ta.trend import MACD
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands
import time

from stock_market_agent_new import STOCK_SECTORS

# ====== Page Config ======
st.set_page_config(page_title="StockMatrix Pro 4.0", layout="wide")

# ====== Custom CSS ======
st.markdown("""
<style>
body { background-color: #0e1117; color: #e8e6e3; font-family: 'Segoe UI', sans-serif; }
.metric-card { padding: 20px; border-radius: 12px; background-color: #1c1f26; margin-bottom: 15px; box-shadow: 2px 2px 15px rgba(0,0,0,0.3);}
.signal-box { border-radius: 8px; padding: 8px; font-weight: bold; text-align: center; margin-top:5px; }
.live-indicator { position: fixed; top: 20px; right: 25px; background-color: #ff0000; color: white; font-weight: bold; border-radius: 50px; padding: 6px 12px; animation: pulse 1s infinite; z-index: 9999; }
.ticker-bar { background-color: #1c1f26; padding: 5px 10px; color: #ffffff; font-weight: bold; border-radius: 5px; margin-bottom: 10px; }
h2, h3 { color: #ffffff; }
@keyframes pulse { 0% {opacity:1;} 50%{opacity:0.5;} 100%{opacity:1;} }
</style>
""", unsafe_allow_html=True)

# ====== Sidebar Settings ======
st.sidebar.title("⚙️ Settings")
selected_tab = st.sidebar.radio("Select Market", ["Stocks", "Crypto", "Metals", "Indices"])
selected_sector = st.sidebar.selectbox("Select Sector", list(STOCK_SECTORS.keys()))
custom_symbol = st.sidebar.text_input("Custom symbol (e.g. TSLA)").upper()
period_option = st.sidebar.select_slider("Time Range", options=["7d","30d","3mo","6mo","1y","2y","5y"], value="30d")
chart_type = st.sidebar.radio("Chart Type", ["Candle", "Line", "Bar"])
theme = st.sidebar.radio("Theme", ["Light", "Dark"])
style = "yahoo" if theme=="Light" else "nightclouds"

# ====== Auto Refresh ======
auto_refresh = st.sidebar.toggle("Enable Auto-Refresh", True)
refresh_value = st.sidebar.slider("Refresh Interval (sec)", 5, 300, 30)
live_mode = st.sidebar.toggle("Live Mode", False)

# ====== Fetch Stock Data ======
@st.cache_data(ttl=60)
def get_stock_data(symbol, period='30d'):
    try:
        stock = yf.Ticker(symbol)
        hist = stock.history(period=period)
        if hist.empty or len(hist) < 2:
            return pd.DataFrame()
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

# ====== Main Page Layout ======
st.title("📊 StockMatrix Pro 4.0")
if live_mode:
    st.markdown("<div class='live-indicator'>LIVE 🔴</div>", unsafe_allow_html=True)

# Display stocks only for selected sector
sector_stocks = STOCK_SECTORS[selected_sector]
selected_stock = custom_symbol if custom_symbol else st.selectbox("Select Stock", sector_stocks)
hist_data = get_stock_data(selected_stock, period_option)

if hist_data.empty:
    st.warning(f"No data for {selected_stock}")
else:
    # ====== Prepare mplfinance plots safely ======
    df_mpf = hist_data[['Open','High','Low','Close','Volume']].copy()
    addplots=[]
    for col, color, panel, ylabel in [('SMA_20','orange',0,''), ('EMA_20','cyan',0,''), ('RSI','purple',1,'RSI'), ('MACD','blue',2,'MACD'), ('MACD_Signal','orange',2,'')]:
        if col in hist_data.columns and hist_data[col].notna().any():
            addplots.append(mpf.make_addplot(hist_data[col], panel=panel, color=color, ylabel=ylabel))
    try:
        fig, axlist = mpf.plot(df_mpf, type=chart_type.lower(), style=style, addplot=addplots if addplots else None,
                               volume=True, returnfig=True, figsize=(12,8))
        st.pyplot(fig)
    except Exception as e:
        st.error(f"Error rendering chart: {e}")

    # ====== Metrics Card ======
    current_price = hist_data['Close'].iloc[-1]
    prev_price = hist_data['Close'].iloc[-2]
    daily_change = ((current_price/prev_price)-1)*100
    current_rsi = hist_data['RSI'].iloc[-1]
    current_macd = hist_data['MACD'].iloc[-1]
    current_macd_signal = hist_data['MACD_Signal'].iloc[-1]
    volatility = hist_data['Close'].pct_change().std()*100

    signal = "Neutral"
    if current_rsi<30 and current_macd>current_macd_signal: signal="Buy"
    elif current_rsi>70 and current_macd<current_macd_signal: signal="Sell"
    signal_color={'Buy':'green','Sell':'red','Neutral':'gray'}

    st.markdown(f"""
    <div class='metric-card'>
        <h3>{selected_stock}</h3>
        <p>Price: ${current_price:.2f} | 24h Change: {daily_change:+.2f}%</p>
        <p>RSI: {current_rsi:.1f} | MACD: {current_macd:.3f} | Signal Line: {current_macd_signal:.3f}</p>
        <p>Volatility (30d): {volatility:.2f}%</p>
        <div class='signal-box' style='border:2px solid {signal_color[signal]}; color:{signal_color[signal]}'>Signal: {signal}</div>
    </div>
    """, unsafe_allow_html=True)

    csv = hist_data.to_csv().encode('utf-8')
    st.download_button("💾 Download CSV", data=csv, file_name=f"{selected_stock}_data.csv")

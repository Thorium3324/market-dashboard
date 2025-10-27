import streamlit as st
import pandas as pd
import yfinance as yf
import mplfinance as mpf
from ta.trend import MACD
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands
import numpy as np
import matplotlib.pyplot as plt

from stock_market_agent_new import STOCK_SECTORS

st.set_page_config(page_title="StockMatrix Pro 4.0", layout="wide")

# ====== Styl ======
st.markdown("""
<style>
body { background-color: #0e1117; color: #e8e6e3; font-family: 'Verdana', sans-serif; }
.metric-card { padding: 12px; border-radius: 10px; margin-bottom: 12px; background-color: #1c1f26; box-shadow: 2px 2px 12px rgba(0,0,0,0.3); font-size: 14px; }
.signal-box { padding: 10px; border-radius: 8px; font-weight: bold; text-align: center; margin-top:5px; font-size: 16px; }
h2, h3, h4 { color: #ffffff; font-weight: normal; }
</style>
""", unsafe_allow_html=True)

# ====== Sidebar ======
st.sidebar.title("⚙️ Settings")
selected_sector = st.sidebar.selectbox("Select Sector", list(STOCK_SECTORS.keys()))
custom_symbol = st.sidebar.text_input("Custom symbol (e.g. TSLA)").upper()
period_option = st.sidebar.select_slider("Time Range", options=["7d","30d","3mo","6mo","1y","2y","5y"], value="30d")
chart_type_option = st.sidebar.radio("Chart Type", ["Candle", "Line", "Bar"])
theme = st.sidebar.radio("Theme", ["Light", "Dark"])
style = "yahoo" if theme=="Light" else "nightclouds"

# Map user-friendly chart types to mplfinance types
chart_type_map = {"Candle": "candle", "Line": "line", "Bar": "ohlc"}

# ====== Fetch stock data ======
@st.cache_data(ttl=60)
def get_stock_data(symbol, period='30d'):
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

# ====== Main Layout ======
st.title("📊 StockMatrix Pro 4.0")

sector_stocks = STOCK_SECTORS[selected_sector]
selected_stock = custom_symbol if custom_symbol else st.selectbox("Select Stock", sector_stocks)
hist_data = get_stock_data(selected_stock, period_option)

if hist_data.empty:
    st.warning(f"No data for {selected_stock}")
else:
    col1, col2 = st.columns([2,1])

    # ----- Wykres główny -----
    with col1:
        df_mpf = hist_data[['Open','High','Low','Close','Volume']]
        addplots=[]
        for col,color,panel,ylabel in [('SMA_20','orange',0,''), ('EMA_20','cyan',0,''), ('RSI','purple',1,'RSI'), ('MACD','blue',2,'MACD'), ('MACD_Signal','orange',2,'')]:
            if col in hist_data.columns and hist_data[col].notna().any():
                addplots.append(mpf.make_addplot(hist_data[col], panel=panel, color=color, ylabel=ylabel))
        try:
            fig, axlist = mpf.plot(df_mpf, type=chart_type_map[chart_type_option], style=style, addplot=addplots if addplots else None,
                                   volume=True, returnfig=True, figsize=(8,5))
            st.pyplot(fig)
        except Exception as e:
            st.error(f"Error rendering chart: {e}")

        # Mini wykresy RSI i MACD
        fig_rsi, ax_rsi = plt.subplots(figsize=(8,1.5))
        ax_rsi.plot(hist_data.index, hist_data['RSI'], color='purple')
        ax_rsi.axhline(70, color='red', linestyle='--', alpha=0.5)
        ax_rsi.axhline(30, color='green', linestyle='--', alpha=0.5)
        ax_rsi.set_facecolor('#0e1117')
        ax_rsi.tick_params(colors='white', labelsize=8)
        ax_rsi.set_title("RSI (14)", color='white', fontsize=10)
        st.pyplot(fig_rsi)

        fig_macd, ax_macd = plt.subplots(figsize=(8,1.5))
        ax_macd.plot(hist_data.index, hist_data['MACD'], color='blue', label='MACD')
        ax_macd.plot(hist_data.index, hist_data['MACD_Signal'], color='orange', label='Signal')
        ax_macd.set_facecolor('#0e1117')
        ax_macd.tick_params(colors='white', labelsize=8)
        ax_macd.set_title("MACD", color='white', fontsize=10)
        ax_macd.legend(frameon=False, fontsize=8)
        st.pyplot(fig_macd)

    # ----- Prawy panel -----
    with col2:
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

        # Sygnał rynkowy
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
        <div class='metric-card'>
            Price: <span style='color:{change_color}'>${current_price:.2f} ({daily_change:+.2f}%)</span><br>
            Signal: <span class='signal-box' style='background-color:{signal_color};'>{signal_text}</span><br>
            RSI (14): {current_rsi:.1f}<br>
            MACD: {current_macd:.3f} | Signal: {current_macd_signal:.3f}<br>
            SMA 20: {sma_20:.2f} | EMA 20: {ema_20:.2f}<br>
            Bollinger Bands: {bb_lower:.2f} - {bb_upper:.2f}<br>
            Volatility (30d): {volatility:.2f}%
        </div>
        """, unsafe_allow_html=True)

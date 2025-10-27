import streamlit as st
import pandas as pd
import yfinance as yf
import mplfinance as mpf
import matplotlib.pyplot as plt
from ta.trend import MACD, ADXIndicator
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.volatility import BollingerBands, AverageTrueRange
from ta.volume import OnBalanceVolumeIndicator
import numpy as np
from stock_market_agent_new import STOCK_SECTORS

# ====== Konfiguracja strony ======
st.set_page_config(page_title="StockMatrix Pro 4.0", layout="wide")

# ====== Styl ======
st.markdown("""
<style>
body { background-color: #0e1117; color: #e8e6e3; font-family: 'Verdana', sans-serif; }
.metric-card { padding: 12px; border-radius: 10px; margin-bottom: 12px; background-color: #1c1f26; box-shadow: 2px 2px 12px rgba(0,0,0,0.3); font-size: 14px; }
.signal-box { padding: 10px; border-radius: 8px; text-align: center; margin-top:5px; font-size: 16px; color:white; font-weight:bold; }
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
chart_type_map = {"Candle":"candle", "Line":"line", "Bar":"ohlc"}

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
        atr = AverageTrueRange(hist['High'], hist['Low'], hist['Close'])
        hist['ATR'] = atr.average_true_range()
        adx = ADXIndicator(hist['High'], hist['Low'], hist['Close'])
        hist['ADX'] = adx.adx()
        obv = OnBalanceVolumeIndicator(hist['Close'], hist['Volume'])
        hist['OBV'] = obv.on_balance_volume()
        stoch = StochasticOscillator(hist['High'], hist['Low'], hist['Close'])
        hist['Stoch'] = stoch.stoch()
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
            fig, axlist = mpf.plot(df_mpf, type=chart_type_map[chart_type_option], style=style,
                                   addplot=addplots if addplots else None, volume=True, returnfig=True, figsize=(8,5))
            st.pyplot(fig)
        except Exception as e:
            st.error(f"Error rendering chart: {e}")

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
        atr = hist_data['ATR'].iloc[-1]
        adx = hist_data['ADX'].iloc[-1]
        obv = hist_data['OBV'].iloc[-1]
        stoch = hist_data['Stoch'].iloc[-1]

        # Signal logic
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
        <div style='display:flex; flex-direction:column; gap:10px;'>

            <div class='metric-card'><b>Price:</b> <span style='color:{change_color}'>${current_price:.2f} ({daily_change:+.2f}%)</span></div>
            <div class='metric-card'><b>Signal:</b> <span class='signal-box' style='background-color:{signal_color};'>{signal_text}</span></div>
            <div class='metric-card'><b>RSI (14):</b> <span style='color:{"green" if current_rsi<30 else "red" if current_rsi>70 else "white"}'>{current_rsi:.1f}</span></div>
            <div class='metric-card'><b>MACD:</b> <span style='color:{"green" if current_macd>current_macd_signal else "red"}'>{current_macd:.3f}</span> | <b>Signal:</b> <span style='color:{"green" if current_macd>current_macd_signal else "red"}'>{current_macd_signal:.3f}</span></div>
            <div class='metric-card'><b>SMA 20:</b> {sma_20:.2f} | <b>EMA 20:</b> {ema_20:.2f}</div>
            <div class='metric-card'><b>Bollinger Bands:</b> {bb_lower:.2f} - {bb_upper:.2f}</div>
            <div class='metric-card'><b>Volatility (30d):</b> {volatility:.2f}%</div>
            <div class='metric-card'><b>ATR (14):</b> {atr:.2f}</div>
            <div class='metric-card'><b>ADX (14):</b> {adx:.2f}</div>
            <div class='metric-card'><b>OBV:</b> {obv:.2f}</div>
            <div class='metric-card'><b>Stochastic %K:</b> {stoch:.2f}</div>

        </div>
        """, unsafe_allow_html=True)

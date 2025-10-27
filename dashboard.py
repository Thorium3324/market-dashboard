import streamlit as st
import yfinance as yf
import pandas as pd
import mplfinance as mpf
from ta.momentum import RSIIndicator
from ta.trend import MACD, ADXIndicator
from ta.volatility import BollingerBands, AverageTrueRange
from ta.volume import OnBalanceVolumeIndicator
from datetime import datetime

# ====== Konfiguracja strony ======
st.set_page_config(page_title="StockMatrix", layout="wide")
st.markdown("<h1 style='text-align: center;'>StockMatrix Pro Dashboard</h1>", unsafe_allow_html=True)

# ====== Funkcje ======
def get_stock_data(symbol, period='1mo'):
    df = yf.download(symbol, period=period)
    if df.empty or df.shape[0]<20:
        return pd.DataFrame()
    df = df.reset_index()
    df = df[['Date','Open','High','Low','Close','Volume']]
    df['Close'] = pd.to_numeric(df['Close'], errors='coerce')
    df = df.dropna(subset=['Close'])
    df = df.set_index('Date')
    
    try:
        df['RSI'] = RSIIndicator(df['Close'], window=14).rsi()
        macd = MACD(df['Close'], window_slow=26, window_fast=12, window_sign=9)
        df['MACD'] = macd.macd()
        df['MACD_Signal'] = macd.macd_signal()
        df['SMA_20'] = df['Close'].rolling(20).mean()
        df['EMA_20'] = df['Close'].ewm(span=20, adjust=False).mean()
        bb = BollingerBands(df['Close'], window=20, window_dev=2)
        df['BB_Upper'] = bb.bollinger_hband()
        df['BB_Lower'] = bb.bollinger_lband()
        df['ATR'] = AverageTrueRange(df['High'], df['Low'], df['Close'], window=14).average_true_range()
        df['OBV'] = OnBalanceVolumeIndicator(df['Close'], df['Volume']).on_balance_volume()
        df['ADX'] = ADXIndicator(df['High'], df['Low'], df['Close'], window=14).adx()
    except:
        pass
    return df

def get_signal(rsi, macd, macd_signal):
    if pd.isna(rsi) or pd.isna(macd) or pd.isna(macd_signal):
        return "HOLD"
    if rsi < 30 and macd > macd_signal:
        return "BUY"
    elif rsi > 70 and macd < macd_signal:
        return "SELL"
    return "HOLD"

def signal_color(signal):
    return {"BUY":"green","SELL":"red","HOLD":"gray"}.get(signal,"gray")

def get_company_logo(symbol):
    return f"https://logo.clearbit.com/{symbol.lower()}.com"

# ====== Lista sektorów i przykładowe spółki ======
STOCK_SECTORS = {
    "Technology": ["AAPL","MSFT","NVDA","AMD","INTC"],
    "Biotech": ["MRNA","BIIB","VRTX","REGN"],
    "Finance": ["JPM","BAC","C","GS"],
    "Energy": ["XOM","CVX","BP","TOT"],
    "Consumer": ["AMZN","WMT","DIS","NKE"]
}

# ====== Kolumny ======
col1, col2, col3 = st.columns([1.5,3,1.5])

# ====== Kolumna 1: ustawienia ======
with col1:
    st.subheader("Ustawienia")
    
    data_type = st.radio("Typ danych:", ["Akcje", "Obligacje", "Kruszcze", "ETF", "Kryptowaluty"])
    
    sector = st.selectbox("Wybierz sektor:", list(STOCK_SECTORS.keys()))
    symbol_list = STOCK_SECTORS[sector]
    symbol = st.selectbox("Wybierz spółkę:", symbol_list)
    
    search_tag = st.text_input("Szukaj po tagu lub symbolu:")
    if search_tag:
        filtered = [s for s in symbol_list if search_tag.upper() in s.upper()]
        if filtered:
            symbol = st.selectbox("Wybierz spółkę:", filtered)
    
    chart_type = st.selectbox("Typ wykresu:", ["Candle","Line","OHLC"])
    chart_map = {"Candle":"candle","Line":"line","OHLC":"ohlc"}
    
    period = st.selectbox("Okres:", ["7d","30d","3mo","6mo","1y","2y","5y"])
    
    refresh_unit = st.selectbox("Auto-refresh co:", ["Minuty","Godziny","Dni"])
    refresh_value = st.slider("Co ile odświeżać:",1,60,5)
    auto_refresh = st.checkbox("Włącz auto-refresh", value=True)

# ====== Kolumna 2: wykres ======
with col2:
    st.subheader(f"{sector} - {symbol}")
    st.image(get_company_logo(symbol), width=80)
    
    data = get_stock_data(symbol, period)
    if data.empty:
        st.warning("Brak wystarczających danych.")
    else:
        df_plot = data[['Open','High','Low','Close','Volume']].copy()
        addplots=[]
        for col_name,color,panel,ylabel in [
            ('SMA_20','orange',0,''), 
            ('EMA_20','cyan',0,''),
            ('RSI','purple',1,'RSI'),
            ('MACD','blue',2,'MACD'),
            ('MACD_Signal','orange',2,'')
        ]:
            if col_name in data.columns and data[col_name].notna().any():
                addplots.append(mpf.make_addplot(data[col_name], panel=panel, color=color, ylabel=ylabel))
        
        fig, axlist = mpf.plot(
            df_plot,
            type=chart_map[chart_type],
            style='charles',
            volume=True,
            returnfig=True,
            addplot=addplots,
            figsize=(6,6)
        )
        st.pyplot(fig)

# ====== Kolumna 3: analiza techniczna ======
with col3:
    st.subheader("Analiza techniczna")
    if not data.empty:
        current_price = data['Close'].iloc[-1]
        prev_price = data['Close'].iloc[-2]
        daily_change = ((current_price-prev_price)/prev_price)*100
        rsi = data['RSI'].iloc[-1]
        macd_val = data['MACD'].iloc[-1]
        macd_signal_val = data['MACD_Signal'].iloc[-1]
        signal = get_signal(rsi, macd_val, macd_signal_val)
        
        st.markdown(f"**Cena:** ${current_price:.2f}")
        st.markdown(f"**Zmiana dzienna:** {daily_change:+.2f}%")
        st.markdown(f"**RSI (14):** {rsi:.2f}")
        st.markdown(f"**MACD:** {macd_val:.2f} | **MACD Signal:** {macd_signal_val:.2f}")
        st.markdown(f"**SMA (20):** {data['SMA_20'].iloc[-1]:.2f}")
        st.markdown(f"**EMA (20):** {data['EMA_20'].iloc[-1]:.2f}")
        st.markdown(f"**Bollinger Upper:** {data['BB_Upper'].iloc[-1]:.2f}")
        st.markdown(f"**Bollinger Lower:** {data['BB_Lower'].iloc[-1]:.2f}")
        st.markdown(f"**ATR:** {data['ATR'].iloc[-1]:.2f}")
        st.markdown(f"**OBV:** {data['OBV'].iloc[-1]:.2f}")
        st.markdown(f"**ADX:** {data['ADX'].iloc[-1]:.2f}")
        st.markdown(f"<span style='color:{signal_color(signal)}; font-weight:bold;'>Sygnał: {signal}</span>", unsafe_allow_html=True)
        
        # Sector Overview
        st.subheader("Sector Overview")
        sector_data = []
        for s in STOCK_SECTORS[sector]:
            sec_data = get_stock_data(s, period)
            if not sec_data.empty:
                sector_data.append({
                    "Symbol": s,
                    "Price": sec_data['Close'].iloc[-1],
                    "Change%": ((sec_data['Close

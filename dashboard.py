import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import mplfinance as mpf
from ta.momentum import RSIIndicator
from ta.trend import MACD
from ta.volatility import BollingerBands, AverageTrueRange
from ta.volume import OnBalanceVolumeIndicator
import time

# ====== Konfiguracja strony ======
st.set_page_config(page_title="StockMatrix", layout="wide")
st.markdown("<h1 style='text-align: center;'>StockMatrix Pro Dashboard</h1>", unsafe_allow_html=True)

# ====== Lista sektorów i spółek ======
STOCK_SECTORS = {
    "Technology": ["AAPL","MSFT","NVDA","AMD","INTC"],
    "Biotech": ["MRNA","BIIB","VRTX","REGN"],
    "Finance": ["JPM","BAC","C","GS"],
    "Energy": ["XOM","CVX","BP","TOT"],
    "Consumer": ["AMZN","WMT","DIS","NKE"]
}

# ====== Funkcje ======
def get_stock_data(symbol, period='1mo'):
    try:
        df = yf.download(symbol, period=period)
        if df.empty or len(df)<2:
            # Fallback: spróbuj większego okresu
            df = yf.download(symbol, period='3mo')
        if df.empty or len(df)<2:
            return pd.DataFrame()
        df = df[['Open','High','Low','Close','Volume']]
        df = df.dropna()
        # Technical indicators
        df['RSI'] = RSIIndicator(df['Close'], window=14).rsi()
        macd = MACD(df['Close'])
        df['MACD'] = macd.macd()
        df['MACD_Signal'] = macd.macd_signal()
        df['SMA_20'] = df['Close'].rolling(20).mean()
        df['EMA_20'] = df['Close'].ewm(span=20, adjust=False).mean()
        bb = BollingerBands(df['Close'])
        df['BB_Upper'] = bb.bollinger_hband()
        df['BB_Lower'] = bb.bollinger_lband()
        df['ATR'] = AverageTrueRange(df['High'], df['Low'], df['Close']).average_true_range()
        df['OBV'] = OnBalanceVolumeIndicator(df['Close'], df['Volume']).on_balance_volume()
        return df
    except Exception as e:
        print(f"Błąd pobierania danych dla {symbol}: {e}")
        return pd.DataFrame()

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

def get_company_info(symbol):
    try:
        stock = yf.Ticker(symbol)
        info = stock.info
        name = info.get('longName', symbol)
        logo = info.get('logo_url', f"https://logo.clearbit.com/{symbol.lower()}.com")
        return name, logo
    except:
        return symbol, f"https://logo.clearbit.com/{symbol.lower()}.com"

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
    refresh_unit = st.selectbox("Auto-refresh co:", ["Sekundy","Minuty"])
    refresh_value = st.slider("Co ile odświeżać:",1,60,5)
    auto_refresh = st.checkbox("Włącz auto-refresh", value=True)

# ====== Dynamiczny refresh ======
if auto_refresh:
    if "last_refresh" not in st.session_state:
        st.session_state.last_refresh = time.time()
    interval = refresh_value if refresh_unit=="Sekundy" else refresh_value*60
    if time.time()-st.session_state.last_refresh>interval:
        st.session_state.last_refresh = time.time()
        st.experimental_rerun()

# ====== Kolumna 2: wykres ======
with col2:
    company_name, company_logo = get_company_info(symbol)
    st.subheader(f"{sector} - {symbol} ({company_name})")
    st.image(company_logo, width=80)
    
    data = get_stock_data(symbol, period)
    if data.empty:
        st.warning("Brak danych do wyświetlenia wykresu.")
        # fallback: wykres liniowy pusty
        st.line_chart([0])
    else:
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
        try:
            fig, axlist = mpf.plot(
                data[['Open','High','Low','Close','Volume']],
                type=chart_map.get(chart_type,"candle"),
                style='charles',
                volume=True,
                returnfig=True,
                addplot=addplots,
                figsize=(6,6)
            )
            st.pyplot(fig)
        except Exception as e:
            st.warning(f"Nie udało się wygenerować wykresu: {e}")
            st.line_chart(data['Close'])

# ====== Kolumna 3: analiza ======
with col3:
    st.subheader("Analiza techniczna")
    if not data.empty:
        current_price = data['Close'].iloc[-1]
        prev_price = data['Close'].iloc[-2]
        daily_change = ((current_price-prev_price)/prev_price)*100
        rsi = data['RSI'].iloc[-1] if 'RSI' in data.columns else np.nan
        macd_val = data['MACD'].iloc[-1] if 'MACD' in data.columns else np.nan
        macd_signal_val = data['MACD_Signal'].iloc[-1] if 'MACD_Signal' in data.columns else np.nan
        atr = data['ATR'].iloc[-1] if 'ATR' in data.columns else np.nan
        obv = data['OBV'].iloc[-1] if 'OBV' in data.columns else np.nan
        bb_upper = data['BB_Upper'].iloc[-1] if 'BB_Upper' in data.columns else np.nan
        bb_lower = data['BB_Lower'].iloc[-1] if 'BB_Lower' in data.columns else np.nan
        signal = get_signal(rsi, macd_val, macd_signal_val)
        st.markdown(f"**Cena:** ${current_price:.2f}")
        st.markdown(f"**Zmiana dzienna:** <span style='color:{'green' if daily_change>0 else 'red'}'>{daily_change:+.2f}%</span>", unsafe_allow_html=True)
        st.markdown(f"**RSI (14):** {rsi:.2f}")
        st.markdown(f"**MACD:** {macd_val:.2f} | **MACD Signal:** {macd_signal_val:.2f}")
        st.markdown(f"**ATR:** {atr:.2f} | **OBV:** {obv:.0f}")
        st.markdown(f"**BB Upper / Lower:** {bb_upper:.2f} / {bb_lower:.2f}")
        st.markdown(f"<span style='color:{signal_color(signal)}; font-weight:bold;'>Sygnał: {signal}</span>", unsafe_allow_html=True)

# ====== Stopka ======
st.markdown("<hr><p style='text-align:center;font-size:12px;'>Dane pobrano z Yahoo Finance</p>", unsafe_allow_html=True)

import streamlit as st
import yfinance as yf
import pandas as pd
import mplfinance as mpf
from ta.momentum import RSIIndicator
from ta.trend import MACD, ADXIndicator
from ta.volatility import BollingerBands, AverageTrueRange
from ta.volume import OnBalanceVolumeIndicator

# ====== Ustawienia strony ======
st.set_page_config(page_title="Professional Stock Dashboard", layout="wide")

# ====== Funkcje ======
def get_stock_data(symbol, period='1mo'):
    df = yf.download(symbol, period=period)
    if df.empty or df.shape[0]<20:  # minimalna ilość danych dla większości wskaźników
        return pd.DataFrame()
    
    # Reset indeksu, upewnij się, że Close jest float
    df = df.reset_index()
    df = df[['Date','Open','High','Low','Close','Volume']]
    df['Close'] = pd.to_numeric(df['Close'], errors='coerce')
    df = df.dropna(subset=['Close'])
    df = df.set_index('Date')
    
    # Obliczenie wskaźników technicznych z zabezpieczeniem
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
    except Exception as e:
        st.warning(f"Nie udało się obliczyć wskaźników technicznych: {e}")
    return df

def get_signal(rsi, macd, macd_signal):
    if pd.isna(rsi) or pd.isna(macd) or pd.isna(macd_signal):
        return "HOLD"
    if rsi < 30 and macd > macd_signal:
        return "BUY"
    elif rsi > 70 and macd < macd_signal:
        return "SELL"
    else:
        return "HOLD"

def signal_color(signal):
    return {"BUY": "green", "SELL": "red", "HOLD": "gray"}.get(signal, "gray")

def get_company_logo(symbol):
    return f'https://logo.clearbit.com/{symbol.lower()}.com'

# ====== Sidebar ======
with st.sidebar:
    st.header("Ustawienia")
    data_type = st.selectbox("Typ danych:", ["Akcje", "Kryptowaluty", "Metale", "ETF", "Obligacje"])
    symbol = st.text_input("Symbol (np. TSLA, AAPL):", "TSLA")
    period = st.selectbox("Okres danych:", ["7d","30d","3mo","6mo","1y","2y","5y"])
    chart_type = st.selectbox("Typ wykresu:", ["Candle", "Line", "OHLC"])
    chart_map = {"Candle":"candle", "Line":"line", "OHLC":"ohlc"}

# ====== Pobranie danych ======
data = get_stock_data(symbol, period)

if data.empty:
    st.warning("Nie udało się pobrać wystarczającej liczby danych dla wybranego okresu.")
else:
    # ====== Layout ======
    col1, col2 = st.columns([2,1])

    # Lewa kolumna: wykres
    with col1:
        st.subheader(f"{symbol} - Wykres")
        df_plot = data[['Open','High','Low','Close','Volume']].copy()
        addplots=[]
        for col,color,panel,ylabel in [
            ('SMA_20','orange',0,''), 
            ('EMA_20','cyan',0,''),
            ('RSI','purple',1,'RSI'),
            ('MACD','blue',2,'MACD'),
            ('MACD_Signal','orange',2,'')
        ]:
            if col in data.columns and data[col].notna().any():
                addplots.append(mpf.make_addplot(data[col], panel=panel, color=color, ylabel=ylabel))
        fig, axlist = mpf.plot(
            df_plot,
            type=chart_map[chart_type],
            style='charles',
            volume=True,
            returnfig=True,
            addplot=addplots,
            figsize=(10,5)
        )
        st.pyplot(fig)

    # Prawa kolumna: analiza techniczna
    with col2:
        st.subheader("Analiza techniczna")
        logo_url = get_company_logo(symbol)
        st.image(logo_url, width=120)
        current_price = data['Close'].iloc[-1]
        prev_price = data['Close'].iloc[-2]
        daily_change = ((current_price - prev_price)/prev_price)*100
        st.markdown(f"**Cena:** ${current_price:.2f}")
        st.markdown(f"**Zmiana dzienna:** {daily_change:+.2f}%")
        rsi = data['RSI'].iloc[-1]
        macd_val = data['MACD'].iloc[-1]
        macd_signal_val = data['MACD_Signal'].iloc[-1]
        signal = get_signal(rsi, macd_val, macd_signal_val)
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

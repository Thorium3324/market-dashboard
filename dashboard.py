import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import mplfinance as mpf
import yfinance as yf
from datetime import datetime, timedelta
from ta.trend import MACD
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands

# Import stock sectors from your existing agent
from stock_market_agent_new import STOCK_SECTORS

# Configuration
st.set_page_config(
    page_title="StockMatrix742",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Mobile viewport configuration
st.markdown("""
    <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
""", unsafe_allow_html=True)

# Sidebar for sector selection
st.sidebar.title("📊 Filter Options")
selected_sector = st.sidebar.selectbox(
    "Select Sector",
    list(STOCK_SECTORS.keys())
)


# Get stock data function
@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_stock_data(symbol, period='30d'):
    try:
        # Try to get company info first to check if stock exists
        stock = yf.Ticker(symbol)
        info = stock.info
        if 'regularMarketPrice' not in info or info['regularMarketPrice'] is None:
            st.warning(f"{symbol} appears to be delisted or invalid")
            return pd.DataFrame()

        # Fetch historical data
        hist = stock.history(period=period)
        if len(hist) == 0:
            st.warning(f"No historical data available for {symbol}")
            return pd.DataFrame()

        # Verify required columns
        required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        if not all(col in hist.columns for col in required_columns):
            missing = [col for col in required_columns if col not in hist.columns]
            st.warning(f"Missing required data for {symbol}: {', '.join(missing)}")
            return pd.DataFrame()

        # Check for null values in required columns
        if hist[required_columns].isnull().any().any():
            st.warning(f"Found missing values in {symbol} data")
            # Forward fill and backward fill to handle missing values
            hist = hist.fillna(method='ffill').fillna(method='bfill')

        # Calculate indicators only if we have valid price data
        if len(hist) > 0 and not hist['Close'].isnull().all():
            # Calculate indicators
            rsi = RSIIndicator(close=hist['Close'], window=14)
            macd = MACD(close=hist['Close'])
            bb = BollingerBands(close=hist['Close'])
            
            hist['RSI'] = rsi.rsi()
            hist['MACD'] = macd.macd()
            hist['MACD_Signal'] = macd.macd_signal()
            hist['BB_Upper'] = bb.bollinger_hband()
            hist['BB_Lower'] = bb.bollinger_lband()
            
            return hist
            
        st.warning(f"Insufficient price data for {symbol}")
        return pd.DataFrame()

    except Exception as e:
        if "Symbol may be delisted" in str(e):
            st.warning(f"{symbol} appears to be delisted")
        else:
            st.error(f"Error fetching data for {symbol}: {str(e)}")
        return pd.DataFrame()

# Trading signal function
def get_signal(rsi, macd, macd_signal):
    signal = "Neutral"
    if rsi < 30 and macd > macd_signal:
        signal = "Buy"
    elif rsi > 70 and macd < macd_signal:
        signal = "Sell"
    return signal

# Signal strength function (0-10)
def get_signal_strength(rsi, macd, macd_signal, volatility):
    strength = 5  # Base strength
    
    # RSI contribution
    if rsi < 20 or rsi > 80:
        strength += 2
    elif rsi < 30 or rsi > 70:
        strength += 1
        
    # MACD contribution
    macd_diff = abs(macd - macd_signal)
    if macd_diff > 0.5:
        strength += 2
    elif macd_diff > 0.2:
        strength += 1
        
    # Volatility contribution
    if volatility > 3:
        strength += 1
        
    return min(10, strength)

# Main dashboard
st.title("📈 Market Intelligence Dashboard")
st.markdown(f"### {selected_sector} Analysis")

# Get stocks for selected sector
sector_stocks = STOCK_SECTORS[selected_sector]

# Create columns for layout
col1, col2, col3 = st.columns([2, 1, 1])

with col1:
    # Stock selector
    selected_stock = st.selectbox("Select Stock for Detailed Analysis", sector_stocks)
    
    if selected_stock:
        try:
            # Fetch detailed data for selected stock
            hist_data = get_stock_data(selected_stock)
            
            if hist_data is not None and not hist_data.empty and all(col in hist_data.columns for col in ['Open', 'High', 'Low', 'Close', 'Volume']):
                # Prepare data for mplfinance
                df_mpf = hist_data[['Open', 'High', 'Low', 'Close', 'Volume']].copy()
                
                # Verify we have valid data
                if df_mpf.isnull().any().any():
                    st.warning(f"Missing data points for {selected_stock}")
                elif len(df_mpf) < 2:  # Need at least 2 points to plot
                    st.warning(f"Insufficient data points for {selected_stock}")
                else:
                    # Additional studies for mplfinance
                    additional_studies = []
                    
                    # Only add indicators if they have valid data
                    if not hist_data['BB_Upper'].isnull().all():
                        additional_studies.extend([
                            mpf.make_addplot(hist_data['BB_Upper'], color='gray', linestyle='--', alpha=0.5),
                            mpf.make_addplot(hist_data['BB_Lower'], color='gray', linestyle='--', alpha=0.5)
                        ])
                    
                    if not hist_data['RSI'].isnull().all():
                        additional_studies.append(
                            mpf.make_addplot(hist_data['RSI'], panel=1, color='purple', ylabel='RSI')
                        )
                    
                    if not hist_data['MACD'].isnull().all() and not hist_data['MACD_Signal'].isnull().all():
                        additional_studies.extend([
                            mpf.make_addplot(hist_data['MACD'], panel=2, color='blue', ylabel='MACD'),
                            mpf.make_addplot(hist_data['MACD_Signal'], panel=2, color='orange')
                        ])

                    # Create the plot
                    mc = mpf.make_marketcolors(
                        up='green',
                        down='red',
                        edge='inherit',
                        wick='inherit',
                        volume='in',
                        ohlc='inherit'
                    )
                    
                    s = mpf.make_mpf_style(
                        marketcolors=mc,
                        gridstyle=':',
                        y_on_right=False
                    )

                    try:
                        # Determine number of panels based on indicators
                        has_rsi = any('panel=1' in str(study) for study in additional_studies)
                        has_macd = any('panel=2' in str(study) for study in additional_studies)
                        
                        # Calculate panel ratios based on indicators and volume
                        if has_rsi and has_macd:
                            panel_ratios = (6, 2, 2, 1)  # Main + RSI + MACD + Volume
                        elif has_rsi or has_macd:
                            panel_ratios = (6, 2, 1)  # Main + 1 indicator + Volume
                        else:
                            panel_ratios = (6, 1)  # Main + Volume

                        # Create the plot
                        fig, axlist = mpf.plot(
                            df_mpf,
                            type='candle',
                            style=s,
                            addplot=additional_studies if additional_studies else None,
                            volume=True,
                            panel_ratios=panel_ratios,
                            title=f'\n{selected_stock} Price Analysis',
                            returnfig=True,
                            figsize=(12, 10)
                        )
                        
                        # Add horizontal lines for RSI if has_rsi
                        if has_rsi:
                            rsi_panel_index = 1
                            axlist[rsi_panel_index].axhline(y=70, color='r', linestyle='--', alpha=0.5)
                            axlist[rsi_panel_index].axhline(y=30, color='g', linestyle='--', alpha=0.5)
                        
                        st.pyplot(fig)
                    except Exception as e:
                        st.error(f"Error plotting data for {selected_stock}: {str(e)}")
            else:
                st.warning(f"No valid data available for {selected_stock}")
        except Exception as e:
            st.error(f"Error processing {selected_stock}: {str(e)}")

with col2:
    st.subheader("Technical Analysis")
    
    if selected_stock:  # Only show technical analysis if a stock is selected
        if hist_data is not None and not hist_data.empty and 'Close' in hist_data.columns:
            try:
                current_price = hist_data['Close'].iloc[-1]
                
                # Calculate daily change only if we have enough data
                if len(hist_data) >= 2:
                    daily_change = ((hist_data['Close'].iloc[-1] / hist_data['Close'].iloc[-2] - 1) * 100)
                else:
                    daily_change = 0
                
                # Get technical indicators if available
                current_rsi = hist_data['RSI'].iloc[-1] if ('RSI' in hist_data.columns and not hist_data['RSI'].isnull().iloc[-1]) else None
                current_macd = hist_data['MACD'].iloc[-1] if ('MACD' in hist_data.columns and not hist_data['MACD'].isnull().iloc[-1]) else None
                current_macd_signal = hist_data['MACD_Signal'].iloc[-1] if ('MACD_Signal' in hist_data.columns and not hist_data['MACD_Signal'].isnull().iloc[-1]) else None
                
                # Calculate volatility only if we have enough data points
                if len(hist_data) > 5:  # At least a week of data
                    volatility = hist_data['Close'].pct_change().std() * 100
                else:
                    volatility = None
                
                # Generate trading signals only if we have all required indicators
                if all(x is not None for x in [current_rsi, current_macd, current_macd_signal]):
                    signal = get_signal(current_rsi, current_macd, current_macd_signal)
                    signal_strength = get_signal_strength(current_rsi, current_macd, current_macd_signal, volatility or 0)
                else:
                    signal = "Neutral"
                    signal_strength = 5
                
                # Price metrics
                st.metric("Price (USD)", f"${current_price:.2f}")
                st.metric("24h Change", f"{daily_change:.2f}%")
                
                # Technical indicators with improved labeling
                if current_rsi is not None:
                    rsi_color = 'red' if current_rsi > 70 else 'green' if current_rsi < 30 else 'normal'
                    st.metric("RSI (14)", f"{current_rsi:.1f}", delta_color=rsi_color)
                
                if current_macd is not None:
                    macd_diff = current_macd - (current_macd_signal or 0)
                    st.metric("MACD", f"{current_macd:.3f}", delta=f"{macd_diff:+.3f}")
                
                if volatility is not None:
                    st.metric("Volatility (30d)", f"{volatility:.1f}%")
                
                # Signal with improved styling
                signal_color = {
                    'Buy': 'green',
                    'Sell': 'red',
                    'Neutral': 'gray'
                }
                st.markdown(
                    f"""
                    <div style="padding: 10px; border-radius: 5px; border: 1px solid {signal_color[signal]};">
                        <h3 style="color: {signal_color[signal]}; margin: 0;">Signal: {signal}</h3>
                    </div>
                    """, 
                    unsafe_allow_html=True
                )
                st.progress(signal_strength / 10)
                st.caption(f"Signal Strength: {signal_strength}/10")
                
            except Exception as e:
                st.error(f"Error processing technical analysis for {selected_stock}: {str(e)}")
        else:
            st.warning(f"Insufficient data available for {selected_stock} technical analysis")
    else:
        st.info("Select a stock to view technical analysis")

with col3:
    st.subheader("Sector Overview")
    sector_data = []
    processed_count = 0
    
    # Progress bar for sector analysis
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Filter out any known delisted or invalid symbols first
    active_symbols = []
    for symbol in sector_stocks[:10]:
        try:
            stock = yf.Ticker(symbol)
            info = stock.info
            if 'regularMarketPrice' in info and info['regularMarketPrice'] is not None:
                active_symbols.append(symbol)
        except:
            continue
    
    total_stocks = len(active_symbols)
    if total_stocks == 0:
        st.warning("No active stocks found in this sector")
    else:
        for i, symbol in enumerate(active_symbols):
            try:
                status_text.text(f"Analyzing {symbol}...")
                hist = get_stock_data(symbol, period='5d')
                
                if hist is not None and not hist.empty and len(hist) >= 2:
                    try:
                        daily_return = (hist['Close'].iloc[-1] / hist['Close'].iloc[-2] - 1) * 100
                        rsi_value = hist['RSI'].iloc[-1] if ('RSI' in hist.columns and not hist['RSI'].isnull().iloc[-1]) else float('nan')
                        current_price = hist['Close'].iloc[-1]
                        
                        if not pd.isna(current_price) and not pd.isna(daily_return):
                            sector_data.append({
                                'Symbol': symbol,
                                'Price': current_price,
                                'Change': daily_return,
                                'RSI': rsi_value
                            })
                            processed_count += 1
                    except Exception as calc_error:
                        st.warning(f"Could not calculate metrics for {symbol}")
                    
                    progress_bar.progress((i + 1) / total_stocks)
            except Exception as e:
                st.warning(f"Could not process data for {symbol}")
                continue
    
    status_text.empty()
    progress_bar.empty()
    
    if sector_data:
        st.caption(f"Showing data for {processed_count} out of {total_stocks} stocks")
        sector_df = pd.DataFrame(sector_data)
        sector_df = sector_df.sort_values('Change', ascending=False)
        
        # Enhanced dataframe styling
        def style_dataframe(val):
            if isinstance(val, (int, float)):
                if pd.isna(val):
                    return ''
                elif 'Change' in str(val):  # For the Change column
                    color = 'red' if val < 0 else 'green'
                    return f'color: {color}; font-weight: bold'
                elif 'RSI' in str(val):  # For the RSI column
                    if val > 70:
                        return 'color: red'
                    elif val < 30:
                        return 'color: green'
            return ''
        
        styled_df = sector_df.style\
            .format({'Price': '${:.2f}', 'Change': '{:+.2f}%', 'RSI': '{:.1f}'})\
            .applymap(style_dataframe)
        
        st.dataframe(styled_df, height=400)
    else:
        st.warning("No sector data available at the moment")

# Footer
st.markdown("---")
st.caption(f"Data source: Yahoo Finance | Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
st.caption("⚠️ This dashboard is for informational purposes only. Not financial advice.")


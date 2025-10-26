import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from ta.trend import MACD
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands

# Email configuration
EMAIL_ADDRESS = "u7583198037@gmail.com"
EMAIL_PASSWORD = "hebg eckk rkxm hqjm"
RECIPIENT_EMAILS = ["biuro4logic@o2.pl", "worldanarchy2121@gmail.com"]  # List of recipients

# Stocks organized by sectors
STOCK_SECTORS = {
    'Biotech & Pharmaceuticals': [
        'ARCT', 'CRSP', 'BIIB', 'VRTX', 'REGN', 'BNTX', 'EVTC', 'GNFT', 'MOR', 'SGEN',
        'MRNA', 'GILD', 'NVAX', 'ILMN', 'SRPT', 'EXEL', 'INCY', 'AMGN', 'SNY', 'RHHBY',
        'AZN', 'MRK', 'PFE', 'BAYN', 'NVO', 'IPN', 'JAZZ', 'IONS', 'BEAM', 'EDIT',
        'NTLA', 'RXRX', 'BBIO', 'RLAY', 'DNLI', 'SDGR', 'ABCL', 'TWST', 'TXG', 'BNGO',
        'VCYT', 'EXAS', 'GH', 'FATE', 'BLUE', 'SRNE', 'IBRX', 'IMCR', 'IMGN', 'IMVT',
        'VIR', 'IOVA', 'AGEN', 'ALEC', 'ALLO', 'ALLR', 'RNA', 'BDTX', 'CALA', 'CADL',
        'CRBU', 'CERE', 'COGT', 'CTMX', 'DCPH', 'DSGN', 'LLY', 'EQRX', 'EVLO', 'FHTX',
        'DNA', 'HARP', 'INSP', 'KNTE', 'KYMR', 'LEGN', 'MRSN', 'MRTX', 'MRUS', 'NKTR',
        'NRIX', 'ONCY', 'ORIC', 'PSTX', 'PBYI', 'RVMD', 'RUBY', 'SANA', 'STRO', 'TNGX',
        'TERN', 'TCRX', 'VXCY', 'VERV', 'ZNTL', 'ZYME', 'ZLAB', 'BGNE', '6185.HK', 'SVA'
    ],
    'Technology & Semiconductors': [
        'NVDA', 'AMD', 'INTC', 'ASML', 'PLTR', 'AI', 'ARM', 'TSM', 'MRVL', 'SMCI'
    ],
    'Gaming & Entertainment': [
        'ATVI', 'EA', 'TTWO', 'CDR.WA', 'UBI.PA', 'RBLX', '7974.T', '6758.T', 'MTTR', 'HUYA'
    ],
    'Electric Vehicles & Battery': [
        'TSLA', 'NIO', 'RIVN', 'LCID', 'NKLA', 'PSNY', 'FREY', 'QS', 'CHPT', 'BLNK'
    ],
    'Clean Energy': [
        'ENPH', 'PLUG', 'FSLR', 'RUN', 'NOVA', 'NEE', 'ORSTED.CO', 'VWS.CO', 'SEDG', 'SMR'
    ],
    'Mining & Materials': [
        'ALB', 'LTHM', 'PLL', 'CCJ', 'UUUU', 'GLEN.L', 'FM.TO', 'LAC', 'MP', 'SQM'
    ],
    'Healthcare Tech & Services': [
        'TDOC', 'AMWL', 'HIMS', 'BBLN', 'GDRX', 'PEAR', 'CVS', 'WBA', 'UNH', 'ANTM',
        'CI', 'HUM', 'CNC', 'MOH', 'ELV', 'MCK', 'CAH', 'ABC', 'VEEV', 'CLOV'
    ],
    'Medical Devices': [
        'MDT', 'BSX', 'SYK', 'ZBH', 'EW', 'ISRG', 'DXCM', 'PODD', 'RMD', 'PHG',
        'SHL.DE', 'GE', '7751.T', '4901.T', '7733.T', '4543.T', 'SN.L', 'VAR', 'ARAY', 'VRAY'
    ]
}

# Flatten the dictionary into a list for tracking
STOCKS_TO_TRACK = [stock for stocks in STOCK_SECTORS.values() for stock in stocks]

# Technical Analysis Parameters
RSI_PERIOD = 14
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9

def get_trading_signal(hist_data):
    """Generate trading signals based on technical indicators"""
    if len(hist_data) < 30:  # Need enough data for indicators
        return "HOLD", {}
    
    # Calculate RSI
    rsi = RSIIndicator(close=hist_data['Close'], window=RSI_PERIOD)
    current_rsi = rsi.rsi().iloc[-1]
    
    # Calculate MACD
    macd = MACD(close=hist_data['Close'])
    macd_line = macd.macd().iloc[-1]
    signal_line = macd.macd_signal().iloc[-1]
    
    # Calculate Bollinger Bands
    bb = BollingerBands(close=hist_data['Close'])
    upper_band = bb.bollinger_hband().iloc[-1]
    lower_band = bb.bollinger_lband().iloc[-1]
    
    # Trading signals logic
    signal = "HOLD"
    reasons = {
        'RSI': round(current_rsi, 2),
        'MACD': f"{'Bullish' if macd_line > signal_line else 'Bearish'}"
    }
    
    if current_rsi < RSI_OVERSOLD and macd_line > signal_line:
        signal = "BUY"
    elif current_rsi > RSI_OVERBOUGHT and macd_line < signal_line:
        signal = "SELL"
    
    return signal, reasons

def get_stock_data():
    """Fetch stock data for tracked stocks"""
    data = {}
    for symbol in STOCKS_TO_TRACK:
        try:
            stock = yf.Ticker(symbol)
            hist = stock.history(period='30d')  # Get 30 days of data for analysis
            if not hist.empty:
                current_price = hist['Close'].iloc[-1]
                prev_price = hist['Close'].iloc[-2]
                price_change = ((current_price - prev_price) / prev_price) * 100
                volume = hist['Volume'].iloc[-1]
                
                # Get trading signals
                signal, reasons = get_trading_signal(hist)
                
                # Calculate volatility (30-day standard deviation of returns)
                volatility = hist['Close'].pct_change().std() * 100
                
                # Generate TradingView chart link
                trading_view_link = f"https://www.tradingview.com/chart/?symbol={symbol}"
                
                data[symbol] = {
                    'price': round(current_price, 2),
                    'change': round(price_change, 2),
                    'volume': volume,
                    'signal': signal,
                    'reasons': reasons,
                    'volatility': round(volatility, 2),
                    'chart_link': trading_view_link
                }
        except Exception as e:
            print(f"Error fetching data for {symbol}: {e}")
    return data

def analyze_market_data(data):
    """Analyze the market data and generate insights"""
    insights = []
    for symbol, info in data.items():
        # Add insights for significant price changes
        if info['change'] > 5:
            insights.append(f"🚀 {symbol} surged: +{info['change']}% with {info['signal']} signal (RSI: {info['reasons']['RSI']})")
        elif info['change'] < -5:
            insights.append(f"📉 {symbol} dropped: {info['change']}% with {info['signal']} signal (RSI: {info['reasons']['RSI']})")
        
        # Add insights for trading signals with strong indicators
        if info['signal'] == "BUY" and info['reasons']['RSI'] < 30:
            insights.append(f"💡 Strong BUY signal for {symbol}: RSI oversold at {info['reasons']['RSI']}, {info['reasons']['MACD']} MACD")
        elif info['signal'] == "SELL" and info['reasons']['RSI'] > 70:
            insights.append(f"⚠️ Strong SELL signal for {symbol}: RSI overbought at {info['reasons']['RSI']}, {info['reasons']['MACD']} MACD")
        
        # Add insights for high volatility
        if info['volatility'] > 15:
            insights.append(f"📊 High volatility alert for {symbol}: {info['volatility']}% (30-day)")
    
    return insights

def create_email_content(data, insights):
    """Create HTML email content"""
    html = f"""
    <html>
        <body>
            <h2>Market Report - {datetime.now().strftime('%Y-%m-%d %H:%M')}</h2>
            <style>
                .sector-header {{
                    background-color: #f8f9fa;
                    padding: 10px;
                    margin-top: 20px;
                    border-radius: 5px;
                    font-size: 1.2em;
                    color: #2c3e50;
                }}
            </style>
    """
    
    # Sort stocks by sector
    sector_data = {}
    for sector, stocks in STOCK_SECTORS.items():
        sector_data[sector] = {stock: data[stock] for stock in stocks if stock in data}
    
    # Create tables for each sector
    for sector, sector_stocks in sector_data.items():
        if sector_stocks:
            html += f"""
                <div class="sector-header">{sector}</div>
                <table style="border-collapse: collapse; width: 100%; margin-bottom: 20px;">
                    <tr style="background-color: #f2f2f2;">
                        <th style="border: 1px solid #ddd; padding: 8px;">Stock</th>
                        <th style="border: 1px solid #ddd; padding: 8px;">Price</th>
                        <th style="border: 1px solid #ddd; padding: 8px;">Change</th>
                        <th style="border: 1px solid #ddd; padding: 8px;">Signal</th>
                        <th style="border: 1px solid #ddd; padding: 8px;">RSI</th>
                        <th style="border: 1px solid #ddd; padding: 8px;">MACD</th>
                        <th style="border: 1px solid #ddd; padding: 8px;">Volatility</th>
                        <th style="border: 1px solid #ddd; padding: 8px;">Chart</th>
                    </tr>
            """
    
            # Sort stocks by absolute price change within each sector
            for symbol, info in sorted(sector_stocks.items(), key=lambda x: abs(x[1]['change']), reverse=True):
                signal_colors = {
                    'BUY': '#d4efdf',    # Green
                    'SELL': '#f9ebea',    # Red
                    'HOLD': '#fef9e7'     # Yellow
                }
                color = signal_colors[info['signal']]
                
                html += f"""
                    <tr style="background-color: {color}">
                        <td style="border: 1px solid #ddd; padding: 8px;">{symbol}</td>
                        <td style="border: 1px solid #ddd; padding: 8px;">${info['price']}</td>
                        <td style="border: 1px solid #ddd; padding: 8px;">{info['change']}%</td>
                        <td style="border: 1px solid #ddd; padding: 8px; font-weight: bold;">{info['signal']}</td>
                        <td style="border: 1px solid #ddd; padding: 8px;">{info['reasons']['RSI']}</td>
                        <td style="border: 1px solid #ddd; padding: 8px;">{info['reasons']['MACD']}</td>
                        <td style="border: 1px solid #ddd; padding: 8px;">{info['volatility']}%</td>
                        <td style="border: 1px solid #ddd; padding: 8px;"><a href="{info['chart_link']}" target="_blank">View Chart</a></td>
                    </tr>
                """
            html += """
                </table>
            """
    
    html += """
            </table>
    """
    
    if insights:
        html += """
            <h3>Key Market Insights</h3>
            <ul>
        """
        for insight in insights:
            html += f"<li>{insight}</li>"
        html += "</ul>"
    
    html += """
            <p style="color: #666; font-size: 12px;">
                This is an automated report. Please do not reply to this email.<br>
                Data provided by Yahoo Finance. Charts powered by TradingView.<br>
                💡 Click 'View Chart' for detailed technical analysis and candlestick patterns.
            </p>
        </body>
    </html>
    """
    return html

def send_email(html_content):
    """Send email with the market report to multiple recipients"""
    try:
        for recipient in RECIPIENT_EMAILS:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f'Market Report - {datetime.now().strftime("%Y-%m-%d %H:%M")}'
            msg['From'] = EMAIL_ADDRESS
            msg['To'] = recipient

            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)

            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
                server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
                server.send_message(msg)
            print(f"Email sent successfully to {recipient}!")
    except Exception as e:
        print(f"Error sending email: {e}")

def daily_task():
    """Main function to run daily"""
    print(f"Running daily task at {datetime.now()}")
    data = get_stock_data()
    if data:
        insights = analyze_market_data(data)
        html_content = create_email_content(data, insights)
        send_email(html_content)

if __name__ == "__main__":
    print("Stock Market Agent started. Running immediate report...")
    daily_task()
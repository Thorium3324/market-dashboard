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

# ====== Email configuration ======
EMAIL_ADDRESS = "u7583198037@gmail.com"
EMAIL_PASSWORD = "hebg eckk rkxm hqjm"
RECIPIENT_EMAILS = ["biuro4logic@o2.pl", "worldanarchy2121@gmail.com"]

# ====== Stocks organized by sectors (maximized) ======
STOCK_SECTORS = {
    'Biotech & Pharmaceuticals': ['ARCT', 'CRSP', 'BIIB', 'VRTX', 'REGN', 'BNTX', 'EVTC', 'GNFT', 'MOR', 'SGEN','MRNA', 'GILD', 'NVAX', 'ILMN', 'SRPT', 'EXEL', 'INCY', 'AMGN', 'SNY', 'RHHBY','AZN', 'MRK', 'PFE', 'BAYN', 'NVO', 'IPN', 'JAZZ', 'IONS', 'BEAM', 'EDIT','NTLA', 'RXRX', 'BBIO', 'RLAY', 'DNLI', 'SDGR', 'ABCL', 'TWST', 'TXG', 'BNGO','VCYT', 'EXAS', 'GH', 'FATE', 'BLUE', 'SRNE', 'IBRX', 'IMCR', 'IMGN', 'IMVT','VIR', 'IOVA', 'AGEN', 'ALEC', 'ALLO', 'ALLR', 'RNA', 'BDTX', 'CALA', 'CADL','CRBU', 'CERE', 'COGT', 'CTMX', 'DCPH', 'DSGN', 'LLY', 'EQRX', 'EVLO', 'FHTX','DNA', 'HARP', 'INSP', 'KNTE', 'KYMR', 'LEGN', 'MRSN', 'MRTX', 'MRUS', 'NKTR','NRIX', 'ONCY', 'ORIC', 'PSTX', 'PBYI', 'RVMD', 'RUBY', 'SANA', 'STRO', 'TNGX','TERN', 'TCRX', 'VXCY', 'VERV', 'ZNTL', 'ZYME', 'ZLAB', 'BGNE', '6185.HK', 'SVA'],
    'Technology & Semiconductors': ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'AMD', 'INTC', 'ASML', 'PLTR','AI', 'ARM', 'TSM', 'MRVL', 'SMCI', 'QCOM', 'TXN', 'ADI', 'MU', 'AVGO', 'ORCL','IBM', 'CRM', 'SAP', 'NOW', 'SHOP', 'SQ', 'ADBE', 'CSCO', 'SNOW', 'ZM', 'UBER','LYFT', 'TWTR', 'SNAP', 'PINS', 'DOCU', 'MDB', 'NET', 'TEAM', 'FSLY', 'OKTA'],
    'Gaming & Entertainment': ['ATVI', 'EA', 'TTWO', 'CDR.WA', 'UBI.PA', 'RBLX', '7974.T', '6758.T', 'MTTR','HUYA', 'ZNGA', 'NVL', 'NEXON', 'SONY', 'DIS', 'NFLX', 'TCEHY', 'TTD', 'NETFLIX'],
    'Electric Vehicles & Battery': ['TSLA', 'NIO', 'RIVN', 'LCID', 'NKLA', 'FREY', 'QS', 'CHPT', 'BLNK', 'BYDDF','KNDI', 'LI', 'XPEV', 'FSR', 'AVL', 'MELI', 'EVGO', 'ENPH'],
    'Clean Energy': ['ENPH', 'PLUG', 'FSLR', 'RUN', 'NOVA', 'NEE', 'ORSTED.CO', 'VWS.CO', 'SEDG','SMR', 'BE', 'SPWR', 'CSIQ', 'AY', 'FCEL', 'BLNK'],
    'Mining & Materials': ['ALB', 'LTHM', 'PLL', 'CCJ', 'UUUU', 'GLEN.L', 'FM.TO', 'LAC', 'MP', 'SQM','RIO', 'BHP', 'VALE', 'FCX', 'NEM', 'GOLD', 'AG', 'PAAS', 'AEM', 'KL', 'SCCO'],
    'Healthcare Tech & Services': ['TDOC', 'AMWL', 'HIMS', 'BBLN', 'GDRX', 'PEAR', 'CVS', 'WBA', 'UNH', 'ANTM','CI', 'HUM', 'CNC', 'MOH', 'ELV', 'MCK', 'CAH', 'ABC', 'VEEV', 'CLOV', 'ZM'],
    'Medical Devices': ['MDT', 'BSX', 'SYK', 'ZBH', 'EW', 'ISRG', 'DXCM', 'PODD', 'RMD', 'PHG','SHL.DE', 'GE', '7751.T', '4901.T', '7733.T', '4543.T', 'SN.L', 'VAR', 'ARAY', 'VRAY','HOLX', 'COO', 'ABT', 'BDX', 'STJ', 'DHR'],
    'Finance & Banks': ['JPM', 'BAC', 'C', 'WFC', 'GS', 'MS', 'USB', 'PNC', 'BK', 'SCHW', 'CB', 'SPGI','V', 'MA', 'AXP', 'COF', 'NDAQ', 'BLK', 'TFC', 'RJF'],
    'Telecom & Internet': ['T', 'VZ', 'TMUS', 'CHL', 'NTT', 'S', 'ORAN', 'BCE', 'TLK', 'VOD', 'DTEGY', 'CMCSA'],
    'Retail & E-Commerce': ['WMT', 'COST', 'AMZN', 'BABA', 'JD', 'SHOP', 'MELI', 'EBAY', 'TGT', 'HD','LOW', 'BBY', 'KMX', 'DG', 'OLLI', 'F', 'GM', 'TSLA'],
    'Oil & Gas': ['XOM', 'CVX', 'COP', 'TOT', 'BP', 'RDS.A', 'RDS.B', 'E', 'SLB', 'HAL','MPC', 'VLO', 'PSX', 'CNP', 'ENB', 'SU', 'EQNR'],
    'Defense & Aerospace': ['LMT', 'BA', 'NOC', 'GD', 'RTX', 'TXT', 'TDY', 'HII', 'CNHI', 'COL'],
    'Food & Beverage': ['KO', 'PEP', 'MNST', 'SBUX', 'MCD', 'CMG', 'YUM', 'DEO', 'GIS', 'KHC','TSN', 'MDLZ', 'COST', 'WMT', 'HSY', 'ADM'],
    'Real Estate': ['PLD', 'AMT', 'CCI', 'SPG', 'VTR', 'EQR', 'AVB', 'O', 'EXR', 'DLR','WY', 'PSA', 'WELL', 'EQIX', 'BXP', 'SBAC'],
    'Utilities': ['NEE', 'DUK', 'SO', 'AEP', 'EXC', 'D', 'SRE', 'PEG', 'EIX', 'ED']
}

# Flatten the dictionary into a list
STOCKS_TO_TRACK = [stock for stocks in STOCK_SECTORS.values() for stock in stocks]

# ====== Technical Analysis Parameters ======
RSI_PERIOD = 14
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30

def get_trading_signal(hist_data):
    if len(hist_data) < 30:
        return "HOLD", {}
    rsi = RSIIndicator(hist_data['Close'], window=RSI_PERIOD)
    current_rsi = rsi.rsi().iloc[-1]
    macd = MACD(hist_data['Close'])
    macd_line = macd.macd().iloc[-1]
    signal_line = macd.macd_signal().iloc[-1]
    bb = BollingerBands(hist_data['Close'])
    upper_band = bb.bollinger_hband().iloc[-1]
    lower_band = bb.bollinger_lband().iloc[-1]
    signal = "HOLD"
    reasons = {'RSI': round(current_rsi, 2), 'MACD': 'Bullish' if macd_line>signal_line else 'Bearish'}
    if current_rsi < RSI_OVERSOLD and macd_line > signal_line:
        signal = "BUY"
    elif current_rsi > RSI_OVERBOUGHT and macd_line < signal_line:
        signal = "SELL"
    return signal, reasons

def get_stock_data():
    data = {}
    for symbol in STOCKS_TO_TRACK:
        try:
            stock = yf.Ticker(symbol)
            hist = stock.history(period='30d')
            if not hist.empty:
                current_price = hist['Close'].iloc[-1]
                prev_price = hist['Close'].iloc[-2]
                price_change = ((current_price - prev_price)/prev_price)*100
                volume = hist['Volume'].iloc[-1]
                signal, reasons = get_trading_signal(hist)
                volatility = hist['Close'].pct_change().std()*100
                # Include only strong signals or >1% change
                if signal in ['BUY','SELL'] or abs(price_change)>1:
                    trading_view_link = f"https://www.tradingview.com/chart/?symbol={symbol}"
                    data[symbol] = {
                        'price': round(current_price,2),
                        'change': round(price_change,2),
                        'volume': volume,
                        'signal': signal,
                        'reasons': reasons,
                        'volatility': round(volatility,2),
                        'chart_link': trading_view_link
                    }
        except:
            continue
    return data

def analyze_market_data(data):
    insights = []
    for symbol, info in data.items():
        if info['change'] > 5:
            insights.append(f"🚀 {symbol} surged: +{info['change']}% ({info['signal']}) RSI:{info['reasons']['RSI']}")
        elif info['change'] < -5:
            insights.append(f"📉 {symbol} dropped: {info['change']}% ({info['signal']}) RSI:{info['reasons']['RSI']}")
        if info['signal']=="BUY" and info['reasons']['RSI']<30:
            insights.append(f"💡 Strong BUY for {symbol}: RSI oversold {info['reasons']['RSI']}, {info['reasons']['MACD']} MACD")
        elif info['signal']=="SELL" and info['reasons']['RSI']>70:
            insights.append(f"⚠️ Strong SELL for {symbol}: RSI overbought {info['reasons']['RSI']}, {info['reasons']['MACD']} MACD")
        if info['volatility']>15:
            insights.append(f"📊 High volatility {symbol}: {info['volatility']}% (30d)")
    return insights

def create_email_content(data, insights):
    html = f"""<html><body><h2>Market Report - {datetime.now().strftime('%Y-%m-%d %H:%M')}</h2>"""
    sector_data = {sector: {s: data[s] for s in stocks if s in data} for sector, stocks in STOCK_SECTORS.items()}
    for sector, stocks in sector_data.items():
        if stocks:
            html += f"<h3>{sector}</h3><table style='border-collapse: collapse; width:100%'>"
            html += "<tr><th>Stock</th><th>Price</th><th>Change</th><th>Signal</th><th>RSI</th><th>MACD</th><th>Volatility</th><th>Chart</th></tr>"
            for s, info in sorted(stocks.items(), key=lambda x: abs(x[1]['change']), reverse=True):
                color={'BUY':'#d4efdf','SELL':'#f9ebea','HOLD':'#fef9e7'}[info['signal']]
                html += f"<tr style='background:{color}'><td>{s}</td><td>${info['price']}</td><td>{info['change']}%</td><td>{info['signal']}</td><td>{info['reasons']['RSI']}</td><td>{info['reasons']['MACD']}</td><td>{info['volatility']}%</td><td><a href='{info['chart_link']}' target='_blank'>View</a></td></tr>"
            html += "</table>"
    if insights:
        html += "<h3>Key Market Insights</h3><ul>"
        for insight in insights:
            html += f"<li>{insight}</li>"
        html += "</ul>"
    html += "<p style='color:#666;font-size:12px'>Automated report. Data via Yahoo Finance. Charts via TradingView.</p></body></html>"
    return html

def send_email(html_content):
    for recipient in RECIPIENT_EMAILS:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"Market Report - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = recipient
        msg.attach(MIMEText(html_content, 'html'))
        with smtplib.SMTP_SSL('smtp.gmail.com',465) as server:
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.send_message(msg)
        print(f"Email sent to {recipient}")

def daily_task():
    print(f"Running daily task at {datetime.now()}")
    data = get_stock_data()
    if data:
        insights = analyze_market_data(data)
        html_content = create_email_content(data, insights)
        send_email(html_content)

if __name__=="__main__":
    print("Stock Market Agent started. Running immediate report...")
    daily_task()

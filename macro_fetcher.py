import yfinance as yf
import requests
import logging
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

def get_dxy_trend():
    """
    Fetches the US Dollar Index (DXY) from Yahoo Finance and calculates a simple short-term trend.
    """
    try:
        # DX-Y.NYB is the ticker for US Dollar Index on Yahoo Finance
        ticker = yf.Ticker('DX-Y.NYB')
        dxy = ticker.history(period='5d')
        if dxy.empty:
            return "Unable to fetch DXY data."
        
        # Calculate a simple trend based on the last few days
        first_close = float(dxy['Close'].iloc[0]) if not dxy['Close'].empty else None
        last_close = float(dxy['Close'].iloc[-1]) if not dxy['Close'].empty else None
        
        if first_close and last_close:
            pct_change = ((last_close - first_close) / first_close) * 100
            trend = "Bullish (Upward)" if pct_change > 0 else "Bearish (Downward)"
            return f"Current DXY is at {last_close:.2f}. The 5-day trend is {trend} ({pct_change:.2f}%)."
        return f"Current DXY is at {last_close:.2f}."
    except Exception as e:
        logger.error(f"Error fetching DXY: {e}")
        return "Error fetching DXY data."

def fetch_ff_calendar(symbol="XAUUSD"):
    url = "https://nfs.faireconomy.media/ff_calendar_thisweek.xml"
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, "xml")
        events = []
        
        # Determine relevant currencies (e.g. EUR and USD for EURUSD)
        currencies = []
        if len(symbol) == 6:
            currencies = [symbol[:3], symbol[3:]]
        else:
            currencies = ["USD"] # fallback
            
        if "XAU" in currencies:
            currencies.remove("XAU")
            currencies.append("USD")
            
        for event in soup.find_all('event'):
            country = event.country
            if country and country.text in currencies:
                impact = event.impact
                if impact and impact.text in ['High', 'Medium']:
                    title = event.title.text if event.title else "Unknown"
                    forecast = event.forecast.text if event.forecast else "N/A"
                    previous = event.previous.text if event.previous else "N/A"
                    events.append(f"- {title} ({country.text}) | Impact: {impact.text} | Forecast: {forecast} | Prev: {previous}")
        
        if not events:
            return f"No high/medium impact events found for {', '.join(currencies)} this week."
        return "\n".join(events[:10])
    except Exception as e:
        logger.error(f"Failed to fetch FF calendar: {e}")
        return "Failed to fetch calendar data."

def fetch_google_news(symbol="XAUUSD"):
    # Construct search query based on symbol
    if len(symbol) == 6:
        base = symbol[:3]
        quote = symbol[3:]
        if base == "XAU":
            query = "gold+USD+economy+forex"
        else:
            query = f"{base}+{quote}+economy+forex"
    else:
        query = f"{symbol}+economy+forex"
        
    url = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, "xml")
        items = soup.find_all("item")
        headlines = []
        for item in items[:5]:
            title = item.title.text if item.title else "Unknown headline"
            headlines.append(f"- {title}")
            
        if not headlines:
            return "No recent news found."
        return "\n".join(headlines)
    except Exception as e:
        logger.error(f"Failed to fetch news: {e}")
        return "Failed to fetch news data."

def get_macro_news_and_calendar(symbol):
    """
    Fetches real-time news and economic calendar data from public RSS/XML feeds.
    """
    calendar_str = f"Recent Economic Calendar Data (High/Medium Impact for {symbol}):\n" + fetch_ff_calendar(symbol)
    news_str = f"Latest Macro News Headlines ({symbol}):\n" + fetch_google_news(symbol)
        
    return calendar_str + "\n\n" + news_str

def fetch_all_macro_data(symbol="XAUUSD"):
    logger.info("Fetching DXY Data...")
    dxy_summary = get_dxy_trend()
    
    logger.info(f"Fetching Macro News & Calendar Data for {symbol}...")
    news_calendar_summary = get_macro_news_and_calendar(symbol)
    
    return f"--- DXY Trend ---\n{dxy_summary}\n\n--- News & Calendar ---\n{news_calendar_summary}"

import yfinance as yf
import pandas as pd
import logging
import os
from dotenv import load_dotenv
try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    mt5 = None
    MT5_AVAILABLE = False

logger = logging.getLogger(__name__)
load_dotenv()

SYMBOL_MAP = {
    'XAUUSD': 'GC=F',
    'EURUSD': 'EURUSD=X',
    'GBPUSD': 'GBPUSD=X',
    'USDJPY': 'JPY=X',
    'BTCUSD': 'BTC-USD',
    'ETHUSD': 'ETH-USD'
}

def get_historical_data(symbol, timeframe, num_candles=100, **kwargs):
    """
    Fetches OHLCV data for a specific symbol and calculates RSI, MACD, and ATR using yfinance.
    kwargs added to silently accept login/password variables passed from older code temporarily.
    """
    yf_symbol = SYMBOL_MAP.get(symbol, symbol)
    
    # Map app timeframe to yfinance interval and period
    if timeframe == '15m':
        interval = '15m'
        period = '1mo'
    elif timeframe == '1h':
        interval = '1h'
        period = '1mo'
    elif timeframe == '1d':
        interval = '1d'
        period = '1y'
    elif timeframe == '1wk':
        interval = '1wk'
        period = '5y'
    elif timeframe == '1mo':
        interval = '1mo'
        period = '10y'
    else:
        # Fallbacks for older requests like H1, H4
        if timeframe == 'H1':
            interval = '1h'
            period = '1mo'
        elif timeframe == 'H4':
            interval = '1h' # Close enough fallback since 4h isn't natively standard without resampling
            period = '1mo'
        else:
            logger.error(f"Invalid timeframe: {timeframe}")
            return None

    logger.info(f"Fetching data for {symbol} ({yf_symbol}) on {timeframe}...")
    try:
        # download returns a dataframe
        df = yf.download(yf_symbol, period=period, interval=interval, progress=False)
        if df.empty:
            logger.error(f"Failed to get data for {symbol} {timeframe}")
            return None
            
        # yfinance > 0.2.x might return multi-index columns for single symbols, let's flatten them safely
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [c[0].lower() for c in df.columns]
        else:
            df.columns = [c.lower() for c in df.columns]
            
        df.reset_index(inplace=True)
        # The index column is usually 'Datetime' or 'Date'
        time_col = 'Datetime' if 'Datetime' in df.columns else 'Date'
        if time_col in df.columns:
            df.rename(columns={time_col: 'time'}, inplace=True)
        
        # Calculate indicators manually to avoid dependency issues FIRST (needs enough historical data)
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI_14'] = 100 - (100 / (1 + rs))
        
        exp1 = df['close'].ewm(span=12, adjust=False).mean()
        exp2 = df['close'].ewm(span=26, adjust=False).mean()
        df['MACD_12_26_9'] = exp1 - exp2
        df['MACDs_12_26_9'] = df['MACD_12_26_9'].ewm(span=9, adjust=False).mean()
        df['MACDh_12_26_9'] = df['MACD_12_26_9'] - df['MACDs_12_26_9']
        
        high_low = df['high'] - df['low']
        high_close = (df['high'] - df['close'].shift()).abs()
        low_close = (df['low'] - df['close'].shift()).abs()
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['ATRr_14'] = true_range.rolling(14).mean()
        
        if 'volume' in df.columns:
            df['Volume_MA_20'] = df['volume'].rolling(20).mean()
        else:
            df['Volume_MA_20'] = 0.0
        
        df.dropna(inplace=True)
        
        # Keep only the latest num_candles
        df = df.tail(num_candles).copy()
        df.reset_index(drop=True, inplace=True)
        
        return df
    except Exception as e:
        logger.error(f"Error fetching data from yfinance: {e}")
        return None

def get_account_balance(**kwargs):
    """
    Returns a mock balance.
    """
    return 10000.0

def get_daily_atr(symbol, **kwargs):
    """
    Fetches the most recent Daily ATR for the requested symbol using yfinance.
    """
    yf_symbol = SYMBOL_MAP.get(symbol, symbol)
    try:
        df = yf.download(yf_symbol, period='1mo', interval='1d', progress=False)
        if df.empty:
            return 25.0
            
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [c[0].lower() for c in df.columns]
        else:
            df.columns = [c.lower() for c in df.columns]
            
        high_low = df['high'] - df['low']
        high_close = (df['high'] - df['close'].shift()).abs()
        low_close = (df['low'] - df['close'].shift()).abs()
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['ATRr_14'] = true_range.rolling(14).mean()
        
        if df.empty or 'ATRr_14' not in df.columns:
            return 25.0
            
        return float(df['ATRr_14'].iloc[-1])
    except Exception as e:
        logger.error(f"Error calculating Daily ATR: {e}")
        return 25.0

def execute_mt5_trade(action, symbol, lot=0.01, sl=None, tp=None, **kwargs):
    """
    Executes a market order on MetaTrader 5.
    """
    if not mt5.initialize():
        logger.error(f"MT5 initialize() failed, error code: {mt5.last_error()}")
        return False, f"MT5 initialization failed. Error: {mt5.last_error()}"

    action = action.upper()
    if action not in ["BUY", "SELL"]:
        return False, f"Invalid action: {action}"

    order_type = mt5.ORDER_TYPE_BUY if action == "BUY" else mt5.ORDER_TYPE_SELL
    
    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is None:
        logger.error(f"{symbol} not found in MT5")
        return False, f"{symbol} not found in MT5"
        
    if not symbol_info.visible:
        if not mt5.symbol_select(symbol, True):
            return False, f"Failed to select {symbol}"

    point = symbol_info.point
    price = mt5.symbol_info_tick(symbol).ask if action == "BUY" else mt5.symbol_info_tick(symbol).bid

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": float(lot),
        "type": order_type,
        "price": price,
        "deviation": 20,
        "magic": 234000,
        "comment": "AI Trading Bot",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    if sl is not None and sl > 0:
        request["sl"] = float(sl)
    if tp is not None and tp > 0:
        request["tp"] = float(tp)

    result = mt5.order_send(request)
    
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        logger.error(f"Order send failed, retcode: {result.retcode}")
        return False, f"Order failed. Error code: {result.retcode}"

    return True, f"Order {result.order} successfully placed! Action: {action}, Symbol: {symbol}, Lot: {lot}, Price: {price}, SL: {sl}, TP: {tp}"


def get_support_resistance(df, prominence=0.01, distance=5):
    """
    Finds Support and Resistance levels using pure pandas/python.
    Returns a list of resistance levels and support levels.
    """
    if df is None or df.empty:
        return [], []
        
    prices = df['close'].values.tolist()
    
    resistances = []
    supports = []
    n = len(prices)
    
    for i in range(distance, n - distance):
        is_peak = True
        is_trough = True
        for j in range(i - distance, i + distance + 1):
            if i != j:
                if prices[i] <= prices[j]:
                    is_peak = False
                if prices[i] >= prices[j]:
                    is_trough = False
                    
        if is_peak:
            # Check prominence (naive check: just needs to be X% higher than adjacent local minima)
            resistances.append(prices[i])
        elif is_trough:
            supports.append(prices[i])
            
    # Filter close levels (naively just return unique sorted)
    resistances = sorted(list(set(resistances)))
    supports = sorted(list(set(supports)))
    
    return supports, resistances

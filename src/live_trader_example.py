import ccxt
import pandas as pd
import pandas_ta as ta
import time
import os
from datetime import datetime

# --- CONFIGURATION ---
API_KEY = 'ZtKWqcd6R5UDwwD5p2qOtvv9YoRXSiHSM2yZ7P9CkNEfEzbVlfYt5s1wR94faqeL'
SECRET_KEY = 'xtyE9AzOpwOhzJNLzfiHcy2zVEd369uFCAwLuFkU54OlG59kZaqFQDMqXLefv3lJ'
SYMBOL = 'BTC/USDT'
TIMEFRAME = '1h'
TRADE_AMOUNT_USDT = 100  # Amount to buy in USDT
USE_TESTNET = True # Set to True to use Binance Testnet
# ---------------------

def get_exchange():
    exchange = ccxt.binance({
        'apiKey': API_KEY,
        'secret': SECRET_KEY,
        'enableRateLimit': True,
        'options': {'defaultType': 'spot'}
    })
    
    if USE_TESTNET:
        exchange.set_sandbox_mode(True)
        print("⚠️  USING BINANCE TESTNET ⚠️")
        
    return exchange

def fetch_data(exchange, symbol, timeframe, limit=100):
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    return df

def calculate_signal(df):
    # Pure Bollinger Bands Strategy (No RSI)
    length = 20
    std = 2.0
    
    # Calculate Indicators
    bb = ta.bbands(df['close'], length=length, std=std)
    
    # Get latest candle (iloc[-1] is the current forming candle, iloc[-2] is the last closed candle)
    # Usually we trade on closed candles to avoid repainting.
    last_candle = df.iloc[-2]
    
    # Extract BB values
    # Note: pandas-ta column names depend on params
    lower_col = f"BBL_{length}_{std}"
    upper_col = f"BBU_{length}_{std}"
    
    # Check if columns exist (pandas-ta naming convention)
    if lower_col not in bb.columns:
        lower_col = bb.columns[0]
        upper_col = bb.columns[2]
        
    lower_band = bb[lower_col].iloc[-2]
    upper_band = bb[upper_col].iloc[-2]
    
    close_price = last_candle['close']
    
    print(f"Time: {last_candle.name} | Price: {close_price} | LowerBB: {lower_band:.2f} | UpperBB: {upper_band:.2f}")
    
    # Logic: Pure Bollinger Reversion
    # Buy when price < lower band
    if close_price < lower_band:
        return 'BUY'
    # Sell when price > upper band
    elif close_price > upper_band:
        return 'SELL'
    
    return 'NEUTRAL'

def execute_trade(exchange, symbol, signal, amount_usdt):
    try:
        # Get current price
        ticker = exchange.fetch_ticker(symbol)
        price = ticker['last']
        
        # Calculate amount in base currency (BTC)
        amount_btc = amount_usdt / price
        
        # Check balance
        balance = exchange.fetch_balance()
        usdt_balance = balance['total']['USDT']
        btc_balance = balance['total']['BTC']
        
        if signal == 'BUY':
            if usdt_balance < amount_usdt:
                print("Insufficient USDT balance.")
                return
            
            print(f"Executing BUY order for {amount_btc:.6f} {symbol.split('/')[0]}...")
            # exchange.create_market_buy_order(symbol, amount_btc) # UNCOMMENT TO ENABLE REAL TRADING
            print("BUY Order Simulated (Uncomment code to execute)")
            
        elif signal == 'SELL':
            # For this simple bot, we sell all available BTC or a fixed amount?
            # Let's assume we sell the same amount we would buy, or check if we have enough.
            if btc_balance < amount_btc:
                print("Insufficient BTC balance to sell.")
                return

            print(f"Executing SELL order for {amount_btc:.6f} {symbol.split('/')[0]}...")
            # exchange.create_market_sell_order(symbol, amount_btc) # UNCOMMENT TO ENABLE REAL TRADING
            print("SELL Order Simulated (Uncomment code to execute)")
            
    except Exception as e:
        print(f"Error executing trade: {e}")

def run_bot():
    print(f"Starting Live Trading Bot for {SYMBOL}...")
    exchange = get_exchange()
    
    while True:
        try:
            print("\nFetching data...")
            df = fetch_data(exchange, SYMBOL, TIMEFRAME)
            signal = calculate_signal(df)
            
            print(f"Signal: {signal}")
            
            if signal != 'NEUTRAL':
                execute_trade(exchange, SYMBOL, signal, TRADE_AMOUNT_USDT)
            
            # Sleep for a while (e.g., 1 minute) before checking again
            # In a real bot, you'd sync this with the candle close time.
            time.sleep(60) 
            
        except Exception as e:
            print(f"Error in main loop: {e}")
            time.sleep(60)

if __name__ == "__main__":
    # WARNING: This script performs REAL TRADING if lines are uncommented.
    # Use with caution and at your own risk.
    run_bot()

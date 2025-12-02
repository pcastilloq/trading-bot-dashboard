import pandas as pd
import pandas_ta as ta
import os
import sys

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.data_loader import DataLoader

def check_status():
    loader = DataLoader(exchange_id='binance')
    symbol = 'BTC/USDT'
    df = loader.fetch_data(symbol, '1d', limit=100)
    
    if df is None:
        print("Error fetching data")
        return

    # Calculate Indicators
    df['sma_7'] = ta.sma(df['close'], length=7)
    df['sma_30'] = ta.sma(df['close'], length=30)
    bb = ta.bbands(df['close'], length=20, std=2.0)
    df = pd.concat([df, bb], axis=1)
    
    last = df.iloc[-1]
    
    print(f"--- STATUS FOR {symbol} ---")
    print(f"Price: ${last['close']:.2f}")
    print(f"SMA 7: ${last['sma_7']:.2f}")
    print(f"SMA 30: ${last['sma_30']:.2f}")
    
    # Check SMA Cross
    if last['sma_7'] > last['sma_30']:
        print("SMA Status: BULLISH (7 > 30)")
    else:
        print("SMA Status: BEARISH (7 < 30)")
        
    # Check Bollinger
    # Dynamic column names
    upper = last[df.columns[df.columns.str.startswith('BBU')][0]]
    lower = last[df.columns[df.columns.str.startswith('BBL')][0]]
    
    print(f"Upper BB: ${upper:.2f}")
    print(f"Lower BB: ${lower:.2f}")
    
    if last['close'] > upper:
        print("BB Status: OVERBOUGHT (Above Upper)")
    elif last['close'] < lower:
        print("BB Status: OVERSOLD (Below Lower)")
    else:
        print("BB Status: NEUTRAL (Inside Bands)")

if __name__ == "__main__":
    check_status()

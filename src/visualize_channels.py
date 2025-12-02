import pandas as pd
import pandas_ta as ta
import matplotlib.pyplot as plt
import os
import sys

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.data_loader import DataLoader

def visualize_channels():
    # 1. Fetch Data
    loader = DataLoader(exchange_id='binance')
    symbol = 'BTC/USDT'
    print(f"Fetching data for {symbol}...")
    df = loader.fetch_data(symbol, '1d', limit=365)
    
    if df is None:
        print("Failed to fetch data.")
        return

    # 2. Calculate Donchian Channels (20 days)
    # Donchian is simply Max High and Min Low of last N periods
    df['donchian_upper'] = df['high'].rolling(window=20).max()
    df['donchian_lower'] = df['low'].rolling(window=20).min()
    df['donchian_mid'] = (df['donchian_upper'] + df['donchian_lower']) / 2
    
    # 3. Calculate Keltner Channels (EMA 20 +/- 2 ATR)
    # pandas-ta kc returns 3 columns
    kc = ta.kc(df['high'], df['low'], df['close'], length=20, scalar=2)
    # Identify columns (usually KCLe_20_2, KCBe_20_2, KCUe_20_2)
    # We'll just grab by index if names vary, or print them
    
    # 4. Plot
    plt.figure(figsize=(14, 8))
    
    # Subplot 1: Donchian
    plt.subplot(2, 1, 1)
    plt.plot(df.index, df['close'], label='Price', color='black', alpha=0.6)
    plt.plot(df.index, df['donchian_upper'], label='Donchian Upper (20d High)', color='green', linestyle='--')
    plt.plot(df.index, df['donchian_lower'], label='Donchian Lower (20d Low)', color='red', linestyle='--')
    plt.fill_between(df.index, df['donchian_upper'], df['donchian_lower'], color='gray', alpha=0.1)
    plt.title(f"Option A: Donchian Channels (Breakout System)")
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    # Subplot 2: Keltner
    plt.subplot(2, 1, 2)
    plt.plot(df.index, df['close'], label='Price', color='black', alpha=0.6)
    if kc is not None and not kc.empty:
        # Assuming standard names, but let's be safe and use iloc
        # 0: Lower, 1: Basis (Mid), 2: Upper
        plt.plot(df.index, kc.iloc[:, 2], label='Keltner Upper', color='green', linestyle='--')
        plt.plot(df.index, kc.iloc[:, 0], label='Keltner Lower', color='red', linestyle='--')
        plt.fill_between(df.index, kc.iloc[:, 2], kc.iloc[:, 0], color='blue', alpha=0.1)
    plt.title(f"Option B: Keltner Channels (Trend Pullback System)")
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    plt.tight_layout()
    output_path = 'data/channels_comparison.png'
    os.makedirs('data', exist_ok=True)
    plt.savefig(output_path)
    print(f"\nComparison chart saved to {output_path}")

if __name__ == "__main__":
    visualize_channels()

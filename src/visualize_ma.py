import pandas as pd
import pandas_ta as ta
import matplotlib.pyplot as plt
import os
import sys

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.data_loader import DataLoader

def visualize_ma():
    # 1. Fetch Data
    loader = DataLoader(exchange_id='binance')
    symbol = 'BTC/USDT'
    print(f"Fetching data for {symbol}...")
    df = loader.fetch_data(symbol, '1d', limit=730) # 2 years
    
    if df is None:
        print("Failed to fetch data.")
        return

    # 2. Calculate SMAs
    # User requested 7 and 30
    df['sma_7'] = ta.sma(df['close'], length=7)
    df['sma_30'] = ta.sma(df['close'], length=30)
    
    # Standard Regime (Golden Cross)
    df['sma_50'] = ta.sma(df['close'], length=50)
    df['sma_200'] = ta.sma(df['close'], length=200)
    
    # 3. Plot
    plt.figure(figsize=(14, 10))
    
    # Subplot 1: SMA 7 vs 30 (Fast Regime)
    plt.subplot(2, 1, 1)
    plt.plot(df.index, df['close'], label='Price', color='gray', alpha=0.3)
    plt.plot(df.index, df['sma_7'], label='SMA 7 (Fast)', color='green', linewidth=1.5)
    plt.plot(df.index, df['sma_30'], label='SMA 30 (Slow)', color='red', linewidth=1.5)
    
    # Fill between for regime
    plt.fill_between(df.index, df['sma_7'], df['sma_30'], 
                     where=(df['sma_7'] > df['sma_30']), color='green', alpha=0.1, label='Bull (7 > 30)')
    plt.fill_between(df.index, df['sma_7'], df['sma_30'], 
                     where=(df['sma_7'] <= df['sma_30']), color='red', alpha=0.1, label='Bear (7 < 30)')
                     
    plt.title(f"Short-Term Regime: SMA 7 vs SMA 30")
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    # Subplot 2: SMA 50 vs 200 (Long-Term Regime)
    plt.subplot(2, 1, 2)
    plt.plot(df.index, df['close'], label='Price', color='gray', alpha=0.3)
    plt.plot(df.index, df['sma_50'], label='SMA 50', color='orange', linewidth=1.5)
    plt.plot(df.index, df['sma_200'], label='SMA 200', color='blue', linewidth=1.5)
    
    plt.fill_between(df.index, df['sma_50'], df['sma_200'], 
                     where=(df['sma_50'] > df['sma_200']), color='green', alpha=0.1, label='Bull (Golden Cross)')
    plt.fill_between(df.index, df['sma_50'], df['sma_200'], 
                     where=(df['sma_50'] <= df['sma_200']), color='red', alpha=0.1, label='Bear (Death Cross)')
                     
    plt.title(f"Long-Term Regime: SMA 50 vs SMA 200")
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    plt.tight_layout()
    output_path = 'data/ma_comparison.png'
    os.makedirs('data', exist_ok=True)
    plt.savefig(output_path)
    print(f"\nMA chart saved to {output_path}")

if __name__ == "__main__":
    visualize_ma()

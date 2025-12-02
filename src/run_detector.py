import pandas as pd
import matplotlib.pyplot as plt
import os
import sys

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.data_loader import DataLoader
from src.regime_detector import RegimeDetector

def run_detector():
    # 1. Fetch Data (Enough for SMA 200)
    loader = DataLoader(exchange_id='binance')
    symbol = 'BTC/USDT'
    print(f"Fetching data for {symbol}...")
    # We need at least 200 candles for SMA, plus some history for context.
    # Let's fetch 2 years to see regime changes.
    df = loader.fetch_data(symbol, '1d', limit=730)
    
    if df is None:
        print("Failed to fetch data.")
        return

    # 2. Detect Regime
    detector = RegimeDetector(df)
    df_regime = detector.detect_regime()
    current_status = detector.get_current_regime()
    
    print("\n--- Market Regime Report ---")
    print(f"Date: {current_status['timestamp']}")
    print(f"Price: ${current_status['price']:.2f}")
    print(f"SMA 200: ${current_status['sma_200']:.2f}")
    print(f"ADX (14): {current_status['adx']:.2f}")
    print(f"REGIME: {current_status['regime'].upper()}")
    
    if current_status['warning']:
        print(f"⚠️  WARNING: {current_status['warning']} ⚠️")
        
    # 3. Visualize
    # Filter for the last year for better visibility
    plot_df = df_regime.iloc[-365:].copy()
    
    plt.figure(figsize=(14, 7))
    plt.plot(plot_df.index, plot_df['close'], label='Price', color='black', alpha=0.6)
    plt.plot(plot_df.index, plot_df['sma_200'], label='SMA 200', color='blue', linestyle='--')
    
    # Color background based on regime
    # We need to find contiguous blocks of regimes
    # A simple way is to iterate or use fill_between with conditions
    
    y_min = plot_df['close'].min() * 0.9
    y_max = plot_df['close'].max() * 1.1
    
    # Fill Bull
    plt.fill_between(plot_df.index, y_min, y_max, where=(plot_df['regime'] == 'Bull'), 
                     color='green', alpha=0.1, label='Bull Regime')
    
    # Fill Bear
    plt.fill_between(plot_df.index, y_min, y_max, where=(plot_df['regime'] == 'Bear'), 
                     color='red', alpha=0.1, label='Bear Regime')
    
    # Fill Sideways
    plt.fill_between(plot_df.index, y_min, y_max, where=(plot_df['regime'] == 'Sideways'), 
                     color='yellow', alpha=0.1, label='Sideways Regime')

    plt.title(f"Market Regime Detection: {symbol} (Last 1 Year)")
    plt.legend(loc='upper left')
    plt.grid(True, alpha=0.3)
    
    output_path = 'data/regime_chart.png'
    os.makedirs('data', exist_ok=True)
    plt.savefig(output_path)
    print(f"\nChart saved to {output_path}")

if __name__ == "__main__":
    run_detector()

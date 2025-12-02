import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
import sys

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.data_loader import DataLoader
from src.strategies import (
    BuyAndHold, SuperTrendStrategy, EMACrossover, SMACrossover, 
    RSIReversion, BollingerBandsReversion, MACDCrossover, DonchianBreakout
)
from src.backtester import Backtester

def identify_scenarios(df, window_days=90, step_days=30):
    scenarios = {'Bull': [], 'Bear': [], 'Sideways': []}
    
    # Iterate with sliding window
    for i in range(0, len(df) - window_days, step_days):
        window = df.iloc[i : i + window_days]
        if len(window) < window_days:
            continue
            
        start_date = window.index[0]
        end_date = window.index[-1]
        
        start_price = window.iloc[0]['close']
        end_price = window.iloc[-1]['close']
        
        # Calculate return
        period_return = (end_price - start_price) / start_price * 100
        
        # Classify
        if period_return > 20: # Increased threshold for Bull to be more distinct
            scenarios['Bull'].append((start_date, end_date, period_return))
        elif period_return < -20:
            scenarios['Bear'].append((start_date, end_date, period_return))
        elif abs(period_return) < 10:
            scenarios['Sideways'].append((start_date, end_date, period_return))
            
    return scenarios

def run_analysis():
    # 1. Fetch Data (5 years approx)
    loader = DataLoader(exchange_id='binance')
    symbol = 'BTC/USDT'
    print("Fetching historical data (2000 candles)...")
    df = loader.fetch_data(symbol, '1d', limit=2000)
    
    if df is None:
        print("Failed to fetch data.")
        return

    # 2. Identify Scenarios
    print("Identifying scenarios...")
    scenarios = identify_scenarios(df)
    
    selected_windows = {}
    for type_, windows in scenarios.items():
        print(f"Found {len(windows)} {type_} windows.")
        # Sort by magnitude to get clear examples
        if type_ == 'Bull':
            windows.sort(key=lambda x: x[2], reverse=True)
        elif type_ == 'Bear':
            windows.sort(key=lambda x: x[2]) # Most negative first
        else:
            windows.sort(key=lambda x: abs(x[2])) # Closest to 0 first
            
        selected_windows[type_] = windows[:5] # Take top 5

    # 3. Run Backtests
    strategies = [
        BuyAndHold(),
        SMACrossover(fast_period=7, slow_period=30), # Requested Strategy
        BollingerBandsReversion(length=20, std=2.0, use_rsi=False), # Previous Sideways Winner
        SMACrossover(fast_period=50, slow_period=200), # Benchmark Trend
    ]
    
    results = []
    
    print("\n--- Running Batch Backtests ---")
    for scenario_type, windows in selected_windows.items():
        for start, end, period_return in windows:
            print(f"Testing {scenario_type}: {start.date()} to {end.date()} (Mkt: {period_return:.1f}%)")
            
            for strategy in strategies:
                # Pass dates as strings
                bt = Backtester(df, strategy, start_date=str(start), end_date=str(end))
                bt.run()
                res = bt.get_results()
                
                results.append({
                    'Scenario': scenario_type,
                    'Window Start': start.date(),
                    'Window End': end.date(),
                    'Market Return': period_return,
                    'Strategy': strategy.name,
                    'Strategy Return': res['Total Return (%)']
                })

    # 4. Aggregate
    results_df = pd.DataFrame(results)
    os.makedirs('data', exist_ok=True)
    results_df.to_csv('data/scenario_results.csv', index=False)
    
    # Pivot for summary: Average Return per Strategy per Scenario
    summary = results_df.groupby(['Scenario', 'Strategy'])['Strategy Return'].mean().unstack()
    
    # Reorder index to logical order if present
    desired_order = ['Bull', 'Sideways', 'Bear']
    summary = summary.reindex([x for x in desired_order if x in summary.index])
    
    print("\nSummary (Average Return %):")
    print(summary)
    
    # 5. Visualize (Heatmap)
    try:
        fig, ax = plt.subplots(figsize=(14, 8))
        
        # Normalize data for color map (optional, but raw values are fine for now)
        im = ax.imshow(summary.values, cmap='RdYlGn', aspect='auto')
        
        # Create colorbar
        cbar = ax.figure.colorbar(im, ax=ax)
        cbar.ax.set_ylabel("Average Return (%)", rotation=-90, va="bottom")
        
        # Labels
        ax.set_xticks(np.arange(len(summary.columns)))
        ax.set_yticks(np.arange(len(summary.index)))
        ax.set_xticklabels(summary.columns, rotation=45, ha="right")
        ax.set_yticklabels(summary.index)
        
        # Annotate
        for i in range(len(summary.index)):
            for j in range(len(summary.columns)):
                val = summary.values[i, j]
                text_color = "black" if -30 < val < 30 else "white"
                ax.text(j, i, f"{val:.1f}%", ha="center", va="center", color=text_color, fontweight='bold')
                            
        ax.set_title("Average Strategy Return by Market Scenario (90-day windows)")
        plt.tight_layout()
        plt.savefig('data/scenario_heatmap.png')
        print("Heatmap saved to data/scenario_heatmap.png")
    except Exception as e:
        print(f"Error plotting heatmap: {e}")

if __name__ == "__main__":
    run_analysis()

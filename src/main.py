import os
import sys

# Add src to path to allow imports if running from root
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.data_loader import DataLoader
from src.strategies import SMACrossover, RSIReversion, BollingerBandsReversion, MACDCrossover, DonchianBreakout, BuyAndHold, SuperTrendStrategy, EMACrossover
from src.backtester import Backtester
from src.visualizer import plot_data, plot_equity_curves
def main():
    # 1. Setup Data Loader
    loader = DataLoader(exchange_id='binance')
    symbol = 'BTC/USDT'
    timeframe = '1d'
    
    # Dates
    simulation_start = '2024-01-01'
    simulation_end = '2024-06-01'
    
    # Fetch data starting 1 year earlier for warmup (indicators need history)
    fetch_start = '2023-01-01T00:00:00Z' 
    fetch_end = '2024-06-01T00:00:00Z'
    
    # 2. Fetch Data
    print(f"--- Fetching Data for {symbol} ---")
    df = loader.fetch_data(symbol, timeframe, limit=1000, start_date=fetch_start, end_date=fetch_end)
    
    if df is None:
        print("Failed to fetch data. Exiting.")
        return

    # Save data locally
    data_path = os.path.join('data', f"{symbol.replace('/', '_')}_{timeframe}.csv")
    loader.save_data(df, data_path)
    
    # Plot Data
    plot_data(df, symbol, filename=os.path.join('data', f"{symbol.replace('/', '_')}_{timeframe}.png"))
    
    # 3. Define Strategies
    strategies = [
        BuyAndHold(),
        SuperTrendStrategy(length=10, multiplier=3.0),
        EMACrossover(fast_period=50, slow_period=200),
        SMACrossover(fast_period=50, slow_period=200),
        RSIReversion(period=14, buy_threshold=30, sell_threshold=70),
        BollingerBandsReversion(length=20, std=2.0, use_rsi=True),
        BollingerBandsReversion(length=20, std=2.0, use_rsi=False),
        MACDCrossover(fast=12, slow=26, signal=9),
        DonchianBreakout(length=20)
    ]
    
    # 4. Run Backtests
    print(f"\n--- Starting Backtests ({simulation_start} to {simulation_end}) ---")
    equity_curves = {}
    all_results = {}
    
    for strategy in strategies:
        print(f"\nRunning Strategy: {strategy.name}")
        # Pass simulation range to Backtester
        backtester = Backtester(df, strategy, start_date=simulation_start, end_date=simulation_end)
        backtester.run()
        results = backtester.get_results()
        
        # Store equity curve
        equity_curves[strategy.name] = backtester.get_equity_curve()
        all_results[strategy.name] = results
        
        print("Results:")
        for key, value in results.items():
            print(f"  {key}: {value}")
            
    # 5. Plot Comparison
    plot_equity_curves(equity_curves, filename=os.path.join('data', 'strategy_comparison.png'))
    
    # Save text results
    with open('results.txt', 'w') as f:
        for strategy_name, result in all_results.items():
            f.write(f"Strategy: {strategy_name}\n")
            for key, value in result.items():
                f.write(f"  {key}: {value}\n")
            f.write("\n")
    print("Results saved to results.txt")

if __name__ == "__main__":
    main()

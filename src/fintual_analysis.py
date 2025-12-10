import sys
import os
import pandas as pd
import pandas_ta as ta

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.data_loader import DataLoader
from src.regime_detector import RegimeDetector
from src.backtester import Backtester
from src.strategies import SMACrossover, BuyAndHold

def analyze_fintual_funds():
    funds = {
        'Risky Norris': 186,
        'Moderate Pitt': 187,
        'Conservative Clooney': 188,
        'Very Conservative Streep': 15077
    }
    
    loader = DataLoader()
    
    print(f"{'Fund':<25} | {'Regime':<10} | {'Action':<6} | {'SMA vs B&H (1Y)':<20}")
    print("-" * 75)
    
    for name, asset_id in funds.items():
        # Get 2 years for robust backtest, but analyze recent regime
        df = loader.fetch_fintual_data(asset_id, limit=730) 
        
        if df is None or df.empty:
            print(f"{name:<25} | {'ERROR':<10}")
            continue
            
        # 1. Detect Regime (Current)
        detector = RegimeDetector(df)
        df_regime = detector.detect_regime()
        current_regime = detector.get_current_regime()['regime']
        
        # 2. Determine Action (SMA Strategy)
        # Using standard 7/30 crypto parameters as baseline, arguably fast for funds but good for trend
        df['sma_7'] = ta.sma(df['close'], length=7)
        df['sma_30'] = ta.sma(df['close'], length=30)
        
        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        action = "WAIT"
        if last['sma_7'] > last['sma_30']:
            action = "HOLD"
            if prev['sma_7'] <= prev['sma_30']:
                action = "BUY"
        else:
            action = "SELL" # Cash
            
        # 3. Backtest (Last 365 Days)
        # Filter last year
        start_date = df.index[-1] - pd.Timedelta(days=365)
        df_backtest = df[df.index >= start_date].copy()
        
        # Run B&H
        bh_strat = BuyAndHold()
        bt_bh = Backtester(df_backtest, bh_strat)
        bt_bh.run()
        res_bh = bt_bh.get_results()
        
        # Run SMA
        sma_strat = SMACrossover(fast_period=7, slow_period=30)
        bt_sma = Backtester(df_backtest, sma_strat)
        bt_sma.run()
        res_sma = bt_sma.get_results()
        
        # Compare
        ret_bh = res_bh['Total Return (%)']
        ret_sma = res_sma['Total Return (%)']
        comparison = f"{ret_sma:.1f}% vs {ret_bh:.1f}%"
        
        print(f"{name:<25} | {current_regime:<10} | {action:<6} | {comparison:<20}")

if __name__ == "__main__":
    analyze_fintual_funds()

import pandas as pd
from .strategies import Strategy

class Backtester:
    def __init__(self, df: pd.DataFrame, strategy: Strategy, initial_capital: float = 10000.0, commission: float = 0.001, start_date: str = None, end_date: str = None):
        """
        Initialize the Backtester.

        Args:
            df (pd.DataFrame): DataFrame containing OHLCV data.
            strategy (Strategy): The strategy to test.
            initial_capital (float): Initial capital for the backtest.
            commission (float): Commission per trade (e.g., 0.001 for 0.1%).
            start_date (str): Start date for the simulation (YYYY-MM-DD).
            end_date (str): End date for the simulation (YYYY-MM-DD).
        """
        self.df = df
        self.strategy = strategy
        self.initial_capital = initial_capital
        self.commission = commission
        self.start_date = start_date
        self.end_date = end_date
        self.trades = []
        self.equity_curve = []
        self.results = {}

    def run(self):
        """
        Run the backtest simulation.
        """
        # Generate signals (on the full dataset to ensure indicators are correct)
        df_signals = self.strategy.generate_signals(self.df)
        
        # Filter for the simulation period
        if self.start_date:
            df_signals = df_signals[df_signals.index >= pd.to_datetime(self.start_date)]
        if self.end_date:
            df_signals = df_signals[df_signals.index <= pd.to_datetime(self.end_date)]
        
        position = 0 # 0: Out, 1: Long
        entry_price = 0.0
        entry_time = None
        current_capital = self.initial_capital # Cash
        
        self.trades = []
        self.equity_curve = []
        
        for index, row in df_signals.iterrows():
            signal = row['signal']
            price = row['close']
            
            # Buy Signal
            if signal == 1 and position == 0:
                position = 1
                entry_price = price
                entry_time = index
                # We don't deduct cash here to keep simple return calculation logic
                # But for equity curve we need to know we are invested
                
            # Sell Signal
            elif signal == -1 and position == 1:
                position = 0
                exit_price = price
                exit_time = index
                
                # Calculate trade result
                effective_entry = entry_price * (1 + self.commission)
                effective_exit = exit_price * (1 - self.commission)
                
                trade_return = (effective_exit - effective_entry) / effective_entry
                
                # Update capital
                current_capital *= (1 + trade_return)
                
                self.trades.append({
                    'entry_time': entry_time,
                    'exit_time': exit_time,
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'return': trade_return
                })
            
            # Calculate Equity for this step
            if position == 1:
                # Unrealized PnL
                # We assume we invested ALL current_capital
                # So equity = current_capital * (current_price / entry_price) 
                # roughly (ignoring commissions for unrealized view)
                change = (price - entry_price) / entry_price
                equity = current_capital * (1 + change)
            else:
                equity = current_capital
                
            self.equity_curve.append(equity)

        # Force close open position at the end
        if position == 1:
            # We need to close at the last available price in the simulation window
            # df_signals might be a subset, but self.df is full.
            # We should use the last row of df_signals
            if not df_signals.empty:
                exit_price = df_signals.iloc[-1]['close']
                exit_time = df_signals.index[-1]
                
                effective_entry = entry_price * (1 + self.commission)
                effective_exit = exit_price * (1 - self.commission)
                
                trade_return = (effective_exit - effective_entry) / effective_entry
                current_capital *= (1 + trade_return)
                
                self.trades.append({
                    'entry_time': entry_time,
                    'exit_time': exit_time,
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'return': trade_return,
                    'type': 'Force Close'
                })
                
                # Update last equity point
                if self.equity_curve:
                    self.equity_curve[-1] = current_capital

        # Calculate final metrics
        total_return = (current_capital - self.initial_capital) / self.initial_capital * 100
        num_trades = len(self.trades)
        winning_trades = [t for t in self.trades if t['return'] > 0]
        win_rate = (len(winning_trades) / num_trades * 100) if num_trades > 0 else 0.0
        
        self.results = {
            'Total Return (%)': round(total_return, 2),
            'Number of Trades': num_trades,
            'Win Rate (%)': round(win_rate, 2),
            'Final Capital': round(current_capital, 2)
        }

    def get_results(self) -> dict:
        """
        Get the results of the backtest.

        Returns:
            dict: Dictionary containing the calculated metrics.
        """
        return self.results

    def get_equity_curve(self) -> pd.Series:
        """
        Get the equity curve of the backtest.

        Returns:
            pd.Series: Series containing the capital over time.
        """
        # The equity curve corresponds to the simulation period (df_signals)
        # We need to reconstruct the index
        # This is a bit tricky because we didn't store the index in equity_curve list
        # But we know it matches df_signals iteration
        
        # Re-filter to get the index
        df_signals = self.strategy.generate_signals(self.df)
        if self.start_date:
            df_signals = df_signals[df_signals.index >= pd.to_datetime(self.start_date)]
        if self.end_date:
            df_signals = df_signals[df_signals.index <= pd.to_datetime(self.end_date)]
            
        return pd.Series(self.equity_curve, index=df_signals.index)

import pandas as pd
import matplotlib.pyplot as plt
import os

def plot_data(df: pd.DataFrame, symbol: str, filename: str = 'price_chart.png'):
    """
    Plot the closing price of the asset.

    Args:
        df (pd.DataFrame): DataFrame containing 'close' price.
        symbol (str): Symbol name for the title.
        filename (str): Output filename for the plot.
    """
    plt.figure(figsize=(12, 6))
    plt.plot(df.index, df['close'], label='Close Price', color='blue')
    plt.title(f'{symbol} Price History')
    plt.xlabel('Date')
    plt.ylabel('Price')
    plt.legend()
    plt.grid(True)
    
    # Save plot
    # Ensure directory exists
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    plt.savefig(filename)
    print(f"Plot saved to {filename}")
    plt.close()

def plot_equity_curves(equity_curves: dict, filename: str = 'equity_curves.png'):
    """
    Plot the equity curves of multiple strategies.

    Args:
        equity_curves (dict): Dictionary {strategy_name: pd.Series}.
        filename (str): Output filename.
    """
    plt.figure(figsize=(12, 6))
    
    for name, series in equity_curves.items():
        plt.plot(series.index, series, label=name)
        
    plt.title('Strategy Performance Comparison')
    plt.xlabel('Date')
    plt.ylabel('Capital (USDT)')
    plt.legend()
    plt.grid(True)
    
    # Save plot
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    plt.savefig(filename)
    print(f"Equity curves plot saved to {filename}")
    plt.close()

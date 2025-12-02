# Modular Crypto Trading Bot Framework

A modular Python framework for backtesting cryptocurrency trading strategies using `ccxt`, `pandas`, and `pandas-ta`.

## Features

- **Modular Architecture**: Separated concerns for data loading, strategy definition, and backtesting.
- **Data Management**: Fetch historical OHLCV data from Binance and save/load from CSV.
- **Strategy Implementation**: Easy-to-extend `Strategy` base class.
  - Included: SMA Crossover, RSI Reversion.
- **Backtesting**: Simulate trades and calculate key performance metrics (Return, Win Rate).

## Installation

1.  Clone the repository.
2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

## Usage

Run the main script to fetch data and execute backtests:

```bash
python src/main.py
```

## Structure

- `src/data_loader.py`: Data fetching and storage.
- `src/strategies.py`: Trading strategies.
- `src/backtester.py`: Backtesting engine.
- `src/main.py`: Entry point.

import ccxt
import pandas as pd
import os
from typing import Optional

class DataLoader:
    def __init__(self, exchange_id: str = 'binance'):
        """
        Initialize the DataLoader with a specific exchange.
        
        Args:
            exchange_id (str): The ID of the exchange to use (default: 'binance').
        """
        self.exchange_id = exchange_id
        try:
            self.exchange = getattr(ccxt, exchange_id)()
        except AttributeError:
            raise ValueError(f"Exchange '{exchange_id}' not found in ccxt.")

    def fetch_data(self, symbol: str, timeframe: str = '1d', limit: int = 100, start_date: Optional[str] = None, end_date: Optional[str] = None) -> Optional[pd.DataFrame]:
        """
        Fetch historical OHLCV data from the exchange.

        Args:
            symbol (str): The trading pair symbol (e.g., 'BTC/USDT').
            timeframe (str): The timeframe for the data (e.g., '1d', '1h').
            limit (int): The number of candles to fetch.
            start_date (str, optional): Start date in ISO 8601 format (e.g., '2024-01-01T00:00:00Z').
            end_date (str, optional): End date in ISO 8601 format.

        Returns:
            pd.DataFrame: DataFrame containing OHLCV data, or None if an error occurs.
        """
        try:
            since = None
            if start_date:
                since = self.exchange.parse8601(start_date)
                print(f"Fetching data for {symbol} ({timeframe}) starting from {start_date}...")
            else:
                print(f"Fetching {limit} candles for {symbol} ({timeframe}) from {self.exchange_id}...")
            
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit, since=since)
            
            if not ohlcv:
                print("No data fetched.")
                return None

            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            if end_date:
                end_timestamp = pd.to_datetime(end_date)
                if end_timestamp.tzinfo is not None:
                    end_timestamp = end_timestamp.tz_localize(None)
                df = df[df.index <= end_timestamp]
                print(f"Filtered data up to {end_date}. Rows: {len(df)}")
            
            return df
        except Exception as e:
            print(f"Primary fetch failed: {e}. Trying fallback (yfinance)...")
            return self.fetch_data_yfinance(symbol, timeframe, limit, start_date, end_date)

    def fetch_data_yfinance(self, symbol: str, timeframe: str, limit: int, start_date: Optional[str], end_date: Optional[str]) -> Optional[pd.DataFrame]:
        """
        Fallback method to fetch data using yfinance.
        """
        try:
            import yfinance as yf
            
            # Map symbol to yfinance format (BTC/USDT -> BTC-USD)
            yf_symbol = symbol.replace('/', '-').replace('USDT', 'USD')
            
            # Map timeframe
            # yfinance supports: 1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo
            tf_map = {
                '1d': '1d',
                '4h': '1h', # yf doesn't support 4h well, fallback to 1h
                '1h': '1h',
                '15m': '15m'
            }
            interval = tf_map.get(timeframe, '1d')
            
            # Calculate period based on limit if no start_date
            period = "2y" # Default to enough history
            
            print(f"Fetching data from yfinance for {yf_symbol} ({interval})...")
            ticker = yf.Ticker(yf_symbol)
            
            if start_date:
                # yfinance expects YYYY-MM-DD
                start = start_date.split('T')[0]
                end = None
                if end_date:
                    end = end_date.split('T')[0]
                df = ticker.history(interval=interval, start=start, end=end)
            else:
                df = ticker.history(period=period, interval=interval)
                
            if df.empty:
                print("yfinance returned empty data.")
                return None
                
            # Format DataFrame to match ccxt structure
            # yfinance columns: Open, High, Low, Close, Volume, Dividends, Stock Splits
            df = df[['Open', 'High', 'Low', 'Close', 'Volume']]
            df.columns = ['open', 'high', 'low', 'close', 'volume']
            df.index.name = 'timestamp'
            
            # Ensure timezone naive
            if df.index.tz is not None:
                df.index = df.index.tz_localize(None)
                
            # Filter limit if needed (take last N)
            if not start_date and limit:
                df = df.tail(limit)
                
            return df
            
        except Exception as e:
            print(f"yfinance fallback failed: {e}")
            return None

    def save_data(self, df: pd.DataFrame, filename: str) -> None:
        """
        Save the DataFrame to a CSV file.

        Args:
            df (pd.DataFrame): The DataFrame to save.
            filename (str): The path to the file where data will be saved.
        """
        try:
            # Ensure the directory exists
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            df.to_csv(filename)
            print(f"Data saved to {filename}")
        except Exception as e:
            print(f"Error saving data: {e}")

    def load_data(self, filename: str) -> Optional[pd.DataFrame]:
        """
        Load data from a CSV file.

        Args:
            filename (str): The path to the CSV file.

        Returns:
            pd.DataFrame: The loaded DataFrame, or None if file not found or error.
        """
        if not os.path.exists(filename):
            print(f"File {filename} does not exist.")
            return None
        
        try:
            df = pd.read_csv(filename, index_col='timestamp', parse_dates=True)
            print(f"Data loaded from {filename}")
            return df
        except Exception as e:
            print(f"Error loading data: {e}")
            return None

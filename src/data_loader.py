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

    def fetch_fintual_data(self, asset_id: int, limit: int = 365) -> Optional[pd.DataFrame]:
        """
        Fetch historical data from Fintual API for a specific fund.
        
        Args:
            asset_id (int): Fintual Asset ID (e.g., 186 for Risky Norris).
            limit (int): Days of history to fetch.
            
        Returns:
            pd.DataFrame: OHLCV DataFrame (Close=NAV, Volume=0).
        """
        try:
            import requests
            url = f"https://fintual.cl/api/real_assets/{asset_id}/days"
            print(f"Fetching Fintual data for Asset {asset_id}...")
            
            # Note: limit in days isn't directly supported by this endpoint in a simple param,
            # it returns all history or we filter. To keep it simple, we fetch all and filter.
            response = requests.get(url) 
            
            if response.status_code != 200:
                print(f"Error fetching from Fintual: {response.status_code}")
                return None
                
            data = response.json().get('data', [])
            if not data:
                print("No data received from Fintual.")
                return None
                
            # Parse records
            records = []
            for item in data:
                date_str = item.get('attributes', {}).get('date')
                price = item.get('attributes', {}).get('price')
                if date_str and price:
                    records.append({'timestamp': pd.to_datetime(date_str), 'close': float(price)})
            
            if not records:
                return None
                
            df = pd.DataFrame(records)
            df.set_index('timestamp', inplace=True)
            df.sort_index(inplace=True)
            
            # Fill other OHLC columns
            df['open'] = df['close']
            df['high'] = df['close']
            df['low'] = df['close']
            df['volume'] = 0.0
            
            # Filter limit
            if limit:
                df = df.tail(limit)
                
            print(f"Fetched {len(df)} days for Asset {asset_id}.")
            return df
            
        except Exception as e:
            print(f"Fintual fetch failed: {e}")
            return None

    def fetch_holdo_data(self, limit: int = 365) -> Optional[pd.DataFrame]:
        """
        Fetch and synthesize historical data for 'Chile Smart Fund' (Holdo).
        
        Args:
            limit (int): Days of history to fetch.
            
        Returns:
            pd.DataFrame: OHLCV DataFrame (Close=Synthetic Index).
        """
        try:
            import yfinance as yf
            
            # Portfolio Definition
            holdo_portfolio = {
                'CHILE.SN': 0.1520, 'SQM-B.SN': 0.1150, 'FALABELLA.SN': 0.0930,
                'BSANTANDER.SN': 0.0880, 'LTM.SN': 0.0840, 'BCI.SN': 0.0750,
                'COPEC.SN': 0.0560, 'ENELCHILE.SN': 0.0410, 'ANDINA-B.SN': 0.0340,
                'CENCOSUD.SN': 0.0320, 'ORO-BLANCO.SN': 0.0320, 'QUINENCO.SN': 0.0250,
                'AGUAS-A.SN': 0.0230, 'CENCOMALLS.SN': 0.0220, 'ITAUCL.SN': 0.0210,
                'CCU.SN': 0.0180, 'VAPORES.SN': 0.0160, 'MALLPLAZA.SN': 0.0160
            }
            
            # Helper to calculate start date for yfinance
            period = "2y" # Fetch plenty of data to ensure overlap
            
            print("Fetching Holdo Portfolio Components...")
            # Fetch data for all tickers
            tickers = list(holdo_portfolio.keys())
            data = yf.download(tickers, period=period, progress=False, group_by='ticker')
            
            if data.empty:
                print("Holdo: No data fetched.")
                return None
            
            # Synthesize Index
            # Strategy: Calculate Daily Return for each asset -> Weighted Average Return -> Cumulative Product
            
            # 1. Extract Close prices
            closes = pd.DataFrame()
            for ticker in tickers:
                if ticker in data.columns.levels[0]:
                    closes[ticker] = data[ticker]['Close']
                elif 'Close' in data.columns: # Single ticker case (unlikely here but safe)
                    closes[ticker] = data['Close']
            
            # 2. Calculate Daily Returns
            returns = closes.pct_change()
            
            # 3. Calculate Weighted Portfolio Return
            # Ensure index alignment and fillna(0) for missing days (stocks not trading) might be risky.
            # Ideally dropna() to only count days where all (or most) traded.
            returns.dropna(how='all', inplace=True) 
            
            # Note: Weights sum to ~0.957. We should probably re-normalize or assume cash drag.
            # Assuming remaining is cash or minor stocks: let's re-normalize to 1.0 for the equity portion?
            # Or just use raw weights (simulating the actual fund exposure).
            # Let's use raw weights as provided.
            
            portfolio_return = pd.Series(0.0, index=returns.index)
            for ticker, weight in holdo_portfolio.items():
                if ticker in returns.columns:
                    # Fill NaN returns with 0 (assuming flat price if no trade)
                    r = returns[ticker].fillna(0.0)
                    portfolio_return += r * weight
            
            # 4. Construct Index (Start at 100)
            # (1 + r).cumprod() * 100
            portfolio_index = (1 + portfolio_return).cumprod() * 100
            
            # 5. Format to OHLCV
            df = pd.DataFrame(portfolio_index, columns=['close'])
            df.index.name = 'timestamp'
            
            # Remove Timezone
            if df.index.tz is not None:
                df.index = df.index.tz_localize(None)
                
            # Filter Limit
            if limit:
                df = df.tail(limit)
                
            df['open'] = df['close']
            df['high'] = df['close']
            df['low'] = df['close']
            df['volume'] = 0.0
            
            print(f"Synthesized Holdo Index. Rows: {len(df)}")
            return df

        except Exception as e:
            print(f"Holdo fetch failed: {e}")
            import traceback
            traceback.print_exc()
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

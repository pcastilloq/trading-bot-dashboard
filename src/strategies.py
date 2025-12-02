from abc import ABC, abstractmethod
import pandas as pd
import pandas_ta as ta

class Strategy(ABC):
    """
    Abstract base class for trading strategies.
    """
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate trading signals based on the strategy logic.
        
        Args:
            df (pd.DataFrame): The DataFrame containing OHLCV data.
            
        Returns:
            pd.DataFrame: The DataFrame with an added 'signal' column.
                          1 for Buy, -1 for Sell, 0 for Neutral.
        """
        pass

class SMACrossover(Strategy):
    def __init__(self, fast_period: int = 50, slow_period: int = 200):
        super().__init__(f"SMA Crossover ({fast_period}/{slow_period})")
        self.fast_period = fast_period
        self.slow_period = slow_period

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        # Avoid modifying the original dataframe
        df = df.copy()
        
        # Calculate indicators
        df['sma_fast'] = ta.sma(df['close'], length=self.fast_period)
        df['sma_slow'] = ta.sma(df['close'], length=self.slow_period)
        
        # Initialize signal column
        df['signal'] = 0
        
        # Generate signals
        # Buy when fast crosses above slow
        # Sell when fast crosses below slow
        # Note: This is a simple implementation. In a real backtest, you'd check for the crossover event.
        # Here we will hold the position as long as fast > slow (Trend Following)
        # Or we can mark the crossover points specifically.
        # The requirement says "1 para comprar, -1 para vender, 0 neutral".
        # Usually for backtesting signal-based, we want to know the state or the action.
        # Let's implement state-based (1 if Bullish, -1 if Bearish) or Event-based.
        # "Cruce de medias" implies events.
        
        # Let's do event-based signals for clarity in backtesting execution loop
        # But vectorised backtesting usually likes states.
        # The prompt says: "Cada estrategia debe tomar un DataFrame y añadir una columna signal (1 para comprar, -1 para vender, 0 neutral)."
        
        # Let's try to identify the crossover points.
        crossover_bullish = (df['sma_fast'] > df['sma_slow']) & (df['sma_fast'].shift(1) <= df['sma_slow'].shift(1))
        crossover_bearish = (df['sma_fast'] < df['sma_slow']) & (df['sma_fast'].shift(1) >= df['sma_slow'].shift(1))
        
        df.loc[crossover_bullish, 'signal'] = 1
        df.loc[crossover_bearish, 'signal'] = -1
        
        return df

class RSIReversion(Strategy):
    def __init__(self, period: int = 14, buy_threshold: int = 30, sell_threshold: int = 70):
        super().__init__(f"RSI Reversion ({period})")
        self.period = period
        self.buy_threshold = buy_threshold
        self.sell_threshold = sell_threshold

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        
        # Calculate RSI
        df['rsi'] = ta.rsi(df['close'], length=self.period)
        
        df['signal'] = 0
        
        # Buy when RSI < 30
        # Sell when RSI > 70
        # This is mean reversion.
        
        # We can implement this as:
        # Signal 1 when RSI crosses below 30 (or is below 30? usually crosses below or crosses back up?)
        # "Compra RSI < 30" implies condition.
        # Let's assume we buy when it drops below 30 and sell when it goes above 70.
        
        # To avoid spamming signals every candle it is below 30, let's just mark the condition.
        # But the backtester needs to handle it. If I return 1 every row, backtester might buy multiple times.
        # Let's stick to "Signal" as an action trigger.
        
        # Trigger buy when RSI < 30
        # Trigger sell when RSI > 70
        
        # Simple logic:
        df.loc[df['rsi'] < self.buy_threshold, 'signal'] = 1
        df.loc[df['rsi'] > self.sell_threshold, 'signal'] = -1
        
        # Note: This will generate continuous buy signals while RSI < 30.
        # The backtester should handle position management (e.g. only buy if not in position).
        
        return df

class BollingerBandsReversion(Strategy):
    def __init__(self, length: int = 20, std: float = 2.0, use_rsi: bool = True, rsi_period: int = 14, rsi_lower: int = 30, rsi_upper: int = 70):
        name = f"Bollinger ({length}, {std})"
        if use_rsi:
            name += f" + RSI ({rsi_period})"
        super().__init__(name)
        self.length = length
        self.std = std
        self.use_rsi = use_rsi
        self.rsi_period = rsi_period
        self.rsi_lower = rsi_lower
        self.rsi_upper = rsi_upper

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        
        # Calculate Bollinger Bands
        bb = ta.bbands(df['close'], length=self.length, std=self.std)
        
        # Calculate RSI if needed
        if self.use_rsi:
            df['rsi'] = ta.rsi(df['close'], length=self.rsi_period)
        
        # Column names usually: BBL_20_2.0, BBM_20_2.0, BBU_20_2.0
        # We need to find them dynamically or assume default names
        lower_col = f"BBL_{self.length}_{self.std}"
        upper_col = f"BBU_{self.length}_{self.std}"
        
        if lower_col not in bb.columns:
             # Fallback if names are different (sometimes pandas_ta uses different naming)
             lower_col = bb.columns[0]
             upper_col = bb.columns[2]

        df = pd.concat([df, bb], axis=1)
        
        df['signal'] = 0
        
        if self.use_rsi:
            # Buy when price < lower band AND RSI < rsi_lower (Confluence)
            buy_condition = (df['close'] < df[lower_col]) & (df['rsi'] < self.rsi_lower)
            
            # Sell when price > upper band OR RSI > rsi_upper (Take profit or overbought)
            sell_condition = (df['close'] > df[upper_col]) | (df['rsi'] > self.rsi_upper)
        else:
            # Pure Bollinger Reversion
            # Buy when price < lower band
            buy_condition = (df['close'] < df[lower_col])
            
            # Sell when price > upper band
            sell_condition = (df['close'] > df[upper_col])
        
        df.loc[buy_condition, 'signal'] = 1
        df.loc[sell_condition, 'signal'] = -1
        
        return df

class BuyAndHold(Strategy):
    def __init__(self):
        super().__init__("Buy & Hold (Benchmark)")

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        # Always signal buy. The backtester will execute buy on the first candle 
        # because it checks (signal == 1 and position == 0).
        df['signal'] = 1
        
        return df

class SuperTrendStrategy(Strategy):
    def __init__(self, length: int = 10, multiplier: float = 3.0):
        super().__init__(f"SuperTrend ({length}, {multiplier})")
        self.length = length
        self.multiplier = multiplier

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        
        # Calculate SuperTrend
        # pandas_ta returns a DataFrame with columns like SUPERT_7_3.0, SUPERTd_7_3.0, SUPERTl_7_3.0, SUPERTs_7_3.0
        st = ta.supertrend(df['high'], df['low'], df['close'], length=self.length, multiplier=self.multiplier)
        
        # We need the direction column (usually SUPERTd_...)
        # 1 is Bullish, -1 is Bearish
        direction_col = f"SUPERTd_{self.length}_{self.multiplier}"
        
        if direction_col not in st.columns:
             # Fallback
             direction_col = st.columns[1]

        df = pd.concat([df, st], axis=1)
        
        df['signal'] = 0
        
        # Buy when direction changes to 1
        buy_condition = (df[direction_col] == 1) & (df[direction_col].shift(1) == -1)
        
        # Sell when direction changes to -1
        sell_condition = (df[direction_col] == -1) & (df[direction_col].shift(1) == 1)
        
        df.loc[buy_condition, 'signal'] = 1
        df.loc[sell_condition, 'signal'] = -1
        
        return df

class EMACrossover(Strategy):
    def __init__(self, fast_period: int = 50, slow_period: int = 200):
        super().__init__(f"EMA Crossover ({fast_period}/{slow_period})")
        self.fast_period = fast_period
        self.slow_period = slow_period

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        
        # Calculate EMAs
        df['ema_fast'] = ta.ema(df['close'], length=self.fast_period)
        df['ema_slow'] = ta.ema(df['close'], length=self.slow_period)
        
        df['signal'] = 0
        
        # Crossover Logic
        crossover_bullish = (df['ema_fast'] > df['ema_slow']) & (df['ema_fast'].shift(1) <= df['ema_slow'].shift(1))
        crossover_bearish = (df['ema_fast'] < df['ema_slow']) & (df['ema_fast'].shift(1) >= df['ema_slow'].shift(1))
        
        df.loc[crossover_bullish, 'signal'] = 1
        df.loc[crossover_bearish, 'signal'] = -1
        
        return df

class MACDCrossover(Strategy):
    def __init__(self, fast: int = 12, slow: int = 26, signal: int = 9):
        super().__init__(f"MACD Crossover ({fast}/{slow}/{signal})")
        self.fast = fast
        self.slow = slow
        self.signal = signal

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        
        # Calculate MACD
        macd = ta.macd(df['close'], fast=self.fast, slow=self.slow, signal=self.signal)
        
        # Columns: MACD_12_26_9, MACDh_12_26_9, MACDs_12_26_9
        macd_col = f"MACD_{self.fast}_{self.slow}_{self.signal}"
        signal_col = f"MACDs_{self.fast}_{self.slow}_{self.signal}"
        
        df = pd.concat([df, macd], axis=1)
        
        df['signal'] = 0
        
        # Bullish Crossover: MACD crosses above Signal
        crossover_bullish = (df[macd_col] > df[signal_col]) & (df[macd_col].shift(1) <= df[signal_col].shift(1))
        # Bearish Crossover: MACD crosses below Signal
        crossover_bearish = (df[macd_col] < df[signal_col]) & (df[macd_col].shift(1) >= df[signal_col].shift(1))
        
        df.loc[crossover_bullish, 'signal'] = 1
        df.loc[crossover_bearish, 'signal'] = -1
        
        return df

class DonchianBreakout(Strategy):
    def __init__(self, length: int = 20):
        super().__init__(f"Donchian Breakout ({length})")
        self.length = length

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        
        # Calculate Donchian Channels
        # Donchian High = Max High of last N periods
        # Donchian Low = Min Low of last N periods
        # pandas-ta has donchian
        donchian = ta.donchian(df['high'], df['low'], lower_length=self.length, upper_length=self.length)
        
        # Columns: DCL_20_20, DCM_20_20, DCU_20_20
        lower_col = f"DCL_{self.length}_{self.length}"
        upper_col = f"DCU_{self.length}_{self.length}"
        
        df = pd.concat([df, donchian], axis=1)
        
        df['signal'] = 0
        
        # Breakout Strategy:
        # Buy when Close > Previous Upper Channel (Breakout Up)
        # Sell when Close < Previous Lower Channel (Breakout Down)
        # We use shift(1) for channel because we want to break the *previous* high
        
        df.loc[df['close'] > df[upper_col].shift(1), 'signal'] = 1
        df.loc[df['close'] < df[lower_col].shift(1), 'signal'] = -1
        
        return df


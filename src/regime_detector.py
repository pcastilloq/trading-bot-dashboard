import pandas as pd
import pandas_ta as ta

class RegimeDetector:
    def __init__(self, df: pd.DataFrame):
        """
        Initialize the RegimeDetector.

        Args:
            df (pd.DataFrame): DataFrame containing OHLCV data.
        """
        self.df = df.copy()

    def detect_regime(self) -> pd.DataFrame:
        """
        Detect the market regime for each candle.

        Returns:
            pd.DataFrame: DataFrame with 'regime' column.
        """
        # Calculate Indicators
        self.df['sma_200'] = ta.sma(self.df['close'], length=200)
        adx = ta.adx(self.df['high'], self.df['low'], self.df['close'], length=14)
        
        # pandas-ta adx returns three columns: ADX_14, DMP_14, DMN_14
        # We need ADX_14. Check column names.
        adx_col = 'ADX_14'
        if adx is not None and adx_col not in adx.columns:
            adx_col = adx.columns[0] # Fallback
            
        if adx is not None:
             self.df['adx'] = adx[adx_col]
        else:
             self.df['adx'] = float('nan')
        
        # Ensure columns are float to avoid Object/NoneType comparison errors
        # If sma_200 is all None (due to short history), fill with NaN and ensure float dtype
        self.df['sma_200'] = pd.to_numeric(self.df['sma_200'], errors='coerce')
        self.df['adx'] = pd.to_numeric(self.df['adx'], errors='coerce')

        # Logic
        # 1. Trend Direction: Price vs SMA 200
        # 2. Trend Strength: ADX > 25
        
        # Define masks to handle NaNs safely
        # If SMA_200 is NaN, we cannot determine Bull/Bear based on it.
        # We default to 'Unknown' or 'Sideways' if data is missing.
        
        self.df['regime'] = 'Unknown'
        
        # Safe comparison using fillna for boolean logic (treating NaN as False for conditions)
        # Note: We keep NaNs in the data but use fillna ONLY for the condition generation
        # to prevent TypeError. But evaluating (NaN > float) is usually False, not Error.
        # The Error (float > NoneType) happens if the column is Object. pd.to_numeric fixes that.
        
        has_sma = self.df['sma_200'].notna()
        has_adx = self.df['adx'].notna()
        
        # Sideways: ADX < 25 (and we have ADX)
        sideways_mask = has_adx & (self.df['adx'] < 25)
        self.df.loc[sideways_mask, 'regime'] = 'Sideways'
        
        # Bull: Price > SMA 200 & ADX >= 25
        bull_mask = has_sma & has_adx & (self.df['close'] > self.df['sma_200']) & (self.df['adx'] >= 25)
        self.df.loc[bull_mask, 'regime'] = 'Bull'
        
        # Bear: Price < SMA 200 & ADX >= 25
        bear_mask = has_sma & has_adx & (self.df['close'] < self.df['sma_200']) & (self.df['adx'] >= 25)
        self.df.loc[bear_mask, 'regime'] = 'Bear'
        
        return self.df

    def get_current_regime(self) -> dict:
        """
        Get the regime of the latest candle.

        Returns:
            dict: Info about the current regime.
        """
        self.detect_regime()
        last_row = self.df.iloc[-1]
        
        # Check for "Regime Change Warning"
        # If ADX is low (< 20) but rising (slope positive), it might be a breakout.
        adx_slope = 0
        if len(self.df) > 2:
            adx_slope = self.df['adx'].iloc[-1] - self.df['adx'].iloc[-2]
            
        warning = None
        if last_row['adx'] < 20 and adx_slope > 0.5:
            warning = "Potential Breakout (ADX Rising from Low)"
        
        # Bollinger Squeeze Check
        bb = ta.bbands(self.df['close'], length=20, std=2.0)
        # Bandwidth = (Upper - Lower) / Middle * 100
        # pandas-ta returns BBB_20_2.0 (Bandwidth)
        bandwidth_col = 'BBB_20_2.0'
        if bandwidth_col in bb.columns:
            bandwidth = bb[bandwidth_col].iloc[-1]
            if bandwidth < 5.0: # Arbitrary low threshold for BTC
                warning = f"Volatility Squeeze (Bandwidth: {bandwidth:.2f}%)"

        return {
            'timestamp': last_row.name,
            'regime': last_row['regime'],
            'price': last_row['close'],
            'sma_200': last_row['sma_200'],
            'adx': last_row['adx'],
            'warning': warning
        }

import streamlit as st
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
import os
import sys

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.data_loader import DataLoader
from src.regime_detector import RegimeDetector

# Page Config
st.set_page_config(page_title="Trading Bot Dashboard", layout="wide")

# Title
st.title("🤖 Crypto Trading Assistant")

# Sidebar
st.sidebar.header("Configuration")
# Asset Class Selector
asset_class = st.sidebar.selectbox("Asset Class", ["Crypto", "Fintual Funds"])

if asset_class == "Crypto":
    symbol = st.sidebar.text_input("Symbol", "BTC/USDT")
    timeframe = st.sidebar.selectbox("Timeframe", ["1d", "4h", "1h", "15m"], index=0)
    limit = st.sidebar.slider("Lookback Days", 30, 365, 90)
    asset_id = None
else:
    fintual_funds = {
        'Risky Norris': 186,
        'Moderate Pitt': 187,
        'Conservative Clooney': 188,
        'Very Conservative Streep': 15077
    }
    fintual_name = st.sidebar.selectbox("Fund", list(fintual_funds.keys()))
    symbol = fintual_name # For display
    asset_id = fintual_funds[fintual_name]
    timeframe = '1d' # Funds are daily
    limit = st.sidebar.slider("Lookback Days", 30, 730, 90)

if st.sidebar.button("Refresh Data"):
    st.rerun()

# Data Loading
@st.cache_data(ttl=60) # Cache for 1 minute
def load_data(symbol, timeframe, limit, asset_id=None):
    loader = DataLoader(exchange_id='binance')
    if asset_id:
        df = loader.fetch_fintual_data(asset_id, limit=limit)
    else:
        df = loader.fetch_data(symbol, timeframe, limit=limit)
    return df

with st.spinner(f"Fetching data for {symbol}..."):
    df = load_data(symbol, timeframe, limit, asset_id)

if df is None:
    st.error("Failed to fetch data. Please check your connection or symbol.")
else:
    # --- Analysis ---
    # 1. Detect Regime
    detector = RegimeDetector(df)
    df = detector.detect_regime()
    current_regime = detector.get_current_regime()
    
    # 2. Calculate Indicators (SMA 7/30 & Bollinger)
    df['sma_7'] = ta.sma(df['close'], length=7)
    df['sma_30'] = ta.sma(df['close'], length=30)
    
    bb = ta.bbands(df['close'], length=20, std=2.0)
    df = pd.concat([df, bb], axis=1)
    
    # Identify BB columns dynamically
    # pandas-ta returns columns like BBL_20_2.0, BBM_20_2.0, BBU_20_2.0
    # But sometimes names vary. We use index fallback.
    if f"BBL_20_2.0" in bb.columns:
        lower_col = f"BBL_20_2.0"
        mid_col = f"BBM_20_2.0"
        upper_col = f"BBU_20_2.0"
    else:
        # Fallback based on index (Lower, Mid, Upper, Bandwidth, Percent)
        lower_col = bb.columns[0]
        mid_col = bb.columns[1]
        upper_col = bb.columns[2]
    
    # 3. Determine Recommendation
    last_row = df.iloc[-1]
    prev_row = df.iloc[-2]
    
    recommendation = "WAIT"
    reason = "No clear signal"
    color = "gray"
    
    if current_regime['regime'] == 'Bull':
        # Strategy: SMA 7/30
        if last_row['sma_7'] > last_row['sma_30']:
            recommendation = "HOLD / BUY"
            reason = "Bull Regime + SMA 7 > SMA 30"
            color = "green"
            if prev_row['sma_7'] <= prev_row['sma_30']:
                recommendation = "BUY NOW (CROSSOVER)"
                reason = "Bull Regime + SMA 7 Crossed Above SMA 30"
        else:
            recommendation = "SELL / WAIT"
            reason = "Bull Regime but SMA 7 < SMA 30 (Pullback)"
            color = "orange"
            
    elif current_regime['regime'] == 'Sideways':
        # Strategy: Bollinger Reversion
        if last_row['close'] < last_row[lower_col]:
            recommendation = "BUY"
            reason = "Sideways Regime + Price below Lower Band"
            color = "green"
        elif last_row['close'] > last_row[upper_col]:
            recommendation = "SELL"
            reason = "Sideways Regime + Price above Upper Band"
            color = "red"
        else:
            recommendation = "WAIT"
            reason = "Sideways Regime + Price inside Bands"
            color = "yellow"
            
    elif current_regime['regime'] == 'Bear':
        # Strategy: Cash
        recommendation = "STAY IN CASH"
        reason = "Bear Regime. Protect Capital."
        color = "red"

    # --- UI Layout ---
    
    # Top Metrics
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Price", f"${last_row['close']:.2f}")
    col2.metric("Regime", current_regime['regime'].upper(), delta=current_regime['warning'], delta_color="inverse")
    col3.metric("ADX Strength", f"{last_row['adx']:.1f}")
    col4.markdown(f"**Action:** :{color}[{recommendation}]")
    
    st.info(f"💡 **Reasoning:** {reason}")

    # Charts
    st.subheader("Market Analysis")
    
    # Main Chart
    fig = go.Figure()
    
    # Candlestick
    fig.add_trace(go.Candlestick(x=df.index,
                open=df['open'], high=df['high'],
                low=df['low'], close=df['close'],
                name='OHLC'))
    
    # SMAs
    fig.add_trace(go.Scatter(x=df.index, y=df['sma_7'], line=dict(color='#00FF00', width=3), name='SMA 7 (Fast)')) # Bright Green
    fig.add_trace(go.Scatter(x=df.index, y=df['sma_30'], line=dict(color='#FF0000', width=3), name='SMA 30 (Slow)')) # Bright Red
    fig.add_trace(go.Scatter(x=df.index, y=df['sma_200'], line=dict(color='#0000FF', width=4, dash='dash'), name='SMA 200')) # Blue
    
    # Bollinger (only if Sideways or user wants)
    if st.checkbox("Show Bollinger Bands", value=(current_regime['regime']=='Sideways')):
        fig.add_trace(go.Scatter(x=df.index, y=df[upper_col], line=dict(color='#006400', width=1.5), name='Upper BB')) # Dark Green
        fig.add_trace(go.Scatter(x=df.index, y=df[lower_col], line=dict(color='#800020', width=1.5), name='Lower BB')) # Burgundy
    
    fig.update_layout(title=f"{symbol} Price Action", xaxis_title="Date", yaxis_title="Price", height=600, template='plotly_white')
    st.plotly_chart(fig, width="stretch")
    
    # Indicator Chart (ADX)
    st.subheader("Regime Indicators")
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=df.index, y=df['adx'], line=dict(color='purple', width=3), name='ADX'))
    fig2.add_hline(y=25, line_dash="dash", line_color="black", annotation_text="Trend Threshold (25)")
    fig2.update_layout(title="Trend Strength (ADX)", height=300, template='plotly_white')
    st.plotly_chart(fig2, width="stretch")
    
    # Raw Data
    with st.expander("View Raw Data"):
        st.dataframe(df.tail(10))

"""
Technical Indicators module for IB RSI Scanner
Handles RSI, ATR, and other technical analysis calculations
"""

import pandas as pd
import ta
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import RSI_WINDOW, ATR_WINDOW, RSI_LOOKBACK_DAYS, OVEREXTENDED_LOOKBACK_DAYS, OVEREXTENDED_ATR_MULTIPLIER


def check_overextended(df: pd.DataFrame, atr_value: float, 
                      lookback_days: int = 5, atr_multiplier: int = 5) -> dict:
    """
    Check if current price is overextended from recent swing low
    Returns detailed measurement structure with all calculations
    
    Args:
        df: DataFrame with OHLCV data (DAILY BARS)
        atr_value: Current ATR value
        lookback_days: Days to look back for swing low (default: 5)
        atr_multiplier: ATR multiplier for threshold (default: 5)
        
    Returns:
        dict: Complete measurement structure with:
            - is_overextended: True/False status
            - swing_low: Lowest low from last N days
            - atr: ATR value
            - atr_contribution: ATR × multiplier
            - threshold: Swing low + ATR contribution
            - current_price: Current close price
            - distance_from_threshold: Dollar amount above/below
            - distance_pct: Percentage above/below threshold
            - proximity_pct: How close to threshold (0-100%)
            - swing_high: Highest high from last N days
            - price_range: Swing high - swing low
    """
    # Initialize empty result structure
    result = {
        'is_overextended': False,
        'swing_low': None,
        'swing_high': None,
        'atr': atr_value,
        'atr_contribution': None,
        'threshold': None,
        'current_price': None,
        'distance_from_threshold': None,
        'distance_pct': None,
        'proximity_pct': None,
        'price_range': None,
        'calculation_valid': False
    }
    
    if df.empty or len(df) < lookback_days + 1:
        return result
    
    # Get recent data (last N trading days + current day) - DAILY BARS
    recent_data = df.iloc[-(lookback_days + 1):]
    
    if recent_data.empty:
        return result
    
    # Find swing low/high from the previous N trading days (exclude current day)
    prev_days_data = recent_data.iloc[:-1]  # Exclude current day
    swing_low = prev_days_data['low'].min()
    swing_high = prev_days_data['high'].max()
    
    # Get current price (most recent close)
    current_price = df['close'].iloc[-1]
    
    # Populate basic values
    result['swing_low'] = float(swing_low)
    result['swing_high'] = float(swing_high)
    result['current_price'] = float(current_price)
    result['price_range'] = float(swing_high - swing_low)
    
    # Calculate overextended threshold
    if atr_value is None or pd.isna(atr_value):
        return result
    
    atr_contribution = atr_value * atr_multiplier
    overextended_threshold = swing_low + atr_contribution
    
    # Calculate distances
    distance_from_threshold = current_price - overextended_threshold
    distance_pct = (distance_from_threshold / overextended_threshold) * 100
    
    # Calculate proximity (how close to threshold as percentage)
    # 100% = at or above threshold, 0% = at swing low
    if overextended_threshold > swing_low:
        proximity_pct = ((current_price - swing_low) / (overextended_threshold - swing_low)) * 100
        proximity_pct = max(0, min(100, proximity_pct))  # Clamp to 0-100
    else:
        proximity_pct = 0
    
    # Check if overextended
    is_overextended = current_price > overextended_threshold
    
    # Populate complete result
    result.update({
        'is_overextended': bool(is_overextended),
        'atr_contribution': float(atr_contribution),
        'threshold': float(overextended_threshold),
        'distance_from_threshold': float(distance_from_threshold),
        'distance_pct': float(distance_pct),
        'proximity_pct': float(proximity_pct),
        'calculation_valid': True
    })
    
    return result


def compute_indicators(df: pd.DataFrame) -> tuple:
    """
    Compute RSI and ATR indicators for price data
    
    Args:
        df: DataFrame with columns: date, open, high, low, close, volume
        
    Returns:
        tuple: (rsi_series, atr_series, (latest_rsi, latest_atr))
    """
    if df.empty or len(df) < max(RSI_WINDOW, ATR_WINDOW) + 1:
        return None, None, (None, None)
    
    close = df['close']
    high = df['high']
    low = df['low']

    # RSI calculation
    rsi_series = ta.momentum.RSIIndicator(close, window=RSI_WINDOW).rsi()

    # ATR calculation
    atr_series = ta.volatility.AverageTrueRange(
        high=high, 
        low=low, 
        close=close, 
        window=ATR_WINDOW
    ).average_true_range()

    # Get latest values
    latest_rsi = rsi_series.iloc[-1] if not rsi_series.empty else None
    latest_atr = atr_series.iloc[-1] if not atr_series.empty else None
    
    return rsi_series, atr_series, (latest_rsi, latest_atr)


def check_rsi_extremes(rsi_series: pd.Series, lookback_days: int = RSI_LOOKBACK_DAYS, 
                      high_threshold: float = 90, low_threshold: float = 10) -> tuple:
    """
    Check if RSI hit extreme values in recent trading days
    
    Args:
        rsi_series: RSI time series
        lookback_days: Number of recent days to check
        high_threshold: Overbought threshold
        low_threshold: Oversold threshold
        
    Returns:
        tuple: (hit_high, hit_low, max_rsi, min_rsi)
    """
    if rsi_series.empty or len(rsi_series) < lookback_days:
        return False, False, None, None
    
    # Get recent RSI values (drop NaN values first)
    recent_rsi = rsi_series.dropna().iloc[-lookback_days:]
    
    if recent_rsi.empty:
        return False, False, None, None
    
    max_rsi = recent_rsi.max()
    min_rsi = recent_rsi.min()
    
    hit_high = max_rsi >= high_threshold
    hit_low = min_rsi <= low_threshold
    
    return hit_high, hit_low, max_rsi, min_rsi


def calculate_volatility_metrics(df: pd.DataFrame) -> dict:
    """
    Calculate additional volatility metrics
    
    Args:
        df: DataFrame with OHLCV data
        
    Returns:
        dict: Dictionary of volatility metrics
    """
    if df.empty or len(df) < 20:
        return {}
    
    close = df['close']
    high = df['high']
    low = df['low']
    
    # Calculate returns
    returns = close.pct_change().dropna()
    
    # Basic volatility metrics
    metrics = {
        'volatility_20d': returns.rolling(20).std() * (252**0.5) if len(returns) >= 20 else None,
        'avg_true_range_20d': ta.volatility.AverageTrueRange(high, low, close, window=20).average_true_range(),
        'price_range_pct': ((high.iloc[-1] - low.iloc[-1]) / close.iloc[-1] * 100) if not close.empty else None
    }
    
    # Bollinger Bands
    if len(close) >= 20:
        bb = ta.volatility.BollingerBands(close, window=20, window_dev=2)
        metrics.update({
            'bb_upper': bb.bollinger_hband().iloc[-1],
            'bb_lower': bb.bollinger_lband().iloc[-1],
            'bb_width': bb.bollinger_wband().iloc[-1],
            'bb_position': ((close.iloc[-1] - bb.bollinger_lband().iloc[-1]) / 
                          (bb.bollinger_hband().iloc[-1] - bb.bollinger_lband().iloc[-1]))
        })
    
    return {k: v for k, v in metrics.items() if v is not None}


def get_momentum_indicators(df: pd.DataFrame) -> dict:
    """
    Calculate momentum indicators
    
    Args:
        df: DataFrame with OHLCV data
        
    Returns:
        dict: Dictionary of momentum indicators
    """
    if df.empty or len(df) < 14:
        return {}
    
    close = df['close']
    high = df['high']
    low = df['low']
    volume = df['volume']
    
    indicators = {}
    
    # RSI variants
    if len(close) >= 14:
        indicators['rsi_14'] = ta.momentum.RSIIndicator(close, window=14).rsi().iloc[-1]
    
    if len(close) >= 9:
        indicators['rsi_9'] = ta.momentum.RSIIndicator(close, window=9).rsi().iloc[-1]
    
    # MACD
    if len(close) >= 26:
        macd = ta.trend.MACD(close)
        indicators.update({
            'macd': macd.macd().iloc[-1],
            'macd_signal': macd.macd_signal().iloc[-1],
            'macd_histogram': macd.macd_diff().iloc[-1]
        })
    
    # Stochastic
    if len(df) >= 14:
        stoch = ta.momentum.StochasticOscillator(high, low, close, window=14, smooth_window=3)
        indicators.update({
            'stoch_k': stoch.stoch().iloc[-1],
            'stoch_d': stoch.stoch_signal().iloc[-1]
        })
    
    # Williams %R
    if len(df) >= 14:
        indicators['williams_r'] = ta.momentum.WilliamsRIndicator(high, low, close, lbp=14).williams_r().iloc[-1]
    
    return {k: v for k, v in indicators.items() if pd.notna(v)}


def generate_signal_summary(rsi_value: float, atr_value: float, hit_high: bool, hit_low: bool) -> dict:
    """
    Generate a summary of trading signals
    
    Args:
        rsi_value: Current RSI value
        atr_value: Current ATR value
        hit_high: Whether RSI hit overbought recently
        hit_low: Whether RSI hit oversold recently
        
    Returns:
        dict: Signal summary
    """
    signals = {
        'rsi_signal': 'neutral',
        'volatility_signal': 'normal',
        'overall_signal': 'neutral',
        'confidence': 'medium'
    }
    
    # RSI signals
    if rsi_value is not None:
        if rsi_value >= 70:
            signals['rsi_signal'] = 'overbought'
        elif rsi_value <= 30:
            signals['rsi_signal'] = 'oversold'
        elif hit_high:
            signals['rsi_signal'] = 'extreme_overbought'
        elif hit_low:
            signals['rsi_signal'] = 'extreme_oversold'
    
    # Volatility signals
    if atr_value is not None:
        # This would need historical ATR context for proper classification
        signals['volatility_signal'] = 'normal'  # Placeholder
    
    # Overall signal combination
    if hit_high or signals['rsi_signal'] == 'extreme_overbought':
        signals['overall_signal'] = 'strong_sell'
        signals['confidence'] = 'high'
    elif hit_low or signals['rsi_signal'] == 'extreme_oversold':
        signals['overall_signal'] = 'strong_buy'
        signals['confidence'] = 'high'
    elif signals['rsi_signal'] == 'overbought':
        signals['overall_signal'] = 'sell'
        signals['confidence'] = 'medium'
    elif signals['rsi_signal'] == 'oversold':
        signals['overall_signal'] = 'buy'
        signals['confidence'] = 'medium'
    
    return signals
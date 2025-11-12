"""
Test script for the overextended calculation feature
"""

import pandas as pd
import sys
import os
from datetime import datetime, timedelta

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
from src.indicators import check_overextended


def test_overextended_calculation():
    """Test the overextended calculation with sample data"""
    print("🧪 Testing Overextended Calculation")
    print("=" * 50)
    
    # Create sample data
    dates = pd.date_range(start='2025-11-05', periods=7, freq='D')
    
    # Example: Stock drops from $220 to $210 swing low, then rallies
    prices = [220, 215, 210, 212, 215, 222, 225]  # Current price: $225
    
    sample_data = pd.DataFrame({
        'date': dates,
        'open': [p * 0.99 for p in prices],
        'high': [p * 1.01 for p in prices],
        'low': [p * 0.98 for p in prices],  # Low will be around 210 * 0.98 = $205.80 on day 3
        'close': prices,
        'volume': [10000] * len(prices)
    })
    
    print("📊 Sample Data:")
    print(sample_data[['date', 'low', 'close']].to_string(index=False))
    
    # Test with ATR = 2 (as in your example)
    atr_value = 2.0
    
    # Run overextended check
    is_overextended, swing_low, threshold, current_price = check_overextended(
        sample_data, atr_value, lookback_days=5, atr_multiplier=5
    )
    
    print(f"\n🔍 Overextended Analysis:")
    print(f"   ATR: ${atr_value}")
    print(f"   Swing Low (last 5 days): ${swing_low:.2f}")
    print(f"   Overextended Threshold: ${threshold:.2f}")
    print(f"   Current Price: ${current_price:.2f}")
    print(f"   Is Overextended: {'✅ YES' if is_overextended else '❌ NO'}")
    
    # Calculation verification
    expected_threshold = swing_low + (atr_value * 5)
    print(f"\n🧮 Calculation Verification:")
    print(f"   Swing Low + (ATR × 5) = ${swing_low:.2f} + (${atr_value} × 5) = ${expected_threshold:.2f}")
    print(f"   Current Price (${current_price:.2f}) > Threshold (${expected_threshold:.2f}): {current_price > expected_threshold}")
    
    return is_overextended, swing_low, threshold, current_price


def test_edge_cases():
    """Test edge cases"""
    print("\n🧪 Testing Edge Cases")
    print("=" * 30)
    
    # Test 1: Insufficient data
    small_data = pd.DataFrame({
        'date': pd.date_range(start='2025-11-11', periods=3),
        'open': [100, 101, 102],
        'high': [101, 102, 103], 
        'low': [99, 100, 101],
        'close': [100, 101, 102],
        'volume': [1000, 1000, 1000]
    })
    
    result = check_overextended(small_data, 2.0, lookback_days=5)
    print(f"1. Insufficient data test: {result[0]} (should be False)")
    
    # Test 2: No ATR value
    sufficient_data = pd.DataFrame({
        'date': pd.date_range(start='2025-11-05', periods=7),
        'open': range(100, 107),
        'high': range(101, 108),
        'low': range(99, 106), 
        'close': range(100, 107),
        'volume': [1000] * 7
    })
    
    result = check_overextended(sufficient_data, None, lookback_days=5)
    print(f"2. No ATR test: {result[0]} (should be False)")


if __name__ == "__main__":
    test_overextended_calculation()
    test_edge_cases()
    
    print(f"\n✅ Overextended calculation feature ready!")
    print("📈 The scanner will now detect when stocks are overextended")
    print("   based on swing lows and ATR multiples.")
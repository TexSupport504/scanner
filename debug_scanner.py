"""
Debug script to identify scanner issues
"""

import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

print("🔍 Debugging Scanner Issues")
print("=" * 40)

# Test imports
try:
    from src.indicators import compute_indicators, check_rsi_extremes, check_overextended
    print("✅ Indicator imports successful")
except Exception as e:
    print(f"❌ Indicator import error: {e}")

try:
    import ta
    print("✅ TA library import successful")
    print(f"   TA version: {ta.__version__ if hasattr(ta, '__version__') else 'unknown'}")
except Exception as e:
    print(f"❌ TA library import error: {e}")

# Test basic TA functionality
try:
    import pandas as pd
    import numpy as np
    
    # Create simple test data
    test_data = pd.DataFrame({
        'date': pd.date_range('2025-11-01', periods=20),
        'open': np.random.uniform(100, 110, 20),
        'high': np.random.uniform(105, 115, 20),
        'low': np.random.uniform(95, 105, 20),
        'close': np.random.uniform(100, 110, 20),
        'volume': np.random.randint(1000, 10000, 20)
    })
    
    print("✅ Test data created successfully")
    
    # Test RSI calculation
    from ta.momentum import RSIIndicator
    rsi_calc = RSIIndicator(test_data['close'], window=14)
    rsi_values = rsi_calc.rsi()
    print(f"✅ RSI calculation successful, last value: {rsi_values.iloc[-1]:.2f}")
    
    # Test ATR calculation  
    from ta.volatility import AverageTrueRange
    atr_calc = AverageTrueRange(test_data['high'], test_data['low'], test_data['close'], window=14)
    atr_values = atr_calc.average_true_range()
    print(f"✅ ATR calculation successful, last value: {atr_values.iloc[-1]:.2f}")
    
    # Test our compute_indicators function
    rsi_series, atr_series, (latest_rsi, latest_atr) = compute_indicators(test_data)
    print(f"✅ compute_indicators successful: RSI={latest_rsi:.2f}, ATR={latest_atr:.2f}")
    
    # Test overextended calculation
    is_overextended, swing_low, threshold, current_price = check_overextended(test_data, latest_atr)
    print(f"✅ check_overextended successful: overextended={is_overextended}")
    
except Exception as e:
    print(f"❌ TA functionality error: {e}")
    import traceback
    traceback.print_exc()

print("\n🔍 Testing scanner module import...")
try:
    from src.scanner import RSIScanner
    print("✅ Scanner import successful")
    
    # Test scanner initialization
    scanner = RSIScanner()
    print("✅ Scanner initialization successful")
    
except Exception as e:
    print(f"❌ Scanner error: {e}")
    import traceback
    traceback.print_exc()

print("\n📊 Analysis Complete!")
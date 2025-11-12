"""
Verify that we're getting real market data from Interactive Brokers
"""

from src.scanner import RSIScanner
import yfinance as yf
from datetime import datetime

def verify_data():
    print("🔍 VERIFYING REAL MARKET DATA")
    print("=" * 50)
    
    scanner = RSIScanner()
    
    if not scanner.connect_to_ib():
        print("❌ Could not connect to IB")
        return
    
    # Test symbols
    test_symbols = ['AAPL', 'CAH', 'MSFT']
    
    for symbol in test_symbols:
        print(f"\n📊 {symbol}:")
        
        # Get IB data
        result = scanner.scan_symbol(symbol)
        ib_price = result.get('current_price', 0)
        ib_rsi = result.get('latest_rsi', 0)
        
        print(f"   IB Price: ${ib_price:.2f}")
        print(f"   IB RSI:   {ib_rsi:.1f}")
        
        # Cross-check with Yahoo Finance for price verification
        try:
            ticker = yf.Ticker(symbol)
            yf_data = ticker.history(period="1d")
            if not yf_data.empty:
                yf_price = yf_data['Close'].iloc[-1]
                price_diff = abs(ib_price - yf_price)
                price_diff_pct = (price_diff / yf_price) * 100
                
                print(f"   YF Price: ${yf_price:.2f}")
                print(f"   Diff:     ${price_diff:.2f} ({price_diff_pct:.1f}%)")
                
                if price_diff_pct < 5:  # Within 5%
                    print("   ✅ Prices match - REAL DATA CONFIRMED")
                else:
                    print("   ⚠️  Large price difference")
            else:
                print("   ❌ No Yahoo Finance data")
                
        except Exception as e:
            print(f"   ❌ YF Error: {e}")
    
    scanner.disconnect_from_ib()
    
    print(f"\n🕐 Data timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("💡 This data is pulled live from Interactive Brokers API")

if __name__ == "__main__":
    verify_data()
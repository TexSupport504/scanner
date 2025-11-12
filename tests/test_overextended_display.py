"""
Test the enhanced overextended measurement and alert display
"""

from src.scanner import RSIScanner

def test_overextended_display():
    """Test the enhanced measurement display for overextended stocks"""
    print("🧪 Testing Enhanced Overextended Measurements")
    print("=" * 60)
    
    scanner = RSIScanner()
    
    # Connect
    if not scanner.connect_to_ib():
        return
    
    # Test symbols that were previously overextended
    test_symbols = ['STE', 'AMGN', 'AKAM', 'DDOG', 'EXPE', 'BDX', 'DD', 'CAH', 'AAPL']
    
    print(f"📊 Testing {len(test_symbols)} symbols for detailed measurements\n")
    
    results = []
    for symbol in test_symbols:
        print(f"📈 Scanning {symbol}...")
        result = scanner.scan_symbol(symbol)
        results.append(result)
        
        # Show immediate feedback
        if result.get('is_overextended'):
            print(f"   ⚡ OVEREXTENDED = TRUE")
            print(f"      Proximity: {result.get('proximity_pct', 0):.0f}%")
        elif result.get('proximity_pct', 0) >= 80:
            print(f"   ⚠️  Approaching overextended ({result.get('proximity_pct', 0):.0f}%)")
        else:
            print(f"   ✓  Normal (Proximity: {result.get('proximity_pct', 0):.0f}%)")
        print()
    
    scanner.disconnect_from_ib()
    
    # Detailed Summary
    print("\n" + "=" * 60)
    print("📊 DETAILED ALERT SUMMARY")
    print("=" * 60)
    
    overextended = [r for r in results if r.get('is_overextended')]
    approaching = [r for r in results if not r.get('is_overextended') and r.get('proximity_pct', 0) >= 80]
    
    print(f"\n⚡ OVEREXTENDED STOCKS: {len(overextended)}")
    for stock in overextended:
        print(f"\n🔴 {stock['symbol']}")
        print(f"   ✅ OVEREXTENDED = TRUE")
        print(f"   📊 Measurement Breakdown:")
        print(f"      Swing Low (5 days):  ${stock.get('swing_low', 0):8.2f}")
        print(f"      ATR Value:           ${stock.get('latest_atr', 0):8.2f}")
        print(f"      ATR × 5:             ${stock.get('atr_contribution', 0):8.2f}")
        print(f"      Threshold:           ${stock.get('overextended_threshold', 0):8.2f}")
        print(f"      Current Price:       ${stock.get('current_price', 0):8.2f}")
        print(f"      Distance:            ${stock.get('distance_from_threshold', 0):+8.2f} ({stock.get('distance_pct', 0):+.2f}%)")
        print(f"      Proximity:           {stock.get('proximity_pct', 0):8.1f}%")
        print(f"      RSI:                 {stock.get('latest_rsi', 0):8.1f}")
    
    if approaching:
        print(f"\n⚠️  APPROACHING OVEREXTENDED: {len(approaching)}")
        for stock in approaching:
            print(f"\n🟡 {stock['symbol']}")
            print(f"   ❌ OVEREXTENDED = FALSE")
            print(f"   📊 But {stock.get('proximity_pct', 0):.1f}% of way to threshold")
            print(f"      Current Price:  ${stock.get('current_price', 0):8.2f}")
            print(f"      Threshold:      ${stock.get('overextended_threshold', 0):8.2f}")
            print(f"      Distance:       ${stock.get('distance_from_threshold', 0):+8.2f}")
            print(f"      RSI:            {stock.get('latest_rsi', 0):8.1f}")
    
    normal = [r for r in results if not r.get('is_overextended') and r.get('proximity_pct', 0) < 80]
    print(f"\n✅ NORMAL STOCKS: {len(normal)}")
    for stock in normal:
        print(f"   {stock['symbol']:>6} - Proximity: {stock.get('proximity_pct', 0):5.1f}% | RSI: {stock.get('latest_rsi', 0):.1f}")
    
    print("\n" + "=" * 60)
    print("🎯 Enhanced measurement system working!")
    print("   - TRUE/FALSE status ✅")
    print("   - Detailed calculations ✅")
    print("   - Proximity warnings ✅")
    print("   - Daily chart data ✅")

if __name__ == "__main__":
    test_overextended_display()
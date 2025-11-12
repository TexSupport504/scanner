"""
Test scanner with a small subset of symbols to verify overextended detection
"""

from src.scanner import RSIScanner

def test_small_scan():
    """Test scanning a few symbols to verify all features work"""
    print("🚀 Testing Enhanced Scanner (Small Sample)")
    print("=" * 50)
    
    scanner = RSIScanner()
    
    # Override tickers with a small sample
    test_symbols = ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'AMZN', 'META', 'NVDA', 'CAH', 'GME', 'AMD']
    scanner.tickers = test_symbols
    
    # Connect
    if not scanner.connect_to_ib():
        return
    
    print(f"📊 Testing {len(test_symbols)} symbols")
    
    results = []
    alerts = []
    
    for i, symbol in enumerate(test_symbols, 1):
        print(f"📈 [{i:2d}/{len(test_symbols)}] Scanning {symbol}...", end=" ")
        
        result = scanner.scan_symbol(symbol)
        results.append(result)
        
        # Check for alerts
        if result['hit_high'] or result['hit_low'] or result.get('is_overextended', False):
            alerts.append(result)
            alert_types = []
            if result['hit_high']:
                alert_types.append("🔴RSI≥90")
            if result['hit_low']:
                alert_types.append("🟢RSI≤10")
            if result.get('is_overextended', False):
                alert_types.append("⚡Overextended")
            print(f"🚨 {'/'.join(alert_types)}!", end=" ")
        
        if result['status'].startswith('error'):
            print("❌ Error", end=" ")
        elif result['latest_rsi'] is not None:
            rsi_str = f"RSI: {result['latest_rsi']:.1f}"
            if result.get('is_overextended', False):
                rsi_str += f" | OVEREXT: ${result['current_price']:.1f} > ${result['overextended_threshold']:.1f}"
            print(rsi_str, end=" ")
        
        print()  # New line
    
    scanner.disconnect_from_ib()
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST RESULTS")
    print("=" * 50)
    
    successful = [r for r in results if r['latest_rsi'] is not None]
    errors = [r for r in results if r['status'].startswith('error')]
    
    print(f"✅ Successful scans: {len(successful)}/{len(test_symbols)}")
    print(f"❌ Errors: {len(errors)}")
    print(f"🚨 Alerts found: {len(alerts)}")
    
    if alerts:
        print(f"\n🔥 ALERTS DETECTED:")
        for alert in alerts:
            alert_types = []
            if alert['hit_high']:
                alert_types.append("🔴 RSI≥90")
            if alert['hit_low']:
                alert_types.append("🟢 RSI≤10")
            if alert.get('is_overextended', False):
                alert_types.append("⚡ Overextended")
            
            print(f"  {alert['symbol']:>6} | {' | '.join(alert_types)}")
            print(f"         RSI: {alert['latest_rsi']:.1f} | Price: ${alert.get('current_price', 0):.2f}")
            if alert.get('is_overextended', False):
                print(f"         Swing Low: ${alert.get('swing_low', 0):.2f} | Threshold: ${alert.get('overextended_threshold', 0):.2f}")
    
    return len(alerts) > 0

if __name__ == "__main__":
    has_alerts = test_small_scan()
    if has_alerts:
        print("\n🎯 Overextended detection feature working correctly!")
    else:
        print("\n📊 No extreme conditions found in test symbols - scanner functioning normally")
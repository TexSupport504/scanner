"""
Run the complete Enhanced IB RSI Scanner on all S&P 500 stocks
"""

from src.scanner import RSIScanner

def main():
    print("🚀 ENHANCED IB RSI SCANNER")
    print("📊 Scanning S&P 500 for:")
    print("   🔴 RSI ≥ 90 (Extremely Overbought)")
    print("   🟢 RSI ≤ 10 (Extremely Oversold)")
    print("   ⚡ Overextended (Price > Swing Low + 5×ATR)")
    print("=" * 60)
    
    scanner = RSIScanner()
    
    # The run_scan method already does everything:
    # - Connects to IB
    # - Fetches S&P 500 tickers
    # - Scans all stocks
    # - Shows results
    # - Saves to database
    scanner.run_scan()

if __name__ == "__main__":
    main()

if __name__ == "__main__":
    main()
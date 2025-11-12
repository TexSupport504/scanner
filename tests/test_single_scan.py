"""
Quick test of scanner with just one symbol to see the specific error
"""

from src.scanner import RSIScanner

def test_single_symbol():
    """Test scanning just one symbol to see the specific error"""
    print("🧪 Testing Single Symbol Scan")
    print("=" * 40)
    
    scanner = RSIScanner()
    
    # Connect to IB
    if not scanner.connect_to_ib():
        return
    
    # Test with AAPL
    print("Testing AAPL scan...")
    result = scanner.scan_symbol('AAPL')
    
    print("Result:")
    for key, value in result.items():
        print(f"  {key}: {value}")
    
    scanner.disconnect_from_ib()

if __name__ == "__main__":
    test_single_symbol()
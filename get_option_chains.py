"""
Get Real Option Chain Data from Interactive Brokers
===================================================
Pulls actual available expirations and strikes for our top trades
"""

from ib_insync import IB, Stock, Option
from datetime import datetime
import asyncio


def get_option_expirations(symbol: str):
    """Get available option expirations for a symbol"""
    ib = IB()
    
    try:
        print(f"\n{'='*80}")
        print(f"🔍 Fetching option chain for {symbol}")
        print(f"{'='*80}")
        
        # Connect to IB Gateway
        ib.connect('127.0.0.1', 7496, clientId=3)
        
        # Create stock contract
        stock = Stock(symbol, 'SMART', 'USD')
        ib.qualifyContracts(stock)
        
        # Get current stock price
        ticker = ib.reqMktData(stock)
        ib.sleep(2)  # Wait for data
        
        current_price = ticker.marketPrice() or ticker.last or ticker.close
        print(f"\n📊 Current Price: ${current_price:.2f}")
        
        # Request option chain
        print(f"\n⏳ Requesting option chain...")
        chains = ib.reqSecDefOptParams(stock.symbol, '', stock.secType, stock.conId)
        
        if not chains:
            print(f"❌ No option chain found for {symbol}")
            return
        
        # Get the main chain (usually first one for US equities)
        chain = chains[0]
        
        print(f"\n✅ Exchange: {chain.exchange}")
        print(f"\n📅 AVAILABLE EXPIRATIONS ({len(chain.expirations)} total):")
        print("-" * 80)
        
        today = datetime.now()
        
        # Show next 10 expirations
        for i, expiration in enumerate(sorted(chain.expirations)[:10], 1):
            # Parse expiration date (format: YYYYMMDD)
            exp_date = datetime.strptime(expiration, '%Y%m%d')
            days_out = (exp_date - today).days
            
            print(f"  {i:2d}. {expiration} ({exp_date.strftime('%b %d, %Y')}) - {days_out} days")
        
        # Show relevant strikes around current price
        print(f"\n💰 SAMPLE STRIKES NEAR ${current_price:.2f}:")
        print("-" * 80)
        
        strikes = sorted([s for s in chain.strikes if abs(s - current_price) <= 10])[:10]
        for strike in strikes:
            diff = strike - current_price
            label = "ATM" if abs(diff) < 1 else "OTM" if diff < 0 else "ITM"
            print(f"  ${strike:.2f} ({label}, {diff:+.2f})")
        
        print(f"\n💡 Recommendation: Use an expiration 30-45 days out")
        print(f"   Best strikes: ATM (${current_price:.0f}) or slightly OTM\n")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        ib.disconnect()


def main():
    """Get option chains for top trades"""
    print("\n" + "="*80)
    print("📋 REAL OPTION CHAIN DATA - TOP PUT OPPORTUNITIES")
    print("="*80)
    
    # Top trades from our analysis
    symbols = [
        "LVS",   # #1 - 100/100 confidence
        "DD",    # #4 - 90/100 confidence, 15.6% target
        "STE",   # #5 - 90/100 confidence, 11.5% target
        "AKAM",  # #10 - 90/100 confidence, 21.8% target!
    ]
    
    for symbol in symbols:
        try:
            get_option_expirations(symbol)
        except Exception as e:
            print(f"\n❌ Failed to get data for {symbol}: {e}")
            continue
    
    print("\n" + "="*80)
    print("✅ Option chain data complete!")
    print("\n💡 Next steps:")
    print("   1. Choose an expiration 30-45 days from today")
    print("   2. Select ATM or slightly OTM PUT strike")
    print("   3. Check bid/ask spread in TWS (should be tight)")
    print("   4. Verify volume > 100 contracts for liquidity")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()

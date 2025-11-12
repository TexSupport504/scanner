"""
Quick Backtest Demo - Test Today's Recommendations Against Recent Performance

Since we need historical scan data for full backtesting, this demo:
1. Takes today's recommendations from daily_scan_results.csv
2. Simulates what would happen with 30% take profit / 25% stop loss
3. Shows potential max gains if signals were perfectly timed

This gives you a preview of the backtesting system capabilities.
"""

import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

class QuickBacktestDemo:
    def __init__(self):
        self.results = []
        
    def load_todays_recommendations(self):
        """Load today's scan results"""
        try:
            df = pd.read_csv('data/exports/daily_scan_results.csv')
            
            # Filter for trading recommendations
            recommendations = df[df['suggested_trade'].notna()].copy()
            
            print(f"📊 Today's Trading Recommendations: {len(recommendations)}")
            print(f"   🔴 LONG PUT: {len(recommendations[recommendations['suggested_trade'] == 'LONG PUT'])}")
            print(f"   🟢 LONG CALL: {len(recommendations[recommendations['suggested_trade'] == 'LONG CALL'])}")
            
            return recommendations
            
        except Exception as e:
            print(f"❌ Error loading recommendations: {e}")
            return pd.DataFrame()
    
    def simulate_quick_backtest(self, symbol, trade_type, entry_price, rsi):
        """
        Quick simulation using recent price data
        """
        try:
            # Get last 30 days of data
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
            
            ticker = yf.Ticker(symbol)
            data = ticker.history(start=start_date, end=end_date, interval='1d')
            
            if data.empty or len(data) < 5:
                return None
                
            # Use recent 10 days to simulate forward performance
            recent_data = data.tail(10)
            
            # Calculate daily returns
            daily_returns = recent_data['Close'].pct_change()
            
            # Simulate profit/loss based on trade type
            if trade_type == 'LONG PUT':
                # PUT profits from stock decline
                max_decline = daily_returns.min() * 100  # Most negative day
                avg_decline = daily_returns[daily_returns < 0].mean() * 100 if len(daily_returns[daily_returns < 0]) > 0 else 0
            else:
                # CALL profits from stock increase
                max_gain = daily_returns.max() * 100  # Most positive day
                avg_gain = daily_returns[daily_returns > 0].mean() * 100 if len(daily_returns[daily_returns > 0]) > 0 else 0
            
            # Calculate what would happen with our rules
            profit_target = 30.0  # 30% profit target
            stop_loss = -25.0     # 25% stop loss
            
            if trade_type == 'LONG PUT':
                max_potential = max_decline
                avg_potential = avg_decline
                
                # Would we hit profit target?
                if max_decline <= -30:  # Stock declined 30%+ (PUT profit)
                    outcome = 'PROFIT_TARGET_HIT'
                    actual_return = 30.0
                elif max_decline >= 25:  # Stock gained 25%+ (PUT loss)
                    outcome = 'STOP_LOSS_HIT'
                    actual_return = -25.0
                else:
                    outcome = 'MIXED'
                    actual_return = -max_decline  # Convert stock decline to PUT profit
                    
            else:  # LONG CALL
                max_potential = max_gain
                avg_potential = avg_gain
                
                # Would we hit profit target?
                if max_gain >= 30:  # Stock gained 30%+ (CALL profit)
                    outcome = 'PROFIT_TARGET_HIT'
                    actual_return = 30.0
                elif max_gain <= -25:  # Stock declined 25%+ (CALL loss)
                    outcome = 'STOP_LOSS_HIT'
                    actual_return = -25.0
                else:
                    outcome = 'MIXED'
                    actual_return = max_gain  # Stock gain = CALL profit
            
            return {
                'symbol': symbol,
                'trade_type': trade_type,
                'entry_price': entry_price,
                'rsi': rsi,
                'max_potential_pct': max_potential,
                'avg_potential_pct': avg_potential,
                'simulated_outcome': outcome,
                'simulated_return_pct': actual_return,
                'would_profit': actual_return > 0
            }
            
        except Exception as e:
            print(f"⚠️ Error simulating {symbol}: {e}")
            return None
    
    def run_demo(self):
        """Run the quick backtest demo"""
        print("🚀 Quick Backtest Demo - Testing Today's Recommendations")
        print("Rules: 30% Take Profit / 25% Stop Loss")
        print("=" * 80)
        
        # Load today's recommendations
        recommendations = self.load_todays_recommendations()
        
        if recommendations.empty:
            print("❌ No recommendations to test")
            return
        
        print(f"\n📈 Testing recent performance for {len(recommendations)} stocks...")
        
        results = []
        
        # Test top 10 recommendations to avoid rate limiting
        test_recs = recommendations.head(10)
        
        for idx, row in test_recs.iterrows():
            print(f"Testing {row['symbol']} ({row['suggested_trade']})...")
            
            result = self.simulate_quick_backtest(
                row['symbol'],
                row['suggested_trade'],
                row['price'],
                row['rsi']
            )
            
            if result:
                results.append(result)
        
        if not results:
            print("❌ No valid results generated")
            return
        
        # Analyze results
        self.results = pd.DataFrame(results)
        self.display_demo_results()
    
    def display_demo_results(self):
        """Display demo results"""
        df = self.results
        
        print("\n" + "=" * 80)
        print("🏆 QUICK BACKTEST DEMO RESULTS")
        print("=" * 80)
        
        # Overall stats
        total_trades = len(df)
        profitable_trades = len(df[df['would_profit']])
        win_rate = profitable_trades / total_trades * 100
        
        print(f"\n📊 DEMO STATISTICS:")
        print(f"   Stocks Tested:        {total_trades}")
        print(f"   Profitable Signals:   {profitable_trades} ({win_rate:.1f}%)")
        print(f"   Average Return:       {df['simulated_return_pct'].mean():+.1f}%")
        print(f"   Best Signal:          {df['simulated_return_pct'].max():+.1f}%")
        print(f"   Worst Signal:         {df['simulated_return_pct'].min():+.1f}%")
        
        # Outcome breakdown
        print(f"\n🎯 OUTCOME BREAKDOWN:")
        for outcome in df['simulated_outcome'].unique():
            count = len(df[df['simulated_outcome'] == outcome])
            print(f"   {outcome:20}: {count} trades ({count/total_trades*100:.1f}%)")
        
        # Performance by trade type
        print(f"\n📈 PERFORMANCE BY TRADE TYPE:")
        for trade_type in df['trade_type'].unique():
            subset = df[df['trade_type'] == trade_type]
            wins = len(subset[subset['would_profit']])
            print(f"   {trade_type}:")
            print(f"     Trades:           {len(subset)}")
            print(f"     Win Rate:         {wins/len(subset)*100:.1f}%")
            print(f"     Avg Return:       {subset['simulated_return_pct'].mean():+.1f}%")
        
        # Detailed results
        print(f"\n🔍 DETAILED RESULTS:")
        display_cols = ['symbol', 'trade_type', 'rsi', 'simulated_return_pct', 'simulated_outcome']
        print(df[display_cols].to_string(index=False))
        
        # Max potential analysis
        print(f"\n💡 MAX POTENTIAL vs RULES:")
        print(f"   Avg Max Potential:    {df['max_potential_pct'].mean():+.1f}%")
        print(f"   Avg Simulated Return: {df['simulated_return_pct'].mean():+.1f}%")
        print(f"   Efficiency:           {(df['simulated_return_pct'].mean()/df['max_potential_pct'].mean())*100:.1f}%")
        
        # Save results
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'data/exports/backtest_demo_{timestamp}.csv'
        df.to_csv(filename, index=False)
        print(f"\n💾 Demo results saved to: {filename}")

def main():
    """Run the quick backtest demo"""
    demo = QuickBacktestDemo()
    demo.run_demo()

if __name__ == "__main__":
    main()
"""
Backtesting System for Daily RSI Scanner Recommendations

Tests performance of LONG PUT/CALL recommendations with:
- 30% take profit target
- 25% stop loss
- Entry at next day's open
- Exit when profit/loss targets hit or at expiration

Analyzes:
- Win rate and average returns
- Maximum potential gains vs actual results
- Signal accuracy across different market conditions
- Performance by priority level and volatility buckets
"""

import pandas as pd
import numpy as np
import sqlite3
from datetime import datetime, timedelta
import yfinance as yf
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

class RSIBacktester:
    def __init__(self, database_path='data/scanner.db'):
        """Initialize backtester with database connection"""
        self.db_path = database_path
        self.results = []
        self.performance_stats = {}
        
    def get_historical_recommendations(self, start_date='2024-01-01', end_date=None):
        """
        Retrieve historical scan results from database
        """
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')
            
        conn = sqlite3.connect(self.db_path)
        
        # Get all scan results with trading recommendations
        query = """
        SELECT 
            scan_date,
            symbol,
            current_price as entry_price,
            latest_rsi as rsi,
            latest_atr as atr,
            is_overextended,
            overextended_threshold,
            priority,
            CASE 
                WHEN latest_rsi >= 90 THEN 'LONG PUT'
                WHEN latest_rsi <= 10 THEN 'LONG CALL'
                WHEN latest_rsi >= 80 AND is_overextended = 1 THEN 'LONG PUT'
                WHEN latest_rsi <= 20 THEN 'LONG CALL'
                ELSE NULL
            END as suggested_trade,
            CASE 
                WHEN latest_rsi >= 90 THEN 1  -- Extreme overbought = Priority 1
                WHEN latest_rsi <= 10 THEN 1  -- Extreme oversold = Priority 1
                WHEN latest_rsi >= 80 AND is_overextended = 1 THEN 1  -- Overextended = Priority 1
                WHEN latest_rsi >= 75 OR latest_rsi <= 25 THEN 2  -- Strong signals = Priority 2
                ELSE 3  -- Regular signals = Priority 3
            END as calculated_priority
        FROM scan_results 
        WHERE scan_date BETWEEN ? AND ?
            AND latest_rsi IS NOT NULL
            AND current_price IS NOT NULL
        ORDER BY scan_date, symbol
        """
        
        df = pd.read_sql_query(query, conn, params=(start_date, end_date))
        conn.close()
        
        # Filter only records with trading recommendations
        df = df[df['suggested_trade'].notna()].copy()
        
        print(f"📊 Found {len(df)} historical recommendations between {start_date} and {end_date}")
        print(f"   - LONG PUT: {len(df[df['suggested_trade'] == 'LONG PUT'])}")
        print(f"   - LONG CALL: {len(df[df['suggested_trade'] == 'LONG CALL'])}")
        
        return df
    
    def get_stock_price_data(self, symbol, start_date, end_date, days_buffer=60):
        """
        Fetch stock price data for backtesting
        """
        try:
            # Add buffer for price movement analysis
            buffer_start = (datetime.strptime(start_date, '%Y-%m-%d') - timedelta(days=days_buffer)).strftime('%Y-%m-%d')
            
            # Download data
            ticker = yf.Ticker(symbol)
            data = ticker.history(start=buffer_start, end=end_date, interval='1d')
            
            if data.empty:
                return None
                
            # Reset index to get dates as column
            data = data.reset_index()
            data['Date'] = data['Date'].dt.strftime('%Y-%m-%d')
            
            return data[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']]
            
        except Exception as e:
            print(f"⚠️ Error fetching data for {symbol}: {e}")
            return None
    
    def simulate_stock_trade(self, row, stock_data, holding_period_days=30):
        """
        Simulate a stock trade with profit/loss targets
        
        For PUT recommendations: Profit when stock goes down
        For CALL recommendations: Profit when stock goes up
        """
        signal_date = row['scan_date']
        entry_price = row['entry_price']
        trade_type = row['suggested_trade']
        
        # Find entry date (next trading day after signal)
        signal_datetime = datetime.strptime(signal_date, '%Y-%m-%d')
        entry_date_target = signal_datetime + timedelta(days=1)
        
        # Find actual entry date in stock data
        stock_data['Date_dt'] = pd.to_datetime(stock_data['Date'])
        entry_candidates = stock_data[stock_data['Date_dt'] >= entry_date_target].copy()
        
        if entry_candidates.empty:
            return None
            
        entry_row = entry_candidates.iloc[0]
        actual_entry_date = entry_row['Date']
        actual_entry_price = entry_row['Open']  # Enter at open
        
        # Calculate exit date (max holding period)
        exit_date_target = datetime.strptime(actual_entry_date, '%Y-%m-%d') + timedelta(days=holding_period_days)
        
        # Get price data for holding period
        holding_data = stock_data[
            (stock_data['Date_dt'] >= datetime.strptime(actual_entry_date, '%Y-%m-%d')) &
            (stock_data['Date_dt'] <= exit_date_target)
        ].copy()
        
        if len(holding_data) < 2:  # Need at least entry day + 1 more day
            return None
            
        # Calculate profit/loss targets
        profit_target = 0.30  # 30% profit target
        loss_limit = 0.25     # 25% stop loss
        
        exit_reason = 'EXPIRED'
        exit_date = holding_data.iloc[-1]['Date']
        exit_price = holding_data.iloc[-1]['Close']
        max_profit_pct = 0
        max_loss_pct = 0
        
        # Track daily P&L to find exit points
        for idx, day_data in holding_data.iterrows():
            if idx == holding_data.index[0]:  # Skip entry day
                continue
                
            daily_high = day_data['High']
            daily_low = day_data['Low']
            daily_close = day_data['Close']
            
            if trade_type == 'LONG PUT':
                # PUT profits when stock goes down
                # Calculate percentage decline from entry
                high_decline = (actual_entry_price - daily_low) / actual_entry_price
                close_decline = (actual_entry_price - daily_close) / actual_entry_price
                
                max_profit_pct = max(max_profit_pct, high_decline)
                max_loss_pct = min(max_loss_pct, -((daily_high - actual_entry_price) / actual_entry_price))
                
                # Check profit target (30% decline = 30% PUT profit)
                if high_decline >= profit_target:
                    exit_reason = 'PROFIT_TARGET'
                    exit_date = day_data['Date']
                    exit_price = actual_entry_price * (1 - profit_target)  # Assume we got the target price
                    break
                
                # Check stop loss (25% increase = 25% PUT loss)
                elif (daily_high - actual_entry_price) / actual_entry_price >= loss_limit:
                    exit_reason = 'STOP_LOSS'
                    exit_date = day_data['Date']
                    exit_price = actual_entry_price * (1 + loss_limit)  # Assume we hit stop loss
                    break
                    
            elif trade_type == 'LONG CALL':
                # CALL profits when stock goes up
                # Calculate percentage gain from entry
                high_gain = (daily_high - actual_entry_price) / actual_entry_price
                close_gain = (daily_close - actual_entry_price) / actual_entry_price
                
                max_profit_pct = max(max_profit_pct, high_gain)
                max_loss_pct = min(max_loss_pct, -((actual_entry_price - daily_low) / actual_entry_price))
                
                # Check profit target (30% increase = 30% CALL profit)
                if high_gain >= profit_target:
                    exit_reason = 'PROFIT_TARGET'
                    exit_date = day_data['Date']
                    exit_price = actual_entry_price * (1 + profit_target)  # Assume we got the target price
                    break
                
                # Check stop loss (25% decline = 25% CALL loss)
                elif (actual_entry_price - daily_low) / actual_entry_price >= loss_limit:
                    exit_reason = 'STOP_LOSS'
                    exit_date = day_data['Date']
                    exit_price = actual_entry_price * (1 - loss_limit)  # Assume we hit stop loss
                    break
        
        # Calculate final P&L
        if trade_type == 'LONG PUT':
            actual_return = (actual_entry_price - exit_price) / actual_entry_price
        else:  # LONG CALL
            actual_return = (exit_price - actual_entry_price) / actual_entry_price
        
        return {
            'signal_date': signal_date,
            'entry_date': actual_entry_date,
            'exit_date': exit_date,
            'symbol': row['symbol'],
            'trade_type': trade_type,
            'rsi': row['rsi'],
            'priority': row.get('calculated_priority', row.get('priority', 3)),
            'is_overextended': row['is_overextended'],
            'entry_price': actual_entry_price,
            'exit_price': exit_price,
            'actual_return_pct': actual_return * 100,
            'max_profit_pct': max_profit_pct * 100,
            'max_loss_pct': max_loss_pct * 100,
            'exit_reason': exit_reason,
            'holding_days': (datetime.strptime(exit_date, '%Y-%m-%d') - datetime.strptime(actual_entry_date, '%Y-%m-%d')).days,
            'win': 1 if actual_return > 0 else 0
        }
    
    def backtest_recommendations(self, start_date='2024-01-01', end_date=None, save_results=True):
        """
        Run complete backtesting analysis
        """
        print("🚀 Starting RSI Scanner Backtest Analysis")
        print("=" * 80)
        
        # Get historical recommendations
        recommendations = self.get_historical_recommendations(start_date, end_date)
        
        if recommendations.empty:
            print("❌ No historical recommendations found for the specified period")
            return None
        
        # Process each recommendation
        results = []
        symbols_processed = set()
        
        print(f"\n📈 Processing {len(recommendations)} recommendations...")
        
        for idx, row in recommendations.iterrows():
            symbol = row['symbol']
            
            # Download stock data if not already cached for this symbol
            if symbol not in symbols_processed:
                print(f"📊 Fetching data for {symbol}... ({len(symbols_processed)+1}/{len(recommendations['symbol'].unique())})")
                
                stock_data = self.get_stock_price_data(
                    symbol, 
                    start_date, 
                    (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
                )
                
                if stock_data is None:
                    print(f"⚠️ Skipping {symbol} - no data available")
                    continue
                
                symbols_processed.add(symbol)
            
            # Simulate the trade
            trade_result = self.simulate_stock_trade(row, stock_data)
            
            if trade_result:
                results.append(trade_result)
        
        # Convert to DataFrame for analysis
        self.results = pd.DataFrame(results)
        
        if self.results.empty:
            print("❌ No valid trades could be simulated")
            return None
        
        # Calculate performance statistics
        self.calculate_performance_stats()
        
        # Display results
        self.display_results()
        
        # Save results
        if save_results:
            self.save_results()
        
        return self.results
    
    def calculate_performance_stats(self):
        """Calculate comprehensive performance statistics"""
        df = self.results
        
        self.performance_stats = {
            'total_trades': len(df),
            'winning_trades': len(df[df['win'] == 1]),
            'losing_trades': len(df[df['win'] == 0]),
            'win_rate': len(df[df['win'] == 1]) / len(df) * 100,
            
            'avg_return': df['actual_return_pct'].mean(),
            'median_return': df['actual_return_pct'].median(),
            'best_trade': df['actual_return_pct'].max(),
            'worst_trade': df['actual_return_pct'].min(),
            'std_dev': df['actual_return_pct'].std(),
            
            'avg_winner': df[df['win'] == 1]['actual_return_pct'].mean() if len(df[df['win'] == 1]) > 0 else 0,
            'avg_loser': df[df['win'] == 0]['actual_return_pct'].mean() if len(df[df['win'] == 0]) > 0 else 0,
            
            'profit_target_hit': len(df[df['exit_reason'] == 'PROFIT_TARGET']),
            'stop_loss_hit': len(df[df['exit_reason'] == 'STOP_LOSS']),
            'expired': len(df[df['exit_reason'] == 'EXPIRED']),
            
            'avg_max_profit': df['max_profit_pct'].mean(),
            'avg_max_loss': df['max_loss_pct'].mean(),
            'avg_holding_days': df['holding_days'].mean()
        }
        
        # Performance by trade type
        for trade_type in df['trade_type'].unique():
            subset = df[df['trade_type'] == trade_type]
            self.performance_stats[f'{trade_type.lower()}_trades'] = len(subset)
            self.performance_stats[f'{trade_type.lower()}_win_rate'] = len(subset[subset['win'] == 1]) / len(subset) * 100
            self.performance_stats[f'{trade_type.lower()}_avg_return'] = subset['actual_return_pct'].mean()
        
        # Performance by priority
        for priority in sorted(df['priority'].unique()):
            subset = df[df['priority'] == priority]
            self.performance_stats[f'priority_{priority}_trades'] = len(subset)
            self.performance_stats[f'priority_{priority}_win_rate'] = len(subset[subset['win'] == 1]) / len(subset) * 100
            self.performance_stats[f'priority_{priority}_avg_return'] = subset['actual_return_pct'].mean()
    
    def display_results(self):
        """Display comprehensive backtesting results"""
        stats = self.performance_stats
        df = self.results
        
        print("\n" + "=" * 80)
        print("🏆 BACKTESTING RESULTS SUMMARY")
        print("=" * 80)
        
        print(f"\n📊 OVERALL PERFORMANCE:")
        print(f"   Total Trades:        {stats['total_trades']:,}")
        print(f"   Winning Trades:      {stats['winning_trades']:,} ({stats['win_rate']:.1f}%)")
        print(f"   Losing Trades:       {stats['losing_trades']:,}")
        
        print(f"\n💰 RETURNS ANALYSIS:")
        print(f"   Average Return:      {stats['avg_return']:+.2f}%")
        print(f"   Median Return:       {stats['median_return']:+.2f}%")
        print(f"   Best Trade:          {stats['best_trade']:+.2f}%")
        print(f"   Worst Trade:         {stats['worst_trade']:+.2f}%")
        print(f"   Standard Deviation:  {stats['std_dev']:.2f}%")
        
        print(f"\n🎯 WIN/LOSS BREAKDOWN:")
        print(f"   Average Winner:      {stats['avg_winner']:+.2f}%")
        print(f"   Average Loser:       {stats['avg_loser']:+.2f}%")
        print(f"   Profit/Loss Ratio:   {abs(stats['avg_winner']/stats['avg_loser']) if stats['avg_loser'] != 0 else 'N/A':.2f}")
        
        print(f"\n🚪 EXIT ANALYSIS:")
        print(f"   Profit Target Hit:   {stats['profit_target_hit']} ({stats['profit_target_hit']/stats['total_trades']*100:.1f}%)")
        print(f"   Stop Loss Hit:       {stats['stop_loss_hit']} ({stats['stop_loss_hit']/stats['total_trades']*100:.1f}%)")
        print(f"   Expired:             {stats['expired']} ({stats['expired']/stats['total_trades']*100:.1f}%)")
        
        print(f"\n📈 POTENTIAL vs ACTUAL:")
        print(f"   Avg Max Profit:      {stats['avg_max_profit']:+.2f}%")
        print(f"   Avg Max Loss:        {stats['avg_max_loss']:+.2f}%")
        print(f"   Avg Holding Days:    {stats['avg_holding_days']:.1f} days")
        
        # Performance by trade type
        print(f"\n🔴 LONG PUT PERFORMANCE:")
        if 'long put_trades' in stats:
            print(f"   Trades:              {stats['long put_trades']}")
            print(f"   Win Rate:            {stats['long put_win_rate']:.1f}%")
            print(f"   Average Return:      {stats['long put_avg_return']:+.2f}%")
        
        print(f"\n🟢 LONG CALL PERFORMANCE:")
        if 'long call_trades' in stats:
            print(f"   Trades:              {stats['long call_trades']}")
            print(f"   Win Rate:            {stats['long call_win_rate']:.1f}%")
            print(f"   Average Return:      {stats['long call_avg_return']:+.2f}%")
        
        # Performance by priority
        print(f"\n🎯 PERFORMANCE BY PRIORITY:")
        for priority in [1, 2, 3]:
            if f'priority_{priority}_trades' in stats:
                print(f"   Priority {priority}:")
                print(f"     Trades:          {stats[f'priority_{priority}_trades']}")
                print(f"     Win Rate:        {stats[f'priority_{priority}_win_rate']:.1f}%")
                print(f"     Avg Return:      {stats[f'priority_{priority}_avg_return']:+.2f}%")
        
        # Top performers
        print(f"\n🏆 TOP 10 BEST TRADES:")
        top_trades = df.nlargest(10, 'actual_return_pct')[['symbol', 'trade_type', 'rsi', 'actual_return_pct', 'exit_reason', 'holding_days']]
        print(top_trades.to_string(index=False))
        
        # Worst performers
        print(f"\n💸 TOP 10 WORST TRADES:")
        worst_trades = df.nsmallest(10, 'actual_return_pct')[['symbol', 'trade_type', 'rsi', 'actual_return_pct', 'exit_reason', 'holding_days']]
        print(worst_trades.to_string(index=False))
    
    def save_results(self):
        """Save detailed results to CSV"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Create exports directory if it doesn't exist
        Path('data/exports/backtest').mkdir(parents=True, exist_ok=True)
        
        # Save detailed results
        results_file = f'data/exports/backtest/backtest_results_{timestamp}.csv'
        self.results.to_csv(results_file, index=False)
        print(f"\n💾 Detailed results saved to: {results_file}")
        
        # Save summary statistics
        stats_df = pd.DataFrame([self.performance_stats])
        stats_file = f'data/exports/backtest/backtest_summary_{timestamp}.csv'
        stats_df.to_csv(stats_file, index=False)
        print(f"💾 Summary statistics saved to: {stats_file}")
        
        return results_file, stats_file

def main():
    """Run backtesting analysis"""
    print("🚀 RSI Scanner Backtesting System")
    print("Testing 30% profit target / 25% stop loss strategy")
    print("=" * 80)
    
    # Initialize backtester
    backtester = RSIBacktester()
    
    # Run backtest (last 3 months for demonstration)
    start_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
    
    results = backtester.backtest_recommendations(
        start_date=start_date,
        end_date=datetime.now().strftime('%Y-%m-%d')
    )
    
    if results is not None:
        print(f"\n✅ Backtesting completed successfully!")
        print(f"📊 {len(results)} trades analyzed")
    else:
        print("❌ Backtesting failed - no data available")

if __name__ == "__main__":
    main()
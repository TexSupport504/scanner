"""
Options Strategy Analyzer for Overextended Stocks
Analyzes overextended stocks and provides options trading strategies
"""

import pandas as pd
import sqlite3
from datetime import datetime, timedelta
import os

class OptionsStrategyAnalyzer:
    def __init__(self, db_path="data/scanner.db"):
        self.db_path = db_path
        
    def get_overextended_stocks(self):
        """Get all stocks meeting overextended criteria"""
        conn = sqlite3.connect(self.db_path)
        
        query = """
            SELECT 
                symbol,
                latest_rsi as rsi,
                latest_atr as atr,
                swing_low,
                overextended_threshold,
                current_price,
                (current_price - overextended_threshold) as distance_from_threshold,
                ((current_price - overextended_threshold) / overextended_threshold * 100) as distance_pct,
                created_at
            FROM scan_results
            WHERE is_overextended = 1
            ORDER BY distance_pct DESC
        """
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        return df
    
    def analyze_options_opportunities(self, df):
        """Analyze each overextended stock for options strategies"""
        
        strategies = []
        
        for idx, row in df.iterrows():
            symbol = row['symbol']
            current_price = row['current_price']
            threshold = row['overextended_threshold']
            swing_low = row['swing_low']
            rsi = row['rsi']
            atr = row['atr']
            distance_pct = row['distance_pct']
            
            # Calculate key levels
            expected_pullback = threshold  # Price likely to return to threshold
            support_level = swing_low      # Strong support at swing low
            risk_distance = current_price - threshold
            reward_distance = threshold - swing_low
            risk_reward_ratio = reward_distance / risk_distance if risk_distance > 0 else 0
            
            # Determine strategy based on conditions
            strategy = self._determine_strategy(
                rsi, distance_pct, current_price, threshold, swing_low, atr
            )
            
            strategies.append({
                'symbol': symbol,
                'current_price': current_price,
                'overextended_threshold': threshold,
                'swing_low': swing_low,
                'rsi': rsi,
                'atr': atr,
                'distance_pct': distance_pct,
                'expected_pullback_target': expected_pullback,
                'support_level': support_level,
                'risk_reward_ratio': risk_reward_ratio,
                'primary_strategy': strategy['primary'],
                'alternative_strategy': strategy['alternative'],
                'risk_level': strategy['risk_level'],
                'timeframe': strategy['timeframe'],
                'strike_suggestion': strategy['strike'],
                'reasoning': strategy['reasoning']
            })
        
        return pd.DataFrame(strategies)
    
    def _determine_strategy(self, rsi, distance_pct, current_price, threshold, swing_low, atr):
        """Determine the best options strategy based on technical conditions
        
        RESTRICTED TO: Level 1 and Level 2 options only
        Level 1: Covered Call, Buy Write
        Level 2: Long Call, Long Put, Long Straddle, Long Strangle, Covered Put,
                 Protective Call, Protective Put, Conversion, Long Call/Put Spread
        """
        
        # Base strategy on RSI and overextension level
        if rsi >= 80 and distance_pct > 2:
            # Extremely overbought and significantly overextended
            primary = "Long PUT Spread (Bearish)"
            alternative = "Long PUT"
            risk_level = "MODERATE"
            timeframe = "1-2 weeks"
            strike = f"Buy: ${current_price:.2f} PUT / Sell: ${threshold:.2f} PUT"
            reasoning = "Extremely overbought with high probability of mean reversion. Bearish PUT spread limiting risk."
            
        elif rsi >= 80 and distance_pct <= 2:
            # Very overbought but close to threshold
            primary = "Long PUT"
            alternative = "Long PUT Spread"
            risk_level = "LOW-MODERATE"
            timeframe = "1 week"
            strike = f"Buy: ${current_price:.2f} PUT"
            reasoning = "Overbought but near threshold. Straight PUT purchase for directional move down."
            
        elif 70 <= rsi < 80 and distance_pct > 1:
            # Moderately overbought
            primary = "Long PUT Spread"
            alternative = "Long Strangle"
            risk_level = "LOW"
            timeframe = "2-3 weeks"
            strike = f"Buy: ${current_price:.2f} PUT / Sell: ${threshold:.2f} PUT"
            reasoning = "Moderately overbought. PUT spread captures downward move with defined risk."
            
        else:
            # Lower risk setup - wait for better entry or use protective strategy
            primary = "Long PUT (at-the-money)"
            alternative = "Long PUT Spread"
            risk_level = "LOW"
            timeframe = "1-2 weeks"
            strike = f"Buy: ${threshold:.2f} PUT"
            reasoning = "Lower confidence. Simple long PUT at threshold for pullback play."
        
        return {
            'primary': primary,
            'alternative': alternative,
            'risk_level': risk_level,
            'timeframe': timeframe,
            'strike': strike,
            'reasoning': reasoning
        }
    
    def generate_trade_plan(self, strategies_df):
        """Generate detailed trade plan for tomorrow"""
        
        print("\n" + "=" * 80)
        print("📊 OPTIONS TRADE PLAN FOR OVEREXTENDED STOCKS")
        print(f"📅 Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print(f"🎯 Trade Date: {(datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')} (Tomorrow)")
        print("=" * 80)
        
        if strategies_df.empty:
            print("\n❌ No overextended stocks found.")
            return
        
        # Sort by risk-reward ratio (best opportunities first)
        strategies_df = strategies_df.sort_values('risk_reward_ratio', ascending=False)
        
        print(f"\n🔥 TOTAL OPPORTUNITIES: {len(strategies_df)}")
        print("\n" + "-" * 80)
        
        for idx, trade in strategies_df.iterrows():
            self._print_trade_card(trade, idx + 1)
        
        # Summary statistics
        print("\n" + "=" * 80)
        print("📈 STRATEGY SUMMARY")
        print("=" * 80)
        
        strategy_counts = strategies_df['primary_strategy'].value_counts()
        for strategy, count in strategy_counts.items():
            print(f"   {strategy}: {count} opportunities")
        
        print(f"\n💰 RISK LEVELS:")
        risk_counts = strategies_df['risk_level'].value_counts()
        for risk, count in risk_counts.items():
            print(f"   {risk}: {count} trades")
        
        print(f"\n⏰ TIMEFRAMES:")
        timeframe_counts = strategies_df['timeframe'].value_counts()
        for tf, count in timeframe_counts.items():
            print(f"   {tf}: {count} trades")
        
        # Export to CSV
        output_file = "data/exports/options_trade_plan.csv"
        strategies_df.to_csv(output_file, index=False)
        print(f"\n💾 Trade plan exported to: {output_file}")
        
        # Best opportunities
        print("\n" + "=" * 80)
        print("⭐ TOP 3 OPPORTUNITIES (Best Risk/Reward)")
        print("=" * 80)
        
        top_3 = strategies_df.head(3)
        for idx, trade in top_3.iterrows():
            print(f"\n🎯 #{idx + 1} {trade['symbol']}")
            print(f"   Strategy: {trade['primary_strategy']}")
            print(f"   Risk/Reward: {trade['risk_reward_ratio']:.2f}")
            print(f"   Current: ${trade['current_price']:.2f} → Target: ${trade['expected_pullback_target']:.2f}")
            print(f"   RSI: {trade['rsi']:.1f} | Distance: {trade['distance_pct']:.2f}%")
    
    def _print_trade_card(self, trade, number):
        """Print detailed trade card for each opportunity"""
        
        print(f"\n{'=' * 80}")
        print(f"🎯 TRADE #{number}: {trade['symbol']}")
        print(f"{'=' * 80}")
        
        # Price levels
        print(f"\n📊 PRICE ANALYSIS:")
        print(f"   Current Price:        ${trade['current_price']:>8.2f}")
        print(f"   Overextended Level:   ${trade['overextended_threshold']:>8.2f}  ← Expected pullback target")
        print(f"   Swing Low (Support):  ${trade['swing_low']:>8.2f}  ← Strong support")
        print(f"   Distance from normal: {trade['distance_pct']:>7.2f}%  ({'Highly' if trade['distance_pct'] > 2 else 'Moderately'} overextended)")
        
        # Technical indicators
        print(f"\n📈 TECHNICAL INDICATORS:")
        print(f"   RSI:                  {trade['rsi']:>8.1f}  ({'Extreme' if trade['rsi'] >= 80 else 'Strong'} overbought)")
        print(f"   ATR:                  ${trade['atr']:>8.2f}  (Daily volatility)")
        print(f"   Risk/Reward Ratio:    {trade['risk_reward_ratio']:>8.2f}:1")
        
        # Strategy recommendation
        print(f"\n🎲 RECOMMENDED STRATEGY:")
        print(f"   PRIMARY:    {trade['primary_strategy']}")
        print(f"   ALTERNATIVE: {trade['alternative_strategy']}")
        print(f"   RISK LEVEL:  {trade['risk_level']}")
        print(f"   TIMEFRAME:   {trade['timeframe']}")
        
        # Strike suggestions
        print(f"\n💡 STRIKE LEVELS:")
        print(f"   {trade['strike_suggestion']}")
        
        # Reasoning
        print(f"\n📝 TRADE THESIS:")
        print(f"   {trade['reasoning']}")
        
        # Entry/Exit plan
        print(f"\n🎯 TRADE PLAN:")
        entry_price = trade['current_price']
        target_price = trade['expected_pullback_target']
        stop_loss = entry_price + (trade['atr'] * 1.5)
        
        print(f"   Entry:       Market open tomorrow (monitor pre-market)")
        print(f"   Target 1:    ${target_price:.2f} (threshold)")
        print(f"   Target 2:    ${trade['swing_low']:.2f} (swing low)")
        print(f"   Stop Loss:   ${stop_loss:.2f} (1.5x ATR above current)")
        print(f"   Max Loss:    {((stop_loss - entry_price) / entry_price * 100):.1f}%")
        print(f"   Expected Move: {((entry_price - target_price) / entry_price * 100):.1f}% down")
        
        # Risk warning
        if trade['risk_level'] in ['MODERATE', 'HIGH']:
            print(f"\n⚠️  WARNING: {trade['risk_level']} risk - Size position accordingly!")
        
        print(f"\n{'=' * 80}")
    
    def run_analysis(self):
        """Run complete options analysis"""
        print("🚀 Starting Options Strategy Analysis...")
        print("=" * 80)
        
        # Get overextended stocks
        print("\n1. Loading overextended stocks from database...")
        df_overextended = self.get_overextended_stocks()
        
        if df_overextended.empty:
            print("   ❌ No overextended stocks found in database.")
            print("   Run the scanner first to get data.")
            return
        
        print(f"   ✅ Found {len(df_overextended)} overextended stocks")
        
        # Analyze strategies
        print("\n2. Analyzing options opportunities...")
        strategies_df = self.analyze_options_opportunities(df_overextended)
        print(f"   ✅ Generated {len(strategies_df)} trade strategies")
        
        # Generate trade plan
        print("\n3. Creating trade plan...")
        self.generate_trade_plan(strategies_df)
        
        print("\n" + "=" * 80)
        print("✅ Analysis complete!")
        print("\n📚 NEXT STEPS:")
        print("   1. Review trade cards above")
        print("   2. Check your broker for actual options prices")
        print("   3. Verify implied volatility (IV) levels")
        print("   4. Size positions according to risk tolerance")
        print("   5. Set alerts for entry prices")
        print("   6. Monitor pre-market action tomorrow")
        print("\n⚠️  DISCLAIMER: This is for educational purposes. Always do your own due diligence!")


def main():
    """Main execution"""
    analyzer = OptionsStrategyAnalyzer()
    analyzer.run_analysis()


if __name__ == "__main__":
    main()
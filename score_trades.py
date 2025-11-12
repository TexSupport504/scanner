"""
Comprehensive Scoring System for Overextended Stock Options Trades
Ranks opportunities based on multiple technical and risk factors
"""

import pandas as pd
import sqlite3
from datetime import datetime
import os


class TradeScorer:
    def __init__(self, db_path="data/scanner.db"):
        self.db_path = db_path
        
        # Scoring weights (total = 100 points)
        self.weights = {
            'overextension_score': 20,      # How far beyond threshold
            'rsi_extreme_score': 20,        # RSI overbought level
            'risk_reward_score': 25,        # Risk/Reward ratio quality
            'volatility_score': 15,         # ATR relative to price
            'momentum_score': 10,           # Recent price action
            'liquidity_score': 10           # Price level (proxy for options liquidity)
        }
    
    def get_overextended_stocks(self):
        """Get all overextended stocks with complete data"""
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
                hit_high,
                hit_low,
                created_at
            FROM scan_results
            WHERE is_overextended = 1
            ORDER BY created_at DESC
        """
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        return df
    
    def calculate_overextension_score(self, distance_pct):
        """
        Score based on how far price is beyond threshold
        0-20 points: Higher distance = higher probability of reversion
        """
        if distance_pct >= 5:
            return 20  # Extremely overextended
        elif distance_pct >= 3:
            return 18
        elif distance_pct >= 2:
            return 15
        elif distance_pct >= 1:
            return 12
        else:
            return 8  # Just barely overextended
    
    def calculate_rsi_score(self, rsi):
        """
        Score based on RSI overbought level
        0-20 points: Higher RSI = stronger reversal signal
        """
        if rsi >= 90:
            return 20  # Extreme overbought
        elif rsi >= 85:
            return 18
        elif rsi >= 80:
            return 16
        elif rsi >= 75:
            return 13
        elif rsi >= 70:
            return 10
        else:
            return 5  # Moderately overbought
    
    def calculate_risk_reward_score(self, current_price, threshold, swing_low):
        """
        Score based on risk/reward ratio
        0-25 points: Better R/R = higher score
        """
        risk = current_price - threshold
        reward = threshold - swing_low
        
        if risk <= 0:
            return 0
        
        rr_ratio = reward / risk
        
        if rr_ratio >= 15:
            return 25  # Excellent R/R
        elif rr_ratio >= 10:
            return 22
        elif rr_ratio >= 7:
            return 19
        elif rr_ratio >= 5:
            return 16
        elif rr_ratio >= 3:
            return 13
        else:
            return 8  # Marginal R/R
    
    def calculate_volatility_score(self, atr, current_price):
        """
        Score based on ATR as percentage of price
        0-15 points: Moderate volatility preferred (tradeable but not crazy)
        """
        atr_pct = (atr / current_price) * 100
        
        if 2 <= atr_pct <= 4:
            return 15  # Sweet spot - good movement potential
        elif 1.5 <= atr_pct < 2 or 4 < atr_pct <= 5:
            return 12  # Acceptable
        elif 1 <= atr_pct < 1.5 or 5 < atr_pct <= 6:
            return 9   # Less ideal
        elif atr_pct < 1:
            return 5   # Too low - small moves
        else:
            return 3   # Too high - very risky
    
    def calculate_momentum_score(self, distance_pct, rsi):
        """
        Score based on momentum exhaustion signals
        0-10 points: Signs that momentum is exhausted
        """
        # Combining overextension with extreme RSI
        momentum_signal = (distance_pct / 5) * (rsi / 100) * 10
        
        if momentum_signal >= 9:
            return 10  # Strong exhaustion signals
        elif momentum_signal >= 7:
            return 8
        elif momentum_signal >= 5:
            return 6
        elif momentum_signal >= 3:
            return 4
        else:
            return 2
    
    def calculate_liquidity_score(self, current_price):
        """
        Score based on stock price (proxy for options liquidity)
        0-10 points: Higher priced stocks typically have better option liquidity
        """
        if current_price >= 200:
            return 10  # Excellent liquidity expected
        elif current_price >= 100:
            return 9
        elif current_price >= 50:
            return 7
        elif current_price >= 25:
            return 5
        else:
            return 3   # May have liquidity issues
    
    def score_all_trades(self, df):
        """Calculate comprehensive scores for all trades"""
        
        scores = []
        
        for idx, row in df.iterrows():
            symbol = row['symbol']
            
            # Calculate individual scores
            overextension = self.calculate_overextension_score(row['distance_pct'])
            rsi_score = self.calculate_rsi_score(row['rsi'])
            rr_score = self.calculate_risk_reward_score(
                row['current_price'], 
                row['overextended_threshold'], 
                row['swing_low']
            )
            volatility = self.calculate_volatility_score(row['atr'], row['current_price'])
            momentum = self.calculate_momentum_score(row['distance_pct'], row['rsi'])
            liquidity = self.calculate_liquidity_score(row['current_price'])
            
            # Calculate total weighted score
            total_score = (
                overextension +
                rsi_score +
                rr_score +
                volatility +
                momentum +
                liquidity
            )
            
            # Calculate component percentages
            components = {
                'overextension_pct': (overextension / self.weights['overextension_score']) * 100,
                'rsi_pct': (rsi_score / self.weights['rsi_extreme_score']) * 100,
                'risk_reward_pct': (rr_score / self.weights['risk_reward_score']) * 100,
                'volatility_pct': (volatility / self.weights['volatility_score']) * 100,
                'momentum_pct': (momentum / self.weights['momentum_score']) * 100,
                'liquidity_pct': (liquidity / self.weights['liquidity_score']) * 100
            }
            
            # Determine trade grade
            if total_score >= 90:
                grade = 'A+'
                quality = 'EXCELLENT'
            elif total_score >= 85:
                grade = 'A'
                quality = 'EXCELLENT'
            elif total_score >= 80:
                grade = 'A-'
                quality = 'VERY GOOD'
            elif total_score >= 75:
                grade = 'B+'
                quality = 'GOOD'
            elif total_score >= 70:
                grade = 'B'
                quality = 'GOOD'
            elif total_score >= 65:
                grade = 'B-'
                quality = 'ACCEPTABLE'
            elif total_score >= 60:
                grade = 'C+'
                quality = 'FAIR'
            else:
                grade = 'C'
                quality = 'MARGINAL'
            
            scores.append({
                'symbol': symbol,
                'total_score': round(total_score, 1),
                'grade': grade,
                'quality': quality,
                'overextension_score': overextension,
                'rsi_score': rsi_score,
                'risk_reward_score': rr_score,
                'volatility_score': volatility,
                'momentum_score': momentum,
                'liquidity_score': liquidity,
                'overextension_pct': round(components['overextension_pct'], 1),
                'rsi_pct': round(components['rsi_pct'], 1),
                'risk_reward_pct': round(components['risk_reward_pct'], 1),
                'volatility_pct': round(components['volatility_pct'], 1),
                'momentum_pct': round(components['momentum_pct'], 1),
                'liquidity_pct': round(components['liquidity_pct'], 1),
                # Keep original data
                'current_price': row['current_price'],
                'threshold': row['overextended_threshold'],
                'swing_low': row['swing_low'],
                'rsi': row['rsi'],
                'atr': row['atr'],
                'distance_pct': row['distance_pct']
            })
        
        return pd.DataFrame(scores)
    
    def generate_ranked_report(self, scores_df):
        """Generate comprehensive ranked report"""
        
        # Sort by total score (highest first)
        scores_df = scores_df.sort_values('total_score', ascending=False)
        
        print("\n" + "=" * 100)
        print("📊 COMPREHENSIVE TRADE SCORING SYSTEM")
        print(f"📅 Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print("=" * 100)
        
        print("\n🎯 SCORING METHODOLOGY (100 Points Total):")
        print("   • Overextension (20 pts):  How far beyond threshold")
        print("   • RSI Extreme (20 pts):    Overbought level intensity")
        print("   • Risk/Reward (25 pts):    Quality of setup")
        print("   • Volatility (15 pts):     ATR relative to price")
        print("   • Momentum (10 pts):       Exhaustion signals")
        print("   • Liquidity (10 pts):      Options trading viability")
        
        print("\n" + "=" * 100)
        print("🏆 RANKED TRADE OPPORTUNITIES")
        print("=" * 100)
        
        for rank, (idx, trade) in enumerate(scores_df.iterrows(), 1):
            self._print_trade_scorecard(trade, rank)
        
        # Summary statistics
        print("\n" + "=" * 100)
        print("📈 SCORING DISTRIBUTION")
        print("=" * 100)
        
        grade_counts = scores_df['grade'].value_counts().sort_index()
        print("\n🎓 GRADE DISTRIBUTION:")
        for grade, count in grade_counts.items():
            quality = scores_df[scores_df['grade'] == grade]['quality'].iloc[0]
            print(f"   {grade} ({quality}): {count} opportunities")
        
        print(f"\n📊 STATISTICS:")
        print(f"   Average Score: {scores_df['total_score'].mean():.1f}")
        print(f"   Median Score:  {scores_df['total_score'].median():.1f}")
        print(f"   Highest Score: {scores_df['total_score'].max():.1f} ({scores_df.iloc[0]['symbol']})")
        print(f"   Lowest Score:  {scores_df['total_score'].min():.1f} ({scores_df.iloc[-1]['symbol']})")
        
        # Top 3 recommendations
        print("\n" + "=" * 100)
        print("⭐ TOP 3 RECOMMENDED TRADES")
        print("=" * 100)
        
        top_3 = scores_df.head(3)
        for rank, (idx, trade) in enumerate(top_3.iterrows(), 1):
            print(f"\n🎯 #{rank} {trade['symbol']} - Score: {trade['total_score']}/100 ({trade['grade']})")
            print(f"   Quality: {trade['quality']}")
            print(f"   Price: ${trade['current_price']:.2f} → ${trade['threshold']:.2f}")
            print(f"   RSI: {trade['rsi']:.1f} | Distance: {trade['distance_pct']:.2f}%")
            print(f"   Strengths: ", end="")
            
            # Identify strongest components
            strengths = []
            if trade['rsi_pct'] >= 80:
                strengths.append("Extreme RSI")
            if trade['risk_reward_pct'] >= 80:
                strengths.append("Excellent R/R")
            if trade['overextension_pct'] >= 80:
                strengths.append("Highly Overextended")
            if trade['volatility_pct'] >= 80:
                strengths.append("Ideal Volatility")
            
            print(", ".join(strengths) if strengths else "Balanced setup")
        
        # Export to CSV
        output_file = "data/exports/trade_scores_ranked.csv"
        scores_df.to_csv(output_file, index=False)
        print(f"\n💾 Scored rankings exported to: {output_file}")
        
        print("\n" + "=" * 100)
    
    def _print_trade_scorecard(self, trade, rank):
        """Print detailed scorecard for each trade"""
        
        # Rank indicator
        if rank == 1:
            rank_icon = "🥇"
        elif rank == 2:
            rank_icon = "🥈"
        elif rank == 3:
            rank_icon = "🥉"
        else:
            rank_icon = f"#{rank}"
        
        print(f"\n{rank_icon} {trade['symbol']} - TOTAL SCORE: {trade['total_score']}/100 ({trade['grade']}) - {trade['quality']}")
        print("-" * 100)
        
        # Score breakdown
        print(f"\n   📊 SCORE BREAKDOWN:")
        print(f"      Overextension:  {trade['overextension_score']:>2}/20 ({trade['overextension_pct']:>5.1f}%) ", end="")
        self._print_score_bar(trade['overextension_pct'])
        
        print(f"      RSI Extreme:    {trade['rsi_score']:>2}/20 ({trade['rsi_pct']:>5.1f}%) ", end="")
        self._print_score_bar(trade['rsi_pct'])
        
        print(f"      Risk/Reward:    {trade['risk_reward_score']:>2}/25 ({trade['risk_reward_pct']:>5.1f}%) ", end="")
        self._print_score_bar(trade['risk_reward_pct'])
        
        print(f"      Volatility:     {trade['volatility_score']:>2}/15 ({trade['volatility_pct']:>5.1f}%) ", end="")
        self._print_score_bar(trade['volatility_pct'])
        
        print(f"      Momentum:       {trade['momentum_score']:>2}/10 ({trade['momentum_pct']:>5.1f}%) ", end="")
        self._print_score_bar(trade['momentum_pct'])
        
        print(f"      Liquidity:      {trade['liquidity_score']:>2}/10 ({trade['liquidity_pct']:>5.1f}%) ", end="")
        self._print_score_bar(trade['liquidity_pct'])
        
        # Trade details
        print(f"\n   💰 TRADE DETAILS:")
        print(f"      Current Price:  ${trade['current_price']:>8.2f}")
        print(f"      Threshold:      ${trade['threshold']:>8.2f} (Target)")
        print(f"      Swing Low:      ${trade['swing_low']:>8.2f} (Support)")
        print(f"      RSI:            {trade['rsi']:>8.1f}")
        print(f"      ATR:            ${trade['atr']:>8.2f}")
        print(f"      Distance:       {trade['distance_pct']:>7.2f}%")
    
    def _print_score_bar(self, percentage):
        """Print visual score bar"""
        bar_length = 30
        filled = int((percentage / 100) * bar_length)
        bar = "█" * filled + "░" * (bar_length - filled)
        
        # Color coding (using text)
        if percentage >= 90:
            status = "🔥"
        elif percentage >= 75:
            status = "✅"
        elif percentage >= 50:
            status = "⚡"
        else:
            status = "⚠️"
        
        print(f"{bar} {status}")
    
    def run_scoring(self):
        """Run complete scoring analysis"""
        print("🚀 Starting Comprehensive Trade Scoring...")
        print("=" * 100)
        
        # Get overextended stocks
        print("\n1. Loading overextended stocks...")
        df = self.get_overextended_stocks()
        
        if df.empty:
            print("   ❌ No overextended stocks found.")
            return
        
        print(f"   ✅ Found {len(df)} overextended stocks")
        
        # Calculate scores
        print("\n2. Calculating comprehensive scores...")
        scores_df = self.score_all_trades(df)
        print(f"   ✅ Scored {len(scores_df)} opportunities")
        
        # Generate report
        print("\n3. Generating ranked report...")
        self.generate_ranked_report(scores_df)
        
        print("\n" + "=" * 100)
        print("✅ Scoring analysis complete!")
        print("\n📚 USE THIS TO:")
        print("   • Prioritize which trades to execute")
        print("   • Allocate position sizes (larger for higher scores)")
        print("   • Identify strongest setups")
        print("   • Focus on A-grade opportunities")


def main():
    """Main execution"""
    scorer = TradeScorer()
    scorer.run_scoring()


if __name__ == "__main__":
    main()
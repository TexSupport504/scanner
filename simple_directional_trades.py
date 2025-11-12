"""
Simple Directional Options Trading Analysis
===========================================
Focuses on basic Level 1 strategies:
- Long PUT for overbought stocks (RSI >= 90 or overextended)
- Long CALL for oversold stocks (RSI <= 10)

Simple approach: Buy options in direction of mean reversion
"""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional


class SimpleDirectionalAnalyzer:
    """Analyzes stocks for simple long put/call opportunities"""
    
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            # Default to scanner.db in the data directory
            script_dir = Path(__file__).parent
            self.db_path = script_dir / "data" / "scanner.db"
        else:
            self.db_path = Path(db_path)
        
    def get_put_opportunities(self):
        """Get stocks suitable for LONG PUT (bearish mean reversion)"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get overbought or overextended stocks
        cursor.execute("""
            SELECT DISTINCT
                symbol,
                current_price,
                latest_rsi,
                latest_atr,
                is_overextended,
                overextended_threshold,
                swing_low,
                scan_date
            FROM scan_results
            WHERE (latest_rsi >= 70 OR is_overextended = 1)
            AND scan_date = (SELECT MAX(scan_date) FROM scan_results)
            AND current_price IS NOT NULL
            AND latest_atr IS NOT NULL
            GROUP BY symbol
            ORDER BY latest_rsi DESC
        """)
        
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results
    
    def get_call_opportunities(self):
        """Get stocks suitable for LONG CALL (bullish mean reversion)"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get oversold stocks
        cursor.execute("""
            SELECT DISTINCT
                symbol,
                current_price,
                latest_rsi,
                latest_atr,
                swing_low,
                scan_date
            FROM scan_results
            WHERE latest_rsi <= 30
            AND scan_date = (SELECT MAX(scan_date) FROM scan_results)
            AND current_price IS NOT NULL
            AND latest_atr IS NOT NULL
            GROUP BY symbol
            ORDER BY latest_rsi ASC
        """)
        
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results
    
    def analyze_long_put(self, stock: dict):
        """Analyze a simple LONG PUT setup"""
        price = stock['current_price']
        atr = stock['latest_atr']
        rsi = stock['latest_rsi']
        
        # Calculate expected downside target
        # If overextended, use that threshold; otherwise use 2x ATR pullback
        if stock.get('overextended_threshold'):
            downside_target = stock['overextended_threshold']
        else:
            downside_target = price - (2 * atr)
        
        # Use swing low as additional support if available and lower
        if stock.get('swing_low') and stock['swing_low'] < downside_target:
            downside_target = stock['swing_low']
        
        # Stop loss: price continues higher
        stop_loss = price + (1.5 * atr)
        
        # Expected profit/loss
        expected_move = price - downside_target  # Positive value = downward move
        max_risk_pct = ((stop_loss - price) / price) * 100
        expected_reward_pct = (expected_move / price) * 100
        
        # Option strategy details
        days_to_expiry = 30  # ~1 month
        strike_selection = "ATM or slightly OTM"
        
        # Confidence scoring
        confidence = 0
        reasons = []
        
        if rsi >= 90:
            confidence += 40
            reasons.append(f"Extreme RSI ({rsi:.1f})")
        elif rsi >= 80:
            confidence += 30
            reasons.append(f"Very overbought ({rsi:.1f})")
        elif rsi >= 70:
            confidence += 20
            reasons.append(f"Overbought ({rsi:.1f})")
            
        if stock.get('is_overextended'):
            confidence += 30
            reasons.append("Overextended above threshold")
            
        atr_pct = (atr / price) * 100
        if 2 <= atr_pct <= 5:
            confidence += 20
            reasons.append(f"Good volatility ({atr_pct:.1f}%)")
        elif atr_pct > 5:
            confidence += 10
            reasons.append(f"High volatility ({atr_pct:.1f}%)")
            
        if expected_reward_pct > max_risk_pct * 2:
            confidence += 10
            reasons.append("Favorable R/R ratio")
            
        return {
            'symbol': stock['symbol'],
            'strategy': 'LONG PUT',
            'direction': 'BEARISH',
            'entry_price': price,
            'target_price': downside_target,
            'stop_loss': stop_loss,
            'expected_move': expected_move,
            'expected_move_pct': expected_reward_pct,
            'max_risk_pct': max_risk_pct,
            'rsi': rsi,
            'atr': atr,
            'atr_pct': atr_pct,
            'days_to_expiry': days_to_expiry,
            'strike_selection': strike_selection,
            'confidence': min(confidence, 100),
            'reasons': reasons
        }
    
    def analyze_long_call(self, stock: dict):
        """Analyze a simple LONG CALL setup"""
        price = stock['current_price']
        atr = stock['latest_atr']
        rsi = stock['latest_rsi']
        
        # Calculate expected bounce
        upside_target = price + (2 * atr)
        
        # Stop loss: price continues lower
        stop_loss = price - (1.5 * atr)
        
        # Expected profit/loss
        expected_move = upside_target - price
        max_risk_pct = ((price - stop_loss) / price) * 100
        expected_reward_pct = (expected_move / price) * 100
        
        # Option strategy details
        days_to_expiry = 30  # ~1 month
        strike_selection = "ATM or slightly OTM"
        
        # Confidence scoring
        confidence = 0
        reasons = []
        
        if rsi <= 10:
            confidence += 40
            reasons.append(f"Extreme oversold ({rsi:.1f})")
        elif rsi <= 20:
            confidence += 30
            reasons.append(f"Very oversold ({rsi:.1f})")
        elif rsi <= 30:
            confidence += 20
            reasons.append(f"Oversold ({rsi:.1f})")
            
        atr_pct = (atr / price) * 100
        if 2 <= atr_pct <= 5:
            confidence += 20
            reasons.append(f"Good volatility ({atr_pct:.1f}%)")
        elif atr_pct > 5:
            confidence += 10
            reasons.append(f"High volatility ({atr_pct:.1f}%)")
            
        if expected_reward_pct > max_risk_pct * 2:
            confidence += 10
            reasons.append("Favorable R/R ratio")
            
        # Bonus for being near swing low
        if stock.get('swing_low') and price <= stock['swing_low'] * 1.05:
            confidence += 20
            reasons.append("Near recent swing low")
            
        return {
            'symbol': stock['symbol'],
            'strategy': 'LONG CALL',
            'direction': 'BULLISH',
            'entry_price': price,
            'target_price': upside_target,
            'stop_loss': stop_loss,
            'expected_move': expected_move,
            'expected_move_pct': expected_reward_pct,
            'max_risk_pct': max_risk_pct,
            'rsi': rsi,
            'atr': atr,
            'atr_pct': atr_pct,
            'days_to_expiry': days_to_expiry,
            'strike_selection': strike_selection,
            'confidence': min(confidence, 100),
            'reasons': reasons
        }
    
    def generate_trade_card(self, analysis: dict):
        """Generate a visual trade card"""
        card = []
        card.append("=" * 80)
        card.append(f"📊 {analysis['symbol']} - {analysis['strategy']}")
        card.append(f"Direction: {analysis['direction']} | Confidence: {analysis['confidence']}/100")
        card.append("=" * 80)
        card.append("")
        
        # Entry/Exit levels
        card.append("💰 TRADE LEVELS:")
        card.append(f"   Entry Price:    ${analysis['entry_price']:>8.2f}")
        card.append(f"   Target Price:   ${analysis['target_price']:>8.2f}  ({analysis['expected_move_pct']:+.1f}%)")
        card.append(f"   Stop Loss:      ${analysis['stop_loss']:>8.2f}  ({-analysis['max_risk_pct']:.1f}%)")
        card.append("")
        
        # Technical indicators
        card.append("📈 TECHNICAL INDICATORS:")
        card.append(f"   RSI:            {analysis['rsi']:>8.1f}")
        card.append(f"   ATR:            ${analysis['atr']:>8.2f}  ({analysis['atr_pct']:.1f}% of price)")
        card.append("")
        
        # Options setup
        card.append("🎯 OPTIONS SETUP:")
        card.append(f"   Strategy:       {analysis['strategy']}")
        card.append(f"   Strike:         {analysis['strike_selection']}")
        card.append(f"   Expiration:     ~{analysis['days_to_expiry']} days out")
        card.append("")
        
        # Confidence reasons
        card.append("✅ SETUP QUALITY:")
        for reason in analysis['reasons']:
            card.append(f"   • {reason}")
        card.append("")
        
        # Risk/Reward
        rr_ratio = analysis['expected_move_pct'] / analysis['max_risk_pct'] if analysis['max_risk_pct'] > 0 else 0
        card.append("⚖️  RISK/REWARD:")
        card.append(f"   Potential Gain:  {analysis['expected_move_pct']:>6.1f}%")
        card.append(f"   Potential Loss:  {analysis['max_risk_pct']:>6.1f}%")
        card.append(f"   R/R Ratio:       {rr_ratio:>6.1f}:1")
        card.append("")
        
        return "\n".join(card)
    
    def run_analysis(self):
        """Run complete simple directional analysis"""
        print("\n" + "=" * 80)
        print("🎯 SIMPLE DIRECTIONAL OPTIONS STRATEGY ANALYZER")
        print("=" * 80)
        print("\nStrategy: Buy directional options for mean reversion setups")
        print("Level: 1 (Basic long puts and calls)")
        print("")
        
        # Analyze LONG PUT opportunities
        print("=" * 80)
        print("🔻 LONG PUT OPPORTUNITIES (Bearish Mean Reversion)")
        print("=" * 80)
        print("")
        
        put_stocks = self.get_put_opportunities()
        put_analyses = []
        
        if put_stocks:
            print(f"Found {len(put_stocks)} overbought/overextended stocks\n")
            
            for stock in put_stocks:
                analysis = self.analyze_long_put(stock)
                put_analyses.append(analysis)
            
            # Sort by confidence
            put_analyses.sort(key=lambda x: x['confidence'], reverse=True)
            
            # Show top opportunities
            for i, analysis in enumerate(put_analyses[:10], 1):  # Top 10
                print(f"\n{'🥇' if i == 1 else '🥈' if i == 2 else '🥉' if i == 3 else f'#{i}'}")
                print(self.generate_trade_card(analysis))
        else:
            print("No overbought stocks found currently.\n")
        
        # Analyze LONG CALL opportunities
        print("\n" + "=" * 80)
        print("🔺 LONG CALL OPPORTUNITIES (Bullish Mean Reversion)")
        print("=" * 80)
        print("")
        
        call_stocks = self.get_call_opportunities()
        call_analyses = []
        
        if call_stocks:
            print(f"Found {len(call_stocks)} oversold stocks\n")
            
            for stock in call_stocks:
                analysis = self.analyze_long_call(stock)
                call_analyses.append(analysis)
            
            # Sort by confidence
            call_analyses.sort(key=lambda x: x['confidence'], reverse=True)
            
            # Show top opportunities
            for i, analysis in enumerate(call_analyses[:10], 1):  # Top 10
                print(f"\n{'🥇' if i == 1 else '🥈' if i == 2 else '🥉' if i == 3 else f'#{i}'}")
                print(self.generate_trade_card(analysis))
        else:
            print("No oversold stocks found currently.\n")
        
        # Summary
        print("\n" + "=" * 80)
        print("📊 SUMMARY")
        print("=" * 80)
        print(f"\nLONG PUT Opportunities:  {len(put_analyses)}")
        print(f"LONG CALL Opportunities: {len(call_analyses)}")
        print(f"\nTotal Setups:            {len(put_analyses) + len(call_analyses)}")
        
        if put_analyses:
            avg_confidence_put = sum(a['confidence'] for a in put_analyses) / len(put_analyses)
            print(f"\nAverage PUT Confidence:  {avg_confidence_put:.0f}/100")
            print(f"Best PUT Setup:          {put_analyses[0]['symbol']} ({put_analyses[0]['confidence']}/100)")
        
        if call_analyses:
            avg_confidence_call = sum(a['confidence'] for a in call_analyses) / len(call_analyses)
            print(f"\nAverage CALL Confidence: {avg_confidence_call:.0f}/100")
            print(f"Best CALL Setup:         {call_analyses[0]['symbol']} ({call_analyses[0]['confidence']}/100)")
        
        print("\n" + "=" * 80)
        print("\n💡 TRADING APPROACH:")
        print("   1. Focus on highest confidence setups (70+ score)")
        print("   2. Use ATM or slightly OTM strikes for better probability")
        print("   3. Target 30-45 days to expiration for time decay balance")
        print("   4. Risk 1-2% of portfolio per trade")
        print("   5. Set stop loss if underlying breaches stop level")
        print("   6. Take profits at 50-100% gain or near target price")
        print("\n" + "=" * 80)


if __name__ == "__main__":
    analyzer = SimpleDirectionalAnalyzer()
    analyzer.run_analysis()

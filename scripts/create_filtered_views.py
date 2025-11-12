"""
Create pre-filtered CSV views for Data Wrangler
These files auto-update each time you run this script after a scan
"""
import pandas as pd
from pathlib import Path

# Load the main scan results
df = pd.read_csv('data/exports/daily_scan_results.csv')

# Create views directory
views_dir = Path('data/exports/views')
views_dir.mkdir(exist_ok=True)

print(f"Creating filtered views from {len(df)} total stocks...\n")

# View 1: Extreme Overbought (RSI >= 90)
extreme_ob = df[df['rsi'] >= 90].sort_values('rsi', ascending=False)
extreme_ob.to_csv(views_dir / '1_extreme_overbought.csv', index=False)
print(f"✓ 1_extreme_overbought.csv - {len(extreme_ob)} stocks (RSI >= 90)")

# View 2: Overextended (is_overextended = 1)
overextended = df[df['is_overextended'] == 1].sort_values('rsi', ascending=False)
overextended.to_csv(views_dir / '2_overextended.csv', index=False)
print(f"✓ 2_overextended.csv - {len(overextended)} stocks (Price > Threshold)")

# View 3: Best PUT Setups (Overextended + RSI 80-95 + ATR 2-5%)
best_puts = df[
    (df['is_overextended'] == 1) & 
    (df['rsi'] >= 80) & 
    (df['rsi'] <= 95) & 
    (df['atr_pct'] >= 2.0) & 
    (df['atr_pct'] <= 5.0)
].sort_values('rsi', ascending=False)
best_puts.to_csv(views_dir / '3_best_put_setups.csv', index=False)
print(f"✓ 3_best_put_setups.csv - {len(best_puts)} stocks (Ideal PUT conditions)")

# View 4: Overbought (RSI 70-90)
overbought = df[(df['rsi'] >= 70) & (df['rsi'] < 90)].sort_values('rsi', ascending=False)
overbought.to_csv(views_dir / '4_overbought.csv', index=False)
print(f"✓ 4_overbought.csv - {len(overbought)} stocks (RSI 70-90)")

# View 5: Extreme Oversold (RSI <= 10)
extreme_os = df[df['rsi'] <= 10].sort_values('rsi')
extreme_os.to_csv(views_dir / '5_extreme_oversold.csv', index=False)
print(f"✓ 5_extreme_oversold.csv - {len(extreme_os)} stocks (RSI <= 10)")

# View 6: Oversold (RSI 10-30)
oversold = df[(df['rsi'] > 10) & (df['rsi'] <= 30)].sort_values('rsi')
oversold.to_csv(views_dir / '6_oversold.csv', index=False)
print(f"✓ 6_oversold.csv - {len(oversold)} stocks (RSI 10-30)")

# View 7: Best CALL Setups (Oversold + RSI 5-20 + ATR 2-5%)
best_calls = df[
    (df['rsi'] >= 5) & 
    (df['rsi'] <= 20) & 
    (df['atr_pct'] >= 2.0) & 
    (df['atr_pct'] <= 5.0)
].sort_values('rsi')
best_calls.to_csv(views_dir / '7_best_call_setups.csv', index=False)
print(f"✓ 7_best_call_setups.csv - {len(best_calls)} stocks (Ideal CALL conditions)")

# View 8: Priority 1 Only (Highest priority trades)
priority_1 = df[df['priority'] == 1].sort_values('rsi', ascending=False)
priority_1.to_csv(views_dir / '8_priority_1.csv', index=False)
print(f"✓ 8_priority_1.csv - {len(priority_1)} stocks (Priority 1)")

# View 9: Ideal Volatility (ATR 2-5%)
ideal_vol = df[(df['atr_pct'] >= 2.0) & (df['atr_pct'] <= 5.0)].sort_values('rsi', ascending=False)
ideal_vol.to_csv(views_dir / '9_ideal_volatility.csv', index=False)
print(f"✓ 9_ideal_volatility.csv - {len(ideal_vol)} stocks (ATR 2-5%)")

# View 10: High Priced (Over $200 - good liquidity)
high_priced = df[df['price'] > 200].sort_values('rsi', ascending=False)
high_priced.to_csv(views_dir / '10_high_priced.csv', index=False)
print(f"✓ 10_high_priced.csv - {len(high_priced)} stocks (Price > $200)")

# View 11: Mid Priced ($50-$200)
mid_priced = df[(df['price'] >= 50) & (df['price'] <= 200)].sort_values('rsi', ascending=False)
mid_priced.to_csv(views_dir / '11_mid_priced.csv', index=False)
print(f"✓ 11_mid_priced.csv - {len(mid_priced)} stocks (Price $50-$200)")

# View 12: Low Priced (Under $50)
low_priced = df[df['price'] < 50].sort_values('rsi', ascending=False)
low_priced.to_csv(views_dir / '12_low_priced.csv', index=False)
print(f"✓ 12_low_priced.csv - {len(low_priced)} stocks (Price < $50)")

# View 13: All LONG PUT Suggestions
long_puts = df[df['suggested_trade'] == 'LONG PUT'].sort_values('rsi', ascending=False)
long_puts.to_csv(views_dir / '13_long_put_suggestions.csv', index=False)
print(f"✓ 13_long_put_suggestions.csv - {len(long_puts)} stocks (Suggested: LONG PUT)")

# View 14: All LONG CALL Suggestions
long_calls = df[df['suggested_trade'] == 'LONG CALL'].sort_values('rsi')
long_calls.to_csv(views_dir / '14_long_call_suggestions.csv', index=False)
print(f"✓ 14_long_call_suggestions.csv - {len(long_calls)} stocks (Suggested: LONG CALL)")

print(f"\n✅ Created 14 filtered views in: {views_dir.absolute()}")
print("\nTo use: Right-click any CSV file in data/exports/views/ and select 'Open in Data Wrangler'")
print("Run this script after each scan to refresh all views!")

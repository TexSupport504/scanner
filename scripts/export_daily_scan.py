"""
Export Daily Scan Results to Single CSV
========================================
Creates/updates ONE file: daily_scan_results.csv
Keep this file open in Data Wrangler and refresh after each scan
"""

import sqlite3
import pandas as pd
from pathlib import Path
from datetime import datetime


def export_daily_scan():
    """Export latest scan results to single CSV file"""
    
    db_path = Path(__file__).parent.parent / "data" / "scanner.db"
    output_file = Path(__file__).parent.parent / "data" / "exports" / "daily_scan_results.csv"
    
    # Ensure exports directory exists
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    print("\n" + "="*80)
    print("📊 EXPORTING DAILY SCAN RESULTS")
    print("="*80)
    
    conn = sqlite3.connect(db_path)
    
    # Get the latest scan results with all relevant data
    query = """
    SELECT 
        sr.scan_date,
        sr.symbol,
        sr.current_price as price,
        sr.latest_rsi as rsi,
        sr.latest_atr as atr,
        ROUND((sr.latest_atr / sr.current_price * 100), 2) as atr_pct,
        sr.is_overextended,
        sr.overextended_threshold as threshold,
        sr.swing_low,
        CASE 
            WHEN sr.is_overextended = 1 THEN 
                ROUND(((sr.current_price - sr.overextended_threshold) / sr.current_price * 100), 2)
            ELSE NULL 
        END as distance_from_threshold_pct,
        CASE
            WHEN sr.latest_rsi >= 90 THEN 'Extreme Overbought'
            WHEN sr.latest_rsi >= 70 THEN 'Overbought'
            WHEN sr.latest_rsi <= 10 THEN 'Extreme Oversold'
            WHEN sr.latest_rsi <= 30 THEN 'Oversold'
            ELSE 'Neutral'
        END as signal,
        CASE
            WHEN sr.latest_rsi >= 90 OR sr.is_overextended = 1 THEN 'LONG PUT'
            WHEN sr.latest_rsi <= 30 THEN 'LONG CALL'
            ELSE NULL
        END as suggested_trade,
        CASE
            WHEN sr.latest_rsi >= 90 THEN 1
            WHEN sr.latest_rsi >= 70 OR sr.is_overextended = 1 THEN 2
            WHEN sr.latest_rsi <= 10 THEN 1
            WHEN sr.latest_rsi <= 30 THEN 2
            ELSE 3
        END as priority,
        sr.created_at
    FROM scan_results sr
    WHERE sr.scan_date = (SELECT MAX(scan_date) FROM scan_results)
    AND sr.current_price IS NOT NULL
    AND sr.latest_atr IS NOT NULL
    ORDER BY 
        CASE
            WHEN sr.latest_rsi >= 90 THEN 1
            WHEN sr.latest_rsi >= 70 OR sr.is_overextended = 1 THEN 2
            WHEN sr.latest_rsi <= 10 THEN 3
            WHEN sr.latest_rsi <= 30 THEN 4
            ELSE 5
        END,
        sr.latest_rsi DESC
    """
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    if df.empty:
        print("❌ No scan data found!")
        return
    
    # Add calculated fields
    df['scan_timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Export to CSV (overwrites existing file)
    df.to_csv(output_file, index=False)
    
    # Print summary
    print(f"\n✅ Exported to: {output_file}")
    print(f"\n📊 SUMMARY:")
    print(f"   Total stocks:      {len(df)}")
    print(f"   Scan date:         {df['scan_date'].iloc[0]}")
    print(f"\n🎯 TRADING OPPORTUNITIES:")
    
    extreme_overbought = len(df[df['rsi'] >= 90])
    overbought = len(df[(df['rsi'] >= 70) & (df['rsi'] < 90)])
    overextended = len(df[df['is_overextended'] == 1])
    extreme_oversold = len(df[df['rsi'] <= 10])
    oversold = len(df[(df['rsi'] > 10) & (df['rsi'] <= 30)])
    
    print(f"   🔴 Extreme Overbought (RSI≥90):     {extreme_overbought}")
    print(f"   🟠 Overbought (RSI 70-90):          {overbought}")
    print(f"   ⚡ Overextended:                    {overextended}")
    print(f"   🟢 Extreme Oversold (RSI≤10):       {extreme_oversold}")
    print(f"   🟡 Oversold (RSI 10-30):            {oversold}")
    
    # Show top opportunities
    print(f"\n🏆 TOP 5 LONG PUT OPPORTUNITIES:")
    top_puts = df[df['suggested_trade'] == 'LONG PUT'].head(5)
    for idx, row in top_puts.iterrows():
        overext_flag = "⚡" if row['is_overextended'] == 1 else ""
        print(f"   {overext_flag} {row['symbol']:6s} | RSI: {row['rsi']:5.1f} | Price: ${row['price']:8.2f} | ATR: {row['atr_pct']:4.1f}%")
    
    print(f"\n🏆 TOP 5 LONG CALL OPPORTUNITIES:")
    top_calls = df[df['suggested_trade'] == 'LONG CALL'].head(5)
    for idx, row in top_calls.iterrows():
        print(f"   {row['symbol']:6s} | RSI: {row['rsi']:5.1f} | Price: ${row['price']:8.2f} | ATR: {row['atr_pct']:4.1f}%")
    
    print("\n" + "="*80)
    print("💡 USAGE:")
    print(f"   1. Open in VS Code Data Wrangler")
    print(f"   2. Run scanner again")
    print(f"   3. Right-click file → Refresh Data Wrangler")
    print(f"   4. Your visualizations will update automatically!")
    print("="*80 + "\n")


if __name__ == "__main__":
    export_daily_scan()

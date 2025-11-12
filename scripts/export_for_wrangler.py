"""
Export scan results to CSV for viewing in Data Wrangler
"""

import sqlite3
import pandas as pd
import os

# Database path
db_path = "data/scanner.db"

def export_to_csv():
    """Export all scan data to CSV files for Data Wrangler"""
    
    if not os.path.exists(db_path):
        print("❌ Database not found. Run a scan first.")
        return
    
    conn = sqlite3.connect(db_path)
    
    print("📊 Exporting data from database to CSV...")
    print("=" * 60)
    
    # Export scan results
    print("\n1. Scan Results (Latest)")
    df_scans = pd.read_sql_query("""
        SELECT 
            scan_date,
            symbol,
            latest_rsi as rsi,
            latest_atr as atr,
            hit_high,
            hit_low,
            is_overextended,
            swing_low,
            overextended_threshold,
            current_price,
            status,
            created_at
        FROM scan_results
        ORDER BY created_at DESC
        LIMIT 500
    """, conn)
    
    output_file = "data/exports/scan_results_latest.csv"
    df_scans.to_csv(output_file, index=False)
    print(f"   ✅ Exported {len(df_scans)} records to: {output_file}")
    
    # Export overextended stocks only
    print("\n2. Overextended Stocks")
    df_overextended = pd.read_sql_query("""
        SELECT 
            scan_date,
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
        ORDER BY created_at DESC
        LIMIT 100
    """, conn)
    
    output_file = "data/exports/overextended_stocks.csv"
    df_overextended.to_csv(output_file, index=False)
    print(f"   ✅ Exported {len(df_overextended)} records to: {output_file}")
    
    # Export RSI extremes
    print("\n3. RSI Extremes (High/Low)")
    df_extremes = pd.read_sql_query("""
        SELECT 
            scan_date,
            symbol,
            latest_rsi as rsi,
            latest_atr as atr,
            hit_high,
            hit_low,
            current_price,
            status,
            created_at
        FROM scan_results
        WHERE hit_high = 1 OR hit_low = 1
        ORDER BY created_at DESC, latest_rsi DESC
        LIMIT 100
    """, conn)
    
    output_file = "data/exports/rsi_extremes.csv"
    df_extremes.to_csv(output_file, index=False)
    print(f"   ✅ Exported {len(df_extremes)} records to: {output_file}")
    
    # Export indicators (detailed)
    print("\n4. Technical Indicators (Latest)")
    df_indicators = pd.read_sql_query("""
        SELECT 
            i.symbol,
            i.date,
            i.rsi_14 as rsi,
            i.atr_14 as atr,
            p.close as price,
            p.high,
            p.low,
            p.volume
        FROM indicators i
        LEFT JOIN price_data p ON i.symbol = p.symbol AND i.date = p.date
        WHERE i.date >= date('now', '-7 days')
        ORDER BY i.date DESC, i.symbol
        LIMIT 5000
    """, conn)
    
    output_file = "data/exports/indicators_detailed.csv"
    df_indicators.to_csv(output_file, index=False)
    print(f"   ✅ Exported {len(df_indicators)} records to: {output_file}")
    
    # Summary statistics
    print("\n5. Summary Statistics")
    summary = pd.read_sql_query("""
        SELECT 
            COUNT(DISTINCT symbol) as total_symbols,
            AVG(latest_rsi) as avg_rsi,
            AVG(latest_atr) as avg_atr,
            SUM(CASE WHEN hit_high = 1 THEN 1 ELSE 0 END) as overbought_count,
            SUM(CASE WHEN hit_low = 1 THEN 1 ELSE 0 END) as oversold_count,
            SUM(CASE WHEN is_overextended = 1 THEN 1 ELSE 0 END) as overextended_count,
            MAX(created_at) as latest_scan
        FROM scan_results
        WHERE created_at >= datetime('now', '-1 day')
    """, conn)
    
    output_file = "data/exports/summary_stats.csv"
    summary.to_csv(output_file, index=False)
    print(f"   ✅ Exported summary to: {output_file}")
    
    conn.close()
    
    print("\n" + "=" * 60)
    print("✅ All data exported!")
    print("\n📂 To view in Data Wrangler:")
    print("   1. Right-click on any CSV file in data/exports/")
    print("   2. Select 'Open in Data Wrangler'")
    print("   3. Or use Ctrl+Shift+P → 'Data Wrangler: Open File in Data Wrangler'")
    print("\n📁 Files created:")
    print("   • scan_results_latest.csv - All recent scans")
    print("   • overextended_stocks.csv - Only overextended stocks")
    print("   • rsi_extremes.csv - RSI extreme conditions")
    print("   • indicators_detailed.csv - Full technical indicators")
    print("   • summary_stats.csv - Summary statistics")

if __name__ == "__main__":
    export_to_csv()
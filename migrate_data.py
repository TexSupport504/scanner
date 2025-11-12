"""
Data Migration Script for IB RSI Scanner
Imports existing CSV scan results into the database
"""

import pandas as pd
import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.database import ScannerDatabase
from config.settings import OUTPUT_DIR


def import_csv_scan_results(csv_file_path: str, scan_date: datetime = None):
    """
    Import CSV scan results into the database
    
    Args:
        csv_file_path: Path to CSV file with scan results
        scan_date: Date of the scan (defaults to today)
    """
    if scan_date is None:
        scan_date = datetime.now()
    
    # Initialize database
    db = ScannerDatabase()
    
    try:
        # Read CSV file
        df = pd.read_csv(csv_file_path)
        print(f"📁 Reading {len(df)} records from {csv_file_path}")
        
        # Expected columns: symbol, rsi_14, atr_14, status
        required_cols = ['symbol', 'rsi_14', 'atr_14', 'status']
        missing_cols = [col for col in required_cols if col not in df.columns]
        
        if missing_cols:
            print(f"❌ Missing required columns: {missing_cols}")
            return False
        
        imported_count = 0
        
        for _, row in df.iterrows():
            symbol = row['symbol']
            latest_rsi = row['rsi_14'] if pd.notna(row['rsi_14']) else None
            latest_atr = row['atr_14'] if pd.notna(row['atr_14']) else None
            status = row['status']
            
            # Determine hit_high and hit_low from status
            hit_high = 'RSI>=90' in str(status)
            hit_low = 'RSI<=10' in str(status)
            
            # Skip if no valid data
            if latest_rsi is None or latest_atr is None:
                continue
            
            # Save to database
            db.save_scan_result(
                scan_date=scan_date,
                symbol=symbol,
                latest_rsi=latest_rsi,
                latest_atr=latest_atr,
                hit_high=hit_high,
                hit_low=hit_low,
                status=status
            )
            
            imported_count += 1
        
        print(f"✅ Successfully imported {imported_count} scan results")
        return True
        
    except Exception as e:
        print(f"❌ Error importing CSV data: {e}")
        return False


def import_existing_data():
    """Import any existing CSV files in the data/exports directory"""
    
    # Look for existing CSV files
    exports_dir = OUTPUT_DIR
    if not os.path.exists(exports_dir):
        print(f"📁 No exports directory found at {exports_dir}")
        return
    
    csv_files = [f for f in os.listdir(exports_dir) if f.endswith('.csv')]
    
    if not csv_files:
        print("📁 No CSV files found to import")
        return
    
    print(f"🔍 Found {len(csv_files)} CSV files to import:")
    
    for csv_file in csv_files:
        csv_path = os.path.join(exports_dir, csv_file)
        print(f"\n📊 Processing {csv_file}...")
        
        # Try to extract date from filename or use current date
        scan_date = datetime.now()  # Could be enhanced to parse date from filename
        
        success = import_csv_scan_results(csv_path, scan_date)
        if success:
            print(f"✅ Imported {csv_file}")
        else:
            print(f"❌ Failed to import {csv_file}")


def show_database_summary():
    """Display summary of data in database"""
    db = ScannerDatabase()
    stats = db.get_database_stats()
    
    print("\n" + "=" * 50)
    print("📊 DATABASE SUMMARY")
    print("=" * 50)
    
    for key, value in stats.items():
        if isinstance(value, (int, float)):
            print(f"{key.replace('_', ' ').title()}: {value:,}")
        else:
            print(f"{key.replace('_', ' ').title()}: {value}")
    
    # Show recent scan results
    recent_scans = db.get_scan_history(7)  # Last 7 days
    if not recent_scans.empty:
        print(f"\n🔍 Recent Scans (Last 7 days): {len(recent_scans)} records")
        
        # Group by scan date
        scan_dates = recent_scans['scan_date'].value_counts().sort_index()
        for date, count in scan_dates.items():
            print(f"  {date}: {count} symbols scanned")
        
        # Show alerts
        alerts = recent_scans[(recent_scans['hit_high'] == 1) | (recent_scans['hit_low'] == 1)]
        if not alerts.empty:
            print(f"\n🚨 Recent Alerts: {len(alerts)}")
            for _, alert in alerts.head(10).iterrows():
                status = "🔴" if alert['hit_high'] else "🟢"
                print(f"  {status} {alert['symbol']} | RSI: {alert['latest_rsi']:.1f}")


def main():
    """Main execution function"""
    print("🔄 IB RSI Scanner Data Migration Tool")
    print("=" * 50)
    
    # Import existing CSV data
    import_existing_data()
    
    # Show database summary
    show_database_summary()


if __name__ == "__main__":
    main()
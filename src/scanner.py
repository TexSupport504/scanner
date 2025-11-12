"""
Enhanced IB RSI/ATR Scanner with Database Caching
Scans S&P 500 stocks for extreme RSI conditions with intelligent caching
"""

from ib_insync import IB, Stock, util
import pandas as pd
import time
import requests
import io
import ta
from datetime import datetime, timedelta
import sys
import os

# Add parent and config directories to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import *
from src.database import ScannerDatabase
from src.cache_manager import CacheManager
from src.indicators import compute_indicators, check_rsi_extremes, check_overextended


class RSIScanner:
    def __init__(self):
        self.db = ScannerDatabase()
        self.cache_manager = CacheManager(self.db)
        self.ib = None
        self.tickers = []
        
    def connect_to_ib(self):
        """Connect to Interactive Brokers"""
        self.ib = IB()
        try:
            self.ib.connect(IB_HOST, IB_PORT, clientId=IB_CLIENT_ID)
            print(f"✅ Connected to IB at {IB_HOST}:{IB_PORT}")
            return True
        except Exception as e:
            print(f"❌ Failed to connect to IB: {e}")
            return False
    
    def disconnect_from_ib(self):
        """Disconnect from Interactive Brokers"""
        if self.ib and self.ib.isConnected():
            self.ib.disconnect()
            print("📡 Disconnected from IB")
    
    def fetch_sp500_tickers(self):
        """Fetch S&P 500 ticker list with exclusions"""
        # Try datahub CSV first
        try:
            r = requests.get(SP500_CSV_URLS[0], timeout=20)
            r.raise_for_status()
            df = pd.read_csv(io.StringIO(r.text))
            tickers = df['Symbol'].str.replace('.', '-', regex=False).tolist()
            # Filter out excluded tickers
            tickers = [t for t in tickers if t not in EXCLUDED_TICKERS]
            self.tickers = sorted(set(tickers))
            print(f"📊 Loaded {len(self.tickers)} S&P 500 tickers (excluded {len(EXCLUDED_TICKERS)})")
            return True
        except Exception:
            # fallback: parse Wikipedia table
            try:
                tables = pd.read_html(SP500_CSV_URLS[1])
                df = tables[0]
                tickers = df['Symbol'].str.replace('.', '-', regex=False).tolist()
                tickers = [t for t in tickers if t not in EXCLUDED_TICKERS]
                self.tickers = sorted(set(tickers))
                print(f"📊 Loaded {len(self.tickers)} S&P 500 tickers from Wikipedia")
                return True
            except Exception as e:
                print(f"❌ Failed to fetch S&P 500 list: {e}")
                return False
    
    def get_historical_data(self, symbol: str, days: int = HIST_DAYS) -> pd.DataFrame:
        """
        Get historical data with intelligent caching
        """
        # Check cache strategy
        fetch_range = self.cache_manager.get_fetch_strategy(symbol)
        
        if fetch_range is None:
            # Use cached data
            start_date = datetime.now() - timedelta(days=days)
            end_date = datetime.now()
            cached_data = self.db.get_cached_price_data(symbol, start_date, end_date)
            if cached_data is not None and not cached_data.empty:
                return cached_data
        
        # Need to fetch from IB
        try:
            contract = Stock(symbol, 'SMART', 'USD')
            bars = self.ib.reqHistoricalData(
                contract,
                endDateTime='',
                durationStr=f'{days} D',
                barSizeSetting='1 day',
                whatToShow='TRADES',
                useRTH=True,
                formatDate=1
            )
            
            if not bars:
                return pd.DataFrame()
            
            # Convert to DataFrame
            df = util.df(bars)
            if df.empty:
                return df
            
            # Merge with cached data and save
            complete_df = self.cache_manager.merge_new_data(symbol, df)
            return complete_df
            
        except Exception as e:
            print(f"⚠️  Error fetching data for {symbol}: {e}")
            # Try to return cached data as fallback
            start_date = datetime.now() - timedelta(days=days)
            end_date = datetime.now()
            cached_data = self.db.get_cached_price_data(symbol, start_date, end_date)
            return cached_data if cached_data is not None else pd.DataFrame()
    
    def scan_symbol(self, symbol: str) -> dict:
        """Scan a single symbol for RSI extremes"""
        try:
            # Get historical data (cached or fresh)
            df = self.get_historical_data(symbol)
            
            if df.empty or len(df) < max(RSI_WINDOW, ATR_WINDOW) + 1:
                return {
                    'symbol': symbol,
                    'status': 'insufficient_data',
                    'latest_rsi': None,
                    'latest_atr': None,
                    'hit_high': False,
                    'hit_low': False,
                    'is_overextended': False,
                    'swing_low': None,
                    'overextended_threshold': None,
                    'current_price': None
                }
            
            # Compute indicators
            rsi_series, atr_series, (latest_rsi, latest_atr) = compute_indicators(df)
            
            if rsi_series is None or latest_rsi is None:
                return {
                    'symbol': symbol,
                    'status': 'calculation_failed',
                    'latest_rsi': None,
                    'latest_atr': None,
                    'hit_high': False,
                    'hit_low': False,
                    'is_overextended': False,
                    'swing_low': None,
                    'overextended_threshold': None,
                    'current_price': None
                }            # Save indicators to database
            self.db.save_indicators(symbol, df, rsi_series, atr_series)
            
            # Check for extreme RSI values
            hit_high, hit_low, max_rsi, min_rsi = check_rsi_extremes(
                rsi_series, 
                RSI_LOOKBACK_DAYS, 
                RSI_HIGH_THRESHOLD, 
                RSI_LOW_THRESHOLD
            )
            
            # Check for overextended condition - returns complete measurement structure
            overextended_data = check_overextended(
                df, latest_atr, 
                OVEREXTENDED_LOOKBACK_DAYS,  # 5 days
                OVEREXTENDED_ATR_MULTIPLIER  # 5x ATR
            )
            
            # Extract values from measurement structure
            is_overextended = overextended_data['is_overextended']
            swing_low = overextended_data['swing_low']
            overextended_threshold = overextended_data['threshold']
            current_price = overextended_data['current_price']
            
            # Determine status
            status = 'no_hit'
            if hit_high:
                status = 'RSI>=90'
            if hit_low:
                status = ('RSI<=10' if status == 'no_hit' else status + ';RSI<=10')
            if is_overextended:
                status = ('overextended' if status == 'no_hit' else status + ';overextended')
            
            result = {
                'symbol': symbol,
                'status': status,
                'latest_rsi': float(latest_rsi),
                'latest_atr': float(latest_atr),
                'hit_high': hit_high,
                'hit_low': hit_low,
                'max_rsi': float(max_rsi) if max_rsi is not None else None,
                'min_rsi': float(min_rsi) if min_rsi is not None else None,
                'is_overextended': is_overextended,
                'swing_low': swing_low,
                'swing_high': overextended_data['swing_high'],
                'overextended_threshold': overextended_threshold,
                'current_price': current_price,
                'atr_contribution': overextended_data['atr_contribution'],
                'distance_from_threshold': overextended_data['distance_from_threshold'],
                'distance_pct': overextended_data['distance_pct'],
                'proximity_pct': overextended_data['proximity_pct'],
                'price_range': overextended_data['price_range'],
                'data_points': len(df),
                'cached': not self.cache_manager.should_fetch_data(symbol)
            }
            
            # Save scan result
            self.db.save_scan_result(
                datetime.now(),
                symbol,
                latest_rsi,
                latest_atr,
                hit_high,
                hit_low,
                status,
                is_overextended,
                swing_low,
                overextended_threshold,
                current_price
            )
            
            return result
            
        except Exception as e:
            return {
                'symbol': symbol,
                'status': f'error:{str(e)}',
                'latest_rsi': None,
                'latest_atr': None,
                'hit_high': False,
                'hit_low': False,
                'is_overextended': False,
                'swing_low': None,
                'overextended_threshold': None,
                'current_price': None
            }
    
    def run_scan(self):
        """Run the complete RSI scan"""
        print("🚀 Starting Enhanced RSI/ATR Scanner")
        print("=" * 60)
        
        # Connect to IB
        if not self.connect_to_ib():
            return
        
        # Fetch tickers
        if not self.fetch_sp500_tickers():
            self.disconnect_from_ib()
            return
        
        # Print cache statistics
        cache_stats = self.cache_manager.get_cache_statistics()
        print(f"💾 Cache Status: {cache_stats.get('fresh_cache_count', 0)} fresh, "
              f"{cache_stats.get('unique_symbols', 0)} total symbols")
        
        results = []
        alerts = []
        cached_count = 0
        
        scan_start_time = time.time()
        
        for i, symbol in enumerate(self.tickers, 1):
            print(f"📈 [{i:3d}/{len(self.tickers)}] Scanning {symbol}...", end=" ")
            
            result = self.scan_symbol(symbol)
            results.append(result)
            
            if result.get('cached', False):
                cached_count += 1
                print("💾", end=" ")
            
            # Check for alerts
            if result['hit_high'] or result['hit_low'] or result.get('is_overextended', False):
                alerts.append(result)
                alert_type = []
                if result['hit_high']:
                    alert_type.append("�RSI High")
                if result['hit_low']:
                    alert_type.append("🟢RSI Low") 
                if result.get('is_overextended', False):
                    alert_type.append("⚡Overextended")
                print(f"🚨 {'/'.join(alert_type)}! RSI: {result['latest_rsi']:.1f}", end=" ")
                if result.get('is_overextended', False):
                    print(f"Price: ${result['current_price']:.2f} > ${result['overextended_threshold']:.2f}", end=" ")
            
            if result['status'] == 'insufficient_data':
                print("⚠️  No data", end=" ")
            elif result['status'].startswith('error'):
                print("❌ Error", end=" ")
            elif result['latest_rsi'] is not None:
                print(f"RSI: {result['latest_rsi']:.1f}", end=" ")
            
            print()  # New line
            
            # Rate limiting
            time.sleep(REQUEST_DELAY)
        
        # Disconnect
        self.disconnect_from_ib()
        
        # Calculate scan performance
        scan_duration = time.time() - scan_start_time
        cache_hit_rate = (cached_count / len(self.tickers)) * 100 if self.tickers else 0
        
        # Save results
        self.save_results(results, alerts)
        
        # Print summary
        self.print_summary(results, alerts, scan_duration, cache_hit_rate)
    
    def save_results(self, results, alerts):
        """Save scan results to CSV files"""
        # Create exports directory
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        
        # Save full results
        df_results = pd.DataFrame(results)
        full_output_path = os.path.join(OUTPUT_DIR, CSV_OUTPUT)
        df_results.to_csv(full_output_path, index=False)
        
        # Save alerts only
        if alerts:
            df_alerts = pd.DataFrame(alerts)
            alerts_output_path = os.path.join(OUTPUT_DIR, SHORTLIST_OUTPUT)
            df_alerts.to_csv(alerts_output_path, index=False)
        
        print(f"💾 Results saved to {OUTPUT_DIR}/")
    
    def print_summary(self, results, alerts, duration, cache_hit_rate):
        """Print scan summary"""
        print("\n" + "=" * 60)
        print("📊 SCAN SUMMARY")
        print("=" * 60)
        
        total_scanned = len(results)
        successful_scans = len([r for r in results if r['latest_rsi'] is not None])
        error_count = len([r for r in results if r['status'].startswith('error')])
        
        print(f"📈 Total symbols scanned: {total_scanned}")
        print(f"✅ Successful scans: {successful_scans}")
        print(f"❌ Errors: {error_count}")
        print(f"⏱️  Scan duration: {duration:.1f} seconds")
        print(f"💾 Cache hit rate: {cache_hit_rate:.1f}%")
        print(f"🚨 Alerts found: {len(alerts)}")
        
        if alerts:
            print(f"\n🔥 EXTREME RSI/OVEREXTENDED ALERTS:")
            print("-" * 50)
            for alert in sorted(alerts, key=lambda x: x['latest_rsi'], reverse=True):
                # Determine alert types
                alert_types = []
                if alert['hit_high']:
                    alert_types.append("🔴 Overbought")
                if alert['hit_low']:
                    alert_types.append("🟢 Oversold")
                if alert.get('is_overextended', False):
                    alert_types.append("⚡ Overextended")
                
                status_emoji = alert_types[0].split()[0] if alert_types else "�"
                print(f"{status_emoji} {alert['symbol']:>6} | "
                      f"RSI: {alert['latest_rsi']:6.1f} | "
                      f"ATR: {alert['latest_atr']:6.2f} | "
                      f"Price: ${alert.get('current_price', 0):7.2f}")
                
                # RSI conditions
                conditions = []
                if alert['hit_high']:
                    conditions.append(f"Overbought (Max: {alert.get('max_rsi', 0):.1f})")
                if alert['hit_low']:
                    conditions.append(f"Oversold (Min: {alert.get('min_rsi', 0):.1f})")
                
                if conditions:
                    print(f"      {' | '.join(conditions)}")
                
                # Enhanced Overextended Measurements
                if alert.get('is_overextended', False):
                    print(f"      ⚡ OVEREXTENDED = TRUE")
                    print(f"         📊 Measurement Breakdown:")
                    print(f"            Swing Low (5d):    ${alert.get('swing_low', 0):7.2f}")
                    print(f"            ATR:               ${alert.get('latest_atr', 0):7.2f}")
                    print(f"            ATR × 5:           ${alert.get('atr_contribution', 0):7.2f}")
                    print(f"            Threshold:         ${alert.get('overextended_threshold', 0):7.2f}")
                    print(f"            Current Price:     ${alert.get('current_price', 0):7.2f}")
                    print(f"            Distance:          ${alert.get('distance_from_threshold', 0):+7.2f} ({alert.get('distance_pct', 0):+.1f}%)")
                    print(f"            Proximity:         {alert.get('proximity_pct', 0):.0f}% (100% = at threshold)")
                
                # Show proximity warning for stocks close to overextended (but not yet there)
                elif alert.get('proximity_pct') is not None and alert.get('proximity_pct', 0) >= 80:
                    print(f"      ⚠️  OVEREXTENDED = FALSE (But approaching!)")
                    print(f"         📊 Proximity: {alert.get('proximity_pct', 0):.0f}% of threshold")
                    print(f"            Current Price:  ${alert.get('current_price', 0):7.2f}")
                    print(f"            Threshold:      ${alert.get('overextended_threshold', 0):7.2f}")
                    print(f"            Distance:       ${alert.get('distance_from_threshold', 0):+7.2f}")
                
                print()
        
        # Database statistics
        db_stats = self.db.get_database_stats()
        print(f"\n💾 Database Statistics:")
        print(f"   Price records: {db_stats.get('price_data_count', 0):,}")
        print(f"   Indicator records: {db_stats.get('indicators_count', 0):,}")
        print(f"   Scan records: {db_stats.get('scan_results_count', 0):,}")
        
        # Auto-export to daily CSV for Data Wrangler
        try:
            import subprocess
            export_script = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'export_daily_scan.py')
            if os.path.exists(export_script):
                print(f"\n📤 Exporting to daily CSV...")
                subprocess.run([sys.executable, export_script], check=True, capture_output=True)
                print(f"✅ daily_scan_results.csv updated!")
        except Exception as e:
            print(f"⚠️  Could not auto-export: {e}")
        
        # Auto-create filtered views for Data Wrangler
        try:
            import subprocess
            views_script = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'create_filtered_views.py')
            if os.path.exists(views_script):
                print(f"\n🔧 Creating filtered views...")
                result = subprocess.run([sys.executable, views_script], check=True, capture_output=True, text=True)
                # Print key stats from the output
                output_lines = result.stdout.strip().split('\n')
                for line in output_lines:
                    if line.startswith('✓'):
                        print(f"   {line}")
                print(f"✅ 14 filtered views created in data/exports/views/")
        except Exception as e:
            print(f"⚠️  Could not create filtered views: {e}")


def main():
    """Main execution function"""
    scanner = RSIScanner()
    scanner.run_scan()


if __name__ == "__main__":
    main()
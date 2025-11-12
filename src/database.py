"""
Database operations for IB RSI Scanner
Handles SQLite operations, caching, and data persistence
"""

import sqlite3
import pandas as pd
import os
from datetime import datetime, timedelta
from typing import Optional, Tuple
import sys

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import DB_PATH, MAX_CACHE_AGE_DAYS


class ScannerDatabase:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or DB_PATH
        self.ensure_database_exists()
        self.create_tables()
    
    def ensure_database_exists(self):
        """Ensure database directory exists"""
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
    
    def create_tables(self):
        """Create database tables if they don't exist"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Historical price data table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS price_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    date DATE NOT NULL,
                    open REAL,
                    high REAL,
                    low REAL,
                    close REAL,
                    volume INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(symbol, date)
                )
            ''')
            
            # Technical indicators table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS indicators (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    date DATE NOT NULL,
                    rsi_14 REAL,
                    atr_14 REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(symbol, date)
                )
            ''')
            
            # Scan results table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS scan_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scan_date DATE NOT NULL,
                    symbol TEXT NOT NULL,
                    latest_rsi REAL,
                    latest_atr REAL,
                    hit_high BOOLEAN,
                    hit_low BOOLEAN,
                    is_overextended BOOLEAN DEFAULT 0,
                    swing_low REAL,
                    overextended_threshold REAL,
                    current_price REAL,
                    status TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Cache metadata table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS cache_metadata (
                    symbol TEXT PRIMARY KEY,
                    last_updated TIMESTAMP,
                    last_date DATE,
                    record_count INTEGER
                )
            ''')
            
            # Create indexes for better performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_price_symbol_date ON price_data(symbol, date)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_indicators_symbol_date ON indicators(symbol, date)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_scan_results_date ON scan_results(scan_date)')
            
            conn.commit()
    
    def get_cached_price_data(self, symbol: str, start_date: datetime, end_date: datetime) -> Optional[pd.DataFrame]:
        """Get cached price data for a symbol within date range"""
        with sqlite3.connect(self.db_path) as conn:
            query = '''
                SELECT date, open, high, low, close, volume
                FROM price_data 
                WHERE symbol = ? AND date >= ? AND date <= ?
                ORDER BY date
            '''
            
            df = pd.read_sql_query(
                query, 
                conn, 
                params=(symbol, start_date.date(), end_date.date()),
                parse_dates=['date']
            )
            
            return df if not df.empty else None
    
    def save_price_data(self, symbol: str, df: pd.DataFrame):
        """Save price data to database"""
        if df.empty:
            return
            
        # Prepare data for insertion
        df_copy = df.copy()
        df_copy['symbol'] = symbol
        df_copy = df_copy[['symbol', 'date', 'open', 'high', 'low', 'close', 'volume']]
        
        with sqlite3.connect(self.db_path) as conn:
            # Use INSERT OR REPLACE to handle duplicates
            df_copy.to_sql('price_data', conn, if_exists='append', index=False, method='multi')
            
            # Update cache metadata
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO cache_metadata (symbol, last_updated, last_date, record_count)
                VALUES (?, ?, ?, ?)
            ''', (
                symbol,
                datetime.now(),
                df['date'].max().date() if not df.empty else None,
                len(df)
            ))
            
            conn.commit()
    
    def save_indicators(self, symbol: str, df: pd.DataFrame, rsi_series: pd.Series, atr_series: pd.Series):
        """Save calculated indicators to database"""
        if df.empty or rsi_series.empty or atr_series.empty:
            return
            
        # Create indicators dataframe
        indicators_df = pd.DataFrame({
            'symbol': symbol,
            'date': df['date'],
            'rsi_14': rsi_series,
            'atr_14': atr_series
        })
        
        # Remove rows with NaN values
        indicators_df = indicators_df.dropna()
        
        if indicators_df.empty:
            return
        
        with sqlite3.connect(self.db_path) as conn:
            # Use manual insertion with INSERT OR REPLACE to handle duplicates
            cursor = conn.cursor()
            for _, row in indicators_df.iterrows():
                cursor.execute('''
                    INSERT OR REPLACE INTO indicators 
                    (symbol, date, rsi_14, atr_14, created_at)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    row['symbol'], 
                    row['date'].date() if hasattr(row['date'], 'date') else row['date'],
                    row['rsi_14'], 
                    row['atr_14'],
                    datetime.now()
                ))
            conn.commit()
    
    def save_scan_result(self, scan_date: datetime, symbol: str, latest_rsi: float, 
                        latest_atr: float, hit_high: bool, hit_low: bool, status: str,
                        is_overextended: bool = False, swing_low: float = None,
                        overextended_threshold: float = None, current_price: float = None):
        """Save scan result to database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO scan_results 
                (scan_date, symbol, latest_rsi, latest_atr, hit_high, hit_low, 
                 is_overextended, swing_low, overextended_threshold, current_price, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (scan_date.date(), symbol, latest_rsi, latest_atr, hit_high, hit_low,
                  is_overextended, swing_low, overextended_threshold, current_price, status))
            conn.commit()
    
    def is_data_fresh(self, symbol: str) -> bool:
        """Check if cached data is fresh enough"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT last_updated FROM cache_metadata WHERE symbol = ?
            ''', (symbol,))
            
            result = cursor.fetchone()
            if not result:
                return False
            
            last_updated = datetime.fromisoformat(result[0])
            age = datetime.now() - last_updated
            
            return age.days < MAX_CACHE_AGE_DAYS
    
    def get_missing_date_range(self, symbol: str, required_start: datetime, required_end: datetime) -> Optional[Tuple[datetime, datetime]]:
        """Determine what date range needs to be fetched for a symbol"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT MIN(date) as min_date, MAX(date) as max_date 
                FROM price_data 
                WHERE symbol = ?
            ''', (symbol,))
            
            result = cursor.fetchone()
            if not result or not result[0]:
                # No data exists, fetch full range
                return (required_start, required_end)
            
            cached_start = datetime.strptime(result[0], '%Y-%m-%d').date()
            cached_end = datetime.strptime(result[1], '%Y-%m-%d').date()
            
            # Check if we have all required data
            if cached_start <= required_start.date() and cached_end >= required_end.date():
                return None  # All data is cached
            
            # Determine what range to fetch
            fetch_start = required_start
            fetch_end = required_end
            
            if cached_end < required_end.date():
                # Need newer data
                fetch_start = datetime.combine(cached_end + timedelta(days=1), datetime.min.time())
            
            if cached_start > required_start.date():
                # Need older data
                fetch_end = datetime.combine(cached_start - timedelta(days=1), datetime.min.time())
            
            return (fetch_start, fetch_end)
    
    def get_scan_history(self, days: int = 30) -> pd.DataFrame:
        """Get scan history for the last N days"""
        with sqlite3.connect(self.db_path) as conn:
            cutoff_date = datetime.now().date() - timedelta(days=days)
            query = '''
                SELECT * FROM scan_results 
                WHERE scan_date >= ?
                ORDER BY scan_date DESC, symbol
            '''
            return pd.read_sql_query(query, conn, params=(cutoff_date,))
    
    def export_to_csv(self, table_name: str, output_path: str):
        """Export table data to CSV"""
        with sqlite3.connect(self.db_path) as conn:
            df = pd.read_sql_query(f'SELECT * FROM {table_name}', conn)
            df.to_csv(output_path, index=False)
            return len(df)
    
    def get_database_stats(self) -> dict:
        """Get database statistics"""
        stats = {}
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Count records in each table
            tables = ['price_data', 'indicators', 'scan_results', 'cache_metadata']
            for table in tables:
                cursor.execute(f'SELECT COUNT(*) FROM {table}')
                stats[f'{table}_count'] = cursor.fetchone()[0]
            
            # Get date ranges
            cursor.execute('SELECT MIN(date), MAX(date) FROM price_data')
            result = cursor.fetchone()
            if result[0]:
                stats['price_data_date_range'] = f"{result[0]} to {result[1]}"
            
            # Get unique symbols count
            cursor.execute('SELECT COUNT(DISTINCT symbol) FROM price_data')
            stats['unique_symbols'] = cursor.fetchone()[0]
        
        return stats
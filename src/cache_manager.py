"""
Cache Manager for IB RSI Scanner
Handles intelligent caching of historical data to minimize API calls
"""

from datetime import datetime, timedelta
import pandas as pd
from typing import Optional, Tuple
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import MAX_CACHE_AGE_DAYS, HIST_DAYS


class CacheManager:
    def __init__(self, database):
        self.db = database
    
    def get_required_data_range(self, hist_days: int = HIST_DAYS) -> Tuple[datetime, datetime]:
        """Calculate the date range we need for analysis"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=hist_days)
        return start_date, end_date
    
    def should_fetch_data(self, symbol: str) -> bool:
        """Determine if we need to fetch data for a symbol"""
        # Check if data exists and is fresh
        if not self.db.is_data_fresh(symbol):
            return True
        
        # Check if we have enough data for the required analysis period
        start_date, end_date = self.get_required_data_range()
        cached_data = self.db.get_cached_price_data(symbol, start_date, end_date)
        
        if cached_data is None or len(cached_data) < 20:  # Need at least 20 days for RSI
            return True
        
        return False
    
    def get_fetch_strategy(self, symbol: str) -> Optional[Tuple[datetime, datetime]]:
        """
        Determine what date range to fetch for a symbol
        Returns None if no fetch is needed, or (start_date, end_date) tuple
        """
        if not self.should_fetch_data(symbol):
            return None
        
        required_start, required_end = self.get_required_data_range()
        missing_range = self.db.get_missing_date_range(symbol, required_start, required_end)
        
        return missing_range
    
    def get_cached_or_partial_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """Get cached data if available, even if partial"""
        start_date, end_date = self.get_required_data_range()
        return self.db.get_cached_price_data(symbol, start_date, end_date)
    
    def merge_new_data(self, symbol: str, new_data: pd.DataFrame) -> pd.DataFrame:
        """Merge new data with existing cached data"""
        # Save new data to cache first
        if not new_data.empty:
            self.db.save_price_data(symbol, new_data)
        
        # Get complete cached data
        start_date, end_date = self.get_required_data_range()
        complete_data = self.db.get_cached_price_data(symbol, start_date, end_date)
        
        return complete_data if complete_data is not None else new_data
    
    def clean_old_cache(self, days_to_keep: int = 90):
        """Remove old cached data to keep database size manageable"""
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        import sqlite3
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()
            
            # Remove old price data
            cursor.execute('DELETE FROM price_data WHERE date < ?', (cutoff_date.date(),))
            
            # Remove old indicators
            cursor.execute('DELETE FROM indicators WHERE date < ?', (cutoff_date.date(),))
            
            # Update cache metadata
            cursor.execute('''
                DELETE FROM cache_metadata 
                WHERE symbol NOT IN (SELECT DISTINCT symbol FROM price_data)
            ''')
            
            conn.commit()
            
            return cursor.rowcount
    
    def get_cache_statistics(self) -> dict:
        """Get cache performance statistics"""
        stats = self.db.get_database_stats()
        
        # Add cache-specific metrics
        import sqlite3
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()
            
            # Fresh cache count
            fresh_cutoff = datetime.now() - timedelta(days=MAX_CACHE_AGE_DAYS)
            cursor.execute('''
                SELECT COUNT(*) FROM cache_metadata 
                WHERE last_updated > ?
            ''', (fresh_cutoff,))
            stats['fresh_cache_count'] = cursor.fetchone()[0]
            
            # Cache hit ratio (approximate)
            cursor.execute('SELECT COUNT(*) FROM cache_metadata')
            total_symbols = cursor.fetchone()[0]
            if total_symbols > 0:
                stats['cache_freshness_ratio'] = stats['fresh_cache_count'] / total_symbols
            else:
                stats['cache_freshness_ratio'] = 0
        
        return stats
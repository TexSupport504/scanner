"""
Unit tests for IB RSI Scanner
"""

import unittest
import sys
import os
import tempfile
import pandas as pd
from datetime import datetime, timedelta

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.database import ScannerDatabase
from src.cache_manager import CacheManager
from src.indicators import compute_indicators, check_rsi_extremes


class TestScannerDatabase(unittest.TestCase):
    def setUp(self):
        """Set up test database"""
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.db = ScannerDatabase(self.temp_db.name)
    
    def tearDown(self):
        """Clean up test database"""
        os.unlink(self.temp_db.name)
    
    def test_database_creation(self):
        """Test database and table creation"""
        stats = self.db.get_database_stats()
        self.assertIn('price_data_count', stats)
        self.assertEqual(stats['price_data_count'], 0)
    
    def test_save_and_retrieve_price_data(self):
        """Test saving and retrieving price data"""
        # Create sample data
        dates = pd.date_range(start='2023-01-01', periods=10, freq='D')
        sample_data = pd.DataFrame({
            'date': dates,
            'open': range(100, 110),
            'high': range(101, 111),
            'low': range(99, 109),
            'close': range(100, 110),
            'volume': range(1000, 1010)
        })
        
        # Save data
        self.db.save_price_data('TEST', sample_data)
        
        # Retrieve data
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 1, 15)
        retrieved_data = self.db.get_cached_price_data('TEST', start_date, end_date)
        
        self.assertIsNotNone(retrieved_data)
        self.assertEqual(len(retrieved_data), 10)


class TestIndicators(unittest.TestCase):
    def setUp(self):
        """Set up test data"""
        # Create sample OHLCV data
        dates = pd.date_range(start='2023-01-01', periods=30, freq='D')
        
        # Create realistic price movements
        close_prices = [100]
        for i in range(29):
            change = (i % 3 - 1) * 0.5  # Simple pattern
            close_prices.append(close_prices[-1] * (1 + change/100))
        
        self.sample_data = pd.DataFrame({
            'date': dates,
            'open': [p * 0.995 for p in close_prices],
            'high': [p * 1.01 for p in close_prices],
            'low': [p * 0.99 for p in close_prices],
            'close': close_prices,
            'volume': range(1000, 1030)
        })
    
    def test_compute_indicators(self):
        """Test RSI and ATR calculation"""
        rsi_series, atr_series, (latest_rsi, latest_atr) = compute_indicators(self.sample_data)
        
        self.assertIsNotNone(rsi_series)
        self.assertIsNotNone(atr_series)
        self.assertIsNotNone(latest_rsi)
        self.assertIsNotNone(latest_atr)
        
        # RSI should be between 0 and 100
        self.assertTrue(0 <= latest_rsi <= 100)
        
        # ATR should be positive
        self.assertTrue(latest_atr > 0)
    
    def test_check_rsi_extremes(self):
        """Test RSI extreme detection"""
        # Create a series with extreme values
        extreme_rsi = pd.Series([50, 60, 70, 80, 95, 85, 75, 65])
        
        hit_high, hit_low, max_rsi, min_rsi = check_rsi_extremes(extreme_rsi, 8, 90, 10)
        
        self.assertTrue(hit_high)  # Should detect 95 > 90
        self.assertFalse(hit_low)  # No values < 10
        self.assertEqual(max_rsi, 95)


class TestCacheManager(unittest.TestCase):
    def setUp(self):
        """Set up cache manager with test database"""
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.db = ScannerDatabase(self.temp_db.name)
        self.cache_manager = CacheManager(self.db)
    
    def tearDown(self):
        """Clean up"""
        os.unlink(self.temp_db.name)
    
    def test_should_fetch_data(self):
        """Test cache fetch decision logic"""
        # For a new symbol, should fetch data
        should_fetch = self.cache_manager.should_fetch_data('NEWSTOCK')
        self.assertTrue(should_fetch)


if __name__ == '__main__':
    unittest.main()
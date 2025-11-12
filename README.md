# 📊 IB RSI Scanner - Interactive Brokers Stock Scanner

A comprehensive Python-based RSI/ATR scanner for S&P 500 stocks using Interactive Brokers API, featuring real-time data analysis, technical indicators, and interactive filtering capabilities.

## 🚀 Features

- **Real-time S&P 500 Stock Scanning**: Connects to Interactive Brokers API for live market data
- **Technical Analysis**: RSI and ATR calculations with overextended threshold detection
### Data Analysis & Backtesting
- **`scanner_dashboard.ipynb`**: Interactive Jupyter notebook with:
  - Clickable filter widgets
  - 6-panel visualization dashboard
  - Pre-built trading opportunity variables
  - Export functions
- **`backtest_system.py`**: Comprehensive backtesting framework
  - 30% take profit / 25% stop loss testing
  - Historical performance analysis
  - Win rate and P&L ratio calculations
- **`backtest_analysis.ipynb`**: Interactive backtesting dashboard
  - Visual backtesting analysis
  - Performance charts and statistics
  - Export functions for results
- **`daily_scan_results.csv`**: Main export file (499 stocks, auto-updated)
- **Data Persistence**: SQLite database with intelligent caching system
- **Multiple Export Formats**: CSV exports for Data Wrangler integration
- **Trading Signals**: Automated LONG PUT/CALL opportunity identification
- **Priority Scoring**: Multi-factor scoring system for trade prioritization

## 📋 Requirements

- Python 3.11+
- Interactive Brokers TWS or Gateway (Paper/Live account)
- Level 2 Options approval (for options strategies)
- **Smart caching system** to avoid redundant API calls
- **Data Wrangler integration** for database management
- **CSV export** capabilities

## Project Structure

```
scanner/
├── src/
│   ├── __init__.py
│   ├── scanner.py          # Main RSI/ATR scanner
│   ├── database.py         # Database operations
│   ├── cache_manager.py    # Caching logic
│   └── indicators.py       # Technical analysis functions
├── data/
│   ├── scanner.db         # SQLite database
│   └── exports/           # CSV export directory
├── config/
│   └── settings.py        # Configuration settings
├── tests/
│   └── test_scanner.py    # Unit tests
├── requirements.txt       # Python dependencies
├── .gitignore
└── README.md
```

## Setup Instructions

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Interactive Brokers**:
   - Install and run TWS or IB Gateway
   - Enable API access in configuration
   - Set appropriate port (7496 for live, 7497 for paper)

3. **Run Scanner**:
   ```bash
   python src/scanner.py
   ```

## Configuration

Edit `config/settings.py` to customize:
- IB connection parameters
- RSI/ATR windows
- Database settings
- Scan parameters

## Database Schema

The SQLite database stores:
- Historical price data with timestamps
- Calculated RSI and ATR values
- Scan results and alerts
- Metadata for cache management

## Dependencies

- `ib_insync`: Interactive Brokers API client
- `pandas`: Data manipulation and analysis
- `ta`: Technical analysis indicators
- `requests`: HTTP requests for S&P 500 data
- `sqlite3`: Database operations (built-in)

## Usage

The scanner automatically:
1. Fetches current S&P 500 ticker list
2. Checks cache for existing data
3. Downloads only missing historical data
4. Calculates RSI and ATR indicators
5. Identifies extreme conditions
6. Saves results to database and CSV

## Output

- **Console**: Real-time scan progress and alerts
- **Database**: Complete historical data and results
- **CSV files**: Exportable scan results
- **Data Wrangler**: Visual database exploration
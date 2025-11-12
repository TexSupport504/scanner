# IB RSI Scanner Configuration

# Interactive Brokers Settings
IB_HOST = '127.0.0.1'
IB_PORT = 7496  # 7496 for live, 7497 for paper trading
IB_CLIENT_ID = 1

# Technical Analysis Settings
RSI_WINDOW = 14
ATR_WINDOW = 14
RSI_LOOKBACK_DAYS = 7   # Days to check for extreme RSI
RSI_HIGH_THRESHOLD = 90
RSI_LOW_THRESHOLD = 10

# Overextended Settings
OVEREXTENDED_LOOKBACK_DAYS = 5  # Days to look for swing low
OVEREXTENDED_ATR_MULTIPLIER = 5  # ATR multiplier for overextended threshold

# Data Settings
HIST_DAYS = 30          # Historical data to retrieve
MAX_CACHE_AGE_DAYS = 1  # Cache data for 1 day

# Database Settings
DB_PATH = 'data/scanner.db'

# Output Settings
OUTPUT_DIR = 'data/exports'
CSV_OUTPUT = 'sp500_rsi_atr_scan.csv'
SHORTLIST_OUTPUT = 'rsi_alerts.csv'

# S&P 500 Data Sources
SP500_CSV_URLS = [
    'https://datahub.io/core/s-and-p-500-companies/r/constituents.csv',
    'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
]

# Excluded tickers (known IB API issues)
EXCLUDED_TICKERS = {'BF-B', 'BRK-B', 'FI', 'WBA'}

# Rate limiting
REQUEST_DELAY = 0.12  # Seconds between API requests
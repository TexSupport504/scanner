# Copilot Instructions for IB RSI Scanner Project

This project is an Interactive Brokers RSI/ATR scanner with database integration and caching capabilities.

## Project Structure
- Python-based financial analysis tool
- SQLite database for storing historical data
- Caching system to avoid redundant API calls
- Technical indicators (RSI, ATR) calculation
- Interactive Brokers API integration

## Key Features
- Real-time connection to Interactive Brokers
- S&P 500 stock scanning
- Extreme RSI condition detection (≥90 overbought, ≤10 oversold)
- ATR volatility analysis
- Data persistence and caching
- CSV export capabilities

## Dependencies
- ib_insync: Interactive Brokers API
- pandas: Data manipulation
- sqlite3: Database storage
- ta: Technical analysis indicators
- requests: HTTP requests for S&P 500 list
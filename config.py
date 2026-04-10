from datetime import date

# Portfolio
STARTING_CASH = 100.0
TARGET_VALUE = 200.0
START_DATE = date(2026, 4, 9)
END_DATE = date(2026, 5, 9)

# Risk management
MAX_POSITION_PCT = 0.30        # Max 30% of portfolio in one position
STOP_LOSS_PCT = 0.07           # Sell if position drops 7%
TAKE_PROFIT_PCT = 0.15         # Sell if position gains 15%
MAX_OPEN_POSITIONS = 5

# Asset universe — mix of volatile stocks, ETFs, and crypto
WATCHLIST = {
    "stocks": [
        "TSLA", "NVDA", "AMD", "COIN", "MARA",
        "SOFI", "PLTR", "RIVN", "NIO", "MSTR",
        "SHOP", "RBLX", "DKNG", "HOOD", "AFRM",
    ],
    "crypto": [
        "BTC-USD", "ETH-USD", "SOL-USD", "DOGE-USD",
        "AVAX-USD", "LINK-USD", "XRP-USD", "ADA-USD",
    ],
    "leveraged_etfs": [
        "TQQQ", "SOXL", "UPRO", "SPXL", "FNGU",
    ],
}

# Technical indicator params
RSI_PERIOD = 14
RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9
BOLLINGER_PERIOD = 20
BOLLINGER_STD = 2
MOMENTUM_LOOKBACK = 10

# How often to run (minutes)
RUN_INTERVAL_MINUTES = 30

# Data directory
DATA_DIR = "data"
PORTFOLIO_FILE = f"{DATA_DIR}/portfolio.json"
TRADES_FILE = f"{DATA_DIR}/trades.json"
LOG_FILE = f"{DATA_DIR}/agent.log"

"""
╔══════════════════════════════════════════════════╗
║   PURE LIQUIDITY ALGO — CONFIGURATION            ║
║   Rishabh's Trading System                       ║
╚══════════════════════════════════════════════════╝

Yeh file mein saari settings hain.
Pehli baar setup karte waqt sirf API keys daalo.
Baaki strategy rules mat chhedo jab tak 50+ trades na ho jaayein.
"""

import os

# ═══════════════════════════════════════════
# 🔑 API KEYS — Yeh daalne ZAROORI hain
# ═══════════════════════════════════════════

# Dhan API (developers.dhan.co se lo)
DHAN_CLIENT_ID = os.getenv("DHAN_CLIENT_ID", "YOUR_CLIENT_ID_HERE")
DHAN_ACCESS_TOKEN = os.getenv("DHAN_ACCESS_TOKEN", "YOUR_ACCESS_TOKEN_HERE")

# Telegram Bot (BotFather se banao)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "YOUR_CHAT_ID_HERE")

# ═══════════════════════════════════════════
# 📊 STRATEGY PARAMETERS — Mat chhedo!
# ═══════════════════════════════════════════

# Trading Window
MARKET_OPEN = "09:15"          # IST
FIRST_CANDLE_END = "09:20"     # Pehli 5M candle complete
ENTRY_WINDOW_START = "09:20"   # Entry start
ENTRY_WINDOW_END = "09:30"     # Entry end
HARD_EXIT_TIME = "10:30"       # EXIT — NO EXCEPTION!

# Candle Settings
CANDLE_TIMEFRAME = "5"         # 5 minute candles
MIN_BODY_PERCENT = 50          # Body 50%+ of total candle

# SL/TP Settings (in Nifty points)
SL_BUFFER_POINTS = 20          # SL = candle low/high +/- 20
TP1_POINTS = 55                # TP1 at 50-60 points (using 55 avg)
TP2_POINTS = 100               # TP2 at 100+ points
TP1_EXIT_PERCENT = 50          # 50% quantity exit at TP1

# VIX Rules
VIX_GREEN = 15                 # Below 15 = trade freely
VIX_CAUTION = 20               # 15-20 = caution
VIX_NO_TRADE = 20              # Above 20 = NO TRADE

# Confidence Rules
CONFIDENCE_TRADE = 80          # 80%+ = full trade
CONFIDENCE_SMALL = 60          # 60-79% = reduced/skip
CONFIDENCE_NO_TRADE = 60       # Below 60% = NO TRADE

# Position Sizing
LOT_SIZE = 75                  # 1 lot = 75 units (March 2026)
MAX_LOTS = 1                   # Maximum 1 lot for now
MAX_TRADES_PER_DAY = 1         # Sirf 1 trade per day

# Options Settings
OPTION_TYPE_CE = "CE"          # Call option
OPTION_TYPE_PE = "PE"          # Put option
EXPIRY_TYPE = "MONTHLY"        # Monthly expiry only
STRIKE_SELECTION = "ATM"       # At-the-money only

# Gap Settings (in Nifty points)
GAP_THRESHOLD = 50             # 50+ points = significant gap

# ═══════════════════════════════════════════
# 🗂️ NIFTY INSTRUMENT DETAILS
# ═══════════════════════════════════════════

NIFTY_SYMBOL = "NIFTY"
EXCHANGE = "NSE"
SEGMENT = "OPTIONS"
INDEX_SECURITY_ID = 13        # Nifty 50 security ID on Dhan

# ═══════════════════════════════════════════
# 📁 FILE PATHS
# ═══════════════════════════════════════════

DATA_DIR = "data"
TRADE_LOG_FILE = f"{DATA_DIR}/trade_log.json"
NIGHT_ANALYSIS_FILE = f"{DATA_DIR}/night_analysis.json"
PAPER_TRADES_FILE = f"{DATA_DIR}/paper_trades.json"

# ═══════════════════════════════════════════
# 🌐 DASHBOARD SETTINGS
# ═══════════════════════════════════════════

DASHBOARD_PORT = 8080
DASHBOARD_HOST = "0.0.0.0"

# ═══════════════════════════════════════════
# 🔄 MODE SETTINGS
# ═══════════════════════════════════════════

# PAPER = Paper trading (no real money)
# SHADOW = Signals only (no execution)
# LIVE = Real trading (BE VERY CAREFUL!)
TRADING_MODE = os.getenv("TRADING_MODE", "PAPER")

# ═══════════════════════════════════════════
# ⏰ TIMEZONE
# ═══════════════════════════════════════════

TIMEZONE = "Asia/Kolkata"      # IST

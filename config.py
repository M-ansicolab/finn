"""FINN configuration: portfolio, thresholds, model routing.

Everything an investor would want to tune lives here, so "what counts as
unusual" is the user's decision, not the code's.
"""
import os

# 18-stock mock portfolio across sectors and sizes (NSE symbols).
PORTFOLIO = [
    "RELIANCE", "HDFCBANK", "TCS", "INFY", "ITC", "LT", "BAJFINANCE",
    "SUNPHARMA", "MARUTI", "TITAN", "ASIANPAINT", "DIXON", "POLYCAB",
    "IRCTC", "DMART", "PERSISTENT", "KPITTECH", "CDSL",
]

# Ad-hoc research demo set (engine is generic; any NSE symbol works).
RESEARCH_DEMO = ["ZOMATO", "TATAMOTORS", "HAL", "NAUKRI"]

# Push thresholds -- user-configurable.
ALERTS = {
    "volume_multiple": 2.0,      # today's volume vs trailing average
    "volume_lookback_days": 20,
    "price_move_pct": 4.0,       # absolute 1-day % move
    # Announcement categories that should interrupt (triggered alert)
    "interrupt_categories": ["results", "M&A", "management_change",
                             "fund_raise", "litigation", "pledging",
                             "credit_rating"],
}

# Model routing: rules first (free), cheap model for bulk extraction,
# strong model only for the final reasoning step.
CHEAP_MODEL = os.getenv("FINN_CHEAP_MODEL", "gemini-2.0-flash")
STRONG_MODEL = os.getenv("FINN_STRONG_MODEL", "gemini-2.5-pro")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

CACHE_DIR = os.getenv("FINN_CACHE", ".cache")

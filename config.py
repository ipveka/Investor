"""
Configuration file for the Portfolio Builder application.
Contains asset lists, descriptions, and categories.
"""

# Define our asset lists
ETF_TICKERS = [
    "SXR8.DE",  # Core S&P 500 (Xetra)
    "ZPRR.DE",  # Russell 2000 U.S. Small Cap (Xetra)
    "EXS5.DE",  # Euro Stoxx 50 (Xetra)
    "MEUD.PA",  # Core STOXX Europe 600 (Euronext Paris)
    "XNKY.DE",  # Nikkei 225 1D JPY (Xetra)
    "XGLE.DE",  # Eurozone Government Bonds (Xetra)
    "ICOM.UK",  # Diversified Commodity (London)
    "CBU0.UK",  # USD Treasury Bond 7–10 Yr (London)
    "DTLA.UK",  # USD Treasury Bond 20+ Yr (London)
    "EGLN.L",   # Physical Gold (London)
]

EU_STOCK_TICKERS = [
    "SIE.DE",   # Siemens (Xetra)
    "SU.PA",    # Schneider Electric (Euronext Paris)
    "KER.PA",   # Kering (Euronext Paris)
    "FR.PA",    # Valeo (Euronext Paris)
    "OVH.PA",   # OVHcloud (Euronext Paris)
    "ETL.PA",   # Eutelsat (Euronext Paris)
    "HAG.DE",   # Hensoldt (Xetra)
    "IDR.MC",   # Indra (Madrid Stock Exchange)
]

US_STOCK_TICKERS = [
    "RKLB",     # Rocket Lab (NASDAQ)
    "DELL",     # Dell Technologies (NYSE)
]

# Create a dictionary to store ticker descriptions
TICKER_DESCRIPTIONS = {
    "SXR8.DE": "Core S&P 500 (Xetra)",
    "ZPRR.DE": "Russell 2000 U.S. Small Cap (Xetra)",
    "EXS5.DE": "Euro Stoxx 50 (Xetra)",
    "MEUD.PA": "Core STOXX Europe 600 (Euronext Paris)",
    "XNKY.DE": "Nikkei 225 1D JPY (Xetra)",
    "XGLE.DE": "Eurozone Government Bonds (Xetra)",
    "ICOM.UK": "Diversified Commodity (London)",
    "CBU0.UK": "USD Treasury Bond 7–10 Yr (London)",
    "DTLA.UK": "USD Treasury Bond 20+ Yr (London)",
    "EGLN.L": "Physical Gold (London)",
    "SIE.DE": "Siemens (Xetra)",
    "SU.PA": "Schneider Electric (Euronext Paris)",
    "KER.PA": "Kering (Euronext Paris)",
    "FR.PA": "Valeo (Euronext Paris)",
    "OVH.PA": "OVHcloud (Euronext Paris)",
    "ETL.PA": "Eutelsat (Euronext Paris)",
    "HAG.DE": "Hensoldt (Xetra)",
    "IDR.MC": "Indra (Madrid Stock Exchange)",
    "RKLB": "Rocket Lab (NASDAQ)",
    "DELL": "Dell Technologies (NYSE)",
}

# Create a dictionary to categorize tickers
TICKER_CATEGORIES = {
    ticker: "ETF" for ticker in ETF_TICKERS
}
TICKER_CATEGORIES.update({ticker: "European Stock" for ticker in EU_STOCK_TICKERS})
TICKER_CATEGORIES.update({ticker: "US Stock" for ticker in US_STOCK_TICKERS})

# Default allocation strategy percentages
DEFAULT_ETF_ALLOCATION = 0.5  # 50% for ETFs
DEFAULT_EU_STOCKS_ALLOCATION = 0.4  # 40% for European stocks
DEFAULT_US_STOCKS_ALLOCATION = 0.1  # 10% for US stocks

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import os
import time
import random

class MarketData:
    def __init__(self, cache_dir='data/cache'):
        """Initialize the MarketData class with a cache directory."""
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        self.market_cap_cache_file = os.path.join(cache_dir, 'market_cap_data.csv')
        self.price_cache_file = os.path.join(cache_dir, 'price_data.csv')
        
    def get_current_price(self, tickers, force_update=False):
        """Get the current price for a list of tickers."""
        if not force_update and os.path.exists(self.price_cache_file):
            try:
                price_data = pd.read_csv(self.price_cache_file, index_col=0)
                # Check if all tickers are in the cache
                if all(ticker in price_data.index for ticker in tickers):
                    return price_data
            except Exception as e:
                print(f"Error reading price cache: {e}")
        
        # Fetch new data
        price_data = pd.DataFrame(columns=['price', 'currency', 'last_updated'])
        
        for ticker in tickers:
            try:
                # Add a random delay between requests to avoid rate limiting
                time.sleep(random.uniform(1.0, 2.0))
                
                stock = yf.Ticker(ticker)
                
                # Try to get data from history first (more reliable)
                try:
                    hist = stock.history(period="1d")
                    if not hist.empty:
                        price = hist['Close'].iloc[-1]
                    else:
                        raise ValueError("No historical data available")
                except Exception:
                    # Fallback to info
                    info = stock.info
                    
                    # Get the current price
                    if 'regularMarketPrice' in info and info['regularMarketPrice'] is not None:
                        price = info['regularMarketPrice']
                    elif 'previousClose' in info and info['previousClose'] is not None:
                        price = info['previousClose']
                    else:
                        price = np.nan
                
                # Get the currency
                try:
                    info = stock.info
                    currency = info.get('currency', 'Unknown')
                except:
                    currency = 'Unknown'
                
                price_data.loc[ticker] = [price, currency, datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
                print(f"Successfully fetched price for {ticker}: {price} {currency}")
                
            except Exception as e:
                print(f"Error fetching price for {ticker}: {e}")
                # If we have cached data for this ticker, use it instead of NaN
                if not force_update and os.path.exists(self.price_cache_file):
                    try:
                        old_data = pd.read_csv(self.price_cache_file, index_col=0)
                        if ticker in old_data.index:
                            price_data.loc[ticker] = old_data.loc[ticker]
                            print(f"Using cached data for {ticker}")
                            continue
                    except:
                        pass
                
                price_data.loc[ticker] = [np.nan, 'Unknown', datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
        
        # Save to cache
        price_data.to_csv(self.price_cache_file)
        
        return price_data
    
    def get_market_cap(self, tickers, force_update=False):
        """Get the market cap for a list of tickers."""
        if not force_update and os.path.exists(self.market_cap_cache_file):
            try:
                market_cap_data = pd.read_csv(self.market_cap_cache_file, index_col=0)
                # Check if all tickers are in the cache
                if all(ticker in market_cap_data.index for ticker in tickers):
                    return market_cap_data
            except Exception as e:
                print(f"Error reading market cap cache: {e}")
        
        # Fetch new data
        market_cap_data = pd.DataFrame(columns=['market_cap', 'currency', 'last_updated'])
        
        for ticker in tickers:
            try:
                # Add a random delay between requests to avoid rate limiting
                time.sleep(random.uniform(1.0, 2.0))
                
                stock = yf.Ticker(ticker)
                info = stock.info
                
                # Get the market cap
                market_cap = info.get('marketCap', np.nan)
                
                # Get the currency
                currency = info.get('currency', 'Unknown')
                
                market_cap_data.loc[ticker] = [market_cap, currency, datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
                print(f"Successfully fetched market cap for {ticker}: {market_cap} {currency}")
                
            except Exception as e:
                print(f"Error fetching market cap for {ticker}: {e}")
                
                # If we have cached data for this ticker, use it instead of NaN
                if not force_update and os.path.exists(self.market_cap_cache_file):
                    try:
                        old_data = pd.read_csv(self.market_cap_cache_file, index_col=0)
                        if ticker in old_data.index:
                            market_cap_data.loc[ticker] = old_data.loc[ticker]
                            print(f"Using cached data for {ticker}")
                            continue
                    except:
                        pass
                
                market_cap_data.loc[ticker] = [np.nan, 'Unknown', datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
        
        # Save to cache
        market_cap_data.to_csv(self.market_cap_cache_file)
        
        return market_cap_data
    
    def update_data(self, tickers):
        """Force update of all market data."""
        print(f"Updating market data for {len(tickers)} tickers...")
        self.get_current_price(tickers, force_update=True)
        self.get_market_cap(tickers, force_update=True)
        return True
        
    def load_sample_data(self):
        """
        Load sample data for testing when Yahoo Finance API is unavailable.
        This creates mock data files that can be used when the API is rate-limited.
        """
        # Sample price data
        price_data = pd.DataFrame(columns=['price', 'currency', 'last_updated'])
        
        # ETFs
        price_data.loc["SXR8.DE"] = [420.50, "EUR", datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
        price_data.loc["ZPRR.DE"] = [210.75, "EUR", datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
        price_data.loc["EXS5.DE"] = [130.25, "EUR", datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
        price_data.loc["MEUD.PA"] = [95.60, "EUR", datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
        price_data.loc["XNKY.DE"] = [180.40, "EUR", datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
        price_data.loc["XGLE.DE"] = [110.30, "EUR", datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
        price_data.loc["ICOM.UK"] = [22.15, "GBP", datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
        price_data.loc["CBU0.UK"] = [18.75, "GBP", datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
        price_data.loc["DTLA.UK"] = [15.20, "GBP", datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
        price_data.loc["EGLN.L"] = [150.80, "GBP", datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
        
        # European stocks
        price_data.loc["SIE.DE"] = [175.30, "EUR", datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
        price_data.loc["SU.PA"] = [220.45, "EUR", datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
        price_data.loc["KER.PA"] = [380.60, "EUR", datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
        price_data.loc["FR.PA"] = [12.75, "EUR", datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
        price_data.loc["OVH.PA"] = [7.85, "EUR", datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
        price_data.loc["ETL.PA"] = [4.32, "EUR", datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
        price_data.loc["HAG.DE"] = [35.40, "EUR", datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
        price_data.loc["IDR.MC"] = [11.25, "EUR", datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
        
        # US stocks
        price_data.loc["RKLB"] = [4.20, "USD", datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
        price_data.loc["DELL"] = [120.50, "USD", datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
        
        # Sample market cap data
        market_cap_data = pd.DataFrame(columns=['market_cap', 'currency', 'last_updated'])
        
        # ETFs (ETFs don't have market cap, but we'll add some values for testing)
        market_cap_data.loc["SXR8.DE"] = [np.nan, "EUR", datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
        market_cap_data.loc["ZPRR.DE"] = [np.nan, "EUR", datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
        market_cap_data.loc["EXS5.DE"] = [np.nan, "EUR", datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
        market_cap_data.loc["MEUD.PA"] = [np.nan, "EUR", datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
        market_cap_data.loc["XNKY.DE"] = [np.nan, "EUR", datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
        market_cap_data.loc["XGLE.DE"] = [np.nan, "EUR", datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
        market_cap_data.loc["ICOM.UK"] = [np.nan, "GBP", datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
        market_cap_data.loc["CBU0.UK"] = [np.nan, "GBP", datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
        market_cap_data.loc["DTLA.UK"] = [np.nan, "GBP", datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
        market_cap_data.loc["EGLN.L"] = [np.nan, "GBP", datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
        
        # European stocks
        market_cap_data.loc["SIE.DE"] = [120000000000, "EUR", datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
        market_cap_data.loc["SU.PA"] = [85000000000, "EUR", datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
        market_cap_data.loc["KER.PA"] = [45000000000, "EUR", datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
        market_cap_data.loc["FR.PA"] = [3500000000, "EUR", datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
        market_cap_data.loc["OVH.PA"] = [750000000, "EUR", datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
        market_cap_data.loc["ETL.PA"] = [1200000000, "EUR", datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
        market_cap_data.loc["HAG.DE"] = [4500000000, "EUR", datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
        market_cap_data.loc["IDR.MC"] = [2000000000, "EUR", datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
        
        # US stocks
        market_cap_data.loc["RKLB"] = [2000000000, "USD", datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
        market_cap_data.loc["DELL"] = [95000000000, "USD", datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
        
        # Save to cache
        price_data.to_csv(self.price_cache_file)
        market_cap_data.to_csv(self.market_cap_cache_file)
        
        print("Sample data loaded successfully!")
        return True

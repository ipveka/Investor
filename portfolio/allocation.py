import pandas as pd
import numpy as np
from config import DEFAULT_ETF_ALLOCATION, DEFAULT_EU_STOCKS_ALLOCATION, DEFAULT_US_STOCKS_ALLOCATION

class PortfolioAllocator:
    def __init__(self, market_data):
        """Initialize the PortfolioAllocator with market data."""
        self.market_data = market_data
        
    def allocate_default_strategy(self, etf_tickers, eu_stock_tickers, us_stock_tickers, initial_investment):
        """
        Allocate portfolio according to the default strategy:
        - 50% for ETFs (equal weight for each ETF)
        - 40% for European stocks weighted by market cap
        - 10% for US stocks with inverted market cap weighting
        """
        allocation = pd.DataFrame(columns=['ticker', 'weight', 'amount', 'shares', 'price', 'market_cap'])
        
        # Get market cap data
        all_tickers = etf_tickers + eu_stock_tickers + us_stock_tickers
        market_cap_data = self.market_data.get_market_cap(all_tickers)
        price_data = self.market_data.get_current_price(all_tickers)
        
        # Calculate ETF allocation (equal weight)
        etf_allocation = DEFAULT_ETF_ALLOCATION  # 50% for ETFs
        if etf_tickers:
            etf_weight_per_ticker = etf_allocation / len(etf_tickers)
            for ticker in etf_tickers:
                price = price_data.loc[ticker, 'price']
                market_cap = market_cap_data.loc[ticker, 'market_cap']
                amount = initial_investment * etf_weight_per_ticker
                shares = int(amount / price) if not pd.isna(price) and price > 0 else 0
                actual_amount = shares * price if not pd.isna(price) else 0
                
                allocation = pd.concat([allocation, pd.DataFrame({
                    'ticker': [ticker],
                    'weight': [etf_weight_per_ticker],
                    'amount': [actual_amount],
                    'shares': [shares],
                    'price': [price],
                    'market_cap': [market_cap]
                })], ignore_index=True)
        
        # Calculate European stocks allocation (weighted by market cap)
        eu_allocation = DEFAULT_EU_STOCKS_ALLOCATION  # 40% for European stocks
        if eu_stock_tickers:
            eu_market_caps = market_cap_data.loc[eu_stock_tickers, 'market_cap']
            # Filter out NaN values
            eu_market_caps = eu_market_caps[~pd.isna(eu_market_caps)]
            
            if not eu_market_caps.empty and eu_market_caps.sum() > 0:
                eu_weights = eu_market_caps / eu_market_caps.sum() * eu_allocation
                
                for ticker in eu_stock_tickers:
                    if ticker in eu_weights.index:
                        weight = eu_weights[ticker]
                        price = price_data.loc[ticker, 'price']
                        market_cap = market_cap_data.loc[ticker, 'market_cap']
                        amount = initial_investment * weight
                        shares = int(amount / price) if not pd.isna(price) and price > 0 else 0
                        actual_amount = shares * price if not pd.isna(price) else 0
                        
                        allocation = pd.concat([allocation, pd.DataFrame({
                            'ticker': [ticker],
                            'weight': [weight],
                            'amount': [actual_amount],
                            'shares': [shares],
                            'price': [price],
                            'market_cap': [market_cap]
                        })], ignore_index=True)
            else:
                # Equal weight if market cap data is not available
                eu_weight_per_ticker = eu_allocation / len(eu_stock_tickers)
                for ticker in eu_stock_tickers:
                    price = price_data.loc[ticker, 'price']
                    market_cap = market_cap_data.loc[ticker, 'market_cap']
                    amount = initial_investment * eu_weight_per_ticker
                    shares = int(amount / price) if not pd.isna(price) and price > 0 else 0
                    actual_amount = shares * price if not pd.isna(price) else 0
                    
                    allocation = pd.concat([allocation, pd.DataFrame({
                        'ticker': [ticker],
                        'weight': [eu_weight_per_ticker],
                        'amount': [actual_amount],
                        'shares': [shares],
                        'price': [price],
                        'market_cap': [market_cap]
                    })], ignore_index=True)
        
        # Calculate US stocks allocation (inverted market cap weighting)
        us_allocation = DEFAULT_US_STOCKS_ALLOCATION  # 10% for US stocks
        if us_stock_tickers:
            us_market_caps = market_cap_data.loc[us_stock_tickers, 'market_cap']
            # Filter out NaN values
            us_market_caps = us_market_caps[~pd.isna(us_market_caps)]
            
            if not us_market_caps.empty and us_market_caps.sum() > 0:
                # Invert market caps (smaller cap gets higher weight)
                inverted_caps = 1 / us_market_caps
                us_weights = inverted_caps / inverted_caps.sum() * us_allocation
                
                for ticker in us_stock_tickers:
                    if ticker in us_weights.index:
                        weight = us_weights[ticker]
                        price = price_data.loc[ticker, 'price']
                        market_cap = market_cap_data.loc[ticker, 'market_cap']
                        amount = initial_investment * weight
                        shares = int(amount / price) if not pd.isna(price) and price > 0 else 0
                        actual_amount = shares * price if not pd.isna(price) else 0
                        
                        allocation = pd.concat([allocation, pd.DataFrame({
                            'ticker': [ticker],
                            'weight': [weight],
                            'amount': [actual_amount],
                            'shares': [shares],
                            'price': [price],
                            'market_cap': [market_cap]
                        })], ignore_index=True)
            else:
                # Equal weight if market cap data is not available
                us_weight_per_ticker = us_allocation / len(us_stock_tickers)
                for ticker in us_stock_tickers:
                    price = price_data.loc[ticker, 'price']
                    market_cap = market_cap_data.loc[ticker, 'market_cap']
                    amount = initial_investment * us_weight_per_ticker
                    shares = int(amount / price) if not pd.isna(price) and price > 0 else 0
                    actual_amount = shares * price if not pd.isna(price) else 0
                    
                    allocation = pd.concat([allocation, pd.DataFrame({
                        'ticker': [ticker],
                        'weight': [us_weight_per_ticker],
                        'amount': [actual_amount],
                        'shares': [shares],
                        'price': [price],
                        'market_cap': [market_cap]
                    })], ignore_index=True)
        
        # Calculate cash left (unallocated capital)
        total_invested = allocation['amount'].sum()
        cash = initial_investment - total_invested
        
        # Add cash to allocation
        if cash > 0:
            allocation = pd.concat([allocation, pd.DataFrame({
                'ticker': ['CASH'],
                'weight': [cash / initial_investment],
                'amount': [cash],
                'shares': [1],
                'price': [cash],
                'market_cap': [np.nan]
            })], ignore_index=True)
        
        return allocation
    
    def allocate_custom(self, tickers, weights, initial_investment):
        """
        Allocate portfolio based on custom weights provided by the user.
        
        Parameters:
        - tickers: List of ticker symbols
        - weights: List of weights (should sum to 1)
        - initial_investment: Total investment amount
        
        Returns:
        - DataFrame with allocation details
        """
        # Normalize weights to ensure they sum to 1
        weights = np.array(weights)
        weights = weights / weights.sum()
        
        # Get price data
        price_data = self.market_data.get_current_price(tickers)
        market_cap_data = self.market_data.get_market_cap(tickers)
        
        allocation = pd.DataFrame(columns=['ticker', 'weight', 'amount', 'shares', 'price', 'market_cap'])
        
        for ticker, weight in zip(tickers, weights):
            price = price_data.loc[ticker, 'price']
            market_cap = market_cap_data.loc[ticker, 'market_cap']
            amount = initial_investment * weight
            shares = int(amount / price) if not pd.isna(price) and price > 0 else 0
            actual_amount = shares * price if not pd.isna(price) else 0
            
            allocation = pd.concat([allocation, pd.DataFrame({
                'ticker': [ticker],
                'weight': [weight],
                'amount': [actual_amount],
                'shares': [shares],
                'price': [price],
                'market_cap': [market_cap]
            })], ignore_index=True)
        
        # Calculate cash left (unallocated capital)
        total_invested = allocation['amount'].sum()
        cash = initial_investment - total_invested
        
        # Add cash to allocation
        if cash > 0:
            allocation = pd.concat([allocation, pd.DataFrame({
                'ticker': ['CASH'],
                'weight': [cash / initial_investment],
                'amount': [cash],
                'shares': [1],
                'price': [cash],
                'market_cap': [np.nan]
            })], ignore_index=True)
        
        return allocation

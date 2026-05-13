import pandas as pd
import numpy as np
from config import DEFAULT_ETF_ALLOCATION, DEFAULT_EU_STOCKS_ALLOCATION, DEFAULT_US_STOCKS_ALLOCATION

ALLOCATION_COLUMNS = ['ticker', 'weight', 'amount', 'shares', 'price', 'market_cap']


class PortfolioAllocator:
    def __init__(self, market_data):
        """Initialize the PortfolioAllocator with market data."""
        self.market_data = market_data

    def _build_row(self, ticker, weight, price_data, market_cap_data, initial_investment):
        """Build a single allocation row for a ticker given its target weight."""
        price = price_data.loc[ticker, 'price']
        market_cap = market_cap_data.loc[ticker, 'market_cap']
        amount = initial_investment * weight
        shares = int(amount / price) if not pd.isna(price) and price > 0 else 0
        actual_amount = shares * price if not pd.isna(price) else 0
        return {
            'ticker': ticker,
            'weight': weight,
            'amount': actual_amount,
            'shares': shares,
            'price': price,
            'market_cap': market_cap,
        }

    def _category_weights(self, tickers, allocation_share, weighting, market_cap_data):
        """
        Return a pandas Series mapping ticker -> target weight for one asset category.

        weighting:
            'equal'              - equal weight across tickers
            'market_cap'         - weight by market cap (falls back to equal if unavailable)
            'inverse_market_cap' - weight by 1/market_cap (falls back to equal if unavailable)
        """
        if weighting in ('market_cap', 'inverse_market_cap'):
            caps = market_cap_data.loc[tickers, 'market_cap']
            caps = caps[~pd.isna(caps)]
            if not caps.empty and caps.sum() > 0:
                base = (1 / caps) if weighting == 'inverse_market_cap' else caps
                return (base / base.sum()) * allocation_share

        equal_weight = allocation_share / len(tickers)
        return pd.Series({t: equal_weight for t in tickers})

    def _allocate_category(self, tickers, allocation_share, weighting,
                           price_data, market_cap_data, initial_investment):
        """Build allocation rows for one asset category."""
        if not tickers:
            return []
        weights = self._category_weights(tickers, allocation_share, weighting, market_cap_data)
        return [
            self._build_row(ticker, float(weights[ticker]),
                            price_data, market_cap_data, initial_investment)
            for ticker in tickers if ticker in weights.index
        ]

    def _append_cash(self, allocation, initial_investment):
        """Append a CASH row for unallocated capital, if any."""
        cash = initial_investment - allocation['amount'].sum()
        if cash <= 0:
            return allocation
        cash_row = pd.DataFrame([{
            'ticker': 'CASH',
            'weight': cash / initial_investment,
            'amount': cash,
            'shares': 1,
            'price': cash,
            'market_cap': np.nan,
        }])
        return pd.concat([allocation, cash_row], ignore_index=True)

    def allocate_default_strategy(self, etf_tickers, eu_stock_tickers, us_stock_tickers, initial_investment):
        """
        Allocate portfolio according to the default strategy:
        - 50% for ETFs (equal weight for each ETF)
        - 40% for European stocks weighted by market cap
        - 10% for US stocks with inverted market cap weighting
        """
        all_tickers = etf_tickers + eu_stock_tickers + us_stock_tickers
        market_cap_data = self.market_data.get_market_cap(all_tickers)
        price_data = self.market_data.get_current_price(all_tickers)

        rows = []
        rows += self._allocate_category(
            etf_tickers, DEFAULT_ETF_ALLOCATION, 'equal',
            price_data, market_cap_data, initial_investment,
        )
        rows += self._allocate_category(
            eu_stock_tickers, DEFAULT_EU_STOCKS_ALLOCATION, 'market_cap',
            price_data, market_cap_data, initial_investment,
        )
        rows += self._allocate_category(
            us_stock_tickers, DEFAULT_US_STOCKS_ALLOCATION, 'inverse_market_cap',
            price_data, market_cap_data, initial_investment,
        )

        allocation = pd.DataFrame(rows, columns=ALLOCATION_COLUMNS)
        return self._append_cash(allocation, initial_investment)

    def allocate_custom(self, tickers, weights, initial_investment):
        """
        Allocate portfolio based on custom weights provided by the user.

        Parameters:
        - tickers: List of ticker symbols
        - weights: List of weights (will be normalized to sum to 1)
        - initial_investment: Total investment amount

        Returns:
        - DataFrame with allocation details
        """
        weights = np.array(weights, dtype=float)
        weights = weights / weights.sum()

        price_data = self.market_data.get_current_price(tickers)
        market_cap_data = self.market_data.get_market_cap(tickers)

        rows = [
            self._build_row(ticker, float(weight), price_data, market_cap_data, initial_investment)
            for ticker, weight in zip(tickers, weights)
        ]
        allocation = pd.DataFrame(rows, columns=ALLOCATION_COLUMNS)
        return self._append_cash(allocation, initial_investment)

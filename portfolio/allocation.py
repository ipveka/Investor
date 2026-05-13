import pandas as pd
import numpy as np
from config import DEFAULT_ETF_ALLOCATION, DEFAULT_EU_STOCKS_ALLOCATION, DEFAULT_US_STOCKS_ALLOCATION

ALLOCATION_COLUMNS = [
    "ticker", "weight", "amount", "shares",
    "price", "raw_price", "currency", "fx_rate",
    "market_cap",
]


class PortfolioAllocator:
    def __init__(self, market_data, fx_converter=None, base_currency="EUR"):
        """Initialize the PortfolioAllocator.

        Parameters
        ----------
        market_data : MarketData
            Source of prices and market caps.
        fx_converter : FXConverter, optional
            When provided, prices and market caps are converted from each
            ticker's native currency to ``base_currency`` before the allocation
            math runs. When omitted, all values are treated as already in the
            base currency (fx_rate=1).
        base_currency : str
            Currency code in which ``initial_investment`` is denominated.
        """
        self.market_data = market_data
        self.fx_converter = fx_converter
        self.base_currency = base_currency

    def _rate(self, currency):
        if self.fx_converter is None:
            return 1.0
        return self.fx_converter.get_rate(currency, self.base_currency)

    def _build_row(self, ticker, weight, price_data, market_cap_data, initial_investment):
        raw_price = price_data.loc[ticker, "price"]
        currency = (
            price_data.loc[ticker, "currency"]
            if "currency" in price_data.columns else self.base_currency
        )
        market_cap = market_cap_data.loc[ticker, "market_cap"]

        fx_rate = self._rate(currency)
        effective_price = raw_price * fx_rate if not pd.isna(raw_price) else raw_price
        market_cap_base = (
            market_cap * fx_rate if not pd.isna(market_cap) else market_cap
        )

        target_amount = initial_investment * weight
        if pd.isna(effective_price) or effective_price <= 0:
            shares = 0
            actual_amount = 0
        else:
            shares = int(target_amount / effective_price)
            actual_amount = shares * effective_price

        return {
            "ticker": ticker,
            "weight": weight,
            "amount": actual_amount,
            "shares": shares,
            "price": effective_price,
            "raw_price": raw_price,
            "currency": currency,
            "fx_rate": fx_rate,
            "market_cap": market_cap_base,
        }

    def _category_weights(self, tickers, allocation_share, weighting,
                          price_data, market_cap_data):
        """
        Return a pandas Series mapping ticker -> target weight for one category.

        Market caps are converted to the base currency before being used to
        weight, so a EUR-priced and a GBP-priced stock are weighted on the same
        scale.
        """
        if weighting in ("market_cap", "inverse_market_cap"):
            caps = market_cap_data.loc[tickers, "market_cap"].astype(float).copy()
            if self.fx_converter is not None and "currency" in price_data.columns:
                for t in tickers:
                    if pd.notna(caps.loc[t]):
                        caps.loc[t] = caps.loc[t] * self._rate(price_data.loc[t, "currency"])
            caps = caps[~pd.isna(caps)]
            if not caps.empty and caps.sum() > 0:
                base = (1 / caps) if weighting == "inverse_market_cap" else caps
                return (base / base.sum()) * allocation_share

        equal_weight = allocation_share / len(tickers)
        return pd.Series({t: equal_weight for t in tickers})

    def _allocate_category(self, tickers, allocation_share, weighting,
                           price_data, market_cap_data, initial_investment):
        if not tickers:
            return []
        weights = self._category_weights(
            tickers, allocation_share, weighting, price_data, market_cap_data,
        )
        return [
            self._build_row(ticker, float(weights[ticker]),
                            price_data, market_cap_data, initial_investment)
            for ticker in tickers if ticker in weights.index
        ]

    def _append_cash(self, allocation, initial_investment):
        cash = initial_investment - allocation["amount"].sum()
        if cash <= 0:
            return allocation
        cash_row = pd.DataFrame([{
            "ticker": "CASH",
            "weight": cash / initial_investment,
            "amount": cash,
            "shares": 1,
            "price": cash,
            "raw_price": cash,
            "currency": self.base_currency,
            "fx_rate": 1.0,
            "market_cap": np.nan,
        }])
        return pd.concat([allocation, cash_row], ignore_index=True)

    def _enrich_with_currencies(self, price_data, tickers):
        """If MarketData can supply currencies and they are missing, fill them in."""
        if "currency" not in price_data.columns:
            return price_data
        unknown = [
            t for t in tickers
            if t in price_data.index
            and price_data.loc[t, "currency"] in (None, "", "Unknown")
        ]
        if not unknown or not hasattr(self.market_data, "get_currencies"):
            return price_data
        try:
            currencies = self.market_data.get_currencies(unknown)
        except Exception:
            return price_data
        for t, ccy in currencies.items():
            if t in price_data.index:
                price_data.loc[t, "currency"] = ccy
        return price_data

    def allocate_default_strategy(self, etf_tickers, eu_stock_tickers, us_stock_tickers,
                                  initial_investment):
        """
        Allocate portfolio according to the default strategy:
        - 50% for ETFs (equal weight for each ETF)
        - 40% for European stocks weighted by market cap (in base currency)
        - 10% for US stocks with inverted market cap weighting (in base currency)
        """
        all_tickers = etf_tickers + eu_stock_tickers + us_stock_tickers
        market_cap_data = self.market_data.get_market_cap(all_tickers)
        price_data = self.market_data.get_current_price(all_tickers)
        price_data = self._enrich_with_currencies(price_data, all_tickers)

        rows = []
        rows += self._allocate_category(
            etf_tickers, DEFAULT_ETF_ALLOCATION, "equal",
            price_data, market_cap_data, initial_investment,
        )
        rows += self._allocate_category(
            eu_stock_tickers, DEFAULT_EU_STOCKS_ALLOCATION, "market_cap",
            price_data, market_cap_data, initial_investment,
        )
        rows += self._allocate_category(
            us_stock_tickers, DEFAULT_US_STOCKS_ALLOCATION, "inverse_market_cap",
            price_data, market_cap_data, initial_investment,
        )

        allocation = pd.DataFrame(rows, columns=ALLOCATION_COLUMNS)
        return self._append_cash(allocation, initial_investment)

    def allocate_custom(self, tickers, weights, initial_investment):
        """
        Allocate portfolio based on custom weights provided by the user.
        Weights are normalised to sum to 1 before being applied.
        """
        weights = np.array(weights, dtype=float)
        weights = weights / weights.sum()

        price_data = self.market_data.get_current_price(tickers)
        market_cap_data = self.market_data.get_market_cap(tickers)
        price_data = self._enrich_with_currencies(price_data, tickers)

        rows = [
            self._build_row(ticker, float(weight),
                            price_data, market_cap_data, initial_investment)
            for ticker, weight in zip(tickers, weights)
        ]
        allocation = pd.DataFrame(rows, columns=ALLOCATION_COLUMNS)
        return self._append_cash(allocation, initial_investment)

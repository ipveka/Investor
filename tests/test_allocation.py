import numpy as np
import pandas as pd
import pytest

from portfolio.allocation import PortfolioAllocator


class FakeMarketData:
    """In-memory market data stub for deterministic allocator tests."""

    def __init__(self, prices, market_caps):
        self._prices = prices
        self._market_caps = market_caps

    def get_current_price(self, tickers):
        rows = {t: [self._prices.get(t, np.nan), "EUR"] for t in tickers}
        return pd.DataFrame.from_dict(rows, orient="index", columns=["price", "currency"])

    def get_market_cap(self, tickers):
        rows = {t: [self._market_caps.get(t, np.nan), "EUR"] for t in tickers}
        return pd.DataFrame.from_dict(rows, orient="index", columns=["market_cap", "currency"])


@pytest.fixture
def market_data():
    prices = {
        "ETF1": 100.0, "ETF2": 50.0,
        "EU1": 200.0, "EU2": 100.0, "EU3": 10.0,
        "US1": 5.0, "US2": 120.0,
        "ZERO": 0.0,
        "NAN": np.nan,
    }
    market_caps = {
        "ETF1": np.nan, "ETF2": np.nan,
        "EU1": 100e9, "EU2": 50e9, "EU3": 1e9,
        "US1": 2e9, "US2": 100e9,
        "ZERO": 1e9, "NAN": 1e9,
    }
    return FakeMarketData(prices, market_caps)


@pytest.fixture
def allocator(market_data):
    return PortfolioAllocator(market_data)


def _rows(df, ticker):
    return df[df["ticker"] == ticker]


def test_etfs_equal_weighted(allocator):
    df = allocator.allocate_default_strategy(["ETF1", "ETF2"], [], [], 10_000)

    etfs = df[df["ticker"].isin(["ETF1", "ETF2"])]
    assert len(etfs) == 2
    # 50% allocation split equally across 2 ETFs -> 25% each.
    assert etfs["weight"].tolist() == pytest.approx([0.25, 0.25])
    # ETF1 @ €100, target €2500 -> 25 shares = €2500 invested.
    assert _rows(df, "ETF1")["shares"].iloc[0] == 25
    assert _rows(df, "ETF1")["amount"].iloc[0] == pytest.approx(2500.0)
    # ETF2 @ €50, target €2500 -> 50 shares.
    assert _rows(df, "ETF2")["shares"].iloc[0] == 50


def test_eu_stocks_market_cap_weighted(allocator):
    df = allocator.allocate_default_strategy([], ["EU1", "EU2", "EU3"], [], 100_000)

    eu = df[df["ticker"].isin(["EU1", "EU2", "EU3"])].set_index("ticker")
    total_cap = 100e9 + 50e9 + 1e9
    # 40% category share, weighted by market cap.
    assert eu.loc["EU1", "weight"] == pytest.approx(0.40 * 100e9 / total_cap)
    assert eu.loc["EU2", "weight"] == pytest.approx(0.40 * 50e9 / total_cap)
    assert eu.loc["EU3", "weight"] == pytest.approx(0.40 * 1e9 / total_cap)
    # Weights inside the category sum to the category share.
    assert eu["weight"].sum() == pytest.approx(0.40)


def test_us_stocks_inverse_market_cap_weighted(allocator):
    df = allocator.allocate_default_strategy([], [], ["US1", "US2"], 10_000)

    us = df[df["ticker"].isin(["US1", "US2"])].set_index("ticker")
    # Smaller-cap US1 should outweigh larger-cap US2.
    assert us.loc["US1", "weight"] > us.loc["US2", "weight"]
    # 10% category share for US stocks.
    assert us["weight"].sum() == pytest.approx(0.10)
    inv_total = 1 / 2e9 + 1 / 100e9
    assert us.loc["US1", "weight"] == pytest.approx(0.10 * (1 / 2e9) / inv_total)


def test_missing_market_caps_fall_back_to_equal(allocator):
    df = allocator.allocate_default_strategy([], ["ETF1", "ETF2"], [], 10_000)

    eu = df[df["ticker"].isin(["ETF1", "ETF2"])]
    # ETF1/ETF2 have NaN market caps -> equal weight within the 40% slice.
    assert eu["weight"].tolist() == pytest.approx([0.20, 0.20])


def test_empty_categories_skipped(allocator):
    df = allocator.allocate_default_strategy([], [], [], 1_000)
    # No assets selected -> only the CASH row remains.
    assert df["ticker"].tolist() == ["CASH"]
    assert df["amount"].iloc[0] == pytest.approx(1_000)


def test_zero_and_nan_prices_yield_zero_shares(allocator):
    df = allocator.allocate_default_strategy(["ZERO", "NAN"], [], [], 10_000)

    assert _rows(df, "ZERO")["shares"].iloc[0] == 0
    assert _rows(df, "ZERO")["amount"].iloc[0] == 0
    assert _rows(df, "NAN")["shares"].iloc[0] == 0
    assert _rows(df, "NAN")["amount"].iloc[0] == 0


def test_cash_row_captures_unallocated_remainder(allocator):
    df = allocator.allocate_default_strategy(["ETF1", "ETF2"], [], [], 10_000)
    invested = df[df["ticker"] != "CASH"]["amount"].sum()
    cash_row = df[df["ticker"] == "CASH"]
    # ETF1 (25 shares × 100) + ETF2 (50 × 50) = 5000 invested out of 10000.
    assert invested == pytest.approx(5_000)
    assert cash_row["amount"].iloc[0] == pytest.approx(5_000)


def test_custom_allocation_normalises_weights(allocator):
    # Weights given as 1:2:1 -> 0.25 / 0.50 / 0.25 after normalization.
    df = allocator.allocate_custom(["ETF1", "ETF2", "EU1"], [1, 2, 1], 10_000)

    assert _rows(df, "ETF1")["weight"].iloc[0] == pytest.approx(0.25)
    assert _rows(df, "ETF2")["weight"].iloc[0] == pytest.approx(0.50)
    assert _rows(df, "EU1")["weight"].iloc[0] == pytest.approx(0.25)


def test_custom_allocation_returns_expected_columns(allocator):
    df = allocator.allocate_custom(["ETF1"], [1.0], 1_000)
    assert list(df.columns) == ["ticker", "weight", "amount", "shares", "price", "market_cap"]

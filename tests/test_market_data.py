"""Tests for the batched price fetch in data.market_data."""
import numpy as np
import pandas as pd
import pytest

from data import market_data as md_module
from data.market_data import MarketData


def _make_multi_index_frame(tickers, closes):
    """Mimic the MultiIndex shape yfinance returns for multi-ticker downloads."""
    cols = pd.MultiIndex.from_product([["Close", "Open"], tickers])
    rows = []
    for c in closes:
        rows.append(list(c) + [0.0] * len(tickers))
    idx = pd.date_range("2024-01-01", periods=len(closes), freq="B")
    return pd.DataFrame(rows, index=idx, columns=cols)


@pytest.fixture
def market(tmp_path):
    return MarketData(cache_dir=str(tmp_path))


def test_batch_fetch_populates_prices(monkeypatch, market):
    calls = []

    def fake_download(tickers, **kwargs):
        calls.append(tickers)
        return _make_multi_index_frame(tickers, closes=[[100.0, 200.0], [101.0, 198.0]])

    monkeypatch.setattr(md_module.yf, "download", fake_download)

    out = market.get_current_price(["AAA", "BBB"])
    assert out.loc["AAA", "price"] == pytest.approx(101.0)
    assert out.loc["BBB", "price"] == pytest.approx(198.0)
    # yfinance.download should be called exactly once even for multiple tickers.
    assert len(calls) == 1


def test_cache_short_circuits_subsequent_calls(monkeypatch, market):
    calls = []

    def fake_download(tickers, **kwargs):
        calls.append(tickers)
        return _make_multi_index_frame(tickers, closes=[[50.0, 75.0]])

    monkeypatch.setattr(md_module.yf, "download", fake_download)

    market.get_current_price(["AAA", "BBB"])
    market.get_current_price(["AAA", "BBB"])
    # Second call reads from the disk cache; no extra yfinance fetch.
    assert len(calls) == 1


def test_force_update_refetches(monkeypatch, market):
    calls = []

    def fake_download(tickers, **kwargs):
        calls.append(tickers)
        return _make_multi_index_frame(tickers, closes=[[10.0, 20.0]])

    monkeypatch.setattr(md_module.yf, "download", fake_download)

    market.get_current_price(["AAA", "BBB"])
    market.get_current_price(["AAA", "BBB"], force_update=True)
    assert len(calls) == 2


def test_batch_failure_returns_nan_rows(monkeypatch, market):
    def boom(*args, **kwargs):
        raise RuntimeError("network down")

    monkeypatch.setattr(md_module.yf, "download", boom)
    out = market.get_current_price(["AAA"])
    assert np.isnan(out.loc["AAA", "price"])


def test_empty_ticker_list_short_circuits(market):
    out = market.get_current_price([])
    assert out.empty
    assert list(out.columns) == ["price", "currency", "last_updated"]

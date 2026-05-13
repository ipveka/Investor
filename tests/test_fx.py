"""Tests for the FXConverter spot-rate module."""
import pandas as pd
import pytest

from data import fx as fx_module
from data.fx import FXConverter, currency_symbol


@pytest.fixture
def converter(tmp_path):
    return FXConverter(cache_dir=str(tmp_path))


def _close_frame(value, dates=None):
    idx = dates or pd.date_range("2024-01-01", periods=1, freq="B")
    return pd.DataFrame({"Close": [value]}, index=idx)


def test_same_currency_is_identity(converter):
    assert converter.get_rate("EUR", "EUR") == 1.0
    assert converter.get_rate("USD", "USD") == 1.0


def test_unknown_currency_defaults_to_one(converter):
    assert converter.get_rate("Unknown", "EUR") == 1.0
    assert converter.get_rate("", "EUR") == 1.0
    assert converter.get_rate(None, "EUR") == 1.0


def test_get_rate_fetches_when_missing(monkeypatch, converter):
    calls = []

    def fake_download(symbol, **kwargs):
        calls.append(symbol)
        return _close_frame(1.08)

    monkeypatch.setattr(fx_module, "__name__", fx_module.__name__)  # keep import path
    # Patch yfinance.download where _fetch_rate imports it locally.
    import yfinance as yf
    monkeypatch.setattr(yf, "download", fake_download)

    assert converter.get_rate("EUR", "USD") == pytest.approx(1.08)
    assert calls == ["EURUSD=X"]


def test_inverse_pair_fallback(monkeypatch, converter):
    """When EURUSD=X is unavailable, FXConverter inverts USDEUR=X."""
    seen = []

    def fake_download(symbol, **kwargs):
        seen.append(symbol)
        if symbol == "EURUSD=X":
            return pd.DataFrame()  # empty -> trigger fallback
        if symbol == "USDEUR=X":
            return _close_frame(0.9259)  # implies EURUSD ≈ 1.08
        return pd.DataFrame()

    import yfinance as yf
    monkeypatch.setattr(yf, "download", fake_download)

    rate = converter.get_rate("EUR", "USD")
    assert rate == pytest.approx(1 / 0.9259, rel=1e-6)
    assert seen == ["EURUSD=X", "USDEUR=X"]


def test_rate_is_memoised(monkeypatch, converter):
    calls = []

    def fake_download(symbol, **kwargs):
        calls.append(symbol)
        return _close_frame(1.25)

    import yfinance as yf
    monkeypatch.setattr(yf, "download", fake_download)

    converter.get_rate("GBP", "USD")
    converter.get_rate("GBP", "USD")
    converter.get_rate("GBP", "USD")
    assert len(calls) == 1


def test_disk_cache_survives_new_instance(monkeypatch, tmp_path):
    def fake_download(symbol, **kwargs):
        return _close_frame(1.25)

    import yfinance as yf
    monkeypatch.setattr(yf, "download", fake_download)

    first = FXConverter(cache_dir=str(tmp_path))
    assert first.get_rate("GBP", "USD") == pytest.approx(1.25)

    # New instance should hit the disk cache and not call yfinance.
    calls = []

    def boom(symbol, **kwargs):
        calls.append(symbol)
        raise AssertionError("Should not be called")

    monkeypatch.setattr(yf, "download", boom)
    second = FXConverter(cache_dir=str(tmp_path))
    assert second.get_rate("GBP", "USD") == pytest.approx(1.25)
    assert calls == []


def test_convert_applies_rate(monkeypatch, converter):
    def fake_download(symbol, **kwargs):
        return _close_frame(1.10)

    import yfinance as yf
    monkeypatch.setattr(yf, "download", fake_download)

    assert converter.convert(100, "EUR", "USD") == pytest.approx(110)


def test_fetch_failure_defaults_to_one(monkeypatch, converter):
    import yfinance as yf
    monkeypatch.setattr(yf, "download", lambda *a, **kw: pd.DataFrame())
    assert converter.get_rate("EUR", "JPY") == 1.0


def test_currency_symbol_known_and_unknown():
    assert currency_symbol("EUR") == "€"
    assert currency_symbol("USD") == "$"
    assert currency_symbol("ABC") == "ABC "
    assert currency_symbol(None) == ""

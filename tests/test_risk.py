import numpy as np
import pandas as pd
import pytest

from portfolio import risk


@pytest.fixture
def flat_prices():
    """A flat price series should have zero volatility, zero drawdown, zero return."""
    idx = pd.date_range("2024-01-01", periods=300, freq="B")
    return pd.DataFrame({"FLAT": np.full(len(idx), 100.0)}, index=idx)


@pytest.fixture
def two_asset_prices():
    """One steady up-trender, one drawdown asset, deterministic returns."""
    idx = pd.date_range("2024-01-01", periods=252, freq="B")
    # UP: +0.1% per day
    up = 100.0 * (1.001 ** np.arange(len(idx)))
    # DOWN: rises then dips for a clear drawdown
    half = len(idx) // 2
    down = np.concatenate([
        100.0 * (1.002 ** np.arange(half)),
        100.0 * (1.002 ** half) * (0.998 ** np.arange(len(idx) - half)),
    ])
    return pd.DataFrame({"UP": up, "DOWN": down}, index=idx)


def test_daily_returns_drops_first_row(two_asset_prices):
    returns = risk.daily_returns(two_asset_prices)
    assert len(returns) == len(two_asset_prices) - 1


def test_flat_series_has_zero_volatility(flat_prices):
    returns = risk.daily_returns(flat_prices)
    assert risk.annualized_volatility(returns["FLAT"]) == pytest.approx(0.0)
    assert risk.max_drawdown(flat_prices["FLAT"]) == pytest.approx(0.0)
    assert risk.total_return(flat_prices["FLAT"]) == pytest.approx(0.0)


def test_volatility_is_positive_for_volatile_asset(two_asset_prices):
    returns = risk.daily_returns(two_asset_prices)
    assert risk.annualized_volatility(returns["UP"]) > 0
    assert risk.annualized_volatility(returns["DOWN"]) > 0


def test_max_drawdown_is_negative_for_declining_asset(two_asset_prices):
    # DOWN rises then falls -> drawdown should be strictly negative.
    assert risk.max_drawdown(two_asset_prices["DOWN"]) < 0
    # UP only rises -> drawdown should be ~0.
    assert risk.max_drawdown(two_asset_prices["UP"]) == pytest.approx(0.0, abs=1e-9)


def test_total_return_positive_for_uptrend(two_asset_prices):
    assert risk.total_return(two_asset_prices["UP"]) > 0


def test_sharpe_is_nan_for_flat_series(flat_prices):
    returns = risk.daily_returns(flat_prices)
    assert np.isnan(risk.sharpe_ratio(returns["FLAT"]))


def test_per_ticker_metrics_shape(two_asset_prices):
    metrics = risk.per_ticker_metrics(two_asset_prices)
    assert list(metrics.index) == ["UP", "DOWN"]
    assert set(metrics.columns) == {"volatility", "max_drawdown", "sharpe", "total_return"}


def test_portfolio_metrics_match_underlying(two_asset_prices):
    # 100% weight on UP should match UP's own metrics.
    metrics = risk.portfolio_metrics(two_asset_prices, {"UP": 1.0})
    assert metrics["total_return"] == pytest.approx(risk.total_return(two_asset_prices["UP"]))
    assert metrics["volatility"] == pytest.approx(
        risk.annualized_volatility(risk.daily_returns(two_asset_prices)["UP"])
    )


def test_portfolio_renormalises_weights(two_asset_prices):
    # Weights summing to 0.5 should still produce a coherent portfolio (renormalised).
    m1 = risk.portfolio_metrics(two_asset_prices, {"UP": 0.25, "DOWN": 0.25})
    m2 = risk.portfolio_metrics(two_asset_prices, {"UP": 0.5, "DOWN": 0.5})
    assert m1["total_return"] == pytest.approx(m2["total_return"])
    assert m1["volatility"] == pytest.approx(m2["volatility"])


def test_portfolio_ignores_unknown_tickers(two_asset_prices):
    metrics = risk.portfolio_metrics(two_asset_prices, {"UP": 1.0, "MISSING": 0.5})
    expected = risk.portfolio_metrics(two_asset_prices, {"UP": 1.0})
    assert metrics["total_return"] == pytest.approx(expected["total_return"])


def test_correlation_matrix_dimensions(two_asset_prices):
    corr = risk.correlation_matrix(two_asset_prices)
    assert corr.shape == (2, 2)
    # Diagonal should be 1.
    assert corr.loc["UP", "UP"] == pytest.approx(1.0)
    assert corr.loc["DOWN", "DOWN"] == pytest.approx(1.0)


def test_correlation_matrix_empty_for_single_ticker(flat_prices):
    assert risk.correlation_matrix(flat_prices).empty


def test_empty_inputs_return_safe_defaults():
    empty = pd.DataFrame()
    assert risk.per_ticker_metrics(empty).empty
    assert risk.portfolio_returns(empty, {"X": 1}).empty
    metrics = risk.portfolio_metrics(empty, {"X": 1})
    assert np.isnan(metrics["volatility"])
    assert risk.correlation_matrix(empty).empty

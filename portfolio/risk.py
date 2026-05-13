"""Risk analytics for portfolio allocations.

Computes annualized volatility, max drawdown, Sharpe ratio, total return, and a
correlation matrix from a historical price DataFrame (rows = dates, columns = tickers).
History fetching lives in :func:`fetch_history` which uses yfinance.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

TRADING_DAYS_PER_YEAR = 252


def fetch_history(tickers, period="3y"):
    """
    Fetch adjusted-close history for a list of tickers via yfinance.

    Returns a DataFrame indexed by date with one column per ticker. Tickers that
    fail to download are silently dropped. Returns an empty DataFrame on total
    failure rather than raising, so the caller can display a friendly message.
    """
    if not tickers:
        return pd.DataFrame()

    try:
        import yfinance as yf
    except ImportError:
        return pd.DataFrame()

    try:
        data = yf.download(
            tickers=tickers,
            period=period,
            interval="1d",
            auto_adjust=True,
            progress=False,
            group_by="column",
            threads=True,
        )
    except Exception:
        return pd.DataFrame()

    if data is None or data.empty:
        return pd.DataFrame()

    # yfinance returns a MultiIndex when len(tickers) > 1, a flat frame for a single ticker.
    if isinstance(data.columns, pd.MultiIndex):
        if "Close" in data.columns.get_level_values(0):
            prices = data["Close"]
        else:
            return pd.DataFrame()
    else:
        col = "Close" if "Close" in data.columns else None
        if col is None:
            return pd.DataFrame()
        prices = data[[col]].rename(columns={col: tickers[0]})

    prices = prices.dropna(how="all")
    return prices


def daily_returns(prices):
    """Simple daily returns. Drops the first all-NaN row produced by pct_change."""
    if prices.empty:
        return prices
    return prices.pct_change().dropna(how="all")


def annualized_volatility(returns):
    """Annualized standard deviation of a return series (or float for a single series)."""
    if isinstance(returns, pd.Series):
        if returns.dropna().empty:
            return float("nan")
        return float(returns.std(ddof=0) * np.sqrt(TRADING_DAYS_PER_YEAR))
    return returns.std(ddof=0) * np.sqrt(TRADING_DAYS_PER_YEAR)


def max_drawdown(prices):
    """Maximum peak-to-trough drawdown of a price series (negative number)."""
    if isinstance(prices, pd.Series):
        s = prices.dropna()
        if s.empty:
            return float("nan")
        running_max = s.cummax()
        drawdown = s / running_max - 1.0
        return float(drawdown.min())
    return {col: max_drawdown(prices[col]) for col in prices.columns}


def total_return(prices):
    """Total return over the available period (last/first - 1)."""
    if isinstance(prices, pd.Series):
        s = prices.dropna()
        if len(s) < 2:
            return float("nan")
        return float(s.iloc[-1] / s.iloc[0] - 1.0)
    return {col: total_return(prices[col]) for col in prices.columns}


def sharpe_ratio(returns, risk_free_rate=0.0):
    """
    Annualized Sharpe ratio. Assumes risk_free_rate is an annual figure (e.g. 0.02).
    """
    if isinstance(returns, pd.Series):
        r = returns.dropna()
        if r.empty:
            return float("nan")
        daily_rf = risk_free_rate / TRADING_DAYS_PER_YEAR
        excess = r - daily_rf
        std = excess.std(ddof=0)
        if std == 0 or np.isnan(std):
            return float("nan")
        return float(excess.mean() / std * np.sqrt(TRADING_DAYS_PER_YEAR))
    return {col: sharpe_ratio(returns[col], risk_free_rate) for col in returns.columns}


def per_ticker_metrics(prices, risk_free_rate=0.0):
    """Compute a DataFrame of risk metrics, one row per ticker."""
    if prices.empty:
        return pd.DataFrame(columns=["volatility", "max_drawdown", "sharpe", "total_return"])

    returns = daily_returns(prices)
    rows = {}
    for ticker in prices.columns:
        rows[ticker] = {
            "volatility": annualized_volatility(returns[ticker]),
            "max_drawdown": max_drawdown(prices[ticker]),
            "sharpe": sharpe_ratio(returns[ticker], risk_free_rate),
            "total_return": total_return(prices[ticker]),
        }
    return pd.DataFrame.from_dict(rows, orient="index")


def portfolio_returns(prices, weights):
    """
    Weighted daily-return series for a portfolio.

    `weights` is a dict {ticker: weight}; tickers absent from `prices` are dropped
    and the remaining weights are renormalised so the series sums to 1.
    """
    if prices.empty or not weights:
        return pd.Series(dtype=float)

    aligned = {t: w for t, w in weights.items() if t in prices.columns and w > 0}
    if not aligned:
        return pd.Series(dtype=float)

    total = sum(aligned.values())
    if total <= 0:
        return pd.Series(dtype=float)
    aligned = {t: w / total for t, w in aligned.items()}

    returns = daily_returns(prices[list(aligned.keys())])
    weight_vec = pd.Series(aligned)
    return (returns * weight_vec).sum(axis=1)


def portfolio_metrics(prices, weights, risk_free_rate=0.0):
    """Aggregate volatility, max drawdown, Sharpe and total return for the portfolio."""
    returns = portfolio_returns(prices, weights)
    if returns.empty:
        return {
            "volatility": float("nan"),
            "max_drawdown": float("nan"),
            "sharpe": float("nan"),
            "total_return": float("nan"),
        }
    # Build a portfolio "price" path from cumulative returns so drawdown is well-defined.
    portfolio_price = (1.0 + returns).cumprod()
    return {
        "volatility": annualized_volatility(returns),
        "max_drawdown": max_drawdown(portfolio_price),
        "sharpe": sharpe_ratio(returns, risk_free_rate),
        "total_return": float(portfolio_price.iloc[-1] - 1.0),
    }


def correlation_matrix(prices):
    """Pearson correlation of daily returns. Empty frame if not enough data."""
    if prices.empty or prices.shape[1] < 2:
        return pd.DataFrame()
    returns = daily_returns(prices)
    return returns.corr()


def cumulative_returns(prices, weights):
    """
    Cumulative return path for a portfolio, starting at 1.0.

    Returns a Series indexed by date. Empty if prices/weights are empty.
    """
    returns = portfolio_returns(prices, weights)
    if returns.empty:
        return pd.Series(dtype=float)
    return (1.0 + returns).cumprod()


def benchmark_cumulative(prices):
    """Cumulative return path of a single-column price frame (or Series)."""
    if isinstance(prices, pd.DataFrame):
        if prices.empty:
            return pd.Series(dtype=float)
        series = prices.iloc[:, 0]
    else:
        series = prices
    series = series.dropna()
    if series.empty:
        return pd.Series(dtype=float)
    return series / series.iloc[0]

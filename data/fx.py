"""Spot FX rates via yfinance with in-memory and on-disk caching.

The conversion model is intentionally simple: a single spot rate per currency
pair, applied to today's prices and market caps. Historical FX moves are not
modelled — risk metrics and backtests still operate on native-currency returns.
"""
from __future__ import annotations

import os
from datetime import datetime

import pandas as pd


SUPPORTED_BASE_CURRENCIES = ["EUR", "USD", "GBP"]

CURRENCY_SYMBOLS = {
    "EUR": "€",
    "USD": "$",
    "GBP": "£",
    "JPY": "¥",
    "CHF": "Fr",
}


def currency_symbol(ccy):
    """Display symbol for a currency code (falls back to '{ccy} ')."""
    if not ccy:
        return ""
    return CURRENCY_SYMBOLS.get(ccy, f"{ccy} ")


class FXConverter:
    def __init__(self, cache_dir="data/cache"):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        self.cache_file = os.path.join(cache_dir, "fx_rates.csv")
        self._cache = {}  # (from, to) -> rate
        self._load_disk_cache()

    def _load_disk_cache(self):
        if not os.path.exists(self.cache_file):
            return
        try:
            df = pd.read_csv(self.cache_file)
            for _, row in df.iterrows():
                self._cache[(row["from"], row["to"])] = float(row["rate"])
        except Exception as e:
            print(f"Could not load FX cache: {e}")

    def _save_disk_cache(self):
        if not self._cache:
            return
        now = datetime.now().isoformat(timespec="seconds")
        df = pd.DataFrame(
            [{"from": f, "to": t, "rate": r, "updated": now}
             for (f, t), r in self._cache.items()]
        )
        df.to_csv(self.cache_file, index=False)

    def get_rate(self, from_ccy, to_ccy):
        """Return the multiplier to convert 1 unit of `from_ccy` into `to_ccy`."""
        if not from_ccy or from_ccy in ("Unknown", "") or from_ccy == to_ccy:
            return 1.0
        key = (from_ccy, to_ccy)
        if key in self._cache:
            return self._cache[key]
        rate = self._fetch_rate(from_ccy, to_ccy)
        self._cache[key] = rate
        self._save_disk_cache()
        return rate

    def _fetch_rate(self, from_ccy, to_ccy):
        """Fetch the latest close of `{from}{to}=X`; fall back to the inverse pair."""
        try:
            import yfinance as yf
        except ImportError:
            return 1.0

        rate = self._download_pair(yf, f"{from_ccy}{to_ccy}=X")
        if rate is not None:
            return rate
        # Inverse pair: 1 EUR-in-USD is the reciprocal of 1 USD-in-EUR.
        inv = self._download_pair(yf, f"{to_ccy}{from_ccy}=X")
        if inv is not None and inv != 0:
            return 1.0 / inv
        print(f"FX fetch failed for {from_ccy}->{to_ccy}, defaulting to 1.0")
        return 1.0

    @staticmethod
    def _download_pair(yf, symbol):
        try:
            data = yf.download(
                symbol, period="5d", interval="1d",
                auto_adjust=True, progress=False, threads=False,
            )
        except Exception as e:
            print(f"FX download error for {symbol}: {e}")
            return None
        if data is None or data.empty:
            return None
        if isinstance(data.columns, pd.MultiIndex):
            if "Close" not in data.columns.get_level_values(0):
                return None
            series = data["Close"].iloc[:, 0].dropna()
        else:
            if "Close" not in data.columns:
                return None
            series = data["Close"].dropna()
        if series.empty:
            return None
        return float(series.iloc[-1])

    def convert(self, amount, from_ccy, to_ccy):
        if pd.isna(amount):
            return amount
        return amount * self.get_rate(from_ccy, to_ccy)

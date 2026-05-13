import pandas as pd
import pytest

from portfolio.persistence import PortfolioStore


@pytest.fixture
def store(tmp_path):
    return PortfolioStore(db_path=str(tmp_path / "test.db"))


@pytest.fixture
def sample_df():
    return pd.DataFrame(
        {
            "ticker": ["ETF1", "EU1", "CASH"],
            "weight": [0.5, 0.4, 0.1],
            "amount": [5000.0, 4000.0, 1000.0],
            "shares": [10, 20, 1],
            "price": [500.0, 200.0, 1000.0],
            "market_cap": [None, 1e10, None],
        }
    )


def test_save_and_load_roundtrip(store, sample_df):
    store.save("baseline", sample_df, 10_000, "Default Strategy")
    loaded, investment, strategy, created_at = store.load("baseline")
    pd.testing.assert_frame_equal(
        loaded.reset_index(drop=True), sample_df.reset_index(drop=True), check_dtype=False
    )
    assert investment == pytest.approx(10_000)
    assert strategy == "Default Strategy"
    assert created_at  # ISO timestamp string


def test_list_snapshots_newest_first(store, sample_df):
    store.save("alpha", sample_df, 1_000, "Default Strategy")
    store.save("beta", sample_df, 2_000, "Manual Weights")
    listed = store.list_snapshots()
    assert listed["name"].tolist() == ["beta", "alpha"]
    assert set(listed.columns) == {"name", "created_at", "initial_investment", "strategy"}


def test_save_duplicate_without_overwrite_raises(store, sample_df):
    store.save("dup", sample_df, 1_000, "Default Strategy")
    with pytest.raises(Exception):
        store.save("dup", sample_df, 2_000, "Default Strategy")


def test_save_with_overwrite_updates(store, sample_df):
    store.save("dup", sample_df, 1_000, "Default Strategy")
    store.save("dup", sample_df, 9_999, "Manual Weights", overwrite=True)
    _, investment, strategy, _ = store.load("dup")
    assert investment == pytest.approx(9_999)
    assert strategy == "Manual Weights"


def test_delete_removes_snapshot(store, sample_df):
    store.save("temp", sample_df, 1_000, "Default Strategy")
    assert store.exists("temp")
    assert store.delete("temp") is True
    assert not store.exists("temp")
    assert store.delete("temp") is False


def test_load_missing_raises_key_error(store):
    with pytest.raises(KeyError):
        store.load("does-not-exist")


def test_empty_name_rejected(store, sample_df):
    with pytest.raises(ValueError):
        store.save("   ", sample_df, 1_000, "Default Strategy")

"""SQLite-backed snapshot store for saved portfolios."""
import io
import os
import sqlite3
from datetime import datetime

import pandas as pd


class PortfolioStore:
    def __init__(self, db_path="data/portfolios.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        self._init_schema()

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def _init_schema(self):
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL,
                    initial_investment REAL NOT NULL,
                    strategy TEXT NOT NULL,
                    allocation_json TEXT NOT NULL
                )
                """
            )

    def save(self, name, allocation_df, initial_investment, strategy, overwrite=False):
        """Save (or overwrite) a named portfolio snapshot."""
        if not name or not name.strip():
            raise ValueError("Snapshot name cannot be empty.")
        payload = allocation_df.to_json(orient="split")
        created_at = datetime.now().isoformat(timespec="seconds")
        with self._connect() as conn:
            if overwrite:
                conn.execute(
                    """
                    INSERT INTO snapshots(name, created_at, initial_investment, strategy, allocation_json)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(name) DO UPDATE SET
                        created_at=excluded.created_at,
                        initial_investment=excluded.initial_investment,
                        strategy=excluded.strategy,
                        allocation_json=excluded.allocation_json
                    """,
                    (name.strip(), created_at, float(initial_investment), strategy, payload),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO snapshots(name, created_at, initial_investment, strategy, allocation_json)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (name.strip(), created_at, float(initial_investment), strategy, payload),
                )

    def list_snapshots(self):
        """Return a DataFrame summarising stored snapshots (newest first)."""
        with self._connect() as conn:
            return pd.read_sql_query(
                "SELECT name, created_at, initial_investment, strategy "
                "FROM snapshots ORDER BY id DESC",
                conn,
            )

    def load(self, name):
        """Return (allocation_df, initial_investment, strategy, created_at) for the given snapshot."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT allocation_json, initial_investment, strategy, created_at "
                "FROM snapshots WHERE name = ?",
                (name,),
            ).fetchone()
        if row is None:
            raise KeyError(f"No snapshot named {name!r}")
        allocation_json, initial_investment, strategy, created_at = row
        allocation_df = pd.read_json(io.StringIO(allocation_json), orient="split")
        return allocation_df, float(initial_investment), strategy, created_at

    def delete(self, name):
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM snapshots WHERE name = ?", (name,))
        return cur.rowcount > 0

    def exists(self, name):
        with self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM snapshots WHERE name = ?", (name,)
            ).fetchone()
        return row is not None

"""
Simple DuckDB database helper for persistence.
"""
import duckdb
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Database path - uses Railway volume if available
DATA_DIR = os.getenv("DATA_DIR", "/app/data")
DB_PATH = os.path.join(DATA_DIR, "wfa.duckdb")


def get_connection():
    """Get DuckDB connection, creating tables if needed."""
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = duckdb.connect(DB_PATH)
    
    # Create tables if they don't exist
    conn.execute("""
        CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            symbol VARCHAR,
            weight DOUBLE,
            model_version VARCHAR
        )
    """)
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            symbol VARCHAR,
            action VARCHAR,
            amount DOUBLE,
            status VARCHAR
        )
    """)
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS model_state (
            key VARCHAR PRIMARY KEY,
            value VARCHAR,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    return conn


def save_signals(signals: dict, model_version: str = "v1"):
    """Save generated signals to database."""
    conn = get_connection()
    timestamp = datetime.utcnow()
    
    for symbol, weight in signals.items():
        conn.execute(
            "INSERT INTO signals (timestamp, symbol, weight, model_version) VALUES (?, ?, ?, ?)",
            [timestamp, symbol, weight, model_version]
        )
    
    conn.close()
    logger.info(f"Saved {len(signals)} signals to database")


def save_trades(trades: list):
    """Save executed trades to database."""
    conn = get_connection()
    timestamp = datetime.utcnow()
    
    for trade in trades:
        conn.execute(
            "INSERT INTO trades (timestamp, symbol, action, amount, status) VALUES (?, ?, ?, ?, ?)",
            [timestamp, trade["symbol"], trade["action"], trade["amount"], "executed"]
        )
    
    conn.close()
    logger.info(f"Saved {len(trades)} trades to database")


def get_recent_signals(limit: int = 10):
    """Get recent signals from database."""
    conn = get_connection()
    result = conn.execute(
        "SELECT * FROM signals ORDER BY timestamp DESC LIMIT ?",
        [limit]
    ).fetchall()
    conn.close()
    return result


def get_recent_trades(limit: int = 10):
    """Get recent trades from database."""
    conn = get_connection()
    result = conn.execute(
        "SELECT * FROM trades ORDER BY timestamp DESC LIMIT ?",
        [limit]
    ).fetchall()
    conn.close()
    return result

"""
YOUR MODEL GOES HERE

This is a placeholder - replace with your WFA strategy logic.
"""
import pandas as pd
from typing import Dict


def generate_signals(prices: pd.DataFrame) -> Dict[str, float]:
    """
    Generate portfolio signals from your Walk-Forward Analysis model.
    
    Args:
        prices: DataFrame with columns ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
                indexed by ticker symbol
        
    Returns:
        dict: {"TICKER": weight, ...} where weights should sum to <= 1.0
              (remainder is cash)
    
    Example:
        return {
            "SPY": 0.40,  # 40% S&P 500
            "QQQ": 0.30,  # 30% Nasdaq
            "GLD": 0.20,  # 20% Gold
            # 10% cash (implicit)
        }
    """
    # ===========================================
    # REPLACE THIS WITH YOUR STRATEGY LOGIC
    # ===========================================
    
    # Example: Equal weight top 3 ETFs
    signals = {
        "SPY": 0.33,
        "QQQ": 0.33,
        "GLD": 0.34,
    }
    
    return signals


def get_model_metadata() -> dict:
    """
    Return metadata about your model for logging/display.
    """
    return {
        "name": "My WFA Model",
        "version": "1.0.0",
        "description": "Walk-Forward Analysis strategy",
        "author": "Your Name",
    }

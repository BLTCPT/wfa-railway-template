"""
Tiingo price data client for market data.
"""
import os
import requests
import pandas as pd
import logging
from datetime import datetime, timedelta
from typing import List, Optional

logger = logging.getLogger(__name__)


class TiingoClient:
    """Client for Tiingo market data API."""
    
    BASE_URL = "https://api.tiingo.com"
    
    def __init__(self):
        self.api_token = os.getenv("TIINGO_API_TOKEN")
        if not self.api_token:
            logger.warning("TIINGO_API_TOKEN not configured")
    
    def _headers(self) -> dict:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Token {self.api_token}"
        }
    
    def is_connected(self) -> bool:
        """Check if Tiingo is properly configured and accessible."""
        if not self.api_token:
            return False
        
        try:
            response = requests.get(
                f"{self.BASE_URL}/api/test",
                headers=self._headers(),
                timeout=10
            )
            return response.status_code == 200
        except Exception:
            return False
    
    def get_prices(
        self,
        tickers: List[str],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        frequency: str = "daily"
    ) -> pd.DataFrame:
        """
        Get historical price data for multiple tickers.
        
        Args:
            tickers: List of ticker symbols
            start_date: Start date (YYYY-MM-DD), defaults to 1 year ago
            end_date: End date (YYYY-MM-DD), defaults to today
            frequency: "daily", "weekly", or "monthly"
            
        Returns:
            DataFrame with columns: date, ticker, open, high, low, close, volume, adjClose
        """
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
        if not start_date:
            start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
        
        all_data = []
        
        for ticker in tickers:
            try:
                response = requests.get(
                    f"{self.BASE_URL}/tiingo/daily/{ticker}/prices",
                    headers=self._headers(),
                    params={
                        "startDate": start_date,
                        "endDate": end_date,
                        "resampleFreq": frequency
                    },
                    timeout=30
                )
                response.raise_for_status()
                
                data = response.json()
                for row in data:
                    row["ticker"] = ticker
                    all_data.append(row)
                    
            except Exception as e:
                logger.error(f"Failed to get prices for {ticker}: {e}")
        
        if not all_data:
            return pd.DataFrame()
        
        df = pd.DataFrame(all_data)
        df["date"] = pd.to_datetime(df["date"]).dt.date
        return df
    
    def get_latest_prices(self, tickers: List[str]) -> dict:
        """
        Get latest prices for multiple tickers.
        
        Returns:
            dict: {"TICKER": {"price": 123.45, "volume": 1000000}, ...}
        """
        if not tickers:
            return {}
        
        ticker_str = ",".join(tickers)
        
        try:
            response = requests.get(
                f"{self.BASE_URL}/iex",
                headers=self._headers(),
                params={"tickers": ticker_str},
                timeout=10
            )
            response.raise_for_status()
            
            result = {}
            for item in response.json():
                ticker = item.get("ticker")
                result[ticker] = {
                    "price": item.get("last") or item.get("tngoLast"),
                    "volume": item.get("volume"),
                    "timestamp": item.get("timestamp")
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get latest prices: {e}")
            return {}
    
    def get_adjusted_close(
        self,
        tickers: List[str],
        lookback_days: int = 252
    ) -> pd.DataFrame:
        """
        Get adjusted close prices pivoted by ticker.
        
        Returns:
            DataFrame with date as index and tickers as columns.
        """
        start_date = (datetime.now() - timedelta(days=lookback_days + 30)).strftime("%Y-%m-%d")
        
        df = self.get_prices(tickers, start_date=start_date)
        
        if df.empty:
            return pd.DataFrame()
        
        # Pivot to get tickers as columns
        pivot = df.pivot_table(
            index="date",
            columns="ticker",
            values="adjClose",
            aggfunc="last"
        )
        
        return pivot.tail(lookback_days)

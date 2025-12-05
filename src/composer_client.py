"""
Composer API client for trade execution.
"""
import os
import requests
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class ComposerClient:
    """Client for Composer.trade API."""
    
    BASE_URL = "https://api.composer.trade/api/v0.1"
    
    def __init__(self):
        self.api_key = os.getenv("COMPOSER_API_KEY")
        self.api_secret = os.getenv("COMPOSER_API_SECRET")
        self.account_uuid = os.getenv("COMPOSER_ACCOUNT_UUID")
        
        if not self.api_key or not self.api_secret:
            logger.warning("Composer credentials not configured")
    
    def _headers(self) -> dict:
        """Get authentication headers."""
        return {
            "x-api-key-id": self.api_key,
            "Authorization": f"Bearer {self.api_secret}",
            "x-origin": "public-api",
            "Content-Type": "application/json"
        }
    
    def is_connected(self) -> bool:
        """Check if Composer is properly configured and accessible."""
        if not self.api_key or not self.api_secret:
            return False
        
        try:
            response = requests.get(
                f"{self.BASE_URL}/accounts/list",
                headers=self._headers(),
                timeout=10
            )
            return response.status_code == 200
        except Exception:
            return False
    
    def list_accounts(self) -> List[dict]:
        """List available Composer accounts."""
        response = requests.get(
            f"{self.BASE_URL}/accounts/list",
            headers=self._headers(),
            timeout=10
        )
        response.raise_for_status()
        return response.json().get("accounts", [])
    
    def get_holdings(self, account_uuid: Optional[str] = None) -> dict:
        """Get current portfolio holdings."""
        account = account_uuid or self.account_uuid
        
        if not account:
            # Use first available account
            accounts = self.list_accounts()
            if accounts:
                account = accounts[0].get("uuid")
        
        if not account:
            raise ValueError("No account available")
        
        response = requests.get(
            f"{self.BASE_URL}/portfolio/accounts/{account}/holding-stats",
            headers=self._headers(),
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    
    def calculate_trades(self, holdings: dict, target_signals: Dict[str, float]) -> List[dict]:
        """
        Calculate required trades to reach target allocation.
        
        Args:
            holdings: Current portfolio holdings
            target_signals: {"TICKER": weight, ...}
            
        Returns:
            List of trade dicts: [{"symbol": "SPY", "action": "buy", "amount": 1000}, ...]
        """
        total_value = holdings.get("total_value", 0)
        current_positions = {
            p["symbol"]: p["value"] 
            for p in holdings.get("positions", [])
        }
        
        trades = []
        
        for symbol, target_weight in target_signals.items():
            target_value = total_value * target_weight
            current_value = current_positions.get(symbol, 0)
            diff = target_value - current_value
            
            if abs(diff) > 100:  # Minimum trade size
                trades.append({
                    "symbol": symbol,
                    "action": "buy" if diff > 0 else "sell",
                    "amount": abs(diff)
                })
        
        return trades
    
    def execute_trades(self, trades: List[dict]) -> dict:
        """
        Execute trades via Composer API.
        
        Note: This is a simplified example. Real implementation
        would use Composer's symphony/allocation endpoints.
        """
        logger.info(f"Executing {len(trades)} trades")
        
        # In production, you would:
        # 1. Create/update a symphony with target allocations
        # 2. Or use the trading API to place orders
        
        return {
            "status": "submitted",
            "trades_count": len(trades),
            "trades": trades
        }

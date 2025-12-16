"""
Schwab API client for trade execution.

This module provides a wrapper around the schwab-py library for easy integration
with your WFA trading system. It handles OAuth2 authentication, position management,
and order execution.

Documentation: https://schwab-py.readthedocs.io/
"""
import os
import logging
from typing import Dict, List, Optional
from decimal import Decimal

logger = logging.getLogger(__name__)

try:
    from schwab import auth
    from schwab.client import Client
    from schwab.orders.equities import equity_buy_market, equity_sell_market
    SCHWAB_AVAILABLE = True
except ImportError:
    SCHWAB_AVAILABLE = False
    logger.warning("schwab-py not installed. Run: pip install schwab-py")


class SchwabClient:
    """Client for Charles Schwab API."""
    
    def __init__(self):
        """
        Initialize Schwab client with OAuth2 authentication.
        
        Environment variables required:
        - SCHWAB_API_KEY: Your API key from developer.schwab.com
        - SCHWAB_API_SECRET: Your API secret
        - SCHWAB_REDIRECT_URI: OAuth redirect URI (default: https://localhost:8182)
        - SCHWAB_ACCOUNT_HASH: (Optional) Target specific account
        """
        if not SCHWAB_AVAILABLE:
            raise ImportError("schwab-py library not installed")
        
        self.api_key = os.getenv("SCHWAB_API_KEY")
        self.api_secret = os.getenv("SCHWAB_API_SECRET")
        self.redirect_uri = os.getenv("SCHWAB_REDIRECT_URI", "https://localhost:8182")
        self.account_hash = os.getenv("SCHWAB_ACCOUNT_HASH")
        
        if not self.api_key or not self.api_secret:
            logger.warning("Schwab credentials not configured")
            self.client = None
            return
        
        # Token storage path (use Railway volume for persistence)
        token_path = os.getenv("SCHWAB_TOKEN_PATH", "/app/data/schwab_tokens.json")
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(token_path), exist_ok=True)
        
        try:
            # Create authenticated client
            self.client = auth.easy_client(
                api_key=self.api_key,
                app_secret=self.api_secret,
                callback_url=self.redirect_uri,
                token_path=token_path
            )
            logger.info("Schwab client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Schwab client: {e}")
            self.client = None
    
    def is_connected(self) -> bool:
        """Check if Schwab client is properly configured and authenticated."""
        if not self.client:
            return False
        
        try:
            # Test connection by getting account numbers
            response = self.client.get_account_numbers()
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Schwab connection test failed: {e}")
            return False
    
    def list_accounts(self) -> List[dict]:
        """
        List all linked Schwab accounts.
        
        Returns:
            List of account dictionaries with accountNumber and hashValue
        """
        if not self.client:
            raise ValueError("Schwab client not initialized")
        
        try:
            response = self.client.get_account_numbers()
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to list accounts: {e}")
            return []
    
    def get_account_hash(self) -> str:
        """
        Get account hash for API calls.
        
        Returns configured account hash or first available account.
        """
        if self.account_hash:
            return self.account_hash
        
        accounts = self.list_accounts()
        if not accounts:
            raise ValueError("No Schwab accounts available")
        
        return accounts[0]['hashValue']
    
    def get_positions(self, account_hash: Optional[str] = None) -> Dict[str, dict]:
        """
        Get current portfolio positions.
        
        Args:
            account_hash: Account hash (uses default if not provided)
            
        Returns:
            dict: {"TICKER": {"quantity": 100, "value": 50000, "avgPrice": 500}, ...}
        """
        if not self.client:
            raise ValueError("Schwab client not initialized")
        
        account = account_hash or self.get_account_hash()
        
        try:
            response = self.client.get_account(
                account,
                fields=Client.Account.Fields.POSITIONS
            )
            response.raise_for_status()
            
            data = response.json()
            positions = {}
            
            # Parse positions
            for position in data.get('securitiesAccount', {}).get('positions', []):
                symbol = position['instrument']['symbol']
                quantity = position.get('longQuantity', 0) - position.get('shortQuantity', 0)
                market_value = position.get('marketValue', 0)
                avg_price = position.get('averagePrice', 0)
                
                positions[symbol] = {
                    'quantity': quantity,
                    'value': market_value,
                    'avgPrice': avg_price
                }
            
            return positions
            
        except Exception as e:
            logger.error(f"Failed to get positions: {e}")
            return {}
    
    def get_account_value(self, account_hash: Optional[str] = None) -> float:
        """
        Get total account value.
        
        Args:
            account_hash: Account hash (uses default if not provided)
            
        Returns:
            Total account value in dollars
        """
        if not self.client:
            raise ValueError("Schwab client not initialized")
        
        account = account_hash or self.get_account_hash()
        
        try:
            response = self.client.get_account(account)
            response.raise_for_status()
            
            data = response.json()
            return data['securitiesAccount']['currentBalances']['liquidationValue']
            
        except Exception as e:
            logger.error(f"Failed to get account value: {e}")
            return 0.0
    
    def get_quote(self, symbol: str) -> dict:
        """
        Get real-time quote for a symbol.
        
        Args:
            symbol: Ticker symbol (e.g., "AAPL")
            
        Returns:
            dict with price, volume, etc.
        """
        if not self.client:
            raise ValueError("Schwab client not initialized")
        
        try:
            response = self.client.get_quote(symbol)
            response.raise_for_status()
            
            data = response.json()
            quote = data.get(symbol, {}).get('quote', {})
            
            return {
                'symbol': symbol,
                'price': quote.get('lastPrice'),
                'bid': quote.get('bidPrice'),
                'ask': quote.get('askPrice'),
                'volume': quote.get('totalVolume'),
                'change': quote.get('netChange'),
                'changePercent': quote.get('netPercentChange')
            }
            
        except Exception as e:
            logger.error(f"Failed to get quote for {symbol}: {e}")
            return {}
    
    def calculate_trades(
        self,
        current_positions: Dict[str, dict],
        target_signals: Dict[str, float],
        total_value: Optional[float] = None
    ) -> List[dict]:
        """
        Calculate required trades to reach target allocation.
        
        Args:
            current_positions: Current positions from get_positions()
            target_signals: Target weights {"TICKER": weight, ...}
            total_value: Total account value (fetched if not provided)
            
        Returns:
            List of trades: [{"symbol": "SPY", "action": "buy", "shares": 10}, ...]
        """
        if total_value is None:
            total_value = self.get_account_value()
        
        trades = []
        
        # Calculate trades for each target position
        for symbol, target_weight in target_signals.items():
            target_value = total_value * target_weight
            current_value = current_positions.get(symbol, {}).get('value', 0)
            diff = target_value - current_value
            
            if abs(diff) < 100:  # Minimum trade size $100
                continue
            
            # Get current price for share calculation
            quote = self.get_quote(symbol)
            price = quote.get('price')
            
            if not price:
                logger.warning(f"Could not get price for {symbol}, skipping trade")
                continue
            
            shares = int(abs(diff) / price)
            
            if shares > 0:
                trades.append({
                    "symbol": symbol,
                    "action": "buy" if diff > 0 else "sell",
                    "shares": shares,
                    "estimatedValue": shares * price
                })
        
        # Sell positions not in target
        for symbol, position in current_positions.items():
            if symbol not in target_signals and position['value'] > 100:
                trades.append({
                    "symbol": symbol,
                    "action": "sell",
                    "shares": int(position['quantity']),
                    "estimatedValue": position['value']
                })
        
        return trades
    
    def place_order(
        self,
        symbol: str,
        action: str,
        shares: int,
        order_type: str = "market",
        account_hash: Optional[str] = None
    ) -> dict:
        """
        Place an order.
        
        Args:
            symbol: Ticker symbol
            action: "buy" or "sell"
            shares: Number of shares
            order_type: "market" or "limit" (market supported for now)
            account_hash: Account hash (uses default if not provided)
            
        Returns:
            dict with order status and ID
        """
        if not self.client:
            raise ValueError("Schwab client not initialized")
        
        account = account_hash or self.get_account_hash()
        
        try:
            # Build order
            if action.lower() == "buy":
                order = equity_buy_market(symbol, shares)
            elif action.lower() == "sell":
                order = equity_sell_market(symbol, shares)
            else:
                raise ValueError(f"Invalid action: {action}")
            
            # Place order
            response = self.client.place_order(account, order)
            
            if response.status_code == 201:
                order_id = response.headers.get('Location', '').split('/')[-1]
                logger.info(f"Order placed: {action} {shares} {symbol}, ID: {order_id}")
                
                return {
                    'status': 'success',
                    'orderId': order_id,
                    'symbol': symbol,
                    'action': action,
                    'shares': shares
                }
            else:
                logger.error(f"Order failed: {response.status_code} - {response.text}")
                return {
                    'status': 'failed',
                    'error': response.text
                }
                
        except Exception as e:
            logger.error(f"Failed to place order: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def execute_trades(
        self,
        trades: List[dict],
        dry_run: bool = True,
        account_hash: Optional[str] = None
    ) -> dict:
        """
        Execute a list of trades.
        
        Args:
            trades: List of trade dicts from calculate_trades()
            dry_run: If True, log trades without executing
            account_hash: Account hash (uses default if not provided)
            
        Returns:
            dict with execution summary
        """
        logger.info(f"Executing {len(trades)} trades (dry_run={dry_run})")
        
        results = []
        
        for trade in trades:
            symbol = trade['symbol']
            action = trade['action']
            shares = trade['shares']
            
            if dry_run:
                logger.info(f"[DRY RUN] {action.upper()} {shares} shares of {symbol}")
                results.append({
                    'symbol': symbol,
                    'action': action,
                    'shares': shares,
                    'status': 'dry_run'
                })
            else:
                result = self.place_order(symbol, action, shares, account_hash=account_hash)
                results.append(result)
        
        successful = sum(1 for r in results if r.get('status') in ['success', 'dry_run'])
        
        return {
            'status': 'completed',
            'total_trades': len(trades),
            'successful': successful,
            'failed': len(trades) - successful,
            'dry_run': dry_run,
            'results': results
        }

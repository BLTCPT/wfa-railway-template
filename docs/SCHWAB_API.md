# Schwab API Integration Guide

This guide explains how to integrate Charles Schwab's trading API with your WFA (Walk-Forward Analysis) trading system deployed on Railway.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Authentication Setup](#authentication-setup)
- [API Capabilities](#api-capabilities)
- [Integration Options](#integration-options)
- [Python Implementation](#python-implementation)
- [Environment Configuration](#environment-configuration)
- [Trading Workflow](#trading-workflow)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

## Overview

The Charles Schwab API allows programmatic access to:
- **Account Information** - Balances, positions, and portfolio details
- **Market Data** - Real-time quotes, historical prices, and options chains
- **Trading** - Place, modify, and cancel orders for stocks and options
- **Order Management** - Track order status and execution history

**Important Notes:**
- Schwab API uses OAuth2 authentication
- No paper trading environment is available
- API access requires a Schwab brokerage account
- Community wrappers (like `schwab-py`) simplify integration

## Prerequisites

Before integrating Schwab API, you need:

1. **Charles Schwab Brokerage Account**
   - Individual, IRA, or other eligible account types
   - Account must be funded and approved for trading

2. **Developer Portal Registration**
   - Register at [Charles Schwab Developer Portal](https://developer.schwab.com)
   - Create an application to obtain credentials
   - Complete the onboarding process

3. **API Credentials**
   - API Key (Client ID)
   - API Secret (Client Secret)
   - Redirect URI (for OAuth2 callback)

## Authentication Setup

### Step 1: Register Your Application

1. Visit [developer.schwab.com](https://developer.schwab.com/products)
2. Sign in with your Schwab account
3. Create a new application
4. Set your redirect URI (e.g., `https://localhost:8182` for local development)
5. Save your **API Key** and **API Secret**

### Step 2: OAuth2 Flow

Schwab uses OAuth2 for authentication:

```
1. User Authorization → 2. Authorization Code → 3. Access Token → 4. Refresh Token
```

The `schwab-py` library handles this automatically via the `easy_client()` method.

### Step 3: Token Management

- **Access Token**: Valid for 30 minutes
- **Refresh Token**: Valid for 7 days
- Tokens are automatically refreshed by the client library
- Store tokens securely (never commit to git)

## API Capabilities

### Account Endpoints

- `get_account()` - Get account details and balances
- `get_account_numbers()` - List all linked account numbers
- `get_account_positions()` - Get current positions

### Market Data Endpoints

- `get_quote()` - Real-time quote for a symbol
- `get_quotes()` - Multiple quotes in one request
- `get_price_history()` - Historical OHLCV data
- `get_option_chain()` - Options data for underlying symbol

### Trading Endpoints

- `place_order()` - Submit a new order
- `replace_order()` - Modify an existing order
- `cancel_order()` - Cancel a pending order
- `get_order()` - Get order details and status
- `get_orders_for_account()` - List all orders

### Supported Order Types

- Market orders
- Limit orders
- Stop orders
- Stop-limit orders
- Trailing stop orders

## Integration Options

### Option 1: Direct Schwab Integration (Recommended for Schwab-only users)

Replace Composer API with Schwab API directly:

**Pros:**
- Direct brokerage integration
- Lower latency
- Full control over execution

**Cons:**
- More complex OAuth2 setup
- No paper trading environment
- Must handle order management directly

### Option 2: Dual Integration (Composer + Schwab)

Use Composer for signals and Schwab for execution:

**Pros:**
- Leverage Composer's backtesting
- Execute on Schwab accounts
- Keep existing workflow

**Cons:**
- Requires maintaining two integrations
- More complex architecture

### Option 3: Copy Trading (Composer → Schwab)

Mirror Composer trades to Schwab automatically:

**Pros:**
- Keep using Composer platform
- Automated synchronization
- Best of both platforms

**Cons:**
- Requires monitoring both accounts
- Potential for sync issues

## Python Implementation

### Install Dependencies

```bash
pip install schwab-py
```

Add to `requirements.txt`:
```
schwab-py>=1.5.0
```

### Basic Client Setup

```python
from schwab import auth, client
import os

# OAuth2 authentication
api_key = os.getenv("SCHWAB_API_KEY")
app_secret = os.getenv("SCHWAB_API_SECRET")
callback_url = os.getenv("SCHWAB_REDIRECT_URI", "https://localhost:8182")
token_path = "/app/data/schwab_tokens.json"  # Railway volume

# Create authenticated client
schwab_client = auth.easy_client(
    api_key=api_key,
    app_secret=app_secret,
    callback_url=callback_url,
    token_path=token_path
)
```

### Get Account Information

```python
# Get account numbers
accounts = schwab_client.get_account_numbers()
account_hash = accounts.json()['accountHash']

# Get account details with positions
account_info = schwab_client.get_account(
    account_hash,
    fields=['positions']
)

positions = account_info.json()['securitiesAccount']['positions']
for position in positions:
    print(f"{position['instrument']['symbol']}: {position['longQuantity']} shares")
```

### Get Market Data

```python
# Get real-time quote
quote = schwab_client.get_quote('AAPL')
price = quote.json()['AAPL']['quote']['lastPrice']

# Get historical data
from schwab.client import Client

history = schwab_client.get_price_history(
    'SPY',
    period_type=Client.PriceHistory.PeriodType.YEAR,
    period=Client.PriceHistory.Period.ONE_YEAR,
    frequency_type=Client.PriceHistory.FrequencyType.DAILY,
    frequency=Client.PriceHistory.Frequency.DAILY
)

candles = history.json()['candles']
```

### Place Orders

```python
from schwab.orders.equities import equity_buy_market, equity_sell_market

# Market buy order
order = equity_buy_market('AAPL', 10)  # Buy 10 shares
response = schwab_client.place_order(account_hash, order)

if response.status_code == 201:
    print("Order placed successfully")
    order_id = response.headers['Location'].split('/')[-1]
```

### Complete Integration Example

See `src/schwab_client.py` for a full implementation that integrates with your WFA model.

## Environment Configuration

Add to `.env`:

```bash
# Schwab API Credentials
SCHWAB_API_KEY=your_api_key_here
SCHWAB_API_SECRET=your_api_secret_here
SCHWAB_REDIRECT_URI=https://localhost:8182
SCHWAB_ACCOUNT_HASH=your_account_hash

# Trading Configuration
SCHWAB_DRY_RUN=true  # Set to false for live trading
```

Add to Railway variables:

```bash
railway variables --set "SCHWAB_API_KEY=your_key"
railway variables --set "SCHWAB_API_SECRET=your_secret"
railway variables --set "SCHWAB_REDIRECT_URI=https://your-app.up.railway.app/oauth/callback"
railway variables --set "SCHWAB_ACCOUNT_HASH=your_account_hash"
```

## Trading Workflow

### 1. Generate Signals (Your WFA Model)

```python
from your_model import generate_signals

signals = generate_signals(price_data)
# Returns: {"SPY": 0.4, "QQQ": 0.3, "GLD": 0.3}
```

### 2. Get Current Positions

```python
from schwab_client import SchwabClient

client = SchwabClient()
positions = client.get_positions()
# Returns: {"SPY": {"quantity": 100, "value": 50000}, ...}
```

### 3. Calculate Required Trades

```python
total_value = sum(p['value'] for p in positions.values())

trades = []
for symbol, target_weight in signals.items():
    target_value = total_value * target_weight
    current_value = positions.get(symbol, {}).get('value', 0)
    diff = target_value - current_value
    
    if abs(diff) > 100:  # Minimum trade size
        trades.append({
            "symbol": symbol,
            "action": "buy" if diff > 0 else "sell",
            "amount": abs(diff)
        })
```

### 4. Execute Trades

```python
for trade in trades:
    if trade['action'] == 'buy':
        client.buy(trade['symbol'], trade['amount'])
    else:
        client.sell(trade['symbol'], trade['amount'])
```

### 5. Schedule Daily Execution

```python
# In scheduler.py
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

scheduler = BackgroundScheduler()

# Schwab trading hours: 9:30 AM - 4:00 PM ET
# Schedule rebalance at 3:30 PM ET
scheduler.add_job(
    run_trading_job,
    trigger=CronTrigger(
        hour=15,
        minute=30,
        day_of_week='mon-fri',
        timezone='America/New_York'
    )
)
```

## Best Practices

### Security

- **Never commit credentials** - Use environment variables
- **Store tokens securely** - Use Railway volumes (`/app/data`)
- **Rotate credentials** - Periodically update API keys
- **Use HTTPS** - Always use secure redirect URIs in production

### Trading

- **Start with dry run** - Test thoroughly before live trading
- **Use limit orders** - Avoid market orders for large positions
- **Monitor execution** - Check order status after placement
- **Handle errors** - Implement retry logic and notifications
- **Respect rate limits** - Schwab API has rate limiting

### Risk Management

- **Set position limits** - Prevent overconcentration
- **Use stop losses** - Protect against large losses
- **Monitor daily** - Review trades and positions
- **Keep cash buffer** - Don't be 100% invested
- **Test with small size** - Start with small positions

### Operational

- **Log everything** - Track all API calls and responses
- **Send notifications** - Discord/Slack for trade alerts
- **Database persistence** - Store signals and trades
- **Graceful degradation** - Handle API outages
- **Version control** - Track model changes

## Troubleshooting

### OAuth2 Authentication Issues

**Problem:** "Invalid redirect URI"

**Solution:**
- Ensure redirect URI in code matches Developer Portal exactly
- Use `https://localhost:8182` for local development
- Use your Railway domain for production

**Problem:** "Token expired"

**Solution:**
- Tokens are automatically refreshed by `schwab-py`
- Check token file permissions (should be readable/writable)
- Delete token file and re-authenticate if corrupted

### Trading Errors

**Problem:** "Insufficient funds"

**Solution:**
- Check account balance before placing orders
- Use `get_account()` to verify available cash
- Reduce position sizes or target weights

**Problem:** "Order rejected - Outside market hours"

**Solution:**
- Schwab trading hours: 9:30 AM - 4:00 PM ET
- Extended hours may be available (check account settings)
- Schedule jobs during regular trading hours

**Problem:** "Symbol not found"

**Solution:**
- Verify ticker symbol is correct
- Some symbols require different format (e.g., options)
- Check if security is supported for trading

### API Rate Limits

**Problem:** "Rate limit exceeded"

**Solution:**
- Implement exponential backoff
- Batch requests where possible (e.g., `get_quotes()`)
- Cache data when appropriate
- Monitor API usage

### Data Issues

**Problem:** "Historical data incomplete"

**Solution:**
- Schwab API doesn't support historical options pricing
- Use alternative data source (Tiingo, Alpha Vantage) for history
- Schwab API is best for real-time data and execution

## Additional Resources

- [Schwab Developer Portal](https://developer.schwab.com/products)
- [schwab-py Documentation](https://schwab-py.readthedocs.io/)
- [schwab-py GitHub](https://github.com/alexgolec/schwab-py)
- [OAuth2 Flow Guide](https://schwab-py.readthedocs.io/en/latest/auth.html)
- [Order Builder Examples](https://schwab-py.readthedocs.io/en/latest/order-templates.html)

## Support

For Schwab API issues:
- Check [schwab-py Discord](https://discord.gg/BEr6y6Xqyv)
- Open issue on [GitHub](https://github.com/alexgolec/schwab-py/issues)
- Contact Schwab Developer Support

For WFA template issues:
- Open issue on this repository
- Check existing documentation in `README.md`

---

**Disclaimer:** This documentation is for educational purposes. Always test thoroughly before trading with real money. The authors are not responsible for any trading losses.

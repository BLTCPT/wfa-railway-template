# WFA Railway Deployment Template

A complete template for deploying Walk-Forward Analysis (WFA) trading systems to Railway with Composer integration.

## What This Template Provides

This template gives you everything needed to deploy your own trading model:

- 🚀 **Railway deployment** - One-click cloud deployment
- 📊 **FastAPI backend** - REST API for your model
- 🔗 **Composer integration** - Connect to your brokerage account
- 💾 **DuckDB persistence** - Your data survives redeployments
- 📱 **Discord alerts** - Get notified on trades
- ⏰ **Scheduled execution** - Daily automated rebalancing

## Prerequisites

Before starting, you'll need:

1. **Railway account** - [Sign up free](https://railway.app)
2. **Composer account** - [Get API keys](https://app.composer.trade/settings/api)
3. **Discord server** - For trade notifications (optional)
4. **Your WFA model** - The strategy logic you want to deploy

## Quick Start

### 1. Use This Template

Click "Use this template" on GitHub, or:

```bash
gh repo create my-trading-bot --template BLTCPT/wfa-railway-template --private
cd my-trading-bot
```

### 2. Add Your Model

Replace `src/your_model.py` with your strategy logic:

```python
# src/your_model.py
def generate_signals(prices: pd.DataFrame) -> dict:
    """
    Your WFA model goes here.
    
    Args:
        prices: DataFrame with OHLCV data
        
    Returns:
        dict: {"symbol": weight, ...} where weights sum to 1.0
    """
    # YOUR STRATEGY LOGIC HERE
    return {"SPY": 0.5, "QQQ": 0.3, "GLD": 0.2}
```

### 3. Configure Environment

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

Required variables:
- `COMPOSER_API_KEY` - From Composer settings
- `COMPOSER_API_SECRET` - From Composer settings
- `DISCORD_WEBHOOK_URL` - From Discord channel settings (optional)

### 4. Deploy to Railway

```bash
# Install Railway CLI
curl -fsSL https://railway.com/install.sh | sh

# Login
railway login

# Create project and deploy
railway init
railway up
```

### 5. Add Persistent Volume

In Railway dashboard:
1. Go to your service
2. Click "Volumes"
3. Add volume mounted at `/app/data`

This ensures your database survives redeployments.

### 6. Set Environment Variables

```bash
railway variables --set "COMPOSER_API_KEY=your_key"
railway variables --set "COMPOSER_API_SECRET=your_secret"
railway variables --set "DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/..."
```

### 7. Get Your URL

```bash
railway domain
```

Your API is now live! Test it:
```bash
curl https://your-app.up.railway.app/health
```

## Project Structure

```
├── src/
│   ├── api.py              # FastAPI endpoints
│   ├── your_model.py       # YOUR STRATEGY (replace this)
│   ├── composer_client.py  # Composer API wrapper
│   └── db.py               # DuckDB persistence
├── scripts/
│   └── scheduler.py        # Daily rebalance scheduler
├── Dockerfile              # Container configuration
├── railway.toml            # Railway deployment config
├── requirements.txt        # Python dependencies
└── .env.example            # Environment template
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/api/v1/signals` | GET | Get current model signals |
| `/api/v1/rebalance` | POST | Execute rebalance (dry_run available) |
| `/api/v1/history` | GET | Get trade history |

## Composer Integration

### Trading Window

Composer executes stock trades from **3:45 PM to 4:00 PM ET**.

Schedule your rebalance for **3:40 PM ET** to allow time for:
1. Signal generation
2. API submission
3. Order queuing

### Account Types

Composer supports multiple account types:
- Individual brokerage
- Traditional IRA
- Roth IRA
- Tax-advantaged accounts

Configure `COMPOSER_ACCOUNT_UUID` to target a specific account.

## Scheduling

### Railway Cron (Simple)

Add to `railway.toml`:
```toml
[deploy]
cronSchedule = "40 19 * * 1-5"  # 3:40 PM ET (during EST)
```

Note: Adjust for DST (19:40 UTC = 3:40 PM EST, 18:40 UTC = 3:40 PM EDT)

### Built-in Scheduler (Flexible)

The included scheduler handles DST automatically:
```python
# scripts/scheduler.py runs at startup and schedules 3:40 PM ET daily
```

## Database Persistence

Uses DuckDB with Railway Volumes:

- **Volume mount**: `/app/data`
- **Database files**: `trading.duckdb`
- **Cost**: ~$0.15/GB/month

Tables:
- `signals` - Daily model outputs
- `trades` - Executed trades
- `snapshots` - Portfolio snapshots

## Discord Notifications

Get alerts for:
- ✅ Successful trades
- ⚠️ Rebalance failures
- 📊 Daily portfolio summary

Setup:
1. Create Discord webhook in channel settings
2. Set `DISCORD_WEBHOOK_URL` in Railway variables

## Cost Estimate

| Component | Monthly Cost |
|-----------|-------------|
| Railway Hobby | $5.00 |
| Volume (1GB) | $0.15 |
| **Total** | **~$5.15** |

## Dry Run Testing

Always test with dry_run first:

```bash
curl -X POST https://your-app.up.railway.app/api/v1/rebalance \
  -H "Content-Type: application/json" \
  -d '{"dry_run": true}'
```

This shows what trades WOULD execute without actually trading.

## Troubleshooting

### "Composer API returns HTML"
- Check API key/secret are correct
- Ensure you're using production URL: `api.composer.trade`

### "Database resets on redeploy"
- Add Railway Volume at `/app/data`
- Verify volume is attached in dashboard

### "Scheduler not running"
- Check Railway logs: `railway logs`
- Verify cron schedule in `railway.toml`

## Security Notes

⚠️ **Never commit credentials to git!**

- Use `.env` for local development (gitignored)
- Use Railway Variables for production
- Rotate API keys periodically

## Resources

- [Railway Docs](https://docs.railway.app)
- [Composer API Docs](https://docs.composer.trade)
- [FastAPI Docs](https://fastapi.tiangolo.com)
- [DuckDB Docs](https://duckdb.org/docs)

## License

MIT License - Use this template however you want!

## Support

Questions? Open an issue or reach out on Discord.

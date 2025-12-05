"""
Scheduler for automated signal generation and trading.
Uses APScheduler for production-grade job scheduling.
"""
import os
import logging
from datetime import datetime
import pytz

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from your_model import WFAModel
from composer_client import ComposerClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_trading_job():
    """
    Main trading job - runs during Composer trading window.
    
    Composer Trading Window: 3:45 PM - 4:00 PM ET
    Schedule this job at 3:40 PM ET to be ready.
    """
    try:
        et = pytz.timezone("America/New_York")
        now = datetime.now(et)
        logger.info(f"Running trading job at {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        
        # 1. Generate signals from your model
        model = WFAModel()
        signals = model.generate_signals()
        
        if not signals:
            logger.warning("No signals generated")
            return
        
        logger.info(f"Generated signals: {signals}")
        
        # 2. Get current holdings
        client = ComposerClient()
        if not client.is_connected():
            logger.error("Composer not connected")
            return
        
        holdings = client.get_holdings()
        
        # 3. Calculate required trades
        trades = client.calculate_trades(holdings, signals)
        
        if not trades:
            logger.info("No trades needed")
            return
        
        # 4. Execute trades (or log in dry-run mode)
        dry_run = os.getenv("DRY_RUN", "true").lower() == "true"
        
        if dry_run:
            logger.info(f"[DRY RUN] Would execute: {trades}")
        else:
            result = client.execute_trades(trades)
            logger.info(f"Execution result: {result}")
        
        # 5. Send notification (optional)
        send_notification(signals, trades, dry_run)
        
    except Exception as e:
        logger.error(f"Trading job failed: {e}", exc_info=True)


def send_notification(signals: dict, trades: list, dry_run: bool):
    """Send notification to Discord/Slack."""
    webhook_url = os.getenv("DISCORD_WEBHOOK") or os.getenv("SLACK_WEBHOOK_URL")
    
    if not webhook_url:
        return
    
    import requests
    
    message = {
        "content": None,
        "embeds": [{
            "title": "🤖 WFA Trading Signal" + (" [DRY RUN]" if dry_run else ""),
            "description": f"Generated {len(signals)} signals, {len(trades)} trades",
            "color": 0x00ff00 if not dry_run else 0xffff00,
            "fields": [
                {"name": "Signals", "value": str(signals)[:1000], "inline": False},
                {"name": "Trades", "value": str(trades)[:1000], "inline": False}
            ],
            "timestamp": datetime.utcnow().isoformat()
        }]
    }
    
    try:
        requests.post(webhook_url, json=message, timeout=10)
    except Exception as e:
        logger.error(f"Failed to send notification: {e}")


def create_scheduler():
    """
    Create scheduler with proper timezone handling.
    
    IMPORTANT: Composer trading window is 3:45 PM - 4:00 PM ET.
    We schedule at 3:40 PM ET to have time to generate signals.
    
    Daylight Saving Time (DST):
    - Use America/New_York timezone which handles DST automatically
    - Do NOT use fixed UTC offsets (they don't adjust for DST)
    """
    scheduler = BackgroundScheduler()
    
    # Trading job at 3:40 PM ET (Mon-Fri)
    # APScheduler with timezone handles DST automatically
    trading_trigger = CronTrigger(
        hour=15,  # 3 PM
        minute=40,
        day_of_week='mon-fri',
        timezone=pytz.timezone('America/New_York')
    )
    
    scheduler.add_job(
        run_trading_job,
        trigger=trading_trigger,
        id='trading_job',
        name='WFA Trading Signal Generation',
        misfire_grace_time=300  # 5 minutes grace period
    )
    
    logger.info("Scheduler configured: Trading job at 3:40 PM ET (Mon-Fri)")
    
    return scheduler


if __name__ == "__main__":
    logger.info("Starting WFA Scheduler")
    
    scheduler = create_scheduler()
    scheduler.start()
    
    # Keep the main thread alive
    try:
        import time
        while True:
            time.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        logger.info("Scheduler stopped")

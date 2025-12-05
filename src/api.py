"""
FastAPI application for WFA trading system.
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Optional
from datetime import datetime
import os
import logging

from dotenv import load_dotenv
load_dotenv()

# Import your model
from src.your_model import generate_signals, get_model_metadata
from src.composer_client import ComposerClient
from src.db import TradingDB

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="WFA Trading API",
    description="Walk-Forward Analysis trading system with Composer integration",
    version="1.0.0"
)

# Initialize clients
db = TradingDB()
composer = ComposerClient() if os.getenv("COMPOSER_API_KEY") else None


class RebalanceRequest(BaseModel):
    dry_run: bool = True


class RebalanceResponse(BaseModel):
    status: str
    signals: Dict[str, float]
    trades: list
    timestamp: str


@app.get("/health")
async def health_check():
    """Health check endpoint for Railway."""
    return {
        "status": "healthy",
        "model": get_model_metadata(),
        "composer_connected": composer is not None and composer.is_connected(),
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/api/v1/signals")
async def get_signals():
    """Get current model signals without executing."""
    try:
        signals = generate_signals(None)  # Pass your price data here
        
        # Save to database
        db.save_signals(signals)
        
        return {
            "signals": signals,
            "model": get_model_metadata(),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error generating signals: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/rebalance", response_model=RebalanceResponse)
async def execute_rebalance(request: RebalanceRequest):
    """
    Execute portfolio rebalance based on model signals.
    
    Set dry_run=true to preview trades without executing.
    """
    try:
        # Generate signals from your model
        signals = generate_signals(None)  # Pass your price data here
        
        if not composer:
            raise HTTPException(
                status_code=503, 
                detail="Composer not configured. Set COMPOSER_API_KEY and COMPOSER_API_SECRET."
            )
        
        # Get current holdings
        holdings = composer.get_holdings()
        
        # Calculate required trades
        trades = composer.calculate_trades(holdings, signals)
        
        if request.dry_run:
            return RebalanceResponse(
                status="dry_run",
                signals=signals,
                trades=trades,
                timestamp=datetime.utcnow().isoformat()
            )
        
        # Execute trades
        result = composer.execute_trades(trades)
        
        # Save to database
        db.save_trade(signals, trades, result)
        
        # Send Discord notification
        send_discord_notification(signals, trades, result)
        
        return RebalanceResponse(
            status="executed",
            signals=signals,
            trades=trades,
            timestamp=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Rebalance error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/history")
async def get_history(days: int = 30):
    """Get trade history."""
    return {"history": db.get_history(days)}


def send_discord_notification(signals: dict, trades: list, result: dict):
    """Send trade notification to Discord."""
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        return
    
    import requests
    
    message = {
        "content": f"📊 **Rebalance Executed**\n\n"
                   f"Signals: {signals}\n"
                   f"Trades: {len(trades)}\n"
                   f"Status: {result.get('status', 'unknown')}"
    }
    
    try:
        requests.post(webhook_url, json=message, timeout=5)
    except Exception as e:
        logger.warning(f"Discord notification failed: {e}")

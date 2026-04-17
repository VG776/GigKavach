"""
api/whatsapp_integration.py
────────────────────────────────────────
Integrates the backend with the WhatsApp bot service running on port 3001.

Provides endpoints for:
  1. Sending messages via the bot (disruption alerts, payout confirmations)
  2. Receiving webhook callbacks from the bot (optional)
  3. Managing worker-bot sessions
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
import httpx
import logging
from config.settings import settings

logger = logging.getLogger("gigkavach.whatsapp_integration")
router = APIRouter(tags=["WhatsApp Integration"])

# Bot service URL (running on port 3001)
BOT_SERVICE_URL = settings.BOT_API_URL or "http://localhost:3001"

# ─── Pydantic Models ────────────────────────────────────────────────

class SendMessageRequest(BaseModel):
    """Request to send a message via WhatsApp bot"""
    phone: str  # e.g., "918074725459"
    message: str
    message_type: Optional[str] = None  # e.g., "disruption_alert", "payout_sent"


class BroadcastDCIAlertRequest(BaseModel):
    """Request to broadcast DCI alert to multiple workers"""
    pincode: str
    dci_score: float
    worker_phones: List[str]
    severity: str  # "none" | "low" | "moderate" | "high" | "critical" | "catastrophic"


class PayoutConfirmationRequest(BaseModel):
    """Request to send payout confirmation via WhatsApp"""
    phone: str
    amount: float
    upi: str
    ref: str  # Razorpay reference
    language: Optional[str] = "en"


# ─── Helper: Call Bot Service ──────────────────────────────────────

async def call_bot_service(endpoint: str, data: dict):
    """
    Make HTTP call to bot service (port 3000)
    
    Args:
        endpoint: e.g., "/send-message"
        data: JSON payload
        
    Returns:
        Response from bot service or raises HTTPException
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            url = f"{BOT_SERVICE_URL}{endpoint}"
            response = await client.post(url, json=data)
            
            if response.status_code not in (200, 201):
                logger.error(
                    f"Bot service error: {response.status_code} {response.text}"
                )
                raise HTTPException(
                    status_code=503,
                    detail=f"Bot service returned {response.status_code}",
                )
            
            return response.json()
    except httpx.ConnectError:
        logger.error(f"Bot service not available at {BOT_SERVICE_URL}")
        raise HTTPException(
            status_code=503,
            detail="WhatsApp bot service is unavailable",
        )
    except Exception as e:
        logger.error(f"Bot service call failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send message: {str(e)}",
        )


# ─── Endpoints ─────────────────────────────────────────────────────

@router.post("/whatsapp/send-message")
async def send_whatsapp_message(req: SendMessageRequest):
    """
    Send a message to a worker via WhatsApp bot.
    
    Example:
    ```
    POST /api/v1/whatsapp/send-message
    {
      "phone": "918074725459",
      "message": "💸 ₹280 sent to your UPI...",
      "message_type": "payout_sent"
    }
    ```
    """
    logger.info(f"Sending WhatsApp to {req.phone}")
    
    response = await call_bot_service(
        "/send-message",
        {
            "phone": req.phone,
            "message": req.message,
            "messageType": req.message_type,
        }
    )
    
    return {
        "status": "ok",
        "message": "Message queued for sending",
        "phone": req.phone,
    }


@router.post("/whatsapp/broadcast-dci-alert")
async def broadcast_dci_alert(req: BroadcastDCIAlertRequest):
    """
    Broadcast a DCI disruption alert to multiple workers in a zone.
    
    Called by DCI poller when DCI ≥ 65 in a zone.
    
    Example:
    ```
    POST /api/v1/whatsapp/broadcast-dci-alert
    {
      "pincode": "560047",
      "dci_score": 78,
      "worker_phones": ["918074725459", "919876543210"],
      "severity": "high"
    }
    ```
    """
    logger.info(f"Broadcasting DCI alert to {len(req.worker_phones)} workers in {req.pincode}")
    
    response = await call_bot_service(
        "/broadcast-dci-alert",
        {
            "pincode": req.pincode,
            "dci_score": req.dci_score,
            "worker_phones": req.worker_phones,
            "severity": req.severity,
        }
    )
    
    return response


@router.post("/whatsapp/send-payout-confirmation")
async def send_payout_confirmation(req: PayoutConfirmationRequest):
    """
    Send payout confirmation to a worker via WhatsApp.
    
    Called by payout service after Razorpay transaction.
    
    Example:
    ```
    POST /api/v1/whatsapp/send-payout-confirmation
    {
      "phone": "918074725459",
      "amount": 280,
      "upi": "ravi@upi",
      "ref": "RZP12345",
      "language": "en"
    }
    ```
    """
    logger.info(f"Sending payout confirmation ₹{req.amount} to {req.phone}")
    
    response = await call_bot_service(
        "/send-payout-confirmation",
        {
            "phone": req.phone,
            "amount": req.amount,
            "upi": req.upi,
            "ref": req.ref,
            "language": req.language,
        }
    )
    
    return response


@router.get("/whatsapp/bot-health")
async def check_bot_health():
    """
    Check if WhatsApp bot service is running and healthy.
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{BOT_SERVICE_URL}/health")
            
            if response.status_code == 200:
                bot_status = response.json()
                return {
                    "status": "ok",
                    "bot_service": bot_status,
                }
            else:
                return {
                    "status": "error",
                    "detail": "Bot service returned error",
                }
    except httpx.ConnectError:
        raise HTTPException(
            status_code=503,
            detail=f"Bot service not available at {BOT_SERVICE_URL}",
        )

"""
api/whatsapp.py
────────────────
WhatsApp Bot Inbound Webhook
Receives messages from the Node.js bot (port 3001) and routes them 
to the onboarding state machine.
"""

import logging
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

from services.onboarding_handlers import route_message

router = APIRouter(tags=["WhatsApp Integration"])
logger = logging.getLogger("gigkavach.whatsapp")


def normalize_whatsapp_phone(phone: str) -> str:
    """Normalize phone value to digits-only E.164 style without '+' for stable identity mapping."""
    digits = "".join(ch for ch in (phone or "") if ch.isdigit())
    return digits

class WhatsAppWebhookRequest(BaseModel):
    phone: str
    body: str
    name: Optional[str] = None
    timestamp: Optional[str] = None

@router.post("/whatsapp/webhook")
async def whatsapp_inbound_webhook(
    req: WhatsAppWebhookRequest
):
    """
    Main webhook receiver for the WhatsApp bot.
    Bots on 3001 should send callbacks here.
    """
    phone = normalize_whatsapp_phone(req.phone)
    message_body = req.body
    
    logger.info(f"📩 [INBOUND] Message from {phone}: {message_body}")
    
    # 1. Process message through the onboarding/command state machine
    try:
        response_text = await route_message(phone, message_body)
        
        # Return response text to the bot so it can reply directly on the same connection.
        # This avoids failures when backend cannot call back to the bot service URL.
        return {
            "status": "ok",
            "reply": response_text or "",
            "delivered": bool(response_text),
        }
        
    except Exception as e:
        logger.error(f"❌ Error in WhatsApp webhook processing: {e}")
        return {"status": "error", "detail": str(e)}

# Keeping the existing sending bridge for backward compatibility with DCI/Settlement
def send_whatsapp_alert(worker_id: str, message_type: str, context: dict = None):
    """
    Legacy sync outbound bridge (used by some older DCI modules).
    In modern flows, call services.whatsapp_service.notify_worker directly.
    """
    if context is None: context = {}
    from services.whatsapp_service import notify_worker
    
    # Simplified mock-to-real mapping for demo
    # In production, look up phone from worker_id in DB
    success = notify_worker(
        phone_number="+918074725459", # Default demo worker
        message_key=message_type, 
        language="en", 
        **context
    )
    return {"status": "sent" if success else "failed"}

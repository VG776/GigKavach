# FastAPI WhatsApp integration for whatsapp-web.js bot
from fastapi import APIRouter, status
import logging
from datetime import datetime

# Import handlers and utilities
try:
    from services.whatsapp_service import notify_worker
except ImportError as e:
    logger_init = logging.getLogger("gigkavach.whatsapp")
    logger_init.error(f"Failed to import handlers: {e}")

logger = logging.getLogger("gigkavach.whatsapp")
router = APIRouter(tags=["WhatsApp Integration"])

def send_whatsapp_alert(worker_id: str, message_type: str, context: dict = None):
    """
    Outbound notification bridge using the unified notify_worker service.
    (Used by DCI Poller / Settlement Service)
    """
    if context is None: context = {}
    
    # In a real scenario, we fetch the worker's phone and language from DB
    # For the hackathon demo, we default to English and generic phone stubs
    success = notify_worker(
        phone_number="+919876543210", # Mock mapping
        message_key=message_type, 
        language="en", 
        **context
    )
    
    logger.info(f"📱 [OUTBOUND ALERT] {message_type} sent to {worker_id} | Success: {success}")
    return {"status": "sent" if success else "failed", "timestamp": datetime.now().isoformat()}

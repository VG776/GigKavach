# FastAPI WhatsApp webhook handler for Twilio
from fastapi import APIRouter, Request, status, Depends
from fastapi.responses import Response as FastAPIResponse
import xml.etree.ElementTree as ET
import logging
from datetime import datetime

# Attempted imports from the services module (Requirement §5)
try:
    from services.whatsapp_service import (
        handle_join, handle_status, handle_renew, handle_shift, 
        handle_lang, handle_help, handle_appeal, log_whatsapp_message,
        notify_worker
    )
except ImportError:
    # Stubs if not yet fully implemented in services to prevent app crash
    async def log_whatsapp_message(s, b): pass
    async def handle_help(s, b): return "GigKavach Help: Type JOIN, STATUS, or RENEW."
    handle_join = handle_status = handle_renew = handle_shift = handle_lang = handle_appeal = handle_help
    from services.whatsapp_service import notify_worker

logger = logging.getLogger("gigkavach.whatsapp")
router = APIRouter(tags=["WhatsApp Webhook"])

@router.post("/whatsapp/webhook", status_code=status.HTTP_200_OK)
async def whatsapp_webhook(request: Request):
    """
    Handles incoming WhatsApp messages from Twilio webhook.
    Parses sender and message body, routes to appropriate handler.
    """
    form = await request.form()
    sender = form.get("From")
    body = form.get("Body", "").strip()

    # Log every incoming message
    await log_whatsapp_message(sender, body)

    # Normalize and route message
    keyword = body.split()[0].upper() if body else ""
    handlers = {
        "JOIN": handle_join,
        "STATUS": handle_status,
        "RENEW": handle_renew,
        "SHIFT": handle_shift,
        "LANG": handle_lang,
        "HELP": handle_help,
        "APPEAL": handle_appeal,
    }
    handler = handlers.get(keyword, handle_help)

    # Call the handler and get response text
    response_text = await handler(sender, body)

    # Build TwiML XML response
    twiml = ET.Element("Response")
    message = ET.SubElement(twiml, "Message")
    message.text = response_text
    xml_str = ET.tostring(twiml, encoding="utf-8")

    return FastAPIResponse(content=xml_str, media_type="application/xml")

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

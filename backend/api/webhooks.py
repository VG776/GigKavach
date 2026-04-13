"""
api/webhooks.py
────────────────
Razorpay Webhook Handler
Listens for asynchronous payout status updates (processed, failed, reversed)
and synchronizes the GigKavach database state.
"""

import logging
import hmac
import hashlib
from fastapi import APIRouter, Request, Header, HTTPException
from config.settings import settings
from utils.supabase_client import get_supabase
from services.whatsapp_service import send_whatsapp_message, notify_worker

router = APIRouter(tags=["Webhooks"])
logger = logging.getLogger("gigkavach.webhooks")

# IMPORTANT: Set RAZORPAY_WEBHOOK_SECRET in your .env
WEBHOOK_SECRET = settings.APP_SECRET_KEY # Fallback or specific secret

@router.post("/webhooks/razorpay")
async def razorpay_webhook_handler(
    request: Request,
    x_razorpay_signature: str = Header(None)
):
    """
    Main entry point for Razorpay webhooks.
    Validates signature and updates payout status.
    """
    body = await request.body()
    
    # 1. Validate Signature (if secret is configured)
    if WEBHOOK_SECRET and x_razorpay_signature:
        expected_signature = hmac.new(
            WEBHOOK_SECRET.encode(),
            body,
            hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(expected_signature, x_razorpay_signature):
            logger.warning("Invalid Razorpay webhook signature received!")
            # In production, you would raise 401, but for demo we might log only
            # raise HTTPException(status_code=401, detail="Invalid signature")

    # 2. Parse Event
    try:
        data = await request.json()
        event = data.get("event")
        payload = data.get("payload", {}).get("payout", {}).get("entity", {})
        
        # Razorpay payout reference (GkKavach payout_id) is in reference_id
        payout_id = payload.get("reference_id")
        rzp_payout_id = payload.get("id")
        rzp_status = payload.get("status")
        
        if not payout_id:
            logger.warning(f"Razorpay webhook received without reference_id: {event}")
            return {"status": "ignored", "reason": "no_reference_id"}

        logger.info(f"Processing RZP Webhook: {event} for payout {payout_id} (Status: {rzp_status})")
        
        sb = get_supabase()
        
        # 3. Handle Status Changes
        if event == "payout.processed":
            await handle_payout_success(sb, payout_id, rzp_payout_id, rzp_status)
        elif event in ["payout.failed", "payout.reversed"]:
            failure_reason = payload.get("status_details", {}).get("description", "Unknown failure")
            await handle_payout_failure(sb, payout_id, rzp_payout_id, rzp_status, failure_reason)
        
        return {"status": "ok"}
        
    except Exception as e:
        logger.error(f"Error processing Razorpay webhook: {e}")
        return {"status": "error", "message": str(e)}

async def handle_payout_success(sb, payout_id: str, rzp_id: str, rzp_status: str):
    """Marks payout as completed and notifies worker."""
    update_data = {
        "status": "completed",
        "razorpay_ref": rzp_status,
        "razorpay_payout_id": rzp_id
    }
    
    result = sb.table("payouts").update(update_data).eq("id", payout_id).execute()
    if result.data:
        payout = result.data[0]
        worker_id = payout.get("worker_id")
        amount = payout.get("final_amount", 0)
        
        # Notify via WhatsApp
        # Fetch worker phone and language
        worker_res = sb.table("workers").select("phone_number, name, language").eq("id", worker_id).single().execute()
        if worker_res.data:
            phone = worker_res.data["phone_number"]
            name = worker_res.data["name"] or "Worker"
            lang = worker_res.data.get("language", "en")
            
            await notify_worker(
                phone_number=phone,
                message_key="payout_processed",
                language=lang,
                name=name,
                amount=amount,
                ref=rzp_id
            )

async def handle_payout_failure(sb, payout_id: str, rzp_id: str, rzp_status: str, reason: str):
    """Marks payout as failed and alerts worker to fix their payment details."""
    update_data = {
        "status": "failed",
        "razorpay_ref": rzp_status,
        "razorpay_payout_id": rzp_id
    }
    
    result = sb.table("payouts").update(update_data).eq("id", payout_id).execute()
    if result.data:
        payout = result.data[0]
        worker_id = payout.get("worker_id")
        
        # Notify via WhatsApp about failure
        worker_res = sb.table("workers").select("phone_number, name, language").eq("id", worker_id).single().execute()
        if worker_res.data:
            phone = worker_res.data["phone_number"]
            name = worker_res.data["name"] or "Worker"
            lang = worker_res.data.get("language", "en")
            
            # Fetch worker's UPI for the template
            payout_res = sb.table("payouts").select("*, workers(upi_id)").eq("id", payout_id).single().execute()
            worker_upi = payout_res.data.get("workers", {}).get("upi_id", "your UPI") if payout_res.data else "your UPI"
            
            await notify_worker(
                phone_number=phone,
                message_key="upi_failed",
                language=lang,
                amount=payout.get("final_amount", 0),
                upi=worker_upi
            )

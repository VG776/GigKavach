"""
services/razorpay_payout_service.py
───────────────────────────────────
Handles disbursement of funds to gig workers using RazorpayX.
Uses direct HTTPX calls to ensure compatibility with RazorpayX API,
bypassing limitations in the standard Razorpay Python SDK.
"""

import logging
import httpx
import base64
from typing import Dict, Any, Optional
from config.settings import settings
from utils.supabase_client import get_supabase

logger = logging.getLogger("gigkavach.razorpay_payout")

# RazorpayX Base URL
RZP_X_BASE_URL = "https://api.razorpay.com/v1"

class RazorpayPayoutError(Exception):
    """Raised when Razorpay processing fails."""
    pass

def _get_auth_header() -> str:
    """Generates the Basic Auth header for Razorpay."""
    auth_str = f"{settings.RAZORPAY_KEY_ID}:{settings.RAZORPAY_KEY_SECRET}"
    encoded_auth = base64.b64encode(auth_str.encode()).decode()
    return f"Basic {encoded_auth}"

async def get_or_create_contact(worker_id: str) -> str:
    """
    Retrieves or creates a RazorpayX Contact for a worker via direct API.
    """
    sb = get_supabase()
    
    # 1. Fetch worker details
    worker_res = sb.table("workers").select("*").eq("id", worker_id).single().execute()
    if not worker_res.data:
        raise RazorpayPayoutError(f"Worker {worker_id} not found")
    
    worker = worker_res.data
    phone = worker.get("phone") or worker.get("phone_number")
    name = worker.get("name") or f"Worker_{worker_id[:8]}"
    
    # 2. Check for cached ID (silently)
    contact_id = worker.get("rzp_contact_id") or worker.get("razorpay_contact_id")
    if contact_id:
        return contact_id

    # 3. Create in RazorpayX via HTTP
    async with httpx.AsyncClient() as client_http:
        payload = {
            "name": name,
            "contact": phone,
            "type": "employee",
            "reference_id": worker_id,
            "notes": {"system": "GigKavach"}
        }
        
        resp = await client_http.post(
            f"{RZP_X_BASE_URL}/contacts",
            json=payload,
            headers={"Authorization": _get_auth_header()}
        )
        
        data = resp.json()
        if resp.status_code in [200, 201]:
            new_id = data["id"]
            # Attempt to cache (silent fail)
            try:
                if "rzp_contact_id" in worker:
                    sb.table("workers").update({"rzp_contact_id": new_id}).eq("id", worker_id).execute()
            except: pass
            return new_id
        elif "already exists" in str(data).lower():
            # In production, we'd extract the ID from the error or search.
            # Simplified for now.
            logger.warning(f"Contact {phone} already exists in RazorpayX.")
            raise RazorpayPayoutError(f"Contact already exists: {data.get('error', {}).get('description')}")
        else:
            raise RazorpayPayoutError(f"RZP Contact failed: {data}")

async def get_or_create_fund_account(worker_id: str, upi_id: str) -> str:
    """
    Links a worker's UPI (VPA) to their Razorpay Contact via direct API.
    """
    contact_id = await get_or_create_contact(worker_id)
    
    async with httpx.AsyncClient() as client_http:
        payload = {
            "contact_id": contact_id,
            "account_type": "vpa",
            "vpa": {"address": upi_id}
        }
        
        resp = await client_http.post(
            f"{RZP_X_BASE_URL}/fund_accounts",
            json=payload,
            headers={"Authorization": _get_auth_header()}
        )
        
        data = resp.json()
        if resp.status_code in [200, 201]:
            return data["id"]
        else:
            raise RazorpayPayoutError(f"RZP Fund Account failed: {data}")

async def initiate_payout(payout_id: str) -> Dict[str, Any]:
    """
    Triggers the actual money transfer via direct HTTP call to RazorpayX.
    """
    sb = get_supabase()
    
    # 1. Fetch payout and worker details
    payout_result = sb.table("payouts").select("*, workers(*)").eq("id", payout_id).single().execute()
    if not payout_result.data:
        raise RazorpayPayoutError(f"Payout {payout_id} not found")
    
    payout = payout_result.data
    worker = payout.get("workers", {})
    worker_id = payout["worker_id"]
    upi_id = payout.get("upi_id") or worker.get("upi_id")
    amount = payout.get("final_amount")
    
    if not upi_id:
        raise RazorpayPayoutError(f"No UPI ID found for worker {worker_id}")

    # 2. Resolve Fund Account
    fa_id = await get_or_create_fund_account(worker_id, upi_id)
    
    # 3. Initiate Payout via HTTP
    async with httpx.AsyncClient() as client_http:
        payload = {
            "account_number": "2323230058864703", # Demo Account
            "fund_account_id": fa_id,
            "amount": int(amount * 100),
            "currency": "INR",
            "mode": "UPI",
            "purpose": "payout",
            "queue_if_low_balance": True,
            "reference_id": payout_id,
            "notes": {"payout_id": payout_id}
        }
        
        logger.info(f"Initiating Razorpay payout of ₹{amount} for {worker_id}")
        resp = await client_http.post(
            f"{RZP_X_BASE_URL}/payouts",
            json=payload,
            headers={"Authorization": _get_auth_header()}
        )
        
        data = resp.json()
        if resp.status_code in [200, 201]:
            # 4. Update local DB (Using verified columns)
            update_data = {
                "status": "processing",
                "razorpay_payout_id": data["id"],
                "razorpay_ref": data["status"]
            }
            try:
                sb.table("payouts").update(update_data).eq("id", payout_id).execute()
            except: pass
            return data
        else:
            # Update status to failed
            try:
                sb.table("payouts").update({"status": "failed", "razorpay_ref": str(data)}).eq("id", payout_id).execute()
            except: pass
            raise RazorpayPayoutError(f"RZP Payout failed: {data}")

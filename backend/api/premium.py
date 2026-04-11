"""
api/premium.py
─────────────────────────────────────────────────────────────
Exposes the endpoint for predicting dynamic premium price quotes.
"""

from fastapi import APIRouter, HTTPException, Query, status
import logging
from pydantic import BaseModel
from typing import Dict, Any

from models.worker import PlanType
from services.premium_service import compute_dynamic_quote

logger = logging.getLogger("gigkavach.api.premium")

router = APIRouter(tags=["Premium"])

class PremiumQuoteResponse(BaseModel):
    worker_id: str
    base_premium: float
    dynamic_premium: float
    discount_applied: float
    bonus_coverage_hours: int
    plan_type: str
    insights: Dict[str, Any]


@router.get(
    "/quote",
    response_model=PremiumQuoteResponse,
    status_code=status.HTTP_200_OK,
    summary="Get dynamic premium quote for a worker"
)
async def get_premium_quote(
    worker_id: str = Query(..., description="UUID of the worker requesting a quote"),
    plan: str = Query(PlanType.BASIC.value, description="Tier: basic, plus, or pro")
):
    """
    Computes a personalized dynamic weekly premium using the AI Pricing model.
    The output abides by the strict Discount-Only psychology, meaning
    the worker's premium can only decrease based on their risk profile and trust score.
    
    If expected risk is exceptionally high, cash discounts may be zero, but 
    free 'Bonus Coverage Hours' are granted instead. 
    """
    try:
        quote = compute_dynamic_quote(worker_id, plan)
        return quote
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(ve)
        )
    except Exception as e:
        logger.error(f"Error computing dynamic quote for {worker_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to compute premium quote."
        )

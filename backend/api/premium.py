"""
api/premium.py
─────────────────────────────────────────────────────────────
Exposes the endpoint for predicting dynamic premium price quotes.
Supports both GET (query params) and POST (request body) for flexibility.
"""

from fastapi import APIRouter, HTTPException, Query, Body, status
import logging
from pydantic import BaseModel, Field, validator
from typing import Dict, Any, Optional

from models.worker import PlanType
from services.premium_service import compute_dynamic_quote

logger = logging.getLogger("gigkavach.api.premium")

router = APIRouter(prefix="/premium", tags=["Premium"])

class PremiumQuoteRequest(BaseModel):
    """Request body for premium quote calculation."""
    worker_id: str = Field(..., description="UUID of the worker requesting a quote", min_length=1)
    plan_tier: str = Field(
        default=PlanType.BASIC.value,
        description="Plan tier: basic, plus, or pro"
    )
    
    @validator('plan_tier')
    def validate_plan_tier(cls, v):
        """Validate that plan_tier is one of the accepted values."""
        valid_plans = [PlanType.BASIC.value, PlanType.PLUS.value, PlanType.PRO.value]
        if v.lower() not in valid_plans:
            raise ValueError(f"Invalid plan tier. Must be one of: {', '.join(valid_plans)}")
        return v.lower()

class PremiumQuoteResponse(BaseModel):
    """Response model for premium quote calculation."""
    worker_id: str
    base_premium: float
    dynamic_premium: float
    discount_applied: float
    bonus_coverage_hours: int
    plan_type: str
    risk_score: Optional[float] = None
    risk_factors: Optional[Dict[str, Any]] = None
    explanation: Optional[str] = None
    insights: Dict[str, Any]


@router.post(
    "/quote",
    response_model=PremiumQuoteResponse,
    status_code=status.HTTP_200_OK,
    summary="Calculate dynamic premium quote (POST)"
)
async def calculate_premium_quote_post(
    request: PremiumQuoteRequest = Body(..., description="Premium quote request parameters")
):
    """
    Computes a personalized dynamic weekly premium using the AI Pricing model.
    
    **Request Body:**
    - `worker_id` (required): UUID of the worker
    - `plan_tier` (required): One of 'basic', 'plus', or 'pro'
    
    **Response:**
    Returns a PremiumQuoteResponse with:
    - `base_premium`: List price for the selected plan
    - `dynamic_premium`: Personalized price after discount
    - `discount_applied`: Amount saved (in currency)
    - `bonus_coverage_hours`: Hours of bonus coverage if DCI is high
    - `plan_type`: Confirmed plan tier
    - `insights`: Risk factors, gig_score, zone risk level, explanation
    
    **Error Handling:**
    - 404: Worker not found
    - 400: Invalid plan tier
    - 500: Model inference failed (falls back to deterministic discount)
    """
    try:
        # Validate worker_id format (basic check)
        if not request.worker_id or len(request.worker_id.strip()) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="worker_id cannot be empty"
            )
        
        # Compute the quote using the service
        quote = await compute_dynamic_quote(request.worker_id, request.plan_tier)
        
        # Enrich response with risk factors if available
        gig_score = quote["insights"].get("gig_score", 0)
        risk_score = max(0, min(100, 100 - gig_score))  # Inverse: low gig_score = high risk
        
        response = PremiumQuoteResponse(
            worker_id=quote["worker_id"],
            base_premium=quote["base_premium"],
            dynamic_premium=quote["dynamic_premium"],
            discount_applied=quote["discount_applied"],
            bonus_coverage_hours=quote["bonus_coverage_hours"],
            plan_type=quote["plan_type"],
            risk_score=risk_score,
            risk_factors={
                "gig_score": gig_score,
                "zone_risk": quote["insights"]["forecasted_zone_risk"],
                "primary_zone": quote["insights"]["primary_zone"]
            },
            explanation=quote["insights"]["reason"],
            insights=quote["insights"]
        )
        
        logger.info(f"Premium quote calculated for {request.worker_id}: ₹{quote['dynamic_premium']}")
        return response
        
    except ValueError as ve:
        logger.warning(f"Validation error for {request.worker_id}: {str(ve)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(ve)
        )
    except Exception as e:
        logger.error(f"Error computing premium quote for {request.worker_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to compute premium quote. Please try again later."
        )


@router.get(
    "/quote",
    response_model=PremiumQuoteResponse,
    status_code=status.HTTP_200_OK,
    summary="Calculate dynamic premium quote (GET - Legacy)"
)
async def calculate_premium_quote_get(
    worker_id: str = Query(..., description="UUID of the worker requesting a quote", min_length=1),
    plan: str = Query(PlanType.BASIC.value, description="Tier: basic, plus, or pro")
):
    """
    Legacy GET endpoint for compatibility.
    Use POST /quote instead for production.
    
    **Query Parameters:**
    - `worker_id` (required): UUID of the worker
    - `plan` (optional): Plan tier (default: basic)
    """
    # Validate plan param
    valid_plans = [PlanType.BASIC.value, PlanType.PLUS.value, PlanType.PRO.value]
    if plan.lower() not in valid_plans:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid plan. Must be one of: {', '.join(valid_plans)}"
        )
    
    try:
        quote = await compute_dynamic_quote(worker_id, plan.lower())
        
        gig_score = quote["insights"].get("gig_score", 0)
        risk_score = max(0, min(100, 100 - gig_score))
        
        response = PremiumQuoteResponse(
            worker_id=quote["worker_id"],
            base_premium=quote["base_premium"],
            dynamic_premium=quote["dynamic_premium"],
            discount_applied=quote["discount_applied"],
            bonus_coverage_hours=quote["bonus_coverage_hours"],
            plan_type=quote["plan_type"],
            risk_score=risk_score,
            risk_factors={
                "gig_score": gig_score,
                "zone_risk": quote["insights"]["forecasted_zone_risk"],
                "primary_zone": quote["insights"]["primary_zone"]
            },
            explanation=quote["insights"]["reason"],
            insights=quote["insights"]
        )
        
        return response
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

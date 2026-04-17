"""
api/fraud.py
──────────────────────────────────────
Fraud Detection Endpoints

Provides HTTP API for real-time fraud assessment on claims.
Integrates with fraud_service.py which manages the 3-stage detection pipeline.
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, status

from services.fraud_service import check_fraud

# Setup logging
logger = logging.getLogger("gigkavach.fraud_api")
# Task 8: prefix removed — main.py mounts this with /api/v1 already
router = APIRouter(tags=["Fraud Detection"])


# ─── Request/Response Models ─────────────────────────────────────────────────

class ClaimData(BaseModel):
    """Claim information for fraud assessment."""
    claim_id: str = Field(..., description="Unique claim ID")
    worker_id: str = Field(..., description="Worker ID")
    dci_score: float = Field(..., ge=0, le=100, description="Disruption Composite Index (0-100)")
    gps_coordinates: Optional[tuple] = Field(None, description="(latitude, longitude)")
    gps_verified_pct: Optional[float] = Field(0.9, ge=0, le=1)
    ip_location: Optional[tuple] = Field(None, description="IP-detected (latitude, longitude)")
    claims_in_zone_2min: Optional[int] = Field(0, description="Co-claims in zone within 2 minutes")
    claim_timestamp_std_sec: Optional[float] = Field(500, description="Std dev of claim timestamps")
    platform_earnings_before_disruption: Optional[float] = Field(0)
    platform_orders_before_disruption: Optional[int] = Field(0)
    disruption_outside_shift: Optional[bool] = Field(False)
    device_id: Optional[str] = Field(None, description="Device identifier")
    

class WorkerHistory(BaseModel):
    """Historical data for a worker."""
    claims_last_7_days: Optional[int] = 2
    dci_scores_at_claim: Optional[list] = Field(None, description="Historical DCI scores")
    last_claim_timestamp: Optional[datetime] = None
    claim_amounts: Optional[list] = None
    zone_claim_density: Optional[float] = 2.0
    device_ids: Optional[Dict[str, list]] = None
    co_claim_count_10min: Optional[int] = 0


class FraudCheckRequest(BaseModel):
    """Request payload for fraud assessment."""
    claim: ClaimData
    worker_history: Optional[WorkerHistory] = None
    user_context: Optional[Dict[str, Any]] = None


class FraudCheckResponse(BaseModel):
    """Response payload from fraud assessment."""
    is_fraud: bool = Field(..., description="True if claim is flagged as fraudulent")
    fraud_score: float = Field(..., ge=0, le=1, description="Fraud probability (0-1)")
    decision: str = Field(..., description="APPROVE|FLAG_50|BLOCK")
    fraud_type: Optional[str] = Field(None, description="Type of fraud detected (if any)")
    payout_action: str = Field(..., description="'100%'|'50%_HOLD_48H'|'0%'")
    explanation: str = Field(..., description="Human-readable reason for decision")
    timestamp: str = Field(..., description="ISO timestamp of assessment")
    confidence: Optional[float] = Field(None, description="Confidence of detection")
    audit_log: Optional[Dict[str, Any]] = Field(None, description="Stage-wise scores for debugging")


# ─── Endpoints ───────────────────────────────────────────────────────────────

@router.post(
    "/check-fraud",
    response_model=FraudCheckResponse,
    summary="Check claim for fraud",
    description="""
    Perform 3-stage fraud detection on a claim:
    
    **Stage 1**: Rule-based hard blocks (device farming, rapid reclaim, etc.)
    
    **Stage 2**: Isolation Forest anomaly detection (unsupervised)
    
    **Stage 3**: XGBoost multi-class classifier (fraud type + confidence)
    
    **Ensemble**: Rule-aware blending
    - If Stage 1 rules trigger: fraud_score = 0.9 (high confidence)
    - Otherwise: fraud_score = 0.2×IF + 0.8×XGB
    
    **Returns**:
    - is_fraud: boolean flag
    - fraud_score: 0-1 probability
    - decision: categorical (APPROVE|FLAG_50|BLOCK)
    - payout_action: what to do with worker payment
    - explanation: why this decision was made
    
    **Example**:
    ```json
    {
      "claim": {
        "claim_id": "CLM_2024_001",
        "worker_id": "W123",
        "dci_score": 78.5,
        "gps_coordinates": [13.0827, 80.2707],
        "gps_verified_pct": 0.95
      },
      "worker_history": {
        "claims_last_7_days": 5,
        "dci_scores_at_claim": [75, 76, 78, 79]
      }
    }
    ```
    """
)
async def check_fraud_endpoint(request: FraudCheckRequest):
    """Check a claim for fraud using the 3-stage detection pipeline."""
    try:
        logger.info(
            f"[FRAUD CHECK] Assessing claim {request.claim.claim_id} "
            f"for worker {request.claim.worker_id}..."
        )
        
        # Convert pydantic models to dicts for service layer
        claim_dict = request.claim.dict(exclude_none=True)
        worker_history_dict = (
            request.worker_history.dict(exclude_none=True)
            if request.worker_history
            else None
        )
        
        # Call fraud detection service
        result = await check_fraud(
            claim=claim_dict,
            worker_history=worker_history_dict,
            user_context=request.user_context,
        )
        
        logger.info(
            f"[FRAUD RESULT] claim={request.claim.claim_id} | "
            f"decision={result['decision']} | score={result['fraud_score']:.3f}"
        )
        
        return FraudCheckResponse(**result)
        
    except Exception as e:
        logger.error(f"[FRAUD ERROR] Failed to assess claim: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Fraud assessment failed: {str(e)}"
        )


@router.get(
    "/fraud/health",
    summary="Fraud detection system health",
    description="Check if fraud detection models are loaded and ready"
)
async def fraud_health():
    """Health check for fraud detection system."""
    try:
        from ml.fraud_detector import get_detector
        detector = get_detector()
        
        return {
            "status": "healthy",
            "models_loaded": True,
            "timestamp": datetime.utcnow().isoformat(),
            "stages": {
                "stage_1": "rule_based_hard_blocks",
                "stage_2": "isolation_forest_v2.0",
                "stage_3": "xgboost_multiclass_v3+"
            },
            "ensemble": "rule_aware (if_rule: 0.9 else: 0.2*IF + 0.8*XGB)"
        }
    except Exception as e:
        logger.error(f"Fraud health check failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Fraud detection system unavailable: {str(e)}"
        )


@router.post(
    "/fraud/batch-check",
    summary="Batch fraud assessment (async)",
    description="Check multiple claims for fraud in a single request (useful for bulk operations)"
)
async def batch_fraud_check(claims: list[FraudCheckRequest]):
    """
    Assess multiple claims for fraud.
    
    Note: This is synchronous for now but suitable for small batches (< 100 claims).
    For large batches, recommend using message queue (Celery/RabbitMQ).
    """
    try:
        results = []
        for claim_request in claims:
            result = await check_fraud_endpoint(claim_request)
            results.append(result)
        
        return {
            "total": len(results),
            "assessed_at": datetime.utcnow().isoformat(),
            "results": results
        }
    except Exception as e:
        logger.error(f"Batch fraud check failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch assessment failed: {str(e)}"
        )


# ─── Fraud Flags Monitoring (Dashboard) ────────────────────────────────────────

class FraudFlagResponse(BaseModel):
    """A fraud flag record from the monitoring dashboard."""
    id: str
    worker_id: str
    worker_name: Optional[str] = None
    payout_id: Optional[str] = None
    signals: Dict[str, bool] = Field(default_factory=dict)
    signal_count: int = 0
    fraud_tier: str = "tier0"
    gps_lat: Optional[float] = None
    gps_lng: Optional[float] = None
    gps_entropy_score: Optional[float] = None
    is_appealed: bool = False
    appeal_outcome: Optional[str] = None
    resolved_at: Optional[str] = None
    notes: Optional[str] = None
    created_at: str
    risk_level: str  # 'low', 'medium', 'high'
    path: str  # 'A', 'B', 'C'


@router.get(
    "/fraud-flags",
    response_model=Dict[str, Any],
    summary="Get all active fraud flags (dashboard)",
    description="""
    Fetches recent fraud flag records from the fraud_flags table with worker details.
    Used by the Fraud Operations Center dashboard.
    
    Returns list of flagged workers with their signal breakdown.
    """
)
async def get_fraud_flags(
    limit: int = 100,
    resolved: bool = False,
    tier: Optional[str] = None
):
    """
    Fetch fraud flag records for the dashboard.
    
    Query params:
      - limit: Max records to return (default: 100)
      - resolved: Include resolved cases (default: false)
      - tier: Filter by tier ('tier0', 'tier1', 'tier2') or None for all
    """
    try:
        from utils.supabase_client import get_supabase
        from utils.pincode_mapper import PINCODE_MAP
        
        sb = get_supabase()
        logger.info(f"[FRAUD_FLAGS] Fetching fraud flags: limit={limit}, resolved={resolved}, tier={tier}")
        
        # Build query
        query = sb.table("fraud_flags").select(
            "id, worker_id, payout_id, sig1_gps, sig2_ip_zone_mismatch, sig3_velocity, "
            "sig4_gps_entropy_low, sig5_claim_timing_cluster, sig6_zone_loyalty_mismatch, "
            "signal_count, fraud_tier, gps_lat, gps_lng, gps_entropy_score, "
            "is_appealed, appeal_outcome, resolved_at, notes, created_at"
        )
        
        # Filter by resolution status
        if not resolved:
            query = query.is_("resolved_at", None)
        
        # Filter by tier if specified
        if tier:
            query = query.eq("fraud_tier", tier)
        
        # Order by creation date (newest first)
        query = query.order("created_at", desc=True).limit(limit)
        
        result = query.execute()
        rows = result.data or []
        logger.info(f"[FRAUD_FLAGS] Found {len(rows)} fraud flag records")
        
        # Fetch worker names - batch query for efficiency
        worker_ids = list(set(row["worker_id"] for row in rows))
        workers_by_id = {}
        
        if worker_ids:
            logger.info(f"[FRAUD_FLAGS] Fetching details for {len(worker_ids)} workers")
            try:
                workers_result = sb.table("workers").select("id, name, gig_score, pin_codes").in_("id", worker_ids).execute()
                for worker in workers_result.data or []:
                    workers_by_id[worker["id"]] = worker
                logger.info(f"[FRAUD_FLAGS] Fetched {len(workers_by_id)} worker records")
            except Exception as worker_err:
                logger.warning(f"[FRAUD_FLAGS] Failed to fetch worker details: {str(worker_err)}")
        
        # Transform fraud flags
        flags_list = []
        for row in rows:
            try:
                # Extract signals
                signals = {
                    "gps": row.get("sig1_gps", False),
                    "ip_mismatch": row.get("sig2_ip_zone_mismatch", False),
                    "velocity": row.get("sig3_velocity", False),
                    "gps_entropy": row.get("sig4_gps_entropy_low", False),
                    "timing_cluster": row.get("sig5_claim_timing_cluster", False),
                    "zone_loyalty": row.get("sig6_zone_loyalty_mismatch", False),
                }
                
                # Calculate risk level based on signal count and tier
                signal_count = row.get("signal_count", 0)
                fraud_tier = row.get("fraud_tier", "tier0")
                
                if fraud_tier == "tier2" or signal_count >= 5:
                    risk_level = "high"
                    path = "C"
                elif fraud_tier == "tier1" or signal_count >= 2:
                    risk_level = "medium"
                    path = "B"
                else:
                    risk_level = "low"
                    path = "A"
                
                # Get worker details
                worker = workers_by_id.get(row["worker_id"], {})
                worker_name = worker.get("name", "Unknown Worker")
                gig_score = worker.get("gig_score", 85)  # Default to 85 if missing
                
                # pin_codes is an array, take the first one
                pin_codes_array = worker.get("pin_codes", [])
                working_pincode = None
                if pin_codes_array and len(pin_codes_array) > 0:
                    working_pincode = pin_codes_array[0]
                
                # Get zone from pincode
                zone_name = "Unknown"
                if working_pincode:
                    try:
                        pincode_str = str(working_pincode).strip()
                        logger.debug(f"[FRAUD_FLAGS] Looking up pincode: {pincode_str}")
                        pincode_info = PINCODE_MAP.get(pincode_str, {})
                        zone_name = pincode_info.get("neighborhood", "Unknown")
                        logger.debug(f"[FRAUD_FLAGS] Mapped pincode {pincode_str} to zone: {zone_name}")
                    except Exception as pincode_err:
                        logger.warning(f"[FRAUD_FLAGS] Failed to map pincode {working_pincode}: {str(pincode_err)}")
                
                flags_list.append({
                    "id": row["id"],
                    "worker_id": row["worker_id"],
                    "worker_name": worker_name,
                    "gig_score": gig_score,
                    "zone": zone_name,
                    "payout_id": row.get("payout_id"),
                    "signals": signals,
                    "signal_count": signal_count,
                    "fraud_tier": fraud_tier,
                    "gps_lat": row.get("gps_lat"),
                    "gps_lng": row.get("gps_lng"),
                    "gps_entropy_score": row.get("gps_entropy_score"),
                    "is_appealed": row.get("is_appealed", False),
                    "appeal_outcome": row.get("appeal_outcome"),
                    "resolved_at": row.get("resolved_at"),
                    "notes": row.get("notes"),
                    "created_at": row.get("created_at"),
                    "risk_level": risk_level,
                    "path": path,
                })
            except Exception as transform_err:
                logger.error(f"[FRAUD_FLAGS] Failed to transform flag record: {str(transform_err)}")
        
        logger.info(f"[FRAUD_FLAGS] Returning {len(flags_list)} transformed fraud flags")
        return {
            "count": len(flags_list),
            "flags": flags_list,
        }
        
    except Exception as e:
        logger.error(f"Failed to fetch fraud flags: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch fraud flags: {str(e)}"
        )


@router.get(
    "/fraud-summary",
    summary="Get fraud summary stats",
    description="High-level fraud statistics for the dashboard"
)
async def get_fraud_summary():
    """Get summary statistics for fraud monitoring dashboard."""
    try:
        from utils.supabase_client import get_supabase
        
        sb = get_supabase()
        logger.info("[FRAUD_SUMMARY] Fetching fraud summary statistics")
        
        # Count high risk active (tier2)
        high_risk = (
            sb.table("fraud_flags")
            .select("id", count="exact")
            .eq("fraud_tier", "tier2")
            .is_("resolved_at", None)
            .execute()
        )
        high_risk_count = high_risk.count if hasattr(high_risk, 'count') else 0
        logger.info(f"[FRAUD_SUMMARY] High risk (tier2) active: {high_risk_count}")
        
        # Count tier1 (medium)
        medium_risk = (
            sb.table("fraud_flags")
            .select("id", count="exact")
            .eq("fraud_tier", "tier1")
            .is_("resolved_at", None)
            .execute()
        )
        medium_risk_count = medium_risk.count if hasattr(medium_risk, 'count') else 0
        logger.info(f"[FRAUD_SUMMARY] Medium risk (tier1) active: {medium_risk_count}")
        
        # Count resolved this week
        from datetime import datetime, timedelta, timezone
        week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        resolved_week = (
            sb.table("fraud_flags")
            .select("id", count="exact")
            .gte("resolved_at", week_ago)
            .execute()
        )
        resolved_count = resolved_week.count if hasattr(resolved_week, 'count') else 0
        logger.info(f"[FRAUD_SUMMARY] Resolved this week: {resolved_count}")
        
        result = {
            "high_risk_active": high_risk_count or 0,
            "medium_risk_active": medium_risk_count or 0,
            "resolved_this_week": resolved_count or 0,
            "total_flagged": (high_risk_count or 0) + (medium_risk_count or 0),
        }
        logger.info(f"[FRAUD_SUMMARY] Returning summary: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Failed to fetch fraud summary: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch fraud summary: {str(e)}"
        )

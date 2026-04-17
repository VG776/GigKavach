"""
Fraud Detection Service Layer

Provides high-level API for fraud checking with logging and audit trail.
"""

import os
import sys
import logging
from datetime import datetime, timezone

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from ml.fraud_detector import get_detector
from services.gigscore_service import update_gig_score, GigScoreEvent
from utils.db import get_supabase

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class FraudDetectionService:
    """Service layer for fraud detection."""
    
    def __init__(self):
        self.detector = get_detector()
    
    async def check_fraud(self, claim, worker_history=None, user_context=None):
        """
        Executes the three-stage fraud detection pipeline:
        1. Behavioral Telemetry Analysis (GPS Jump, Speed Anomalies)
        2. Pattern Recognition (Device ID, Rapid Payout Reclaim)
        3. ML-Driven ML Anomaly Detection (Isolation Forest)
        
        Returns a dict with 'decision', 'fraud_score', and 'fraud_type'.
        """
        worker_id = claim.get('worker_id')
        claim_id = claim.get('claim_id')
        
        logger.info(f"Starting fraud check for worker={worker_id} claim={claim_id}")
        
        try:
            # --- STAGE 0: Enrichment ---
            # Fetch worker's delivery pin codes to verify location
            sb = get_supabase()
            worker_res = sb.table("workers").select("pin_codes").eq("id", worker_id).single().execute()
            
            if worker_res.data:
                worker_pincodes = worker_res.data.get('pin_codes', [])
                logger.info(f"Enriched claim with worker zones: {worker_pincodes}")
            else:
                worker_pincodes = []
                logger.warning(f"Could not find worker zones for enrichment: {worker_id}")

            # --- STAGE 1: Real-time Behavioral Telemetry & Shield Logic ---
            from utils.redis_client import get_redis
            import json
            
            rc = await get_redis()
            
            # 1. Telemetry Window Fetching
            raw_history = await rc.lrange(f"telemetry:{worker_id}", 0, -1)
            location_history = [json.loads(s) for s in raw_history] if raw_history else []
            
            # 2. Shield Gating (Signal 2): Verify shift was active
            shift_data = await rc.get(f"shift_active:{worker_id}")
            is_on_shift = shift_data is not None
            
            # 3. Geo-IP Cross-check (Signal 1): 
            # In production, we get IP from request. For simulation, use user_context
            ip_lat = user_context.get('ip_lat') if user_context else None
            ip_lng = user_context.get('ip_lng') if user_context else None
            
            gps_ip_dist = 0
            if ip_lat and ip_lng and location_history:
                from services.telemetry_service import telemetry_processor
                curr_lat = location_history[0]['lat']
                curr_lng = location_history[0]['lng']
                gps_ip_dist = telemetry_processor._haversine(ip_lat, ip_lng, curr_lat, curr_lng)
            
            # Inject signals into claim for the detector
            claim['location_history'] = location_history
            claim['is_on_shift'] = is_on_shift
            claim['gps_ip_distance_km'] = gps_ip_dist
            
            logger.info(f"Enriched claim with telemetry. OnShift={is_on_shift}, Points={len(location_history)}, IP-Dist={gps_ip_dist:.1f}km")
            
            # --- STAGE 2: Model Inference ---
            model_result = self.detector.detect_fraud(claim)
            
            decision = model_result.get('decision', 'APPROVE')
            fraud_score = model_result.get('fraud_score', 0.0)
            fraud_type = model_result.get('fraud_type', 'none')
            
            # --- STAGE 3: Trinity Feedback Integration ---
            # If fraud is detected, trigger GigScore penalty automatically
            if decision in ['FLAG_50', 'BLOCK']:
                penalty_event = GigScoreEvent.FRAUD_TIER_1 if decision == 'FLAG_50' else GigScoreEvent.FRAUD_TIER_2
                update_gig_score(worker_id, penalty_event, {
                    'claim_id': claim_id,
                    'fraud_score': fraud_score,
                    'fraud_type': fraud_type,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })
                logger.warning(f"Trinity Feedback: Worker={worker_id} penalized for {fraud_type}")

            return {
                'decision': decision,
                'fraud_score': fraud_score,
                'fraud_type': fraud_type,
                'is_fraud': decision != 'APPROVE',
                'explanation': f"Detected {fraud_type} with {fraud_score*100:.1f}% confidence.",
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Fraud detection error: {e}")
            # Safe fallback: Flag suspicious but don't block
            return {
                'decision': 'FLAG_50',
                'fraud_score': 0.5,
                'fraud_type': 'system_error',
                'is_fraud': True,
                'explanation': f"Error during assessment: {e}. Flagged for manual review.",
                'timestamp': datetime.now(timezone.utc).isoformat()
            }

async def check_fraud(claim, worker_history=None, user_context=None):
    """Entry point for checking fraud."""
    service = FraudDetectionService()
    return await service.check_fraud(claim, worker_history, user_context)

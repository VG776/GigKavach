"""
Fraud Detection Service Layer

Provides high-level API for fraud checking with logging and audit trail.
"""

import os
import sys
import logging
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from ml.fraud_detector import get_detector

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
    
    def check_fraud(self, claim, worker_history=None, user_context=None):
        """
        Check claim for fraud.
        
        Args:
            claim (dict): Claim data (dci_score, gps_coordinates, etc.)
            worker_history (dict, optional): Worker's claim history
            user_context (dict, optional): Additional context (user_id, api_version, etc.)
        
        Returns:
            dict with keys:
              - is_fraud (bool)
              - fraud_score (float): 0-1
              - decision (str): APPROVE|FLAG_50|BLOCK
              - fraud_type (str): Type of fraud detected (if any)
              - payout_action (str): What to do with payout (100%|50%_HOLD_48H|0%)
              - explanation (str): Human-readable reason
              - timestamp (str): ISO timestamp
              - detector_version (str): Model version
              - audit_log (dict): For logging/debugging
        """
        
        try:
            # Get fraud detection result
            result = self.detector.detect_fraud(claim, worker_history)
            
            # Map decision to payout action
            payout_action = self._get_payout_action(result['decision'])
            
            # Build response
            response = {
                'is_fraud': result['decision'] != 'APPROVE',
                'fraud_score': result['fraud_score'],
                'decision': result['decision'],
                'fraud_type': result['fraud_type'],
                'payout_action': payout_action,
                'explanation': self._get_explanation(result),
                'timestamp': datetime.utcnow().isoformat(),
                'detector_version': '2.0',
                'audit_log': {
                    'stage1_result': result['stage1_result'],
                    'stage2_score': result['stage2_score'],
                    'stage3_score': result['stage3_score'],
                    'confidence': result['confidence'],
                    'claim_id': claim.get('claim_id'),
                    'worker_id': claim.get('worker_id'),
                    'user_context': user_context or {},
                }
            }
            
            # Logging
            log_msg = (
                f"Fraud check - claim_id={claim.get('claim_id')}, "
                f"worker_id={claim.get('worker_id')}, "
                f"decision={response['decision']}, "
                f"fraud_score={response['fraud_score']:.4f}"
            )
            
            if response['is_fraud']:
                logger.warning(f"[FRAUD DETECTED] {log_msg} - {response['fraud_type']}")
            else:
                logger.info(f"[FRAUD CLEAR] {log_msg}")
            
            return response
        
        except Exception as e:
            logger.error(f"Fraud detection error: {str(e)}")
            # Safe default: flag suspicious claims
            return {
                'is_fraud': True,
                'fraud_score': 0.5,
                'decision': 'FLAG_50',
                'fraud_type': 'unknown_error',
                'payout_action': '50%_HOLD_48H',
                'explanation': 'Error in fraud detection - holding for review',
                'timestamp': datetime.utcnow().isoformat(),
                'detector_version': '2.0',
                'audit_log': {
                    'error': str(e),
                    'claim_id': claim.get('claim_id', 'unknown'),
                }
            }
    
    def _get_payout_action(self, decision):
        """Map fraud decision to payout action."""
        mapping = {
            'APPROVE': '100%',
            'FLAG_50': '50%_HOLD_48H',
            'BLOCK': '0%',
        }
        return mapping.get(decision, '50%_HOLD_48H')
    
    def _get_explanation(self, result):
        """Generate human-readable explanation."""
        decision = result['decision']
        fraud_type = result['fraud_type']
        fraud_score = result['fraud_score']
        stage1 = result['stage1_result']
        
        if stage1 != 'PASS':
            return stage1
        
        if decision == 'APPROVE':
            return 'Claim approved: fraud score < 0.30'
        elif decision == 'FLAG_50':
            return (
                f'Claim flagged ({fraud_score:.1%}): Possible {fraud_type}. '
                '50% paid now, 50% held for 48h verification.'
            )
        elif decision == 'BLOCK':
            return (
                f'Claim blocked ({fraud_score:.1%}): Detected {fraud_type}. '
                'Zero payout due to fraud risk.'
            )
        else:
            return 'Unknown decision'


# Global service instance
_service = None


def get_fraud_service():
    """Get or initialize the fraud detection service singleton."""
    global _service
    if _service is None:
        _service = FraudDetectionService()
    return _service


# Convenience functions
def check_fraud(claim, worker_history=None, user_context=None):
    """Check claim for fraud."""
    service = get_fraud_service()
    return service.check_fraud(claim, worker_history, user_context)

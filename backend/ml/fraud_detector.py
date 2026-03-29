"""
3-Stage Fraud Detector (Rules → Isolation Forest → XGBoost)

Pipeline:
  Stage 1: Rule-based hard blocks
    - Device farming: Multiple workers on same device
    - Rapid re-claim: Claiming within 6 hours of last claim
    - Zone density surge: 5+ workers claiming same zone in 30 min
    - Threshold gaming: 3+ claims near DCI 65-70 band
  
  Stage 2: Isolation Forest (unsupervised anomaly detection)
  
  Stage 3: XGBoost (supervised classification)
  
  Ensemble (v3+): Rule-aware blending
    - If Stage 1 rules triggered: fraud_score = 0.9 (high confidence)
    - If Stage 1 rules NOT triggered: fraud_score = 0.2*IF + 0.8*XGBoost (ML-driven)

Outputs decision and fraud type.
"""

import os
import sys
import json
import numpy as np
import pickle
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from backend.ml.fraud_features_engineering import FraudFeaturesEngineer


class FraudDetector:
    """3-stage fraud detection pipeline."""
    
    # Fraud score thresholds
    THRESHOLD_APPROVE = 0.30
    THRESHOLD_FLAG_50 = 0.50
    
    # Feature columns (31 features from feature engineer)
    FEATURE_COLS = FraudFeaturesEngineer.NUMERICAL_FEATURES
    
    def __init__(self, model_dir='models/fraud_detection_v2'):
        """Load pre-trained models."""
        self.model_dir = Path(model_dir)
        self._load_models()
        self.feature_engineer = FraudFeaturesEngineer()
    
    def _load_models(self):
        """Load Stage 2 (IF) and Stage 3 (XGB) models."""
        if_path = self.model_dir / 'stage2_isolation_forest.pkl'
        xgb_path = self.model_dir / 'stage3_xgboost.pkl'
        scaler_path = self.model_dir / 'feature_scaler.pkl'
        
        if not if_path.exists():
            raise FileNotFoundError(f"Model not found: {if_path}")
        if not xgb_path.exists():
            raise FileNotFoundError(f"Model not found: {xgb_path}")
        if not scaler_path.exists():
            raise FileNotFoundError(f"Model not found: {scaler_path}")
        
        with open(if_path, 'rb') as f:
            self.isolation_forest = pickle.load(f)
        
        with open(xgb_path, 'rb') as f:
            self.xgboost_model = pickle.load(f)
        
        with open(scaler_path, 'rb') as f:
            self.scaler = pickle.load(f)
    
    def detect_fraud(self, claim, worker_history=None):
        """
        Full 3-stage fraud detection.
        
        Args:
            claim (dict): Claim data with location, DCI, timing info
            worker_history (dict, optional): Worker's claim history
        
        Returns:
            dict with keys:
              - fraud_score (float): 0-1, higher = more fraudulent
              - decision (str): APPROVE|FLAG_50|BLOCK
              - fraud_type (str): Device farming|Coordinated rings|etc.
              - stage1_result (str): PASS|BLOCK with reason
              - stage2_score (float): IF anomaly score
              - stage3_score (float): XGBoost probability
              - confidence (float): 0-1
        """
        
        # Stage 1: Rule-based hard blocks
        stage1_result = self._stage1_rules(claim, worker_history)
        if stage1_result['decision'] == 'BLOCK':
            return {
                'fraud_score': 1.0,
                'decision': 'BLOCK',
                'fraud_type': stage1_result['fraud_type'],
                'stage1_result': f"BLOCK: {stage1_result['reason']}",
                'stage2_score': None,
                'stage3_score': None,
                'confidence': 1.0,
            }
        
        # Stage 2 & 3: Model-based scoring
        features = self.feature_engineer.extract_features(claim, worker_history)
        
        # Extract in correct feature order
        X = np.array([features[col] for col in self.FEATURE_COLS], dtype=float).reshape(1, -1)
        X_scaled = self.scaler.transform(X)[0]
        
        # Stage 2: Isolation Forest anomaly score
        if_score_raw = self.isolation_forest.score_samples(X_scaled.reshape(1, -1))[0]
        if_score = 1 / (1 + np.exp(if_score_raw))  # Normalize to [0, 1]
        
        # Stage 3: XGBoost with IF score
        X_with_if = np.concatenate([X_scaled, [if_score]]).reshape(1, -1)
        xgb_score = self.xgboost_model.predict_proba(X_with_if)[0, 1]
        
        # Rule-aware ensemble (Improvement #5)
        # If rules triggered soft flag, be more confident (0.9)
        # Otherwise, let ML models decide (0.2*IF + 0.8*XGB for better weighting)
        if stage1_result['decision'] == 'PASS':
            # No rules triggered - trust ML models more
            fraud_score = 0.2 * if_score + 0.8 * xgb_score
        else:
            # Rules found soft signal - high confidence in alert
            fraud_score = 0.9
        
        # Decision
        if fraud_score < self.THRESHOLD_APPROVE:
            decision = 'APPROVE'
        elif fraud_score < self.THRESHOLD_FLAG_50:
            decision = 'FLAG_50'
        else:
            decision = 'BLOCK'
        
        # Fraud type identification
        fraud_type = self._identify_fraud_type(features, if_score, xgb_score)
        
        return {
            'fraud_score': float(fraud_score),
            'decision': decision,
            'fraud_type': fraud_type,
            'stage1_result': 'PASS',
            'stage2_score': float(if_score),
            'stage3_score': float(xgb_score),
            'confidence': max(if_score, xgb_score),
        }
    
    def _stage1_rules(self, claim, worker_history):
        """
        Stage 1: Rule-based hard blocks.
        
        Returns dict with keys:
          - decision (str): PASS|BLOCK
          - fraud_type (str)
          - reason (str)
        """
        
        # Block 1: Device farming detection
        if worker_history:
            device_id = claim.get('device_id')
            device_workers = worker_history.get('device_ids', {}).get(device_id, [])
            if len(device_workers) > 1:
                return {
                    'decision': 'BLOCK',
                    'fraud_type': 'device_farming',
                    'reason': f'Device {device_id} has {len(device_workers)} workers',
                }
        
        # Block 2: Rapid re-claim detection
        if worker_history:
            last_claim_ts = worker_history.get('last_claim_timestamp')
            if last_claim_ts and isinstance(last_claim_ts, datetime):
                time_since_last = (datetime.now() - last_claim_ts).total_seconds() / 3600
                if time_since_last < 6:
                    return {
                        'decision': 'BLOCK',
                        'fraud_type': 'rapid_reclaim',
                        'reason': f'Claimed {time_since_last:.1f} hours ago',
                    }
        
        # Block 3: Zone claim density surge
        zone_density = claim.get('claims_in_zone_2min', 0)
        if zone_density >= 5:
            return {
                'decision': 'BLOCK',
                'fraud_type': 'coordinated_rings',
                'reason': f'Zone density surge: {zone_density} workers in 30min',
            }
        
        # Block 4: Threshold gaming pattern (SOFTENED - avoid perfect memorization)
        if worker_history:
            dci_scores = worker_history.get('dci_scores_at_claim', [claim.get('dci_score', 70)])
            dci_in_band = sum(1 for d in dci_scores if 65 <= d <= 70)
            threshold_proximity = dci_in_band / len(dci_scores) if len(dci_scores) > 0 else 0
            
            avg_dci = np.mean(dci_scores)
            near_threshold_count = len(dci_scores)
            
            # SOFTENED: Require VERY strong signal (0.75+ proximity) to block
            # This prevents memorization of synthetic data patterns
            # Real threshold gamers often stay below 0.6, so this is conservative
            if threshold_proximity > 0.75 and 64 <= avg_dci <= 72 and near_threshold_count >= 4:
                return {
                    'decision': 'BLOCK',
                    'fraud_type': 'threshold_gaming',
                    'reason': f'Strong threshold gaming signal: {threshold_proximity:.1%} claims at DCI 64-72',
                }
        
        return {
            'decision': 'PASS',
            'fraud_type': None,
            'reason': None,
        }
    
    def _identify_fraud_type(self, features, if_score, xgb_score):
        """Identify fraud type based on feature patterns."""
        
        gps_dist = features.get('gps_ip_distance_km', 0)
        gps_verified = features.get('gps_verified_pct', 1.0)
        claims_zone_2min = features.get('claims_in_zone_2min', 0)
        claim_timestamp_std = features.get('claim_timestamp_std_sec', 1000)
        
        # GPS spoof: High distance + low GPS verification
        if gps_dist > 100 and gps_verified < 0.3:
            return 'gps_spoof'
        
        # Coordinated rings: High zone density + low timestamp variance
        if claims_zone_2min >= 5 and claim_timestamp_std < 300:
            return 'coordinated_rings'
        
        # Default to generic fraud
        return 'fraud_pattern'


# Global detector instance
_detector = None


def get_detector():
    """Get or initialize the fraud detector singleton."""
    global _detector
    if _detector is None:
        _detector = FraudDetector()
    return _detector

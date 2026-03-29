"""
Fraud Detection Feature Engineering - 3 Stages
Unified feature extraction for:
  - Stage 1: Rule-based hard blocks
  - Stage 2: Isolation Forest (unsupervised)
  - Stage 3: XGBoost (supervised)

Total: 33 features (24 original + 9 new history-based)
"""

import numpy as np
from datetime import datetime
from typing import Dict, Optional, List


class FraudFeaturesEngineer:
    """Extract all fraud detection features from claim + worker history."""
    
    # Original 24 features (Stages 1 & 2)
    ORIGINAL_FEATURES = [
        'gps_ip_distance_km', 'gps_verified_pct', 'claims_in_zone_2min',
        'claim_timestamp_std_sec', 'dci_score', 'dci_above_threshold',
        'platform_earnings_before_disruption', 'platform_orders_before_disruption',
        'platform_active_hours_week', 'hours_since_last_platform_activity',
        'registration_days_ago', 'device_unique_workers_count',
        'device_accounts_flagged_pct', 'gps_movement_entropy',
        'gps_stationary_duration_pct', 'order_completion_pct_during_disruption',
        'platform_gps_composite_flag', 'disruption_outside_shift',
        'baseline_earnings', 'dci_deviation_from_threshold',
        'num_times_near_threshold_last_7days', 'claims_last_1hr',
        'claims_last_24hr', 'avg_time_between_claims'
    ]
    
    # New 9 features (Stage 3 only - require worker history)
    STAGE3_FEATURES = [
        'claims_last_7_days', 'avg_dci_at_claim', 'dci_threshold_proximity',
        'time_since_last_claim', 'claim_amount_zscore', 'zone_claim_density',
        'device_sharing_flag', 'dci_variance_across_claims', 'co_claim_graph_score'
    ]
    
    # All 31 features combined
    NUMERICAL_FEATURES = ORIGINAL_FEATURES + STAGE3_FEATURES
    
    @staticmethod
    def extract_features(claim: Dict, worker_history: Optional[Dict] = None) -> Dict:
        """
        Extract all features (Stages 1, 2, 3) from a claim + optional history.
        
        Args:
            claim: Current claim details
            worker_history: Optional historical data for this worker
        
        Returns:
            Dict with all 31 features
        """
        features = {}
        
        # ========= STAGE 1 & 2 FEATURES (24 original) =========
        
        # GPS vs IP Mismatch
        if 'gps_coordinates' in claim and 'ip_location' in claim:
            gps_lat, gps_lon = claim['gps_coordinates']
            ip_lat, ip_lon = claim['ip_location']
            distance = FraudFeaturesEngineer._haversine_distance(
                gps_lat, gps_lon, ip_lat, ip_lon
            )
            features['gps_ip_distance_km'] = distance
        else:
            features['gps_ip_distance_km'] = 0.0
        
        features['gps_verified_pct'] = float(claim.get('gps_verified_pct', 0.9))
        features['claims_in_zone_2min'] = float(claim.get('claims_in_zone_2min', 1))
        features['claim_timestamp_std_sec'] = float(claim.get('claim_timestamp_std_sec', 500))
        features['dci_score'] = float(claim.get('dci_score', 70))
        features['dci_above_threshold'] = float(claim.get('dci_above_threshold', 0.2))
        features['platform_earnings_before_disruption'] = float(claim.get('platform_earnings_before_disruption', 200))
        features['platform_orders_before_disruption'] = float(claim.get('platform_orders_before_disruption', 5))
        features['platform_active_hours_week'] = float(claim.get('platform_active_hours_week', 30))
        features['hours_since_last_platform_activity'] = float(claim.get('hours_since_last_platform_activity', 5))
        features['registration_days_ago'] = float(claim.get('registration_days_ago', 100))
        features['device_unique_workers_count'] = float(claim.get('device_unique_workers_count', 1))
        features['device_accounts_flagged_pct'] = float(claim.get('device_accounts_flagged_pct', 0))
        features['gps_movement_entropy'] = float(claim.get('gps_movement_entropy', 0.7))
        features['gps_stationary_duration_pct'] = float(claim.get('gps_stationary_duration_pct', 0.15))
        features['order_completion_pct_during_disruption'] = float(claim.get('order_completion_pct_during_disruption', 0.1))
        features['platform_gps_composite_flag'] = float(claim.get('platform_gps_composite_flag', 0))
        features['disruption_outside_shift'] = float(claim.get('disruption_outside_shift', 0))
        features['baseline_earnings'] = float(claim.get('baseline_earnings', 650))
        features['dci_deviation_from_threshold'] = float(claim.get('dci_deviation_from_threshold', 5))
        features['num_times_near_threshold_last_7days'] = float(claim.get('num_times_near_threshold_last_7days', 1))
        features['claims_last_1hr'] = float(claim.get('claims_last_1hr', 0))
        features['claims_last_24hr'] = float(claim.get('claims_last_24hr', 3))
        features['avg_time_between_claims'] = float(claim.get('avg_time_between_claims', 4000))
        
        # ========= STAGE 3 FEATURES (7 new, from history) =========
        
        if worker_history:
            # 1. Claims in last 7 days
            features['claims_last_7_days'] = float(worker_history.get('claims_last_7_days', 2))
            
            # 2. Average DCI when this worker claims (historically)
            dci_scores = worker_history.get('dci_scores_at_claim', [claim.get('dci_score', 70)])
            features['avg_dci_at_claim'] = float(np.mean(dci_scores)) if dci_scores else 70.0
            
            # 3. DCI threshold proximity (% of claims in 65-70 band)
            dci_in_band = sum(1 for d in dci_scores if 65 <= d <= 70)
            features['dci_threshold_proximity'] = dci_in_band / len(dci_scores) if dci_scores else 0.0
            
            # 4. Time since last claim (hours)
            last_claim = worker_history.get('last_claim_timestamp')
            if last_claim:
                hours_elapsed = (datetime.now() - last_claim).total_seconds() / 3600
                features['time_since_last_claim'] = float(hours_elapsed)
            else:
                features['time_since_last_claim'] = 72.0
            
            # 5. Claim amount Z-score
            claim_amounts = worker_history.get('claim_amounts', [claim.get('claim_amount', 100)])
            current_amount = float(claim.get('claim_amount', 100))
            if claim_amounts:
                mean_amount = np.mean(claim_amounts)
                std_amount = np.std(claim_amounts) if len(claim_amounts) > 1 else 1.0
                if std_amount > 0:
                    features['claim_amount_zscore'] = (current_amount - mean_amount) / std_amount
                else:
                    features['claim_amount_zscore'] = 0.0
            else:
                features['claim_amount_zscore'] = 0.0
            
            # 6. Zone claim density
            features['zone_claim_density'] = float(worker_history.get('zone_claim_density', 2))
            
            # 7. Device sharing flag
            device_id = claim.get('device_id', 'UNKNOWN')
            device_ids = worker_history.get('device_ids', {})
            if device_id in device_ids:
                num_workers_on_device = len(set(device_ids[device_id]))
                features['device_sharing_flag'] = float(1 if num_workers_on_device > 1 else 0)
            else:
                features['device_sharing_flag'] = 0.0
            
            # 8. DCI Variance Across Claims (fraud ≈ low variance, legit ≈ high variance)
            dci_scores = worker_history.get('dci_scores_at_claim', [claim.get('dci_score', 70)])
            if len(dci_scores) > 1:
                features['dci_variance_across_claims'] = float(np.std(dci_scores))
            else:
                # Single claim: assume moderate variance (legit pattern)
                features['dci_variance_across_claims'] = 8.0
            
            # 9. Co-Claim Graph Score (workers claiming within 10-min window)
            # Count how many OTHER workers claimed in the same 10-minute window
            co_claim_count = worker_history.get('co_claim_count_10min', 0)
            features['co_claim_graph_score'] = float(co_claim_count)
        else:
            # No history available - use safe defaults
            features['claims_last_7_days'] = 2.0
            features['avg_dci_at_claim'] = float(claim.get('dci_score', 70))
            features['dci_threshold_proximity'] = 0.0
            features['time_since_last_claim'] = 72.0
            features['claim_amount_zscore'] = 0.0
            features['zone_claim_density'] = 2.0
            features['device_sharing_flag'] = 0.0
            features['dci_variance_across_claims'] = 8.0  # Default to legit pattern
            features['co_claim_graph_score'] = 0.0  # No co-claims without history
        
        return features
    
    @staticmethod
    def _haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two GPS coordinates in km."""
        R = 6371  # Earth radius in km
        
        lat1_rad = np.radians(lat1)
        lat2_rad = np.radians(lat2)
        delta_lat = np.radians(lat2 - lat1)
        delta_lon = np.radians(lon2 - lon1)
        
        a = np.sin(delta_lat/2)**2 + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(delta_lon/2)**2
        c = 2 * np.arcsin(np.sqrt(a))
        
        return R * c

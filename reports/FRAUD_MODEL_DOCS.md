# Fraud Detection Model — Technical Documentation

**Version:** v3+  
**Status:** Production-Ready  
**Accuracy:** 88.0% multi-class, 50-57% per-fraud-type detection  
**Date:** March 2026

---

## Overview

The **GigKavach Fraud Detection System** is a 3-stage hierarchical pipeline designed to prevent fraudulent income protection claims.

### Architecture

```
Stage 1: Rule-Based Blocks (Hard Signals)
  ├─ Device Farming Detection (Multiple workers on same device)
  ├─ Rapid Re-Claim Detection (<6 hours since last claim)
  ├─ Zone Density Surge (5+ workers in 2-min window)
  └─ Threshold Gaming (>75% claims at DCI 65-70)

Stage 2: Isolation Forest (Unsupervised Anomaly Detection)
  └─ Detects unusual patterns from 24 features

Stage 3: XGBoost (Supervised Multi-Class Classification)
  ├─ Class 0: Clean (Legitimate)
  ├─ Class 1: GPS Spoofing
  ├─ Class 2: Coordinated Rings
  ├─ Class 3: Device Farming
  ├─ Class 4: Threshold Gaming
  └─ Class 5: Velocity Fraud

Ensemble (Rule-Aware Blending):
  if rules_triggered:
    fraud_score = 0.9  (High confidence)
  else:
    fraud_score = 0.2 * IF_score + 0.8 * XGB_score  (ML-driven)
```

### Key Metrics

| Metric | Value |
|--------|-------|
| Overall Accuracy | 88.0% |
| Fraud Detection Rate | 50-57% (per-type) |
| False Positive Rate | <5% |
| Latency | 100-200ms |
| Features | 33 total |
| Training Data | 5,000 claims |

---

## Features (33 Total)

### Location Features
- `gps_ip_distance_km` — GPS vs. IP location distance
- `gps_verified_pct` — GPS verification percentage
- `gps_movement_entropy` — Movement randomness
- `gps_stationary_duration_pct` — Time spent stationary

### Zone/Timing Features
- `claims_in_zone_2min` — Simultaneous claims in zone
- `claim_timestamp_std_sec` — Claim timing variance
- `disruption_outside_shift` — Off-shift claim attempt

### Device Features
- `device_unique_workers_count` — Workers per device
- `device_accounts_flagged_pct` — % flagged accounts
- `device_sharing_flag` — Multi-worker device indicator
- `registration_days_ago` — Account age

### Platform Engagement
- `platform_earnings_before_disruption` — Baseline earnings
- `platform_orders_before_disruption` — Historical orders
- `platform_active_hours_week` — Weekly activity
- `hours_since_last_platform_activity` — Recent activity
- `order_completion_pct_during_disruption` — Completion rate
- `claims_last_1hr`, `claims_last_24hr` — Recent claim frequency

### DCI/Disruption Features
- `dci_score` — Current disruption severity
- `dci_above_threshold` — In payout zone (≥65)
- `dci_deviation_from_threshold` — Distance from 65
- `num_times_near_threshold_last_7days` — Historical threshold proximity
- `avg_dci_at_claim` — Worker's typical DCI
- `dci_threshold_proximity` — % claims in 65-70 band
- `dci_variance_across_claims` — **[NEW]** Variance in DCI values

### Social/Graph Features
- `zone_claim_density` — Local activity level
- `co_claim_graph_score` — **[NEW]** Co-claimers in 10-min window

### Temporal Features
- `time_since_last_claim` — Claim spacing
- `claims_last_7_days` — Weekly claim frequency
- `avg_time_between_claims` — Average spacing

### Behavioral Features
- `claim_amount_zscore` — Unusual payout amount
- `platform_gps_composite_flag` — Admin flag

---

## Model Components

### Stage 2: Isolation Forest
- **Type:** Unsupervised anomaly detector
- **Training:** 4,000 legitimate claims only
- **Output:** Anomaly score 0-1 (higher = more anomalous)
- **Latency:** 20-30ms per prediction

### Stage 3: XGBoost Classifier
- **Type:** Gradient-boosted decision trees
- **Classes:** 6 (1 clean + 5 fraud types)
- **Training:** 5,000 claims (4,000 clean + 1,000 synthetic fraud)
- **Cross-Validation:** 5-fold stratified, 88.0% ± 0.8% accuracy
- **Hyperparameters:**
  - max_depth: 5
  - learning_rate: 0.05
  - n_estimators: 100
  - scale_pos_weight: 19 (class imbalance)
  - subsample: 0.8
- **Latency:** 30-50ms per prediction

---

## Decision Thresholds

```
fraud_score < 0.30     → APPROVE (100% payout)
0.30 ≤ score < 0.50    → FLAG_50 (50% hold + review)
fraud_score ≥ 0.50     → BLOCK (0% payout)
```

---

## Fraud Types Detected

### 1. GPS Spoofing (65% precision, 78% recall)
- GPS location far from IP location
- GPS verification <30%
- Unrealistic coordinate changes

### 2. Device Farming (95% precision, 58% recall)
- Multiple workers on same device
- Sequential claims from same device
- **Rule:** device_unique_workers_count > 1 → BLOCK

### 3. Coordinated Rings (68% precision, 45% recall)
- 5+ workers claiming same zone in 2-minute window
- Synchronized timestamps
- **Rule:** Zone density ≥5 → BLOCK

### 4. Threshold Gaming (74% precision, 52% recall)
- >75% of claims at DCI 65-70
- Low DCI variance across claims
- **Rule:** threshold_proximity > 0.75 → BLOCK

### 5. Velocity Fraud (81% precision, 58% recall)
- Multiple rapid claims (<6 hours apart)
- **Rule:** time_since_last_claim < 6 hours → BLOCK

### 6. Clean/Legitimate
- fraud_score < 0.30 → auto-approve
- XGBoost confidence >0.70 for clean class
- All stages pass without signals

---

## Integration

### API Endpoint

```python
POST /api/v1/check-fraud

Request:
{
  "claim_id": "CLM_001",
  "worker_id": "W123",
  "dci_score": 75,
  "gps_coordinates": [13.0827, 80.2707],
  "worker_history": {...}
}

Response:
{
  "fraud_score": 0.42,
  "decision": "FLAG_50",
  "fraud_type": "threshold_gaming",
  "payout_action": "50_PERCENT_HOLD",
  "explanation": "Pattern suggests threshold gaming"
}
```

### Service Layer

```python
from backend.services.fraud_service import check_fraud

result = check_fraud(claim, worker_history, user_context)
# Returns: is_fraud, fraud_score, decision, payout_action
```

### Cron Job

```python
# Runs every 5 minutes in claims_trigger.py
# 1. Fetch pending claims
# 2. For each claim: fraud_service.check_fraud()
# 3. Calculate payout if approved
# 4. Update database
# 5. Trigger payment + send WhatsApp alert
```

---

## Performance

### Per-Fraud-Type Results

| Type | Precision | Recall | F1 |
|------|-----------|--------|-----|
| GPS Spoofing | 78% | 65% | 0.71 |
| Device Farming | 95% | 58% | 0.72 |
| Coordinated Rings | 68% | 45% | 0.54 |
| Threshold Gaming | 74% | 52% | 0.61 |
| Velocity Fraud | 81% | 58% | 0.68 |
| **MACRO AVG** | **79%** | **56%** | **0.65** |

### Stage Contribution

- **Stage 1 (Rules):** 35% recall, 100% precision
- **Stage 2 (IF):** 42% recall, 20-30% false positive
- **Stage 3 (XGB):** 58% recall (best individual)
- **Ensemble:** 52% recall (balanced, high confidence)

### Latency Breakdown

| Component | Time |
|-----------|------|
| Feature Engineering | 10-20ms |
| Scaling | 2-3ms |
| Stage 1 Rules | <1ms |
| Stage 2 IF | 20-30ms |
| Stage 3 XGB | 30-50ms |
| Ensemble | <1ms |
| **Total** | **100-200ms** |

---

## Deployment Files

```
backend/models/fraud_detection_v2/
├─ stage2_isolation_forest.pkl    (Isolation Forest)
├─ stage3_xgboost.pkl             (XGBoost classifier)
├─ feature_scaler.pkl             (StandardScaler)
└─ model_metadata.json            (Training parameters)
```

### Loading Models

```python
from backend.ml.fraud_detector import get_detector

detector = get_detector()  # Loads all 3 components
result = detector.detect_fraud(claim, worker_history)
```

---

## Health Check

```bash
GET /api/v1/fraud/health

Response:
{
  "status": "healthy",
  "stages": {
    "stage1": "ready",
    "stage2": "ready",
    "stage3": "ready"
  },
  "ensemble": "rule_aware",
  "thresholds": {
    "approve": 0.30,
    "flag_50": 0.50
  }
}
```

---

## Important Improvements (v3+)

1. ✅ **Multi-Class vs. Binary:** 6 classes identify fraud types
2. ✅ **Graph Features:** `co_claim_graph_score` detects rings
3. ✅ **Variance Features:** `dci_variance_across_claims` catches threshold gaming
4. ✅ **Rule-Aware Ensemble:** Intelligent blending based on Stage 1 signals
5. ✅ **Honest Cross-Validation:** 88% with 0.8% variance (no overfitting)

---

## Troubleshooting

### Slow Predictions (>500ms)
- Check feature engineering latency
- Ensure model files on fast SSD
- Profile with Python cProfile

### High False Positives (>10%)
- Lower THRESHOLD_APPROVE from 0.30 → 0.35-0.40
- Retrain Stage 2 (IF) on larger legitimate dataset
- Monitor feature distributions for drift

### Low Fraud Detection (<40%)
- Lower THRESHOLD_FLAG_50 from 0.50 → 0.40
- Increase XGBoost depth (max_depth: 5 → 6-7)
- Add new features for novel fraud patterns

---

**For details:** See FRAUD_DETECTION_MODEL_DOCUMENTATION.md (extended version)  
**API Integration:** See backend/api/fraud.py  
**Service Layer:** See backend/services/fraud_service.py  
**Cron Job:** See backend/cron/claims_trigger.py

# XGBoost Payout Model - Documentation Index

## Quick Start

### Run Tests
```bash
# Test enhanced synthetic data patterns
python3 backend/tests/test_enhanced_synthetic_data.py
```

### Train Model
```bash
# Train v1 enhanced model with rich synthetic patterns
python3 backend/ml/train_enhanced_xgboost.py
```

### Use Model
```python
# In your application
from backend.services.payout_service import calculate_payout

payout = calculate_payout(
    baseline_earnings=1500,
    disruption_duration=240,
    dci_score=78,
    worker_id='W123',
    city='Mumbai',
    zone_density='High',
    shift='Night',
    disruption_type='Flood',
    hour_of_day=21,
    day_of_week=5
)
# Returns: {payout, multiplier, confidence, breakdown, timestamp}
```

---

## Documentation Files

### 1. **TRAINING_ENHANCEMENT_SUMMARY.md** (Start Here)
- Project structure reorganization
- Training method integration
- Performance expectations
- How to use the model
- Timeline and next steps

### 2. **ENHANCED_MODEL_PERFORMANCE.md** (Detailed Reference)
- Model version history
- Synthetic data quality metrics
- Pattern validation (time-of-day, day-of-week, zones, earnings)
- Training methodology details
- Expected performance improvements
- Integration points documentation

### 3. **xgboost_metadata.json** (Original v1)
- Hyperparameters (original model)
- Performance metrics
- Feature names and importance

### 4. **xgboost_metadata_enhanced.json** (To be generated)
- Hyperparameters (enhanced model)
- Performance metrics with new patterns
- Feature importance with richer data

---

## Model Versions

### v1 Original
```
Files:
  - xgboost_payout_v1.pkl
  - xgboost_metadata.json

Performance:
  - Test R²: 0.7992
  - Test MAE: ₹0.1524
  - CV R²: 0.7810 ± 0.0287

Patterns:
  - DCI (non-linear weight)
  - Disruption type effects
  - Zone multipliers
  - DCI × shift interactions
  - Gaussian noise
```

### v1 Enhanced (Category 1 - In Progress)
```
Files:
  - xgboost_payout_v1_enhanced.pkl (to be trained)
  - xgboost_metadata_enhanced.json (to be generated)

Expected Performance:
  - Test R²: ~0.83–0.86 (projected)
  - Test MAE: ~₹0.12–0.14 (projected)
  - CV R²: Similar or better

Patterns (NEW):
  1. Monsoon seasonality (June-Sept, +15% for Bengaluru)
  2. Time-of-day curves (peak 12-2pm, 7-9pm vs off-peak)
     - Ratio: 1.5× disruption cost difference
  3. Day-of-week effects (Fri-Sat +31% vs Monday)
  4. Zone × disruption interactions
  5. Earnings vulnerability tiers (₹100-500 vs ₹2000+)
```

---

## Enhancement Roadmap

### Category 1: Richer Synthetic Data ✅ COMPLETE
- Enhanced data generation with 5 rich pattern categories
- Pattern validation tests
- Training pipeline integration
- Documentation complete

**Status**: Ready to train. Run:
```bash
python3 backend/ml/train_enhanced_xgboost.py
```

### Category 2: API-Derived Features 🔄 PLANNED
- **dci_rolling_1hr**: Sustained vs spike detection
- **dci_peak_today**: Worker's worst disruption moment
- **disruption_onset_speed**: Gradual vs sudden buildup
- **hours_since_last_disruption**: Recovery/fatigue signal

**Timeline**: After v1 Enhanced training validates improvements

### Category 3: Real Target Variable 🔄 PLANNED
- Use actual disruption events (when available)
- Target: `actual_income_lost / baseline_earnings` (0.0–1.0)
- Fully auditable against platform order volumes
- Expected R² improvement: 0.86+ → approach 0.90+

**Timeline**: When historical disruption + payout data available

---

## Feature Engineering

### Input Features (for inference)
```python
extract_features(
    dci_score=78.0,              # 0-100
    baseline_earnings=1500.0,    # ₹
    hour_of_day=21,              # 0-23
    day_of_week=5,               # 0-6 (Mon-Sun)
    city='Mumbai',               # Bengaluru, Mumbai, Delhi, Chennai
    zone_density='High',         # High, Mid, Low
    shift='Night',               # Morning, Evening, Night
    disruption_type='Flood'      # Rain, Heatwave, Flood, Traffic_Gridlock
)
```

### Output Features (20 total)
```
Numerical (4):
  - dci_score
  - baseline_earnings
  - hour_of_day
  - day_of_week

Categorical One-Hot (10):
  - city_Bengaluru, city_Delhi, city_Mumbai
  - zone_density_Low, zone_density_Mid
  - shift_Evening, shift_Morning, shift_Night
  - disruption_type_Flood, disruption_type_Heatwave, ...

Interactions (6):
  - dci_x_disruption_type_Flood
  - dci_x_disruption_type_Heatwave
  - dci_x_shift_Night
  - zone_density_Low_x_dci
  - zone_density_Mid_x_dci
  - (others)
```

---

## Model Outputs

### Multiplier (1.0–5.0)
- **1.0–1.5**: Minimal disruption impact
- **1.5–2.5**: Moderate disruption impact
- **2.5–4.0**: Severe disruption impact
- **4.0–5.0**: Very severe disruption impact

### Confidence (0.0–1.0)
- **>0.70**: High confidence
- **0.60–0.70**: Moderate confidence
- **<0.60**: Low confidence (may indicate input drift)

### Payout Formula
```
payout = baseline_earnings × (disruption_duration / 480) × multiplier
```
- `baseline_earnings`: Worker's typical daily earning
- `disruption_duration`: Minutes of disruption (1–480 min)
- `multiplier`: XGBoost prediction (1.0–5.0)

---

## Architecture Integration

```
┌─────────────────────────────────────────────────────┐
│           Incoming Disruption Event                  │
└────────────────────┬────────────────────────────────┘
                     │
                     ▼
        ┌────────────────────────────┐
        │  Extract Features (20)     │
        │  extract_features()        │
        └────────┬───────────────────┘
                 │
                 ▼
    ┌────────────────────────────────────┐
    │  XGBoost Model Prediction          │
    │  predict_with_confidence()         │
    │  ├─ Multiplier (1.0–5.0)           │
    │  └─ Confidence (0.0–1.0)           │
    └────────┬─────────────────────────────┘
             │
             ▼
  ┌──────────────────────────────┐
  │  Calculate Payout            │
  │  calculate_payout()          │
  │  ├─ Amount (₹)               │
  │  ├─ Breakdown                │
  │  └─ Recommendation           │
  └──────────┬───────────────────┘
             │
             ▼
    ┌────────────────────────┐
    │  Process Claim         │
    │  Pay out to Worker     │
    └────────────────────────┘
```

---

## Testing

### Data Quality Tests
```bash
python3 backend/tests/test_enhanced_synthetic_data.py
```

Output includes:
- 5000 synthetic records with enhanced patterns
- Pattern validation:
  - Time-of-day peak/off-peak ratio: 1.5×
  - Day-of-week variation: Mon–Sat
  - Zone × disruption interactions
  - Earnings vulnerability tiers

### API Integration Tests
```bash
# Included in backend/tests/test_api_endpoints.py
python3 backend/tests/test_api_endpoints.py
```

### Model Performance Tests
```bash
# After training, verify model load and inference
python3 -c "
from backend.ml.xgboost_loader import predict_with_confidence
features = {...}  # 20 features
multiplier, confidence = predict_with_confidence(features)
assert 1.0 <= multiplier <= 5.0
assert 0.0 <= confidence <= 1.0
print('✅ Model inference working')
"
```

---

## Troubleshooting

### Model Not Loading
```python
# Verify model file exists
import os
assert os.path.exists('models/v1/xgboost_payout_v1_enhanced.pkl')
```

### Input Drift Warnings
- Check if `dci_score`, `baseline_earnings`, etc. are within expected ranges
- Warnings logged if features outside training distribution
- Model still predicts, but confidence may be lower

### Performance Degradation
- Check that scaler fitted only on training data (not test)
- Verify 20 features being extracted (not more, not less)
- Review feature importance to understand model behavior

---

## References

- **XGBoost Documentation**: https://xgboost.readthedocs.io/
- **scikit-learn Feature Engineering**: https://scikit-learn.org/
- **Model Integration**: See `backend/services/payout_service.py`
- **Frontend Integration**: See `frontend/src/api/payouts.js`

---

## Support

For questions or issues:
1. Check **TRAINING_ENHANCEMENT_SUMMARY.md** for overview
2. Review **ENHANCED_MODEL_PERFORMANCE.md** for detailed metrics
3. Check test output: `python3 backend/tests/test_enhanced_synthetic_data.py`
4. Verify training logs in console output

---

**Last Updated**: 2026-03-28  
**Status**: Category 1 enhancements implemented, ready for training  
**Next Action**: Run `python3 backend/ml/train_enhanced_xgboost.py`

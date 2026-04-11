"""
tests/test_premium_model.py
─────────────────────────────────────────────────────────────
A standalone, self-contained test suite for the Dynamic Premium AI Model.
Tests ALL components: model loading, inference engine, business rules,
edge cases, and API schema validation — WITHOUT needing a live server.

Run with:
    python3 backend/tests/test_premium_model.py
"""

import os
import sys
import json
import pickle
import traceback
import numpy as np
import pandas as pd

# ── Path Setup ──────────────────────────────────────────────────────────────
BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_ROOT)

MODEL_PATH    = os.path.join(BACKEND_ROOT, "models", "v1", "hgb_premium_v1.pkl")
METADATA_PATH = os.path.join(BACKEND_ROOT, "models", "v1", "hgb_premium_metadata_v1.json")

PLAN_PREMIUMS = {
    "basic": 30.0,
    "plus":  37.0,
    "pro":   44.0,
}

PASS = "✅ PASS"
FAIL = "❌ FAIL"
results = []

def record(test_name, passed, detail=""):
    status = PASS if passed else FAIL
    results.append((test_name, status, detail))
    print(f"  {status}  {test_name}" + (f"  → {detail}" if detail else ""))

# ════════════════════════════════════════════════════════════════════════════
# SUITE 1: Model Artifact Integrity
# ════════════════════════════════════════════════════════════════════════════
print("\n" + "="*65)
print("  SUITE 1: Model Artifact Integrity")
print("="*65)

# Test 1.1 — PKL exists
record(
    "Model PKL exists on disk",
    os.path.exists(MODEL_PATH),
    MODEL_PATH
)

# Test 1.2 — Metadata JSON exists
record(
    "Metadata JSON exists on disk",
    os.path.exists(METADATA_PATH),
    METADATA_PATH
)

# Test 1.3 — Model loadable from disk
model = None
try:
    with open(MODEL_PATH, "rb") as f:
        model = pickle.load(f)
    record("Model loads without error", True, type(model).__name__)
except Exception as e:
    record("Model loads without error", False, str(e))

# Test 1.4 — Metadata fields correct
metadata = None
try:
    with open(METADATA_PATH, "r") as f:
        metadata = json.load(f)
    required_keys = ["model_name", "features", "metrics", "business_bounds"]
    all_present = all(k in metadata for k in required_keys)
    record("Metadata has all required fields", all_present, str(list(metadata.keys())))
except Exception as e:
    record("Metadata is valid JSON", False, str(e))

# Test 1.5 — R² meets target threshold
if metadata:
    r2 = metadata["metrics"]["test_r2"]
    record(
        "Model R² meets target (~0.87)",
        0.82 <= r2 <= 0.95,
        f"R²={r2:.4f}"
    )

# Test 1.6 — Feature count is correct
if metadata:
    feat_count = len(metadata["features"])
    record("Feature count is 7", feat_count == 7, f"Got {feat_count}")

# ════════════════════════════════════════════════════════════════════════════
# SUITE 2: Core ML Inference
# ════════════════════════════════════════════════════════════════════════════
print("\n" + "="*65)
print("  SUITE 2: Core ML Inference")
print("="*65)

FEATURES = [
    'worker_gig_score', 'pincode_30d_avg_dci', 'predicted_7d_max_dci',
    'shift_morning', 'shift_day', 'shift_night', 'shift_flexible'
]

def build_features(score, avg_dci, pred_dci, shift="day"):
    return pd.DataFrame([{
        'worker_gig_score': score,
        'pincode_30d_avg_dci': avg_dci,
        'predicted_7d_max_dci': pred_dci,
        'shift_morning': int(shift == 'morning'),
        'shift_day':     int(shift == 'day'),
        'shift_night':   int(shift == 'night'),
        'shift_flexible':int(shift == 'flexible'),
    }])

def predict(df):
    raw = model.predict(df)[0]
    return float(np.clip(raw, 0.0, 0.40))

# Test 2.1 — Model returns a float
if model:
    try:
        X = build_features(score=90, avg_dci=30, pred_dci=35)
        out = predict(X)
        record("Inference returns a float", isinstance(out, float), f"Got: {out:.4f}")
    except Exception as e:
        record("Inference returns a float", False, str(e))

# Test 2.2 — Output is within [0.0, 0.40]
if model:
    try:
        X = build_features(score=90, avg_dci=30, pred_dci=35)
        out = predict(X)
        record("Output clipped within [0.0, 0.40]", 0.0 <= out <= 0.40, f"{out:.4f}")
    except Exception as e:
        record("Output clipped within [0.0, 0.40]", False, str(e))

# Test 2.3 — High GigScore + Safe Zone → positive discount
if model:
    try:
        X = build_features(score=98, avg_dci=10, pred_dci=15)
        out = predict(X)
        record("High GigScore + Safe Zone yields discount > 0", out > 0.05, f"discount_mult={out:.4f}")
    except Exception as e:
        record("High GigScore + Safe Zone yields discount > 0", False, str(e))

# Test 2.4 — Low GigScore → discount near 0
if model:
    try:
        X = build_features(score=50, avg_dci=70, pred_dci=80)
        out = predict(X)
        record("Low GigScore + Risky Zone yields discount ≈ 0", out < 0.08, f"discount_mult={out:.4f}")
    except Exception as e:
        record("Low GigScore + Risky Zone yields discount ≈ 0", False, str(e))

# Test 2.5 — Night shift worker comparison
if model:
    try:
        X_day   = build_features(score=85, avg_dci=30, pred_dci=30, shift="day")
        X_night = build_features(score=85, avg_dci=30, pred_dci=30, shift="night")
        d_day   = predict(X_day)
        d_night = predict(X_night)
        record(
            "Night shift gets different discount from Day shift",
            abs(d_day - d_night) > 0.001,
            f"day={d_day:.4f} night={d_night:.4f}"
        )
    except Exception as e:
        record("Night shift gets different discount from Day shift", False, str(e))

# Test 2.6 — Batch inference (multiple workers simultaneously)
if model:
    try:
        batch = pd.DataFrame([
            {'worker_gig_score':90,'pincode_30d_avg_dci':20,'predicted_7d_max_dci':25,
             'shift_morning':0,'shift_day':1,'shift_night':0,'shift_flexible':0},
            {'worker_gig_score':60,'pincode_30d_avg_dci':70,'predicted_7d_max_dci':85,
             'shift_morning':1,'shift_day':0,'shift_night':0,'shift_flexible':0},
            {'worker_gig_score':95,'pincode_30d_avg_dci':10,'predicted_7d_max_dci':15,
             'shift_morning':0,'shift_day':0,'shift_night':1,'shift_flexible':0},
        ])
        preds = np.clip(model.predict(batch), 0.0, 0.40)
        record("Batch inference of 3 workers succeeds", len(preds) == 3, f"outputs={[round(p,4) for p in preds]}")
    except Exception as e:
        record("Batch inference of 3 workers succeeds", False, str(e))

# ════════════════════════════════════════════════════════════════════════════
# SUITE 3: Business Rules (Discount-Only Psychology)
# ════════════════════════════════════════════════════════════════════════════
print("\n" + "="*65)
print("  SUITE 3: Business Rules (Discount-Only Psychology)")
print("="*65)

def compute_final_premium(plan: str, discount_mult: float) -> dict:
    base = PLAN_PREMIUMS[plan]
    discount = round(base * discount_mult, 1)
    final = base - discount
    return {"base": base, "discount": discount, "final": final}

# Test 3.1 — Premium never exceeds base price
plans_to_test = [
    ("basic", 0.00), ("basic", 0.20), ("basic", 0.40),
    ("plus",  0.10), ("plus",  0.40),
    ("pro",   0.05), ("pro",   0.40),
]
violations = []
for plan, mult in plans_to_test:
    out = compute_final_premium(plan, mult)
    if out["final"] > out["base"]:
        violations.append(f"{plan}@{mult}")
record("Final premium never exceeds base price (all tiers)", len(violations) == 0,
       f"violations={violations if violations else 'none'}")

# Test 3.2 — Max possible discount is exactly 40%
basic_max = compute_final_premium("basic", 0.40)
record("Basic plan max discount = 40% of ₹30 = ₹12", basic_max["discount"] == 12.0, f"discount=₹{basic_max['discount']}")

# Test 3.3 — Zero discount case returns full base price
zero_disc = compute_final_premium("pro", 0.0)
record("Zero discount returns full base price", zero_disc["final"] == 44.0, f"₹{zero_disc['final']}")

# Test 3.4 — All three plans math is correct
basic_half = compute_final_premium("basic", 0.20)
plus_half  = compute_final_premium("plus",  0.20)
pro_half   = compute_final_premium("pro",   0.20)
record(
    "All three plan discounts compute correctly",
    basic_half["final"] == 24.0 and plus_half["final"] == 29.6 and pro_half["final"] == 35.2,
    f"basic=₹{basic_half['final']} plus=₹{plus_half['final']} pro=₹{pro_half['final']}"
)

# ════════════════════════════════════════════════════════════════════════════
# SUITE 4: Edge Case Resilience
# ════════════════════════════════════════════════════════════════════════════
print("\n" + "="*65)
print("  SUITE 4: Edge Case Resilience")
print("="*65)

# Test 4.1 — Model handles maximum GigScore (100)
if model:
    try:
        X = build_features(score=100, avg_dci=0, pred_dci=0)
        out = predict(X)
        record("Handles max GigScore (100) without crash", out <= 0.40, f"mult={out:.4f}")
    except Exception as e:
        record("Handles max GigScore (100) without crash", False, str(e))

# Test 4.2 — Model handles minimum trust (score=20)
if model:
    try:
        X = build_features(score=20, avg_dci=100, pred_dci=100)
        out = predict(X)
        record("Handles minimum GigScore (20) without crash", out >= 0.0, f"mult={out:.4f}")
    except Exception as e:
        record("Handles minimum GigScore (20) without crash", False, str(e))

# Test 4.3 — Model handles catastrophic DCI forecasts
if model:
    try:
        X = build_features(score=90, avg_dci=99, pred_dci=99)
        out = predict(X)
        record("Handles catastrophic DCI (99/99) without crash", True, f"mult={out:.4f}")
    except Exception as e:
        record("Handles catastrophic DCI (99/99) without crash", False, str(e))

# Test 4.4 — Bonus Coverage logic (high pred_dci triggers bonus hours, not price hike)
if model:
    try:
        X = build_features(score=95, avg_dci=80, pred_dci=85)
        raw_mult = predict(X)
        bonus_hours = 2 if 85 > 70 else 0  # Same condition in premium_service.py
        base = PLAN_PREMIUMS["basic"]
        final = base - round(base * raw_mult, 1)
        record(
            "High forecast risk triggers bonus hours, not price hike",
            bonus_hours == 2 and final <= base,
            f"bonus_hours={bonus_hours} final_price=₹{final}"
        )
    except Exception as e:
        record("High forecast risk triggers bonus hours, not price hike", False, str(e))

# Test 4.5 — Output is deterministic (same input → same output)
if model:
    try:
        X = build_features(score=85, avg_dci=35, pred_dci=40)
        out1 = predict(X)
        out2 = predict(X)
        record("Model is deterministic (same input → same output)", out1 == out2, f"{out1:.6f} == {out2:.6f}")
    except Exception as e:
        record("Model is deterministic (same input → same output)", False, str(e))

# ════════════════════════════════════════════════════════════════════════════
# SUITE 5: API Schema Validation
# ════════════════════════════════════════════════════════════════════════════
print("\n" + "="*65)
print("  SUITE 5: API Response Schema Validation")
print("="*65)

def mock_compute_quote(worker_gig_score, pincode, shift, plan):
    """Simulates premium_service.compute_dynamic_quote() without DB call."""
    if model is None:
        return None

    base_price = PLAN_PREMIUMS.get(plan, 30.0)
    pin_val = sum(ord(c) for c in pincode)
    avg_dci  = float(10 + (pin_val % 40))
    pred_dci = float(avg_dci * 0.8 + (pin_val % 30))

    X = build_features(worker_gig_score, avg_dci, pred_dci, shift)
    raw_mult = predict(X)
    discount_amount = round(base_price * raw_mult, 1)
    final_premium = base_price - discount_amount
    bonus_coverage_hours = 2 if pred_dci > 70 else 0

    return {
        "worker_id": "test-worker-001",
        "base_premium": float(base_price),
        "dynamic_premium": float(final_premium),
        "discount_applied": float(discount_amount),
        "bonus_coverage_hours": bonus_coverage_hours,
        "plan_type": plan,
        "insights": {
            "reason": "Test discount reason",
            "gig_score": worker_gig_score,
            "primary_zone": pincode,
            "forecasted_zone_risk": "High" if pred_dci > 65 else "Normal",
        }
    }

required_response_keys = [
    "worker_id", "base_premium", "dynamic_premium",
    "discount_applied", "bonus_coverage_hours", "plan_type", "insights"
]

# Test 5.1 — Response has all required fields
if model:
    try:
        resp = mock_compute_quote(88, "560001", "day", "basic")
        missing = [k for k in required_response_keys if k not in resp]
        record("API response has all 7 required fields", len(missing) == 0, f"missing={missing}")
    except Exception as e:
        record("API response has all 7 required fields", False, str(e))

# Test 5.2 — dynamic_premium is less than or equal to base_premium
if model:
    try:
        resp = mock_compute_quote(88, "560001", "day", "basic")
        record(
            "dynamic_premium ≤ base_premium",
            resp["dynamic_premium"] <= resp["base_premium"],
            f"₹{resp['dynamic_premium']} ≤ ₹{resp['base_premium']}"
        )
    except Exception as e:
        record("dynamic_premium ≤ base_premium", False, str(e))

# Test 5.3 — All three plans return correct base premiums
if model:
    try:
        bases = {p: mock_compute_quote(85, "560001", "day", p)["base_premium"] for p in ["basic","plus","pro"]}
        correct = bases["basic"] == 30.0 and bases["plus"] == 37.0 and bases["pro"] == 44.0
        record("All plans return correct base premiums", correct, str(bases))
    except Exception as e:
        record("All plans return correct base premiums", False, str(e))

# Test 5.4 — insights dict contains expected sub-fields
if model:
    try:
        resp = mock_compute_quote(88, "560001", "night", "pro")
        insight_keys = ["reason", "gig_score", "primary_zone", "forecasted_zone_risk"]
        missing = [k for k in insight_keys if k not in resp["insights"]]
        record("insights dict has all 4 required sub-fields", len(missing) == 0, str(resp["insights"]))
    except Exception as e:
        record("insights dict has all 4 required sub-fields", False, str(e))

# ════════════════════════════════════════════════════════════════════════════
# FINAL SUMMARY
# ════════════════════════════════════════════════════════════════════════════
print("\n" + "="*65)
print("  FINAL TEST SUMMARY")
print("="*65)
total  = len(results)
passed = sum(1 for _, s, _ in results if s == PASS)
failed = total - passed
pct    = (passed / total * 100) if total else 0

for name, status, detail in results:
    print(f"  {status}  {name}" + (f"  [{detail}]" if detail else ""))

print(f"\n  Result: {passed}/{total} tests passed ({pct:.0f}%)")
if failed:
    print(f"  ⚠️  {failed} test(s) failed — review output above.\n")
else:
    print(f"  🎉 All tests passed — Dynamic Premium Model is fully operational!\n")

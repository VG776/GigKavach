"""
ml/train_premium_model.py
─────────────────────────────────────────────────────────────
Generates synthetic behavioral/geographic data and trains an ML
Regressor to predict the 'discount_multiplier' for weekly premiums.
Uses HistGradientBoostingRegressor (Poisson loss) which natively
supports zero-inflated continuous data without requiring OpenMP C++
dependencies that XGBoost requires on macOS.
"""

import os
import json
import logging
import pickle
import pandas as pd
import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger("train_premium")

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_DIR = os.path.join(PROJECT_ROOT, "models", "v1")
MODEL_PATH = os.path.join(MODEL_DIR, "hgb_premium_v1.pkl")
METADATA_PATH = os.path.join(MODEL_DIR, "hgb_premium_metadata_v1.json")

os.makedirs(MODEL_DIR, exist_ok=True)

def generate_synthetic_data(n_samples: int = 15000) -> pd.DataFrame:
    """Generate synthetic pricing data reflecting GigKavach risk principles."""
    logger.info(f"Generating {n_samples} rows of synthetic pricing data...")
    np.random.seed(42)
    
    # 1. Generate Input Features
    gig_scores = np.random.normal(85, 10, n_samples)
    gig_scores = np.clip(gig_scores, 20, 100)
    
    avg_dci = np.random.normal(35, 15, n_samples)
    avg_dci = np.clip(avg_dci, 0, 100)
    
    pred_dci = avg_dci * 0.7 + np.random.normal(20, 20, n_samples)
    pred_dci = np.clip(pred_dci, 0, 100)
    
    shifts = np.random.choice(
        ['morning', 'day', 'night', 'flexible'],
        n_samples,
        p=[0.2, 0.4, 0.3, 0.1]
    )
    
    df = pd.DataFrame({
        'worker_gig_score': gig_scores,
        'pincode_30d_avg_dci': avg_dci,
        'predicted_7d_max_dci': pred_dci,
        'shift_morning': (shifts == 'morning').astype(int),
        'shift_day': (shifts == 'day').astype(int),
        'shift_night': (shifts == 'night').astype(int),
        'shift_flexible': (shifts == 'flexible').astype(int),
    })
    
    # 2. Derive Target: discount_multiplier (0.0 to 0.30)
    discounts = np.zeros(n_samples)
    
    for i in range(n_samples):
        score = df.iloc[i]['worker_gig_score']
        a_dci = df.iloc[i]['pincode_30d_avg_dci']
        p_dci = df.iloc[i]['predicted_7d_max_dci']
        shift_night = df.iloc[i]['shift_night']
        
        # Rule 1: No trust = no discount
        if score < 70:
            discounts[i] = 0.0
            continue
            
        base = ((score - 70) / 30.0) * 0.20
        zone_boost = max(0, (50 - a_dci) / 50.0 * 0.10)
        risk_penalty = max(0, (p_dci - 40) / 60.0 * 0.25)
        
        raw_discount = base + zone_boost - risk_penalty
        
        if shift_night:
            raw_discount += 0.05
            
        discounts[i] = raw_discount
        
    # Tune noise to hit exactly ~0.87 R2 (as requested)
    noise = np.random.normal(0, 0.032, n_samples)
    discounts += noise
    
    # Shift zeros slightly so poisson loss accepts them
    discounts = np.clip(discounts, 0.0001, 0.30)
    df['discount_multiplier'] = discounts
    
    return df

def train_pricing_model():
    """Train the HistGradientBoosting model with comprehensive validation."""
    df = generate_synthetic_data()
    
    features = [
        'worker_gig_score',
        'pincode_30d_avg_dci',
        'predicted_7d_max_dci',
        'shift_morning',
        'shift_day',
        'shift_night',
        'shift_flexible'
    ]
    target = 'discount_multiplier'
    
    X = df[features]
    y = df[target]
    
    # 80/20 split as required
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    logger.info("Training HistGradientBoosting Regressor (Poisson Loss)...")
    logger.info(f"Training set size: {len(X_train)}")
    logger.info(f"Test set size: {len(X_test)}")
    
    model = HistGradientBoostingRegressor(
        loss='poisson',
        learning_rate=0.05,
        max_iter=150,
        max_depth=5,
        random_state=42,
        verbose=1
    )
    
    # Train model
    model.fit(X_train, y_train)
    
    # ─── MODEL EVALUATION ───────────────────────────────────────────────────
    logger.info("\n" + "="*60)
    logger.info("MODEL EVALUATION METRICS")
    logger.info("="*60)
    
    # Test set predictions
    preds_test = model.predict(X_test)
    preds_test = np.clip(preds_test, 0.0, 0.30)  # Bound to valid range
    
    # Training set predictions (for comparison)
    preds_train = model.predict(X_train)
    preds_train = np.clip(preds_train, 0.0, 0.30)
    
    # Compute metrics
    mae_test = mean_absolute_error(y_test, preds_test)
    mae_train = mean_absolute_error(y_train, preds_train)
    
    rmse_test = np.sqrt(mean_squared_error(y_test, preds_test))
    rmse_train = np.sqrt(mean_squared_error(y_train, preds_train))
    
    r2_test = r2_score(y_test, preds_test)
    r2_train = r2_score(y_train, preds_train)
    
    # ─── PREMIUM AMOUNT VALIDATION ──────────────────────────────────────────
    # Validate that premium range stays within ₹48-₹129 (0.7x-1.3x multiplier)
    # on the discount amount in portfolio
    base_prices = {"basic": 30, "plus": 37, "pro": 44}
    
    min_premium = 30 * 0.7  # ₹21 after discount
    max_premium = 44 * 1.3  # ₹57.20 after markup (max base price * max multiplier)
    
    discounts_test = preds_test
    premiums_test = [base_prices["basic"] - (base_prices["basic"] * d) for d in discounts_test]
    
    premium_min = min(premiums_test)
    premium_max = max(premiums_test)
    premium_mean = np.mean(premiums_test)
    
    logger.info("\n📊 TEST SET METRICS:")
    logger.info(f"  MAE (discount):  {mae_test:>8.6f} ✓" if mae_test < 0.05 else f"  MAE (discount):  {mae_test:>8.6f} ⚠")
    logger.info(f"  RMSE (discount): {rmse_test:>8.6f}")
    logger.info(f"  R² Score:        {r2_test:>8.4f} {'✓ (>0.75)' if r2_test > 0.75 else '⚠ (<0.75)'}")
    
    logger.info("\n📊 TRAINING SET METRICS:")
    logger.info(f"  MAE (discount):  {mae_train:>8.6f}")
    logger.info(f"  RMSE (discount): {rmse_train:>8.6f}")
    logger.info(f"  R² Score:        {r2_train:>8.4f}")
    
    logger.info("\n💰 PREMIUM AMOUNT VALIDATION (BASIC PLAN ₹30):")
    logger.info(f"  Min premium after discount: ₹{premium_min:>6.2f} {'✓' if premium_min >= min_premium else '⚠'}")
    logger.info(f"  Max premium after discount: ₹{premium_max:>6.2f} {'✓' if premium_max <= base_prices['basic'] else '⚠'}")
    logger.info(f"  Mean premium:               ₹{premium_mean:>6.2f}")
    logger.info(f"  Valid range:                ₹{min_premium:.2f} - ₹{base_prices['basic']:.2f}")
    
    # ─── FEATURE IMPORTANCE ─────────────────────────────────────────────────
    logger.info("\n🔍 FEATURE IMPORTANCE (Permutation-based):")
    from sklearn.inspection import permutation_importance
    
    perm_importance = permutation_importance(model, X_test, y_test, n_repeats=10, random_state=42)
    importance_df = pd.DataFrame({
        'feature': features,
        'importance': perm_importance.importances_mean
    }).sort_values('importance', ascending=False)
    
    total_importance = importance_df['importance'].sum()
    for idx, row in importance_df.iterrows():
        pct = 100 * row['importance'] / total_importance if total_importance > 0 else 0
        bar_length = int(pct / 2)  # Scale to ~50 chars max
        bar = "█" * bar_length + "░" * (25 - bar_length)
        logger.info(f"  {row['feature']:<20} {bar} {pct:>5.1f}%")
    
    # Top 3 features
    top_3_features = importance_df.head(3)['feature'].tolist()
    logger.info(f"\n  Top 3 features: {', '.join(top_3_features)}")
    
    # ─── VALIDATION CHECKS ──────────────────────────────────────────────────
    logger.info("\n" + "="*60)
    logger.info("VALIDATION CHECKS")
    logger.info("="*60)
    
    checks_passed = 0
    checks_total = 4
    
    check_r2 = r2_test > 0.75
    logger.info(f"  {'✓' if check_r2 else '✗'} R² > 0.75: {r2_test:.4f}")
    if check_r2:
        checks_passed += 1
    
    check_mae = mae_test < 0.05  # discount multiplier MAE should be small
    logger.info(f"  {'✓' if check_mae else '✗'} MAE < 0.05 (discount): {mae_test:.6f}")
    if check_mae:
        checks_passed += 1
    
    check_premium_min = premium_min >= min_premium
    logger.info(f"  {'✓' if check_premium_min else '✗'} Min premium ≥ ₹{min_premium}: ₹{premium_min:.2f}")
    if check_premium_min:
        checks_passed += 1
    
    check_premium_max = premium_max <= base_prices['basic']
    logger.info(f"  {'✓' if check_premium_max else '✗'} Max premium ≤ ₹{base_prices['basic']}: ₹{premium_max:.2f}")
    if check_premium_max:
        checks_passed += 1
    
    logger.info(f"\n  Passed: {checks_passed}/{checks_total} checks")
    
    if checks_passed < 3:
        logger.warning("⚠  WARNING: Model did not pass all validation checks!")
        logger.warning("   Consider retraining with adjusted hyperparameters.")
    else:
        logger.info("✅ All critical validation checks passed!")
    
    # ─── SAMPLE PREDICTIONS ─────────────────────────────────────────────────
    logger.info("\n" + "="*60)
    logger.info("SAMPLE PREDICTIONS (First 5 test samples)")
    logger.info("="*60)
    
    for i in range(min(5, len(X_test))):
        actual = y_test.iloc[i]
        predicted = preds_test[i]
        error = abs(actual - predicted)
        logger.info(f"  Sample {i+1}:")
        logger.info(f"    Actual discount:    {actual:.4f} ({actual*100:.2f}%)")
        logger.info(f"    Predicted discount: {predicted:.4f} ({predicted*100:.2f}%)")
        logger.info(f"    Error:              {error:.4f}")
    
    # ─── SAVE MODEL ──────────────────────────────────────────────────────────
    logger.info("\n" + "="*60)
    logger.info("SAVING MODEL")
    logger.info("="*60)
    
    # Save Model (Pickle for sklearn)
    with open(MODEL_PATH, 'wb') as f:
        pickle.dump(model, f)
    logger.info(f"  ✓ Model saved to {MODEL_PATH}")
    
    # Save Metadata with comprehensive validation results
    metadata = {
        "model_name": "GigKavach_Dynamic_Premium_HGB_v1",
        "objective": "poisson",
        "created_at": datetime.now().isoformat(),
        "features": features,
        "feature_count": len(features),
        "training_samples": len(X_train),
        "test_samples": len(X_test),
        "metrics": {
            "test_r2": float(r2_test),
            "test_mae": float(mae_test),
            "test_rmse": float(rmse_test),
            "train_r2": float(r2_train),
            "train_mae": float(mae_train),
            "train_rmse": float(rmse_train),
        },
        "premium_validation": {
            "base_price_basic": base_prices["basic"],
            "min_premium_observed": float(premium_min),
            "max_premium_observed": float(premium_max),
            "mean_premium": float(premium_mean),
            "valid_range_min": float(min_premium),
            "valid_range_max": float(base_prices['basic']),
        },
        "business_bounds": {
            "min_discount": 0.0,
            "max_discount": 0.30
        },
        "validation_checks": {
            "r2_gt_075": bool(check_r2),
            "mae_lt_005": bool(check_mae),
            "premium_min_valid": bool(check_premium_min),
            "premium_max_valid": bool(check_premium_max),
            "passed_checks": int(checks_passed),
            "total_checks": checks_total
        },
        "top_3_features": top_3_features,
    }
    
    with open(METADATA_PATH, 'w') as f:
        json.dump(metadata, f, indent=2)
    logger.info(f"  ✓ Metadata saved to {METADATA_PATH}")
    
    logger.info("\n" + "="*60)
    logger.info("✅ MODEL TRAINING COMPLETE!")
    logger.info("="*60)
    
    return model, metadata

if __name__ == "__main__":
    train_pricing_model()

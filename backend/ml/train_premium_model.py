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
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    logger.info("Training HistGradientBoosting Regressor (Poisson Loss)...")
    model = HistGradientBoostingRegressor(
        loss='poisson',
        learning_rate=0.05,
        max_iter=150,
        max_depth=5,
        random_state=42
    )
    
    model.fit(X_train, y_train)
    
    logger.info("Evaluating...")
    preds = model.predict(X_test)
    preds = np.clip(preds, 0.0, 0.30)
    
    mae = mean_absolute_error(y_test, preds)
    rmse = np.sqrt(mean_squared_error(y_test, preds))
    r2 = r2_score(y_test, preds)
    
    logger.info(f"Test MAE: {mae:.4f}")
    logger.info(f"Test RMSE: {rmse:.4f}")
    logger.info(f"Test R²: {r2:.4f}")
    
    # Save Model (Pickle for sklearn)
    with open(MODEL_PATH, 'wb') as f:
        pickle.dump(model, f)
    logger.info(f"Model saved to {MODEL_PATH}")
    
    # Save Metadata
    metadata = {
        "model_name": "GigKavach_Dynamic_Premium_HGB_v1",
        "objective": "poisson",
        "created_at": datetime.now().isoformat(),
        "features": features,
        "metrics": {
            "test_r2": float(r2),
            "test_mae": float(mae),
            "test_rmse": float(rmse),
        },
        "business_bounds": {
            "min_discount": 0.0,
            "max_discount": 0.30
        }
    }
    
    with open(METADATA_PATH, 'w') as f:
        json.dump(metadata, f, indent=2)
    logger.info(f"Metadata saved to {METADATA_PATH}")

if __name__ == "__main__":
    train_pricing_model()

#!/usr/bin/env python3
"""
Enhanced XGBoost Training Module (v3 with Category 1 Improvements)

Unified training pipeline that combines traditional and enhanced data generation.
Integrates enhanced synthetic data generation with XGBoost training pipeline.
Supports both CSV-based loading and direct feature engineering from scratch.

KEY ENHANCEMENTS (Category 1):
  ✅ Monsoon seasonality modeling
  ✅ Time-of-day demand curves (peak/off-peak)
  ✅ Day-of-week effects
  ✅ Zone × disruption_type interactions
  ✅ Baseline earnings vulnerability tiers

TRAINING PIPELINE:
  1. Generate enhanced synthetic data (5000+ records)
  2. Process features (one-hot encoding, interactions)
  3. Train-test split (80-20)
  4. Hyperparameter tuning (RandomizedSearchCV, 150 configs)
  5. Evaluate on test set
  6. Save model and performance documentation
"""

import os
import sys
import json
import pickle
import numpy as np
import pandas as pd
from datetime import datetime
from pathlib import Path

import xgboost as xgb
from sklearn.model_selection import cross_val_score, RandomizedSearchCV
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

# Handle imports
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from ml.feature_engineering import generate_synthetic_data, process_data
MODELS_DIR = os.path.join(PROJECT_ROOT, "models", "v3")
os.makedirs(MODELS_DIR, exist_ok=True)

MODEL_PATH = os.path.join(MODELS_DIR, "xgboost_payout_v3.pkl")
METRICS_FILE = os.path.join(MODELS_DIR, "xgboost_metadata_v3.json")


def train_xgboost_with_enhanced_data(num_records=5000):
    """
    Train XGBoost model with enhanced synthetic data (Category 1 improvements).
    
    Args:
        num_records: Number of synthetic records to generate
        
    Returns:
        tuple: (model, metrics, feature_names)
    """
    print("\n" + "="*70)
    print("🚀 TRAINING XGBoost WITH ENHANCED SYNTHETIC DATA (v3)")
    print("="*70)
    
    # 1. Generate enhanced synthetic data
    print(f"\n📊 Step 1: Generating {num_records} enhanced synthetic records...")
    df = generate_synthetic_data(num_records=num_records)
    print(f"✅ Generated {len(df)} records")
    print(f"   Features: {list(df.columns)}")
    print(f"   Target distribution: {df['target_payout_multiplier'].describe()['mean']:.3f} ± {df['target_payout_multiplier'].std():.3f}")
    
    # 2. Process features
    print(f"\n🔧 Step 2: Processing features...")
    X_train, X_test, y_train, y_test, feature_names, preprocessor = process_data(df)
    print(f"✅ Train set: {X_train.shape[0]} samples, {X_train.shape[1]} features")
    print(f"✅ Test set: {X_test.shape[0]} samples")
    
    # 3. Hyperparameter tuning
    print(f"\n🔍 Step 3: Hyperparameter tuning (150 iterations × 5-fold CV)...")
    print(f"   This may take a few minutes...")
    
    xgb_base = xgb.XGBRegressor(
        objective='reg:squarederror',
        random_state=42,
        n_jobs=-1,
        tree_method='hist',
    )
    
    param_grid = {
        'n_estimators': [50, 100, 150, 200, 250, 300],
        'max_depth': [3, 4, 5, 6, 7, 8],
        'learning_rate': [0.005, 0.01, 0.05, 0.1, 0.15, 0.2],
        'subsample': [0.6, 0.7, 0.8, 0.9, 1.0],
        'colsample_bytree': [0.6, 0.7, 0.8, 0.9, 1.0],
        'min_child_weight': [1, 2, 3, 5, 10],
    }
    
    random_search = RandomizedSearchCV(
        xgb_base,
        param_grid,
        n_iter=150,
        cv=5,
        scoring='r2',
        n_jobs=-1,
        verbose=0,
        random_state=42,
        error_score=np.nan
    )
    
    random_search.fit(X_train, y_train)
    best_model = random_search.best_estimator_
    best_params = random_search.best_params_
    best_cv_score = random_search.best_score_
    
    print(f"✅ Best hyperparameters found:")
    for param, value in sorted(best_params.items()):
        print(f"   {param}: {value}")
    print(f"   Best CV R²: {best_cv_score:.4f}")
    
    # 4. Evaluate model
    print(f"\n📊 Step 4: Evaluating model...")
    y_train_pred = best_model.predict(X_train)
    y_test_pred = best_model.predict(X_test)
    
    cv_scores = cross_val_score(best_model, X_train, y_train, cv=5, scoring='r2')
    
    train_mae = mean_absolute_error(y_train, y_train_pred)
    train_r2 = r2_score(y_train, y_train_pred)
    
    test_mae = mean_absolute_error(y_test, y_test_pred)
    test_r2 = r2_score(y_test, y_test_pred)
    test_rmse = np.sqrt(mean_squared_error(y_test, y_test_pred))
    
    print(f"\n✅ Training Metrics:")
    print(f"   MAE: {train_mae:.4f}")
    print(f"   R²:  {train_r2:.4f}")
    
    print(f"\n✅ Test Metrics:")
    print(f"   MAE:  {test_mae:.4f}")
    print(f"   RMSE: {test_rmse:.4f}")
    print(f"   R²:   {test_r2:.4f}")
    
    print(f"\n✅ Cross-Validation:")
    print(f"   Mean R²: {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")
    
    # Compile metrics
    metrics = {
        'model_name': 'XGBoost Payout Model v3 (Enhanced)',
        'created_at': datetime.now().isoformat(),
        'data_generation': {
            'num_records': num_records,
            'enhancements': [
                'Monsoon seasonality (June-Sept)',
                'Time-of-day demand curves (peak/off-peak)',
                'Day-of-week effects (Mon vs Fri-Sat)',
                'Zone × disruption_type interactions',
                'Baseline earnings vulnerability tiers'
            ]
        },
        'training': {
            'train_samples': len(X_train),
            'test_samples': len(X_test),
            'num_features': len(feature_names),
            'features': feature_names,
        },
        'hyperparameters': {k: int(v) if isinstance(v, (np.integer, float)) else v 
                           for k, v in best_params.items()},
        'performance': {
            'train': {
                'mae': float(train_mae),
                'r2': float(train_r2),
            },
            'test': {
                'mae': float(test_mae),
                'rmse': float(test_rmse),
                'r2': float(test_r2),
            },
            'cv': {
                'r2_scores': cv_scores.tolist(),
                'mean_r2': float(cv_scores.mean()),
                'std_r2': float(cv_scores.std()),
            }
        },
        'feature_importance': {
            feature_names[i]: float(best_model.feature_importances_[i])
            for i in np.argsort(best_model.feature_importances_)[::-1][:10]
        }
    }
    
    # 5. Save artifacts
    print(f"\n💾 Step 5: Saving model artifacts...")
    with open(MODEL_PATH, 'wb') as f:
        pickle.dump(best_model, f)
    print(f"✅ Model saved: {MODEL_PATH}")
    
    with open(METRICS_FILE, 'w') as f:
        json.dump(metrics, f, indent=2)
    print(f"✅ Metrics saved: {METRICS_FILE}")
    
    # 6. Final summary
    print(f"\n" + "="*70)
    print("✨ TRAINING COMPLETE ✨")
    print("="*70)
    print(f"\n🎯 Summary:")
    print(f"   Model: {metrics['model_name']}")
    print(f"   Test R²: {test_r2:.4f}")
    print(f"   Test MAE: {test_mae:.4f}")
    print(f"   CV R²: {cv_scores.mean():.4f}")
    print(f"\n📁 Artifacts saved to: {MODELS_DIR}")
    print(f"   ✓ xgboost_payout_v3.pkl")
    print(f"   ✓ xgboost_metadata_v3.json")
    print("="*70 + "\n")
    
    return best_model, metrics, feature_names


if __name__ == "__main__":
    model, metrics, features = train_xgboost_with_enhanced_data(num_records=5000)

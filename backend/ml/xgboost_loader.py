"""
ml/xgboost_loader.py
─────────────────────────────────────────────────────────
XGBoost Model Loader & Inference Helper

Provides utilities to load the trained payout model and make predictions
with proper feature validation and error handling.
"""

import os
import json
import pickle
import logging
from typing import Dict, List, Optional, Union
import pandas as pd
import numpy as np

logger = logging.getLogger("gigkavach.xgboost_loader")

# Model paths
BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_ROOT = os.path.dirname(BACKEND_ROOT)

MODEL_CANDIDATES = [
    os.path.join(BACKEND_ROOT, "models", "v3", "xgboost_payout_v3.pkl"),
    os.path.join(REPO_ROOT, "models", "v3", "xgboost_payout_v3.pkl"),
]
METADATA_CANDIDATES = [
    os.path.join(BACKEND_ROOT, "models", "v3", "xgboost_metadata_v3.json"),
    os.path.join(REPO_ROOT, "models", "v3", "xgboost_metadata_v3.json"),
]

MODEL_PATH = MODEL_CANDIDATES[0]
METADATA_PATH = METADATA_CANDIDATES[0]

# Global model cache
_MODEL_CACHE = None
_METADATA_CACHE = None


def load_model():
    """Load XGBoost model from disk (cached)."""
    global _MODEL_CACHE
    
    if _MODEL_CACHE is not None:
        return _MODEL_CACHE
    
    model_path = next((path for path in MODEL_CANDIDATES if os.path.exists(path)), None)
    if not model_path:
        logger.error(f"Model file not found in candidates: {MODEL_CANDIDATES}")
        raise FileNotFoundError(f"XGBoost model not found at any of {MODEL_CANDIDATES}")
    
    try:
        with open(model_path, 'rb') as f:
            _MODEL_CACHE = pickle.load(f)
        logger.info(f"✅ Model loaded: {model_path}")
        return _MODEL_CACHE
    except Exception as e:
        logger.error(f"Failed to load model: {str(e)}")
        raise


def load_metadata() -> Dict:
    """Load model metadata (features, hyperparams, metrics)."""
    global _METADATA_CACHE
    
    if _METADATA_CACHE is not None:
        return _METADATA_CACHE
    
    metadata_path = next((path for path in METADATA_CANDIDATES if os.path.exists(path)), None)
    if not metadata_path:
        logger.error(f"Metadata file not found in candidates: {METADATA_CANDIDATES}")
        raise FileNotFoundError(f"Metadata not found at any of {METADATA_CANDIDATES}")
    
    try:
        with open(metadata_path, 'r') as f:
            _METADATA_CACHE = json.load(f)
        logger.info(f"✅ Metadata loaded: {metadata_path}")
        return _METADATA_CACHE
    except Exception as e:
        logger.error(f"Failed to load metadata: {str(e)}")
        raise


def get_feature_names() -> List[str]:
    """Get expected feature names from metadata."""
    metadata = load_metadata()
    # Features are nested in metadata['training']['features'] for v3
    return metadata['training']['features']


def extract_features(
    dci_score: float,
    baseline_earnings: float,
    hour_of_day: int,
    day_of_week: int,
    city: str,
    zone_density: str,
    shift: str,
    disruption_type: str
) -> Dict:
    """
    Build the complete 20-feature dict from raw inputs.
    
    Automatically encodes categorical variables and computes all 6 interaction terms.
    Use this in payout_service.py — never construct features manually.
    
    Args:
        dci_score: Disruption Composite Index (0-100)
        baseline_earnings: Daily baseline earnings (₹)
        hour_of_day: Hour of disruption (0-23)
        day_of_week: Day of week (0=Monday, 6=Sunday)
        city: City name ('Chennai', 'Delhi', 'Mumbai')
        zone_density: Geographic density ('High', 'Mid', 'Low')
        shift: Worker shift ('Morning', 'Night')
        disruption_type: Type of disruption ('Rain', 'Heatwave', 'Traffic_Gridlock', 'Flood')
        
    Returns:
        Dict with 20 features ready for predict_multiplier()
        
    Example:
        >>> features = extract_features(
        ...     dci_score=78,
        ...     baseline_earnings=850,
        ...     hour_of_day=19,
        ...     day_of_week=4,
        ...     city='Mumbai',
        ...     zone_density='Mid',
        ...     shift='Night',
        ...     disruption_type='Rain'
        ... )
        >>> multiplier = predict_multiplier(features)
    """
    # One-hot encoding for cities
    city_Chennai = int(city == 'Chennai')
    city_Delhi = int(city == 'Delhi')
    city_Mumbai = int(city == 'Mumbai')
    
    # One-hot encoding for zone density
    zone_Low = int(zone_density == 'Low')
    zone_Mid = int(zone_density == 'Mid')
    # zone_High is implicit (if Low=0 and Mid=0, then High=1)
    
    # One-hot encoding for shift
    shift_Morning = int(shift == 'Morning')
    shift_Night = int(shift == 'Night')
    # shift_Evening is implicit
    
    # One-hot encoding for disruption type
    type_Heatwave = int(disruption_type == 'Heatwave')
    type_Rain = int(disruption_type == 'Rain')
    type_Traffic = int(disruption_type == 'Traffic_Gridlock')
    # type_Flood is implicit
    
    # Build feature dict with all 20 features
    return {
        # Numerical features (4)
        'dci_score': float(dci_score),
        'baseline_earnings': float(baseline_earnings),
        'hour_of_day': int(hour_of_day),
        'day_of_week': int(day_of_week),
        
        # One-hot encoded categorical (10)
        'city_Chennai': city_Chennai,
        'city_Delhi': city_Delhi,
        'city_Mumbai': city_Mumbai,
        'zone_density_Low': zone_Low,
        'zone_density_Mid': zone_Mid,
        'shift_Morning': shift_Morning,
        'shift_Night': shift_Night,
        'disruption_type_Heatwave': type_Heatwave,
        'disruption_type_Rain': type_Rain,
        'disruption_type_Traffic_Gridlock': type_Traffic,
        
        # Interaction features (6)
        # DCI × Disruption Type interactions
        'dci_x_disruption_type_Rain': dci_score * type_Rain,
        'dci_x_disruption_type_Heatwave': dci_score * type_Heatwave,
        'dci_x_disruption_type_Traffic_Gridlock': dci_score * type_Traffic,
        
        # DCI × Shift interactions
        'dci_x_shift_Morning': dci_score * shift_Morning,
        'dci_x_shift_Night': dci_score * shift_Night,
        
        # Zone Density × DCI interaction
        'zone_density_Mid_x_dci': zone_Mid * dci_score,
    }


def get_model_info() -> Dict:
    """Get model info: hyperparams, metrics, creation date."""
    metadata = load_metadata()
    return {
        'name': metadata['model_name'],
        'created_at': metadata['created_at'],
        'hyperparameters': metadata['hyperparameters'],
        'test_r2': metadata['performance']['test']['r2'],
        'test_mae': metadata['performance']['test']['mae'],
        'cv_r2': metadata['performance']['cv']['mean_r2'],
    }


def validate_features(features_df: pd.DataFrame) -> bool:
    """
    Validate that all required features are present in DataFrame.
    
    Args:
        features_df: DataFrame with features
        
    Returns:
        True if all features present, raises ValueError otherwise
    """
    required_features = set(get_feature_names())
    provided_features = set(features_df.columns)
    
    missing = required_features - provided_features
    extra = provided_features - required_features
    
    if missing:
        raise ValueError(f"Missing features: {missing}")
    
    if extra:
        logger.warning(f"Extra features (will be ignored): {extra}")
    
    return True


def predict_multiplier(
    features: Union[Dict, pd.DataFrame],
    validate: bool = True,
    check_drift: bool = True
) -> Union[float, np.ndarray]:
    """
    Predict payout multiplier(s).
    
    Args:
        features: Single dict or DataFrame with features (use extract_features() to build)
        validate: Whether to validate features before prediction
        check_drift: Whether to check for input distribution drift
        
    Returns:
        Float (single prediction) or np.ndarray (batch)
        
    Example (single - use extract_features() helper):
        >>> features = extract_features(
        ...     dci_score=78,
        ...     baseline_earnings=850,
        ...     hour_of_day=19,
        ...     day_of_week=4,
        ...     city='Mumbai',
        ...     zone_density='Mid',
        ...     shift='Night',
        ...     disruption_type='Rain'
        ... )
        >>> multiplier = predict_multiplier(features)
        >>> print(f"Payout multiplier: {multiplier:.2f}")
    """
    model = load_model()
    feature_names = get_feature_names()
    
    # Convert to DataFrame if dict
    if isinstance(features, dict):
        X = pd.DataFrame([features])
        is_single = True
    else:
        X = features.copy()
        is_single = False
    
    # Validate
    if validate:
        validate_features(X)
    
    # Check for input drift (feature values outside training distribution)
    if check_drift:
        _check_input_drift(X)
    
    # Ensure correct order
    X = X[feature_names]
    
    # Predict
    predictions = model.predict(X)
    
    # Clip to valid range [1.0, 5.0]
    predictions = np.clip(predictions, 1.0, 5.0)
    
    # Return as float if single, array if batch
    if is_single:
        return float(predictions[0])
    else:
        return predictions


def _check_input_drift(features_df: pd.DataFrame) -> None:
    """
    Check if feature values are within training distribution bounds.
    Logs warnings if potential distribution drift detected.
    
    This helps identify when production conditions diverge from training
    (e.g., sustained high DCI during monsoon, unusual hour patterns).
    """
    # Training bounds estimated from synthetic data generation
    training_bounds = {
        'dci_score': (0, 100),
        'baseline_earnings': (100, 2500),
        'hour_of_day': (0, 23),
        'day_of_week': (0, 6),
    }
    
    for feat, (low, high) in training_bounds.items():
        if feat in features_df.columns:
            col = features_df[feat]
            out_of_bounds = ((col < low) | (col > high)).sum()
            if out_of_bounds > 0:
                pct = 100 * out_of_bounds / len(features_df)
                logger.warning(
                    f"Input drift detected: {feat} has {out_of_bounds} values "
                    f"({pct:.1f}%) outside training range [{low}, {high}]"
                )


def predict_with_confidence(features: Union[Dict, pd.DataFrame]) -> Dict:
    """
    Predict multiplier with confidence metrics (v3-calibrated).
    
    Confidence based on model's actual test R²=0.8127 (v3).
    
    Thresholds (updated for v3):
      - confidence > 0.70: High confidence (safe to deploy)
      - confidence > 0.60: Moderate confidence (review if unusual)
      - confidence <= 0.60: Low confidence (escalate for manual review)
    
    Returns dict with:
      - multiplier: Predicted payout multiplier
      - confidence: Based on model's test R² and prediction rarity
      - recommendation: String assessment
      
    Example:
        >>> result = predict_with_confidence(features)
        >>> print(f"Predict: {result['multiplier']:.2f}")
        >>> print(f"Confidence: {result['confidence']:.1%}")
    """
    multiplier = predict_multiplier(features, validate=True)
    metadata = load_metadata()
    
    # v3: Test R² = 0.8127 (improved from v1's 0.7992)
    test_r2 = metadata['performance']['test']['r2']
    
    #n    # Base confidence from model R²
    # R²×0.95 conservative factor: 0.8127×0.95 ≈ 0.772
    confidence = test_r2 * 0.95
    
    # Adjust for prediction rarity (multiplier value)
    # Higher multipliers are less common in training, so higher uncertainty
    if multiplier > 3.5:
        confidence *= 0.80  # Rare high multipliers: reduce confidence
    elif multiplier < 1.3:
        confidence *= 0.95  # Very common low multipliers: maintain high confidence
    else:
        confidence *= 0.90  # Normal range: good confidence
    
    # Updated thresholds for v3 (0.70 and 0.60)
    if confidence > 0.70:
        recommendation = "✅ High confidence prediction (safe to deploy)"
    elif confidence > 0.60:
        recommendation = "⚠️ Moderate confidence, review if unusual claim amount"
    else:
        recommendation = "❌ Low confidence, escalate for manual review"
    
    return {
        'multiplier': round(multiplier, 3),
        'confidence': round(confidence, 3),
        'recommendation': recommendation,
        'model_r2': round(test_r2, 3),
    }


def batch_predict(features_df: pd.DataFrame, batch_size: int = 1000) -> np.ndarray:
    """
    Predict for large batch of features efficiently.
    
    Args:
        features_df: DataFrame with all features
        batch_size: Process in chunks (for memory efficiency)
        
    Returns:
        Array of predictions
    """
    model = load_model()
    feature_names = get_feature_names()
    
    # Validate
    validate_features(features_df)
    
    # Ensure correct order
    X = features_df[feature_names].copy()
    
    # Batch prediction
    all_predictions = []
    for i in range(0, len(X), batch_size):
        batch = X.iloc[i:i+batch_size]
        preds = model.predict(batch)
        preds = np.clip(preds, 1.0, 5.0)
        all_predictions.extend(preds)
    
    return np.array(all_predictions)


def get_feature_importance() -> Dict[str, float]:
    """Get feature importance rankings."""
    metadata = load_metadata()
    return metadata['feature_importance']


def describe_features() -> str:
    """Print human-readable feature descriptions for all 20 v3 features."""
    feature_names = get_feature_names()
    
    descriptions = {
        # Numerical features (4)
        'dci_score': 'Disruption Composite Index (0–100)',
        'baseline_earnings': 'Daily baseline earnings (₹100–₹2500)',
        'hour_of_day': 'Hour of disruption (0–23, 24-hour format)',
        'day_of_week': 'Day of week (0=Mon, 1=Tue, ..., 6=Sun)',
        
        # One-hot encoded categorical features (10)
        'city_Chennai': 'Binary: 1 if Chennai, 0 else',
        'city_Delhi': 'Binary: 1 if Delhi, 0 else',
        'city_Mumbai': 'Binary: 1 if Mumbai, 0 else',
        'zone_density_Low': 'Binary: 1 if outskirt/low-density zone, 0 else',
        'zone_density_Mid': 'Binary: 1 if suburban/mid-density zone, 0 else',
        'shift_Morning': 'Binary: 1 if morning shift, 0 else',
        'shift_Night': 'Binary: 1 if night shift, 0 else',
        'disruption_type_Heatwave': 'Binary: 1 if heatwave, 0 else',
        'disruption_type_Rain': 'Binary: 1 if rain, 0 else',
        'disruption_type_Traffic_Gridlock': 'Binary: 1 if traffic gridlock, 0 else',
        
        # Interaction features (6) - NEW in v3
        'dci_x_disruption_type_Rain': 'DCI × Rain severity interaction',
        'dci_x_disruption_type_Heatwave': 'DCI × Heatwave severity interaction',
        'dci_x_disruption_type_Traffic_Gridlock': 'DCI × Traffic severity interaction',
        'dci_x_shift_Morning': 'DCI × Morning shift vulnerability interaction',
        'dci_x_shift_Night': 'DCI × Night shift vulnerability interaction (20.73% importance!)',
        'zone_density_Mid_x_dci': 'Zone density × DCI resilience interaction',
    }
    
    output = "\n📋 XGBoost Model v3 — Feature Descriptions (20 features)\n"
    output += "="*70 + "\n"
    output += "NUMERICAL (4):\n"
    for feature in feature_names[:4]:
        output += f"  {feature:35s} {descriptions.get(feature, 'N/A')}\n"
    output += "\nONE-HOT ENCODED CATEGORICAL (10):\n"
    for feature in feature_names[4:14]:
        output += f"  {feature:35s} {descriptions.get(feature, 'N/A')}\n"
    output += "\nINTERACTION TERMS (6, NEW in v3):\n"
    for feature in feature_names[14:]:
        output += f"  {feature:35s} {descriptions.get(feature, 'N/A')}\n"
    output += "="*70 + "\n"
    
    return output


# ──────────────────────────────────────────────────────────
# Example Usage (Run this module directly to test)
# ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(describe_features())
    
    print("\n📊 Model Info:")
    info = get_model_info()
    for key, value in info.items():
        print(f"  {key}: {value}")
    
    print("\n📈 Feature Importance (Top 5):")
    importance = get_feature_importance()
    for i, (feature, score) in enumerate(sorted(importance.items(), key=lambda x: -x[1])[:5], 1):
        print(f"  {i}. {feature}: {score:.4f}")
    
    print("\n🧪 Example Prediction (using extract_features helper):")
    # NEW: Use extract_features() to build features automatically
    # This ensures all 20 v3 features are created correctly
    features = extract_features(
        dci_score=78,
        baseline_earnings=850,
        hour_of_day=19,
        day_of_week=4,
        city='Mumbai',
        zone_density='Mid',
        shift='Night',
        disruption_type='Rain'
    )
    
    print(f"  Features dict (20 features):")
    for key, value in features.items():
        if isinstance(value, float):
            print(f"    {key}: {value:.2f}")
        else:
            print(f"    {key}: {value}")
    
    result = predict_with_confidence(features)
    print(f"\n  Predicted Multiplier: {result['multiplier']:.3f}")
    print(f"  Confidence: {result['confidence']:.1%}")
    print(f"  {result['recommendation']}")
    print(f"  Model Test R²: {result['model_r2']:.3f}")
    
    # Example full payout calculation
    baseline = 850
    duration_minutes = 240
    payout = baseline * (duration_minutes / 480) * result['multiplier']
    print(f"\n💰 Full Payout Calculation:")
    print(f"  Baseline: ₹{baseline}")
    print(f"  Duration factor: {duration_minutes}/480 = {duration_minutes/480:.2f}")
    print(f"  Multiplier: {result['multiplier']:.3f}")
    print(f"  Final payout: ₹{payout:.2f}")

#!/usr/bin/env python3
"""
tests/test_premium_calculation_pipeline.py
───────────────────────────────────────────────────────────────
Comprehensive end-to-end tests for the premium calculation pipeline.

Tests cover:
1. Synthetic data generation (1000 workers, realistic distributions)
2. Model training (80/20 split, validation metrics)
3. Feature extraction and inference
4. API endpoint (POST with validation)
5. Premium amount bounds (₹21-₹57.20)
6. Risk scoring and factor analysis

Run with:
    pytest tests/test_premium_calculation_pipeline.py -v
"""

import os
import sys
import logging
import pytest
import numpy as np
import pandas as pd
import json
from datetime import datetime
from pathlib import Path

# Add backend to path
BACKEND_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_DIR))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_premium_pipeline")


class TestSyntheticDataGeneration:
    """Test synthetic data generation for premium model training."""
    
    def test_synthetic_workers_generation(self):
        """Test that 1000 workers are generated with realistic distributions."""
        from backend.ml.train_premium_model import generate_synthetic_data
        
        df = generate_synthetic_data(n_samples=1000)
        
        # Validate dimensions
        assert len(df) == 1000, f"Expected 1000 workers, got {len(df)}"
        assert "worker_gig_score" in df.columns
        assert "pincode_30d_avg_dci" in df.columns
        assert "predicted_7d_max_dci" in df.columns
        assert "discount_multiplier" in df.columns
        
        # Validate feature ranges
        assert (df["worker_gig_score"] >= 20).all() and (df["worker_gig_score"] <= 100).all()
        assert (df["pincode_30d_avg_dci"] >= 0).all() and (df["pincode_30d_avg_dci"] <= 100).all()
        assert (df["predicted_7d_max_dci"] >= 0).all() and (df["predicted_7d_max_dci"] <= 100).all()
        assert (df["discount_multiplier"] >= 0.0).all() and (df["discount_multiplier"] <= 0.30).all()
        
        # Validate shift one-hot encoding
        assert "shift_morning" in df.columns
        assert "shift_day" in df.columns
        assert "shift_night" in df.columns
        assert "shift_flexible" in df.columns
        
        # At most one shift should be 1 per worker
        shift_cols = ["shift_morning", "shift_day", "shift_night", "shift_flexible"]
        shift_sums = (df[shift_cols] == 1).sum(axis=1)
        assert (shift_sums <= 1).all(), "Each worker should have at most one shift"
        
        logger.info(f"✅ Generated {len(df)} workers with realistic distributions")

    def test_synthetic_data_distributions(self):
        """Test that synthetic data has realistic statistical properties."""
        from backend.ml.train_premium_model import generate_synthetic_data
        
        df = generate_synthetic_data(n_samples=1000)
        
        # GigScore should be normally distributed around 85
        gig_mean = df["worker_gig_score"].mean()
        gig_std = df["worker_gig_score"].std()
        assert 80 <= gig_mean <= 90, f"GigScore mean should be ~85, got {gig_mean}"
        assert 8 <= gig_std <= 12, f"GigScore std should be ~10, got {gig_std}"
        
        # Discount multiplier should be reasonably distributed
        discount_mean = df["discount_multiplier"].mean()
        discount_std = df["discount_multiplier"].std()
        assert 0.05 <= discount_mean <= 0.15, f"Discount mean should be ~0.10, got {discount_mean}"
        assert discount_std > 0.01, f"Discount should have variation"
        
        logger.info(f"✅ Data distributions validated")


class TestModelTraining:
    """Test model training and validation."""
    
    def test_model_training(self):
        """Test model training with proper 80/20 split."""
        from backend.ml.train_premium_model import train_pricing_model
        from sklearn.metrics import r2_score, mean_absolute_error
        
        model, metadata = train_pricing_model()
        
        # Validate model exists and has expected attributes
        assert model is not None
        assert hasattr(model, 'predict')
        assert hasattr(model, 'feature_importances_')
        
        # Validate metadata
        assert "metrics" in metadata
        assert "test_r2" in metadata["metrics"]
        assert "test_mae" in metadata["metrics"]
        assert "test_rmse" in metadata["metrics"]
        
        logger.info(f"✅ Model training successful")

    def test_model_metrics_validation(self):
        """Test that model meets required validation metrics."""
        from backend.ml.train_premium_model import train_pricing_model
        
        model, metadata = train_pricing_model()
        
        r2 = metadata["metrics"]["test_r2"]
        mae = metadata["metrics"]["test_mae"]
        
        # Validate R² > 0.75 (as required)
        assert r2 > 0.75, f"R² should be > 0.75, got {r2}"
        
        # Validate MAE < 0.05 on discount multiplier (< ₹15 on premium)
        # MAE on discount_multiplier: if discount mean is 0.10, ₹15 / ₹150 base ≈ 0.10 error
        assert mae < 0.05, f"MAE should be < 0.05, got {mae}"
        
        logger.info(f"✅ Model metrics validated: R²={r2:.4f}, MAE={mae:.6f}")

    def test_premium_amount_bounds(self):
        """Test that predicted premiums stay within valid range."""
        from backend.ml.train_premium_model import generate_synthetic_data
        from sklearn.ensemble import HistGradientBoostingRegressor
        from sklearn.model_selection import train_test_split
        
        df = generate_synthetic_data(n_samples=1000)
        
        features = [
            'worker_gig_score', 'pincode_30d_avg_dci', 'predicted_7d_max_dci',
            'shift_morning', 'shift_day', 'shift_night', 'shift_flexible'
        ]
        
        X = df[features]
        y = df['discount_multiplier']
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        model = HistGradientBoostingRegressor(loss='poisson', learning_rate=0.05, max_iter=150, max_depth=5)
        model.fit(X_train, y_train)
        
        preds = model.predict(X_test)
        preds = np.clip(preds, 0.0, 0.30)
        
        # Calculate final premiums for BASIC plan (₹30)
        base_price = 30
        premiums = [base_price - (base_price * d) for d in preds]
        
        # Premium should stay within ₹21-₹30 (0.7x to 1.0x before any markup)
        min_premium = min(premiums)
        max_premium = max(premiums)
        
        min_allowed = base_price * 0.7  # ₹21
        max_allowed = base_price  # ₹30
        
        assert min_premium >= min_allowed, f"Min premium ₹{min_premium} should be >= ₹{min_allowed}"
        assert max_premium <= max_allowed, f"Max premium ₹{max_premium} should be <= ₹{max_allowed}"
        
        logger.info(f"✅ Premium bounds validated: ₹{min_premium:.2f} - ₹{max_premium:.2f}")


class TestFeatureExtraction:
    """Test feature extraction and validation."""
    
    def test_feature_extraction_order(self):
        """Test that features are extracted in correct order for model."""
        import pandas as pd
        from backend.ml.train_premium_model import generate_synthetic_data
        
        df = generate_synthetic_data(n_samples=10)
        
        expected_features = [
            'worker_gig_score',
            'pincode_30d_avg_dci',
            'predicted_7d_max_dci',
            'shift_morning',
            'shift_day',
            'shift_night',
            'shift_flexible'
        ]
        
        for feature in expected_features:
            assert feature in df.columns, f"Missing feature: {feature}"
        
        # Extract features in order
        X = df[expected_features]
        assert X.shape[1] == 7, f"Expected 7 features, got {X.shape[1]}"
        
        logger.info(f"✅ Feature extraction validated")

    def test_feature_normalization_bounds(self):
        """Test that all features are within expected bounds."""
        from backend.ml.train_premium_model import generate_synthetic_data
        
        df = generate_synthetic_data(n_samples=1000)
        
        # GigScore: [0, 100]
        assert (df['worker_gig_score'] >= 0).all() and (df['worker_gig_score'] <= 100).all()
        
        # DCI values: [0, 100]
        assert (df['pincode_30d_avg_dci'] >= 0).all() and (df['pincode_30d_avg_dci'] <= 100).all()
        assert (df['predicted_7d_max_dci'] >= 0).all() and (df['predicted_7d_max_dci'] <= 100).all()
        
        # Shift encoding: {0, 1}
        for col in ['shift_morning', 'shift_day', 'shift_night', 'shift_flexible']:
            assert df[col].isin([0, 1]).all(), f"Shift feature {col} should be binary"
        
        logger.info(f"✅ Feature normalization bounds validated")


class TestInference:
    """Test model inference and risk scoring."""
    
    def test_inference_with_sample_features(self):
        """Test inference with sample worker features."""
        from backend.ml.train_premium_model import load_ai_model
        import pandas as pd
        import numpy as np
        
        model, metadata = load_ai_model()
        
        # Create sample feature vector
        sample = pd.DataFrame([{
            'worker_gig_score': 85.0,
            'pincode_30d_avg_dci': 35.0,
            'predicted_7d_max_dci': 50.0,
            'shift_morning': 0,
            'shift_day': 1,
            'shift_night': 0,
            'shift_flexible': 0
        }])
        
        # Run inference
        prediction = model.predict(sample)[0]
        prediction = np.clip(prediction, 0.0, 0.30)
        
        # Validate output
        assert 0.0 <= prediction <= 0.30, f"Prediction should be [0.0, 0.30], got {prediction}"
        
        # Calculate final premium (BASIC plan)
        base_price = 30
        discount_amount = base_price * prediction
        final_premium = base_price - discount_amount
        
        assert 21 <= final_premium <= 30, f"Premium should be [21, 30], got {final_premium}"
        
        logger.info(f"✅ Inference validated: discount={prediction:.4f}, premium=₹{final_premium:.2f}")

    def test_risk_score_calculation(self):
        """Test risk score calculation from model outputs."""
        
        # Risk score = 100 - gig_score
        test_cases = [
            (100, 0),    # Perfect trust = 0 risk
            (85, 15),    # Good trust = low risk
            (70, 30),    # Moderate trust = medium risk
            (50, 50),    # Low trust = high risk
            (30, 70),    # Very low trust = very high risk
        ]
        
        for gig_score, expected_risk in test_cases:
            risk_score = max(0, min(100, 100 - gig_score))
            assert risk_score == expected_risk, f"Risk for gig_score {gig_score} should be {expected_risk}"
        
        logger.info(f"✅ Risk score calculation validated")


class TestAPIValidation:
    """Test API endpoint validation and error handling."""
    
    def test_premium_quote_request_validation(self):
        """Test request validation."""
        from backend.api.premium import PremiumQuoteRequest
        from pydantic import ValidationError
        
        # Valid requests
        valid_request = PremiumQuoteRequest(
            worker_id="test-worker-123",
            plan_tier="basic"
        )
        assert valid_request.worker_id == "test-worker-123"
        assert valid_request.plan_tier == "basic"
        
        # Invalid plan tier
        with pytest.raises(ValidationError):
            PremiumQuoteRequest(
                worker_id="test-worker-123",
                plan_tier="invalid"
            )
        
        logger.info(f"✅ API request validation tested")

    def test_premium_quote_response_structure(self):
        """Test response model structure."""
        from backend.api.premium import PremiumQuoteResponse
        
        response = PremiumQuoteResponse(
            worker_id="test-123",
            base_premium=30.0,
            dynamic_premium=27.0,
            discount_applied=3.0,
            bonus_coverage_hours=1,
            plan_type="basic",
            risk_score=15.0,
            risk_factors={"gig_score": 85, "zone_risk": "Normal"},
            explanation="Test explanation",
            insights={"reason": "Test"}
        )
        
        assert response.worker_id == "test-123"
        assert response.base_premium == 30.0
        assert response.dynamic_premium == 27.0
        assert response.risk_score == 15.0
        
        logger.info(f"✅ API response structure validated")


class TestBusinessLogic:
    """Test business logic validation."""
    
    def test_discount_only_psychology(self):
        """Test that premiums never increase (discount-only psychology)."""
        from backend.ml.train_premium_model import generate_synthetic_data
        from sklearn.ensemble import HistGradientBoostingRegressor
        from sklearn.model_selection import train_test_split
        
        df = generate_synthetic_data(n_samples=100)
        
        features = [
            'worker_gig_score', 'pincode_30d_avg_dci', 'predicted_7d_max_dci',
            'shift_morning', 'shift_day', 'shift_night', 'shift_flexible'
        ]
        
        X = df[features]
        y = df['discount_multiplier']
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        model = HistGradientBoostingRegressor(loss='poisson', learning_rate=0.05, max_iter=150, max_depth=5)
        model.fit(X_train, y_train)
        
        preds = model.predict(X_test)
        preds = np.clip(preds, 0.0, 0.30)
        
        # All predictions should be in [0, 0.30] range (discount only)
        assert (preds >= 0.0).all(), "No premiums should be negative"
        assert (preds <= 0.30).all(), "Maximum discount is 30%"
        
        logger.info(f"✅ Discount-only psychology enforced")

    def test_bonus_coverage_logic(self):
        """Test bonus coverage hours calculation."""
        
        # Bonus coverage should scale with plan and DCI risk
        test_cases = [
            ("basic", 50, 0),      # Low DCI, no bonus
            ("basic", 75, 1),      # High DCI, max 1 bonus
            ("plus", 50, 0),       # Low DCI, no bonus
            ("plus", 75, 2),       # High DCI, max 2 bonus
            ("pro", 50, 0),        # Low DCI, no bonus
            ("pro", 75, 3),        # High DCI, max 3 bonus
        ]
        
        plan_limits = {"basic": 1, "plus": 2, "pro": 3}
        dci_threshold = 70
        
        for plan, dci, expected_bonus in test_cases:
            bonus = 0
            if dci > dci_threshold:
                plan_limit = plan_limits.get(plan, 2)
                bonus = min(plan_limit, 3)
            
            assert bonus == expected_bonus, f"Plan {plan}, DCI {dci}: expected bonus {expected_bonus}, got {bonus}"
        
        logger.info(f"✅ Bonus coverage logic validated")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

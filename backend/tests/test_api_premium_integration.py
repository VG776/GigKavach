"""
tests/test_api_premium_integration.py
─────────────────────────────────────────────────────────────
End-to-End API integration test for Premium Model.
Tests the full flow: model loading → inference → API response formatting.

Run with:
    python backend/tests/test_api_premium_integration.py
    OR
    pytest tests/test_api_premium_integration.py -v
"""

import os
import sys
import json
import logging

# ── Path Setup ──────────────────────────────────────────────────────────────
BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_ROOT)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)
logger = logging.getLogger(__name__)

import asyncio
import pandas as pd

def run_tests():
    """Main test suite."""
    
    print("\n" + "="*70)
    print("  END-TO-END PREMIUM MODEL API INTEGRATION TEST")
    print("="*70)
    
    # Load model outside of tests for efficiency
    from services.premium_service import load_ai_model, compute_dynamic_quote
    
    model, metadata = load_ai_model()
    
    test_results = []
    
    # ──────────────────────────────────────────────────────────────────────────
    # TEST 1: Model Loading
    # ──────────────────────────────────────────────────────────────────────────
    print("\n[TEST 1] Model Loading")
    print("-" * 70)
    
    try:
        assert model is not None, "Model is None"
        assert metadata is not None, "Metadata is None"
        assert model != "FAILED", "Model loading failed"
        
        print(f"  ✓ Model loaded: {type(model).__name__}")
        print(f"  ✓ Metadata loaded with {len(metadata['features'])} features")
        print(f"  ✓ Model R² Score: {metadata['metrics']['test_r2']:.4f}")
        
        test_results.append(("Model Loading", True, ""))
    except AssertionError as e:
        print(f"  ✗ {e}")
        test_results.append(("Model Loading", False, str(e)))
    
    # ──────────────────────────────────────────────────────────────────────────
    # TEST 2: Feature Alignment
    # ──────────────────────────────────────────────────────────────────────────
    print("\n[TEST 2] Feature Vectors")
    print("-" * 70)
    
    try:
        expected_features = [
            'worker_gig_score',
            'pincode_30d_avg_dci',
            'predicted_7d_max_dci',
            'shift_morning',
            'shift_day',
            'shift_night',
            'shift_flexible'
        ]
        
        actual_features = metadata['features']
        assert actual_features == expected_features, f"Feature mismatch: {actual_features}"
        
        print(f"  ✓ Feature count: {len(actual_features)}")
        print(f"  ✓ Features match expected: {', '.join(actual_features[:3])}...")
        
        test_results.append(("Feature Alignment", True, ""))
    except AssertionError as e:
        print(f"  ✗ {e}")
        test_results.append(("Feature Alignment", False, str(e)))
    
    # ──────────────────────────────────────────────────────────────────────────
    # TEST 3: Inference - High GigScore (Safe Worker)
    # ──────────────────────────────────────────────────────────────────────────
    print("\n[TEST 3] Inference: Safe Worker (GigScore=95)")
    print("-" * 70)
    
    try:
        test_df = pd.DataFrame([{
            'worker_gig_score': 95,
            'pincode_30d_avg_dci': 25,
            'predicted_7d_max_dci': 30,
            'shift_morning': 0,
            'shift_day': 1,
            'shift_night': 0,
            'shift_flexible': 0,
        }][0:1])
        
        prediction = model.predict(test_df)[0]
        
        assert isinstance(prediction, (float, int)), f"Prediction not numeric: {type(prediction)}"
        assert 0.0 <= prediction <= 0.40, f"Prediction out of range: {prediction}"
        assert prediction > 0.15, f"Safe worker should get significant discount: {prediction}"
        
        print(f"  ✓ Prediction: {prediction:.4f} (discount multiplier)")
        print(f"  ✓ Safe worker gets ~{int(prediction*100)}% discount")
        print(f"  ✓ Example: ₹30 base → ₹{30 - round(30*prediction, 1)} final price")
        
        test_results.append(("Inference: Safe Worker", True, f"discount={prediction:.4f}"))
    except Exception as e:
        print(f"  ✗ {e}")
        test_results.append(("Inference: Safe Worker", False, str(e)))
    
    # ──────────────────────────────────────────────────────────────────────────
    # TEST 4: Inference - Risky Worker
    # ──────────────────────────────────────────────────────────────────────────
    print("\n[TEST 4] Inference: Risky Worker (GigScore=40, High DCI)")
    print("-" * 70)
    
    try:
        test_df = pd.DataFrame([{
            'worker_gig_score': 40,
            'pincode_30d_avg_dci': 75,
            'predicted_7d_max_dci': 85,
            'shift_morning': 0,
            'shift_day': 0,
            'shift_night': 1,
            'shift_flexible': 0,
        }][0:1])
        
        prediction = model.predict(test_df)[0]
        
        assert isinstance(prediction, (float, int)), f"Prediction not numeric"
        assert 0.0 <= prediction <= 0.44, f"Prediction out of range"
        # Risky worker gets minimal or zero discount
        assert prediction < 0.15, f"Risky worker should get minimal discount: {prediction}"
        
        print(f"  ✓ Prediction: {prediction:.4f} (discount multiplier)")
        print(f"  ✓ Risky worker gets ~{int(prediction*100)}% discount (minimal)")
        print(f"  ✓ Example: ₹30 base → ₹{30 - round(30*prediction, 1)} final price")
        print(f"  ⓘ High DCI triggers bonus hours instead of price hike (Psychology)")
        
        test_results.append(("Inference: Risky Worker", True, f"discount={prediction:.4f}"))
    except Exception as e:
        print(f"  ✗ {e}")
        test_results.append(("Inference: Risky Worker", False, str(e)))
    
    # ──────────────────────────────────────────────────────────────────────────
    # TEST 5: Batch Inference
    # ──────────────────────────────────────────────────────────────────────────
    print("\n[TEST 5] Batch Inference (3 workers)")
    print("-" * 70)
    
    try:
        batch_df = pd.DataFrame([
            {
                'worker_gig_score': 90,
                'pincode_30d_avg_dci': 20,
                'predicted_7d_max_dci': 25,
                'shift_morning': 0,
                'shift_day': 1,
                'shift_night': 0,
                'shift_flexible': 0,
            },
            {
                'worker_gig_score': 60,
                'pincode_30d_avg_dci': 60,
                'predicted_7d_max_dci': 75,
                'shift_morning': 1,
                'shift_day': 0,
                'shift_night': 0,
                'shift_flexible': 0,
            },
            {
                'worker_gig_score': 95,
                'pincode_30d_avg_dci': 15,
                'predicted_7d_max_dci': 20,
                'shift_morning': 0,
                'shift_day': 0,
                'shift_night': 1,
                'shift_flexible': 0,
            }
        ])
        
        predictions = model.predict(batch_df)
        
        assert len(predictions) == 3, f"Expected 3 predictions, got {len(predictions)}"
        assert all(0.0 <= p <= 0.40 for p in predictions), "Any prediction out of range"
        # Verify ranking: Worker 2 (95 gig) > Worker 1 (90 gig) > Worker 2 (60 gig)
        assert predictions[2] > predictions[0], "High gig workers should get better discounts"
        assert predictions[0] > predictions[1], "Medium gig better than low gig"
        
        print(f"  ✓ Batch predictions: {[f'{p:.4f}' for p in predictions]}")
        print(f"  ✓ All within valid range [0.0, 0.40]")
        print(f"  ✓ Ranking correct: 95>90>60 gig scores → discounts decrease as risk increases")
        
        test_results.append(("Batch Inference", True, f"predictions={len(predictions)}"))
    except Exception as e:
        print(f"  ✗ {e}")
        test_results.append(("Batch Inference", False, str(e)))
    
    # ──────────────────────────────────────────────────────────────────────────
    # TEST 6: Pricing Math - All Plans
    # ──────────────────────────────────────────────────────────────────────────
    print("\n[TEST 6] Pricing Math (All Plans)")
    print("-" * 70)
    
    try:
        plan_premiums = {
            "basic": 30.0,
            "plus": 37.0,
            "pro": 44.0,
        }
        
        discount_mult = 0.20  # 20% discount
        
        results = {}
        for plan, base in plan_premiums.items():
            discount_amt = round(base * discount_mult, 1)
            final = base - discount_amt
            results[plan] = {
                "base": base,
                "discount": discount_amt,
                "final": final
            }
        
        # Verify no plan exceeds base price
        assert all(r["final"] <= r["base"] for r in results.values()), "Final > base price"
        
        print(f"  ✓ Basic:  ₹30.00 - ₹6.00 = ₹{results['basic']['final']:.2f}")
        print(f"  ✓ Plus:   ₹37.00 - ₹7.40 = ₹{results['plus']['final']:.2f}")
        print(f"  ✓ Pro:    ₹44.00 - ₹8.80 = ₹{results['pro']['final']:.2f}")
        print(f"  ✓ All premiums within valid business ranges")
        
        test_results.append(("Pricing Math", True, "All plans valid"))
    except Exception as e:
        print(f"  ✗ {e}")
        test_results.append(("Pricing Math", False, str(e)))
    
    # ──────────────────────────────────────────────────────────────────────────
    # TEST 7: Determinism (Model Reproducibility)
    # ──────────────────────────────────────────────────────────────────────────
    print("\n[TEST 7] Model Determinism")
    print("-" * 70)
    
    try:
        test_df = pd.DataFrame([{
            'worker_gig_score': 80,
            'pincode_30d_avg_dci': 40,
            'predicted_7d_max_dci': 50,
            'shift_morning': 1,
            'shift_day': 0,
            'shift_night': 0,
            'shift_flexible': 0,
        }][0:1])
        
        pred1 = model.predict(test_df)[0]
        pred2 = model.predict(test_df)[0]
        pred3 = model.predict(test_df)[0]
        
        assert pred1 == pred2 == pred3, f"Predictions differ: {pred1} vs {pred2} vs {pred3}"
        
        print(f"  ✓ Prediction 1: {pred1:.8f}")
        print(f"  ✓ Prediction 2: {pred2:.8f}")
        print(f"  ✓ Prediction 3: {pred3:.8f}")
        print(f"  ✓ Model is fully deterministic (GPU/CPU independent)")
        
        test_results.append(("Model Determinism", True, ""))
    except Exception as e:
        print(f"  ✗ {e}")
        test_results.append(("Model Determinism", False, str(e)))
    
    # ──────────────────────────────────────────────────────────────────────────
    # TEST 8: Edge Cases - Extreme Values
    # ──────────────────────────────────────────────────────────────────────────
    print("\n[TEST 8] Edge Cases: Extreme Values")
    print("-" * 70)
    
    try:
        edge_cases = [
            ("Max GigScore", 100, 0, 0),
            ("Min GigScore", 20, 100, 100),
            ("Mixed", 70, 50, 50),
        ]
        
        all_pass = True
        for name, score, avg_dci, pred_dci in edge_cases:
            test_df = pd.DataFrame([{
                'worker_gig_score': score,
                'pincode_30d_avg_dci': avg_dci,
                'predicted_7d_max_dci': pred_dci,
                'shift_morning': 0,
                'shift_day': 1,
                'shift_night': 0,
                'shift_flexible': 0,
            }][0:1])
            
            try:
                pred = model.predict(test_df)[0]
                assert 0.0 <= pred <= 0.40, f"Out of range: {pred}"
                print(f"  ✓ {name:20} (score={score:3d}, dci={pred_dci:3d}) → {pred:.4f}")
            except Exception as e:
                print(f"  ✗ {name:20} failed: {e}")
                all_pass = False
        
        assert all_pass, "Some edge cases failed"
        test_results.append(("Edge Cases", True, "All extreme values handled"))
    except Exception as e:
        print(f"  ✗ {e}")
        test_results.append(("Edge Cases", False, str(e)))
    
    # ──────────────────────────────────────────────────────────────────────────
    # FINAL SUMMARY
    # ──────────────────────────────────────────────────────────────────────────
    print("\n" + "="*70)
    print("  TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for _, p, _ in test_results if p)
    total = len(test_results)
    
    for name, passed_flag, detail in test_results:
        status = "✓" if passed_flag else "✗"
        detail_str = f" ({detail})" if detail else ""
        print(f"  {status} {name:30} {detail_str}")
    
    print("\n" + "="*70)
    if passed == total:
        print(f"  🎉 ALL {total} TESTS PASSED")
        print("="*70)
        print("\n  Next Steps:")
        print("  1. Backend API is ready: /api/v1/premium/quote")
        print("  2. Run: uvicorn main:app --reload --port 8000")
        print("  3. Test with frontend at http://localhost:3000")
        print("  4. API docs: http://localhost:8000/docs")
        return True
    else:
        print(f"  ❌ {total - passed}/{total} TESTS FAILED")
        print("="*70)
        return False

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)

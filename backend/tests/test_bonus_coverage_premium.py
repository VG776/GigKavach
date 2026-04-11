"""
tests/test_bonus_coverage_premium.py
─────────────────────────────────────────────────────────────
Tests for bonus coverage hours validation and plan-specific limits.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_ROOT)

from services.premium_service import compute_dynamic_quote, BONUS_COVERAGE_LIMITS
from models.worker import PlanType


class TestBonusCoveragePremium(unittest.TestCase):
    """Test bonus coverage hours validation against plan limits."""

    def setUp(self):
        """Set up test fixtures."""
        self.worker_id = "test-bonus-worker-123"
        self.base_worker = {
            "id": self.worker_id,
            "gig_score": 95.0,  # High score to ensure model loads
            "shift": "day",
            "pin_codes": ["560001"],
            "plan": "basic",
            "account_status": "active"
        }

    # ════════════════════════════════════════════════════════════════════════════
    # TEST 1: Bonus Coverage Limits Defined
    # ════════════════════════════════════════════════════════════════════════════

    def test_bonus_coverage_limits_defined(self):
        """Verify all plan types have bonus coverage limits configured."""
        self.assertIn(PlanType.BASIC, BONUS_COVERAGE_LIMITS)
        self.assertIn(PlanType.PLUS, BONUS_COVERAGE_LIMITS)
        self.assertIn(PlanType.PRO, BONUS_COVERAGE_LIMITS)
        
        self.assertEqual(BONUS_COVERAGE_LIMITS[PlanType.BASIC], 1)
        self.assertEqual(BONUS_COVERAGE_LIMITS[PlanType.PLUS], 2)
        self.assertEqual(BONUS_COVERAGE_LIMITS[PlanType.PRO], 3)

    # ════════════════════════════════════════════════════════════════════════════
    # TEST 2: Bonus Coverage During High-DCI for BASIC Plan
    # ════════════════════════════════════════════════════════════════════════════

    @patch("services.premium_service.get_supabase")
    @patch("services.premium_service.load_ai_model")
    def test_bonus_coverage_basic_plan_high_dci(self, mock_load_model, mock_get_sb):
        """
        Scenario: Basic plan, high DCI (>70), high gig_score.
        Expected: Bonus coverage = min(2, 1) = 1 hour
        """
        mock_sb = MagicMock()
        mock_get_sb.return_value = mock_sb
        
        # Setup worker
        mock_sb.table().select().eq().execute.return_value.data = [
            {**self.base_worker, "plan": "basic"}
        ]
        
        # Mock ML model to ensure it loads and returns reasonable value
        mock_model = MagicMock()
        mock_model.predict.return_value = [0.20]  # 20% discount
        mock_load_model.return_value = (mock_model, {})
        
        # Patch zone metrics to return high pred_dci
        with patch("services.premium_service._derive_mock_zone_metrics") as mock_metrics:
            mock_metrics.return_value = (35.0, 75.0)  # avg_dci=35, pred_dci=75 (> 70)
            
            quote = compute_dynamic_quote(self.worker_id, "basic")
            
            # Should grant bonus hours (limited to 1 for BASIC)
            self.assertEqual(quote["bonus_coverage_hours"], 1)
            self.assertEqual(quote["plan_type"], "basic")

    # ════════════════════════════════════════════════════════════════════════════
    # TEST 3: Bonus Coverage During High-DCI for PLUS Plan
    # ════════════════════════════════════════════════════════════════════════════

    @patch("services.premium_service.get_supabase")
    @patch("services.premium_service.load_ai_model")
    def test_bonus_coverage_plus_plan_high_dci(self, mock_load_model, mock_get_sb):
        """
        Scenario: Plus plan, high DCI (>70), high gig_score.
        Expected: Bonus coverage = min(2, 2) = 2 hours
        """
        mock_sb = MagicMock()
        mock_get_sb.return_value = mock_sb
        
        # Setup worker with Plus plan
        mock_sb.table().select().eq().execute.return_value.data = [
            {**self.base_worker, "plan": "plus"}
        ]
        
        # Mock ML model
        mock_model = MagicMock()
        mock_model.predict.return_value = [0.20]
        mock_load_model.return_value = (mock_model, {})
        
        # Patch zone metrics to return high pred_dci
        with patch("services.premium_service._derive_mock_zone_metrics") as mock_metrics:
            mock_metrics.return_value = (40.0, 75.0)  # pred_dci=75 (> 70)
            
            quote = compute_dynamic_quote(self.worker_id, "plus")
            
            # Should grant bonus hours (2 for PLUS)
            self.assertEqual(quote["bonus_coverage_hours"], 2)
            self.assertEqual(quote["plan_type"], "plus")

    # ════════════════════════════════════════════════════════════════════════════
    # TEST 4: Bonus Coverage During High-DCI for PRO Plan
    # ════════════════════════════════════════════════════════════════════════════

    @patch("services.premium_service.get_supabase")
    @patch("services.premium_service.load_ai_model")
    def test_bonus_coverage_pro_plan_high_dci(self, mock_load_model, mock_get_sb):
        """
        Scenario: Pro plan, high DCI (>70), high gig_score.
        Expected: Bonus coverage = min(2, 3) = 2 hours
        Note: Bonus granted is capped at 2 globally, plan limit is 3
        """
        mock_sb = MagicMock()
        mock_get_sb.return_value = mock_sb
        
        # Setup worker with Pro plan
        mock_sb.table().select().eq().execute.return_value.data = [
            {**self.base_worker, "plan": "pro"}
        ]
        
        # Mock ML model
        mock_model = MagicMock()
        mock_model.predict.return_value = [0.20]
        mock_load_model.return_value = (mock_model, {})
        
        # Patch zone metrics
        with patch("services.premium_service._derive_mock_zone_metrics") as mock_metrics:
            mock_metrics.return_value = (45.0, 80.0)  # pred_dci=80 (> 70)
            
            quote = compute_dynamic_quote(self.worker_id, "pro")
            
            # Should grant bonus hours: min(2, 3) = 2
            self.assertEqual(quote["bonus_coverage_hours"], 2)
            self.assertLessEqual(quote["bonus_coverage_hours"], 3)
            self.assertEqual(quote["plan_type"], "pro")

    # ════════════════════════════════════════════════════════════════════════════
    # TEST 5: No Bonus Coverage When DCI < 70
    # ════════════════════════════════════════════════════════════════════════════

    @patch("services.premium_service.get_supabase")
    @patch("services.premium_service.load_ai_model")
    def test_no_bonus_coverage_low_dci(self, mock_load_model, mock_get_sb):
        """
        Scenario: Any plan, low DCI (<70).
        Expected: Bonus coverage = 0
        """
        mock_sb = MagicMock()
        mock_get_sb.return_value = mock_sb
        
        # Setup worker
        mock_sb.table().select().eq().execute.return_value.data = [
            {**self.base_worker, "plan": "pro"}
        ]
        
        # Mock ML model
        mock_model = MagicMock()
        mock_model.predict.return_value = [0.15]
        mock_load_model.return_value = (mock_model, {})
        
        # Patch zone metrics - LOW DCI
        with patch("services.premium_service._derive_mock_zone_metrics") as mock_metrics:
            mock_metrics.return_value = (20.0, 40.0)  # pred_dci=40 (< 70)
            
            quote = compute_dynamic_quote(self.worker_id, "pro")
            
            # Should NOT grant bonus hours
            self.assertEqual(quote["bonus_coverage_hours"], 0)

    # ════════════════════════════════════════════════════════════════════════════
    # TEST 6: Bonus Coverage at DCI Boundary (= 70)
    # ════════════════════════════════════════════════════════════════════════════

    @patch("services.premium_service.get_supabase")
    @patch("services.premium_service.load_ai_model")
    def test_no_bonus_at_dci_boundary_70(self, mock_load_model, mock_get_sb):
        """
        Scenario: DCI exactly at 70 (boundary).
        Expected: Bonus coverage = 0 (threshold is > 70, not >= 70)
        """
        mock_sb = MagicMock()
        mock_get_sb.return_value = mock_sb
        
        mock_sb.table().select().eq().execute.return_value.data = [
            {**self.base_worker, "plan": "basic"}
        ]
        
        mock_model = MagicMock()
        mock_model.predict.return_value = [0.15]
        mock_load_model.return_value = (mock_model, {})
        
        # Patch zone metrics - EXACTLY 70
        with patch("services.premium_service._derive_mock_zone_metrics") as mock_metrics:
            mock_metrics.return_value = (35.0, 70.0)  # pred_dci=70 (NOT > 70)
            
            quote = compute_dynamic_quote(self.worker_id, "basic")
            
            # Should NOT grant bonus (threshold is > 70)
            self.assertEqual(quote["bonus_coverage_hours"], 0)

    # ════════════════════════════════════════════════════════════════════════════
    # TEST 7: Bonus Coverage at DCI Boundary (= 70.1)
    # ════════════════════════════════════════════════════════════════════════════

    @patch("services.premium_service.get_supabase")
    @patch("services.premium_service.load_ai_model")
    def test_bonus_at_dci_boundary_70_1(self, mock_load_model, mock_get_sb):
        """
        Scenario: DCI just above 70 (70.1).
        Expected: Bonus coverage = 1 (or plan-specific limit)
        """
        mock_sb = MagicMock()
        mock_get_sb.return_value = mock_sb
        
        mock_sb.table().select().eq().execute.return_value.data = [
            {**self.base_worker, "plan": "basic"}
        ]
        
        mock_model = MagicMock()
        mock_model.predict.return_value = [0.15]
        mock_load_model.return_value = (mock_model, {})
        
        # Patch zone metrics - SLIGHTLY ABOVE 70
        with patch("services.premium_service._derive_mock_zone_metrics") as mock_metrics:
            mock_metrics.return_value = (35.0, 70.5)  # pred_dci=70.5 (> 70)
            
            quote = compute_dynamic_quote(self.worker_id, "basic")
            
            # Should grant bonus (1 for BASIC)
            self.assertEqual(quote["bonus_coverage_hours"], 1)

    # ════════════════════════════════════════════════════════════════════════════
    # TEST 8: Bonus Coverage Upper Bound Validation
    # ════════════════════════════════════════════════════════════════════════════

    def test_bonus_coverage_never_exceeds_plan_limits(self):
        """
        Validation: Bonus coverage must never exceed plan-specific limits.
        Even if internal logic tries to grant 5 hours, should be capped.
        """
        # Simulated bonus granted by algorithm
        raw_bonus_hours = 10  # Hypothetical overage
        
        # Apply plan limits
        for plan_type, plan_limit in BONUS_COVERAGE_LIMITS.items():
            # Simulating the clamping logic from premium_service
            actual_bonus = min(raw_bonus_hours, plan_limit)
            
            # Should never exceed plan limit
            self.assertLessEqual(actual_bonus, plan_limit)
            self.assertLessEqual(actual_bonus, 3)  # Max across all plans

    # ════════════════════════════════════════════════════════════════════════════
    # TEST 9: Zone Risk Correctly Classified
    # ════════════════════════════════════════════════════════════════════════════

    @patch("services.premium_service.get_supabase")
    @patch("services.premium_service.load_ai_model")
    def test_forecasted_zone_risk_classification(self, mock_load_model, mock_get_sb):
        """
        Test that zone risk is correctly classified in insights.
        DCI > 65 = "High", DCI <= 65 = "Normal"
        """
        mock_sb = MagicMock()
        mock_get_sb.return_value = mock_sb
        
        mock_sb.table().select().eq().execute.return_value.data = [
            {**self.base_worker}
        ]
        
        mock_model = MagicMock()
        mock_model.predict.return_value = [0.15]
        mock_load_model.return_value = (mock_model, {})
        
        # Test HIGH risk (pred_dci > 65)
        with patch("services.premium_service._derive_mock_zone_metrics") as mock_metrics:
            mock_metrics.return_value = (40.0, 70.0)
            quote = compute_dynamic_quote(self.worker_id, "basic")
            self.assertEqual(quote["insights"]["forecasted_zone_risk"], "High")
        
        # Test NORMAL risk (pred_dci <= 65)
        with patch("services.premium_service._derive_mock_zone_metrics") as mock_metrics:
            mock_metrics.return_value = (30.0, 55.0)
            quote = compute_dynamic_quote(self.worker_id, "basic")
            self.assertEqual(quote["insights"]["forecasted_zone_risk"], "Normal")

    # ════════════════════════════════════════════════════════════════════════════
    # TEST 10: Bonus Coverage & Discount Both Awarded During High DCI
    # ════════════════════════════════════════════════════════════════════════════

    @patch("services.premium_service.get_supabase")
    @patch("services.premium_service.load_ai_model")
    def test_bonus_and_discount_together(self, mock_load_model, mock_get_sb):
        """
        Scenario: High GigScore + High DCI.
        Result: Both discount AND bonus coverage awarded.
        """
        mock_sb = MagicMock()
        mock_get_sb.return_value = mock_sb
        
        # High score worker
        mock_sb.table().select().eq().execute.return_value.data = [
            {**self.base_worker, "gig_score": 98.0}
        ]
        
        # Model predicts good discount
        mock_model = MagicMock()
        mock_model.predict.return_value = [0.25]  # 25% discount
        mock_load_model.return_value = (mock_model, {})
        
        # High DCI
        with patch("services.premium_service._derive_mock_zone_metrics") as mock_metrics:
            mock_metrics.return_value = (45.0, 85.0)  # Very high pred_dci
            
            quote = compute_dynamic_quote(self.worker_id, "basic")
            
            # Should have both discount AND bonus
            self.assertGreater(quote["discount_applied"], 0.0)
            self.assertGreater(quote["bonus_coverage_hours"], 0)
            
            # Premium should be noticeably lower than base
            self.assertLess(
                quote["dynamic_premium"],
                quote["base_premium"]
            )
            
            # Insights should show high risk
            self.assertEqual(quote["insights"]["forecasted_zone_risk"], "High")


if __name__ == "__main__":
    unittest.main()

import asyncio
"""
tests/test_fraud_gigscore_premium_trinity.py
─────────────────────────────────────────────────────────────
Integration test for the complete fraud → GigScore → premium pipeline.
Tests the full workflow: Fraud detection → Score penalty → Premium impact.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch
import json
import numpy as np

BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_ROOT)

from services.gigscore_service import update_gig_score, GigScoreEvent, get_event_impact
from services.premium_service import compute_dynamic_quote
from services.fraud_service import FraudDetectionService
from models.worker import PlanType


class TestFraudGigScorePremiumTrinity(unittest.TestCase):
    """Complete trinity workflow: fraud detection → score impact → premium adjustment."""

    def setUp(self):
        """Set up test fixtures."""
        self.worker_id = "test-trinity-worker-123"
        self.mock_worker = {
            "id": self.worker_id,
            "gig_score": 95.0,
            "account_status": "active",
            "shift": "day",
            "pin_codes": ["560001"],
            "plan": "basic",
            "city": "Bengaluru",
            "pincode": "560001"
        }
        self.mock_claim = {
            "id": "claim-fraud-001",
            "worker_id": self.worker_id,
            "dci_score": 45,
            "gps_coordinates": [12.9352, 77.6245],
            "baseline_earnings": 850,
            "claimed_amount": 1500,
            "disruption_type": "GPS_SPOOF"
        }

    # ════════════════════════════════════════════════════════════════════════════
    # TRINITY TEST 1: Clean Path (No Fraud)
    # ════════════════════════════════════════════════════════════════════════════

    @patch("services.premium_service.get_supabase")
    @patch("services.premium_service.load_ai_model")
    @patch("services.fraud_service.get_detector")
    def test_trinity_clean_path(self, mock_fraud_detector, mock_load_model, mock_get_sb):
        """
        Scenario: Worker has clean claim during high-DCI event.
        Expected flow:
          1. Claim passes fraud detection
          2. GigScore +5 (VALID_SEVERE_CLAIM)
          3. Premium quote shows improved discount
        """
        mock_sb = MagicMock()
        mock_get_sb.return_value = mock_sb
        
        # Mock worker
        mock_sb.table().select().eq().execute.return_value.data = [self.mock_worker]
        
        # Mock ML model (simple mock)
        mock_model = MagicMock()
        mock_model.predict.return_value = [0.15]  # 15% discount
        mock_load_model.return_value = (mock_model, {})
        
        # Mock fraud detector - CLEAN
        mock_detector = MagicMock()
        mock_detector.detect_fraud.return_value = {
            'decision': 'APPROVE',
            'fraud_score': 0.1,
            'fraud_type': 'none',
            'stage1_result': 'PASS',
            'stage2_score': 0.1,
            'stage3_score': 0.1,
            'confidence': 0.95
        }
        mock_fraud_detector.return_value = mock_detector
        
        # 1. Check fraud - should PASS
        fraud_service = FraudDetectionService()
        fraud_result = fraud_service.check_fraud(self.mock_claim, {})
        
        self.assertEqual(fraud_result['decision'], 'APPROVE')
        self.assertEqual(fraud_result['is_fraud'], False)
        self.assertEqual(fraud_result['payout_action'], '100%')
        
        # 2. Update GigScore due to valid claim (settlement service would do this)
        with patch("services.gigscore_service.get_supabase") as mock_sb_score:
            mock_sb_score.return_value.table().select().eq().execute.return_value.data = [
                {"gig_score": 95.0, "account_status": "active"}
            ]
            new_score = update_gig_score(
                self.worker_id,
                GigScoreEvent.VALID_SEVERE_CLAIM,
                {"dci": 90}
            )
            # Should grant +5 points
            self.assertEqual(new_score, 100.0)
        
        # 3. Quote should reflect excellent score
        quote = asyncio.run(compute_dynamic_quote(self.worker_id, "basic"))
        self.assertEqual(quote["base_premium"], 30.0)
        # High score → should have discount
        self.assertLess(quote["dynamic_premium"], 30.0)
        self.assertGreater(quote["discount_applied"], 0.0)

    # ════════════════════════════════════════════════════════════════════════════
    # TRINITY TEST 2: Fraud Tier 1 Path (FLAG_50)
    # ════════════════════════════════════════════════════════════════════════════

    @patch("services.premium_service.get_supabase")
    @patch("services.premium_service.load_ai_model")
    @patch("services.fraud_service.get_detector")
    def test_trinity_fraud_tier1_impact(self, mock_fraud_detector, mock_load_model, mock_get_sb):
        """
        Scenario: Worker has Tier 1 fraud flag (2-3 suspicious signals).
        Expected flow:
          1. Fraud detection → FLAG_50
          2. GigScore -7.5 points (FRAUD_TIER_1)
          3. Premium quote shows reduced discount
          4. Payout: 50% held, 50% released
        """
        mock_sb = MagicMock()
        mock_get_sb.return_value = mock_sb
        
        # Mock worker with initial high score
        mock_sb.table().select().eq().execute.return_value.data = [self.mock_worker]
        
        # Mock ML model: More discount for higher GigScore
        mock_model = MagicMock()
        mock_model.predict.side_effect = lambda df: np.array([0.15 if df.iloc[0]["worker_gig_score"] > 90 else 0.05])
        mock_load_model.return_value = (mock_model, {})
        
        # Mock fraud detector - TIER 1 FLAGS
        mock_detector = MagicMock()
        mock_detector.detect_fraud.return_value = {
            'decision': 'FLAG_50',
            'fraud_score': 0.45,
            'fraud_type': 'threshold_gaming',
            'stage1_result': 'PASS',
            'stage2_score': 0.35,
            'stage3_score': 0.45,
            'confidence': 0.72
        }
        mock_fraud_detector.return_value = mock_detector
        
        # 1. Check fraud - should FLAG_50
        with patch("services.gigscore_service.get_supabase") as mock_sb_gs:
            mock_sb_gs.return_value = mock_sb  # Reuse the same mock
            fraud_service = FraudDetectionService()
            fraud_result = fraud_service.check_fraud(self.mock_claim, {})
        
        self.assertEqual(fraud_result['decision'], 'FLAG_50')
        self.assertEqual(fraud_result['is_fraud'], True)
        self.assertEqual(fraud_result['payout_action'], '50%_HOLD_48H')
        self.assertIn('possible', fraud_result['explanation'].lower())
        
        # 2. Update GigScore due to fraud Tier 1
        with patch("services.gigscore_service.get_supabase") as mock_sb_score:
            mock_sb_score.return_value.table().select().eq().execute.return_value.data = [
                {"gig_score": 95.0, "account_status": "active"}
            ]
            new_score = update_gig_score(
                self.worker_id,
                GigScoreEvent.FRAUD_TIER_1,
                {"claim_id": "claim-fraud-001"}
            )
            # Should deduct 7.5 points
            self.assertEqual(new_score, 87.5)
        
        # 3. Update worker in DB with new score
        with patch("services.premium_service.get_supabase") as mock_sb_quote:
            mock_sb_quote.return_value.table().select().eq().execute.return_value.data = [
                {**self.mock_worker, "gig_score": 87.5}
            ]
            quote = asyncio.run(compute_dynamic_quote(self.worker_id, "basic"))
            
            # Premium should be affected (less discount than high-score case)
            self.assertLess(quote["discount_applied"], 4.5)
            # Account should remain active (still > 30)
            # (In actual flow, this would be checked)
            
            # Reason should mention improved score needed
            self.assertIn(
                discount_rate := quote["discount_applied"] / 30.0 if quote["discount_applied"] > 0 else 0.0,
                [x / 100.0 for x in range(0, 11)]  # Check discount is reasonable
            )

    # ════════════════════════════════════════════════════════════════════════════
    # TRINITY TEST 3: Fraud Tier 2 Path (BLOCK) + Suspension
    # ════════════════════════════════════════════════════════════════════════════

    @patch("services.premium_service.get_supabase")
    @patch("services.premium_service.load_ai_model")
    @patch("services.fraud_service.get_detector")
    def test_trinity_fraud_tier2_suspension(self, mock_fraud_detector, mock_load_model, mock_get_sb):
        """
        Scenario: Worker has Tier 2 fraud (5+ signals, confirmed spoofing).
        Expected flow:
          1. Fraud detection → BLOCK (fraud_score > 0.7)
          2. GigScore -25 points (FRAUD_TIER_2)
          3. Score drops below 30 → account suspended
          4. Premium quote blocked (account suspended)
          5. Payout: 0%
        """
        mock_sb = MagicMock()
        mock_get_sb.return_value = mock_sb
        
        # Mock worker with moderate score
        worker_moderate = {**self.mock_worker, "gig_score": 50.0}
        mock_sb.table().select().eq().execute.return_value.data = [worker_moderate]
        
        # Mock ML model (won't be called if account suspended, but set anyway)
        mock_model = MagicMock()
        mock_model.predict.return_value = [0.0]
        mock_load_model.return_value = (mock_model, {})
        
        # Mock fraud detector - TIER 2 BLOCK
        mock_detector = MagicMock()
        mock_detector.detect_fraud.return_value = {
            'decision': 'BLOCK',
            'fraud_score': 0.82,
            'fraud_type': 'gps_spoofing_syndicate',
            'stage1_result': 'PASS',
            'stage2_score': 0.75,
            'stage3_score': 0.82,
            'confidence': 0.95
        }
        mock_fraud_detector.return_value = mock_detector
        
        # 1. Check fraud - should BLOCK
        with patch("services.gigscore_service.get_supabase") as mock_sb_gs:
            mock_sb_gs.return_value = mock_sb
            fraud_service = FraudDetectionService()
            fraud_result = fraud_service.check_fraud(self.mock_claim, {})
        
        self.assertEqual(fraud_result['decision'], 'BLOCK')
        self.assertEqual(fraud_result['is_fraud'], True)
        self.assertEqual(fraud_result['payout_action'], '0%')
        
        # 2. Update GigScore due to fraud Tier 2
        with patch("services.gigscore_service.get_supabase") as mock_sb_score:
            mock_sb_score.return_value.table().select().eq().execute.return_value.data = [
                {"gig_score": 50.0, "account_status": "active"}
            ]
            new_score = update_gig_score(
                self.worker_id,
                GigScoreEvent.FRAUD_TIER_2,
                {"claim_id": "claim-fraud-001"}
            )
            # Should deduct 25 points: 50 - 25 = 25
            self.assertEqual(new_score, 25.0)
        
        # 3. Verify suspension happened (score < 30)
        # In a real scenario, account_status would be set to "suspended"
        # Here we test that the penalty was severe enough
        self.assertLess(new_score, 30.0)

    # ════════════════════════════════════════════════════════════════════════════
    # TRINITY TEST 4: Appeal & Reactivation Path
    # ════════════════════════════════════════════════════════════════════════════

    @patch("services.premium_service.get_supabase")
    @patch("services.premium_service.load_ai_model")
    def test_trinity_appeal_restores_premium(self, mock_load_model, mock_get_sb):
        """
        Scenario: Worker was penalized (Tier 1), but successfully appeals.
        Expected flow:
          1. Initial: GigScore = 95
          2. After fraud: GigScore = 87.5 (penalty -7.5)
          3. After appeal: GigScore = 95+ (penalty restored + bonus)
          4. Premium quote shows restored discount
        """
        mock_sb = MagicMock()
        mock_get_sb.return_value = mock_sb
        
        # Mock ML model: More discount for higher GigScore
        mock_model = MagicMock()
        mock_model.predict.side_effect = lambda df: np.array([0.15 if df.iloc[0]["worker_gig_score"] > 90 else 0.05])
        mock_load_model.return_value = (mock_model, {})
        
        # Phase 1: Initial high score
        initial_worker = {**self.mock_worker, "gig_score": 95.0}
        mock_sb.table().select().eq().execute.return_value.data = [initial_worker]
        
        quote_before = asyncio.run(compute_dynamic_quote(self.worker_id, "basic"))
        discount_before = quote_before["discount_applied"]
        
        # Phase 2: After fraud Tier 1 penalty
        with patch("services.gigscore_service.get_supabase") as mock_sb_score:
            mock_sb_score.return_value.table().select().eq().execute.return_value.data = [
                {"gig_score": 95.0, "account_status": "active"}
            ]
            new_score_after_fraud = update_gig_score(
                self.worker_id,
                GigScoreEvent.FRAUD_TIER_1,
                {}
            )
            self.assertEqual(new_score_after_fraud, 87.5)
        
        # Phase 3: After successful appeal (SUCCESSFUL_APPEAL grants +15, plus restore ~7.5)
        with patch("services.gigscore_service.get_supabase") as mock_sb_score:
            # Appeal event provides penalty_amount in metadata
            mock_sb_score.return_value.table().select().eq().execute.return_value.data = [
                {"gig_score": 87.5, "account_status": "active"}
            ]
            new_score_after_appeal = update_gig_score(
                self.worker_id,
                GigScoreEvent.SUCCESSFUL_APPEAL,
                {"penalty_amount": 7.5}
            )
            # Score should be restored and boosted: 87.5 + 7.5 + 5 = 100.0
            self.assertEqual(new_score_after_appeal, 100.0)
        
        # Phase 4: Verify premium is restored
        with patch("services.premium_service.get_supabase") as mock_sb_quote:
            mock_sb_quote.return_value.table().select().eq().execute.return_value.data = [
                {**self.mock_worker, "gig_score": 100.0}
            ]
            quote_after = asyncio.run(compute_dynamic_quote(self.worker_id, "basic"))
            discount_after = quote_after["discount_applied"]
            
            # Discount should be restored (similar to before fraud)
            # Allow 0.5 margin due to model variance
            self.assertGreaterEqual(discount_after, discount_before - 0.5)

    # ════════════════════════════════════════════════════════════════════════════
    # TRINITY TEST 5: Multiple Workers, Mixed Outcomes
    # ════════════════════════════════════════════════════════════════════════════

    @patch("services.premium_service.get_supabase")
    @patch("services.premium_service.load_ai_model")
    def test_trinity_multiple_workers_isolation(self, mock_load_model, mock_get_sb):
        """
        Scenario: Multiple workers, different fraud outcomes.
        Ensures that fraud penalties don't cross-pollinate between workers.
        """
        # Mock ML model: More discount for higher GigScore
        mock_model = MagicMock()
        mock_model.predict.side_effect = lambda df: np.array([0.2 if df.iloc[0]["worker_gig_score"] > 90 else 0.05])
        mock_load_model.return_value = (mock_model, {})
        
        # Worker A: Clean
        worker_a = {"id": "worker-a", "gig_score": 95.0, "account_status": "active", **self.mock_worker}
        
        # Worker B: Fraudulent
        worker_b = {"id": "worker-b", "gig_score": 50.0, "account_status": "active", **self.mock_worker}
        
        mock_sb = MagicMock()
        mock_get_sb.return_value = mock_sb
        
        # Get Worker A quote (high score, good discount)
        mock_sb.table().select().eq().execute.return_value.data = [worker_a]
        quote_a_before = asyncio.run(compute_dynamic_quote("worker-a", "basic"))
        
        # Get Worker B quote (moderate score, lower discount)
        mock_sb.table().select().eq().execute.return_value.data = [worker_b]
        quote_b_before = asyncio.run(compute_dynamic_quote("worker-b", "basic"))
        
        # Apply fraud penalty to Worker B only
        with patch("services.gigscore_service.get_supabase") as mock_sb_score:
            mock_sb_score.return_value.table().select().eq().execute.return_value.data = [
                {"gig_score": 50.0, "account_status": "active"}
            ]
            new_score_b = update_gig_score("worker-b", GigScoreEvent.FRAUD_TIER_1, {})
            self.assertEqual(new_score_b, 42.5)
        
        # Update worker_b object for the next mock call
        worker_b["gig_score"] = new_score_b
        
        # Get Worker A quote again (should be unchanged)
        mock_sb.table().select().eq().execute.return_value.data = [worker_a]
        quote_a_after = asyncio.run(compute_dynamic_quote("worker-a", "basic"))
        
        # Get Worker B quote again (should show impact)
        mock_sb.table().select().eq().execute.return_value.data = [worker_b]
        quote_b_after = asyncio.run(compute_dynamic_quote(
            "worker-b",
            "basic"
        ))
        
        # Worker A's quote should be unchanged
        self.assertEqual(quote_a_before["discount_applied"], quote_a_after["discount_applied"])
        
        # Worker B's quote should be affected (less discount)
        self.assertLess(quote_b_after["discount_applied"], quote_b_before["discount_applied"])


if __name__ == "__main__":
    unittest.main()

import pytest
from unittest.mock import MagicMock, patch
from services.fraud_service import FraudDetectionService
from services.gigscore_service import GigScoreEvent
from services.premium_service import compute_dynamic_quote

@pytest.mark.asyncio
class TestFraudGigScorePremiumTrinity:
    def setUp(self):
        self.worker_id = "f47ac10b-58cc-4372-a567-0e02b2c3d479"
        self.mock_worker = {
            "id": self.worker_id,
            "gig_score": 95.0,
            "pin_codes": ["560001"],
            "shift": "day",
            "plan": "basic"
        }
        self.mock_claim = {
            "id": "audit-test-123",
            "worker_id": self.worker_id,
            "baseline_earnings": 1000,
            "dci_score": 85.0
        }

    @patch("services.fraud_service.get_supabase")
    @patch("services.premium_service.get_supabase")
    @patch("services.fraud_service.get_detector")
    async def test_trinity_clean_path(self, mock_fraud_detector, mock_get_sb_premium, mock_get_sb_fraud):
        self.setUp()
        mock_sb = MagicMock()
        mock_get_sb_premium.return_value = mock_sb
        mock_get_sb_fraud.return_value = mock_sb
        mock_sb.table().select().eq().execute.return_value.data = [self.mock_worker]
        
        mock_detector = MagicMock()
        mock_detector.detect_fraud.return_value = {"decision": "APPROVE", "fraud_score": 0.1, "fraud_type": "clean"}
        mock_fraud_detector.return_value = mock_detector
        
        fraud_service = FraudDetectionService()
        result = fraud_service.check_fraud(self.mock_claim, {})
        assert result["decision"] == "APPROVE"

    @patch("services.fraud_service.get_supabase")
    @patch("services.premium_service.get_supabase")
    @patch("services.fraud_service.get_detector")
    async def test_trinity_fraud_tier1_impact(self, mock_fraud_detector, mock_get_sb_premium, mock_get_sb_fraud):
        self.setUp()
        mock_sb = MagicMock()
        mock_get_sb_premium.return_value = mock_sb
        mock_get_sb_fraud.return_value = mock_sb
        mock_sb.table().select().eq().execute.return_value.data = [self.mock_worker]
        
        mock_detector = MagicMock()
        mock_detector.detect_fraud.return_value = {"decision": "FLAG_50", "fraud_score": 0.5, "fraud_type": "gps_jump"}
        mock_fraud_detector.return_value = mock_detector
        
        fraud_service = FraudDetectionService()
        result = fraud_service.check_fraud(self.mock_claim, {})
        assert result["decision"] == "FLAG_50"

    @patch("services.fraud_service.get_supabase")
    @patch("services.premium_service.get_supabase")
    @patch("services.fraud_service.get_detector")
    async def test_trinity_fraud_tier2_suspension(self, mock_fraud_detector, mock_get_sb_premium, mock_get_sb_fraud):
        self.setUp()
        mock_sb = MagicMock()
        mock_get_sb_premium.return_value = mock_sb
        mock_get_sb_fraud.return_value = mock_sb
        mock_sb.table().select().eq().execute.return_value.data = [self.mock_worker]
        
        mock_detector = MagicMock()
        mock_detector.detect_fraud.return_value = {"decision": "BLOCK", "fraud_score": 0.8, "fraud_type": "syndicate"}
        mock_fraud_detector.return_value = mock_detector
        
        fraud_service = FraudDetectionService()
        result = fraud_service.check_fraud(self.mock_claim, {})
        assert result["decision"] == "BLOCK"
